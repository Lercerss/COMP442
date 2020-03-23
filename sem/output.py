from typing import List, Set

from lex import Token, TokenType
from syn.sets import EPSILON
from .table import GLOBALS, SymbolTable, Record


def warn(msg):
    print("Semantic Warning: " + msg)


def error(msg):
    print("Semantic Error: " + msg)


def invalid_token(token: Token):
    print(str(token))


def panic(expected: Set[TokenType], found: Token):
    print(
        "Syntax Error: Expected one of [{expected}] but found {found}".format(
            expected=",".join(str(e) for e in expected if e is not EPSILON),
            found=str(found),
        )
    )


def resume(skipped: List[Token], next_token: Token):
    print(
        "Recovery: Skipped [{skipped}]".format(
            skipped=",".join(str(s) for s in skipped)
        )
    )
    print("Recovery: Resuming at {next_token}".format(next_token=next_token))


def success():
    formatter = TableFormatter(GLOBALS)
    print(formatter.output())  # TODO write to file instead


class HRule:
    """Horizontal Rule"""


class TableFormatter:
    def __init__(self, table: SymbolTable):
        self.lines = self.format_table(table)
        self.sub_tables = [l for l in self.lines if isinstance(l, TableFormatter)]
        self.columns = self.column_sizes()
        max_columns = list(self.columns)
        for table in self.sub_tables:
            max_columns += [0] * max(0, len(table.columns) - len(max_columns))
            for i in range(len(table.columns)):
                max_columns[i] = max(max_columns[i], table.columns[i])
        self.update_column_sizes(max_columns)

    def format_table(self, table: SymbolTable):
        formats = [
            HRule,
            ["table", table.name],
            HRule,
        ]
        if table.inherits is not None:
            formats.append(
                ["inherits"]
                + ([inherit.name for inherit in table.inherits] or ["none"])
            )

        for records in table.entries.values():
            for record in records:
                formats.append(record.format())
                if record.table:
                    formats.append(TableFormatter(record.table))

        formats.append(HRule)
        return formats

    def depth(self):
        if self.sub_tables:
            return max(table.depth() for table in self.sub_tables) + 1
        return 1

    def update_column_sizes(self, max_columns: List[int]):
        for i in range(min(len(self.columns), len(max_columns))):
            self.columns[i] = max_columns[i]

        for table in self.sub_tables:
            table.update_column_sizes(max_columns)

    def column_sizes(self) -> List[int]:
        columns = [0] * max(len(line) for line in self.lines if type(line) == list)
        for line in self.lines:
            if line is HRule or isinstance(line, TableFormatter):
                continue
            for i in range(len(line)):
                columns[i] = max(columns[i], len(line[i]))

        return columns

    def _output(self) -> List[str]:
        out = []
        for line in self.lines:
            if line is HRule:
                out.append("=" * (sum(self.columns) + 4 * self.depth()))
            elif isinstance(line, TableFormatter):
                out += [
                    "|     {}".format(l)
                    for l in line._output()  # pylint: disable=no-member
                ]
            else:
                columns = self.columns[: len(line)]
                columns[-1] += sum(self.columns[len(line) :]) + 3 * (
                    len(line) - len(self.columns)
                )
                out.append("| " + " | ".join(l.ljust(c) for c, l in zip(columns, line)))

        max_len = max(len(l.strip()) for l in out)
        out = [
            line.ljust(max_len + 2, "=")
            if line.startswith("=")
            else line.strip().ljust(max_len) + " |"
            for line in out
        ]

        return out

    def output(self) -> str:
        return "\n".join(self._output())
