import streamlit as st

from core.ayuda import PASOS, QUE_HACE, glosario
from core.casos import CASOS
from core.ui import AVISO, COLORES, banner_bd

st.title("🚡 SIMTELE-RISK")
st.subheader("Simulador educativo de métodos numéricos")
st.caption(AVISO)
banner_bd()

st.markdown("**¿Qué es esto?** Una herramienta para probar, con datos inventados, cómo se calculan cosas como *cuánto tarda en frenar una cabina*, "
            "*cuándo habría que inspeccionar un equipo*, *cuánto se balancea con el viento* o *cómo rellenar datos perdidos de un sensor*. "
            "Cada módulo indica qué datos ingresar y cómo interpretar el resultado.")
with st.container(border=True):
    st.markdown("##### Cómo empezar (3 pasos)")
    st.markdown("1️⃣ Elige uno de los **4 módulos** de abajo (o del menú de la izquierda).  \n"
                "2️⃣ Escoge un escenario y pulsa **▶ Ejecutar**: ya traen valores de ejemplo que se pueden ejecutar de inmediato.  \n"
                "3️⃣ Lee el **resumen** en palabras simples, y si quieres, cambia los números, guarda el experimento y recupéralo en **Historial**.")

cols = st.columns(2)
for i, (clave, c) in enumerate(CASOS.items()):
    with cols[i % 2].container(border=True):
        st.markdown(f'<div style="height:7px;border-radius:7px;background:{COLORES[clave]};margin-bottom:10px"></div>', unsafe_allow_html=True)
        st.markdown(f"### {c['icono']} {c['nombre']}")
        st.write(QUE_HACE[clave][0])
        st.page_link(c["pagina"], label="Abrir módulo", icon="➡️")

st.divider()
st.page_link("pages/5_Historial.py", label="Historial: volver a abrir experimentos guardados", icon="🗂️")
glosario()
