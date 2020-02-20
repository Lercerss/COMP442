import re

from collections import OrderedDict
from typing import List, Set

from lex import Token, TokenType
from .ast import ASTNode
from .sets import EPSILON

EXTENSION = re.compile(r"\.src$")

class Leaf:
    pass

class ParserOutput:
    def __init__(self, source_file: str):
        self.derivation_file = open(EXTENSION.sub(".outderivation", source_file), "w")
        self.derivation_variant_file = open(
            EXTENSION.sub(".outderivation.var", source_file), "w"
        )
        self.ast_file = open(EXTENSION.sub(".outast", source_file), "w")
        self.derivations = []  # Forest of derivation sub-trees

    def _format_rule(self, lhs, rhs):
        return "{lhs} -> {rhs}\n".format(
            lhs=lhs, rhs=" ".join(r if r != EPSILON else "EPSILON" for r in rhs)
        )

    def _pop(self, non_terminal):
        for i, (nt, sub_tree) in enumerate(self.derivations):
            if nt == non_terminal:
                self.derivations.pop(i)
                return sub_tree
        return Leaf

    def _add(self, lhs: str, rhs: List[str]):
        sub_tree = OrderedDict()
        for r in rhs:
            sub_tree[r] = self._pop(r)

        self.derivations.append((lhs, sub_tree))

    def add(self, lhs: str, rhs: List[str]):
        self._add(lhs, rhs)
        self.derivation_file.write(self._format_rule(lhs, rhs))

    def panic(self, expected: Set[TokenType], found: Token):
        print(
            "PANIC: Expected one of [{expected}] but found {found}".format(
                expected=",".join(str(e) for e in expected if e is not EPSILON), found=str(found),
            )
        )

    def resume(self, skipped, next_token):
        print(
            "PANIC: Skipped [{skipped}]".format(
                skipped=",".join(str(s) for s in skipped)
            )
        )
        print("PANIC: Resuming at {next_token}".format(next_token=next_token))

    def invalid_token(self, token):
        print(token)

    def _replace_derivation(self, current, lhs, rhs):
        i = current.index(lhs)
        return (
            current[:i]
            + [d for d in rhs if d is not EPSILON]
            + current[i + 1 :]
        )

    def derivation_variant(self):
        current = [self.derivations[-1][0]]
        trees = self.derivations
        while trees:
            lhs, rhs = trees.pop(0)
            if rhs is not Leaf:
                current = self._replace_derivation(current, lhs, rhs.keys())
                trees += list(rhs.items())

            self.derivation_variant_file.write(" ".join(current) + "\n")

    def ast(self, root: ASTNode, success: bool):
        if success:
            self.derivation_variant()
        self.ast_file.write(root.to_xml() + "\n")
