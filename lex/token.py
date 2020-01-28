from enum import Enum, unique, auto


@unique
class TokenType(Enum):
    def __str__(self):
        return str(self.name).lower()


class Generic(TokenType):
    ID = auto()
    BLOCK_CMT = auto()
    INLINE_CMT = auto()
    EOF = auto()


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
    ESCAPING = str.maketrans({"\n": r"\n", "\t": r"\t", "\r": r"\r",})

    def __init__(self, token_type: TokenType, lexeme: str, location: int):
        self.token_type = token_type
        self.lexeme = lexeme
        self.location = location

    def __str__(self):
        format_str = "[{token_type}, {lexeme}, {location}]"
        if isinstance(self.token_type, Errors):
            format_str = '{token_type}: "{lexeme}": line {location}.'

        return format_str.format(
            lexeme=self.lexeme.translate(self.ESCAPING),
            token_type=self.token_type,
            location=self.location,
        )

    def __eq__(self, other):
        return (
            isinstance(other, Token)
            and self.token_type == other.token_type
            and self.lexeme == other.lexeme
        )

    def __repr__(self):
        return "Token({token_type}, {lexeme}, {location})".format(
            token_type=Enum.__str__(self.token_type),  # Bypass overriden __str__
            lexeme=repr(self.lexeme),
            location=self.location,
        )
