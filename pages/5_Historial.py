import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import db, registro
from core.comun import comparar_vectores
from core.escenarios import TIPOS
from core.ui import AVISO, banner_bd

st.title("🗂️ Historial de experimentos")
st.caption(AVISO)
engine = banner_bd()
if engine is None:
    st.stop()

f1, f2, f3 = st.columns(3)
caso = f1.selectbox("Caso", [""] + db.CASOS, format_func=lambda v: v or "Todos")
tipo = f2.selectbox("Escenario", [""] + list(TIPOS), format_func=lambda v: (v or "Todos").replace("_", " "))
texto = f3.text_input("Buscar por equipo/usuario")
df = db.listar_simulaciones(engine, caso or None, tipo or None, texto or None)
st.dataframe(df, width="stretch", hide_index=True)
if df.empty:
    st.info("Aún no hay simulaciones guardadas. Ejecuta y guarda una en cualquier módulo.")
    st.stop()

sid = st.selectbox("Abrir simulación #", df["id"].tolist())
S = db.cargar_simulacion(engine, int(sid))
st.markdown(f"### Simulación #{S['id']} · {S['caso']} · {S['tipo'].replace('_', ' ')}")
st.caption(f"Fecha: {S['fecha']} · Equipo: {S['equipo'] or '—'} · Estado: {S['estado']} · Fuente: {S['fuente_datos']}")
with st.expander("Parámetros guardados (JSON)"):
    st.json(S["parametros_json"])


def _val(e, k):
    return (e["resumen"].get("valor_json") or {}).get(k)


def _met(e, k):
    return (e["resumen"].get("metrica_error_json") or {}).get(k)


filas = []
for e in S["ejecuciones"]:
    its = e["iteraciones"]
    ult = its[-1] if its else {}
    filas.append({"Método": e["metodo"], "Convergió": "sí" if e["convergio"] else "NO", "Tolerancia": e["tolerancia"], "Paso": e["paso"],
                  "Máx. iter": e["max_iter"], "Filas guardadas": len(its), "Residuo final": ult.get("residual"),
                  "Error abs final": ult.get("error_abs"), "Tiempo ms": None if e["tiempo_ms"] is None else round(e["tiempo_ms"], 3)})
st.dataframe(pd.DataFrame(filas).style.format({"Tolerancia": "{:.1e}", "Paso": "{:.4g}", "Residuo final": "{:.2e}", "Error abs final": "{:.2e}"}, na_rep="—"),
             width="stretch", hide_index=True)

# ---------------------------------------------------------------- gráficos recuperados de la base de datos
def _layout(fig, titulo, x, y, logy=False, logx=False):
    fig.update_layout(title=titulo, xaxis_title=x, yaxis_title=y, height=380, margin=dict(t=50, b=40), legend=dict(orientation="h", y=-0.25))
    if logy:
        fig.update_yaxes(type="log")
    if logx:
        fig.update_xaxes(type="log")
    return fig


grupos = {}
for e in S["ejecuciones"]:
    grupos.setdefault(_val(e, "grafico") or "iterativo", []).append(e)

