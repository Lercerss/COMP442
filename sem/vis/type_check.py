from itertools import chain
from typing import List

from lex.token import Keywords as K, Literals as L, Location, Operators as O
from sem.visitor import Visitor
from sem.table import (
    BOOLEAN,
    DATA_RECORD_TYPES,
    equal_params,
    FLOAT,
    GLOBALS,
    INT,
    Record,
    RecordType,
    SymbolTable,
    SymbolType,
    VOID,
)
from syn.ast import ASTNode, GroupNodeType, LeafNodeType, ListNodeType


class TypeExtractor:
    def __init__(self, container: Visitor, scope: SymbolTable):
        self.handlers = {
            node_type: getattr(self, "_visit_" + str(node_type), lambda n, t: t)
            for node_type in chain(GroupNodeType, LeafNodeType, ListNodeType)
        }
        self.scope = scope
        self.container = container
        self.error = container.error
        self.warn = container.warn

    def visit(self, node: ASTNode) -> List[SymbolType]:
        types = [self.visit(c) for c in node.children]
        return self.handlers[node.node_type](node, types)

    def _temp_record(self, type_, node):
        node.record = Record("", type_, RecordType.TEMP, None)
        self.scope.insert(node.record)

    def _binary_op(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        if None in types:
            return None

        if types[0] != types[1]:
            self.error(
                'Mismatched types "{left}" and "{right}" for "{bin_op}" operator'.format(
                    bin_op=node.token.lexeme, left=types[0], right=types[1]
                ),
                node.token.location,
            )
            return None

        expected_types = (
            (BOOLEAN) if node.token.token_type in (O.AND, O.OR) else (FLOAT, INT)
        )
        if sum(len(t.dims) for t in types) > 2 or types[0].base not in expected_types:
            self.error(
                'Cannot apply operation "{bin_op}" on types "{left}" and "{right}"'.format(
                    bin_op=node.token.lexeme, left=types[0], right=types[1]
                ),
                node.token.location,
            )
            return None
        return types[0]

    def _visit_rel_expr(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        if self._binary_op(node, types) is None:
            return None
        return SymbolType(BOOLEAN, [])

    def _visit_add_expr(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        type_ = self._binary_op(node, types)
        self._temp_record(type_, node)
        return type_

    def _visit_mult_expr(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        type_ = self._binary_op(node, types)
        self._temp_record(type_, node)
        return type_

    def _visit_not(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        type_ = types[0]
        self._temp_record(type_, node)
        return type_

    def _visit_sign(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        type_ = types[0]
        self._temp_record(type_, node)
        return type_

    def _type_for_data_member(
        self,
        node: ASTNode,
        types: List[SymbolType],
        records: List[Record],
        is_first: bool,
    ) -> SymbolType:
        token = node.children[0].token
        record = next((r for r in records if r.record_type in DATA_RECORD_TYPES), None,)
        if record is None:
            self.error(
                'Use of undeclared {type} "{name}"'.format(
                    type="local variable" if is_first else "data member",
                    name=token.lexeme,
                ),
                token.location,
            )
            return None

        index_types = types or []
        if len(index_types) > len(record.type.dims) or any(
            type_ != SymbolType(INT, []) for type_ in index_types
        ):
            self.error(
                'Invalid indexing for "{name}", type is "{type}"'.format(
                    name=token.lexeme, type=record.format_type()
                ),
                token.location,
            )
            return None

        if index_types:
            # Reserve space for offset calculation
            node.temp_record = Record("", SymbolType(INT, []), RecordType.TEMP, None)
            self.scope.insert(node.temp_record)

        node.record = record
        return SymbolType(record.type.base, record.type.dims[len(index_types) :])

    def _type_for_func_call(
        self,
        node: ASTNode,
        types: List[SymbolType],
        records: List[Record],
        is_first: bool,
    ) -> SymbolType:
        params = [
            Record("", t, RecordType.PARAM, node.children[0].token.location)
            for t in types
        ]
        record = next(
            (
                r
                for r in records
                if r.record_type == RecordType.FUNCTION
                and equal_params(r.params, params)
            ),
            None,
        )
        if record is None:
            self.error(
                'Use of undeclared {type} "{name}({f_type})"'.format(
                    type="function" if is_first else "member function",
                    name=node.children[0].token.lexeme,
                    f_type=", ".join(p.format_type() for p in params),
                ),
                node.children[0].token.location,
            )
            return None
        self._temp_record(record.type, node)
        node.record.table = record.table
        return record.type

    def _type_for_node(
        self, node: ASTNode, types: List[SymbolType], scope: SymbolTable, is_first: bool
    ):
        node_type = node.node_type
        name = node.children[0].token.lexeme
        location = node.children[0].token.location
        if not scope:
            self.error(
                'Use of the "." operator on non-class symbol', location,
            )
            return None
        if is_first:
            records = scope.search_in_scope(name)
        else:
            records = scope.search_member(
                name, K.PRIVATE if self.scope.has_private_access(scope) else K.PUBLIC
            )
        if not records:
            self.error(
                'Use of undeclared {type} "{name}"'.format(
                    type="local variable" if is_first else "data member", name=name,
                ),
                location,
            )
            return None

        if node_type == GroupNodeType.DATA_MEMBER:
            return self._type_for_data_member(node, types, records, is_first)
        else:
            return self._type_for_func_call(node, types, records, is_first)

    def _type_for_node_chain(
        self, node: ASTNode, types: List[SymbolType]
    ) -> SymbolType:
        scope = self.scope
        for i in range(len(node.children)):
            child = node.children[i]
            type_ = self._type_for_node(child, types[i], scope, i == 0)
            if type_ is None:
                return None
            scope = type_.base.table
        return type_

    def _visit_var(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        return self._type_for_node_chain(node, types)

    def _visit_f_call_stat(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        return self._type_for_node_chain(node, types)

    def _visit_f_call(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        # Pass types extracted from arg_list
        return types[1]

    def _visit_data_member(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        # Pass types extracted from index_list
        return types[1]

    def _visit_arg_list(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        # Pass types extracted from children
        return types

    def _visit_index_list(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        # Pass types extracted from children
        return types

    def _visit_literal(self, node: ASTNode, types: List[SymbolType]) -> SymbolType:
        if node.token.token_type == L.INTEGER_LITERAL:
            return SymbolType(INT, [])
        return SymbolType(FLOAT, [])


class TypeCheck(Visitor):
    def _parent_scope(self, node: ASTNode):
        parent = node.parent
        while parent is not None:
            if parent.record and parent.record.table:
                return parent.record

            parent = parent.parent
        return None

    def _invalid_type(self, expr: str, found: SymbolType, location: Location):
        self.error(
            'Invalid type "{type}" for {expr} expression'.format(
                type=str(found), expr=expr
            ),
            location,
        )

    def _visit_f_call_stat(self, node: ASTNode):
        if node.parent.node_type == ListNodeType.STAT_BLOCK:
            TypeExtractor(self, self._parent_scope(node).table).visit(node)

    def _visit_if_stat(self, node: ASTNode):
        type_ = TypeExtractor(self, self._parent_scope(node).table).visit(
            node.children[0]
        )
        if type_ is None:
            return

        if type_.base != BOOLEAN and not type_.is_array():
            self._invalid_type("if()", type_, node.token.location)

    def _visit_assign_stat(self, node: ASTNode):
        extractor = TypeExtractor(self, self._parent_scope(node).table)
        var_type = extractor.visit(node.children[0])
        val_type = extractor.visit(node.children[1])
        if var_type is None or val_type is None:
            return

        if var_type != val_type:
            last_id = node.children[0].children[-1].children[0].token
            self.error(
                'Invalid type "{val_type}" for assignment to "{name}", expected "{var_type}"'.format(
                    val_type=val_type, name=last_id.lexeme, var_type=var_type
                ),
                last_id.location,
            )

    def _visit_while_stat(self, node: ASTNode):
        type_ = TypeExtractor(self, self._parent_scope(node).table).visit(
            node.children[0]
        )
        if type_ is None:
            return

        if type_.base != BOOLEAN and not type_.is_array():
            self._invalid_type("while()", type_, node.token.location)

    def _visit_read_stat(self, node: ASTNode):
        type_ = TypeExtractor(self, self._parent_scope(node).table).visit(
            node.children[0]
        )
        if type_ is None:
            return

        if type_.base not in (FLOAT, INT) and not type_.is_array():
            self._invalid_type("read()", type_, node.token.location)

    def _visit_write_stat(self, node: ASTNode):
        type_ = TypeExtractor(self, self._parent_scope(node).table).visit(
            node.children[0]
        )
        if type_ is None:
            return

        if type_.base not in (FLOAT, INT) and not type_.is_array():
            self._invalid_type("write()", type_, node.token.location)

    def _visit_return_stat(self, node: ASTNode):
        func_record = self._parent_scope(node)
        type_ = TypeExtractor(self, func_record.table).visit(node.children[0])
        if type_ is None:
            return

        if type_ != func_record.type:
            self.error(
                'Return type "{type}" does not match function\'s declared return type'.format(
                    type=type_
                ),
                node.token.location,
            )

    def _visit_prog(self, node: ASTNode):
        GLOBALS.update_offsets()

    def _visit_id(self, node: ASTNode):
        return

    def _visit_type(self, node: ASTNode):
        return

    def _visit_literal(self, node: ASTNode):
        return

    def _visit_visibility(self, node: ASTNode):
        return

    def _visit_scope_spec(self, node: ASTNode):
        return

    def _visit_epsilon(self, node: ASTNode):
        return

    def _visit_class_list(self, node: ASTNode):
        return

    def _visit_func_list(self, node: ASTNode):
        return

    def _visit_inher_list(self, node: ASTNode):
        return

    def _visit_member_list(self, node: ASTNode):
        return

    def _visit_local_list(self, node: ASTNode):
        return

    def _visit_param_list(self, node: ASTNode):
        return

    def _visit_dim_list(self, node: ASTNode):
        return

    def _visit_stat_block(self, node: ASTNode):
        return

    def _visit_var(self, node: ASTNode):
        return

    def _visit_index_list(self, node: ASTNode):
        return

    def _visit_arg_list(self, node: ASTNode):
        return

    def _visit_main(self, node: ASTNode):
        return

    def _visit_class_decl(self, node: ASTNode):
        return

    def _visit_func_decl(self, node: ASTNode):
        return

    def _visit_func_def(self, node: ASTNode):
        return

    def _visit_member_decl(self, node: ASTNode):
        return

    def _visit_var_decl(self, node: ASTNode):
        return

    def _visit_func_param(self, node: ASTNode):
        return

    def _visit_data_member(self, node: ASTNode):
        return

    def _visit_f_call(self, node: ASTNode):
        return

    def _visit_rel_expr(self, node: ASTNode):
        return

    def _visit_add_expr(self, node: ASTNode):
        return

    def _visit_mult_expr(self, node: ASTNode):
        return

    def _visit_not(self, node: ASTNode):
        return

    def _visit_sign(self, node: ASTNode):
        return
