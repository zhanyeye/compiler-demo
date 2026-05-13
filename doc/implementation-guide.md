# ZLang 实现导读

本文档是 ZLang 编译器各模块的代码导读，帮助读者快速定位和理解每个源文件的实现细节。

> 详细的设计原理请参阅 [design.md](design.md)，语言语法请参阅 [api-reference.md](api-reference.md)。

---

## 1. Python 实现（`src/python/`）

### 1.1 `zlang/token.py` — Token 类型定义（~100 行）

**核心内容**：

- `TokenType` 枚举类：定义了所有 Token 类型，分为以下几组：
  - 字面量：`INT`, `FLOAT`, `STRING`, `BOOL`
  - 标识符：`IDENT`
  - 运算符：`PLUS`, `MINUS`, `STAR`, `SLASH`, `PERCENT`, `EQ`, `NEQ`, `LT`, `GT`, `LTE`, `GTE`, `AND`, `OR`, `NOT`, `ASSIGN`, `PLUS_ASSIGN`, `MINUS_ASSIGN`
  - 界符：`LPAREN`, `RPAREN`, `LBRACE`, `RBRACE`, `LBRACKET`, `RBRACKET`, `COMMA`, `COLON`, `SEMICOLON`, `DOT`, `ARROW`
  - 关键字：`LET`, `FN`, `IF`, `ELSE`, `FOR`, `IN`, `WHILE`, `SWITCH`, `CASE`, `DEFAULT`, `RETURN`, `STRUCT`, `IMPORT`, `TRUE`, `FALSE`, `BREAK`, `CONTINUE`
  - 特殊：`NEWLINE`（语句分隔符），`EOF`
- `Token` 数据类：记录 `type`, `value`, `line`, `col`
- `KEYWORDS` 字典：关键字字符串 → `TokenType` 的映射

**关键设计**：`NEWLINE` 被作为独立的 Token 类型，因为 ZLang 使用换行作为语句分隔符（类似 Go）。

### 1.2 `zlang/lexer.py` — 词法分析器（~220 行）

**类结构**：

```
Lexer
├── __init__(source, filename)     初始化并立即执行词法分析
├── _peek(offset=0)               向前看字符
├── _advance()                    消费字符，更新行列号
├── _match(expected)              条件消费
├── _add_token(type, value)       追加 Token
├── _skip_whitespace_and_comments()  跳过空白和注释
├── _read_string(quote)           读取字符串（处理转义）
├── _read_number()                读取数字（区分 int/float）
├── _read_identifier()            读取标识符/关键字
└── _tokenize()                   主扫描循环
```

**Token 分类流程**：

```
字符 → 数字开头? → _read_number() → INT 或 FLOAT
     → 引号开头? → _read_string() → STRING
     → 字母/_?  → _read_identifier() → 关键字 或 IDENT
     → 运算符?  → 先消费首字符，再看下一个 → 单字符或双字符运算符
     → 界符?    → 直接映射
     → 换行?    → NEWLINE（合并连续换行）
     → 其他     → LexerError
```

**要点**：
- 使用 `_peek(1)` 实现向前看（区分 `=` 和 `==`、`/` 和 `//` 等）
- 转义字符处理：`\n`, `\t`, `\\`, `\"` 等
- 注释支持：行注释 `//` 和块注释 `/* */`

### 1.3 `zlang/ast.py` — AST 节点定义（~180 行）

**节点层次**：

