# ZLang 编译器设计文档

## 1. 项目概述

ZLang 是一个教学型编程语言，包含完整的**词法分析器（Lexer）**、**语法分析器（Parser）**和**虚拟机解释器（VM）**。提供 Python 和 Go 两种实现，整个编译流程为：

```
源代码 (.zl) → [Lexer] → Token 流 → [Parser] → AST → [VM] → 执行结果
```

项目提供三个执行后端：

| 后端 | 路径 | 语言 | 执行方式 | 相对性能 |
|------|------|------|---------|---------|
| VM | `python/zlang/` | Python | 树遍历 | 1x |
| XVM | `python/zlangx/` | Python | 字节码栈式 VM | 1.7x |
| Go VM | `src/golang/` | Go | 树遍历 | 20x |

本项目采用经典的**三段式编译器架构**，每一层职责清晰、互相解耦：

| 阶段 | 模块 | 输入 | 输出 | 职责 |
|------|------|------|------|------|
| 前端-词法分析 | `lexer.py` | 源码字符串 | Token 列表 | 字符级扫描，识别词法单元 |
| 前端-语法分析 | `parser.py` | Token 列表 | AST（抽象语法树） | 按文法规则构建语法树 |
| 后端-执行 | `vm.py` | AST | 运行结果 | 遍历 AST，解释执行 |

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    CLI 入口层                         │
│                  __main__.py                         │
│         (run / repl / tokens / ast)                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                   编译器前端                          │
│                                                      │
│  ┌──────────┐    Token[]    ┌──────────┐    AST      │
│  │  Lexer   │ ──────────▶  │  Parser  │ ──────▶    │
│  │lexer.py  │               │parser.py │             │
│  └──────────┘               └──────────┘             │
│                                                      │
│  支撑模块: token.py (Token类型)  ast.py (AST节点)     │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                  编译器后端                           │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │           VM (虚拟机 / 解释器)                │    │
│  │              vm.py                           │    │
│  │                                              │    │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────┐ │    │
│  │  │ 环境系统  │  │ 执行引擎  │  │ 模块系统   │ │    │
│  │  │Environment│  │ _exec/_eval│ │ import     │ │    │
│  │  └──────────┘  └──────────┘  └───────────┘ │    │
│  │                                              │    │
│  │  内置函数: print, len, push, typeof, str...  │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                 标准库 & 示例                         │
│     std/math.zl  std/utils.zl  examples/*.zl        │
└──────────────────────────────────────────────────────┘
```

---

## 3. 词法分析器（Lexer）

### 3.1 职责

将源代码的**字符流**转换为**Token 流**。这是编译器的第一道工序，负责：

- 识别关键字（`let`, `fn`, `if`, `while` 等）
- 识别标识符（变量名、函数名）
- 识别字面量（整数、浮点数、字符串、布尔值）
- 识别运算符和界符
- 过滤空白和注释
- 记录每个 Token 的行列号（用于错误定位）

### 3.2 设计要点

#### 逐字符扫描（Character-by-Character Scanning）

Lexer 维护一个 `pos` 指针，逐字符前进，通过 `_peek()` 预读和 `_advance()` 消费：

```python
def _peek(self, offset=0):     # 查看字符，不移动指针（向前看）
    idx = self.pos + offset
    return self.source[idx] if idx < len(self.source) else "\0"

def _advance(self):            # 消费字符，移动指针
    ch = self._peek()
    self.pos += 1
    # 同步更新行号、列号
    return ch
```

**向前看（Lookahead）** 是词法分析的核心能力：
- 识别 `==` 需要向前看 1 个字符（看到 `=` 后再看下一个是不是 `=`）
- 识别 `//` 注释同样需要向前看

#### Token 分类策略

```
字符流
  │
  ├─ 数字开头? ──→ _read_number() ──→ INT 或 FLOAT
  │
  ├─ 引号开头? ──→ _read_string() ──→ STRING（处理转义）
  │
  ├─ 字母/_开头? ──→ _read_identifier() ──→ 查关键字表
  │                                      ├─ 命中 → 关键字 Token
  │                                      └─ 未命中 → IDENT Token
  │
  ├─ 运算符? ──→ 先消费首字符，再 _match() 看第二个
  │              如: '+' 后看 '=' → PLUS_ASSIGN
  │
  ├─ 界符? ──→ 直接映射 (, ), {, }, [, ], ,, :, ;, .
  │
  ├─ 换行? ──→ NEWLINE（合并连续换行）
  │
  └─ 其他 ──→ 抛出 LexerError
```

#### 换行符作为语句分隔符

ZLang 中换行符（`\n`）是语义相关的——它充当语句分隔符，类似 Go 的设计。这要求 Lexer 将换行作为 Token 输出（而非简单丢弃），同时合并连续空行避免冗余。

### 3.3 关键数据结构

```python
@dataclass
class Token:
    type: TokenType   # Token 类型枚举
    value: any        # 字面值（如 42, "hello", true）
    line: int         # 所在行号
    col: int          # 所在列号
```

### 3.4 文件位置

核心代码：`zlang/lexer.py`（约 220 行）
类型定义：`zlang/token.py`

---

## 4. 语法分析器（Parser）

### 4.1 职责

将 Token 流按照文法规则构建为 **AST（抽象语法树）**。AST 是源代码的结构化表示，去掉了无意义的细节（如括号、分号），保留了语义结构。

### 4.2 解析方法：递归下降（Recursive Descent）

ZLang 采用**递归下降解析**，即为每个文法规则编写一个独立的解析方法。每个方法：

1. 查看当前 Token 决定走哪条分支
2. 消费匹配的 Token
3. 递归调用子规则方法
4. 返回 AST 节点

```
parse() → _top_level() → _statement() → _if_stmt()
                                         ↓
                                    _expression()
                                         ↓
                                    _assignment()
                                         ↓
                                    _logic_or()
                                         ↓
                                       ...
                                         ↓
                                    _primary()
```

### 4.3 运算符优先级（Precedence Climbing）

表达式的解析通过**优先级分层**实现，每一层处理一个优先级的运算符：

```
优先级从低到高:
  assignment    =   +=  -=
  logic_or      ||
  logic_and     &&
  equality      ==  !=
  comparison    <  >  <=  >=
  addition      +  -
  multiplication *  /  %
  unary         !  -
  postfix       函数调用()  成员访问.  下标[]
  primary       字面量  标识符  括号
```

**为什么这样分层？** 因为 `1 + 2 * 3` 应该解析为 `1 + (2 * 3)`。乘法优先级更高，所以在更深层的方法中解析。调用链为：

```
_expression() → _assignment() → _logic_or() → _logic_and()
→ _equality() → _comparison() → _addition() → _multiplication()
→ _unary() → _postfix() → _primary()
```

每层方法的模式相同：

```python
def _addition(self):
    left = self._multiplication()       # 先解析更高优先级
    while tok := self._match(T.PLUS, T.MINUS):  # 然后看有没有本层运算符
        right = self._multiplication()   # 右边也要先解析更高优先级
        left = BinaryOp(tok.value, left, right)  # 左结合
    return left
```

### 4.4 辅助方法

```python
_peek()         # 查看当前 Token，不消费
_advance()      # 消费当前 Token，返回它
_expect(type)   # 期望当前 Token 类型，不匹配则报错
_match(*types)  # 如果匹配则消费，返回 Token 或 None
_skip_newlines() # 跳过换行 Token
```

### 4.5 关键设计决策

**赋值的右结合性**：`a = b = c` 应解析为 `a = (b = c)`，通过递归调用 `_assignment()` 实现：

```python
def _assignment(self):
    expr = self._logic_or()
    if self._match(T.ASSIGN):
        value = self._assignment()  # 递归！右结合
        return Assignment(expr, value)
    return expr
```

**匿名函数作为表达式**：`fn(x) { return x * 2 }` 可以出现在任何表达式位置（如函数参数），通过在 `_primary()` 中识别 `fn` 关键字实现。

### 4.6 文件位置

核心代码：`zlang/parser.py`（约 420 行）
AST 定义：`zlang/ast.py`

---

## 5. 抽象语法树（AST）

### 5.1 设计原则

AST 的节点设计遵循以下原则：

- **每种语法结构一个类**：`IfStatement`、`BinaryOp`、`FuncDecl` 等
- **统一基类**：所有节点继承 `ASTNode`
- **使用 dataclass**：自动生成 `__init__`，减少样板代码
- **表达式与语句分离**：表达式有值（如 `1 + 2`），语句没有（如 `let x = 1`）

### 5.2 AST 节点层次

```
ASTNode（基类）
│
├── 类型
│   └── TypeExpr              类型注解
│
├── 表达式（有返回值）
│   ├── IntLiteral            整数字面量
│   ├── FloatLiteral          浮点数字面量
│   ├── StringLiteral         字符串字面量
│   ├── BoolLiteral           布尔字面量
│   ├── Identifier            标识符引用
│   ├── ArrayLiteral          数组字面量
│   ├── BinaryOp              二元运算
│   ├── UnaryOp               一元运算
│   ├── CallExpr              函数调用
│   ├── MemberAccess          成员访问 (obj.field)
│   ├── IndexAccess           下标访问 (arr[i])
│   ├── Assignment            赋值 (x = v)
│   └── CompoundAssignment    复合赋值 (x += v)
│
├── 语句（无返回值）
│   ├── ExprStatement         表达式语句
│   ├── LetStatement          变量声明
│   ├── Block                 代码块
│   ├── IfStatement           条件语句
│   ├── ForInStatement        for-in 循环
│   ├── WhileStatement        while 循环
│   ├── SwitchStatement       switch 语句
│   ├── ReturnStatement       return 语句
│   ├── BreakStatement        break 语句
│   └── ContinueStatement     continue 语句
│
├── 声明
│   ├── FuncDecl              函数声明
│   ├── StructDecl            结构体声明
│   └── ImportDecl            导入声明
│
└── Program                   程序根节点
```

### 5.3 AST 示例

源代码：

```zlang
let x = 1 + 2 * 3
```

对应的 AST 结构：

```
Program
  LetStatement(name="x", type_ann=None)
    init:
      BinaryOp(op="+")
        left: IntLiteral(1)
        right: BinaryOp(op="*")
                 left: IntLiteral(2)
                 right: IntLiteral(3)
```

可以使用 `python -m zlang ast <file>` 查看任意 ZLang 程序的 AST。

---

## 6. 虚拟机 / 解释器（VM）

### 6.1 执行模型

ZLang 采用**树遍历解释器（Tree-Walking Interpreter）**模式：直接遍历 AST 节点并执行，不生成中间字节码。

执行流程：

```
Program
  └── _exec(stmt, env) → 根据 AST 节点类型分派
        ├── LetStatement → env.define(name, eval(init))
        ├── IfStatement  → 判断条件 → exec_block(then/else)
        ├── ForInStatement → 遍历数组 → exec_block(body)
        ├── FuncDecl     → 创建 ZFunction → env.define(name, fn)
        └── ...

表达式求值：
  _eval(expr, env) → 根据 AST 节点类型分派
        ├── BinaryOp    → eval(left) op eval(right)
        ├── CallExpr    → eval(callee), eval(args) → 调用函数
        ├── Identifier  → env.get(name)
        └── ...
```

### 6.2 作用域系统（Environment）

作用域是编译器中最重要的概念之一。ZLang 采用**词法作用域（Lexical Scoping）**，通过链式 Environment 实现：

```
全局环境 (global_env)
  │  print, len, ...
  │
  ├── 函数环境 (fn_env)
  │     │  a = 10, b = 20
  │     │
  │     ├── 块环境 (block_env)
  │     │     └── x = 42
  │     │
  │     └── 循环环境 (loop_env)
  │           └── item = "apple"
  │
  └── 另一个函数环境 ...
```

**查找规则**：

```python
def get(self, name):
    if name in self.vars:      # 先在当前作用域找
        return self.vars[name]
    if self.parent:            # 找不到，向父作用域找
        return self.parent.get(name)
    raise Error                # 全都找不到，报错
```

**块作用域隔离**：每个 `{ }` 块创建新的子环境，块内定义的变量不会泄漏到外层：

```zlang
let x = 1
if true {
    let x = 99    // 块作用域内的 x，不影响外层
}
print(x)          // 输出 1，不是 99
```

### 6.3 闭包（Closure）

闭包是函数与其定义时环境的组合。ZLang 中每个函数都捕获其定义时的 Environment：

```zlang
fn make_counter(start) {
    let count = start          // count 存在于 make_counter 的环境中
    fn increment() {
        count += 1             // increment 闭包捕获了这个环境
        return count
    }
    return increment           // 返回函数，它"记住"了 count
}
```

实现原理：

```python
# 函数声明时，记录当前环境作为闭包
fn = ZFunction(name, params, body, closure=当前env)

# 函数调用时，基于闭包创建新的调用环境
call_env = Environment(parent=fn.closure)
```

关键点：函数被返回后，它仍然持有对定义时环境的引用，所以 `count` 变量不会被销毁。

### 6.4 控制流的实现

break / continue / return 通过 **Python 异常** 实现跨层跳转：

```
for 循环体
  └── exec(stmt)
        └── if 语句
              └── break 语句
                    └── raise BreakSignal   ← 异常穿透多层调用
                          ↑
for 循环捕获 ──────────────┘
  except BreakSignal: break
```

这种设计的优势是不需要在每个执行方法中检查返回值，代码更简洁。劣势是异常创建有一定性能开销。

### 6.5 函数调用流程

```
调用 foo(1, 2)
  │
  ▼
eval(CallExpr)                    # 1. 求值 callee → ZFunction
  │                               # 2. 求值所有参数
  ▼
eval(args) → [1, 2]
  │
  ▼
_call_function(fn, [1, 2])
  │
  ├── 检查参数数量
  ├── 创建调用环境: Environment(parent=fn.closure)
  ├── 绑定参数: call_env.define("a", 1), call_env.define("b", 2)
  ├── 执行函数体: _exec_block(fn.body, call_env)
  │     └── 遇到 return → raise ReturnSignal(value)
  │
  └── except ReturnSignal → 返回 value
```

### 6.6 结构体实例化

ZLang 的结构体没有类和继承，是简单的数据容器：

```
struct Point { x: float, y: float }

let p = Point()    // 调用 StructDecl 节点 → 创建 ZStructInstance
p.x = 3.0          // MemberAccess 赋值 → instance.fields["x"] = 3.0
print(p.x)         // MemberAccess 读取 → instance.fields["x"]
```

### 6.7 模块导入系统

```
import std.math
  │
  ▼
_exec_ImportDecl()
  │
  ├── _load_module("std.math")
  │     │
  │     ├── 检查缓存（已加载则直接返回）
  │     ├── resolve_import("std.math")
  │     │     └── "std.math" → "std/math.zl" → 读取源码
  │     ├── Lexer(source) → Parser(tokens) → AST
  │     ├── 在独立环境中执行 AST
  │     └── 收集非内置函数的变量作为导出符号
  │
  └── 将导出符号注入当前环境: env.define(name, value)
```

模块只加载一次，后续 import 命中缓存（单例模式）。

### 6.8 逻辑运算与短路求值

ZLang 支持 `&&`（逻辑与）、`||`（逻辑或）、`!`（逻辑非）三种逻辑运算符。

**短路求值（Short-Circuit Evaluation）** 是逻辑运算的核心优化：

```python
# && 短路：左边为假值时直接返回左边，不计算右边
if node.op == "&&":
    left = self._eval(node.left, env)
    return left if not self._is_truthy(left) else self._eval(node.right, env)

# || 短路：左边为真值时直接返回左边，不计算右边
if node.op == "||":
    left = self._eval(node.left, env)
    return left if self._is_truthy(left) else self._eval(node.right, env)
```

短路求值的实际意义：
- **性能优化**：避免不必要的计算
- **安全防护**：`if arr && len(arr) > 0` 避免对空值调用 len
- **逻辑正确性**：`if ptr && ptr.value` 先检查指针是否为空

**真假规则（Truthiness）**：

```
假值: null, false, 0, 0.0, "", []
真值: 除假值外的所有值（包括负数、非空字符串、非空数组等）
```

**运算符优先级**：`!` > `&&` > `||`

```
!a && b || c    等价于    ((!a) && b) || c
```

### 6.9 文件位置

核心代码：`zlang/vm.py`（约 560 行）

---

## 7. 语言特性对照

| 特性 | 语法 | AST 节点 | VM 方法 |
|------|------|----------|---------|
| 变量 | `let x = 1` | `LetStatement` | `_exec_LetStatement` |
| 赋值 | `x = 2` | `Assignment` | `_eval_Assignment` |
| 复合赋值 | `x += 1` | `CompoundAssignment` | `_eval_CompoundAssignment` |
| 条件 | `if/else` | `IfStatement` | `_exec_IfStatement` |
| for-in | `for x in arr {}` | `ForInStatement` | `_exec_ForInStatement` |
| while | `while cond {}` | `WhileStatement` | `_exec_WhileStatement` |
| switch | `switch/case` | `SwitchStatement` | `_exec_SwitchStatement` |
| 逻辑与 | `a && b` | `BinaryOp("&&")` | `_eval_BinaryOp`（短路） |
| 逻辑或 | `a \|\| b` | `BinaryOp("\|\|")` | `_eval_BinaryOp`（短路） |
| 逻辑非 | `!a` | `UnaryOp("!")` | `_eval_UnaryOp` |
| 函数 | `fn f() {}` | `FuncDecl` | `_exec_FuncDecl` |
| 匿名函数 | `fn(x) {}` | `FuncDecl(name="")` | `_eval_FuncDecl` |
| 闭包 | 嵌套函数 | `FuncDecl` + `Environment` | `_call_function` |
| 结构体 | `struct S {}` | `StructDecl` | `_exec_StructDecl` |
| 数组 | `[1, 2]` | `ArrayLiteral` | `_eval_ArrayLiteral` |
| 导入 | `import x.y` | `ImportDecl` | `_exec_ImportDecl` |
| break | `break` | `BreakStatement` | `_exec_BreakStatement` |
| continue | `continue` | `ContinueStatement` | `_exec_ContinueStatement` |
| return | `return x` | `ReturnStatement` | `_exec_ReturnStatement` |

---

## 8. 错误处理体系

ZLang 的错误分三个层级，对应编译器的三个阶段：

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ LexerError  │   │ ParseError  │   │  ZLangError │
│  词法错误    │   │  语法错误    │   │  运行时错误  │
└─────────────┘   └─────────────┘   └─────────────┘
  非法字符          缺少括号           未定义变量
  未闭合字符串       缺少分号           类型错误
  非法运算符         意料的Token        除零错误
```

每个错误都包含**位置信息**（行号、列号），方便用户定位问题。

---

## 9. 测试体系

```
tests/
├── test_lexer.py    21 个测试   Token类型、运算符、关键字、注释、错误处理
├── test_parser.py   33 个测试   表达式、语句、声明、运算符优先级、错误恢复
└── test_vm.py       48 个测试   算术、变量、控制流、函数、结构体、数组、作用域
                   ─────────
                   102 个测试
```

测试策略：每一层独立测试，上层测试不依赖底层实现细节。

---

## 10. 关键知识点整理

### 10.1 编译原理核心概念

**词法分析（Lexical Analysis / Scanning）**

| 概念 | 说明 | 本项目对应 |
|------|------|-----------|
| Token | 最小的不可分割的词法单元 | `Token` dataclass |
| Lookahead | 向前看字符，用于区分 `=` 和 `==` | `_peek(offset)` |
| 关键字表 | 将保留字映射为特定 Token 类型 | `KEYWORDS` 字典 |
| 转义序列 | `\n`, `\t` 等在字符串中的处理 | `_read_string()` 中的 `escape_map` |
| 正则 vs 手写 | 两种词法分析方式 | 本项目采用手写扫描器 |

**语法分析（Syntax Analysis / Parsing）**

| 概念 | 说明 | 本项目对应 |
|------|------|-----------|
| 文法（Grammar） | 描述语言结构的规则 | 模块顶部注释中的 BNF |
| 递归下降 | 为每条文法规则写一个方法 | Parser 类的所有 `_xxx()` 方法 |
| LL(1) | 从左到右扫描，左推导，1 个 Token 向前看 | 本项目的解析策略 |
| 运算符优先级 | 不同运算符的绑定强度 | 从 `_assignment` 到 `_primary` 的调用链 |
| 左结合 vs 右结合 | 同优先级运算符的分组方向 | 赋值右结合（递归），其他左结合（循环） |
| 歧义消除 | 同一串 Token 可能有多种解析方式 | 优先级分层天然消除歧义 |
| FIRST 集 | 每条文法规则可以由哪些 Token 开头 | `_statement()` 中的 `if tok.type ==` 判断 |

**抽象语法树（AST）**

| 概念 | 说明 |
|------|------|
| 具体语法树 vs 抽象语法树 | CST 保留所有细节（括号、分号），AST 只保留语义结构 |
| 访问者模式 | 遍历 AST 的经典设计模式（本项目用方法分派简化实现） |
| 语法导向翻译 | 每条文法规则对应一种 AST 节点 |

### 10.2 编程语言设计概念

**作用域（Scope）**

| 概念 | 说明 | 本项目对应 |
|------|------|-----------|
| 词法作用域 | 函数的定义位置决定可访问的变量 | `Environment` 链式查找 |
| 动态作用域 | 函数的调用位置决定可访问的变量 | 本项目未采用 |
| 块作用域 | `{ }` 内的变量只在块内可见 | `_exec_block()` 创建子 Environment |
| 全局作用域 | 整个程序共享的最外层环境 | `Interpreter.global_env` |
| 自由变量 | 函数内引用但未在函数内定义的变量 | 闭包中 `count` 就是自由变量 |

**闭包（Closure）**

```
闭包 = 函数代码 + 定义时的环境引用

关键特性：
1. 函数可以"记住"定义时的变量（即使定义环境已出栈）
2. 每次调用外层函数会创建新的闭包（独立的变量空间）
3. 闭包是实现高阶函数、回调、状态封装的基础
```

**类型系统**

| 概念 | 说明 | 本项目对应 |
|------|------|-----------|
| 动态类型 | 运行时才确定变量类型 | ZLang 采用动态类型 |
| 静态类型 | 编译时确定变量类型 | ZLang 的类型注解仅供文档用 |
| 强类型 | 不允许隐式类型转换 | `+` 运算报错而非自动转换 |
| 弱类型 | 允许隐式类型转换 | `"3" + 2` 可能为 `"32"` 或 `5` |
| 类型注解 | 可选的类型标记 | `let x: int = 42`（当前不强制） |

### 10.3 解释器实现模式

**树遍历解释器（Tree-Walking Interpreter）**

```
优点: 实现简单，代码直观，适合教学
缺点: 每次执行都重新遍历 AST，性能较差
代表: Ruby（早期）、Lua（早期）、Python（CPython 参考实现）
```

**字节码解释器（Bytecode Interpreter）**

```
优点: 编译一次，执行多次；字节码更紧凑，可优化
缺点: 需要额外的编译阶段和虚拟机
代表: Python（CPython）、Java（JVM）、Lua（Lua 5.0+）
流程: 源码 → AST → 字节码 → 栈式VM执行
```

**JIT 编译器（Just-In-Time Compiler）**

```
优点: 运行时将热点代码编译为机器码，性能接近原生
缺点: 实现复杂，启动慢，内存占用大
代表: V8（JavaScript）、PyPy（Python）、HotSpot（Java）
```

**AOT 编译器（Ahead-Of-Time Compiler）**

```
优点: 编译为机器码，运行时零开销
缺点: 编译慢，平台相关
代表: GCC（C）、rustc（Rust）、Go compiler
流程: 源码 → AST → IR → 优化 → 机器码
```

### 10.4 设计模式

| 模式 | 应用场景 | 本项目对应 |
|------|---------|-----------|
| 策略模式 | 根据节点类型选择执行策略 | `_exec` / `_eval` 的方法分派 |
| 责任链模式 | 作用域链的变量查找 | `Environment.get()` 沿 parent 链查找 |
| 工厂方法 | 创建不同类型的 AST 节点 | Parser 中各 `_xxx()` 方法 |
| 单例模式 | 模块只加载一次 | `_loaded_modules` 缓存 |
| 解释器模式 | 执行语法树 | 整个 VM 本质上就是解释器模式 |
| 访问者模式 | 区分不同类型的 AST 节点 | `getattr(self, f"_exec_{type(node).__name__}")` |

### 10.5 工程实践

**关注点分离（Separation of Concerns）**

Lexer 只关心字符→Token，Parser 只关心 Token→AST，VM 只关心 AST→执行。三层互不依赖内部实现，仅通过数据结构（Token 列表、AST）通信。

**错误恢复（Error Recovery）**

词法/语法错误提供精确的行列号定位。运行时错误通过异常传播，携带上下文信息。

**可扩展性**

添加新语法特性的步骤：
1. `token.py` 添加新 Token 类型
2. `lexer.py` 添加识别规则
3. `ast.py` 添加新 AST 节点
4. `parser.py` 添加解析方法
5. `vm.py` 添加执行/求值方法

每步只修改一个文件，影响范围可控。

---

## 11. 性能分析与优化方向

### 11.1 当前性能瓶颈

| 瓶颈 | 原因 | 影响 |
|------|------|------|
| AST 遍历开销 | 每次执行都递归遍历 Python 对象 | 比字节码 VM 慢 5-10x |
| 动态方法分派 | `getattr()` 字符串查找 | 每个节点一次反射调用 |
| 异常做控制流 | `break`/`return` 用 Python 异常 | 异常对象创建开销大 |
| Python 对象开销 | 每个 int/string 都是 Python 对象 | 内存占用高 |

### 11.2 优化路线

```
Python 树遍历           Python 字节码            Go 原生
源码                    源码                     源码
 ↓                       ↓                        ↓
AST ──→ 直接执行        AST ──→ 字节码           AST ──→ 直接执行
                          ↓                     (编译为机器码)
                       栈式VM执行
```

实际性能对比（综合基准测试，50 次迭代取均值）：

| 版本 | 每次耗时 | 相对性能 |
|------|---------|---------|
| zlang（Python 树遍历） | ~2.8s | 1x |
| zlangx（Python 字节码） | ~1.3s | 1.7x |
| golang（Go 原生） | ~0.14s | **20x** |

Go 版本的核心优势：
- 编译为原生机器码，无 Python 解释器开销
- `interface{}` + 类型断言替代 Python 动态类型
- `defer/recover` 高效处理控制流（break/continue/return）
- `ZArray` 包装类型实现数组原地修改

---

## 12. 目录结构总览

```
compiler-demo/
├── src/                              编译器实现
│   ├── python/                       Python 实现
│   │   ├── zlang/                    树遍历解释器
│   │   │   ├── __init__.py           包入口
│   │   │   ├── __main__.py           CLI 命令行工具
│   │   │   ├── token.py              Token 类型与关键字定义
│   │   │   ├── lexer.py              词法分析器
│   │   │   ├── ast.py                AST 节点定义（25 种）
│   │   │   ├── parser.py             语法分析器（递归下降）
│   │   │   └── vm.py                 虚拟机 / 解释器
│   │   ├── zlangx/                   字节码虚拟机
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py           CLI 入口
│   │   │   ├── bytecode.py           字节码指令定义
│   │   │   ├── compiler.py           AST → 字节码编译器
│   │   │   └── vm.py                 栈式字节码虚拟机
│   │   └── tests/                    测试用例（102 个）
│   │       ├── test_lexer.py         词法分析测试（21 个）
│   │       ├── test_parser.py        语法分析测试（33 个）
│   │       └── test_vm.py            执行引擎测试（48 个）
│   └── golang/                       Go 高性能实现
│       ├── go.mod
│       ├── token.go                  Token 类型定义
│       ├── lexer.go                  词法分析器
│       ├── ast.go                    AST 节点定义
│       ├── parser.go                 语法分析器
│       ├── vm.go                     树遍历解释器
│       └── main.go                   CLI 入口
├── examples/                         示例程序 & 标准库
│   ├── hello.zl                      基础语法
│   ├── control_flow.zl               控制流
│   ├── functions.zl                  函数与闭包
│   ├── structs.zl                    结构体
│   ├── import_demo.zl                模块导入
│   ├── bench.zl                      性能基准测试
│   ├── bench_loop.zl                 纯循环微基准
│   └── std/                          标准库（用 ZLang 自身编写）
│       ├── math.zl                   数学函数
│       └── utils.zl                  工具函数
├── doc/                              设计文档
│   └── design.md                     本文档
└── README.md                         项目说明
```
