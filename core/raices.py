"""Raíces de f(x)=0: bisección, Newton-Raphson y secante. Misma estructura de resultado que los sistemas lineales."""
import math
from time import perf_counter

import numpy as np

from .funciones import derivada_numerica


def _reg(k, x, f, x_ref, **extra):
    fx = f(x)
    ea = None if x_ref is None else abs(x - x_ref)
    er = None if (x_ref is None or x_ref == 0) else ea / abs(x_ref)
    return {"numero": k, "aproximacion": float(x), "residual": abs(float(fx)), "error_abs": ea, "error_rel": er,
            "fx": float(fx), **extra}


def orden_observado(hist):
    """p ≈ ln(e_{k+1}/e_k) / ln(e_k/e_{k-1}) (mediana de los últimos valores válidos)."""
    e = [h["error_abs"] for h in hist if h["error_abs"] is not None and h["error_abs"] > 1e-14]
    ps = []
    for k in range(1, len(e) - 1):
        try:
            if e[k - 1] > e[k] > e[k + 1]:
                ps.append(math.log(e[k + 1] / e[k]) / math.log(e[k] / e[k - 1]))
        except (ValueError, ZeroDivisionError):
            pass
    return float(np.median(ps[-4:])) if ps else None


def _fin(nombre, x, hist, conv, motivo, t0, tol, max_iter, **extra):
    return {"metodo": nombre, "x": x, "iteraciones": hist[-1]["numero"], "convergio": bool(conv),
            "motivo_parada": motivo, "historial": hist, "tiempo_ms": (perf_counter() - t0) * 1000,
            "tolerancia": tol, "max_iter": max_iter, "extra": {"orden": orden_observado(hist), **extra}}


def biseccion(f, a, b, tol=1e-10, max_iter=200, x_ref=None):
    t0 = perf_counter()
    fa, fb = f(a), f(b)
    if not (np.isfinite(fa) and np.isfinite(fb)):
        return _fin("Bisección", float("nan"), [_reg(0, (a + b) / 2, lambda x: float("nan"), x_ref)], False,
                    "f no es finita en los extremos", t0, tol, max_iter)
    if fa * fb > 0:
        return _fin("Bisección", float("nan"), [_reg(0, (a + b) / 2, f, x_ref, a=a, b=b)], False,
                    f"NO APLICABLE: f(a)·f(b) > 0 en [{a:g}, {b:g}] (no hay cambio de signo)", t0, tol, max_iter)
    hist, conv, motivo = [], False, "se alcanzó max_iter"
    for k in range(1, max_iter + 1):
        c = (a + b) / 2
        fc = f(c)
        hist.append(_reg(k, c, f, x_ref, a=a, b=b))
        if fc == 0 or (b - a) / 2 < tol:
            conv, motivo = True, "(b−a)/2 < tol" if fc != 0 else "f(c) = 0"
            break
        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    return _fin("Bisección", hist[-1]["aproximacion"], hist, conv, motivo, t0, tol, max_iter)


def newton_raphson(f, df, x0, tol=1e-10, max_iter=100, x_ref=None):
    """df puede ser None: se usa derivada por diferencias centrales (se declara en 'extra')."""
    t0 = perf_counter()
    deriv = df if df is not None else (lambda x: derivada_numerica(f, x))
    x = float(x0)
    hist = [_reg(0, x, f, x_ref)]
    conv, motivo = False, "se alcanzó max_iter"
    for k in range(1, max_iter + 1):
        d = deriv(x)
        if not np.isfinite(d) or abs(d) < 1e-14:
            motivo = "f'(x) ≈ 0: Newton no puede continuar"
            break
        xn = x - f(x) / d
        if not np.isfinite(xn) or abs(xn) > 1e12:
            motivo = "DIVERGE (valor no finito o |x| > 1e12)"
            break
        paso = abs(xn - x)
        x = xn
        hist.append(_reg(k, x, f, x_ref))
        if paso < tol:
            conv, motivo = True, "|x_k − x_{k−1}| < tol"
            break
    return _fin("Newton-Raphson", x, hist, conv, motivo, t0, tol, max_iter,
                derivada="analítica" if df is not None else "numérica (diferencias centrales)")


def secante(f, x0, x1, tol=1e-10, max_iter=100, x_ref=None):
    t0 = perf_counter()
    xa, xb = float(x0), float(x1)
    hist = [_reg(0, xa, f, x_ref), _reg(1, xb, f, x_ref)]
    conv, motivo = False, "se alcanzó max_iter"
    for k in range(2, max_iter + 2):
        fa, fb = f(xa), f(xb)
        if fb == fa or not np.isfinite(fb - fa):
            motivo = "f(x_k) = f(x_{k−1}): la secante es horizontal"
            break
        xn = xb - fb * (xb - xa) / (fb - fa)
        if not np.isfinite(xn) or abs(xn) > 1e12:
            motivo = "DIVERGE (valor no finito o |x| > 1e12)"
            break
        paso = abs(xn - xb)
        xa, xb = xb, xn
        hist.append(_reg(k, xb, f, x_ref))
        if paso < tol:
            conv, motivo = True, "|x_k − x_{k−1}| < tol"
            break
    return _fin("Secante", xb, hist, conv, motivo, t0, tol, max_iter)


def raiz_referencia_alta_precision(f, a, b):
    """Bisección con tolerancia 1e-15 (referencia numérica justificada). None si no hay cambio de signo."""
    r = biseccion(f, a, b, tol=1e-15, max_iter=200)
    return r["x"] if r["convergio"] else None


def raices_cuadratica(c0, c1, c2):
    """Raíces reales de c2 t² + c1 t + c0 = 0 con fórmula estable (sin cancelación)."""
    if c2 == 0:
        return [] if c1 == 0 else [-c0 / c1]
    disc = c1 * c1 - 4 * c2 * c0
    if disc < 0:
        return []
    q = -0.5 * (c1 + math.copysign(math.sqrt(disc), c1 if c1 != 0 else 1.0))
    rs = [q / c2] + ([c0 / q] if q != 0 else [])
    return sorted(set(rs))
