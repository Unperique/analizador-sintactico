# Analizador Léxico, Sintáctico y Semántico – B-Minor

Implementación de un compilador frontend para el lenguaje **B-Minor**, desarrollado en Python. Incluye análisis léxico, sintáctico, construcción del AST, visualización y análisis semántico con chequeo de tipos.

**Autor:** Andrés Morales

---

## Descripción

El proyecto toma un archivo fuente `.bminor`, lo tokeniza, lo parsea, construye un AST y lo analiza semánticamente. Si el código es válido, muestra el árbol en consola y genera una imagen PNG del grafo. Los errores (léxicos, sintácticos o semánticos) se reportan con tipo, número y línea.

---

## Estructura del proyecto

```
analizador-sintactico/
│
├── lexer.py        # Analizador léxico (tokenizador)
├── parser.py       # Analizador sintáctico + construcción del AST
├── model.py        # Nodos del AST (clases de datos)
├── errors.py       # Reporte de errores léxicos/sintácticos
├── visualizer.py   # Visualización: Rich Tree + Graphviz
├── symtab.py       # Tabla de símbolos con alcance léxico (ChainMap)
├── typesys.py      # Sistema de tipos y tablas de compatibilidad
└── checker.py      # Analizador semántico (patrón Visitor + multimethod)
```

---

## Módulos

### `lexer.py` — Analizador Léxico
Convierte el código fuente en una secuencia de tokens usando `sly.Lexer`.

**Tokens reconocidos:**
- **Palabras clave:** `integer`, `float`, `boolean`, `char`, `string`, `void`, `array`, `function`, `if`, `else`, `for`, `while`, `return`, `print`, `break`, `continue`, `true`, `false`, `constant`, `auto`
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
Construye el AST a partir de los tokens usando `sly.Parser`.

**Construcciones del lenguaje soportadas:**

| Construcción | Ejemplo |
|---|---|
| Declaración de variable | `x : integer;` |
| Declaración con inicialización | `y : integer = 10;` |
| Declaración de arreglo | `a : array [5] integer;` |
| Declaración de función | `f : function integer (n : integer) = { ... }` |
| `if / else` | `if (cond) stmt else stmt` |
| `for` | `for (init; cond; update) stmt` |
| `while` | `while (cond) stmt` |
| `print` | `print expr1, expr2;` |
| `return` | `return expr;` |
| `break / continue` | `break;` |
| Expresiones | Binarias, unarias, postfijas, llamadas, acceso a arreglo |

---

### `model.py` — Nodos del AST
Define las clases que representan cada nodo del árbol. Todos heredan de `Node`, que guarda el número de línea y expone el método `accept(v)` para el patrón Visitor.

**Nodos disponibles:**

| Categoría | Clases |
|---|---|
| Programa | `Program` |
| Declaraciones | `VarDecl`, `FuncDecl`, `Parameter` |
| Tipos | `SimpleType`, `ArrayType`, `FuncType` |
| Sentencias | `Block`, `IfStmt`, `ForStmt`, `WhileStmt`, `PrintStmt`, `ReturnStmt`, `BreakStmt`, `ContinueStmt`, `ExprStmt` |
| Expresiones | `BinaryOp`, `UnaryOp`, `PostfixOp`, `AssignOp`, `Location`, `ArrayAccess`, `FuncCall`, `ArrayLiteral`, `Literal` |

---

### `errors.py` — Sistema de Errores Léxicos/Sintácticos
Centraliza el reporte de errores con formato enriquecido usando `rich`.

**Formato de salida:**
```
Error Léxico #1 (línea 5) Carácter ilegal '@'
Error Sintáctico #2 (línea 12) Token inesperado: ';' (tipo: SEMI)
```

**API:**
```python
error(message, lineno=None, error_type="Error")  # reporta un error
errors_detected()                                 # retorna cantidad de errores
clear_errors()                                    # reinicia el contador
```

---

### `symtab.py` — Tabla de Símbolos
Implementa la tabla de símbolos con alcance léxico usando `ChainMap`.

**Características:**
- Cada `Symtab` representa un scope (global, función, bloque)
- `add(name, value)` define un símbolo en el scope actual; lanza `SymbolDefinedError` o `SymbolConflictError` si ya existe
- `get(name)` busca respetando el alcance léxico (del scope actual hacia los padres)
- `print()` imprime el árbol de scopes completo con `rich`

---

### `typesys.py` — Sistema de Tipos
Define las tablas de compatibilidad de operadores.

**Operadores binarios soportados:**

| Operador | Tipos permitidos | Tipo resultado |
|---|---|---|
| `+  -  *  /  %` | `integer, integer` | `integer` |
| `+  -  *  /  %` | `float, float` | `float` |
| `^` | `integer, integer` | `integer` |
| `<  <=  >  >=  ==  !=` | `integer, integer` | `boolean` |
| `<  <=  >  >=  ==  !=` | `float, float` | `boolean` |
| `<  <=  >  >=  ==  !=` | `char, char` | `boolean` |
| `==  !=` | `boolean, boolean` | `boolean` |
| `&&  \|\|` | `boolean, boolean` | `boolean` |
| `+  ==  !=` | `string, string` | `string / boolean` |

