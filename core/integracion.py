"""Integración numérica: trapecio compuesto, Simpson 1/3 compuesto y Romberg."""
import numpy as np


def _vec(f):
    def g(x):
        x = np.asarray(x, float)
        return np.broadcast_to(np.asarray(f(x), float), x.shape)
    return g


def trapecio_compuesto(f, a, b, n):
    f = _vec(f)
    h = (b - a) / n
    y = f(a + h * np.arange(n + 1))
    return float(h * (y[0] / 2 + y[1:-1].sum() + y[-1] / 2))


def simpson_13_compuesto(f, a, b, n):
    if n % 2:
        raise ValueError("Simpson 1/3 compuesto requiere un número PAR de subintervalos.")
    f = _vec(f)
    h = (b - a) / n
    y = f(a + h * np.arange(n + 1))
    return float(h / 3 * (y[0] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum() + y[-1]))


def romberg(f, a, b, m):
    """Tabla de Romberg R[i][j], i,j = 0..m. R[i][0] = trapecio con 2^i subintervalos."""
    f = _vec(f)
    R = np.zeros((m + 1, m + 1))
    R[0, 0] = (b - a) * (f(a) + f(b)) / 2
    for i in range(1, m + 1):
        h = (b - a) / 2 ** i
        puntos = a + h * (2 * np.arange(2 ** (i - 1)) + 1)
        R[i, 0] = R[i - 1, 0] / 2 + h * f(puntos).sum()
        for j in range(1, i + 1):
            R[i, j] = R[i, j - 1] + (R[i, j - 1] - R[i - 1, j - 1]) / (4 ** j - 1)
    return R


def tabla_refinamiento(f, a, b, kmax, I_ref):
    """Para n = 2^k (k=1..kmax): trapecio, Simpson y Romberg R[k][k] con sus errores respecto de I_ref."""
    R = romberg(f, a, b, kmax)
    filas = []
    for k in range(1, kmax + 1):
        n = 2 ** k
        vals = {"Trapecio compuesto": trapecio_compuesto(f, a, b, n),
                "Simpson 1/3 compuesto": simpson_13_compuesto(f, a, b, n),
                "Romberg": float(R[k, k])}
        fila = {"k": k, "n": n, "h": (b - a) / n}
        for nombre, v in vals.items():
            ea = None if I_ref is None else abs(v - I_ref)
            er = None if (I_ref is None or I_ref == 0) else ea / abs(I_ref)
            fila[nombre] = {"valor": v, "error_abs": ea, "error_rel": er}
        filas.append(fila)
    return filas, R


def integral_referencia(f, a, b, partir=None, m=13):
    """Referencia de alta precisión: Romberg nivel m (2^13 subintervalos). Si `partir` (nodos de no
    suavidad, p. ej. ceros de x(t) al integrar |x|) se integra por tramos suaves."""
    pts = [a] + sorted(p for p in (partir or []) if a < p < b) + [b]
    tot = 0.0
    for u, v in zip(pts[:-1], pts[1:]):
        tot += float(romberg(f, u, v, m)[m, m])
    return tot


def ceros_en_intervalo(f, a, b, n_scan=4000):
    """Ceros de una función continua (barrido + bisección) para partir integrales de |f|."""
    f = _vec(f)
    t = np.linspace(a, b, n_scan + 1)
    y = f(t)
    ceros = []
    for i in np.where(y[:-1] * y[1:] < 0)[0]:
        lo, hi = t[i], t[i + 1]
        flo = float(f(lo))
        for _ in range(60):
            mid = (lo + hi) / 2
            fm = float(f(mid))
            if flo * fm <= 0:
                hi = mid
            else:
                lo, flo = mid, fm
        ceros.append((lo + hi) / 2)
    return ceros
