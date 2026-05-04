# checker.py
# -*- coding: utf-8 -*-
'''
Analizador semántico para B-Minor (nuevo model.py del profe).

Recorre el AST con el patrón Visitor (multimethod/multimeta).
Por cada nodo: gestiona tabla de símbolos, anota node.type y acumula errores.

Uso:
    from checker import Checker
    checker = Checker.check(ast)
    if not checker.ok():
        for msg in checker.errors: print(msg)
'''
from __future__ import annotations

from typing import Optional
from multimethod import multimeta

from symtab import Symtab
from model  import (
    Node, Visitor, Symbol,
    Type, IntegerType, BooleanType, FloatType, CharType, StringType, VoidType, ArrayType,
    INT, BOOL, FLOAT, CHAR, STRING, VOID,
    Program,
    VarDecl, ConstDecl, FuncDecl, Param, ParamList,
    Block,
    IfStmt, ForStmt, WhileStmt,
    PrintStmt, ReturnStmt, BreakStmt, ContinueStmt,
    Assignment,
    BinOp, UnaryOp,
    VarLoc, ArrayLoc, FuncCall, ExprList, ArrayLiteral,
    IntegerLiteral, BooleanLiteral, FloatLiteral, CharLiteral, StringLiteral,
)


# =============================================================================
# Tablas de compatibilidad de operadores (usando Type)
# =============================================================================

def _t(ty: Type) -> str:
    return type(ty).__name__


_BINOP: dict[tuple, type] = {
    # integer aritmética
    ('IntegerType', '+',  'IntegerType'): IntegerType,
    ('IntegerType', '-',  'IntegerType'): IntegerType,
    ('IntegerType', '*',  'IntegerType'): IntegerType,
    ('IntegerType', '/',  'IntegerType'): IntegerType,
    ('IntegerType', '%',  'IntegerType'): IntegerType,
    ('IntegerType', '^',  'IntegerType'): IntegerType,
    # integer comparación
    ('IntegerType', '<',  'IntegerType'): BooleanType,
    ('IntegerType', '<=', 'IntegerType'): BooleanType,
    ('IntegerType', '>',  'IntegerType'): BooleanType,
    ('IntegerType', '>=', 'IntegerType'): BooleanType,
    ('IntegerType', '==', 'IntegerType'): BooleanType,
    ('IntegerType', '!=', 'IntegerType'): BooleanType,
    # float aritmética
    ('FloatType', '+',  'FloatType'): FloatType,
    ('FloatType', '-',  'FloatType'): FloatType,
    ('FloatType', '*',  'FloatType'): FloatType,
    ('FloatType', '/',  'FloatType'): FloatType,
    ('FloatType', '%',  'FloatType'): FloatType,
    ('FloatType', '^',  'FloatType'): FloatType,
    # float comparación
    ('FloatType', '<',  'FloatType'): BooleanType,
    ('FloatType', '<=', 'FloatType'): BooleanType,
    ('FloatType', '>',  'FloatType'): BooleanType,
    ('FloatType', '>=', 'FloatType'): BooleanType,
    ('FloatType', '==', 'FloatType'): BooleanType,
    ('FloatType', '!=', 'FloatType'): BooleanType,
    # boolean
    ('BooleanType', '&&', 'BooleanType'): BooleanType,
    ('BooleanType', '||', 'BooleanType'): BooleanType,
    ('BooleanType', '==', 'BooleanType'): BooleanType,
    ('BooleanType', '!=', 'BooleanType'): BooleanType,
    # char
    ('CharType', '<',  'CharType'): BooleanType,
    ('CharType', '<=', 'CharType'): BooleanType,
    ('CharType', '>',  'CharType'): BooleanType,
    ('CharType', '>=', 'CharType'): BooleanType,
    ('CharType', '==', 'CharType'): BooleanType,
    ('CharType', '!=', 'CharType'): BooleanType,
    # string
    ('StringType', '+',  'StringType'): StringType,
    ('StringType', '==', 'StringType'): BooleanType,
    ('StringType', '!=', 'StringType'): BooleanType,
}

