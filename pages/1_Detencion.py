import numpy as np
import pandas as pd
import streamlit as st

from core import m1_detencion as M
from core.casos import CASOS
from core.comun import (fig_convergencia_paso, fig_errores_tiempo, fig_refinamiento, fig_trayectorias, g)
from core.edo import VARIANTES_RK2
from core.funciones import AYUDA
from core.ui import AVISO, banner_bd
from core.ui_comun import (Entrada, df_refinamiento, ejecutar, interpretacion_y_guardado, mostrar_raices,
                           mostrar_refinamiento)

C = CASOS["detencion"]
st.title(f"{C['icono']} {C['nombre']}")
st.caption(AVISO)
engine = banner_bd()
tab_m, tab_r, tab_i = st.tabs(["1 · Modelo y parámetros", "2 · Resultados", "3 · Interpretación"])

with tab_m:
    st.markdown(f"**Pregunta:** {C['pregunta']}")
    st.latex(C["modelo"])
    st.markdown(f"**Variables y unidades:** {C['variables']}  \n**Referencia analítica:** {C['analitico']}")
    tipo = st.radio("Escenario (valores iniciales; todo es editable)", ["NORMAL", "ESTRÉS", "MAL_CONDICIONADO"],
                    horizontal=True, format_func=lambda t: t.replace("_", " "))
    st.info(M.DESCRIPCION[tipo])
    E = Entrada(M.PRESETS[tipo], tipo, "m1")
    P = {}
    st.markdown("##### Condiciones iniciales y restricciones")
    c = st.columns(4)
    with c[0]: P["v0"] = E.f("Velocidad inicial v0 [m/s]", "v0", positivo=True)
    with c[1]: P["x0"] = E.f("Posición inicial x0 [m]", "x0")
    with c[2]: P["t_reaccion"] = E.f("Tiempo de reacción [s]", "t_reaccion", help="Distancia de reacción = v0·t_reacción (antes de frenar).")
    with c[3]: P["d_disp"] = E.f("Distancia disponible [m] (0 = sin límite)", "d_disp")
    st.markdown("##### Modelo de frenado")
    P["modelo"] = E.sel("Desaceleración", "modelo", ["constante", "personalizada"],
                        fmt=lambda m: "Constante a" if m == "constante" else "Personalizada a(v, t) — la escribes tú", horizontal=True)
    if P["modelo"] == "constante":
        P["a"] = E.f("Desaceleración a [m/s²]", "a", positivo=True)
        P.update(expr_a=M.BASE["expr_a"], v_exacta="", x_exacta="", dv_exacta="", t_det_ref=0.0)
    else:
        P["a"] = M.BASE["a"]
        P["expr_a"] = E.t("a(v, t) [m/s²] — variables: v, t", "expr_a", help=AYUDA + " Ej.: 0.5+0.3*v, 1+0.1*t, 2*sqrt(abs(v)/5)")
        with st.expander("Solución analítica (opcional, recomendada): permite medir errores reales", expanded=bool(M.PRESETS[tipo]["v_exacta"])):
            st.caption("Ingresa v(t) y x(t) exactas (variable t). Si las dejas vacías, la referencia será RK4 con paso mucho menor.")
            P["v_exacta"] = E.t("v(t) exacta", "v_exacta")
            P["x_exacta"] = E.t("x(t) exacta", "x_exacta")
            P["dv_exacta"] = E.t("v'(t) exacta (opcional; si no, derivada numérica)", "dv_exacta")
            P["t_det_ref"] = E.f("t_det de referencia (0 = calcular automáticamente)", "t_det_ref")
    st.markdown("##### Simulación (EDO)")
    c = st.columns(3)
    with c[0]: P["tf"] = E.f("Tiempo final tf [s]", "tf", positivo=True)
    with c[1]: P["N"] = E.i("Número de pasos N (h = tf/N)", "N", 2, 2000)
    with c[2]: P["rk2"] = E.sel("Variante de RK2", "rk2", list(VARIANTES_RK2), fmt=lambda k: VARIANTES_RK2[k][0])
    st.markdown("##### Raíces de v(t) = 0")
    c = st.columns(4)
    with c[0]: P["bis_a"] = E.f("Bisección: a", "bis_a")
    with c[1]: P["bis_b"] = E.f("Bisección: b", "bis_b")
    with c[2]: P["x0_newton"] = E.f("Newton: x0", "x0_newton")
    with c[3]:
        P["x0_sec"] = E.f("Secante: x0", "x0_sec")
        P["x1_sec"] = E.f("Secante: x1", "x1_sec")
    c = st.columns(2)
    with c[0]: P["tol"] = E.f("Tolerancia (|x_k − x_{k−1}| < tol)", "tol", positivo=True)
    with c[1]: P["max_iter"] = E.i("Máx. iteraciones", "max_iter", 1, 1000)
    st.markdown("##### Integración de v(t) en [0, t_det] y sensibilidad")
    c = st.columns(3)
    with c[0]: P["kint"] = E.slider("Refinamientos: n = 2, 4, …, 2^k", "kint", 2, 12)
    with c[1]: P["sobre"] = E.sel("Integrar sobre", "sobre", ["referencia", "rk4"],
                                  fmt=lambda s: "v(t) de referencia" if s == "referencia" else "trayectoria RK4", horizontal=True)
    with c[2]: P["eps_sens"] = E.f("Perturbación relativa (sensibilidad)", "eps_sens", positivo=True)
    for e in E.errores:
        st.error(e)
    if not E.errores:
        ejecutar("m1", tipo, P, M)

