import re

from .token import Token, Errors, Generic

EXTENSION = re.compile(r"\.src$")


class TokenOutput:
    def __init__(self, source_file: str):
        self.out_file = open(EXTENSION.sub(".outlextokens", source_file), "w")
        self.error_file = open(EXTENSION.sub(".outlexerrors", source_file), "w")
        self.last_line = 1

    def write(self, token: Token):
        if isinstance(token.token_type, Errors):
            self._write_error(token)
        elif token.token_type is Generic.EOF:
            pass
        else:
            self._write_out(token)

    def _write_out(self, token: Token):
        if self.last_line < token.location.line:
            self.last_line = token.location.line
            self.out_file.write("\n")

        self.out_file.write(str(token) + " ")

    def _write_error(self, token: Errors):
        self.error_file.write(str(token) + "\n")
