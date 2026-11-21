"""Registro de módulos: permite RELANZAR una simulación guardada desde el Historial."""
from . import m1_detencion, m2_raices, m3_oscilaciones, m4_sensores, modulo2
from .comun import comparar_vectores


def relanzar(caso, params):
    """Devuelve la lista de ejecuciones recalculadas (mismo formato que se guarda)."""
    if caso == "Detención de emergencia":
        return m1_detencion.ejecuciones(params)
    if caso == "Oscilaciones por viento":
        return m3_oscilaciones.ejecuciones(params)
    if caso == "Reconstrucción de sensores":
        return m4_sensores.ejecuciones(params)
    if caso == "Deterioro y mantenimiento":
        if params.get("submodulo") == "raices":
            return m2_raices.ejecuciones(params)
        out = modulo2.correr(params)
        return modulo2.a_ejecuciones(out, params, "")
    raise ValueError(f"Caso desconocido: {caso}")


def vector_comparable(resumen_valor):
    v = resumen_valor or {}
    if "comparar" in v:
        return v["comparar"]
    return v.get("x", [])
