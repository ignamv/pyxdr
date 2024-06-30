import ply.lex
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

reserved = {"const", "enum", "struct", "unsigned", "int"}
tokens = ["ID", "NUMBER"] + [r.upper() for r in reserved]
literals = list(";={},")

t_ignore = " \t"


@dataclass
class Token:
    type: str
    value: Any
    line: int
    column: int


@dataclass
class LocalizedException(Exception):
    line: int
    column: int
    msg: str


class LexError(LocalizedException):
    pass


class TranslationError(LocalizedException):
    pass


def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    t.lexer.last_newline = t.lexpos + len(t.value)


def t_COMMENT(t):
    r"/\*(.|\n)*?\*/"
    pass


def t_error(t):
    raise LexError(t)


def t_ID(t):
    r"[a-zA-Z_][a-zA-Z_0-9]*"
    if t.value in reserved:
        t.type = t.value.upper()
    else:
        t.type = "ID"
    return t


def t_NUMBER(t):
    r"-?\d+"
    t.value = int(t.value)
    return t


lexer = ply.lex.lex()


def lex(inp: str) -> Iterable[Token]:
    lexer.lineno = 1
    lexer.last_newline = 0
    lexer.input(inp)
    while True:
        rawtok = lexer.token()
        if not rawtok:
            break
        yield Token(
            type=rawtok.type,
            value=rawtok.value,
            line=lexer.lineno,
            column=lexer.lexpos - lexer.last_newline,
        )


class Translator:
    def __init__(self, tokens):
        self.constants = set()
        self.tokens = iter(tokens)
        self.token = None
        self.readtok()

    def readtok(self) -> ply.lex.LexToken:
        ret = self.token
        try:
            self.token = next(self.tokens)
        except StopIteration:
            self.token = None
        return ret

    def error(self, msg, tok=None):
        if tok is None:
            tok = self.token
        if tok is None:
            raise TranslationError(msg=msg, line=-1, column=-1)
        else:
            raise TranslationError(msg=msg, line=tok.line, column=tok.column)

    def expect(self, *types) -> ply.lex.LexToken:
        assert all(
            t in tokens or t in literals for t in types
        ), f"Invalid tokens {types}"
        actual = "EOF" if self.token is None else self.token.type
        if self.token is None or self.token.type not in types:
            self.error(f"Expected {types} but got {actual}")
        return self.readtok()

    def translate_toplevel(self):
        ret = []
        while self.token is not None:
            translate = {
                "CONST": self.translate_const,
                "ENUM": self.translate_enum,
                "STRUCT": self.translate_struct,
            }[self.token.type]
            ret.append(translate())
        return "\n".join(ret)

    def translate_value(self):
        value = self.expect("NUMBER", "ID")
        if value.type == "ID":
            if value.value not in self.constants:
                self.error(f"Reference to unknown constant {value.value}", tok=value)
        return value.value

    def translate_const(self):
        self.expect("CONST")
        name = self.expect("ID").value
        self.expect("=")
        value = self.translate_value()
        self.expect(";")
        return f"{name} = {value}"

    def translate_enum(self):
        self.expect("ENUM")
        enumname = self.expect("ID").value
        self.expect("{")
        lines = [f"class {enumname}(Enum):"]
        while True:
            membername = self.expect("ID").value
            self.expect("=")
            membervalue = self.translate_value()
            lines.append(f"    {membername} = {membervalue}")
            if self.expect("}", ",").type == "}":
                break
        self.expect(";")
        return "\n".join(lines)

    def translate_struct(self):
        self.expect("STRUCT")
        structname = self.expect("ID")
        ret = self.translate_struct_body(structname.value)
        self.expect(";")
        return ret

    def translate_struct_body(self, name):
        lines = [f"class {name}(Struct):"]
        self.expect("{")
        while True:
            type_, name = self.parse_declaration()
            lines.append(f"    {name}: {type_}")
            self.expect(";")
            if self.token.type == "}":
                break
        self.expect("}")
        return "\n".join(lines)

    def parse_declaration(self):
        if self.token.type == "ID":
            type_ = self.readtok().value
        else:
            if self.token.type == "UNSIGNED":
                unsigned = True
                self.readtok()
            else:
                unsigned = False
            self.expect("INT")
            if unsigned:
                type_ = "UnsignedInt.hint"
            else:
                type_ = "Int.hint"
        name = self.expect("ID").value
        return type_, name


def translate_xdr_to_python(xdrcode: str) -> str:
    return Translator(lex(xdrcode)).translate_toplevel()
