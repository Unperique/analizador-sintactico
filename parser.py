# parser.py
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
    debugfile = 'grammar.txt'

    tokens = Lexer.tokens

    # =================================================
    # PROGRAMA
    # =================================================

    @_("decl_list")
    def prog(self, p):
        return _L(Program(decls=p.decl_list), p.lineno)

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
        return _L(VarDecl(name=p.ID, type=p.type_simple), p.lineno)

    @_("ID ':' type_array_sized ';'")
    def decl(self, p):
        return _L(VarDecl(name=p.ID, type=p.type_array_sized), p.lineno)

    @_("ID ':' FUNCTION type_ret '(' opt_param_list ')' ';'")
    def decl(self, p):
        parms = _L(ParamList(params=p.opt_param_list), p.lineno)
        return _L(FuncDecl(name=p.ID, parms=parms, type=p.type_ret, body=Block(stmts=[])), p.lineno)

    @_("decl_init")
    def decl(self, p):
        return p.decl_init

    # === DECLARACIONES con inicialización

    @_("ID ':' type_simple '=' expr ';'")
    def decl_init(self, p):
        return _L(VarDecl(name=p.ID, type=p.type_simple, value=p.expr), p.lineno)

    @_("ID ':' CONSTANT '=' expr ';'")
    def decl_init(self, p):
        return _L(ConstDecl(name=p.ID, type=VOID, value=p.expr), p.lineno)

    @_("ID ':' type_array_sized '=' '{' opt_expr_list '}' ';'")
    def decl_init(self, p):
        return _L(VarDecl(name=p.ID, type=p.type_array_sized, value=ArrayLiteral(exprs=p.opt_expr_list)), p.lineno)

    @_("ID ':' FUNCTION type_ret '(' opt_param_list ')' '=' '{' opt_stmt_list '}'")
    def decl_init(self, p):
        parms = _L(ParamList(params=p.opt_param_list), p.lineno)
        return _L(FuncDecl(name=p.ID, parms=parms, type=p.type_ret, body=Block(stmts=p.opt_stmt_list)), p.lineno)

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
        return _L(IfStmt(test=p.if_cond,
                         then_block=as_block(p.closed_stmt0),
                         else_block=as_block(p.closed_stmt1)), p.lineno)

    @_("if_cond stmt")
    def if_stmt_open(self, p):
        return _L(IfStmt(test=p.if_cond, then_block=as_block(p.stmt), else_block=None), p.lineno)

    @_("if_cond closed_stmt ELSE if_stmt_open")
    def if_stmt_open(self, p):
        return _L(IfStmt(test=p.if_cond,
                         then_block=as_block(p.closed_stmt),
                         else_block=as_block(p.if_stmt_open)), p.lineno)

    # -------------------------------------------------
    # FOR
    # -------------------------------------------------

    @_("FOR '(' opt_expr ';' opt_expr ';' opt_expr ')'")
    def for_header(self, p):
        return (p.opt_expr0, p.opt_expr1, p.opt_expr2)

    @_("for_header open_stmt")
    def for_stmt_open(self, p):
        init, test, step = p.for_header
        return _L(ForStmt(init=init, test=test, step=step, body=as_block(p.open_stmt)), p.lineno)

    @_("for_header closed_stmt")
    def for_stmt_closed(self, p):
        init, test, step = p.for_header
        return _L(ForStmt(init=init, test=test, step=step, body=as_block(p.closed_stmt)), p.lineno)

    # -------------------------------------------------
    # WHILE
    # -------------------------------------------------

    @_("WHILE '(' opt_expr ')'")
    def while_cond(self, p):
        return p.opt_expr

    @_("while_cond open_stmt")
    def while_stmt_open(self, p):
        return _L(WhileStmt(test=p.while_cond, body=as_block(p.open_stmt)), p.lineno)

    @_("while_cond closed_stmt")
    def while_stmt_closed(self, p):
        return _L(WhileStmt(test=p.while_cond, body=as_block(p.closed_stmt)), p.lineno)

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
        # Assignment, FuncCall, UnaryOp como sentencias se incluyen directamente
        return p.expr

    # PRINT — una o varias expresiones; varias se envuelven en ExprList
    @_("PRINT opt_expr_list ';'")
    def print_stmt(self, p):
        exprs = p.opt_expr_list
        if len(exprs) == 1:
            expr = exprs[0]
        elif len(exprs) == 0:
            expr = ExprList(exprs=[])
        else:
            expr = ExprList(exprs=exprs)
        return _L(PrintStmt(expr=expr), p.lineno)

    # RETURN
    @_("RETURN opt_expr ';'")
    def return_stmt(self, p):
        return _L(ReturnStmt(expr=p.opt_expr), p.lineno)

    @_("BREAK ';'")
    def break_stmt(self, p):
        return _L(BreakStmt(), p.lineno)

    @_("CONTINUE ';'")
    def continue_stmt(self, p):
        return _L(ContinueStmt(), p.lineno)

    # BLOCK
    @_("'{' stmt_list '}'")
    def block_stmt(self, p):
        return _L(Block(stmts=p.stmt_list), p.lineno)

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
    # ASIGNACIONES
    # -------------------------------------------------

    @_("expr1")
    def expr(self, p):
        return p[0]

    @_("lval  '='  expr1")
    def expr1(self, p):
        return _L(Assignment(loc=p.lval, expr=p.expr1, oper='='), p.lineno)

    @_("lval ADDEQ expr1")
    def expr1(self, p):
        return _L(Assignment(loc=p.lval, expr=p.expr1, oper='+='), p.lineno)

    @_("lval SUBEQ expr1")
    def expr1(self, p):
        return _L(Assignment(loc=p.lval, expr=p.expr1, oper='-='), p.lineno)

    @_("lval MULEQ expr1")
    def expr1(self, p):
        return _L(Assignment(loc=p.lval, expr=p.expr1, oper='*='), p.lineno)

    @_("lval DIVEQ expr1")
    def expr1(self, p):
        return _L(Assignment(loc=p.lval, expr=p.expr1, oper='/='), p.lineno)

    @_("lval MODEQ expr1")
    def expr1(self, p):
        return _L(Assignment(loc=p.lval, expr=p.expr1, oper='%='), p.lineno)

    @_("expr2")
    def expr1(self, p):
        return p[0]

    # ----------- LVALUES -------------------

    @_("ID")
    def lval(self, p):
        return _L(VarLoc(name=p.ID), p.lineno)

    @_("ID subscript")
    def lval(self, p):
        return _L(ArrayLoc(name=p.ID, index=p.subscript), p.lineno)

    # -------------------------------------------------
    # OPERADORES BINARIOS (precedencia ascendente)
    # -------------------------------------------------

    @_("expr2 LOR expr3")
    def expr2(self, p):
        return _L(BinOp(oper=p[1], left=p.expr2, right=p.expr3), p.lineno)

    @_("expr3")
    def expr2(self, p):
        return p[0]

    @_("expr3 LAND expr4")
    def expr3(self, p):
        return _L(BinOp(oper=p[1], left=p.expr3, right=p.expr4), p.lineno)

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
        return _L(BinOp(oper=p[1], left=p.expr4, right=p.expr5), p.lineno)

    @_("expr5")
    def expr4(self, p):
        return p[0]

    @_("expr5 '+' expr6")
    @_("expr5 '-' expr6")
    def expr5(self, p):
        return _L(BinOp(oper=p[1], left=p.expr5, right=p.expr6), p.lineno)

    @_("expr6")
    def expr5(self, p):
        return p[0]

    @_("expr6 '*' expr7")
    @_("expr6 '/' expr7")
    @_("expr6 '%' expr7")
    def expr6(self, p):
        return _L(BinOp(oper=p[1], left=p.expr6, right=p.expr7), p.lineno)

    @_("expr7")
    def expr6(self, p):
        return p[0]

    @_("expr7 '^' expr8")
    def expr7(self, p):
        return _L(BinOp(oper=p[1], left=p.expr7, right=p.expr8), p.lineno)

    @_("expr8")
    def expr7(self, p):
        return p[0]

    @_("'-' expr8")
    @_("'!' expr8")
    def expr8(self, p):
        return _L(UnaryOp(oper=p[0], expr=p.expr8), p.lineno)

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
        return _L(UnaryOp(oper='++', expr=p.postfix), p.lineno)

    @_("postfix DEC")
    def postfix(self, p):
        return _L(UnaryOp(oper='--', expr=p.postfix), p.lineno)

    @_("prefix")
    def primary(self, p):
        return p[0]

    @_("INC prefix")
    def prefix(self, p):
        return _L(UnaryOp(oper='++', expr=p.prefix), p.lineno)

    @_("DEC prefix")
    def prefix(self, p):
        return _L(UnaryOp(oper='--', expr=p.prefix), p.lineno)

    @_("group")
    def prefix(self, p):
        return p[0]

    @_("'(' expr ')'")
    def group(self, p):
        return p.expr

    @_("ID '(' opt_expr_list ')'")
    def group(self, p):
        return _L(FuncCall(name=p.ID, args=ExprList(exprs=p.opt_expr_list)), p.lineno)

    @_("ID subscript")
    def group(self, p):
        return _L(ArrayLoc(name=p.ID, index=p.subscript), p.lineno)

    @_("factor")
    def group(self, p):
        return p[0]

    # ÍNDICE DE ARREGLO
    @_("'[' expr ']'")
    def subscript(self, p):
        return p.expr

    # -------------------------------------------------
    # FACTORES (literales e identificadores)
    # -------------------------------------------------

    @_("ID")
    def factor(self, p):
        return _L(VarLoc(name=p.ID), p.lineno)

    @_("INTEGER_LITERAL")
    def factor(self, p):
        return _L(IntegerLiteral(value=p[0]), p.lineno)

    @_("FLOAT_LITERAL")
    def factor(self, p):
        return _L(FloatLiteral(value=p[0]), p.lineno)

    @_("CHAR_LITERAL")
    def factor(self, p):
        return _L(CharLiteral(value=p[0]), p.lineno)

    @_("STRING_LITERAL")
    def factor(self, p):
        return _L(StringLiteral(value=p[0]), p.lineno)

    @_("TRUE")
    def factor(self, p):
        return _L(BooleanLiteral(value=True), p.lineno)

    @_("FALSE")
    def factor(self, p):
        return _L(BooleanLiteral(value=False), p.lineno)

    # =================================================
    # TIPOS
    # =================================================

    @_("INTEGER")
    def type_simple(self, p):
        return IntegerType()

    @_("FLOAT")
    def type_simple(self, p):
        return FloatType()

    @_("BOOLEAN")
    def type_simple(self, p):
        return BooleanType()

    @_("CHAR")
    def type_simple(self, p):
        return CharType()

    @_("STRING")
    def type_simple(self, p):
        return StringType()

    @_("VOID")
    def type_simple(self, p):
        return VoidType()

    @_("type_simple")
    @_("type_array_sized")
    def type_ret(self, p):
        return p[0]

    @_("ARRAY '[' ']' type_simple")
    @_("ARRAY '[' ']' type_array")
    def type_array(self, p):
        return ArrayType(base=p[3])

    @_("ARRAY subscript type_simple")
    @_("ARRAY subscript type_array_sized")
    def type_array_sized(self, p):
        size_node = p.subscript
        size = size_node.value if isinstance(size_node, IntegerLiteral) else None
        return ArrayType(base=p[2], size=size)

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
        return _L(Param(name=p.ID, type=p.type_simple), p.lineno)

    @_("ID ':' type_array")
    def param(self, p):
        return _L(Param(name=p.ID, type=p.type_array), p.lineno)

    @_("ID ':' type_array_sized")
    def param(self, p):
        return _L(Param(name=p.ID, type=p.type_array_sized), p.lineno)

    # =================================================
    # UTILIDAD: EMPTY
    # =================================================

    @_("")
    def empty(self, p):
        pass

    def error(self, p):
        if p:
            error(f"Token inesperado: {p.value!r} (tipo: {p.type})", p.lineno, "Error Sintáctico")
        else:
            error("Fin de archivo inesperado (¿falta cerrar un bloque o expresión?)", error_type="Error Sintáctico")


# ===================================================
# Utilidad: convertir algo en bloque si no lo es
# ===================================================

def as_block(x):
    if isinstance(x, Block):
        return x
    if isinstance(x, list):
        return Block(stmts=x)
    return Block(stmts=[x])


# ===================================================
# Punto de entrada
# ===================================================

def parse(txt):
    l = Lexer()
    p = Parser()
    return p.parse(l.tokenize(txt))


if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    if len(sys.argv) != 2:
        raise SystemExit("Uso: python parser.py <archivo.bminor>")

    filename = sys.argv[1]
    txt = open(filename, encoding='utf-8').read()
    ast = parse(txt)

    if not errors_detected():
        from rich import print as rprint
        from rich.pretty import pprint
        pprint(ast)
