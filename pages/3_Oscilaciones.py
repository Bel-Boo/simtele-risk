import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import m3_oscilaciones as M, resumen
from core.ayuda import glosario, guia, mostrar_resumen, selector_escenario
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
tab_m, tab_r, tab_i = st.tabs(["1 · Datos de entrada", "2 · Resultados", "3 · Interpretación y guardado"])

with tab_m:
    guia("oscilaciones")
    tipo = selector_escenario()
    st.info(M.DESCRIPCION[tipo])
    E = Entrada(M.PRESETS[tipo], tipo, "m3")
    P = {}
    st.markdown("##### Datos básicos de la cabina")
    c = st.columns(3)
    with c[0]: P["m"] = E.f("Masa (kg)", "m", positivo=True, help="Peso de la cabina con su carga.")
    with c[1]: P["k"] = E.f("Rigidez (N/m)", "k", positivo=True, help="Qué tan «dura» es la sujeción: más rigidez, oscila más rápido.")
    with c[2]: P["c"] = E.f("Amortiguamiento (N·s/m)", "c", help="Qué tanto «frena» el balanceo. 0 = oscila para siempre.")
    if P["m"] > 0 and P["k"] > 0 and P["c"] >= 0:
        mo = M.parametros_modales(P)
        if mo["wd"]:
            st.success(f"Con estos datos la cabina **oscila** ≈ {mo['wd'] / (2 * np.pi):.3g} veces por segundo y se va calmando "
                       f"(ζ = {mo['zeta']:.3g}; con ζ ≥ 1, o c ≥ {mo['c_critico']:.4g}, dejaría de oscilar).")
        else:
            st.warning(f"Con estos datos la cabina **no oscila** (ζ = {mo['zeta']:.3g} ≥ 1): vuelve al reposo sin balancearse.")
    c = st.columns(3)
    with c[0]: P["F_expr"] = E.t("Fuerza del viento F(t) en newtons", "F_expr",
                                 help=AYUDA + " Escribe 0 si no hay viento. Ej.: 300*sin(2*t) = viento que empuja y suelta 2 veces cada 2π segundos.")
    with c[1]: P["x0"] = E.f("Posición inicial (m)", "x0", help="Cuánto está desplazada la cabina al empezar. 0 = en reposo en el centro.")
    with c[2]: P["tf"] = E.f("Tiempo a simular (s)", "tf", positivo=True)
    with st.expander("⚙️ Opciones avanzadas"):
        c = st.columns(4)
        with c[0]: P["v0"] = E.f("Velocidad inicial (m/s)", "v0")
        with c[1]: P["N"] = E.i("Número de pasos de la simulación", "N", 2, 2000, help="Más pasos = más preciso pero más lento.")
        with c[2]: P["rk2"] = E.sel("Variante del método simple (RK2)", "rk2", list(VARIANTES_RK2), fmt=lambda k: VARIANTES_RK2[k][0])
        with c[3]: P["eps_sens"] = E.f("Cambio de prueba para sensibilidad (0.01 = 1%)", "eps_sens", positivo=True)
        if P["tf"] > 0:
            st.caption(f"Tamaño del paso h = tiempo/pasos = {P['tf'] / P['N']:.3g} s.")
        c = st.columns(3)
        with c[0]: P["magnitud"] = E.sel("Magnitud acumulada a calcular", "magnitud", ["x2", "abs"], horizontal=True,
                                         fmt=lambda s: "Suma de x² (energía)" if s == "x2" else "Suma de |x| (desplazamiento total)")
        with c[1]: P["kint"] = E.slider("Cuántas veces refinar el cálculo", "kint", 2, 12)
        with c[2]: P["sobre"] = E.sel("El cálculo usa…", "sobre", ["referencia", "rk4"], horizontal=True,
                                      fmt=lambda s: "la posición de referencia" if s == "referencia" else "la posición simulada (RK4)")
    for e in E.errores:
        st.error(e)
    E.restablecer()
    if not E.errores:
        ejecutar("m3", tipo, P, M)

S = st.session_state.get("m3")

