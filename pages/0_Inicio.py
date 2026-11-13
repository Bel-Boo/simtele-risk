import streamlit as st
from core.casos import CASOS
from core.ui import AVISO, COLORES, banner_bd

st.title("🚡 SIMTELE-RISK")
st.subheader("Desafío integrador · Métodos Numéricos")
st.caption(AVISO)
banner_bd()

cols = st.columns(2)
for i, (clave, c) in enumerate(CASOS.items()):
    with cols[i % 2].container(border=True):
        st.markdown(f'<div style="height:7px;border-radius:7px;background:{COLORES[clave]};margin-bottom:10px"></div>',
                    unsafe_allow_html=True)
        st.markdown(f"### {c['icono']} {c['nombre']}")
        st.write(c["pregunta"])
        st.caption("Métodos: " + ", ".join(c["metodos"][:5]) + ("…" if len(c["metodos"]) > 5 else ""))
        st.caption(f"Estado: {c['estado']}")
        st.page_link(c["pagina"], label="Abrir módulo", icon="➡️")

st.divider()
st.page_link("pages/5_Historial.py", label="Historial de experimentos", icon="🗂️")
