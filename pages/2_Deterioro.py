import numpy as np
import streamlit as st

from core import modulo2, resumen
from core.ayuda import glosario, guia, mostrar_resumen, selector_escenario
from core.casos import CASOS
from core.escenarios import EJEMPLO_MATRIZ, PARAMS_DEFECTO, parsear_matriz, parsear_vector, validar_matriz
from core.graficos import fig_convergencia, fig_errores, fig_solucion, tabla_metodos
from core.sistemas_lineales import diagnostico
from core.ui import AVISO, banner_bd
from core.ui_comun import interpretacion_y_guardado

C = CASOS["deterioro"]
st.title(f"{C['icono']} {C['nombre']}")
st.caption(AVISO)
engine = banner_bd()
guia("deterioro")

sub = st.radio("¿Qué parte quieres usar?", ["Raíces: ¿cuándo se alcanza el umbral?", "Sistemas lineales: cálculo de calibración"], horizontal=True)
if sub.startswith("Raíces"):
    from core.ui_deterioro import render_raices
    render_raices(engine)
    st.stop()

MATRICES_TXT = {"tridiagonal_dd": "Sencilla y estable (ejemplo que se resuelve fácil)", "poisson1d": "Grande y lenta de resolver (ejemplo exigente)",
                "hilbert": "Matriz de Hilbert (muy sensible; ejemplo delicado)", "personalizada": "La escribo yo"}


class _Lineal:  # adaptador para reutilizar el bloque de interpretación y guardado
    @staticmethod
    def conclusion_numerica(out):
        return modulo2.conclusion_numerica(out, out["_tipo"])

    @staticmethod
    def conclusion_problema(out):
        return modulo2.conclusion_problema(out, out["_tipo"], out["_params"])

    @staticmethod
    def ejecuciones(p, texto, out=None):
        return modulo2.a_ejecuciones(out, p, texto)


tab_modelo, tab_res, tab_interp = st.tabs(["1 · Datos de entrada", "2 · Resultados", "3 · Interpretación y guardado"])

with tab_modelo:
    st.markdown("**Qué se calcula:** un sistema de ecuaciones **A·x = b** (como el que sale al calibrar el modelo de deterioro con datos). "
                "Se construye a partir de una respuesta x conocida (x = 1, 2, 3…), así la app puede medir el error real de cada método: "
                "referencia directa, LU, Jacobi, Gauss-Seidel y gradiente conjugado.")
    tipo = selector_escenario()
    st.info(C["escenarios"][tipo])
    base = PARAMS_DEFECTO[tipo]
    k = tipo
    st.markdown("##### Datos básicos")
    c1, c2 = st.columns(2)
    claves = list(MATRICES_TXT)
    matriz = c1.selectbox("Tipo de matriz A", claves, index=claves.index(base["matriz"]), format_func=MATRICES_TXT.get, key=f"mat_{k}")
    n = base["n"]
    if matriz == "personalizada":
        c2.caption("El tamaño será el de la matriz que escribas abajo.")
    else:
        n = c2.number_input("Cantidad de ecuaciones n (mínimo 4)", 4, 200, base["n"], step=1, key=f"n_{k}")
    with st.expander("⚙️ Opciones avanzadas (puedes dejarlas como están)"):
        c3, c4, c5 = st.columns(3)
        tol = c3.select_slider("Precisión exigida", [10.0 ** -e for e in range(2, 15)], value=base["tol"], format_func=lambda v: f"{v:.0e}", key=f"tol_{k}")
        max_iter = c4.number_input("Máximo de iteraciones (intentos)", 10, 100000, base["max_iter"], step=100, key=f"mi_{k}")
        eps_sens = c5.select_slider("Cambio de prueba para sensibilidad", [10.0 ** -e for e in range(1, 13)], value=base["eps_sens"],
                                    format_func=lambda v: f"{v:.0e}", key=f"es_{k}")
    params = {"matriz": matriz, "n": int(n), "tol": float(tol), "max_iter": int(max_iter), "eps_sens": float(eps_sens)}
    matriz_ok = True
    if matriz == "personalizada":
        st.markdown("##### Tu matriz A")
        txt = st.text_area("Una fila por línea, con los números separados por espacios (mínimo 4×4, cuadrada). También vale [[1,2],[3,4]] y fracciones como 1/3.",
                           EJEMPLO_MATRIZ, height=170, key=f"A_{k}")
        xtxt = st.text_input("Respuesta x conocida (opcional; vacío = 1, 2, 3, …)", key=f"xs_{k}")
        try:
            Ac = parsear_matriz(txt)
            xc = parsear_vector(xtxt) if xtxt.strip() else None
            validar_matriz(Ac, xc)
            params["A"], params["n"] = Ac.tolist(), int(Ac.shape[0])
            if xc is not None:
                params["x_star"] = xc.tolist()
            dg = diagnostico(Ac)
            st.success(f"Matriz {dg['n']}×{dg['n']} válida · κ(A) = {dg['kappa']:.3e} · {'SPD' if dg['spd'] else 'NO SPD'} · "
                       f"{'diagonalmente dominante' if dg['diag_dominante'] else 'no diagonalmente dominante'}")
            if not dg["spd"]:
                st.warning("La matriz no es simétrica definida positiva (SPD): el gradiente conjugado no tiene garantía de funcionar. Se ejecuta igual y se reporta lo que pase.")
        except ValueError as e:
            matriz_ok = False
            st.error(str(e))
    if st.button("↺ Restablecer los valores de este escenario", key=f"rst_lin_{k}"):
        for key in [kk for kk in st.session_state if str(kk).endswith(f"_{k}") and str(kk).split("_")[0] in ("mat", "n", "tol", "mi", "es", "A", "xs")]:
            del st.session_state[key]
        st.rerun()
    if st.button("▶ Ejecutar los 5 métodos", type="primary", disabled=not matriz_ok):
        try:
            with st.spinner("Calculando…"):
                out = modulo2.correr(params)
                out["_tipo"], out["_params"] = tipo, params
                st.session_state["m2"] = {"tipo": tipo, "params": params, "out": out, "id": st.session_state.get("m2", {}).get("id", 0) + 1, "guardada": None}
            st.success("✅ Listo. Ahora abre la pestaña «2 · Resultados».")
        except Exception as e:
            st.error(f"Error en el cálculo: {e}")

