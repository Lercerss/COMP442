import re
from typing import Generator

from .token import Token, Generic, Symbols, Operators, Literals, Keywords, Errors

from .characters import (
    ALPHANUM,
    DIGIT,
    DUAL_SYMBOL,
    LETTER,
    NON_ZERO,
    SINGLE_SYMBOL,
    SYMBOL,
    WHITESPACE,
)


class CallableStateMachine:
    def __init__(self, scanner):
        self.scanner = scanner
        self.handler = self._default

    def _default(self, char):
        """Forward character to the scanner's error handler"""
        self.scanner.handler = self.scanner._handle_error
        self.scanner.handler(char)

    def __call__(self, char):
        self.handler(char)

    def transition(self, char, new_state):
        """Change state and handle the received character"""
        self.handler = new_state
        self.scanner.lexeme += char

    def repeat(self, char):
        """Handle received character and stay at current state"""
        self.scanner.lexeme += char

    def success(self, char=""):
        """Output a token"""
        self.scanner.tokenized = True
        self.scanner.backtrack = char

    def forward(self, char, state):
        """Change state without handling the received character"""
        self.handler = state
        self.handler(char)


class NumericalHandler(CallableStateMachine):
    r"""Handles the following state transitions:
    numerical -> (integer) -> point -> (valid-float) <--> float
          \->  (zero)  ---/                  \-> exponent  ->  (e-zero)
                                                  |  \- signed -/
                                                   \-----> \-> (digit)
    """
    # TODO "100. ", "100.id", "100.0.0"

    def __init__(self, scanner):
        super().__init__(scanner)
        self.handler = self._handle_numerical

    def _handle_error(self, char):
        """Trap state, captures characters until whitespace or symbol"""
        self.scanner.token_type = Errors.INVALID_NUMBER
        if char in ALPHANUM:
            self.scanner.lexeme += char
        else:
            self.success(char)

    def _handle_numerical(self, char):
        """Initial state"""
        self.scanner.token_type = Literals.INTEGER_LITERAL

        if char == "0":
            self.transition(char, self._handle_zero)
        elif char in NON_ZERO:
            self.transition(char, self._handle_integer)
        else:
            self.scanner.token_type = None
            self._default(char)  # Invalid character

    def _handle_zero(self, char):
        if char == ".":
            self.transition(char, self._handle_point)
        elif char in DIGIT:
            self.transition(char, self._handle_error)
        else:
            self.success(char)

    def _handle_integer(self, char):
        if char == ".":
            self.transition(char, self._handle_point)
        elif char in DIGIT:
            self.repeat(char)
        else:
            self.success(char)

    def _handle_point(self, char):
        if char in DIGIT:
            self.transition(char, self._handle_valid_float)
            self.scanner.token_type = Literals.FLOAT_LITERAL
        else:
            self.forward(char, self._handle_error)

    def _handle_valid_float(self, char):

        if char == "e":
            self.transition(char, self._handle_exponent)
        elif char == "0":
            self.transition(char, self._handle_float)
        elif char in NON_ZERO:
            self.repeat(char)
        else:
            self.success(char)

    def _handle_float(self, char):
        if char == "0":
            self.repeat(char)
        elif char in NON_ZERO:
            self.transition(char, self._handle_valid_float)
        else:
            self.forward(char, self._handle_error)

    def _handle_exponent(self, char):
        if char in ("+", "-"):
            self.transition(char, self._handle_signed)
        elif char in NON_ZERO:
            self.transition(char, self._handle_digit)
        elif char == "0":
            self.transition(char, self._handle_e_zero)
        else:
            self.forward(char, self._handle_error)

    def _handle_signed(self, char):
        if char in NON_ZERO:
            self.transition(char, self._handle_digit)
        elif char == "0":
            self.transition(char, self._handle_e_zero)
        else:
            self.forward(char, self._handle_error)

    def _handle_digit(self, char):
        if char in DIGIT:
            self.repeat(char)
        else:
            self.success(char)

    def _handle_e_zero(self, char):
        if char in DIGIT:
            self.transition(char, self._handle_error)
        else:
            self.success(char)


