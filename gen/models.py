from collections import OrderedDict
from itertools import chain
from typing import List, Dict


class Line:
    def __init__(self, instruction, args, symbol=None, comment=None):
        self.instruction = instruction
        self.args = args
        self.symbol = symbol
        self.comment = comment

    def format(self, max_size) -> str:
        out = (" {symbol:" + str(max_size) + "} {instruction:5} {args:15}").format(
            symbol=self.symbol or "",
            instruction=self.instruction,
            args=",".join(self.args),
        )
        if self.comment:
            out += "% " + self.comment
        return out.rstrip()


class Function:
    def __init__(self, name, lines=None):
        self.name = name
        self.lines: List[Line] = lines or []

    def format(self, max_size) -> str:
        out = " % begin function {name} definition\n".format(name=self.name)
        for line in self.lines:
            out += line.format(max_size) + "\n"

        return out + " % end function {name} definition\n".format(name=self.name)


class Prog:
    def __init__(self):
        self.functions: List[Function] = []
        self.constants: Dict[str, Line] = OrderedDict()

    def reserve(self, tag, size, comment=None):
        if tag in self.constants:
            return
        self.constants[tag] = Line("res", [str(size)], symbol=tag, comment=comment)

    def store_constant(self, tag, *value, comment=None):
        if tag in self.constants:
            return
        self.constants[tag] = Line("db", value, symbol=tag, comment=comment)

    def output(self) -> str:
        executable = ""
        max_size = max(
            (len(l.symbol) for f in self.functions for l in f.lines if l.symbol),
            default=1,
        )
        max_size = max(max_size, 7)
        for func in self.functions:
            executable += func.format(max_size) + "\n"

        executable += " % Constants\n"
        executable += " " * max_size + "  align\n"

        for line in self.constants.values():
            executable += line.format(max_size) + "\n"

        return executable
