from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from rich import print

from model import *

# ===================================================
# IR model
# ===================================================

Instruction = tuple


@dataclass
class Storage:
    """Dónde vive un símbolo durante la generación de IR."""
    name: str
    ty: Type
    is_global: bool = False
    is_param: bool = False
    is_const: bool = False


@dataclass
class IRFunction:
    name: str
    params: list[tuple[str, Type]]
    return_type: Type
    instructions: list[Instruction] = field(default_factory=list)


@dataclass
class IRProgram:
    globals: list[Instruction] = field(default_factory=list)
    functions: list[IRFunction] = field(default_factory=list)

    def format(self) -> str:
        out: list[str] = []
        if self.globals:
            out.append("# Globals")
            for inst in self.globals:
                out.append(format_instruction(inst))
            out.append("")

        for fn in self.functions:
            params = ", ".join(f"{name}:{ty}" for name, ty in fn.params)
            out.append(f"function {fn.name}({params}) -> {fn.return_type}")
            for inst in fn.instructions:
                out.append(f"  {format_instruction(inst)}")
            out.append("")
        return "\n".join(out).rstrip()


# ===================================================
# Pretty printing
# ===================================================


def format_instruction(inst: Instruction) -> str:
    op = inst[0]
    if len(inst) == 1:
        return op
    args = ", ".join(
        repr(x) if isinstance(x, str) and x.startswith("L") else str(x)
        for x in inst[1:]
    )
    return f"{op} {args}"


# ===================================================
# Generator
# ===================================================


