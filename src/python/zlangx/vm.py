"""
ZLangX 栈式字节码虚拟机。

用紧凑的指令派发循环执行字节码，避免递归 AST 遍历。
核心优化点：
  - 扁平指令数组，顺序执行，无需递归
  - if/elif 整数比较派发，比 getattr 反射快
  - 操作数栈 + 字典环境，减少对象创建
  - 控制流用 ip 跳转，无需 Python 异常开销
"""

from zlangx.bytecode import Op, CodeObject
from zlang.ast import StructDecl


def _fmt(value):
    """将运行时值转为用户可读字符串。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if value is None:
        return "null"
    if isinstance(value, list):
        return "[" + ", ".join(_fmt(v) for v in value) + "]"
    return str(value)


def _is_truthy(val):
    """判断值的真假。"""
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


class XFunction:
    """编译后的函数：携带 CodeObject 和闭包环境。"""
    __slots__ = ("name", "code", "env")

    def __init__(self, name, code, env):
        self.name = name
        self.code = code
        self.env = env


class XVM:
    """
    ZLangX 字节码虚拟机。

    用法:
        vm = XVM()
        vm.run(code_object)
    """

    def __init__(self, import_resolver=None):
        self.globals = {}
        self.import_resolver = import_resolver
        self._loaded_modules = {}
        self._struct_defs = {}

    def run(self, code):
        """执行顶层 CodeObject。"""
        self._struct_defs.update(code.struct_defs)
        return self._execute(code, self.globals)

    def _execute(self, code, env):
        """核心执行循环：逐条取指令，派发执行。"""
        instructions = code.instructions
        constants = code.constants
        names = code.names
        field_names = code.field_names
        code_objects = code.code_objects

        stack = []
        ip = 0
        n = len(instructions)

        while ip < n:
            inst = instructions[ip]
            op = inst.op

            # ---- 栈操作 ----
            if op == Op.LOAD_CONST:
                stack.append(constants[inst.arg])
            elif op == Op.LOAD_NAME:
                name = names[inst.arg]
                if name in env:
                    stack.append(env[name])
                else:
                    raise RuntimeError(f"Undefined variable '{name}'")
            elif op == Op.STORE_NAME:
                env[names[inst.arg]] = stack.pop()
            elif op == Op.POP:
                stack.pop()
            elif op == Op.DUP:
                stack.append(stack[-1])

            # ---- 算术运算 ----
            elif op == Op.BINARY_ADD:
                b = stack.pop(); a = stack.pop()
                stack.append(a + b)
            elif op == Op.BINARY_SUB:
                b = stack.pop(); a = stack.pop()
                stack.append(a - b)
            elif op == Op.BINARY_MUL:
                b = stack.pop(); a = stack.pop()
                stack.append(a * b)
            elif op == Op.BINARY_DIV:
                b = stack.pop(); a = stack.pop()
                stack.append(a / b)
            elif op == Op.BINARY_MOD:
                b = stack.pop(); a = stack.pop()
                stack.append(a % b)
            elif op == Op.UNARY_NEG:
                stack.append(-stack.pop())
            elif op == Op.UNARY_NOT:
                stack.append(not _is_truthy(stack.pop()))

            # ---- 比较运算 ----
            elif op == Op.COMPARE_EQ:
                b = stack.pop(); a = stack.pop()
                stack.append(type(a) == type(b) and a == b)
            elif op == Op.COMPARE_NEQ:
                b = stack.pop(); a = stack.pop()
                stack.append(not (type(a) == type(b) and a == b))
            elif op == Op.COMPARE_LT:
                b = stack.pop(); a = stack.pop()
                stack.append(a < b)
            elif op == Op.COMPARE_GT:
                b = stack.pop(); a = stack.pop()
                stack.append(a > b)
            elif op == Op.COMPARE_LTE:
                b = stack.pop(); a = stack.pop()
                stack.append(a <= b)
            elif op == Op.COMPARE_GTE:
                b = stack.pop(); a = stack.pop()
                stack.append(a >= b)

            # ---- 跳转 ----
            elif op == Op.JUMP:
                ip = inst.arg
                continue
            elif op == Op.JUMP_IF_FALSE:
                if not _is_truthy(stack.pop()):
                    ip = inst.arg
                    continue
            elif op == Op.JUMP_IF_TRUE:
                if _is_truthy(stack.pop()):
                    ip = inst.arg
                    continue
            elif op == Op.JUMP_IF_FALSE_OR_POP:
                if not _is_truthy(stack[-1]):
                    ip = inst.arg
                    continue
                stack.pop()
            elif op == Op.JUMP_IF_TRUE_OR_POP:
                if _is_truthy(stack[-1]):
                    ip = inst.arg
                    continue
                stack.pop()

            # ---- 函数调用 ----
            elif op == Op.MAKE_FUNC:
                fn_code = code_objects[inst.arg]
                stack.append(XFunction(fn_code.name, fn_code, env))
            elif op == Op.CALL:
                argc = inst.arg
                callee = stack[-argc - 1]

                if isinstance(callee, XFunction):
                    fn = callee
                    call_env = dict(fn.env)
                    fn_params = fn.code.names[:argc]
                    for i in range(argc):
                        call_env[fn_params[i]] = stack[-argc + i]
                    del stack[-argc - 1:]
                    result = self._execute(fn.code, call_env)
                    # break/continue 信号穿透
                    if isinstance(result, str) and result in ("__break__", "__continue__"):
                        return result
                    stack.append(result)

                elif callee in self._struct_defs or (isinstance(callee, str) and callee in self._struct_defs):
                    struct_def = self._struct_defs[callee]
                    instance = {}
                    for i, f in enumerate(struct_def.fields):
                        instance[f.name] = stack[-argc + i] if i < argc else None
                    del stack[-argc - 1:]
                    stack.append(instance)

                elif callable(callee):
                    args = stack[-argc:]
                    del stack[-argc - 1:]
                    result = callee(*args)
                    stack.append(result)
                else:
                    raise RuntimeError(f"Not callable: {_fmt(callee)}")

            elif op == Op.RETURN:
                return stack[-1] if stack else None
            elif op == Op.RETURN_NULL:
                return None

            # ---- 数组 ----
            elif op == Op.BUILD_ARRAY:
                elems = stack[-inst.arg:]
                del stack[-inst.arg:]
                stack.append(elems)
            elif op == Op.INDEX_GET:
                idx = stack.pop(); obj = stack.pop()
                i = int(idx)
                if i < 0:
                    i += len(obj)
                stack.append(obj[i])
            elif op == Op.INDEX_SET:
                val = stack.pop(); idx = stack.pop(); obj = stack.pop()
                obj[int(idx)] = val

            # ---- 结构体字段 ----
            elif op == Op.MEMBER_GET:
                obj = stack.pop()
                field = field_names[inst.arg]
                if isinstance(obj, dict):
                    if field not in obj:
                        raise RuntimeError(f"No field '{field}'")
                    stack.append(obj[field])
                else:
                    raise RuntimeError(f"Cannot access '.{field}' on {type(obj).__name__}")
            elif op == Op.MEMBER_SET:
                val = stack.pop(); obj = stack.pop()
                field = field_names[inst.arg]
                obj[field] = val
                stack.append(val)
            elif op == Op.MAKE_STRUCT:
                # 将结构体名称压栈，作为构造器的标记
                stack.append(names[inst.arg])

            # ---- 控制流信号 ----
            elif op == Op.BREAK:
                return "__break__"
            elif op == Op.CONTINUE:
                return "__continue__"

            # ---- 内置函数 ----
            elif op == Op.BUILTIN_PRINT:
                argc = inst.arg
                parts = [_fmt(stack[-argc + i]) for i in range(argc)]
                print(" ".join(parts))
                del stack[-argc:]
                stack.append(None)
            elif op == Op.BUILTIN_LEN:
                stack.append(len(stack.pop()))
            elif op == Op.BUILTIN_PUSH:
                val = stack.pop()
                arr = stack[-1]
                arr.append(val)
                stack.append(arr)
            elif op == Op.BUILTIN_TYPEOF:
                val = stack.pop()
                if isinstance(val, bool): t = "bool"
                elif isinstance(val, int): t = "int"
                elif isinstance(val, float): t = "float"
                elif isinstance(val, str): t = "string"
                elif isinstance(val, list): t = "array"
                elif isinstance(val, dict): t = "struct"
                elif val is None: t = "null"
                else: t = type(val).__name__
                stack.append(t)
            elif op == Op.BUILTIN_STR:
                stack.append(_fmt(stack.pop()))
            elif op == Op.BUILTIN_INT:
                stack.append(int(stack.pop()))
            elif op == Op.BUILTIN_FLOAT:
                stack.append(float(stack.pop()))

            # ---- 导入 ----
            elif op == Op.IMPORT:
                self._do_import(names[inst.arg], env)

            # ---- 停机 ----
            elif op == Op.HALT:
                break

            ip += 1

        return stack[-1] if stack else None

    def _do_import(self, module_path, env):
        """导入模块，复用 zlang 的前端。"""
        if module_path in self._loaded_modules:
            env.update(self._loaded_modules[module_path])
            return

        if not self.import_resolver:
            raise RuntimeError(f"No import resolver for '{module_path}'")

        source, filename = self.import_resolver(module_path)
        from zlang.lexer import Lexer
        from zlang.parser import Parser
        from zlangx.compiler import Compiler

        tokens = Lexer(source, filename).tokens
        program = Parser(tokens, filename).parse()
        module_code = Compiler().compile(program)

        module_env = dict(env)
        self._struct_defs.update(module_code.struct_defs)
        self._execute(module_code, module_env)

        builtin_names = {"print", "len", "push", "typeof", "str", "int", "float"}
        exports = {k: v for k, v in module_env.items()
                   if k not in env and k not in builtin_names}
        self._loaded_modules[module_path] = exports
        env.update(exports)
