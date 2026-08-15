# Pines

Todas las versiones del kit viven acá y en ningún otro lado. El blueprint las lee de este
archivo, `scripts/auditar.py` verifica que lo generado las respete, y `scripts/verificar_pines.py`
las compara contra los registros vivos.

Un número repetido en dos archivos algún día dice dos cosas distintas.

**Verificado contra PyPI el 2026-08-14.**

---

## Las dos reglas

**Se fija con `==`, nunca con `>=`.** Un piso no es un pin: dice "esta o cualquiera que venga
después", y las que vienen después no las probó nadie. Esto no es teoría, es el defecto que
justifica el kit entero:

```
fastapi 0.141.1  declara  starlette>=0.46.0        ← sin techo
starlette         1.3.1   2026-06-12               ← la última que existía cuando salió fastapi
                  1.4.0   2026-08-05  ┐
                  1.4.1   2026-08-05  │  todas DESPUÉS
                  1.5.0   2026-08-08  │  de que fastapi 0.141.1
                  1.5.1   2026-08-08  │  se congelara
                  1.6.0   2026-08-08  ┘
```

Un `pip install fastapi` hoy te empareja FastAPI con un Starlette tres minors adelante de
cualquier cosa contra la que se haya probado. No falla al instalar. Falla después, raro, y el
error no nombra a ninguno de los dos. Por eso `starlette` está fijado a `1.3.1`.

**No se fija una versión con menos de 72 horas.** No tuvo reposo. `anthropic 0.122.0` salió el
2026-08-13 a las 18:36 UTC; el kit fija `0.121.0`, del 2026-08-07. Cuando 0.122.0 cumpla tres
días y alguien la corra, se sube acá y se vuelve a correr el bucle.

**Y dos líneas de este archivo rompen esa regla hoy, dicho acá y no escondido.** La corrida de
`scripts/verificar_pines.py` del 2026-08-14 cierra en `FAIL · 2 errores · 2 avisos`, y los dos
errores son de acá:

```
[ERROR] pin/sin_reposo   PINES.md:87   uvicorn==0.52.3 salió hace 28 h: no tuvo reposo
[ERROR] pin/sin_reposo   PINES.md:200  ruff==0.16.3 salió hace 29 h: no tuvo reposo
```

Los dos entraron el 2026-08-13, el mismo día que salieron. La última con reposo de cada una es
`uvicorn==0.52.1`, del 2026-08-01, y `ruff==0.16.2`, del 2026-08-07 —`0.52.2` tampoco sirve, es de
hace 38 horas—. No se bajaron en esta ronda porque bajar el servidor y el linter es un cambio de
runtime con su propia corrida de la suite, y esta ronda vino a destrabar la rama `service_account`;
queda escrito acá para que la próxima corrida del bucle no lo descubra de nuevo. Los dos pines que
sí entraron hoy, `PyJWT` y `cryptography`, tienen 85 y 14 días de reposo.

Los números de línea son de esa corrida y envejecen a la primera edición; lo que manda es el
nombre del paquete.

---

## Python

```
>=3.11,<3.15
```

El piso lo impone `websockets 17.0.1`, que pide `>=3.11`, y se gana el lugar igual:
`asyncio.TaskGroup`, `except*`, `datetime.UTC`, `tomllib`. El techo es porque `pydantic-core` y
`asyncpg` llegan hasta `cp314`.

**Verificado: todas las dependencias compiladas llegan a 3.14 con rueda.** Nada se compila desde
fuente, así que una máquina moderna no necesita toolchain. `pydantic-core` y `asyncpg` publican
`cp314`; `cryptography 50.0.0` llega por otra puerta y da lo mismo —su rueda `cp311-abi3` sirve de
3.11 en adelante por ABI estable, y además publica `cp314-cp314t` para el intérprete sin GIL—.
Medido en esta máquina, con Python 3.14.6:

```text
Using cached cryptography-50.0.0-cp311-abi3-macosx_11_0_arm64.whl (4.0 MB)
```

