"""Textos de ayuda en lenguaje simple: guía de uso, glosario y presentación del resumen."""
import streamlit as st

ESC_TXT = {"NORMAL": "NORMAL · caso típico", "ESTRÉS": "ESTRÉS · caso exigente", "MAL_CONDICIONADO": "MAL CONDICIONADO · caso delicado"}
ESC_EXPLICA = ("**NORMAL**: valores típicos, todo debería salir bien. · **ESTRÉS**: condiciones más duras (más tiempo, pasos grandes, ruido…) "
               "para ver cuándo empiezan los errores. · **MAL CONDICIONADO**: un problema matemáticamente *delicado*, donde cambios mínimos "
               "en los datos dan resultados muy distintos. *No significa que sea peligroso ni que el programa falle.*")

QUE_HACE = {
    "detencion": ("Simula el frenado de emergencia de una cabina y responde: **¿cuánto tarda en detenerse y cuántos metros recorre?** "
                  "¿Alcanza a parar antes de un obstáculo?",
                  "Datos básicos: velocidad, tiempo de reacción y fuerza de frenado. El resto de parámetros está en «Opciones avanzadas»."),
    "deterioro": ("Estima **en qué día un indicador de desgaste (inventado) llegaría al límite de inspección** y qué pasa si el mantenimiento se retrasa. "
                  "Tiene dos partes: *Raíces* (¿cuándo?) y *Sistemas lineales* (cálculo de calibración).",
                  "En *Raíces* escribes cómo crece el desgaste y el límite. En *Sistemas lineales* puedes usar una matriz de ejemplo o pegar la tuya."),
    "oscilaciones": ("Simula **cómo se balancea una cabina empujada por el viento**: cuánto se mueve, qué tan rápido oscila y cuánto tarda en calmarse.",
                     "Datos básicos: masa, rigidez, amortiguamiento y fuerza del viento (0 = sin viento). El resto de parámetros está en «Opciones avanzadas»."),
    "sensores": ("Un sensor dejó de registrar algunos datos. Este módulo **rellena los datos que faltan** dibujando una curva que pasa por los datos "
                 "conocidos, y mide cuánto se equivoca.",
                 "Puedes dejar que la app genere los datos o pegar los tuyos. Tú eliges qué puntos «se pierden» para comprobar la reconstrucción."),
}
PASOS = ("1️⃣ Elige un escenario (puedes cambiar cualquier número).  \n2️⃣ Pulsa **▶ Ejecutar**.  \n"
         "3️⃣ En **«2 · Resultados»** lee primero el *resumen* y después los detalles.  \n"
         "4️⃣ En **«3 · Interpretación»** revisa las conclusiones y **guarda** el experimento; luego lo recuperas en **Historial**.")

GLOSARIO = [
    ("Escenario", "Un conjunto de datos de partida. NORMAL = típico, ESTRÉS = exigente, MAL CONDICIONADO = delicado. Siempre puedes cambiar los números."),
    ("Valor de referencia", "El resultado correcto conocido (por una fórmula exacta o un cálculo muy fino) con el que comparamos lo que calcula cada método."),
    ("Error absoluto", "Cuánto se equivoca un resultado: |valor correcto − valor calculado|, en las mismas unidades."),
    ("Error relativo / porcentual", "Ese error comparado con el tamaño del valor. El porcentual lo expresa en %. Sirve para saber si el error es grande *respecto* al resultado."),
    ("Residuo", "Qué tanto «falla» una solución al reemplazarla en la ecuación original. Un residuo pequeño **no siempre** significa que la respuesta sea precisa."),
    ("Tolerancia", "La precisión que exiges. El método se detiene cuando el error estimado baja de ese valor."),
    ("Iteraciones / convergencia", "Algunos métodos mejoran la respuesta paso a paso. «Convergió» = llegó a la precisión pedida. «No convergió» = se quedó sin pasos o se descontroló (diverge)."),
    ("Paso (h)", "Tamaño del salto de tiempo en una simulación. Paso más pequeño = más preciso, pero más lento."),
    ("RK2 y RK4", "Dos métodos para simular cómo cambia algo en el tiempo. RK4 es más preciso que RK2, que es más simple."),
    ("Bisección, Newton y secante", "Tres formas de encontrar *cuándo* algo vale cero (por ejemplo, cuándo la velocidad llega a 0 o el desgaste llega al límite)."),
    ("Trapecio, Simpson y Romberg", "Tres formas de calcular un área bajo una curva (una integral), por ejemplo la distancia recorrida a partir de la velocidad."),
    ("Lagrange, Newton y spline", "Formas de dibujar una curva que pasa exactamente por los puntos conocidos para estimar los que faltan. El spline usa tramos suaves y suele ser más estable."),
    ("Ruido", "Variación aleatoria que contamina las mediciones de un sensor."),
    ("Mal condicionado (κ grande)", "Problema muy sensible: un cambio mínimo en los datos produce un cambio enorme en el resultado. **No es lo mismo** que peligroso ni que «no converge»."),
    ("Matriz SPD", "Matriz simétrica y definida positiva. El método del gradiente conjugado solo está garantizado para este tipo de matrices."),
    ("Sensibilidad", "Cuánto cambia el resultado si cambias un dato un poquito. Amplificación 1 = cambia lo mismo; 500 = cambia 500 veces más."),
]


def guia(clave):
    que, datos = QUE_HACE[clave]
    with st.expander("📘 ¿Qué hace este módulo y cómo se usa? (léelo primero)", expanded=True):
        st.markdown(que)
        st.markdown(PASOS)
        st.caption(datos)
        st.markdown(ESC_EXPLICA)


def glosario():
    with st.expander("📖 Glosario: ¿qué significan estas palabras?"):
        for t, d in GLOSARIO:
            st.markdown(f"**{t}:** {d}")


def mostrar_resumen(res):
    """res = {'lineas': [...], 'veredictos': [(nivel, texto), ...]} de core/resumen.py"""
    st.markdown("#### 📝 Resumen en palabras simples")
    for linea in res["lineas"]:
        st.markdown(f"- {linea}")
    for nivel, texto in res["veredictos"]:
        {"ok": st.success, "warn": st.warning, "bad": st.error}[nivel](texto)
    st.caption("Debajo están los detalles técnicos (tablas y gráficos) por si quieres revisar cómo se llegó a estos resultados.")


def selector_escenario(key=None):
    return st.radio("Elige un escenario (son solo valores de partida; puedes cambiar cualquier número)", list(ESC_TXT),
                    horizontal=True, format_func=ESC_TXT.get, key=key)