class IRCodeGen(Visitor):
    """
    Generador de código IR para B-Minor.

    Genera instrucciones SSA en forma de tuplas:
        (opcode, operando1, operando2, ..., destino)
    """

    def __init__(self):
        self.program = IRProgram()
        self.current_function: Optional[IRFunction] = None
        self.current_return_type: Type = VOID
        self.temp_count = 0
        self.label_count = 0
        self.scopes: list[dict[str, Storage]] = []
        self.loop_stack: list[tuple[str, str]] = []
        # Pool de strings: [(label, texto)] → se emiten como DATAS al inicio
        self.string_pool: list[tuple[str, str]] = []
        self.str_count = 0

    @classmethod
    def generate(cls, node: Program) -> IRProgram:
        gen = cls()
        gen.visit(node)
        # Anteponer DATAS de strings al bloque global
        if gen.string_pool:
            datas = []
            for label, text in gen.string_pool:
                bytes_list = [ord(c) for c in text] + [0]   # null-terminated
                datas.append(("DATAS", label, *bytes_list))
            gen.program.globals = datas + gen.program.globals
        return gen.program

    # -------------------------------------------------
    # Helpers básicos
    # -------------------------------------------------

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"R{self.temp_count}"

    def new_label(self, prefix: str = "") -> str:
        """Genera labels con prefijo L, igual que el estándar del profe: 'Lthen1', 'Lfor_test10'."""
        self.label_count += 1
        return f"L{prefix}{self.label_count}"

    def emit(self, *inst) -> None:
        inst = tuple(inst)
        if self.current_function is None:
            self.program.globals.append(inst)
        else:
            self.current_function.instructions.append(inst)

    def push_scope(self) -> None:
        self.scopes.append({})

    def pop_scope(self) -> None:
        self.scopes.pop()

    def bind(self, storage: Storage) -> None:
        if not self.scopes:
            self.push_scope()
        self.scopes[-1][storage.name] = storage

    def lookup(self, name: str) -> Storage:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise NameError(f"Nombre no resuelto en IRCodeGen: {name}")

    def infer_type(self, node: Optional[Node]) -> Type:
        if node is None:
            return VOID
        ty = getattr(node, "type", None)
        if isinstance(ty, Type):
            return ty
        if isinstance(node, IntegerLiteral):
            return INT
        if isinstance(node, BooleanLiteral):
            return BOOL
        if isinstance(node, FloatLiteral):
            return FLOAT
        if isinstance(node, CharLiteral):
            return CHAR
        if isinstance(node, StringLiteral):
            return STRING
        if isinstance(node, (VarDecl, ConstDecl, Param)):
            return node.type
        # Para VarLoc, consultar la tabla de scopes
        if isinstance(node, VarLoc):
            try:
                return self.lookup(node.name).ty
            except NameError:
                pass
        return INT

    def type_suffix(self, ty: Type) -> str:
        if isinstance(ty, (IntegerType, BooleanType)):
            return "I"
        if isinstance(ty, FloatType):
            return "F"
        if isinstance(ty, CharType):
            return "B"
        if isinstance(ty, StringType):
            return "S"
        if isinstance(ty, VoidType):
            return "V"
        if isinstance(ty, ArrayType):
            return "I"   # arrays se tratan como puntero entero
        raise NotImplementedError(f"Tipo no soportado: {ty}")

    def move_opcode(self, ty: Type) -> str:
        return f"MOV{self.type_suffix(ty)}"

    def load_opcode(self, ty: Type) -> str:
        return f"LOAD{self.type_suffix(ty)}"

    def store_opcode(self, ty: Type) -> str:
        return f"STORE{self.type_suffix(ty)}"

    def alloc_opcode(self, ty: Type) -> str:
        return f"ALLOC{self.type_suffix(ty)}"

    def var_opcode(self, ty: Type) -> str:
        return f"VAR{self.type_suffix(ty)}"

    def print_opcode(self, ty: Type) -> str:
        return f"PRINT{self.type_suffix(ty)}"

    def cmp_opcode(self, ty: Type) -> str:
        return f"CMP{self.type_suffix(ty)}"

    def binary_arith_opcode(self, oper: str, ty: Type) -> str:
        suffix = self.type_suffix(ty)
        table = {
            "+": f"ADD{suffix}",
            "-": f"SUB{suffix}",
            "*": f"MUL{suffix}",
            "/": f"DIV{suffix}",
            # '%' se expande como a-(a/b)*b — no hay MODI en el spec
        }
        if oper not in table:
            raise NotImplementedError(f"Aritmética no soportada: {oper}")
        return table[oper]

    # -------------------------------------------------
    # Programa y declaraciones
    # -------------------------------------------------

    def visit(self, node: Program):
        self.push_scope()

        # Primera pasada: registrar nombres globales
        for decl in node.decls:
            if isinstance(decl, (VarDecl, ConstDecl)):
                self.bind(Storage(
                    decl.name, decl.type,
                    is_global=True,
                    is_const=isinstance(decl, ConstDecl),
                ))
            elif isinstance(decl, FuncDecl):
                self.bind(Storage(decl.name, decl.type, is_global=True))

        # Segunda pasada: generar IR
        for decl in node.decls:
            self.visit(decl)

        self.pop_scope()
        return self.program

    def visit(self, node: VarDecl):
        if self.current_function is None:
            self.emit(self.var_opcode(node.type), node.name)
            if node.value is not None and not isinstance(node.value, ArrayLiteral):
                src = self.visit(node.value)
                self.emit(self.store_opcode(node.type), src, node.name)
            return

        self.bind(Storage(node.name, node.type, is_const=not node.mutable))
        self.emit(self.alloc_opcode(node.type), node.name)
        if node.value is not None and not isinstance(node.value, ArrayLiteral):
            src = self.visit(node.value)
            self.emit(self.store_opcode(node.type), src, node.name)

    def visit(self, node: ConstDecl):
        if self.current_function is None:
            self.emit(self.var_opcode(node.type), node.name)
            src = self.visit(node.value)
            self.emit(self.store_opcode(node.type), src, node.name)
            return

        self.bind(Storage(node.name, node.type, is_const=True))
        self.emit(self.alloc_opcode(node.type), node.name)
        src = self.visit(node.value)
        self.emit(self.store_opcode(node.type), src, node.name)

    def visit(self, node: FuncDecl):
        prev_fn  = self.current_function
        prev_ret = self.current_return_type

        fn = IRFunction(
            name=node.name,
            params=[(p.name, p.type) for p in node.parms.params],
            return_type=node.type,
        )
        self.program.functions.append(fn)
        self.current_function = fn
        self.current_return_type = node.type

        self.push_scope()
        for p in node.parms.params:
            self.bind(Storage(p.name, p.type, is_param=True))
            self.emit(self.alloc_opcode(p.type), p.name)

        self.visit(node.body)

        # Cierre automático de funciones void sin return explícito
        if isinstance(node.type, VoidType):
            if not fn.instructions or fn.instructions[-1][0] != "RET":
                self.emit("RET")

        self.pop_scope()
        self.current_function = prev_fn
        self.current_return_type = prev_ret

    def visit(self, node: Block):
        self.push_scope()
        for stmt in node.stmts:
            self.visit(stmt)
        self.pop_scope()

    def visit(self, node: ParamList):
        return None

    def visit(self, node: Param):
        return None

    # -------------------------------------------------
    # Sentencias
    # -------------------------------------------------

    def visit(self, node: Assignment):
        """Asignación simple y compuesta a variables y arreglos."""

        # --- Asignación a arreglo: arr[index] = expr ---
        if isinstance(node.loc, ArrayLoc):
            storage   = self.lookup(node.loc.name)
            elem_size = 8

            # Dirección base
            base_reg = self.new_temp()
            self.emit(self.load_opcode(IntegerType()), storage.name, base_reg)

            # Índice
            if isinstance(node.loc.index, int):
                idx_reg = self.new_temp()
                self.emit("MOVI", node.loc.index, idx_reg)
            else:
                idx_reg = self.visit(node.loc.index)

            # offset = index * elem_size
            sz_reg  = self.new_temp()
            off_reg = self.new_temp()
            self.emit("MOVI", elem_size, sz_reg)
            self.emit("MULI", idx_reg, sz_reg, off_reg)

            # addr = base + offset
            addr_reg = self.new_temp()
            self.emit("ADDI", base_reg, off_reg, addr_reg)

            # valor a guardar
            src = self.visit(node.expr)
            self.emit("STOREA", src, addr_reg)
            return src

        # --- Asignación a variable ---
        if not isinstance(node.loc, VarLoc):
            raise NotImplementedError(f"Assignment: loc no soportado: {type(node.loc).__name__}")

        storage = self.lookup(node.loc.name)

        if node.oper == "=":
            src = self.visit(node.expr)
            self.emit(self.store_opcode(storage.ty), src, storage.name)
            return src

        # Asignaciones compuestas: +=, -=, *=, /=, %=
        base_op = node.oper[0]   # '+', '-', '*', '/', '%'
        cur = self.new_temp()
        self.emit(self.load_opcode(storage.ty), storage.name, cur)
        rhs = self.visit(node.expr)
        result = self.new_temp()
        opcode = self.binary_arith_opcode(base_op, storage.ty)
        self.emit(opcode, cur, rhs, result)
        self.emit(self.store_opcode(storage.ty), result, storage.name)
        return result

    def visit(self, node: PrintStmt):
        if isinstance(node.expr, ExprList):
            for e in node.expr.exprs:
                reg = self.visit(e)
                ty  = self.infer_type(e)
                self.emit(self.print_opcode(ty), reg)
        else:
            reg = self.visit(node.expr)
            ty  = self.infer_type(node.expr)
            self.emit(self.print_opcode(ty), reg)

    def visit(self, node: IfStmt):
        test_reg = self.visit(node.test)

        if node.else_block is not None:
            # if/else: then → else → merge
            label_then = self.new_label("then")
            label_else = self.new_label("end")
            label_end  = self.new_label("end")

            self.emit("CBRANCH", test_reg, label_then, label_else)
            self.emit("LABEL",   label_then)
            self.visit(node.then_block)
            self.emit("BRANCH",  label_end)
            self.emit("LABEL",   label_else)
            self.visit(node.else_block)
            self.emit("LABEL",   label_end)
        else:
            # if sin else: siempre 3 labels (then, end_false, merge)
            label_then      = self.new_label("then")
            label_end_false = self.new_label("end")
            label_end       = self.new_label("end")

            self.emit("CBRANCH", test_reg, label_then, label_end_false)
            self.emit("LABEL",   label_then)
            self.visit(node.then_block)
            self.emit("BRANCH",  label_end)
            self.emit("LABEL",   label_end_false)
            self.emit("LABEL",   label_end)

    def visit(self, node: WhileStmt):
        label_test = self.new_label("while_test")
        label_body = self.new_label("while_body")
        label_end  = self.new_label("while_end")

        self.loop_stack.append((label_test, label_end))

        self.emit("LABEL", label_test)
        if node.test is not None:
            test_reg = self.visit(node.test)
            self.emit("CBRANCH", test_reg, label_body, label_end)
        self.emit("LABEL", label_body)
        self.visit(node.body)
        self.emit("BRANCH", label_test)
        self.emit("LABEL", label_end)

        self.loop_stack.pop()

    def visit(self, node: ForStmt):
        if node.init is not None:
            self.visit(node.init)

        label_test = self.new_label("for_test")
        label_body = self.new_label("for_body")
        label_step = self.new_label("for_step")
        label_end  = self.new_label("for_end")

        self.loop_stack.append((label_step, label_end))

        self.emit("LABEL", label_test)
        if node.test is not None:
            test_reg = self.visit(node.test)
            self.emit("CBRANCH", test_reg, label_body, label_end)
        self.emit("LABEL", label_body)
        self.visit(node.body)
        self.emit("BRANCH", label_step)   # salto explícito al step (como el profe)
        self.emit("LABEL", label_step)
        if node.step is not None:
            self.visit(node.step)
        self.emit("BRANCH", label_test)
        self.emit("LABEL", label_end)

        self.loop_stack.pop()

    def visit(self, node: ReturnStmt):
        if node.expr is None:
            self.emit("RET")
            return
        reg = self.visit(node.expr)
        self.emit("RET", reg)

    def visit(self, node: BreakStmt):
        if self.loop_stack:
            _, break_label = self.loop_stack[-1]
            self.emit("BRANCH", break_label)

    def visit(self, node: ContinueStmt):
        if self.loop_stack:
            continue_label, _ = self.loop_stack[-1]
            self.emit("BRANCH", continue_label)

    # -------------------------------------------------
    # Expresiones
    # -------------------------------------------------

    def visit(self, node: VarLoc):
        storage = self.lookup(node.name)
        tmp = self.new_temp()
        self.emit(self.load_opcode(storage.ty), storage.name, tmp)
        return tmp

    def visit(self, node: ArrayLoc):
        """
        Acceso a arreglo: arr[index].

        Genera aritmética de índice explícita:
            LOADI  arr_base, R_base
            <visitar index → R_idx>
            MOVI   elem_size, R_sz
            MULI   R_idx, R_sz, R_off     ; offset = index * elem_size
            ADDI   R_base, R_off, R_addr  ; addr   = base  + offset
            LOADA  R_addr, R_dest         ; carga elemento
        """
        storage = self.lookup(node.name)
        elem_ty  = storage.ty.base if isinstance(storage.ty, ArrayType) else storage.ty
        elem_size = 8   # 8 bytes por elemento (modelo de 64 bits)

        # 1. Cargar dirección base del arreglo
        base_reg = self.new_temp()
        self.emit(self.load_opcode(IntegerType()), storage.name, base_reg)

        # 2. Evaluar índice
        if isinstance(node.index, int):
            idx_reg = self.new_temp()
            self.emit("MOVI", node.index, idx_reg)
        else:
            idx_reg = self.visit(node.index)

        # 3. offset = index * elem_size
        sz_reg  = self.new_temp()
        off_reg = self.new_temp()
        self.emit("MOVI", elem_size, sz_reg)
        self.emit("MULI", idx_reg, sz_reg, off_reg)

        # 4. addr = base + offset
        addr_reg = self.new_temp()
        self.emit("ADDI", base_reg, off_reg, addr_reg)

        # 5. Cargar elemento desde la dirección calculada
        dest = self.new_temp()
        self.emit("LOADA", addr_reg, dest)
        return dest

    def visit(self, node: FuncCall):
        """Llamada a función: evalúa args y emite CALL."""
        arg_regs = [self.visit(arg) for arg in node.args.exprs]
        out = self.new_temp()
        self.emit("CALL", node.name, *arg_regs, out)
        return out

    def visit(self, node: BinOp):
        left_reg  = self.visit(node.left)
        right_reg = self.visit(node.right)
        left_ty   = self.infer_type(node.left)
        out       = self.new_temp()

        # Aritmética básica
        if node.oper in {"+", "-", "*", "/"}:
            opcode = self.binary_arith_opcode(node.oper, left_ty)
            self.emit(opcode, left_reg, right_reg, out)
            return out

        # Módulo: expandido como a - (a/b)*b  (no existe MODI en el spec)
        if node.oper == "%":
            suffix = self.type_suffix(left_ty)
            quot = self.new_temp()
            prod = self.new_temp()
            self.emit(f"DIV{suffix}", left_reg, right_reg, quot)
            self.emit(f"MUL{suffix}", quot,     right_reg, prod)
            self.emit(f"SUB{suffix}", left_reg, prod,      out)
            return out

        # Comparaciones: < <= > >= == !=
        if node.oper in {"<", "<=", ">", ">=", "==", "!="}:
            opcode = self.cmp_opcode(left_ty)
            self.emit(opcode, node.oper, left_reg, right_reg, out)
            return out

        # Operadores lógicos booleanos
        if node.oper == "&&":
            self.emit("AND", left_reg, right_reg, out)
            return out
        if node.oper == "||":
            self.emit("OR", left_reg, right_reg, out)
            return out

        raise NotImplementedError(f"BinOp no soportado: {node.oper!r}")

    def visit(self, node: UnaryOp):
        reg = self.visit(node.expr)
        ty  = self.infer_type(node.expr)
        out = self.new_temp()

        # +x  →  no-op
        if node.oper == "+":
            return reg

        # -x  →  0 - x
        if node.oper == "-":
            zero = self.new_temp()
            self.emit(self.move_opcode(ty), 0, zero)
            self.emit(f"SUB{self.type_suffix(ty)}", zero, reg, out)
            return out

        # !x  →  x XOR 1  (booleano)
        if node.oper == "!":
            one = self.new_temp()
            self.emit("MOVI", 1, one)
            self.emit("XOR", reg, one, out)
            return out

        # ++x / --x  (prefijo y postfijo)
        if node.oper in {"++", "--"}:
            one = self.new_temp()
            self.emit(self.move_opcode(ty), 1, one)
            arith = f"ADD{self.type_suffix(ty)}" if node.oper == "++" else f"SUB{self.type_suffix(ty)}"
            self.emit(arith, reg, one, out)
            # Escribir resultado de vuelta a la variable
            if isinstance(node.expr, VarLoc):
                storage = self.lookup(node.expr.name)
                self.emit(self.store_opcode(storage.ty), out, storage.name)
            return out

        raise NotImplementedError(f"UnaryOp no soportado: {node.oper!r}")

    # -------------------------------------------------
    # Literales
    # -------------------------------------------------

    def visit(self, node: IntegerLiteral):
        tmp = self.new_temp()
        self.emit("MOVI", int(node.value), tmp)
        return tmp

    def visit(self, node: BooleanLiteral):
        tmp = self.new_temp()
        self.emit("MOVI", 1 if node.value else 0, tmp)
        return tmp

    def visit(self, node: FloatLiteral):
        tmp = self.new_temp()
        self.emit("MOVF", float(node.value), tmp)
        return tmp

    def visit(self, node: CharLiteral):
        tmp = self.new_temp()
        value = ord(node.value) if isinstance(node.value, str) else int(node.value)
        self.emit("MOVB", value, tmp)
        return tmp

    def visit(self, node: StringLiteral):
        # Cada ocurrencia crea su propia entrada (igual que el profe)
        label = f".str{self.str_count}"
        self.str_count += 1
        self.string_pool.append((label, node.value))
        tmp = self.new_temp()
        self.emit("ADDR", label, tmp)
        return tmp

    def visit(self, node: ExprList):
        return [self.visit(expr) for expr in node.exprs]

    def visit(self, node: ArrayLiteral):
        return [self.visit(expr) for expr in node.exprs]


# ===================================================
# Punto de entrada CLI
# ===================================================

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) == 2:
        from parser import parse
        from errors import errors_detected, clear_errors

        filename = sys.argv[1]
        source   = open(filename, encoding="utf-8").read()
        clear_errors()
        ast = parse(source)
        if errors_detected():
            raise SystemExit("Errores sintácticos — no se puede generar IR.")
        ir = IRCodeGen.generate(ast)
        print(ir.format())
        sys.exit(0)

    # Demo incorporada
    ast = Program([
        FuncDecl(
            name="main",
            parms=ParamList([]),
            type=VOID,
            body=Block([
                VarDecl(name="x", type=INT,
                        value=BinOp(oper="+",
                                    left=IntegerLiteral(2),
                                    right=BinOp(oper="*",
                                                left=IntegerLiteral(3),
                                                right=IntegerLiteral(4),
                                                type=INT),
                                    type=INT)),
                PrintStmt(expr=VarLoc(name="x", type=INT)),
            ]),
        )
    ])

    ir = IRCodeGen.generate(ast)
    print(ir.format())