El riesgo real es el inverso, y es el que el kit sí atiende: tu laptop corre una versión y el
contenedor otra. Por eso la imagen base está fijada en `python:3.12-slim` —la de cobertura de
ruedas más ancha y más reposo— y la compuerta corre las pruebas **adentro de la imagen**, no
solo en tu máquina.

---

## Runtime

```
fastapi==0.141.1
starlette==1.3.1          # ver "las dos reglas". Sin esto, fastapi flota.
uvicorn==0.52.3
uvloop==0.22.1            # los extras de uvicorn[standard], fijados uno por uno
httptools==0.8.0          #   para que `[standard]` no se mueva por abajo
watchfiles==1.2.0
websockets==17.0.1
anyio==4.14.2             # lo comparten anthropic y starlette; suelto, flota

anthropic==0.121.0        # no 0.122.0: salió hace horas
httpx==0.28.1
pydantic==2.13.4
pydantic-settings==2.15.0
python-dotenv==1.2.2
PyYAML==6.0.3

SQLAlchemy==2.0.52
asyncpg==0.31.0           # ← el que faltaba. Ver abajo.
aiosqlite==0.22.1
greenlet==3.5.5           # SQLAlchemy lo declara bajo un marcador de plataforma;
                          #   en una arquitectura no listada, el async muere en runtime
alembic==1.19.1

APScheduler==3.11.3       # el recordatorio de 24 h. Ver abajo.
tenacity==9.1.4
structlog==26.1.0

PyJWT==2.13.0             # el JWT RS256 de la cuenta de servicio de Google. Ver abajo.
cryptography==50.0.0      # el extra [crypto] de PyJWT, fijado aparte por lo mismo
                          #   que los extras de uvicorn: `PyJWT[crypto]` pide
                          #   `cryptography>=3.4.0`, un piso sin techo
```

### `asyncpg`, y por qué se escapa de cualquier análisis de imports

`asyncpg` **nunca se importa por nombre**. Aparece una sola vez, adentro de una cadena:

```python
url.replace("postgresql://", "postgresql+asyncpg://")
```

Un analizador que recorra los `import` del proyecto no lo ve. Por eso se cayó del kit de
referencia, y por eso el primer despliegue con Postgres en Railway muere con
`ModuleNotFoundError` — con SQLite anda perfecto, porque con SQLite esa línea nunca corre.

La compuerta no busca imports para esto: busca `\+(\w+)://` en las cadenas del proyecto y exige
que cada driver que encuentre esté fijado acá.

### `APScheduler`, y por qué no es el cron de Railway

El paso 4 programa un recordatorio 24 horas antes de la cita. El cron de Railway no puede:
mínimo de 5 minutos, solo UTC, y exige que el proceso termine. Un recordatorio corre en el
servicio que ya está prendido, con `SQLAlchemyJobStore` sobre la misma base —si no, un despliegue
se lleva puestos los trabajos pendientes— y un barrido al arrancar que rearma lo que venció
mientras estuvo caído.

### `PyJWT` y `cryptography`, y por qué no `google-auth`

Destraban la rama `service_account` del paso 4. Google pide un JWT firmado con RS256 para
cambiarlo por un `access_token`, RS256 no se firma con la biblioteca estándar, y hasta esta ronda
ninguna librería que lo hiciera estaba acá: `blueprint/33-agenda.md` paso 2 dejaba esa rama
declarada y detenida. El camino `authorized_user` no la necesita nunca —ahí el token sale de un
formulario— y por eso sigue siendo el que anda sin fijar nada.

Las dos candidatas eran `PyJWT[crypto]` y `google-auth`. Gana `PyJWT`, por tres motivos medidos y
no por gusto:

1. **La compuerta resuelve `jwt` y no resuelve `google`.** El chequeo 06 `deps-imports` mapea la
   raíz importada a una distribución fijada, y ese mapa —`IMPORT_A_DISTRIBUCION`, en
   `scripts/auditar.py`— dice `"jwt": "PyJWT"` y dice `"google": "google-api-python-client"`. Con
   `google-auth` fijado acá, un `from google.oauth2 import service_account` cae en la distribución
   equivocada y la compuerta lo marca. Medido sobre dos árboles de un módulo cada uno, con el mismo
   auditor y el mismo `.venv`:

   ```
   [ok      ] 06 deps-imports       1 imports de terceros, todos fijados
   [FALLA   ] 06 deps-imports
       [ERROR] deps/import_sin_pin  agente/calendario.py:3
               importa `google` y ninguna distribución fijada lo provee
   ```

   El primero importa `jwt` con `PyJWT==2.13.0` fijado; el segundo importa `google.oauth2` con
   `google-auth==2.56.3` fijado. Un rojo garantizado para quien construya, en un chequeo que es de
   otro dueño.
