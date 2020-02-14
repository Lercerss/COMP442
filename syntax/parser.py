from collections import namedtuple
from typing import Generator, Tuple

from lex import Scanner, Token, TokenType
from .sets import *
from .ast import ASTNode, GroupNodeType, LeafNodeType, ListNodeType

ParserResult = namedtuple("ParserResult", ["success", "ast"])


class Parser:
    def __init__(self, source):
        self.scanner: Scanner = Scanner(source)
        self.lookahead: Token = None
        self.token_iter: Generator[Token, None, None] = None

    def _next(self):
        previous = self.lookahead
        self.lookahead = next(self.token_iter)
        return previous

    def _match(self, token_type: TokenType):
        return self._next().token_type == token_type

    def start(self) -> Tuple[bool, ASTNode]:
        self.token_iter = iter(self.scanner)
        self._next()
        root = ASTNode(GroupNodeType.PROG, self.lookahead)
        try:
            if all(self._prog(root), self._match(G.EOF)):
                return True
        except StopIteration:
            pass
        return False

    def _add_op(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_add_op
        follow = FOLLOW_add_op

    def _a_params(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_a_params
        follow = FOLLOW_a_params

    def _a_params_tail(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_a_params_tail
        follow = FOLLOW_a_params_tail

    def _arith_expr(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_arith_expr
        follow = FOLLOW_arith_expr

    def _array_size(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_array_size
        follow = FOLLOW_array_size

    def _assign_op(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_assign_op
        follow = FOLLOW_assign_op

    def _assign_stat(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_assign_stat
        follow = FOLLOW_assign_stat

    def _class_decl(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_class_decl
        follow = FOLLOW_class_decl

    def _expr(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_expr
        follow = FOLLOW_expr

    def _factor(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_factor
        follow = FOLLOW_factor

    def _f_params(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_f_params
        follow = FOLLOW_f_params

    def _f_params_tail(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_f_params_tail
        follow = FOLLOW_f_params_tail

    def _func_body(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_func_body
        follow = FOLLOW_func_body

    def _func_decl(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_func_decl
        follow = FOLLOW_func_decl

    def _func_def(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_func_def
        follow = FOLLOW_func_def

    def _func_head(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_func_head
        follow = FOLLOW_func_head

    def _function_call(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_function_call
        follow = FOLLOW_function_call

    def _idnest(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_idnest
        follow = FOLLOW_idnest

    def _indice(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_indice
        follow = FOLLOW_indice

    def _member_decl(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_member_decl
        follow = FOLLOW_member_decl

    def _mult_op(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_mult_op
        follow = FOLLOW_mult_op

    def _opt_class_decl2(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_opt_class_decl2
        follow = FOLLOW_opt_class_decl2

    def _opt_func_body0(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_opt_func_body0
        follow = FOLLOW_opt_func_body0

    def _opt_func_head0(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_opt_func_head0
        follow = FOLLOW_opt_func_head0

    def _prog(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_prog
        follow = FOLLOW_prog

    def _rel_expr(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rel_expr
        follow = FOLLOW_rel_expr

    def _rel_op(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rel_op
        follow = FOLLOW_rel_op

    def _rept_a_params1(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_a_params1
        follow = FOLLOW_rept_a_params1

    def _rept_class_decl4(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_class_decl4
        follow = FOLLOW_rept_class_decl4

    def _rept_f_params2(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_f_params2
        follow = FOLLOW_rept_f_params2

    def _rept_f_params3(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_f_params3
        follow = FOLLOW_rept_f_params3

    def _rept_f_params_tail3(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_f_params_tail3
        follow = FOLLOW_rept_f_params_tail3

    def _rept_func_body2(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_func_body2
        follow = FOLLOW_rept_func_body2

    def _rept_function_call0(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_function_call0
        follow = FOLLOW_rept_function_call0

    def _rept_idnest1(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_idnest1
        follow = FOLLOW_rept_idnest1

    def _rept_opt_class_decl22(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_opt_class_decl22
        follow = FOLLOW_rept_opt_class_decl22

    def _rept_opt_func_body01(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_opt_func_body01
        follow = FOLLOW_rept_opt_func_body01

    def _rept_prog0(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_prog0
        follow = FOLLOW_rept_prog0

    def _rept_prog1(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_prog1
        follow = FOLLOW_rept_prog1

    def _rept_stat_block1(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_stat_block1
        follow = FOLLOW_rept_stat_block1

    def _rept_var_decl2(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_var_decl2
        follow = FOLLOW_rept_var_decl2

    def _rept_variable0(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_variable0
        follow = FOLLOW_rept_variable0

    def _rept_variable2(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rept_variable2
        follow = FOLLOW_rept_variable2

    def _rightrec_arith_expr(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rightrec_arith_expr
        follow = FOLLOW_rightrec_arith_expr

    def _rightrec_term(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_rightrec_term
        follow = FOLLOW_rightrec_term

    def _sign(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_sign
        follow = FOLLOW_sign

    def _START(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_START
        follow = FOLLOW_START

    def _stat_block(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_stat_block
        follow = FOLLOW_stat_block

    def _statement(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_statement
        follow = FOLLOW_statement

    def _term(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_term
        follow = FOLLOW_term

    def _type(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_type
        follow = FOLLOW_type

    def _var_decl(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_var_decl
        follow = FOLLOW_var_decl

    def _variable(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_variable
        follow = FOLLOW_variable

    def _visibility(self, *args):  # LT_AUTO_FUNCTION
        first = FIRST_visibility
        follow = FOLLOW_visibility
