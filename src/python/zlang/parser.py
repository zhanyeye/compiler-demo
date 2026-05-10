"""
ZLang 语法分析器（Parser）。

递归下降解析器，将 Token 流转换为 AST（抽象语法树）。

文法概览：
    program        = (statement | import_decl)* EOF
    statement      = let_stmt | func_decl | struct_decl | if_stmt
                   | for_stmt | while_stmt | switch_stmt | return_stmt
                   | break_stmt | continue_stmt | expr_stmt
    expr           = assignment
    assignment     = logic_or ('=' assignment | '+=' assignment | '-=' assignment)?
    logic_or       = logic_and ('||' logic_and)*
    logic_and      = equality ('&&' equality)*
    equality       = comparison (('==' | '!=') comparison)*
    comparison     = addition (('<' | '>' | '<=' | '>=') addition)*
    addition       = multiplication (('+' | '-') multiplication)*
    multiplication = unary (('*' | '/' | '%') unary)*
    unary          = ('!' | '-') unary | postfix
    postfix        = primary ('(' args ')' | '.' ident | '[' expr ']')*
    primary        = INT | FLOAT | STRING | BOOL | ident | '(' expr ')'
                   | '[' elements ']' | fn '(' params ')' block
"""

from zlang.token import TokenType as T
from zlang.ast import *
from zlang.lexer import Lexer


class ParseError(Exception):
    """语法分析错误，包含 Token 位置信息。"""

    def __init__(self, message, token):
        super().__init__(f"Parse error at line {token.line}: {message} (got {token.type.name} {token.value!r})")
        self.token = token


