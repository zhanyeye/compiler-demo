// ZLang 虚拟机 / 解释器（VM）。
// 遍历 AST 并直接执行，支持变量作用域、函数闭包、结构体、数组、控制流和模块导入。

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// ---- 控制流信号 ----

type breakSignal struct{}
type continueSignal struct{}

// ReturnSignal return 信号，携带返回值。
type ReturnSignal struct {
	Value interface{}
}

// ZLangError 运行时错误。
type ZLangError struct {
	Msg string
}

func (e *ZLangError) Error() string {
	return "RuntimeError: " + e.Msg
}

// ---- 运行时对象 ----

// ZArray 数组包装类型，使 append 能原地修改。
type ZArray struct {
	Elements []interface{}
}

// ZFunction 用户定义的函数对象，携带闭包环境。
type ZFunction struct {
	Name    string
	Params  []*FuncParam
	Body    Node
	Closure *Environment
}

// ZStructInstance 结构体实例。
type ZStructInstance struct {
	StructName string
	Fields     map[string]interface{}
}

// ZModule 已导入模块。
type ZModule struct {
	Name    string
	Exports map[string]interface{}
}

// ZBuiltinFunc 内置函数类型。
type ZBuiltinFunc func(args ...interface{}) interface{}

// ---- 环境（词法作用域） ----

// Environment 变量作用域环境，支持嵌套（链式父作用域查找）。
type Environment struct {
	vars   map[string]interface{}
	parent *Environment
}

func newEnvironment(parent *Environment) *Environment {
	return &Environment{vars: make(map[string]interface{}), parent: parent}
}

func (e *Environment) define(name string, value interface{}) {
	e.vars[name] = value
}

func (e *Environment) get(name string) (interface{}, error) {
	if val, ok := e.vars[name]; ok {
		return val, nil
	}
	if e.parent != nil {
		return e.parent.get(name)
	}
	return nil, &ZLangError{fmt.Sprintf("Undefined variable '%s'", name)}
}

func (e *Environment) set(name string, value interface{}) error {
	if _, ok := e.vars[name]; ok {
		e.vars[name] = value
		return nil
	}
	if e.parent != nil {
		return e.parent.set(name, value)
	}
	return &ZLangError{fmt.Sprintf("Undefined variable '%s'", name)}
}

// ---- 格式化工具 ----

