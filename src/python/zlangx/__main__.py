"""
ZLangX CLI 入口 — 字节码加速版。

用法:
    python -m zlangx run <file.zl>    字节码编译 + 执行
    python -m zlangx bytecode <file>  查看字节码（调试）
    python -m zlangx bench <file.zl>  性能对比基准测试
"""

import sys
import os
import time
import argparse

from zlang.lexer import Lexer
from zlang.parser import Parser
from zlangx.compiler import Compiler
from zlangx.vm import XVM


def resolve_import(module_path):
    """模块路径解析（同 zlang）。"""
    parts = module_path.split(".")
    filepath = os.path.join(*parts) + ".zl"
    full = os.path.join(os.getcwd(), filepath)
    if os.path.isfile(full):
        with open(full, "r", encoding="utf-8") as f:
            return f.read(), full
    raise FileNotFoundError(f"Cannot find module '{module_path}'")


def cmd_run(args):
    """编译并执行 ZLang 程序（字节码模式）。"""
    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    tokens = Lexer(source, args.file).tokens
    program = Parser(tokens, args.file).parse()
    code = Compiler().compile(program)

    if args.verbose:
        print("=" * 50)
        print("字节码:")
        print(code.dump())
        print("=" * 50)

    vm = XVM(import_resolver=resolve_import)
    vm.run(code)


def cmd_bytecode(args):
    """查看编译生成的字节码。"""
    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()
    tokens = Lexer(source, args.file).tokens
    program = Parser(tokens, args.file).parse()
    code = Compiler().compile(program)
    print(code.dump())


def cmd_bench(args):
    """性能对比：zlang（树遍历）vs zlangx（字节码）。"""
    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    tokens = Lexer(source, args.file).tokens
    program = Parser(tokens, args.file).parse()

    # zlang 树遍历
    from zlang.vm import Interpreter
    interp = Interpreter()
    t0 = time.perf_counter()
    for _ in range(args.n):
        interp.run(program)
    t_tree = time.perf_counter() - t0

    # zlangx 字节码
    code = Compiler().compile(program)
    vm = XVM()
    t0 = time.perf_counter()
    for _ in range(args.n):
        vm.run(code)
    t_bytecode = time.perf_counter() - t0

    print(f"文件: {args.file}")
    print(f"迭代: {args.n} 次")
    print(f"zlang  (树遍历): {t_tree:.4f}s")
    print(f"zlangx (字节码): {t_bytecode:.4f}s")
    if t_bytecode > 0:
        speedup = t_tree / t_bytecode
        print(f"加速比: {speedup:.1f}x")


def main():
    parser = argparse.ArgumentParser(description="ZLangX — 字节码加速版")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="编译并执行（字节码模式）")
    run_p.add_argument("file", help="Path to .zl file")
    run_p.add_argument("-v", "--verbose", action="store_true", help="显示字节码")

    bc_p = sub.add_parser("bytecode", help="查看字节码")
    bc_p.add_argument("file", help="Path to .zl file")

    bench_p = sub.add_parser("bench", help="性能对比 zlang vs zlangx")
    bench_p.add_argument("file")
    bench_p.add_argument("-n", type=int, default=100, help="迭代次数")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "bytecode":
        cmd_bytecode(args)
    elif args.command == "bench":
        cmd_bench(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
