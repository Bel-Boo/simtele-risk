"""Módulo 4 · Reconstrucción de señales: Lagrange, Newton (dif. divididas) y spline cúbico natural."""
import math

import numpy as np

from . import raices
from .comun import ejecucion, g
from .funciones import ErrorExpresion, compilar
from .interpolacion import (SplineNatural, constante_lebesgue, cond_vandermonde, diferencias_divididas, lagrange,
                            newton_dd, nodos_chebyshev)

BASE = dict(fuente="sintetica", func="sin(t)", a=0.0, b=6.0, n=12, nodos="equiespaciados", nodos_txt="", sigma=0.0,
            semilla=42, ocultos="2, 5, 8", datos_txt="", umbral="", tol=1e-10, max_iter=100, eps_sens=1e-3, n_graf=200)
PRESETS = {
    "NORMAL": dict(BASE),
    "ESTRÉS": dict(BASE, n=20, sigma=0.05, ocultos="3, 7, 10, 11, 15", umbral="0.5"),
    "MAL_CONDICIONADO": dict(BASE, b=12.0, n=25, sigma=1e-3, ocultos="4, 12, 20", eps_sens=1e-3),
}
DESCRIPCION = {
    "NORMAL": "y(t)=sen t con 12 nodos equiespaciados y SIN ruido; se ocultan 3 puntos interiores y se mide el error de reconstrucción.",
    "ESTRÉS": "Ruido gaussiano σ=0.05, más nodos (20) y más puntos ocultos (5, algunos consecutivos). Se mide la distorsión por ruido.",
    "MAL_CONDICIONADO": "25 nodos EQUIESPACIADOS en [0,12] (polinomio de grado 24): κ(Vandermonde) y constante de Lebesgue enormes; "
                        "ruido de solo 1e-3 se amplifica fuertemente en los extremos (fenómeno de Runge). Compárese con nodos de Chebyshev.",
}
NOMBRES = ("Lagrange", "Newton (diferencias divididas)", "Spline cúbico natural")


def _lista_ints(txt):
    try:
        return sorted({int(x) for x in str(txt).replace(";", ",").split(",") if x.strip()})
    except ValueError:
        raise ValueError("Los índices de puntos ocultos deben ser enteros separados por comas (ej.: 2, 5, 8).")


def parsear_datos(txt):
    t, y = [], []
    for i, linea in enumerate(str(txt).strip().splitlines(), 1):
        partes = [x for x in linea.replace(";", " ").replace(",", " ").replace("\t", " ").split(" ") if x]
        if not partes:
            continue
        if len(partes) != 2:
            raise ValueError(f"Línea {i}: se esperaban 2 valores (t y y).")
        try:
            t.append(float(partes[0]))
            y.append(float(partes[1]))
        except ValueError:
            raise ValueError(f"Línea {i}: '{linea.strip()}' no es numérica (usa punto decimal).")
    return np.array(t), np.array(y)


def _datos(p):
    """Devuelve t, y_medido, y_verdadero (None si son datos propios), función base (o None)."""
    if p["fuente"] == "propios":
        t, y = parsear_datos(p["datos_txt"])
        if len(t) < 5:
            raise ValueError("Pega al menos 5 pares (t, y).")
        o = np.argsort(t)
        return t[o], y[o], None, None
    F = compilar(p["func"], ("t",))
    n = int(p["n"])
    if p["a"] >= p["b"]:
        raise ValueError("Debe cumplirse a < b.")
    if not (5 <= n <= 60):
        raise ValueError("El número de nodos debe estar entre 5 y 60.")
    if p["nodos"] == "chebyshev":
        t = nodos_chebyshev(p["a"], p["b"], n)
    elif p["nodos"] == "personalizados":
        t = np.sort(np.array([float(x) for x in str(p["nodos_txt"]).replace(";", ",").split(",") if x.strip()]))
        if len(t) < 5:
            raise ValueError("Ingresa al menos 5 valores de t.")
    else:
        t = np.linspace(p["a"], p["b"], n)
    y_ver = F.vec(t)
    rng = np.random.default_rng(int(p["semilla"]))
    y_med = y_ver + p["sigma"] * rng.standard_normal(len(t))
    return t, y_med, y_ver, F


def validar(p):
    try:
        t, y, yv, F = _datos(p)
        idx = _lista_ints(p["ocultos"])
        if not idx:
            return "Indica al menos un punto oculto (índices desde 0)."
        if min(idx) < 0 or max(idx) >= len(t):
            return f"Los índices deben estar entre 0 y {len(t) - 1}."
        if len(t) - len(idx) < 4:
            return "Deben quedar al menos 4 nodos conocidos."
        if np.any(np.diff(t) <= 0):
            return "Los nodos t deben ser estrictamente crecientes."
        if str(p["umbral"]).strip():
            float(p["umbral"])
    except (ValueError, ErrorExpresion) as e:
        return str(e)
    return None


