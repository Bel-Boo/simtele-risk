"""Resumen en lenguaje simple de cada módulo (a partir de los resultados de los motores). Sin Streamlit."""
import numpy as np

from .comun import g


def _plural(n, s, p):
    return s if n == 1 else p


def m1(o):
    p, L, V = o["params"], [], []
    if o["td_ref"] is not None:
        L.append(f"🛑 La cabina se detiene a los **{g(o['td_ref'], 4)} s** de empezar a frenar y recorre **{g(o['I_ref'], 4)} m** durante el frenado.")
    L.append(f"⏱️ Antes de frenar avanza **{o['d_reac']:.2f} m** por el tiempo de reacción ({p['t_reaccion']:g} s). Distancia total para detenerse: **{o['d_total']:.2f} m**.")
    if o["margen"] is not None:
        V.append(("ok", f"✅ SÍ alcanza a detenerse: sobran {o['margen']:.2f} m de los {p['d_disp']:g} m disponibles.") if o["margen"] >= 0
                 else ("bad", f"❌ NO alcanza a detenerse: se pasa por {abs(o['margen']):.2f} m de los {p['d_disp']:g} m disponibles."))
    r2, r4 = o["edo"]
    esc = max(1e-9, float(np.nanmax(np.abs(o["Yref"][:, 0]))))
    if not r4["convergio"]:
        V.append(("bad", "❌ La simulación se descontroló. Aumenta el número de pasos N (opciones avanzadas)."))
    elif r4["err_max"] / esc < 1e-3:
        V.append(("ok", f"✅ El cálculo es confiable: el método preciso (RK4) se equivoca como máximo {r4['err_max']:.1e} m."))
    else:
        V.append(("warn", f"⚠️ El cálculo tiene un error de hasta {r4['err_max']:.2g} m. Prueba con más pasos N para mejorarlo."))
    if r2["err_max"] > 10 * r4["err_max"] and r2["err_max"] > 1e-9:
        L.append(f"🔬 El método simple (RK2) se equivoca hasta {r2['err_max']:.2g} m; el preciso (RK4), {r4['err_max']:.2g} m.")
    if any("NO APLICABLE" in r["motivo_parada"] for r in o["raices"]):
        V.append(("warn", "⚠️ Caso delicado: la velocidad toca el cero sin cruzarlo (raíz doble). La bisección no se puede usar y los otros métodos se vuelven lentos. "
                          "Es una dificultad matemática, no un peligro físico."))
    else:
        malos = [r["metodo"] for r in o["raices"] if not r["convergio"]]
        if malos:
            V.append(("warn", "⚠️ No llegaron a la precisión pedida: " + ", ".join(malos) + "."))
    s = {x["parámetro"]: x for x in o["sens"]}
    if "v0" in s:
        L.append(f"📈 Si la velocidad inicial aumenta {p['eps_sens'] * 100:g}%, la distancia de frenado aumenta **{s['v0']['Δrel d_frenado'] * 100:.2f}%**.")
    return {"lineas": L, "veredictos": V}


def m2r(o):
    p, L, V = o["params"], [], []
    if o["t_ref"] is not None:
        L.append(f"📅 Con estos datos el indicador llega al umbral de inspección a los **{g(o['t_ref'], 5)} días**.")
    if o["mant"]:
        m = o["mant"]
        L.append(f"🔧 Mantenimiento previsto el día {m['t_mant_programado']:g}" + (f", retrasado {m['retraso']:g} días (queda el día {m['t_efectivo']:g})" if m["retraso"] else "") + ".")
        V.append(("bad", f"❌ El umbral se alcanzaría {abs(m['margen']):.1f} días ANTES del mantenimiento.") if m["antes"]
                 else ("ok", f"✅ El mantenimiento llega a tiempo: hay {m['margen']:.1f} días de margen."))
    ok = [r for r in o["raices"] if r["convergio"]]
    if len(ok) == 3:
        V.append(("ok", "✅ Los tres métodos (bisección, Newton y secante) encontraron la misma respuesta."))
    else:
        malos = [f"{r['metodo']} ({r['motivo_parada'].split(':')[0]})" for r in o["raices"] if not r["convergio"]]
        V.append(("warn", "⚠️ Algún método no llegó a la respuesta: " + "; ".join(malos) + ". Revisa el intervalo y los puntos de partida en las opciones avanzadas."))
    if any(s["amplificación"] is None for s in o["sens"]):
        V.append(("warn", "⚠️ Resultado muy sensible: un cambio minúsculo en algún dato hace que la solución desaparezca o aparezca. "
                          "En la práctica habría que dejar un margen de seguridad amplio."))
    elif o["sens"]:
        mx = max(abs(s["amplificación"]) for s in o["sens"])
        L.append(f"📈 Sensibilidad: un cambio de 1% en un dato mueve la fecha del umbral como máximo {mx:.2f}%.")
    return {"lineas": L, "veredictos": V}


