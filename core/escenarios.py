"""Construcción reproducible de sistemas A x* = b para los escenarios del Módulo 2 (calibración)."""
import ast
import re
from fractions import Fraction

import numpy as np

TIPOS = ("NORMAL", "ESTRÉS", "MAL_CONDICIONADO")
MATRICES = {
    "tridiagonal_dd": "Tridiagonal diagonalmente dominante SPD (4 en la diagonal, -1 fuera)",
    "poisson1d": "Poisson 1D SPD (2 en la diagonal, -1 fuera): converge lento en Jacobi/GS",
    "hilbert": "Hilbert SPD, kappa(A) enorme (mal condicionada)",
    "personalizada": "Personalizada (la pegas tú)",
}

PARAMS_DEFECTO = {
    "NORMAL": {"matriz": "tridiagonal_dd", "n": 6, "tol": 1e-10, "max_iter": 1000, "eps_sens": 1e-6},
    "ESTRÉS": {"matriz": "poisson1d", "n": 40, "tol": 1e-12, "max_iter": 20000, "eps_sens": 1e-3},
    "MAL_CONDICIONADO": {"matriz": "hilbert", "n": 6, "tol": 1e-10, "max_iter": 5000, "eps_sens": 1e-10},
}


def construir_matriz(tipo, n):
    if tipo == "tridiagonal_dd":
        return 4.0 * np.eye(n) - np.eye(n, k=1) - np.eye(n, k=-1)
    if tipo == "poisson1d":
        return 2.0 * np.eye(n) - np.eye(n, k=1) - np.eye(n, k=-1)
    if tipo == "hilbert":
        i = np.arange(1, n + 1)
        return 1.0 / (i[:, None] + i[None, :] - 1.0)
    raise ValueError(f"Tipo de matriz desconocido: {tipo}")


EJEMPLO_MATRIZ = "10 2 1 0\n2 9 -1 1\n1 -1 8 2\n0 1 2 7"


def _num(tok):
    tok = str(tok).strip()
    try:
        v = float(Fraction(tok)) if "/" in tok else float(tok)
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"'{tok}' no es un número válido (usa punto decimal, p. ej. 0.5, o fracciones como 1/3).")
    if not np.isfinite(v):
        raise ValueError("La matriz contiene valores no finitos (nan/inf).")
    return v


def parsear_matriz(texto):
    """Acepta: una fila por línea (separadas por espacios, comas, tabs o ;) o formato [[1,2],[3,4]]."""
    t = (texto or "").strip()
    if not t:
        raise ValueError("Pega una matriz: una fila por línea.")
    if t.startswith("[["):
        try:
            filas = [[_num(x) for x in f] for f in ast.literal_eval(t)]
        except (ValueError, SyntaxError, TypeError):
            raise ValueError("Formato [[...],[...]] inválido. Revisa corchetes y comas.")
    else:
        filas = []
        for linea in re.split(r"[\n]+", t):
            linea = linea.strip().strip("[]").rstrip(";")
            if linea:
                filas.append([_num(x) for x in re.split(r"[\s,;]+", linea) if x])
    if len({len(f) for f in filas}) != 1:
        raise ValueError("Todas las filas deben tener la misma cantidad de elementos.")
    return np.array(filas, dtype=float)


def parsear_vector(texto):
    return np.array([_num(x) for x in re.split(r"[\s,;]+", texto.strip().strip("[]")) if x], dtype=float)


def validar_matriz(A, x_star=None):
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError(f"La matriz debe ser cuadrada; la tuya es {A.shape[0]}×{A.shape[1] if A.ndim == 2 else '?'}.")
    n = A.shape[0]
    if n < 4:
        raise ValueError(f"La consigna exige n ≥ 4; la tuya es {n}×{n}.")
    if n > 200:
        raise ValueError("Por rendimiento, n ≤ 200.")
    if np.linalg.matrix_rank(A) < n:
        raise ValueError("La matriz es singular (rango incompleto): A x = b no tiene solución única.")
    if x_star is not None:
        if len(x_star) != n:
            raise ValueError(f"x* debe tener {n} elementos; tiene {len(x_star)}.")
        if not np.any(x_star):
            raise ValueError("x* no puede ser todo ceros (no se podría calcular el error relativo).")


def construir_sistema(params):
    """A, b = A x*, x* conocido. Determinista: mismos params -> mismo sistema."""
    if params["matriz"] == "personalizada":
        A = np.array(params["A"], dtype=float)
        xs = params.get("x_star")
        xs = np.array(xs, dtype=float) if xs else None
        validar_matriz(A, xs)
        n = A.shape[0]
        x_star = xs if xs is not None else np.arange(1, n + 1, dtype=float)
        return A, A @ x_star, x_star
    n = int(params["n"])
    if n < 4:
        raise ValueError("La consigna exige n >= 4")
    A = construir_matriz(params["matriz"], n)
    x_star = np.arange(1, n + 1, dtype=float)
    return A, A @ x_star, x_star
