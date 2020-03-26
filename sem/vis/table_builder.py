from sem.visitor import Visitor
from sem.table import (
    BaseType,
    equal_params,
    GLOBALS,
    Record,
    RecordType,
    SymbolTable,
    SymbolType,
    VOID,
)
from syn.ast import ASTNode


class TableBuilder(Visitor):
    def _visit_class_list(self, node: ASTNode):
        for child in node.children:
            GLOBALS.insert(child.record)

    def _visit_func_list(self, node: ASTNode):
        return

    def _visit_inher_list(self, node: ASTNode):
        return

    def _visit_member_list(self, node: ASTNode):
        for child in node.children:
            child.record.record_type = child.record.record_type or RecordType.DATA

    def _visit_local_list(self, node: ASTNode):
        for child in node.children:
            child.record.record_type = RecordType.LOCAL

    def _visit_param_list(self, node: ASTNode):
        return

    def _visit_dim_list(self, node: ASTNode):
        return

    def _visit_arg_list(self, node: ASTNode):
        return

    def _visit_prog(self, node: ASTNode):
        GLOBALS.insert(node.children[2].record)

    def _visit_main(self, node: ASTNode):
        table = SymbolTable("main")
        for child in node.children[0].children:  # Locals
            table.insert(child.record)
        node.record = Record(
            "main",
            SymbolType("void", []),
            RecordType.FUNCTION,
            node.token.location,
            params=[],
            table=table,
        )

    def _visit_class_decl(self, node: ASTNode):
        name = node.children[0].token.lexeme
        table = SymbolTable(
            name,
            [BaseType(inherit.token.lexeme) for inherit in node.children[1].children],
        )

        for child in node.children[2].children:  # Members
            table.insert(child.record)
        node.record = Record(
            name, None, RecordType.CLASS, node.children[0].token.location, table=table
        )

    def _visit_func_decl(self, node: ASTNode):
        # Only for member function
        node.record = Record(
            node.children[0].token.lexeme,
            SymbolType(node.children[2].token.lexeme, []),
            RecordType.FUNCTION,
            node.children[0].token.location,
            params=[param.record for param in node.children[1].children],
        )

    def _visit_func_def(self, node: ASTNode):
        name = node.children[1].token.lexeme
        table = SymbolTable(name)
        params = [param.record for param in node.children[2].children]
        for param in params:
            table.insert(param)

        for child in node.children[4].children:  # Locals
            table.insert(child.record)

        node.record = Record(
            name,
            SymbolType(node.children[3].token.lexeme, []),
            RecordType.FUNCTION,
            node.children[1].token.location,
            params=params,
            table=table,
        )

        scope = node.children[0].token
        if scope:
            parent = BaseType(scope.lexeme).table
            if not parent:
                self.error(
                    'Class "{name}" has not been declared'.format(name=scope.lexeme),
                    scope.location,
                )
                return
            records = parent.entries.get(name, [])
            record = next(
                (
                    r
                    for r in records
                    if r.record_type == RecordType.FUNCTION
                    and equal_params(r.params, params)
                    and r.type.base is node.record.type.base
                ),
                None,
            )
            if not record:
                self.error(
                    'Member function "{scope}::{name}{type}" is defined but has not been declared'.format(
                        scope=scope.lexeme, name=name, type=node.record.format_type()
                    ),
                    scope.location,
                )
                return
            record.table = table  # Attach table on existing record in the class table
            table.inherits = [BaseType(scope.lexeme)]
            table.name = scope.lexeme + "::" + table.name
            node.record = record
        else:
            GLOBALS.insert(node.record)

    def _visit_member_decl(self, node: ASTNode):
        node.record = node.children[1].record
        node.record.visibility = node.children[0].token.token_type

    def _visit_var_decl(self, node: ASTNode):
        node.record = Record(
            node.children[1].token.lexeme,  # ID
            SymbolType(
                node.children[0].token.lexeme,
                [child.token for child in node.children[2].children],
            ),
            None,
            node.children[1].token.location,
        )

    def _visit_func_param(self, node: ASTNode):
        node.record = Record(
            node.children[1].token.lexeme,  # ID
            SymbolType(
                node.children[0].token.lexeme,
                [child.token for child in node.children[2].children],
            ),
            RecordType.PARAM,
            node.children[1].token.location,
        )

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

    def _visit_stat_block(self, node: ASTNode):
        return

    def _visit_var(self, node: ASTNode):
        return

    def _visit_f_call_stat(self, node: ASTNode):
        return

    def _visit_index_list(self, node: ASTNode):
        return

    def _visit_data_member(self, node: ASTNode):
        return

    def _visit_f_call(self, node: ASTNode):
        return

    def _visit_if_stat(self, node: ASTNode):
        return

    def _visit_assign_stat(self, node: ASTNode):
        return

    def _visit_while_stat(self, node: ASTNode):
        return

    def _visit_read_stat(self, node: ASTNode):
        return

    def _visit_write_stat(self, node: ASTNode):
        return

    def _visit_return_stat(self, node: ASTNode):
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

    def _visit_epsilon(self, node: ASTNode):
        return
