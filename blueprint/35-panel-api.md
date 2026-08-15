# 35 · El panel y la API

**Fase 4.** Entrás con los seis pasos y el CRM escritos; salís con el servicio arriba, el webhook
—el aviso automático que WhatsApp le manda a tu servidor cuando entra un mensaje; ver
`blueprint/00-contrato.md` § 10— atendido por proveedor, la API detrás de su token y una vista que
se abre en el navegador.

**El módulo se llama `agente/servidor.py`, y este archivo es su único dueño.** No es una
preferencia: el `CMD` del `Dockerfile` dice `uvicorn agente.servidor:app`, y el `Dockerfile` se
copia verbatim de `plantillas/infra/` y no se edita nunca. Ningún otro archivo del blueprint escribe
un servidor: la fase 3 termina sin ninguna app en el árbol, y así lo fijan `blueprint/00-contrato.md`
§ 3 y § 4. Si en tu árbol ya hay un módulo de servidor cuando llegás acá, algo de la fase 3 se
escribió de más: no lo renombres, revisá contra el contrato.

**Invariante 2** —un invariante es una de las seis reglas de `CLAUDE.md` que ningún archivo puede
romper, cada una con su chequeo en la compuerta `scripts/auditar.py`; ver
`blueprint/00-contrato.md` § 10—: el panel aprueba, `enviar()` manda. **Invariante 3:** un solo
cliente HTTP, el de `agente/http.py`, con `timeout=`. **Invariante 1:** las firmas se verifican —y
se emiten— sobre el cuerpo crudo, o sea los bytes exactos de la petición tal como llegaron por el
cable, antes de parsearlos (§ 10 otra vez). **Invariante 4:** `PANEL_TOKEN` se nombra acá y el valor
lo escribe quien instala.

---

### Paso 1 · Levantá el servicio con el nombre que el Dockerfile ya nombra

**Objetivo.** El servicio arranca, escucha en `0.0.0.0` y toma el puerto de `PORT`.

**Hacé esto.**

```python
# agente/servidor.py
from fastapi import FastAPI

from agente.ajustes import Ajustes, ajustes
from panel.panel import router as panel_router

# Este módulo se recarga, y `agente/ajustes.py` declara una sola instancia que el resto del
# árbol ya tiene importada por nombre. Se refresca en el lugar: construir otra dejaría dos.
ajustes.__dict__.update(Ajustes().__dict__)

app = FastAPI(title="Cerrador de WhatsApp", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(panel_router)
```

```bash
.venv/bin/uvicorn agente.servidor:app --host 0.0.0.0 --port ${PORT:-8000}
```

**Esa línea del `ajustes` no la nombra ninguna otra parte del blueprint, y es media hora de la que
nadie avisa.** `Ajustes()` lee `.env` y el entorno **una sola vez, cuando se importa
`agente/ajustes.py`**, y de ahí sale la instancia que importan `agente/enviar.py`,
`agente/proveedores/` y este archivo. `pruebas/test_firmas.py` y `pruebas/test_idempotencia.py`
cambian el entorno con `monkeypatch.setenv` y después recargan **sólo** este módulo
—`importlib.reload(importlib.import_module("agente.servidor"))`—: `agente/ajustes.py` no se vuelve
a importar, así que sin refrescar la instancia el servidor recargado sigue leyendo el proveedor y
el token del primer arranque. Se lee como dos rutas rotas y ninguna dice por qué:

```
POST /webhook/zernio → 404   el paso 3 compara `proveedor != ajustes.proveedor`
GET  /webhook/meta   → 403   el alta compara contra otro `WHATSAPP_VERIFY_TOKEN`
```

Medido sobre un build entero, sacando esa sola línea: `4 failed, 150 passed`. Va
`ajustes.__dict__.update(Ajustes().__dict__)` y no `ajustes = Ajustes()`: lo segundo crea una
segunda instancia acá adentro y el resto del árbol sigue leyendo la primera, que es el mismo bug
con una cara más difícil.

**Las rutas se escriben con sus anotaciones, y si te sale `TypeError: metaclass conflict` al
importar este módulo, el defecto no es tuyo.** Va acá porque la traza no nombra ni a FastAPI ni a
freezegun, así que quien caiga ahí no tiene de dónde agarrarse:

```
TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass
of the metaclasses of all its bases
  pydantic/v1/types.py:1180  class ConstrainedDate(date, metaclass=ConstrainedNumberMeta)
```

**Lo dispara cualquier parámetro anotado**, y no la anotación de retorno sola, que es a la que la
regla vieja le echaba la culpa. Por cada parámetro que tiene que validar, FastAPI llama a
`create_model_field()`, que llama a `annotation_is_pydantic_v1()`, que hace
`from pydantic import v1` la primera vez que se lo piden. El retorno entra por el mismo
`create_model_field()`, por el modelo de respuesta, y revienta igual: por eso sacarlo parecía
arreglarlo. No arregla nada, porque el paso 3 de este mismo archivo escribe
`async def alta(proveedor: str, request: Request)` y ese `proveedor: str` alcanza solo. Adentro de
la suite ese import cae adentro del `freeze_time` de sesión de `pruebas/conftest.py`, donde
`datetime.date` es `freezegun.api.FakeDate` y su metaclase no es `type`.

No revienta la ruta: revienta el `import` del módulo entero, así que se lleva puestos a
`pruebas/test_panel.py`, `pruebas/test_idempotencia.py` y `pruebas/test_bandeja.py` de una vez.
Sobre un build fiel a este archivo eran 31 nodos rojos. Sobre el build mínimo con el que se midió
esta ronda —estas diez rutas y nada más adentro— son 24, y de esos 18 son `test_panel.py` entero
menos los dos nodos que sólo leen el archivo con `ast`.

Medido en esta máquina, con Python 3.14.6, fastapi 0.141.1, pydantic 2.13.4 y freezegun 1.5.5,
declarando cada una de estas rutas adentro de un `freeze_time`, una por intérprete limpio:

```
-> str                                            TypeError: metaclass conflict …
-> dict                                           TypeError: metaclass conflict …
x: str = None                                     TypeError: metaclass conflict …
x: int = 50                                       TypeError: metaclass conflict …
id: int, el path param de /x/{id}                 TypeError: metaclass conflict …
sólo request: Request                             ok
sin ningún parámetro                              ok
pydantic.v1 cargado antes de congelar, -> str     ok
pydantic.v1 cargado antes de congelar, id: int    ok
```

Sobre el build con el que se midió, la primera que revienta es `/api/conversaciones`, con sus
`estado: str = ""` y `limite: int = 50`; `/panel`, que no lleva un solo parámetro, se declara sin
ruido tres líneas antes. La regla vieja miraba justo la que andaba.

Las dos últimas filas son las que mandan, y el arreglo no es de este archivo:
`pruebas/conftest.py` carga `pydantic.v1` antes de entrar en `freeze_time` —es
`cargar_pydantic_v1()`, con esta misma medición al lado—, el import perezoso de FastAPI encuentra
el módulo ya cargado, y las anotaciones vuelven a ser inofensivas. **Ya está puesto.** Si esa línea
se revierte, esto vuelve, y vuelve con esta cara.

La regla que este paso traía hasta la ronda pasada —«ninguna ruta lleva anotación de retorno»—
nombraba mal el disparador y no cubría el caso que el propio archivo prescribe dos pasos más abajo.
Sale.

