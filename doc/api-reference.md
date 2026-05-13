# ZLang 语言参考手册

本文档是 ZLang 语言的完整语法和功能参考。

---

## 1. 数据类型

| 类型 | 关键字 | 示例 | 说明 |
|------|--------|------|------|
| 整数 | `int` | `42`, `-7`, `0` | 任意精度整数 |
| 浮点数 | `float` | `3.14`, `-0.5` | 双精度浮点数 |
| 字符串 | `string` | `"hello"`, `"世界\n"` | 双引号，支持转义 |
| 布尔值 | `bool` | `true`, `false` | 逻辑真/假 |
| 数组 | `array` | `[1, 2, 3]` | 动态长度，异构元素 |
| 空值 | `null` | `null` | 表示"没有值" |

### 类型注解（可选）

ZLang 支持可选的类型注解，当前仅作文档用途，不参与类型检查：

```zlang
let x: int = 42
let name: string = "ZLang"
let nums: []int = [1, 2, 3]
```

### 真假值规则（Truthiness）

以下值为 **假（falsy）**，其余均为真：

- `null`
- `false`
- `0` / `0.0`
- `""` （空字符串）
- `[]` （空数组）

---

## 2. 变量

使用 `let` 关键字声明变量：

```zlang
let x = 42                  // 自动推断类型
let name: string = "hello"  // 带类型注解
let y                        // 声明但不初始化，值为 null
```

变量赋值和复合赋值：

```zlang
x = 100        // 赋值
x += 5         // 等价于 x = x + 5
x -= 3         // 等价于 x = x - 3
```

**作用域规则**：`let` 声明的变量遵循 **词法作用域**（块作用域），在 `{ }` 内定义的变量不会泄漏到外层。

---

## 3. 运算符

### 3.1 算术运算符

| 运算符 | 含义 | 示例 | 结果 |
|--------|------|------|------|
| `+` | 加法 / 字符串拼接 | `1 + 2` | `3` |
| `-` | 减法 | `5 - 3` | `2` |
| `*` | 乘法 | `3 * 4` | `12` |
| `/` | 除法 | `10 / 3` | `3.333...` |
| `%` | 取模 | `10 % 3` | `1` |
| `-` | 负号（一元） | `-x` | 取反 |

### 3.2 比较运算符

| 运算符 | 含义 | 示例 | 结果 |
|--------|------|------|------|
| `==` | 等于 | `1 == 1` | `true` |
| `!=` | 不等于 | `1 != 2` | `true` |
| `<` | 小于 | `1 < 2` | `true` |
| `>` | 大于 | `2 > 1` | `true` |
| `<=` | 小于等于 | `1 <= 1` | `true` |
| `>=` | 大于等于 | `2 >= 1` | `true` |

> `==` 和 `!=` 为**严格比较**（要求类型和值都相同）。

### 3.3 逻辑运算符

| 运算符 | 含义 | 示例 | 结果 |
|--------|------|------|------|
| `&&` | 逻辑与（短路） | `true && false` | `false` |
| `\|\|` | 逻辑或（短路） | `true \|\| false` | `true` |
| `!` | 逻辑非 | `!true` | `false` |

**短路求值**：
- `&&`：左边为假时直接返回，不再计算右边
- `||`：左边为真时直接返回，不再计算右边

### 3.4 运算符优先级

从低到高排列：

| 优先级 | 运算符 | 结合性 |
|--------|--------|--------|
| 1（最低） | `=` `+=` `-=` | 右结合 |
| 2 | `\|\|` | 左结合 |
| 3 | `&&` | 左结合 |
| 4 | `==` `!=` | 左结合 |
| 5 | `<` `>` `<=` `>=` | 左结合 |
| 6 | `+` `-` | 左结合 |
| 7 | `*` `/` `%` | 左结合 |
| 8 | `!` `-`（一元） | 右结合 |
| 9（最高） | `()` `.` `[]`（后缀） | 左结合 |

---

## 4. 控制流

