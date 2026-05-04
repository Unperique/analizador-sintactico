# Compilador B-Minor en Python

Implementación de un compilador completo para el lenguaje **B-Minor**, desarrollado en Python. Cubre todas las fases del frontend: análisis léxico, sintáctico, semántico y generación de código intermedio (IR).

**Autor:** Andrés Morales

---

## Descripción

El proyecto toma un archivo fuente `.bminor` y lo procesa a través de cuatro fases:

```
Código fuente (.bminor)
        │
        ▼
  Análisis léxico          →  tokens
        │
        ▼
  Análisis sintáctico      →  AST
        │
        ▼
  Análisis semántico       →  AST anotado + tabla de símbolos
        │
        ▼
  Generación de IR         →  instrucciones SSA
```

Los errores (léxicos, sintácticos o semánticos) se reportan con tipo, número y línea sin abortar en el primer error.

---

## Estructura del proyecto

```
analizador-sintactico/
│
├── lexer.py            # Analizador léxico (tokenizador)
├── parser.py           # Analizador sintáctico + construcción del AST
├── model.py            # Nodos del AST y tipos del lenguaje
├── errors.py           # Reporte de errores léxicos/sintácticos
├── visualizer.py       # Visualización del AST: Rich Tree + Graphviz
├── symtab.py           # Tabla de símbolos con alcance léxico (ChainMap)
├── typesys.py          # Tablas de compatibilidad de operadores
├── checker.py          # Analizador semántico (Visitor + multimethod)
└── ircode_starter.py   # Generador de código intermedio SSA
```

---

## Módulos

### `lexer.py` — Analizador Léxico
Convierte el código fuente en tokens usando `sly.Lexer`.

**Tokens reconocidos:**
- **Palabras clave:** `integer`, `float`, `boolean`, `char`, `string`, `void`, `array`, `function`, `if`, `else`, `for`, `while`, `return`, `print`, `break`, `continue`, `true`, `false`, `constant`
- **Literales:** enteros, flotantes, caracteres (`'a'`), cadenas (`"texto"`)
- **Operadores:** aritméticos (`+ - * / % ^`), relacionales (`< <= > >= == !=`), lógicos (`&& ||`), asignación compuesta (`+= -= *= /= %=`), incremento/decremento (`++ --`)
- **Comentarios:** `// línea` y `/* bloque */`

**Errores léxicos detectados:**
- Carácter ilegal
- Literal de carácter mal formado
- Literal entera u flotante con ceros a la izquierda (`07`, `0123.4`)
- Comentario de bloque sin cerrar

---

### `parser.py` — Analizador Sintáctico
Construye el AST usando `sly.Parser`.

**Construcciones soportadas:**

| Construcción | Ejemplo |
|---|---|
| Declaración de variable | `x : integer;` |
| Declaración con inicialización | `y : integer = 10;` |
| Constante | `MAX : constant = 100;` |
| Declaración de arreglo | `a : array [5] integer;` |
| Declaración de función | `f : function integer (n : integer) = { ... }` |
| `if / else` | `if (cond) stmt else stmt` |
| `for` | `for (init; cond; step) stmt` |
| `while` | `while (cond) stmt` |
| `print` | `print expr1, expr2;` |
| `return` | `return expr;` |
| `break / continue` | `break;` / `continue;` |
| Expresiones | Binarias, unarias, postfijas, llamadas, acceso a arreglo |

---

### `model.py` — Nodos del AST y Sistema de Tipos
Define la jerarquía de nodos del AST y los tipos del lenguaje. Todos los nodos heredan de `Node` y exponen `accept(v)` para el patrón Visitor.

**Tipos del lenguaje:**

| Clase | Constante | Descripción |
|---|---|---|
| `IntegerType` | `INT` | Entero |
| `FloatType` | `FLOAT` | Flotante |
| `BooleanType` | `BOOL` | Booleano |
| `CharType` | `CHAR` | Carácter |
| `StringType` | `STRING` | Cadena |
| `VoidType` | `VOID` | Sin valor |
| `ArrayType(base, size)` | — | Arreglo de tipo base |

