# checker.py
# -*- coding: utf-8 -*-
'''
Analizador semántico para B-Minor.

Recorre el AST mediante el patrón Visitor implementado con `multimethod`
(metaclase multimeta).  Por cada nodo:
  - gestiona la tabla de símbolos y los alcances léxicos,
  - anota n.type con el tipo resultante,
  - acumula errores semánticos sin abortar.

Uso:
    from checker import Checker
    from parser  import parse

    ast     = parse(source_code)
    checker = Checker.check(ast)
    if not checker.ok():
        for msg in checker.errors:
            print(msg)
'''
from __future__ import annotations

from dataclasses import dataclass, field
from typing      import Any, Optional

from multimethod  import multimeta

from symtab  import Symtab
from typesys import check_binop, check_unaryop, lookup_type
from model   import (
    Node,
    Program,
    VarDecl, FuncDecl, Parameter,
    SimpleType, ArrayType, FuncType,
    Block,
    IfStmt, ForStmt, WhileStmt,
    PrintStmt, ReturnStmt, BreakStmt, ContinueStmt, ExprStmt,
    BinaryOp, UnaryOp, PostfixOp, AssignOp,
    Location, ArrayAccess, FuncCall, ArrayLiteral, Literal,
)


# =============================================================================
# Clase Visitor base (multimeta habilita despacho múltiple por tipo)
# =============================================================================

class Visitor(metaclass=multimeta):
    pass


# =============================================================================
# Símbolo en la tabla
# =============================================================================

@dataclass
class Symbol:
    name    : str
    kind    : str        # 'var' | 'param' | 'func'
    type    : Any        # str p.ej. 'integer', o tupla ('array','integer'), ('func','integer')
    node    : Any = None
    mutable : bool = True

    def __repr__(self):
        return f"Symbol({self.name!r}, kind={self.kind!r}, type={self.type!r})"


# =============================================================================
# Utilidades de tipos
# =============================================================================

def resolve_type(type_node) -> Any:
    """
    Convierte un nodo de tipo del AST en una representación de tipo interna:
      SimpleType('integer')          -> 'integer'
      ArrayType(SimpleType('int'),…) -> ('array', 'integer')
      FuncType(ret, params)          -> ('func', ret_type)
      str (fallback parser)          -> str
    """
    if isinstance(type_node, SimpleType):
        return type_node.name
    if isinstance(type_node, ArrayType):
        return ('array', resolve_type(type_node.basetype))
    if isinstance(type_node, FuncType):
        return ('func', resolve_type(type_node.returntype))
    if isinstance(type_node, str):
        return type_node   # 'constant' u otro fallback del parser
    return None


def types_compatible(t1, t2) -> bool:
    """Compatibilidad estricta de tipos (B-Minor es fuertemente tipado)."""
    return t1 == t2


def type_label(t) -> str:
    """Representación legible de un tipo para mensajes de error."""
    if isinstance(t, tuple):
        if t[0] == 'array':
            return f"array[{type_label(t[1])}]"
        if t[0] == 'func':
            return f"function→{type_label(t[1])}"
    return str(t) if t is not None else '?'


# =============================================================================
# Checker principal
# =============================================================================

