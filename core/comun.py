"""Utilidades comunes (sin Streamlit): formato de resultados para la BD y gráficos."""
import numpy as np
import plotly.graph_objects as go


def g(x, d=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{x:.{d}g}"


def ejecucion(res, referencia, valor, metricas=None, interpretacion="", paso=None):
    """Convierte un resultado de método al formato que guarda db.guardar_simulacion."""
    return {"metodo": res["metodo"], "tolerancia": res.get("tolerancia"), "paso": paso,
            "max_iter": res.get("max_iter"), "convergio": bool(res["convergio"]), "tiempo_ms": res.get("tiempo_ms"),
            "historial": res["historial"],
            "resumen": {"referencia": referencia, "valor": valor, "metricas": metricas or {},
                        "interpretacion": interpretacion}}


def orden_de_tabla(filas, nombre):
    """Orden observado p = log2(e_k / e_{k+1}) con los dos últimos refinamientos (n se duplica)."""
    e = [f[nombre]["error_abs"] for f in filas if f[nombre]["error_abs"] is not None]
    if len(e) >= 2 and e[-1] > 1e-14 and e[-2] > 1e-14:
        return float(np.log2(e[-2] / e[-1]))
    return None


def comparar_vectores(a, b, tol=1e-8):
    """Compara dos listas (None = NaN). Devuelve (máx_dif, coincide)."""
    A = np.array([np.nan if v is None else v for v in a], float)
    B = np.array([np.nan if v is None else v for v in b], float)
    if A.shape != B.shape:
        return float("nan"), False
    ambos_nan = np.isnan(A) & np.isnan(B)
    d = np.where(ambos_nan, 0.0, np.abs(A - B))
    mx = float(np.nanmax(d)) if d.size else 0.0
    return mx, bool(np.all(np.isfinite(d)) and mx <= tol * max(1.0, float(np.nanmax(np.abs(B))) if B.size else 1.0))


# ------------------------------------------------------------------ gráficos
def _lay(fig, titulo, x, y, logy=False, logx=False, h=380):
    fig.update_layout(title=titulo, xaxis_title=x, yaxis_title=y, height=h, margin=dict(t=50, b=40),
                      legend=dict(orientation="h", y=-0.25))
    if logy:
        fig.update_yaxes(type="log")
    if logx:
        fig.update_xaxes(type="log")
    return fig


def fig_iterativo(resultados, campo="residual", titulo="Convergencia"):
    fig = go.Figure()
    for r in resultados:
        h = [p for p in r["historial"] if p.get(campo) is not None]
        if len(h) >= 2:
            fig.add_scatter(x=[p["numero"] for p in h], y=[max(p[campo], 1e-20) for p in h], mode="lines+markers",
                            name=r["metodo"])
    return _lay(fig, titulo, "Iteración", "Residuo |f(x)|" if campo == "residual" else "Error absoluto", logy=True)


def fig_trayectorias(series, titulo, xlab="t [s]", ylab="", referencia=None):
    """series: {nombre: (t, y)}; referencia: (t, y) en línea gruesa."""
    fig = go.Figure()
    if referencia is not None:
        fig.add_scatter(x=referencia[0], y=referencia[1], mode="lines", name="Referencia", line=dict(width=4, color="gray"))
    for n, (t, y) in series.items():
        fig.add_scatter(x=t, y=y, mode="lines", name=n, line=dict(dash="dash"))
    return _lay(fig, titulo, xlab, ylab)


def fig_errores_tiempo(series, titulo="Error respecto de la referencia"):
    fig = go.Figure()
    for n, (t, e) in series.items():
        fig.add_scatter(x=t, y=np.maximum(e, 1e-20), mode="lines", name=n)
    return _lay(fig, titulo, "t [s]", "‖y − y_ref‖₂", logy=True)


def fig_refinamiento(filas, titulo="Error vs número de subintervalos"):
    fig = go.Figure()
    for nombre in ("Trapecio compuesto", "Simpson 1/3 compuesto", "Romberg"):
        pts = [(f["n"], f[nombre]["error_abs"]) for f in filas if f[nombre]["error_abs"] is not None]
        if pts:
            fig.add_scatter(x=[p[0] for p in pts], y=[max(p[1], 1e-20) for p in pts], mode="lines+markers", name=nombre)
    return _lay(fig, titulo, "n (subintervalos)", "Error absoluto", logy=True, logx=True)


def fig_convergencia_paso(filas, titulo="Orden de convergencia RK (error en t_f vs h)"):
    fig = go.Figure()
    for m, nom in (("rk2", "RK2"), ("rk4", "RK4")):
        pts = [(f["h"], f[m]) for f in filas if f[m] > 0]
        fig.add_scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines+markers", name=nom)
    return _lay(fig, titulo, "paso h [s]", "Error en t_f", logy=True, logx=True)