### 4.1 if / else if / else

```zlang
let score = 85
if score >= 90 {
    print("优秀")
} else if score >= 60 {
    print("及格")
} else {
    print("不及格")
}
```

### 4.2 for-in 循环

遍历数组元素：

```zlang
let fruits = ["苹果", "香蕉", "橙子"]
for fruit in fruits {
    print(fruit)
}
```

### 4.3 while 循环

```zlang
let i = 0
while i < 10 {
    print(i)
    i += 1
}
```

### 4.4 switch / case / default

```zlang
let day = "周一"
switch day {
    case "周一":
        print("工作日")
    case "周六":
        print("周末")
    case "周日":
        print("周末")
    default:
        print("普通工作日")
}
```

### 4.5 break / continue

在 `for-in` 和 `while` 循环中使用：

```zlang
for item in [1, 2, 3, 4, 5] {
    if item == 3 {
        continue    // 跳过本次迭代
    }
    if item == 5 {
        break       // 跳出循环
    }
    print(item)     // 输出: 1, 2, 4
}
```

---

## 5. 函数

### 5.1 函数声明

```zlang
fn add(a, b) {
    return a + b
}
print(add(3, 5))    // 输出: 8
```

支持类型注解和返回值类型：

```zlang
fn multiply(a: int, b: int) -> int {
    return a * b
}
```

### 5.2 递归

```zlang
fn factorial(n) {
    if n <= 1 {
        return 1
    }
    return n * factorial(n - 1)
}
print(factorial(10))    // 输出: 3628800
```

### 5.3 匿名函数 & 闭包

```zlang
// 匿名函数赋值给变量
let double = fn(x) { return x * 2 }
print(double(5))    // 输出: 10

// 闭包：函数"记住"定义时的环境
fn make_counter(start) {
    let count = start
    fn increment() {
        count += 1
        return count
    }
    return increment
}

let counter = make_counter(0)
print(counter())    // 输出: 1
print(counter())    // 输出: 2
print(counter())    // 输出: 3
```

### 5.4 高阶函数

```zlang
fn map(arr, f) {
    let result = []
    for item in arr {
        push(result, f(item))
    }
    return result
}

let nums = [1, 2, 3, 4]
let doubled = map(nums, fn(x) { return x * 2 })
print(doubled)      // 输出: [2, 4, 6, 8]
```

---

## 6. 数组

```zlang
let arr = [1, 2, 3, "hello", true]  // 异构数组

// 访问元素（0-indexed）
print(arr[0])       // 输出: 1

// 修改元素
arr[0] = 99

// 负数索引
print(arr[-1])      // 输出: true（最后一个元素）

// 追加元素
push(arr, "new")
print(len(arr))     // 输出: 6
```

---

## 7. 结构体

```zlang
struct Point {
    x: float
    y: float
}

let p = Point()     // 实例化
p.x = 3.0          // 设置字段
p.y = 4.0
print(p.x)         // 访问字段，输出: 3.0

// 结构体数组
let points = []
push(points, Point())
points[0].x = 1.0
points[0].y = 2.0
```

> ZLang 的结构体是纯数据容器，没有方法和继承。可以用函数来模拟方法行为。

---

## 8. 模块导入

```zlang
import std.math
import std.utils

// 导入后，模块导出的函数和常量可直接使用
print(std_math_abs(-42))      // 输出: 42
print(std_math_pow(2, 10))    // 输出: 1024
print(std_utils_repeat("Hi", 3))  // 输出: HiHiHi
```

**导入规则**：
- 使用点分路径：`import std.math` 对应文件 `std/math.zl`
- 模块只会加载一次（缓存机制）
- 模块中所有非内置函数的变量都会被导出

---

## 9. 注释

```zlang
// 单行注释

/*
   多行注释
   可以跨越多行
*/
```

---

## 10. 内置函数

