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
            T(K.CLASS, "class", 1),
            T(G.ID, "MyClass", 1),
            T(K.INHERITS, "inherits", 1),
            T(G.ID, "Other", 1),
            T(S.OPEN_CBR, "{", 1),
        ],
        2: [T(G.INLINE_CMT, "// MyClass has some doc", 2)],
        3: [
            T(K.PRIVATE, "private", 3),
            T(K.FLOAT, "float", 3),
            T(G.ID, "member1", 3),
            T(S.SEMI_COLON, ";", 3),
        ],
        4: [
            T(K.PUBLIC, "public", 4),
            T(K.INTEGER, "integer", 4),
            T(G.ID, "member2", 4),
            T(S.SEMI_COLON, ";", 4),
        ],
        # 5: []
        6: [
            T(K.PUBLIC, "public", 6),
            T(G.ID, "method", 6),
            T(S.OPEN_PAR, "(", 6),
            T(K.FLOAT, "float", 6),
            T(G.ID, "test", 6),
            T(S.CLOSE_PAR, ")", 6),
            T(S.OPEN_CBR, "{", 6),
        ],
        7: [
            T(K.FLOAT, "float", 7),
            T(G.ID, "good", 7),
            T(S.ASSIGN, "=", 7),
            T(L.FLOAT_LITERAL, "12.345e-78", 7),
        ],
        8: [
            T(K.FLOAT, "float", 8),
            T(G.ID, "okay", 8),
            T(S.ASSIGN, "=", 8),
            T(L.FLOAT_LITERAL, "0.0", 8),
        ],
        9: [
            T(K.RETURN, "return", 9),
            T(G.ID, "okay", 9),
            T(O.DIV, "/", 9),
            T(G.ID, "good", 9),
            T(O.MULT, "*", 9),
            T(G.ID, "test", 9),
        ],
        10: [T(S.CLOSE_CBR, "}", 10)],
        11: [T(G.BLOCK_CMT, "/* I think this is good */", 11)],
        12: [T(S.CLOSE_CBR, "}", 12), T(G.EOF, "", 12)],
    },
)
