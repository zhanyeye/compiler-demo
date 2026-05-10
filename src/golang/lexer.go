// ZLang 词法分析器（Lexer）。
// 将源代码文本逐字符扫描并转换为 Token 流。

package main

import (
	"fmt"
	"strings"
)

// LexerError 表示词法分析过程中的错误。
type LexerError struct {
	Line int
	Col  int
	Msg  string
}

func (e *LexerError) Error() string {
	return fmt.Sprintf("Lexer error at line %d, col %d: %s", e.Line, e.Col, e.Msg)
}

// Lexer 词法分析器，逐字符扫描源代码并生成 Token 列表。
type Lexer struct {
	source   string
	filename string
	pos      int
	line     int
	col      int
	tokens   []Token
}

// NewLexer 创建并执行词法分析，返回 Token 列表。
func NewLexer(source, filename string) []Token {
	l := &Lexer{
		source:   source,
		filename: filename,
		line:     1,
		col:      1,
	}
	l.tokenize()
	return l.tokens
}

// peek 查看当前位置偏移 offset 处的字符，不移动指针。
func (l *Lexer) peek(offset int) byte {
	idx := l.pos + offset
	if idx < len(l.source) {
		return l.source[idx]
	}
	return 0
}

// advance 前进一个字符，更新行号和列号，返回当前字符。
func (l *Lexer) advance() byte {
	ch := l.peek(0)
	l.pos++
	if ch == '\n' {
		l.line++
		l.col = 1
	} else {
		l.col++
	}
	return ch
}

// match 如果当前字符匹配期望值则前进，返回是否匹配成功。
func (l *Lexer) match(expected byte) bool {
	if l.peek(0) == expected {
		l.advance()
		return true
	}
	return false
}

// addToken 向 Token 列表追加一个新的 Token。
func (l *Lexer) addToken(ttype TokenType, value interface{}) {
	l.tokens = append(l.tokens, Token{ttype, value, l.line, l.col})
}

// skipWhitespaceAndComments 跳过空格、制表符和注释（// 和 /* */）。
func (l *Lexer) skipWhitespaceAndComments() {
	for l.pos < len(l.source) {
		ch := l.peek(0)
		if ch == ' ' || ch == '\t' || ch == '\r' {
			l.advance()
		} else if ch == '/' && l.peek(1) == '/' {
			// 行注释
			for l.pos < len(l.source) && l.peek(0) != '\n' {
				l.advance()
			}
		} else if ch == '/' && l.peek(1) == '*' {
			// 块注释
			l.advance() // /
			l.advance() // *
			for l.pos < len(l.source) {
				if l.peek(0) == '*' && l.peek(1) == '/' {
					l.advance() // *
					l.advance() // /
					break
				}
				l.advance()
			}
		} else {
			break
		}
	}
}

// readString 读取字符串字面量，处理转义字符。
func (l *Lexer) readString(quote byte) string {
	l.advance() // 跳过开始引号
	var sb strings.Builder
	for l.peek(0) != quote && l.peek(0) != 0 {
		if l.peek(0) == '\\' {
			l.advance()
			switch l.advance() {
			case 'n':
				sb.WriteByte('\n')
			case 't':
				sb.WriteByte('\t')
			case 'r':
				sb.WriteByte('\r')
			case '\\':
				sb.WriteByte('\\')
			case '\'':
				sb.WriteByte('\'')
			case '"':
				sb.WriteByte('"')
			default:
				sb.WriteByte(l.source[l.pos-1])
			}
		} else {
			sb.WriteByte(l.advance())
		}
	}
	if l.peek(0) == 0 {
		panic(&LexerError{l.line, l.col, "Unterminated string"})
	}
	l.advance() // 跳过结束引号
	return sb.String()
}

// isDigit 判断字符是否为数字。
func isDigit(ch byte) bool {
	return ch >= '0' && ch <= '9'
}