**Nodos del AST:**

| Categoría | Clases |
|---|---|
| Programa | `Program` |
| Declaraciones | `VarDecl`, `ConstDecl`, `FuncDecl`, `Param`, `ParamList` |
| Sentencias | `Block`, `IfStmt`, `ForStmt`, `WhileStmt`, `PrintStmt`, `ReturnStmt`, `BreakStmt`, `ContinueStmt`, `Assignment` |
| Expresiones | `BinOp`, `UnaryOp`, `VarLoc`, `ArrayLoc`, `FuncCall`, `ExprList`, `ArrayLiteral` |
| Literales | `IntegerLiteral`, `FloatLiteral`, `BooleanLiteral`, `CharLiteral`, `StringLiteral` |

---

### `errors.py` — Sistema de Errores
Reporta errores léxicos y sintácticos con `rich`.

```
Error Léxico #1 (línea 5) Carácter ilegal '@'
Error Sintáctico #2 (línea 12) Token inesperado: ';' (tipo: SEMI)
```

---

### `symtab.py` — Tabla de Símbolos
Tabla de símbolos con alcance léxico implementada con `ChainMap`.

- `add(name, value)` — define un símbolo en el scope actual
- `get(name)` — busca respetando el alcance léxico (del scope actual hacia los padres)
- Lanza `SymbolDefinedError` en redeclaración, `SymbolConflictError` en conflicto de tipo

---

### `checker.py` — Analizador Semántico
Recorre el AST con el patrón **Visitor** (`multimethod`/`multimeta`) y verifica reglas semánticas.

**Implementación del Visitor:**
```python
from multimethod import multimeta

class Visitor(metaclass=multimeta):
    pass

class Checker(Visitor):
    def visit(self, n: Program):  ...
    def visit(self, n: VarDecl):  ...
    def visit(self, n: BinOp):    ...
    # un método visit por cada nodo del AST
```

**Tabla de símbolos:**
Cada `Symbol` almacena: `name`, `kind` (`var`/`const`/`param`/`func`), `type`, `node`, `mutable`.

**Chequeos implementados:**

| Categoría | Regla |
|---|---|
| Declaraciones | Redeclaración en el mismo alcance |
| Uso de variables | Símbolo no definido antes de usarse |
| Inicialización | Tipo del valor debe coincidir con el declarado |
| Asignación (`=`) | Tipos compatibles en ambos lados |
| Asignación compuesta (`+=`, etc.) | Operación y resultado compatibles |
| Operadores binarios | Tipos válidos por tabla de operadores |
| Operadores unarios y postfijos | Tipo válido por tabla de operadores |
| Condición `if / while / for` | Debe ser `boolean` |
| Llamada a función | Cantidad y tipos de argumentos correctos |
| Retorno | Tipo coincide con el declarado en la función |
| Acceso a arreglo | Variable debe ser arreglo, índice debe ser `integer` |
| Alcances léxicos | Nuevo scope en bloques `{}`, funciones y `for` |

**Formato de salida:**
```
Error Semántico (línea 11): operador '+' no soportado entre integer y float
Error Semántico (línea 19): función 'f' espera 2 argumentos pero recibió 1
semantic check: failed — 2 errores semánticos
```

---

### `ircode_starter.py` — Generador de Código Intermedio (IR)
Genera código intermedio SSA (Static Single Assignment) a partir del AST. Extiende el patrón Visitor y produce instrucciones como tuplas `(opcode, operando..., destino)`.

**Instrucciones generadas:**

