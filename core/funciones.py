"""Evaluación SEGURA de expresiones escritas por el usuario (sin eval libre).
Solo permite números, variables declaradas, + - * / ** y funciones matemáticas de una lista blanca."""
import ast
import math

import numpy as np

FUNCIONES = {"sin": np.sin, "cos": np.cos, "tan": np.tan, "exp": np.exp, "log": np.log, "ln": np.log,
             "log10": np.log10, "sqrt": np.sqrt, "abs": np.abs, "sinh": np.sinh, "cosh": np.cosh,
             "tanh": np.tanh, "atan": np.arctan, "asin": np.arcsin, "acos": np.arccos, "sign": np.sign,
             "min": np.minimum, "max": np.maximum}
CONSTANTES = {"pi": math.pi, "e": math.e}
AYUDA = ("Puedes usar + − * / ** (o ^), paréntesis, pi, e y las funciones: " + ", ".join(sorted(FUNCIONES)) + ".")


class ErrorExpresion(ValueError):
    pass


class _Flotar(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ErrorExpresion("Solo se permiten números en la expresión.")
        return ast.copy_location(ast.Constant(float(node.value)), node)


def _validar(n, variables):
    if isinstance(n, ast.Expression):
        return _validar(n.body, variables)
    if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
        _validar(n.left, variables)
        return _validar(n.right, variables)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
        return _validar(n.operand, variables)
    if isinstance(n, ast.Constant):
        return
    if isinstance(n, ast.Name):
        if n.id not in variables and n.id not in CONSTANTES:
            raise ErrorExpresion(f"'{n.id}' no es válido. Variables permitidas: {', '.join(variables)}. {AYUDA}")
        return
    if isinstance(n, ast.Call):
        if not isinstance(n.func, ast.Name) or n.func.id not in FUNCIONES or n.keywords:
            raise ErrorExpresion(f"Función no permitida. {AYUDA}")
        for a in n.args:
            _validar(a, variables)
        return
    raise ErrorExpresion(f"Expresión no permitida. {AYUDA}")


class Funcion:
    """f(*variables) compilada de forma segura. `.vec(t)` evalúa sobre arreglos."""

    def __init__(self, texto, variables=("t",)):
        texto = (texto or "").strip().replace("^", "**")
        if not texto:
            raise ErrorExpresion("La expresión está vacía.")
        if len(texto) > 300:
            raise ErrorExpresion("Expresión demasiado larga.")
        try:
            arbol = ast.parse(texto, mode="eval")
        except SyntaxError:
            raise ErrorExpresion("Sintaxis inválida. Revisa paréntesis y operadores (ej.: 2*sin(t) + t**2).")
        arbol = ast.fix_missing_locations(_Flotar().visit(arbol))
        _validar(arbol, variables)
        self.texto, self.variables = texto, tuple(variables)
        self._code = compile(arbol, "<expr>", "eval")
        self._ns = {"__builtins__": {}, **FUNCIONES, **CONSTANTES}

    def __call__(self, *args):
        with np.errstate(all="ignore"):
            try:
                return eval(self._code, self._ns, dict(zip(self.variables, args)))
            except (ZeroDivisionError, OverflowError, ValueError):
                return float("nan")

    def vec(self, t):
        t = np.asarray(t, dtype=float)
        return np.broadcast_to(np.asarray(self(t), dtype=float), t.shape).copy()


def compilar(texto, variables=("t",)):
    return Funcion(texto, variables)


def derivada_numerica(f, x, h=None):
    """Diferencias centrales: f'(x) ≈ [f(x+h) − f(x−h)] / (2h)."""
    h = h or 1e-5 * max(1.0, abs(x))
    return (f(x + h) - f(x - h)) / (2 * h)
