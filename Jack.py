"""
CSTPLANGS - Simple Language Compiler/Interpreter
FEU Institute of Technology - Computer Science Department

Phases:
  1. Lexer       - Tokenizes input source code
  2. Parser      - Builds an Abstract Syntax Tree (AST)
  3. Semantic    - Type checks and validates declarations
  4. Interpreter - Executes the AST
"""

import sys
import emoji

# =============================================================================
# PHASE 1: LEXER (Tokenizer)
# =============================================================================

# Token types
TT_VAR    = 'VAR'
TT_INPUT  = 'INPUT'
TT_OUTPUT = 'OUTPUT'
TT_IDENT  = 'IDENTIFIER'
TT_INT    = 'INTEGER'
TT_PLUS   = 'PLUS'
TT_MINUS  = 'MINUS'
TT_MUL    = 'MUL'
TT_DIV    = 'DIV'
TT_ASSIGN = 'ASSIGN'
TT_SEMI   = 'SEMICOLON'
TT_LPAREN = 'LPAREN'
TT_RPAREN = 'RPAREN'
TT_EOF    = 'EOF'

KEYWORDS = {'var', 'input', 'output'}


class Token:
    def __init__(self, type_, value, line):
        self.type  = type_
        self.value = value
        self.line  = line

    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, line={self.line})'


class LexerError(Exception):
    pass

class ParseError(Exception):
    pass

class SemanticError(Exception):
    pass

class RuntimeError_(Exception):
    pass


class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.tokens = []

    def error(self, msg):
        raise LexerError(f"[Lexer] Line {self.line}: {msg}")
        

    def peek(self):
        return self.source[self.pos] if self.pos < len(self.source) else None

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
        return ch

    def skip_whitespace(self):
        while self.peek() and self.peek() in ' \t\r\n':
            self.advance()

    def skip_comment(self):
        """Skip /* ... */ block comments (may span multiple lines)."""
        self.advance()  # consume '/'
        self.advance()  # consume '*'
        while self.pos < len(self.source):
            if self.source[self.pos] == '*' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '/':
                self.advance()  # consume '*'
                self.advance()  # consume '/'
                return
            self.advance()
        self.error("Unterminated block comment")

    def read_number(self):
        start = self.pos
        while self.peek() and self.peek().isdigit():
            self.advance()
        return self.source[start:self.pos]

    def read_identifier(self):
        start = self.pos
        while self.peek() and (self.peek().isalnum() or self.peek() == '_'):
            self.advance()
        return self.source[start:self.pos]

    def tokenize(self):
        simple = {
            '+': TT_PLUS,
            '-': TT_MINUS,
            '*': TT_MUL,
            '/': TT_DIV,
            '=': TT_ASSIGN,
            ';': TT_SEMI,
            '(': TT_LPAREN,
            ')': TT_RPAREN,
        }

        while self.pos < len(self.source):
            self.skip_whitespace()
            if self.pos >= len(self.source):
                break

            ch = self.peek()

            # Block comment
            if ch == '/' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '*':
                self.skip_comment()
                continue

            # Integer literal
            if ch.isdigit():
                line = self.line
                num  = self.read_number()
                self.tokens.append(Token(TT_INT, int(num), line))
                continue

            # Identifier or keyword
            if ch.isalpha() or ch == '_':
                line  = self.line
                ident = self.read_identifier()
                if ident in KEYWORDS:
                    tt = {'var': TT_VAR, 'input': TT_INPUT, 'output': TT_OUTPUT}[ident]
                    self.tokens.append(Token(tt, ident, line))
                else:
                    self.tokens.append(Token(TT_IDENT, ident, line))
                continue

            # Single-character tokens
            if ch in simple:
                line = self.line
                self.advance()
                self.tokens.append(Token(simple[ch], ch, line))
                continue

            self.error(f"Unexpected character: {ch!r}")

        self.tokens.append(Token(TT_EOF, None, self.line))
        return self.tokens


# =============================================================================
# PHASE 2: PARSER  (Recursive-Descent → AST)
# =============================================================================

# AST node classes
class VarDeclNode:
    """var <name> ;"""
    def __init__(self, name, line):
        self.name = name
        self.line = line

class AssignNode:
    """<name> = <expr> ;"""
    def __init__(self, name, expr, line):
        self.name = name
        self.expr = expr
        self.line = line

class InputNode:
    """input <name> ;"""
    def __init__(self, name, line):
        self.name = name
        self.line = line

class OutputNode:
    """output <name> ;"""
    def __init__(self, name, line):
        self.name = name
        self.line = line

class BinOpNode:
    """<left> op <right>"""
    def __init__(self, left, op, right):
        self.left  = left
        self.op    = op
        self.right = right

class NumberNode:
    def __init__(self, value):
        self.value = value