| Categoría | Instrucciones |
|---|---|
| Literales | `MOVI`, `MOVF`, `MOVB`, `MOVS` |
| Variables globales | `VARI`, `VARF`, `VARB`, `VARS` |
| Variables locales | `ALLOCI`, `ALLOCF`, `ALLOCB`, `ALLOCS` |
| Carga/almacenamiento | `LOADI/F/B/S`, `STOREI/F/B/S` |
| Aritmética | `ADDI/F`, `SUBI/F`, `MULI/F`, `DIVI/F`, `MODI` |
| Comparación | `CMPI/F/B op, r1, r2, dest` |
| Lógica | `AND`, `OR`, `XOR` |
| Impresión | `PRINTI`, `PRINTF`, `PRINTB`, `PRINTS` |
| Control de flujo | `LABEL`, `BRANCH`, `CBRANCH test, label_true, label_false` |
| Funciones | `CALL nombre, arg1..., dest` / `RET` / `RET Rx` |
| Arreglos | `LOADA addr, dest` / `STOREA src, addr` |

**Ejemplo de IR generado** para un factorial recursivo:
```
function factorial(n:integer) -> integer
  ALLOCI n
  LOADI n, R1
  MOVI 1, R2
  CMPI <=, R1, R2, R3
  CBRANCH R3, then1, else2
  LABEL then1
    MOVI 1, R4
    RET R4
  LABEL else2
    LOADI n, R5
    LOADI n, R6
    MOVI 1, R7
    SUBI R6, R7, R8
    CALL factorial, R8, R9
    MULI R5, R9, R10
    RET R10
  LABEL endif3
```

**Acceso a arreglos con aritmética de índice:**
```
# arr[i]  →  base + i * 8
LOADI arr, R1       ; dirección base
LOADI i,   R2       ; índice
MOVI  8,   R3       ; tamaño de elemento (8 bytes)
MULI  R2, R3, R4    ; offset = i * 8
ADDI  R1, R4, R5    ; addr   = base + offset
LOADA R5,  R6       ; cargar elemento
```

**`break` y `continue` con pila de labels:**
- `break` → `BRANCH endwhile/endfor` (label del loop más cercano)
- `continue` en `while` → `BRANCH while_test`
- `continue` en `for` → `BRANCH forstep` (ejecuta el step antes de re-evaluar)

---

## Instalación

```bash
pip install sly rich graphviz multimethod
```

Para generar imágenes PNG del AST se necesita el ejecutable `dot` de [Graphviz](https://graphviz.org/download/).

---

## Uso

```bash
# Generar código IR
python ircode_starter.py archivo.bminor

# Análisis semántico
python checker.py archivo.bminor

# Visualizar AST (Rich Tree + PNG)
python visualizer.py archivo.bminor

# Solo análisis léxico
python lexer.py archivo.bminor

# Solo análisis sintáctico
python parser.py archivo.bminor
```

---

## Ejemplos

### Código válido — salida del generador IR (`good9.bminor`)

```bminor
factorial: function integer (n: integer) = {
    if (n <= 1) { return 1; }
    else        { return n * factorial(n - 1); }
}
```

```bash
python ircode_starter.py typechecker/good9.bminor
```

### Análisis semántico exitoso

```bash
python checker.py typechecker/good3.bminor
# semantic check: success
```

### Análisis semántico con errores

```bash
python checker.py typechecker/bad3.bminor
# Error Semántico (línea 11): operador '+' no soportado entre integer y float
# ...
# semantic check: failed — 12 errores semánticos
```

---

## Archivos de prueba

Los archivos de prueba están en `typechecker/`:

| Archivos | Descripción |
|---|---|
| `good0`–`good9` | Programas semánticamente correctos |
| `bad0`–`bad9` | Programas con errores semánticos detectables |

---

## Archivos generados (ignorados por git)

| Directorio | Contenido |
|---|---|
| `imagenes_bminor/` | Imágenes PNG del AST |
| `dot_bminor/` | Archivos `.dot` del grafo |
| `__pycache__/` | Caché de Python |
