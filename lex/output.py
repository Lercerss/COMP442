import re

from .token import Token, Errors, Generic

EXTENSION = re.compile(r"\.src$")


class TokenOutput:
    def __init__(self, source_file: str):
        super().__init__(source_file)
        self.__tokens_file = open(EXTENSION.sub(".outlextokens", source_file), "w")
        self.__errors_file = open(EXTENSION.sub(".outlexerrors", source_file), "w")
        self.__errors = []
        self.__last_line = 1

    def token(self, token: Token):
        if isinstance(token.token_type, Errors):
            self.__write_error(token)
        elif token.token_type is Generic.EOF:
            pass
        else:
            self.__write_out(token)

    def __write_out(self, token: Token):
        if self.__last_line < token.location.line:
            self.__last_line = token.location.line
            self.__tokens_file.write("\n")

        self.__tokens_file.write(str(token) + " ")

    def __write_error(self, token: Token):
        error_str = str(token) + "\n"
        self.__errors.append((token.location, error_str))

        self.__errors_file.write(error_str)

    def did_fail(self):
        return len(self.__errors) > 0

    def collect_files(self):
        return [self.__errors_file.name, self.__tokens_file.name]

    def list_errors(self):
        return self.__errors
