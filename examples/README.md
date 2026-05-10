# 示例程序

本目录包含 ZLang 语言的示例程序，由浅入深演示各项功能。

## 运行方式

```bash
# 在项目根目录执行
python -m zlang run examples/<文件名>.zl
```

## 示例列表

### [hello.zl](hello.zl) — 基础语法

变量定义、算术运算、字符串拼接、类型转换。

```bash
python -m zlang run examples/hello.zl
```

### [control_flow.zl](control_flow.zl) — 控制流

if/else if/else 条件判断、for-in 遍历、while 循环、switch/case 匹配。

```bash
python -m zlang run examples/control_flow.zl
```

### [functions.zl](functions.zl) — 函数与闭包

函数定义、递归（阶乘、斐波那契）、闭包（计数器）、高阶函数（map/filter）、匿名函数。

```bash
python -m zlang run examples/functions.zl
```

### [structs.zl](structs.zl) — 结构体

结构体定义与实例化、字段读写、结构体数组、用函数模拟方法。

```bash
python -m zlang run examples/structs.zl
```

### [import_demo.zl](import_demo.zl) — 模块导入

`import` 语句的使用，加载 `std/` 标准库中的函数和常量。

```bash
python -m zlang run examples/import_demo.zl
```

## 学习建议

建议按以下顺序阅读和运行：

1. `hello.zl` → 了解基本语法
2. `control_flow.zl` → 掌握流程控制
3. `functions.zl` → 理解函数和闭包
4. `structs.zl` → 学习结构体
5. `import_demo.zl` → 了解模块化

每个文件顶部都有中文注释说明演示内容，代码中也有详细注释。
