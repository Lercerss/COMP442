from .vis.table_builder import TableBuilder


class SemanticAnalyzer:
    def __init__(self, root, output=None):
        self.root = root
        self.visitors = [TableBuilder(output)]

    def start(self):
        for visitor in self.visitors:
            self.root.accept(visitor)