```
ASTNode（基类）
├── TypeExpr                      类型注解
├── 表达式（有返回值）
│   ├── IntLiteral                整数 42
│   ├── FloatLiteral              浮点 3.14
│   ├── StringLiteral             字符串 "hello"
│   ├── BoolLiteral               布尔 true/false
│   ├── Identifier                标识符 x
│   ├── ArrayLiteral              数组 [1, 2, 3]
│   ├── BinaryOp                  二元运算 a + b
│   ├── UnaryOp                   一元运算 -x, !true
│   ├── CallExpr                  函数调用 f(1, 2)
│   ├── MemberAccess              成员访问 obj.field
│   ├── IndexAccess               下标访问 arr[0]
│   ├── Assignment                赋值 x = 10
│   └── CompoundAssignment        复合赋值 x += 1
├── 语句（无返回值）
│   ├── ExprStatement             表达式语句
│   ├── LetStatement              let x = 42
│   ├── Block                     { ... }
│   ├── IfStatement               if/else if/else
│   ├── ForInStatement            for item in arr { }
│   ├── WhileStatement            while cond { }
│   ├── SwitchStatement           switch/case/default
│   ├── SwitchCase                单个 case 分支
│   ├── ReturnStatement           return expr
│   ├── BreakStatement            break
│   └── ContinueStatement         continue
├── 声明
│   ├── FuncParam                 函数参数
│   ├── FuncDecl                  fn name(params) { body }
│   ├── StructField               结构体字段
│   ├── StructDecl                struct Name { fields }
│   └── ImportDecl                import std.math
└── Program                       程序根节点
```

所有节点使用 Python `@dataclass` 装饰器，自动生成 `__init__`。

### 1.4 `zlang/parser.py` — 语法分析器（~420 行）

**类结构**：

```
Parser
├── 辅助方法
│   ├── _peek()                   查看当前 Token
│   ├── _advance()                消费 Token
│   ├── _expect(type)             期望并消费
│   ├── _match(*types)            条件消费
│   ├── _skip_newlines()          跳过换行
│   └── _expect_end()             期望语句结束
│
├── 程序
│   ├── parse()                   入口：解析整个程序
│   └── _top_level()              顶层声明或语句
│
├── 声明
│   ├── _import_decl()            import 声明
│   ├── _func_decl()              函数声明
│   └── _struct_decl()            结构体声明
│
├── 语句
│   ├── _statement()              分派各种语句
│   ├── _let_stmt()               let 语句
│   ├── _if_stmt()                if 语句
│   ├── _for_stmt()               for-in 语句
│   ├── _while_stmt()             while 语句
│   ├── _switch_stmt()            switch 语句
│   ├── _return_stmt()            return 语句
│   └── _expr_stmt()              表达式语句
│
└── 表达式（优先级从低到高）
    ├── _expression()             入口
    ├── _assignment()             赋值（=, +=, -=）— 右结合
    ├── _logic_or()               逻辑或 ||
    ├── _logic_and()              逻辑与 &&
    ├── _equality()               相等性 == !=
    ├── _comparison()             比较 < > <= >=
    ├── _addition()               加减 + -
    ├── _multiplication()         乘除 * / %
    ├── _unary()                  一元 ! -
    ├── _postfix()                后缀 () . []
    └── _primary()                基础：字面量、标识符、括号、数组、匿名函数
```

**核心设计**：
- **递归下降**：每个文法规则对应一个方法
- **优先级分层**：从 `_assignment` 到 `_primary` 的调用链实现运算符优先级
- **左结合 vs 右结合**：赋值用递归实现右结合，其他用 `while` 循环实现左结合

### 1.5 `zlang/vm.py` — 虚拟机/解释器（~560 行）

**运行时对象**：

| 类 | 用途 |
|----|------|
| `BreakSignal` | break 异常信号 |
| `ContinueSignal` | continue 异常信号 |
| `ReturnSignal` | return 异常信号（携带返回值） |
| `ZLangError` | 运行时错误 |
| `ZFunction` | 用户定义函数（携带闭包） |
| `ZStructInstance` | 结构体实例（字段字典） |
| `ZModule` | 已导入模块（导出符号字典） |
| `Environment` | 作用域环境（链式父作用域查找） |

**Environment 查找流程**：

```
env.get("x")
  → 在当前 env.vars 中查找
  → 未找到 → env.parent.get("x")（沿父链向上）
  → 全都未找到 → 抛出 ZLangError
```

**Interpreter 类核心方法**：

