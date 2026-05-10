// ZLang 语法分析器（Parser）。
// 递归下降解析器，将 Token 流转换为 AST（抽象语法树）。

package main

import (
	"fmt"
)

// ParseError 语法分析错误。
type ParseError struct {
	Line int
	Msg  string
	Tok  Token
}

func (e *ParseError) Error() string {
	return fmt.Sprintf("Parse error at line %d: %s (got %s %v)", e.Line, e.Msg, tokenName(e.Tok.Type), e.Tok.Value)
}

// Parser 递归下降语法分析器。
type Parser struct {
	tokens   []Token
	pos      int
	filename string
}

// NewParser 创建解析器实例。
func NewParser(tokens []Token, filename string) *Parser {
	return &Parser{tokens: tokens, filename: filename}
}

// ---- 辅助方法 ----

func (p *Parser) peek() Token {
	return p.tokens[p.pos]
}

func (p *Parser) advance() Token {
	tok := p.tokens[p.pos]
	p.pos++
	return tok
}

func (p *Parser) expect(ttype TokenType) Token {
	tok := p.peek()
	if tok.Type != ttype {
		panic(&ParseError{tok.Line, fmt.Sprintf("Expected %s", tokenName(ttype)), tok})
	}
	return p.advance()
}

func (p *Parser) match(types ...TokenType) *Token {
	for _, t := range types {
		if p.peek().Type == t {
			tok := p.advance()
			return &tok
		}
	}
	return nil
}

func (p *Parser) skipNewlines() {
	for p.peek().Type == T_NEWLINE {
		p.advance()
	}
}

func (p *Parser) expectEnd() {
	tok := p.peek()
	if tok.Type == T_NEWLINE || tok.Type == T_SEMICOLON || tok.Type == T_EOF || tok.Type == T_RBRACE {
		if tok.Type == T_NEWLINE || tok.Type == T_SEMICOLON {
			p.advance()
		}
		return
	}
	panic(&ParseError{tok.Line, "Expected end of statement", tok})
}

// ---- 程序 ----

// Parse 解析整个程序，返回 Program AST 节点。
func (p *Parser) Parse() *Program {
	stmts := []Node{}
	p.skipNewlines()
	for p.peek().Type != T_EOF {
		stmts = append(stmts, p.topLevel())
		p.skipNewlines()
	}
	return &Program{Statements: stmts, Filename: p.filename}
}

func (p *Parser) topLevel() Node {
	switch p.peek().Type {
	case T_IMPORT:
		return p.importDecl()
	case T_FN:
		return p.funcDecl()
	case T_STRUCT:
		return p.structDecl()
	}
	return p.statement()
}

// ---- 声明 ----

func (p *Parser) importDecl() Node {
	p.expect(T_IMPORT)
	pathParts := []string{p.expect(T_IDENT).Value.(string)}
	for p.match(T_DOT) != nil {
		pathParts = append(pathParts, p.expect(T_IDENT).Value.(string))
	}
	p.expectEnd()
	result := ""
	for i, s := range pathParts {
		if i > 0 {
			result += "."
		}
		result += s
	}
	return &ImportDecl{ModulePath: result}
}

func (p *Parser) funcDecl() Node {
	p.expect(T_FN)
	name := p.expect(T_IDENT).Value.(string)
	p.expect(T_LPAREN)
	params := p.paramList()
	p.expect(T_RPAREN)
	var retType Node
	if p.match(T_ARROW) != nil {
		retType = p.typeExpr()
	}
	p.skipNewlines()
	body := p.block()
	return &FuncDecl{Name: name, Params: params, ReturnType: retType, Body: body}
}

func (p *Parser) paramList() []*FuncParam {
	params := []*FuncParam{}
	if p.peek().Type == T_RPAREN {
		return params
	}
	params = append(params, p.funcParam())
	for p.match(T_COMMA) != nil {
		params = append(params, p.funcParam())
	}
	return params
}

func (p *Parser) funcParam() *FuncParam {
	name := p.expect(T_IDENT).Value.(string)
	var typeAnn Node
	if p.match(T_COLON) != nil {
		typeAnn = p.typeExpr()
	}
	return &FuncParam{Name: name, TypeAnn: typeAnn}
}

func (p *Parser) structDecl() Node {
	p.expect(T_STRUCT)
	name := p.expect(T_IDENT).Value.(string)
	p.skipNewlines()
	p.expect(T_LBRACE)
	p.skipNewlines()
	fields := []*StructField{}
	for p.peek().Type != T_RBRACE {
		fname := p.expect(T_IDENT).Value.(string)
		p.expect(T_COLON)
		ftype := p.typeExpr()
		fields = append(fields, &StructField{Name: fname, TypeAnn: ftype})
		p.match(T_COMMA)
		p.skipNewlines()
	}
	p.expect(T_RBRACE)
	p.skipNewlines()
	return &StructDecl{Name: name, Fields: fields}
}

