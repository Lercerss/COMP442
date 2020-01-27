import re

from .token import Token, Errors

EXTENSION = re.compile(r".*\.\w+$")


class TokenOutput:
    def __init__(self, source_file: str):
        self.out_file = open(EXTENSION.replace(source_file, ".outlextokens"), "w")
        self.error_file = open(EXTENSION.replace(source_file, ".outlexerrors"), "w")
        self.last_line = 1

    def write(self, token: Token):
        if isinstance(token, Errors):
            self._write_error(token)

    def _write_out(self, token: Token):
        if self.last_line < token.location:
            self.last_line = token.location
            self.out_file.write("\n")

        self.out_file.write(str(token) + " ")

    def _write_error(self, token: Errors):
        self.error_file.write(str(token) + "\n")

