# 🚡 SIMTELE-RISK — Desafío integrador de Métodos Numéricos

Aplicación web (Streamlit) con **4 casos de estudio** inspirados en un sistema de transporte por cable.
**Uso estrictamente educativo: datos y parámetros sintéticos; sin conexión con equipos reales ni fallas verificadas de ninguna empresa.**

- **Integrantes:** Estrugo Perez Valeria Isabel · Tarqui Humerez Mayra Belen
- **Mención:** Ingeniería de Sistemas
- **App desplegada:** https://simtele-risk-psiwmfc6lsrdcgh3fmr4j2.streamlit.app/

## Estado del proyecto

| Módulo | Métodos | Escenarios |
|---|---|---|
| 1 · Detención de emergencia | RK2 (3 variantes), RK4, trapecio, Simpson 1/3, Romberg, bisección, Newton-Raphson, secante | NORMAL · ESTRÉS · MAL CONDICIONADO |
| 2 · Deterioro y mantenimiento | Raíces (bisección, Newton, secante) + sistemas lineales (Jacobi, Gauss-Seidel, LU, gradiente conjugado, directa) + integración de la tasa | NORMAL · ESTRÉS · MAL CONDICIONADO |
| 3 · Oscilaciones por viento | RK2, RK4, trapecio, Simpson 1/3, Romberg | NORMAL · ESTRÉS · MAL CONDICIONADO |
| 4 · Reconstrucción de sensores | Lagrange, Newton (diferencias divididas), spline cúbico natural, raíces (cruce de umbral) | NORMAL · ESTRÉS · MAL CONDICIONADO |
| Teoría de errores (transversal) | Error absoluto, relativo, porcentual, residual, sensibilidad, número de condición, orden observado | todos |
| Historial | Buscar, abrir, visualizar y relanzar cualquier simulación guardada | todos |

Todos los métodos están **programados a mano** (NumPy solo para productos matriz-vector y la referencia directa). Cada método se verifica contra una solución analítica; cuando no existe, se usa una referencia numérica justificada (RK4 con paso mucho menor y estimación del error por Richardson, o bisección con tolerancia 1e-15).

## Entrada de datos

Los escenarios solo cargan valores iniciales; **todo es editable**:
- Funciones escritas por el usuario (evaluadas de forma segura, sin `eval` libre): `a(v,t)`, `F(t)`, `D(t)`, `y(t)`. Ejemplos: `0.5+0.3*v`, `300*sin(2*t)`, `5*exp(0.01*t)`, `sin(t)+0.3*cos(3*t)`.
- Matriz A personalizada en el módulo 2 (sistemas lineales): una fila por línea, p. ej.
  ```
  10 2 1 0
  2 9 -1 1
  1 -1 8 2
  0 1 2 7
  ```
- Datos propios en el módulo 4: un par `t y` por línea.
- Decimales con punto o coma y notación científica (`1e-10`).

## Estructura

```
app.py                       Enrutador y menú
pages/                       0_Inicio, 1_Detencion, 2_Deterioro, 3_Oscilaciones, 4_Sensores, 5_Historial
core/errores.py              Teoría de errores transversal
core/sistemas_lineales.py    Jacobi, Gauss-Seidel, LU, gradiente conjugado, directa
core/raices.py               Bisección, Newton-Raphson, secante
core/integracion.py          Trapecio, Simpson 1/3, Romberg
core/interpolacion.py        Lagrange, Newton, spline natural, Hermite, Lebesgue
core/edo.py                  RK2 (variante declarada) y RK4
core/funciones.py            Evaluador seguro de expresiones
core/m1_detencion.py, m2_raices.py, modulo2.py, m3_oscilaciones.py, m4_sensores.py   Motor de cada módulo
core/registro.py             Relanzado de simulaciones desde el historial
core/db.py                   Tablas (SQLAlchemy), guardar y cargar
core/ui.py, ui_comun.py, ui_deterioro.py, comun.py, graficos.py, casos.py, escenarios.py   Interfaz y utilidades
db/schema_postgres.sql       Script SQL (PostgreSQL)
docs/DER.md                  DER (Mermaid) y modelo relacional
tests/                       Pruebas con pytest
```

## Ejecutar en local

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Sin configurar nada usa SQLite local (`data/simtele_local.db`).

## Pruebas

```bash
python -m pytest -q tests
```
Verifican cada familia de métodos contra soluciones analíticas (órdenes de convergencia de Newton, trapecio, Simpson, RK2 y RK4), la seguridad del evaluador de expresiones y, para los cuatro módulos, el ciclo **ejecutar → guardar → reiniciar → recuperar → repetir el cálculo → coincidencia**.

## Base de datos en la nube

Streamlit Community Cloud borra los archivos locales al reiniciar, por eso se usa PostgreSQL externo (Supabase o Neon).
1. Crea un proyecto en Supabase o Neon.
2. En su **SQL Editor** ejecuta `db/schema_postgres.sql` (6 tablas: `caso_estudio`, `escenario`, `simulacion`, `ejecucion_metodo`, `iteracion_resultado`, `resultado_resumen`).
3. En **Streamlit Cloud → Settings → Secrets** pega (usa el *Session pooler*):
   ```toml
   [db]
   dialect  = "postgresql+psycopg2"
   host     = "aws-0-xxxx.pooler.supabase.com"
   port     = 5432
   database = "postgres"
   username = "postgres.<project-ref>"
   password = "TU_CONTRASEÑA"
   ```
   Hay una plantilla en `.streamlit/secrets.toml.example`. **Nunca subas contraseñas a GitHub.**
4. Reinicia la app: la barra lateral debe decir `Base de datos: postgresql`.

## Despliegue

1. Sube el repo a GitHub.
2. https://share.streamlit.io → *Create app* → repo, rama `main`, archivo `app.py`.
3. En *Advanced settings → Secrets* pega la configuración de la BD.

## Prueba de persistencia (defensa)

Cualquier módulo → elegir escenario → **Ejecutar** → pestaña *Interpretación* → **Guardar** → actualizar o reiniciar la app → **Historial** → abrir la simulación (parámetros, tablas y gráficos se recuperan de la BD) → **Repetir el cálculo** → ✅ en todos los métodos.

## Limitaciones

- Los modelos son simplificados e hipotéticos (frenado 1D, oscilador lineal de 1 grado de libertad, deterioro cuadrático).
- Los sistemas lineales auxiliares de los módulos 3 y 4 no se incluyen; el spline resuelve su sistema tridiagonal con el método de Thomas.
- Para n grande, la ejecución con referencia RK4 de paso fino puede tardar unos segundos.
