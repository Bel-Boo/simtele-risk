"""Lógica del Módulo 2 (calibración por sistemas lineales) separada de la interfaz."""
import numpy as np
from .errores import error_porcentual, sensibilidad
from .escenarios import construir_sistema
from .sistemas_lineales import diagnostico, lu_resolver, resolver_todos


def correr(params):
    A, b, x_star = construir_sistema(params)
    diag = diagnostico(A)
    res = resolver_todos(A, b, x_star, float(params["tol"]), int(params["max_iter"]))
    sens = sensibilidad(lambda A_, b_: lu_resolver(A_, b_)["x"], A, b, eps=float(params["eps_sens"]))
    return {"A": A, "b": b, "x_star": x_star, "diag": diag, "res": res, "sens": sens}


def conclusion_numerica(out, tipo):
    d, res, s = out["diag"], out["res"], out["sens"]
    it = [r for r in res if r["tolerancia"] is not None]
    ok = [r["metodo"] for r in it if r["convergio"]]
    mal = [r["metodo"] for r in it if not r["convergio"]]
    L = [f"κ(A) = {d['kappa']:.3e}; A {'es' if d['spd'] else 'NO es'} SPD y "
         f"{'es' if d['diag_dominante'] else 'NO es'} diagonalmente dominante.",
         f"Radio espectral: ρ(T_Jacobi) = {d['rho_jacobi']:.4f}, ρ(T_GS) = {d['rho_gauss_seidel']:.4f} "
         "(un método estacionario converge para todo x0 si y solo si ρ < 1)."]
    if ok:
        mejor = min((r for r in it if r["convergio"]), key=lambda r: r["iteraciones"])
        L.append(f"Convergieron: {', '.join(ok)}. El de menos iteraciones fue {mejor['metodo']} ({mejor['iteraciones']}).")
    if mal:
        L.append(f"NO alcanzaron la tolerancia: {', '.join(mal)}. Ver criterio de parada: distinguir DIVERGENCIA "
                 "(ρ > 1) de convergencia lenta (ρ ≈ 1) y ambas de un problema mal condicionado.")
    ref = res[0]["historial"][-1]
    L.append(f"La referencia directa logra residuo {ref['residual']:.1e} y error {ref['error_abs']:.1e}. "
             f"Con una perturbación relativa de {s['cambio_rel_b']:.1e} en b, la solución cambió "
             f"{s['cambio_rel_x']:.1e} (amplificación {s['amplificacion']:.1f} ≤ κ(A) = {s['cota_kappa']:.2e}).")
    if tipo == "MAL_CONDICIONADO":
        L.append("Un residuo pequeño NO implica error pequeño cuando κ(A) es grande: error ≲ κ(A)·residuo relativo.")
    return "\n".join(f"- {l}" for l in L)


