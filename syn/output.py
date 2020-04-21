import re

from collections import OrderedDict
from typing import List, Set

from lex import Token, TokenType
from .ast import ASTNode
from .sets import EPSILON
from .parser import ErrorHandler, ProductionHandler

EXTENSION = re.compile(r"\.src$")


class Leaf:
    pass


class ParserOutput(ErrorHandler, ProductionHandler):
    def __init__(self, source_file: str):
        super().__init__(source_file)
        self.__derivation_file = open(EXTENSION.sub(".outderivation", source_file), "w")
        self.__derivation_variant_file = open(
            EXTENSION.sub(".outderivation.var", source_file), "w"
        )
        self.__ast_file = open(EXTENSION.sub(".outast", source_file), "w")
        self.__errors_file = open(EXTENSION.sub(".outsyntaxerrors", source_file), "w")
        self.__derivations = []  # Forest of derivation sub-trees
        self.__failed = False

    def __format_rule(self, lhs, rhs):
        return "{lhs} -> {rhs}\n".format(
            lhs=lhs, rhs=" ".join(r if r != EPSILON else "EPSILON" for r in rhs)
        )

    def __pop(self, non_terminal):
        for i, (nt, sub_tree) in enumerate(self.__derivations):
            if nt == non_terminal:
                self.__derivations.pop(i)
                return sub_tree
        return Leaf

    def __add(self, lhs: str, rhs: List[str]):
        sub_tree = OrderedDict()
        for r in rhs:
            sub_tree[r] = self.__pop(r)

        self.__derivations.append((lhs, sub_tree))

    def add(self, lhs: str, rhs: List[str]):
        self.__add(lhs, rhs)
        self.__derivation_file.write(self.__format_rule(lhs, rhs))

    def panic(self, expected: Set[TokenType], found: Token):
        self.__errors_file.write(
            "PANIC: Expected one of [{expected}] but found {found}\n".format(
                expected=",".join(str(e) for e in expected if e is not EPSILON),
                found=str(found),
            )
        )
        self.__failed = True

    def resume(self, skipped, next_token):
        self.__errors_file.write(
            "PANIC: Skipped [{skipped}]\n".format(
                skipped=",".join(str(s) for s in skipped)
            )
        )
        self.__errors_file.write(
            "PANIC: Resuming at {next_token}\n".format(next_token=next_token)
        )
        self.__failed = True

    def __replace_derivation(self, current, lhs, rhs):
        i = current.index(lhs)
        return current[:i] + [d for d in rhs if d is not EPSILON] + current[i + 1 :]

    def __derivation_variant(self):
        current = [self.__derivations[-1][0]]
        trees = self.__derivations
        while trees:
            lhs, rhs = trees.pop(0)
            if rhs is not Leaf:
                current = self.__replace_derivation(current, lhs, rhs.keys())
                trees += list(rhs.items())

            self.__derivation_variant_file.write(" ".join(current) + "\n")

    def ast(self, root: ASTNode):
        if not self.__failed:
            self.__derivation_variant()
        self.__ast_file.write(root.to_xml() + "\n")

    def did_fail(self):
        return self.__failed

    def collect_files(self):
        files = [
            self.__errors_file.name,
            self.__ast_file.name,
            self.__derivation_file.name,
        ]
        if not self.__failed:
            files.append(self.__derivation_variant_file.name)

        return files
