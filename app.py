import streamlit as st
from core.ui import estilo, sidebar_marca

st.set_page_config(page_title="SIMTELE-RISK", page_icon="🚡", layout="wide")
estilo()

pg = st.navigation([
    st.Page("pages/0_Inicio.py", title="Inicio", icon="🏠", default=True),
    st.Page("pages/1_Detencion.py", title="Detención", icon="🛑"),
    st.Page("pages/2_Deterioro.py", title="Deterioro", icon="🔧"),
    st.Page("pages/3_Oscilaciones.py", title="Oscilaciones", icon="🌬️"),
    st.Page("pages/4_Sensores.py", title="Sensores", icon="📡"),
    st.Page("pages/5_Historial.py", title="Historial", icon="🗂️"),
])
sidebar_marca()
pg.run()
