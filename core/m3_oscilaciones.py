"""Módulo 3 · Oscilaciones por viento: m x'' + c x' + k x = F(t) con RK2 y RK4; integración de x² o |x|."""
import math

import numpy as np

from . import edo, integracion as integ
from .comun import ejecucion, g, orden_de_tabla
from .funciones import ErrorExpresion, compilar
from .interpolacion import hermite_cubico

BASE = dict(m=1200.0, c=480.0, k=4800.0, F_expr="0", x0=0.5, v0=0.0, tf=20.0, N=400, rk2="punto_medio",
            magnitud="x2", kint=8, sobre="referencia", eps_sens=0.01)
PRESETS = {
    "NORMAL": dict(BASE),
    "ESTRÉS": dict(BASE, c=240.0, F_expr="300*sin(2*t)", x0=0.0, tf=60.0, N=300, kint=9),
    "MAL_CONDICIONADO": dict(BASE, c=4795.2, tf=20.0, N=400, eps_sens=1e-5),
}
DESCRIPCION = {
    "NORMAL": "Vibración libre subamortiguada (ζ=0.1, F=0): solución analítica e^{−ζω₀t}[C1 cos ω_d t + C2 sen ω_d t].",
    "ESTRÉS": "Fuerza armónica F=300·sen(2t) en RESONANCIA (Ω=ω₀), tiempo largo (60 s) y paso grueso (h=0.2 s): RK2 pierde precisión. "
              "Referencia: RK4 con paso mucho menor (numérica justificada).",
    "MAL_CONDICIONADO": "Amortiguamiento casi crítico ζ=0.999: ω_d = ω₀√(1−ζ²) es hipersensible a c, k y m (amplificación ≈ ζ²/(1−ζ²) ≈ 500).",
}


def validar(p):
    try:
        if min(p["m"], p["k"]) <= 0 or p["c"] < 0:
            return "m y k deben ser > 0 y c ≥ 0."
        if p["tf"] <= 0 or not (2 <= p["N"] <= 2000):
            return "tf > 0 y N entre 2 y 2000."
        compilar(p["F_expr"], ("t",))
    except ErrorExpresion as e:
        return str(e)
    return None


def parametros_modales(p):
    w0 = math.sqrt(p["k"] / p["m"])
    z = p["c"] / (2 * math.sqrt(p["k"] * p["m"]))
    wd = w0 * math.sqrt(1 - z * z) if z < 1 else None
    return {"w0": w0, "zeta": z, "wd": wd, "c_critico": 2 * math.sqrt(p["k"] * p["m"])}


def solucion_libre(p):
    """(x(t), v(t)) analíticas vectorizadas para F=0 (subamortiguado, crítico o sobreamortiguado)."""
    m_ = parametros_modales(p)
    w0, z, x0, v0 = m_["w0"], m_["zeta"], p["x0"], p["v0"]
    if z < 1 - 1e-9:
        wd, s = m_["wd"], z * w0
        A, B = x0, (v0 + s * x0) / wd
        x = lambda t: np.exp(-s * np.asarray(t, float)) * (A * np.cos(wd * np.asarray(t, float)) + B * np.sin(wd * np.asarray(t, float)))
        v = lambda t: np.exp(-s * np.asarray(t, float)) * ((-s * A + wd * B) * np.cos(wd * np.asarray(t, float)) + (-s * B - wd * A) * np.sin(wd * np.asarray(t, float)))
    elif abs(z - 1) <= 1e-9:
        B = v0 + w0 * x0
        x = lambda t: np.exp(-w0 * np.asarray(t, float)) * (x0 + B * np.asarray(t, float))
        v = lambda t: np.exp(-w0 * np.asarray(t, float)) * (B - w0 * x0 - w0 * B * np.asarray(t, float))
    else:
        q = math.sqrt(z * z - 1)
        r1, r2 = -w0 * (z - q), -w0 * (z + q)
        C1, C2 = (v0 - r2 * x0) / (r1 - r2), (r1 * x0 - v0) / (r1 - r2)
        x = lambda t: C1 * np.exp(r1 * np.asarray(t, float)) + C2 * np.exp(r2 * np.asarray(t, float))
        v = lambda t: C1 * r1 * np.exp(r1 * np.asarray(t, float)) + C2 * r2 * np.exp(r2 * np.asarray(t, float))
    return x, v