```
Interpreter
├── run(program)                           执行入口
├── _exec(node, env)                       语句执行分派
│   ├── _exec_LetStatement                 变量声明
│   ├── _exec_IfStatement                  条件语句
│   ├── _exec_ForInStatement               for-in 循环
│   ├── _exec_WhileStatement               while 循环
│   ├── _exec_SwitchStatement              switch 语句
│   ├── _exec_FuncDecl                     函数声明
│   ├── _exec_StructDecl                   结构体声明
│   ├── _exec_ImportDecl                   模块导入
│   ├── _exec_ReturnStatement              return
│   ├── _exec_BreakStatement               break → raise BreakSignal
│   ├── _exec_ContinueStatement            continue → raise ContinueSignal
│   └── _exec_ExprStatement                表达式语句
├── _eval(node, env)                       表达式求值分派
│   ├── _eval_BinaryOp                     二元运算（含短路逻辑）
│   ├── _eval_UnaryOp                      一元运算
│   ├── _eval_CallExpr                     函数调用
│   ├── _eval_MemberAccess                 成员访问
│   ├── _eval_IndexAccess                  下标访问
│   ├── _eval_Assignment                   赋值
│   ├── _eval_CompoundAssignment           复合赋值
│   ├── _eval_ArrayLiteral                 数组字面量
│   └── _eval_xxx_Literal                  各种字面量
├── _call_function(fn, args)               函数调用实现
├── _exec_block(block, env)                执行代码块
├── _is_truthy(val)                        真假值判断
└── _load_module(path)                     加载模块（带缓存）
```

**控制流实现机制**：

break / continue / return 通过 Python 异常穿透多层调用栈，由对应的捕获层处理：

```python
# 循环中
try:
    self._exec(stmt, env)
except BreakSignal:
    break
except ContinueSignal:
    continue

# 函数中
try:
    self._exec_block(body, call_env)
except ReturnSignal as r:
    return r.value
```

**内置函数**：

在 `global_env` 中预定义的 Python 函数：`_builtin_print`, `_builtin_len`, `_builtin_push`, `_builtin_typeof`, `_builtin_str`, `_builtin_int`, `_builtin_float`。

### 1.6 `zlang/__main__.py` — CLI 入口（~120 行）

**子命令**：

| 命令 | 用法 | 功能 |
|------|------|------|
| `run` | `python -m zlang run <file>` | 编译并执行 ZLang 程序 |
| `repl` | `python -m zlang repl` | 启动交互式 REPL |
| `tokens` | `python -m zlang tokens <file>` | 输出 Token 流（调试） |
| `ast` | `python -m zlang ast <file>` | 输出 AST（调试） |

**模块解析**：`resolve_import()` 将点分模块路径转换为文件路径（如 `std.math` → `std/math.zl`），在当前目录和 `examples/` 下查找。

---

## 2. Python 字节码版（`src/python/zlangx/`）

> zlangx **复用 zlang 的前端**（Lexer + Parser + AST），仅实现编译器和字节码 VM。

### 2.1 `zlangx/bytecode.py` — 字节码指令集（~200 行）

**指令集分类**：

| 类别 | 指令 | 说明 |
|------|------|------|
| 栈操作 | `LOAD_CONST`, `LOAD_NAME`, `STORE_NAME`, `POP`, `DUP` | 压栈/出栈/存取变量 |
| 算术 | `BINARY_ADD/SUB/MUL/DIV/MOD`, `UNARY_NEG/NOT` | 四则运算 |
| 比较 | `COMPARE_EQ/NEQ/LT/GT/LTE/GTE` | 比较运算 |
| 跳转 | `JUMP`, `JUMP_IF_FALSE/TRUE`, `JUMP_IF_FALSE_OR_POP`, `JUMP_IF_TRUE_OR_POP` | 控制流跳转 |
| 函数 | `CALL`, `RETURN`, `RETURN_NULL`, `MAKE_FUNC` | 函数调用 |
| 数组 | `BUILD_ARRAY`, `INDEX_GET`, `INDEX_SET` | 数组操作 |
| 结构体 | `MEMBER_GET`, `MEMBER_SET`, `MAKE_STRUCT` | 结构体字段 |
| 控制流信号 | `BREAK`, `CONTINUE` | break/continue |
| 内置函数 | `BUILTIN_PRINT/LEN/PUSH/TYPEOF/STR/INT/FLOAT` | 内置操作 |
| 导入 | `IMPORT` | 模块导入 |
| 停机 | `HALT` | 程序结束 |

