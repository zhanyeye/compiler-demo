// ZLang 词法单元（Token）定义。
// 定义了所有 Token 类型常量和 Token 结构体，供词法分析器使用。

package main

// TokenType 表示词法单元的类型。
type TokenType int

const (
	// 字面量
	T_INT TokenType = iota
	T_FLOAT
	T_STRING
	T_BOOL

	// 标识符
	T_IDENT

	// 运算符
	T_PLUS
	T_MINUS
	T_STAR
	T_SLASH
	T_PERCENT
	T_EQ       // ==
	T_NEQ      // !=
	T_LT       // <
	T_GT       // >
	T_LTE      // <=
	T_GTE      // >=
	T_AND      // &&
	T_OR       // ||
	T_NOT      // !
	T_ASSIGN   // =
	T_PLUS_ASSIGN  // +=
	T_MINUS_ASSIGN // -=

	// 界符
	T_LPAREN    // (
	T_RPAREN    // )
	T_LBRACE    // {
	T_RBRACE    // }
	T_LBRACKET  // [
	T_RBRACKET  // ]
	T_COMMA     // ,
	T_COLON     // :
	T_SEMICOLON // ;
	T_DOT       // .
	T_ARROW     // ->

	// 关键字
	T_LET
	T_FN
	T_IF
	T_ELSE
	T_FOR
	T_IN
	T_WHILE
	T_SWITCH
	T_CASE
	T_DEFAULT
	T_RETURN
	T_STRUCT
	T_IMPORT
	T_TRUE
	T_FALSE
	T_BREAK
	T_CONTINUE

	// 特殊
	T_NEWLINE
	T_EOF
)

// Token 表示一个词法单元，记录类型、值、行列号。
type Token struct {
	Type  TokenType
	Value interface{}
	Line  int
	Col   int
}

// 关键字映射表：字符串 → TokenType
var keywords = map[string]TokenType{
	"let":      T_LET,
	"fn":       T_FN,
	"if":       T_IF,
	"else":     T_ELSE,
	"for":      T_FOR,
	"in":       T_IN,
	"while":    T_WHILE,
	"switch":   T_SWITCH,
	"case":     T_CASE,
	"default":  T_DEFAULT,
	"return":   T_RETURN,
	"struct":   T_STRUCT,
	"import":   T_IMPORT,
	"true":     T_TRUE,
	"false":    T_FALSE,
	"break":    T_BREAK,
	"continue": T_CONTINUE,
}

// tokenName 返回 TokenType 的可读名称。
func tokenName(t TokenType) string {
	names := map[TokenType]string{
		T_INT: "INT", T_FLOAT: "FLOAT", T_STRING: "STRING", T_BOOL: "BOOL",
		T_IDENT: "IDENT",
		T_PLUS: "PLUS", T_MINUS: "MINUS", T_STAR: "STAR", T_SLASH: "SLASH",
		T_PERCENT: "PERCENT", T_EQ: "EQ", T_NEQ: "NEQ",
		T_LT: "LT", T_GT: "GT", T_LTE: "LTE", T_GTE: "GTE",
		T_AND: "AND", T_OR: "OR", T_NOT: "NOT",
		T_ASSIGN: "ASSIGN", T_PLUS_ASSIGN: "PLUS_ASSIGN", T_MINUS_ASSIGN: "MINUS_ASSIGN",
		T_LPAREN: "LPAREN", T_RPAREN: "RPAREN",
		T_LBRACE: "LBRACE", T_RBRACE: "RBRACE",
		T_LBRACKET: "LBRACKET", T_RBRACKET: "RBRACKET",
		T_COMMA: "COMMA", T_COLON: "COLON", T_SEMICOLON: "SEMICOLON",
		T_DOT: "DOT", T_ARROW: "ARROW",
		T_LET: "LET", T_FN: "FN", T_IF: "IF", T_ELSE: "ELSE",
		T_FOR: "FOR", T_IN: "IN", T_WHILE: "WHILE",
		T_SWITCH: "SWITCH", T_CASE: "CASE", T_DEFAULT: "DEFAULT",
		T_RETURN: "RETURN", T_STRUCT: "STRUCT", T_IMPORT: "IMPORT",
		T_TRUE: "TRUE", T_FALSE: "FALSE",
		T_BREAK: "BREAK", T_CONTINUE: "CONTINUE",
		T_NEWLINE: "NEWLINE", T_EOF: "EOF",
	}
	if n, ok := names[t]; ok {
		return n
	}
	return "UNKNOWN"
}