def _es_libre(p):
    return p["F_expr"].strip().replace(" ", "") in ("", "0", "0.0")


def _amplitud(p, N=None):
    """Amplitud máxima por RK4 (usada en sensibilidad)."""
    F = compilar(p["F_expr"], ("t",))
    f = lambda t, y: [y[1], (float(F(t)) - p["c"] * y[1] - p["k"] * y[0]) / p["m"]]
    _, Y, _, div = edo.integrar(f, 0.0, [p["x0"], p["v0"]], p["tf"], N or p["N"], "rk4")
    return None if div else float(np.max(np.abs(Y[:, 0])))


def correr(p):
    p = {**BASE, **p}
    err = validar(p)
    if err:
        raise ValueError(err)
    N, tf = int(p["N"]), float(p["tf"])
    F = compilar(p["F_expr"], ("t",))
    m_, c_, k_ = p["m"], p["c"], p["k"]
    f = lambda t, y: [y[1], (float(F(t)) - c_ * y[1] - k_ * y[0]) / m_]
    modal = parametros_modales(p)
    t = tf / N * np.arange(N + 1)
    err_ref = None
    if _es_libre(p):
        xr_, vr_ = solucion_libre(p)
        tipo_ref = "analítica (vibración libre)"
        xref, vref = xr_, vr_
        y_ref_final = np.array([float(xr_(tf)), float(vr_(tf))])
    else:
        Yg, err_ref, (tt, Yf) = edo.referencia_fina(f, 0.0, [p["x0"], p["v0"]], tf, N)
        dYf = np.array([f(ti, yi) for ti, yi in zip(tt, Yf)])
        xref = lambda s: hermite_cubico(tt, Yf[:, 0], dYf[:, 0], s)
        vref = lambda s: hermite_cubico(tt, Yf[:, 1], dYf[:, 1], s)
        tipo_ref = f"numérica: RK4 con {len(tt) - 1} pasos (h/{(len(tt) - 1) // N})"
        y_ref_final = Yg[-1]
    Yref = np.column_stack([xref(t), vref(t)])
    tdens = np.linspace(0, tf, 20001)
    amp_ref = float(np.max(np.abs(xref(tdens))))

    nombres = {"rk2": f"RK2 · {edo.VARIANTES_RK2[p['rk2']][0]}", "rk4": "RK4 clásico"}
    runs = []
    for mm in ("rk2", "rk4"):
        T, Y, ms, div = edo.integrar(f, 0.0, [p["x0"], p["v0"]], tf, N, mm, p["rk2"])
        e = np.linalg.norm(Y - Yref, axis=1)
        nr = np.linalg.norm(Yref, axis=1)
        dY = np.array([f(ti, yi) for ti, yi in zip(T, Y)]) if not div else np.zeros_like(Y)
        hist = [{"numero": i, "aproximacion": [float(T[i])] + Y[i].tolist(), "residual": None, "error_abs": float(e[i]),
                 "error_rel": float(e[i] / nr[i]) if nr[i] > 0 else None} for i in range(N + 1)]
        runs.append({"metodo": nombres[mm], "clave": mm, "t": T, "Y": Y, "dY": dY, "err": e, "historial": hist,
                     "convergio": not div, "motivo_parada": "DIVERGE" if div else "paso completo", "tiempo_ms": ms,
                     "tolerancia": None, "max_iter": None, "amp": float(np.nanmax(np.abs(Y[:, 0]))),
                     "err_max": float(np.nanmax(e)), "err_final": float(e[-1])})
    dif_rk = float(np.nanmax(np.abs(runs[0]["Y"][:, 0] - runs[1]["Y"][:, 0])))
    estudio = edo.estudio_convergencia(f, 0.0, [p["x0"], p["v0"]], tf, N, y_ref_final, p["rk2"])

    # ---- integración de la magnitud acumulada
    g_mag = (lambda s: np.asarray(xref(s)) ** 2) if p["magnitud"] == "x2" else (lambda s: np.abs(xref(s)))
    if p["sobre"] == "referencia":
        xi = xref
    else:
        r4 = runs[1]
        xi = lambda s: hermite_cubico(r4["t"], r4["Y"][:, 0], r4["dY"][:, 0], s)
    f_int = (lambda s: np.asarray(xi(s)) ** 2) if p["magnitud"] == "x2" else (lambda s: np.abs(xi(s)))
    partir = integ.ceros_en_intervalo(xref, 0.0, tf) if p["magnitud"] == "abs" else None
    I_ref = integ.integral_referencia(g_mag, 0.0, tf, partir)
    tabla, R = integ.tabla_refinamiento(f_int, 0.0, tf, int(p["kint"]), I_ref)

    # ---- sensibilidad de la frecuencia amortiguada y de la amplitud a m, c, k
    eps, sens = float(p["eps_sens"]), []
    A0 = _amplitud(p, min(N, 600))
    for k in ("m", "c", "k"):
        if p[k] == 0:
            continue
        q = {**p, k: p[k] * (1 + eps)}
        mq = parametros_modales(q)
        fila = {"parámetro": k, "Δrel parámetro": eps}
        if modal["wd"] and mq["wd"]:
            fila["Δrel ω_d"] = (mq["wd"] - modal["wd"]) / modal["wd"]
            fila["amplif. ω_d"] = fila["Δrel ω_d"] / eps
        Aq = _amplitud(q, min(N, 600))
        if A0 and Aq:
            fila["Δrel A_max"] = (Aq - A0) / A0
            fila["amplif. A_max"] = fila["Δrel A_max"] / eps
        sens.append(fila)
    avisos = []
    if modal["zeta"] >= 1:
        avisos.append("ζ ≥ 1: el sistema no oscila (críticamente o sobreamortiguado).")
    h = tf / N
    return {"params": p, "t": t, "Yref": Yref, "tipo_ref": tipo_ref, "err_ref": err_ref, "modal": modal, "edo": runs,
            "amp_ref": amp_ref, "dif_rk": dif_rk, "estudio": estudio, "tabla_int": tabla, "I_ref": I_ref, "sens": sens,
            "avisos": avisos, "xref": xref, "vref": vref, "h": h}


