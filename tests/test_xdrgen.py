from pyxdr.xdrgen import translate_xdr_to_python, lex, TranslationError
import pytest
from typing import Any


def lex_to_list(inp: str) -> list[tuple[str, Any]]:
    return [(tok.type, tok.value) for tok in lex(inp)]


def test_lex():
    assert lex_to_list("const MAXUSERNAME = -32;") == [
        ("CONST", "const"),
        ("ID", "MAXUSERNAME"),
        ("=", "="),
        ("NUMBER", -32),
        (";", ";"),
    ]


@pytest.mark.parametrize(
    "xdr,python",
    [
        ("const MAXUSERNAME = 32;", "MAXUSERNAME = 32"),
        (
            """
    enum filekind {
       TEXT = 0,       /* ascii data */
       DATA = 1,       /* raw data   */
       EXEC = 2        /* executable */
    };
    """,
            """\
class filekind(Enum):
    TEXT = 0
    DATA = 1
    EXEC = 2""",
        ),
        (
            """\
struct structname {
    int myint;
    unsigned int myunsigned;
};""",
            """\
class structname(Struct):
    myint: Int.hint
    myunsigned: UnsignedInt.hint""",
        ),
        (
            """\
struct child {
    int myint;
};
struct parent {
    child mychild;
};""",
            """\
class child(Struct):
    myint: Int.hint
class parent(Struct):
    mychild: child""",
        ),
    ],
)
def test_translate(xdr, python):
    assert translate_xdr_to_python(xdr) == python


def test_unknown_reference():
    with pytest.raises(TranslationError):
        translate_xdr_to_python("const A = MISSING;")


# TODO: test name collisions
