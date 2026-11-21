import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import m4_sensores as M
from core.casos import CASOS
from core.comun import g
from core.funciones import AYUDA
from core.ui import AVISO, banner_bd
from core.ui_comun import Entrada, ejecutar, interpretacion_y_guardado, mostrar_raices

C = CASOS["sensores"]
st.title(f"{C['icono']} {C['nombre']}")
st.caption(AVISO)
engine = banner_bd()
tab_m, tab_r, tab_i = st.tabs(["1 · Datos y parámetros", "2 · Resultados", "3 · Interpretación"])

with tab_m:
    st.markdown(f"**Pregunta:** {C['pregunta']}")
    st.latex(C["modelo"])
    st.markdown(f"**Variables y unidades:** {C['variables']}  \n**Referencia:** {C['analitico']}")
    tipo = st.radio("Escenario (valores iniciales; todo es editable)", ["NORMAL", "ESTRÉS", "MAL_CONDICIONADO"],
                    horizontal=True, format_func=lambda t: t.replace("_", " "))
    st.info(M.DESCRIPCION[tipo])
    E = Entrada(M.PRESETS[tipo], tipo, "m4")
    P = {}
    P["fuente"] = E.sel("Origen de los datos", "fuente", ["sintetica", "propios"], horizontal=True,
                        fmt=lambda s: "Sintéticos (los genera la app)" if s == "sintetica" else "Datos propios (pegar t, y)")
    if P["fuente"] == "sintetica":
        c = st.columns(4)
        with c[0]: P["func"] = E.t("y(t) verdadera — variable t", "func", help=AYUDA + " Ej.: sin(t), exp(-t), sin(t)+0.3*cos(3*t)")
        with c[1]: P["a"] = E.f("Intervalo: a", "a")
        with c[2]: P["b"] = E.f("Intervalo: b", "b")
        with c[3]: P["n"] = E.i("Número de nodos n (5 a 60)", "n", 5, 60)
        c = st.columns(3)
        with c[0]: P["nodos"] = E.sel("Distribución de nodos", "nodos", ["equiespaciados", "chebyshev", "personalizados"])
        with c[1]: P["sigma"] = E.f("Ruido gaussiano σ", "sigma")
        with c[2]: P["semilla"] = E.i("Semilla del ruido (reproducible)", "semilla", 0, 10**6)
        P["nodos_txt"] = E.t("Nodos t personalizados (separados por comas)", "nodos_txt") if P["nodos"] == "personalizados" else ""
        P["datos_txt"] = ""
    else:
        P["datos_txt"] = E.t("Datos: un par «t y» por línea (separa con espacio, coma o ;)", "datos_txt", area=True, height=180,
                             help="Ej.:\n0 0.0\n1 0.84\n2 0.91 ...")
        P.update(func="sin(t)", a=0.0, b=1.0, n=10, nodos="equiespaciados", nodos_txt="", sigma=0.0, semilla=0)
    P["ocultos"] = E.t("Índices de los puntos a ocultar (desde 0, separados por comas)", "ocultos",
                       help="Se retiran del conjunto y se reconstruyen; el error se mide ahí.")
    c = st.columns(4)
    with c[0]: P["umbral"] = E.t("Umbral para cruce (opcional)", "umbral", help="Valor y* para hallar t con S(t)=y* por raíces.")
    with c[1]: P["tol"] = E.f("Tolerancia de raíces", "tol", positivo=True)
    with c[2]: P["max_iter"] = E.i("Máx. iteraciones", "max_iter", 1, 1000)
    with c[3]: P["eps_sens"] = E.f("Perturbación de datos (estabilidad)", "eps_sens", positivo=True)
    P["n_graf"] = 200
    for e in E.errores:
        st.error(e)
    # vista previa de los datos
    if not E.errores:
        try:
            _t, _y, _yv, _ = M._datos({**M.BASE, **P})
            idx = M._lista_ints(P["ocultos"])
            with st.expander(f"Vista previa de los {len(_t)} puntos (ocultos: {idx})"):
                st.dataframe(pd.DataFrame({"índice": range(len(_t)), "t": _t, "y medido": _y,
                                           **({"y verdadera": _yv} if _yv is not None else {}),
                                           "oculto": [i in idx for i in range(len(_t))]}), width="stretch", hide_index=True)
        except Exception as e:
            st.warning(f"Datos aún inválidos: {e}")
        ejecutar("m4", tipo, P, M)

S = st.session_state.get("m4")

