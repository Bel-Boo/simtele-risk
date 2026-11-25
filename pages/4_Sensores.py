import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import m4_sensores as M, resumen
from core.ayuda import glosario, guia, mostrar_resumen, selector_escenario
from core.casos import CASOS
from core.comun import g
from core.funciones import AYUDA
from core.ui import AVISO, banner_bd
from core.ui_comun import Entrada, ejecutar, interpretacion_y_guardado, mostrar_raices

C = CASOS["sensores"]
st.title(f"{C['icono']} {C['nombre']}")
st.caption(AVISO)
engine = banner_bd()
tab_m, tab_r, tab_i = st.tabs(["1 · Datos de entrada", "2 · Resultados", "3 · Interpretación y guardado"])

with tab_m:
    guia("sensores")
    tipo = selector_escenario()
    st.info(M.DESCRIPCION[tipo])
    E = Entrada(M.PRESETS[tipo], tipo, "m4")
    P = {}
    P["fuente"] = E.sel("¿De dónde vienen los datos?", "fuente", ["sintetica", "propios"], horizontal=True,
                        fmt=lambda s: "Los genera la app (señal inventada)" if s == "sintetica" else "Los pego yo (mis propios datos)")
    st.markdown("##### Datos del sensor")
    if P["fuente"] == "sintetica":
        c = st.columns(4)
        with c[0]: P["func"] = E.t("Señal real del sensor y(t)", "func", help=AYUDA + " Ej.: sin(t), exp(-t), sin(t)+0.3*cos(3*t).")
        with c[1]: P["a"] = E.f("Tiempo inicial", "a")
        with c[2]: P["b"] = E.f("Tiempo final", "b")
        with c[3]: P["n"] = E.i("Cantidad de mediciones (5 a 60)", "n", 5, 60)
        c = st.columns(3)
        with c[0]: P["sigma"] = E.f("Ruido de medición", "sigma", help="0 = medición perfecta. Ej.: 0.05 = error típico de ±0.05 en cada dato.")
        with c[1]: P["nodos"] = E.sel("¿Cuándo se mide?", "nodos", ["equiespaciados", "chebyshev", "personalizados"],
                                      fmt=lambda s: {"equiespaciados": "A intervalos iguales", "chebyshev": "Más seguido en los extremos (Chebyshev)", "personalizados": "En los tiempos que yo escriba"}[s])
        with c[2]: P["semilla"] = E.i("Semilla del ruido", "semilla", 0, 10**6, help="Con la misma semilla el ruido es siempre el mismo (resultados repetibles).")
        P["nodos_txt"] = E.t("Tiempos de medición (separados por comas)", "nodos_txt") if P["nodos"] == "personalizados" else ""
        P["datos_txt"] = ""
    else:
        P["datos_txt"] = E.t("Pega tus datos: una medición por línea, «tiempo valor» (separa con espacio, coma o ;)", "datos_txt", area=True, height=180,
                             help="Ejemplo:\n0 0.0\n1 0.84\n2 0.91\n3 0.14\n4 -0.76")
        P.update(func="sin(t)", a=0.0, b=1.0, n=10, nodos="equiespaciados", nodos_txt="", sigma=0.0, semilla=0)
    for e in E.errores:
        st.error(e)
    datos_ok = False
    if not E.errores:
        try:
            _t, _y, _yv, _ = M._datos({**M.BASE, **P, "ocultos": "0"})
            n_pts = len(_t)
            pred = [i for i in M._lista_ints(M.PRESETS[tipo]["ocultos"]) if i < n_pts]
            sel = st.multiselect("¿Qué mediciones «se perdieron»? (se ocultan y luego se reconstruyen)", list(range(n_pts)),
                                 default=pred if P["fuente"] == "sintetica" else [i for i in (3, 6) if i < n_pts],
                                 format_func=lambda i: f"#{i} (t = {_t[i]:.3g})", key=f"m4_oc_{tipo}_{P['fuente']}_{n_pts}",
                                 help="Elige datos del interior. Los de los extremos obligan a EXTRAPOLAR y el error crece mucho.")
            P["ocultos"] = ", ".join(str(i) for i in sel)
            datos_ok = True
            with st.expander(f"Ver los {n_pts} datos (los ocultos están marcados)"):
                st.dataframe(pd.DataFrame({"#": range(n_pts), "tiempo": _t, "valor medido": _y,
                                           **({"valor real": _yv} if _yv is not None else {}),
                                           "oculto": ["sí" if i in sel else "" for i in range(n_pts)]}), width="stretch", hide_index=True)
        except Exception as e:
            st.warning(f"Revisa los datos: {e}")
    with st.expander("⚙️ Opciones avanzadas (puedes dejarlas como están)"):
        c = st.columns(4)
        with c[0]: P["umbral"] = E.t("Valor límite para hallar cuándo se cruza (opcional)", "umbral", help="Ej.: 0.5 → ¿en qué instante la señal reconstruida llega a 0.5?")
        with c[1]: P["tol"] = E.f("Precisión de esa búsqueda", "tol", positivo=True)
        with c[2]: P["max_iter"] = E.i("Máximo de intentos", "max_iter", 1, 1000)
        with c[3]: P["eps_sens"] = E.f("Ruido de prueba para medir estabilidad", "eps_sens", positivo=True,
                                       help="Se agrega este ruido a los datos conocidos para ver cuánto se distorsiona la curva.")
    P["n_graf"] = 200
    for e in E.errores:
        st.error(e)
    E.restablecer()
    if not E.errores and datos_ok:
        if not P["ocultos"]:
            st.warning("Elige al menos una medición que se haya perdido.")
        else:
            ejecutar("m4", tipo, P, M)

