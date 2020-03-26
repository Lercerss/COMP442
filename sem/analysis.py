from .vis.table_builder import TableBuilder
from .vis.table_check import TableCheck
from .vis.type_check import TypeCheck
from .table import GLOBALS


class SemanticAnalyzer:
    def __init__(self, root, output=None):
        GLOBALS.entries.clear()
        self.root = root
        self.visitors = [vis(output) for vis in (TableBuilder, TableCheck, TypeCheck)]

    def start(self):
        for visitor in self.visitors:
            self.root.accept(visitor)