**Operadores unarios:**

| Operador | Tipo permitido | Tipo resultado |
|---|---|---|
| `+  -  ++  --` | `integer` | `integer` |
| `+  -` | `float` | `float` |
| `!` | `boolean` | `boolean` |

**API:**
```python
lookup_type(name)                    # valida si el nombre es un tipo primitivo
check_binop(op, left_type, right_type)  # retorna tipo resultado o None
check_unaryop(op, operand_type)         # retorna tipo resultado o None
```

---

### `checker.py` — Analizador Semántico
Punto de entrada del análisis semántico. Recorre el AST mediante el **patrón Visitor** implementado con la librería `multimethod` (`multimeta`).

**Implementación del Visitor:**
```python
from multimethod import multimeta

class Visitor(metaclass=multimeta):
    pass

class Checker(Visitor):
    def visit(self, n: Program):   ...
    def visit(self, n: VarDecl):   ...
    def visit(self, n: BinaryOp):  ...
    # un método visit por cada nodo del AST
```

**Tabla de símbolos:**  
Cada `Symbol` almacena: `name`, `kind` (`var`/`param`/`func`), `type`, `node`, `mutable`.

**Chequeos semánticos implementados:**

| Categoría | Regla |
|---|---|
| Declaraciones | Redeclaración en el mismo alcance |
| Uso de variables | Símbolo no definido antes de usarse |
| Tipos en inicialización | El tipo del valor debe coincidir con el declarado |
| Asignación (`=`) | Tipos compatibles en ambos lados |
| Asignación compuesta (`+=`, etc.) | Operación y resultado compatibles con el tipo destino |
| Operadores binarios | Tipos válidos según tabla de `typesys` |
| Operadores unarios | Tipo válido según tabla de `typesys` |
| Incremento/decremento (`++`/`--`) | Solo sobre `integer` |
| Condición `if / while / for` | Debe ser `boolean` |
| Llamada a función | Cantidad y tipos de argumentos correctos |
| Retorno | Tipo retornado coincide con el declarado en la función |
| Acceso a arreglo | Variable debe ser de tipo arreglo, índice debe ser `integer` |
| Alcances léxicos | Nuevo scope en bloques `{}`, funciones y `for` |

**Formato de errores:**
```
Error Semántico (línea 11): operador '+' no soportado entre integer y float
Error Semántico (línea 15): no se puede asignar integer a boolean
Error Semántico (línea 19): la función 'func' espera 1 argumento pero recibió 0
```

---

### `visualizer.py` — Visualizador del AST
Punto de entrada para visualizar el AST de un programa válido.

**Salida en consola (Rich Tree):**
```
Program (línea 1)
└── decls
    ├── VarDecl (línea 2)
    │   ├── name: 'x'
    │   └── datatype
    │       └── SimpleType
    │           └── name: 'integer'
    ...
```

**Salida en archivo:**
- `dot_bminor/<nombre>_ast.dot` — archivo DOT del grafo
- `imagenes_bminor/<nombre>_ast.png` — imagen PNG (requiere Graphviz instalado)

---

## Instalación

```bash
pip install sly rich graphviz multimethod
```

Para generar imágenes PNG, también se necesita el ejecutable `dot` de [Graphviz](https://graphviz.org/download/).

---

## Uso

```bash
# Análisis semántico completo
python checker.py bminor/archivo.bminor

# Visualizar AST (Rich Tree + PNG)
python visualizer.py bminor/archivo.bminor

# Solo análisis léxico (tabla de tokens)
python lexer.py bminor/archivo.bminor

# Solo análisis sintáctico (AST como dict)
python parser.py bminor/archivo.bminor
```

---

## Ejemplos

### Código válido (`good3.bminor`)
```bminor
main : function integer (args : string) = {
    result : integer = usage();
    return 0;
}

usage : function void () = {
    print "Usage", 10;
    return;
}
```
Salida:
```
semantic check: success  (bminor/good3.bminor)
```

### Código con errores semánticos (`bad3.bminor`)
```
Error Semántico (línea 11): operador '+' no soportado entre integer y float
Error Semántico (línea 12): operador '+' no soportado entre float y string
...
semantic check: failed — 12 errores semánticos
```

### Código con error sintáctico (`bad0.bminor`)
```bminor
/* Missing type in declaration */
a : 10;
```
Salida:
```
Error Sintáctico #1 (línea 2) Token inesperado: 10 (tipo: INTEGER_LITERAL)
El archivo tiene errores léxicos/sintácticos.
```

---

## Archivos generados (ignorados por git)

| Directorio | Contenido |
|---|---|
| `imagenes_bminor/` | Imágenes PNG del AST |
| `dot_bminor/` | Archivos `.dot` del grafo |
| `__pycache__/` | Caché de Python |
