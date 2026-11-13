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


COLORES = {"detencion": "#ff4d4f", "deterioro": "#faad14", "oscilaciones": "#36cfc9", "sensores": "#4096ff"}
_NAV = ["#f472b6", "#ff4d4f", "#faad14", "#36cfc9", "#4096ff", "#b37feb"]


def estilo():
    """CSS global: barra lateral con degradado, enlaces de colores, tarjetas y botones."""
    nav = "\n".join(
        f'[data-testid="stSidebarNav"] li:nth-child({i}) a{{border-left-color:{c} !important;}}'
        f'\n[data-testid="stSidebarNav"] li:nth-child({i}) a[aria-current="page"]'
        f'{{background:linear-gradient(90deg,{c}55,{c}11) !important;}}'
        for i, c in enumerate(_NAV, start=1))
    st.markdown(f"""
<style>
[data-testid="stSidebar"]{{background:linear-gradient(190deg,#0b1020 0%,#1b1446 55%,#3b1d6e 100%);
  border-right:1px solid rgba(255,255,255,.08);}}
[data-testid="stSidebarNav"] a{{border-radius:12px;margin:5px 0;padding:.6rem .85rem;
  border-left:6px solid transparent;background:rgba(255,255,255,.05);transition:all .15s ease;}}
[data-testid="stSidebarNav"] a:hover{{background:rgba(255,255,255,.14);transform:translateX(4px);}}
[data-testid="stSidebarNav"] a[aria-current="page"]{{font-weight:700;box-shadow:0 0 14px rgba(255,255,255,.10);}}
{nav}
h1{{background:linear-gradient(90deg,#ff7eb3,#a78bfa,#38bdf8);-webkit-background-clip:text;
  background-clip:text;-webkit-text-fill-color:transparent;font-weight:800 !important;}}
[data-testid="stMetric"]{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.12);
  border-radius:14px;padding:12px 16px;}}
[data-testid="stVerticalBlockBorderWrapper"]{{border-radius:16px;}}
button[kind="primary"]{{background:linear-gradient(90deg,#ff4d6d,#8b5cf6);border:0;color:white;font-weight:700;}}
button[kind="primary"]:hover{{filter:brightness(1.15);}}
button[data-baseweb="tab"]{{font-weight:600;}}
.marca{{padding:.9rem 1rem;border-radius:14px;margin-top:1rem;
  background:linear-gradient(135deg,#ff4d6d33,#8b5cf633,#38bdf833);border:1px solid rgba(255,255,255,.15);}}
.marca b{{font-size:1.15rem;}}
.chip{{display:inline-block;padding:2px 10px;margin:2px 3px 2px 0;border-radius:999px;font-size:.75rem;
  font-weight:600;color:#0b1020;}}
</style>""", unsafe_allow_html=True)


def sidebar_marca():
    chips = "".join(f'<span class="chip" style="background:{c}">{t}</span>' for t, c in
                    [("NORMAL", "#4ade80"), ("ESTRÉS", "#facc15"), ("MAL COND.", "#f87171")])
    st.sidebar.markdown(
        f'<div class="marca"><b>🚡 SIMTELE-RISK</b><br><small>Métodos Numéricos · uso educativo</small>'
        f'<br><div style="margin-top:6px">{chips}</div></div>', unsafe_allow_html=True)