`railway.json` no trae `startCommand` a propósito: agregarlo pisa el `CMD` y lo único que vas a leer
es `service unavailable`. `docs_url=None` tampoco es gusto: `/docs` publica la superficie entera
—incluida la bandeja— en una URL pública, y `PANEL_TOKEN` no la cubre. `redoc_url` y `openapi_url`
van en `None` por lo mismo.

**Las rutas son estas y no hay otras.** Es la tabla de `blueprint/00-contrato.md` § 3, y los pasos
que siguen las escriben una por una.

| Método | Ruta | Qué hace | Token |
|---|---|---|---|
| GET | `/salud` | 200 siempre, con `faltan` y `modo`. Nunca 503 | no |
| GET | `/webhook/{proveedor}` | alta de Meta: `hub.challenge` verbatim, **texto plano** | no |
| POST | `/webhook/{proveedor}` | entrante: cuerpo crudo, firma, dedupe, 200, y recién ahí el modelo | no |
| GET | `/panel` | el HTML, sin build ni CDN | cookie o `?token=` |
| GET | `/api/conversaciones` | lista, con `estado`, `limite` (techo 200) y `desde` | sí |
| GET | `/api/conversaciones/{id}` | `{id}` es `contacto_id`, nunca el número | sí |
| GET | `/api/leads` | la tabla del archivo 34 | sí |
| GET | `/api/pendientes` | los borradores de los pasos 3, 4 y 5 | sí |
| POST | `/api/pendientes/{id}/aprobar` | vuelve a correr el paso con `confirmado: true` | sí |
| POST | `/api/pendientes/{id}/rechazar` | lo cierra con motivo y no manda nada | sí |
| POST | `/api/webhooks-salientes` | da de alta un destino firmado | sí |

**Diez rutas, once métodos:** `/webhook/{proveedor}` comparte camino entre el GET y el POST. Esa es
la ruta que `blueprint/50-despliegue.md` da de alta en Meta como
`https://<tu-dominio>/webhook/meta` y en Zernio como `https://<tu-dominio>/webhook/zernio`: las dos
existen contra esta tabla, y con cualquier otra forma el alta es un 404.

**Tenés que ver.** El comando es el de `blueprint/00-contrato.md` § 3, y suma las dos mitades —la
app y el router del panel— a propósito:

```bash
.venv/bin/python -c "
from agente.servidor import app
from panel.panel import router as panel
rutas = [r for r in app.routes if hasattr(r, 'path')] + list(panel.routes)
caminos = sorted({r.path for r in rutas})
print(len(caminos), 'rutas ·', sum(len(r.methods) for r in rutas), 'métodos')
print(caminos)"
```

```
10 rutas · 11 métodos
['/api/conversaciones', '/api/conversaciones/{id}', '/api/leads', '/api/pendientes',
 '/api/pendientes/{id}/aprobar', '/api/pendientes/{id}/rechazar', '/api/webhooks-salientes',
 '/panel', '/salud', '/webhook/{proveedor}']
```

La lista sale en un solo renglón; acá va cortada para que entre. Diez rutas, y
`/webhook/{proveedor}` una sola vez: el GET y el POST comparten camino.

**Por qué no `app.routes` a secas.** Con los pines de `PINES.md` —fastapi 0.141.1 y starlette
1.3.1— `include_router` ya no copia las rutas del router adentro de `app.routes`: mete **un**
objeto `_IncludedRouter` que las envuelve, y ese objeto no tiene `.path`. Sobre el router que el
paso 4 exige —`APIRouter(dependencies=[Depends(exigir_token)])` más `include_router`, nunca ruta
por ruta— la forma vieja, `sorted({r.path for r in app.routes})`, que es la que este paso traía,
termina así contra un build entero:

```
AttributeError: '_IncludedRouter' object has no attribute 'path'
```

Las rutas del panel están montadas y contestan: lo roto era la verificación, no el servidor. El
razonamiento completo está en § 3.

**Si falla.**

- **`AttributeError: '_IncludedRouter' object has no attribute 'path'`.** Estás corriendo la forma
  vieja. Es la línea de arriba, con las dos mitades sumadas, y no `app.routes` a secas.
- **`Error loading ASGI app. Could not import module "agente.servidor"`.** El módulo no está donde
  uvicorn lo busca: falta `agente/__init__.py`, el archivo quedó con otro nombre, o lo estás
  corriendo desde otro directorio. El `Dockerfile` es verbatim y el que se acomoda es tu módulo.
- **El contenedor arranca sano y Railway lo mata igual.** Escuchaste en `127.0.0.1` o fijaste el
  puerto a mano. Railway inyecta `PORT` y el valor cambia entre despliegues.
- **`Address already in use`.** Otro proceso en 8000. `PORT=8010 .venv/bin/uvicorn ...`.
- **`ImportError` circular.** El servidor importa el panel y el panel importa los pasos. Los pasos no
  importan a ninguno de los dos.
- **`TypeError: metaclass conflict` con `pydantic/v1/types.py` adentro de la traza, y la suite
  entera en rojo desde `import panel.panel`.** No son tus rutas: falta la carga de `pydantic.v1`
  antes del `freeze_time` de `pruebas/conftest.py`. Sacar anotaciones no lo arregla —lo dispara
  cualquier parámetro anotado, y el paso 3 escribe uno—. Está explicado arriba, con la medición.

---

### Paso 2 · `GET /salud`, que nunca devuelve 503

**Objetivo.** Railway recibe 200 aunque falte la mitad de las credenciales, y el cuerpo dice cuáles.

**Hacé esto.**

```python
# agente/servidor.py
SIEMPRE = ("ANTHROPIC_API_KEY", "PANEL_TOKEN")

POR_PROVEEDOR = {
    "meta": ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_VERIFY_TOKEN",
             "META_APP_SECRET"),
    "zernio": ("ZERNIO_API_KEY", "ZERNIO_WEBHOOK_SECRET", "ZERNIO_ACCOUNT_ID"),
    "demo": (),
}

OPCIONALES = ("GOOGLE_CALENDAR_ID", "GOOGLE_SERVICE_ACCOUNT_JSON",
              "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
              "OPENAI_API_KEY", "SLACK_WEBHOOK_URL", "DATABASE_URL")


@app.get("/salud")
async def salud():
    requeridas = SIEMPRE + POR_PROVEEDOR.get(ajustes.proveedor, ())
    faltan = [v for v in requeridas + OPCIONALES if not os.getenv(v)]
    return {"ok": True, "proveedor": ajustes.proveedor, "base": await sondear_base(),
            "faltan": faltan, "modo": ajustes.modo}
```

**Las tres listas son estas y salen de `env.example`.** Dieciséis nombres acá, más `MODELO` y
`WHATSAPP_PROVIDER`, que tienen default en `agente/ajustes.py` y por eso no pueden faltar: dieciocho,
las dieciocho de `env.example`. Si mañana aparece una variable nueva ahí, entra en una de las tres o
`/salud` deja de verla.

- **`SIEMPRE`** son dos. `ANTHROPIC_API_KEY` hace falta también en `demo` —el demo se ahorra las
  credenciales de WhatsApp, no el modelo que redacta— y `PANEL_TOKEN` es la puerta del paso 4, que
  vacío devuelve 503 en todo el router.
- **`POR_PROVEEDOR`** se resuelve **en cada llamada, contra el proveedor configurado**, no una sola
  vez al importar. Con `meta` entran las cuatro de Meta y ninguna de Zernio, y al revés. Un proveedor
  que no está en el diccionario no revienta: `.get(..., ())` deja la lista vacía, y del POST dirigido
  a un proveedor que no es el configurado se encarga el 404 del paso 3.