def ejecuciones(p, interpretacion="", out=None):
    out = out or correr(p)
    L = []
    for r in out["edo"]:
        last = r["Y"][-1]
        L.append(ejecucion(r, f"Referencia {out['tipo_ref']}", {
            "grafico": "edo", "comparar": [float(last[0]), float(last[1]), r["amp"]], "amplitud_max": r["amp"]},
            {"error_max": r["err_max"], "error_final": r["err_final"], "dif_rk2_rk4": out["dif_rk"]}, interpretacion, out["h"]))
    for nombre in ("Trapecio compuesto", "Simpson 1/3 compuesto", "Romberg"):
        hist = [{"numero": f["k"], "aproximacion": f[nombre]["valor"], "residual": None,
                 "error_abs": f[nombre]["error_abs"], "error_rel": f[nombre]["error_rel"]} for f in out["tabla_int"]]
        res = {"metodo": nombre, "tolerancia": None, "max_iter": None, "convergio": True, "tiempo_ms": None, "historial": hist}
        L.append(ejecucion(res, f"∫{'x²' if out['params']['magnitud'] == 'x2' else '|x|'} dt = {g(out['I_ref'], 10)} (referencia)",
                           {"grafico": "refinamiento", "comparar": [hist[-1]["aproximacion"]], "n": [f["n"] for f in out["tabla_int"]]},
                           {"orden_observado": orden_de_tabla(out["tabla_int"], nombre)}, interpretacion,
                           out["params"]["tf"] / out["tabla_int"][-1]["n"]))
    return L


