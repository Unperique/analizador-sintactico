# model.py
# -*- coding: utf-8 -*-

class Node:
    """Clase base para todos los nodos del AST."""
    def __init__(self):
        self.lineno = None

# ==============================================================================
# Declaraciones
# ==============================================================================

class Program(Node):
    def __init__(self, decls):
        super().__init__()
        self.decls = decls

class VarDecl(Node):
    def __init__(self, name, datatype, value=None):
        super().__init__()
        self.name = name
        self.datatype = datatype
        self.value = value

class FuncDecl(Node):
    def __init__(self, name, datatype, params, body=None):
        super().__init__()
        self.name = name
        self.datatype = datatype
        self.params = params
        self.body = body

class Parameter(Node):
    def __init__(self, name, datatype):
        super().__init__()
        self.name = name
        self.datatype = datatype

# ==============================================================================
# Tipos
# ==============================================================================

class SimpleType(Node):
    def __init__(self, name):
        super().__init__()
        self.name = name

class ArrayType(Node):
    def __init__(self, basetype, size=None):
        super().__init__()
        self.basetype = basetype
        self.size = size

class FuncType(Node):
    def __init__(self, returntype, params):
        super().__init__()
        self.returntype = returntype
        self.params = params

# ==============================================================================
# Sentencias
# ==============================================================================

class Block(Node):
    def __init__(self, stmts):
        super().__init__()
        self.stmts = stmts

class IfStmt(Node):
    def __init__(self, cond, then_b, else_b=None):
        super().__init__()
        self.cond = cond
        self.then_b = then_b
        self.else_b = else_b

class ForStmt(Node):
    def __init__(self, init, cond, update, body):
        super().__init__()
        self.init = init
        self.cond = cond
        self.update = update
        self.body = body

class WhileStmt(Node):
    def __init__(self, cond, body):
        super().__init__()
        self.cond = cond
        self.body = body

class PrintStmt(Node):
    def __init__(self, exprs):
        super().__init__()
        self.exprs = exprs

class ReturnStmt(Node):
    def __init__(self, expr=None):
        super().__init__()
        self.expr = expr

class BreakStmt(Node):
    def __init__(self):
        super().__init__()

class ContinueStmt(Node):
    def __init__(self):
        super().__init__()

class ExprStmt(Node):
    def __init__(self, expr):
        super().__init__()
        self.expr = expr

# ==============================================================================
# Expresiones
# ==============================================================================

class BinaryOp(Node):
    def __init__(self, op, left, right):
        super().__init__()
        self.op = op
        self.left = left
        self.right = right

class UnaryOp(Node):
    def __init__(self, op, expr):
        super().__init__()
        self.op = op
        self.expr = expr

class PostfixOp(Node):
    def __init__(self, op, expr):
        super().__init__()
        self.op = op
        self.expr = expr

class AssignOp(Node):
    def __init__(self, op, lval, expr):
        super().__init__()
        self.op = op
        self.lval = lval
        self.expr = expr

class Location(Node):
    def __init__(self, name):
        super().__init__()
        self.name = name

class ArrayAccess(Node):
    def __init__(self, name, index):
        super().__init__()
        self.name = name
        self.index = index

class FuncCall(Node):
    def __init__(self, name, args):
        super().__init__()
        self.name = name
        self.args = args

class ArrayLiteral(Node):
    def __init__(self, exprs):
        super().__init__()
        self.exprs = exprs

class Literal(Node):
    def __init__(self, value, type_name):
        super().__init__()
        self.value = value
        self.type_name = type_name