S = st.session_state.get("m1")

with tab_r:
    if not S:
        st.info("Ejecuta una simulación en la pestaña 1.")
    else:
        o, p = S["out"], S["out"]["params"]
        st.markdown(f"#### Escenario **{S['tipo'].replace('_', ' ')}** · referencia {o['tipo_ref']}"
                    + (f" (error estimado ≈ {o['err_ref']:.1e})" if o["err_ref"] else ""))
        for a in o["avisos"]:
            st.warning(a)
        m = st.columns(5)
        m[0].metric("t_det [s]", g(o["td_ref"], 6))
        m[1].metric("Dist. frenado [m]", g(o["I_ref"], 6))
        m[2].metric("Dist. reacción [m]", g(o["d_reac"], 5))
        m[3].metric("Dist. total [m]", g(o["d_total"], 6))
        m[4].metric("Margen [m]", g(o["margen"], 5) if o["margen"] is not None else "sin límite",
                    delta=None if o["margen"] is None else ("alcanza" if o["margen"] >= 0 else "NO alcanza"),
                    delta_color="normal" if (o["margen"] or 0) >= 0 else "inverse")
        s1, s2, s3, s4 = st.tabs(["EDO: RK2 vs RK4", "Integración de v(t)", "Raíces v(t) = 0", "Convergencia y sensibilidad"])
        with s1:
            st.dataframe(pd.DataFrame([{"Método": r["metodo"], "t_det estimado [s]": r["t_det"], "Dist. frenado [m]": r["d_frenado"],
                                        "Error máx": r["err_max"], "Error en tf": r["err_final"], "Tiempo (ms)": round(r["tiempo_ms"], 3),
                                        "Estado": r["motivo_parada"]} for r in o["edo"]]).style.format(
                {"Error máx": "{:.3e}", "Error en tf": "{:.3e}", "t_det estimado [s]": "{:.8g}", "Dist. frenado [m]": "{:.8g}"}, na_rep="—"),
                width="stretch", hide_index=True)
            tt = np.linspace(0, p["tf"], 600)
            c1, c2 = st.columns(2)
            c1.plotly_chart(fig_trayectorias({r["metodo"]: (r["t"], r["Y"][:, 1]) for r in o["edo"]}, "Velocidad v(t)", ylab="v [m/s]",
                                             referencia=(tt, o["vref"](tt))), width="stretch", key="m1_v")
            c2.plotly_chart(fig_trayectorias({r["metodo"]: (r["t"], r["Y"][:, 0]) for r in o["edo"]}, "Posición x(t)", ylab="x [m]",
                                             referencia=(tt, o["xref"](tt))), width="stretch", key="m1_x")
            st.plotly_chart(fig_errores_tiempo({r["metodo"]: (r["t"], r["err"]) for r in o["edo"]}), width="stretch", key="m1_err")
            with st.expander("Tabla temporal (t, x, v, error)"):
                nom = st.selectbox("Método", [r["metodo"] for r in o["edo"]], key="m1_tab")
                r = next(r for r in o["edo"] if r["metodo"] == nom)
                st.dataframe(pd.DataFrame({"t": r["t"], "x": r["Y"][:, 0], "v": r["Y"][:, 1], "x_ref": o["Yref"][:, 0],
                                           "v_ref": o["Yref"][:, 1], "error": r["err"]}), width="stretch", hide_index=True)
        with s2:
            st.caption(f"∫₀^{g(o['T_int'], 6)} v dt = distancia de frenado. Referencia: {g(o['I_ref'], 12)} m.")
            mostrar_refinamiento(o["tabla_int"], o["R"])
            st.plotly_chart(fig_refinamiento(o["tabla_int"]), width="stretch", key="m1_ref")
        with s3:
            mostrar_raices(o["raices"], "m1r")
        with s4:
            c1, c2 = st.columns(2)
            e = pd.DataFrame(o["estudio"])
            c1.plotly_chart(fig_convergencia_paso(o["estudio"]), width="stretch", key="m1_conv")
            with c2:
                st.dataframe(e.style.format({"h": "{:.4g}", "rk2": "{:.3e}", "rk4": "{:.3e}", "p_rk2": "{:.2f}", "p_rk4": "{:.2f}"}, na_rep="—"),
                             width="stretch", hide_index=True)
                st.caption("p = log₂(e_j / e_{j+1}): orden observado. Si el error es ≈ redondeo no hay orden que medir.")
            if o["sens"]:
                st.markdown("**Sensibilidad** (simulación RK4 con perturbación relativa ε)")
                st.dataframe(pd.DataFrame(o["sens"]).style.format(precision=4, na_rep="—"), width="stretch", hide_index=True)

with tab_i:
    if not S:
        st.info("Ejecuta una simulación primero.")
    else:
        interpretacion_y_guardado(engine, C["nombre"], S, M, "Sintético: parámetros ingresados por el usuario; referencia analítica o RK4 fino")
