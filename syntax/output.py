import re

from typing import List, Set

from lex import Token, TokenType
from .ast import ASTNode
from .sets import EPSILON

EXTENSION = re.compile(r"\.src$")


class ParserOutput:
    def __init__(self, source_file: str):
        self.derivation_file = open(EXTENSION.sub(".outderivation", source_file), "w")
        self.ast_file = open(EXTENSION.sub(".outast", source_file), "w")

    def add(self, lhs: str, rhs: List[str]):
        self.derivation_file.write(
            "{lhs} -> {rhs}\n".format(
                lhs=lhs, rhs=" ".join(r if r != EPSILON else "EPSILON" for r in rhs)
            )
        )

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

    def ast(self, root: ASTNode):
        pass
