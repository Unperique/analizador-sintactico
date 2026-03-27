# Analizador Sintáctico – B-Minor

Implementación de un analizador léxico y sintáctico para el lenguaje **B-Minor**, desarrollado en Python con la biblioteca `sly`. Genera un Árbol de Sintaxis Abstracta (AST) y lo visualiza tanto en consola (Rich Tree) como en imagen (Graphviz).

**Autor:** Andrés Morales

---

## Descripción

El proyecto toma un archivo fuente `.bminor`, lo tokeniza, lo parsea y construye un AST. Si el código es válido, muestra el árbol en consola y genera una imagen PNG del grafo. Si hay errores, los reporta con tipo, número y línea.

---

## Estructura del proyecto

```
analizador-sintactico/
│
├── lexer.py          # Analizador léxico (tokenizador)
├── parser.py         # Analizador sintáctico + construcción del AST
├── model.py          # Nodos del AST (clases de datos)
├── errors.py         # Sistema de reporte de errores
├── visualizer.py     # Visualización: Rich Tree + Graphviz
│
└── AnalizadorSintactico_AndresMorales_1004754257/
    ├── lexer.py
    ├── parser.py
    ├── model.py
    ├── errors.py
    ├── visualizer.py
    ├── grammar.txt       # Gramática generada por sly (debug)
    └── bminor/
        ├── good0.bminor  # Casos válidos (good0 – good9)
        └── bad0.bminor   # Casos con errores (bad0 – bad5)
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
Define las clases que representan cada nodo del árbol. Todos heredan de `Node`, que guarda el número de línea.

**Nodos disponibles:**

| Categoría | Clases |
|---|---|
| Programa | `Program` |
| Declaraciones | `VarDecl`, `FuncDecl`, `Parameter` |
| Tipos | `SimpleType`, `ArrayType`, `FuncType` |
| Sentencias | `Block`, `IfStmt`, `ForStmt`, `WhileStmt`, `PrintStmt`, `ReturnStmt`, `BreakStmt`, `ContinueStmt`, `ExprStmt` |
| Expresiones | `BinaryOp`, `UnaryOp`, `PostfixOp`, `AssignOp`, `Location`, `ArrayAccess`, `FuncCall`, `ArrayLiteral`, `Literal` |

---

### `errors.py` — Sistema de Errores
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

### `visualizer.py` — Visualizador del AST
Punto de entrada principal del proyecto.

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
pip install sly rich graphviz
```

Para generar imágenes PNG, también se necesita el ejecutable `dot` de [Graphviz](https://graphviz.org/download/).

---

## Uso

```bash
# Visualizar AST (Rich Tree + PNG)
python visualizer.py archivo.bminor

# Solo análisis léxico (tabla de tokens)
python lexer.py archivo.bminor

# Solo análisis sintáctico (AST como dict)
python parser.py archivo.bminor
```

---

## Ejemplos

### Código válido (`good0.bminor`)
```bminor
x: integer;
y: integer = 123;
f: float = 45.67;
b: boolean = false;
c: char = 'q';
s: string = "hello bminor\n";
a: array [2] boolean = {true, false};
```

### Código con error (`bad0.bminor`)
```bminor
/* Missing type in declaration */
a : 10;
```
Salida:
```
Error Sintáctico #1 (línea 2) Token inesperado: 10 (tipo: INTEGER_LITERAL)
1 error encontrado. No se puede generar el AST.
```

---

## Archivos generados (ignorados por git)

| Directorio | Contenido |
|---|---|
| `imagenes_bminor/` | Imágenes PNG del AST |
| `dot_bminor/` | Archivos `.dot` del grafo |
| `__pycache__/` | Caché de Python |
