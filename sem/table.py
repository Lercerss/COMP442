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
        instance.__is_new = True
        cls.__instances[name] = instance
        return instance

    def __init__(self, name, simple_type=False, size=0):
        if self.__is_new:  # pylint: disable=access-member-before-definition
            self.name = name
            self.simple_type = simple_type
            self._size = size
            self.__is_new = False

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

    @property
    def size(self) -> int:
        if self.simple_type:
            return self._size

        if self.table:
            return self.table.current_size()

        return 0


FLOAT = BaseType("float", simple_type=True, size=8)
INT = BaseType("integer", simple_type=True, size=4)
VOID = BaseType("void", simple_type=True, size=0)
BOOLEAN = BaseType("boolean", simple_type=True, size=0)


class SymbolType:
    def __init__(self, base: str, dims: List[Token]):
        self.base: BaseType = base if type(base) == BaseType else BaseType(base)
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

    def is_complex(self):
        return self.is_array() or self.base.table is not None

    def mul_for_dim(self, dim: int) -> int:
        mul = 1
        for dim in self.dims[dim + 1 :]:
            if dim is None:
                continue
            mul *= int(dim.lexeme)
        return mul * self.base.size

    @property
    def size(self) -> int:
        return self.mul_for_dim(-1)


@unique
class RecordType(Enum):
    CLASS = auto()
    DATA = auto()  # Data member of a class
    FUNCTION = auto()
    PARAM = auto()
    LOCAL = auto()
    TEMP = auto()

    def __str__(self):
        return str(self.name).lower()


DATA_RECORD_TYPES = {RecordType.PARAM, RecordType.DATA, RecordType.LOCAL}


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
        offset: int = 0,
    ):
        self.name = name
        self.type = type_
        self.record_type = record_type
        self.location = location
        self.params = params
        self.visibility = visibility
        self.table = table
        self.offset = offset

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
        values.append(str(self.offset))
        values.append(str(self.size))
        return values

    def __eq__(self, other):
        return (
            isinstance(other, Record)
            and self.name == other.name
            and self.type == other.type
            and self.record_type == other.record_type
            and equal_params(self.params, other.params)
        )

    @property
    def size(self) -> int:
        if self.record_type == RecordType.FUNCTION:
            return 0
        elif self.record_type == RecordType.CLASS:
            return self.table.current_size()

        return self.type.size

    def is_pointer(self):
        return self.record_type == RecordType.PARAM and self.type.is_complex()

    def memory_location(self) -> str:
        if self.record_type in (RecordType.TEMP, RecordType.LOCAL, RecordType.PARAM):
            # On the stack
            return str(-self.offset) + "(r14)"
        return


def equal_params(left: List[Record], right: List[Record]):
    if left is None or right is None:
        return left is right
    return tuple(p.type for p in left) == tuple(p.type for p in right)


class SymbolTable:
    def __init__(self, name: str, inherits: List[BaseType] = None, is_function=False):
        self.name = name
        self.inherits = inherits
        self.is_function = is_function
        self.entries: Dict[str, List[Record]] = defaultdict(list)
        self._temp_count = 0

    def insert(self, record: Record):
        record.offset = sum(len(r) for r in self.entries.values())
        if record.record_type == RecordType.TEMP:
            record.name = self._temp_name()
        self.entries[record.name].append(record)

    def has_private_access(self, scope):
        return self.name.startswith(scope.name + "::")

    def dependencies(self) -> List[BaseType]:
        return (self.inherits or []) + list(
            r.type.base
            for records in self.entries.values()
            for r in records
            if r.type.base.table is not None and r.record_type in DATA_RECORD_TYPES
        )

    def remove_dependency(self, type_: BaseType):
        if type_ in self.inherits:
            self.inherits.remove(type_)
        else:
            for records in self.entries.values():
                record = next((r for r in records if r.type.base == type_), None)
                if record:
                    records.remove(record)
                    break

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

    def current_size(self) -> int:
        return sum(
            entry.type.size
            for entries in self.entries.values()
            for entry in entries
            if entry.record_type != RecordType.FUNCTION
        ) + sum(parent.size for parent in (self.inherits or []))

    def _temp_name(self) -> str:
        """Unique (per-scope) temporary variable names that dont conflict with user-defined names"""
        self._temp_count += 1
        return "_" + str(self._temp_count)

    def _frame_offset(self) -> int:
        if self.name == "main":
            return 0

        if "::" in self.name:
            # Add space for `this`
            # TODO Handle floats?
            return 8 + 4

        if self.is_function:
            # Reserve space for return value and return address
            # TODO Handle floats?
            return 8

        if self.inherits:
            return sum(parent.size for parent in self.inherits)

        return 0

    def update_offsets(self):
        records = [r for entries in self.entries.values() for r in entries]
        records.sort(key=lambda r: r.offset)
        size = self._frame_offset()
        tables = []
        for record in records:
            if (
                record.record_type == RecordType.FUNCTION
                or record.record_type == RecordType.CLASS
            ):
                record.offset = 0
                if record.table is not self and record.table is not None:
                    tables.append(record.table)
                continue
            record.offset = size
            if record.is_pointer():
                size += 4
            else:
                size += record.size

        for table in tables:
            table.update_offsets()


GLOBALS = SymbolTable("global")
GLOBALS.search_in_scope = GLOBALS.search_member  # Avoid recursive lookup