def conclusion_problema(out, tipo, params, horizonte_dias=200.0):
    d, res = out["diag"], out["res"]
    buenos = [r for r in res if r["convergio"]]
    malos = [r for r in res if r["tolerancia"] is not None and not r["convergio"]]
    rel = lambda r: r["historial"][-1]["error_rel"] or 0.0
    peor = max(buenos, key=rel)
    iters = {r["metodo"]: (r["iteraciones"] if r["convergio"] else None) for r in res}
    fi = lambda m: f"{iters[m]} iteraciones" if iters[m] else "no convergió"
    n = d["n"]
    dias = rel(peor) * horizonte_dias
    L = [f"- Qué representa x: los {n} coeficientes de calibración del modelo hipotético de deterioro "
         f"D(t) = D0 + αt + βt². x* es el valor 'verdadero' sintético y el error de x se propaga al tiempo "
         f"estimado t* en que se alcanzaría el umbral de inspección.",
         f"- Ejemplo ilustrativo (suponiendo t* ≈ {horizonte_dias:.0f} días): el peor error relativo entre los métodos "
         f"que convergieron fue {rel(peor):.1e} ({peor['metodo']}); a primer orden movería t* unos {dias:.1e} días."]
    if tipo == "NORMAL":
        L += [f"- Resultado: con κ(A) = {d['kappa']:.1f} el problema está bien condicionado; todos los métodos llegan a la "
              "misma calibración y la fecha de inspección no cambia según el método elegido.",
              f"- Lo que cambia es el costo: Jacobi {fi('Jacobi')}, Gauss-Seidel {fi('Gauss-Seidel')}, "
              f"Gradiente Conjugado {fi('Gradiente Conjugado')}; los directos resuelven en un paso."]
    elif tipo == "ESTRÉS":
        L += [f"- Estrés ≠ mal condicionado: se pidió un sistema grande (n = {n}) y tolerancia {params['tol']:.0e}, "
              f"pero κ(A) = {d['kappa']:.0f} sigue siendo moderado, por eso la exactitud se mantiene.",
              f"- Lo que se encarece es el cálculo: Jacobi {fi('Jacobi')}, Gauss-Seidel {fi('Gauss-Seidel')}, "
              f"Gradiente Conjugado {fi('Gradiente Conjugado')}. Con más puntos de calibración, un método lento puede "
              "volverse impráctico aunque converja.",
              "- El riesgo modelado (cuándo se llega al umbral) no cambia por usar un sistema más grande."]
    else:
        L += [f"- κ(A) = {d['kappa']:.2e}: hay mucha amplificación. Error de x hasta {rel(peor):.1e} aunque el residuo es "
              f"{peor['historial'][-1]['residual']:.1e}; el residuo pequeño engaña.",
              ("- Métodos que no lograron la tolerancia: " + ", ".join(r["metodo"] for r in malos) +
               ". Sus valores no sirven para planificar una inspección.") if malos else
              "- Todos los métodos lograron la tolerancia, pero con pérdida de dígitos.",
              "- Interpretación: datos de calibración casi redundantes (columnas casi dependientes) amplifican el ruido de "
              "medición hasta κ veces; los coeficientes, y por tanto t*, serían poco confiables.",
              "- Mitigación: más datos bien distribuidos, reformular o regularizar el ajuste."]
    L += ["- Variables que influyen: número y distribución de los datos de calibración, ruido, condicionamiento y precisión de máquina.",
          "- Qué NO puede inferirse: los datos son sintéticos y el modelo es hipotético; no dice nada sobre el estado de "
          "ninguna cabina ni de Mi Teleférico, y no sustituye una inspección real."]
    return "\n".join(L)


PLANTILLA_PROBLEMA = (
    "(Completar con sus palabras)\n"
    "- Qué representa x en la calibración de D(t) = D0 + αt + βt² y qué significa un error en x para la "
    "estimación del tiempo de inspección.\n"
    "- Qué variables influyen (número de datos, ruido, condicionamiento del ajuste).\n"
    "- Qué NO puede inferirse: los datos son sintéticos y el modelo es hipotético."
)


def a_ejecuciones(out, params, interpretacion):
    x_star = out["x_star"]
    ejs = []
    for r in out["res"]:
        u = r["historial"][-1]
        ejs.append({
            "metodo": r["metodo"], "tolerancia": r["tolerancia"], "paso": None, "max_iter": r["max_iter"],
            "convergio": r["convergio"], "tiempo_ms": r["tiempo_ms"], "historial": r["historial"],
            "resumen": {
                "referencia": "x* conocido; b = A x*",
                "valor": {"x": r["x"], "iteraciones": r["iteraciones"], "motivo_parada": r["motivo_parada"]},
                "metricas": {"residual": u["residual"], "error_abs": u["error_abs"], "error_rel": u["error_rel"],
                             "error_pct": error_porcentual(x_star, r["x"]), "kappa": out["diag"]["kappa"],
                             "sensibilidad": out["sens"]},
                "interpretacion": interpretacion,
            },
        })
    return ejs
