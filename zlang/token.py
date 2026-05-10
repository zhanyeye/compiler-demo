"""
ZLang 词法单元（Token）定义。

定义了所有 Token 类型枚举和 Token 数据类，供词法分析器使用。
"""

from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    """词法单元类型枚举，涵盖 ZLang 支持的所有词法类别。"""

    # --- 字面量 ---
    INT = auto()        # 整数，如 42
    FLOAT = auto()      # 浮点数，如 3.14
    STRING = auto()     # 字符串，如 "hello"
    BOOL = auto()       # 布尔值，true / false

    # --- 标识符 ---
    IDENT = auto()      # 标识符，如变量名、函数名

    # --- 运算符 ---
    PLUS = auto()       # +
    MINUS = auto()      # -
    STAR = auto()       # *
    SLASH = auto()      # /
    PERCENT = auto()    # %
    EQ = auto()         # ==
    NEQ = auto()        # !=
    LT = auto()         # <
    GT = auto()         # >
    LTE = auto()        # <=
    GTE = auto()        # >=
    AND = auto()        # &&
    OR = auto()         # ||
    NOT = auto()        # !
    ASSIGN = auto()     # =
    PLUS_ASSIGN = auto()    # +=
    MINUS_ASSIGN = auto()   # -=

    # --- 界符 ---
    LPAREN = auto()     # (
    RPAREN = auto()     # )
    LBRACE = auto()     # {
    RBRACE = auto()     # }
    LBRACKET = auto()   # [
    RBRACKET = auto()   # ]
    COMMA = auto()      # ,
    COLON = auto()      # :
    SEMICOLON = auto()  # ;
    DOT = auto()        # .
    ARROW = auto()      # ->

    # --- 关键字 ---
    LET = auto()        # let（变量声明）
    FN = auto()         # fn（函数声明）
    IF = auto()         # if
    ELSE = auto()       # else
    FOR = auto()        # for
    IN = auto()         # in
    WHILE = auto()      # while
    SWITCH = auto()     # switch
    CASE = auto()       # case
    DEFAULT = auto()    # default
    RETURN = auto()     # return
    STRUCT = auto()     # struct
    IMPORT = auto()     # import
    TRUE = auto()       # true
    FALSE = auto()      # false
    BREAK = auto()      # break
    CONTINUE = auto()   # continue

    # --- 特殊 ---
    NEWLINE = auto()    # 换行符（作为语句分隔符）
    EOF = auto()        # 文件结束


@dataclass
class Token:
    """词法单元，记录类型、值、行列号。"""
    type: TokenType
    value: any
    line: int
    col: int

    def __repr__(self):
        """返回 Token 的可读字符串表示。"""
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


# 关键字映射表：字符串 → TokenType
KEYWORDS = {
    "let": TokenType.LET,
    "fn": TokenType.FN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "while": TokenType.WHILE,
    "switch": TokenType.SWITCH,
    "case": TokenType.CASE,
    "default": TokenType.DEFAULT,
    "return": TokenType.RETURN,
    "struct": TokenType.STRUCT,
    "import": TokenType.IMPORT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
}