class SymbolHandler(CallableStateMachine):
    r"""Handles the following state transitions:
    (first-symbol) -> (dual-symbol) -> block-comment <--> (star)
                                \-> (inline-comment)
    """

    SYMBOL_TYPES = {
        # Single-character symbols
        "+": Operators.PLUS,
        "-": Operators.MINUS,
        "*": Operators.MULT,
        ";": Symbols.SEMI_COLON,
        ".": Symbols.DOT,
        ",": Symbols.COMMA,
        "(": Symbols.OPEN_PAR,
        ")": Symbols.CLOSE_PAR,
        "{": Symbols.OPEN_CBR,
        "}": Symbols.CLOSE_CBR,
        "[": Symbols.OPEN_SBR,
        "]": Symbols.CLOSE_SBR,
        # 2-character symbols
        "=": {"=": Operators.EQ, "": Symbols.ASSIGN,},
        "<": {">": Operators.NEQ, "=": Operators.LTE, "": Operators.LT,},
        ">": {"=": Operators.GTE, "": Operators.GT,},
        ":": {":": Symbols.DCOLON, "": Symbols.COLON,},
        "/": {"/": Generic.INLINE_CMT, "*": Generic.BLOCK_CMT, "": Operators.DIV,},
    }

    def __init__(self, scanner):
        super().__init__(scanner)
        self.handler = self._handle_first_symbol
        self.symbol_types = self.SYMBOL_TYPES

    def _handle_first_symbol(self, char):
        if char in SINGLE_SYMBOL:
            self.scanner.token_type = self.SYMBOL_TYPES[char]
            self.scanner.lexeme += char
            self.success()
        elif char in DUAL_SYMBOL:
            self.symbol_types = self.SYMBOL_TYPES[char]
            self.transition(char, self._handle_dual_symbol)
        else:
            self._default(char)  # Invalid character

    def _handle_dual_symbol(self, char):
        if char in self.symbol_types:
            self.scanner.token_type = self.symbol_types[char]

            if self.scanner.token_type is Generic.INLINE_CMT:
                self.transition(char, self._handle_inline_comment)
            elif self.scanner.token_type is Generic.BLOCK_CMT:
                self.transition(char, self._handle_block_comment)
            else:
                self.scanner.lexeme += char
                self.success()
        else:
            self.scanner.token_type = self.symbol_types[""]
            self.success(char)

    def _handle_inline_comment(self, char):
        if char == "\n":
            self.success(char)
        else:
            self.repeat(char)

    def _handle_block_comment(self, char):
        if char == "*":
            self.transition(char, self._handle_block_star)
        else:
            if char == "\n":
                self.scanner.line_no += 1
            self.repeat(char)

    def _handle_block_star(self, char):
        if char == "/":
            self.scanner.lexeme += char
            self.success()
        elif char == "*":
            self.repeat(char)
        else:
            if char == "\n":
                self.scanner.line_no += 1
            self.transition(char, self._handle_block_comment)


class WordHandler(CallableStateMachine):

    KEYWORDS = {
        word.name.lower(): word
        for word in list(Keywords) + [Operators.OR, Operators.AND, Operators.NOT]
    }

    def __init__(self, scanner):
        super().__init__(scanner)
        self.handler = self._handle_first_letter

    def _handle_first_letter(self, char):
        if char in LETTER:
            self.transition(char, self._handle_identifier)
        elif char in ALPHANUM:
            self.scanner.handler = self.scanner._handle_error
            self.scanner.token_type = Errors.INVALID_IDENTIFIER
            self.scanner.lexeme += char
        else:
            self._default(char)  # Invalid character

    def _handle_identifier(self, char):
        if char in ALPHANUM:
            self.repeat(char)
        else:
            self.success(char)

    def success(self, char=""):
        super().success(char)
        self.scanner.token_type = self.KEYWORDS.get(self.scanner.lexeme, Generic.ID)


class Scanner:
    """Iterable scanner that yields tokens found in source"""

    def __init__(self, source):
        assert source.readable()
        self.source = source
        self.line_no = 1
        self.token_line_no = 1
        self.handler = self._handle_empty
        self.lexeme = ""
        self.tokenized = False
        self.token_type = None
        self.backtrack = ""

    def _handle_empty(self, char):
        """Default case when lexeme is empty"""
        if char in WHITESPACE:
            if char == "\n":
                self.line_no += 1
            return

        self.token_line_no = self.line_no
        if char in DIGIT:
            self.handler = NumericalHandler(self)
        elif char in ALPHANUM:
            self.handler = WordHandler(self)
        elif char in SYMBOL:
            self.handler = SymbolHandler(self)
        else:
            self.handler = self._handle_error
        self.handler(char)  # Forward

    def _handle_error(self, char):
        if self.token_type:
            if char in ALPHANUM:
                self.lexeme += char
            else:
                self.tokenized = True
                self.backtrack = char
        elif char in ALPHANUM:
            self.lexeme += char
            self.token_type = Errors.INVALID_IDENTIFIER
        else:
            self.tokenized = True
            self.token_type = Errors.INVALID_CHARACTER

    def _handle(self, char):
        if char is None:
            self.tokenized = True
            self.token_type = Generic.EOF
            return

        self.handler(char)

    def _reset(self):
        self.handler = self._handle_empty
        self.lexeme = ""
        self.tokenized = False
        self.token_type = None

    def __iter__(self) -> Generator[Token, None, None]:
        src = self.source.read()
        if not src:
            return
        char_generator = iter(src)

        while self.token_type is not Generic.EOF:
            self._reset()
            if self.backtrack:
                char = self.backtrack
                self.backtrack = ""
                self._handle(char)

            while not self.tokenized:
                self._handle(next(char_generator, None))

            yield Token(self.token_type, self.lexeme, self.token_line_no)
