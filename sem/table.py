from collections import defaultdict
from enum import Enum, unique, auto
from typing import Dict, List

from lex.token import Token, Location, TokenType, Keywords as K


class BaseType:
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
        return next(
            (
                r.table
                for r in GLOBALS.search_in_scope(self.name)
                if r.record_type == RecordType.CLASS
            ),
            None,
        )


FLOAT = BaseType("float", simple_type=True)
INT = BaseType("integer", simple_type=True)
VOID = BaseType("void", simple_type=True)
BOOLEAN = BaseType("", simple_type=True)


class SymbolType:
    def __init__(self, base: str, dims: List[Token]):
        self.base = base if type(base) == BaseType else BaseType(base)
        self.dims = dims

    def __eq__(self, other):
        return (
            isinstance(other, SymbolType)
            and self.base is other.base
            and len(self.dims) == len(other.dims)
        )

    def __str__(self):
        return self.base.name + "".join(
            "[{}]".format(t.lexeme if t else "") for t in self.dims
        )

    def __hash__(self):
        return hash(str(self))

    def is_array(self):
        return len(self.dims) > 0


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
        location: Location,
        params: List["Record"] = None,
        visibility: TokenType = None,
        table: "SymbolTable" = None,
    ):
        self.name = name
        self.type = type_
        self.record_type = record_type
        self.location = location
        self.params = params
        self.visibility = visibility
        self.table = table

    def format_type(self) -> str:
        params = ""
        if self.record_type == RecordType.FUNCTION and self.params is not None:
            params = "({}) : ".format(", ".join(p.format_type() for p in self.params))
        return params + str(self.type)

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
            and self.type == other.type
            and self.record_type == other.record_type
            and equal_params(self.params, other.params)
        )


def equal_params(left: List[Record], right: List[Record]):
    if left is None or right is None:
        return left is right
    return tuple(p.type for p in left) == tuple(p.type for p in right)


class SymbolTable:
    def __init__(self, name: str, inherits: List[BaseType] = None):
        self.name = name
        self.inherits = inherits
        self.entries: Dict[str, List[Record]] = defaultdict(list)

    def insert(self, record: Record):
        self.entries[record.name].append(record)
        if record.table:
            record.table.parent = self

    def has_private_access(self, scope):
        return self.name.startswith(scope.name + "::")

    def search_in_scope(self, name) -> List[Record]:
        return self.search_member(name, K.PRIVATE) + GLOBALS.search_member(name)

    def search_member(self, name, visibility: TokenType = K.PRIVATE) -> List[Record]:
        return [
            entry
            for entry in self.entries.get(name, [])
            if visibility == K.PRIVATE or entry.visibility == K.PUBLIC
        ] + [
            entry
            for parent in (self.inherits or [])
            for entry in parent.table.search_member(
                name, visibility if self.has_private_access(parent) else K.PUBLIC,
            )
        ]


GLOBALS = SymbolTable("global")
GLOBALS.search_in_scope = GLOBALS.search_member  # Avoid recursive lookup
