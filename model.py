from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from multimethod import multimeta


class Visitor(metaclass=multimeta):
	"""Visitor base basado en multimethod/multimeta."""
	pass
	
	
class Node:
	lineno: int = 0
	
	def accept(self, v: Visitor):
		return v.visit(self)
		
		
# ===================================================
# Tipos
# ===================================================


class Type(Node):
	name: str = "<type>"
	
	def __str__(self) -> str:
		return self.name
		
	def __repr__(self) -> str:
		return self.name
		
	def __eq__(self, other: object) -> bool:
		return type(self) is type(other) and self.__dict__ == getattr(other, "__dict__", {})
		
		
@dataclass(eq=False)
class IntegerType(Type):
	name: str = "integer"
	
	
@dataclass(eq=False)
class BooleanType(Type):
	name: str = "boolean"


@dataclass(eq=False)
class FloatType(Type):
	name: str = "float"


@dataclass(eq=False)
class CharType(Type):
	name: str = "char"
	
	
@dataclass(eq=False)
class StringType(Type):
	name: str = "string"
	
	
@dataclass(eq=False)
class VoidType(Type):
	name: str = "void"
	
	
@dataclass(eq=False)
class ArrayType(Type):
	base: Type = field(default_factory=IntegerType)
	size: Optional[int] = None
	
	@property
	def name(self) -> str:
		return f"array[{self.size if self.size is not None else ''}] {self.base}"
		
	def __str__(self) -> str:
		return self.name
		
		
INT   = IntegerType()
BOOL  = BooleanType()
FLOAT = FloatType()
CHAR  = CharType()
STRING = StringType()
VOID  = VoidType()


# ===================================================
# Soporte para Visitor y tabla de símbolos
# ===================================================


@dataclass
class Symbol:
	name: str
	kind: str              # var, const, param, func
	type: Type
	node: Any = None
	mutable: bool = True
	params: list[Type] = field(default_factory=list)
	
	def __repr__(self) -> str:
		return (
			f"Symbol(name={self.name!r}, kind={self.kind!r}, type={self.type!r}, "
			f"mutable={self.mutable!r}, params={self.params!r})"
		)
		
		
# ===================================================
# Programa y auxiliares
# ===================================================


@dataclass
class Program(Node):
	decls: list[Node]
	lineno: int = 0
	
	
@dataclass
class Block(Node):
	stmts: list[Node]
	lineno: int = 0
	
	
@dataclass
class Param(Node):
	name: str
	type: Type
	lineno: int = 0
	
	
@dataclass
class ParamList(Node):
	params: list[Param]
	lineno: int = 0
	
	
@dataclass
class ExprList(Node):
	exprs: list[Node]
	lineno: int = 0
	
	
# ===================================================
# Declaraciones
# ===================================================


@dataclass
class VarDecl(Node):
	name: str
	type: Type
	value: Optional[Node] = None
	mutable: bool = True
	lineno: int = 0
	
	
@dataclass
class ConstDecl(Node):
	name: str
	type: Type
	value: Node
	lineno: int = 0
	mutable: bool = False
	
	
@dataclass
class FuncDecl(Node):
	name: str
	parms: ParamList
	type: Type
	body: Block
	lineno: int = 0
	
	
# ===================================================
# Sentencias
# ===================================================


@dataclass
class Assignment(Node):
	loc: Node
	expr: Node
	oper: str = "="
	lineno: int = 0
	
	
@dataclass
class PrintStmt(Node):
	expr: Node
	lineno: int = 0
	
	
@dataclass
class IfStmt(Node):
	test: Node
	then_block: Block
	else_block: Optional[Block] = None
	lineno: int = 0
	
	
@dataclass
class WhileStmt(Node):
	test: Node
	body: Block
	lineno: int = 0
	
	
@dataclass
class ForStmt(Node):
	init: Optional[Node]
	test: Optional[Node]
	step: Optional[Node]
	body: Block
	lineno: int = 0
	
	
@dataclass
class ReturnStmt(Node):
	expr: Optional[Node] = None
	lineno: int = 0
	
	
# ===================================================
# Expresiones y ubicaciones
# ===================================================


@dataclass
class Expr(Node):
	type: Optional[Type] = None
	lineno: int = 0
	
	
@dataclass
class VarLoc(Expr):
	name: str = ""
	sym: Optional[Symbol] = None
	lineno: int = 0
	type: Optional[Type] = None
	
	
@dataclass
class ArrayLoc(Expr):
	name: str = ""
	index: Node = None
	sym: Optional[Symbol] = None
	lineno: int = 0
	type: Optional[Type] = None
	
	
@dataclass
class FuncCall(Expr):
	name: str = ""
	args: ExprList = field(default_factory=lambda: ExprList([]))
	sym: Optional[Symbol] = None
	lineno: int = 0
	type: Optional[Type] = None
	
	
@dataclass
class BinOp(Expr):
	oper: str = ""
	left: Node = None
	right: Node = None
	lineno: int = 0
	type: Optional[Type] = None
	
	
@dataclass
class UnaryOp(Expr):
	oper: str = ""
	expr: Node = None
	lineno: int = 0
	type: Optional[Type] = None
	
	
@dataclass
class IntegerLiteral(Expr):
	value: int = 0
	lineno: int = 0
	type: Optional[Type] = field(default_factory=IntegerType)


@dataclass
class BooleanLiteral(Expr):
	value: bool = False
	lineno: int = 0
	type: Optional[Type] = field(default_factory=BooleanType)


@dataclass
class CharLiteral(Expr):
	value: str = "\0"
	lineno: int = 0
	type: Optional[Type] = field(default_factory=CharType)


@dataclass
class StringLiteral(Expr):
	value: str = ""
	lineno: int = 0
	type: Optional[Type] = field(default_factory=StringType)


@dataclass
class FloatLiteral(Expr):
	value: float = 0.0
	lineno: int = 0
	type: Optional[Type] = field(default_factory=FloatType)


# ===================================================
# Nodos auxiliares no incluidos en el model base
# ===================================================

@dataclass
class BreakStmt(Node):
	lineno: int = 0


@dataclass
class ContinueStmt(Node):
	lineno: int = 0


@dataclass
class ArrayLiteral(Node):
	exprs: list
	lineno: int = 0

