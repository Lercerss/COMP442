from collections import namedtuple
from enum import Enum, unique, auto
from typing import List

from lex import Token


@unique
class NodeType(Enum):
    def __str__(self):
        return str(self.name).lower()


class ListNodeType(NodeType):
    CLASS_LIST = auto()
    FUNC_LIST = auto()
    INHER_LIST = auto()
    MEMBER_LIST = auto()
    LOCAL_LIST = auto()
    PARAM_LIST = auto()  # Function definition
    DIM_LIST = auto()
    STAT_BLOCK = auto()
    VAR = auto()
    F_CALL_STAT = auto()
    INDEX_LIST = auto()
    ARG_LIST = auto()  # Function call


class GroupNodeType(NodeType):
    PROG = auto()
    MAIN = auto()
    CLASS_DECL = auto()
    FUNC_DECL = auto()
    FUNC_DEF = auto()
    MEMBER_DECL = auto()
    VAR_DECL = auto()
    FUNC_PARAM = auto()
    DATA_MEMBER = auto()
    F_CALL = auto()
    IF_STAT = auto()
    ASSIGN_STAT = auto()
    WHILE_STAT = auto()
    READ_STAT = auto()
    WRITE_STAT = auto()
    RETURN_STAT = auto()
    REL_EXPR = auto()
    ADD_EXPR = auto()
    MULT_EXPR = auto()
    NOT = auto()
    SIGN = auto()


class LeafNodeType(NodeType):
    EPSILON = auto()
    ID = auto()
    TYPE = auto()
    LITERAL = auto()
    VISIBILITY = auto()
    SCOPE_SPEC = auto()


class ASTNode:
    def __init__(self, node_type: NodeType, token: Token = None):
        self.node_type = node_type
        self.token = token
        self.children: List["ASTNode"] = []
        self.parent: "ASTNode" = None
        self.record: "sem.table.Record" = None
        self.temp_record: "sem.table.Record" = None
        self.code = []

    def make_child(self, node_type: NodeType, token: Token = None) -> "ASTNode":
        """Create a new node and adopt it"""
        node = ASTNode(node_type, token)
        self.adopt(node)
        return node

    def adopt(self, node: "ASTNode"):
        """Adopt an existing node"""
        self.children.append(node)
        node.parent = self

    def insert_commutative(self, node: "ASTNode"):
        """Insert a new node into an existing commutative operator tree"""
        top_children = self.children
        self.children = node.children
        node.children = top_children
        for c in top_children:
            c.parent = node

        top_attributes = self.node_type, self.token
        self.node_type, self.token = node.node_type, node.token
        node.node_type, node.token = top_attributes

        temp_node = node
        children = temp_node.children
        while temp_node.node_type == node.node_type and len(children) == 2:
            temp_node = temp_node.children[0]
            children = temp_node.children

        temp_node.children = [self] + children

    def absorb(self):
        """Self becomes its first child"""
        child = self.children[0]
        self.children, child.children = child.children, []
        self.node_type = child.node_type
        self.token = child.token
        child.parent = None

    def to_xml(self, indent=0) -> str:
        if self.children:
            return "{indent}<{node}{token}>\n{children}\n{indent}</{node}>".format(
                node=str(self.node_type),
                token=(' token="{}"'.format(str(self.token)) if self.token else ""),
                indent="  " * indent,
                children="\n".join(c.to_xml(indent + 1) for c in self.children),
            )
        return "  " * indent + "<{}/>".format(
            str(self.node_type)
            + (' token="{}"'.format(str(self.token)) if self.token else "")
        )

    def accept(self, visitor):
        """Allow the visitor to recursively walk the AST"""
        if (
            (
                self.node_type == GroupNodeType.FUNC_DEF
                or self.node_type == GroupNodeType.MAIN
            )
            and self.record
            and self.record.table
        ):
            visitor.scope = self.record.table
        for c in self.children:
            c.accept(visitor)
        visitor.visit(self)