class Checker(Visitor):

    def __init__(self):
        self.errors          : list[str]         = []
        self.symtab          : Optional[Symtab]  = None
        self.current_function: Optional[FuncDecl] = None

    # ------------------------------------------------------------------
    # Punto de entrada
    # ------------------------------------------------------------------
    @classmethod
    def check(cls, node: Node) -> 'Checker':
        checker = cls()
        checker._open_scope("global")
        checker.visit(node)
        return checker

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    def _error(self, node: Node, message: str):
        lineno = getattr(node, 'lineno', '?')
        self.errors.append(f"Error Semántico (línea {lineno}): {message}")

    def _open_scope(self, name: str):
        if self.symtab is None:
            self.symtab = Symtab(name)
        else:
            self.symtab = Symtab(name, parent=self.symtab)

    def _close_scope(self):
        if self.symtab is not None:
            self.symtab = self.symtab.parent

    def _define(self, node: Node, name: str, sym: Symbol):
        try:
            self.symtab.add(name, sym)
        except Symtab.SymbolDefinedError:
            self._error(node, f"redeclaración de '{name}' en el mismo alcance")
        except Symtab.SymbolConflictError:
            self._error(node, f"conflicto de símbolo '{name}' (tipo distinto al previo)")

    def _lookup(self, node: Node, name: str) -> Optional[Symbol]:
        sym = self.symtab.get(name) if self.symtab else None
        if sym is None:
            self._error(node, f"símbolo '{name}' no definido")
        return sym

    def ok(self) -> bool:
        return len(self.errors) == 0

    # ==================================================================
    # VISITORS — Programa
    # ==================================================================

    def visit(self, n: Program):
        for decl in n.decls:
            self.visit(decl)

    # ==================================================================
    # VISITORS — Declaraciones
    # ==================================================================

    def visit(self, n: VarDecl):
        dtype = resolve_type(n.datatype)

        # Si hay inicializador, analizarlo primero para obtener su tipo
        if n.value is not None:
            self.visit(n.value)
            val_type = getattr(n.value, 'type', None)

            # 'constant': inferir tipo desde el valor
            if dtype == 'constant' and val_type is not None:
                dtype = val_type
            elif dtype is not None and val_type is not None:
                if not types_compatible(dtype, val_type):
                    self._error(
                        n,
                        f"no se puede inicializar '{n.name}' "
                        f"(tipo {type_label(dtype)}) con valor de tipo "
                        f"{type_label(val_type)}"
                    )

        sym = Symbol(name=n.name, kind='var', type=dtype, node=n)
        self._define(n, n.name, sym)
        n.type = dtype

    def visit(self, n: FuncDecl):
        dtype = resolve_type(n.datatype)   # ('func', ret_type)
        sym = Symbol(name=n.name, kind='func', type=dtype, node=n, mutable=False)
        self._define(n, n.name, sym)
        n.type = dtype

        # Prototipos (sin cuerpo) solo registran el símbolo
        if n.body is None:
            return

        old_func          = self.current_function
        self.current_function = n

        self._open_scope(f"function {n.name}")
        for param in n.params:
            self.visit(param)
        self.visit(n.body)
        self._close_scope()

        self.current_function = old_func

    def visit(self, n: Parameter):
        dtype = resolve_type(n.datatype)
        sym = Symbol(name=n.name, kind='param', type=dtype, node=n)
        self._define(n, n.name, sym)
        n.type = dtype

    # ==================================================================
    # VISITORS — Sentencias
    # ==================================================================

    def visit(self, n: Block):
        self._open_scope("block")
        for stmt in n.stmts:
            self.visit(stmt)
        self._close_scope()

    def visit(self, n: ExprStmt):
        self.visit(n.expr)

    def visit(self, n: IfStmt):
        if n.cond is not None:
            self.visit(n.cond)
            cond_type = getattr(n.cond, 'type', None)
            if cond_type is not None and cond_type != 'boolean':
                self._error(
                    n,
                    f"la condición del if debe ser boolean, "
                    f"se recibió {type_label(cond_type)}"
                )
        self.visit(n.then_b)
        if n.else_b is not None:
            self.visit(n.else_b)

    def visit(self, n: WhileStmt):
        if n.cond is not None:
            self.visit(n.cond)
            cond_type = getattr(n.cond, 'type', None)
            if cond_type is not None and cond_type != 'boolean':
                self._error(
                    n,
                    f"la condición del while debe ser boolean, "
                    f"se recibió {type_label(cond_type)}"
                )
        self.visit(n.body)

    def visit(self, n: ForStmt):
        # El for abre su propio alcance para variables de control
        self._open_scope("for")
        if n.init is not None:
            self.visit(n.init)
        if n.cond is not None:
            self.visit(n.cond)
            cond_type = getattr(n.cond, 'type', None)
            if cond_type is not None and cond_type != 'boolean':
                self._error(
                    n,
                    f"la condición del for debe ser boolean, "
                    f"se recibió {type_label(cond_type)}"
                )
        if n.update is not None:
            self.visit(n.update)
        self.visit(n.body)
        self._close_scope()

    def visit(self, n: PrintStmt):
        for expr in n.exprs:
            self.visit(expr)

    def visit(self, n: ReturnStmt):
        if n.expr is not None:
            self.visit(n.expr)

        if self.current_function is None:
            return

        # Tipo de retorno esperado desde ('func', ret_type)
        func_type = resolve_type(self.current_function.datatype)
        expected_ret = func_type[1] if (isinstance(func_type, tuple) and func_type[0] == 'func') else None

        if n.expr is None:
            if expected_ret is not None and expected_ret != 'void':
                self._error(
                    n,
                    f"la función '{self.current_function.name}' debe retornar "
                    f"{type_label(expected_ret)} pero no retorna nada"
                )
        else:
            actual_ret = getattr(n.expr, 'type', None)
            if expected_ret is not None and actual_ret is not None:
                if not types_compatible(expected_ret, actual_ret):
                    self._error(
                        n,
                        f"tipo de retorno incorrecto en '{self.current_function.name}': "
                        f"se esperaba {type_label(expected_ret)}, "
                        f"se recibió {type_label(actual_ret)}"
                    )

    def visit(self, n: BreakStmt):
        pass   # validación de contexto (dentro de loop) es opcional

    def visit(self, n: ContinueStmt):
        pass

    # ==================================================================
    # VISITORS — Expresiones
    # ==================================================================

    def visit(self, n: Literal):
        n.type = n.type_name

    def visit(self, n: Location):
        sym = self._lookup(n, n.name)
        n.sym  = sym
        n.type = sym.type if sym else None

    def visit(self, n: ArrayAccess):
        sym = self._lookup(n, n.name)
        n.sym = sym

        if sym is not None:
            arr_type = sym.type
            if isinstance(arr_type, tuple) and arr_type[0] == 'array':
                n.type = arr_type[1]   # tipo base del arreglo
            else:
                self._error(n, f"'{n.name}' no es un arreglo")
                n.type = None
        else:
            n.type = None

        # El índice debe ser integer
        self.visit(n.index)
        idx_type = getattr(n.index, 'type', None)
        if idx_type is not None and idx_type != 'integer':
            self._error(
                n,
                f"el índice del arreglo debe ser integer, "
                f"se recibió {type_label(idx_type)}"
            )

    def visit(self, n: FuncCall):
        sym = self._lookup(n, n.name)

        if sym is not None and sym.kind != 'func':
            self._error(n, f"'{n.name}' no es una función")
            sym = None

        # Analizar argumentos primero
        for arg in n.args:
            self.visit(arg)

        if sym is not None:
            func_node = sym.node  # FuncDecl original
            if func_node is not None and hasattr(func_node, 'params'):
                expected = len(func_node.params)
                actual   = len(n.args)
                if expected != actual:
                    self._error(
                        n,
                        f"la función '{n.name}' espera {expected} "
                        f"argumento{'s' if expected != 1 else ''} "
                        f"pero recibió {actual}"
                    )
                else:
                    for i, (arg, param) in enumerate(zip(n.args, func_node.params)):
                        arg_type   = getattr(arg, 'type', None)
                        param_type = resolve_type(param.datatype)
                        if arg_type is not None and param_type is not None:
                            if not types_compatible(arg_type, param_type):
                                self._error(
                                    n,
                                    f"argumento {i+1} de '{n.name}': "
                                    f"se esperaba {type_label(param_type)}, "
                                    f"se recibió {type_label(arg_type)}"
                                )

            # Tipo del resultado de la llamada = tipo de retorno
            func_type = sym.type
            n.type = func_type[1] if (isinstance(func_type, tuple) and func_type[0] == 'func') else None
        else:
            n.type = None

        n.sym = sym

    def visit(self, n: BinaryOp):
        self.visit(n.left)
        self.visit(n.right)
        left_type  = getattr(n.left,  'type', None)
        right_type = getattr(n.right, 'type', None)

        if left_type is not None and right_type is not None:
            result = check_binop(n.op, left_type, right_type)
            if result is None:
                self._error(
                    n,
                    f"operador '{n.op}' no soportado entre "
                    f"{type_label(left_type)} y {type_label(right_type)}"
                )
            n.type = result
        else:
            n.type = None

    def visit(self, n: UnaryOp):
        self.visit(n.expr)
        operand_type = getattr(n.expr, 'type', None)

        if operand_type is not None:
            result = check_unaryop(n.op, operand_type)
            if result is None:
                self._error(
                    n,
                    f"operador unario '{n.op}' no soportado "
                    f"para tipo {type_label(operand_type)}"
                )
            n.type = result
        else:
            n.type = None

    def visit(self, n: PostfixOp):
        self.visit(n.expr)
        operand_type = getattr(n.expr, 'type', None)

        if operand_type is not None:
            if operand_type != 'integer':
                self._error(
                    n,
                    f"'{n.op}' solo aplica a integer, "
                    f"se recibió {type_label(operand_type)}"
                )
            n.type = 'integer'
        else:
            n.type = None

    def visit(self, n: AssignOp):
        self.visit(n.lval)
        self.visit(n.expr)
        lval_type = getattr(n.lval, 'type', None)
        expr_type = getattr(n.expr, 'type', None)

        if n.op == '=':
            if lval_type is not None and expr_type is not None:
                if not types_compatible(lval_type, expr_type):
                    self._error(
                        n,
                        f"no se puede asignar {type_label(expr_type)} "
                        f"a {type_label(lval_type)}"
                    )
            n.type = lval_type
        else:
            # Asignación compuesta: +=, -=, *=, /=, %=
            base_op = n.op[0]   # '+', '-', '*', '/', '%'
            if lval_type is not None and expr_type is not None:
                result = check_binop(base_op, lval_type, expr_type)
                if result is None:
                    self._error(
                        n,
                        f"operador '{n.op}' no soportado entre "
                        f"{type_label(lval_type)} y {type_label(expr_type)}"
                    )
                elif not types_compatible(lval_type, result):
                    self._error(
                        n,
                        f"resultado de '{n.op}' ({type_label(result)}) "
                        f"no es compatible con {type_label(lval_type)}"
                    )
            n.type = lval_type

    def visit(self, n: ArrayLiteral):
        for expr in n.exprs:
            self.visit(expr)

        types = [getattr(e, 'type', None) for e in n.exprs]
        types = [t for t in types if t is not None]

        if types:
            unique = list(dict.fromkeys(str(t) for t in types))
            if len(unique) > 1:
                self._error(
                    n,
                    f"los elementos del arreglo literal tienen tipos "
                    f"inconsistentes: {', '.join(unique)}"
                )
            n.type = ('array', types[0])
        else:
            n.type = None

    # Nodos de tipo: no producen errores semánticos por sí solos
    def visit(self, n: SimpleType):
        pass

    def visit(self, n: ArrayType):
        pass

    def visit(self, n: FuncType):
        pass


