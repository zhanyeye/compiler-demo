// ZLang 抽象语法树（AST）节点定义。
// 所有 AST 节点均使用 Node 接口，每个节点表示一种语言结构。

package main

// Node 是所有 AST 节点的接口。
type Node interface {
	nodeType() string
}

// ---- 类型 ----

// TypeExpr 类型注解节点。
type TypeExpr struct {
	Name        string
	GenericArgs []Node
}

func (n *TypeExpr) nodeType() string { return "TypeExpr" }

// ---- 表达式 ----

// IntLiteral 整数字面量。
type IntLiteral struct {
	Value int
}

func (n *IntLiteral) nodeType() string { return "IntLiteral" }

// FloatLiteral 浮点数字面量。
type FloatLiteral struct {
	Value float64
}

func (n *FloatLiteral) nodeType() string { return "FloatLiteral" }

// StringLiteral 字符串字面量。
type StringLiteral struct {
	Value string
}

func (n *StringLiteral) nodeType() string { return "StringLiteral" }

// BoolLiteral 布尔字面量。
type BoolLiteral struct {
	Value bool
}

func (n *BoolLiteral) nodeType() string { return "BoolLiteral" }

// Identifier 标识符。
type Identifier struct {
	Name string
}

func (n *Identifier) nodeType() string { return "Identifier" }

// ArrayLiteral 数组字面量。
type ArrayLiteral struct {
	Elements []Node
}

func (n *ArrayLiteral) nodeType() string { return "ArrayLiteral" }

// BinaryOp 二元运算表达式。
type BinaryOp struct {
	Op    string
	Left  Node
	Right Node
}

func (n *BinaryOp) nodeType() string { return "BinaryOp" }

// UnaryOp 一元运算表达式。
type UnaryOp struct {
	Op      string
	Operand Node
}

func (n *UnaryOp) nodeType() string { return "UnaryOp" }

// CallExpr 函数调用表达式。
type CallExpr struct {
	Callee Node
	Args   []Node
}

func (n *CallExpr) nodeType() string { return "CallExpr" }

// MemberAccess 成员访问表达式。
type MemberAccess struct {
	Object Node
	Member string
}

func (n *MemberAccess) nodeType() string { return "MemberAccess" }

// IndexAccess 下标访问表达式。
type IndexAccess struct {
	Object Node
	Index  Node
}

func (n *IndexAccess) nodeType() string { return "IndexAccess" }

// Assignment 赋值表达式。
type Assignment struct {
	Target Node
	Value  Node
}

func (n *Assignment) nodeType() string { return "Assignment" }

// CompoundAssignment 复合赋值表达式（+=, -=）。
type CompoundAssignment struct {
	Op     string
	Target Node
	Value  Node
}

func (n *CompoundAssignment) nodeType() string { return "CompoundAssignment" }

// ---- 语句 ----

// ExprStatement 表达式语句。
type ExprStatement struct {
	Expr Node
}

func (n *ExprStatement) nodeType() string { return "ExprStatement" }

// LetStatement 变量声明语句。
type LetStatement struct {
	Name    string
	TypeAnn Node // *TypeExpr or nil
	Init    Node // 初始值表达式，可能为 nil
}

func (n *LetStatement) nodeType() string { return "LetStatement" }

// Block 代码块。
type Block struct {
	Statements []Node
}

func (n *Block) nodeType() string { return "Block" }

// IfStatement 条件语句。
type IfStatement struct {
	Condition Node
	ThenBlock Node // *Block
	ElseBlock Node // *Block 或 *IfStatement，可能为 nil
}

func (n *IfStatement) nodeType() string { return "IfStatement" }

// ForInStatement for-in 循环语句。
type ForInStatement struct {
	VarName  string
	Iterable Node
	Body     Node // *Block
}

func (n *ForInStatement) nodeType() string { return "ForInStatement" }

// WhileStatement while 循环语句。
type WhileStatement struct {
	Condition Node
	Body      Node // *Block
}

func (n *WhileStatement) nodeType() string { return "WhileStatement" }

// SwitchCase switch 语句中的一个 case 分支。
type SwitchCase struct {
	Value Node // nil 表示 default
	Body  Node // *Block
}

func (n *SwitchCase) nodeType() string { return "SwitchCase" }

// SwitchStatement switch 语句。
type SwitchStatement struct {
	Expr  Node
	Cases []*SwitchCase
}

func (n *SwitchStatement) nodeType() string { return "SwitchStatement" }

// ReturnStatement return 语句。
type ReturnStatement struct {
	Value Node // 可能为 nil
}

func (n *ReturnStatement) nodeType() string { return "ReturnStatement" }

// BreakStatement break 语句。
type BreakStatement struct{}

func (n *BreakStatement) nodeType() string { return "BreakStatement" }

// ContinueStatement continue 语句。
type ContinueStatement struct{}

func (n *ContinueStatement) nodeType() string { return "ContinueStatement" }

// ---- 声明 ----

// FuncParam 函数参数。
type FuncParam struct {
	Name    string
	TypeAnn Node // *TypeExpr or nil
}

func (n *FuncParam) nodeType() string { return "FuncParam" }

// FuncDecl 函数声明。
type FuncDecl struct {
	Name       string
	Params     []*FuncParam
	ReturnType Node // *TypeExpr or nil
	Body       Node // *Block
}

func (n *FuncDecl) nodeType() string { return "FuncDecl" }

// StructField 结构体字段。
type StructField struct {
	Name    string
	TypeAnn Node // *TypeExpr
}

func (n *StructField) nodeType() string { return "StructField" }

// StructDecl 结构体声明。
type StructDecl struct {
	Name   string
	Fields []*StructField
}

func (n *StructDecl) nodeType() string { return "StructDecl" }

// ImportDecl 导入声明。
type ImportDecl struct {
	ModulePath string
}

func (n *ImportDecl) nodeType() string { return "ImportDecl" }

// Program 程序根节点。
type Program struct {
	Statements []Node
	Filename   string
}

func (n *Program) nodeType() string { return "Program" }