- **`OPCIONALES`** son las que dejan un paso sin correr y no tumban el ciclo: sin Google no hay
  agenda, sin Supabase no hay CRM, sin `OPENAI_API_KEY` un audio frena con el motivo escrito, sin
  Slack la escalación pasa igual y lo que se pierde es el aviso.

`DATABASE_URL` está entre las opcionales a propósito: vacía no es un error, `normalizar_url()` cae a
`sqlite+aiosqlite:///./wca.db` y eso es lo correcto en tu máquina. En Railway ese SQLite se lo lleva
el próximo despliegue, y eso se lee en `base`, no en `faltan`.

**Con `WHATSAPP_PROVIDER=meta`, `META_APP_SECRET` entra en `faltan` si no está cargada.** Es la que
verifica la firma de cada entrega, no se usa para mandar nada, y por eso es la que más se olvida:
sin ella el servicio acepta cualquier POST que le llegue. Es el criterio que
`blueprint/50-despliegue.md`, paso 4, verifica antes de dar el despliegue por bueno: con el proveedor
en `meta`, ese nombre no puede estar en la lista. Si `faltan` no lo puede nombrar nunca, ese criterio
pasa por vacío y un servicio sin el secreto cargado da verde. Ver `blueprint/00-contrato.md` § 7.

**Nunca 503.** Este chequeo contesta "el proceso atiende", no "está bien configurado". Un 503 porque
falta `SUPABASE_URL` hace que Railway mate el despliegue, y con él el panel que te iba a decir cuál
falta: quedás con un servicio que no arranca y un tablero que dice `Deploy failed` y nada más. Una
requerida que falta se nombra igual de fuerte y devuelve 200 igual: la lista informa, el código de
estado no.

`healthcheckTimeout` son 120 segundos. `sondear_base()` va con su propio timeout corto y devuelve
`"sin_probar"` en vez de esperar: una base que todavía está arrancando cuelga la respuesta y el
despliegue muere por tiempo, no por la base.

`/salud` queda afuera del router del panel. Railway no manda cabeceras.

**Dos cosas que este handler no hace, y las dos las escribió un revisor siguiendo este mismo
paso.** No las encontró ninguna prueba ni la compuerta: las encontró mirando la salida de su build.
Van acá porque acá es donde se escribe `/salud`, y porque hasta esta ronda esta página inducía las
dos: `/salud` era el único lugar del archivo que tocaba la base, y ningún archivo decía dónde se
migra ni cómo se cierra la sonda.

1. **`/salud` no crea ni migra nada.** Ese revisor puso `create_all` adentro del handler, que es lo
   que queda a mano cuando la primera petición contra una base vacía devuelve `no such table`. Es
   un DDL colgado de una ruta **pública y sin token**: cualquiera que dé con la URL lo dispara, y
   Railway lo dispara solo cada vez que sondea, para siempre. Un chequeo de salud dice «el proceso
   atiende» y no escribe una sola tabla.

   **Dónde va la migración, para que no haya que inventarla acá.** `agente/base.py` expone
   `migrar(engine=None)` desde la fase 3 —`blueprint/30-generacion.md`, el paso de `base.py`— y se
   la llama **una vez, al arrancar el servicio**, en el `lifespan` de `agente/servidor.py` y en la
   misma función donde se llama `barrer_recordatorios()` de `blueprint/33-agenda.md` paso 4. En la
   suite la llama `correr_ciclo()` sobre el engine que vino en `deps`, que es el punto 3 de
   `blueprint/40-pruebas.md` paso 2. Son los dos únicos lugares.

2. **`sondear_base()` cierra lo que abre, y no construye un engine por llamada.** El mismo build
   dejaba una conexión colgada por cada `/salud`, y SQLAlchemy lo dice en voz alta: ocho
   `SAWarning: The garbage collector is trying to clean up non-checked-in connection` en una
   corrida con ocho llamadas. Railway sondea cada pocos segundos y no para nunca, así que eso no es
   un aviso de pruebas: es el pool agotado a las pocas horas, y lo que se lee del otro lado es un
   servicio que deja de contestar sin ningún error a la vista.

   La forma es el gestor de contexto, sobre el motor en curso y no sobre uno nuevo:

   ```python
   async def sondear_base() -> str:
       try:
           async with asyncio.timeout(2):
               async with motor().connect() as conexion:      # el `async with` la devuelve al pool
                   await conexion.execute(text("select 1"))
       except Exception:                                       # noqa: BLE001 — nunca 503
           return "sin_probar"
       return motor().url.get_backend_name()
   ```

   `motor()` es el motor en curso de `agente/base.py` —el nombre sale de
   `blueprint/40-pruebas.md` paso 2, punto 2, con `armar_motor(url)` y `usar_motor(engine)` al
   lado— y no uno construido acá: un `create_async_engine()` por petición abre un pool nuevo cada
   vez, y ése no lo cierra nadie aunque la conexión se devuelva.

**Tenés que ver.**

```bash
curl -s http://localhost:8000/salud
```

Con `demo` y un `.env` recién copiado, donde sólo están las dos de `SIEMPRE`:

```json
{"ok":true,"proveedor":"demo","base":"sqlite","faltan":["GOOGLE_CALENDAR_ID","GOOGLE_SERVICE_ACCOUNT_JSON","SUPABASE_URL","SUPABASE_SERVICE_KEY","OPENAI_API_KEY","SLACK_WEBHOOK_URL","DATABASE_URL"],"modo":"borrador"}
```

Sale en un solo renglón. Ninguna requerida en la lista, y `200` con siete nombres adentro.

Y que la de Meta esté donde tiene que estar, sin levantar el servicio:

```bash
.venv/bin/python -c "from agente.servidor import POR_PROVEEDOR, OPCIONALES; print('META_APP_SECRET' in POR_PROVEEDOR['meta'], 'META_APP_SECRET' in OPCIONALES)"
```

```
True False
```

Requerida con `meta`, y no opcional. Si sale `False True`, `/salud` da verde con el servicio
aceptando cualquier POST.

**Y que el handler las mire.** Las tres listas pueden estar perfectas y la comprensión recorrer
sólo `OPCIONALES`: eso también sale `True False` acá arriba, y sale `pass` en la compuerta. La que
manda es ésta, que le pregunta a `/salud` y no a las constantes:

```bash
.venv/bin/python -c "
import os
os.environ['WHATSAPP_PROVIDER'] = 'meta'
os.environ['META_APP_SECRET'] = ''
from fastapi.testclient import TestClient
from agente.servidor import app
print('META_APP_SECRET' in TestClient(app).get('/salud').json()['faltan'])"
```

```
True
```

Antes del `True` sale un aviso de starlette sobre `httpx`: viene de los pines, no es tuyo y no
cambia el resultado.

La variable va en vacío y no se saca del entorno: para `os.getenv` es lo mismo —el handler
pregunta `if not os.getenv(v)`— y a diferencia de sacarla sobrevive a un `.env` en disco, porque
`python-dotenv` no pisa lo que ya está puesto pero sí completa lo que falta.

Un `False` acá quiere decir que `faltan` no está recorriendo `requeridas`, y desde ahí **ninguna**
requerida puede aparecer nunca en esa lista. Eso no se lee como un defecto: se lee como un
despliegue sano. El «Tenés que ver» del paso 4 de `blueprint/50-despliegue.md` —«con el proveedor
en `meta`, `META_APP_SECRET` no puede estar en esa lista»— pasa por vacío, y un servicio que no
verifica una sola firma y contesta 401 en todas las entregas da verde. Los nodos `test_salud_*` de
`pruebas/test_panel.py` afirman lo mismo, con `meta` y con `zernio`, y en los dos sentidos: la que
falta aparece y la que está cargada no.