class IdentNode:
    def __init__(self, name, line):
        self.name = name
        self.line = line


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos    = 0

    def current(self):
        return self.tokens[self.pos]

    def error(self, msg):
        tok = self.current()
        raise ParseError(f"[Parser] Line {tok.line}: {msg}")

    def eat(self, type_):
        tok = self.current()
        if tok.type != type_:
            self.error(f"Expected {type_}, got {tok.type} ({tok.value!r})")
        self.pos += 1
        return tok

    def peek_type(self):
        return self.current().type

    # --- Grammar rules ---

    def parse(self):
        """program → statement* EOF"""
        stmts = []
        while self.peek_type() != TT_EOF:
            stmts.append(self.statement())
        return stmts

    def statement(self):
        tt = self.peek_type()
        if tt == TT_VAR:
            return self.var_decl()
        if tt == TT_INPUT:
            return self.input_stmt()
        if tt == TT_OUTPUT:
            return self.output_stmt()
        if tt == TT_IDENT:
            return self.assign_stmt()
        self.error(f"Unexpected token: {self.current().value!r}")

    def var_decl(self):
        """var <ident> ;"""
        line = self.current().line
        self.eat(TT_VAR)
        name_tok = self.eat(TT_IDENT)
        self.eat(TT_SEMI)
        return VarDeclNode(name_tok.value, line)

    def input_stmt(self):
        """input <ident> ;"""
        line = self.current().line
        self.eat(TT_INPUT)
        name_tok = self.eat(TT_IDENT)
        self.eat(TT_SEMI)
        return InputNode(name_tok.value, line)

    def output_stmt(self):
        """output <ident> ;"""
        line = self.current().line
        self.eat(TT_OUTPUT)
        name_tok = self.eat(TT_IDENT)
        self.eat(TT_SEMI)
        return OutputNode(name_tok.value, line)

    def assign_stmt(self):
        """<ident> = <expr> ;"""
        line = self.current().line
        name_tok = self.eat(TT_IDENT)
        self.eat(TT_ASSIGN)
        expr = self.expr()
        self.eat(TT_SEMI)
        return AssignNode(name_tok.value, expr, line)

    # --- Expression parsing (operator precedence) ---
    #  expr   → term   (('+' | '-') term)*
    #  term   → factor (('*' | '/') factor)*
    #  factor → NUMBER | IDENT | '(' expr ')'

    def expr(self):
        node = self.term()
        while self.peek_type() in (TT_PLUS, TT_MINUS):
            op  = self.eat(self.peek_type())
            rhs = self.term()
            node = BinOpNode(node, op.value, rhs)
        return node

    def term(self):
        node = self.factor()
        while self.peek_type() in (TT_MUL, TT_DIV):
            op  = self.eat(self.peek_type())
            rhs = self.factor()
            node = BinOpNode(node, op.value, rhs)
        return node

    def factor(self):
        tok = self.current()
        if tok.type == TT_INT:
            self.eat(TT_INT)
            return NumberNode(tok.value)
        if tok.type == TT_IDENT:
            self.eat(TT_IDENT)
            return IdentNode(tok.value, tok.line)
        if tok.type == TT_LPAREN:
            self.eat(TT_LPAREN)
            node = self.expr()
            self.eat(TT_RPAREN)
            return node
        self.error(f"Expected number, identifier, or '(' — got {tok.value!r}")


# =============================================================================
# PHASE 3: SEMANTIC ANALYSIS
# =============================================================================

class SemanticAnalyzer:
    def __init__(self):
        self.declared = set()   # variables that have been declared

    def error(self, msg, line):
        raise SemanticError(f"[Semantic] Line {line}: {msg}")

    def analyze(self, stmts):
        for stmt in stmts:
            self.check_stmt(stmt)

    def check_stmt(self, stmt):
        if isinstance(stmt, VarDeclNode):
            if stmt.name in self.declared:
                self.error(f"Variable '{stmt.name}' already declared", stmt.line)
            self.declared.add(stmt.name)

        elif isinstance(stmt, AssignNode):
            if stmt.name not in self.declared:
                self.error(f"Variable '{stmt.name}' used before declaration", stmt.line)
            self.check_expr(stmt.expr)

        elif isinstance(stmt, InputNode):
            if stmt.name not in self.declared:
                self.error(f"Variable '{stmt.name}' used before declaration", stmt.line)

        elif isinstance(stmt, OutputNode):
            if stmt.name not in self.declared:
                self.error(f"Variable '{stmt.name}' used before declaration", stmt.line)

    def check_expr(self, node):
        if isinstance(node, NumberNode):
            return
        if isinstance(node, IdentNode):
            if node.name not in self.declared:
                self.error(f"Variable '{node.name}' used before declaration", node.line)
        if isinstance(node, BinOpNode):
            self.check_expr(node.left)
            self.check_expr(node.right)


# =============================================================================
# PHASE 4: INTERPRETER (Tree-Walk Execution)
# =============================================================================

