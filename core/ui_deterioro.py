"""Módulo 2 · subexperimento de raíces (interfaz en lenguaje simple)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import m2_raices as M, resumen
from .ayuda import glosario, mostrar_resumen, selector_escenario
from .casos import CASOS
from .comun import fig_refinamiento, g
from .funciones import AYUDA
from .ui_comun import Entrada, ejecutar, interpretacion_y_guardado, mostrar_raices, mostrar_refinamiento

C = CASOS["deterioro"]


def render_raices(engine):
    tab_m, tab_r, tab_i = st.tabs(["1 · Datos de entrada", "2 · Resultados", "3 · Interpretación y guardado"])
    with tab_m:
        st.markdown("**Pregunta:** ¿en qué día el indicador de deterioro llegaría al umbral de inspección?")
        st.latex(C["modelo"])
        st.caption("D = indicador de deterioro (sin unidades, inventado) · t = días desde hoy · α = rapidez con que crece el deterioro · β = si el deterioro se acelera (β>0) o se frena (β<0).")
        tipo = selector_escenario(key="m2r_tipo")
        st.info(M.DESCRIPCION[tipo])
        E = Entrada(M.PRESETS[tipo], tipo, "m2r")
        P = {"submodulo": "raices"}
        P["modelo"] = E.sel("¿Cómo crece el deterioro?", "modelo", ["cuadratico", "personalizado"], horizontal=True,
                            fmt=lambda m: "Con la fórmula D(t) = D0 + α·t + β·t² (lo más simple)" if m == "cuadratico" else "Con mi propia fórmula D(t)")
        st.markdown("##### Datos básicos")
        if P["modelo"] == "cuadratico":
            c = st.columns(4)
            with c[0]: P["D0"] = E.f("Deterioro inicial D0", "D0", help="Valor del indicador hoy.")
            with c[1]: P["alpha"] = E.f("Rapidez de deterioro α (por día)", "alpha")
            with c[2]: P["beta"] = E.f("Aceleración β (por día²)", "beta", help="0 = deterioro constante. Positivo = se acelera. Negativo = se frena.")
            with c[3]: P["D_umbral"] = E.f("Umbral de inspección", "D_umbral", help="Valor del indicador en que hay que inspeccionar.")
            P.update(expr_D=M.BASE["expr_D"], expr_dD="")
        else:
            c = st.columns(2)
            with c[0]: P["expr_D"] = E.t("Fórmula del deterioro D(t)", "expr_D", help=AYUDA + " Variable: t (días). Ej.: 5*exp(0.01*t) o 12+3*sin(0.02*t)+0.01*t.")
            with c[1]: P["D_umbral"] = E.f("Umbral de inspección", "D_umbral")
            P.update(D0=M.BASE["D0"], alpha=M.BASE["alpha"], beta=M.BASE["beta"], expr_dD="")
        c = st.columns(2)
        with c[0]: P["t_mant"] = E.f("Día de mantenimiento programado (0 = ninguno)", "t_mant")
        with c[1]: P["retraso"] = E.f("Retraso hipotético del mantenimiento (días)", "retraso", help="¿Y si el mantenimiento se atrasa?")
        with st.expander("⚙️ Opciones avanzadas (puedes dejarlas como están)"):
            auto = False
            if P["modelo"] == "cuadratico":
                auto = st.checkbox("Calcular solo el intervalo de búsqueda y los puntos de partida (recomendado)", value=(tipo != "MAL_CONDICIONADO"), key=f"m2r_auto_{tipo}")
            if auto:
                t_ref = M._t_estrella({**M.BASE, **P, "a": 0.0, "b": 1000.0})
                if t_ref:
                    P.update(a=0.0, b=2.5 * t_ref, x0_newton=0.5 * t_ref, x0_sec=0.3 * t_ref, x1_sec=0.7 * t_ref)
                else:
                    P.update(a=M.BASE["a"], b=M.BASE["b"], x0_newton=M.BASE["x0_newton"], x0_sec=M.BASE["x0_sec"], x1_sec=M.BASE["x1_sec"])
                    st.warning("Con estos datos el indicador no llega al umbral; se usan los valores estándar.")
            else:
                c = st.columns(5)
                with c[0]: P["a"] = E.f("Bisección: desde el día", "a")
                with c[1]: P["b"] = E.f("…hasta el día", "b")
                with c[2]: P["x0_newton"] = E.f("Newton: día de partida", "x0_newton")
                with c[3]: P["x0_sec"] = E.f("Secante: 1.er día de partida", "x0_sec")
                with c[4]: P["x1_sec"] = E.f("Secante: 2.º día de partida", "x1_sec")
            if P["modelo"] == "personalizado":
                P["expr_dD"] = E.t("Derivada D'(t) (opcional; si la dejas vacía se calcula sola)", "expr_dD")
            c = st.columns(4)
            with c[0]: P["tol"] = E.f("Precisión exigida", "tol", positivo=True, help="Ej.: 1e-10 = 0.0000000001")
            with c[1]: P["max_iter"] = E.i("Máximo de intentos", "max_iter", 1, 1000)
            with c[2]: P["eps_sens"] = E.f("Cambio de prueba para sensibilidad (0.001 = 0.1%)", "eps_sens", positivo=True)
            with c[3]: P["kint"] = E.slider("Cuántas veces refinar la integral", "kint", 2, 12)
            P["integrar_tasa"] = st.checkbox("Calcular también el deterioro acumulado integrando su rapidez (trapecio, Simpson, Romberg)", value=True, key=f"m2r_int_{tipo}")
        for e in E.errores:
            st.error(e)
        E.restablecer()
        if not E.errores:
            ejecutar("m2r", tipo, P, M)

    S = st.session_state.get("m2r")
    with tab_r:
        if not S:
            st.info("Primero pulsa **▶ Ejecutar** en la pestaña «1 · Datos de entrada».")
        else:
            o, p = S["out"], S["out"]["params"]
            st.markdown(f"#### Escenario {S['tipo'].replace('_', ' ')}")
            for a in o["avisos"]:
                st.warning(a)
            mostrar_resumen(resumen.m2r(o))
            info = o["info"]
            m = st.columns(4)
            m[0].metric("Día en que se alcanza el umbral", g(o["t_ref"], 8))
            m[1].metric("Discriminante", g(info.get("discriminante"), 4), help="Si es ≈ 0 el umbral casi no se alcanza (raíz casi doble).")
            m[2].metric("Máximo de D (si β<0)", g(info.get("D_max"), 6))
            if o["mant"]:
                m[3].metric("Margen hasta el mantenimiento (días)", g(o["mant"]["margen"], 5),
                            delta="umbral ANTES del mantenimiento" if o["mant"]["antes"] else "hay margen",
                            delta_color="inverse" if o["mant"]["antes"] else "normal")
            st.markdown("### 🔬 Detalles técnicos")
            s1, s2, s3 = st.tabs(["Búsqueda de la fecha (raíces)", "Sensibilidad y mantenimiento", "Deterioro acumulado (integración)"])
            with s1:
                top = max(p["b"], (o["mant"] or {}).get("t_efectivo", 0), (o["t_ref"] or 0) * 1.3)
                tt = np.linspace(0, top, 600)
                fig = go.Figure()
                fig.add_scatter(x=tt, y=o["D"](tt), mode="lines", name="Deterioro D(t)")
                fig.add_hline(y=p["D_umbral"], line_dash="dot", annotation_text="umbral")
                if o["t_ref"] is not None:
                    fig.add_vline(x=o["t_ref"], line_dash="dash", annotation_text="día del umbral")
                if o["mant"]:
                    fig.add_vline(x=o["mant"]["t_efectivo"], line_color="gray", annotation_text="mantenimiento")
                fig.update_layout(title="Evolución del deterioro", xaxis_title="días", yaxis_title="D", height=360, margin=dict(t=50, b=40))
                st.plotly_chart(fig, width="stretch", key="m2r_D")
                st.caption("Cómo leerlo: la curva sube hasta cruzar la línea del umbral; esa fecha es la respuesta. La línea gris es el día del mantenimiento.")
                mostrar_raices(o["raices"], "m2r")
            with s2:
                filas = [{"Dato que se cambia": s["parámetro"], "Fecha si el dato sube": s["t*(+ε)"], "Fecha si el dato baja": s["t*(−ε)"],
                          "Amplificación": s["amplificación"] if s["amplificación"] is not None else "sin solución (desaparece o aparece)"} for s in o["sens"]]
                st.markdown(f"**Sensibilidad:** qué tanto se mueve la fecha si cada dato cambia {p['eps_sens'] * 100:g}%")
                st.dataframe(pd.DataFrame(filas).style.format({"Fecha si el dato sube": "{:.8g}", "Fecha si el dato baja": "{:.8g}"}, na_rep="no existe"), width="stretch", hide_index=True)
                st.caption("Amplificación 1 = la fecha cambia en la misma proporción que el dato; un número grande significa que el resultado es muy sensible.")
                if o["mant"]:
                    st.markdown("**Mantenimiento hipotéticamente retrasado**")
                    st.dataframe(pd.DataFrame([o["mant"]]).style.format(precision=5), width="stretch", hide_index=True)
            with s3:
                if o["tabla_int"]:
                    st.caption(f"Sumar la rapidez de deterioro desde hoy hasta el día del umbral debe dar D(umbral) − D(0) = {g(o['I_ref'], 12)}. Se calcula con 3 métodos.")
                    mostrar_refinamiento(o["tabla_int"])
                    st.plotly_chart(fig_refinamiento(o["tabla_int"]), width="stretch", key="m2r_ref")
                else:
                    st.info("Activa «Calcular también el deterioro acumulado» en las opciones avanzadas y asegúrate de que exista el día del umbral.")
            glosario()
    with tab_i:
        if not S:
            st.info("Primero ejecuta una simulación.")
        else:
            interpretacion_y_guardado(engine, "Deterioro y mantenimiento", S, M, "Sintético: parámetros ingresados por el usuario; referencia por fórmula cuadrática o bisección 1e-15")
