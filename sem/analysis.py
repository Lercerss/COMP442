from .vis.table_builder import TableBuilder
from .vis.table_check import TableCheck
from .vis.type_check import TypeCheck
from .table import GLOBALS


class SemanticAnalyzer:
    def __init__(self, output=None):
        self.visitors = [vis(output) for vis in (TableBuilder, TableCheck, TypeCheck)]

    def start(self, root):
        GLOBALS.entries.clear()
        for visitor in self.visitors:
            root.accept(visitor)
