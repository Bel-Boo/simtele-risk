"""Módulo 2 · Deterioro (raíces): tiempo t* en que D(t) alcanza el umbral. Bisección, Newton y secante."""
import math

import numpy as np

from . import integracion as integ, raices
from .comun import ejecucion, g, orden_de_tabla
from .funciones import ErrorExpresion, compilar, derivada_numerica

BASE = dict(modelo="cuadratico", D0=10.0, alpha=0.05, beta=0.0002, D_umbral=40.0,
            expr_D="10+0.05*t+0.0002*t**2", expr_dD="", a=0.0, b=1000.0, x0_newton=100.0, x0_sec=50.0, x1_sec=150.0,
            tol=1e-10, max_iter=100, t_mant=240.0, retraso=0.0, eps_sens=1e-3, integrar_tasa=True, kint=6)
PRESETS = {
    "NORMAL": dict(BASE),
    "ESTRÉS": dict(BASE, alpha=0.01, beta=0.0006, tol=1e-12, max_iter=200, x0_newton=50.0, x0_sec=20.0, x1_sec=80.0,
                   t_mant=200.0, retraso=60.0, eps_sens=1e-2, kint=8),
    "MAL_CONDICIONADO": dict(BASE, alpha=0.1, beta=-0.0005, D_umbral=14.999999, b=100.0, x0_newton=50.0,
                             x0_sec=20.0, x1_sec=60.0, t_mant=90.0, eps_sens=1e-6),
}
DESCRIPCION = {
    "NORMAL": "D(t)=D0+αt+βt² con raíz simple bien separada: todos los métodos convergen con su orden teórico.",
    "ESTRÉS": "Deterioro más acelerado (β mayor), tolerancia 1e-12 y mantenimiento RETRASADO 60 días: ¿se alcanza el umbral antes de intervenir?",
    "MAL_CONDICIONADO": "β<0 (el indicador se satura): el umbral queda casi TANGENTE al máximo de D (raíz casi doble). La raíz es "
                        "hipersensible: un cambio de 1e-6 en el umbral puede hacerla desaparecer.",
}


def validar(p):
    try:
        if p["modelo"] == "cuadratico":
            if p["alpha"] == 0 and p["beta"] == 0:
                return "α y β no pueden ser ambos cero."
        else:
            compilar(p["expr_D"], ("t",))
            if p["expr_dD"].strip():
                compilar(p["expr_dD"], ("t",))
        if p["a"] >= p["b"]:
            return "En el intervalo de bisección debe cumplirse a < b."
        if p["tol"] <= 0 or p["max_iter"] < 1:
            return "Tolerancia > 0 y máx. iteraciones ≥ 1."
    except ErrorExpresion as e:
        return str(e)
    return None


def _D(p):
    if p["modelo"] == "cuadratico":
        D0, al, be = p["D0"], p["alpha"], p["beta"]
        return (lambda t: D0 + al * t + be * t * t), (lambda t: al + 2 * be * t)
    Df = compilar(p["expr_D"], ("t",))
    D = lambda t: float(Df(t)) if np.ndim(t) == 0 else Df.vec(t)
    if p["expr_dD"].strip():
        dDf = compilar(p["expr_dD"], ("t",))
        return D, (lambda t: float(dDf(t)) if np.ndim(t) == 0 else dDf.vec(t))
    return D, None


def _t_estrella(p, **cambios):
    """Raíz física (la más pequeña t ≥ 0 con D(t)=D_umbral) de referencia."""
    q = {**p, **cambios}
    if q["modelo"] == "cuadratico":
        rs = [r for r in raices.raices_cuadratica(q["D0"] - q["D_umbral"], q["alpha"], q["beta"]) if r >= 0]
        return min(rs) if rs else None
    D, _ = _D(q)
    return raices.raiz_referencia_alta_precision(lambda t: D(t) - q["D_umbral"], q["a"], q["b"])