def _evalua(nombre, tk, yk, xq):
    if nombre == NOMBRES[0]:
        return lagrange(tk, yk, xq)
    if nombre == NOMBRES[1]:
        return newton_dd(tk, yk, xq)
    return SplineNatural(tk, yk)(xq)


def correr(p):
    import time
    p = {**BASE, **p}
    err = validar(p)
    if err:
        raise ValueError(err)
    t, y_med, y_ver, F = _datos(p)
    idx = _lista_ints(p["ocultos"])
    mask = np.ones(len(t), bool)
    mask[idx] = False
    tk, yk, th = t[mask], y_med[mask], t[~mask]
    ref_h = (y_ver if y_ver is not None else y_med)[~mask]
    ref_txt = "y(t) verdadera (sin ruido)" if y_ver is not None else "valor medido en el dato ocultado"
    tg = np.linspace(t.min(), t.max(), int(p["n_graf"]))
    yg_ver = F.vec(tg) if F is not None else None

    # diagnósticos de condicionamiento
    diag = {"n_conocidos": int(mask.sum()), "grado": int(mask.sum()) - 1,
            "cond_vandermonde": cond_vandermonde(tk) if len(tk) <= 40 else None,
            "lebesgue": constante_lebesgue(tk, m=1500) if len(tk) <= 40 else None,
            "h_max": float(np.max(np.diff(tk))), "h_min": float(np.min(np.diff(tk)))}
    if len(tk) <= 40:
        diag["lebesgue_chebyshev"] = constante_lebesgue(nodos_chebyshev(tk[0], tk[-1], len(tk)), m=1500)

    # sensibilidad ante perturbación de los datos (amplificación observada)
    rng = np.random.default_rng(int(p["semilla"]) + 1)
    delta = float(p["eps_sens"]) * rng.standard_normal(len(tk))
    dmax = float(np.max(np.abs(delta)))

    res = []
    for nom in NOMBRES:
        t0 = time.perf_counter()
        yh = _evalua(nom, tk, yk, th)
        yg = _evalua(nom, tk, yk, tg)
        ms = (time.perf_counter() - t0) * 1000
        ea = np.abs(yh - ref_h)
        er = [float(a / abs(r)) if abs(r) > 1e-12 else None for a, r in zip(ea, ref_h)]
        hist = [{"numero": int(i), "aproximacion": [float(th[j]), float(yh[j])], "residual": None, "error_abs": float(ea[j]),
                 "error_rel": er[j]} for j, i in enumerate(np.where(~mask)[0])]
        amp_h = float(np.max(np.abs(_evalua(nom, tk, yk + delta, th) - yh)) / dmax)
        amp_g = float(np.max(np.abs(_evalua(nom, tk, yk + delta, tg) - yg)) / dmax)
        res.append({"metodo": nom, "yh": yh, "yg": yg, "historial": hist, "convergio": bool(np.all(np.isfinite(yh))),
                    "motivo_parada": "evaluación directa", "tiempo_ms": ms, "tolerancia": None, "max_iter": None,
                    "err_max": float(ea.max()), "err_rms": float(np.sqrt(np.mean(ea ** 2))), "err_h": ea,
                    "err_curva": None if yg_ver is None else float(np.max(np.abs(yg - yg_ver))),
                    "amp_ocultos": amp_h, "amp_curva": amp_g})
    dif_ln = float(np.max(np.abs(res[0]["yh"] - res[1]["yh"])))

    # cruce de umbral con la curva interpolada (spline) por raíces
    cruce = None
    if str(p["umbral"]).strip():
        u = float(p["umbral"])
        S = SplineNatural(tk, yk)
        s = S(tg) - u
        ii = np.where(s[:-1] * s[1:] < 0)[0]
        if len(ii):
            lo, hi = float(tg[ii[0]]), float(tg[ii[0] + 1])
            fS = lambda x: float(S(np.float64(x))) - u
            dS = lambda x: float(S.derivada(np.float64(x)))
            ref = None
            if F is not None:
                ref = raices.raiz_referencia_alta_precision(lambda x: float(F(x)) - u, lo - (hi - lo), hi + (hi - lo))
            rr = [raices.biseccion(fS, lo, hi, p["tol"], p["max_iter"], ref),
                  raices.newton_raphson(fS, dS, (lo + hi) / 2, p["tol"], p["max_iter"], ref),
                  raices.secante(fS, lo, hi, p["tol"], p["max_iter"], ref)]
            cruce = {"umbral": u, "ref": ref, "bracket": (lo, hi), "res": rr}
        else:
            cruce = {"umbral": u, "ref": None, "bracket": None, "res": []}
    avisos = []
    if min(idx) == 0 or max(idx) == len(t) - 1:
        avisos.append("Ocultaste un extremo: es EXTRAPOLACIÓN, no interpolación; el error crece mucho.")
    return {"params": p, "t": t, "y_med": y_med, "y_ver": y_ver, "mask": mask, "tk": tk, "yk": yk, "th": th, "ref_h": ref_h,
            "ref_txt": ref_txt, "tg": tg, "yg_ver": yg_ver, "diag": diag, "res": res, "dif_lag_newton": dif_ln, "cruce": cruce,
            "avisos": avisos, "tabla_dd": diferencias_divididas(tk, yk) if len(tk) <= 10 else None, "dmax": dmax}


