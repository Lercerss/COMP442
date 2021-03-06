from collections import defaultdict
from itertools import chain
from typing import List

from lex import Generic as G
from sem.visitor import Visitor
from sem.table import (
    BaseType,
    equal_params,
    GLOBALS,
    VOID,
    RecordType,
    SymbolTable,
)
from syn.ast import ASTNode, GroupNodeType, LeafNodeType, ListNodeType


class ReturnVisitor:
    def __init__(self, container):
        self.handlers = {
            node_type: getattr(self, "_visit_" + str(node_type), lambda n, t: any(t))
            for node_type in chain(GroupNodeType, LeafNodeType, ListNodeType)
        }
        self.error = container.error

    def visit(self, node: ASTNode) -> bool:
        branches = [self.visit(c) for c in node.children]
        return self.handlers[node.node_type](node, branches)

    def _visit_return_stat(self, node: ASTNode, branches: List[bool]):
        return True

    def _visit_if_stat(self, node: ASTNode, branches: List[bool]):
        return branches[1] and branches[2]  # Both stat_blocks must be True

    def _visit_while_stat(self, node: ASTNode, branches: List[bool]):
        return branches[1]

    def _visit_stat_block(self, node: ASTNode, branches: List[bool]):
        if not branches:
            return False

        if not branches[-1] and any(branches):
            first_return = next(i for i, b in enumerate(branches) if b)
            self.error(
                "Unreachable statement", node.children[first_return + 1].token.location
            )
        return any(branches)


