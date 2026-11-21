"""Módulo 1 · Detención de emergencia: EDO (RK2, RK4) + integración de v(t) + raíces de v(t)=0."""
import math

import numpy as np

from . import edo, integracion as integ, raices
from .comun import comparar_vectores, ejecucion, g, orden_de_tabla
from .funciones import ErrorExpresion, compilar, derivada_numerica
from .interpolacion import hermite_cubico

BASE = dict(modelo="constante", v0=5.0, x0=0.0, a=1.0, expr_a="0.5+0.3*v", v_exacta="", x_exacta="", dv_exacta="",
            t_det_ref=0.0, t_reaccion=0.5, d_disp=30.0, tf=6.0, N=24, rk2="punto_medio", tol=1e-10, max_iter=100,
            bis_a=0.0, bis_b=6.0, x0_newton=1.0, x0_sec=0.5, x1_sec=2.0, kint=6, sobre="referencia", eps_sens=0.01)
PRESETS = {
    "NORMAL": dict(BASE),
    "ESTRÉS": dict(BASE, modelo="personalizada", v0=7.0, expr_a="0.5+0.3*v", t_reaccion=2.0, d_disp=25.0, tf=8.0, N=8,
                   v_exacta="(7+0.5/0.3)*exp(-0.3*t)-0.5/0.3", x_exacta="(7+0.5/0.3)*(1-exp(-0.3*t))/0.3-0.5*t/0.3",
                   dv_exacta="-0.3*(7+0.5/0.3)*exp(-0.3*t)", bis_b=8.0, x0_newton=3.0, x0_sec=2.0, x1_sec=4.0, kint=7),
    "MAL_CONDICIONADO": dict(BASE, modelo="personalizada", v0=5.0, expr_a="2*sqrt(abs(v)/5)", t_reaccion=0.5,
                             d_disp=20.0, tf=5.0, N=20, v_exacta="5*(1-t/5)**2", dv_exacta="-2*(1-t/5)",
                             x_exacta="5*t-t**2+t**3/15", t_det_ref=5.0, bis_a=0.0, bis_b=6.0, x0_newton=1.0,
                             x0_sec=1.0, x1_sec=2.0),
}
DESCRIPCION = {
    "NORMAL": "Desaceleración constante: v(t)=v0−a·t, x(t)=x0+v0·t−(a/2)t², t_det=v0/a, d=v0²/(2a). Paso adecuado.",
    "ESTRÉS": "Frenado con resistencia a(v)=0.5+0.3·v (solución exacta conocida), reacción de 2 s, paso grueso (N=8) y "
              "distancia disponible limitada. Estrés ≠ mal condicionado: cambia el error numérico, no la sensibilidad.",
    "MAL_CONDICIONADO": "v(t)=5(1−t/5)² tiene RAÍZ DOBLE en t=5: v'(5)=0. Bisección no aplica (v no cambia de signo) y "
                        "Newton pierde la convergencia cuadrática. Residuo pequeño ≠ error pequeño.",
}


def validar(p):
    try:
        if p["v0"] <= 0 or p["tf"] <= 0:
            return "v0 y tf deben ser positivos."
        if not (2 <= p["N"] <= 2000):
            return "N (número de pasos) debe estar entre 2 y 2000."
        if p["modelo"] == "constante":
            if p["a"] <= 0:
                return "La desaceleración a debe ser > 0."
        else:
            compilar(p["expr_a"], ("v", "t"))
        if bool(p["v_exacta"].strip()) != bool(p["x_exacta"].strip()) and p["modelo"] != "constante":
            return "Para usar solución analítica ingresa AMBAS: v(t) y x(t) (o deja las dos vacías)."
        for k in ("v_exacta", "x_exacta", "dv_exacta"):
            if p[k].strip():
                compilar(p[k], ("t",))
        if p["bis_a"] >= p["bis_b"]:
            return "En el intervalo de bisección debe cumplirse a < b."
        if p["tol"] <= 0 or p["max_iter"] < 1:
            return "Tolerancia > 0 y máx. iteraciones ≥ 1."
        if p["t_reaccion"] < 0:
            return "El tiempo de reacción no puede ser negativo."
    except ErrorExpresion as e:
        return str(e)
    return None