def conclusion_numerica(out):
    p, L = out["params"], []
    r2, r4 = out["edo"]
    L.append(f"Referencia {out['tipo_ref']}" + (f" (error estimado ≈ {out['err_ref']:.1e})" if out["err_ref"] else "")
             + f". Con h = {out['h']:.3g} s: error máximo RK2 = {r2['err_max']:.2e}, RK4 = {r4['err_max']:.2e}; "
             f"diferencia máxima entre ambos en x(t) = {out['dif_rk']:.2e}.")
    e = out["estudio"][-1]
    if e.get("p_rk2") and e.get("p_rk4"):
        L.append(f"Orden observado: RK2 ≈ {e['p_rk2']:.2f} y RK4 ≈ {e['p_rk4']:.2f} (teóricos 2 y 4).")
    ratio = r2["err_max"] / r4["err_max"] if r4["err_max"] > 0 else float("inf")
    L.append(f"RK2 comete ≈ {ratio:.0f} veces el error de RK4 con el mismo paso, pero RK4 usa 4 evaluaciones de f por paso frente a 2.")
    tab = out["tabla_int"]
    u = tab[-1]
    L.append(f"Integral de {'x²' if p['magnitud'] == 'x2' else '|x|'} con n = {u['n']}: error trapecio {u['Trapecio compuesto']['error_abs']:.1e}, "
             f"Simpson {u['Simpson 1/3 compuesto']['error_abs']:.1e}, Romberg {u['Romberg']['error_abs']:.1e}."
             + (" Con |x| el integrando no es suave en los cruces por cero y se degrada el orden de todos los métodos." if p["magnitud"] == "abs" else ""))
    return "\n".join(f"- {x}" for x in L)


def conclusion_problema(out):
    p, m, L = out["params"], out["modal"], []
    L.append(f"ω₀ = {m['w0']:.4g} rad/s, ζ = {m['zeta']:.4g}" + (f", ω_d = {m['wd']:.4g} rad/s." if m["wd"] else " (sin oscilación)."))
    L.append(f"La amplitud máxima es ≈ {out['amp_ref']:.4g} m (referencia); RK2 la estima en {out['edo'][0]['amp']:.4g} m y RK4 en {out['edo'][1]['amp']:.4g} m.")
    if not _es_libre(p):
        L.append("Con fuerza externa la respuesta depende de la cercanía entre la frecuencia de la fuerza y ω₀: cerca de la resonancia la "
                 "amplitud crece hasta que el amortiguamiento la limita; el riesgo modelado cambia, no solo el error numérico.")
    s = {x["parámetro"]: x for x in out["sens"]}
    if "c" in s and "amplif. ω_d" in s["c"]:
        L.append(f"Sensibilidad (+{p['eps_sens'] * 100:.2g}% en c): ω_d cambia {s['c']['Δrel ω_d'] * 100:.3g}% (amplificación {s['c']['amplif. ω_d']:.1f}). "
                 + ("Cerca de ζ = 1 la frecuencia amortiguada es hipersensible a los parámetros: es mal condicionamiento del modelo, no peligro físico." if abs(s["c"]["amplif. ω_d"]) > 20 else ""))
    L.append("Qué NO puede inferirse: es un oscilador lineal de 1 grado de libertad con fuerza sintética; no modela turbulencia, cable ni cabina "
             "reales ni las normas de operación con viento de Mi Teleférico.")
    return "\n".join(f"- {x}" for x in L)
