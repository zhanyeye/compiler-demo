"""
ZLang 抽象语法树（AST）节点定义。

所有 AST 节点均继承自 ASTNode。每个节点表示一种语言结构
（表达式、语句、声明等）。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any


# 基类
class ASTNode:
    """所有 AST 节点的基类。"""
    pass


# ---- 类型 ----

@dataclass
class TypeExpr(ASTNode):
    """类型注解，如 'int'、'string'、'MyStruct'、'[]int'。"""
    name: str
    generic_args: List["TypeExpr"] = field(default_factory=list)

    def __repr__(self):
        """返回类型的字符串表示，支持泛型参数。"""
        if self.generic_args:
            args = ", ".join(str(a) for a in self.generic_args)
            return f"{self.name}[{args}]"
        return self.name


# ---- 表达式 ----

@dataclass
class IntLiteral(ASTNode):
    """整数字面量，如 42。"""
    value: int

@dataclass
class FloatLiteral(ASTNode):
    """浮点数字面量，如 3.14。"""
    value: float

@dataclass
class StringLiteral(ASTNode):
    """字符串字面量，如 "hello"。"""
    value: str

@dataclass
class BoolLiteral(ASTNode):
    """布尔字面量，true 或 false。"""
    value: bool

@dataclass
class Identifier(ASTNode):
    """标识符，引用变量名、函数名等。"""
    name: str

@dataclass
class ArrayLiteral(ASTNode):
    """数组字面量，如 [1, 2, 3]。"""
    elements: List[ASTNode]

@dataclass
class BinaryOp(ASTNode):
    """二元运算表达式，如 a + b、x == y。"""
    op: str
    left: ASTNode
    right: ASTNode

@dataclass
class UnaryOp(ASTNode):
    """一元运算表达式，如 -5、!true。"""
    op: str
    operand: ASTNode

@dataclass
class CallExpr(ASTNode):
    """函数调用表达式，如 foo(1, 2)。"""
    callee: ASTNode
    args: List[ASTNode]

@dataclass
class MemberAccess(ASTNode):
    """成员访问表达式，如 obj.field。"""
    object: ASTNode
    member: str

@dataclass
class IndexAccess(ASTNode):
    """下标访问表达式，如 arr[0]。"""
    object: ASTNode
    index: ASTNode

@dataclass
class Assignment(ASTNode):
    """赋值表达式，如 x = 10。"""
    target: ASTNode  # Identifier, MemberAccess 或 IndexAccess
    value: ASTNode

@dataclass
class CompoundAssignment(ASTNode):
    """复合赋值表达式，如 x += 1、x -= 2。"""
    op: str  # "+=" 或 "-="
    target: ASTNode
    value: ASTNode


# ---- 语句 ----

@dataclass
class ExprStatement(ASTNode):
    """表达式语句，如 print("hello")。"""
    expr: ASTNode

@dataclass
class LetStatement(ASTNode):
    """变量声明语句，如 let x = 42。"""
    name: str
    type_ann: Optional[TypeExpr]
    init: Optional[ASTNode]

@dataclass
class Block(ASTNode):
    """代码块，包含一组语句序列。"""
    statements: List[ASTNode]

@dataclass
class IfStatement(ASTNode):
    """条件语句，if / else if / else。"""
    condition: ASTNode
    then_block: Block
    else_block: Optional[ASTNode]  # Block 或另一个 IfStatement

@dataclass
class ForInStatement(ASTNode):
    """for-in 循环语句，如 for item in arr { ... }。"""
    var_name: str
    iterable: ASTNode
    body: Block

@dataclass
class WhileStatement(ASTNode):
    """while 循环语句，如 while cond { ... }。"""
    condition: ASTNode
    body: Block

@dataclass
class SwitchCase(ASTNode):
    """switch 语句中的一个 case 分支。"""
    value: Optional[ASTNode]  # None 表示 default 分支
    body: Block

@dataclass
class SwitchStatement(ASTNode):
    """switch 语句，根据表达式值匹配 case 分支。"""
    expr: ASTNode
    cases: List[SwitchCase]

@dataclass
class ReturnStatement(ASTNode):
    """return 语句，可带返回值也可不带。"""
    value: Optional[ASTNode]

@dataclass
class BreakStatement(ASTNode):
    """break 语句，跳出当前循环。"""
    pass

@dataclass
class ContinueStatement(ASTNode):
    """continue 语句，跳过当前迭代。"""
    pass


# ---- 声明 ----

@dataclass
class FuncParam(ASTNode):
    """函数参数，包含参数名和可选的类型注解。"""
    name: str
    type_ann: Optional[TypeExpr]

@dataclass
class FuncDecl(ASTNode):
    """函数声明，如 fn add(a, b) -> int { ... }。"""
    name: str
    params: List[FuncParam]
    return_type: Optional[TypeExpr]
    body: Block

@dataclass
class StructField(ASTNode):
    """结构体字段，包含字段名和类型。"""
    name: str
    type_ann: TypeExpr

@dataclass
class StructDecl(ASTNode):
    """结构体声明，如 struct Point { x: float, y: float }。"""
    name: str
    fields: List[StructField]

@dataclass
class ImportDecl(ASTNode):
    """导入声明，如 import std.math。"""
    module_path: str  # 如 "std.math" 或 "mylib"


# ---- 顶层 ----

@dataclass
class Program(ASTNode):
    """程序根节点，包含所有顶层语句。"""
    statements: List[ASTNode]
    filename: str = "<stdin>"