2. **`google-auth` trae su propio transporte HTTP.** Refrescar sus credenciales pide un
   `google.auth.transport.Request`, que es `requests` o `urllib3`, y el kit tiene **un solo**
   cliente HTTP —`agente/http.py`, con `timeout=`; es el invariante 3, y lo mira el chequeo 12
   `http-unico`—. `PyJWT` no abre ningún socket: firma una cadena y el `POST` lo hace el mismo
   cliente que ya hace el del camino `authorized_user`.
3. **Menos superficie que flota por abajo.** `google-auth 2.56.3` declara `pyasn1-modules>=0.2.1`
   y `cryptography>=38.0.3`, dos pisos sin techo; `PyJWT 2.13.0` declara uno solo,
   `cryptography>=3.4.0` bajo el extra `crypto`, y por eso `cryptography` va fijado acá al lado en
   vez de `PyJWT[crypto]`. Es el mismo movimiento que los extras de `uvicorn[standard]`.

`PyJWT 2.13.0` es del 2026-05-21 y `cryptography 50.0.0` del 2026-07-31: 84 y 13 días de reposo, o
sea las dos pasan la regla de las 72 horas. `cryptography` arrastra `cffi` y `pycparser`, que no se
fijan, igual que el resto del árbol transitivo del kit.

**Sin `cryptography`, `PyJWT` instalado igual no firma RS256** y el error es explícito, que es la
mitad del motivo para fijarla al lado:

```
NotImplementedError: Algorithm 'RS256' could not be found. Do you have cryptography installed?
```

---

## Dev y pruebas

```
pytest==9.1.1
pytest-asyncio==1.4.0
jsonschema==4.26.0        # sin esto, el contrato de los seis pasos no tiene validador
respx==0.23.1
freezegun==1.5.5          # la única forma de probar un recordatorio de 24 h en menos de un segundo
ruff==0.16.3
```

---

## Modelo

```
MODELO=claude-opus-5
```

Adaptive thinking explícito (`thinking={"type": "adaptive"}`) y `output_config={"effort": "medium"}`.
Explícito y no omitido: en Opus 5 adaptive es el default, pero si mañana alguien cambia el
modelo, omitirlo significa *sin* thinking en varios de la familia.

No van `temperature`, `top_p`, `top_k` ni `budget_tokens`: los cuatro devuelven 400. Tampoco
prefill de turno assistant.

**Un cambio de modelo vuelve a correr el bucle de auditoría.** El blueprint es prompts, y un
modelo nuevo los sigue distinto. Esto no es ceremonia: el kit de referencia quedó fijado en
`claude-sonnet-4-6` y nadie lo notó hasta que alguien lo leyó. Este archivo lleva fecha para que
la próxima vez se note.

---

## Lo que a propósito NO se fija

**`zernio-sdk`.** Publicó cinco versiones el mismo 2026-08-13 (`1.4.493` a `1.4.498`). Fijarlo
exacto se puede, pero no sirve: la verificación de firma necesita el **cuerpo crudo** de la
petición, que ningún SDK te entrega, y los endpoints, cabeceras y códigos de error ya están en el
blueprint. `httpx` pelado saca una superficie de deriva entera del medio.

**`python-multipart`.** Estaba en el kit de referencia. Meta y Zernio mandan JSON; nada acá parsea
un formulario. Era carga.

---

## Volver a verificar

```bash
python3 scripts/verificar_pines.py
```

Compara cada línea contra PyPI y contra la lista de modelos, e informa qué se movió, qué tiene
menos de 72 horas y qué quedó sin verificar. Avisa cuando la fecha de arriba pasa los 90 días.
