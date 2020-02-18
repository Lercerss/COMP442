from collections import namedtuple
from functools import wraps
from typing import Generator, List, Set, Tuple

from lex import Scanner, Token, TokenType
from .sets import *
from .ast import ASTNode, GroupNodeType, LeafNodeType, ListNodeType

ParserResult = namedtuple("ParserResult", ["success", "ast"])


def skip_errors(func):
    @wraps(func)
    def wrapped(self, *args):
        if self._skip_errors(func.__name__):
            return False
        if func(self, *args):
            return True
        print("Failed to parse rule: " + func.__name__)
        return False

    return wrapped


class Parser:
    def __init__(self, source, prodcution_handler=None, error_handler=None):
        self.scanner: Scanner = Scanner(source)
        self.lookahead: Token = None
        self.current: Token = None
        self.token_iter: Generator[Token, None, None] = None
        self.prodcution_handler = prodcution_handler
        self.error_handler = error_handler
        self.lex_errors = []

    def _on_production(self, lhs: str, *rhs: List[str]):
        if self.prodcution_handler:
            self.prodcution_handler.add(lhs, rhs)

    def _on_panic(self, expected: Set[TokenType]):
        if self.error_handler:
            self.error_handler.panic(expected, self.lookahead)

    def _on_panic_resume(self, skipped: List[Token]):
        if self.error_handler:
            self.error_handler.resume(skipped, self.lookahead)

    def _on_error_token(self, token):
        if self.error_handler:
            self.error_handler.invalid_token(token)

    def _next(self):
        self.current = self.lookahead
        self.lookahead = next(self.token_iter)
        while self._la_in(IGNORED_TOKENS):
            if isinstance(self.lookahead.token_type, E):
                self._on_error_token(self.lookahead)
                self.lex_errors.append(self.lookahead)
            self.lookahead = next(self.token_iter)
        return self.current

    def _panic(self, good_set, recovery_set):
        self._on_panic(good_set)
        skipped = []
        while not self._la_in(recovery_set):
            skipped.append(self._next())

        self._on_panic_resume(skipped)
        return not self._la_in(good_set)

    def _match(self, token_type: TokenType):
        if self.lookahead.token_type == token_type:
            self._next()
            return True

        # TODO Significant error handling here?
        self._panic([token_type], [token_type])
        return self._next().token_type == token_type

    def _la_in(self, set_: Set[TokenType]) -> bool:
        return self.lookahead.token_type in set_

    def _la_eq(self, token_type: TokenType) -> bool:
        return self.lookahead.token_type == token_type

    def _skip_errors(self, rule: str) -> bool:
        """Check if the next token is in FIRST(rule)
        
        If it isn't, enter panic mode"""
        # TODO Check implementation matches expectations
        first_set = eval("FIRST" + rule)
        first_and_follow_set = eval("FF" + rule)
        if EPSILON in first_set:
            first_set = first_and_follow_set

        if self._la_in(first_set):
            return False

        return self._panic(first_set, first_and_follow_set)

    def start(self) -> ParserResult:
        self.token_iter = iter(self.scanner)
        self._next()
        root = ASTNode(GroupNodeType.PROG, self.lookahead)
        try:
            if self._prog([root]) and self._la_eq(G.EOF) and len(self.lex_errors) == 0:
                return ParserResult(True, root)
        except StopIteration:
            pass
        return ParserResult(False, root)

    @skip_errors
    def _add_op(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(O.PLUS):
            if self._match(O.PLUS):
                self._on_production("addOp", "'+'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.MINUS):
            if self._match(O.MINUS):
                self._on_production("addOp", "'-'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.OR):
            if self._match(O.OR):
                self._on_production("addOp", "'or'")
                nodes[0].token = self.current
                return True
        return False

    @skip_errors
    def _a_params(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_expr):
            if self._expr(nodes) and self._rept_a_params1(nodes):
                self._on_production("aParams", "expr", "rept-aParams1")
                # TODO AST
                return True
        elif self._la_in(FOLLOW_a_params):
            self._on_production("aParams", EPSILON)
            # TODO AST
            return True
        return False

    @skip_errors
    def _a_params_tail(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(S.COMMA):
            if self._match(S.COMMA) and self._expr(nodes):
                # TODO AST
                self._on_production("aParamsTail", "','", "expr")
                return True
        return False

    @skip_errors
    def _arith_expr(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_term):
            if self._term(nodes) and self._rightrec_arith_expr(nodes):
                self._on_production("arithExpr", "term", "rightrec-arithExpr")
                return True
        return False

    @skip_errors
    def _array_size(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(S.OPEN_SBR) and self._match(S.OPEN_SBR):
            token = self.lookahead
            if self._la_eq(L.INTEGER_LITERAL):
                if self._match(L.INTEGER_LITERAL) and self._match(S.CLOSE_SBR):
                    self._on_production("arraySize", "'['", "intNum", "']'")
                    nodes[0].token = token
                    return True
            elif self._la_eq(S.CLOSE_SBR):
                if self._match(S.CLOSE_SBR):
                    self._on_production("arraySize", "'['", "']'")
                    # nodes[0] = None  # TODO AST?
                    return True
        return False

    @skip_errors
    def _class_decl(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(K.CLASS):
            if self._match(K.CLASS) and self._match(G.ID):
                id_ = self.current
                if (
                    self._opt_class_decl2(nodes)
                    and self._match(S.OPEN_CBR)
                    and self._rept_class_decl4(nodes)
                    and self._match(S.CLOSE_CBR)
                    and self._match(S.SEMI_COLON)
                ):
                    self._on_production(
                        "classDecl",
                        "'class'",
                        "'id'",
                        "opt-classDecl2",
                        "'{'",
                        "rept-classDecl4",
                        "'}'",
                        "';'",
                    )
                    nodes[0].token = id_  # TODO AST
                    return True

        return False

    @skip_errors
    def _expr(self, nodes):  # LT_AUTO_FUNCTION
        # TODO AST
        if self._la_in(FIRST_arith_expr) and self._arith_expr(nodes):
            if self._la_in(FIRST_rel_op):
                if self._rel_op(nodes) and self._arith_expr(nodes):
                    self._on_production("relExpr", "arithExpr", "relOp", "arithExpr")
                    self._on_production("expr", "relExpr")
                    return True
            elif self._la_in(FOLLOW_arith_expr):
                self._on_production("expr", "arithExpr")
                return True

        return False

    @skip_errors
    def _factor(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(G.ID):
            if self._nested_var_or_call(
                nodes, end_variable=True, end_function_call=True
            ):
                # TODO AST
                self._on_production(
                    "factor",
                    "variable"
                    if nodes[-1].node_type == GroupNodeType.DATA_MEMBER
                    else "functionCall",
                )
                return True
        elif self._la_eq(L.INTEGER_LITERAL):
            if self._match(L.INTEGER_LITERAL):
                self._on_production("factor", "'intNum'")
                return True
        elif self._la_eq(L.FLOAT_LITERAL):
            if self._match(L.FLOAT_LITERAL):
                self._on_production("factor", "'floatNum'")
                return True
        elif self._la_eq(S.OPEN_PAR):
            if (
                self._match(S.OPEN_PAR)
                and self._arith_expr(nodes)
                and self._match(S.CLOSE_PAR)
            ):
                self._on_production("factor", "'('", "arithExpr", "')'")
                return True
        elif self._la_eq(O.NOT):
            if self._match(O.NOT) and self._factor(nodes):
                self._on_production("factor", "'not'", "factor")
                return True
        elif self._la_in(FIRST_sign):
            if self._sign(nodes) and self._factor(nodes):
                self._on_production("factor", "sign", "factor")
                return True

        return False

    @skip_errors
    def _f_params(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_type):
            if (
                self._type(nodes)
                and self._match(G.ID)
                and self._rept_f_params2(nodes)
                and self._rept_f_params3(nodes)
            ):
                self._on_production(
                    "fParams", "type", "'id'", "rept-fParams2", "rept-fParams3"
                )
                return True
        elif self._la_in(FOLLOW_f_params):
            self._on_production("fParams", EPSILON)
            return True
        return False

    @skip_errors
    def _f_params_tail(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(S.COMMA):
            if self._match(S.COMMA) and self._type(nodes) and self._match(G.ID):
                id_ = self.current
                if self._rept_f_params_tail3(nodes):
                    self._on_production(
                        "fParamsTail", "','", "type", "'id'", "rept-fParamsTail3"
                    )
                    nodes[0].token = id_
                    return True

        return False

    @skip_errors
    def _func_body(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_opt_func_body0) or self._la_eq(K.DO):
            if (
                self._opt_func_body0(nodes)
                and self._match(K.DO)
                and self._rept_func_body2(nodes)
                and self._match(K.END)
            ):
                self._on_production(
                    "funcBody", "opt-funcBody0", "'do'", "rept-funcBody2", "'end'"
                )
                return True
        return False

    @skip_errors
    def _func_decl(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(G.ID) and self._match(G.ID):
            id_ = self.current
            if (
                self._la_eq(S.OPEN_PAR)
                and self._match(S.OPEN_PAR)
                and self._f_params(nodes)
                and self._match(S.CLOSE_PAR)
                and self._match(S.COLON)
            ):
                if self._la_eq(K.VOID):
                    if self._match(K.VOID) and self._match(S.SEMI_COLON):
                        self._on_production(
                            "funcDecl",
                            "'id'",
                            "'('",
                            "fParams",
                            "')'",
                            "':'",
                            "'void'",
                            "';'",
                        )
                        # TODO AST
                        return True
                elif self._la_in(FIRST_type):
                    if self._type(nodes) and self._match(S.SEMI_COLON):
                        self._on_production(
                            "funcDecl",
                            "'id'",
                            "'('",
                            "fParams",
                            "')'",
                            "':'",
                            "type",
                            "';'",
                        )
                        # TODO AST
                        return True
        return False

    @skip_errors
    def _func_def(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_func_head):
            if (
                self._func_head(nodes)
                and self._func_body(nodes)
                and self._match(S.SEMI_COLON)
            ):
                self._on_production("funcDef", "funcHead", "funcBody", "';'")
                # TODO AST
                return True
        return False

    @skip_errors
    def _func_head(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(G.ID) and self._match(G.ID):
            if self._la_eq(S.DCOLON):
                if not (self._match(S.DCOLON) and self._match(G.ID)):
                    return False
                self._on_production("opt-funcHead0", "'id'", "'sr'")
            else:
                self._on_production("opt-funcHead0", EPSILON)

            if (
                self._match(S.OPEN_PAR)
                and self._f_params(nodes)
                and self._match(S.CLOSE_PAR)
                and self._match(S.COLON)
            ):
                if self._la_eq(K.VOID):
                    if self._match(K.VOID):
                        self._on_production(
                            "funcHead",
                            "opt-funcHead0",
                            "'id'",
                            "'('",
                            "fParams",
                            "')'",
                            "':'",
                            "'void'",
                        )
                        return True
                elif self._la_in(FIRST_type):
                    if self._type(nodes):
                        self._on_production(
                            "funcHead",
                            "opt-funcHead0",
                            "'id'",
                            "'('",
                            "fParams",
                            "')'",
                            "':'",
                            "type",
                        )
                        return True
        return False

    def _nested_var_or_call(
        self, nodes, end_variable=False, end_function_call=False
    ):  # LT_AUTO_FUNCTION LT_NOT_FROM_GRAM
        if self._skip_errors("_variable"):
            return False

        # TODO AST
        if self._la_eq(G.ID) and self._match(G.ID):
            if self._la_eq(S.OPEN_PAR):
                if (
                    self._match(S.OPEN_PAR)
                    and self._a_params(nodes)
                    and self._match(S.CLOSE_PAR)
                ):
                    if self._la_eq(S.DOT):
                        if self._match(S.DOT):
                            self._on_production(
                                "idnest", "'id'", "'('", "aParams", "')'", "'.'"
                            )
                            if self._nested_var_or_call(
                                nodes, end_variable, end_function_call
                            ):
                                return True
                    elif end_function_call and self._la_in(FOLLOW_function_call):
                        self._on_production(
                            "functionCall",
                            "rept-functionCall0",
                            "'id'",
                            "'('",
                            "aParams",
                            "')'",
                        )
                        nodes[-1].node_type = GroupNodeType.F_CALL
                        return True
            elif (
                self._la_in(FIRST_rept_idnest1)
                or self._la_eq(S.DOT)
                or (self._la_in(FOLLOW_variable) and end_variable)
            ):
                if self._rept_idnest1(nodes):
                    if self._la_eq(S.DOT):
                        if self._match(S.DOT):
                            self._on_production("idnest", "'id'", "rept-idnest1", "'.'")
                            if self._nested_var_or_call(
                                nodes, end_variable, end_function_call
                            ):
                                return True
                    elif end_variable and self._la_in(FOLLOW_variable):
                        self._on_production(
                            "variable", "rept-variable0", "'id'", "rept-variable2"
                        )
                        nodes[-1].node_type = GroupNodeType.DATA_MEMBER
                        return True
        return False

    @skip_errors
    def _indice(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(S.OPEN_SBR) and self._match(S.OPEN_SBR):
            if self._arith_expr(nodes) and self._match(S.CLOSE_SBR):
                self._on_production("indice", "'['", "arithExpr", "']'")
                return True
        return False

    @skip_errors
    def _member_decl(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_func_decl):
            if self._func_decl(nodes):
                self._on_production("memberDecl", "funcDecl")
                return True
        elif self._la_in(FIRST_var_decl):
            if self._var_decl(nodes):
                self._on_production("memberDecl", "varDecl")
                return True
        return False

    @skip_errors
    def _mult_op(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(O.MULT):
            if self._match(O.MULT):
                self._on_production("multOp", "'*'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.DIV):
            if self._match(O.DIV):
                self._on_production("multOp", "'/'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.AND):
            if self._match(O.AND):
                self._on_production("multOp", "'and'")
                nodes[0].token = self.current
                return True
        return False

    @skip_errors
    def _opt_class_decl2(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(K.INHERITS):
            if (
                self._match(K.INHERITS)
                and self._match(G.ID)
                and self._rept_opt_class_decl22(nodes)
            ):
                # TODO AST
                self._on_production(
                    "opt-classDecl2", "'inherits'", "'id'", "rept-opt-classDecl22"
                )
                return True
        elif self._la_in(FOLLOW_opt_class_decl2):
            self._on_production("opt-classDecl2", EPSILON)
            return True
        return False

    @skip_errors
    def _opt_func_body0(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(K.LOCAL):
            if self._match(K.LOCAL) and self._rept_opt_func_body01(nodes):
                self._on_production("opt-funcBody0", "'local'", "rept-opt-funcBody01")
                return True
        elif self._la_in(FOLLOW_opt_func_body0):
            self._on_production("opt-funcBody0", EPSILON)
            return True
        return False

    @skip_errors
    def _prog(self, nodes):  # LT_AUTO_FUNCTION
        if (
            self._la_in(FIRST_rept_prog0)
            or self._la_in(FIRST_rept_prog1)
            or self._la_eq(K.MAIN)
        ):
            if (
                self._rept_prog0(nodes)
                and self._rept_prog1(nodes)
                and self._match(K.MAIN)
                and self._func_body(nodes)
            ):
                # TODO AST
                self._on_production(
                    "prog", "rept-prog0", "rept-prog1", "'main'", "funcBody"
                )
                return True
        return False

    @skip_errors
    def _rel_expr(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_arith_expr):
            if (
                self._arith_expr(nodes)
                and self._rel_op(nodes)
                and self._arith_expr(nodes)
            ):
                # TODO AST
                self._on_production("relExpr", "arithExpr", "relOp", "arithExpr")
                return True
        return False

    @skip_errors
    def _rel_op(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(O.EQ):
            if self._match(O.EQ):
                self._on_production("relOp", "'eq'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.NEQ):
            if self._match(O.NEQ):
                self._on_production("relOp", "'neq'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.LT):
            if self._match(O.LT):
                self._on_production("relOp", "'lt'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.GT):
            if self._match(O.GT):
                self._on_production("relOp", "'gt'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.LTE):
            if self._match(O.LTE):
                self._on_production("relOp", "'leq'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.GTE):
            if self._match(O.GTE):
                self._on_production("relOp", "'leq'")
                nodes[0].token = self.current
                return True
        return False

    @skip_errors
    def _rept_a_params1(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_a_params_tail):
            if self._a_params_tail(nodes) and self._rept_a_params1(nodes):
                self._on_production("rept-aParams1", "aParamsTails", "rept-aParams1")
                return True
        elif self._la_in(FOLLOW_rept_a_params1):
            self._on_production("rept-aParams1", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_class_decl4(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_visibility):
            if (
                self._visibility(nodes)
                and self._member_decl(nodes)
                and self._rept_class_decl4(nodes)
            ):
                # TODO AST
                self._on_production(
                    "rept-classDecl4", "visibility", "memberDecl", "rept-classDecl4"
                )
                return True
        elif self._la_in(FOLLOW_rept_class_decl4):
            self._on_production("rept-classDecl4", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_f_params2(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_array_size):
            if self._array_size(nodes) and self._rept_f_params2(nodes):
                self._on_production("rept-fParams2", "arraySize", "rept-fParams2")
                return True
        elif self._la_in(FOLLOW_rept_f_params2):
            self._on_production("rept-fParams2", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_f_params3(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_f_params_tail):
            if self._f_params_tail(nodes) and self._rept_f_params3(nodes):
                # TODO AST
                self._on_production("rept-fParams3", "fParamsTail", "rept-fParams3")
                return True
        elif self._la_in(FOLLOW_rept_f_params3):
            self._on_production("rept-fParams3", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_f_params_tail3(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_array_size):
            if self._array_size(nodes) and self._rept_f_params_tail3(nodes):
                # TODO AST
                self._on_production(
                    "rept-fParamsTail3", "arraySize", "rept-fParamsTail3"
                )
                return True
        elif self._la_in(FOLLOW_rept_f_params_tail3):
            self._on_production("rept-fParamsTail3", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_func_body2(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_statement):
            if self._statement(nodes) and self._rept_func_body2(nodes):
                # TODO AST
                self._on_production("rept-funcBody2", "statement", "rept-funcBody2")
                return True
        elif self._la_in(FOLLOW_rept_func_body2):
            self._on_production("rept-funcBody2", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_idnest1(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_indice):
            if self._indice(nodes) and self._rept_idnest1(nodes):
                # TODO AST
                self._on_production("rept-idnest1", "indice", "rept-idnest1")
                return True
        elif self._la_in(FOLLOW_rept_idnest1):
            self._on_production("rept-idnest1", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_opt_class_decl22(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(S.COMMA):
            if (
                self._match(S.COMMA)
                and self._match(G.ID)
                and self._rept_opt_class_decl22(nodes)
            ):
                # TODO AST
                self._on_production(
                    "rept-opt-classDecl22", "','", "'id'", "rept-opt-classDecl22"
                )
                return True
        elif self._la_in(FOLLOW_rept_opt_class_decl22):
            self._on_production("rept-opt-classDecl22", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_opt_func_body01(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_var_decl):
            if self._var_decl(nodes) and self._rept_opt_func_body01(nodes):
                # TODO AST
                self._on_production(
                    "rept-opt-funcBody01", "varDecl", "rept-opt-funcBody01"
                )
                return True
        elif self._la_in(FOLLOW_rept_opt_func_body01):
            self._on_production("rept-opt-funcBody01", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_prog0(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_class_decl):
            if self._class_decl(nodes) and self._rept_prog0(nodes):
                # TODO AST
                self._on_production("rept-prog0", "classDecl", "rept-prog0")
                return True
        elif self._la_in(FOLLOW_rept_prog0):
            self._on_production("rept-prog0", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_prog1(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_func_def):
            if self._func_def(nodes) and self._rept_prog1(nodes):
                # TODO AST
                self._on_production("rept-prog1", "funcDef", "rept-prog1")
                return True
        elif self._la_in(FOLLOW_rept_prog1):
            self._on_production("rept-prog1", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_stat_block1(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_statement):
            if self._statement(nodes) and self._rept_stat_block1(nodes):
                # TODO AST
                self._on_production("rept-statBlock1", "statement", "rept-statBlock1")
                return True
        elif self._la_in(FOLLOW_rept_stat_block1):
            self._on_production("rept-statBlock1", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_var_decl2(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_array_size):
            if self._array_size(nodes) and self._rept_var_decl2(nodes):
                # TODO AST
                self._on_production("rept-varDecl2", "arraySize", "rept-varDecl2")
                return True
        elif self._la_in(FOLLOW_rept_var_decl2):
            self._on_production("rept-varDecl2", EPSILON)
            return True
        return False

    @skip_errors
    def _rightrec_arith_expr(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_add_op):
            if (
                self._add_op(nodes)
                and self._term(nodes)
                and self._rightrec_arith_expr(nodes)
            ):
                # TODO AST
                self._on_production(
                    "rightrec-arithExpr", "addOp", "term", "rightrec-arithExpr"
                )
                return True
        elif self._la_in(FOLLOW_rightrec_arith_expr):
            self._on_production("rightrec-arithExpr", EPSILON)
            return True
        return False

    @skip_errors
    def _rightrec_term(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_mult_op):
            if (
                self._mult_op(nodes)
                and self._factor(nodes)
                and self._rightrec_term(nodes)
            ):
                # TODO AST
                self._on_production(
                    "rightrec-term", "multOp", "factor", "rightrec-term"
                )
                return True
        elif self._la_in(FOLLOW_rightrec_term):
            self._on_production("rightrec-term", EPSILON)
            return True
        return False

    @skip_errors
    def _sign(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(O.PLUS):
            if self._match(O.PLUS):
                self._on_production("sign", "'+'")
                nodes[0].token = self.current
                return True
        elif self._la_eq(O.MINUS):
            if self._match(O.MINUS):
                self._on_production("sign", "'-'")
                nodes[0].token = self.current
                return True
        return False

    @skip_errors
    def _stat_block(self, nodes):  # LT_AUTO_FUNCTION
        # TODO AST
        if self._la_in(FIRST_statement):
            if self._statement(nodes):
                self._on_production("statBlock", "statement")
                return True
        elif self._la_eq(K.DO):
            if (
                self._match(K.DO)
                and self._rept_stat_block1(nodes)
                and self._match(K.END)
            ):
                self._on_production("statBlock", "'do'", "rept-statBlock1", "'end'")
                return True
        elif self._la_in(FOLLOW_stat_block):
            self._on_production("statBlock", EPSILON)
            return True
        return False

    @skip_errors
    def _statement(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_variable):
            if self._nested_var_or_call(
                nodes, end_variable=True, end_function_call=True
            ):
                last_node = nodes[-1].node_type
                if self._la_eq(S.ASSIGN) and last_node == GroupNodeType.DATA_MEMBER:
                    if self._match(S.ASSIGN) and self._expr(nodes):
                        self._on_production("assignStat", "variable", "'='", "expr")
                        if self._match(S.SEMI_COLON):
                            self._on_production("statement", "assignStat", "';'")
                            return True
                # TODO AST
                elif self._la_eq(S.SEMI_COLON) and last_node == GroupNodeType.F_CALL:
                    if self._match(S.SEMI_COLON):
                        self._on_production("statement", "functionCall", "';'")
                        return True
        elif self._la_eq(K.IF):
            if (
                self._match(K.IF)
                and self._match(S.OPEN_PAR)
                and self._rel_expr(nodes)
                and self._match(S.CLOSE_PAR)
                and self._match(K.THEN)
                and self._stat_block(nodes)
                and self._match(K.ELSE)
                and self._stat_block(nodes)
                and self._match(S.SEMI_COLON)
            ):
                # TODO AST
                self._on_production(
                    "statement",
                    "'if'",
                    "'('",
                    "relExpr",
                    "')'",
                    "'then'",
                    "statBlock",
                    "'else'",
                    "statBlock",
                    "';'",
                )
                return True
        elif self._la_eq(K.WHILE):
            if (
                self._match(K.WHILE)
                and self._match(S.OPEN_PAR)
                and self._rel_expr(nodes)
                and self._match(S.CLOSE_PAR)
                and self._stat_block(nodes)
                and self._match(S.SEMI_COLON)
            ):
                # TODO AST
                self._on_production(
                    "statement", "'while'", "'('", "relExpr", "')'", "statBlock", "';'",
                )
                return True
        elif self._la_eq(K.READ):
            if (
                self._match(K.READ)
                and self._match(S.OPEN_PAR)
                and self._nested_var_or_call(nodes, end_variable=True)
                and self._match(S.CLOSE_PAR)
                and self._match(S.SEMI_COLON)
            ):
                # TODO AST
                self._on_production(
                    "statement", "'read'", "'('", "variable", "')'", "';'",
                )
                return True
        elif self._la_eq(K.WRITE):
            if (
                self._match(K.WRITE)
                and self._match(S.OPEN_PAR)
                and self._expr(nodes)
                and self._match(S.CLOSE_PAR)
                and self._match(S.SEMI_COLON)
            ):
                # TODO AST
                self._on_production(
                    "statement", "'write'", "'('", "expr", "')'", "';'",
                )
                return True
        elif self._la_eq(K.RETURN):
            if (
                self._match(K.RETURN)
                and self._match(S.OPEN_PAR)
                and self._expr(nodes)
                and self._match(S.CLOSE_PAR)
                and self._match(S.SEMI_COLON)
            ):
                # TODO AST
                self._on_production(
                    "statement", "'return'", "'('", "expr", "')'", "';'",
                )
                return True
        return False

    @skip_errors
    def _term(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_factor):
            if self._factor(nodes) and self._rightrec_term(nodes):
                # TODO AST
                self._on_production("term", "factor", "rightrec-term")
                return True
        return False

    @skip_errors
    def _type(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(K.INTEGER):
            if self._match(K.INTEGER):
                nodes[0].token = self.current
                self._on_production("type", "'integer'")
                return True
        elif self._la_eq(K.FLOAT):
            if self._match(K.FLOAT):
                nodes[0].token = self.current
                self._on_production("type", "'float'")
                return True
        elif self._la_eq(G.ID):
            if self._match(G.ID):
                nodes[0].token = self.current
                self._on_production("type", "'id'")
                return True
        return False

    @skip_errors
    def _var_decl(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_type):
            if (
                self._type(nodes)
                and self._match(G.ID)
                and self._rept_var_decl2(nodes)
                and self._match(S.SEMI_COLON)
            ):
                self._on_production("varDecl", "type", "'id'", "rept-varDecl2", "';'")
                return True
        return False

    @skip_errors
    def _visibility(self, nodes):  # LT_AUTO_FUNCTION
        if self._la_eq(K.PUBLIC):
            if self._match(K.PUBLIC):
                nodes[0].token = self.current
                self._on_production("visibility", "'public'")
                return True
        elif self._la_eq(K.PRIVATE):
            if self._match(K.PRIVATE):
                nodes[0].token = self.current
                self._on_production("visibility", "'private'")
                return True
        return False
