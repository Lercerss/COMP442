import re

from typing import List, Set

from lex.token import Location, Token, TokenType
from syn.sets import EPSILON
from .table import GLOBALS, SymbolTable, Record

EXTENSION = re.compile(r"\.src$")


class SemanticOutput:
    def __init__(self):
        self._errors = []
        self._parse_errors = []
        self.warned = False
        self.failed = False

    def warn(self, msg, location):
        self._errors.append((location or Location(-1, 0), "Semantic Warning: " + msg))
        self.warned = True

    def error(self, msg, location):
        self._errors.append((location or Location(-1, 0), "Semantic Error: " + msg))
        self.failed = True

    def invalid_token(self, token: Token):
        self._errors.append(str(token))

    def panic(self, expected: Set[TokenType], found: Token):
        self._parse_errors.append(
            "Syntax Error: Expected one of [{expected}] but found {found}".format(
                expected=",".join(str(e) for e in expected if e is not EPSILON),
                found=str(found),
            )
        )

    def resume(self, skipped: List[Token], next_token: Token):
        self._parse_errors.append(
            "Recovery: Skipped [{skipped}]".format(
                skipped=",".join(str(s) for s in skipped)
            )
        )
        self._parse_errors.append(
            "Recovery: Resuming at {next_token}".format(next_token=next_token)
        )

    def format_error(self, error):
        if error[0].line < 0:
            return error[1]
        return error[1] + ": line {location.line}, column {location.column}".format(
            location=error[0]
        )

    def success(self, source_file: str):
        formatter = TableFormatter(GLOBALS)

        if self.failed:
            print(source_file + ": Failed to compile")
        elif self.warned:
            print(source_file + ": Compiled with warnings")
        else:
            print(source_file + ": Compiled successfully")

        with open(EXTENSION.sub(".outsemanticerrors", source_file), "w") as f:
            f.write("\n".join(self.format_error(e) for e in sorted(self._errors)))

        with open(EXTENSION.sub(".outsymboltables", source_file), "w") as f:
            f.write(formatter.output())

        with open(EXTENSION.sub(".outsyntaxerrors", source_file), "w") as f:
            pass

    def fail(self, source_file: str):
        print(source_file + ": Failed to parse")
        with open(EXTENSION.sub(".outsyntaxerrors", source_file), "w") as f:
            f.write("\n".join(self._parse_errors))

        with open(EXTENSION.sub(".outsemanticerrors", source_file), "w") as f:
            pass

        with open(EXTENSION.sub(".outsymboltables", source_file), "w") as f:
            pass


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