func zfmt(value interface{}) string {
	switch v := value.(type) {
	case bool:
		if v {
			return "true"
		}
		return "false"
	case string:
		return v
	case float64:
		if v == float64(int64(v)) {
			return fmt.Sprintf("%d", int64(v))
		}
		return fmt.Sprintf("%g", v)
	case int:
		return fmt.Sprintf("%d", v)
	case nil:
		return "null"
	case *ZArray:
		parts := make([]string, len(v.Elements))
		for i, item := range v.Elements {
			parts[i] = zfmt(item)
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case *ZStructInstance:
		parts := make([]string, 0, len(v.Fields))
		for k, val := range v.Fields {
			parts = append(parts, fmt.Sprintf("%s: %s", k, zfmt(val)))
		}
		return fmt.Sprintf("%s{%s}", v.StructName, strings.Join(parts, ", "))
	case *ZFunction:
		return fmt.Sprintf("<fn %s>", v.Name)
	case *ZModule:
		return fmt.Sprintf("<module %s>", v.Name)
	default:
		return fmt.Sprintf("%v", v)
	}
}

// ---- 解释器 ----

// Interpreter ZLang 解释器。
type Interpreter struct {
	globalEnv      *Environment
	importResolver func(string) (string, string, error)
	loadedModules  map[string]*ZModule
}

// NewInterpreter 创建解释器实例，注册内置函数。
func NewInterpreter(importResolver func(string) (string, string, error)) *Interpreter {
	interp := &Interpreter{
		globalEnv:      newEnvironment(nil),
		importResolver: importResolver,
		loadedModules:  make(map[string]*ZModule),
	}
	interp.registerBuiltins(interp.globalEnv)
	return interp
}

func (interp *Interpreter) registerBuiltins(env *Environment) {
	env.define("print", ZBuiltinFunc(func(args ...interface{}) interface{} {
		parts := make([]string, len(args))
		for i, a := range args {
			parts[i] = zfmt(a)
		}
		fmt.Println(strings.Join(parts, " "))
		return nil
	}))
	env.define("len", ZBuiltinFunc(func(args ...interface{}) interface{} {
		switch v := args[0].(type) {
		case *ZArray:
			return len(v.Elements)
		case string:
			return len(v)
		default:
			panic(&ZLangError{fmt.Sprintf("len() not supported for %T", v)})
		}
	}))
	env.define("push", ZBuiltinFunc(func(args ...interface{}) interface{} {
		if arr, ok := args[0].(*ZArray); ok {
			arr.Elements = append(arr.Elements, args[1])
			return arr
		}
		panic(&ZLangError{"push() expects an array as first argument"})
	}))
	env.define("typeof", ZBuiltinFunc(func(args ...interface{}) interface{} {
		switch v := args[0].(type) {
		case bool:
			return "bool"
		case int:
			return "int"
		case float64:
			return "float"
		case string:
			return "string"
		case *ZArray:
			return "array"
		case *ZStructInstance:
			return v.StructName
		case *ZFunction:
			return "function"
		case nil:
			return "null"
		default:
			return "unknown"
		}
	}))
	env.define("str", ZBuiltinFunc(func(args ...interface{}) interface{} {
		return zfmt(args[0])
	}))
	env.define("int", ZBuiltinFunc(func(args ...interface{}) interface{} {
		switch v := args[0].(type) {
		case int:
			return v
		case float64:
			return int(v)
		case string:
			var n int
			fmt.Sscanf(v, "%d", &n)
			return n
		case bool:
			if v {
				return 1
			}
			return 0
		default:
			panic(&ZLangError{fmt.Sprintf("Cannot convert %T to int", v)})
		}
	}))
	env.define("float", ZBuiltinFunc(func(args ...interface{}) interface{} {
		switch v := args[0].(type) {
		case float64:
			return v
		case int:
			return float64(v)
		case string:
			var f float64
			fmt.Sscanf(v, "%f", &f)
			return f
		case bool:
			if v {
				return 1.0
			}
			return 0.0
		default:
			panic(&ZLangError{fmt.Sprintf("Cannot convert %T to float", v)})
		}
	}))
}

// Run 执行一个 Program AST 节点。
func (interp *Interpreter) Run(program *Program) {
	for _, stmt := range program.Statements {
		interp.exec(stmt, interp.globalEnv)
	}
}

// ---- 语句执行 ----

func (interp *Interpreter) exec(node Node, env *Environment) interface{} {
	switch n := node.(type) {
	case *LetStatement:
		var val interface{}
		if n.Init != nil {
			val = interp.eval(n.Init, env)
		}
		env.define(n.Name, val)
		return nil
	case *ExprStatement:
		return interp.eval(n.Expr, env)
	case *IfStatement:
		return interp.execIf(n, env)
	case *ForInStatement:
		return interp.execForIn(n, env)
	case *WhileStatement:
		return interp.execWhile(n, env)
	case *SwitchStatement:
		return interp.execSwitch(n, env)
	case *ReturnStatement:
		var val interface{}
		if n.Value != nil {
			val = interp.eval(n.Value, env)
		}
		panic(ReturnSignal{Value: val})
	case *BreakStatement:
		panic(breakSignal{})
	case *ContinueStatement:
		panic(continueSignal{})
	case *FuncDecl:
		fn := &ZFunction{Name: n.Name, Params: n.Params, Body: n.Body, Closure: env}
		env.define(n.Name, fn)
		return nil
	case *StructDecl:
		env.define(n.Name, n)
		return nil
	case *ImportDecl:
		interp.execImport(n, env)
		return nil
	case *Block:
		interp.execBlock(n, env)
		return nil
	}
	panic(&ZLangError{fmt.Sprintf("Unknown statement: %s", node.nodeType())})
}

func (interp *Interpreter) execIf(node *IfStatement, env *Environment) interface{} {
	if isTruthy(interp.eval(node.Condition, env)) {
		interp.execBlock(node.ThenBlock.(*Block), env)
	} else if node.ElseBlock != nil {
		switch els := node.ElseBlock.(type) {
		case *IfStatement:
			interp.execIf(els, env)
		case *Block:
			interp.execBlock(els, env)
		}
	}
	return nil
}

func (interp *Interpreter) execForIn(node *ForInStatement, env *Environment) interface{} {
	iterable := interp.eval(node.Iterable, env)
	var arr []interface{}
	switch v := iterable.(type) {
	case *ZArray:
		arr = v.Elements
	default:
		panic(&ZLangError{"for-in requires an iterable (array)"})
	}
	for _, item := range arr {
		loopEnv := newEnvironment(env)
		loopEnv.define(node.VarName, item)
		func() {
			defer func() {
				if r := recover(); r != nil {
					switch r.(type) {
					case continueSignal:
						// 继续下一个迭代
					case breakSignal:
						panic(r) // 向上传播
					default:
						panic(r)
					}
				}
			}()
			interp.execBlock(node.Body.(*Block), loopEnv)
		}()
	}
	return nil
}

func (interp *Interpreter) execWhile(node *WhileStatement, env *Environment) interface{} {
	for isTruthy(interp.eval(node.Condition, env)) {
		func() {
			defer func() {
				if r := recover(); r != nil {
					switch r.(type) {
					case continueSignal:
						// 继续
					case breakSignal:
						panic(r)
					default:
						panic(r)
					}
				}
			}()
			interp.execBlock(node.Body.(*Block), env)
		}()
	}
	return nil
}

func (interp *Interpreter) execSwitch(node *SwitchStatement, env *Environment) interface{} {
	target := interp.eval(node.Expr, env)
	matched := false
	for _, c := range node.Cases {
		if !matched {
			if c.Value == nil {
				matched = true
			} else if valuesEqual(target, interp.eval(c.Value, env)) {
				matched = true
			}
		}
		if matched {
			func() {
				defer func() {
					if r := recover(); r != nil {
						switch r.(type) {
						case breakSignal:
							// 吸收 break，停止 switch
						default:
							panic(r)
						}
					}
				}()
				interp.execBlock(c.Body.(*Block), env)
			}()
		}
	}
	return nil
}

func (interp *Interpreter) execImport(node *ImportDecl, env *Environment) {
	if interp.importResolver == nil {
		panic(&ZLangError{fmt.Sprintf("Cannot import '%s': no import resolver", node.ModulePath)})
	}
	module := interp.loadModule(node.ModulePath)
	for name, val := range module.Exports {
		env.define(name, val)
	}
}

func (interp *Interpreter) execBlock(block *Block, env *Environment) {
	blockEnv := newEnvironment(env)
	for _, stmt := range block.Statements {
		interp.exec(stmt, blockEnv)
	}
}

// ---- 表达式求值 ----

func (interp *Interpreter) eval(node Node, env *Environment) interface{} {
	switch n := node.(type) {
	case *IntLiteral:
		return n.Value
	case *FloatLiteral:
		return n.Value
	case *StringLiteral:
		return n.Value
	case *BoolLiteral:
		return n.Value
	case *ArrayLiteral:
		elements := make([]interface{}, len(n.Elements))
		for i, el := range n.Elements {
			elements[i] = interp.eval(el, env)
		}
		return &ZArray{Elements: elements}
	case *Identifier:
		val, err := env.get(n.Name)
		if err != nil {
			panic(err)
		}
		return val
	case *BinaryOp:
		return interp.evalBinaryOp(n, env)
	case *UnaryOp:
		return interp.evalUnaryOp(n, env)
	case *Assignment:
		return interp.evalAssignment(n, env)
	case *CompoundAssignment:
		return interp.evalCompoundAssignment(n, env)
	case *CallExpr:
		return interp.evalCall(n, env)
	case *MemberAccess:
		return interp.evalMemberAccess(n, env)
	case *IndexAccess:
		return interp.evalIndexAccess(n, env)
	case *FuncDecl:
		return &ZFunction{Name: n.Name, Params: n.Params, Body: n.Body, Closure: env}
	}
	panic(&ZLangError{fmt.Sprintf("Unknown expression: %s", node.nodeType())})
}

func (interp *Interpreter) evalBinaryOp(node *BinaryOp, env *Environment) interface{} {
	// 短路求值
	if node.Op == "&&" {
		left := interp.eval(node.Left, env)
		if !isTruthy(left) {
			return left
		}
		return interp.eval(node.Right, env)
	}
	if node.Op == "||" {
		left := interp.eval(node.Left, env)
		if isTruthy(left) {
			return left
		}
		return interp.eval(node.Right, env)
	}

	left := interp.eval(node.Left, env)
	right := interp.eval(node.Right, env)

	switch node.Op {
	case "+":
		if ls, ok := left.(string); ok {
			if rs, ok := right.(string); ok {
				return ls + rs
			}
			return ls + zfmt(right)
		}
		return arithOp(left, right, func(a, b float64) float64 { return a + b })
	case "-":
		return arithOp(left, right, func(a, b float64) float64 { return a - b })
	case "*":
		return arithOp(left, right, func(a, b float64) float64 { return a * b })
	case "/":
		return arithOp(left, right, func(a, b float64) float64 { return a / b })
	case "%":
		return int(toFloat(left)) % int(toFloat(right))
	case "==":
		return valuesEqual(left, right)
	case "!=":
		return !valuesEqual(left, right)
	case "<":
		return toFloat(left) < toFloat(right)
	case ">":
		return toFloat(left) > toFloat(right)
	case "<=":
		return toFloat(left) <= toFloat(right)
	case ">=":
		return toFloat(left) >= toFloat(right)
	}
	panic(&ZLangError{fmt.Sprintf("Unknown operator: %s", node.Op)})
}

func arithOp(left, right interface{}, fn func(float64, float64) float64) interface{} {
	l, r := toFloat(left), toFloat(right)
	result := fn(l, r)
	if _, ok := left.(int); ok {
		if _, ok2 := right.(int); ok2 {
			return int(result)
		}
	}
	return result
}

func toFloat(v interface{}) float64 {
	switch n := v.(type) {
	case int:
		return float64(n)
	case float64:
		return n
	case bool:
		if n {
			return 1.0
		}
		return 0.0
	}
	return 0.0
}

func (interp *Interpreter) evalUnaryOp(node *UnaryOp, env *Environment) interface{} {
	val := interp.eval(node.Operand, env)
	switch node.Op {
	case "-":
		switch v := val.(type) {
		case int:
			return -v
		case float64:
			return -v
		}
		return -toFloat(val)
	case "!":
		return !isTruthy(val)
	}
	panic(&ZLangError{fmt.Sprintf("Unknown unary operator: %s", node.Op)})
}

func (interp *Interpreter) evalAssignment(node *Assignment, env *Environment) interface{} {
	value := interp.eval(node.Value, env)
	interp.assignTarget(node.Target, value, env)
	return value
}

func (interp *Interpreter) evalCompoundAssignment(node *CompoundAssignment, env *Environment) interface{} {
	current := interp.eval(node.Target, env)
	rhs := interp.eval(node.Value, env)
	var newVal interface{}
	switch node.Op {
	case "+=":
		if s, ok := current.(string); ok {
			newVal = s + zfmt(rhs)
		} else {
			newVal = arithOp(current, rhs, func(a, b float64) float64 { return a + b })
		}
	case "-=":
		newVal = arithOp(current, rhs, func(a, b float64) float64 { return a - b })
	}
	interp.assignTarget(node.Target, newVal, env)
	return newVal
}

func (interp *Interpreter) assignTarget(target Node, value interface{}, env *Environment) {
	switch t := target.(type) {
	case *Identifier:
		if err := env.set(t.Name, value); err != nil {
			panic(err)
		}
	case *MemberAccess:
		obj := interp.eval(t.Object, env)
		if inst, ok := obj.(*ZStructInstance); ok {
			inst.Fields[t.Member] = value
		} else {
			panic(&ZLangError{fmt.Sprintf("Cannot set field on %T", obj)})
		}
	case *IndexAccess:
		obj := interp.eval(t.Object, env)
		idx := interp.eval(t.Index, env)
		if arr, ok := obj.(*ZArray); ok {
			i := int(toFloat(idx))
			if i < 0 {
				i += len(arr.Elements)
			}
			arr.Elements[i] = value
		} else {
			panic(&ZLangError{fmt.Sprintf("Cannot index-assign on %T", obj)})
		}
	default:
		panic(&ZLangError{"Invalid assignment target"})
	}
}

func (interp *Interpreter) evalCall(node *CallExpr, env *Environment) interface{} {
	callee := interp.eval(node.Callee, env)
	args := make([]interface{}, len(node.Args))
	for i, a := range node.Args {
		args[i] = interp.eval(a, env)
	}

	switch fn := callee.(type) {
	case ZBuiltinFunc:
		return fn(args...)
	case *ZFunction:
		return interp.callFunction(fn, args)
	case *StructDecl:
		return interp.instantiateStruct(fn, args)
	}
	panic(&ZLangError{fmt.Sprintf("'%s' is not callable", zfmt(callee))})
}

func (interp *Interpreter) callFunction(fn *ZFunction, args []interface{}) interface{} {
	if len(args) != len(fn.Params) {
		panic(&ZLangError{fmt.Sprintf("Function '%s' expects %d args, got %d", fn.Name, len(fn.Params), len(args))})
	}
	callEnv := newEnvironment(fn.Closure)
	for i, param := range fn.Params {
		callEnv.define(param.Name, args[i])
	}
	var result interface{}
	func() {
		defer func() {
			if r := recover(); r != nil {
				switch sig := r.(type) {
				case ReturnSignal:
					result = sig.Value
				default:
					panic(r)
				}
			}
		}()
		interp.execBlock(fn.Body.(*Block), callEnv)
	}()
	return result
}

func (interp *Interpreter) instantiateStruct(structDef *StructDecl, args []interface{}) *ZStructInstance {
	fields := make(map[string]interface{})
	if len(args) == 0 {
		for _, f := range structDef.Fields {
			fields[f.Name] = nil
		}
	} else {
		for i, f := range structDef.Fields {
			if i < len(args) {
				fields[f.Name] = args[i]
			} else {
				fields[f.Name] = nil
			}
		}
	}
	return &ZStructInstance{StructName: structDef.Name, Fields: fields}
}

func (interp *Interpreter) evalMemberAccess(node *MemberAccess, env *Environment) interface{} {
	obj := interp.eval(node.Object, env)
	switch o := obj.(type) {
	case *ZStructInstance:
		if val, ok := o.Fields[node.Member]; ok {
			return val
		}
		panic(&ZLangError{fmt.Sprintf("Struct '%s' has no field '%s'", o.StructName, node.Member)})
	case *ZModule:
		if val, ok := o.Exports[node.Member]; ok {
			return val
		}
		panic(&ZLangError{fmt.Sprintf("Module '%s' has no export '%s'", o.Name, node.Member)})
	case string:
		return interp.stringMethod(o, node.Member)
	}
	panic(&ZLangError{fmt.Sprintf("Cannot access '.%s' on %T", node.Member, obj)})
}

func (interp *Interpreter) stringMethod(s, method string) interface{} {
	switch method {
	case "len":
		return len(s)
	case "upper":
		return strings.ToUpper(s)
	case "lower":
		return strings.ToLower(s)
	case "trim":
		return strings.TrimSpace(s)
	case "split":
		return ZBuiltinFunc(func(args ...interface{}) interface{} {
			sep := ""
			if len(args) > 0 {
				sep = args[0].(string)
			}
			parts := strings.Split(s, sep)
			result := make([]interface{}, len(parts))
			for i, p := range parts {
				result[i] = p
			}
			return &ZArray{Elements: result}
		})
	case "contains":
		return ZBuiltinFunc(func(args ...interface{}) interface{} {
			return strings.Contains(s, args[0].(string))
		})
	case "starts_with":
		return ZBuiltinFunc(func(args ...interface{}) interface{} {
			return strings.HasPrefix(s, args[0].(string))
		})
	case "ends_with":
		return ZBuiltinFunc(func(args ...interface{}) interface{} {
			return strings.HasSuffix(s, args[0].(string))
		})
	}
	panic(&ZLangError{fmt.Sprintf("String has no method '%s'", method)})
}

func (interp *Interpreter) evalIndexAccess(node *IndexAccess, env *Environment) interface{} {
	obj := interp.eval(node.Object, env)
	idx := interp.eval(node.Index, env)
	switch o := obj.(type) {
	case *ZArray:
		i := int(toFloat(idx))
		if i < 0 {
			i += len(o.Elements)
		}
		if i < 0 || i >= len(o.Elements) {
			panic(&ZLangError{fmt.Sprintf("Index %d out of range", i)})
		}
		return o.Elements[i]
	case string:
		i := int(toFloat(idx))
		if i < 0 {
			i += len(o)
		}
		return string([]rune(o)[i])
	}
	panic(&ZLangError{fmt.Sprintf("Cannot index %T", obj)})
}

// ---- 辅助方法 ----

func isTruthy(val interface{}) bool {
	switch v := val.(type) {
	case nil:
		return false
	case bool:
		return v
	case int:
		return v != 0
	case float64:
		return v != 0.0
	case string:
		return len(v) > 0
	case *ZArray:
		return len(v.Elements) > 0
	}
	return true
}

func valuesEqual(a, b interface{}) bool {
	switch av := a.(type) {
	case int:
		if bv, ok := b.(int); ok {
			return av == bv
		}
	case float64:
		if bv, ok := b.(float64); ok {
			return av == bv
		}
	case string:
		if bv, ok := b.(string); ok {
			return av == bv
		}
	case bool:
		if bv, ok := b.(bool); ok {
			return av == bv
		}
	case nil:
		return b == nil
	}
	return false
}

func (interp *Interpreter) loadModule(modulePath string) *ZModule {
	if m, ok := interp.loadedModules[modulePath]; ok {
		return m
	}

	source, filename, err := interp.importResolver(modulePath)
	if err != nil {
		panic(&ZLangError{fmt.Sprintf("Cannot find module '%s': %v", modulePath, err)})
	}

	tokens := NewLexer(source, filename)
	program := NewParser(tokens, filename).Parse()

	moduleEnv := newEnvironment(nil)
	interp.registerBuiltins(moduleEnv)
	for _, stmt := range program.Statements {
		interp.exec(stmt, moduleEnv)
	}

	exports := make(map[string]interface{})
	builtinNames := map[string]bool{
		"print": true, "len": true, "push": true, "typeof": true,
		"str": true, "int": true, "float": true,
	}
	for name, val := range moduleEnv.vars {
		if !builtinNames[name] {
			exports[name] = val
		}
	}

	module := &ZModule{Name: modulePath, Exports: exports}
	interp.loadedModules[modulePath] = module
	return module
}

// ResolveImport 根据模块路径解析并加载模块源码。
// 将点分路径转换为文件路径：如 "std.math" → "std/math.zl"。
// 依次在当前工作目录和 <project_root>/examples/ 下查找。
func ResolveImport(modulePath string) (string, string, error) {
	parts := strings.Split(modulePath, ".")
	relPath := strings.Join(parts, string(os.PathSeparator)) + ".zl"

	cwd, _ := os.Getwd()
	// 项目根目录 = src/golang 上溯两级
	projectRoot := filepath.Join(cwd, "..", "..")

	searchDirs := []string{cwd, filepath.Join(projectRoot, "examples")}
	for _, dir := range searchDirs {
		full := filepath.Join(dir, relPath)
		data, err := os.ReadFile(full)
		if err == nil {
			return string(data), full, nil
		}
	}
	return "", "", fmt.Errorf("cannot find module '%s'", modulePath)
}