class TableCheck(Visitor):
    def __init__(self, output=None):
        super().__init__(output=output)
        self.cycles = set()
        self.return_visitor = ReturnVisitor(self)

    def _add_cycle(self, cycle: List[BaseType], location):
        cycle = [type_.name for type_ in cycle]
        cycle_hash = tuple(sorted(cycle))
        if cycle_hash in self.cycles:
            # Avoid reporting duplicate cycles
            return

        self.cycles.add(cycle_hash)
        self.error(
            "Class dependency cycle found {{{}}}".format("->".join(reversed(cycle))),
            location,
        )

    def check_dependency_cycles(self, node: ASTNode):
        table = node.record.table
        inherits = [(parent, [BaseType(table.name)]) for parent in table.dependencies()]
        while inherits:
            parent, introduced_by = inherits.pop(0)
            if len(set(introduced_by)) != len(introduced_by):
                cycle = introduced_by[: introduced_by.index(introduced_by.pop(0)) + 1]
                self._add_cycle(cycle, node.children[0].token.location)
                table.remove_dependency(cycle[-2])
                return
            inherits += [
                (new_parent, [parent, *introduced_by])
                for new_parent in parent.table.dependencies()
            ]

    def check_basic_inheritance(self, node: ASTNode):
        table = node.record.table
        name = node.record.name
        for parent in table.inherits:
            if parent.table is None:
                table.inherits.remove(parent)
                self.error(
                    'Use of undeclared class "{name}"'.format(name=parent.name),
                    node.children[0].token.location,
                )

        if BaseType(name) in table.inherits:
            table.inherits.remove(BaseType(name))
            self.error(
                'Class "{name}" cannot inherit from itself'.format(name=name),
                node.children[0].token.location,
            )

    def check_duplicate_entries(self, table: SymbolTable, is_class_scope: bool = False):
        for name, records in table.entries.items():
            records_per_type = defaultdict(list)
            for r in records:
                records_per_type[r.record_type].append(r)

            if len(records_per_type[RecordType.FUNCTION]) > 1:
                name = ((table.name + "::") if is_class_scope else "") + name
                params_lookup = defaultdict(list)
                for record in records_per_type[RecordType.FUNCTION]:
                    params_lookup[tuple(r.type for r in record.params)].append(record)
                if len(params_lookup) != len(records_per_type[RecordType.FUNCTION]):
                    while params_lookup:
                        _, dup_records = params_lookup.popitem()
                        if len(dup_records) > 1:
                            self.error(
                                'Multiply declared function "{name}{type}"'.format(
                                    name=name, type=dup_records[1].format_type()
                                )
                            )
                else:
                    self.warn('Function "{name}" is overloaded'.format(name=name))

            if len(records_per_type[RecordType.CLASS]) > 1:
                self.error(
                    'Multiply declared class "{name}"'.format(name=name),
                    records_per_type[RecordType.CLASS][1].location,
                )

            if len(records_per_type[RecordType.LOCAL]) > 1 or (
                len(records_per_type[RecordType.PARAM]) > 0
                and len(records_per_type[RecordType.LOCAL]) > 0
            ):
                self.error(
                    'Multiply declared local variable "{name}"'.format(name=name),
                    records_per_type[RecordType.LOCAL][:2][-1].location,
                )

            if len(records_per_type[RecordType.DATA]) > 1:
                self.error(
                    'Multiply declared data member "{name}"'.format(name=name),
                    records_per_type[RecordType.DATA][1].location,
                )

            if len(records_per_type[RecordType.PARAM]) > 1:
                self.error(
                    'Multiply declared parameter "{name}"'.format(name=name),
                    records_per_type[RecordType.PARAM][1].location,
                )

    def check_shadowed_members(self, table: SymbolTable):
        for name, records in table.entries.items():
            parent_records = [
                pr
                for pr in table.search_member(name)
                if all(pr is not r for r in records)
            ]
            data_member = next(
                (r for r in records if r.record_type == RecordType.DATA), None
            )
            if data_member and any(
                r.record_type == RecordType.DATA for r in parent_records
            ):
                self.warn(
                    'Data member "{name}" shadows inherited member'.format(name=name),
                    data_member.location,
                )

            funcs = [r for r in records if r.record_type == RecordType.FUNCTION]
            parent_funcs = [
                r.params for r in parent_records if r.record_type == RecordType.FUNCTION
            ]
            if parent_funcs:
                for func in funcs:
                    if any(
                        equal_params(parent, func.params) for parent in parent_funcs
                    ):
                        self.warn(
                            'Function "{name}{type}" shadows inherited member'.format(
                                name=name, type=func.format_type()
                            ),
                            func.location,
                        )

    def _visit_prog(self, node: ASTNode):
        self.check_duplicate_entries(GLOBALS)

    def _visit_main(self, node: ASTNode):
        self.check_duplicate_entries(node.record.table)

    def _visit_class_decl(self, node: ASTNode):
        self.check_basic_inheritance(node)
        self.check_dependency_cycles(node)
        self.check_duplicate_entries(node.record.table, is_class_scope=True)
        self.check_shadowed_members(node.record.table)

    def check_has_return_stat(self, node: ASTNode):
        if not self.return_visitor.visit(node.children[-1]):  # Visit stat_block
            scope = node.children[0].token.lexeme if node.children[0].token else ""
            token = node.children[1].token
            self.error(
                'Missing return statement for function "{}"'.format(
                    scope + "::" + token.lexeme
                ),
                token.location,
            )

    def _visit_func_def(self, node: ASTNode):
        self.check_duplicate_entries(node.record.table)
        if node.record.type.base != VOID:
            self.check_has_return_stat(node)

    def _visit_func_decl(self, node: ASTNode):
        if node.record.table is None:
            self.error(
                'Member function "{scope}::{name}{type}" is declared but has not been defined'.format(
                    scope=node.parent.parent.parent.children[0].token.lexeme,
                    name=node.record.name,
                    type=node.record.format_type(),
                ),
                node.children[0].token.location,
            )

    def _visit_type(self, node: ASTNode):
        token = node.token
        if token.token_type == G.ID and BaseType(token.lexeme).table is None:
            self.error(
                'Use of undeclared class "{name}"'.format(name=token.lexeme),
                token.location,
            )

    def _visit_id(self, node: ASTNode):
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

    def _visit_f_call_stat(self, node: ASTNode):
        return

    def _visit_index_list(self, node: ASTNode):
        return

    def _visit_arg_list(self, node: ASTNode):
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