def _afun(p, escala=1.0):
    if p["modelo"] == "constante":
        a = p["a"] * escala
        return lambda v, t: a
    A = compilar(p["expr_a"], ("v", "t"))
    return lambda v, t: escala * float(A(v, t))


def _instante_detencion(t, V, dV):
    idx = np.where((V[:-1] > 0) & (V[1:] <= 0))[0]
    if len(idx) == 0:
        return None
    i = int(idx[0])
    lo, hi = t[i], t[i + 1]
    tt, vv, dd = t[i:i + 2], V[i:i + 2], dV[i:i + 2]
    for _ in range(60):
        mid = (lo + hi) / 2
        if float(hermite_cubico(tt, vv, dd, mid)) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _sim_rapida(p, v0, escala):
    """RK4 con N pasos; devuelve (t_det, d_frenado) o (None, None)."""
    afun = _afun(p, escala)
    f = lambda t, y: [y[1], -afun(y[1], t)]
    tf = p["tf"] * 1.25
    t, Y, _, div = edo.integrar(f, 0.0, [p["x0"], v0], tf, int(p["N"] * 1.25) + 1, "rk4")
    if div:
        return None, None
    dY = np.array([f(ti, yi) for ti, yi in zip(t, Y)])
    td = _instante_detencion(t, Y[:, 1], dY[:, 1])
    if td is None:
        return None, None
    xd = float(hermite_cubico(t, Y[:, 0], dY[:, 0], td))
    return td, xd - p["x0"]


