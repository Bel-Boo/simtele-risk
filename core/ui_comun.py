"""Componentes Streamlit compartidos por los módulos 1-4 (entradas libres, tablas, guardado)."""
import numpy as np
import pandas as pd
import streamlit as st

from . import db
from .comun import fig_iterativo, g


class Entrada:
    """Campos de entrada con valores iniciales del escenario, SIEMPRE editables (el usuario escribe lo que quiera).
    Los decimales aceptan punto o coma y la notación científica (1e-8)."""

    def __init__(self, P, tipo, pref):
        self.P, self.tipo, self.pref, self.errores = P, tipo, pref, []

    def restablecer(self):
        """Botón que devuelve TODOS los campos de este escenario a sus valores iniciales."""
        if st.button("↺ Restablecer los valores de este escenario", key=f"rst_{self.pref}_{self.tipo}",
                     help="Borra tus cambios y vuelve a los números originales del escenario."):
            for k in [k for k in st.session_state if str(k).startswith(f"{self.pref}_") and str(k).endswith(f"_{self.tipo}")]:
                del st.session_state[k]
            st.rerun()

    def _k(self, campo):
        return f"{self.pref}_{campo}_{self.tipo}"

    def f(self, label, campo, help=None, positivo=False):
        s = st.text_input(label, value=str(self.P[campo]), key=self._k(campo), help=help)
        try:
            v = float(s.strip().replace(",", "."))
            if not np.isfinite(v):
                raise ValueError
            if positivo and v <= 0:
                self.errores.append(f"«{label}» debe ser > 0.")
            return v
        except ValueError:
            self.errores.append(f"«{label}»: '{s}' no es un número válido.")
            return float(self.P[campo])

    def i(self, label, campo, mn, mx, help=None):
        return int(st.number_input(label, mn, mx, int(self.P[campo]), step=1, key=self._k(campo), help=help))

    def t(self, label, campo, help=None, area=False, height=120):
        if area:
            return st.text_area(label, value=str(self.P[campo]), key=self._k(campo), help=help, height=height)
        return st.text_input(label, value=str(self.P[campo]), key=self._k(campo), help=help)

    def sel(self, label, campo, opciones, fmt=None, horizontal=False, help=None):
        idx = opciones.index(self.P[campo]) if self.P[campo] in opciones else 0
        if horizontal:
            return st.radio(label, opciones, index=idx, key=self._k(campo), horizontal=True,
                            format_func=fmt or str, help=help)
        return st.selectbox(label, opciones, index=idx, key=self._k(campo), format_func=fmt or str, help=help)

    def slider(self, label, campo, mn, mx, help=None):
        return st.slider(label, mn, mx, int(self.P[campo]), key=self._k(campo), help=help)


def _fmt_df(df, cols_e):
    return df.style.format({c: "{:.3e}" for c in cols_e if c in df.columns}, na_rep="—")


def df_raices(res):
    filas = []
    for r in res:
        u = r["historial"][-1]
        filas.append({"Método": r["metodo"], "Convergió": "sí" if r["convergio"] else "NO", "Iteraciones": r["iteraciones"],
                      "Raíz": r["x"] if np.isfinite(r["x"]) else None, "Error abs": u["error_abs"], "Residuo |f|": u["residual"],
                      "Orden observado": r["extra"].get("orden"), "Tiempo (ms)": round(r["tiempo_ms"], 3),
                      "Criterio de parada": r["motivo_parada"]})
    return pd.DataFrame(filas)


def mostrar_raices(res, key):
    df = df_raices(res)
    st.dataframe(df.style.format({"Raíz": "{:.10g}", "Error abs": "{:.3e}", "Residuo |f|": "{:.3e}", "Orden observado": "{:.2f}"},
                                 na_rep="—"), width="stretch", hide_index=True)
    c1, c2 = st.columns(2)
    c1.plotly_chart(fig_iterativo(res, "error_abs", "Error |x_k − x*| por iteración"), width="stretch", key=f"{key}_e")
    c2.plotly_chart(fig_iterativo(res, "residual", "Residuo |f(x_k)| por iteración"), width="stretch", key=f"{key}_r")
    with st.expander("Tabla de iteraciones"):
        nom = st.selectbox("Método", [r["metodo"] for r in res], key=f"{key}_sel")
        r = next(r for r in res if r["metodo"] == nom)
        filas = [{"k": h["numero"], "x_k": h["aproximacion"], "f(x_k)": h["fx"], "|f(x_k)|": h["residual"],
                  "error abs": h["error_abs"], "error rel": h["error_rel"],
                  **({"a": h["a"], "b": h["b"]} if "a" in h else {})} for h in r["historial"]]
        st.dataframe(_fmt_df(pd.DataFrame(filas), ["f(x_k)", "|f(x_k)|", "error abs", "error rel"]), width="stretch", hide_index=True)


