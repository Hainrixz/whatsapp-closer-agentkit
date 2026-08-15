# 30 · La generación

**Fase 3.** Entrás con la entrevista contestada y `.venv` armado; salís con el núcleo de `agente/`:
el paquete, la configuración, el único cliente HTTP, la base, el emisor del contrato y el prompt.

**La fase 3 no termina acá.** El transporte —`enviar()` y los tres proveedores— lo escribe
`blueprint/31-proveedores.md`, y los medios y los cuerpos de los pasos,
`blueprint/32-multimodal.md`. Cada archivo de `agente/` tiene un solo dueño y está en la tabla de
`blueprint/00-contrato.md` § 4.

**Se copia con `cp`, nunca se reescribe:** lo de `plantillas/`. Una copia por bash es exacta byte a
byte por construcción; un Read seguido de un Write es una paráfrasis, y una paráfrasis plausible de
estos archivos es indetectable: instala, construye, despliega y falla después. Sólo se editan los
placeholders que `plantillas/MANIFIESTO.json` nombre para ese archivo, y hoy las siete entradas
traen `"placeholders": []`.

```
plantillas/infra/requirements.txt             → requirements.txt  (ya copiado en la fase 1)
plantillas/config/playbook-base.yaml          → config/playbook-base.yaml  (ya copiado en la fase 2)
plantillas/infra/Dockerfile                   → Dockerfile
plantillas/infra/railway.json                 → railway.json
plantillas/contratos/wire_schema.py           → agente/wire_schema.py
plantillas/contratos/wire_schema.golden.json  → agente/wire_schema.golden.json
plantillas/seguridad/firmas.py                → agente/firmas.py
```

Las dos que ya venían copiadas se verifican igual en el paso 1: `--proyecto` mira las siete. Si
`config/playbook-base.yaml` falta, el paso 1 de `blueprint/25-playbook.md` no corrió su `cp` —va en
los tres caminos, no sólo en el A—; volvé ahí antes de seguir.

**Se escribe desde la entrevista:** lo que dice «acá» en la columna de la derecha. Anotá el sha256
de cada archivo escrito en `.wca-estado.json`, o `/seguir` no puede saber qué cambiaste a mano.

