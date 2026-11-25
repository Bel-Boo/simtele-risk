import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core import m1_detencion, m2_raices, m3_oscilaciones, m4_sensores, modulo2, resumen
from core.escenarios import PARAMS_DEFECTO


def test_resumenes_en_lenguaje_simple_para_todos_los_escenarios():
    for tipo in ("NORMAL", "ESTRÉS", "MAL_CONDICIONADO"):
        for mod, fn in ((m1_detencion, resumen.m1), (m2_raices, resumen.m2r), (m3_oscilaciones, resumen.m3), (m4_sensores, resumen.m4)):
            r = fn(mod.correr(mod.PRESETS[tipo]))
            assert r["lineas"] or r["veredictos"]
            assert all(n in ("ok", "warn", "bad") for n, _ in r["veredictos"])
        assert resumen.m2l(modulo2.correr(PARAMS_DEFECTO[tipo]), tipo)["veredictos"]


def test_escenarios_tienen_el_veredicto_esperado():
    assert resumen.m1(m1_detencion.correr(m1_detencion.PRESETS["NORMAL"]))["veredictos"][0][0] == "ok"      # alcanza a detenerse
    assert resumen.m1(m1_detencion.correr(m1_detencion.PRESETS["ESTRÉS"]))["veredictos"][0][0] == "bad"     # no alcanza
    assert resumen.m2r(m2_raices.correr(m2_raices.PRESETS["NORMAL"]))["veredictos"][0][0] == "ok"           # mantenimiento a tiempo
    assert resumen.m2r(m2_raices.correr(m2_raices.PRESETS["ESTRÉS"]))["veredictos"][0][0] == "bad"          # mantenimiento retrasado
