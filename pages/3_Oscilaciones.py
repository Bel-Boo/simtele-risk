import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import m3_oscilaciones as M
from core.casos import CASOS
from core.comun import fig_convergencia_paso, fig_errores_tiempo, fig_refinamiento, fig_trayectorias, g
from core.edo import VARIANTES_RK2
from core.funciones import AYUDA
from core.ui import AVISO, banner_bd
from core.ui_comun import Entrada, ejecutar, interpretacion_y_guardado, mostrar_refinamiento

C = CASOS["oscilaciones"]
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
    E = Entrada(M.PRESETS[tipo], tipo, "m3")
    P = {}
    st.markdown("##### Sistema masa–resorte–amortiguador")
    c = st.columns(3)
    with c[0]: P["m"] = E.f("Masa m [kg]", "m", positivo=True)
    with c[1]: P["c"] = E.f("Amortiguamiento c [N·s/m]", "c")
    with c[2]: P["k"] = E.f("Rigidez k [N/m]", "k", positivo=True)
    if P["m"] > 0 and P["k"] > 0 and P["c"] >= 0:
        mo = M.parametros_modales(P)
        st.caption(f"ω₀ = √(k/m) = **{mo['w0']:.5g}** rad/s · ζ = c/(2√(km)) = **{mo['zeta']:.5g}** · c crítico = {mo['c_critico']:.5g} · "
                   + (f"ω_d = ω₀√(1−ζ²) = **{mo['wd']:.5g}** rad/s" if mo["wd"] else "**sin oscilación** (ζ ≥ 1)"))
    st.markdown("##### Fuerza externa y condiciones iniciales")
    c = st.columns(3)
    with c[0]: P["F_expr"] = E.t("F(t) [N] — variable t", "F_expr", help=AYUDA + " Ej.: 0 (libre), 300*sin(2*t), 200*(1+0.3*sin(0.5*t))")
    with c[1]: P["x0"] = E.f("x(0) [m]", "x0")
    with c[2]: P["v0"] = E.f("v(0) [m/s]", "v0")
    st.markdown("##### Simulación (EDO) e integración")
    c = st.columns(4)
    with c[0]: P["tf"] = E.f("Tiempo final tf [s]", "tf", positivo=True)
    with c[1]: P["N"] = E.i("Pasos N (h = tf/N)", "N", 2, 2000)
    with c[2]: P["rk2"] = E.sel("Variante de RK2", "rk2", list(VARIANTES_RK2), fmt=lambda k: VARIANTES_RK2[k][0])
    with c[3]: P["eps_sens"] = E.f("Perturbación relativa (sensibilidad)", "eps_sens", positivo=True)
    c = st.columns(3)
    with c[0]: P["magnitud"] = E.sel("Magnitud acumulada a integrar", "magnitud", ["x2", "abs"],
                                     fmt=lambda s: "∫ x(t)² dt" if s == "x2" else "∫ |x(t)| dt", horizontal=True)
    with c[1]: P["kint"] = E.slider("Refinamientos: n = 2, 4, …, 2^k", "kint", 2, 12)
    with c[2]: P["sobre"] = E.sel("Integrar sobre", "sobre", ["referencia", "rk4"],
                                  fmt=lambda s: "x(t) de referencia" if s == "referencia" else "trayectoria RK4", horizontal=True)
    for e in E.errores:
        st.error(e)
    if not E.errores:
        ejecutar("m3", tipo, P, M)

S = st.session_state.get("m3")