# =============================================================================
# Punto de entrada de línea de comandos
# =============================================================================

def _print_results(checker: Checker, filename: str):
    from rich.console import Console
    from errors       import errors_detected

    console = Console(force_terminal=True, highlight=False)

    if checker.ok():
        console.print(f"\n[bold green]semantic check: success[/bold green]  ({filename})\n")
    else:
        for msg in checker.errors:
            console.print(f"[bold red]{msg}[/bold red]")
        n = len(checker.errors)
        console.print(
            f"\n[bold red]semantic check: failed[/bold red] "
            f"— {n} error{'es' if n != 1 else ''} semántico{'s' if n != 1 else ''}\n"
        )


if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    from parser import parse
    from errors import errors_detected, clear_errors

    if len(sys.argv) != 2:
        raise SystemExit("Uso: python checker.py <archivo.bminor>")

    filename = sys.argv[1]
    try:
        source = open(filename, encoding='utf-8').read()
    except FileNotFoundError:
        raise SystemExit(f"Archivo no encontrado: {filename}")

    clear_errors()
    ast = parse(source)

    if errors_detected() or ast is None:
        raise SystemExit("El archivo tiene errores léxicos/sintácticos. Corríjalos antes del análisis semántico.")

    checker = Checker.check(ast)
    _print_results(checker, filename)
    sys.exit(0 if checker.ok() else 1)
