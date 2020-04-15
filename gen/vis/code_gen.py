from collections import defaultdict
from contextlib import contextmanager
from typing import List

from lex.token import Operators as O
from sem.table import Record, RecordType
from sem.visitor import Visitor
from syn.ast import ASTNode, GroupNodeType

from gen.models import Function, Line

OP_TO_INSTRUCTION = {
    O.EQ: "ceq",
    O.NEQ: "cne",
    O.LT: "clt",
    O.GT: "cgt",
    O.LTE: "cle",
    O.GTE: "cge",
    O.PLUS: "add",
    O.MINUS: "sub",
    O.DIV: "div",
    O.MULT: "mul",
    O.OR: "or",
    O.AND: "and",
    O.NOT: "not",
}


def _add_line(lines, *args, **kwargs):
    lines.append(Line(*args, **kwargs))


class CodeGenerator(Visitor):
    def __init__(self, prog=None):
        super().__init__(output=None)
        self.prog = prog
        self._register_stack = ["r" + str(i) for i in range(12, 0, -1)]
        self._counter = defaultdict(int)
        self._mangled_names = {}

    def counter(self, type_):
        self._counter[type_] += 1
        return self._counter[type_]

    def mangle(self, name, type_):
        if name not in self._mangled_names:
            self._mangled_names[name] = "{}{}{}".format(
                type_, self.counter(type_), name.replace("::", "_")
            )

        return self._mangled_names[name]

    def pop_reg(self) -> str:
        return self._register_stack.pop()

    def push_reg(self, reg: str):
        self._register_stack.append(reg)

    @contextmanager
    def register(self):
        register = self.pop_reg()
        yield register
        self.push_reg(register)

    def load_in_reg(self, node: ASTNode, register: str):
        if node.record:
            # TODO Probably needs more lines when accessing a class var?
            return Line("lw", [register, node.record.memory_location()])
        else:
            # TODO Assumed if there is no record it has to be a literal
            # TODO Handle float literals
            return Line("addi", [register, "r0", node.token.lexeme])

    @contextmanager
    def new_frame(self, lines: List[Line]):
        _add_line(
            lines,
            "addi",
            ["r14", "r14", str(-self.scope.current_size())],
            comment="increment stack frame",
        )
        yield
        _add_line(
            lines,
            "subi",
            ["r14", "r14", str(-self.scope.current_size())],
            comment="decrement stack frame",
        )

    def _visit_var(self, node: ASTNode):
        first_record = node.children[0].record
        record = Record("", first_record.type, RecordType.TEMP, first_record.location,)
        for child in node.children:
            if child.node_type == GroupNodeType.DATA_MEMBER:
                # TODO Handle indexing
                record.offset += child.record.offset
            else:
                # TODO Handle member functions
                # Use current record.offset to set the "this" of the function call

                offset = 8  # Leave space for return value and r15 in stack frame
                offset += self.scope.current_size()

                for arg in child.children[1].children:  # Handle arguments
                    with self.register() as register:
                        node.code.append(self.load_in_reg(arg, register))
                        _add_line(
                            node.code, "sw", [str(-offset) + "(r14)", register],
                        )
                        if arg.record:
                            offset += arg.record.type.size
                        else:  # Literal
                            # TODO Handle float literal
                            offset += 4

                with self.new_frame(node.code):  # Call function
                    _add_line(
                        node.code,
                        "jl",
                        ["r15", self.mangle(child.record.table.name, "func")],
                    )

                with self.register() as register:  # Retrieve return value
                    _add_line(
                        node.code,
                        "lw",
                        [register, str(-self.scope.current_size()) + "(r14)"],
                    )
                    _add_line(
                        node.code, "sw", [child.record.memory_location(), register]
                    )
                record.offset = child.record.offset

        node.record = record

    def _visit_f_call_stat(self, node: ASTNode):
        node.code = node.children[-1].code

    def _visit_main(self, node: ASTNode):
        main = Function("main")
        _add_line(main.lines, "entry", [])
        _add_line(
            main.lines,
            "addi",
            ["r14", "r0", "topaddr"],
            comment="Push initial stack pointer",
        )
        _add_line(
            main.lines,
            "addi",
            ["r14", "r14", "-4"],
            comment="Adjust stack pointer offset",
        )

        for stat in node.children[1].children:
            main.lines += stat.code

        _add_line(main.lines, "hlt", [])

        self.prog.functions.append(main)

    def _visit_func_def(self, node: ASTNode):
        name = self.mangle(node.record.table.name, "func")
        func = Function(name)
        # Return value at 0(r14) and return address at -4(r14)
        _add_line(func.lines, "sw", ["-4(r14)", "r15"], symbol=name)

        for stat in node.children[-1].children:
            func.lines += stat.code

        _add_line(func.lines, "sw", ["0(r14)", "r0"])
        _add_line(func.lines, "lw", ["r15", "-4(r14)"], symbol=name + "return")
        _add_line(func.lines, "jr", ["r15"])

        self.prog.functions.append(func)

    def _visit_if_stat(self, node: ASTNode):
        # TODO Implement
        return

    def _visit_assign_stat(self, node: ASTNode):
        # TODO Only works for local variables right now!
        # TODO Only works for integers
        lhs = node.children[0]
        rhs = node.children[1]
        node.code += lhs.code
        node.code += rhs.code

        with self.register() as register:
            node.code.append(self.load_in_reg(rhs, register))
            _add_line(node.code, "sw", [lhs.record.memory_location(), register])

    def _visit_while_stat(self, node: ASTNode):
        # TODO Implement
        return

    def _visit_read_stat(self, node: ASTNode):
        # TODO Implement
        return

    def _visit_write_stat(self, node: ASTNode):
        self.prog.reserve("buf", 20)

        value = node.children[0]
        with self.register() as register:
            node.code.append(self.load_in_reg(value, register))

            with self.new_frame(node.code):
                _add_line(node.code, "sw", ["-8(r14)", register])
                with self.register() as buf_reg:
                    _add_line(node.code, "addi", [buf_reg, "r0", "buf"])
                    _add_line(node.code, "sw", ["-12(r14)", buf_reg])
                _add_line(node.code, "jl", ["r15", "intstr"])
                _add_line(node.code, "sw", ["-8(r14)", "r13"])
                _add_line(node.code, "jl", ["r15", "putstr"])

    def _visit_return_stat(self, node: ASTNode):
        name = self.mangle(self.scope.name, "func")
        child = node.children[0]
        node.code += child.code
        with self.register() as register:
            node.code.append(self.load_in_reg(child, register))
            _add_line(node.code, "sw", ["0(r14)", register])
            _add_line(node.code, "j", [name + "return"])

    def _dyadic_expr(self, node: ASTNode):
        lhs = node.children[0]
        rhs = node.children[1]
        node.code += lhs.code
        node.code += rhs.code
        with self.register() as lhs_reg, self.register() as rhs_reg, self.register() as res_reg:
            node.code.append(self.load_in_reg(lhs, lhs_reg))
            node.code.append(self.load_in_reg(rhs, rhs_reg))
            _add_line(
                node.code,
                OP_TO_INSTRUCTION[node.token.token_type],
                [res_reg, lhs_reg, rhs_reg],
            )
            _add_line(node.code, "sw", [node.record.memory_location(), res_reg])

    def _visit_rel_expr(self, node: ASTNode):
        self._dyadic_expr(node)

    def _visit_add_expr(self, node: ASTNode):
        self._dyadic_expr(node)

    def _visit_mult_expr(self, node: ASTNode):
        self._dyadic_expr(node)

    def _monadic_expr(self, node: ASTNode):
        child = node.children[0]
        node.code += child.code
        with self.register() as res_reg, self.register() as child_reg:
            node.code.append(self.load_in_reg(child, child_reg))
            _add_line(
                node.code,
                OP_TO_INSTRUCTION[node.token.token_type],
                [res_reg, child_reg],
            )
            _add_line(node.code, "sw", [node.record.memory_location(), res_reg])

    def _visit_not(self, node: ASTNode):
        self._monadic_expr(node)

    def _visit_sign(self, node: ASTNode):
        self._monadic_expr(node)

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

    def _visit_class_decl(self, node: ASTNode):
        return

    def _visit_func_decl(self, node: ASTNode):
        return

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

    def _visit_index_list(self, node: ASTNode):
        return

    def _visit_arg_list(self, node: ASTNode):
        return

    def _visit_prog(self, node: ASTNode):
        return
