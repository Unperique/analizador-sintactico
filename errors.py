# errors.py
'''
Gestión de errores del compilador.

Una de las partes más importantes (y molestas) de escribir un compilador
es la notificación fiable de mensajes de error al usuario. Este archivo
debería consolidar algunas funciones básicas de gestión de errores en un solo lugar.
Facilitar la notificación de errores. Facilitar la detección de errores.

Podría ampliarse para que sea más potente posteriormente.

Variable global que indica si se ha producido algún error. El compilador puede 
consultar esto posteriormente para decidir si debe detenerse.
'''
from rich.console import Console

_errors_detected = 0
_console = Console(stderr=True)

def error(message, lineno=None, error_type="Error"):
	global _errors_detected
	_errors_detected += 1
	label = f"[bold red]{error_type} #{_errors_detected}[/bold red]"
	location = f"[yellow](línea {lineno})[/yellow]" if lineno else ""
	_console.print(f"{label} {location} {message}")

def errors_detected():
	return _errors_detected

def clear_errors():
	global _errors_detected
	_errors_detected = 0
