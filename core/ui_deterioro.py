"""Módulo 2 · subexperimento de raíces (interfaz)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import m2_raices as M
from .casos import CASOS
from .comun import fig_refinamiento, g
from .funciones import AYUDA
from .ui_comun import Entrada, ejecutar, interpretacion_y_guardado, mostrar_raices, mostrar_refinamiento

C = CASOS["deterioro"]


def render_raices(engine):
    tab_m, tab_r, tab_i = st.tabs(["1 · Modelo y parámetros", "2 · Resultados", "3 · Interpretación"])
    with tab_m:
        st.markdown(f"**Pregunta:** {C['pregunta']}")
        st.latex(C["modelo"])
        st.markdown("**Referencia analítica:** resolver βt²+αt+(D0−D_umbral)=0 y elegir la raíz físicamente admisible "
                    "(la menor t ≥ 0). Variables: D [adimensional], α [1/día], β [1/día²], t [días].")
        tipo = st.radio("Escenario (valores iniciales; todo es editable)", ["NORMAL", "ESTRÉS", "MAL_CONDICIONADO"],
                        horizontal=True, format_func=lambda t: t.replace("_", " "), key="m2r_tipo")
        st.info(M.DESCRIPCION[tipo])
        E = Entrada(M.PRESETS[tipo], tipo, "m2r")
        P = {"submodulo": "raices"}
        P["modelo"] = E.sel("Modelo de deterioro", "modelo", ["cuadratico", "personalizado"], horizontal=True,
                            fmt=lambda m: "Cuadrático D0+αt+βt²" if m == "cuadratico" else "Personalizado D(t) — la escribes tú")
        if P["modelo"] == "cuadratico":
            c = st.columns(4)
            with c[0]: P["D0"] = E.f("D0", "D0")
            with c[1]: P["alpha"] = E.f("α [1/día]", "alpha")
            with c[2]: P["beta"] = E.f("β [1/día²]", "beta")
            with c[3]: P["D_umbral"] = E.f("Umbral de inspección D_umbral", "D_umbral")
            P.update(expr_D=M.BASE["expr_D"], expr_dD="")
        else:
            c = st.columns(3)
            with c[0]: P["expr_D"] = E.t("D(t) — variable t", "expr_D", help=AYUDA + " Ej.: 10+0.05*t+0.0002*t**2, 5*exp(0.01*t), 12+3*sin(0.02*t)+0.01*t")
            with c[1]: P["expr_dD"] = E.t("D'(t) (opcional; si no, derivada numérica)", "expr_dD")
            with c[2]: P["D_umbral"] = E.f("Umbral de inspección D_umbral", "D_umbral")
            P.update(D0=M.BASE["D0"], alpha=M.BASE["alpha"], beta=M.BASE["beta"])
        st.markdown("##### Métodos de raíces")
        c = st.columns(5)
        with c[0]: P["a"] = E.f("Bisección: a [día]", "a")
        with c[1]: P["b"] = E.f("Bisección: b [día]", "b")
        with c[2]: P["x0_newton"] = E.f("Newton: x0", "x0_newton")
        with c[3]: P["x0_sec"] = E.f("Secante: x0", "x0_sec")
        with c[4]: P["x1_sec"] = E.f("Secante: x1", "x1_sec")
        c = st.columns(2)
        with c[0]: P["tol"] = E.f("Tolerancia (|x_k − x_{k−1}| < tol)", "tol", positivo=True)
        with c[1]: P["max_iter"] = E.i("Máx. iteraciones", "max_iter", 1, 1000)
        st.markdown("##### Mantenimiento, sensibilidad e integración de la tasa")
        c = st.columns(4)
        with c[0]: P["t_mant"] = E.f("Mantenimiento programado [día] (0 = ninguno)", "t_mant")
        with c[1]: P["retraso"] = E.f("Retraso hipotético [días]", "retraso")
        with c[2]: P["eps_sens"] = E.f("Perturbación relativa (sensibilidad)", "eps_sens", positivo=True)
        with c[3]: P["kint"] = E.slider("Refinamientos: n = 2, 4, …, 2^k", "kint", 2, 12)
        P["integrar_tasa"] = st.checkbox("Integrar la tasa D'(t) en [0, t*] (trapecio, Simpson, Romberg)", value=True, key=f"m2r_int_{tipo}")
        for e in E.errores:
            st.error(e)
        if not E.errores:
            ejecutar("m2r", tipo, P, M)

    S = st.session_state.get("m2r")
    with tab_r:
        if not S:
            st.info("Ejecuta una simulación en la pestaña 1.")
            return_ = True
        else:
            o, p = S["out"], S["out"]["params"]
            st.markdown(f"#### Escenario **{S['tipo'].replace('_', ' ')}**")
            for a in o["avisos"]:
                st.warning(a)
            m = st.columns(4)
            m[0].metric("t* de referencia [días]", g(o["t_ref"], 8))
            info = o["info"]
            m[1].metric("Discriminante", g(info.get("discriminante"), 4))
            m[2].metric("Máx. de D (si β<0)", g(info.get("D_max"), 6))
            if o["mant"]:
                m[3].metric("Margen vs mantenimiento [días]", g(o["mant"]["margen"], 5),
                            delta="umbral ANTES del mantenimiento" if o["mant"]["antes"] else "hay margen",
                            delta_color="inverse" if o["mant"]["antes"] else "normal")
            s1, s2, s3 = st.tabs(["Raíces", "Sensibilidad y mantenimiento", "Integración de la tasa"])
            with s1:
                top = max(p["b"], (o["mant"] or {}).get("t_efectivo", 0), (o["t_ref"] or 0) * 1.3)
                tt = np.linspace(0, top, 600)
                fig = go.Figure()
                fig.add_scatter(x=tt, y=o["D"](tt), mode="lines", name="D(t)")
                fig.add_hline(y=p["D_umbral"], line_dash="dot", annotation_text="umbral")
                if o["t_ref"] is not None:
                    fig.add_vline(x=o["t_ref"], line_dash="dash", annotation_text="t*")
                if o["mant"]:
                    fig.add_vline(x=o["mant"]["t_efectivo"], line_color="gray", annotation_text="mantenimiento")
                fig.update_layout(title="Indicador de deterioro D(t)", xaxis_title="t [días]", yaxis_title="D", height=360, margin=dict(t=50, b=40))
                st.plotly_chart(fig, width="stretch", key="m2r_D")
                mostrar_raices(o["raices"], "m2r")
            with s2:
                filas = [{"Parámetro": s["parámetro"], "t*(+ε)": s["t*(+ε)"], "t*(−ε)": s["t*(−ε)"],
                          "Amplificación": s["amplificación"] if s["amplificación"] is not None else "sin raíz (se pierde o aparece)"} for s in o["sens"]]
                st.markdown(f"**Sensibilidad de t*** a una perturbación relativa ε = {p['eps_sens']:g} (diferencias centrales)")
                st.dataframe(pd.DataFrame(filas).style.format({"t*(+ε)": "{:.8g}", "t*(−ε)": "{:.8g}"}, na_rep="no existe"), width="stretch", hide_index=True)
                if o["mant"]:
                    st.markdown("**Mantenimiento hipotéticamente retrasado**")
                    st.dataframe(pd.DataFrame([o["mant"]]).style.format(precision=5), width="stretch", hide_index=True)
            with s3:
                if o["tabla_int"]:
                    st.caption(f"∫₀^t* D'(t) dt = D(t*) − D(0) = {g(o['I_ref'], 12)} (teorema fundamental del cálculo).")
                    mostrar_refinamiento(o["tabla_int"])
                    st.plotly_chart(fig_refinamiento(o["tabla_int"]), width="stretch", key="m2r_ref")
                else:
                    st.info("Activa «Integrar la tasa» y asegúrate de que exista t*.")
    with tab_i:
        if not S:
            st.info("Ejecuta una simulación primero.")
        else:
            interpretacion_y_guardado(engine, "Deterioro y mantenimiento (raíces)".split(" (")[0], S, M, "Sintético: parámetros ingresados por el usuario; referencia por fórmula cuadrática o bisección 1e-15")