**Si falla.**

- **Devuelve 503.** Sacá la condición. Es la falla que se lee como "Railway no despliega" y no nombra
  a nadie.
- **El despliegue queda en `Deploying` y se cae a los dos minutos.** `/salud` está tocando la base sin
  timeout propio.
- **404.** `healthcheckPath` es `/salud`, no `/health`, y va sin barra final.
- **`faltan` las nombra todas y el `.env` está lleno.** Estás leyendo `os.environ` antes de que
  `python-dotenv` cargue el `.env`, así que el handler no ve una sola variable. El síntoma es la
  lista completa, no una lista vacía.
- **`faltan` vacío con el `.env` vacío.** `NameError: name 'OPCIONALES' is not defined` es el caso
  ruidoso y sale solo. El caso mudo es que `requeridas` no se esté sumando a la comprensión: entonces
  ninguna requerida puede aparecer nunca, `META_APP_SECRET` tampoco, y el criterio de
  `blueprint/50-despliegue.md`, paso 4, pasa por vacío en vez de por bueno.
- **`faltan` nombra las de Zernio con el proveedor en `meta`.** `POR_PROVEEDOR` se resolvió una vez al
  importar, con otro valor de `WHATSAPP_PROVIDER`. Se arma adentro del handler.
- **`SAWarning: The garbage collector is trying to clean up non-checked-in connection`, y hay uno
  por cada `/salud`.** `sondear_base()` abre y no devuelve. Es el `async with` de arriba, y no se
  arregla subiendo el `pool_size`.
- **La primera petición contra una base vacía dice `no such table` y el arreglo fue un `create_all`
  en `/salud`.** No va ahí: va una vez al arrancar. Ver los dos puntos de arriba.

---

### Paso 3 · Los dos webhooks, uno por proveedor

**Objetivo.** Cada proveedor tiene su URL de alta, y una entrega dirigida a un proveedor que no está
configurado no se procesa.

**Hacé esto.**

```python
@app.get("/webhook/{proveedor}")     # el alta de Meta: texto plano, no JSON
async def alta(proveedor: str, request: Request):
    ...

@app.post("/webhook/{proveedor}")
async def entrante(proveedor: str, request: Request):
    if proveedor != ajustes.proveedor:
        raise HTTPException(404)
    crudo = await request.body()     # bytes, antes de cualquier parseo
    ...
```

El proveedor va en la ruta para que puedas tener las dos altas puestas y cambiar
`WHATSAPP_PROVIDER` sin darlas de alta otra vez. El 404 al que no está configurado es a propósito:
verificar una entrega de Meta con el secreto de Zernio es un 401 en bucle que se lee como secreto mal
copiado.

**Invariante 1: la firma se verifica sobre el cuerpo crudo, con `hmac.compare_digest`.** Le pasás
`await request.body()`, esos bytes. Reserializar —parsear el JSON y volver a escribirlo, que cambia
el espaciado y el escapado de las tildes y produce otros bytes; ver `blueprint/00-contrato.md` § 10—
pasa todas las pruebas locales y falla todas las entregas reales. El módulo ya está en
`agente/firmas.py` y no se reescribe.

El orden y el presupuesto de 5 segundos están en `blueprint/31-proveedores.md`, paso 5: cuerpo,
firma, dedupe —descartar la entrega repetida, porque el proveedor entrega al-menos-una-vez y
reintenta hasta siete veces; § 10 otra vez—, 200, y recién después el modelo. El alta del webhook en
Meta se contesta como **texto plano**:
`JSONResponse("1158201444")` manda las comillas adentro del cuerpo y el alta no ocurre sin ningún
error a la vista.

**Tenés que ver.** Con `WHATSAPP_PROVIDER=meta`:

```bash
curl -s "http://localhost:8000/webhook/meta?hub.mode=subscribe&hub.verify_token=$WHATSAPP_VERIFY_TOKEN&hub.challenge=1158201444"
```

```
1158201444
```

Sin comillas y sin llaves.

**Si falla.**

- **Sale `"1158201444"`.** Es `JSONResponse`. Meta compara el cuerpo crudo contra lo que mandó.
- **404 en el alta.** La ruta lleva un proveedor y `WHATSAPP_PROVIDER` dice otro.
- **401 en cada entrega.** Mirá el prefijo: Meta manda `sha256=<hex>` y Zernio manda el hex pelado en
  minúscula. Es la única diferencia de formato entre los dos.
- **La misma persona contestada cuatro veces.** Contestaste después de correr el modelo. Zernio
  reintenta hasta siete veces y entrega al-menos-una-vez.

---

### Paso 4 · La puerta: `PANEL_TOKEN`

**Objetivo.** Sin token no hay panel ni API, y con el token equivocado tampoco.

**Hacé esto.** Una dependencia sobre el router entero, no ruta por ruta.

```python
def exigir_token(request: Request) -> None:
    esperado = (os.getenv("PANEL_TOKEN") or "").encode()
    if len(esperado) < 32:
        raise HTTPException(503, "PANEL_TOKEN vacío o de menos de 32 caracteres")
    dado = (request.headers.get("authorization", "").removeprefix("Bearer ")
            or request.cookies.get("wca_panel", "")
            or request.query_params.get("token", "")).encode()
    if not hmac.compare_digest(esperado, dado):
        raise HTTPException(401, "token del panel inválido")

router = APIRouter(dependencies=[Depends(exigir_token)])
```

**Lee tres lugares y en este orden: la cabecera `Authorization: Bearer`, la cookie `wca_panel` y el
parámetro `?token=` de la query.** El tercero no es una comodidad: el navegador entra la primera vez
por `/panel?token=…`, y sin esa rama ese primer ingreso da 401 y la cookie no se llega a poner
nunca. Está en `blueprint/00-contrato.md` § 3, con las otras dos reglas del servidor.

**El token es un requisito, no una opción.** El panel queda en una URL pública de Railway desde el
primer despliegue. Sin token, cualquiera que dé con la dirección lee las conversaciones de los
clientes del negocio: nombres, teléfonos, presupuestos y el resumen del CRM. Por eso vacío devuelve
503 y no "abierto": el default abierto es el que nadie nota hasta que ya pasó.

`hmac.compare_digest` —la comparación que tarda lo mismo acierte o falle; ver
`blueprint/00-contrato.md` § 10— y no `==`: la comparación normal corta en el primer byte distinto,
y eso se mide desde afuera. Va en el router entero, con `Depends` y nunca ruta por ruta, para que la
que agregues mañana nazca protegida.

Cuando el token entra por la query, el servidor deja una cookie `HttpOnly`, `SameSite=Strict`,
`Secure` sobre https, y redirige a `/panel` pelado, para que el token no quede en el historial ni en
los registros del proxy.

Generá el valor, no lo inventes:

```bash
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Tenés que ver.** Tres pedidos y no dos: sin token, con un token que no es, y con el bueno.

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/leads
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer no-es-este-el-token-pero-mide-lo-mismo" http://localhost:8000/api/leads
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $PANEL_TOKEN" http://localhost:8000/api/leads
```

```
401
401
200
```

El segundo es el que agrega información. Con `401` y `200` solos, una comparación con `startswith`
—o cualquier otra que abra con un prefijo— sale idéntica.

