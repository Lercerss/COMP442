from enum import Enum, unique, auto


@unique
class TokenType(Enum):
    def __str__(self):
        return str(self.name).lower()


class Generic(TokenType):
    ID = auto()
    BLOCK_CMT = auto()
    INLINE_CMT = auto()


class Literals(TokenType):
    INTEGER_LITERAL = auto()
    FLOAT_LITERAL = auto()


class Keywords(TokenType):
    IF = auto()
    THEN = auto()
    ELSE = auto()
    WHILE = auto()
    DO = auto()
    END = auto()
    RETURN = auto()
    INTEGER = auto()
    FLOAT = auto()
    CLASS = auto()
    INHERITS = auto()
    PUBLIC = auto()
    PRIVATE = auto()
    LOCAL = auto()
    READ = auto()
    WRITE = auto()
    MAIN = auto()


class Operators(TokenType):
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    PLUS = auto()
    MINUS = auto()
    DIV = auto()
    MULT = auto()
    OR = auto()
    AND = auto()
    NOT = auto()


class Symbols(TokenType):
    OPEN_PAR = auto()
    CLOSE_PAR = auto()
    OPEN_CBR = auto()
    CLOSE_CBR = auto()
    OPEN_SBR = auto()
    CLOSE_SBR = auto()
    COLON = auto()
    DCOLON = auto()
    ASSIGN = auto()
    DOT = auto()
    COMMA = auto()
    SEMI_COLON = auto()


class Errors(TokenType):
    INVALID_NUMBER = auto()
    INVALID_CHARACTER = auto()
    INVALID_IDENTIFIER = auto()

    def __str__(self):
        return "Lexical error: " + str(self.name).replace("_", " ").lower().capitalize()


class Token:
    def __init__(self, token_type, lexeme, location):
        self.token_type = token_type
        self.lexeme = lexeme
        self.location = location

    def __str__(self):
        if isinstance(self.token_type, Errors):
            return '{token_type}: "{lexeme}": line {location}.'.format(**self.__dict__)
        return "[{token_type}, {lexeme}, {location}]".format(**self.__dict__)
