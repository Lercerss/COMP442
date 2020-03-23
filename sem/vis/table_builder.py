from sem.visitor import Visitor
from sem.table import GLOBALS, Record, RecordType, SymbolTable, SymbolType, VOID
from syn.ast import ASTNode


class TableBuilder(Visitor):
    def _visit_class_list(self, node: ASTNode):
        # TODO Could use some refactoring
        inheritance = {}
        for child in node.children:
            inheritance[child.record.table.name] = [
                parent.name for parent in child.record.table.inherits
            ]
            GLOBALS.insert(child.record)

        for child in node.children:
            for parent in child.children[1].children:
                if parent.token.lexeme not in inheritance:
                    self.error(
                        'Class "{name}" has not been declared: '
                        "line {location.line}, column {location.column}".format(
                            name=parent.token.lexeme, location=parent.token.location
                        )
                    )

        cycles = set()
        for class_, inherits in inheritance.items():
            inherits = [(parent, [class_]) for parent in inherits]
            count = 0
            while inherits:
                parent, introduced_by = inherits.pop(0)
                if len(set(introduced_by)) != len(introduced_by):
                    cycles.add(
                        tuple(
                            sorted(
                                introduced_by[
                                    : introduced_by.index(introduced_by.pop(0)) + 1
                                ]
                            )
                        )
                    )
                    break
                inherits += [
                    (new_parent, [parent, *introduced_by])
                    for new_parent in inheritance[parent]
                ]
                count += 1
                if count > 15:
                    raise RecursionError()  # TODO Remove debug

        for cycle in cycles:
            self.error("Class inheritance cycle found: {{{}}}".format(", ".join(cycle)))
            # TODO Refactor error recovery? Needs some logging
            inherits = SymbolType(cycle[0]).table.inherits
            inherits.remove(
                next(SymbolType(c) for c in cycle if SymbolType(c) in inherits)
            )  # Break cycle

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
        node.record = Record("main", VOID, RecordType.FUNCTION, table=table)

    def _visit_class_decl(self, node: ASTNode):
        name = node.children[0].token.lexeme
        table = SymbolTable(
            name,
            [SymbolType(inherit.token.lexeme) for inherit in node.children[1].children],
        )
        if SymbolType(name) in table.inherits:
            # TODO Refactor error recovery? Needs some logging
            table.inherits.remove(SymbolType(name))
            self.error('Class "{}" cannot inherit from itself.'.format(name))

        for child in node.children[2].children:  # Members
            table.insert(child.record)
        node.record = Record(name, None, RecordType.CLASS, table=table)

    def _visit_func_decl(self, node: ASTNode):
        # Only for member function
        node.record = Record(
            node.children[0].token.lexeme,
            SymbolType(node.children[2].token.lexeme),
            RecordType.FUNCTION,
            params=[param.record for param in node.children[1].children],
        )

    def _visit_func_def(self, node: ASTNode):
        # TODO Could use some refactoring
        name = node.children[1].token.lexeme
        table = SymbolTable(name)
        params = [param.record for param in node.children[2].children]
        for param in params:
            table.insert(param)

        for child in node.children[4].children:  # Locals
            table.insert(child.record)

        node.record = Record(
            name,
            SymbolType(node.children[3].token.lexeme),
            RecordType.FUNCTION,
            params=params,
            table=table,
        )

        scope = node.children[0].token
        if scope:
            parent = SymbolType(scope.lexeme).table
            if not parent:
                self.error(
                    'Class "{name}" has not been declared: '
                    "line {location.line}, column {location.column}".format(
                        name=scope.lexeme, location=scope.location
                    )
                )
                return
            records = parent.search_member(name)
            record = next(
                (
                    r
                    for r in records
                    if r.record_type == RecordType.FUNCTION
                    and r.params == params
                    and r.type is node.record.type
                ),
                None,
            )
            if not record:
                self.error(
                    'Member function "{scope}::{name}{type}" is defined but has not been declared'.format(
                        scope=scope.lexeme, name=name, type=node.record.format_type()
                    )
                )
                return
            record.table = table  # Attach table on existing record in the class table
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
            SymbolType(node.children[0].token.lexeme),  # Type ID
            None,
            [child.token for child in node.children[2].children],  # Dims
        )

    def _visit_func_param(self, node: ASTNode):
        node.record = Record(
            node.children[1].token.lexeme,  # ID
            SymbolType(node.children[0].token.lexeme),  # Type ID
            RecordType.PARAM,
            [child.token for child in node.children[2].children],  # Dims
        )

    def _visit_id(self, node: ASTNode):
        return

    def _visit_type(self, node: ASTNode):
        return

    def _visit_literal(self, node: ASTNode):
        return

    def _visit_rel_op(self, node: ASTNode):
        return

    def _visit_add_op(self, node: ASTNode):
        return

    def _visit_mult_op(self, node: ASTNode):
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