**Y después la suite, porque tres curls sobre una ruta no dicen nada de las otras siete:**

```bash
.venv/bin/python -m pytest pruebas/test_panel.py -q
```

```
20 passed
```

Ese archivo le pregunta a la app **qué tiene montado** y pide cada ruta bajo `/api/` y `/panel`
sin token, con el token equivocado y con el bueno; cuenta la comparación por AST, para que un
`compare_digest` que quedó sólo en un comentario no la pase; y afirma la contracara, que `/salud`
siga contestando sin token. Veinte nodos el día que se escribió —eran diecisiete antes de los tres
del escapado del paso 8, y este renglón se quedó atrás una ronda—: el número que manda lo imprime
`pytest pruebas/test_panel.py --collect-only -q`, que en este árbol dice `20 tests collected`.

La compuerta lo mira por su lado, sin levantar nada: el chequeo 21 `panel-cerrado` de
`scripts/auditar.py` lee el árbol y marca toda ruta bajo `/api/` que no cuelgue de un router con
la dependencia puesta.

**Si falla.**

- **503 en todo.** `PANEL_TOKEN` vacío o corto. Generá uno con el comando de arriba.
- **200 sin cabecera.** El `Depends` quedó en una ruta suelta y no en el router.
- **401 con el token correcto.** La cabecera llegó como `bearer` en minúscula, o la variable del
  shell arrastra un salto de línea. Compará los largos antes de dudar del valor.
- **401 la primera vez que abrís `/panel?token=…` en el navegador, y con `curl` y cabecera va 200.**
  `exigir_token` no está mirando la query. Son tres lugares y el tercero es el único que puede abrir
  la puerta cuando todavía no hay cookie.
- **`/salud` empezó a pedir token.** Se coló adentro de este router. Railway no manda cabeceras y el
  despliegue se muere en el chequeo de salud.
- **`auditar` marca `panel/router_abierto`.** Es esta línea, sin el `dependencies=`. Es la que
  hace que el kit entero dé verde con el panel abierto en una URL pública.
- **`auditar` marca `panel/ruta_suelta`.** Hay una ruta de `/api/` montada con `@app.get(...)`
  sobre la app, o sobre un segundo router sin la dependencia. El router puede estar perfecto: esa
  ruta queda afuera igual.
- **`auditar` marca `panel/dependencia_por_ruta`.** La dependencia quedó en cada ruta y no en el
  router. Cierra hoy y abre mañana: la que agregues nace sin nada y nadie la va a mirar dos veces
  porque las de al lado están bien.

---

### Paso 5 · La API de lectura

**Objetivo.** Se listan conversaciones y leads sin abrir la base a mano.

**Hacé esto.** Tres rutas, todas colgadas del router del paso 4.

```
GET /api/conversaciones?estado=&limite=50&desde=   lista, ordenada por último mensaje
GET /api/conversaciones/{id}                        mensajes, score, objeción y los seis pasos
GET /api/leads?etapa=&limite=50                     la tabla del archivo 34
```

`{id}` es `contacto_id`, el `businessScopedUserId` —el identificador que el proveedor le da a un
contacto dentro de tu negocio; ver `blueprint/00-contrato.md` § 10—, y no el número: es la clave del
archivo 34 y el teléfono puede faltar.

`limite` va con techo —200— y la página siguiente sale por cursor con `desde`. Sin techo, un
`GET /api/conversaciones` contra seis meses de chats devuelve todo, y el que se queda sin memoria es
el contenedor, no el navegador.

Devuelven JSON y nada de HTML. El HTML lo arma el paso 8, y ahí se escapa.

**Tenés que ver.**

```bash
curl -s -H "Authorization: Bearer $PANEL_TOKEN" "http://localhost:8000/api/leads?limite=1"
```

```json
[{"contacto_id":"bsu_01HZK3M9QX7T2VW4","numero":null,"etapa":"calificado","score":62,"temperatura":"tibio","proximo_paso":"Confirmar horario"}]
```

**Si falla.**

- **`[]` con filas en la base.** Estás filtrando por número. Se indexa por `contacto_id`.
- **500 con `Object of type datetime is not JSON serializable`.** Devolvé ISO 8601 con offset, el
  mismo formato del contrato.
- **La lista tarda y empeora con el tiempo.** Falta `leads_etapa_idx` del archivo 34.
- **El proxy registra los cuerpos.** Esa respuesta trae teléfonos y resúmenes del CRM. Apagá el
  registro de cuerpos para `/api/` antes de desplegar, no después.

---

### Paso 6 · La bandeja: pendientes, aprobar y rechazar

**Objetivo.** Un borrador —el texto que el paso redactó y no mandó, esperando confirmación; ver
`blueprint/00-contrato.md` § 10— se resuelve de a uno, y aprobar es lo único que dispara un envío.

**Hacé esto.**

```
GET  /api/pendientes                los borradores de los pasos 3, 4 y 5
POST /api/pendientes/{id}/aprobar   vuelve a correr el paso con `confirmado` en verdadero
POST /api/pendientes/{id}/rechazar  lo cierra con motivo y no manda nada
```

**La fila la escribe el paso, no el panel, y este archivo no es su dueño.** El paso 3 en `borrador`
redacta, escribe la fila en `pendientes` y ahí termina; lo escribe `blueprint/60-bandeja.md` paso 2
y ahí está también el archivo `bandeja/<id>.md` que la acompaña. Se dice acá porque estas tres
rutas no pueden hacer nada sin esa fila, y porque **hasta esta ronda nada en el árbol la escribía y
ninguna prueba la pedía**: `pruebas/test_panel.py` le pasaba a `pagina()` una lista de pendientes
fabricada a mano, y el chequeo 22 `rutas-del-contrato` sólo mira que las rutas estén montadas. Un
build donde el paso redacta y no guarda pasa entero: `/api/pendientes` devuelve `[]` porque no hay
nada, aprobar devuelve 404 para todo id porque no hay nada que aprobar, y las dos respuestas se
leen como correctas mientras quien opera abre la bandeja vacía todos los días.

**Las tres formas, que ahora están fijadas porque hay una prueba que las pide.**

`GET /api/pendientes` devuelve una **lista JSON pelada**, un objeto por borrador sin resolver,
igual que `/api/leads` del paso 5 y con la forma exacta que `pagina(datos)` espera en
`datos["pendientes"]` (paso 8). Cinco claves como piso, y las que sume el panel de razonamiento:

```json
[{"id":1,"paso":3,"estado":"pendiente","contacto_id":"bsu_01HZK3M9QX7T2VW4","texto":"El curso sale 12000 MXN…"}]
```

- **`id`** es lo único con lo que se puede aprobar. **`estado`** nace en `pendiente`: es el valor
  que mira el `update … where estado = 'pendiente'` de más abajo, y con cualquier otro ese update
  no encuentra nada y aprobar no manda nunca. **`texto`** es el borrador tal como lo redactó el
  paso: es lo que quien opera lee antes de firmar, así que tiene que ser el mismo que después sale.
- **`contacto_id` y nunca el número.** Es la clave del archivo 34 y el teléfono puede venir nulo.
- **Los tres pasos que dejan borrador no son tres siempre.** El 3 deja el suyo con el texto; el 5
  deja la fila del CRM armada con `escrito` en falso (`blueprint/00-contrato.md` § 13); el 4 deja
  borrador **sólo si hay un horario elegido**, porque sin eso no hay nada que agendar y su motivo
  es «no hay horario elegido» y no el del modo (`blueprint/33-agenda.md` paso 3).

