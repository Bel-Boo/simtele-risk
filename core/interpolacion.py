"""Interpolación: Lagrange, Newton (diferencias divididas), spline cúbico natural y utilidades."""
import numpy as np


def _validar_nodos(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.ndim != 1 or len(x) != len(y) or len(x) < 2:
        raise ValueError("Se necesitan al menos 2 nodos y los mismos datos en x e y.")
    if np.any(np.diff(x) <= 0):
        raise ValueError("Los nodos x deben ser estrictamente crecientes (sin repetidos).")
    return x, y


def lagrange(x, y, xq):
    """P(xq) = Σ y_i · L_i(xq),  L_i = Π_{j≠i} (xq − x_j)/(x_i − x_j)."""
    x, y = _validar_nodos(x, y)
    xq = np.asarray(xq, float)
    P = np.zeros_like(xq)
    for i in range(len(x)):
        L = np.ones_like(xq)
        for j in range(len(x)):
            if j != i:
                L *= (xq - x[j]) / (x[i] - x[j])
        P += y[i] * L
    return P


def base_lagrange(x, xq):
    """Matriz de polinomios L_i(xq) (para la constante de Lebesgue)."""
    x = np.asarray(x, float)
    xq = np.asarray(xq, float)
    L = np.ones((len(x), len(xq)))
    for i in range(len(x)):
        for j in range(len(x)):
            if j != i:
                L[i] *= (xq - x[j]) / (x[i] - x[j])
    return L


def diferencias_divididas(x, y):
    """Tabla triangular de diferencias divididas; los coeficientes son la 1.ª fila."""
    x, y = _validar_nodos(x, y)
    n = len(x)
    T = np.zeros((n, n))
    T[:, 0] = y
    for j in range(1, n):
        for i in range(n - j):
            T[i, j] = (T[i + 1, j - 1] - T[i, j - 1]) / (x[i + j] - x[i])
    return T


def newton_dd(x, y, xq, T=None):
    """Forma de Newton evaluada con esquema de Horner."""
    x, y = _validar_nodos(x, y)
    T = diferencias_divididas(x, y) if T is None else T
    c = T[0]
    xq = np.asarray(xq, float)
    P = np.full_like(xq, c[-1])
    for k in range(len(x) - 2, -1, -1):
        P = P * (xq - x[k]) + c[k]
    return P


def _thomas(a, b, c, d):
    """Resuelve un sistema tridiagonal (a: sub, b: diagonal, c: super)."""
    n = len(d)
    cp, dp = np.zeros(n), np.zeros(n)
    cp[0], dp[0] = c[0] / b[0], d[0] / b[0]
    for i in range(1, n):
        den = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / den if i < n - 1 else 0.0
        dp[i] = (d[i] - a[i] * dp[i - 1]) / den
    x = np.zeros(n)
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


class SplineNatural:
    """Spline cúbico natural S''(x_0) = S''(x_n) = 0. Los c_i salen de un sistema tridiagonal SPD."""

    def __init__(self, x, y):
        x, y = _validar_nodos(x, y)
        if len(x) < 3:
            raise ValueError("El spline cúbico necesita al menos 3 nodos.")
        n = len(x) - 1
        h = np.diff(x)
        alpha = np.zeros(n + 1)
        alpha[1:n] = 3 * ((y[2:] - y[1:-1]) / h[1:] - (y[1:-1] - y[:-2]) / h[:-1])
        a = np.zeros(n + 1)
        b = np.ones(n + 1)
        c = np.zeros(n + 1)
        a[1:n], b[1:n], c[1:n] = h[:-1], 2 * (h[:-1] + h[1:]), h[1:]
        cc = _thomas(a, b, c, alpha)
        self.x, self.y, self.c = x, y, cc
        self.b = (y[1:] - y[:-1]) / h - h * (2 * cc[:-1] + cc[1:]) / 3
        self.d = (cc[1:] - cc[:-1]) / (3 * h)

    def __call__(self, xq):
        xq = np.asarray(xq, float)
        i = np.clip(np.searchsorted(self.x, xq, side="right") - 1, 0, len(self.x) - 2)
        dx = xq - self.x[i]
        return self.y[i] + self.b[i] * dx + self.c[i] * dx ** 2 + self.d[i] * dx ** 3

    def derivada(self, xq):
        xq = np.asarray(xq, float)
        i = np.clip(np.searchsorted(self.x, xq, side="right") - 1, 0, len(self.x) - 2)
        dx = xq - self.x[i]
        return self.b[i] + 2 * self.c[i] * dx + 3 * self.d[i] * dx ** 2


def hermite_cubico(t, y, dy, tq):
    """Interpolante cúbico de Hermite (usa valores y derivadas en los nodos): 'salida densa' de las EDO."""
    t, y, dy = np.asarray(t, float), np.asarray(y, float), np.asarray(dy, float)
    tq = np.asarray(tq, float)
    i = np.clip(np.searchsorted(t, tq, side="right") - 1, 0, len(t) - 2)
    h = t[i + 1] - t[i]
    s = (tq - t[i]) / h
    h00 = 2 * s ** 3 - 3 * s ** 2 + 1
    h10 = s ** 3 - 2 * s ** 2 + s
    h01 = -2 * s ** 3 + 3 * s ** 2
    h11 = s ** 3 - s ** 2
    return h00 * y[i] + h10 * h * dy[i] + h01 * y[i + 1] + h11 * h * dy[i + 1]


def nodos_chebyshev(a, b, n):
    k = np.arange(n)
    return np.sort((a + b) / 2 + (b - a) / 2 * np.cos((2 * k + 1) * np.pi / (2 * n)))


def cond_vandermonde(x):
    return float(np.linalg.cond(np.vander(np.asarray(x, float), increasing=True), 2))


def constante_lebesgue(x, a=None, b=None, m=2000):
    """Λ_n = max_t Σ|L_i(t)|: amplificación máxima del error de los datos por la interpolación polinómica."""
    x = np.asarray(x, float)
    a = x[0] if a is None else a
    b = x[-1] if b is None else b
    tt = np.linspace(a, b, m)
    return float(np.max(np.abs(base_lagrange(x, tt)).sum(axis=0)))