def df_refinamiento(tabla):
    filas = []
    for f in tabla:
        fila = {"k": f["k"], "n": f["n"], "h": f["h"]}
        for nom, corto in (("Trapecio compuesto", "Trapecio"), ("Simpson 1/3 compuesto", "Simpson"), ("Romberg", "Romberg")):
            fila[f"{corto}"] = f[nom]["valor"]
            fila[f"err {corto}"] = f[nom]["error_abs"]
        filas.append(fila)
    return pd.DataFrame(filas)


def mostrar_refinamiento(tabla, R=None):
    df = df_refinamiento(tabla)
    st.dataframe(df.style.format({c: "{:.3e}" for c in df.columns if c.startswith("err")} | {"h": "{:.4g}",
                 "Trapecio": "{:.10g}", "Simpson": "{:.10g}", "Romberg": "{:.10g}"}, na_rep="—"), width="stretch", hide_index=True)
    if R is not None:
        with st.expander("Tabla de Romberg R[i][j] (columna j = extrapolación de Richardson de orden 2j+2)"):
            st.dataframe(pd.DataFrame(np.where(np.tril(np.ones_like(R)) > 0, R, np.nan)).style.format("{:.10g}", na_rep=""),
                         width="stretch")


def interpretacion_y_guardado(engine, caso, S, mod, fuente):
    """Pestaña de interpretación: dos conclusiones separadas (editables) + guardado en la base de datos."""
    rid = S["id"]
    st.info("Aquí se explican los resultados. Los textos son **borradores automáticos**: léelos, corrígelos con tus palabras y luego guarda. "
            "Son dos conclusiones distintas: una sobre **los métodos de cálculo** y otra sobre **el problema que se simula**.")
    st.markdown("### 1) Conclusión de los MÉTODOS (¿qué método funcionó mejor y por qué?)")
    c_num = st.text_area("Editable", mod.conclusion_numerica(S["out"]), height=260, key=f"cn_{caso}_{rid}")
    st.markdown("### 2) Conclusión del PROBLEMA (¿qué significa el resultado en la vida real y qué no se puede asegurar?)")
    c_pro = st.text_area("Editable", mod.conclusion_problema(S["out"]), height=260, key=f"cp_{caso}_{rid}")
    st.divider()
    st.text_input("Tu nombre o equipo (opcional, ayuda a encontrar el experimento en el Historial)", key="equipo")
    if engine is None:
        st.warning("Sin base de datos: no se puede guardar.")
    elif S.get("guardada"):
        st.success(f"Guardada como simulación #{S['guardada']}. Ábrela en **Historial**.")
    elif st.button("💾 Guardar este experimento", key=f"save_{caso}_{rid}"):
        texto = f"## CONCLUSIÓN NUMÉRICA\n{c_num}\n\n## CONCLUSIÓN DEL PROBLEMA\n{c_pro}"
        S["guardada"] = db.guardar_simulacion(engine, caso, S["tipo"], S["params"], fuente,
                                              mod.ejecuciones(S["params"], texto, out=S["out"]),
                                              equipo=st.session_state.get("equipo") or None)
        st.rerun()


def ejecutar(clave, tipo, params, mod):
    """Botón de ejecución común; guarda el resultado en session_state[clave]."""
    err = mod.validar(params)
    if err:
        st.error(err)
    if st.button("▶ Ejecutar", type="primary", disabled=bool(err), key=f"run_{clave}"):
        try:
            with st.spinner("Calculando…"):
                st.session_state[clave] = {"tipo": tipo, "params": params, "out": mod.correr(params),
                                           "id": st.session_state.get(clave, {}).get("id", 0) + 1, "guardada": None}
            st.success("✅ Listo. Ahora abre la pestaña «2 · Resultados».")
        except Exception as e:  # mensaje claro al usuario, sin tumbar la app
            st.error(f"No se pudo calcular: {e}")