def correr(p):
    p = {**BASE, **p}
    err = validar(p)
    if err:
        raise ValueError(err)
    N, tf, v0, x0 = int(p["N"]), float(p["tf"]), float(p["v0"]), float(p["x0"])
    afun = _afun(p)
    f = lambda t, y: [y[1], -afun(y[1], t)]
    t = tf / N * np.arange(N + 1)
    avisos = []

    # ---------- referencia
    err_ref = None
    if p["modelo"] == "constante":
        a = p["a"]
        vref = lambda s: v0 - a * np.asarray(s, float)
        xref = lambda s: x0 + v0 * np.asarray(s, float) - a / 2 * np.asarray(s, float) ** 2
        dvref = lambda s: -a + 0 * np.asarray(s, float)
        tipo_ref = "analítica (a constante)"
    elif p["v_exacta"].strip():
        Vf, Xf = compilar(p["v_exacta"], ("t",)), compilar(p["x_exacta"], ("t",))
        vref, xref = Vf.vec, Xf.vec
        if p["dv_exacta"].strip():
            dvref = compilar(p["dv_exacta"], ("t",)).vec
        else:
            dvref = lambda s: (vref(np.asarray(s, float) + 1e-6) - vref(np.asarray(s, float) - 1e-6)) / 2e-6
        tipo_ref = "analítica (ingresada)"
    else:
        Yg, err_ref, (tt, Yf) = edo.referencia_fina(f, 0.0, [x0, v0], tf, N)
        dYf = np.array([f(ti, yi) for ti, yi in zip(tt, Yf)])
        vref = lambda s: hermite_cubico(tt, Yf[:, 1], dYf[:, 1], s)
        xref = lambda s: hermite_cubico(tt, Yf[:, 0], dYf[:, 0], s)
        dvref = lambda s: np.interp(s, tt, dYf[:, 1])
        tipo_ref = f"numérica: RK4 con {len(tt) - 1} pasos (h/{(len(tt) - 1) // N})"
    Yref = np.column_stack([xref(t), vref(t)])

    # ---------- EDO
    nombres = {"rk2": f"RK2 · {edo.VARIANTES_RK2[p['rk2']][0]}", "rk4": "RK4 clásico"}
    runs = []
    for m in ("rk2", "rk4"):
        T, Y, ms, div = edo.integrar(f, 0.0, [x0, v0], tf, N, m, p["rk2"])
        e = np.linalg.norm(Y - Yref, axis=1)
        nr = np.linalg.norm(Yref, axis=1)
        dY = np.array([f(ti, yi) for ti, yi in zip(T, Y)]) if not div else np.zeros_like(Y)
        hist = [{"numero": k, "aproximacion": [float(T[k])] + Y[k].tolist(), "residual": None,
                 "error_abs": float(e[k]), "error_rel": float(e[k] / nr[k]) if nr[k] > 0 else None} for k in range(N + 1)]
        td = None if div else _instante_detencion(T, Y[:, 1], dY[:, 1])
        xd = None if td is None else float(hermite_cubico(T, Y[:, 0], dY[:, 0], td)) - x0
        runs.append({"metodo": nombres[m], "clave": m, "t": T, "Y": Y, "dY": dY, "err": e, "historial": hist,
                     "convergio": not div, "motivo_parada": "DIVERGE" if div else "paso completo", "tiempo_ms": ms,
                     "tolerancia": None, "max_iter": None, "t_det": td, "d_frenado": xd,
                     "err_max": float(np.nanmax(e)), "err_final": float(e[-1])})
    y_ref_final = Yref[-1] if tipo_ref.startswith("anal") else Yg[-1]
    estudio = edo.estudio_convergencia(f, 0.0, [x0, v0], tf, N, y_ref_final, p["rk2"])

    # ---------- raíces de v(t) = 0
    vs = lambda s: float(vref(np.float64(s)))
    dvs = (lambda s: float(dvref(np.float64(s)))) if (p["modelo"] == "constante" or p["dv_exacta"].strip()) else None
    if p["modelo"] == "constante":
        td_ref = v0 / p["a"]
    elif p["t_det_ref"] > 0:
        td_ref = float(p["t_det_ref"])
    else:
        td_ref = raices.raiz_referencia_alta_precision(vs, p["bis_a"], p["bis_b"])
    rs = [raices.biseccion(vs, p["bis_a"], p["bis_b"], p["tol"], p["max_iter"], td_ref),
          raices.newton_raphson(vs, dvs, p["x0_newton"], p["tol"], p["max_iter"], td_ref),
          raices.secante(vs, p["x0_sec"], p["x1_sec"], p["tol"], p["max_iter"], td_ref)]
    if td_ref is None:
        avisos.append("No hay t_det de referencia (v no cambia de signo en el intervalo): los errores de las raíces "
                      "no se pueden calcular; ingresa 't_det de referencia' si lo conoces.")
    conv = [r for r in rs if r["convergio"]]
    T_int = td_ref if td_ref is not None else (conv[0]["x"] if conv else tf)
    if T_int > tf:
        avisos.append("t_det > tf: la simulación termina antes de detenerse; aumenta tf.")
        T_int = tf

    # ---------- integración de v(t) en [0, t_det]
    if p["sobre"] == "referencia":
        f_int = lambda s: vref(s)
    else:
        r4 = runs[1]
        f_int = lambda s: hermite_cubico(r4["t"], r4["Y"][:, 1], r4["dY"][:, 1], s)
    I_ref = float(xref(T_int) - xref(0.0))
    tabla, R = integ.tabla_refinamiento(f_int, 0.0, T_int, int(p["kint"]), I_ref)

    # ---------- distancias y restricción
    d_reac = v0 * p["t_reaccion"]
    d_fren_ref = I_ref
    d_tot = d_reac + d_fren_ref
    margen = None if p["d_disp"] <= 0 else p["d_disp"] - d_tot
    if margen is not None and margen < 0:
        avisos.append(f"La distancia total de parada ({d_tot:.2f} m) SUPERA la disponible ({p['d_disp']:.2f} m).")

    # ---------- sensibilidad (RK4 con perturbación relativa eps)
    eps = float(p["eps_sens"])
    td0, d0 = _sim_rapida(p, v0, 1.0)
    sens = []
    if td0 is not None:
        for nombre, v0p, esc in (("v0", v0 * (1 + eps), 1.0), ("a (escala)", v0, 1 + eps)):
            tdp, dp = _sim_rapida(p, v0p, esc)
            if tdp is not None:
                sens.append({"parámetro": nombre, "Δrel parámetro": eps, "Δrel t_det": float((tdp - td0) / td0),
                             "Δrel d_frenado": (dp - d0) / d0,
                             "amplif. t_det": float((tdp - td0) / td0 / eps), "amplif. d_frenado": (dp - d0) / d0 / eps})
        if p["t_reaccion"] > 0:
            dt0 = v0 * p["t_reaccion"] + d0
            dt1 = v0 * p["t_reaccion"] * (1 + eps) + d0
            sens.append({"parámetro": "t_reacción", "Δrel parámetro": eps, "Δrel t_det": 0.0,
                         "Δrel d_frenado": 0.0, "amplif. t_det": 0.0, "amplif. d_frenado": 0.0,
                         "Δrel d_total": (dt1 - dt0) / dt0, "amplif. d_total": (dt1 - dt0) / dt0 / eps})
    else:
        avisos.append("Sensibilidad no calculada: v no llegó a 0 dentro de la simulación perturbada.")

    return {"params": p, "t": t, "Yref": Yref, "tipo_ref": tipo_ref, "err_ref": err_ref, "edo": runs,
            "estudio": estudio, "raices": rs, "td_ref": td_ref, "T_int": T_int, "tabla_int": tabla, "R": R,
            "I_ref": I_ref, "d_reac": d_reac, "d_total": d_tot, "margen": margen, "sens": sens, "avisos": avisos,
            "vref": vref, "xref": xref}


