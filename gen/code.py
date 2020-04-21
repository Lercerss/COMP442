from sem.table import GLOBALS
from syn.ast import ASTNode

from .models import Prog
from .vis.code_gen import CodeGenerator


class Generator:
    def __init__(self):
        self.prog = Prog()
        self.visitors = [CodeGenerator(self.prog)]

    def start(self, root: ASTNode) -> str:
        for visitor in self.visitors:
            root.accept(visitor)

        return self.prog.output()
