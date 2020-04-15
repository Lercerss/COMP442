from sem.table import GLOBALS
from syn.ast import ASTNode

from .models import Prog
from .vis.code_gen import CodeGenerator


class Generator:
    def __init__(self, root: ASTNode):
        self.root = root
        self.prog = Prog()
        self.visitors = [CodeGenerator(self.prog)]

    def start(self) -> str:
        GLOBALS.update_offsets()

        for visitor in self.visitors:
            self.root.accept(visitor)

        return self.prog.output()