M = st.session_state.get("m2")

with tab_res:
    if not M:
        st.info("Primero pulsa **▶ Ejecutar** en la pestaña «1 · Datos de entrada».")
    else:
        out, d, s = M["out"], M["out"]["diag"], M["out"]["sens"]
        st.markdown(f"#### Escenario {M['tipo'].replace('_', ' ')} · {MATRICES_TXT[M['params']['matriz']]} · n = {d['n']}")
        mostrar_resumen(resumen.m2l(out, M["tipo"]))
        m = st.columns(4)
        m[0].metric("κ(A): sensibilidad del sistema", f"{d['kappa']:.3e}", help="Cuanto más grande, más sensible: pequeños errores en los datos se amplifican.")
        m[1].metric("¿A es SPD?", "sí" if d["spd"] else "no")
        m[2].metric("ρ de Jacobi", f"{d['rho_jacobi']:.4f}", help="Si es menor que 1, Jacobi converge.")
        m[3].metric("ρ de Gauss-Seidel", f"{d['rho_gauss_seidel']:.4f}", help="Si es menor que 1, Gauss-Seidel converge.")
        st.markdown("### 🔬 Detalles técnicos")
        st.caption(f"Diagonalmente dominante: **{'sí' if d['diag_dominante'] else 'no'}** (si es sí, Jacobi y Gauss-Seidel convergen seguro). Si A es SPD, Gauss-Seidel y el gradiente conjugado convergen.")
        st.dataframe(tabla_metodos(out["res"]).style.format({"Residuo ‖b−Ax‖": "{:.2e}", "Error abs ‖x*−x‖": "{:.2e}", "Error rel": "{:.2e}", "Error %": "{:.2e}"}, na_rep="—"),
                     width="stretch", hide_index=True)
        g1, g2 = st.columns(2)
        g1.plotly_chart(fig_convergencia(out["res"]), width="stretch")
        g2.plotly_chart(fig_errores(out["res"]), width="stretch")
        st.caption("Cómo leerlo: a la izquierda, cada línea es un método iterativo; si baja, se acerca a la respuesta. A la derecha, barras más bajas = mejor.")
        st.plotly_chart(fig_solucion(out["res"], out["x_star"]), width="stretch")
        st.caption("Cómo leerlo: la línea gruesa es la respuesta exacta; los puntos de cada método deberían caer sobre ella.")
        st.markdown("**Sensibilidad:** qué pasa si cambias un poquito los datos b (resuelto con LU)")
        st.table({"Cambio relativo en b": [f"{s['cambio_rel_b']:.2e}"], "Cambio relativo en la respuesta": [f"{s['cambio_rel_x']:.2e}"],
                  "Amplificación": [f"{s['amplificacion']:.2f}"], "Máximo posible (κ)": [f"{s['cota_kappa']:.2e}"]})
        with st.expander("Ver los factores de LU (P·A = L·U)" + (" — solo si n ≤ 8" if d["n"] > 8 else "")):
            if d["n"] <= 8:
                ex = out["res"][1]["extra"]
                st.write("Permutación P:", ex["P"])
                st.write("L"); st.dataframe(ex["L"])
                st.write("U"); st.dataframe(ex["U"])
            else:
                st.write("Usa n ≤ 8 para visualizar los factores.")
        with st.expander("Ver las iteraciones (primeras 50) de un método"):
            nom = st.selectbox("Método", [r["metodo"] for r in out["res"]])
            r = next(r for r in out["res"] if r["metodo"] == nom)
            st.dataframe([{"k": h["numero"], "residuo": h["residual"], "error_abs": h["error_abs"], "error_rel": h["error_rel"],
                           "x": np.round(h["aproximacion"], 6).tolist()} for h in r["historial"][:50]], width="stretch", hide_index=True)
        glosario()

with tab_interp:
    if not M:
        st.info("Primero ejecuta una simulación.")
    else:
        interpretacion_y_guardado(engine, C["nombre"], M, _Lineal, "Sintético: A construida por fórmula o ingresada por el usuario; b = A·x*")