`POST /api/pendientes/{id}/aprobar` va **sin cuerpo** y devuelve el pendiente resuelto. La
excepción es el borrador del paso 4: ahí el cuerpo lleva el horario que eligió quien opera,
`{"horario_elegido": "…"}`, y ese valor entra en `mensaje.horario_elegido` de la misma entrada con
la que se vuelve a correr el paso. Sin eso, aprobar el borrador del paso 4 desde la bandeja no
agenda nada: la confirmación autoriza, no elige.

`POST /api/pendientes/{id}/rechazar` lleva `{"motivo": "…"}`, deja el estado en `rechazado` y
devuelve la misma forma con `enviado` en falso. Ese motivo es el rastro: es lo que `/bandeja
resumen` cuenta en «Los frenaste» (`blueprint/60-bandeja.md` paso 4).

**Los dos códigos que no son 200, y ninguno es 500.**

| Caso | Código | Qué devuelve |
|---|---|---|
| el `id` no existe | `404` | un pendiente que no está no es un error del servicio |
| el `id` ya se resolvió | `409` | con `ya_resuelto` adentro del cuerpo |

Un 500 en esta ruta deja a quien acaba de apretar `va` sin saber si el mensaje salió, y deja el
cuerpo de la traza —con el texto del chat adentro— en el registro del proxy.

**Aprobar no manda desde el panel.** Vuelve a correr el paso con `confirmado` en verdadero, y el que
manda sigue siendo el único `enviar()`: ventana de 24 horas —el plazo desde el último mensaje del
contacto en el que WhatsApp deja contestar texto libre; ver `blueprint/00-contrato.md` § 10—,
chequeo de baneo y nunca escribirle primero a quien no escribió. **Invariante 2.** Un `post` al
proveedor desde el panel es un segundo camino de salida, y lo que se pierde ahí no es una respuesta:
es el número de WhatsApp del negocio.

Aprobar dos veces no manda dos veces. El pendiente pasa a `aprobado` con un
`update ... where estado = 'pendiente'` y se decide por si actualizó, no por un `select` previo. La
`Idempotency-Key` del envío —una cabecera con una clave sacada del contenido: conversación, paso y
hash del texto; § 10 otra vez— sale del contenido y no de un uuid nuevo por intento, que sería un
contador y no una idempotencia.

Con cada borrador viaja su panel de razonamiento —el score con el motivo, si la objeción estaba en el
playbook, de qué hueco de `disponibilidad` salió cada horario—, que es lo que muestra `/bandeja`. La
compuerta numérica de `/soltar` está en `blueprint/60-bandeja.md`.

**Tenés que ver.**

```bash
curl -s -X POST -H "Authorization: Bearer $PANEL_TOKEN" http://localhost:8000/api/pendientes/1/aprobar
```

```json
{"id":1,"paso":3,"estado":"aprobado","enviado":true}
```

El mismo `POST` repetido devuelve `409` con `ya_resuelto`.

**Y después la suite, porque un curl sobre el pendiente 1 no dice nada de los otros cuatro casos:**

```bash
.venv/bin/python -m pytest pruebas/test_bandeja.py -q
```

```
8 passed
```

Ese archivo corre un turno en `borrador` con el arnés de `pruebas/proveedor_falso.py` y después le
pregunta a estas tres rutas por HTTP, con el `TestClient`. Afirma cinco cosas, cada una en las dos
direcciones: que el turno **escriba** la fila y que mientras esté pendiente no salga nada al cable;
que aprobar mande **un** mensaje con la `Idempotency-Key` que pone `enviar()` y que rechazar no
mande ninguno; que resolver dos veces —y también rechazar y después aprobar— conteste 409 sin mover
la cuenta de envíos; y que el id inventado dé 404 **con el id real contestando 200 en la misma
corrida**, que es lo único que separa un 404 honesto de un build que contesta 404 a todo porque
nunca tuvo un pendiente. Ocho nodos el día que se escribió: el número que manda lo imprime
`pytest pruebas/test_bandeja.py --collect-only -q`.

**Si falla.**

- **El mismo texto salió dos veces.** El `update` no era condicional, o alguien hizo `select` y
  después `update`. Entre esas dos líneas entra el segundo clic.
- **`GET /api/pendientes` devuelve `[]` con el agente contestando en `borrador` todos los días.**
  Nadie escribe la fila. El paso redacta, muestra y no guarda: se arregla en el paso que redacta y
  no acá; ver `blueprint/60-bandeja.md` paso 2.
- **Aprobar contesta 404 sobre un id que `GET /api/pendientes` acaba de devolver.** La ruta y el
  paso están leyendo dos bases distintas, o el `id` de la lista no es el que la ruta busca.
- **Aprobar contesta 200 y `enviado` en verdadero y el transporte no vio nada.** La ruta marcó el
  pendiente como aprobado y no volvió a correr el paso. `enviado` sale del `Resultado` de
  `enviar()`, no de que el `update` haya andado.
- **`enviado` en verdadero y no llegó nada.** El paso corrió y `enviar()` se negó por la ventana.
  Mirá `respuesta.ventana_abierta`: fuera de las 24 horas hace falta una plantilla aprobada, o sea
  un texto con huecos que Meta revisó de antemano y que se da de alta antes (§ 10).
- **Aprobar tarda medio minuto y el navegador corta.** El paso llama al modelo. Devolvé 202 y que la
  bandeja consulte; si no, el pendiente queda a medias y nadie sabe si salió.

---

### Paso 7 · Los webhooks salientes, firmados sobre los bytes que se mandan

**Objetivo.** Los eventos del agente salen firmados hacia donde vos digas, y el destino no puede ser
cualquiera.

**Hacé esto.** `POST /api/webhooks-salientes` da de alta un destino:
`{"url": "https://...", "eventos": ["lead.calificado", "cita.agendada"]}`.

Se serializa una vez, se firman esos bytes y se mandan esos bytes:

```python
cuerpo = json.dumps(evento, separators=(",", ":"), ensure_ascii=False).encode()
firma = hmac.new(secreto, cuerpo, hashlib.sha256).hexdigest()
await cliente.post(destino, content=cuerpo, timeout=10.0,
                   headers={"X-WCA-Signature": f"sha256={firma}",
                            "X-WCA-Event-Id": evento_id,
                            "Content-Type": "application/json"})
```

`content=` y no `json=`. Con `json=` httpx vuelve a serializar con su propio espaciado y el que
recibe verifica contra otros bytes: es el invariante 1 visto desde el otro lado, y falla igual de
tarde y con la misma cara de secreto mal copiado.

El destino se valida al darlo de alta: sólo `https`, y nunca `localhost`, `127.0.0.0/8`,
`169.254.169.254` ni rangos privados. Un destino libre convierte esta ruta en una forma de pedirle
cosas a la red interna de Railway desde afuera.

Sale por el cliente de `agente/http.py`, con `timeout=`, y desde la cola: nunca adentro del ciclo del
webhook entrante, que tiene cinco segundos.

**Tenés que ver.** Dos cosas, y no son de la misma categoría.

**La que mira alguien**: que la ruta esté montada y cerrada. `POST /api/webhooks-salientes` está en
la tabla de once métodos del chequeo 22 de `scripts/auditar.py`; el 21 `panel-cerrado` exige que
cuelgue del router con la dependencia; y `pruebas/test_panel.py` la pide sin token, con el token
equivocado y con el bueno. Eso corre solo en cada compuerta.

