import io

from collections import namedtuple

from lex import Token as T
from lex.token import (
    Errors as E,
    Generic as G,
    Keywords as K,
    Literals as L,
    Operators as O,
    Symbols as S,
)

Fixture = namedtuple("Fixture", ["input", "expected"])


SAMPLE = Fixture(
    io.StringIO(
        """class MyClass inherits Other {
    // MyClass has some doc
    private float member1;
    public integer member2;

    public method(float test){
        float good = 12.345e-78
        float okay = 0.0
        return okay / good * test
    }
    /* I think this is good */
}
"""
    ),
    {
        1: [
            T(K.CLASS, "class", (0, 0)),
            T(G.ID, "MyClass", (0, 0)),
            T(K.INHERITS, "inherits", (0, 0)),
            T(G.ID, "Other", (0, 0)),
            T(S.OPEN_CBR, "{", (0, 0)),
        ],
        2: [T(G.INLINE_CMT, "// MyClass has some doc", (0, 0))],
        3: [
            T(K.PRIVATE, "private", (0, 0)),
            T(K.FLOAT, "float", (0, 0)),
            T(G.ID, "member1", (0, 0)),
            T(S.SEMI_COLON, ";", (0, 0)),
        ],
        4: [
            T(K.PUBLIC, "public", (0, 0)),
            T(K.INTEGER, "integer", (0, 0)),
            T(G.ID, "member2", (0, 0)),
            T(S.SEMI_COLON, ";", (0, 0)),
        ],
        # 5: [],
        6: [
            T(K.PUBLIC, "public", (0, 0)),
            T(G.ID, "method", (0, 0)),
            T(S.OPEN_PAR, "(", (0, 0)),
            T(K.FLOAT, "float", (0, 0)),
            T(G.ID, "test", (0, 0)),
            T(S.CLOSE_PAR, ")", (0, 0)),
            T(S.OPEN_CBR, "{", (0, 0)),
        ],
        7: [
            T(K.FLOAT, "float", (0, 0)),
            T(G.ID, "good", (0, 0)),
            T(S.ASSIGN, "=", (0, 0)),
            T(L.FLOAT_LITERAL, "12.345e-78", (0, 0)),
        ],
        8: [
            T(K.FLOAT, "float", (0, 0)),
            T(G.ID, "okay", (0, 0)),
            T(S.ASSIGN, "=", (0, 0)),
            T(L.FLOAT_LITERAL, "0.0", (0, 0)),
        ],
        9: [
            T(K.RETURN, "return", (0, 0)),
            T(G.ID, "okay", (0, 0)),
            T(O.DIV, "/", (0, 0)),
            T(G.ID, "good", (0, 0)),
            T(O.MULT, "*", (0, 0)),
            T(G.ID, "test", (0, 0)),
        ],
        10: [T(S.CLOSE_CBR, "}", (0, 0))],
        11: [T(G.BLOCK_CMT, "/* I think this is good */", (0, 0))],
        12: [T(S.CLOSE_CBR, "}", (0, 0)), T(G.EOF, "", (0, 0))],
    },
)

SINGLE_INLINE_CMT = Fixture(
    io.StringIO("// This is a single line and nothing else"),
    {
        1: [
            T(G.INLINE_CMT, "// This is a single line and nothing else", (0, 0)),
            T(G.EOF, "", (0, 0)),
        ]
    },
)
