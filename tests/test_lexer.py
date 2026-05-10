"""
Tests for ZLang Lexer.

Covers: token types, operators, keywords, strings, numbers, comments, error handling.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zlang.lexer import Lexer, LexerError
from zlang.token import TokenType as T


class TestBasicTokens:
    def test_integer(self):
        tokens = Lexer("42\n").tokens
        assert tokens[0].type == T.INT
        assert tokens[0].value == 42

    def test_float(self):
        tokens = Lexer("3.14\n").tokens
        assert tokens[0].type == T.FLOAT
        assert tokens[0].value == 3.14

    def test_string_double(self):
        tokens = Lexer('"hello"\n').tokens
        assert tokens[0].type == T.STRING
        assert tokens[0].value == "hello"

    def test_string_single(self):
        tokens = Lexer("'world'\n").tokens
        assert tokens[0].type == T.STRING
        assert tokens[0].value == "world"

    def test_string_escape(self):
        tokens = Lexer(r'"line1\nline2"' + "\n").tokens
        assert tokens[0].type == T.STRING
        assert tokens[0].value == "line1\nline2"

    def test_bool_true(self):
        tokens = Lexer("true\n").tokens
        assert tokens[0].type == T.BOOL
        assert tokens[0].value is True

    def test_bool_false(self):
        tokens = Lexer("false\n").tokens
        assert tokens[0].type == T.BOOL
        assert tokens[0].value is False

    def test_identifier(self):
        tokens = Lexer("my_var\n").tokens
        assert tokens[0].type == T.IDENT
        assert tokens[0].value == "my_var"


class TestOperators:
    def test_arithmetic(self):
        src = "+ - * / %\n"
        tokens = Lexer(src).tokens
        types = [t.type for t in tokens if t.type != T.NEWLINE and t.type != T.EOF]
        assert types == [T.PLUS, T.MINUS, T.STAR, T.SLASH, T.PERCENT]

    def test_comparison(self):
        src = "== != < > <= >=\n"
        tokens = Lexer(src).tokens
        types = [t.type for t in tokens if t.type != T.NEWLINE and t.type != T.EOF]
        assert types == [T.EQ, T.NEQ, T.LT, T.GT, T.LTE, T.GTE]

    def test_logical(self):
        src = "&& || !\n"
        tokens = Lexer(src).tokens
        types = [t.type for t in tokens if t.type != T.NEWLINE and t.type != T.EOF]
        assert types == [T.AND, T.OR, T.NOT]

    def test_assignment(self):
        src = "= += -=\n"
        tokens = Lexer(src).tokens
        types = [t.type for t in tokens if t.type != T.NEWLINE and t.type != T.EOF]
        assert types == [T.ASSIGN, T.PLUS_ASSIGN, T.MINUS_ASSIGN]

    def test_arrow(self):
        tokens = Lexer("->\n").tokens
        assert tokens[0].type == T.ARROW


class TestKeywords:
    def test_keywords(self):
        src = "let fn if else for in while switch case default return struct import break continue\n"
        tokens = Lexer(src).tokens
        expected = [
            T.LET, T.FN, T.IF, T.ELSE, T.FOR, T.IN, T.WHILE,
            T.SWITCH, T.CASE, T.DEFAULT, T.RETURN, T.STRUCT,
            T.IMPORT, T.BREAK, T.CONTINUE
        ]
        types = [t.type for t in tokens if t.type != T.NEWLINE and t.type != T.EOF]
        assert types == expected


class TestDelimiters:
    def test_delimiters(self):
        src = "( ) { } [ ] , : ; .\n"
        tokens = Lexer(src).tokens
        expected = [
            T.LPAREN, T.RPAREN, T.LBRACE, T.RBRACE,
            T.LBRACKET, T.RBRACKET, T.COMMA, T.COLON,
            T.SEMICOLON, T.DOT
        ]
        types = [t.type for t in tokens if t.type != T.NEWLINE and t.type != T.EOF]
        assert types == expected


class TestComments:
    def test_line_comment(self):
        tokens = Lexer("42 // this is a comment\n").tokens
        assert tokens[0].value == 42

    def test_block_comment(self):
        tokens = Lexer("42 /* block */ 99\n").tokens
        vals = [t.value for t in tokens if t.type in (T.INT,)]
        assert vals == [42, 99]

    def test_comment_does_not_interfere(self):
        src = "let x = 1 // comment\nlet y = 2\n"
        tokens = Lexer(src).tokens
        ints = [t.value for t in tokens if t.type == T.INT]
        assert ints == [1, 2]


class TestErrors:
    def test_unexpected_char(self):
        with pytest.raises(LexerError):
            Lexer("@$\n")

    def test_unterminated_string(self):
        with pytest.raises(LexerError):
            Lexer('"unterminated\n')


class TestLineTracking:
    def test_line_numbers(self):
        src = "a\nb\nc\n"
        tokens = Lexer(src).tokens
        idents = [t for t in tokens if t.type == T.IDENT]
        assert idents[0].line == 1
        assert idents[1].line == 2
        assert idents[2].line == 3