func (p *Parser) typeExpr() Node {
	name := p.expect(T_IDENT).Value.(string)
	generics := []Node{}
	if p.match(T_LBRACKET) != nil {
		generics = append(generics, p.typeExpr())
		for p.match(T_COMMA) != nil {
			generics = append(generics, p.typeExpr())
		}
		p.expect(T_RBRACKET)
	}
	return &TypeExpr{Name: name, GenericArgs: generics}
}

// ---- 语句 ----

func (p *Parser) block() Node {
	p.expect(T_LBRACE)
	p.skipNewlines()
	stmts := []Node{}
	for p.peek().Type != T_RBRACE {
		stmts = append(stmts, p.statement())
		p.skipNewlines()
	}
	p.expect(T_RBRACE)
	return &Block{Statements: stmts}
}

func (p *Parser) statement() Node {
	switch p.peek().Type {
	case T_LET:
		return p.letStmt()
	case T_IF:
		return p.ifStmt()
	case T_FOR:
		return p.forStmt()
	case T_WHILE:
		return p.whileStmt()
	case T_SWITCH:
		return p.switchStmt()
	case T_RETURN:
		return p.returnStmt()
	case T_BREAK:
		p.advance()
		p.expectEnd()
		return &BreakStatement{}
	case T_CONTINUE:
		p.advance()
		p.expectEnd()
		return &ContinueStatement{}
	case T_FN:
		return p.funcDecl()
	case T_STRUCT:
		return p.structDecl()
	}
	return p.exprStmt()
}

func (p *Parser) letStmt() Node {
	p.expect(T_LET)
	name := p.expect(T_IDENT).Value.(string)
	var typeAnn Node
	if p.match(T_COLON) != nil {
		typeAnn = p.typeExpr()
	}
	var init Node
	if p.match(T_ASSIGN) != nil {
		init = p.expression()
	}
	p.expectEnd()
	return &LetStatement{Name: name, TypeAnn: typeAnn, Init: init}
}

func (p *Parser) ifStmt() Node {
	p.expect(T_IF)
	condition := p.expression()
	p.skipNewlines()
	thenBlock := p.block()
	var elseBlock Node
	p.skipNewlines()
	if p.match(T_ELSE) != nil {
		p.skipNewlines()
		if p.peek().Type == T_IF {
			elseBlock = p.ifStmt()
		} else {
			elseBlock = p.block()
		}
	}
	return &IfStatement{Condition: condition, ThenBlock: thenBlock, ElseBlock: elseBlock}
}

func (p *Parser) forStmt() Node {
	p.expect(T_FOR)
	varName := p.expect(T_IDENT).Value.(string)
	p.expect(T_IN)
	iterable := p.expression()
	p.skipNewlines()
	body := p.block()
	return &ForInStatement{VarName: varName, Iterable: iterable, Body: body}
}

func (p *Parser) whileStmt() Node {
	p.expect(T_WHILE)
	condition := p.expression()
	p.skipNewlines()
	body := p.block()
	return &WhileStatement{Condition: condition, Body: body}
}

func (p *Parser) switchStmt() Node {
	p.expect(T_SWITCH)
	expr := p.expression()
	p.skipNewlines()
	p.expect(T_LBRACE)
	p.skipNewlines()
	cases := []*SwitchCase{}
	for p.peek().Type == T_CASE || p.peek().Type == T_DEFAULT {
		if p.peek().Type == T_DEFAULT {
			p.advance()
			p.expect(T_COLON)
			p.skipNewlines()
			body := p.switchBody()
			cases = append(cases, &SwitchCase{Value: nil, Body: body})
		} else {
			p.advance() // case
			value := p.expression()
			p.expect(T_COLON)
			p.skipNewlines()
			body := p.switchBody()
			cases = append(cases, &SwitchCase{Value: value, Body: body})
		}
		p.skipNewlines()
	}
	p.expect(T_RBRACE)
	return &SwitchStatement{Expr: expr, Cases: cases}
}

func (p *Parser) switchBody() Node {
	stmts := []Node{}
	for p.peek().Type != T_CASE && p.peek().Type != T_DEFAULT && p.peek().Type != T_RBRACE {
		stmts = append(stmts, p.statement())
		p.skipNewlines()
	}
	return &Block{Statements: stmts}
}

func (p *Parser) returnStmt() Node {
	p.expect(T_RETURN)
	var value Node
	t := p.peek().Type
	if t != T_NEWLINE && t != T_SEMICOLON && t != T_EOF && t != T_RBRACE {
		value = p.expression()
	}
	p.expectEnd()
	return &ReturnStatement{Value: value}
}

func (p *Parser) exprStmt() Node {
	expr := p.expression()
	p.expectEnd()
	return &ExprStatement{Expr: expr}
}

// ---- 表达式（运算符优先级爬升） ----

