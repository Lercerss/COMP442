from abc import ABC, abstractmethod
from itertools import chain

from syn.ast import ASTNode, GroupNodeType, LeafNodeType, ListNodeType


class Visitor(ABC):
    def __init__(self, output=None):
        self.handlers = {  # Dynamic dispatch
            node_type: getattr(self, "_visit_" + str(node_type))
            for node_type in chain(GroupNodeType, LeafNodeType, ListNodeType)
        }
        self.output = output

    def visit(self, node: ASTNode):
        self.handlers[node.node_type](node)

    def warn(self, msg: str):
        if self.output:
            self.output.warn(msg)

    def error(self, msg: str):
        if self.output:
            self.output.error(msg)

    @abstractmethod
    def _visit_id(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_type(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_literal(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_rel_op(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_add_op(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_mult_op(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_visibility(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_scope_spec(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_epsilon(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_class_list(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_func_list(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_inher_list(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_member_list(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_local_list(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_param_list(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_dim_list(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_stat_block(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_var(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_f_call_stat(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_index_list(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_arg_list(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_prog(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_main(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_class_decl(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_func_decl(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_func_def(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_member_decl(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_var_decl(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_func_param(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_data_member(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_f_call(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_if_stat(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_assign_stat(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_while_stat(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_read_stat(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_write_stat(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_return_stat(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_rel_expr(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_add_expr(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_mult_expr(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_not(self, node: ASTNode):
        raise NotImplementedError()

    @abstractmethod
    def _visit_sign(self, node: ASTNode):
        raise NotImplementedError()
