"""
ZLang 命令行入口。

支持以下子命令：
    python -m zlang run <file.zl>      运行 ZLang 程序
    python -m zlang repl                启动交互式 REPL
    python -m zlang tokens <file.zl>    输出 Token 流（调试用）
    python -m zlang ast <file.zl>       输出 AST（调试用）
"""

import sys
import os
import argparse

from zlang.lexer import Lexer
from zlang.parser import Parser
from zlang.vm import Interpreter
from zlang.ast import ASTNode


def resolve_import(module_path):
    """
    根据模块路径解析并加载模块源码。

    将点分路径转换为文件路径：如 "std.math" → "std/math.zl"
    在当前工作目录下查找模块文件。
    """
    parts = module_path.split(".")
    filepath = os.path.join(*parts) + ".zl"

    search_dirs = [os.getcwd()]
    for d in search_dirs:
        full = os.path.join(d, filepath)
        if os.path.isfile(full):
            with open(full, "r", encoding="utf-8") as f:
                return f.read(), full

    raise FileNotFoundError(f"Cannot find module '{module_path}' (looked for '{filepath}')")


def cmd_run(args):
    """运行一个 ZLang 源文件。"""
    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()
    interp = Interpreter(import_resolver=resolve_import)
    tokens = Lexer(source, args.file).tokens
    program = Parser(tokens, args.file).parse()
    interp.run(program)


def cmd_repl(args):
    """启动交互式 REPL（读取-求值-打印循环）。"""
    interp = Interpreter(import_resolver=resolve_import)
    print("ZLang REPL v0.1 — type 'exit' to quit, 'help' for info")

    while True:
        try:
            line = input("zl> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        line = line.strip()
        if not line:
            continue
        if line == "exit":
            break
        if line == "help":
            print("Enter ZLang expressions or statements. Multi-line blocks not supported in REPL.")
            continue

        try:
            tokens = Lexer(line + "\n", "<repl>").tokens
            program = Parser(tokens, "<repl>").parse()
            result = None
            for stmt in program.statements:
                result = interp._exec(stmt, interp.global_env)
            if result is not None:
                from zlang.vm import _fmt
                print(_fmt(result))
        except Exception as e:
            print(f"Error: {e}")


def cmd_tokens(args):
    """输出源文件的 Token 流（调试用）。"""
    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()
    tokens = Lexer(source, args.file).tokens
    for tok in tokens:
        print(tok)


def cmd_ast(args):
    """输出源文件的 AST 结构（调试用）。"""
    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()
    tokens = Lexer(source, args.file).tokens
    program = Parser(tokens, args.file).parse()
    _print_ast(program, indent=0)


def _print_ast(node, indent=0):
    """递归打印 AST 节点的树形结构。"""
    prefix = "  " * indent
    if isinstance(node, list):
        for item in node:
            _print_ast(item, indent)
        return
    fields = {k: v for k, v in node.__dict__.items() if not k.startswith("_")}
    name = type(node).__name__
    simple = {}
    children = {}
    for k, v in fields.items():
        if isinstance(v, ASTNode):
            children[k] = v
        elif isinstance(v, list) and v and isinstance(v[0], ASTNode):
            children[k] = v
        else:
            simple[k] = v
    if simple:
        parts = ", ".join(f"{k}={v!r}" for k, v in simple.items())
        print(f"{prefix}{name}({parts})")
    else:
        print(f"{prefix}{name}")
    for k, v in children.items():
        print(f"{prefix}  {k}:")
        _print_ast(v, indent + 2)


def main():
    """解析命令行参数并分派到对应子命令。"""
    parser = argparse.ArgumentParser(description="ZLang compiler & interpreter")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run a ZLang source file")
    run_p.add_argument("file", help="Path to .zl file")

    sub.add_parser("repl", help="Start interactive REPL")

    tok_p = sub.add_parser("tokens", help="Dump tokens (debug)")
    tok_p.add_argument("file", help="Path to .zl file")

    ast_p = sub.add_parser("ast", help="Dump AST (debug)")
    ast_p.add_argument("file", help="Path to .zl file")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "repl":
        cmd_repl(args)
    elif args.command == "tokens":
        cmd_tokens(args)
    elif args.command == "ast":
        cmd_ast(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
