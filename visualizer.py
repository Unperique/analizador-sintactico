# visualizer.py
# -*- coding: utf-8 -*-
#
# Taller: Visualización del AST en B-Minor
# Uso: python visualizer.py <archivo.bminor>

import sys
import uuid

# Forzar UTF-8 en la consola de Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from rich.tree    import Tree
from rich.console import Console
from graphviz     import Digraph

from model  import Node
from parser import parse
from errors import errors_detected, clear_errors

console = Console(force_terminal=True, highlight=False)


# =============================================================================
# PARTE 3 – Rich Tree
# =============================================================================

def build_rich_tree(node):
    """Recorre el AST y construye un Rich Tree para visualización en consola."""

    # Nodo None (campo opcional vacío)
    if node is None:
        return Tree("[dim]∅[/dim]")

    # Nodo AST (subclase de Node)
    if isinstance(node, Node):
        name  = type(node).__name__
        lineno_str = f" [dim](línea {node.lineno})[/dim]" if getattr(node, 'lineno', None) else ""
        tree  = Tree(f"[bold cyan]{name}[/bold cyan]{lineno_str}")

        for field, value in vars(node).items():
            if field == 'lineno':
                continue

            # Valor None → no mostrar
            if value is None:
                continue

            # Lista de hijos
            if isinstance(value, list):
                if not value:
                    tree.add(f"[yellow]{field}[/yellow]: [dim][][/dim]")
                else:
                    branch = tree.add(f"[yellow]{field}[/yellow]")
                    for item in value:
                        branch.add(build_rich_tree(item))

            # Hijo AST
            elif isinstance(value, Node):
                branch = tree.add(f"[yellow]{field}[/yellow]")
                branch.add(build_rich_tree(value))

            # Valor primitivo
            else:
                tree.add(f"[yellow]{field}[/yellow]: [green]{repr(value)}[/green]")

        return tree

    # Valor primitivo suelto (str, int, float, bool)
    return Tree(f"[green]{repr(node)}[/green]")


# =============================================================================
# PARTE 4 – Graphviz
# =============================================================================

def build_graphviz(node, dot=None, parent_id=None, edge_label=None):
    """Recorre el AST y construye un grafo Graphviz."""

    if dot is None:
        dot = Digraph(comment='AST B-Minor')
        dot.attr(rankdir='TB', fontname='Helvetica', fontsize='12')
        dot.attr('node',
                 shape='box',
                 style='rounded,filled',
                 fillcolor='#AED6F1',
                 fontname='Helvetica',
                 fontsize='11')
        dot.attr('edge', fontname='Helvetica', fontsize='9', color='#555555')

    if node is None:
        return dot

    node_id = str(uuid.uuid4())

    if isinstance(node, Node):
        # Etiqueta: nombre de clase + atributos primitivos
        lines = [type(node).__name__]
        for field, value in vars(node).items():
            if field == 'lineno':
                continue
            if not isinstance(value, (Node, list)) and value is not None:
                lines.append(f"{field} = {repr(value)}")

        label = "\n".join(lines)
        dot.node(node_id, label)

        if parent_id is not None:
            dot.edge(parent_id, node_id, label=edge_label or '')

        # Recursión en hijos
        for field, value in vars(node).items():
            if field == 'lineno':
                continue
            if isinstance(value, Node):
                build_graphviz(value, dot, node_id, field)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, Node):
                        build_graphviz(item, dot, node_id, f"{field}[{i}]")

    return dot


# =============================================================================
# PARTE 5 – Integración (main)
# =============================================================================

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python visualizer.py <archivo.bminor>")

    filename = sys.argv[1]

    # Leer archivo fuente
    try:
        source = open(filename, encoding='utf-8').read()
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] No se encontró el archivo '{filename}'")
        sys.exit(1)

    # Limpiar errores anteriores y parsear
    clear_errors()
    try:
        ast = parse(source)
    except Exception:
        ast = None  # El error ya fue reportado por errors.py

    # Si hay errores los muestra errors.py (con número de línea)
    if errors_detected() or ast is None:
        n = errors_detected()
        console.print(
            f"\n[bold red]{n} error{'es' if n != 1 else ''} encontrado{'s' if n != 1 else ''}.[/bold red] "
            "No se puede generar el AST."
        )
        sys.exit(1)

    console.print("\n[bold green]Analisis exitoso.[/bold green]\n")

    # --- Rich Tree ---
    console.rule("[bold]Árbol AST – Rich[/bold]")
    tree = build_rich_tree(ast)
    console.print(tree)

    # --- Graphviz ---
    console.rule("[bold]Graphviz[/bold]")
    dot = build_graphviz(ast)
    import os
    img_dir = 'imagenes_bminor'
    dot_dir = 'dot_bminor'
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(dot_dir, exist_ok=True)

    base_name = os.path.basename(filename).rsplit('.', 1)[0] + '_ast'
    out_base  = os.path.join(img_dir, base_name)
    dot_path  = os.path.join(dot_dir, base_name + '.dot')

    # Siempre guardar el archivo .dot en dot_bminor/
    dot.save(dot_path)
    console.print(f"Archivo DOT guardado en: [cyan]{dot_path}[/cyan]")

    # Intentar renderizar a PNG (requiere Graphviz instalado en el sistema)
    import os, shutil
    # Agregar rutas comunes de Graphviz en Windows si no está en el PATH
    for _gv_path in [r"C:\Program Files\Graphviz\bin", r"C:\Program Files (x86)\Graphviz\bin"]:
        if os.path.isdir(_gv_path) and _gv_path not in os.environ.get("PATH", ""):
            os.environ["PATH"] += os.pathsep + _gv_path
    try:
        dot.render(out_base, format='png', cleanup=True)
        console.print(f"Imagen PNG guardada en:  [cyan]{out_base}.png[/cyan]")
    except Exception:
        console.print(
            "[yellow]Graphviz no esta instalado en el sistema (ejecutable 'dot' no encontrado).[/yellow]\n"
            f"Puedes visualizar el archivo DOT en: [cyan]https://dreampuf.github.io/GraphvizOnline/[/cyan]\n"
            f"o instalar Graphviz desde: [cyan]https://graphviz.org/download/[/cyan]"
        )
    console.print("")


if __name__ == '__main__':
    main()