func (p *Parser) expression() Node {
	return p.assignment()
}

func (p *Parser) assignment() Node {
	expr := p.logicOr()
	if p.match(T_ASSIGN) != nil {
		value := p.assignment()
		return &Assignment{Target: expr, Value: value}
	}
	if p.match(T_PLUS_ASSIGN) != nil {
		value := p.assignment()
		return &CompoundAssignment{Op: "+=", Target: expr, Value: value}
	}
	if p.match(T_MINUS_ASSIGN) != nil {
		value := p.assignment()
		return &CompoundAssignment{Op: "-=", Target: expr, Value: value}
	}
	return expr
}

func (p *Parser) logicOr() Node {
	left := p.logicAnd()
	for p.match(T_OR) != nil {
		right := p.logicAnd()
		left = &BinaryOp{Op: "||", Left: left, Right: right}
	}
	return left
}

func (p *Parser) logicAnd() Node {
	left := p.equality()
	for p.match(T_AND) != nil {
		right := p.equality()
		left = &BinaryOp{Op: "&&", Left: left, Right: right}
	}
	return left
}

func (p *Parser) equality() Node {
	left := p.comparison()
	for {
		tok := p.match(T_EQ, T_NEQ)
		if tok == nil {
			break
		}
		right := p.comparison()
		left = &BinaryOp{Op: tok.Value.(string), Left: left, Right: right}
	}
	return left
}

func (p *Parser) comparison() Node {
	left := p.addition()
	for {
		tok := p.match(T_LT, T_GT, T_LTE, T_GTE)
		if tok == nil {
			break
		}
		right := p.addition()
		left = &BinaryOp{Op: tok.Value.(string), Left: left, Right: right}
	}
	return left
}

func (p *Parser) addition() Node {
	left := p.multiplication()
	for {
		tok := p.match(T_PLUS, T_MINUS)
		if tok == nil {
			break
		}
		right := p.multiplication()
		left = &BinaryOp{Op: tok.Value.(string), Left: left, Right: right}
	}
	return left
}

func (p *Parser) multiplication() Node {
	left := p.unary()
	for {
		tok := p.match(T_STAR, T_SLASH, T_PERCENT)
		if tok == nil {
			break
		}
		right := p.unary()
		left = &BinaryOp{Op: tok.Value.(string), Left: left, Right: right}
	}
	return left
}

func (p *Parser) unary() Node {
	tok := p.match(T_NOT, T_MINUS)
	if tok != nil {
		return &UnaryOp{Op: tok.Value.(string), Operand: p.unary()}
	}
	return p.postfix()
}

func (p *Parser) postfix() Node {
	expr := p.primary()
	for {
		if p.match(T_LPAREN) != nil {
			args := []Node{}
			if p.peek().Type != T_RPAREN {
				args = append(args, p.expression())
				for p.match(T_COMMA) != nil {
					args = append(args, p.expression())
				}
			}
			p.expect(T_RPAREN)
			expr = &CallExpr{Callee: expr, Args: args}
		} else if p.match(T_DOT) != nil {
			member := p.expect(T_IDENT).Value.(string)
			expr = &MemberAccess{Object: expr, Member: member}
		} else if p.match(T_LBRACKET) != nil {
			index := p.expression()
			p.expect(T_RBRACKET)
			expr = &IndexAccess{Object: expr, Index: index}
		} else {
			break
		}
	}
	return expr
}

func (p *Parser) primary() Node {
	tok := p.peek()

	switch tok.Type {
	case T_INT:
		p.advance()
		return &IntLiteral{Value: tok.Value.(int)}
	case T_FLOAT:
		p.advance()
		return &FloatLiteral{Value: tok.Value.(float64)}
	case T_STRING:
		p.advance()
		return &StringLiteral{Value: tok.Value.(string)}
	case T_BOOL:
		p.advance()
		return &BoolLiteral{Value: tok.Value.(bool)}
	case T_IDENT:
		p.advance()
		return &Identifier{Name: tok.Value.(string)}
	case T_LPAREN:
		p.advance()
		expr := p.expression()
		p.expect(T_RPAREN)
		return expr
	case T_LBRACKET:
		p.advance()
		elements := []Node{}
		if p.peek().Type != T_RBRACKET {
			elements = append(elements, p.expression())
			for p.match(T_COMMA) != nil {
				elements = append(elements, p.expression())
			}
		}
		p.expect(T_RBRACKET)
		return &ArrayLiteral{Elements: elements}
	case T_FN:
		return p.anonymousFunc()
	}

	panic(&ParseError{tok.Line, "Expected expression", tok})
}

func (p *Parser) anonymousFunc() Node {
	p.expect(T_FN)
	p.expect(T_LPAREN)
	params := p.paramList()
	p.expect(T_RPAREN)
	p.skipNewlines()
	body := p.block()
	return &FuncDecl{Name: "", Params: params, ReturnType: nil, Body: body}
}
