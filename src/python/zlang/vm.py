"""
ZLang 虚拟机 / 解释器（VM）。

遍历 AST 并直接执行。支持：
  - 变量与作用域（嵌套环境）
  - 函数（闭包）、递归
  - 结构体（实例化、字段访问）
  - 数组（下标访问、字面量）
  - 控制流：if/else、for-in、while、switch、break、continue、return
  - 模块导入
  - 内置函数：print, len, push, typeof, str, int, float
"""

from zlang.ast import *
from zlang.parser import ParseError


class BreakSignal(Exception):
    """break 信号，用于跳出循环。"""
    pass

class ContinueSignal(Exception):
    """continue 信号，用于跳过当前迭代。"""
    pass

class ReturnSignal(Exception):
    """return 信号，携带返回值用于退出函数。"""

    def __init__(self, value):
        self.value = value


class ZLangError(Exception):
    """运行时错误。"""

    def __init__(self, message, node=None):
        self.node = node
        loc = f" (line {node.__dict__.get('line', '?')})" if node else ""
        super().__init__(f"RuntimeError{loc}: {message}")


# ---- 运行时对象 ----

class ZFunction:
    """用户定义的函数对象，携带闭包环境。"""

    def __init__(self, name, params, body, closure):
        """
        参数:
            name:    函数名
            params:  参数列表（FuncParam AST 节点）
            body:    函数体（Block AST 节点）
            closure: 闭包环境（定义时的 Environment）
        """
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure

    def __repr__(self):
        """返回函数的可读表示。"""
        return f"<fn {self.name}>"


class ZStructInstance:
    """结构体实例，存储字段名到值的映射。"""

    def __init__(self, struct_name, fields):
        """
        参数:
            struct_name: 结构体名称
            fields:      字段字典 {name: value}
        """
        self.struct_name = struct_name
        self.fields = fields

    def __repr__(self):
        """返回结构体实例的可读表示。"""
        pairs = ", ".join(f"{k}: {_fmt(v)}" for k, v in self.fields.items())
        return f"{self.struct_name}{{{pairs}}}"


class ZModule:
    """已导入模块，存储导出的符号。"""

    def __init__(self, name, exports):
        """
        参数:
            name:    模块路径
            exports: 导出符号字典 {name: value}
        """
        self.name = name
        self.exports = exports

    def __repr__(self):
        """返回模块的可读表示。"""
        return f"<module {self.name}>"


# ---- 环境（词法作用域） ----

class Environment:
    """变量作用域环境，支持嵌套（链式父作用域查找）。"""

    def __init__(self, parent=None):
        """
        参数:
            parent: 父作用域，查找变量时沿父链向上搜索
        """
        self.vars = {}
        self.parent = parent

    def define(self, name, value):
        """在当前作用域定义一个新变量。"""
        self.vars[name] = value

    def get(self, name):
        """查找变量值，沿父作用域链向上搜索。"""
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise ZLangError(f"Undefined variable '{name}'")

    def set(self, name, value):
        """修改已有变量的值，沿父作用域链向上搜索。"""
        if name in self.vars:
            self.vars[name] = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        raise ZLangError(f"Undefined variable '{name}'")


# ---- 格式化工具 ----