**La que no mira nadie, y va dicho acá**: la firma sobre los bytes que se mandan. Es una
comprobación **a mano y de una sola vez**, para ver el `content=` contra el `json=` con tus propios
ojos. Escribí `pruebas/webhook_saliente.py`: firmá un evento, verificá esos bytes, y verificá de
nuevo los mismos datos reserializados con `json.dumps` por default.

```bash
.venv/bin/python -m pruebas.webhook_saliente
```

```
cuerpo 214 bytes · firma verifica: True · reserializado verifica: False
```

El `False` vale tanto como el `True`.

**Y no lo exige nadie, que es el punto de este párrafo.** El nombre no empieza con `test_`, así que
`pytest` no lo junta; y no está en `PISO_DE_MODULOS` de `scripts/auditar.py`. Sobre el kit de esta
ronda:

```bash
grep -rn webhook_saliente pruebas/ scripts/ || echo "sin una sola línea"
```

```
sin una sola línea
```

La única página que lo nombra es ésta. Si mañana lo borrás, la compuerta sigue en
`pass` y la suite en el mismo total. Vale por lo que te enseña la primera vez que lo corrés, no como
piso. El día que alguien quiera que sea un piso son dos movimientos, y ninguno es de este archivo:
que se llame `test_…` y las dos verificaciones sean aserciones —lo decide `blueprint/40-pruebas.md`,
que es el dueño de `pruebas/`— o que entre en la lista de la compuerta, que es un cambio del kit.

**Si falla.**

- **El destino dice firma inválida y el JSON se ve idéntico.** Mandaste con `json=`. Los espacios de
  httpx no son los tuyos.
- **`169.254.169.254` quedó aceptado.** Falta el filtro. Es la dirección de metadatos de la nube.
- **Cada evento tarda 30 segundos.** El destino cuelga y no pusiste `timeout=`. Si eso corre adentro
  del webhook entrante, se te va el presupuesto de cinco segundos entero.

---

### Paso 8 · `GET /panel`, HTML sin paso de build

**Objetivo.** El panel se abre en el navegador, lo sirve el mismo FastAPI y el repo corre sin `npm`.

**Hacé esto.** Una ruta que devuelve un HTML entero, con el CSS adentro de un `<style>` y el poco JS
adentro de un `<script>`. Ninguna etiqueta apunta a un CDN. No hay `package.json`, ni `dist`, ni
paso de build: se clona y corre.

Tres vistas y nada más: la bandeja, las conversaciones y los leads. **Las filas se arman del lado del
servidor y viajan adentro del HTML**, y el poco JS que hay sólo refresca. Las rutas de `/api/` siguen
devolviendo JSON —paso 5— y son las que usa ese refresco y cualquier otro cliente; lo que no hacen es
armar HTML.

**El HTML lo arma una función de módulo y se llama `pagina(datos)`.** `datos` trae `leads`,
`conversaciones` y `pendientes`, con la forma exacta en que los devuelven las rutas de `/api/`, y la
función devuelve la página entera como cadena. La ruta junta los datos, llama a `pagina()` y
contesta `HTMLResponse`. Y hace una cosa más, que es la regla 3 de `blueprint/00-contrato.md` § 3:
cambiar el `?token=` de la primera entrada por la cookie.

```python
MES = 60 * 60 * 24 * 30


@router.get("/panel", response_class=HTMLResponse)
async def ver_panel(request: Request):
    ya_tenia = (request.headers.get("authorization", "").removeprefix("Bearer ")
                or request.cookies.get("wca_panel", ""))
    token = request.query_params.get("token", "")
    if token and not ya_tenia:        # entró por la query: es lo único que lo dejó pasar
        vuelta = RedirectResponse("/panel", status_code=303)
        vuelta.set_cookie("wca_panel", token, max_age=MES, httponly=True, samesite="strict",
                          secure=request.headers.get("x-forwarded-proto",
                                                     request.url.scheme) == "https")
        return vuelta
    return pagina(await datos_del_panel())
```

**Por qué esa rama vive acá y no en `exigir_token`.** La dependencia contesta sí o no; no devuelve
respuestas. Y de las diez rutas, `/panel` es la única a la que llega un navegador con la URL en la
barra: las de `/api/` las pide el JS con la cookie ya puesta. El paso 4 dice que el servidor deja la
cookie y redirige a `/panel` pelado, y éste es el renglón donde eso pasa. Sin él, `exigir_token`
acepta el `?token=` en cada pedido y el token se queda en la barra, en el historial y en los
registros de cada proxy del camino, que es exactamente lo que la regla 3 evita.

**`ya_tenia` repite la precedencia de `exigir_token` a propósito** —cabecera, cookie, y recién ahí
la query—. Sin esa guarda, un `?token=` cualquiera pegado a la URL de alguien que ya tiene la cookie
buena se la pisa con el valor de la query. Con ella, el único caso que escribe cookie es aquel en
que la cookie todavía no existe.

Dos detalles del bloque, cortos. `RedirectResponse` es un `Response`, así que sale tal cual: el
`response_class=HTMLResponse` manda sobre lo que la ruta devuelve como cadena y no sobre esto. Y
`secure` sale del `X-Forwarded-Proto` antes que del esquema de la petición, porque detrás del proxy
de Railway el esquema que ve uvicorn es `http` y la cookie quedaría sin `Secure`.

Medido en esta máquina, con fastapi 0.141.1 y starlette 1.3.1, sobre esta ruta y el `exigir_token`
del paso 4:

```
sin nada            401
con ?token=         303 · /panel · wca_panel=…; HttpOnly; Max-Age=2592000; Path=/; SameSite=strict
con ?token= malo    401
con la cookie       200 · <!doctype html><title>panel</title>l
cookie + query malo 200 · set-cookie None
con la cabecera     200 · set-cookie None
```

Va sin anotación de retorno, y ahora por dos motivos: devuelve dos cosas —la cadena y el redirect—,
y con `response_class=HTMLResponse` el modelo de respuesta que FastAPI armaría con un `-> str` no se
mira. Ponerla no rompe nada. Lo que rompía era el `freeze_time` de la suite contra cualquier
anotación, y eso se arregló en `pruebas/conftest.py`; el paso 1 lo cuenta con la medición.

Separarla no es prolijidad: es lo único que hace verificable el párrafo que sigue. Con el HTML
armado adentro del handler, para meterle una fila envenenada hay que migrar una base, sembrar un
lead y levantar el servicio, y eso no lo hace ninguna prueba —por eso el escapado del panel llegó
hasta acá con un `curl | grep` que no corre nadie—. Con `pagina()` afuera, `pruebas/test_panel.py` le
pone enfrente un `resumen` con `<script>` adentro y lee la cadena que sale.

**Todo lo que viene de un chat se escapa con `html.escape` adentro de `pagina()`.** El panel muestra
texto que escribió un desconocido por WhatsApp: el `resumen` del CRM lo redacta el modelo leyendo lo
que mandó el contacto, el `nombre` viene del perfil de WhatsApp y el texto del borrador del paso 3 es
la respuesta a ese mensaje. Un `<script>` adentro de cualquiera de los tres corre en el navegador de
quien lee la bandeja, y ahí vive la cookie `wca_panel`: es el camino más corto que existe para perder
el panel entero.

Dos cosas que se hacen mal y se leen bien:

- **`html.escape(valor, quote=False)`.** Adentro de un atributo —un `title=`, un `value=`, un
  `data-…`— no hace falta abrir una etiqueta: alcanza con cerrar la comilla. El default escapa las
  comillas; el default es lo que hay que dejar quieto.
