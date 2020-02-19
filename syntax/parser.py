from collections import namedtuple
from functools import wraps
from typing import Generator, List, Set, Tuple

from lex import Scanner, Token, TokenType
from .sets import *
from .ast import ASTNode, GroupNodeType, LeafNodeType, ListNodeType

ParserResult = namedtuple("ParserResult", ["success", "ast"])


# TODO Remove temp comments


def skip_errors(func):
    @wraps(func)
    def wrapped(self, *args):
        if self._skip_errors(eval("FIRST" + func.__name__), eval("FF" + func.__name__)):
            return True
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
        if self._next().token_type == token_type:
            return True

        self._on_panic([token_type])
        return False

    def _la_in(self, set_: Set[TokenType]) -> bool:
        return self.lookahead.token_type in set_

    def _la_eq(self, token_type: TokenType) -> bool:
        return self.lookahead.token_type == token_type

    def _skip_errors(
        self, first_set: Set[TokenType], first_and_follow_set: Set[TokenType]
    ) -> bool:
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
            if self._prog(root) and self._la_eq(G.EOF) and len(self.lex_errors) == 0:
                return ParserResult(True, root)
        except StopIteration:
            pass
        return ParserResult(False, root)

    @skip_errors
    def _add_op(self, add_op: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(O.PLUS):
            if self._match(O.PLUS):
                self._on_production("addOp", "'+'")
                add_op.token = self.current
                return True
        elif self._la_eq(O.MINUS):
            if self._match(O.MINUS):
                self._on_production("addOp", "'-'")
                add_op.token = self.current
                return True
        elif self._la_eq(O.OR):
            if self._match(O.OR):
                self._on_production("addOp", "'or'")
                add_op.token = self.current
                return True
        return False

    @skip_errors
    def _a_params(self, args: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_expr):
            if self._expr(args) and self._rept_a_params1(args):
                self._on_production("aParams", "expr", "rept-aParams1")
                return True
        elif self._la_in(FOLLOW_a_params):
            self._on_production("aParams", EPSILON)
            return True
        return False

    @skip_errors
    def _a_params_tail(self, args: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(S.COMMA):
            if self._match(S.COMMA) and self._expr(args):
                self._on_production("aParamsTail", "','", "expr")
                return True
        return False

    @skip_errors
    def _arith_expr(self, add_expr: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_term):
            if self._term(add_expr) and self._rightrec_arith_expr(add_expr):
                if not add_expr.token:
                    add_expr.absorb()
                self._on_production("arithExpr", "term", "rightrec-arithExpr")
                return True
        return False

    @skip_errors
    def _array_size(self, dims: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(S.OPEN_SBR) and self._match(S.OPEN_SBR):
            if self._skip_errors(FIRST_nested_array_size, FF_nested_array_size):
                return True

            if self._la_eq(L.INTEGER_LITERAL):
                dims.make_child(LeafNodeType.LITERAL, self.lookahead)
                if self._match(L.INTEGER_LITERAL) and self._match(S.CLOSE_SBR):
                    self._on_production("arraySize", "'['", "intNum", "']'")
                    return True
            elif self._la_eq(S.CLOSE_SBR):
                dims.make_child(LeafNodeType.EPSILON)
                if self._match(S.CLOSE_SBR):
                    self._on_production("arraySize", "'['", "']'")
                    return True
        return False

    @skip_errors
    def _class_decl(self, class_decl: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(K.CLASS):
            if self._match(K.CLASS) and self._match(G.ID):
                class_decl.make_child(LeafNodeType.ID, self.current)
                inherits = class_decl.make_child(ListNodeType.INHER_LIST)
                members = class_decl.make_child(ListNodeType.MEMBER_LIST)
                if (
                    self._opt_class_decl2(inherits)
                    and self._match(S.OPEN_CBR)
                    and self._rept_class_decl4(members)
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
                    return True

        return False

    @skip_errors
    def _expr(self, container: ASTNode):  # LT_AUTO_FUNCTION
        left = ASTNode(GroupNodeType.ADD_EXPR)
        if self._la_in(FIRST_arith_expr) and self._arith_expr(left):
            if self._la_in(FIRST_rel_op):
                rel_expr = container.make_child(GroupNodeType.REL_EXPR)
                rel_expr.adopt(left)
                right = rel_expr.make_child(GroupNodeType.ADD_EXPR)
                if self._rel_op(rel_expr) and self._arith_expr(right):
                    self._on_production("relExpr", "arithExpr", "relOp", "arithExpr")
                    self._on_production("expr", "relExpr")
                    return True
            elif self._la_in(FOLLOW_arith_expr):
                container.adopt(left)
                self._on_production("expr", "arithExpr")
                return True

        return False

    @skip_errors
    def _factor(self, container: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(G.ID):
            var = container.make_child(ListNodeType.VAR)
            if self._nested_var_or_call(var, end_variable=True, end_function_call=True):
                if var.children[-1].node_type == GroupNodeType.DATA_MEMBER:
                    self._on_production("factor", "variable")
                else:
                    self._on_production("factor", "functionCall")

                return True
        elif self._la_eq(L.INTEGER_LITERAL):
            if self._match(L.INTEGER_LITERAL):
                container.make_child(LeafNodeType.LITERAL, self.current)
                self._on_production("factor", "'intNum'")
                return True
        elif self._la_eq(L.FLOAT_LITERAL):
            if self._match(L.FLOAT_LITERAL):
                container.make_child(LeafNodeType.LITERAL, self.current)
                self._on_production("factor", "'floatNum'")
                return True
        elif self._la_eq(S.OPEN_PAR):
            add_expr = container.make_child(GroupNodeType.ADD_EXPR)
            if (
                self._match(S.OPEN_PAR)
                and self._arith_expr(add_expr)
                and self._match(S.CLOSE_PAR)
            ):
                self._on_production("factor", "'('", "arithExpr", "')'")
                return True
        elif self._la_eq(O.NOT):
            not_ = container.make_child(GroupNodeType.NOT)
            if self._match(O.NOT) and self._factor(not_):
                self._on_production("factor", "'not'", "factor")
                return True
        elif self._la_in(FIRST_sign):
            sign = container.make_child(GroupNodeType.SIGN)
            if self._sign(sign) and self._factor(sign):
                self._on_production("factor", "sign", "factor")
                return True

        return False

    @skip_errors
    def _f_params(self, params: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_type):
            param = params.make_child(GroupNodeType.FUNC_PARAM)
            type_ = param.make_child(LeafNodeType.TYPE)
            if self._type(type_) and self._match(G.ID):
                param.make_child(LeafNodeType.ID, self.current)
                dims = param.make_child(ListNodeType.DIM_LIST)
                if self._rept_f_params2(dims) and self._rept_f_params3(params):
                    self._on_production(
                        "fParams", "type", "'id'", "rept-fParams2", "rept-fParams3"
                    )
                    return True
        elif self._la_in(FOLLOW_f_params):
            self._on_production("fParams", EPSILON)
            return True
        return False

    @skip_errors
    def _f_params_tail(self, params: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(S.COMMA):
            param = params.make_child(GroupNodeType.FUNC_PARAM)
            type_ = param.make_child(LeafNodeType.TYPE)
            if self._match(S.COMMA) and self._type(type_) and self._match(G.ID):
                param.make_child(LeafNodeType.ID, self.current)
                if self._rept_f_params_tail3(param):
                    self._on_production(
                        "fParamsTail", "','", "type", "'id'", "rept-fParamsTail3"
                    )
                    return True

        return False

    @skip_errors
    def _func_body(self, func_def: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_opt_func_body0) or self._la_eq(K.DO):
            locals_ = func_def.make_child(ListNodeType.LOCAL_LIST)
            statements = func_def.make_child(ListNodeType.STAT_BLOCK)
            if (
                self._opt_func_body0(locals_)
                and self._match(K.DO)
                and self._rept_func_body2(statements)
                and self._match(K.END)
            ):
                self._on_production(
                    "funcBody", "opt-funcBody0", "'do'", "rept-funcBody2", "'end'"
                )
                return True
        return False

    @skip_errors
    def _func_decl(self, func_decl):  # LT_AUTO_FUNCTION
        if self._la_eq(G.ID) and self._match(G.ID):
            func_decl.make_child(LeafNodeType.ID, self.current)
            params = func_decl.make_child(ListNodeType.PARAM_LIST)
            if (
                self._la_eq(S.OPEN_PAR)
                and self._match(S.OPEN_PAR)
                and self._f_params(params)
                and self._match(S.CLOSE_PAR)
                and self._match(S.COLON)
            ):
                if self._la_eq(K.VOID):
                    func_decl.make_child(LeafNodeType.TYPE, self.lookahead)
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
                        return True
                elif self._la_in(FIRST_type):
                    type_ = func_decl.make_child(LeafNodeType.TYPE)
                    if self._type(type_) and self._match(S.SEMI_COLON):
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
                        return True
        return False

    @skip_errors
    def _func_def(self, func_def: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_func_head):
            if (
                self._func_head(func_def)
                and self._func_body(func_def)
                and self._match(S.SEMI_COLON)
            ):
                self._on_production("funcDef", "funcHead", "funcBody", "';'")
                return True
        return False

    @skip_errors
    def _func_head(self, func_def: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(G.ID) and self._match(G.ID):
            scope_spec = func_def.make_child(LeafNodeType.SCOPE_SPEC, self.current)
            if self._la_eq(S.DCOLON):
                if not (self._match(S.DCOLON) and self._match(G.ID)):
                    return False
                self._on_production("opt-funcHead0", "'id'", "'sr'")
            else:
                self._on_production("opt-funcHead0", EPSILON)
                scope_spec.token = None

            func_def.make_child(LeafNodeType.ID, self.current)
            params = func_def.make_child(ListNodeType.PARAM_LIST)
            if (
                self._match(S.OPEN_PAR)
                and self._f_params(params)
                and self._match(S.CLOSE_PAR)
                and self._match(S.COLON)
            ):
                if self._la_eq(K.VOID):
                    func_def.make_child(LeafNodeType.TYPE, self.lookahead)
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
                    type_ = func_def.make_child(LeafNodeType.TYPE)
                    if self._type(type_):
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
        self, var: ASTNode, end_variable=False, end_function_call=False
    ):  # LT_AUTO_FUNCTION LT_NOT_FROM_GRAM
        if self._skip_errors(FIRST_variable, FF_variable):
            return True

        if self._la_eq(G.ID) and self._match(G.ID):
            if self._la_eq(S.OPEN_PAR):
                call = var.make_child(GroupNodeType.F_CALL)
                call.make_child(LeafNodeType.ID, self.current)
                args = call.make_child(ListNodeType.ARG_LIST)
                if (
                    self._match(S.OPEN_PAR)
                    and self._a_params(args)
                    and self._match(S.CLOSE_PAR)
                ):
                    if self._la_eq(S.DOT):
                        if self._match(S.DOT):
                            self._on_production(
                                "idnest", "'id'", "'('", "aParams", "')'", "'.'"
                            )
                            if self._nested_var_or_call(
                                var, end_variable, end_function_call
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
                        return True
            elif (
                self._la_in(FIRST_rept_idnest1)
                or self._la_eq(S.DOT)
                or (self._la_in(FOLLOW_variable) and end_variable)
            ):
                data_member = var.make_child(GroupNodeType.DATA_MEMBER)
                data_member.make_child(LeafNodeType.ID, self.current)
                dims = data_member.make_child(ListNodeType.DIM_LIST)
                if self._rept_idnest1(dims):
                    if self._la_eq(S.DOT):
                        if self._match(S.DOT):
                            self._on_production("idnest", "'id'", "rept-idnest1", "'.'")
                            if self._nested_var_or_call(
                                var, end_variable, end_function_call
                            ):
                                return True
                    elif end_variable and self._la_in(FOLLOW_variable):
                        self._on_production(
                            "variable", "rept-variable0", "'id'", "rept-variable2"
                        )
                        return True
        return False

    @skip_errors
    def _indice(self, add_expr: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(S.OPEN_SBR) and self._match(S.OPEN_SBR):
            if self._arith_expr(add_expr) and self._match(S.CLOSE_SBR):
                self._on_production("indice", "'['", "arithExpr", "']'")
                return True
        return False

    @skip_errors
    def _member_decl(self, member: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_func_decl):
            func_decl = member.make_child(GroupNodeType.FUNC_DECL)
            if self._func_decl(func_decl):
                self._on_production("memberDecl", "funcDecl")
                return True
        elif self._la_in(FIRST_var_decl):
            var_decl = member.make_child(GroupNodeType.VAR_DECL)
            if self._var_decl(var_decl):
                self._on_production("memberDecl", "varDecl")
                return True
        return False

    @skip_errors
    def _mult_op(self, mult_expr: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(O.MULT):
            if self._match(O.MULT):
                self._on_production("multOp", "'*'")
                mult_expr.token = self.current
                return True
        elif self._la_eq(O.DIV):
            if self._match(O.DIV):
                self._on_production("multOp", "'/'")
                mult_expr.token = self.current
                return True
        elif self._la_eq(O.AND):
            if self._match(O.AND):
                self._on_production("multOp", "'and'")
                mult_expr.token = self.current
                return True
        return False

    @skip_errors
    def _opt_class_decl2(self, inherits):  # LT_AUTO_FUNCTION
        if self._la_eq(K.INHERITS):
            if self._match(K.INHERITS) and self._match(G.ID):
                inherits.make_child(LeafNodeType.ID, self.current)
                if self._rept_opt_class_decl22(inherits):
                    self._on_production(
                        "opt-classDecl2", "'inherits'", "'id'", "rept-opt-classDecl22"
                    )
                    return True
        elif self._la_in(FOLLOW_opt_class_decl2):
            self._on_production("opt-classDecl2", EPSILON)
            return True
        return False

    @skip_errors
    def _opt_func_body0(self, locals_: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(K.LOCAL):
            if self._match(K.LOCAL) and self._rept_opt_func_body01(locals_):
                self._on_production("opt-funcBody0", "'local'", "rept-opt-funcBody01")
                return True
        elif self._la_in(FOLLOW_opt_func_body0):
            self._on_production("opt-funcBody0", EPSILON)
            return True
        return False

    @skip_errors
    def _prog(self, root: ASTNode):  # LT_AUTO_FUNCTION
        classes = root.make_child(ListNodeType.CLASS_LIST)
        funcs = root.make_child(ListNodeType.FUNC_LIST)
        stat_block = root.make_child(ListNodeType.STAT_BLOCK)
        if (
            self._la_in(FIRST_rept_prog0)
            or self._la_in(FIRST_rept_prog1)
            or self._la_eq(K.MAIN)
        ):
            if (
                self._rept_prog0(classes)
                and self._rept_prog1(funcs)
                and self._match(K.MAIN)
                and self._func_body(stat_block)
            ):
                self._on_production(
                    "prog", "rept-prog0", "rept-prog1", "'main'", "funcBody"
                )
                return True
        return False

    @skip_errors
    def _rel_expr(self, rel_expr: ASTNode):  # LT_AUTO_FUNCTION
        left = rel_expr.make_child(GroupNodeType.ADD_EXPR)
        right = rel_expr.make_child(GroupNodeType.ADD_EXPR)
        if self._la_in(FIRST_arith_expr):
            if (
                self._arith_expr(left)
                and self._rel_op(rel_expr)
                and self._arith_expr(right)
            ):
                self._on_production("relExpr", "arithExpr", "relOp", "arithExpr")
                return True
        return False

    @skip_errors
    def _rel_op(self, rel_expr: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(O.EQ):
            if self._match(O.EQ):
                self._on_production("relOp", "'eq'")
                rel_expr.token = self.current
                return True
        elif self._la_eq(O.NEQ):
            if self._match(O.NEQ):
                self._on_production("relOp", "'neq'")
                rel_expr.token = self.current
                return True
        elif self._la_eq(O.LT):
            if self._match(O.LT):
                self._on_production("relOp", "'lt'")
                rel_expr.token = self.current
                return True
        elif self._la_eq(O.GT):
            if self._match(O.GT):
                self._on_production("relOp", "'gt'")
                rel_expr.token = self.current
                return True
        elif self._la_eq(O.LTE):
            if self._match(O.LTE):
                self._on_production("relOp", "'leq'")
                rel_expr.token = self.current
                return True
        elif self._la_eq(O.GTE):
            if self._match(O.GTE):
                self._on_production("relOp", "'leq'")
                rel_expr.token = self.current
                return True
        return False

    @skip_errors
    def _rept_a_params1(self, args: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_a_params_tail):
            if self._a_params_tail(args) and self._rept_a_params1(args):
                self._on_production("rept-aParams1", "aParamsTails", "rept-aParams1")
                return True
        elif self._la_in(FOLLOW_rept_a_params1):
            self._on_production("rept-aParams1", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_class_decl4(self, members: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_visibility):
            member = members.make_child(GroupNodeType.MEMBER_DECL)
            visibility = member.make_child(LeafNodeType.VISIBILITY)
            if (
                self._visibility(visibility)
                and self._member_decl(member)
                and self._rept_class_decl4(members)
            ):
                self._on_production(
                    "rept-classDecl4", "visibility", "memberDecl", "rept-classDecl4"
                )
                return True
        elif self._la_in(FOLLOW_rept_class_decl4):
            self._on_production("rept-classDecl4", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_f_params2(self, dims: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_array_size):
            if self._array_size(dims) and self._rept_f_params2(dims):
                self._on_production("rept-fParams2", "arraySize", "rept-fParams2")
                return True
        elif self._la_in(FOLLOW_rept_f_params2):
            self._on_production("rept-fParams2", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_f_params3(self, params):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_f_params_tail):
            if self._f_params_tail(params) and self._rept_f_params3(params):
                self._on_production("rept-fParams3", "fParamsTail", "rept-fParams3")
                return True
        elif self._la_in(FOLLOW_rept_f_params3):
            self._on_production("rept-fParams3", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_f_params_tail3(self, dims):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_array_size):
            if self._array_size(dims) and self._rept_f_params_tail3(dims):
                self._on_production(
                    "rept-fParamsTail3", "arraySize", "rept-fParamsTail3"
                )
                return True
        elif self._la_in(FOLLOW_rept_f_params_tail3):
            self._on_production("rept-fParamsTail3", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_func_body2(self, statements: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_statement):
            if self._statement(statements) and self._rept_func_body2(statements):
                self._on_production("rept-funcBody2", "statement", "rept-funcBody2")
                return True
        elif self._la_in(FOLLOW_rept_func_body2):
            self._on_production("rept-funcBody2", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_idnest1(self, dims: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_indice):
            add_expr = dims.make_child(GroupNodeType.ADD_EXPR)
            if self._indice(add_expr) and self._rept_idnest1(dims):
                self._on_production("rept-idnest1", "indice", "rept-idnest1")
                return True
        elif self._la_in(FOLLOW_rept_idnest1):
            self._on_production("rept-idnest1", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_opt_class_decl22(self, inherits):  # LT_AUTO_FUNCTION
        if self._la_eq(S.COMMA):
            if self._match(S.COMMA) and self._match(G.ID):
                inherits.make_child(LeafNodeType.ID, self.current)
                if self._rept_opt_class_decl22(inherits):
                    self._on_production(
                        "rept-opt-classDecl22", "','", "'id'", "rept-opt-classDecl22"
                    )
                    return True
        elif self._la_in(FOLLOW_rept_opt_class_decl22):
            self._on_production("rept-opt-classDecl22", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_opt_func_body01(self, locals_: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_var_decl):
            var_decl = locals_.make_child(GroupNodeType.VAR_DECL)
            if self._var_decl(var_decl) and self._rept_opt_func_body01(locals_):
                self._on_production(
                    "rept-opt-funcBody01", "varDecl", "rept-opt-funcBody01"
                )
                return True
        elif self._la_in(FOLLOW_rept_opt_func_body01):
            self._on_production("rept-opt-funcBody01", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_prog0(self, classes: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_class_decl):
            class_decl = classes.make_child(GroupNodeType.CLASS_DECL)
            if self._class_decl(class_decl) and self._rept_prog0(classes):
                self._on_production("rept-prog0", "classDecl", "rept-prog0")
                return True
        elif self._la_in(FOLLOW_rept_prog0):
            self._on_production("rept-prog0", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_prog1(self, functions: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_func_def):
            func_def = functions.make_child(GroupNodeType.FUNC_DEF)
            if self._func_def(func_def) and self._rept_prog1(functions):
                self._on_production("rept-prog1", "funcDef", "rept-prog1")
                return True
        elif self._la_in(FOLLOW_rept_prog1):
            self._on_production("rept-prog1", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_stat_block1(self, stat_block: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_statement):
            if self._statement(stat_block) and self._rept_stat_block1(stat_block):
                self._on_production("rept-statBlock1", "statement", "rept-statBlock1")
                return True
        elif self._la_in(FOLLOW_rept_stat_block1):
            self._on_production("rept-statBlock1", EPSILON)
            return True
        return False

    @skip_errors
    def _rept_var_decl2(self, dims: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_array_size):
            if self._array_size(dims) and self._rept_var_decl2(dims):
                self._on_production("rept-varDecl2", "arraySize", "rept-varDecl2")
                return True
        elif self._la_in(FOLLOW_rept_var_decl2):
            self._on_production("rept-varDecl2", EPSILON)
            return True
        return False

    @skip_errors
    def _rightrec_arith_expr(self, add_expr: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_add_op):
            right = ASTNode(GroupNodeType.ADD_EXPR)
            if (
                self._add_op(add_expr)
                and self._term(add_expr)
                and self._rightrec_arith_expr(right)
            ):
                if right.token:
                    right.swap(add_expr)
                self._on_production(
                    "rightrec-arithExpr", "addOp", "term", "rightrec-arithExpr"
                )
                return True
        elif self._la_in(FOLLOW_rightrec_arith_expr):
            self._on_production("rightrec-arithExpr", EPSILON)
            return True
        return False

    @skip_errors
    def _rightrec_term(self, mult_expr: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_mult_op):
            right = ASTNode(GroupNodeType.MULT_EXPR)
            if (
                self._mult_op(mult_expr)
                and self._factor(mult_expr)
                and self._rightrec_term(right)
            ):
                if right.token:
                    right.swap(mult_expr)
                self._on_production(
                    "rightrec-term", "multOp", "factor", "rightrec-term"
                )
                return True
        elif self._la_in(FOLLOW_rightrec_term):
            self._on_production("rightrec-term", EPSILON)
            return True
        return False

    @skip_errors
    def _sign(self, sign: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(O.PLUS):
            if self._match(O.PLUS):
                self._on_production("sign", "'+'")
                sign.token = self.current
                return True
        elif self._la_eq(O.MINUS):
            if self._match(O.MINUS):
                self._on_production("sign", "'-'")
                sign.token = self.current
                return True
        return False

    @skip_errors
    def _stat_block(self, stat_block: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_statement):
            if self._statement(stat_block):
                self._on_production("statBlock", "statement")
                return True
        elif self._la_eq(K.DO):
            if (
                self._match(K.DO)
                and self._rept_stat_block1(stat_block)
                and self._match(K.END)
            ):
                self._on_production("statBlock", "'do'", "rept-statBlock1", "'end'")
                return True
        elif self._la_in(FOLLOW_stat_block):
            self._on_production("statBlock", EPSILON)
            return True
        return False

    @skip_errors
    def _statement(self, container: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_variable):
            var = ASTNode(ListNodeType.VAR)
            if self._nested_var_or_call(var, end_variable=True, end_function_call=True):
                last_node = var.children[-1].node_type
                if self._la_eq(S.ASSIGN) and last_node == GroupNodeType.DATA_MEMBER:
                    assign = container.make_child(GroupNodeType.ASSIGN_STAT)
                    assign.adopt(var)
                    if self._match(S.ASSIGN) and self._expr(assign):
                        self._on_production("assignStat", "variable", "'='", "expr")
                        if self._match(S.SEMI_COLON):
                            self._on_production("statement", "assignStat", "';'")
                            return True
                elif self._la_eq(S.SEMI_COLON) and last_node == GroupNodeType.F_CALL:
                    var.node_type = ListNodeType.F_CALL_STAT
                    container.adopt(var)
                    if self._match(S.SEMI_COLON):
                        self._on_production("statement", "functionCall", "';'")
                        return True
        elif self._la_eq(K.IF):
            if_ = container.make_child(GroupNodeType.IF_STAT)
            rel_expr = if_.make_child(GroupNodeType.REL_EXPR)
            then = if_.make_child(ListNodeType.STAT_BLOCK)
            else_ = if_.make_child(ListNodeType.STAT_BLOCK)
            if (
                self._match(K.IF)
                and self._match(S.OPEN_PAR)
                and self._rel_expr(rel_expr)
                and self._match(S.CLOSE_PAR)
                and self._match(K.THEN)
                and self._stat_block(then)
                and self._match(K.ELSE)
                and self._stat_block(else_)
                and self._match(S.SEMI_COLON)
            ):
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
            while_ = container.make_child(GroupNodeType.WHILE_STAT)
            rel_expr = while_.make_child(GroupNodeType.REL_EXPR)
            stat_block = while_.make_child(ListNodeType.STAT_BLOCK)
            if (
                self._match(K.WHILE)
                and self._match(S.OPEN_PAR)
                and self._rel_expr(rel_expr)
                and self._match(S.CLOSE_PAR)
                and self._stat_block(stat_block)
                and self._match(S.SEMI_COLON)
            ):
                self._on_production(
                    "statement", "'while'", "'('", "relExpr", "')'", "statBlock", "';'",
                )
                return True
        elif self._la_eq(K.READ):
            read = container.make_child(GroupNodeType.READ_STAT)
            var = read.make_child(ListNodeType.VAR)
            if (
                self._match(K.READ)
                and self._match(S.OPEN_PAR)
                and self._nested_var_or_call(var, end_variable=True)
                and self._match(S.CLOSE_PAR)
                and self._match(S.SEMI_COLON)
            ):
                self._on_production(
                    "statement", "'read'", "'('", "variable", "')'", "';'",
                )
                return True
        elif self._la_eq(K.WRITE):
            write = container.make_child(GroupNodeType.WRITE_STAT)
            if (
                self._match(K.WRITE)
                and self._match(S.OPEN_PAR)
                and self._expr(write)
                and self._match(S.CLOSE_PAR)
                and self._match(S.SEMI_COLON)
            ):
                self._on_production(
                    "statement", "'write'", "'('", "expr", "')'", "';'",
                )
                return True
        elif self._la_eq(K.RETURN):
            return_ = container.make_child(GroupNodeType.RETURN_STAT)
            if (
                self._match(K.RETURN)
                and self._match(S.OPEN_PAR)
                and self._expr(return_)
                and self._match(S.CLOSE_PAR)
                and self._match(S.SEMI_COLON)
            ):
                self._on_production(
                    "statement", "'return'", "'('", "expr", "')'", "';'",
                )
                return True
        return False

    @skip_errors
    def _term(self, container: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_factor):
            mult_expr = container.make_child(GroupNodeType.MULT_EXPR)
            if self._factor(mult_expr) and self._rightrec_term(mult_expr):
                if not mult_expr.token:
                    mult_expr.absorb()
                self._on_production("term", "factor", "rightrec-term")
                return True
        return False

    @skip_errors
    def _type(self, type_: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(K.INTEGER):
            if self._match(K.INTEGER):
                type_.token = self.current
                self._on_production("type", "'integer'")
                return True
        elif self._la_eq(K.FLOAT):
            if self._match(K.FLOAT):
                type_.token = self.current
                self._on_production("type", "'float'")
                return True
        elif self._la_eq(G.ID):
            if self._match(G.ID):
                type_.token = self.current
                self._on_production("type", "'id'")
                return True
        return False

    @skip_errors
    def _var_decl(self, var_decl: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_in(FIRST_type):
            type_ = var_decl.make_child(LeafNodeType.TYPE)
            if self._type(type_) and self._match(G.ID):
                var_decl.make_child(LeafNodeType.ID, self.current)
                dims = var_decl.make_child(ListNodeType.DIM_LIST)
                if self._rept_var_decl2(dims) and self._match(S.SEMI_COLON):
                    self._on_production(
                        "varDecl", "type", "'id'", "rept-varDecl2", "';'"
                    )
                    return True
        return False

    @skip_errors
    def _visibility(self, visibility: ASTNode):  # LT_AUTO_FUNCTION
        if self._la_eq(K.PUBLIC):
            if self._match(K.PUBLIC):
                visibility.token = self.current
                self._on_production("visibility", "'public'")
                return True
        elif self._la_eq(K.PRIVATE):
            if self._match(K.PRIVATE):
                visibility.token = self.current
                self._on_production("visibility", "'private'")
                return True
        return False