with tab_r:
    if not S:
        st.info("Ejecuta una simulación en la pestaña 1.")
    else:
        o, p, mo = S["out"], S["out"]["params"], S["out"]["modal"]
        st.markdown(f"#### Escenario **{S['tipo'].replace('_', ' ')}** · referencia {o['tipo_ref']}"
                    + (f" (error estimado ≈ {o['err_ref']:.1e})" if o["err_ref"] else ""))
        for a in o["avisos"]:
            st.warning(a)
        m = st.columns(5)
        m[0].metric("ω₀ [rad/s]", g(mo["w0"], 5))
        m[1].metric("ζ", g(mo["zeta"], 5))
        m[2].metric("ω_d [rad/s]", g(mo["wd"], 5))
        m[3].metric("Amplitud máx (ref.)", g(o["amp_ref"], 5))
        m[4].metric("máx |x_RK2 − x_RK4|", f"{o['dif_rk']:.2e}")
        s1, s2, s3 = st.tabs(["EDO: RK2 vs RK4", "Integración de la magnitud acumulada", "Convergencia y sensibilidad"])
        with s1:
            st.dataframe(pd.DataFrame([{"Método": r["metodo"], "Amplitud máx": r["amp"], "Error máx": r["err_max"],
                                        "Error en tf": r["err_final"], "Tiempo (ms)": round(r["tiempo_ms"], 3), "Estado": r["motivo_parada"]}
                                       for r in o["edo"]]).style.format({"Amplitud máx": "{:.6g}", "Error máx": "{:.3e}", "Error en tf": "{:.3e}"}),
                         width="stretch", hide_index=True)
            tt = np.linspace(0, p["tf"], 1500)
            c1, c2 = st.columns(2)
            c1.plotly_chart(fig_trayectorias({r["metodo"]: (r["t"], r["Y"][:, 0]) for r in o["edo"]}, "Posición x(t)", ylab="x [m]",
                                             referencia=(tt, o["xref"](tt))), width="stretch", key="m3_x")
            c2.plotly_chart(fig_errores_tiempo({r["metodo"]: (r["t"], r["err"]) for r in o["edo"]}), width="stretch", key="m3_e")
            fase = go.Figure()
            fase.add_scatter(x=o["xref"](tt), y=o["vref"](tt), mode="lines", name="Referencia", line=dict(width=4, color="gray"))
            for r in o["edo"]:
                fase.add_scatter(x=r["Y"][:, 0], y=r["Y"][:, 1], mode="lines", name=r["metodo"], line=dict(dash="dash"))
            fase.update_layout(title="Plano de fases (x, v)", xaxis_title="x [m]", yaxis_title="v [m/s]", height=380,
                               margin=dict(t=50, b=40), legend=dict(orientation="h", y=-0.25))
            st.plotly_chart(fase, width="stretch", key="m3_fase")
            with st.expander("Tabla temporal (t, x, v, error)"):
                nom = st.selectbox("Método", [r["metodo"] for r in o["edo"]], key="m3_tab")
                r = next(r for r in o["edo"] if r["metodo"] == nom)
                st.dataframe(pd.DataFrame({"t": r["t"], "x": r["Y"][:, 0], "v": r["Y"][:, 1], "x_ref": o["Yref"][:, 0],
                                           "v_ref": o["Yref"][:, 1], "error": r["err"]}), width="stretch", hide_index=True)
        with s2:
            st.caption(f"{'∫ x² dt' if p['magnitud'] == 'x2' else '∫ |x| dt'} sobre [0, {p['tf']:g}]. Referencia de alta precisión: {g(o['I_ref'], 12)} "
                       "(Romberg nivel 13" + (", partido en los ceros de x" if p["magnitud"] == "abs" else "") + ").")
            mostrar_refinamiento(o["tabla_int"])
            st.plotly_chart(fig_refinamiento(o["tabla_int"]), width="stretch", key="m3_ref")
        with s3:
            c1, c2 = st.columns(2)
            c1.plotly_chart(fig_convergencia_paso(o["estudio"]), width="stretch", key="m3_conv")
            c2.dataframe(pd.DataFrame(o["estudio"]).style.format({"h": "{:.4g}", "rk2": "{:.3e}", "rk4": "{:.3e}", "p_rk2": "{:.2f}", "p_rk4": "{:.2f}"}, na_rep="—"),
                         width="stretch", hide_index=True)
            st.markdown("**Sensibilidad** a perturbaciones relativas de m, c, k (amplif. = Δrel salida / Δrel parámetro)")
            st.dataframe(pd.DataFrame(o["sens"]).style.format(precision=4, na_rep="—"), width="stretch", hide_index=True)

with tab_i:
    if not S:
        st.info("Ejecuta una simulación primero.")
    else:
        interpretacion_y_guardado(engine, C["nombre"], S, M, "Sintético: parámetros ingresados por el usuario; referencia analítica (F=0) o RK4 fino")
