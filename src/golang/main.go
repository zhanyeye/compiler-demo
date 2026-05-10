// ZLangGo — ZLang 的高性能 Go 实现。
// 支持子命令：run（运行程序）、repl（交互式）、tokens（词法分析）、ast（语法分析）。

package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"time"
)

func main() {
	if len(os.Args) < 2 {
		printHelp()
		return
	}

	cmd := os.Args[1]
	switch cmd {
	case "run":
		if len(os.Args) < 3 {
			fmt.Println("Usage: zlanggo run <file.zl>")
			return
		}
		cmdRun(os.Args[2])
	case "repl":
		cmdRepl()
	case "tokens":
		if len(os.Args) < 3 {
			fmt.Println("Usage: zlanggo tokens <file.zl>")
			return
		}
		cmdTokens(os.Args[2])
	case "ast":
		if len(os.Args) < 3 {
			fmt.Println("Usage: zlanggo ast <file.zl>")
			return
		}
		cmdAst(os.Args[2])
	case "bench":
		if len(os.Args) < 3 {
			fmt.Println("Usage: zlanggo bench <file.zl> [-n iterations]")
			return
		}
		n := 50
		for i := 3; i < len(os.Args); i++ {
			if os.Args[i] == "-n" && i+1 < len(os.Args) {
				fmt.Sscanf(os.Args[i+1], "%d", &n)
			}
		}
		cmdBench(os.Args[2], n)
	default:
		fmt.Printf("Unknown command: %s\n", cmd)
		printHelp()
	}
}

func printHelp() {
	fmt.Println("ZLangGo — ZLang 编译器 & 解释器 (Go 高性能版)")
	fmt.Println()
	fmt.Println("用法:")
	fmt.Println("  zlanggo run <file.zl>      运行 ZLang 程序")
	fmt.Println("  zlanggo repl               启动交互式 REPL")
	fmt.Println("  zlanggo tokens <file.zl>   输出 Token 流")
	fmt.Println("  zlanggo ast <file.zl>      输出 AST")
	fmt.Println("  zlanggo bench <file.zl>    性能基准测试")
}

func cmdRun(filename string) {
	source, err := os.ReadFile(filename)
	if err != nil {
		fmt.Printf("Error: cannot read file '%s': %v\n", filename, err)
		return
	}

	defer func() {
		if r := recover(); r != nil {
			switch e := r.(type) {
			case *LexerError:
				fmt.Println(e.Error())
			case *ParseError:
				fmt.Println(e.Error())
			case *ZLangError:
				fmt.Println(e.Error())
			case error:
				fmt.Printf("Error: %v\n", e)
			default:
				fmt.Printf("Error: %v\n", r)
			}
			os.Exit(1)
		}
	}()

	tokens := NewLexer(string(source), filename)
	program := NewParser(tokens, filename).Parse()
	interp := NewInterpreter(ResolveImport)
	interp.Run(program)
}

func cmdRepl() {
	interp := NewInterpreter(ResolveImport)
	reader := bufio.NewReader(os.Stdin)
	fmt.Println("ZLang REPL v0.1 (Go) — type 'exit' to quit, 'help' for info")

	for {
		fmt.Print("zl> ")
		line, err := reader.ReadString('\n')
		if err != nil {
			fmt.Println()
			break
		}

		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		if line == "exit" {
			break
		}
		if line == "help" {
			fmt.Println("Enter ZLang expressions or statements.")
			continue
		}

		func() {
			defer func() {
				if r := recover(); r != nil {
					fmt.Printf("Error: %v\n", r)
				}
			}()

			tokens := NewLexer(line+"\n", "<repl>")
			program := NewParser(tokens, "<repl>").Parse()
			for _, stmt := range program.Statements {
				result := interp.exec(stmt, interp.globalEnv)
				if result != nil {
					fmt.Println(zfmt(result))
				}
			}
		}()
	}
}

func cmdTokens(filename string) {
	source, err := os.ReadFile(filename)
	if err != nil {
		fmt.Printf("Error: cannot read file '%s': %v\n", filename, err)
		return
	}
	tokens := NewLexer(string(source), filename)
	for _, tok := range tokens {
		fmt.Printf("Token(%s, %v, line=%d)\n", tokenName(tok.Type), tok.Value, tok.Line)
	}
}

func cmdAst(filename string) {
	source, err := os.ReadFile(filename)
	if err != nil {
		fmt.Printf("Error: cannot read file '%s': %v\n", filename, err)
		return
	}
	tokens := NewLexer(string(source), filename)
	program := NewParser(tokens, filename).Parse()
	printAST(program, 0)
}

