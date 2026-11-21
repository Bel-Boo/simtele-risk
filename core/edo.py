"""EDO con RK2 (familia de un parámetro α; variante declarada) y RK4 clásico. Sistemas y' = f(t, y)."""
import math
from time import perf_counter

import numpy as np

VARIANTES_RK2 = {"punto_medio": ("Punto medio (α = 1/2)", 0.5),
                 "heun": ("Heun / trapecio mejorado (α = 1)", 1.0),
                 "ralston": ("Ralston (α = 2/3)", 2 / 3)}


def paso_rk2(f, t, y, h, alpha):
    """y_{n+1} = y_n + h[(1 − 1/(2α)) k1 + (1/(2α)) k2],  k2 = f(t + αh, y + αh k1)."""
    k1 = f(t, y)
    k2 = f(t + alpha * h, [yi + alpha * h * ki for yi, ki in zip(y, k1)])
    w2 = 1 / (2 * alpha)
    w1 = 1 - w2
    return [yi + h * (w1 * a + w2 * b) for yi, a, b in zip(y, k1, k2)]


def paso_rk4(f, t, y, h):
    k1 = f(t, y)
    k2 = f(t + h / 2, [yi + h / 2 * k for yi, k in zip(y, k1)])
    k3 = f(t + h / 2, [yi + h / 2 * k for yi, k in zip(y, k2)])
    k4 = f(t + h, [yi + h * k for yi, k in zip(y, k3)])
    return [yi + h / 6 * (a + 2 * b + 2 * c + d) for yi, a, b, c, d in zip(y, k1, k2, k3, k4)]


def integrar(f, t0, y0, tf, N, metodo, variante="punto_medio"):
    """Devuelve (t, Y, tiempo_ms, divergio). Y tiene forma (N+1, dim)."""
    ini = perf_counter()
    h = (tf - t0) / N
    alpha = VARIANTES_RK2[variante][1]
    y = [float(v) for v in y0]
    Y = [y]
    divergio = False
    for i in range(N):
        t = t0 + i * h
        y = paso_rk4(f, t, y, h) if metodo == "rk4" else paso_rk2(f, t, y, h, alpha)
        if not math.isfinite(sum(y)):
            divergio = True
            Y.extend([[float("nan")] * len(y0)] * (N - i))
            break
        Y.append(y)
    return t0 + h * np.arange(N + 1), np.array(Y, float), (perf_counter() - ini) * 1000, divergio


def referencia_fina(f, t0, y0, tf, N, s=None):
    """RK4 con N·2^s pasos muestreado en la malla de N pasos. Estimación del error de la referencia por
    Richardson: |Y_{h} − Y_{2h}| / 15. Devuelve (Y_en_malla, error_estimado, (t_fino, Y_fino))."""
    if s is None:
        s = max(5, math.ceil(math.log2(30000 / N)))
    tt, Yf, _, _ = integrar(f, t0, y0, tf, N * 2 ** s, "rk4")
    _, Yg, _, _ = integrar(f, t0, y0, tf, N * 2 ** (s - 1), "rk4")
    err = float(np.nanmax(np.abs(Yf[::2] - Yg))) / 15
    return Yf[:: 2 ** s], err, (tt, Yf)


def estudio_convergencia(f, t0, y0, tf, N, y_ref_final, variante="punto_medio", niveles=4):
    """Error en t_f con N, 2N, 4N, 8N pasos. Orden observado p = log2(e_j / e_{j+1})."""
    filas = []
    for j in range(niveles):
        Nj = N * 2 ** j
        fila = {"N": Nj, "h": (tf - t0) / Nj}
        for m in ("rk2", "rk4"):
            _, Y, _, _ = integrar(f, t0, y0, tf, Nj, m, variante)
            fila[m] = float(np.linalg.norm(Y[-1] - np.asarray(y_ref_final)))
        filas.append(fila)
    for m in ("rk2", "rk4"):
        for j in range(niveles - 1):
            a, b = filas[j][m], filas[j + 1][m]
            filas[j + 1][f"p_{m}"] = math.log2(a / b) if a > 1e-14 and b > 1e-14 else None
    return filas
