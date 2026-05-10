"""
ZLangX 字节码编译器。

遍历 AST，将其编译为 CodeObject（字节码指令序列）。
编译器只遍历一次 AST，生成扁平的指令数组，供 VM 直接执行。
"""

from zlang.ast import *
from zlangx.bytecode import Op, CodeObject


class Compiler:
    """
    AST → 字节码编译器。

    用法:
        code = Compiler().compile(program)
        # code.dump()  查看生成的字节码
    """

    def __init__(self):
        pass

    def compile(self, node):
        """编译 AST 节点，返回 CodeObject。"""
        if isinstance(node, Program):
            return self._compile_program(node)
        raise RuntimeError(f"Cannot compile {type(node).__name__}")

    def _compile_program(self, node):
        """编译程序顶层。"""
        code = CodeObject(name="<module>")
        for stmt in node.statements:
            self._compile_node(stmt, code)
        code.emit(Op.HALT, line=0)
        return code

    def _compile_node(self, node, code):
        """根据 AST 节点类型分派编译方法。"""
        method = f"_c_{type(node).__name__}"
        handler = getattr(self, method, None)
        if handler:
            return handler(node, code)
        raise RuntimeError(f"Cannot compile {type(node).__name__}")

    # ---- 语句 ----

    def _c_LetStatement(self, node, code):
        """编译 let x = expr → 先编译 expr，再 STORE_NAME。"""
        if node.init:
            self._compile_node(node.init, code)
        else:
            code.emit(Op.LOAD_CONST, code.add_const(None), line=0)
        name_idx = code.add_name(node.name)
        code.emit(Op.STORE_NAME, name_idx, line=0)

    def _c_ExprStatement(self, node, code):
        """编译表达式语句 → 编译表达式后 POP 丢弃结果。"""
        self._compile_node(node.expr, code)
        code.emit(Op.POP, line=0)

    def _c_Block(self, node, code):
        """编译代码块 → 依次编译每条语句。"""
        for stmt in node.statements:
            self._compile_node(stmt, code)

    def _c_IfStatement(self, node, code):
        """编译 if/else → 条件跳转指令。"""
        self._compile_node(node.condition, code)
        jump_to_else = code.emit(Op.JUMP_IF_FALSE, 0, line=0)
        self._compile_node(node.then_block, code)
        if node.else_block:
            jump_to_end = code.emit(Op.JUMP, 0, line=0)
            code.instructions[jump_to_else].arg = len(code.instructions)
            self._compile_node(node.else_block, code)
            code.instructions[jump_to_end].arg = len(code.instructions)
        else:
            code.instructions[jump_to_else].arg = len(code.instructions)

    def _c_WhileStatement(self, node, code):
        """编译 while → 循环跳转 + 条件跳转。"""
        loop_start = len(code.instructions)
        self._compile_node(node.condition, code)
        jump_to_end = code.emit(Op.JUMP_IF_FALSE, 0, line=0)
        self._compile_node(node.body, code)
        code.emit(Op.JUMP, loop_start, line=0)
        code.instructions[jump_to_end].arg = len(code.instructions)

    def _c_ForInStatement(self, node, code):
        """
        编译 for-in → 编译为 while + index 的等价循环:
            iterable = <expr>
            _idx = 0
            _len = len(iterable)
            while _idx < _len {
                var = iterable[_idx]
                <body>
                _idx += 1
            }
        """
        # 生成唯一临时变量名
        tmp_iter = f"__for_iter_{id(node)}"
        tmp_idx = f"__for_idx_{id(node)}"
        tmp_len = f"__for_len_{id(node)}"

        # iterable = <expr>
        self._compile_node(node.iterable, code)
        code.emit(Op.STORE_NAME, code.add_name(tmp_iter), line=0)

        # _len = len(iterable)
        code.emit(Op.LOAD_NAME, code.add_name(tmp_iter), line=0)
        code.emit(Op.BUILTIN_LEN, line=0)
        code.emit(Op.STORE_NAME, code.add_name(tmp_len), line=0)

        # _idx = 0
        code.emit(Op.LOAD_CONST, code.add_const(0), line=0)
        code.emit(Op.STORE_NAME, code.add_name(tmp_idx), line=0)

        # while _idx < _len
        loop_start = len(code.instructions)
        code.emit(Op.LOAD_NAME, code.add_name(tmp_idx), line=0)
        code.emit(Op.LOAD_NAME, code.add_name(tmp_len), line=0)
        code.emit(Op.COMPARE_LT, line=0)
        jump_to_end = code.emit(Op.JUMP_IF_FALSE, 0, line=0)

        # var = iterable[_idx]
        code.emit(Op.LOAD_NAME, code.add_name(tmp_iter), line=0)
        code.emit(Op.LOAD_NAME, code.add_name(tmp_idx), line=0)
        code.emit(Op.INDEX_GET, line=0)
        code.emit(Op.STORE_NAME, code.add_name(node.var_name), line=0)

        # 循环体
        self._compile_node(node.body, code)

        # _idx += 1
        code.emit(Op.LOAD_NAME, code.add_name(tmp_idx), line=0)
        code.emit(Op.LOAD_CONST, code.add_const(1), line=0)
        code.emit(Op.BINARY_ADD, line=0)
        code.emit(Op.STORE_NAME, code.add_name(tmp_idx), line=0)

        code.emit(Op.JUMP, loop_start, line=0)
        code.instructions[jump_to_end].arg = len(code.instructions)

    def _c_SwitchStatement(self, node, code):
        """编译 switch → 等价为一系列 if-else。"""
        self._compile_node(node.expr, code)
        expr_idx = code.add_name("__switch_expr__")
        code.emit(Op.STORE_NAME, expr_idx, line=0)

        jumps_to_end = []
        for case in node.cases:
            if case.value is None:
                # default: 直接执行
                self._compile_node(case.body, code)
            else:
                # if expr == case_value
                code.emit(Op.LOAD_NAME, expr_idx, line=0)
                self._compile_node(case.value, code)
                code.emit(Op.COMPARE_EQ, line=0)
                jump_to_next = code.emit(Op.JUMP_IF_FALSE, 0, line=0)
                self._compile_node(case.body, code)
                jumps_to_end.append(code.emit(Op.JUMP, 0, line=0))
                code.instructions[jump_to_next].arg = len(code.instructions)

        for jmp in jumps_to_end:
            code.instructions[jmp].arg = len(code.instructions)

    def _c_ReturnStatement(self, node, code):
        """编译 return → 编译返回值后 RETURN。"""
        if node.value:
            self._compile_node(node.value, code)
            code.emit(Op.RETURN, line=0)
        else:
            code.emit(Op.RETURN_NULL, line=0)

    def _c_BreakStatement(self, node, code):
        """编译 break → BREAK 指令。"""
        code.emit(Op.BREAK, line=0)

    def _c_ContinueStatement(self, node, code):
        """编译 continue → CONTINUE 指令。"""
        code.emit(Op.CONTINUE, line=0)

    def _c_FuncDecl(self, node, code):
        """编译函数声明 → 生成子 CodeObject，然后 MAKE_FUNC 绑定到名称。"""
        fn_code = CodeObject(name=node.name or "<anonymous>")
        for param in node.params:
            fn_code.add_name(param.name)
        for stmt in node.body.statements:
            self._compile_node(stmt, fn_code)
        fn_code.emit(Op.RETURN_NULL, line=0)
        co_idx = code.add_code_object(fn_code)
        code.emit(Op.MAKE_FUNC, co_idx, line=0)
        if node.name:
            code.emit(Op.STORE_NAME, code.add_name(node.name), line=0)

    def _c_StructDecl(self, node, code):
        """编译结构体声明 → 记录结构体定义，将名称存储到变量环境。"""
        code.struct_defs[node.name] = node
        code.emit(Op.LOAD_CONST, code.add_const(node.name), line=0)
        code.emit(Op.STORE_NAME, code.add_name(node.name), line=0)

    def _c_ImportDecl(self, node, code):
        """编译 import → IMPORT 指令。"""
        code.emit(Op.IMPORT, code.add_name(node.module_path), line=0)

    # ---- 表达式 ----

    def _c_IntLiteral(self, node, code):
        code.emit(Op.LOAD_CONST, code.add_const(node.value), line=0)

    def _c_FloatLiteral(self, node, code):
        code.emit(Op.LOAD_CONST, code.add_const(node.value), line=0)

    def _c_StringLiteral(self, node, code):
        code.emit(Op.LOAD_CONST, code.add_const(node.value), line=0)

    def _c_BoolLiteral(self, node, code):
        code.emit(Op.LOAD_CONST, code.add_const(node.value), line=0)

    def _c_Identifier(self, node, code):
        code.emit(Op.LOAD_NAME, code.add_name(node.name), line=0)

    def _c_ArrayLiteral(self, node, code):
        """编译数组字面量 → 先编译所有元素，再 BUILD_ARRAY。"""
        for el in node.elements:
            self._compile_node(el, code)
        code.emit(Op.BUILD_ARRAY, len(node.elements), line=0)

    def _c_BinaryOp(self, node, code):
        """编译二元运算 → 编译左右操作数，发射对应运算指令。"""
        # 短路逻辑运算需要特殊处理
        if node.op == "&&":
            self._compile_node(node.left, code)
            jump = code.emit(Op.JUMP_IF_FALSE_OR_POP, 0, line=0)
            self._compile_node(node.right, code)
            code.instructions[jump].arg = len(code.instructions)
            return
        if node.op == "||":
            self._compile_node(node.left, code)
            jump = code.emit(Op.JUMP_IF_TRUE_OR_POP, 0, line=0)
            self._compile_node(node.right, code)
            code.instructions[jump].arg = len(code.instructions)
            return

        self._compile_node(node.left, code)
        self._compile_node(node.right, code)

        op_map = {
            "+": Op.BINARY_ADD, "-": Op.BINARY_SUB,
            "*": Op.BINARY_MUL, "/": Op.BINARY_DIV, "%": Op.BINARY_MOD,
            "==": Op.COMPARE_EQ, "!=": Op.COMPARE_NEQ,
            "<": Op.COMPARE_LT, ">": Op.COMPARE_GT,
            "<=": Op.COMPARE_LTE, ">=": Op.COMPARE_GTE,
        }
        if node.op in op_map:
            code.emit(op_map[node.op], line=0)
        else:
            raise RuntimeError(f"Unknown binary op: {node.op}")

    def _c_UnaryOp(self, node, code):
        """编译一元运算 → 编译操作数，发射 NEG/NOT 指令。"""
        self._compile_node(node.operand, code)
        if node.op == "-":
            code.emit(Op.UNARY_NEG, line=0)
        elif node.op == "!":
            code.emit(Op.UNARY_NOT, line=0)
        else:
            raise RuntimeError(f"Unknown unary op: {node.op}")

    def _c_Assignment(self, node, code):
        """编译赋值 x = expr → 编译 expr，按目标类型存储。"""
        self._compile_node(node.value, code)
        self._compile_store_target(node.target, code)

    def _c_CompoundAssignment(self, node, code):
        """编译复合赋值 x += expr → 编译为 LOAD + OP + STORE。"""
        self._compile_load_target(node.target, code)
        self._compile_node(node.value, code)
        op = Op.BINARY_ADD if node.op == "+=" else Op.BINARY_SUB
        code.emit(op, line=0)
        self._compile_store_target(node.target, code)

    def _compile_load_target(self, target, code):
        """编译赋值目标的读取操作（加载当前值）。"""
        if isinstance(target, Identifier):
            code.emit(Op.LOAD_NAME, code.add_name(target.name), line=0)
        elif isinstance(target, MemberAccess):
            self._compile_node(target.object, code)
            code.emit(Op.MEMBER_GET, code.add_field(target.member), line=0)
        elif isinstance(target, IndexAccess):
            self._compile_node(target.object, code)
            self._compile_node(target.index, code)
            code.emit(Op.INDEX_GET, line=0)

    def _compile_store_target(self, target, code):
        """编译赋值目标的写入操作。存储后重新压入值，供 ExprStatement 的 POP 消费。"""
        if isinstance(target, Identifier):
            name_idx = code.add_name(target.name)
            code.emit(Op.STORE_NAME, name_idx, line=0)
            code.emit(Op.LOAD_NAME, name_idx, line=0)
        elif isinstance(target, MemberAccess):
            val_name = "__assign_val__"
            code.emit(Op.STORE_NAME, code.add_name(val_name), line=0)
            self._compile_node(target.object, code)
            code.emit(Op.LOAD_NAME, code.add_name(val_name), line=0)
            code.emit(Op.MEMBER_SET, code.add_field(target.member), line=0)
        elif isinstance(target, IndexAccess):
            val_name = "__assign_val__"
            code.emit(Op.STORE_NAME, code.add_name(val_name), line=0)
            self._compile_node(target.object, code)
            self._compile_node(target.index, code)
            code.emit(Op.LOAD_NAME, code.add_name(val_name), line=0)
            code.emit(Op.INDEX_SET, line=0)
            code.emit(Op.LOAD_NAME, code.add_name(val_name), line=0)

    def _c_CallExpr(self, node, code):
        """编译函数调用 → 识别内置函数或普通调用。"""
        # 特殊处理内置函数
        if isinstance(node.callee, Identifier):
            name = node.callee.name
            if name == "print":
                for arg in node.args:
                    self._compile_node(arg, code)
                code.emit(Op.BUILTIN_PRINT, len(node.args), line=0)
                return
            if name == "len":
                self._compile_node(node.args[0], code)
                code.emit(Op.BUILTIN_LEN, line=0)
                return
            if name == "push":
                self._compile_node(node.args[0], code)
                self._compile_node(node.args[1], code)
                code.emit(Op.BUILTIN_PUSH, line=0)
                return
            if name == "typeof":
                self._compile_node(node.args[0], code)
                code.emit(Op.BUILTIN_TYPEOF, line=0)
                return
            if name == "str":
                self._compile_node(node.args[0], code)
                code.emit(Op.BUILTIN_STR, line=0)
                return
            if name == "int":
                self._compile_node(node.args[0], code)
                code.emit(Op.BUILTIN_INT, line=0)
                return
            if name == "float":
                self._compile_node(node.args[0], code)
                code.emit(Op.BUILTIN_FLOAT, line=0)
                return

        # 普通函数调用
        self._compile_node(node.callee, code)
        for arg in node.args:
            self._compile_node(arg, code)
        code.emit(Op.CALL, len(node.args), line=0)

    def _c_MemberAccess(self, node, code):
        """编译成员访问 obj.field → 编译 obj，MEMBER_GET。"""
        self._compile_node(node.object, code)
        code.emit(Op.MEMBER_GET, code.add_field(node.member), line=0)

    def _c_IndexAccess(self, node, code):
        """编译下标访问 arr[idx] → 编译 arr 和 idx，INDEX_GET。"""
        self._compile_node(node.object, code)
        self._compile_node(node.index, code)
        code.emit(Op.INDEX_GET, line=0)