for gr, ejs in grupos.items():
    if gr == "iterativo":
        fig = go.Figure()
        for e in ejs:
            pts = [(i["numero"], i["residual"]) for i in e["iteraciones"] if i["residual"] is not None]
            if len(pts) > 1:
                fig.add_scatter(x=[p[0] for p in pts], y=[max(p[1], 1e-20) for p in pts], name=e["metodo"], mode="lines+markers")
        st.plotly_chart(_layout(fig, "Convergencia: residuo vs iteración (recuperado de la BD)", "Iteración", "Residuo", logy=True), width="stretch", key=f"h_{gr}")
    elif gr == "edo":
        c1, c2 = st.columns(2)
        f1_, f2_ = go.Figure(), go.Figure()
        for e in ejs:
            its = [i for i in e["iteraciones"] if isinstance(i["aproximacion_json"], list)]
            t = [i["aproximacion_json"][0] for i in its]
            f1_.add_scatter(x=t, y=[i["aproximacion_json"][1] for i in its], name=e["metodo"], mode="lines")
            f2_.add_scatter(x=t, y=[max(i["error_abs"] or 1e-20, 1e-20) for i in its], name=e["metodo"], mode="lines")
        c1.plotly_chart(_layout(f1_, "Trayectoria x(t) (recuperada de la BD)", "t [s]", "x"), width="stretch", key="h_edo1")
        c2.plotly_chart(_layout(f2_, "Error vs t (recuperado de la BD)", "t [s]", "‖y − y_ref‖", logy=True), width="stretch", key="h_edo2")
    elif gr == "refinamiento":
        fig = go.Figure()
        for e in ejs:
            ns = _val(e, "n") or [i["numero"] for i in e["iteraciones"]]
            fig.add_scatter(x=ns, y=[max(i["error_abs"] or 1e-20, 1e-20) for i in e["iteraciones"]], name=e["metodo"], mode="lines+markers")
        st.plotly_chart(_layout(fig, "Refinamiento: error vs n (recuperado de la BD)", "n (subintervalos)", "Error absoluto", logy=True, logx=True), width="stretch", key="h_ref")
    elif gr == "interpolacion":
        fig = go.Figure()
        for e in ejs:
            fig.add_scatter(x=_val(e, "t_graf"), y=_val(e, "y_graf"), name=e["metodo"], mode="lines")
        e0 = ejs[0]
        fig.add_scatter(x=_val(e0, "t_nodos"), y=_val(e0, "y_nodos"), mode="markers", name="Nodos", marker=dict(color="black"))
        fig.add_scatter(x=_val(e0, "t_ocultos"), y=_val(e0, "y_ref_ocultos"), mode="markers", name="Ocultos (ref.)", marker=dict(symbol="x", size=12, color="red"))
        ys = np.array(_val(e0, "y_nodos") + _val(e0, "y_ref_ocultos"), float)
        rg = float(np.ptp(ys)) or 1.0
        fig.update_yaxes(range=[ys.min() - 1.5 * rg, ys.max() + 1.5 * rg])
        st.plotly_chart(_layout(fig, "Curvas reconstruidas (recuperadas de la BD)", "t", "y"), width="stretch", key="h_int")

interp = next((e["resumen"].get("interpretacion") for e in S["ejecuciones"] if e["resumen"].get("interpretacion")), None)
if interp:
    with st.expander("Interpretación guardada (conclusiones)"):
        st.markdown(interp.replace("\n", "  \n"))
with st.expander("Ver iteraciones guardadas de un método"):
    nom = st.selectbox("Método", [e["metodo"] for e in S["ejecuciones"]], key="h_met")
    e = next(e for e in S["ejecuciones"] if e["metodo"] == nom)
    st.dataframe(pd.DataFrame([{"numero": i["numero"], "aproximacion": str(i["aproximacion_json"])[:80], "residual": i["residual"],
                                "error_abs": i["error_abs"], "error_rel": i["error_rel"]} for i in e["iteraciones"]]),
                 width="stretch", hide_index=True)

# ---------------------------------------------------------------- relanzar
st.divider()
st.markdown("### 🔁 Relanzar y verificar coincidencia")
tol_c = st.select_slider("Tolerancia de coincidencia (relativa)", [10.0 ** -e for e in range(4, 15)], value=1e-8, format_func=lambda v: f"{v:.0e}")
if st.button("Repetir el cálculo con los parámetros guardados"):
    try:
        nuevas = registro.relanzar(S["caso"], S["parametros_json"])
    except Exception as ex:
        st.error(f"No se pudo relanzar: {ex}")
        st.stop()
    rows, ok_all = [], True
    for e, n in zip(S["ejecuciones"], nuevas):
        a = registro.vector_comparable(e["resumen"].get("valor_json"))
        b = registro.vector_comparable(n["resumen"]["valor"])
        mx, ok = comparar_vectores(a, b, tol_c)
        ok_all &= ok
        rows.append({"Método": e["metodo"], "Valores comparados": len(a), "Máx |guardado − nuevo|": mx, "Coincide": "✅" if ok else "❌"})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    (st.success if ok_all else st.error)("Los resultados recalculados coinciden con los guardados dentro de la tolerancia." if ok_all
                                         else "Hay diferencias fuera de la tolerancia.")
