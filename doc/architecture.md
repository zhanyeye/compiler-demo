# ZLang 项目架构概览

## 1. 项目简介

ZLang 是一个教学型编程语言项目，实现了一个从源代码到执行结果的完整编译器/解释器流水线。项目使用 **三段式编译器架构**（前端 + 后端），并提供 **三种执行后端** 来对比不同实现策略的性能差异。

```
源代码 (.zl) → [Lexer] → Token 流 → [Parser] → AST → [后端] → 执行结果
```

## 2. 三种实现对比

| 维度 | Python 树遍历 (`zlang`) | Python 字节码 (`zlangx`) | Go 树遍历 (`golang`) |
|------|------------------------|-------------------------|---------------------|
| **路径** | `src/python/zlang/` | `src/python/zlangx/` | `src/golang/` |
| **语言** | Python | Python | Go |
| **执行方式** | 递归遍历 AST | 栈式字节码 VM | 递归遍历 AST |
| **相对性能** | 1x（基准） | ~1.7x | ~20x |
| **代码量** | ~1400 行 | ~800 行（复用前端） | ~2500 行 |
| **前端共享** | 自有 | 复用 `zlang` 的 Lexer + Parser | 独立实现 |
| **适用场景** | 学习、调试、REPL | 性能对比教学 | 高性能执行 |

## 3. 项目目录结构

```
compiler-demo/
├── README.md                          项目总体说明
├── doc/                               文档目录
│   ├── design.md                      编译器设计文档（核心）
│   ├── architecture.md                本文件：架构概览
│   ├── api-reference.md               ZLang 语言参考
│   └── implementation-guide.md        实现导读
│
├── examples/                          ZLang 示例程序
│   ├── hello.zl                       基础语法演示
│   ├── control_flow.zl                控制流演示
│   ├── functions.zl                   函数与闭包
│   ├── structs.zl                     结构体
│   ├── import_demo.zl                 模块导入
│   ├── bench.zl / bench_loop.zl       性能基准测试
│   └── std/                           标准库
│       ├── math.zl                    数学函数
│       └── utils.zl                   工具函数
│
└── src/                               编译器源码
    ├── python/                        Python 实现
    │   ├── zlang/                     树遍历解释器
    │   │   ├── __init__.py            包入口
    │   │   ├── __main__.py            CLI 入口（run/repl/tokens/ast）
    │   │   ├── token.py               Token 类型定义（~100行）
    │   │   ├── lexer.py               词法分析器（~220行）
    │   │   ├── ast.py                 AST 节点定义（~180行）
    │   │   ├── parser.py              语法分析器（~420行）
    │   │   └── vm.py                  虚拟机/解释器（~560行）
    │   ├── zlangx/                    字节码虚拟机
    │   │   ├── __init__.py            包入口
    │   │   ├── __main__.py            CLI 入口（run/bytecode/bench）
    │   │   ├── bytecode.py            字节码指令集 + CodeObject（~200行）
    │   │   ├── compiler.py            AST → 字节码编译器（~300行）
    │   │   └── vm.py                  栈式字节码 VM（~300行）
    │   └── tests/                     Python 单元测试
    │       ├── test_lexer.py          词法分析器测试（21个）
    │       ├── test_parser.py         语法分析器测试（33个）
    │       └── test_vm.py             虚拟机测试（48个）
    │
    └── golang/                        Go 实现
        ├── go.mod                     Go 模块定义
        ├── main.go                    CLI 入口 + bench 命令
        ├── token.go                   Token 类型定义
        ├── lexer.go                   词法分析器
        ├── ast.go                     AST 节点定义
        ├── parser.go                  语法分析器
        └── vm.go                      虚拟机/解释器
```

## 4. 编译流水线

### 4.1 Python 树遍历解释器（`zlang`）

最直接的实现方式，AST 生成后直接递归遍历执行。

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Lexer   │     │  Parser  │     │    VM    │
│lexer.py  │ ──→ │parser.py │ ──→ │  vm.py   │
│          │     │          │     │          │
│ 源码字符  │     │ Token流  │     │   AST    │
│ → Token[]│     │  → AST   │     │ → 结果   │
└──────────┘     └──────────┘     └──────────┘
  token.py          ast.py          Environment
                                   内置函数
