# ZLang — 一个简洁的编程语言 & 编译器

ZLang 是一个用 Python 实现的教学型编程语言，包含完整的 **词法分析器**、**语法分析器（Parser）** 和 **虚拟机解释器（VM）**。

## 特性

| 特性 | 状态 |
|------|------|
| 变量定义 (`let`) | ✅ |
| 数据类型 (int, float, string, bool, array) | ✅ |
| if / else if / else | ✅ |
| for-in 循环 | ✅ |
| while 循环 | ✅ |
| switch / case / default | ✅ |
| 函数定义 & 递归 | ✅ |
| 匿名函数 (闭包) | ✅ |
| 结构体 (struct) | ✅ |
| 数组 (array) | ✅ |
| 文件导入 (import) | ✅ |
| break / continue | ✅ |
| 注释 (// 和 /* */) | ✅ |
| 内置函数 (print, len, push, typeof, str, int, float) | ✅ |

## 快速开始

### 运行程序

```bash
python -m zlang run examples/hello.zl
```

### 交互式 REPL

```bash
python -m zlang repl
```

### 调试

```bash
# 查看词法分析结果
python -m zlang tokens examples/hello.zl

# 查看 AST
python -m zlang ast examples/hello.zl
```

### 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

## 项目结构

```
compiler-demo/
├── zlang/                   # 编译器核心代码
│   ├── __init__.py          # 包入口
│   ├── __main__.py          # CLI 入口 (python -m zlang)
│   ├── token.py             # Token 类型定义
│   ├── lexer.py             # 词法分析器：源码 → Token 流
│   ├── ast.py               # AST 节点定义
│   ├── parser.py            # 语法分析器：Token 流 → AST
│   └── vm.py                # 虚拟机：AST → 执行结果
├── std/                     # 标准库
│   ├── math.zl              # 数学函数库
│   └── utils.zl             # 工具函数库
├── examples/                # 示例程序
│   ├── hello.zl             # 基础语法
│   ├── control_flow.zl      # 控制流
│   ├── functions.zl         # 函数、闭包、高阶函数
│   ├── structs.zl           # 结构体
│   └── import_demo.zl       # 文件导入
├── tests/                   # 测试用例
│   ├── test_lexer.py        # 词法分析器测试
│   ├── test_parser.py       # 语法分析器测试
│   └── test_vm.py           # 虚拟机测试
└── README.md
```

## 语言语法参考

### 变量

```zlang
let x = 42                  // 自动推断类型
let name: string = "Alice"  // 可选类型注解
let pi = 3.14
let flag = true
let arr = [1, 2, 3]
```

### 运算符

```
算术:  +  -  *  /  %
比较:  ==  !=  <  >  <=  >=
逻辑:  &&  ||  !
赋值:  =  +=  -=
```

### 逻辑表达式

ZLang 支持 `&&`（逻辑与）、`||`（逻辑或）、`!`（逻辑非），并采用**短路求值**：

- `&&`：左边为 false 时直接返回，不再计算右边
- `||`：左边为 true 时直接返回，不再计算右边
- `!`：对任意值取反（遵循 ZLang 的真假规则）

```zlang
// 基本逻辑运算
let a = true && false       // false
let b = true || false       // true
let c = !true               // false

// 复合条件判断
let age = 25
let score = 85
if age >= 18 && score >= 60 {
    print("通过")
}
if age < 18 || score < 60 {
    print("未通过")
} else {
    print("合格")
}

// 逻辑非 + 比较运算
if !(score == 100) {
    print("不是满分")
}

// 0、空字符串、空数组、null 视为 false
if !0 { print("0 是假值") }
if !"" { print("空字符串是假值") }
if ![] { print("空数组是假值") }
if !false { print("false 是假值") }
```

### 条件语句

```zlang
if score >= 90 {
    print("A")
} else if score >= 80 {
    print("B")
} else {
    print("C")
}
```

### 循环

```zlang
// for-in 遍历数组
for item in [1, 2, 3] {
    print(item)
}

// while 循环
let i = 0
while i < 10 {
    i += 1
}

// break 和 continue
for n in [1, 2, 3, 4, 5] {
    if n == 3 { continue }
    if n == 5 { break }
    print(n)
}
```

### Switch

```zlang
switch day {
    case "Monday":
        print("工作日开始")
        break
    case "Saturday":
    case "Sunday":
        print("周末!")
        break
    default:
        print("普通的一天")
        break
}
```

### 函数

```zlang
// 基本函数
fn add(a, b) {
    return a + b
}

// 带类型注解
fn greet(name: string) -> string {
    return "Hello, " + name
}

// 递归
fn factorial(n) {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}

// 闭包
fn make_counter(start) {
    let count = start
    fn increment() {
        count += 1
        return count
    }
    return increment
}

// 匿名函数
let doubled = map([1, 2, 3], fn(x) { return x * 2 })
```

### 结构体

```zlang
struct Point {
    x: float
    y: float
}

let p = Point()
p.x = 3.0
p.y = 4.0
print(str(p.x) + ", " + str(p.y))
```

### 数组

```zlang
let arr = [1, 2, 3]
print(arr[0])        // 索引访问
print(arr[-1])       // 负索引
print(len(arr))      // 长度
push(arr, 4)         // 追加元素
arr[1] = 99          // 索引赋值
```

### 导入

```zlang
import std.math
import std.utils

let area = std_math_pi * std_math_square(5.0)
```

### 内置函数

| 函数 | 说明 |
|------|------|
| `print(...)` | 打印值（多参数空格分隔） |
| `len(arr)` | 数组或字符串长度 |
| `push(arr, val)` | 向数组追加元素 |
| `typeof(val)` | 返回类型名称 |
| `str(val)` | 转为字符串 |
| `int(val)` | 转为整数 |
| `float(val)` | 转为浮点数 |

### 注释

```zlang
// 单行注释

/* 多行
   注释 */
```

## 编译器架构

```
源码 (.zl 文件)
    │
    ▼
┌─────────┐
│  Lexer   │  词法分析：字符流 → Token 流
└────┬─────┘
     │  Token[]
     ▼
┌─────────┐
│ Parser  │  语法分析：Token 流 → AST (抽象语法树)
└────┬─────┘
     │  Program AST
     ▼
┌─────────┐
│   VM    │  解释执行：遍历 AST → 运行结果
└─────────┘
```

- **Lexer** (`zlang/lexer.py`): 将源代码文本拆分为 Token 序列，处理关键字、标识符、数字、字符串、运算符等
- **Parser** (`zlang/parser.py`): 递归下降解析器，将 Token 流构建为 AST，支持运算符优先级
- **VM** (`zlang/vm.py`): 树遍历解释器，直接执行 AST 节点，支持作用域、闭包、结构体实例化

## License

MIT
