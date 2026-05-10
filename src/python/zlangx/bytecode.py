"""
ZLangX 字节码指令定义。

定义虚拟机的指令集（Opcode）和编译产物（CodeObject）。
指令集设计为栈式（Stack-based），每条指令从操作数栈取值、压入结果。
"""

from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Any


class Op(IntEnum):
    """
    字节码操作码。

    指令格式: [opcode, arg?]
    - 无参数指令: 仅 opcode，如 BINARY_ADD
    - 有参数指令: opcode + arg，如 LOAD_CONST 42
    """

    # ---- 栈操作 ----
    LOAD_CONST = 1      # 压入常量池[arg]的值
    LOAD_NAME = 2       # 压入变量名表[arg]对应的值
    STORE_NAME = 3      # 弹出栈顶，存入变量名表[arg]
    POP = 4             # 弹出栈顶，丢弃
    DUP = 5             # 复制栈顶

    # ---- 算术运算 ----
    BINARY_ADD = 10     # 弹出 b, a，压入 a + b
    BINARY_SUB = 11     # 弹出 b, a，压入 a - b
    BINARY_MUL = 12     # 弹出 b, a，压入 a * b
    BINARY_DIV = 13     # 弹出 b, a，压入 a / b
    BINARY_MOD = 14     # 弹出 b, a，压入 a % b
    UNARY_NEG = 15      # 弹出 a，压入 -a
    UNARY_NOT = 16      # 弹出 a，压入 !is_truthy(a)

    # ---- 比较运算 ----
    COMPARE_EQ = 20     # 弹出 b, a，压入 a == b
    COMPARE_NEQ = 21    # 弹出 b, a，压入 a != b
    COMPARE_LT = 22     # 弹出 b, a，压入 a < b
    COMPARE_GT = 23     # 弹出 b, a，压入 a > b
    COMPARE_LTE = 24    # 弹出 b, a，压入 a <= b
    COMPARE_GTE = 25    # 弹出 b, a，压入 a >= b

    # ---- 逻辑运算（含短路） ----
    JUMP = 30           # 无条件跳转到 arg
    JUMP_IF_FALSE = 31  # 弹出栈顶，假则跳转到 arg
    JUMP_IF_TRUE = 32   # 弹出栈顶，真则跳转到 arg
    JUMP_IF_FALSE_OR_POP = 33  # 短路 &&：假则跳转且保留栈顶，真则弹出
    JUMP_IF_TRUE_OR_POP = 34   # 短路 ||：真则跳转且保留栈顶，假则弹出

    # ---- 函数调用 ----
    CALL = 40           # 弹出 callee 和 arg 个参数，压入返回值
    RETURN = 41         # 弹出栈顶作为返回值
    RETURN_NULL = 42    # 返回 null（无返回值）
    MAKE_FUNC = 43      # 创建闭包函数，arg 为 code_objects 索引

    # ---- 数组 ----
    BUILD_ARRAY = 50    # 弹出 arg 个元素，构建数组
    INDEX_GET = 51      # 弹出 index, obj，压入 obj[index]
    INDEX_SET = 52      # 弹出 value, index, obj，执行 obj[index]=value

    # ---- 结构体 ----
    MEMBER_GET = 60     # 弹出 obj，压入 obj[arg对应的字段名]
    MEMBER_SET = 61     # 弹出 value, obj，执行 obj.字段名 = value
    MAKE_STRUCT = 62    # 创建结构体实例，arg 为名称表索引

    # ---- 控制流信号 ----
    BREAK = 70          # break 信号
    CONTINUE = 71       # continue 信号

    # ---- 内置函数 ----
    BUILTIN_PRINT = 80  # 弹出 arg 个值，打印
    BUILTIN_LEN = 81    # 弹出值，压入 len
    BUILTIN_PUSH = 82   # 弹出 val, arr，压入结果
    BUILTIN_TYPEOF = 83 # 弹出值，压入类型名
    BUILTIN_STR = 84    # 弹出值，压入字符串
    BUILTIN_INT = 85    # 弹出值，压入整数
    BUILTIN_FLOAT = 86  # 弹出值，压入浮点数

    # ---- 导入 ----
    IMPORT = 90         # 导入模块，arg 为名称表索引

    # ---- 调试 ----
    HALT = 99           # 停机


# 指令是否有参数的查找表
_HAS_ARG = set()
for _op in Op:
    if _op not in (
        Op.BINARY_ADD, Op.BINARY_SUB, Op.BINARY_MUL, Op.BINARY_DIV, Op.BINARY_MOD,
        Op.UNARY_NEG, Op.UNARY_NOT,
        Op.COMPARE_EQ, Op.COMPARE_NEQ, Op.COMPARE_LT, Op.COMPARE_GT, Op.COMPARE_LTE, Op.COMPARE_GTE,
        Op.RETURN, Op.RETURN_NULL,
        Op.INDEX_GET, Op.INDEX_SET,
        Op.POP, Op.DUP,
        Op.BREAK, Op.CONTINUE,
        Op.HALT,
    ):
        _HAS_ARG.add(_op)


@dataclass
class Instruction:
    """单条字节码指令。"""
    op: Op
    arg: int = 0
    line: int = 0

    def __repr__(self):
        if self.op in _HAS_ARG:
            return f"{self.op.name} {self.arg}"
        return self.op.name


@dataclass
class CodeObject:
    """
    编译产物：一段字节码及其关联数据。

    每个函数体编译为一个独立的 CodeObject，
    顶层代码也编译为一个 CodeObject。
    """
    name: str                               # 代码对象名称（函数名或 "<module>"）
    instructions: List[Instruction] = field(default_factory=list)
    constants: List[Any] = field(default_factory=list)      # 常量池
    names: List[str] = field(default_factory=list)          # 变量名表
    field_names: List[str] = field(default_factory=list)    # 结构体字段名表
    code_objects: List["CodeObject"] = field(default_factory=list)  # 子函数
    struct_defs: dict = field(default_factory=dict)         # 结构体定义

    def emit(self, op, arg=0, line=0):
        """追加一条指令，返回其索引位置。"""
        idx = len(self.instructions)
        self.instructions.append(Instruction(op, arg, line))
        return idx

    def add_const(self, value):
        """添加常量到常量池，返回索引（去重）。"""
        for i, c in enumerate(self.constants):
            if c is value or (type(c) == type(value) and c == value):
                return i
        self.constants.append(value)
        return len(self.constants) - 1

    def add_name(self, name):
        """添加名称到名称表，返回索引（去重）。"""
        if name in self.names:
            return self.names.index(name)
        self.names.append(name)
        return len(self.names) - 1

    def add_field(self, name):
        """添加字段名到字段名表，返回索引（去重）。"""
        if name in self.field_names:
            return self.field_names.index(name)
        self.field_names.append(name)
        return len(self.field_names) - 1

    def add_code_object(self, code_obj):
        """添加子函数的 CodeObject，返回索引。"""
        self.code_objects.append(code_obj)
        return len(self.code_objects) - 1

    def dump(self, indent=0):
        """以可读格式输出字节码。"""
        prefix = "  " * indent
        lines = [f"{prefix}CodeObject({self.name}, consts={self.constants}, names={self.names})"]
        for i, inst in enumerate(self.instructions):
            lines.append(f"{prefix}  {i:4d}: {inst}")
        for co in self.code_objects:
            lines.append(co.dump(indent + 1))
        return "\n".join(lines)