_UNARYOP: dict[tuple, type] = {
    ('+',  'IntegerType'): IntegerType,
    ('-',  'IntegerType'): IntegerType,
    ('++', 'IntegerType'): IntegerType,
    ('--', 'IntegerType'): IntegerType,
    ('+',  'FloatType'):   FloatType,
    ('-',  'FloatType'):   FloatType,
    ('!',  'BooleanType'): BooleanType,
}


def check_binop(oper: str, lt: Type, rt: Type) -> Optional[Type]:
    cls = _BINOP.get((_t(lt), oper, _t(rt)))
    return cls() if cls else None


def check_unaryop(oper: str, t: Type) -> Optional[Type]:
    cls = _UNARYOP.get((oper, _t(t)))
    return cls() if cls else None


def types_eq(a: Optional[Type], b: Optional[Type]) -> bool:
    if a is None or b is None:
        return True   # no propagar errores si falta info
    return type(a) is type(b)


# =============================================================================
# Checker
# =============================================================================

class Checker(Visitor):

    def __init__(self):
        self.errors          : list[str]          = []
        self.symtab          : Optional[Symtab]   = None
        self.current_function: Optional[FuncDecl] = None

    @classmethod
    def check(cls, node: Node) -> 'Checker':
        c = cls()
        c._open("global")
        c.visit(node)
        return c

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _err(self, node: Node, msg: str):
        ln = getattr(node, 'lineno', '?')
        self.errors.append(f"Error Semántico (línea {ln}): {msg}")

    def _open(self, name: str):
        self.symtab = Symtab(name) if self.symtab is None else Symtab(name, parent=self.symtab)

    def _close(self):
        if self.symtab:
            self.symtab = self.symtab.parent

    def _define(self, node: Node, name: str, sym: Symbol):
        try:
            self.symtab.add(name, sym)
        except Symtab.SymbolDefinedError:
            self._err(node, f"redeclaración de '{name}' en el mismo alcance")
        except Symtab.SymbolConflictError:
            self._err(node, f"conflicto de símbolo '{name}' (tipo distinto al previo)")

    def _lookup(self, node: Node, name: str) -> Optional[Symbol]:
        sym = self.symtab.get(name) if self.symtab else None
        if sym is None:
            self._err(node, f"símbolo '{name}' no definido")
        return sym

    def ok(self) -> bool:
        return len(self.errors) == 0

    # ==================================================================
    # Programa
    # ==================================================================

    def visit(self, n: Program):
        for d in n.decls:
            self.visit(d)

    # ==================================================================
    # Declaraciones
    # ==================================================================

    def visit(self, n: VarDecl):
        if n.value is not None:
            self.visit(n.value)
            vt = getattr(n.value, 'type', None)
            if vt is not None and n.type is not None:
                if not isinstance(n.type, VoidType) and not types_eq(n.type, vt):
                    self._err(n, f"no se puede inicializar '{n.name}' "
                                 f"({n.type}) con valor de tipo {vt}")
        sym = Symbol(name=n.name, kind='var', type=n.type, node=n, mutable=n.mutable)
        self._define(n, n.name, sym)

    def visit(self, n: ConstDecl):
        self.visit(n.value)
        inferred = getattr(n.value, 'type', None)
        # Si el tipo es VOID (placeholder del parser), inferirlo del valor
        if isinstance(n.type, VoidType) and inferred is not None:
            n.type = inferred
        elif inferred is not None and not isinstance(n.type, VoidType):
            if not types_eq(n.type, inferred):
                self._err(n, f"constante '{n.name}': tipo declarado {n.type} "
                              f"no coincide con valor de tipo {inferred}")
        sym = Symbol(name=n.name, kind='const', type=n.type, node=n, mutable=False)
        self._define(n, n.name, sym)

    def visit(self, n: FuncDecl):
        param_types = [p.type for p in n.parms.params]
        sym = Symbol(name=n.name, kind='func', type=n.type, node=n,
                     mutable=False, params=param_types)
        self._define(n, n.name, sym)

        if not n.body.stmts:   # prototipo vacío — solo registrar
            return

        prev = self.current_function
        self.current_function = n

        self._open(f"function {n.name}")
        for p in n.parms.params:
            self.visit(p)
        self.visit(n.body)
        self._close()

        self.current_function = prev

    def visit(self, n: Param):
        sym = Symbol(name=n.name, kind='param', type=n.type, node=n)
        self._define(n, n.name, sym)

    def visit(self, n: ParamList):
        pass   # procesado desde FuncDecl

    # ==================================================================
    # Sentencias
    # ==================================================================

    def visit(self, n: Block):
        self._open("block")
        for s in n.stmts:
            self.visit(s)
        self._close()

    def visit(self, n: IfStmt):
        if n.test is not None:
            self.visit(n.test)
            tt = getattr(n.test, 'type', None)
            if tt is not None and not isinstance(tt, BooleanType):
                self._err(n, f"condición del if debe ser boolean, se recibió {tt}")
        self.visit(n.then_block)
        if n.else_block is not None:
            self.visit(n.else_block)

    def visit(self, n: WhileStmt):
        if n.test is not None:
            self.visit(n.test)
            tt = getattr(n.test, 'type', None)
            if tt is not None and not isinstance(tt, BooleanType):
                self._err(n, f"condición del while debe ser boolean, se recibió {tt}")
        self.visit(n.body)

    def visit(self, n: ForStmt):
        self._open("for")
        if n.init is not None:
            self.visit(n.init)
        if n.test is not None:
            self.visit(n.test)
            tt = getattr(n.test, 'type', None)
            if tt is not None and not isinstance(tt, BooleanType):
                self._err(n, f"condición del for debe ser boolean, se recibió {tt}")
        if n.step is not None:
            self.visit(n.step)
        self.visit(n.body)
        self._close()

    def visit(self, n: PrintStmt):
        self.visit(n.expr)

    def visit(self, n: ReturnStmt):
        if n.expr is not None:
            self.visit(n.expr)
        if self.current_function is None:
            return
        expected = self.current_function.type   # Type de retorno
        if n.expr is None:
            if expected is not None and not isinstance(expected, VoidType):
                self._err(n, f"función '{self.current_function.name}' debe "
                              f"retornar {expected}, no retorna nada")
        else:
            actual = getattr(n.expr, 'type', None)
            if actual is not None and expected is not None:
                if not types_eq(expected, actual):
                    self._err(n, f"retorno incorrecto en '{self.current_function.name}': "
                                 f"se esperaba {expected}, se recibió {actual}")

    def visit(self, n: BreakStmt):
        pass

    def visit(self, n: ContinueStmt):
        pass

    # ==================================================================
    # Expresiones
    # ==================================================================

    def visit(self, n: Assignment):
        self.visit(n.loc)
        self.visit(n.expr)
        lt = getattr(n.loc,  'type', None)
        rt = getattr(n.expr, 'type', None)

        if n.oper == '=':
            if lt is not None and rt is not None and not types_eq(lt, rt):
                self._err(n, f"no se puede asignar {rt} a {lt}")
            n.type = lt
        else:
            base_op = n.oper[0]   # '+', '-', '*', '/', '%'
            if lt is not None and rt is not None:
                result = check_binop(base_op, lt, rt)
                if result is None:
                    self._err(n, f"operador '{n.oper}' no soportado entre {lt} y {rt}")
                elif not types_eq(lt, result):
                    self._err(n, f"resultado de '{n.oper}' ({result}) no compatible con {lt}")
            n.type = lt

    def visit(self, n: BinOp):
        self.visit(n.left)
        self.visit(n.right)
        lt = getattr(n.left,  'type', None)
        rt = getattr(n.right, 'type', None)
        if lt is not None and rt is not None:
            result = check_binop(n.oper, lt, rt)
            if result is None:
                self._err(n, f"operador '{n.oper}' no soportado entre {lt} y {rt}")
            n.type = result
        else:
            n.type = None

    def visit(self, n: UnaryOp):
        self.visit(n.expr)
        t = getattr(n.expr, 'type', None)
        if t is not None:
            result = check_unaryop(n.oper, t)
            if result is None:
                self._err(n, f"operador '{n.oper}' no soportado para tipo {t}")
            n.type = result
        else:
            n.type = None

    def visit(self, n: VarLoc):
        sym = self._lookup(n, n.name)
        n.sym  = sym
        n.type = sym.type if sym else None

    def visit(self, n: ArrayLoc):
        sym = self._lookup(n, n.name)
        n.sym = sym
        if sym is not None:
            if isinstance(sym.type, ArrayType):
                n.type = sym.type.base
            else:
                self._err(n, f"'{n.name}' no es un arreglo")
                n.type = None
        else:
            n.type = None
        self.visit(n.index)
        it = getattr(n.index, 'type', None)
        if it is not None and not isinstance(it, IntegerType):
            self._err(n, f"índice del arreglo debe ser integer, se recibió {it}")

    def visit(self, n: FuncCall):
        sym = self._lookup(n, n.name)
        if sym is not None and sym.kind not in ('func',):
            self._err(n, f"'{n.name}' no es una función")
            sym = None

        for arg in n.args.exprs:
            self.visit(arg)

        if sym is not None:
            fn_node = sym.node
            if fn_node is not None:
                expected = len(fn_node.parms.params)
                actual   = len(n.args.exprs)
                if expected != actual:
                    self._err(n, f"función '{n.name}' espera {expected} "
                                 f"arg(s) pero recibió {actual}")
                else:
                    for i, (arg, param) in enumerate(zip(n.args.exprs, fn_node.parms.params)):
                        at = getattr(arg, 'type', None)
                        pt = param.type
                        if at is not None and pt is not None and not types_eq(at, pt):
                            self._err(n, f"argumento {i+1} de '{n.name}': "
                                         f"se esperaba {pt}, se recibió {at}")
            n.type = sym.type
        else:
            n.type = None
        n.sym = sym

    def visit(self, n: ExprList):
        for e in n.exprs:
            self.visit(e)

    def visit(self, n: ArrayLiteral):
        for e in n.exprs:
            self.visit(e)
        types = [getattr(e, 'type', None) for e in n.exprs if getattr(e, 'type', None)]
        if types and len({type(t).__name__ for t in types}) > 1:
            self._err(n, f"elementos del arreglo tienen tipos inconsistentes")

    # Literales — anotar tipo
    def visit(self, n: IntegerLiteral): pass   # type ya fijado en model
    def visit(self, n: BooleanLiteral): pass
    def visit(self, n: FloatLiteral):   pass
    def visit(self, n: CharLiteral):    pass
    def visit(self, n: StringLiteral):  pass


# =============================================================================
# Punto de entrada CLI
# =============================================================================

if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    from rich.console import Console
    from parser       import parse
    from errors       import errors_detected, clear_errors

    if len(sys.argv) != 2:
        raise SystemExit("Uso: python checker.py <archivo.bminor>")

    console  = Console(force_terminal=True, highlight=False)
    filename = sys.argv[1]
    try:
        source = open(filename, encoding='utf-8').read()
    except FileNotFoundError:
        raise SystemExit(f"Archivo no encontrado: {filename}")

    clear_errors()
    ast = parse(source)
    if errors_detected() or ast is None:
        raise SystemExit("Errores léxicos/sintácticos. Corrígelos antes del análisis semántico.")

    checker = Checker.check(ast)
    if checker.ok():
        console.print(f"\n[bold green]semantic check: success[/bold green]  ({filename})\n")
    else:
        for msg in checker.errors:
            console.print(f"[bold red]{msg}[/bold red]")
        n = len(checker.errors)
        console.print(f"\n[bold red]semantic check: failed[/bold red] — "
                      f"{n} error{'es' if n != 1 else ''} semántico{'s' if n != 1 else ''}\n")
    sys.exit(0 if checker.ok() else 1)
