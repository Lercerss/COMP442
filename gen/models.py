from collections import OrderedDict
from typing import List, Dict


class Line:
    def __init__(self, instruction, args, symbol=None, comment=None):
        self.instruction = instruction
        self.args = args
        self.symbol = symbol
        self.comment = comment

    def format(self) -> str:
        out = " {symbol:7} {instruction:5} {args:15}".format(
            symbol=self.symbol or "",
            instruction=self.instruction,
            args=",".join(self.args),
        )
        if self.comment:
            out += "% " + self.comment
        return out.rstrip()


class Function:
    def __init__(self, name):
        self.name = name
        self.lines: List[Line] = []

    def format(self) -> str:
        out = " % begin function {name} definition\n".format(name=self.name)
        for line in self.lines:
            out += line.format() + "\n"

        return out + " % end function {name} definition\n".format(name=self.name)


class Prog:
    def __init__(self):
        self.functions: List[Function] = []
        self.reserved: Dict[str, Line] = OrderedDict()

    def reserve(self, tag, size):
        if tag in self.reserved:
            return
        self.reserved[tag] = Line("res", [str(size)], symbol=tag)

    def output(self) -> str:
        executable = ""
        for func in self.functions:
            executable += func.format() + "\n"

        for line in self.reserved.values():
            executable += line.format() + "\n"

        return executable
