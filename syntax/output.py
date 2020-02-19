import re

from collections import defaultdict, namedtuple
from typing import List, Set

from lex import Token, TokenType
from .ast import ASTNode
from .sets import EPSILON

EXTENSION = re.compile(r"\.src$")

Derivation = namedtuple("Derivation", ["lhs", "rhs"])


class ParserOutput:
    def __init__(self, source_file: str):
        self.derivation_file = open(EXTENSION.sub(".outderivation", source_file), "w")
        self.derivation_variant_file = open(
            EXTENSION.sub(".outderivation.var", source_file), "w"
        )
        self.ast_file = open(EXTENSION.sub(".outast", source_file), "w")
        self.derivations = []

    def _format_rule(self, lhs, rhs):
        return "{lhs} -> {rhs}\n".format(
            lhs=lhs, rhs=" ".join(r if r != EPSILON else "EPSILON" for r in rhs)
        )

    def add(self, lhs: str, rhs: List[str]):
        self.derivations.append(Derivation(lhs, rhs))
        self.derivation_file.write(self._format_rule(lhs, rhs))

    def panic(self, expected: Set[TokenType], found: Token):
        print(
            "PANIC: Expected one of [{expected}] but found {found}".format(
                expected=",".join(str(e) for e in expected), found=str(found),
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

    def _replace_derivation(self, current, derivation):
        i = current.index(derivation.lhs)
        return (
            current[:i]
            + [d for d in derivation.rhs if d is not EPSILON]
            + current[i + 1 :]
        )

    def _next_derivation(self, current):
        for i in range(len(self.derivations)):
            if self.derivations[i].lhs in current:
                return self.derivations.pop(i)
        return None

    def derivation_variant(self):
        current = ["prog"]
        self.derivation_variant_file.write("prog\n")
        while self.derivations:
            derivation = self._next_derivation(current)
            if not derivation:
                break

            current = self._replace_derivation(current, derivation)
            self.derivation_variant_file.write(" ".join(current) + "\n")
        self.derivation_variant_file.write("\n")

    def ast(self, root: ASTNode):
        self.derivation_variant()
        self.ast_file.write(root.to_xml() + "\n")