| 函数 | 签名 | 说明 | 示例 |
|------|------|------|------|
| `print` | `print(*args)` | 打印值，空格分隔 | `print("x =", 42)` |
| `len` | `len(obj) -> int` | 返回数组或字符串长度 | `len([1,2,3])` → `3` |
| `push` | `push(arr, val) -> array` | 向数组末尾追加元素 | `push(arr, 4)` |
| `typeof` | `typeof(val) -> string` | 返回类型名称 | `typeof(42)` → `"int"` |
| `str` | `str(val) -> string` | 将值转为字符串 | `str(42)` → `"42"` |
| `int` | `int(val) -> int` | 转换为整数 | `int("42")` → `42` |
| `float` | `float(val) -> float` | 转换为浮点数 | `float("3.14")` → `3.14` |

### `typeof` 返回值

| 输入类型 | 返回字符串 |
|----------|-----------|
| `bool` | `"bool"` |
| `int` | `"int"` |
| `float` | `"float"` |
| `string` | `"string"` |
| `array` | `"array"` |
| `struct` | 结构体名称 |
| `function` | `"function"` |
| `null` | `"null"` |

---

## 11. 标准库

### 11.1 `std/math.zl` — 数学函数

| 导出名称 | 类型 | 说明 |
|----------|------|------|
| `std_math_pi` | 常量 | 圆周率 π ≈ 3.14159 |
| `std_math_abs(x)` | 函数 | 绝对值 |
| `std_math_square(x)` | 函数 | 平方 |
| `std_math_max(a, b)` | 函数 | 最大值 |
| `std_math_min(a, b)` | 函数 | 最小值 |
| `std_math_pow(base, exp)` | 函数 | 整数幂 |

### 11.2 `std/utils.zl` — 工具函数

| 导出名称 | 类型 | 说明 |
|----------|------|------|
| `std_utils_repeat(s, n)` | 函数 | 重复字符串 n 次 |
| `std_utils_clamp(val, min, max)` | 函数 | 限制值在范围内 |
| `std_utils_reverse(arr)` | 函数 | 反转数组 |
| `std_utils_contains(arr, target)` | 函数 | 判断数组是否包含元素 |

---

## 12. 语法速查（BNF 概览）

```
program        = (statement | import_decl)* EOF

import_decl    = "import" IDENT ("." IDENT)* 语句结束

statement      = let_stmt | func_decl | struct_decl
               | if_stmt | for_stmt | while_stmt | switch_stmt
               | return_stmt | break_stmt | continue_stmt
               | expr_stmt

let_stmt       = "let" IDENT (":" type_expr)? ("=" expr)? 语句结束
func_decl      = "fn" IDENT "(" param_list ")" ("->" type_expr)? block
struct_decl    = "struct" IDENT "{" field_list "}"

if_stmt        = "if" expr block ("else" (if_stmt | block))?
for_stmt       = "for" IDENT "in" expr block
while_stmt     = "while" expr block
switch_stmt    = "switch" expr "{" case_clause* "}"
case_clause    = ("case" expr | "default") ":" block

return_stmt    = "return" expr? 语句结束
break_stmt     = "break" 语句结束
continue_stmt  = "continue" 语句结束

expr           = assignment
assignment     = logic_or (("=" | "+=" | "-=") assignment)?
logic_or       = logic_and ("||" logic_and)*
logic_and      = equality ("&&" equality)*
equality       = comparison (("==" | "!=") comparison)*
comparison     = addition (("<" | ">" | "<=" | ">=") addition)*
addition       = multiplication (("+" | "-") multiplication)*
multiplication = unary (("*" | "/" | "%") unary)*
unary          = ("!" | "-") unary | postfix
postfix        = primary ("(" args ")" | "." IDENT | "[" expr "]")*
primary        = INT | FLOAT | STRING | BOOL | IDENT
               | "(" expr ")" | "[" expr_list "]" | "fn" "(" params ")" block

block          = "{" statement* "}"
```

> **语句分隔符**：换行符（`\n`）作为语句分隔符，也支持用分号（`;`）。