def ejecuciones(p, interpretacion="", out=None):
    out = out or correr(p)
    h = out["params"]["tf"] / out["params"]["N"]
    L = []
    for r in out["edo"]:
        last = r["Y"][-1]
        L.append(ejecucion(r, f"Referencia {out['tipo_ref']}", {
            "grafico": "edo", "comparar": [float(last[0]), float(last[1]), r["t_det"], r["d_frenado"]],
            "t_det": r["t_det"], "d_frenado": r["d_frenado"]},
            {"error_max": r["err_max"], "error_final": r["err_final"], "error_ref": out["err_ref"]}, interpretacion, h))
    for r in out["raices"]:
        L.append(ejecucion(r, f"t_det de referencia = {g(out['td_ref'], 10)}", {
            "grafico": "iterativo", "comparar": [r["x"]], "raiz": r["x"], "motivo": r["motivo_parada"]},
            {"orden_observado": r["extra"].get("orden")}, interpretacion))
    for nombre in ("Trapecio compuesto", "Simpson 1/3 compuesto", "Romberg"):
        hist = [{"numero": f["k"], "aproximacion": f[nombre]["valor"], "residual": None,
                 "error_abs": f[nombre]["error_abs"], "error_rel": f[nombre]["error_rel"]} for f in out["tabla_int"]]
        res = {"metodo": nombre, "tolerancia": None, "max_iter": None, "convergio": True, "tiempo_ms": None,
               "historial": hist}
        L.append(ejecucion(res, f"∫v dt = {g(out['I_ref'], 10)} (referencia)", {
            "grafico": "refinamiento", "comparar": [hist[-1]["aproximacion"]], "n": [f["n"] for f in out["tabla_int"]]},
            {"orden_observado": orden_de_tabla(out["tabla_int"], nombre)}, interpretacion,
            out["T_int"] / out["tabla_int"][-1]["n"]))
    return L


def comparar(p, guardadas):
    return ejecuciones(p)


