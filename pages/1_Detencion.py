import numpy as np
import pandas as pd
import streamlit as st

from core import m1_detencion as M, resumen
from core.ayuda import glosario, guia, mostrar_resumen, selector_escenario
from core.casos import CASOS
from core.comun import fig_convergencia_paso, fig_errores_tiempo, fig_refinamiento, fig_trayectorias, g
from core.edo import VARIANTES_RK2
from core.funciones import AYUDA
from core.ui import AVISO, banner_bd
from core.ui_comun import Entrada, ejecutar, interpretacion_y_guardado, mostrar_raices, mostrar_refinamiento

C = CASOS["detencion"]
st.title(f"{C['icono']} {C['nombre']}")
st.caption(AVISO)
engine = banner_bd()
tab_m, tab_r, tab_i = st.tabs(["1 · Datos de entrada", "2 · Resultados", "3 · Interpretación y guardado"])

with tab_m:
    guia("detencion")
    tipo = selector_escenario()
    st.info(M.DESCRIPCION[tipo])
    E = Entrada(M.PRESETS[tipo], tipo, "m1")
    P = {}
    st.markdown("##### Datos básicos")
    c = st.columns(3)
    with c[0]: P["v0"] = E.f("Velocidad de la cabina al empezar a frenar (m/s)", "v0", positivo=True, help="Ej.: 5 m/s equivale a 18 km/h.")
    with c[1]: P["t_reaccion"] = E.f("Tiempo de reacción (s)", "t_reaccion", help="Segundos que pasan entre detectar la emergencia y que empiecen los frenos. Pon 0 si no aplica.")
    with c[2]: P["d_disp"] = E.f("Distancia disponible para frenar (m)", "d_disp", help="Metros libres hasta el obstáculo. Pon 0 si no hay límite.")
    P["modelo"] = E.sel("¿Cómo frena la cabina?", "modelo", ["constante", "personalizada"], horizontal=True,
                        fmt=lambda m: "Con fuerza constante (lo más simple)" if m == "constante" else "Con fuerza variable (escribo la fórmula)")
    if P["modelo"] == "constante":
        P["a"] = E.f("Desaceleración (m/s²)", "a", positivo=True, help="Cuánta velocidad pierde la cabina cada segundo. Ej.: 1 = pierde 1 m/s por segundo.")
        P.update(expr_a=M.BASE["expr_a"], v_exacta="", x_exacta="", dv_exacta="", t_det_ref=0.0)
    else:
        P["a"] = M.BASE["a"]
        P["expr_a"] = E.t("Fórmula de la desaceleración a(v, t) en m/s²", "expr_a",
                          help=AYUDA + " Variables: v (velocidad) y t (tiempo). Ej.: 0.5+0.3*v (frena más fuerte si va rápido).")
        with st.expander("Respuesta exacta conocida (opcional, para medir el error real)", expanded=bool(M.PRESETS[tipo]["v_exacta"])):
            st.caption("Si conoces las fórmulas exactas de v(t) y x(t), escríbelas (variable t) y la app medirá el error real de cada método. "
                       "Si las dejas vacías, la app usa como referencia una simulación mucho más fina.")
            P["v_exacta"] = E.t("v(t) exacta", "v_exacta")
            P["x_exacta"] = E.t("x(t) exacta", "x_exacta")
            P["dv_exacta"] = E.t("Derivada v'(t) exacta (opcional)", "dv_exacta")
            P["t_det_ref"] = E.f("Instante de detención conocido (0 = que la app lo calcule)", "t_det_ref")
    with st.expander("⚙️ Opciones avanzadas (puedes dejarlas como están)"):
        P["x0"] = E.f("Posición inicial x0 (m)", "x0")
        auto = False
        if P["modelo"] == "constante":
            auto = st.checkbox("Calcular solo el tiempo de simulación y los puntos de partida (recomendado)", value=True, key=f"m1_auto_{tipo}")
        if auto:
            tf = 1.3 * P["v0"] / P["a"] if P["a"] > 0 else 1.0
            P.update(tf=tf, bis_a=0.0, bis_b=tf, x0_newton=tf / 4, x0_sec=tf / 8, x1_sec=tf / 2)
            st.caption(f"Se simulará hasta {tf:.3g} s (un 30% más que el tiempo de frenado).")
        else:
            c = st.columns(3)
            with c[0]: P["tf"] = E.f("Tiempo a simular (s)", "tf", positivo=True)
            with c[1]: P["bis_a"] = E.f("Búsqueda del cero (bisección): desde (s)", "bis_a")
            with c[2]: P["bis_b"] = E.f("…hasta (s)", "bis_b")
            c = st.columns(3)
            with c[0]: P["x0_newton"] = E.f("Newton: punto de partida (s)", "x0_newton")
            with c[1]: P["x0_sec"] = E.f("Secante: 1.er punto de partida (s)", "x0_sec")
            with c[2]: P["x1_sec"] = E.f("Secante: 2.º punto de partida (s)", "x1_sec")
        c = st.columns(3)
        with c[0]: P["N"] = E.i("Número de pasos de la simulación", "N", 2, 2000, help="Más pasos = más preciso pero más lento (h = tiempo/pasos).")
        with c[1]: P["rk2"] = E.sel("Variante del método simple (RK2)", "rk2", list(VARIANTES_RK2), fmt=lambda k: VARIANTES_RK2[k][0])
        with c[2]: P["eps_sens"] = E.f("Cambio de prueba para medir sensibilidad (0.01 = 1%)", "eps_sens", positivo=True)
        c = st.columns(3)
        with c[0]: P["tol"] = E.f("Precisión exigida a la búsqueda del cero", "tol", positivo=True, help="Ej.: 1e-10 = 0.0000000001")
        with c[1]: P["max_iter"] = E.i("Máximo de intentos de búsqueda", "max_iter", 1, 1000)
        with c[2]: P["kint"] = E.slider("Cuántas veces refinar el cálculo de la distancia", "kint", 2, 12)
        P["sobre"] = E.sel("El cálculo de la distancia usa…", "sobre", ["referencia", "rk4"], horizontal=True,
                           fmt=lambda s: "la velocidad exacta/de referencia" if s == "referencia" else "la velocidad simulada (RK4)")
    for e in E.errores:
        st.error(e)
    E.restablecer()
    if not E.errores:
        ejecutar("m1", tipo, P, M)

