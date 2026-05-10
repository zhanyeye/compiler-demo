# 标准库（std）

ZLang 的标准库模块，通过 `import` 语句导入使用。

## 导入方式

```zlang
import std.math
import std.utils
```

导入后，模块中导出的所有函数和常量会自动注入当前作用域，可直接使用。

## 模块列表

### [math.zl](math.zl) — 数学函数库

提供常用的数学常量和函数。

| 导出名称 | 类型 | 说明 |
|----------|------|------|
| `std_math_pi` | 常量 | 圆周率 π ≈ 3.141592653589793 |
| `std_math_abs(x)` | 函数 | 绝对值：`abs(-42)` → `42` |
| `std_math_square(x)` | 函数 | 平方：`square(5)` → `25` |
| `std_math_max(a, b)` | 函数 | 最大值：`max(3, 7)` → `7` |
| `std_math_min(a, b)` | 函数 | 最小值：`min(3, 7)` → `3` |
| `std_math_pow(base, exp)` | 函数 | 整数幂：`pow(2, 10)` → `1024` |

**使用示例：**

```zlang
import std.math

let r = 5.0
let area = std_math_pi * std_math_square(r)
print("圆面积: " + str(area))

print("绝对值: " + str(std_math_abs(-42)))
print("2^10 = " + str(std_math_pow(2, 10)))
```

### [utils.zl](utils.zl) — 工具函数库

提供字符串和数组操作的实用工具。

| 导出名称 | 类型 | 说明 |
|----------|------|------|
| `std_utils_repeat(s, n)` | 函数 | 重复字符串 n 次：`repeat("Hi", 3)` → `"HiHiHi"` |
| `std_utils_clamp(val, min, max)` | 函数 | 限制值在范围内：`clamp(150, 0, 100)` → `100` |
| `std_utils_reverse(arr)` | 函数 | 反转数组：`reverse([1,2,3])` → `[3,2,1]` |
| `std_utils_contains(arr, target)` | 函数 | 判断数组是否包含元素：`contains([1,2,3], 2)` → `true` |

**使用示例：**

```zlang
import std.utils

let msg = std_utils_repeat("ZLang", 3)
print(msg)

let val = std_utils_clamp(200, 0, 100)
print("限制后: " + str(val))

let reversed = std_utils_reverse([1, 2, 3, 4, 5])
print("反转: " + str(reversed))

if std_utils_contains([10, 20, 30], 20) {
    print("找到了!")
}
```

## 如何编写自己的模块

1. 在 `std/` 目录（或任意目录）下创建 `.zl` 文件
2. 在文件中用 `let` 和 `fn` 定义变量和函数
3. 使用 `import <路径>` 导入，路径中的 `.` 对应目录分隔符

例如创建 `std/string.zl`：

```zlang
// std/string.zl
fn std_string_join(arr, sep) {
    let result = ""
    let first = true
    for item in arr {
        if !first {
            result += sep
        }
        result += str(item)
        first = false
    }
    return result
}
```

然后在程序中导入：

```zlang
import std.string
print(std_string_join(["a", "b", "c"], ", "))
```