def _fmt(value):
    """将运行时值转换为用户可读的字符串表示。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        return str(value)
    if value is None:
        return "null"
    if isinstance(value, list):
        return "[" + ", ".join(_fmt(v) for v in value) + "]"
    return str(value)


# ---- 内置函数 ----

def _builtin_print(*args):
    """内置 print 函数：打印参数，空格分隔。"""
    print(" ".join(_fmt(a) for a in args))
    return None

def _builtin_len(obj):
    """内置 len 函数：返回数组或字符串的长度。"""
    if isinstance(obj, (list, str)):
        return len(obj)
    raise ZLangError(f"len() not supported for {type(obj).__name__}")

def _builtin_push(arr, val):
    """内置 push 函数：向数组末尾追加一个元素。"""
    if isinstance(arr, list):
        arr.append(val)
        return arr
    raise ZLangError("push() expects an array as first argument")

def _builtin_typeof(val):
    """内置 typeof 函数：返回值的类型名称字符串。"""
    if isinstance(val, bool):
        return "bool"
    if isinstance(val, int):
        return "int"
    if isinstance(val, float):
        return "float"
    if isinstance(val, str):
        return "string"
    if isinstance(val, list):
        return "array"
    if isinstance(val, ZStructInstance):
        return val.struct_name
    if isinstance(val, ZFunction):
        return "function"
    if val is None:
        return "null"
    return type(val).__name__

def _builtin_str(val):
    """内置 str 函数：将值转换为字符串。"""
    return _fmt(val)

def _builtin_int(val):
    """内置 int 函数：将值转换为整数。"""
    return int(val)

def _builtin_float(val):
    """内置 float 函数：将值转换为浮点数。"""
    return float(val)


# ---- 解释器 ----

class Interpreter:
    """
    ZLang 解释器，遍历 AST 并执行。

    用法:
        interp = Interpreter(import_resolver=resolve_import)
        interp.run(program)
    """

    def __init__(self, import_resolver=None):
        """
        初始化解释器，注册内置函数。

        参数:
            import_resolver: 模块导入解析函数，接收模块路径，返回 (源码, 文件名)
        """
        self.global_env = Environment()
        self.import_resolver = import_resolver
        self._loaded_modules = {}
        self._init_builtins()

    def _init_builtins(self):
        """在全局环境中注册所有内置函数。"""
        self.global_env.define("print", _builtin_print)
        self.global_env.define("len", _builtin_len)
        self.global_env.define("push", _builtin_push)
        self.global_env.define("typeof", _builtin_typeof)
        self.global_env.define("str", _builtin_str)
        self.global_env.define("int", _builtin_int)
        self.global_env.define("float", _builtin_float)

    def run(self, program, env=None):
        """执行一个 Program AST 节点。"""
        env = env or self.global_env
        result = None
        for stmt in program.statements:
            result = self._exec(stmt, env)
        return result

    def exec_source(self, source, filename="<stdin>"):
        """便捷方法：词法分析 → 语法分析 → 执行。"""
        from zlang.lexer import Lexer
        from zlang.parser import Parser
        tokens = Lexer(source, filename).tokens
        program = Parser(tokens, filename).parse()
        return self.run(program)

    # ---- 语句执行 ----

    def _exec(self, node, env):
        """根据 AST 节点类型分派到对应的执行方法。"""
        method = f"_exec_{type(node).__name__}"
        handler = getattr(self, method, None)
        if handler:
            return handler(node, env)
        raise ZLangError(f"Unknown AST node: {type(node).__name__}")

    def _exec_Program(self, node, env):
        """执行程序根节点。"""
        for stmt in node.statements:
            self._exec(stmt, env)
        return None

    def _exec_LetStatement(self, node, env):
        """执行变量声明语句。"""
        value = self._eval(node.init, env) if node.init else None
        env.define(node.name, value)
        return None

    def _exec_ExprStatement(self, node, env):
        """执行表达式语句，返回表达式的值。"""
        return self._eval(node.expr, env)

    def _exec_IfStatement(self, node, env):
        """执行 if / else if / else 条件语句。"""
        if self._is_truthy(self._eval(node.condition, env)):
            self._exec_block(node.then_block, env)
        elif node.else_block:
            if isinstance(node.else_block, IfStatement):
                self._exec_IfStatement(node.else_block, env)
            else:
                self._exec_block(node.else_block, env)
        return None

    def _exec_ForInStatement(self, node, env):
        """执行 for-in 循环语句，迭代数组的每个元素。"""
        iterable = self._eval(node.iterable, env)
        if not isinstance(iterable, list):
            raise ZLangError("for-in requires an iterable (array)")
        for item in iterable:
            loop_env = Environment(env)
            loop_env.define(node.var_name, item)
            try:
                self._exec_block(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return None

    def _exec_WhileStatement(self, node, env):
        """执行 while 循环语句。"""
        while self._is_truthy(self._eval(node.condition, env)):
            try:
                self._exec_block(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return None

    def _exec_SwitchStatement(self, node, env):
        """执行 switch 语句，匹配 case 分支并执行对应代码块。"""
        target = self._eval(node.expr, env)
        matched = False
        for case in node.cases:
            if not matched:
                if case.value is None:
                    # default 分支
                    matched = True
                elif self._values_equal(target, self._eval(case.value, env)):
                    matched = True
            if matched:
                try:
                    self._exec_block(case.body, env)
                except BreakSignal:
                    return None
        return None

    def _exec_ReturnStatement(self, node, env):
        """执行 return 语句，通过异常机制退出函数。"""
        value = self._eval(node.value, env) if node.value else None
        raise ReturnSignal(value)

    def _exec_BreakStatement(self, node, env):
        """执行 break 语句，跳出当前循环。"""
        raise BreakSignal()

    def _exec_ContinueStatement(self, node, env):
        """执行 continue 语句，跳过当前迭代。"""
        raise ContinueSignal()

    def _exec_FuncDecl(self, node, env):
        """执行函数声明，创建 ZFunction 对象并注册到当前环境。"""
        fn = ZFunction(node.name, node.params, node.body, env)
        env.define(node.name, fn)
        return None

    def _exec_StructDecl(self, node, env):
        """执行结构体声明，将 AST 节点注册为可调用的构造器。"""
        struct_def = node
        env.define(node.name, struct_def)
        return None

    def _exec_ImportDecl(self, node, env):
        """执行 import 声明，加载模块并将导出符号注入当前环境。"""
        if not self.import_resolver:
            raise ZLangError(f"Cannot import '{node.module_path}': no import resolver configured")
        module = self._load_module(node.module_path)
        for name, val in module.exports.items():
            env.define(name, val)
        return None

    def _exec_Block(self, node, env):
        """执行代码块。"""
        self._exec_block(node, env)
        return None

    def _exec_block(self, block, env):
        """在新的子作用域中执行代码块内的语句序列。"""
        block_env = Environment(env)
        for stmt in block.statements:
            self._exec(stmt, block_env)

    # ---- 表达式求值 ----

    def _eval(self, node, env):
        """根据 AST 节点类型分派到对应的求值方法。"""
        method = f"_eval_{type(node).__name__}"
        handler = getattr(self, method, None)
        if handler:
            return handler(node, env)
        raise ZLangError(f"Unknown expression: {type(node).__name__}")

    def _eval_IntLiteral(self, node, env):
        """求值整数字面量。"""
        return node.value

    def _eval_FloatLiteral(self, node, env):
        """求值浮点数字面量。"""
        return node.value

    def _eval_StringLiteral(self, node, env):
        """求值字符串字面量。"""
        return node.value

    def _eval_BoolLiteral(self, node, env):
        """求值布尔字面量。"""
        return node.value

    def _eval_ArrayLiteral(self, node, env):
        """求值数组字面量，递归求值每个元素。"""
        return [self._eval(el, env) for el in node.elements]

    def _eval_Identifier(self, node, env):
        """求值标识符，从环境中查找变量值。"""
        return env.get(node.name)

    def _eval_BinaryOp(self, node, env):
        """求值二元运算，逻辑运算符支持短路求值。"""
        # 短路求值
        if node.op == "&&":
            left = self._eval(node.left, env)
            return left if not self._is_truthy(left) else self._eval(node.right, env)
        if node.op == "||":
            left = self._eval(node.left, env)
            return left if self._is_truthy(left) else self._eval(node.right, env)

        left = self._eval(node.left, env)
        right = self._eval(node.right, env)

        ops = {
            "+":  lambda a, b: a + b,
            "-":  lambda a, b: a - b,
            "*":  lambda a, b: a * b,
            "/":  lambda a, b: a / b,
            "%":  lambda a, b: a % b,
            "==": lambda a, b: self._values_equal(a, b),
            "!=": lambda a, b: not self._values_equal(a, b),
            "<":  lambda a, b: a < b,
            ">":  lambda a, b: a > b,
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
        }
        if node.op in ops:
            try:
                return ops[node.op](left, right)
            except TypeError:
                raise ZLangError(f"Cannot apply '{node.op}' to {_fmt(left)} and {_fmt(right)}")
        raise ZLangError(f"Unknown operator: {node.op}")

    def _eval_UnaryOp(self, node, env):
        """求值一元运算（取负、逻辑非）。"""
        val = self._eval(node.operand, env)
        if node.op == "-":
            return -val
        if node.op == "!":
            return not self._is_truthy(val)
        raise ZLangError(f"Unknown unary operator: {node.op}")

    def _eval_Assignment(self, node, env):
        """求值赋值表达式 x = value。"""
        value = self._eval(node.value, env)
        self._assign(node.target, value, env)
        return value

    def _eval_CompoundAssignment(self, node, env):
        """求值复合赋值表达式 x += 1 / x -= 1。"""
        current = self._eval(node.target, env)
        rhs = self._eval(node.value, env)
        if node.op == "+=":
            new_val = current + rhs
        elif node.op == "-=":
            new_val = current - rhs
        else:
            raise ZLangError(f"Unknown compound operator: {node.op}")
        self._assign(node.target, new_val, env)
        return new_val

    def _assign(self, target, value, env):
        """执行赋值操作，支持变量、结构体字段和数组下标。"""
        if isinstance(target, Identifier):
            env.set(target.name, value)
        elif isinstance(target, MemberAccess):
            obj = self._eval(target.object, env)
            if isinstance(obj, ZStructInstance):
                obj.fields[target.member] = value
            else:
                raise ZLangError(f"Cannot set field on {type(obj).__name__}")
        elif isinstance(target, IndexAccess):
            obj = self._eval(target.object, env)
            idx = self._eval(target.index, env)
            if isinstance(obj, list):
                obj[int(idx)] = value
            else:
                raise ZLangError(f"Cannot index-assign on {type(obj).__name__}")
        else:
            raise ZLangError("Invalid assignment target")

    def _eval_CallExpr(self, node, env):
        """求值函数调用表达式，支持内置函数、用户函数和结构体构造。"""
        callee = self._eval(node.callee, env)
        args = [self._eval(a, env) for a in node.args]

        # 内置函数（Python callable）
        if callable(callee):
            return callee(*args)

        # 用户定义函数
        if isinstance(callee, ZFunction):
            return self._call_function(callee, args)

        # 结构体实例化：callee 是 StructDecl AST 节点
        if isinstance(callee, StructDecl):
            return self._instantiate_struct(callee, args)

        raise ZLangError(f"'{_fmt(callee)}' is not callable")

    def _call_function(self, fn, args):
        """调用用户定义函数：创建新环境、绑定参数、执行函数体。"""
        if len(args) != len(fn.params):
            raise ZLangError(f"Function '{fn.name}' expects {len(fn.params)} args, got {len(args)}")
        call_env = Environment(fn.closure)
        for param, arg in zip(fn.params, args):
            call_env.define(param.name, arg)
        try:
            self._exec_block(fn.body, call_env)
        except ReturnSignal as ret:
            return ret.value
        return None

    def _instantiate_struct(self, struct_def, args):
        """实例化结构体：创建字段字典并返回 ZStructInstance。"""
        fields = {}
        if len(args) == 0:
            # 无参数：所有字段初始化为 None
            for f in struct_def.fields:
                fields[f.name] = None
        elif len(args) == 1 and isinstance(args[0], dict):
            # 字典参数
            fields = args[0]
        else:
            # 按位置传参
            for f, v in zip(struct_def.fields, args):
                fields[f.name] = v
        return ZStructInstance(struct_def.name, fields)

    def _eval_MemberAccess(self, node, env):
        """求值成员访问表达式 obj.field，支持结构体、模块和字符串方法。"""
        obj = self._eval(node.object, env)
        # 结构体字段访问
        if isinstance(obj, ZStructInstance):
            if node.member in obj.fields:
                return obj.fields[node.member]
            raise ZLangError(f"Struct '{obj.struct_name}' has no field '{node.member}'")
        # 模块成员访问
        if isinstance(obj, ZModule):
            if node.member in obj.exports:
                return obj.exports[node.member]
            raise ZLangError(f"Module '{obj.name}' has no export '{node.member}'")
        # 字符串方法
        if isinstance(obj, str):
            return self._string_method(obj, node.member)
        raise ZLangError(f"Cannot access '.{node.member}' on {type(obj).__name__}")

    def _string_method(self, s, method):
        """获取字符串内置方法（len, upper, lower, trim, split, contains 等）。"""
        if method == "len":
            return len(s)
        if method == "upper":
            return s.upper()
        if method == "lower":
            return s.lower()
        if method == "trim":
            return s.strip()
        if method == "split":
            return lambda sep=None: s.split(sep)
        if method == "contains":
            return lambda sub: sub in s
        if method == "starts_with":
            return lambda prefix: s.startswith(prefix)
        if method == "ends_with":
            return lambda suffix: s.endswith(suffix)
        raise ZLangError(f"String has no method '{method}'")

    def _eval_IndexAccess(self, node, env):
        """求值下标访问表达式 arr[index]，支持负索引。"""
        obj = self._eval(node.object, env)
        idx = self._eval(node.index, env)
        if isinstance(obj, list):
            i = int(idx)
            if i < 0:
                i += len(obj)
            return obj[i]
        if isinstance(obj, str):
            return obj[int(idx)]
        raise ZLangError(f"Cannot index {type(obj).__name__}")

    def _eval_FuncDecl(self, node, env):
        """求值匿名函数表达式 fn(x) { return x * 2 }。"""
        return ZFunction(node.name or "<anonymous>", node.params, node.body, env)

    # ---- 辅助方法 ----

    def _is_truthy(self, val):
        """判断值是否为"真"，遵循 ZLang 的真假规则。"""
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return val != 0
        if isinstance(val, float):
            return val != 0.0
        if isinstance(val, str):
            return len(val) > 0
        if isinstance(val, list):
            return len(val) > 0
        return True

    def _values_equal(self, a, b):
        """判断两个值是否相等（严格类型比较）。"""
        if type(a) != type(b):
            return False
        return a == b

    def _load_module(self, module_path):
        """加载并缓存模块：词法分析 → 语法分析 → 执行 → 收集导出符号。"""
        if module_path in self._loaded_modules:
            return self._loaded_modules[module_path]

        source, filename = self.import_resolver(module_path)
        from zlang.lexer import Lexer
        from zlang.parser import Parser
        tokens = Lexer(source, filename).tokens
        program = Parser(tokens, filename).parse()

        module_env = Environment()
        self._init_builtins_in(module_env)
        self.run(program, module_env)

        # 收集所有非内置函数的定义作为导出符号
        exports = {}
        builtin_names = {"print", "len", "push", "typeof", "str", "int", "float"}
        for name, val in module_env.vars.items():
            if name not in builtin_names:
                exports[name] = val

        module = ZModule(module_path, exports)
        self._loaded_modules[module_path] = module
        return module

    def _init_builtins_in(self, env):
        """在指定环境中注册内置函数（用于模块导入）。"""
        env.define("print", _builtin_print)
        env.define("len", _builtin_len)
        env.define("push", _builtin_push)
        env.define("typeof", _builtin_typeof)
        env.define("str", _builtin_str)
        env.define("int", _builtin_int)
        env.define("float", _builtin_float)