S = st.session_state.get("m1")

with tab_r:
    if not S:
        st.info("Primero pulsa **▶ Ejecutar** en la pestaña «1 · Datos de entrada».")
    else:
        o, p = S["out"], S["out"]["params"]
        st.markdown(f"#### Escenario {S['tipo'].replace('_', ' ')}")
        for a in o["avisos"]:
            st.warning(a)
        mostrar_resumen(resumen.m1(o))
        m = st.columns(5)
        m[0].metric("Tiempo hasta detenerse (s)", g(o["td_ref"], 5))
        m[1].metric("Distancia de frenado (m)", g(o["I_ref"], 5))
        m[2].metric("Distancia de reacción (m)", g(o["d_reac"], 4))
        m[3].metric("Distancia total (m)", g(o["d_total"], 5))
        m[4].metric("Margen (m)", g(o["margen"], 4) if o["margen"] is not None else "sin límite",
                    delta=None if o["margen"] is None else ("alcanza" if o["margen"] >= 0 else "NO alcanza"),
                    delta_color="normal" if (o["margen"] or 0) >= 0 else "inverse")
        st.markdown("### 🔬 Detalles técnicos")
        s1, s2, s3, s4 = st.tabs(["Simulación (RK2 vs RK4)", "Distancia por integración", "Cuándo llega a 0 (raíces)", "Precisión y sensibilidad"])
        with s1:
            st.caption(f"Valor correcto de comparación: {o['tipo_ref']}" + (f" (error estimado de esa referencia ≈ {o['err_ref']:.1e})" if o["err_ref"] else "") + ".")
            st.dataframe(pd.DataFrame([{"Método": r["metodo"], "Tiempo hasta detenerse (s)": r["t_det"], "Distancia de frenado (m)": r["d_frenado"],
                                        "Error máximo": r["err_max"], "Error al final": r["err_final"], "Tiempo de cálculo (ms)": round(r["tiempo_ms"], 3),
                                        "Estado": r["motivo_parada"]} for r in o["edo"]]).style.format(
                {"Error máximo": "{:.3e}", "Error al final": "{:.3e}", "Tiempo hasta detenerse (s)": "{:.8g}", "Distancia de frenado (m)": "{:.8g}"}, na_rep="—"),
                width="stretch", hide_index=True)
            tt = np.linspace(0, p["tf"], 600)
            c1, c2 = st.columns(2)
            c1.plotly_chart(fig_trayectorias({r["metodo"]: (r["t"], r["Y"][:, 1]) for r in o["edo"]}, "Velocidad en el tiempo", ylab="v (m/s)",
                                             referencia=(tt, o["vref"](tt))), width="stretch", key="m1_v")
            c2.plotly_chart(fig_trayectorias({r["metodo"]: (r["t"], r["Y"][:, 0]) for r in o["edo"]}, "Posición en el tiempo", ylab="x (m)",
                                             referencia=(tt, o["xref"](tt))), width="stretch", key="m1_x")
            st.caption("Cómo leerlo: la línea gris gruesa es el valor correcto y las punteadas son lo que calcula cada método. Si se superponen, el método es bueno.")
            st.plotly_chart(fig_errores_tiempo({r["metodo"]: (r["t"], r["err"]) for r in o["edo"]}), width="stretch", key="m1_err")
            st.caption("Cómo leerlo: cuanto más abajo está la línea, menor es el error (escala logarítmica).")
            with st.expander("Ver la tabla tiempo por tiempo"):
                nom = st.selectbox("Método", [r["metodo"] for r in o["edo"]], key="m1_tab")
                r = next(r for r in o["edo"] if r["metodo"] == nom)
                st.dataframe(pd.DataFrame({"t": r["t"], "x": r["Y"][:, 0], "v": r["Y"][:, 1], "x correcta": o["Yref"][:, 0],
                                           "v correcta": o["Yref"][:, 1], "error": r["err"]}), width="stretch", hide_index=True)
        with s2:
            st.caption(f"La distancia de frenado es el área bajo la curva de velocidad entre 0 y {g(o['T_int'], 6)} s. Valor correcto: {g(o['I_ref'], 12)} m. "
                       "Se calcula con 3 métodos, dividiendo el intervalo en más y más partes (n).")
            mostrar_refinamiento(o["tabla_int"], o["R"])
            st.plotly_chart(fig_refinamiento(o["tabla_int"]), width="stretch", key="m1_ref")
            st.caption("Cómo leerlo: a medida que n crece, el error baja. Romberg suele bajar más rápido.")
        with s3:
            st.caption("Cuándo la velocidad llega exactamente a 0. Cada método busca ese instante de forma distinta.")
            mostrar_raices(o["raices"], "m1r")
        with s4:
            c1, c2 = st.columns(2)
            c1.plotly_chart(fig_convergencia_paso(o["estudio"]), width="stretch", key="m1_conv")
            with c2:
                st.dataframe(pd.DataFrame(o["estudio"]).style.format({"h": "{:.4g}", "rk2": "{:.3e}", "rk4": "{:.3e}", "p_rk2": "{:.2f}", "p_rk4": "{:.2f}"}, na_rep="—"),
                             width="stretch", hide_index=True)
            st.caption("Cómo leerlo: al hacer el paso h más pequeño el error baja. «p» es la rapidez con que baja (RK2 ≈ 2, RK4 ≈ 4). Si el error es casi cero, ya no hay nada que medir.")
            if o["sens"]:
                st.markdown("**Sensibilidad:** qué pasa si cambias un dato un poquito")
                st.dataframe(pd.DataFrame(o["sens"]).style.format(precision=4, na_rep="—"), width="stretch", hide_index=True)
        glosario()

with tab_i:
    if not S:
        st.info("Primero ejecuta una simulación.")
    else:
        interpretacion_y_guardado(engine, C["nombre"], S, M, "Sintético: parámetros ingresados por el usuario; referencia analítica o RK4 fino")