class Interpreter:
    def __init__(self):
        self.env = {}   # variable name → integer value

    def error(self, msg):
        raise RuntimeError_(f"[Runtime] {msg}")

    def run(self, stmts):
        for stmt in stmts:
            self.exec_stmt(stmt)

    def exec_stmt(self, stmt):
        if isinstance(stmt, VarDeclNode):
            self.env[stmt.name] = 0   # default value

        elif isinstance(stmt, AssignNode):
            self.env[stmt.name] = self.eval_expr(stmt.expr)

        elif isinstance(stmt, InputNode):
            raw = input(f"  Enter value for '{stmt.name}': ")
            try:
                self.env[stmt.name] = int(raw)
            except ValueError:
                self.error(f"Expected an integer, got {raw!r}")

        elif isinstance(stmt, OutputNode):
            print(f"  {stmt.name} = {self.env[stmt.name]}")

    def eval_expr(self, node):
        if isinstance(node, NumberNode):
            return node.value

        if isinstance(node, IdentNode):
            return self.env[node.name]

        if isinstance(node, BinOpNode):
            lv = self.eval_expr(node.left)
            rv = self.eval_expr(node.right)
            if node.op == '+': return lv + rv
            if node.op == '-': return lv - rv
            if node.op == '*': return lv * rv
            if node.op == '/':
                if rv == 0:
                    self.error("Division by zero")
                return lv // rv   # integer division

        self.error(f"Unknown node type: {type(node)}")


# =============================================================================
# DRIVER
# =============================================================================

def print_header(title, char='=', width=56):
    print(char * width)
    print(f"  {title}")
    print(char * width)


def print_section(title):
    print(f"\n{'─' * 56}")
    print(f"  {title}")
    print(f"{'─' * 56}")


def compile_and_run(source, filepath):
    print_header("CSTPLANGS  ·  Translation of Programming Language")
    print(f"  File : {filepath}")
    print(f"  Lines: {source.count(chr(10)) + 1}")

    # ── Source Listing ────────────────────────────────────────
    print_section("SOURCE CODE")
    for i, line in enumerate(source.splitlines(), 1):
        print(f"  {i:>3} │  {line}")

    # ── Phase 1: Lexing ───────────────────────────────────────
    print_section("PHASE 1 · LEXER  —  Tokenizing source")
    try:
        lexer  = Lexer(source)
        tokens = lexer.tokenize()
    except LexerError as e:
        print(f"\n  ✖ {e}")
        return

    # Pretty token table
    print(f"\n  {'#':<5} {'TYPE':<14} {'VALUE':<20} {'LINE'}")
    print(f"  {'─'*5} {'─'*14} {'─'*20} {'─'*4}")
    for i, tok in enumerate(tokens):
        if tok.type == TT_EOF:
            break
        print(f"  {i:<5} {tok.type:<14} {str(tok.value):<20} {tok.line}")
    print(f"\n  ✔ {len(tokens)-1} token(s) produced.")

    # ── Phase 2: Parsing ──────────────────────────────────────
    print_section("PHASE 2 · PARSER  —  Building AST")
    try:
        parser = Parser(tokens)
        ast    = parser.parse()
    except ParseError as e:
        print(f"\n  ✖ {e}")
        return

    # AST summary
    print(f"\n  {'NODE TYPE':<22} {'DETAILS'}")
    print(f"  {'─'*22} {'─'*30}")
    for node in ast:
        if isinstance(node, VarDeclNode):
            print(f"  {'VarDeclNode':<22} var {node.name}  (line {node.line})")
        elif isinstance(node, AssignNode):
            print(f"  {'AssignNode':<22} {node.name} = <expr>  (line {node.line})")
        elif isinstance(node, InputNode):
            print(f"  {'InputNode':<22} input {node.name}  (line {node.line})")
        elif isinstance(node, OutputNode):
            print(f"  {'OutputNode':<22} output {node.name}  (line {node.line})")
    print(f"\n  ✔ {len(ast)} AST node(s) produced.")

    # ── Phase 3: Semantic Analysis ────────────────────────────
    print_section("PHASE 3 · SEMANTIC ANALYSIS  —  Validating program")
    try:
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)
    except SemanticError as e:
        print(f"\n  ✖ {e}")
        return

    print(f"\n  Declared variables : {sorted(analyzer.declared)}")
    print(f"  ✔ No semantic errors found.")

    # ── Phase 4: Execution ────────────────────────────────────
    print_section("PHASE 4 · INTERPRETER  —  Executing program")
    print()
    try:
        interpreter = Interpreter()
        interpreter.run(ast)
    except RuntimeError_ as e:
        print(f"\n  ✖ {e}")
        
        return

    print_section("DONE  —  Program finished successfully")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python compiler.py <source_file.txt>")
        print("Example: python compiler.py program.txt")
        sys.exit(1)
       
    filepath = sys.argv[1]
    try:
        with open(filepath, 'r') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.",)
        sys.exit(1)

    compile_and_run(source, filepath)


if __name__ == '__main__':
    main()