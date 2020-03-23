from collections import defaultdict
from enum import Enum, unique, auto
from typing import Dict, List

from lex.token import Token, TokenType, Keywords as K


class SymbolType:
    __instances = {}

    def __new__(cls, name, *args, **kwargs):
        if name in cls.__instances:
            return cls.__instances[name]
        instance = super().__new__(cls)
        cls.__instances[name] = instance
        return instance

    def __init__(self, name, simple_type=False):
        self.name = name
        self.simple_type = simple_type

    @property
    def table(self) -> "SymbolTable":
        if self.simple_type:
            return None
        return next((r.table for r in GLOBALS.search_in_scope(self.name)), None)


FLOAT = SymbolType("float", simple_type=True)
INT = SymbolType("integer", simple_type=True)
VOID = SymbolType("void", simple_type=True)


@unique
class RecordType(Enum):
    CLASS = auto()
    DATA = auto()  # Data member of a class
    FUNCTION = auto()
    PARAM = auto()
    LOCAL = auto()

    def __str__(self):
        return str(self.name).lower()


class Record:
    def __init__(
        self,
        name: str,
        type_: SymbolType,
        record_type: RecordType,
        dims: List[Token] = [],
        params: List["Record"] = None,
        visibility: TokenType = None,
        table: "SymbolTable" = None,
    ):
        self.name = name
        self.type = type_
        self.record_type = record_type
        self.dims = dims
        self.params = params
        self.visibility = visibility
        self.table = table

    def format_type(self) -> str:
        params = ""
        if self.record_type == RecordType.FUNCTION and self.params is not None:
            params = "({}): ".format(", ".join(p.format_type() for p in self.params))
        return (
            params
            + self.type.name
            + "".join("[{}]".format(t.lexeme if t else "") for t in self.dims)
        )

    def format(self) -> List[str]:
        values = [str(self.record_type), str(self.name)]
        if self.record_type != RecordType.CLASS:
            values.append(self.format_type())
        if self.visibility:
            values.append(str(self.visibility))
        return values

    def __eq__(self, other):
        return (
            isinstance(other, Record)
            and self.name == other.name
            and self.type is other.type
            and self.dims == other.dims
            and self.record_type == other.record_type
            and self.params == other.params
        )


class SymbolTable:
    def __init__(self, name: str, inherits: List[SymbolType] = None):
        self.name = name
        self.inherits = inherits
        self.entries: Dict[str, List[Record]] = defaultdict(list)

    def insert(self, record: Record):
        self.entries[record.name].append(record)
        if record.table:
            record.table.parent = self

    def _search_in_scope(self, name) -> List[Record]:
        return [entry for entry in self.entries.get(name, [])] + [
            entry
            for parent in (self.inherits or [])
            for entry in parent.table._search_in_scope(name)
        ]

    def search_in_scope(self, name) -> List[Record]:
        return self._search_in_scope(name) + GLOBALS._search_in_scope(name)

    def search_member(self, name, visibility: TokenType = K.PRIVATE) -> List[Record]:
        return [
            entry
            for entry in self.entries.get(name, [])
            if visibility == K.PRIVATE or entry.visibility == K.PUBLIC
        ] + [
            entry
            for parent in (self.inherits or [])
            for entry in parent.table.search_member(name, K.PUBLIC)
        ]


GLOBALS = SymbolTable("global")
GLOBALS.search_in_scope = GLOBALS._search_in_scope  # Avoid recursive lookup
