import re

from typing import List, Set

from lex.token import Location, Token, TokenType
from syn.sets import EPSILON
from .table import GLOBALS, SymbolTable, Record

EXTENSION = re.compile(r"\.src$")


class SemanticOutput:
    def __init__(self, source_file: str):
        self.__errors = []
        self.__errors_file = open(EXTENSION.sub(".outsemanticerrors", source_file), "w")
        self.__tables_file = open(EXTENSION.sub(".outsymboltables", source_file), "w")
        self.__warned = False
        self.__failed = False

    def warn(self, msg, location):
        self.__errors.append((location or Location(-1, 0), "Semantic Warning: " + msg))
        self.__warned = True

    def error(self, msg, location):
        self.__errors.append((location or Location(-1, 0), "Semantic Error: " + msg))
        self.__failed = True

    def __format_error(self, error):
        if error[0].line < 0:
            return error[1]
        return error[1] + ": line {location.line}, column {location.column}".format(
            location=error[0]
        )

    def tables(self):
        self.__errors_file.write(
            "\n".join(self.__format_error(e) for e in sorted(self.__errors))
        )

        formatter = TableFormatter(GLOBALS)
        self.__tables_file.write(formatter.output())

    def did_fail(self):
        return self.__failed

    def did_warn(self):
        return self.__warned

    def collect_files(self):
        return [self.__errors_file.name, self.__tables_file.name]


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
                out.append("=")
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