def m2l(out, tipo):
    d, res, s = out["diag"], out["res"], out["sens"]
    L = [f"🧮 Se resolvió un sistema de **{d['n']} ecuaciones** con 5 métodos y se comparó con la respuesta exacta conocida."]
    k = d["kappa"]
    nivel = "bien condicionado (poco sensible)" if k < 1e3 else "algo sensible" if k < 1e8 else "MUY sensible (mal condicionado)"
    L.append(f"📐 κ(A) = {k:.2e}: el sistema es {nivel}.")
    it = [r for r in res if r["tolerancia"] is not None]
    ok = [r["metodo"] for r in it if r["convergio"]]
    mal = [r["metodo"] for r in it if not r["convergio"]]
    V = []
    if not mal:
        V.append(("ok", "✅ Todos los métodos iterativos llegaron a la precisión pedida."))
    else:
        V.append(("warn", "⚠️ No llegaron a la precisión: " + ", ".join(mal) + " (se descontrolaron o necesitan más iteraciones)."))
    ref = res[0]["historial"][-1]
    if k > 1e6:
        V.append(("warn", f"⚠️ Ojo: el residuo es pequeño ({ref['residual']:.1e}) pero el error es {ref['error_abs']:.1e}. En sistemas muy sensibles el residuo engaña."))
    if not d["spd"]:
        V.append(("warn", "⚠️ La matriz no es simétrica definida positiva: el gradiente conjugado no tiene garantía de funcionar."))
    return {"lineas": L, "veredictos": V}


def m3(o):
    p, mo, L, V = o["params"], o["modal"], [], []
    if mo["wd"]:
        L.append(f"🌬️ La cabina **oscila** unas {mo['wd'] / (2 * np.pi):.3g} veces por segundo (ω_d = {mo['wd']:.3g} rad/s) y tarda en calmarse según el amortiguamiento (ζ = {mo['zeta']:.3g}).")
    else:
        L.append(f"🌬️ Con este amortiguamiento (ζ = {mo['zeta']:.3g} ≥ 1) la cabina **no oscila**: vuelve al reposo sin balancearse.")
    L.append(f"↔️ Se aleja como máximo **{o['amp_ref']:.3g} m** de su posición de reposo.")
    if p["F_expr"].strip() not in ("0", "0.0", ""):
        L.append("💨 Hay una fuerza de viento: si su frecuencia se acerca a la natural de la cabina, el movimiento se amplifica (resonancia).")
    r2, r4 = o["edo"]
    esc = max(1e-9, o["amp_ref"])
    if not r4["convergio"]:
        V.append(("bad", "❌ La simulación se descontroló. Aumenta el número de pasos N."))
    elif r4["err_max"] / esc < 1e-3:
        V.append(("ok", f"✅ El cálculo es confiable: el método preciso (RK4) se equivoca como máximo {r4['err_max']:.1e} m."))
    else:
        V.append(("warn", f"⚠️ El error del cálculo llega a {r4['err_max']:.2g} m. Prueba con más pasos N."))
    if r2["err_max"] > 10 * r4["err_max"] and r2["err_max"] / esc > 5e-2:
        V.append(("warn", f"⚠️ El método simple (RK2) se equivoca bastante ({r2['err_max']:.2g} m) con este paso; RK4 es mucho mejor."))
    c = next((s for s in o["sens"] if s["parámetro"] == "c" and "amplif. ω_d" in s), None)
    if c and abs(c["amplif. ω_d"]) > 20:
        V.append(("warn", f"⚠️ Caso delicado: un cambio pequeño del amortiguamiento cambia mucho la frecuencia de oscilación (amplificación {abs(c['amplif. ω_d']):.0f}×). Es sensibilidad matemática, no peligro."))
    return {"lineas": L, "veredictos": V}


def m4(o):
    p, d, L, V = o["params"], o["diag"], [], []
    mejor = min(o["res"], key=lambda r: r["err_max"])
    L.append(f"📡 Se ocultaron **{len(o['th'])} datos** y se reconstruyeron con los {d['n_conocidos']} datos conocidos.")
    L.append(f"🏆 El método que menos se equivocó fue **{mejor['metodo']}**, con un error máximo de {mejor['err_max']:.2g} (en las unidades de la señal).")
    pol, spl = o["res"][0], o["res"][2]
    if pol["amp_curva"] > 20:
        V.append(("warn", f"⚠️ Los polinomios (Lagrange/Newton) son inestables con tantos nodos: amplifican el ruido {pol['amp_curva']:.0f} veces (el spline, {spl['amp_curva']:.1f}). "
                          "Usa menos nodos, nodos de Chebyshev o el spline."))
    else:
        V.append(("ok", f"✅ La reconstrucción es estable: el ruido se amplifica poco (polinomio {pol['amp_curva']:.1f}×, spline {spl['amp_curva']:.1f}×)."))
    if p.get("sigma", 0) > 0 and p["fuente"] == "sintetica":
        L.append(f"🔊 Los datos tienen ruido (σ = {p['sigma']:g}): las curvas pasan por cada dato, ruido incluido.")
    for a in o["avisos"]:
        V.append(("warn", "⚠️ " + a))
    return {"lineas": L, "veredictos": V}