```
agente/__init__.py     el paquete, y vacío: no reexporta nada             acá, paso 2
agente/ajustes.py      las 18 variables de `.env`: tipo, ningún valor      acá, paso 2
agente/config.py       proyecta `config/*.yaml` a la entrada, y el modo    acá, paso 2
agente/http.py         el ÚNICO cliente httpx, con `timeout=`              acá, paso 3
agente/base.py         contactos, mensajes, dedupe y la ventana de 24 h    acá, paso 3
agente/salida.py       el emisor del contrato: presiembra los seis pasos   acá, paso 4
agente/prompt.py       el prefijo estático del prompt de sistema           acá, paso 5
agente/modelo.py       la llamada a Anthropic con el esquema angosto       acá, paso 5

agente/enviar.py       la ÚNICA salida hacia WhatsApp                      31-proveedores.md, paso 1
                       `avisar_interno()`, el aviso del paso 6, al final   32-multimodal.md, paso 5
agente/proveedores/    la base abstracta, `demo`, `meta` y `zernio`        31-proveedores.md
agente/medios.py       la bajada de audio e imagen                         32-multimodal.md, paso 1
agente/pasos/          `paso_1`, `paso_2`, `paso_3` y `paso_6`             32-multimodal.md
agente/integraciones/  `calendario.py` y `paso_4_agenda.py`                33-agenda.md
                       `crm.py` y `paso_5_crm.py`                          34-crm.md
agente/servidor.py     la app de FastAPI y sus diez rutas                  35-panel-api.md
panel/panel.py         la bandeja de borradores, detrás de `PANEL_TOKEN`   35-panel-api.md
agente/ciclo.py        `correr_ciclo(entrada, *, modelo, deps)`            40-pruebas.md, paso 2
pruebas/*.py           las seis aserciones, los dobles y el simulador      40-pruebas.md
```

**El módulo del servidor se llama `agente/servidor.py`, desde ahora y en todas las fases.** No hay
otro módulo de aplicación en el árbol, ni acá ni después. No es preferencia: el `CMD` del
`Dockerfile` que copiás en el paso 1 dice `exec uvicorn agente.servidor:app`, ese archivo es
verbatim y no se edita nunca. Ver `blueprint/00-contrato.md` § 3.

**El orden.** Primero lo copiado, así los invariantes están en disco antes de la primera línea
propia. Después el paquete y la configuración; después la base y el cliente HTTP, que no importan a
nadie; después el emisor del contrato, y al final el prompt y la llamada al modelo.

Lo que sigue después de este archivo va en ese orden por la misma razón: `enviar()` necesita
cliente, base y proveedor, y los cuerpos de los seis pasos necesitan `enviar()`. Escritos acá
importan una función que todavía no existe, y su verificación —`pytest pruebas -q`— corre sobre
pruebas que escribe `blueprint/40-pruebas.md`. Adelantarlos es quedarse con imports rotos a mitad de
camino.

---

### Paso 1 · Copiá las cinco plantillas que faltan

**Objetivo.** Los siete archivos verbatim están en su destino y sus hashes coinciden.

**Hacé esto.** En PowerShell es `Copy-Item origen destino`, el mismo par por línea.

```bash
mkdir -p agente
cp plantillas/infra/Dockerfile Dockerfile
cp plantillas/infra/railway.json railway.json
cp plantillas/contratos/wire_schema.py agente/wire_schema.py
cp plantillas/contratos/wire_schema.golden.json agente/wire_schema.golden.json
cp plantillas/seguridad/firmas.py agente/firmas.py
python3 scripts/hash_plantillas.py --verificar --proyecto . && echo COPIA-OK
```

**Tenés que ver.** Tres líneas, y ningún archivo nombrado:

```
7 plantillas al día con el manifiesto.
7 archivos generados iguales a su plantilla.
COPIA-OK
```

**Si falla.** `error del build`, sale con 2: un generado se apartó de su plantilla y la salida trae
el `cp` que lo arregla; copiala de nuevo en vez de editarla. `error del kit`, sale con 1: el
manifiesto quedó viejo por algo nuestro; pará y decilo, no corras `--escribir` sobre un kit clonado.
`cp: no such file`: estás fuera de la raíz, verificá con `pwd`.

---

### Paso 2 · Escribí el esqueleto, la proyección de la configuración y el modo

**Objetivo.** `agente/` es un paquete, `entrada_desde_config()` devuelve algo que valida contra
`contratos/entrada.schema.json`, y el modo por defecto es `borrador` sin depender de ningún archivo.

**Hacé esto.** `agente/ajustes.py` con pydantic-settings, y `agente/config.py` con **dos** funciones
y no una. **Invariante 4: ninguna credencial en el árbol** —`ajustes.py` nombra variables y lee los
valores en runtime; ninguno va a un archivo versionado ni pasa por una tool call. Lo prueba el
chequeo `secretos`.

#### Lo que `agente/ajustes.py` expone, entero

El módulo declara una clase `Ajustes(BaseSettings)` y **una sola instancia**, `ajustes = Ajustes()`.
Todo el resto del árbol la importa así, y ésta es la única forma que se escribe:

```python
from agente.ajustes import ajustes
```

**Y `agente/__init__.py` queda vacío.** El paquete y nada más: no reexporta la instancia, no importa
`ajustes.py` ni ningún otro módulo de `agente/`. Un `__init__.py` que importa medio paquete convierte
cualquier import en la carga del árbol entero, y el ciclo `ajustes` → `config` que la propiedad `modo`
esquiva con su import diferido vuelve por esa puerta. La forma que anduvo dando vueltas
—`from agente import ajustes`, y después `ajustes.whatsapp_phone_number_id`— sólo es cierta si el
`__init__.py` reexporta la instancia, y acá no reexporta nada: con el archivo vacío ese import te da
el **módulo**, y el atributo se cae recién cuando alguien lo lee. Ver `blueprint/00-contrato.md` § 4.

Esta tabla es la especificación completa. **Un atributo que otro archivo usa y que no está acá es un
`AttributeError` en runtime, en una máquina nueva y con la credencial bien puesta** —no falla al
arrancar, falla en la primera entrega real—. Si agregás una variable, entra en esta tabla y en
`env.example` el mismo día.

| Variable de entorno | Atributo | Tipo | Obligatoria | Qué pasa si falta |
|---|---|---|---|---|
| `ANTHROPIC_API_KEY` | `anthropic_api_key` | `str \| None` | siempre, también en `demo` | el paso 3 no redacta: 401 de Anthropic. El demo se ahorra WhatsApp, no el modelo |
| `MODELO` | `modelo` | `str`, default `claude-opus-5` | no: trae el default de `PINES.md` | usa el default. Si el valor no coincide con `PINES.md`, `auditar.py` lo rechaza y te dice los dos |
| `WHATSAPP_PROVIDER` | `proveedor` | `Literal["meta", "zernio", "demo"]`, default `demo` | no | queda en `demo`: reproduce las entregas grabadas de `pruebas/fixtures/` y no abre un socket |
| `WHATSAPP_TOKEN` | `whatsapp_token` | `str \| None` | con `meta` | 401 en cada envío. No sale ningún mensaje |
| `WHATSAPP_PHONE_NUMBER_ID` | `whatsapp_phone_number_id` | `str \| None` | con `meta` | la URL de envío no se puede armar: `RUTA_META.format(...)` queda con `None` adentro |
| `WHATSAPP_VERIFY_TOKEN` | `whatsapp_verify_token` | `str \| None` | con `meta` | el alta del webhook falla y Meta no dice por qué |
| `META_APP_SECRET` | `meta_app_secret` | `str \| None` | con `meta` | ninguna firma verifica: 401 en todas las entregas, con cara de secreto mal copiado. Ver `blueprint/00-contrato.md` § 7 |
| `ZERNIO_API_KEY` | `zernio_api_key` | `str \| None` | con `zernio` | 401 en cada envío |
| `ZERNIO_WEBHOOK_SECRET` | `zernio_webhook_secret` | `str \| None` | con `zernio` | ninguna entrega verifica; Zernio reintenta siete veces y después la pierde |
| `ZERNIO_ACCOUNT_ID` | `zernio_account_id` | `str \| None` | con `zernio` | los medios no se bajan y el paso 1 se detiene con el motivo. Ver `blueprint/32-multimodal.md` |
| `GOOGLE_CALENDAR_ID` | `google_calendar_id` | `str \| None` | no | el paso 4 queda detenido con el motivo; el horario se confirma y el evento lo carga una persona |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | `google_service_account_json` | `str \| None`, ruta absoluta | no | lo mismo que la anterior. Con ruta relativa, `FileNotFoundError`: el servicio arranca en otro directorio |
| `SUPABASE_URL` | `supabase_url` | `str \| None` | no | el paso 5 devuelve la fila en la salida con `crm.escrito` en falso. No pierde el dato; no lo guarda |
| `SUPABASE_SERVICE_KEY` | `supabase_service_key` | `str \| None` | no | lo mismo que la anterior |
| `OPENAI_API_KEY` | `openai_api_key` | `str \| None` | no | un audio frena el ciclo con el motivo escrito, no con una transcripción inventada |
| `SLACK_WEBHOOK_URL` | `slack_webhook_url` | `str \| None` | no | la escalación ocurre igual y el aviso queda en la salida, para que lo lea alguien |
| `DATABASE_URL` | `database_url` | `str \| None` | no | `normalizar_url(None)` devuelve `sqlite+aiosqlite:///./wca.db`, un archivo al lado del proyecto |
| `PANEL_TOKEN` | `panel_token` | `str \| None` | no, pero el panel la exige | el router del panel devuelve 503 en todo. `/salud` sigue en 200: está afuera de ese router |

**Dieciocho variables, y son las dieciocho de `env.example`.** Si los dos números no coinciden, uno
de los dos archivos quedó atrás.

Cuatro reglas sobre la clase, y las cuatro se pagan si se rompen:

1. **Ningún campo es requerido a nivel de pydantic.** Todos son opcionales, con `None` o con el
   default de la tabla. Un campo requerido levanta `ValidationError` al importar el módulo, el
   proceso no arranca, `/salud` no contesta nunca y Railway mata el despliegue en el chequeo de
   salud. La columna «obligatoria» se chequea al usar la variable, no al importarla.
2. **El atributo se llama igual que la variable en minúscula, con una sola excepción:**
   `WHATSAPP_PROVIDER` → `proveedor`, declarado con alias explícito. Ningún otro se renombra, así
   quien lee un archivo de `agente/` sube de un atributo a su variable sin abrir esta tabla.
3. **Ningún valor se imprime, se loguea ni se escribe en un archivo versionado.** Ni siquiera
   truncado. Lo prueba el chequeo `secretos`.
4. **`PORT` no es atributo de `ajustes`.** La lee uvicorn y el valor lo inyecta Railway en cada
   despliegue. Leerla acá invita a fijarla a mano, que es la falla del contenedor sano al que nadie
   alcanza.

**Un atributo que no sale del entorno: `ajustes.modo`.** No existe una variable `MODO` y no se
agrega: el modo sale de `config/cerrador.yaml`, y eso está decidido en `blueprint/00-contrato.md`
§ 9. `modo` es una propiedad de sólo lectura que devuelve `modo_efectivo()`, con el `import` adentro
del cuerpo de la propiedad —a nivel de módulo, `ajustes.py` importando `config.py` cierra el ciclo—.
Sin `config/cerrador.yaml` devuelve `borrador`, que es el default del kit entero. `agente/servidor.py`
lo publica en `/salud` y lo inserta en cada ciclo; la ruta la escribe `blueprint/35-panel-api.md`.

**La lista que `/salud` devuelve en `faltan` sale de esta tabla**, filtrada por el proveedor
configurado: con `meta` nombra `META_APP_SECRET`, con `zernio` no. Quien escribe esa ruta es
`blueprint/35-panel-api.md`, paso 2; lo que no puede es inventar un nombre que no esté acá.

#### Y `agente/config.py`, con dos funciones

- **`entrada_desde_config()`** proyecta `config/*.yaml` como lo dejó `blueprint/20-entrevista.md`,
  paso 13. Son **nueve claves y ninguna más**: `canal_interno`, `catalogo`, `disponibilidad`,
  `opciones_horario`, `palabras_escalacion`, `playbook`, `rango_precio`, `umbrales`, `version`. El
  contrato es `additionalProperties: false`: `negocio`, `agente` y `tratamiento` no son campos, y el
  tratamiento viaja adentro de `playbook.tono`.
- **`modo_efectivo()`** devuelve `borrador` o `automatico`: el más conservador entre `paso_3`,
  `paso_4` y `paso_5` de `config/cerrador.yaml`. Ese archivo lo escribe `blueprint/60-bandeja.md`, o
  sea que en toda la fase 3 no existe, y **sin él la función devuelve `borrador`**. El default no
  depende de que exista un archivo.

`mensaje`, `modo` y `confirmado` no son configuración: los inserta `agente/servidor.py` en cada
ciclo. Nueve más tres son las doce propiedades del contrato de entrada.

**Tenés que ver.** Tres comandos:

```bash
.venv/bin/python -c "from agente.config import entrada_desde_config as e; print(sorted(e()))"
.venv/bin/python -c "from agente.config import modo_efectivo as m; print(m())"
.venv/bin/python -c "from agente.ajustes import ajustes; print([a for a in ('anthropic_api_key','modelo','proveedor','modo','whatsapp_token','whatsapp_phone_number_id','whatsapp_verify_token','meta_app_secret','zernio_api_key','zernio_webhook_secret','zernio_account_id','google_calendar_id','google_service_account_json','supabase_url','supabase_service_key','openai_api_key','slack_webhook_url','database_url','panel_token') if not hasattr(ajustes, a)] or 'AJUSTES-OK')"
```

El primero imprime las nueve claves en orden alfabético y ninguna más. El segundo, `borrador`, con
`config/cerrador.yaml` todavía sin escribir. El tercero, `AJUSTES-OK`, con el `.env` vacío: mira que
los diecinueve atributos existan, no que tengan valor. Corrélo ahora y no en la fase 4, que es
cuando se descubre solo y con un cliente escribiendo del otro lado.

**Si falla.** `ModuleNotFoundError: agente`: falta `__init__.py`, o estás parado en otra carpeta.
Una clave de más: se coló sin proyectar y el chequeo `contrato` rebota la entrada entera.
`ModuleNotFoundError: yaml`: corriste con el Python del sistema y no con `.venv`.
`FileNotFoundError: config/cerrador.yaml`: `modo_efectivo()` tiene que tratar la ausencia como el
caso normal, no como un error.

El tercero imprime una lista en vez de `AJUSTES-OK`: cada nombre de esa lista es un atributo que
falta en la clase y que otro archivo va a usar. `['meta_app_secret']` es el caso típico y el que más
tarda en aparecer, porque sólo se toca con `WHATSAPP_PROVIDER=meta` y en una entrega real.
`ValidationError` al importar: dejaste un campo requerido; van todos opcionales, regla 1.
`ImportError` circular entre `ajustes` y `config`: el `import` de `modo_efectivo()` quedó a nivel de
módulo y va adentro de la propiedad.

Y el que no aparece acá sino dos fases más adelante, en la primera entrega real:

```
AttributeError: module 'agente.ajustes' has no attribute 'whatsapp_phone_number_id'
```

Ese módulo que se nombra en el mensaje es la pista: alguien escribió `from agente import ajustes` y
le quedó el módulo en la mano. Es un import, no un atributo que falte. Corregilo a
`from agente.ajustes import ajustes` en el archivo que falló, y no lo arregles agregándole un
reexport a `agente/__init__.py`, que es el que sí queda vacío.

---

### Paso 3 · Escribí `agente/http.py` y `agente/base.py`

**Objetivo.** Hay un solo cliente HTTP, y hay estado: contactos por `contacto_id`, mensajes con su
id de evento, y la hora del último entrante para la ventana de 24 horas.

**Hacé esto.** Una única construcción de `httpx.AsyncClient(timeout=...)` que todo lo demás importa.
**Invariante 3: un solo cliente HTTP, con `timeout=` explícito** —sin timeout httpx espera para
siempre, y el webhook de Zernio —el aviso automático que el proveedor le manda a tu servidor cuando
entra un mensaje; ver `blueprint/00-contrato.md` § 10— pide 2xx en menos de 5 segundos y reintenta
hasta siete veces. Lo prueba `http-unico`.

La base es SQLAlchemy async sobre `DATABASE_URL`. `asyncpg` no aparece en ningún `import`: vive
adentro de la cadena de conexión, y el chequeo `deps-drivers` busca `+(\w+)://` y exige que el
driver esté fijado en `PINES.md`. Con SQLite esa línea nunca corre y la falta aparece recién en el
primer despliegue con Postgres.

**Las dos funciones de URL, y son dos.** El jobstore de APScheduler 3 es síncrono y no entiende la
forma async; ver `blueprint/00-contrato.md` § 8.

```python
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ESQUEMAS = {"postgres": "postgresql+asyncpg", "postgresql": "postgresql+asyncpg",
            "sqlite": "sqlite+aiosqlite"}
NO_LAS_ENTIENDE = {"sslmode", "channel_binding", "target_session_attrs", "gssencmode"}


def normalizar_url(cruda: str | None) -> str:
    """La URL de la aplicación, siempre async. Descarta lo que asyncpg no entiende."""
    if not cruda:
        return "sqlite+aiosqlite:///./wca.db"
    p = urlsplit(cruda)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if k.lower() not in NO_LAS_ENTIENDE]
    return _armar(ESQUEMAS.get(p.scheme, p.scheme), p.netloc, p.path,
                  urlencode(query), p.fragment)


def _armar(esquema: str, netloc: str, path: str, query: str, fragmento: str) -> str:
    """Arma la URL a mano en vez de con `urlunsplit`.

    `urlunsplit` no vuelve a poner el `//` cuando `netloc` es cadena vacía y el path no
    arranca con `//`. Con SQLite —que no tiene host— `sqlite:///./wca.db` sale
    `sqlite:/./wca.db`, y SQLAlchemy 2.0 lo rechaza con `ArgumentError: Could not parse
    SQLAlchemy URL`. Postgres no lo sufre porque siempre trae host.
    """
    url = f"{esquema}://{netloc}{path}"
    if query:
        url += f"?{query}"
    if fragmento:
        url += f"#{fragmento}"
    return url


class RecordatorioSinDriver(RuntimeError):
    """No hay driver síncrono fijado en PINES.md. Ver blueprint/00-contrato.md § 8."""


def url_sincrona(cruda: str | None) -> str:
    """La URL del jobstore, que es síncrono. Conserva `sslmode` y compañía: libpq sí las entiende."""
    if not cruda:
        return "sqlite:///./wca.db"
    p = urlsplit(cruda)
    if p.scheme.split("+")[0] == "sqlite":
        return _armar("sqlite", p.netloc, p.path, p.query, p.fragment)
    # Este texto termina en `pasos[3].motivo`, que es campo declarado de
    # `contratos/salida.schema.json` y viaja en la salida del ciclo. O sea: lo lee gente que no
    # tiene por qué saber qué es un jobstore ni dónde vive PINES.md. Se escribe para esa
    # persona, y el detalle técnico queda en `PENDIENTES.md`.
    raise RecordatorioSinDriver(
        "la cita quedó agendada y la confirmación salió; el recordatorio de 24 horas antes no "
        "se pudo programar sobre esta base de datos. Con SQLite anda. Si estás en Postgres, "
        "avisale vos al contacto el día anterior hasta que esto se destrabe")
```

`postgres://` es lo que entregan Railway y Supabase, y SQLAlchemy no lo carga desde la 1.4.
`sslmode` es palabra clave de libpq y asyncpg la recibe como argumento de `connect()`: si el
servidor exige TLS, va aparte en `connect_args={"ssl": "require"}`. Con SQLite ninguna de las dos
líneas corre.

**Las tablas, y las columnas que otro archivo va a leer.** Indexá por `contacto_id` y nunca por
número: es la aserción 1, y el teléfono puede faltar.

```
contactos       contacto_id (PK) · numero (puede ser nulo) · nuevo · mensajes_previos
conversaciones  conversacion_id (PK) · contacto_id · last_inbound_at · window_expires_at
                ultimo_entrante · ultimo_saliente_hash · salientes_seguidos · baja_en
eventos         evento_id (PK) · recibido_en          el dedupe de entrada, una fila por evento
```

Las cuatro últimas columnas de `conversaciones` existen para las guardas de `enviar()`, que las lee
y no las calcula. Quién escribe cada una y para qué está en `blueprint/31-proveedores.md`, paso 1.
`registrar_evento(evento_id)` devuelve `True` la primera vez y `False` después: es el dedupe
—descartar la entrega repetida; ver `blueprint/00-contrato.md` § 10—, y se resuelve con un solo
`INSERT ... ON CONFLICT DO NOTHING`.

**`migrar(engine=None)` lleva el engine por parámetro.** Sin argumento corre sobre el de la
aplicación, que es como lo llaman ésta y las fases que siguen. Con argumento corre sobre el que le
pasan, y eso es lo que le hace falta a la suite: un engine por prueba, en memoria, que es el punto de
reinicio entre ciclos. Ver `blueprint/40-pruebas.md`, paso 2.

**Tenés que ver.** Tres comandos:

```bash
grep -rn "AsyncClient(\|httpx.Client(" agente panel | grep -v agente/http.py
.venv/bin/python -c "import asyncio, agente.base as b; asyncio.run(b.migrar()); print('BASE-OK')"
.venv/bin/python -c "from agente.base import normalizar_url as n; print(n('postgres://u:p@h:5432/db?sslmode=require'))"
```

El primero sin salida. El segundo, `BASE-OK`. El tercero, `postgresql+asyncpg://u:p@h:5432/db`.

**Si falla.** `http/cliente_suelto`: hay otra construcción fuera de `agente/http.py`, borrala e
importá. `http/sin_timeout`: una constante del módulo no alcanza, va como `timeout=` en la llamada.
`ModuleNotFoundError: aiosqlite`: la URL quedó `sqlite://` sin el `+aiosqlite`. Falta `greenlet`:
SQLAlchemy lo declara bajo un marcador de plataforma, reinstalá con el `requirements.txt` copiado.
`drivers/interpolado`: armaste la cadena desde afuera (`postgresql+{drv}://`) y ahí el chequeo sólo
puede avisar; escribí el driver. `connect() got an unexpected keyword argument 'sslmode'`:
reescribiste el esquema y dejaste el parámetro, que es la mitad que se olvida siempre.

---

### Paso 4 · Escribí `agente/salida.py`, el emisor del contrato

**Objetivo.** No hay camino de código que emita cinco pasos ni siete.

**Hacé esto.** Presembrá los seis registros antes de que corra el primer paso, y que cada paso mute
el suyo por índice:

```python
pasos = [{"n": i, "estado": "salteado", "motivo": None} for i in range(1, 7)]
...
pasos[n - 1]["estado"] = "hecho"
```

Sin `append`, sin filtros, sin un `if` que agregue un registro: seis entran y seis salen, y el
contrato se cumple por construcción y no por disciplina.

**El modelo escribe prosa; el código decide hechos.** Del modelo salen `texto`, `motivo` y
`resumen`; del código, `pasos`, `estado`, `enviado`, `escrito`, `cita`, `handoff`,
`horarios_ofrecidos` y `temperatura`. Por eso el esquema angosto de `agente/wire_schema.py` ni
siquiera tiene esos campos: lo que no se pregunta no se puede mentir. El modelo propone y el código
verifica en tres:

- **`presupuesto`.** `anclar_presupuesto()` exige una subcadena literal del mensaje y con cifras
  adentro. Si no la hay, el presupuesto se fuerza a nulo y el descarte va en `motivo`.
- **La objeción.** Búsqueda exacta contra `playbook.objeciones`. Si no está,
  `respuesta.objecion_en_playbook` queda en falso y se nombra sin responderla. El campo del contrato
  es `respuesta.objecion_detectada`, no `objecion`.
- **El resumen.** Tres líneas como máximo. La conversación entera pegada ahí falla la aserción 5.

**Tenés que ver.** Escribí la salida del caso en `pruebas/salida-caso-01.json` y corré la compuerta
—`scripts/auditar.py`, veintitrés chequeos y nada se publica sin `pass`; ver
`blueprint/00-contrato.md` § 10—:

```bash
.venv/bin/python scripts/auditar.py
```

El chequeo `contrato` dice `1 salida(s) válidas, con los seis pasos en orden`. El intérprete es el
del `.venv` y no `python3`: el Python del sistema no trae `jsonschema`, y sin él ese chequeo saltea
en vez de correr. Ver `blueprint/00-contrato.md` § 5.

**Si falla.** `contrato/pasos_desordenados`: alguien filtró o reordenó; seis pasos con `n: 1`
validan contra el esquema y no significan nada, por eso lo mira el auditor. `no valida:
additionalProperties`: agregaste una clave que el contrato no tiene. `contrato` o `contrato-control`
en `salteado`: estás corriendo con el Python del sistema. Un salteado no es un aprobado.

---

### Paso 5 · Escribí `agente/prompt.py` y `agente/modelo.py`

**Objetivo.** El prefijo del prompt es idéntico byte por byte en cada petición, y la llamada usa el
modelo de `PINES.md`.

**Hacé esto.** Una `prompt_de_sistema()` que hornea negocio, nombre del agente, tratamiento,
catálogo y playbook, y la llamada con `esquema_wire()`. **Invariante 6: el modelo sale de `PINES.md`
y de ningún otro lado** —hoy `claude-opus-5`, leído de `MODELO`. Van `thinking={"type": "adaptive"}`
y `output_config={"effort": "medium"}`, explícitos; no van `temperature`, `top_p`, `top_k` ni
`budget_tokens`, que devuelven 400.

Nada variable en el prefijo estático —la parte del prompt de sistema que no cambia nunca; ver
`blueprint/00-contrato.md` § 10—: ni `datetime.now()`, ni `uuid`, ni `random`, ni un valor
interpolado desde la petición. Un prefijo que cambia pone la tasa de acierto del caché en cero, para
siempre y sin un error visible: sube la factura y no hay nada roto que mirar. El chequeo
`cache-estatico` mira funciones cuyo nombre diga `prompt`, `sistema` o `system`; con otro nombre
saltea y lo avisa, que no es lo mismo que pasar.

**`agente/modelo.py` expone una fábrica, y se llama `modelo_de_produccion()`.** Sin argumentos,
devuelve el objeto que `correr_ciclo(entrada, *, modelo, deps)` recibe en `modelo`. A ese objeto se
lo llama `modelo(sistema=…, mensajes=…)` y devuelve **el dict de los once campos del esquema
angosto**, o una corrutina que devuelva eso. Nada más: la respuesta del SDK entera no sale de este
archivo. Si sale, cada paso se arregla solo con la forma de la API y subir el pin del SDK pasa a
tocar seis archivos en vez de uno.

El nombre no es una preferencia. `pruebas/simulador.py` lo busca así:

```python
fabrica = getattr(modelo, "modelo_de_produccion", None)
```

y con otro nombre la falla es muda: `getattr(..., None)` no levanta nada, el simulador se cae al
stub y la cabecera dice «modelo stub, sin ANTHROPIC_API_KEY» **con la clave cargada**. Quien lo mire
va a ir a buscar la variable de entorno, que está bien. Por eso el símbolo está además en el piso de
la compuerta —`PISO_DE_MODULOS["agente/modelo.py"]` en `scripts/auditar.py`—, donde era el único que
no prometía ninguna prosa. La prosa es este párrafo.

**Mirá `stop_reason` antes de tocar `content`.** Con este modelo los clasificadores de seguridad
pueden declinar un pedido: eso vuelve como **200**, con `stop_reason` en `refusal` y `content`
vacío. Un `content[0]` a ciegas no lee 401 ni 429: revienta con `IndexError` adentro del ciclo, en
el primer mensaje que toque un tema que el clasificador mira. Un `raise` con el motivo escrito
alcanza; lo que no alcanza es no mirarlo. **Ninguna prueba del kit cubre esta rama todavía**, y se
dice acá para que no se lea como cubierta: `PINES.md` no nombra el `refusal` y `pruebas/test_modelo.py`
tampoco lo mira.

**Tenés que ver.** Dos cosas. El prefijo, idéntico entre llamadas:

```bash
.venv/bin/python -c "from agente.prompt import prompt_de_sistema as p; print(p() == p())"
```

```
True
```

Y las once de `pruebas/test_modelo.py`, que es lo único del kit que mira **adentro** de la llamada
—qué modelo viaja en el cuerpo, qué `thinking`, qué `effort`, qué esquema, y de qué bloque de la
respuesta sale la salida—, contra bytes de una respuesta grabada, sin credencial y sin red:

```bash
.venv/bin/python -m pytest pruebas/test_modelo.py -q
```

```
11 passed
```

Ese archivo es el que cubre la orilla que el resto de la suite no puede tocar: `StubModel` se
inyecta justamente para no ejecutar esta función, así que hasta esta ronda, vaciándola a un `raise`,
el árbol seguía en `199 passed` y la compuerta en `PASS · 0 errores · 0 avisos · 0 salteados`. Hoy
esa misma poda deja los once nodos en error.

**Si falla.** `cache/prefijo_variable` nombra archivo y línea: sacá esa lectura del prefijo y pasala
por el turno de usuario. `modelo/parametro_400`: sacá el parámetro, no lo comentes al lado.
`modelo/retirado`: quedó un id viejo escrito a mano en algún literal. Y las de la suite:

- **`no define modelo_de_produccion()`.** Está escrito con otro nombre. Ver más arriba: el simulador
  lo busca así y se cae al stub en silencio.
- **`no supe llamar al modelo`.** El objeto no acepta `modelo(sistema=…, mensajes=…)`. Es la misma
  convención con la que `agente/ciclo.py` llama al `StubModel` de las pruebas.
- **`el pedido va con model=…`.** El literal quedó en otro archivo, o `MODELO` se lee y se pisa más
  abajo. El chequeo 10 hace grep de literales; esto mira el cuerpo que sale.
- **`output_config.effort`.** Omitirlo no da error: corre en el nivel por default de la API, que hoy
  es otro y cuesta otra cosa. El nivel sale de `PINES.md` y de ningún otro lado.
- **`lo que devolvió el modelo no es lo que trae la respuesta grabada`.** La extracción está leyendo
  `content[0]`, que con `thinking` prendido es el bloque de pensamiento y viene vacío.

---

## Lo que no se escribe acá

Cada línea de esta tabla tiene un dueño y un archivo. Adelantar cualquiera de ellas es escribir
contra funciones que todavía no existen, y sobre todo es escribir dos veces la misma pieza con dos
especificaciones distintas: eso fue lo que dejó este blueprint sin poder seguirse.

| Lo que falta de `agente/` | Quién lo escribe |
|---|---|
| `enviar.py`, con las cuatro URL de envío y las tres guardas | `blueprint/31-proveedores.md` paso 1 |
| `proveedores/`: la base abstracta, `demo`, `meta` y `zernio` | `blueprint/31-proveedores.md` pasos 2 a 5 |
| `medios.py`, la bajada de audio e imagen | `blueprint/32-multimodal.md` paso 1 |
| los cuerpos de los pasos 1, 2, 3 y 6, y `avisar_interno()` adentro de `enviar.py` | `blueprint/32-multimodal.md` |
| `integraciones/calendario.py` y `pasos/paso_4_agenda.py` | `blueprint/33-agenda.md` |
| `integraciones/crm.py` y `pasos/paso_5_crm.py` | `blueprint/34-crm.md` |
| `servidor.py`, sus diez rutas y `panel/panel.py` | `blueprint/35-panel-api.md` |
| `ciclo.py` y `pruebas/*.py` | `blueprint/40-pruebas.md` |

---

## Qué quedó hecho

Los seis archivos verbatim en su destino. El paquete, los ajustes con sus dieciocho variables y el
`modo` derivado, la configuración con sus nueve claves, el único cliente HTTP, la base con las dos
funciones de URL, el emisor que presiembra los seis pasos, y el prompt que no cambia entre
peticiones.

La compuerta todavía no da `pass`, y no tiene por qué: la fase 3 sigue en los dos archivos que
vienen. Lo que sí tiene que decir es esto:

```bash
.venv/bin/python scripts/auditar.py | grep "enviar-unico\|enviar/sin_modulo"
```

```
  [FALLA   ] 13 enviar-unico
      [ERROR] enviar/sin_modulo   agente/enviar.py:0   no existe agente/enviar.py y la construcción…
```

Es el hallazgo que te tiene que quedar abierto acá, y lo cierra el paso 1 del archivo que sigue. Si
en cambio leés `enviar/segundo_camino` —el host pelado— o `enviar/salida_de_mensajeria` —la URL de
envío entera—, alguien escribió un destino de mensajería en un módulo de este archivo: sacalo ahora,
porque después no se ve. Los dos ids están en `blueprint/00-contrato.md` § 12.

Anotalo en `.wca-estado.json`: `fase` en `generacion` y el sha256 de cada archivo escrito.

**Próximo archivo:** `blueprint/31-proveedores.md`, que reserva el único camino de salida y escribe
los tres transportes.