```

### 4.2 Python 字节码虚拟机（`zlangx`）

在 `zlang` 的基础上增加编译阶段，将 AST 编译为字节码后由栈式 VM 执行。

```
┌─────────────────────── 已复用 zlang 前端 ───────────────────────┐
│  Lexer (lexer.py)  ──→  Parser (parser.py)  ──→  AST            │
└──────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────── zlangx 独有 ─────────────────────────────┐
│  Compiler (compiler.py)  ──→  CodeObject (字节码)               │
│                                      │                           │
│                                      ▼                           │
│                              XVM (vm.py)                        │
│                         栈式字节码虚拟机                         │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3 Go 高性能版（`golang`）

与 Python `zlang` 架构相同（树遍历），但用 Go 重写以获得原生性能。

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Lexer   │     │  Parser  │     │    VM    │
│lexer.go  │ ──→ │parser.go │ ──→ │  vm.go   │
└──────────┘     └──────────┘     └──────────┘
  token.go          ast.go           Environment
```

## 5. 模块依赖关系

### 5.1 Python `zlang` 模块依赖

```
__main__.py
  ├── lexer.py ──── token.py
  ├── parser.py ─── token.py, ast.py
  └── vm.py ─────── ast.py, parser.py

数据流: token.py → lexer.py → parser.py → vm.py
                                  ↑
                               ast.py
```

### 5.2 Python `zlangx` 模块依赖

```
__main__.py
  ├── zlang.lexer   (复用)
  ├── zlang.parser  (复用)
  ├── compiler.py ─── zlang.ast, bytecode.py
  └── vm.py ───────── bytecode.py, zlang.ast(仅 StructDecl)

数据流: zlang前端 → compiler.py → bytecode.py → vm.py
```

### 5.3 Go 模块依赖

```
main.go
  ├── lexer.go ──── token.go
  ├── parser.go ─── token.go, ast.go
  └── vm.go ─────── ast.go

所有文件属于 package main，直接互相引用。
```

## 6. 代码量统计

| 模块 | Python (`zlang`) | Python (`zlangx`) | Go (`golang`) |
|------|:-:|:-:|:-:|
| Token 定义 | ~100 行 | — (复用) | ~100 行 |
| Lexer | ~220 行 | — (复用) | ~250 行 |
| AST 定义 | ~180 行 | — (复用) | ~200 行 |
| Parser | ~420 行 | — (复用) | ~450 行 |
| VM / 解释器 | ~560 行 | ~300 行 | ~600 行 |
| 字节码定义 | — | ~200 行 | — |
| 编译器 | — | ~300 行 | — |
| CLI 入口 | ~120 行 | ~120 行 | ~180 行 |
| **合计** | **~1600 行** | **~920 行** | **~1780 行** |
| 测试 | 102 个测试 | — | — |

## 7. 快速开始

### Python 树遍历版

```bash
cd src/python
python -m zlang run ../../examples/hello.zl     # 运行程序
python -m zlang repl                             # 交互式 REPL
python -m zlang tokens ../../examples/hello.zl   # 查看 Token 流
python -m zlang ast ../../examples/hello.zl      # 查看 AST
python -m pytest tests/ -v                       # 运行测试
```

### Python 字节码版

```bash
cd src/python
python -m zlangx run ../../examples/hello.zl              # 运行程序
python -m zlangx run ../../examples/hello.zl -v           # 显示字节码
python -m zlangx bytecode ../../examples/hello.zl         # 查看字节码
python -m zlangx bench ../../examples/bench.zl -n 50      # 性能对比
```

### Go 高性能版

```bash
cd src/golang
go build -o zlanggo .
./zlanggo run ../../examples/hello.zl            # 运行程序
./zlanggo repl                                    # 交互式 REPL
./zlanggo tokens ../../examples/hello.zl          # 查看 Token 流
./zlanggo ast ../../examples/hello.zl             # 查看 AST
./zlanggo bench ../../examples/bench.zl -n 50     # 性能基准测试
```
