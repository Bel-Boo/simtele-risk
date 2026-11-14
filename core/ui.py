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


COLORES = {"detencion": "#4b5563", "deterioro": "#6b7280", "oscilaciones": "#9ca3af", "sensores": "#78716c"}


def estilo():
    """CSS neutro (grises translúcidos): se ve bien en modo claro Y oscuro."""
    st.markdown("""
<style>
[data-testid="stSidebarNav"] a{border-radius:10px;margin:5px 0;padding:.6rem .85rem;
  border-left:6px solid rgba(128,128,128,.55);background:rgba(128,128,128,.10);transition:all .15s ease;}
[data-testid="stSidebarNav"] a:hover{background:rgba(128,128,128,.24);border-left-color:currentColor;transform:translateX(4px);}
[data-testid="stSidebarNav"] a[aria-current="page"]{font-weight:800;border-left-color:currentColor;
  background:rgba(128,128,128,.30);}
h1{font-weight:800 !important;letter-spacing:-.5px;}
[data-testid="stMetric"]{background:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.35);
  border-left:5px solid rgba(128,128,128,.9);border-radius:10px;padding:12px 16px;}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px;}
button[kind="primary"]{font-weight:700;border-radius:10px;}
button[data-baseweb="tab"]{font-weight:600;}
.marca{padding:.9rem 1rem;border-radius:12px;margin-top:1rem;
  background:rgba(128,128,128,.14);border:1px solid rgba(128,128,128,.40);}
.marca b{font-size:1.15rem;}
.chip{display:inline-block;padding:2px 10px;margin:2px 3px 2px 0;border-radius:999px;font-size:.75rem;
  font-weight:700;border:1px solid rgba(128,128,128,.7);}
.chip-n{background:#f5f5f5;color:#111;}
.chip-e{background:#9ca3af;color:#111;}
.chip-m{background:#111;color:#f5f5f5;}
</style>""", unsafe_allow_html=True)


def sidebar_marca():
    st.sidebar.markdown(
        '<div class="marca"><b>🚡 SIMTELE-RISK</b><br><small>Métodos Numéricos · uso educativo</small>'
        '<br><div style="margin-top:6px"><span class="chip chip-n">NORMAL</span>'
        '<span class="chip chip-e">ESTRÉS</span><span class="chip chip-m">MAL COND.</span></div></div>',
        unsafe_allow_html=True)
