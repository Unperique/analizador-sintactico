# typesys.py
'''
Sistema de tipos
================
Tablas de compatibilidad de operadores para B-Minor.
Cada entrada (_bin_ops, _unary_ops) mapea
(tipo_izq, operador, tipo_der) -> tipo_resultado
para binarios, y (operador, tipo) -> tipo_resultado para unarios.
'''

typenames = { 'integer', 'float', 'boolean', 'char', 'string' }

# ---------------------------------------------------------------------------
# Operadores binarios
# ---------------------------------------------------------------------------
_bin_ops = {
    # --- Integer ---
    ('integer', '+',  'integer') : 'integer',
    ('integer', '-',  'integer') : 'integer',
    ('integer', '*',  'integer') : 'integer',
    ('integer', '/',  'integer') : 'integer',
    ('integer', '%',  'integer') : 'integer',
    ('integer', '^',  'integer') : 'integer',   # potencia

    ('integer', '<',  'integer') : 'boolean',
    ('integer', '<=', 'integer') : 'boolean',
    ('integer', '>',  'integer') : 'boolean',
    ('integer', '>=', 'integer') : 'boolean',
    ('integer', '==', 'integer') : 'boolean',
    ('integer', '!=', 'integer') : 'boolean',

    # --- Float ---
    ('float', '+',  'float') : 'float',
    ('float', '-',  'float') : 'float',
    ('float', '*',  'float') : 'float',
    ('float', '/',  'float') : 'float',
    ('float', '%',  'float') : 'float',
    ('float', '^',  'float') : 'float',

    ('float', '<',  'float') : 'boolean',
    ('float', '<=', 'float') : 'boolean',
    ('float', '>',  'float') : 'boolean',
    ('float', '>=', 'float') : 'boolean',
    ('float', '==', 'float') : 'boolean',
    ('float', '!=', 'float') : 'boolean',

    # --- Boolean ---
    ('boolean', '&&', 'boolean') : 'boolean',
    ('boolean', '||', 'boolean') : 'boolean',
    ('boolean', '==', 'boolean') : 'boolean',
    ('boolean', '!=', 'boolean') : 'boolean',

    # --- Char ---
    ('char', '<',  'char') : 'boolean',
    ('char', '<=', 'char') : 'boolean',
    ('char', '>',  'char') : 'boolean',
    ('char', '>=', 'char') : 'boolean',
    ('char', '==', 'char') : 'boolean',
    ('char', '!=', 'char') : 'boolean',

    # --- String ---
    ('string', '+',  'string') : 'string',
    ('string', '==', 'string') : 'boolean',
    ('string', '!=', 'string') : 'boolean',
}

# ---------------------------------------------------------------------------
# Operadores unarios  (incluye prefijos ++ / --)
# ---------------------------------------------------------------------------
_unary_ops = {
    ('+',  'integer') : 'integer',
    ('-',  'integer') : 'integer',
    ('++', 'integer') : 'integer',
    ('--', 'integer') : 'integer',

    ('+',  'float')   : 'float',
    ('-',  'float')   : 'float',

    ('!',  'boolean') : 'boolean',
}

# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def lookup_type(name: str):
    """Devuelve el nombre del tipo si es primitivo válido, si no None."""
    return name if name in typenames else None


def check_binop(op: str, left_type, right_type):
    """Tipo resultado de (left_type op right_type), o None si no es válido."""
    return _bin_ops.get((left_type, op, right_type))


def check_unaryop(op: str, operand_type):
    """Tipo resultado de (op operand_type), o None si no es válido."""
    return _unary_ops.get((op, operand_type))