def ejecuciones(p, interpretacion="", out=None):
    out = out or correr(p)
    sub = np.linspace(0, len(out["tg"]) - 1, min(200, len(out["tg"]))).astype(int)
    L = []
    for r in out["res"]:
        L.append(ejecucion(r, f"Referencia: {out['ref_txt']}", {
            "grafico": "interpolacion", "comparar": r["yh"].tolist(), "t_graf": out["tg"][sub].tolist(),
            "y_graf": r["yg"][sub].tolist(), "t_ocultos": out["th"].tolist(), "y_ref_ocultos": out["ref_h"].tolist(),
            "t_nodos": out["tk"].tolist(), "y_nodos": out["yk"].tolist()},
            {"error_max": r["err_max"], "error_rms": r["err_rms"], "error_curva": r["err_curva"],
             "amplificacion_ruido": r["amp_curva"], "cond_vandermonde": out["diag"]["cond_vandermonde"],
             "lebesgue": out["diag"]["lebesgue"]}, interpretacion))
    if out["cruce"] and out["cruce"]["res"]:
        for r in out["cruce"]["res"]:
            L.append(ejecucion(r, f"cruce de umbral {out['cruce']['umbral']:g} (referencia {g(out['cruce']['ref'], 10)})",
                               {"grafico": "iterativo", "comparar": [r["x"]], "raiz": r["x"]}, {}, interpretacion))
    return L


def conclusion_numerica(out):
    p, d, L = out["params"], out["diag"], []
    for r in out["res"]:
        L.append(f"{r['metodo']}: error máximo en los puntos ocultos {r['err_max']:.2e} (RMS {r['err_rms']:.2e})"
                 + (f"; error máximo en toda la curva {r['err_curva']:.2e}" if r["err_curva"] is not None else "") + ".")
    L.append(f"Lagrange y Newton construyen el MISMO polinomio de grado {d['grado']}: difieren solo en {out['dif_lag_newton']:.1e} (redondeo); "
             "la forma de Newton con Horner suele ser más estable y barata, y permite añadir nodos sin recalcular.")
    if d["cond_vandermonde"] is not None:
        L.append(f"κ(Vandermonde) = {d['cond_vandermonde']:.2e}; constante de Lebesgue de tus nodos Λ = {d['lebesgue']:.2e} frente a "
                 f"{d['lebesgue_chebyshev']:.2f} con nodos de Chebyshev. Λ acota cuánto se amplifica el error de los datos.")
    pol, spl = out["res"][0], out["res"][2]
    L.append(f"Amplificación observada de una perturbación de {p['eps_sens']:.0e} en los datos: polinomio {pol['amp_curva']:.2f}×, spline {spl['amp_curva']:.2f}×. "
             "El spline (cúbicos por tramos, sistema tridiagonal bien condicionado) es mucho más estable que un polinomio de grado alto.")
    if out["cruce"] and out["cruce"]["res"]:
        c = out["cruce"]
        L.append(f"Cruce de umbral {c['umbral']:g} sobre el spline: " + "; ".join(
            f"{r['metodo']} {g(r['x'], 8)} ({r['iteraciones']} it.)" if r["convergio"] else f"{r['metodo']} no convergió" for r in c["res"]) + ".")
    return "\n".join(f"- {x}" for x in L)


def conclusion_problema(out):
    p, d, L = out["params"], out["diag"], []
    mejor = min(out["res"], key=lambda r: r["err_max"])
    L.append(f"Se ocultaron {len(out['th'])} registros y se reconstruyeron con {d['n_conocidos']} nodos conocidos; el mejor método fue {mejor['metodo']} "
             f"con error máximo {mejor['err_max']:.2e} (unidades de la señal).")
    if p["sigma"] > 0 and p["fuente"] == "sintetica":
        L.append(f"Con ruido σ = {p['sigma']:g} la reconstrucción hereda y puede amplificar el error: interpolar datos ruidosos obliga a pasar EXACTAMENTE por "
                 "cada dato, ruido incluido. Para señales reales suele ser mejor suavizar (ajuste por mínimos cuadrados) que interpolar.")
    L.append(f"El espaciamiento influye: h entre {d['h_min']:.3g} y {d['h_max']:.3g}. Huecos grandes (puntos ocultos consecutivos) reducen la confiabilidad; "
             "los extremos del intervalo son los más inestables, sobre todo con polinomios de grado alto y nodos equiespaciados.")
    L.append("Qué NO puede inferirse: la señal es sintética; un error pequeño en los puntos ocultos no garantiza buen comportamiento fuera del "
             "intervalo ni entre nodos; no dice nada sobre sensores reales de Mi Teleférico.")
    return "\n".join(f"- {x}" for x in L)
