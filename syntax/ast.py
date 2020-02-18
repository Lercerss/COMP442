from collections import namedtuple
from enum import Enum, unique, auto
from lex import Token

Siblings = namedtuple("Siblings", ["leftmost", "right"])


@unique
class NodeType(Enum):
    def __str__(self):
        return str(self.name).lower()


class ListNodeType(NodeType):
    CLASS_LIST = auto()
    FUNC_LIST = auto()
    INHER_LIST = auto()
    MEMBER_LIST = auto()
    PARAM_LIST = auto()  # Function definition
    DIM_LIST = auto()
    STAT_BLOCK = auto()
    VAR = auto()
    INDEX_LIST = auto()
    ARG_LIST = auto()  # Function call


class GroupNodeType(NodeType):
    PROG = auto()
    DATA_MEMBER = auto()
    F_CALL = auto()


class LeafNodeType(NodeType):
    EPSILON = auto()
    ID = auto()
    TYPE = auto()
    LITERAL = auto()
    REL_OP = auto()


class ASTNode:
    def __init__(self, node_type: NodeType, token: Token = None):
        self.node_type = node_type
        self.token = token
        self.children = []
        self.parent = None
        self.siblings = Siblings(leftmost=None, right=None)