with tab_r:
    if not S:
        st.info("Primero pulsa **▶ Ejecutar** en la pestaña «1 · Datos de entrada».")
    else:
        o, p, mo = S["out"], S["out"]["params"], S["out"]["modal"]
        st.markdown(f"#### Escenario {S['tipo'].replace('_', ' ')}")
        for a in o["avisos"]:
            st.warning(a)
        mostrar_resumen(resumen.m3(o))
        m = st.columns(5)
        m[0].metric("Frecuencia natural ω₀ (rad/s)", g(mo["w0"], 5))
        m[1].metric("Amortiguamiento ζ", g(mo["zeta"], 5))
        m[2].metric("Frecuencia real ω_d (rad/s)", g(mo["wd"], 5))
        m[3].metric("Desplazamiento máximo (m)", g(o["amp_ref"], 5))
        m[4].metric("Diferencia RK2 vs RK4 (m)", f"{o['dif_rk']:.2e}")
        st.markdown("### 🔬 Detalles técnicos")
        s1, s2, s3 = st.tabs(["Simulación (RK2 vs RK4)", "Magnitud acumulada (integración)", "Precisión y sensibilidad"])
        with s1:
            st.caption(f"Valor correcto de comparación: {o['tipo_ref']}" + (f" (error estimado de esa referencia ≈ {o['err_ref']:.1e})" if o["err_ref"] else "") + ".")
            st.dataframe(pd.DataFrame([{"Método": r["metodo"], "Desplazamiento máximo (m)": r["amp"], "Error máximo": r["err_max"],
                                        "Error al final": r["err_final"], "Tiempo de cálculo (ms)": round(r["tiempo_ms"], 3), "Estado": r["motivo_parada"]}
                                       for r in o["edo"]]).style.format({"Desplazamiento máximo (m)": "{:.6g}", "Error máximo": "{:.3e}", "Error al final": "{:.3e}"}),
                         width="stretch", hide_index=True)
            tt = np.linspace(0, p["tf"], 1500)
            c1, c2 = st.columns(2)
            c1.plotly_chart(fig_trayectorias({r["metodo"]: (r["t"], r["Y"][:, 0]) for r in o["edo"]}, "Posición de la cabina en el tiempo", ylab="x (m)",
                                             referencia=(tt, o["xref"](tt))), width="stretch", key="m3_x")
            c2.plotly_chart(fig_errores_tiempo({r["metodo"]: (r["t"], r["err"]) for r in o["edo"]}), width="stretch", key="m3_e")
            st.caption("Cómo leerlo: a la izquierda, la línea gris es el movimiento correcto y las punteadas lo que calcula cada método. "
                       "A la derecha, cuanto más abajo la línea, menor el error.")
            fase = go.Figure()
            fase.add_scatter(x=o["xref"](tt), y=o["vref"](tt), mode="lines", name="Referencia", line=dict(width=4, color="gray"))
            for r in o["edo"]:
                fase.add_scatter(x=r["Y"][:, 0], y=r["Y"][:, 1], mode="lines", name=r["metodo"], line=dict(dash="dash"))
            fase.update_layout(title="Posición contra velocidad (plano de fases)", xaxis_title="x (m)", yaxis_title="v (m/s)", height=380,
                               margin=dict(t=50, b=40), legend=dict(orientation="h", y=-0.25))
            st.plotly_chart(fase, width="stretch", key="m3_fase")
            st.caption("Cómo leerlo: una espiral hacia el centro significa que la oscilación se va apagando.")
            with st.expander("Ver la tabla tiempo por tiempo"):
                nom = st.selectbox("Método", [r["metodo"] for r in o["edo"]], key="m3_tab")
                r = next(r for r in o["edo"] if r["metodo"] == nom)
                st.dataframe(pd.DataFrame({"t": r["t"], "x": r["Y"][:, 0], "v": r["Y"][:, 1], "x correcta": o["Yref"][:, 0],
                                           "v correcta": o["Yref"][:, 1], "error": r["err"]}), width="stretch", hide_index=True)
        with s2:
            st.caption(f"Se calcula {'la suma de x²' if p['magnitud'] == 'x2' else 'la suma de |x|'} durante toda la simulación con 3 métodos, dividiendo el tiempo "
                       f"en más y más partes (n). Valor correcto: {g(o['I_ref'], 12)}.")
            mostrar_refinamiento(o["tabla_int"])
            st.plotly_chart(fig_refinamiento(o["tabla_int"]), width="stretch", key="m3_ref")
            st.caption("Cómo leerlo: a medida que n crece, el error baja.")
        with s3:
            c1, c2 = st.columns(2)
            c1.plotly_chart(fig_convergencia_paso(o["estudio"]), width="stretch", key="m3_conv")
            c2.dataframe(pd.DataFrame(o["estudio"]).style.format({"h": "{:.4g}", "rk2": "{:.3e}", "rk4": "{:.3e}", "p_rk2": "{:.2f}", "p_rk4": "{:.2f}"}, na_rep="—"),
                         width="stretch", hide_index=True)
            st.caption("Cómo leerlo: al achicar el paso h el error baja; «p» mide qué tan rápido (RK2 ≈ 2, RK4 ≈ 4).")
            st.markdown("**Sensibilidad:** qué pasa si cambias un poquito la masa, el amortiguamiento o la rigidez (amplificación = cambio del resultado ÷ cambio del dato)")
            st.dataframe(pd.DataFrame(o["sens"]).style.format(precision=4, na_rep="—"), width="stretch", hide_index=True)
        glosario()

with tab_i:
    if not S:
        st.info("Primero ejecuta una simulación.")
    else:
        interpretacion_y_guardado(engine, C["nombre"], S, M, "Sintético: parámetros ingresados por el usuario; referencia analítica (F=0) o RK4 fino")
