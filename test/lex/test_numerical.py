import io
from unittest import TestCase

from lex.token import Token, Literals, Errors, Generic, Operators, Symbols
from lex.scanner import Scanner, NumericalHandler


class NumericalTestCase(TestCase):
    def _make_scanner(self, input_):
        return Scanner(io.StringIO(input_ + "\n"))

    def _one_token(self, input_, token_type):
        scanner = self._make_scanner(input_)
        it = iter(scanner)
        token = next(it, None)

        self.assertEqual(token, Token(token_type, input_, (0, 0)))
        self.assertEqual(next(it), Token(Generic.EOF, "", (0, 0)))

    def _many_tokens(self, inputs, types):
        scanner = self._make_scanner("".join(inputs))
        it = iter(scanner)

        for i, type_ in enumerate(types):
            self.assertEqual(
                next(it, None),
                Token(type_, inputs[i].strip(), (0, 0)),
                "Token {} does not match".format(i),
            )

        self.assertEqual(next(it), Token(Generic.EOF, "", (0, 0)))

    def test_integer(self):
        self._one_token("12345", Literals.INTEGER_LITERAL)

    def test_float(self):
        self._one_token("12.34", Literals.FLOAT_LITERAL)
        self._one_token("0.123", Literals.FLOAT_LITERAL)
        self._one_token("12.34e2", Literals.FLOAT_LITERAL)
        self._one_token("12.34e-2", Literals.FLOAT_LITERAL)
        self._one_token("124124124.34123123123e-1223452", Literals.FLOAT_LITERAL)
        self._one_token("12.34e+2", Literals.FLOAT_LITERAL)
        self._one_token("0.1234e+2", Literals.FLOAT_LITERAL)
        self._one_token("0.1234e-2", Literals.FLOAT_LITERAL)

    def test_zeroes(self):
        self._one_token("0", Literals.INTEGER_LITERAL)
        self._one_token("0.0", Literals.FLOAT_LITERAL)
        self._one_token("0.0e0", Literals.FLOAT_LITERAL)
        self._one_token("0.01e10", Literals.FLOAT_LITERAL)
        self._one_token("0.001e-0", Literals.FLOAT_LITERAL)
        self._one_token("0.0001e+0", Literals.FLOAT_LITERAL)

    def test_bad_integer(self):
        self._one_token("00", Errors.INVALID_NUMBER)
        self._one_token("01", Errors.INVALID_NUMBER)
        self._one_token("012345", Errors.INVALID_NUMBER)
        self._one_token("01e", Errors.INVALID_NUMBER)
        self._one_token("01", Errors.INVALID_NUMBER)

    def test_bad_float(self):
        self._one_token("1.", Errors.INVALID_NUMBER)
        self._one_token("01.", Errors.INVALID_NUMBER)
        self._one_token("0.10", Errors.INVALID_NUMBER)
        self._one_token("0.10e", Errors.INVALID_NUMBER)
        self._one_token("0.1e01", Errors.INVALID_NUMBER)
        self._one_token("0.1e+01", Errors.INVALID_NUMBER)
        self._one_token("0.1e-01", Errors.INVALID_NUMBER)
        self._one_token("111.123ee12", Errors.INVALID_NUMBER)
        self._one_token("111.123ee", Errors.INVALID_NUMBER)
        self._one_token("0.0ee", Errors.INVALID_NUMBER)
        self._one_token("0.0a", Errors.INVALID_NUMBER)
        self._one_token("01a", Errors.INVALID_NUMBER)
        self._one_token("1ae", Errors.INVALID_NUMBER)
        self._one_token("0ae", Errors.INVALID_NUMBER)
        self._one_token("1aee", Errors.INVALID_NUMBER)
        self._one_token("0.0e.01", Errors.INVALID_NUMBER)

    def test_bad_identifier(self):
        self._one_token("1abc", Errors.INVALID_IDENTIFIER)
        self._one_token("1_abc", Errors.INVALID_IDENTIFIER)
        self._one_token("1aea", Errors.INVALID_IDENTIFIER)
        self._one_token("0aea", Errors.INVALID_IDENTIFIER)
        self._one_token("0.0aa", Errors.INVALID_IDENTIFIER)
        self._one_token("100a.id", Errors.INVALID_IDENTIFIER)

    def test_bad_with_symbol(self):
        self._many_tokens(
            ["0.10e", "-", "01"],  # 0.10e-01
            [Errors.INVALID_NUMBER, Operators.MINUS, Errors.INVALID_NUMBER],
        )
        self._many_tokens(
            ["0.10e", "+", "01"],  # 0.10e+01
            [Errors.INVALID_NUMBER, Operators.PLUS, Errors.INVALID_NUMBER],
        )
        self._many_tokens(
            ["0.0e1", ".", "1"],  # 0.0e1.1
            [Literals.FLOAT_LITERAL, Symbols.DOT, Literals.INTEGER_LITERAL],
        )
        self._many_tokens(
            ["100. "], [Errors.INVALID_NUMBER],  # 100.
        )
        self._many_tokens(
            ["100.0", ".", "0"],  # 100.0.0
            [Literals.FLOAT_LITERAL, Symbols.DOT, Literals.INTEGER_LITERAL],
        )
        self._many_tokens(
            ["100", ".", "id"],  # 100.id
            [Literals.INTEGER_LITERAL, Symbols.DOT, Generic.ID],
        )
