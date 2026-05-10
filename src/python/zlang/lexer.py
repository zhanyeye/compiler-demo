"""
ZLang 词法分析器（Lexer）。

将源代码文本转换为 Token 流。
支持：标识符、数字、字符串、运算符、关键字和注释。
"""

from zlang.token import Token, TokenType, KEYWORDS


class LexerError(Exception):
    """词法分析错误，包含行列号信息。"""

    def __init__(self, message, line, col):
        super().__init__(f"Lexer error at line {line}, col {col}: {message}")
        self.line = line
        self.col = col


class Lexer:
    """
    词法分析器，逐字符扫描源代码并生成 Token 列表。

    用法:
        tokens = Lexer(source_code, "my_file.zl").tokens
    """

    def __init__(self, source, filename="<stdin>"):
        """
        初始化词法分析器并立即执行词法分析。

        参数:
            source:   源代码字符串
            filename: 文件名（用于错误提示）
        """
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self._tokenize()

    def _peek(self, offset=0):
        """查看当前位置偏移 offset 处的字符，不移动指针。"""
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else "\0"

    def _advance(self):
        """前进一个字符，更新行号和列号，返回当前字符。"""
        ch = self._peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _match(self, expected):
        """如果当前字符匹配期望值则前进，返回是否匹配成功。"""
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _add_token(self, ttype, value):
        """向 Token 列表追加一个新的 Token。"""
        self.tokens.append(Token(ttype, value, self.line, self.col))

    def _skip_whitespace_and_comments(self):
        """跳过空格、制表符和注释（// 和 /* */）。"""
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in (" ", "\t", "\r"):
                self._advance()
            # 行注释：// ...
            elif ch == "/" and self._peek(1) == "/":
                while self.pos < len(self.source) and self._peek() != "\n":
                    self._advance()
            # 块注释：/* ... */
            elif ch == "/" and self._peek(1) == "*":
                self._advance()  # 跳过 /
                self._advance()  # 跳过 *
                while self.pos < len(self.source):
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance()  # 跳过 *
                        self._advance()  # 跳过 /
                        break
                    self._advance()
            else:
                break

    def _read_string(self, quote):
        """读取字符串字面量，处理转义字符。"""
        self._advance()  # 跳过开始引号
        result = []
        while self._peek() != quote and self._peek() != "\0":
            if self._peek() == "\\":
                self._advance()
                escape_map = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", '"': '"'}
                ch = self._advance()
                result.append(escape_map.get(ch, ch))
            else:
                result.append(self._advance())
        if self._peek() == "\0":
            raise LexerError("Unterminated string", self.line, self.col)
        self._advance()  # 跳过结束引号
        return "".join(result)

    def _read_number(self):
        """读取数字字面量（整数或浮点数）。"""
        start = self.pos
        is_float = False
        while self._peek().isdigit() or self._peek() == ".":
            if self._peek() == ".":
                if is_float:
                    break
                is_float = True
            self._advance()
        text = self.source[start:self.pos]
        return float(text) if is_float else int(text)

    def _read_identifier(self):
        """读取标识符（字母、数字、下划线组成）。"""
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        return self.source[start:self.pos]

    def _tokenize(self):
        """主词法分析循环，逐字符生成 Token 序列。"""
        while self.pos < len(self.source):
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.source):
                break

            ch = self._peek()
            line, col = self.line, self.col

            # 换行符（作为语句分隔符，合并连续换行）
            if ch == "\n":
                if not self.tokens or self.tokens[-1].type != TokenType.NEWLINE:
                    self._advance()
                    self._add_token(TokenType.NEWLINE, "\n")
                else:
                    self._advance()
                continue

            # 数字
            if ch.isdigit():
                value = self._read_number()
                ttype = TokenType.FLOAT if isinstance(value, float) else TokenType.INT
                self._add_token(ttype, value)
                continue

            # 字符串
            if ch in ('"', "'"):
                value = self._read_string(ch)
                self._add_token(TokenType.STRING, value)
                continue

            # 标识符和关键字
            if ch.isalpha() or ch == "_":
                value = self._read_identifier()
                ttype = KEYWORDS.get(value, TokenType.IDENT)
                if ttype == TokenType.TRUE:
                    self._add_token(TokenType.BOOL, True)
                elif ttype == TokenType.FALSE:
                    self._add_token(TokenType.BOOL, False)
                else:
                    self._add_token(ttype, value)
                continue

            # 双字符运算符
            self._advance()  # 消费当前字符
            if ch == "+":
                if self._match("="):
                    self._add_token(TokenType.PLUS_ASSIGN, "+=")
                else:
                    self._add_token(TokenType.PLUS, "+")
                continue
            if ch == "-":
                if self._match(">"):
                    self._add_token(TokenType.ARROW, "->")
                elif self._match("="):
                    self._add_token(TokenType.MINUS_ASSIGN, "-=")
                else:
                    self._add_token(TokenType.MINUS, "-")
                continue
            if ch == "*":
                self._add_token(TokenType.STAR, "*")
                continue
            if ch == "/":
                self._add_token(TokenType.SLASH, "/")
                continue
            if ch == "%":
                self._add_token(TokenType.PERCENT, "%")
                continue
            if ch == "=":
                if self._match("="):
                    self._add_token(TokenType.EQ, "==")
                else:
                    self._add_token(TokenType.ASSIGN, "=")
                continue
            if ch == "!":
                if self._match("="):
                    self._add_token(TokenType.NEQ, "!=")
                else:
                    self._add_token(TokenType.NOT, "!")
                continue
            if ch == "<":
                if self._match("="):
                    self._add_token(TokenType.LTE, "<=")
                else:
                    self._add_token(TokenType.LT, "<")
                continue
            if ch == ">":
                if self._match("="):
                    self._add_token(TokenType.GTE, ">=")
                else:
                    self._add_token(TokenType.GT, ">")
                continue
            if ch == "&" and self._match("&"):
                self._add_token(TokenType.AND, "&&")
                continue
            if ch == "|" and self._match("|"):
                self._add_token(TokenType.OR, "||")
                continue

            # 单字符界符
            simple = {
                "(": TokenType.LPAREN, ")": TokenType.RPAREN,
                "{": TokenType.LBRACE, "}": TokenType.RBRACE,
                "[": TokenType.LBRACKET, "]": TokenType.RBRACKET,
                ",": TokenType.COMMA, ":": TokenType.COLON,
                ";": TokenType.SEMICOLON, ".": TokenType.DOT,
            }
            if ch in simple:
                self._add_token(simple[ch], ch)
                continue

            raise LexerError(f"Unexpected character: {ch!r}", line, col)

        # 确保 Token 流以 EOF 结尾
        if self.tokens and self.tokens[-1].type == TokenType.NEWLINE:
            self.tokens.pop()
        self._add_token(TokenType.EOF, None)