func printAST(node Node, indent int) {
	prefix := strings.Repeat("  ", indent)

	switch n := node.(type) {
	case *Program:
		fmt.Printf("%sProgram(%s)\n", prefix, n.Filename)
		for _, stmt := range n.Statements {
			printAST(stmt, indent+1)
		}
	case *Block:
		for _, stmt := range n.Statements {
			printAST(stmt, indent)
		}
	case *LetStatement:
		fmt.Printf("%sLetStatement(name=%s)\n", prefix, n.Name)
		if n.Init != nil {
			printAST(n.Init, indent+1)
		}
	case *ExprStatement:
		printAST(n.Expr, indent)
	case *IfStatement:
		fmt.Printf("%sIfStatement\n", prefix)
		printAST(n.Condition, indent+1)
		printAST(n.ThenBlock, indent+1)
		if n.ElseBlock != nil {
			printAST(n.ElseBlock, indent+1)
		}
	case *ForInStatement:
		fmt.Printf("%sForInStatement(var=%s)\n", prefix, n.VarName)
		printAST(n.Iterable, indent+1)
		printAST(n.Body, indent+1)
	case *WhileStatement:
		fmt.Printf("%sWhileStatement\n", prefix)
		printAST(n.Condition, indent+1)
		printAST(n.Body, indent+1)
	case *FuncDecl:
		fmt.Printf("%sFuncDecl(name=%s, params=%d)\n", prefix, n.Name, len(n.Params))
		printAST(n.Body, indent+1)
	case *ReturnStatement:
		fmt.Printf("%sReturnStatement\n", prefix)
		if n.Value != nil {
			printAST(n.Value, indent+1)
		}
	case *BreakStatement:
		fmt.Printf("%sBreakStatement\n", prefix)
	case *ContinueStatement:
		fmt.Printf("%sContinueStatement\n", prefix)
	case *StructDecl:
		fmt.Printf("%sStructDecl(name=%s)\n", prefix, n.Name)
	case *ImportDecl:
		fmt.Printf("%sImportDecl(path=%s)\n", prefix, n.ModulePath)
	case *BinaryOp:
		fmt.Printf("%sBinaryOp(op=%s)\n", prefix, n.Op)
		printAST(n.Left, indent+1)
		printAST(n.Right, indent+1)
	case *UnaryOp:
		fmt.Printf("%sUnaryOp(op=%s)\n", prefix, n.Op)
		printAST(n.Operand, indent+1)
	case *Assignment:
		fmt.Printf("%sAssignment\n", prefix)
		printAST(n.Target, indent+1)
		printAST(n.Value, indent+1)
	case *CompoundAssignment:
		fmt.Printf("%sCompoundAssignment(op=%s)\n", prefix, n.Op)
		printAST(n.Target, indent+1)
		printAST(n.Value, indent+1)
	case *CallExpr:
		fmt.Printf("%sCallExpr(args=%d)\n", prefix, len(n.Args))
		printAST(n.Callee, indent+1)
		for _, arg := range n.Args {
			printAST(arg, indent+1)
		}
	case *MemberAccess:
		fmt.Printf("%sMemberAccess(member=%s)\n", prefix, n.Member)
		printAST(n.Object, indent+1)
	case *IndexAccess:
		fmt.Printf("%sIndexAccess\n", prefix)
		printAST(n.Object, indent+1)
		printAST(n.Index, indent+1)
	case *IntLiteral:
		fmt.Printf("%sIntLiteral(%d)\n", prefix, n.Value)
	case *FloatLiteral:
		fmt.Printf("%sFloatLiteral(%g)\n", prefix, n.Value)
	case *StringLiteral:
		fmt.Printf("%sStringLiteral(%q)\n", prefix, n.Value)
	case *BoolLiteral:
		fmt.Printf("%sBoolLiteral(%v)\n", prefix, n.Value)
	case *Identifier:
		fmt.Printf("%sIdentifier(%s)\n", prefix, n.Name)
	case *ArrayLiteral:
		fmt.Printf("%sArrayLiteral(len=%d)\n", prefix, len(n.Elements))
		for _, el := range n.Elements {
			printAST(el, indent+1)
		}
	default:
		fmt.Printf("%s%T\n", prefix, node)
	}
}

func cmdBench(filename string, iterations int) {
	source, err := os.ReadFile(filename)
	if err != nil {
		fmt.Printf("Error: cannot read file '%s': %v\n", filename, err)
		return
	}

	// 预编译
	tokens := NewLexer(string(source), filename)
	program := NewParser(tokens, filename).Parse()

	// Go 版本基准测试
	start := time.Now()
	for i := 0; i < iterations; i++ {
		interp := NewInterpreter(ResolveImport)
		interp.Run(program)
	}
	goDuration := time.Since(start)

	fmt.Printf("zlanggo (Go): %d iterations in %v (%.2f ms/run)\n",
		iterations, goDuration, float64(goDuration.Milliseconds())/float64(iterations))
}