def correr(p):
    p = {**BASE, **p}
    err = validar(p)
    if err:
        raise ValueError(err)
    D, dD = _D(p)
    Du = p["D_umbral"]
    f = lambda t: D(t) - Du
    df = (lambda t: dD(t)) if dD is not None else None
    avisos = []
    t_ref = _t_estrella(p)
    if t_ref is None:
        avisos.append("No existe t* ≥ 0 con D(t*) = D_umbral (la ecuación no tiene raíz física / no hay cambio de signo en [a,b]).")
    if D(0.0) >= Du:
        avisos.append("D(0) ≥ D_umbral: el umbral ya está superado en t = 0.")
    rs = [raices.biseccion(f, p["a"], p["b"], p["tol"], p["max_iter"], t_ref),
          raices.newton_raphson(f, df, p["x0_newton"], p["tol"], p["max_iter"], t_ref),
          raices.secante(f, p["x0_sec"], p["x1_sec"], p["tol"], p["max_iter"], t_ref)]
    # discriminante / información de la cuadrática
    info = {}
    if p["modelo"] == "cuadratico":
        disc = p["alpha"] ** 2 - 4 * p["beta"] * (p["D0"] - Du)
        info = {"discriminante": disc, "raices": raices.raices_cuadratica(p["D0"] - Du, p["alpha"], p["beta"])}
        if p["beta"] < 0:
            tv = -p["alpha"] / (2 * p["beta"])
            info["t_vertice"], info["D_max"] = tv, D(tv)
    # sensibilidad (diferencias centrales)
    eps, sens = float(p["eps_sens"]), []
    if t_ref is not None:
        claves = ("D0", "alpha", "beta", "D_umbral") if p["modelo"] == "cuadratico" else ("D_umbral",)
        for k in claves:
            v = p[k]
            if v == 0:
                continue
            tp, tm = _t_estrella(p, **{k: v * (1 + eps)}), _t_estrella(p, **{k: v * (1 - eps)})
            amp = None if (tp is None or tm is None) else (tp - tm) / (2 * eps * t_ref)
            sens.append({"parámetro": k, "t*(+ε)": tp, "t*(−ε)": tm, "amplificación": amp})
    # mantenimiento
    mant = None
    if p["t_mant"] > 0 and t_ref is not None:
        t_ef = p["t_mant"] + p["retraso"]
        mant = {"t_mant_programado": p["t_mant"], "retraso": p["retraso"], "t_efectivo": t_ef, "t_estrella": t_ref,
                "margen": t_ef - t_ref, "D_en_mantenimiento": float(D(t_ef)), "antes": t_ref < t_ef}
    # integral de la tasa D'(t) en [0, t*]  (= D(t*) − D(0))
    tabla, I_ref = None, None
    if p["integrar_tasa"] and t_ref is not None and t_ref > 0:
        if dD is not None:
            rate = lambda t: dD(np.asarray(t, float))
        else:
            rate = lambda t: (D(np.asarray(t, float) + 1e-5) - D(np.asarray(t, float) - 1e-5)) / 2e-5
        I_ref = float(D(t_ref) - D(0.0))
        tabla, _ = integ.tabla_refinamiento(rate, 0.0, t_ref, int(p["kint"]), I_ref)
    return {"params": p, "raices": rs, "t_ref": t_ref, "info": info, "sens": sens, "mant": mant, "tabla_int": tabla,
            "I_ref": I_ref, "avisos": avisos, "D": D}


def ejecuciones(p, interpretacion="", out=None):
    out = out or correr(p)
    L = []
    for r in out["raices"]:
        L.append(ejecucion(r, f"t* de referencia = {g(out['t_ref'], 12)} ({'fórmula cuadrática' if out['params']['modelo'] == 'cuadratico' else 'bisección 1e-15'})",
                           {"grafico": "iterativo", "comparar": [r["x"]], "raiz": r["x"], "motivo": r["motivo_parada"]},
                           {"orden_observado": r["extra"].get("orden"), "sensibilidad": out["sens"], "mantenimiento": out["mant"]},
                           interpretacion))
    if out["tabla_int"]:
        for nombre in ("Trapecio compuesto", "Simpson 1/3 compuesto", "Romberg"):
            hist = [{"numero": f["k"], "aproximacion": f[nombre]["valor"], "residual": None,
                     "error_abs": f[nombre]["error_abs"], "error_rel": f[nombre]["error_rel"]} for f in out["tabla_int"]]
            res = {"metodo": nombre, "tolerancia": None, "max_iter": None, "convergio": True, "tiempo_ms": None, "historial": hist}
            L.append(ejecucion(res, f"∫D'(t)dt = D(t*) − D(0) = {g(out['I_ref'], 10)}",
                               {"grafico": "refinamiento", "comparar": [hist[-1]["aproximacion"]]}, {}, interpretacion))
    return L