with tab_r:
    if not S:
        st.info("Ejecuta una simulación en la pestaña 1.")
    else:
        o, p, d = S["out"], S["out"]["params"], S["out"]["diag"]
        st.markdown(f"#### Escenario **{S['tipo'].replace('_', ' ')}** · error medido contra: {o['ref_txt']}")
        for a in o["avisos"]:
            st.warning(a)
        m = st.columns(5)
        m[0].metric("Nodos conocidos", d["n_conocidos"])
        m[1].metric("Grado del polinomio", d["grado"])
        m[2].metric("κ(Vandermonde)", g(d["cond_vandermonde"], 3))
        m[3].metric("Λ (Lebesgue) tus nodos", g(d["lebesgue"], 3))
        m[4].metric("Λ con Chebyshev", g(d.get("lebesgue_chebyshev"), 3))
        s1, s2, s3 = st.tabs(["Curvas y reconstrucción", "Errores y estabilidad ante ruido", "Cruce de umbral"])
        with s1:
            fig = go.Figure()
            if o["yg_ver"] is not None:
                fig.add_scatter(x=o["tg"], y=o["yg_ver"], mode="lines", name="y(t) verdadera", line=dict(width=4, color="gray"))
            for r in o["res"]:
                fig.add_scatter(x=o["tg"], y=r["yg"], mode="lines", name=r["metodo"], line=dict(dash="dash"))
            fig.add_scatter(x=o["tk"], y=o["yk"], mode="markers", name="Nodos conocidos", marker=dict(size=8, color="black"))
            fig.add_scatter(x=o["th"], y=o["ref_h"], mode="markers", name="Puntos ocultos (referencia)",
                            marker=dict(size=13, symbol="x", color="red"))
            ys = np.concatenate([o["yk"], o["ref_h"]])
            rango = float(np.ptp(ys)) or 1.0
            fig.update_yaxes(range=[ys.min() - 1.5 * rango, ys.max() + 1.5 * rango])
            fig.update_layout(title="Curvas superpuestas (eje y acotado: las oscilaciones de Runge pueden salirse)", height=440,
                              xaxis_title="t", yaxis_title="y", legend=dict(orientation="h", y=-0.25), margin=dict(t=50, b=40))
            st.plotly_chart(fig, width="stretch", key="m4_curvas")
            if o["tabla_dd"] is not None:
                with st.expander("Tabla de diferencias divididas (Newton)"):
                    st.dataframe(pd.DataFrame(np.where(np.add.outer(np.arange(len(o["tabla_dd"])), np.arange(len(o["tabla_dd"]))) <= len(o["tabla_dd"]) - 1, o["tabla_dd"], np.nan)).style.format("{:.6g}", na_rep=""))
        with s2:
            tabla = pd.DataFrame([{"Método": r["metodo"], "Error máx (ocultos)": r["err_max"], "Error RMS (ocultos)": r["err_rms"],
                                   "Error máx (curva completa)": r["err_curva"], "Amplificación del ruido (curva)": r["amp_curva"],
                                   "Tiempo (ms)": round(r["tiempo_ms"], 3)} for r in o["res"]])
            st.dataframe(tabla.style.format({"Error máx (ocultos)": "{:.3e}", "Error RMS (ocultos)": "{:.3e}", "Error máx (curva completa)": "{:.3e}",
                                             "Amplificación del ruido (curva)": "{:.2f}"}, na_rep="—"), width="stretch", hide_index=True)
            st.caption(f"Lagrange vs Newton difieren en {o['dif_lag_newton']:.1e} (mismo polinomio, distinto redondeo). "
                       f"Amplificación = (máx cambio de la curva) / (máx perturbación {o['dmax']:.1e} de los datos); está acotada por Λ para polinomios.")
            c1, c2 = st.columns(2)
            fb = go.Figure()
            for r in o["res"]:
                fb.add_bar(x=[f"t={t:.3g}" for t in o["th"]], y=np.maximum(r["err_h"], 1e-20), name=r["metodo"])
            fb.update_yaxes(type="log", title="Error absoluto")
            fb.update_layout(title="Error en cada punto ocultado", barmode="group", height=380, margin=dict(t=50, b=40),
                             legend=dict(orientation="h", y=-0.3))
            c1.plotly_chart(fb, width="stretch", key="m4_err")
            fa = go.Figure(go.Bar(x=[r["metodo"] for r in o["res"]], y=[r["amp_curva"] for r in o["res"]]))
            fa.update_yaxes(type="log", title="Amplificación observada")
            fa.update_layout(title="Estabilidad ante ruido en los datos", height=380, margin=dict(t=50, b=40))
            c2.plotly_chart(fa, width="stretch", key="m4_amp")
            if p["fuente"] == "sintetica" and st.button("Comparar con nodos de Chebyshev (mismos n y mismos índices)"):
                try:
                    oc = M.correr({**p, "nodos": "chebyshev"})
                    st.dataframe(pd.DataFrame([{"Método": a["metodo"], "Error máx ocultos (tus nodos)": a["err_max"],
                                                "Error máx ocultos (Chebyshev)": b["err_max"], "Error curva (tus nodos)": a["err_curva"],
                                                "Error curva (Chebyshev)": b["err_curva"], "Amplificación (tus nodos)": a["amp_curva"],
                                                "Amplificación (Chebyshev)": b["amp_curva"]} for a, b in zip(o["res"], oc["res"])]
                                              ).style.format(precision=4, na_rep="—"), width="stretch", hide_index=True)
                except Exception as e:
                    st.error(str(e))
        with s3:
            c = o["cruce"]
            if c is None:
                st.info("Escribe un umbral en la pestaña 1 para hallar el instante en que la curva interpolada lo cruza.")
            elif not c["res"]:
                st.warning(f"La curva (spline) no cruza el umbral {c['umbral']:g} dentro del intervalo.")
            else:
                st.caption(f"S(t) = {c['umbral']:g} sobre el spline; intervalo inicial {c['bracket'][0]:.4g}–{c['bracket'][1]:.4g}; "
                           f"referencia: {g(c['ref'], 12)} (bisección 1e-15 sobre la función verdadera).")
                mostrar_raices(c["res"], "m4r")

with tab_i:
    if not S:
        st.info("Ejecuta una simulación primero.")
    else:
        interpretacion_y_guardado(engine, C["nombre"], S, M, "Sintético con ruido gaussiano (semilla fija) o datos ingresados por el usuario")