// isAlpha 判断字符是否为字母或下划线。
func isAlpha(ch byte) bool {
	return (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || ch == '_'
}

// isAlphaNum 判断字符是否为字母、数字或下划线。
func isAlphaNum(ch byte) bool {
	return isAlpha(ch) || isDigit(ch)
}

// readNumber 读取数字字面量（整数或浮点数）。
func (l *Lexer) readNumber() interface{} {
	start := l.pos
	isFloat := false
	for isDigit(l.peek(0)) || l.peek(0) == '.' {
		if l.peek(0) == '.' {
			if isFloat {
				break
			}
			isFloat = true
		}
		l.advance()
	}
	text := l.source[start:l.pos]
	if isFloat {
		var f float64
		fmt.Sscanf(text, "%f", &f)
		return f
	}
	var n int
	fmt.Sscanf(text, "%d", &n)
	return n
}

// readIdentifier 读取标识符。
func (l *Lexer) readIdentifier() string {
	start := l.pos
	for isAlphaNum(l.peek(0)) {
		l.advance()
	}
	return l.source[start:l.pos]
}

// tokenize 主词法分析循环，逐字符生成 Token 序列。
func (l *Lexer) tokenize() {
	for l.pos < len(l.source) {
		l.skipWhitespaceAndComments()
		if l.pos >= len(l.source) {
			break
		}

		ch := l.peek(0)
		line, col := l.line, l.col

		// 换行符
		if ch == '\n' {
			if len(l.tokens) == 0 || l.tokens[len(l.tokens)-1].Type != T_NEWLINE {
				l.advance()
				l.addToken(T_NEWLINE, "\n")
			} else {
				l.advance()
			}
			continue
		}

		// 数字
		if isDigit(ch) {
			val := l.readNumber()
			if _, ok := val.(float64); ok {
				l.addToken(T_FLOAT, val)
			} else {
				l.addToken(T_INT, val)
			}
			continue
		}

		// 字符串
		if ch == '"' || ch == '\'' {
			val := l.readString(ch)
			l.addToken(T_STRING, val)
			continue
		}

		// 标识符和关键字
		if isAlpha(ch) {
			val := l.readIdentifier()
			if tt, ok := keywords[val]; ok {
				if tt == T_TRUE {
					l.addToken(T_BOOL, true)
				} else if tt == T_FALSE {
					l.addToken(T_BOOL, false)
				} else {
					l.addToken(tt, val)
				}
			} else {
				l.addToken(T_IDENT, val)
			}
			continue
		}

		// 运算符和界符
		l.advance() // 消费当前字符
		switch ch {
		case '+':
			if l.match('=') {
				l.addToken(T_PLUS_ASSIGN, "+=")
			} else {
				l.addToken(T_PLUS, "+")
			}
		case '-':
			if l.match('>') {
				l.addToken(T_ARROW, "->")
			} else if l.match('=') {
				l.addToken(T_MINUS_ASSIGN, "-=")
			} else {
				l.addToken(T_MINUS, "-")
			}
		case '*':
			l.addToken(T_STAR, "*")
		case '/':
			l.addToken(T_SLASH, "/")
		case '%':
			l.addToken(T_PERCENT, "%")
		case '=':
			if l.match('=') {
				l.addToken(T_EQ, "==")
			} else {
				l.addToken(T_ASSIGN, "=")
			}
		case '!':
			if l.match('=') {
				l.addToken(T_NEQ, "!=")
			} else {
				l.addToken(T_NOT, "!")
			}
		case '<':
			if l.match('=') {
				l.addToken(T_LTE, "<=")
			} else {
				l.addToken(T_LT, "<")
			}
		case '>':
			if l.match('=') {
				l.addToken(T_GTE, ">=")
			} else {
				l.addToken(T_GT, ">")
			}
		case '&':
			if l.match('&') {
				l.addToken(T_AND, "&&")
			} else {
				panic(&LexerError{line, col, fmt.Sprintf("Unexpected character: '%c'", ch)})
			}
		case '|':
			if l.match('|') {
				l.addToken(T_OR, "||")
			} else {
				panic(&LexerError{line, col, fmt.Sprintf("Unexpected character: '%c'", ch)})
			}
		case '(':
			l.addToken(T_LPAREN, "(")
		case ')':
			l.addToken(T_RPAREN, ")")
		case '{':
			l.addToken(T_LBRACE, "{")
		case '}':
			l.addToken(T_RBRACE, "}")
		case '[':
			l.addToken(T_LBRACKET, "[")
		case ']':
			l.addToken(T_RBRACKET, "]")
		case ',':
			l.addToken(T_COMMA, ",")
		case ':':
			l.addToken(T_COLON, ":")
		case ';':
			l.addToken(T_SEMICOLON, ";")
		case '.':
			l.addToken(T_DOT, ".")
		default:
			panic(&LexerError{line, col, fmt.Sprintf("Unexpected character: '%c'", ch)})
		}
	}

	// 去掉末尾的 NEWLINE
	if len(l.tokens) > 0 && l.tokens[len(l.tokens)-1].Type == T_NEWLINE {
		l.tokens = l.tokens[:len(l.tokens)-1]
	}
	l.addToken(T_EOF, nil)
}