S = st.session_state.get("m4")

with tab_r:
    if not S:
        st.info("Primero pulsa **▶ Ejecutar** en la pestaña «1 · Datos de entrada».")
    else:
        o, p, d = S["out"], S["out"]["params"], S["out"]["diag"]
        st.markdown(f"#### Escenario {S['tipo'].replace('_', ' ')}")
        mostrar_resumen(resumen.m4(o))
        m = st.columns(5)
        m[0].metric("Datos conocidos", d["n_conocidos"])
        m[1].metric("Grado del polinomio", d["grado"])
        m[2].metric("κ de Vandermonde", g(d["cond_vandermonde"], 3))
        m[3].metric("Λ con tus nodos", g(d["lebesgue"], 3))
        m[4].metric("Λ con Chebyshev", g(d.get("lebesgue_chebyshev"), 3))
        st.caption("κ y Λ miden qué tan *inestable* es dibujar la curva con esos tiempos de medición: cuanto más grandes, más se amplifica cualquier error de los datos.")
        st.markdown("### 🔬 Detalles técnicos")
        s1, s2, s3 = st.tabs(["Curvas reconstruidas", "Errores y efecto del ruido", "Cuándo se cruza un valor límite"])
        with s1:
            fig = go.Figure()
            if o["yg_ver"] is not None:
                fig.add_scatter(x=o["tg"], y=o["yg_ver"], mode="lines", name="Señal real", line=dict(width=4, color="gray"))
            for r in o["res"]:
                fig.add_scatter(x=o["tg"], y=r["yg"], mode="lines", name=r["metodo"], line=dict(dash="dash"))
            fig.add_scatter(x=o["tk"], y=o["yk"], mode="markers", name="Datos conocidos", marker=dict(size=8, color="black"))
            fig.add_scatter(x=o["th"], y=o["ref_h"], mode="markers", name="Datos perdidos (valor correcto)", marker=dict(size=13, symbol="x", color="red"))
            ys = np.concatenate([o["yk"], o["ref_h"]])
            rango = float(np.ptp(ys)) or 1.0
            fig.update_yaxes(range=[ys.min() - 1.5 * rango, ys.max() + 1.5 * rango])
            fig.update_layout(title="Señal real y curvas reconstruidas", height=440, xaxis_title="tiempo", yaxis_title="valor",
                              legend=dict(orientation="h", y=-0.25), margin=dict(t=50, b=40))
            st.plotly_chart(fig, width="stretch", key="m4_curvas")
            st.caption("Cómo leerlo: las ✖ rojas son los datos perdidos. Un buen método pasa cerca de ellas. Si una curva se dispara hacia arriba o abajo, es inestable "
                       "(el eje está acotado para que se pueda ver).")
            if o["tabla_dd"] is not None:
                with st.expander("Tabla de diferencias divididas (método de Newton)"):
                    n_ = len(o["tabla_dd"])
                    st.dataframe(pd.DataFrame(np.where(np.add.outer(np.arange(n_), np.arange(n_)) <= n_ - 1, o["tabla_dd"], np.nan)).style.format("{:.6g}", na_rep=""))
        with s2:
            tabla = pd.DataFrame([{"Método": r["metodo"], "Error máximo en datos perdidos": r["err_max"], "Error promedio (RMS)": r["err_rms"],
                                   "Error máximo en toda la curva": r["err_curva"], "Amplificación del ruido": r["amp_curva"],
                                   "Tiempo de cálculo (ms)": round(r["tiempo_ms"], 3)} for r in o["res"]])
            st.dataframe(tabla.style.format({"Error máximo en datos perdidos": "{:.3e}", "Error promedio (RMS)": "{:.3e}", "Error máximo en toda la curva": "{:.3e}",
                                             "Amplificación del ruido": "{:.2f}"}, na_rep="—"), width="stretch", hide_index=True)
            st.caption(f"Lagrange y Newton dibujan el MISMO polinomio (difieren en {o['dif_lag_newton']:.1e}, solo por redondeo). "
                       f"«Amplificación del ruido» = cuánto se mueve la curva por cada unidad de ruido añadido ({o['dmax']:.1e}); 1 es lo ideal.")
            c1, c2 = st.columns(2)
            fb = go.Figure()
            for r in o["res"]:
                fb.add_bar(x=[f"t={t:.3g}" for t in o["th"]], y=np.maximum(r["err_h"], 1e-20), name=r["metodo"])
            fb.update_yaxes(type="log", title="Error")
            fb.update_layout(title="Error en cada dato perdido", barmode="group", height=380, margin=dict(t=50, b=40), legend=dict(orientation="h", y=-0.3))
            c1.plotly_chart(fb, width="stretch", key="m4_err")
            fa = go.Figure(go.Bar(x=[r["metodo"] for r in o["res"]], y=[r["amp_curva"] for r in o["res"]]))
            fa.update_yaxes(type="log", title="Amplificación")
            fa.update_layout(title="Estabilidad ante ruido en los datos", height=380, margin=dict(t=50, b=40))
            c2.plotly_chart(fa, width="stretch", key="m4_amp")
            st.caption("Cómo leerlo: barras más bajas = mejor. En la derecha, una barra muy alta significa que el método amplifica mucho el ruido.")
            if p["fuente"] == "sintetica" and st.button("Comparar con medir en los tiempos de Chebyshev (mismos datos perdidos)"):
                try:
                    oc = M.correr({**p, "nodos": "chebyshev"})
                    st.dataframe(pd.DataFrame([{"Método": a["metodo"], "Error en perdidos (tus tiempos)": a["err_max"], "Error en perdidos (Chebyshev)": b["err_max"],
                                                "Error en la curva (tus tiempos)": a["err_curva"], "Error en la curva (Chebyshev)": b["err_curva"],
                                                "Amplificación (tus tiempos)": a["amp_curva"], "Amplificación (Chebyshev)": b["amp_curva"]}
                                               for a, b in zip(o["res"], oc["res"])]).style.format(precision=4, na_rep="—"), width="stretch", hide_index=True)
                except Exception as e:
                    st.error(str(e))
        with s3:
            c = o["cruce"]
            if c is None:
                st.info("Si quieres saber cuándo la señal llega a un valor, escríbelo en «Opciones avanzadas» de la pestaña 1.")
            elif not c["res"]:
                st.warning(f"La curva reconstruida (spline) no llega a {c['umbral']:g} dentro del intervalo.")
            else:
                st.caption(f"Instante en que la curva reconstruida (spline) vale {c['umbral']:g}. Valor correcto: {g(c['ref'], 12)}.")
                mostrar_raices(c["res"], "m4r")
        glosario()

with tab_i:
    if not S:
        st.info("Primero ejecuta una simulación.")
    else:
        interpretacion_y_guardado(engine, C["nombre"], S, M, "Sintético con ruido gaussiano (semilla fija) o datos ingresados por el usuario")
