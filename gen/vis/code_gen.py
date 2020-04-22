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

    def new_mangled(self, name, type_):
        """As moon symbols cannot contain "::" replace it with "_"
        To prevent symbol name clashes, use a counter to guarantee uniqueness"""
        self._mangled_names[(name, type_)] = "{}{}{}".format(
            type_, self.counter(type_), name.replace("::", "_")
        )
        return self._mangled_names[(name, type_)]

    def get_mangled(self, name, type_):
        if (name, type_) not in self._mangled_names:
            return self.new_mangled(name, type_)
        return self._mangled_names[(name, type_)]

    def pop_reg(self) -> str:
        return self._register_stack.pop()

    def push_reg(self, reg: str):
        self._register_stack.append(reg)

    @contextmanager
    def register(self):
        register = self.pop_reg()
        yield register
        self.push_reg(register)

    def dereference(self, code, record: Record, offset: int, register: str):
        with self.register() as addr_reg:
            _add_line(code, "lw", [addr_reg, record.memory_location()])
            _add_line(
                code, "lw", [register, str(-offset) + "(" + addr_reg + ")"],
            )

    def load_in_reg(self, code: List[Line], node: ASTNode, register: str):
        if node.temp_record:
            # Dynamic access offset needs to be loaded
            self.dereference(code, node.temp_record, node.record.offset, register)
        elif node.record:
            if node.record.is_pointer():
                # Complex parameters passed as pointers
                self.dereference(code, node.record, 0, register)
            else:
                _add_line(code, "lw", [register, node.record.memory_location()])
        else:
            # TODO Handle float literals
            _add_line(code, "addi", [register, "r0", node.token.lexeme])

    def store_from_reg(self, code: List[Line], node: ASTNode, register: str):
        if node.temp_record:
            # Dynamic access offset needs to be loaded
            with self.register() as addr_reg:
                _add_line(code, "lw", [addr_reg, node.temp_record.memory_location()])
                _add_line(
                    code,
                    "sw",
                    [str(-node.record.offset) + "(" + addr_reg + ")", register],
                )
        elif node.record:
            _add_line(code, "sw", [node.record.memory_location(), register])

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
        if first_record.record_type == RecordType.DATA:
            node.temp_record = Record(
                "", first_record.type, RecordType.TEMP, first_record.location,
            )
            node.temp_record.offset = 8

        for child in node.children:
            if child.node_type == GroupNodeType.DATA_MEMBER:
                record.offset += child.record.offset
                index_list = child.children[1]
                if index_list.children:
                    # Array indexing
                    offset_code = []
                    with self.register() as ofs_reg, self.register() as tmp_reg:
                        op, start_addr = "addi", ["r14", str(-record.offset)]
                        if node.temp_record:
                            op, start_addr = (
                                "lw",
                                [str(-node.temp_record.offset) + "(r14)"],
                            )
                        elif child.record.is_pointer():
                            op, start_addr = "lw", [child.record.memory_location()]

                        _add_line(offset_code, op, [ofs_reg, *start_addr])
                        for i, index in enumerate(index_list.children):
                            node.code += index.code
                            self.load_in_reg(offset_code, index, tmp_reg)
                            _add_line(
                                offset_code,
                                "muli",
                                [
                                    tmp_reg,
                                    tmp_reg,
                                    str(child.record.type.mul_for_dim(i)),
                                ],
                            )
                            _add_line(offset_code, "sub", [ofs_reg, ofs_reg, tmp_reg])

                        _add_line(
                            offset_code,
                            "sw",
                            [child.temp_record.memory_location(), ofs_reg],
                        )
                    node.code += offset_code
                    record.offset = 0
                    node.temp_record = child.temp_record
            else:
                offset = 8  # Leave space for return value and r15 in stack frame
                offset += self.scope.current_size()

                if "::" in child.record.table.name:
                    # Add `this` pointer
                    with self.register() as register:
                        if node.temp_record:
                            _add_line(
                                node.code,
                                "lw",
                                [register, node.temp_record.memory_location()],
                            )
                            _add_line(
                                node.code,
                                "addi",
                                [register, register, str(-record.offset)],
                            )
                        else:
                            _add_line(
                                node.code,
                                "addi",
                                [register, "r14", str(-record.offset)],
                            )
                        _add_line(
                            node.code, "sw", [str(-offset) + "(r14)", register],
                        )
                    offset += 4

                for arg in child.children[1].children:  # Handle arguments
                    node.code += arg.code
                    with self.register() as register:
                        if arg.record and arg.record.type.is_complex():
                            # Pass complex arguments as pointers
                            _add_line(
                                node.code,
                                "addi",
                                [register, "r14", str(-arg.record.offset)],
                            )
                        else:
                            self.load_in_reg(node.code, arg, register)
                        _add_line(
                            node.code, "sw", [str(-offset) + "(r14)", register],
                        )
                        if arg.record:
                            if arg.record.type.is_complex():
                                offset += 4
                            else:
                                offset += arg.record.type.size
                        else:  # Literal
                            # TODO Handle float literal
                            offset += 4

                with self.new_frame(node.code):  # Call function
                    _add_line(
                        node.code,
                        "jl",
                        ["r15", self.get_mangled(child.record.table.name, "func")],
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
        self._visit_var(node)

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
        name = self.get_mangled(node.record.table.name, "func")
        func = Function(name)
        # TODO Handle returning floats?
        # TODO Handle returning objects
        # Return value at 0(r14) and return address at -4(r14)
        _add_line(func.lines, "sw", ["-4(r14)", "r15"], symbol=name)

        for stat in node.children[-1].children:
            func.lines += stat.code

        _add_line(func.lines, "sw", ["0(r14)", "r0"])
        _add_line(func.lines, "lw", ["r15", "-4(r14)"], symbol=name + "return")
        _add_line(func.lines, "jr", ["r15"])

        self.prog.functions.append(func)

    def _visit_if_stat(self, node: ASTNode):
        rel_expr = node.children[0]
        register = rel_expr.code[-1].args[0]
        if_sym = self.new_mangled(self.scope.name, "if")

        node.code += rel_expr.code
        _add_line(node.code, "bz", [register, if_sym + "else"], symbol=if_sym)

        for stat in node.children[1].children:
            node.code += stat.code

        _add_line(node.code, "j", [if_sym + "done"])
        _add_line(node.code, "nop", [], symbol=if_sym + "else")

        for stat in node.children[2].children:
            node.code += stat.code

        _add_line(node.code, "nop", [], symbol=if_sym + "done")

    def _visit_assign_stat(self, node: ASTNode):
        # TODO Handle floats?
        lhs = node.children[0]
        rhs = node.children[1]
        node.code += rhs.code
        node.code += lhs.code

        with self.register() as register:
            self.load_in_reg(node.code, rhs, register)
            self.store_from_reg(node.code, lhs, register)

    def _visit_while_stat(self, node: ASTNode):
        rel_expr = node.children[0]
        register = rel_expr.code[-1].args[0]
        while_sym = self.new_mangled(self.scope.name, "while")

        node.code += rel_expr.code
        node.code[0].symbol = while_sym
        _add_line(node.code, "bz", [register, while_sym + "done"])

        for stat in node.children[1].children:
            node.code += stat.code

        _add_line(node.code, "j", [while_sym])
        _add_line(node.code, "nop", [], symbol=while_sym + "done")

    def _visit_read_stat(self, node: ASTNode):
        self.prog.reserve("buf", 20, comment="str buffer")

        # TODO Only works for integers
        # TODO Might need work for arrays
        child = node.children[0]
        node.code += child.code

        with self.new_frame(node.code):
            with self.register() as buf_reg:
                _add_line(node.code, "addi", [buf_reg, "r0", "buf"])
                _add_line(node.code, "sw", ["-8(r14)", buf_reg])
            _add_line(node.code, "jl", ["r15", "getstr"])
            _add_line(node.code, "jl", ["r15", "strint"])
        self.store_from_reg(node.code, child, "r13")

    def _visit_write_stat(self, node: ASTNode):
        self.prog.reserve("buf", 20, comment="str buffer")
        self.prog.store_constant("nl", "13", "10", "0", comment='nl = "\\r\\n\\0"')

        value = node.children[0]
        node.code += value.code

        with self.register() as register:
            self.load_in_reg(node.code, value, register)

            with self.new_frame(node.code):
                _add_line(node.code, "sw", ["-8(r14)", register])
                with self.register() as buf_reg:
                    _add_line(node.code, "addi", [buf_reg, "r0", "buf"])
                    _add_line(node.code, "sw", ["-12(r14)", buf_reg])
                _add_line(node.code, "jl", ["r15", "intstr"])
                _add_line(node.code, "sw", ["-8(r14)", "r13"])
                _add_line(node.code, "jl", ["r15", "putstr"])
                # Append a newline
                with self.register() as nl_reg:
                    _add_line(node.code, "addi", [nl_reg, "r0", "nl"])
                    _add_line(node.code, "sw", ["-8(r14)", nl_reg])
                _add_line(node.code, "jl", ["r15", "putstr"])

    def _visit_return_stat(self, node: ASTNode):
        name = self.get_mangled(self.scope.name, "func")
        child = node.children[0]
        node.code += child.code
        with self.register() as register:
            self.load_in_reg(node.code, child, register)
            _add_line(node.code, "sw", ["0(r14)", register])
            _add_line(node.code, "j", [name + "return"])

    def _visit_rel_expr(self, node: ASTNode):
        lhs = node.children[0]
        rhs = node.children[1]
        node.code += rhs.code
        node.code += lhs.code
        with self.register() as lhs_reg, self.register() as rhs_reg, self.register() as res_reg:
            self.load_in_reg(node.code, lhs, lhs_reg)
            self.load_in_reg(node.code, rhs, rhs_reg)
            _add_line(
                node.code,
                OP_TO_INSTRUCTION[node.token.token_type],
                [res_reg, lhs_reg, rhs_reg],
            )

    def _dyadic_expr(self, node: ASTNode):
        lhs = node.children[0]
        rhs = node.children[1]
        node.code += rhs.code
        node.code += lhs.code
        with self.register() as lhs_reg, self.register() as rhs_reg, self.register() as res_reg:
            self.load_in_reg(node.code, lhs, lhs_reg)
            self.load_in_reg(node.code, rhs, rhs_reg)
            _add_line(
                node.code,
                OP_TO_INSTRUCTION[node.token.token_type],
                [res_reg, lhs_reg, rhs_reg],
            )
            _add_line(node.code, "sw", [node.record.memory_location(), res_reg])

    def _visit_add_expr(self, node: ASTNode):
        self._dyadic_expr(node)

    def _visit_mult_expr(self, node: ASTNode):
        self._dyadic_expr(node)

    def _visit_not(self, node: ASTNode):
        child = node.children[0]
        node.code += child.code
        with self.register() as res_reg, self.register() as child_reg:
            self.load_in_reg(node.code, child, child_reg)
            _add_line(
                node.code,
                OP_TO_INSTRUCTION[node.token.token_type],
                [res_reg, child_reg],
            )
            _add_line(node.code, "sw", [node.record.memory_location(), res_reg])

    def _visit_sign(self, node: ASTNode):
        child = node.children[0]
        node.code += child.code
        with self.register() as res_reg, self.register() as child_reg:
            self.load_in_reg(node.code, child, child_reg)
            _add_line(
                node.code,
                OP_TO_INSTRUCTION[node.token.token_type],
                [res_reg, "r0", child_reg],
            )
            _add_line(node.code, "sw", [node.record.memory_location(), res_reg])

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