# ------------------------------------------------------------------ conclusiones automáticas
def conclusion_numerica(out):
    p, L = out["params"], []
    r2, r4 = out["edo"]
    L.append(f"EDO: referencia {out['tipo_ref']}" + (f" (error estimado de la referencia ≈ {out['err_ref']:.1e})"
             if out["err_ref"] else "") + f". Error máximo: RK2 = {r2['err_max']:.2e}, RK4 = {r4['err_max']:.2e} con h = {p['tf'] / p['N']:.3g} s.")
    e = out["estudio"]
    p2, p4 = e[-1].get("p_rk2"), e[-1].get("p_rk4")
    if p2 and p4:
        L.append(f"Orden observado al reducir h: RK2 ≈ {p2:.2f} (teórico 2) y RK4 ≈ {p4:.2f} (teórico 4)."
                 + (" Un orden menor al teórico indica que la solución o la ecuación no es suficientemente suave "
                    "(aquí a(v)=√|v| no es Lipschitz en v = 0)." if p4 < 3.5 else ""))
    else:
        L.append("El error de RK2 y RK4 está al nivel del redondeo (p. ej. con a constante la solución es polinómica de grado ≤ 2 y ambos "
                 "métodos la integran exactamente), por eso no se observa un orden.")
    tab = out["tabla_int"]
    ords = {n: orden_de_tabla(tab, n) for n in ("Trapecio compuesto", "Simpson 1/3 compuesto", "Romberg")}
    ult = tab[-1]
    L.append(f"Integración con n = {ult['n']}: error trapecio {ult['Trapecio compuesto']['error_abs']:.1e}, Simpson "
             f"{ult['Simpson 1/3 compuesto']['error_abs']:.1e}, Romberg {ult['Romberg']['error_abs']:.1e}. Órdenes observados: "
             + ", ".join(f"{k.split()[0]} {g(v, 3) if v else '— (error ≈ redondeo)'}" for k, v in ords.items()) + " (teóricos 2, 4 y mayor).")
    for r in out["raices"]:
        txt = f"{r['metodo']}: " + (f"{r['iteraciones']} iteraciones, error {g(r['historial'][-1]['error_abs'], 3)}, orden ≈ {g(r['extra'].get('orden'), 3)}"
                                    if r["convergio"] else f"NO convergió ({r['motivo_parada']})")
        L.append(txt)
    if p["modelo"] != "constante" and out["tipo_ref"].startswith("anal") and p["t_det_ref"] > 0:
        L.append("En raíz doble (v'(t_det) = 0) Newton y la secante convergen solo linealmente (orden ≈ 1) y el residuo |v| es mucho "
                 "menor que el error en t: un residuo pequeño no garantiza una raíz precisa. No es un fallo de convergencia ni un "
                 "problema físicamente peligroso: es sensibilidad matemática de la raíz.")
    return "\n".join(f"- {x}" for x in L)


def conclusion_problema(out):
    p, L = out["params"], []
    td = out["td_ref"]
    L.append(f"El vehículo se detiene en t ≈ {g(td, 5)} s tras iniciar el frenado; la distancia de frenado es {g(out['I_ref'], 5)} m y la de "
             f"reacción {out['d_reac']:.2f} m (v0·t_reacción), total {out['d_total']:.2f} m.")
    if out["margen"] is not None:
        L.append(("Con la distancia disponible de " f"{p['d_disp']:.1f} m el margen es {out['margen']:.2f} m: " +
                  ("SÍ alcanza a detenerse." if out["margen"] >= 0 else "NO alcanza: se necesitaría menor velocidad, mayor frenado o menor tiempo de reacción.")))
    if out["sens"]:
        s = {x["parámetro"]: x for x in out["sens"]}
        if "v0" in s:
            L.append(f"Sensibilidad (+{p['eps_sens'] * 100:.1f}% en el parámetro): la distancia de frenado cambia {s['v0']['Δrel d_frenado'] * 100:.2f}% por v0 "
                     f"(amplificación {s['v0']['amplif. d_frenado']:.2f}; con a constante vale 2 porque d ∝ v0²) y {s.get('a (escala)', {}).get('Δrel d_frenado', float('nan')) * 100:.2f}% por la desaceleración.")
    L.append("Variables que más influyen: velocidad inicial (efecto cuadrático), intensidad de frenado y tiempo de reacción; el paso numérico solo "
             "importa si el error numérico se acerca al margen de seguridad.")
    L.append("Qué NO puede inferirse: modelo 1D sin pendiente, viento, adherencia ni fallas del sistema de frenos real; parámetros sintéticos; "
             "no describe ninguna cabina real de Mi Teleférico.")
    return "\n".join(f"- {x}" for x in L)
