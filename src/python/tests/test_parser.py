"""
Tests for ZLang Parser.

Covers: expressions, statements, declarations, error handling.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zlang.lexer import Lexer
from zlang.parser import Parser, ParseError
from zlang.ast import *


def _parse(source):
    tokens = Lexer(source + "\n").tokens
    return Parser(tokens).parse()


class TestExpressions:
    def test_int_literal(self):
        prog = _parse("42")
        stmt = prog.statements[0]
        assert isinstance(stmt, ExprStatement)
        assert isinstance(stmt.expr, IntLiteral)
        assert stmt.expr.value == 42

    def test_float_literal(self):
        prog = _parse("3.14")
        stmt = prog.statements[0]
        assert isinstance(stmt.expr, FloatLiteral)
        assert stmt.expr.value == 3.14

    def test_string_literal(self):
        prog = _parse('"hello"')
        stmt = prog.statements[0]
        assert isinstance(stmt.expr, StringLiteral)
        assert stmt.expr.value == "hello"

    def test_bool_literal(self):
        prog = _parse("true")
        stmt = prog.statements[0]
        assert isinstance(stmt.expr, BoolLiteral)
        assert stmt.expr.value is True

    def test_identifier(self):
        prog = _parse("x")
        stmt = prog.statements[0]
        assert isinstance(stmt.expr, Identifier)
        assert stmt.expr.name == "x"

    def test_binary_op(self):
        prog = _parse("1 + 2")
        expr = prog.statements[0].expr
        assert isinstance(expr, BinaryOp)
        assert expr.op == "+"

    def test_unary_minus(self):
        prog = _parse("-5")
        expr = prog.statements[0].expr
        assert isinstance(expr, UnaryOp)
        assert expr.op == "-"
        assert isinstance(expr.operand, IntLiteral)

    def test_unary_not(self):
        prog = _parse("!true")
        expr = prog.statements[0].expr
        assert isinstance(expr, UnaryOp)
        assert expr.op == "!"

    def test_parenthesized(self):
        prog = _parse("(1 + 2)")
        expr = prog.statements[0].expr
        assert isinstance(expr, BinaryOp)

    def test_operator_precedence(self):
        # 1 + 2 * 3  =>  1 + (2 * 3)
        prog = _parse("1 + 2 * 3")
        expr = prog.statements[0].expr
        assert isinstance(expr, BinaryOp)
        assert expr.op == "+"
        assert isinstance(expr.right, BinaryOp)
        assert expr.right.op == "*"

    def test_call_expr(self):
        prog = _parse("foo(1, 2)")
        expr = prog.statements[0].expr
        assert isinstance(expr, CallExpr)
        assert isinstance(expr.callee, Identifier)
        assert len(expr.args) == 2

    def test_member_access(self):
        prog = _parse("obj.field")
        expr = prog.statements[0].expr
        assert isinstance(expr, MemberAccess)
        assert expr.member == "field"

    def test_index_access(self):
        prog = _parse("arr[0]")
        expr = prog.statements[0].expr
        assert isinstance(expr, IndexAccess)

    def test_array_literal(self):
        prog = _parse("[1, 2, 3]")
        expr = prog.statements[0].expr
        assert isinstance(expr, ArrayLiteral)
        assert len(expr.elements) == 3

    def test_assignment(self):
        prog = _parse("x = 10")
        expr = prog.statements[0].expr
        assert isinstance(expr, Assignment)

    def test_compound_assignment(self):
        prog = _parse("x += 1")
        expr = prog.statements[0].expr
        assert isinstance(expr, CompoundAssignment)
        assert expr.op == "+="


class TestStatements:
    def test_let_statement(self):
        prog = _parse("let x = 42")
        stmt = prog.statements[0]
        assert isinstance(stmt, LetStatement)
        assert stmt.name == "x"
        assert isinstance(stmt.init, IntLiteral)

    def test_let_with_type(self):
        prog = _parse("let x: int = 42")
        stmt = prog.statements[0]
        assert isinstance(stmt, LetStatement)
        assert stmt.type_ann is not None
        assert stmt.type_ann.name == "int"

    def test_if_statement(self):
        src = "if x > 0 { print(x) }"
        prog = _parse(src)
        stmt = prog.statements[0]
        assert isinstance(stmt, IfStatement)
        assert isinstance(stmt.condition, BinaryOp)
        assert isinstance(stmt.then_block, Block)

    def test_if_else(self):
        src = "if true { 1 } else { 2 }"
        prog = _parse(src)
        stmt = prog.statements[0]
        assert isinstance(stmt, IfStatement)
        assert stmt.else_block is not None

    def test_for_in(self):
        src = "for item in items { print(item) }"
        prog = _parse(src)
        stmt = prog.statements[0]
        assert isinstance(stmt, ForInStatement)
        assert stmt.var_name == "item"

    def test_while(self):
        src = "while true { break }"
        prog = _parse(src)
        stmt = prog.statements[0]
        assert isinstance(stmt, WhileStatement)

    def test_switch(self):
        src = """switch x {
            case 1: print("one")
                break
            default: print("other")
                break
        }"""
        prog = _parse(src)
        stmt = prog.statements[0]
        assert isinstance(stmt, SwitchStatement)
        assert len(stmt.cases) == 2

    def test_return(self):
        prog = _parse("return 42")
        stmt = prog.statements[0]
        assert isinstance(stmt, ReturnStatement)
        assert isinstance(stmt.value, IntLiteral)

    def test_return_void(self):
        prog = _parse("return")
        stmt = prog.statements[0]
        assert isinstance(stmt, ReturnStatement)
        assert stmt.value is None

    def test_break(self):
        prog = _parse("break")
        assert isinstance(prog.statements[0], BreakStatement)

    def test_continue(self):
        prog = _parse("continue")
        assert isinstance(prog.statements[0], ContinueStatement)


class TestDeclarations:
    def test_func_decl(self):
        src = "fn add(a, b) { return a + b }"
        prog = _parse(src)
        decl = prog.statements[0]
        assert isinstance(decl, FuncDecl)
        assert decl.name == "add"
        assert len(decl.params) == 2

    def test_func_with_types(self):
        src = "fn add(a: int, b: int) -> int { return a + b }"
        prog = _parse(src)
        decl = prog.statements[0]
        assert decl.return_type is not None

    def test_struct_decl(self):
        src = """struct Point {
            x: float
            y: float
        }"""
        prog = _parse(src)
        decl = prog.statements[0]
        assert isinstance(decl, StructDecl)
        assert decl.name == "Point"
        assert len(decl.fields) == 2

    def test_import(self):
        prog = _parse("import std.math")
        decl = prog.statements[0]
        assert isinstance(decl, ImportDecl)
        assert decl.module_path == "std.math"


class TestParseErrors:
    def test_unexpected_token(self):
        with pytest.raises(ParseError):
            _parse("let = 10")

    def test_missing_brace(self):
        with pytest.raises(ParseError):
            _parse("if true { 1 ")
