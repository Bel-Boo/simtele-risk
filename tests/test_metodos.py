"""Pruebas de la Semana 2: cada familia contra solución analítica + persistencia/relanzado de todos los módulos."""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core import db, edo, integracion as integ, interpolacion as ip, raices, registro
from core import m1_detencion, m2_raices, m3_oscilaciones, m4_sensores
from core.comun import comparar_vectores
from core.funciones import ErrorExpresion, compilar


def test_expresiones_seguras():
    f = compilar("2*sin(t)+t^2", ("t",))
    assert f(0.0) == 0.0 and f(1.0) == pytest.approx(2 * math.sin(1) + 1)
    for malo in ["__import__('os')", "t.real", "open('x')", "[1]", "lambda: 1", "z+1", "'a'"]:
        with pytest.raises(ErrorExpresion):
            compilar(malo, ("t",))


def test_raices_sqrt2():
    g = lambda x: x * x - 2
    r = math.sqrt(2)
    b = raices.biseccion(g, 0, 2, 1e-12, x_ref=r)
    n = raices.newton_raphson(g, lambda x: 2 * x, 1, 1e-12, x_ref=r)
    s = raices.secante(g, 1, 2, 1e-12, x_ref=r)
    assert all(m["convergio"] and abs(m["x"] - r) < 1e-10 for m in (b, n, s))
    assert n["iteraciones"] < s["iteraciones"] < b["iteraciones"]
    assert n["extra"]["orden"] == pytest.approx(2, abs=0.2)
    assert not raices.biseccion(lambda x: (x - 1) ** 2, 0, 3)["convergio"]      # raíz doble: sin cambio de signo


def test_cuadratica_estable():
    rs = raices.raices_cuadratica(-30, 0.05, 0.0002)
    assert 281.97 < max(rs) < 281.98


def test_integracion_ordenes():
    tab, R = integ.tabla_refinamiento(np.sin, 0, math.pi, 6, 2.0)
    for nombre, p in (("Trapecio compuesto", 2), ("Simpson 1/3 compuesto", 4)):
        e1, e2 = tab[-3][nombre]["error_abs"], tab[-2][nombre]["error_abs"]
        assert math.log2(e1 / e2) == pytest.approx(p, abs=0.15)
    assert tab[-1]["Romberg"]["error_abs"] < 1e-12
    with pytest.raises(ValueError):
        integ.simpson_13_compuesto(np.sin, 0, 1, 5)


def test_interpolacion():
    x = np.linspace(0, 6, 10)
    q = np.array([0.7, 2.2, 4.9])
    assert np.allclose(ip.lagrange(x, np.sin(x), q), ip.newton_dd(x, np.sin(x), q), atol=1e-12)
    assert np.max(np.abs(ip.SplineNatural(x, np.sin(x))(q) - np.sin(q))) < 2e-3
    xs = np.array([0.0, 1, 2, 3, 4])
    assert np.allclose(ip.SplineNatural(xs, xs ** 3)(xs), xs ** 3)               # pasa por los nodos
    assert ip.constante_lebesgue(np.linspace(0, 12, 25)) > 100 * ip.constante_lebesgue(ip.nodos_chebyshev(0, 12, 25))
    with pytest.raises(ValueError):
        ip.lagrange([0, 1, 1], [0, 1, 2], 0.5)                                    # nodos repetidos


def test_edo_ordenes():
    w = 2.0
    f = lambda t, y: [y[1], -w * w * y[0]]
    ex = [math.cos(3 * w), -w * math.sin(3 * w)]
    est = edo.estudio_convergencia(f, 0, [1, 0], 3, 20, ex)
    assert est[-1]["p_rk2"] == pytest.approx(2, abs=0.2) and est[-1]["p_rk4"] == pytest.approx(4, abs=0.2)


@pytest.mark.parametrize("mod", [m1_detencion, m2_raices, m3_oscilaciones, m4_sensores])
def test_tres_escenarios_corren_y_generan_conclusiones(mod):
    for tipo, p in mod.PRESETS.items():
        out = mod.correr(p)
        assert mod.validar({**mod.BASE, **p}) is None
        assert len(mod.ejecuciones(p, out=out)) >= 3
        assert len(mod.conclusion_numerica(out)) > 50 and "NO puede inferirse" in mod.conclusion_problema(out)


def test_modulo1_analitico():
    out = m1_detencion.correr(m1_detencion.PRESETS["NORMAL"])
    assert out["td_ref"] == pytest.approx(5.0) and out["I_ref"] == pytest.approx(12.5)
    assert all(r["err_max"] < 1e-12 for r in out["edo"])
    mal = m1_detencion.correr(m1_detencion.PRESETS["MAL_CONDICIONADO"])
    assert not mal["raices"][0]["convergio"] or mal["raices"][1]["extra"]["orden"] < 1.3   # raíz doble → orden ≈ 1
    est = m1_detencion.correr(m1_detencion.PRESETS["ESTRÉS"])
    assert est["margen"] < 0 and est["edo"][0]["err_max"] > 100 * est["edo"][1]["err_max"]


def test_modulo3_analitico_libre():
    out = m3_oscilaciones.correr(m3_oscilaciones.PRESETS["NORMAL"])
    assert out["tipo_ref"].startswith("analítica") and out["amp_ref"] == pytest.approx(0.5, abs=1e-6)
    assert out["edo"][1]["err_max"] < out["edo"][0]["err_max"] / 100


def test_modulo4_runge():
    out = m4_sensores.correr(m4_sensores.PRESETS["MAL_CONDICIONADO"])
    pol, spl = out["res"][0], out["res"][2]
    assert pol["amp_curva"] > 100 * spl["amp_curva"] and out["diag"]["lebesgue"] > 1e3
    prop = m4_sensores.correr({**m4_sensores.BASE, "fuente": "propios", "ocultos": "3,6",
                               "datos_txt": "\n".join(f"{x},{x * x}" for x in range(10))})
    assert prop["res"][0]["err_max"] < 1e-9
    with pytest.raises(ValueError):
        m4_sensores.correr({**m4_sensores.BASE, "ocultos": "99"})


@pytest.mark.parametrize("caso,mod", [("Detención de emergencia", m1_detencion), ("Deterioro y mantenimiento", m2_raices),
                                      ("Oscilaciones por viento", m3_oscilaciones), ("Reconstrucción de sensores", m4_sensores)])
def test_guardar_reiniciar_recuperar_relanzar(tmp_path, caso, mod):
    url = f"sqlite:///{tmp_path / 'x.db'}"
    eng = db.get_engine(url, forzar=True)
    p = {**mod.PRESETS["ESTRÉS"], **({"submodulo": "raices"} if mod is m2_raices else {})}
    sid = db.guardar_simulacion(eng, caso, "ESTRÉS", p, "test", mod.ejecuciones(p, "texto"))
    eng.dispose()
    S = db.cargar_simulacion(db.get_engine(url, forzar=True), sid)          # "reinicio"
    assert S["parametros_json"]["submodulo" if mod is m2_raices else list(p)[0]] is not None
    nuevas = registro.relanzar(S["caso"], S["parametros_json"])
    assert len(nuevas) == len(S["ejecuciones"])
    for e, n in zip(S["ejecuciones"], nuevas):
        mx, ok = comparar_vectores(registro.vector_comparable(e["resumen"]["valor_json"]), registro.vector_comparable(n["resumen"]["valor"]), 1e-8)
        assert ok, (e["metodo"], mx)