class Parser:
    """
    递归下降语法分析器。

    用法:
        program = Parser(tokens, "my_file.zl").parse()
    """

    def __init__(self, tokens, filename="<stdin>"):
        """
        初始化解析器。

        参数:
            tokens:   Lexer 生成的 Token 列表
            filename: 文件名（用于错误提示）
        """
        self.tokens = tokens
        self.pos = 0
        self.filename = filename

    # ---- 辅助方法 ----

    def _peek(self):
        """查看当前 Token，不移动指针。"""
        return self.tokens[self.pos]

    def _advance(self):
        """前进一个 Token，返回被消费的 Token。"""
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, ttype):
        """期望当前 Token 为指定类型，匹配则前进，否则抛出错误。"""
        tok = self._peek()
        if tok.type != ttype:
            raise ParseError(f"Expected {ttype.name}", tok)
        return self._advance()

    def _match(self, *ttypes):
        """如果当前 Token 类型在给定列表中则前进，返回匹配到的 Token 或 None。"""
        if self._peek().type in ttypes:
            return self._advance()
        return None

    def _skip_newlines(self):
        """跳过连续的换行 Token。"""
        while self._peek().type == T.NEWLINE:
            self._advance()

    def _expect_end(self):
        """消费语句结束符（换行、分号、右花括号或 EOF）。"""
        tok = self._peek()
        if tok.type in (T.NEWLINE, T.SEMICOLON, T.EOF, T.RBRACE):
            if tok.type in (T.NEWLINE, T.SEMICOLON):
                self._advance()
            return
        raise ParseError("Expected end of statement", tok)

    # ---- 程序 ----

    def parse(self):
        """解析整个程序，返回 Program AST 节点。"""
        stmts = []
        self._skip_newlines()
        while self._peek().type != T.EOF:
            stmts.append(self._top_level())
            self._skip_newlines()
        return Program(stmts, self.filename)

    def _top_level(self):
        """解析顶层声明（import、函数、结构体）或普通语句。"""
        if self._peek().type == T.IMPORT:
            return self._import_decl()
        if self._peek().type == T.FN:
            return self._func_decl()
        if self._peek().type == T.STRUCT:
            return self._struct_decl()
        return self._statement()

    # ---- 声明 ----

    def _import_decl(self):
        """解析 import 声明，如 import std.math。"""
        self._expect(T.IMPORT)
        path_parts = []
        path_parts.append(self._expect(T.IDENT).value)
        while self._match(T.DOT):
            path_parts.append(self._expect(T.IDENT).value)
        self._expect_end()
        return ImportDecl(".".join(path_parts))

    def _func_decl(self):
        """解析函数声明，如 fn add(a: int, b: int) -> int { ... }。"""
        self._expect(T.FN)
        name = self._expect(T.IDENT).value
        self._expect(T.LPAREN)
        params = self._param_list()
        self._expect(T.RPAREN)
        ret_type = None
        if self._match(T.ARROW):
            ret_type = self._type_expr()
        self._skip_newlines()
        body = self._block()
        return FuncDecl(name, params, ret_type, body)

    def _param_list(self):
        """解析函数参数列表，如 (a, b: int, c: string)。"""
        params = []
        if self._peek().type == T.RPAREN:
            return params
        params.append(self._func_param())
        while self._match(T.COMMA):
            params.append(self._func_param())
        return params

    def _func_param(self):
        """解析单个函数参数，包含参数名和可选类型注解。"""
        name = self._expect(T.IDENT).value
        type_ann = None
        if self._match(T.COLON):
            type_ann = self._type_expr()
        return FuncParam(name, type_ann)

    def _struct_decl(self):
        """解析结构体声明，如 struct Point { x: float, y: float }。"""
        self._expect(T.STRUCT)
        name = self._expect(T.IDENT).value
        self._skip_newlines()
        self._expect(T.LBRACE)
        self._skip_newlines()
        fields = []
        while self._peek().type != T.RBRACE:
            fname = self._expect(T.IDENT).value
            self._expect(T.COLON)
            ftype = self._type_expr()
            fields.append(StructField(fname, ftype))
            self._match(T.COMMA)
            self._skip_newlines()
        self._expect(T.RBRACE)
        self._skip_newlines()
        return StructDecl(name, fields)

    def _type_expr(self):
        """解析类型表达式，支持泛型参数如 []int。"""
        name = self._expect(T.IDENT).value
        generics = []
        if self._match(T.LBRACKET):
            generics.append(self._type_expr())
            while self._match(T.COMMA):
                generics.append(self._type_expr())
            self._expect(T.RBRACKET)
        return TypeExpr(name, generics)

    # ---- 语句 ----

    def _block(self):
        """解析代码块 { ... }。"""
        self._expect(T.LBRACE)
        self._skip_newlines()
        stmts = []
        while self._peek().type != T.RBRACE:
            stmts.append(self._statement())
            self._skip_newlines()
        self._expect(T.RBRACE)
        return Block(stmts)

    def _statement(self):
        """根据当前 Token 类型分派到对应的语句解析方法。"""
        tok = self._peek()
        if tok.type == T.LET:
            return self._let_stmt()
        if tok.type == T.IF:
            return self._if_stmt()
        if tok.type == T.FOR:
            return self._for_stmt()
        if tok.type == T.WHILE:
            return self._while_stmt()
        if tok.type == T.SWITCH:
            return self._switch_stmt()
        if tok.type == T.RETURN:
            return self._return_stmt()
        if tok.type == T.BREAK:
            self._advance()
            self._expect_end()
            return BreakStatement()
        if tok.type == T.CONTINUE:
            self._advance()
            self._expect_end()
            return ContinueStatement()
        if tok.type == T.FN:
            return self._func_decl()
        if tok.type == T.STRUCT:
            return self._struct_decl()
        return self._expr_stmt()

    def _let_stmt(self):
        """解析变量声明语句，如 let x: int = 42。"""
        self._expect(T.LET)
        name = self._expect(T.IDENT).value
        type_ann = None
        if self._match(T.COLON):
            type_ann = self._type_expr()
        init = None
        if self._match(T.ASSIGN):
            init = self._expression()
        self._expect_end()
        return LetStatement(name, type_ann, init)

    def _if_stmt(self):
        """解析 if / else if / else 语句。"""
        self._expect(T.IF)
        condition = self._expression()
        self._skip_newlines()
        then_block = self._block()
        else_block = None
        self._skip_newlines()
        if self._match(T.ELSE):
            self._skip_newlines()
            if self._peek().type == T.IF:
                else_block = self._if_stmt()
            else:
                else_block = self._block()
        return IfStatement(condition, then_block, else_block)

    def _for_stmt(self):
        """解析 for-in 循环语句，如 for item in arr { ... }。"""
        self._expect(T.FOR)
        var_name = self._expect(T.IDENT).value
        self._expect(T.IN)
        iterable = self._expression()
        self._skip_newlines()
        body = self._block()
        return ForInStatement(var_name, iterable, body)

    def _while_stmt(self):
        """解析 while 循环语句，如 while cond { ... }。"""
        self._expect(T.WHILE)
        condition = self._expression()
        self._skip_newlines()
        body = self._block()
        return WhileStatement(condition, body)

    def _switch_stmt(self):
        """解析 switch/case/default 语句。"""
        self._expect(T.SWITCH)
        expr = self._expression()
        self._skip_newlines()
        self._expect(T.LBRACE)
        self._skip_newlines()
        cases = []
        while self._peek().type in (T.CASE, T.DEFAULT):
            if self._peek().type == T.DEFAULT:
                self._advance()
                self._expect(T.COLON)
                self._skip_newlines()
                body = self._switch_body()
                cases.append(SwitchCase(None, body))
            else:
                self._advance()  # 跳过 'case'
                value = self._expression()
                self._expect(T.COLON)
                self._skip_newlines()
                body = self._switch_body()
                cases.append(SwitchCase(value, body))
            self._skip_newlines()
        self._expect(T.RBRACE)
        return SwitchStatement(expr, cases)

    def _switch_body(self):
        """解析 switch case 分支内的语句序列。"""
        stmts = []
        while self._peek().type not in (T.CASE, T.DEFAULT, T.RBRACE):
            stmts.append(self._statement())
            self._skip_newlines()
        return Block(stmts)

    def _return_stmt(self):
        """解析 return 语句，可带返回值也可不带。"""
        self._expect(T.RETURN)
        value = None
        if self._peek().type not in (T.NEWLINE, T.SEMICOLON, T.EOF, T.RBRACE):
            value = self._expression()
        self._expect_end()
        return ReturnStatement(value)

    def _expr_stmt(self):
        """解析表达式语句（以表达式结尾的语句）。"""
        expr = self._expression()
        self._expect_end()
        return ExprStatement(expr)

    # ---- 表达式（运算符优先级爬升） ----

    def _expression(self):
        """解析表达式入口，从赋值优先级开始。"""
        return self._assignment()

    def _assignment(self):
        """解析赋值表达式 (=, +=, -=)，右结合。"""
        expr = self._logic_or()
        if tok := self._match(T.ASSIGN):
            value = self._assignment()
            return Assignment(expr, value)
        if tok := self._match(T.PLUS_ASSIGN):
            value = self._assignment()
            return CompoundAssignment("+=", expr, value)
        if tok := self._match(T.MINUS_ASSIGN):
            value = self._assignment()
            return CompoundAssignment("-=", expr, value)
        return expr

    def _logic_or(self):
        """解析逻辑或表达式 (||)，左结合。"""
        left = self._logic_and()
        while self._match(T.OR):
            right = self._logic_and()
            left = BinaryOp("||", left, right)
        return left

    def _logic_and(self):
        """解析逻辑与表达式 (&&)，左结合。"""
        left = self._equality()
        while self._match(T.AND):
            right = self._equality()
            left = BinaryOp("&&", left, right)
        return left

    def _equality(self):
        """解析相等性表达式 (==, !=)，左结合。"""
        left = self._comparison()
        while tok := self._match(T.EQ, T.NEQ):
            right = self._comparison()
            left = BinaryOp(tok.value, left, right)
        return left

    def _comparison(self):
        """解析比较表达式 (<, >, <=, >=)，左结合。"""
        left = self._addition()
        while tok := self._match(T.LT, T.GT, T.LTE, T.GTE):
            right = self._addition()
            left = BinaryOp(tok.value, left, right)
        return left

    def _addition(self):
        """解析加减表达式 (+, -)，左结合。"""
        left = self._multiplication()
        while tok := self._match(T.PLUS, T.MINUS):
            right = self._multiplication()
            left = BinaryOp(tok.value, left, right)
        return left

    def _multiplication(self):
        """解析乘除取模表达式 (*, /, %)，左结合。"""
        left = self._unary()
        while tok := self._match(T.STAR, T.SLASH, T.PERCENT):
            right = self._unary()
            left = BinaryOp(tok.value, left, right)
        return left

    def _unary(self):
        """解析一元表达式 (!, -)，右结合。"""
        if tok := self._match(T.NOT, T.MINUS):
            return UnaryOp(tok.value, self._unary())
        return self._postfix()

    def _postfix(self):
        """解析后缀表达式：函数调用、成员访问、下标访问。"""
        expr = self._primary()
        while True:
            if self._match(T.LPAREN):
                args = []
                if self._peek().type != T.RPAREN:
                    args.append(self._expression())
                    while self._match(T.COMMA):
                        args.append(self._expression())
                self._expect(T.RPAREN)
                expr = CallExpr(expr, args)
            elif self._match(T.DOT):
                member = self._expect(T.IDENT).value
                expr = MemberAccess(expr, member)
            elif self._match(T.LBRACKET):
                index = self._expression()
                self._expect(T.RBRACKET)
                expr = IndexAccess(expr, index)
            else:
                break
        return expr

    def _primary(self):
        """解析基本表达式：字面量、标识符、括号表达式、数组、匿名函数。"""
        tok = self._peek()

        if tok.type == T.INT:
            self._advance()
            return IntLiteral(tok.value)
        if tok.type == T.FLOAT:
            self._advance()
            return FloatLiteral(tok.value)
        if tok.type == T.STRING:
            self._advance()
            return StringLiteral(tok.value)
        if tok.type == T.BOOL:
            self._advance()
            return BoolLiteral(tok.value)
        if tok.type == T.IDENT:
            self._advance()
            return Identifier(tok.value)
        if tok.type == T.LPAREN:
            self._advance()
            expr = self._expression()
            self._expect(T.RPAREN)
            return expr
        if tok.type == T.LBRACKET:
            self._advance()
            elements = []
            if self._peek().type != T.RBRACKET:
                elements.append(self._expression())
                while self._match(T.COMMA):
                    elements.append(self._expression())
            self._expect(T.RBRACKET)
            return ArrayLiteral(elements)

        # 匿名函数：fn(params) { body }
        if tok.type == T.FN:
            return self._anonymous_func()

        raise ParseError("Expected expression", tok)

    def _anonymous_func(self):
        """解析匿名函数表达式，如 fn(x) { return x * 2 }。"""
        self._expect(T.FN)
        self._expect(T.LPAREN)
        params = self._param_list()
        self._expect(T.RPAREN)
        self._skip_newlines()
        body = self._block()
        return FuncDecl("", params, None, body)