**CodeObject 结构**：

```python
CodeObject:
  name: str                       # 名称（函数名或 "<module>"）
  instructions: List[Instruction] # 指令数组
  constants: List[Any]            # 常量池（数字、字符串等）
  names: List[str]                # 变量名表
  field_names: List[str]          # 结构体字段名表
  code_objects: List[CodeObject]  # 嵌套函数的 CodeObject
  struct_defs: dict               # 结构体定义
```

**指令格式**：每条指令由 `[opcode, arg?]` 组成，无参数指令仅 opcode。

### 2.2 `zlangx/compiler.py` — AST → 字节码编译器（~300 行）

```
Compiler
├── compile(program)                编译入口
├── _compile_program(node)          编译顶层程序
├── _compile_node(node, code)       节点类型分派
│
├── 语句编译
│   ├── _c_LetStatement            let → LOAD_CONST/编译init + STORE_NAME
│   ├── _c_ExprStatement           表达式语句 → 编译表达式 + POP
│   ├── _c_Block                   块 → 依次编译每条语句
│   ├── _c_IfStatement             if → JUMP_IF_FALSE 条件跳转
│   ├── _c_WhileStatement          while → 循环跳转
│   ├── _c_ForInStatement          for-in → 编译为 while + index 等价循环
│   ├── _c_SwitchStatement         switch → 编译为 if-else 链
│   ├── _c_ReturnStatement         return → RETURN / RETURN_NULL
│   ├── _c_BreakStatement          break → BREAK
│   ├── _c_ContinueStatement       continue → CONTINUE
│   ├── _c_FuncDecl                函数 → 子 CodeObject + MAKE_FUNC
│   ├── _c_StructDecl              结构体 → 记录定义
│   └── _c_ImportDecl              import → IMPORT
│
└── 表达式编译
    ├── _c_IntLiteral              整数 → LOAD_CONST
    ├── _c_FloatLiteral            浮点 → LOAD_CONST
    ├── _c_StringLiteral           字符串 → LOAD_CONST
    ├── _c_BoolLiteral             布尔 → LOAD_CONST
    ├── _c_Identifier              标识符 → LOAD_NAME
    ├── _c_ArrayLiteral            数组 → 编译所有元素 + BUILD_ARRAY
    ├── _c_BinaryOp                二元运算（含短路逻辑的特殊处理）
    ├── _c_UnaryOp                 一元运算
    ├── _c_CallExpr                函数调用 → 编译参数 + CALL
    ├── _c_MemberAccess            成员访问 → MEMBER_GET
    ├── _c_IndexAccess             下标访问 → INDEX_GET
    ├── _c_Assignment              赋值 → 编译值 + STORE_NAME
    └── _c_CompoundAssignment      复合赋值 → LOAD + 运算 + STORE
```

**关键编译策略**：
- **短路逻辑**：`&&` 和 `||` 使用 `JUMP_IF_FALSE_OR_POP` 和 `JUMP_IF_TRUE_OR_POP` 实现短路
- **for-in 编译**：转换为等价的 while + index 循环
- **函数编译**：每个函数生成独立的 `CodeObject`，通过 `MAKE_FUNC` 创建闭包
- **回填（Backpatching）**：先发出跳转指令占位，编译完目标位置后再回填地址

### 2.3 `zlangx/vm.py` — 栈式字节码虚拟机（~300 行）

```
XVM
├── run(code)                      执行入口
├── _execute(code, env)            核心指令派发循环
│   ├── 栈操作分支
│   ├── 算术运算分支
│   ├── 比较运算分支
│   ├── 跳转分支
│   ├── 函数调用分支
│   ├── 数组操作分支
│   ├── 结构体操作分支
│   ├── 控制流信号分支
│   ├── 内置函数分支
│   ├── 导入分支
│   └── 停机分支
└── _do_import(module_path, env)   模块导入实现
```

