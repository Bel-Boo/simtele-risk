"""Utilidades compartidas de la interfaz Streamlit."""
import streamlit as st
from .casos import CASOS

AVISO = ("⚠️ Sistema **estrictamente educativo**. Los datos y parámetros son **sintéticos/hipotéticos** y no "
         "describen fallas verificadas de Mi Teleférico ni tienen conexión con equipos de control reales.")


@st.cache_resource(show_spinner="Conectando con la base de datos…")
def obtener_engine():
    from .db import get_engine
    try:
        return get_engine(), None
    except Exception as e:  # la app sigue funcionando sin BD, pero sin guardar
        return None, str(e)


def banner_bd():
    engine, err = obtener_engine()
    if engine is None:
        st.error(f"No hay conexión con la base de datos; no se podrá guardar ni abrir el historial.\n\n`{err}`")
    else:
        st.sidebar.caption(f"🗄️ Base de datos: **{engine.dialect.name}**")
    return engine


def pagina_pendiente(clave):
    """Pantalla de un módulo que aún no se implementa (prototipo Semana 1)."""
    c = CASOS[clave]
    st.title(f"{c['icono']} {c['nombre']}")
    st.caption(AVISO)
    banner_bd()
    st.info(f"Módulo visible en el prototipo. Estado: **{c['estado']}**.")
    t1, t2 = st.tabs(["Modelo", "Escenarios definidos"])
    with t1:
        st.markdown(f"**Pregunta:** {c['pregunta']}")
        st.latex(c["modelo"])
        st.markdown(f"**Variables y unidades:** {c['variables']}")
        st.markdown(f"**Referencia analítica:** {c['analitico']}")
        st.markdown("**Métodos que se usarán:** " + ", ".join(c["metodos"]))
    with t2:
        for tipo, desc in c["escenarios"].items():
            st.markdown(f"**{tipo.replace('_', ' ')}** — {desc}")


COLORES = {"detencion": "#e11d2e", "deterioro": "#f5f5f5", "oscilaciones": "#9ca3af", "sensores": "#7f1d1d"}


def estilo():
    """CSS global: paleta negro / blanco / gris / rojo."""
    st.markdown("""
<style>
[data-testid="stSidebar"]{background:linear-gradient(190deg,#000000 0%,#0f0f10 60%,#1c1c1e 100%);
  border-right:1px solid rgba(255,255,255,.10);}
[data-testid="stSidebarNav"] a{border-radius:10px;margin:5px 0;padding:.6rem .85rem;
  border-left:6px solid #4b5563;background:rgba(255,255,255,.05);transition:all .15s ease;}
[data-testid="stSidebarNav"] a:hover{background:rgba(255,255,255,.14);border-left-color:#f5f5f5;transform:translateX(4px);}
[data-testid="stSidebarNav"] a[aria-current="page"]{font-weight:700;border-left-color:#e11d2e;
  background:linear-gradient(90deg,rgba(225,29,46,.38),rgba(225,29,46,.06));}
h1{background:linear-gradient(90deg,#ffffff,#d1d5db 55%,#ef4444);-webkit-background-clip:text;
  background-clip:text;-webkit-text-fill-color:transparent;font-weight:800 !important;}
[data-testid="stMetric"]{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.14);
  border-left:4px solid #e11d2e;border-radius:10px;padding:12px 16px;}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px;}
button[kind="primary"]{background:linear-gradient(90deg,#e11d2e,#8f1220);border:0;color:#fff;font-weight:700;}
button[kind="primary"]:hover{filter:brightness(1.2);}
button[data-baseweb="tab"]{font-weight:600;}
.marca{padding:.9rem 1rem;border-radius:12px;margin-top:1rem;
  background:linear-gradient(135deg,rgba(225,29,46,.25),rgba(255,255,255,.05));border:1px solid rgba(255,255,255,.18);}
.marca b{font-size:1.15rem;}
.chip{display:inline-block;padding:2px 10px;margin:2px 3px 2px 0;border-radius:999px;font-size:.75rem;font-weight:700;}
</style>""", unsafe_allow_html=True)


def sidebar_marca():
    chips = "".join(f'<span class="chip" style="background:{bg};color:{fg}">{t}</span>' for t, bg, fg in
                    [("NORMAL", "#f5f5f5", "#0a0a0a"), ("ESTRÉS", "#9ca3af", "#0a0a0a"), ("MAL COND.", "#e11d2e", "#ffffff")])
    st.sidebar.markdown(
        f'<div class="marca"><b>🚡 SIMTELE-RISK</b><br><small>Métodos Numéricos · uso educativo</small>'
        f'<br><div style="margin-top:6px">{chips}</div></div>', unsafe_allow_html=True)