def conclusion_numerica(out):
    p, L = out["params"], []
    L.append(f"Referencia t* = {g(out['t_ref'], 10)} días ({'fórmula cuadrática estable' if p['modelo'] == 'cuadratico' else 'bisección con tolerancia 1e-15'}).")
    for r in out["raices"]:
        if r["convergio"]:
            L.append(f"{r['metodo']}: {r['iteraciones']} iteraciones, error final {g(r['historial'][-1]['error_abs'], 3)}, residual |D−D_u| = "
                     f"{g(r['historial'][-1]['residual'], 3)}, orden observado ≈ {g(r['extra'].get('orden'), 3)}.")
        else:
            L.append(f"{r['metodo']}: NO convergió — {r['motivo_parada']}.")
    if out["info"].get("discriminante") is not None and abs(out["info"]["discriminante"]) < 1e-6:
        L.append(f"Discriminante ≈ {out['info']['discriminante']:.1e}: raíz casi doble. El residuo puede ser diminuto con un error de t* mucho mayor; "
                 "Newton y la secante pierden velocidad (orden → 1). Es mal condicionamiento de la raíz, no falta de convergencia.")
    if out["tabla_int"]:
        u = out["tabla_int"][-1]
        L.append(f"Integración de la tasa (n = {u['n']}): error trapecio {u['Trapecio compuesto']['error_abs']:.1e}, Simpson "
                 f"{u['Simpson 1/3 compuesto']['error_abs']:.1e}, Romberg {u['Romberg']['error_abs']:.1e}."
                 + (" La tasa α+2βt es lineal, por eso los tres métodos son exactos salvo redondeo." if p["modelo"] == "cuadratico" else ""))
    return "\n".join(f"- {x}" for x in L)


def conclusion_problema(out):
    p, L = out["params"], []
    if out["t_ref"] is not None:
        L.append(f"Con estos parámetros hipotéticos el indicador alcanzaría el umbral de inspección a los {g(out['t_ref'], 5)} días.")
    if out["mant"]:
        m = out["mant"]
        L.append(f"Mantenimiento programado en el día {m['t_mant_programado']:g} con retraso de {m['retraso']:g} días → efectivo en el día {m['t_efectivo']:g}. "
                 + (f"El umbral se alcanzaría {abs(m['margen']):.1f} días ANTES del mantenimiento: el retraso volvería insuficiente el plan." if m["antes"]
                    else f"Hay un margen de {m['margen']:.1f} días antes de alcanzar el umbral."))
    cond = [s for s in out["sens"] if s["amplificación"] is not None]
    if cond:
        mx = max(cond, key=lambda s: abs(s["amplificación"]))
        L.append(f"Parámetro más influyente: {mx['parámetro']} (un cambio relativo de 1 en el parámetro mueve t* en {mx['amplificación']:.2f} veces su valor relativo).")
    sin_raiz = [s["parámetro"] for s in out["sens"] if s["amplificación"] is None]
    if sin_raiz:
        L.append("Al perturbar " + ", ".join(sin_raiz) + " la raíz desaparece o aparece: el resultado es cualitativamente inestable ante pequeñas "
                 "incertidumbres. En un caso real esto exigiría una cota de seguridad amplia.")
    L.append("Qué NO puede inferirse: el indicador D y sus parámetros son hipotéticos; el modelo cuadrático no representa desgaste real ni "
             "la condición de equipos de Mi Teleférico, y no sustituye una inspección.")
    return "\n".join(f"- {x}" for x in L)