- **Escapar a mano con tres `.replace()`.** Se olvida el `&` primero —y ahí `&amp;lt;` vuelve a
  leerse como `<`— o se olvidan las comillas. `html.escape` es de la biblioteca estándar y no hay
  motor de plantillas que escape por vos: sin paso de build, si no está escrito, no pasa.

**El símbolo va al piso de la compuerta.** `PISO_DE_MODULOS["panel/panel.py"]` de `scripts/auditar.py`
pide hoy `router` y `exigir_token`; suma `pagina`, y por el mismo motivo que los otros dos: es el
nombre que busca `pruebas/test_panel.py`, y sin él esas pruebas se caen con «no define `pagina`» en
vez de mirar lo que vinieron a mirar. El chequeo 14 exige que exista; las pruebas exigen que escape.

**Tenés que ver.** Ninguna referencia externa en la página:

```bash
curl -s -H "Authorization: Bearer $PANEL_TOKEN" http://localhost:8000/panel | grep -c "https\?://\|<script src"
```

```
0
```

Y la primera entrada por la query, que es la regla 3 de `blueprint/00-contrato.md` § 3: un `303` a
`/panel` pelado con la cookie ya puesta, y no un `200` con el token en la barra.

```bash
curl -s -o /dev/null -D - "http://localhost:8000/panel?token=$PANEL_TOKEN" | grep -i "^HTTP/\|^location\|^set-cookie"
```

```
HTTP/1.1 303 See Other
location: /panel
set-cookie: wca_panel=…; HttpOnly; Max-Age=2592000; Path=/; SameSite=strict
```

`Secure` no sale ahí porque estás en `localhost` por http. Sobre el dominio de Railway sí sale, y
eso es lo que mira la última línea del `secure=` del bloque.

Y los tres nodos del escapado, que sí corren sin levantar nada:

```bash
.venv/bin/python -m pytest pruebas/test_panel.py -q -k escapa
```

```
3 passed, 17 deselected
```

Medido sobre un build en verde, cambiando `html.escape` por `str` adentro de `pagina()`: la suite
daba `199 passed` y el chequeo 21 `panel-cerrado` seguía en `[ok]`. Con estos tres, esa misma poda
son tres rojos.

**Si falla.**

- **Sin red el panel se ve sin estilos.** Quedó un `<link>` a un CDN. Pegá el CSS adentro.
- **Un mensaje con `<b>` se ve en negrita.** Estás inyectando sin escapar. Escapá y volvé a mirar la
  bandeja con un mensaje que traiga etiquetas.
- **`el HTML del panel trae <script>alert(1)</script> crudo`.** Falta el `html.escape` en el campo
  que muestra esa fila. No alcanza con escapar el que te acordaste: el rojo nombra el texto, no el
  campo.
- **`el HTML del panel no trae &lt;script&gt;… en ninguna parte`.** O el panel no muestra ninguno de
  los campos que escribe un contacto —y entonces la promesa de arriba no promete nada—, o los está
  borrando en vez de escaparlos. Escapar no es sacar: quien opera tiene que ver qué dijo el contacto,
  con las etiquetas a la vista, para decidir si escala.
- **`no hay una sola llamada a html.escape`.** Está escapado a mano. Ver arriba.
- **El navegador da 401 y `curl` con cabecera da 200.** Entrá una vez por `/panel?token=...` para que
  el servidor deje la cookie.
- **Entrás por `/panel?token=…`, se ve la página, y el token se queda en la barra.** Quedó afuera la
  rama del redirect. `exigir_token` te dejó pasar por la query y nadie cambió la query por la cookie:
  se ve bien, y ese token viaja en cada pedido y queda escrito en el historial del navegador y en el
  registro de todos los proxys del camino. Se mira con `-o /dev/null -w "%{http_code}"`: tiene que
  dar `303` y no `200`.
- **Abriste `/panel?token=…` con la sesión ya abierta y quedaste afuera.** La rama corre sin la
  guarda `ya_tenia` y le escribió a la cookie lo que traía la query. Un token viejo pegado a un
  enlace cierra la sesión de quien ya estaba adentro.
- **No hay `curl` (Windows).**
  `Invoke-WebRequest -Headers @{Authorization="Bearer $env:PANEL_TOKEN"} http://localhost:8000/panel`.

---

## Qué quedó hecho

`agente/servidor.py` con el nombre que el `Dockerfile` ya nombraba, escuchando en `0.0.0.0` con el
`PORT` del entorno, y con las diez rutas de la tabla y ninguna más. `/salud` que devuelve 200 y la
lista de lo que falta —las requeridas del proveedor configurado incluidas—, fuera del router del
panel. Los dos webhooks por proveedor, en el mismo
camino que después da de alta `blueprint/50-despliegue.md`, con la firma sobre el cuerpo crudo. Todo
lo demás detrás de `PANEL_TOKEN`, comparado con `compare_digest` y leído de los tres lugares. La
bandeja que aprueba sin abrir un segundo camino de salida. Los webhooks salientes firmados sobre los
bytes que se mandan. Y un panel que se sirve solo.

Y la puerta con algo encima, que hasta esta ronda no tenía: `pruebas/test_panel.py` pide cada ruta
sin token, con el token equivocado y con el bueno, y el chequeo 21 `panel-cerrado` de la compuerta
marca la que no cuelgue del router con la dependencia. Antes de esto, `router = APIRouter()` —una
línea sin el `dependencies=`— daba `PASS · 0 errores · 0 avisos · 0 salteados` con `GET /api/leads`
devolviendo los teléfonos y los resúmenes del CRM sin ninguna credencial.

Y la otra mitad de esa misma puerta, que es la que se abre desde adentro: tres nodos más en el mismo
archivo le pasan a `pagina()` un lead con `<script>alert(1)</script>` en el `resumen` y afirman los
dos sentidos —el guión no sale crudo, y el texto igual se ve, escapado—, más la comilla del atributo
y la llamada a `html.escape` contada por AST y no por texto. Sacar el escapado dejaba la suite en
`199 passed` y el chequeo 21 en `[ok]`.

**Y la bandeja, que era la última superficie de este archivo sin una sola aserción encima.** Las
tres rutas estaban montadas, contestaban 401 sin token y salían en el chequeo 22: lo que no había
era una fila de `pendientes` escrita por nadie en todo el árbol, así que un build donde el paso
redacta y no guarda daba `PASS · 0 errores · 0 avisos · 0 salteados` con el único camino por el que
un borrador se convierte en un mensaje devolviendo 404 para siempre. `pruebas/test_bandeja.py` es
lo que lo pide ahora, y las formas de las tres respuestas quedaron escritas en el paso 6 porque hay
una prueba que las lee.

Y dos cosas de `/salud` que se escriben en el paso 2 y que ninguna prueba veía: **ese handler no
crea ni migra tablas** —un DDL colgado de una ruta pública sin token, disparado por la sonda de
Railway cada pocos segundos— y **`sondear_base()` devuelve al pool lo que saca**, con `async with`
y sobre el motor en curso. Las dos las escribió un revisor siguiendo este archivo, las dos las vio
mirando la salida de su build, y las dos las inducía esta página.

Anotalo en `.wca-estado.json`: `fase` en `panel` y el sha256 de cada archivo escrito.

**Próximo archivo:** `blueprint/40-pruebas.md`, que corre `caso-01.md` contra `demo` con sus seis
aserciones.