**执行模型**：
- **操作数栈**：每个 `_execute` 调用拥有独立的栈
- **环境**：使用 Python 字典 `{name: value}` 而非 `Environment` 对象
- **指令指针 ip**：顺序递增，跳转指令直接修改 ip
- **函数调用**：递归调用 `_execute()`（每层调用有独立栈和 ip）

**性能优化点**（相比树遍历）：
- 扁平指令数组，顺序执行，无递归 AST 遍历
- if/elif 整数比较派发，比 `getattr` 反射快
- 控制流用 ip 跳转，无需 Python 异常开销
- 字典环境，减少对象创建

### 2.4 `zlangx/__main__.py` — CLI 入口（~120 行）

| 命令 | 用法 | 功能 |
|------|------|------|
| `run` | `python -m zlangx run <file> [-v]` | 字节码编译 + 执行（`-v` 显示字节码） |
| `bytecode` | `python -m zlangx bytecode <file>` | 查看生成的字节码 |
| `bench` | `python -m zlangx bench <file> [-n N]` | 性能对比：树遍历 vs 字节码 |

---

## 3. Go 实现（`src/golang/`）

Go 版本与 Python `zlang` 架构完全一致（树遍历解释器），用 Go 重写以获得原生性能。

### 3.1 文件对应关系

| Go 文件 | Python 对应 | 说明 |
|---------|------------|------|
| `token.go` | `token.py` | Token 类型常量 + Token 结构体 |
| `lexer.go` | `lexer.py` | 词法分析器 |
| `ast.go` | `ast.py` | AST 节点定义（使用 Node 接口） |
| `parser.go` | `parser.py` | 递归下降语法分析器 |
| `vm.go` | `vm.py` | 树遍历解释器 |
| `main.go` | `__main__.py` | CLI 入口 + bench 命令 |

### 3.2 Go 与 Python 实现的主要差异

| 方面 | Python | Go |
|------|--------|-----|
| Token 类型 | `Enum` 类 | `const iota` |
| AST 节点 | `@dataclass` 类 | 结构体 + `Node` 接口 |
| 错误处理 | `raise Exception` | `panic` + `recover` |
| 变量作用域 | `Environment` 类 | `Environment` 结构体 |
| 数组 | Python `list` | `ZArray` 包装类型（支持原地 append） |
| 值表示 | Python 动态类型 | `interface{}` |
| 控制流信号 | Python `Exception` | Go `struct` + `panic/recover` |
| 内置函数 | Python 函数 | `ZBuiltinFunc` 类型 |
| 模块缓存 | 实例属性 `_loaded_modules` | 包级变量 `loadedModules` |

### 3.3 Go 特有设计

**ZArray 包装类型**：

Go 中 `append()` 返回新切片而非原地修改。为了实现 `push()` 的原地修改语义，使用 `ZArray` 包装：

```go
type ZArray struct {
    Elements []interface{}
}
```

**错误恢复模式**：

Go 版在 CLI 层使用 `defer/panic/recover` 模式替代 Python 的 `try/except`：

```go
defer func() {
    if r := recover(); r != nil {
        // 统一处理 LexerError, ParseError, ZLangError
    }
}()
```

---

## 4. 测试（`src/python/tests/`）

### 4.1 `test_lexer.py` — 词法分析器测试（21 个）

覆盖：Token 类型识别、运算符、关键字、字符串转义、注释、错误处理。

### 4.2 `test_parser.py` — 语法分析器测试（33 个）

覆盖：表达式解析、语句解析、声明解析、运算符优先级、嵌套结构、错误恢复。

### 4.3 `test_vm.py` — 虚拟机测试（48 个）

覆盖：算术运算、变量、控制流（if/for/while/switch）、函数与递归、闭包、结构体、数组、作用域、break/continue/return。

**运行测试**：

```bash
cd src/python
pip install pytest
python -m pytest tests/ -v
```
