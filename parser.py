# grammar.py (versión actualizada para nuevo AST)
import logging
import sly
from rich import print

from lexer  import Lexer
from errors import error, errors_detected
from model  import *


def _L(node, lineno):
	node.lineno = lineno
	return node
	
	
class Parser(sly.Parser):
	log = logging.getLogger()
	log.setLevel(logging.ERROR)
	expected_shift_reduce = 1
	debugfile='grammar.txt'
	
	tokens = Lexer.tokens
	
	# =================================================
	# PROGRAMA
	# =================================================
	
	@_("decl_list")
	def prog(self, p):
		return _L(Program(p.decl_list), p.lineno)
	
	# =================================================
	# LISTAS DE DECLARACIONES
	# =================================================
	
	@_("decl decl_list")
	def decl_list(self, p):
		return [p.decl] + p.decl_list
		
	@_("empty")
	def decl_list(self, p):
		return []
		
	# =================================================
	# DECLARACIONES
	# =================================================
	
	@_("ID ':' type_simple ';'")
	def decl(self, p):
		return _L(VarDecl(p.ID, p.type_simple), p.lineno)
		
	@_("ID ':' type_array_sized ';'")
	def decl(self, p):
		return _L(VarDecl(p.ID, p.type_array_sized), p.lineno)
		
	@_("ID ':' type_func ';'")
	def decl(self, p):
		return _L(FuncDecl(p.ID, p.type_func, p.type_func.params, None), p.lineno)
		
	@_("decl_init")
	def decl(self, p):
		return p.decl_init
		
	# === DECLARACIONES con inicialización
	
	@_("ID ':' type_simple '=' expr ';'")
	def decl_init(self, p):
		return _L(VarDecl(p.ID, p.type_simple, p.expr), p.lineno)
		
	@_("ID ':' CONSTANT '=' expr ';'")
	def decl_init(self, p):
		# En B-Minor, constantes son como variables inicializadas pero con el modificador "const" que aquí no representamos distinto
		return _L(VarDecl(p.ID, p.CONSTANT, p.expr), p.lineno)
		
	@_("ID ':' type_array_sized '=' '{' opt_expr_list '}' ';'")
	def decl_init(self, p):
		return _L(VarDecl(p.ID, p.type_array_sized, ArrayLiteral(p.opt_expr_list)), p.lineno)
		
	@_("ID ':' type_func '=' '{' opt_stmt_list '}'")
	def decl_init(self, p):
		return _L(FuncDecl(p.ID, p.type_func, p.type_func.params, Block(p.opt_stmt_list)), p.lineno)
		
	# =================================================
	# STATEMENTS
	# =================================================
	
	@_("stmt_list")
	def opt_stmt_list(self, p):
		return p.stmt_list
		
	@_("empty")
	def opt_stmt_list(self, p):
		return []
		
	@_("stmt stmt_list")
	def stmt_list(self, p):
		return [p.stmt] + p.stmt_list
		
	@_("stmt")
	def stmt_list(self, p):
		return [p.stmt]
		
	@_("open_stmt")
	@_("closed_stmt")
	def stmt(self, p):
		return p[0]

	@_("if_stmt_closed")
	@_("for_stmt_closed")
	@_("while_stmt_closed")
	@_("simple_stmt")
	def closed_stmt(self, p):
		return p[0]

	@_("if_stmt_open")
	@_("for_stmt_open")
	@_("while_stmt_open")
	def open_stmt(self, p):
		return p[0]

	# -------------------------------------------------
	# IF
	# -------------------------------------------------
	
	@_("IF '(' opt_expr ')'")
	def if_cond(self, p):
		return p.opt_expr
		
	@_("if_cond closed_stmt ELSE closed_stmt")
	def if_stmt_closed(self, p):
		return _L(IfStmt(p.if_cond, as_block(p.closed_stmt0), as_block(p.closed_stmt1)), p.lineno)
		
	@_("if_cond stmt")
	def if_stmt_open(self, p):
		return _L(IfStmt(p.if_cond, as_block(p.stmt), None), p.lineno)
		
	@_("if_cond closed_stmt ELSE if_stmt_open")
	def if_stmt_open(self, p):
		return _L(IfStmt(p.if_cond, as_block(p.closed_stmt), as_block(p.if_stmt_open)), p.lineno)
		
	# -------------------------------------------------
	# FOR
	# -------------------------------------------------
	
	@_("FOR '(' opt_expr ';' opt_expr ';' opt_expr ')'")
	def for_header(self, p):
		return (p.opt_expr0, p.opt_expr1, p.opt_expr2)
		
	@_("for_header open_stmt")
	def for_stmt_open(self, p):
		return _L(ForStmt(p.for_header[0], p.for_header[1], p.for_header[2], as_block(p.open_stmt)), p.lineno)
		
	@_("for_header closed_stmt")
	def for_stmt_closed(self, p):
		return _L(ForStmt(p.for_header[0], p.for_header[1], p.for_header[2], as_block(p.closed_stmt)), p.lineno)
		
	# -------------------------------------------------
	# WHILE
	# -------------------------------------------------
	
	@_("WHILE '(' opt_expr ')'")
	def while_cond(self, p):
		return p.opt_expr
		
	@_("while_cond open_stmt")
	def while_stmt_open(self, p):
		return _L(WhileStmt(p.while_cond, as_block(p.open_stmt)), p.lineno)
		
	@_("while_cond closed_stmt")
	def while_stmt_closed(self, p):
		return _L(WhileStmt(p.while_cond, as_block(p.closed_stmt)), p.lineno)
		
	# -------------------------------------------------
	# SIMPLE STATEMENTS
	# -------------------------------------------------
	
	@_("print_stmt")
	@_("return_stmt")
	@_("break_stmt")
	@_("continue_stmt")
	@_("block_stmt")
	@_("decl")
	def simple_stmt(self, p):
		return p[0]

	@_("expr ';'")
	def simple_stmt(self, p):
		return _L(ExprStmt(p.expr), p.lineno)

	# PRINT
	@_("PRINT opt_expr_list ';'")
	def print_stmt(self, p):
		return _L(PrintStmt(p.opt_expr_list), p.lineno)
		
	# RETURN
	@_("RETURN opt_expr ';'")
	def return_stmt(self, p):
		return _L(ReturnStmt(p.opt_expr), p.lineno)

	@_("BREAK ';'")
	def break_stmt(self, p):
		return _L(BreakStmt(), p.lineno)

	@_("CONTINUE ';'")
	def continue_stmt(self, p):
		return _L(ContinueStmt(), p.lineno)

	# BLOCK
	@_("'{' stmt_list '}'")
	def block_stmt(self, p):
		return _L(Block(p.stmt_list), p.lineno)
		
	# =================================================
	# EXPRESIONES
	# =================================================
	
	@_("empty")
	def opt_expr_list(self, p):
		return []
		
	@_("expr_list")
	def opt_expr_list(self, p):
		return p.expr_list
		
	@_("expr ',' expr_list")
	def expr_list(self, p):
		return [p.expr] + p.expr_list
		
	@_("expr")
	def expr_list(self, p):
		return [p.expr]
		
	@_("empty")
	def opt_expr(self, p):
		return None
		
	@_("expr")
	def opt_expr(self, p):
		return p.expr
		
	# -------------------------------------------------
	# PRIMARY
	# -------------------------------------------------
	
	@_("expr1")
	def expr(self, p):
		return p[0]
		
	@_("lval  '='  expr1")
	@_("lval ADDEQ expr1")
	@_("lval SUBEQ expr1")
	@_("lval MULEQ expr1")
	@_("lval DIVEQ expr1")
	@_("lval MODEQ expr1")
	def expr1(self, p):
		return _L(AssignOp(p[1], p.lval, p.expr1), p.lineno)
		
	@_("expr2")
	def expr1(self, p):
		return p[0]
		
	# ----------- LVALUES -------------------
	
	@_("ID")
	def lval(self, p):
		return _L(Location(p.ID), p.lineno)
		
	@_("ID index")
	def lval(self, p):
		return _L(ArrayAccess(p.ID, p.index), p.lineno)
		
	# -------------------------------------------------
	# OPERADORES
	# -------------------------------------------------
	
	@_("expr2 LOR expr3")
	def expr2(self, p):
		return _L(BinaryOp(p[1], p.expr2, p.expr3), p.lineno)
		
	@_("expr3")
	def expr2(self, p):
		return p[0]
		
	@_("expr3 LAND expr4")
	def expr3(self, p):
		return _L(BinaryOp(p[1], p.expr3, p.expr4), p.lineno)
		
	@_("expr4")
	def expr3(self, p):
		return p[0]
		
	@_("expr4 EQ expr5")
	@_("expr4 NE expr5")
	@_("expr4 LT expr5")
	@_("expr4 LE expr5")
	@_("expr4 GT expr5")
	@_("expr4 GE expr5")
	def expr4(self, p):
		return _L(BinaryOp(p[1], p.expr4, p.expr5), p.lineno)

	@_("expr5")
	def expr4(self, p):
		return p[0]
		
	@_("expr5 '+' expr6")
	@_("expr5 '-' expr6")
	def expr5(self, p):
		return _L(BinaryOp(p[1], p.expr5, p.expr6), p.lineno)
		
	@_("expr6")
	def expr5(self, p):
		return p[0]
		
	@_("expr6 '*' expr7")
	@_("expr6 '/' expr7")
	@_("expr6 '%' expr7")
	def expr6(self, p):
		return _L(BinaryOp(p[1], p.expr6, p.expr7), p.lineno)
		
	@_("expr7")
	def expr6(self, p):
		return p[0]
		
	@_("expr7 '^' expr8")
	def expr7(self, p):
		return _L(BinaryOp(p[1], p.expr7, p.expr8), p.lineno)
		
	@_("expr8")
	def expr7(self, p):
		return p[0]
		
	@_("'-' expr8")
	@_("'!' expr8")
	def expr8(self, p):
		return _L(UnaryOp(p[0], p.expr8), p.lineno)

	@_("expr9")
	def expr8(self, p):
		return p[0]

	@_("postfix")
	def expr9(self, p):
		return p[0]

	@_("primary")
	def postfix(self, p):
		return p[0]

	@_("postfix INC")
	def postfix(self, p):
		return _L(PostfixOp(p[1], p.postfix), p.lineno)

	@_("postfix DEC")
	def postfix(self, p):
		return _L(PostfixOp(p[1], p.postfix), p.lineno)

	@_("prefix")
	def primary(self, p):
		return p[0]

	@_("INC prefix")
	def prefix(self, p):
		return _L(UnaryOp(p[0], p.prefix), p.lineno)

	@_("DEC prefix")
	def prefix(self, p):
		return _L(UnaryOp(p[0], p.prefix), p.lineno)

	@_("group")
	def prefix(self, p):
		return p[0]
		
	@_("'(' expr ')'")
	def group(self, p):
		return p.expr
		
	@_("ID '(' opt_expr_list ')'")
	def group(self, p):
		return _L(FuncCall(p.ID, p.opt_expr_list), p.lineno)
		
	@_("ID index")
	def group(self, p):
		return _L(ArrayAccess(p.ID, p.index), p.lineno)
		
	@_("factor")
	def group(self, p):
		return p[0]
		
	# INDICE DE ARREGLO
	@_("'[' expr ']'")
	def index(self, p):
		return p.expr
	
	# -------------------------------------------------
	# FACTORES
	# -------------------------------------------------
	
	@_("ID")
	def factor(self, p):
		return _L(Location(p.ID), p.lineno)
		
	@_("INTEGER_LITERAL")
	def factor(self, p):
		return _L(Literal(p[0], "integer"), p.lineno)
		
	@_("FLOAT_LITERAL")
	def factor(self, p):
		return _L(Literal(p[0], "float"), p.lineno)
		
	@_("CHAR_LITERAL")
	def factor(self, p):
		return _L(Literal(p[0], "char"), p.lineno)
		
	@_("STRING_LITERAL")
	def factor(self, p):
		return _L(Literal(p[0], "string"), p.lineno)
		
	@_("TRUE", "FALSE")
	def factor(self, p):
		return _L(Literal(p[0], "boolean"), p.lineno)
		
	# =================================================
	# TIPOS
	# =================================================
	
	@_("INTEGER")
	@_("FLOAT")
	@_("BOOLEAN")
	@_("CHAR")
	@_("STRING")
	@_("VOID")
	def type_simple(self, p):
		return _L(SimpleType(p[0]), p.lineno)
		
	@_("ARRAY '[' ']' type_simple")
	@_("ARRAY '[' ']' type_array")
	def type_array(self, p):
		return _L(ArrayType(p[3]), p.lineno)
		
	@_("ARRAY index type_simple")
	@_("ARRAY index type_array_sized")
	def type_array_sized(self, p):
		return _L(ArrayType(p[2], p.index), p.lineno)
		
	@_("FUNCTION type_simple '(' opt_param_list ')'")
	@_("FUNCTION type_array_sized '(' opt_param_list ')'")
	def type_func(self, p):
		return _L(FuncType(p[1], p.opt_param_list), p.lineno)
		
	@_("empty")
	def opt_param_list(self, p):
		return []
		
	@_("param_list")
	def opt_param_list(self, p):
		return p.param_list
		
	@_("param_list ',' param")
	def param_list(self, p):
		return p.param_list + [p.param]
		
	@_("param")
	def param_list(self, p):
		return [p.param]
		
	@_("ID ':' type_simple")
	def param(self, p):
		return _L(Parameter(p.ID, p.type_simple), p.lineno)
		
	@_("ID ':' type_array")
	def param(self, p):
		return _L(Parameter(p.ID, p.type_array), p.lineno)
		
	@_("ID ':' type_array_sized")
	def param(self, p):
		return _L(Parameter(p.ID, p.type_array_sized), p.lineno)
		
	# =================================================
	# UTILIDAD: EMPTY
	# =================================================
	
	@_("")
	def empty(self, p):
		pass
		
	def error(self, p):
		lineno = p.lineno if p else 'EOF'
		value = repr(p.value) if p else 'EOF'
		error(f'Syntax error at {value}', lineno)
		
# ===================================================
# Utilidad: convertir algo en bloque si no lo es
# ===================================================
def as_block(x):
	if isinstance(x, Block):
		return x
	if isinstance(x, list):
		return Block(x)
	return Block([x])
	
	
# Convertir AST a diccionario
def ast_to_dict(node):
	if isinstance(node, list):
		return [ast_to_dict(item) for item in node]
	elif hasattr(node, "__dict__"):
		return {key: ast_to_dict(value) for key, value in node.__dict__.items()}
	else:
		return node

# ===================================================
# test
# ===================================================
def parse(txt):
	l = Lexer()
	p = Parser()
	return p.parse(l.tokenize(txt))
	
	
if __name__ == '__main__':
	import sys, json
	
	if sys.platform != 'ios':
	
		if len(sys.argv) != 2:
			raise SystemExit("Usage: python gparse.py <filename>")
			
		filename = sys.argv[1]
		
	else:
		from file_picker import file_picker_dialog
		
		filename = file_picker_dialog(
			title='Seleccionar una archivo',
			root_dir='./test/',
			file_pattern='^.*[.]bpp'
		)
		
	if filename:
		txt = open(filename, encoding='utf-8').read()
		ast = parse(txt)
		
		if not errors_detected():
			print(ast)
