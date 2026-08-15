# 00 · El contrato del blueprint

Los dieciséis archivos de `blueprint/` se escribieron en paralelo y quedaron diciendo cosas
distintas sobre lo mismo. Éste es el desempate: **cuando dos archivos discrepan, gana lo que
diga acá.** Si el caso no está acá, gana lo que ya funciona en disco, y se anota en
`PENDIENTES.md`.

Es una referencia, no una fase. No se lee entero para construir: se abre cuando hay una duda de
nombre, de orden, de ruta o de dueño. Los pasos con los cuatro tiempos —Objetivo, Hacé esto,
Tenés que ver, Si falla— viven en los otros quince; acá hay uno solo, al final, que verifica que
este contrato se esté cumpliendo.

---

## 1 · Los nombres de archivo reales

Corré `ls blueprint/`. **Manda el disco.** Estos seis nombres no existen y ningún archivo los
puede citar: el chequeo 01 `blueprint-existe` los marca uno por uno.

| Nombre inventado | Nombre real |
|---|---|
| `10-preparacion.md` | `10-entorno.md` |
| `30-esqueleto.md` | `30-generacion.md` |
| `32-firmas.md` | `32-multimodal.md` |
| `33-enviar.md` | `33-agenda.md` |
| `34-pasos.md` | `34-crm.md` |
| `35-agenda-crm.md` | `35-panel-api.md` |

Los dieciséis que sí existen:

```
00-mapa.md  00-contrato.md  05-arranque.md  10-entorno.md  20-entrevista.md
25-playbook.md  30-generacion.md  31-proveedores.md  32-multimodal.md
33-agenda.md  34-crm.md  35-panel-api.md
40-pruebas.md  90-auditoria.md  50-despliegue.md  60-bandeja.md
```

---

## 2 · La cadena de fases

**El número del archivo no es el orden.** El orden es esta cadena, y cada archivo la declara al
cerrar con una línea `**Próximo archivo:**`. Sin esa línea quien construye se saltea el archivo
siguiente entero, que es lo que pasa hoy entre `30` y `31`.

| # | Archivo | Fase | Cierra con `**Próximo archivo:**` |
|---|---|---|---|
| 1 | `00-mapa.md` | primero | `blueprint/00-contrato.md` |
| 2 | `00-contrato.md` | primero | `blueprint/05-arranque.md` |
| 3 | `05-arranque.md` | 0 | `blueprint/10-entorno.md` |
| 4 | `10-entorno.md` | 1 | `blueprint/20-entrevista.md` |
| 5 | `20-entrevista.md` | 2 | `blueprint/25-playbook.md` |
| 6 | `25-playbook.md` | 2 | `blueprint/30-generacion.md` |
| 7 | `30-generacion.md` | 3 | `blueprint/31-proveedores.md` |
| 8 | `31-proveedores.md` | 3 | `blueprint/32-multimodal.md` |
| 9 | `32-multimodal.md` | 3 | `blueprint/33-agenda.md` |
| 10 | `33-agenda.md` | 4 | `blueprint/34-crm.md` |
| 11 | `34-crm.md` | 4 | `blueprint/35-panel-api.md` |
| 12 | `35-panel-api.md` | 4 | `blueprint/40-pruebas.md` |
| 13 | `40-pruebas.md` | 5 | `blueprint/90-auditoria.md` |
| 14 | `90-auditoria.md` | compuerta | `blueprint/50-despliegue.md` |
| 15 | `50-despliegue.md` | 6 | `blueprint/60-bandeja.md` |
| 16 | `60-bandeja.md` | después | no hay: se abre cada día |

La columna «Fase» de esta tabla es el orden, no lo que se escribe en `.wca-estado.json`. Ningún
archivo anota `0`, `1` ni `compuerta`: anotan una palabra —`arranque`, `entorno`, `crm`—, y la
traducción de esa palabra al archivo vive en la tabla de `blueprint/00-mapa.md`, columna «`fase`
en el estado». Retomar cruzando contra esta columna no encuentra nada.

Dos cosas que se leen al revés de la numeración y son correctas:

- **`90-auditoria.md` corre antes de `50-despliegue.md`.** `50` arranca con «entrás con `/revisar`
  en `pass`», y `90` cierra con «con `pass`, y sólo con `pass`, seguís a `/publicar`». El 90 lleva
  ese número porque también es el archivo que `/revisar` abre cualquier día, no porque vaya último.
- **`25-playbook.md` se entra dos veces**: desde `20-entrevista.md` en la primera corrida, y desde
  `/playbook` cualquier otro día. En el segundo caso no hay próximo archivo: se vuelve a quien
  llamó, y eso va escrito al lado de la línea.

Lo que hoy dice `30-generacion.md` —«lo que sigue son las pruebas del caso y el despliegue»— es el
defecto que este apartado corrige: se saltea `31`, `32`, `33`, `34` y `35`, o sea los proveedores,
los medios, la agenda, el CRM y el panel enteros.

---

## 3 · Un solo servidor: `agente/servidor.py`

**El módulo se llama `agente/servidor.py`.** No es preferencia: el `CMD` del `Dockerfile` dice
`uvicorn agente.servidor:app`, ese archivo se copia verbatim de `plantillas/infra/` y no se edita
nunca. `agente/app.py` no existe en ningún árbol, en ninguna fase.

Las rutas son éstas y no hay otras. `docs_url`, `redoc_url` y `openapi_url` van en `None`.

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

**Diez rutas, once métodos**: `/webhook/{proveedor}` comparte camino entre el GET y el POST. La
verificación es ésta, y con los pines vigentes no puede ser `sorted({r.path for r in app.routes})`:

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

La lista sale en un solo renglón; acá va cortada para que entre.

**Por qué no `app.routes` a secas.** Con fastapi 0.141.1 y starlette 1.3.1, `include_router` ya no
copia las rutas del router adentro de `app.routes`: mete **un** objeto `_IncludedRouter` que las
envuelve, y ese objeto no tiene `.path`. Sobre el panel que este mismo § 3 exige
—`APIRouter(dependencies=[Depends(exigir_token)])` más `include_router`, nunca ruta por ruta— la
forma vieja termina así:

```
AttributeError: '_IncludedRouter' object has no attribute 'path'
```

Y lo que `app.routes` llega a mostrar es sólo lo que se dio de alta sobre la app:

```bash
.venv/bin/python -c "
from agente.servidor import app
print([(type(r).__name__, getattr(r, 'path', '—')) for r in app.routes])"
```

```
[('_IncludedRouter', '—'), ('APIRoute', '/salud'), ('APIRoute', '/webhook/{proveedor}'),
 ('APIRoute', '/webhook/{proveedor}')]
```

Las del panel están montadas y contestan —`/panel`, `/api/leads`, `/api/pendientes` y
`/api/conversaciones` devuelven su código, no 404—: lo roto era la verificación, no el servidor. Por
eso el comando suma las dos mitades, la app y el router, en vez de pedirle a `app.routes` que las
traiga juntas.

Los tres bloques de arriba salieron de correr esto con los pines de `PINES.md` sobre una app
armada con esta forma —`FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` con `/salud` y
las dos del webhook, más el router del panel por `include_router`—, no sobre un build entero.

`app.openapi()` también da 10 y 11, con `openapi_url=None` puesto igual, y es una línea más corta.
No es el que se prescribe: cuenta lo que está en el esquema, así que una ruta con
`include_in_schema=False` desaparece de esa cuenta y sigue montada. Lo que hay que contar es lo
montado.

Tres reglas que no se negocian:

1. **`/salud` queda afuera del router del panel.** Railway no manda cabeceras: adentro, el
   despliegue se muere en el chequeo de salud.
2. **El proveedor va en la ruta.** `/webhook/meta` y `/webhook/zernio` se dan de alta las dos, y
   cambiar `WHATSAPP_PROVIDER` no obliga a darlas de alta otra vez. El POST dirigido a un
   proveedor que no es el configurado devuelve 404, no 401.
3. **`exigir_token` lee tres lugares, en este orden**: la cabecera `Authorization: Bearer`, la
   cookie `wca_panel`, y el parámetro `?token=` de la query. El tercero existe porque el navegador
   entra la primera vez por `/panel?token=…`; sin él ese primer ingreso da 401 y la cookie no se
   llega a poner nunca. En esa rama el servidor deja la cookie —`HttpOnly`, `SameSite=Strict`,
   `Secure` sobre https— y redirige a `/panel` pelado. La comparación es `hmac.compare_digest`
   sobre el router entero, con `Depends`, nunca ruta por ruta.

El alta del webhook de `50-despliegue.md` apunta a `https://<dominio>/webhook/meta`, y con esta
tabla existe. Hoy, contra el árbol de `30`, es un 404.

---

## 4 · El mapa de módulos: un archivo, un dueño

Cada archivo del árbol lo escribe **un solo** blueprint. El resto lo puede nombrar y remitir; no
lo vuelve a especificar.

| Archivo | Qué contiene | Lo escribe |
|---|---|---|
| `requirements.txt` | verbatim, `cp` desde `plantillas/infra/` | `10-entorno.md` paso 5 |
| `Dockerfile` · `railway.json` | verbatim, `cp` | `30-generacion.md` paso 1 |
| `agente/wire_schema.py` · `.golden.json` | verbatim, `cp` | `30-generacion.md` paso 1 |
| `agente/firmas.py` | verbatim, `cp`. No se reescribe nunca | `30-generacion.md` paso 1 |
| `agente/__init__.py` · `ajustes.py` | el paquete —vacío— y los nombres de variables | `30-generacion.md` paso 2 |
| `agente/config.py` | `entrada_desde_config()` y `modo_efectivo()` | `30-generacion.md` |
| `agente/http.py` | el ÚNICO cliente httpx, con `timeout=` | `30-generacion.md` |
| `agente/base.py` | contactos, dedupe, ventana de 24 h, `normalizar_url()`, `url_sincrona()` | `30-generacion.md` |
| `agente/salida.py` | presiembra los seis pasos y verifica lo que el modelo propone | `30-generacion.md` |
| `agente/prompt.py` · `modelo.py` | el prefijo estático y la llamada a Anthropic | `30-generacion.md` |
| `agente/enviar.py` | el ÚNICO camino de salida, y las cuatro URL de envío | `31-proveedores.md` paso 1 |
| `agente/enviar.py` → `avisar_interno()` | el aviso interno del paso 6, al final del mismo archivo | `32-multimodal.md` paso 5 |
| `agente/proveedores/base.py` · `__init__.py` | la base abstracta, `Mensaje` y `elegir()` | `31-proveedores.md` paso 2 |
| `agente/proveedores/demo.py` | reproduce `pruebas/fixtures/` | `31-proveedores.md` paso 3 |
| `agente/proveedores/meta.py` | firma, parseo y alta de la Cloud API | `31-proveedores.md` paso 4 |
| `agente/proveedores/zernio.py` | firma, dedupe y el presupuesto de 5 s | `31-proveedores.md` paso 5 |
| `agente/medios.py` | la bajada de audio e imagen | `32-multimodal.md` paso 1 |
| `agente/pasos/paso_1_contexto.py` … `paso_3_responder.py`, `paso_6_handoff.py` | cuatro de los seis cuerpos | `32-multimodal.md`, paso de cierre |
| `agente/integraciones/calendario.py` · `agente/pasos/paso_4_agenda.py` | evento, `freeBusy` y recordatorio | `33-agenda.md` |
| `agente/integraciones/crm.py` · `agente/pasos/paso_5_crm.py` | la tabla `leads` y el upsert | `34-crm.md` |
| `agente/servidor.py` · `panel/panel.py` | la app y el router del panel | `35-panel-api.md` |
| `agente/ciclo.py` | `correr_ciclo(entrada, *, modelo, deps)` | `40-pruebas.md` paso 2 |
| `pruebas/*.py` · `pruebas/caso-02.md` | los dobles viven en `proveedor_falso.py`, no en `dobles.py` | `40-pruebas.md` |
| `config/marca.yaml` · `negocio.yaml` · `agenda.yaml` | ocho de las doce respuestas: Q1 a Q3 y Q5 a Q9 | `20-entrevista.md` |
| `config/playbook-base.yaml` | copia verbatim de `plantillas/config/`. **No se edita nunca** | `25-playbook.md` paso 1 |
| `config/playbook.yaml` | objeciones y tono | `25-playbook.md` paso 7 |
| `config/cerrador.yaml` | los tres modos y los cinco pisos de `/soltar` | `60-bandeja.md` paso 1 |

Lo que cambia contra lo que hay hoy:

- **`30-generacion.md` deja de escribir seis cosas.** Sus pasos 4 y 5 (proveedores y `enviar.py`),
  su paso 8 (los seis pasos y las integraciones) y su paso 9 (el panel y `app.py`) pasan a remitir.
  Queda con cinco pasos: copiadas, `ajustes`+`config`, `http`+`base`, `salida`, `prompt`+`modelo`.
- **El bloque de código de `normalizar_url()` vive en `30-generacion.md`**, junto a `base.py`.
  `34-crm.md` paso 2 se queda con la verificación y remite. Es lo que hace que `base.py` esté
  entero antes de que alguien lo importe.
- **`agente/integraciones/aviso.py` no existe: el aviso interno es `avisar_interno()` y vive al
  final de `agente/enviar.py`.** No es por el chequeo 13 —con el invariante 2 enunciado por destino,
  un `.post` a `SLACK_WEBHOOK_URL` no es un mensaje a un contacto y no se marca desde ningún
  archivo; ver § 12—. Es por esta tabla: un archivo, un dueño, y el dueño de lo que sale del proceso
  hacia una persona es `agente/enviar.py`, con dos funciones adentro —una hacia el contacto, otra
  hacia tu equipo—.
- **`agente/http.py` deja de ser un archivo eximido de nada.** Era la excepción que el chequeo 13
  necesitaba mientras decidía por verbo, y adentro de esa excepción vivió un segundo camino de
  salida entero, con la compuerta en verde. Sigue siendo el único cliente httpx —invariante 3— y eso
  no cambia; lo que cambia es que un mensaje escrito ahí adentro se marca igual que en cualquier
  otro archivo (§ 12).
- **Los cuerpos de los pasos 1, 2, 3 y 6 se escriben en `32-multimodal.md`**, después de
  `enviar.py` y de `medios.py`. Escritos en `30` importan una `enviar()` que todavía no existe, y
  su «Tenés que ver» —una corrida de `pytest pruebas -q` con un total escrito a mano— no puede dar
  verde: esas pruebas las escribe `40`. El total va sin el entero a propósito; la regla y la tabla
  de quién arregla qué están en `40-pruebas.md`, paso 8.
- **`config/playbook-base.yaml` es la única fila que nadie escribe: se copia.** `25-playbook.md`
  paso 1 la deja con un `cp`, en los tres caminos y no sólo en el A. **No se edita nunca**, ni
  para arreglar una tilde: el paso 1 de `30-generacion.md` corre
  `scripts/hash_plantillas.py --verificar --proyecto .`, que la compara byte por byte contra
  `plantillas/config/playbook-base.yaml`, y una línea cambiada sale como `error del build` con
  código 2. Lo que se edita es `config/playbook.yaml`, que lo escribe el paso 7. Es también el
  único archivo de `config/` que `.gitignore` deja afuera —`/config/playbook-base.yaml`, anclado—,
  porque el original ya está versionado en `plantillas/` y dos copias exactas en el mismo repo
  convierten cualquier diff del kit en un cambio que parece tuyo.
- **La instancia de `ajustes` se importa de una sola forma, y es
  `from agente.ajustes import ajustes`.** La escribe `30-generacion.md` paso 2 y la usa todo el
  resto del árbol: `agente/enviar.py` en `31-proveedores.md` paso 1, y `agente/servidor.py` en
  `35-panel-api.md` paso 1, que además trae la clase con la misma línea. `agente/__init__.py` queda
  **vacío** —el paquete y nada más—: no reexporta la instancia, no importa `ajustes.py` ni ningún
  otro módulo del paquete. La otra forma que anduvo dando vueltas, `from agente import ajustes`,
  con ese `__init__.py` te da el **módulo** y no la instancia, y el atributo se cae recién cuando
  alguien lo lee. Medido en esta máquina, con `agente/__init__.py` vacío:

  ```
  AttributeError: module 'agente.ajustes' has no attribute 'whatsapp_phone_number_id'
  ```

  Reexportar en `__init__.py` también funciona y no es lo que se escribe: deja `agente.ajustes`
  nombrando dos cosas —el módulo y la instancia— según por dónde entres, y el que hereda el árbol
  tiene que saber cuál de las dos le tocó.
- **Las doce respuestas de la entrevista aterrizan en tres lugares, no en uno.** Q1 a Q3 y Q5 a Q9
  van a `config/marca.yaml`, `negocio.yaml` y `agenda.yaml`, que escribe `20-entrevista.md` paso 13.
  Q4 va a `config/playbook.yaml`, que escribe `25-playbook.md` paso 7 y es su dueño único. Q10 a Q12
  van a `.env` y a ningún archivo versionado. Por eso `20-entrevista.md` dice «doce preguntas
  numeradas, once se hacen acá»: las dos cuentas son ciertas y hablan de cosas distintas.
- **Todo módulo del árbol abre con `from __future__ import annotations`.** Está en los dos archivos
  que se copian verbatim —`plantillas/contratos/wire_schema.py` y `plantillas/seguridad/firmas.py`—
  y en el cuerpo de `agente/enviar.py` que escribe `31-proveedores.md` paso 1; el resto lo sigue.
  **La consecuencia:** en runtime las anotaciones son cadenas, así que `inspect.signature()` las
  imprime entre comillas y una verificación que compare la firma impresa necesita `eval_str=True`.
  Medido en esta máquina, con Python 3.14.6, sobre `async def correr_ciclo(entrada: dict, *, modelo,
  deps) -> dict`:

  ```
  (entrada: 'dict', *, modelo, deps) -> 'dict'      inspect.signature(f)
  (entrada: dict, *, modelo, deps) -> dict          inspect.signature(f, eval_str=True)
  ```

  El único lugar del kit que compara una firma impresa es `40-pruebas.md` paso 2, y por eso su
  comando tiene que llevar `eval_str=True`. Lo que no se hace es sacarle el `__future__` a ese
  archivo para que la firma imprima linda: deja un módulo con otra regla que los demás.
  **Aplicado.** Tres rondas sobrevivió escrito acá y sin cambiar allá; el comando de
  `40-pruebas.md` paso 2 lleva la bandera desde esta ronda, con la medición al lado y un «Si falla»
  para la firma entre comillas. Si vuelve a aparecer sin la bandera, es un archivo que se revirtió.

---

## 5 · El comando de la compuerta

**La forma correcta, y la única que se escribe en el blueprint:**

```bash
.venv/bin/python scripts/auditar.py            # macOS, Linux, WSL
```

```powershell
.venv\Scripts\python.exe scripts\auditar.py    # Windows con PowerShell o cmd
```

```bash
.venv/Scripts/python.exe scripts/auditar.py    # Git Bash sobre Windows
```

Con `--json`, con `--formato texto` y con `--censo`, igual: cambia la bandera, no el intérprete.

**`--censo` es la única bandera que no emite veredicto.** Corre la suite entera una vez por campo
de `contratos/salida.schema.json`, deja `EVIDENCIA/censo.json` y vuelve; el que lee esa evidencia
es el chequeo 23 en la corrida normal. Se pide aparte porque cuesta una suite por campo, y sin
ella el 23 saltea —o sea, con `agente/` en el árbol el veredicto queda en `parcial`—. Se corre una
vez, en el paso 8 de `40-pruebas.md`, entre el `pytest` y la compuerta.

**Por qué.** El `python3` del sistema no trae `jsonschema` ni `pydantic`. Sin `jsonschema`,
`contrato-control` saltea; `contrato-control` está en `SIEMPRE_EXIGIBLES`, así que entra en
`exigidos_sin_correr`, el veredicto baja a `parcial` y la salida es 3. Verificado en esta máquina,
sobre el kit sin construir y sin `.venv`: `python3 scripts/auditar.py` →
`PARCIAL · 0 errores · 0 avisos · 14 salteados`, exit 3. Los tres que se suman a los once
legítimos son `11 wire-schema` sin pydantic, `17 contrato-control` sin jsonschema y `19 pruebas`
sin pytest. El blueprint manda correr un comando que no puede dar el `pass` que el mismo blueprint
manda esperar.

**El matiz, que se dice y no se esconde.** `auditar.py` resuelve solo el intérprete del proyecto:
`_elegir_interprete()` busca `.venv/bin/python3`, `.venv/bin/python`, `venv/bin/python3` y
`.venv/Scripts/python.exe`, en ese orden. Con `.venv` en la raíz, `python3 scripts/auditar.py`
también da el resultado correcto. Se prescribe igual la forma del venv porque no depende de que
`.venv` esté donde el auditor lo busca, y porque falla ruidoso en vez de degradarse a `parcial`.

**Los doce lugares donde el comando está escrito.** Los once primeros decían
`python3 scripts/auditar.py` y pasaron a la forma del venv; el doceavo nace ya en esa forma. Los
números de línea envejecen —cada ronda mueve texto arriba de ellos—: son de cuándo se escribió la
tabla, y lo que manda es el «Qué es».

| Archivo | Línea | Qué es |
|---|---|---|
| `10-entorno.md` | 514 | la corrida opcional del cierre de la fase 1 |
| `20-entrevista.md` | 341 | «Tenés que ver» del paso 13 |
| `30-generacion.md` | 212 | «Tenés que ver» del emisor del contrato |
| `30-generacion.md` | 286 | el cierre de la fase 3 |
| `31-proveedores.md` | 48 | `\| grep` del chequeo `enviar-unico` |
| `31-proveedores.md` | 62 | «a secas» para Windows sin `grep` |
| `32-multimodal.md` | 43 | `\| grep` del chequeo `enviar-unico`, dos veces: paso 1 y paso 5 |
| `33-agenda.md` | 236 | el cierre de la fase |
| `40-pruebas.md` | 365 | el cierre de la fase 5 |
| `90-auditoria.md` | 18 | «Hacé esto» del paso 1 |
| `90-auditoria.md` | 162 | `--json` del paso 5 |
| `40-pruebas.md` | 976 | **`--censo`**, en el «Hacé esto» del paso 8: la corrida cara que deja `EVIDENCIA/censo.json` para el chequeo 23. Es el único lugar donde va la bandera |

**Dos excepciones, las dos escritas a propósito.**

1. `10-entorno.md` línea 514 corre después de crear el `.venv` y espera salteados, no `pass`.
   Cambia el intérprete y deja de esperar `pass`: en fase 1 no existe `agente/`.
2. **`.claude/skills/revisar/SKILL.md` no cambia.** Su comando inyectado es
   `python3 ${CLAUDE_PROJECT_DIR}/scripts/auditar.py --formato texto || true`, y su `allowed-tools`
   tiene que coincidir con esa cadena carácter por carácter o el chequeo de permisos aborta la
   invocación entera. Para cuando alguien corre `/revisar`, el `.venv` ya existe y `auditar.py` lo
   encuentra solo. El `|| true` tampoco se toca: el veredicto distinto de cero es el caso normal.

`.claude/settings.json` tiene que sumar la entrada `Bash(.venv/bin/python scripts/auditar.py:*)` a
la lista `allow`. Sin eso, cada corrida del comando nuevo pide permiso.

---

## 6 · La bajada de medios: un solo lugar

**Vive en `agente/medios.py`. La llama `agente/pasos/paso_1_contexto.py` como primera acción al
desencolar, después del 200. Nunca en el handler de `agente/servidor.py`.**

La frase «se baja al recibirlo» aparece hoy en cinco lugares y sólo uno aclara *después del 200*.
Quien construya en orden la pone en el handler, se le va el presupuesto de cinco segundos y se
come los siete reintentos de Zernio: la misma persona contestada cuatro veces.

Las dos mitades, juntas y sin cortar:

- **Al recibirlo, no cuando hace falta.** Meta suelta el archivo a los pocos días —unos siete, a
  veces menos— y desde ahí la bajada devuelve 400 para siempre. Ese 400 no se recupera.
- **Después del 200, no antes.** El handler contesta y encola. La tensión se resuelve por
  ubicación, no por velocidad.

El archivo queda en `medios/<contacto_id>/<media_id>` y la ruta en `mensaje.media_local`, que es
propiedad declarada de `mensaje` en `contratos/entrada.schema.json`. `/medios/` va en
`.gitignore`, anclado con `/`.

`agente/medios.py` **no escribe ningún host**: importa `BASE_META` y `BASE_ZERNIO` de
`agente/enviar.py`, que es donde § 4 los puso. La bajada de un medio **no** es un envío y la
compuerta no la marca —`graph.facebook.com/<version>/<media_id>` no es una URL de mensajería; ver
§ 12—. El import se pide igual, y por un motivo más chico: la versión de la Graph escrita dos veces
se desincroniza a la primera que alguien suba una y no la otra.

**Quién dice qué:**

| Archivo | Qué le toca |
|---|---|
| `32-multimodal.md` paso 1 | la especificación entera. Es el dueño |
| `31-proveedores.md` paso 5 | una línea y remisión a `32`. No repite el procedimiento |
| `20-entrevista.md` Q11 | por qué `ZERNIO_ACCOUNT_ID` es obligatoria, y remisión |
| `50-despliegue.md` paso 6 | el modo de falla («audios e imágenes rotos»), y remisión |
| `env.example` | el comentario de `ZERNIO_ACCOUNT_ID`, con «en el paso 1, después del 200» |

---

## 7 · `META_APP_SECRET`

**Existe, es obligatoria con `WHATSAPP_PROVIDER=meta`, y hoy no está en ningún lado.**
`plantillas/seguridad/firmas.py` pide `secreto=` en `verificar_meta()`, y ese secreto es el App
Secret de la aplicación. No está en `env.example`, ni en Q11, ni en `31-proveedores.md`: quien
elige `meta` llega al despliegue con un proveedor que no puede verificar una sola firma, y lee
401 en todas las entregas.

```
META_APP_SECRET=
```

- **De dónde sale.** developers.facebook.com → tu app → Configuración → Básica → **Clave secreta
  de la app**. Está tapada detrás de «Mostrar» y te vuelve a pedir la contraseña de la cuenta.
- **La trampa.** No es `WHATSAPP_TOKEN` —ése autoriza a mandar— ni `WHATSAPP_VERIFY_TOKEN` —ése lo
  inventás vos y sólo sirve para el alta—. Son tres valores distintos de la misma pantalla de
  Meta, y el error de usar uno por otro se lee siempre igual: 401 en cada entrega, con cara de
  secreto mal copiado.
- **Dónde se usa.** `agente/proveedores/meta.py`, y en ningún otro archivo:
  `verificar_meta(crudo, cabecera=…, secreto=ajustes.meta_app_secret)`.
- **Con `zernio` o `demo` no hace falta.** Zernio firma con `ZERNIO_WEBHOOK_SECRET` y `demo` saca
  el secreto del `.meta.json` del fixture.

Con esto `env.example` pasa de 17 variables activas a 18. `/salud` la nombra en `faltan` cuando el
proveedor configurado es `meta`.

---

## 8 · La URL síncrona y el recordatorio de 24 horas

El jobstore de APScheduler 3 es **síncrono**: necesita la URL sin `+asyncpg` y sin `+aiosqlite`.
`34-crm.md` dice que `normalizar_url` es la única función del proyecto y siempre devuelve la forma
async. Y `psycopg2` **no está en `PINES.md`** —verificado: no aparece ni ahí ni en
`plantillas/infra/requirements.txt`—. O sea que en el camino recomendado, Railway con Postgres, el
recordatorio de 24 horas no existe hoy, y ningún archivo lo dice.

**La decisión: no se fija un driver síncrono, y se declara detenido.** Escribir un pin que nadie
verificó contra PyPI rompe el invariante 6 y la regla de las 72 horas de `PINES.md`.

**Detenido no quiere decir para siempre, y ya hay un ejemplo trabajado.** La otra detención del
kit —la librería de RS256 de `33-agenda.md` paso 2— se levantó verificando las dos candidatas
contra PyPI, eligiendo la que la compuerta sabe resolver, fijándola con `==` y con fecha,
instalándola y recién ahí reescribiendo el archivo que la esperaba. Este driver se levanta con el
mismo recorrido y con los mismos tres archivos moviéndose juntos, que son los de acá abajo.

**`agente/base.py` expone dos funciones y no una:**

| Función | Devuelve | `sslmode` y compañía |
|---|---|---|
| `normalizar_url(cruda)` | `postgresql+asyncpg://…` · `sqlite+aiosqlite:///./wca.db` | los descarta: asyncpg no los entiende |
| `url_sincrona(cruda)` | `sqlite:///./wca.db` · con Postgres, levanta `RecordatorioSinDriver` | los conserva: libpq sí los entiende |

**La conducta, por base:**

- **SQLite.** El recordatorio funciona entero. `sqlite3` es de la biblioteca estándar y no hace
  falta fijar nada.
- **Postgres.** `url_sincrona()` levanta `RecordatorioSinDriver`. El paso 4 deja
  `cita.recordatorio_programado` en falso con el motivo escrito; **la cita y la confirmación por
  WhatsApp salen igual**. Se dice al agendar, no después.

```
recordatorio de la cita del 2026-03-02 11:00: no lo puedo programar.
El jobstore de APScheduler es síncrono y con Postgres pide un driver síncrono que no está
fijado en PINES.md. La cita y la confirmación sí salen. Con SQLite el recordatorio anda.
Ver blueprint/00-contrato.md § 8 y PENDIENTES.md.
```

**Cómo se levanta la detención**, para que quien lo haga no lo haga a medias. Los tres archivos se
mueven juntos, y ninguno es un paso de tu construcción: es un cambio del kit.

1. `PINES.md`: la línea del driver síncrono, verificada contra PyPI, con más de 72 horas de reposo.
2. `plantillas/infra/requirements.txt`: la misma línea, copiada desde ahí.
3. `python3 scripts/hash_plantillas.py --escribir`, para que `plantillas/MANIFIESTO.json` vuelva a
   coincidir. Sin eso el chequeo 02 falla con `manifiesto/kit_viejo`.

Y `PENDIENTES.md` suma la entrada: «el recordatorio de 24 h con Postgres, detenido hasta que se
fije un driver síncrono».

---

## 9 · `modo` y las claves de `config.py`

Los tres modos viven en `config/cerrador.yaml`, uno por paso destructivo. El contrato de entrada
tiene **un solo** `modo`, porque describe una llamada. Las dos cosas son ciertas y no chocan si se
separan las funciones:

| Función de `agente/config.py` | Devuelve | Cuándo corre |
|---|---|---|
| `entrada_desde_config()` | **nueve claves y ninguna más** | al armar la entrada |
| `modo_efectivo()` | `borrador` o `automatico`: el más conservador de `paso_3`, `paso_4` y `paso_5` | por ciclo |

Las nueve, en orden alfabético: `canal_interno`, `catalogo`, `disponibilidad`, `opciones_horario`,
`palabras_escalacion`, `playbook`, `rango_precio`, `umbrales`, `version`.

**`modo` no es una de las nueve.** Lo inserta `agente/servidor.py` en cada ciclo, junto con
`mensaje` y `confirmado`. Nueve más tres son las doce propiedades de
`contratos/entrada.schema.json`, que es `additionalProperties: false`.

Sin `config/cerrador.yaml` en disco —o sea en toda la fase 3, porque ese archivo lo escribe
`60-bandeja.md`— `modo_efectivo()` devuelve `borrador`. El default no depende de que exista un
archivo.

Así queda cierto lo que dice `30-generacion.md` («nueve claves y ninguna más») y lo que dice
`60-bandeja.md` («`config.py` proyecta el modo»), sin que ninguno de los dos tenga que aflojar.

---

## 10 · El glosario

`CLAUDE.md` fija «cero jerga» como regla y el repo usa «webhook» unas sesenta veces sin definirlo
una sola vez. Estas son las definiciones, una línea cada una, en castellano llano.

**La regla: cada término se explica la primera vez que aparece en cada archivo**, entre guiones
largos y con la remisión pegada. Después, en ese archivo, se usa pelado.

> …el webhook —el aviso automático que WhatsApp le manda a tu servidor cuando entra un mensaje;
> ver `blueprint/00-contrato.md` § 10— llega como POST…

| Término | Qué es |
|---|---|
| **webhook** | El aviso automático que un servicio le manda a tu servidor cuando pasa algo. Acá, cuando entra un mensaje de WhatsApp. |
| **alta del webhook** | El trámite de decirle al proveedor a qué URL avisar. Meta lo hace con un GET que trae `hub.challenge`, que hay que devolver tal cual y como texto plano. |
| **cuerpo crudo** | Los bytes exactos de la petición, tal como llegaron por el cable, antes de parsearlos. En FastAPI, `await request.body()`. Es el invariante 1. |
| **HMAC** | Una huella criptográfica de un texto calculada con un secreto compartido. El que manda la calcula y la firma; el que recibe la recalcula y compara. Si no coincide, la entrega no es de quien dice ser. |
| **firma** | El HMAC que viaja en una cabecera. Meta la manda en `X-Hub-Signature-256` con el prefijo `sha256=`; Zernio en `X-Zernio-Signature`, hex minúscula y sin prefijo. |
| **`hmac.compare_digest`** | La comparación que tarda lo mismo acierte o falle. Con `==` el tiempo de respuesta filtra cuántos caracteres del principio adivinaste. |
| **reserializar** | Parsear el JSON y volver a escribirlo. Cambia el espaciado y el escapado de las tildes, produce otros bytes y por lo tanto otra firma. Pasa las pruebas locales y falla el 100 % de las entregas reales. |
| **ventana de 24 horas** | El plazo desde el último mensaje del contacto en el que WhatsApp deja contestar texto libre. Cerrada la ventana sólo entran plantillas aprobadas. |
| **plantilla aprobada** | Un texto con huecos que Meta revisó de antemano. Es lo único que se puede mandar fuera de la ventana de 24 horas. Se da de alta y se espera aprobación; suele tardar horas. |
| **dedupe** | Descartar la entrega repetida. El proveedor entrega **al-menos-una-vez** y reintenta hasta siete veces: sin dedupe el mismo cliente recibe la misma respuesta cuatro veces. |
| **al-menos-una-vez** | La garantía del proveedor: el mensaje llega, y puede llegar varias veces. Nunca promete llegar una sola. |
| **idempotencia** | Que repetir la misma operación no la haga dos veces. Son dos trabajos distintos: el dedupe a la entrada, y la `Idempotency-Key` a la salida. |
| **`Idempotency-Key`** | Una cabecera con una clave sacada del contenido —conversación, paso y hash del texto—. Con un uuid nuevo por intento no es idempotencia: es un contador. |
| **`businessScopedUserId`** | El identificador que Zernio le da a un contacto dentro de tu negocio. Es el ancla de todo, porque `phoneNumber` puede venir nulo desde abril de 2026. |
| **`wa_id`** | Lo mismo del lado de Meta. Los dos aterrizan en `mensaje.contacto_id`. |
| **cuenta de servicio** | Un usuario de Google que es un programa y no una persona. Se autentica con un archivo JSON y no con una contraseña, y por eso sobrevive a que quien la configuró cambie la clave o se vaya. Para pedir el token firma un JWT con RS256 —`PINES.md` fija `PyJWT` y `cryptography`; ver `blueprint/33-agenda.md` paso 2—. Crearla no alcanza: hay que compartirle el calendario a mano, con la dirección terminada en `.iam.gserviceaccount.com`. |
| **JWT** | Un texto con tres partes separadas por puntos —cabecera, reclamos y firma—, cada una en base64url. Los reclamos son datos en claro: no está cifrado, está firmado. Lo que prueba no es quién lo lee sino quién lo escribió. |
| **RS256** | El algoritmo con que se firma ese JWT cuando la credencial es una cuenta de servicio: hash SHA-256 y firma RSA con la clave privada del archivo JSON. Google verifica con la pública, que ya tiene. No se hace con la biblioteca estándar de Python, y por eso pide una librería fijada. |
| **`iat` · `exp`** | Los dos reclamos de reloj del JWT: cuándo se emitió y cuándo vence. Google los compara contra su propio reloj, así que una máquina desincronizada produce un JWT bien firmado que igual se rechaza. |
| **jobstore** | Donde el programador de tareas guarda lo que tiene pendiente. Si vive en memoria, un despliegue se lleva puestos los trabajos; por eso va sobre la misma base. |
| **upsert** | Un `insert` que, si la fila ya está, actualiza en vez de fallar. Nunca un `delete` seguido de un `insert`. |
| **RLS** | Las políticas de fila de Postgres. Sin políticas, la tabla queda invisible para la clave `anon`; la `service_role` las saltea, y por eso es la que va en `.env`. |
| **caché de prompt** | El descuento que hace la API cuando el principio del prompt es idéntico byte por byte a la petición anterior. Un solo valor variable ahí adentro lo pone en cero, sin ningún error visible. |
| **prefijo estático** | La parte del prompt de sistema que no cambia nunca. Sin reloj, sin `uuid`, sin `random`, sin nada interpolado desde la petición. |
| **borrador · automático** | Los dos modos. En `borrador` los pasos 3, 4 y 5 redactan, muestran y esperan confirmación explícita. Es el default y lo cambia quien instala. |
| **compuerta** | `scripts/auditar.py`. Veintitrés chequeos, tres veredictos, y nada se publica sin `pass`. |
| **veredicto `parcial`** | «No encontré nada, y algo que tenía que mirarse no se miró». Sale con código 3. Un salteado no es un aprobado. |
| **invariante** | Una de las seis reglas de `CLAUDE.md` que ningún archivo puede romper. Cada una tiene su chequeo en la compuerta. |

Dos aclaraciones de nombre que ahorran una hora de confusión:

- **`Mensaje` no es `mensaje`.** `Mensaje` es la dataclass de `agente/proveedores/base.py`, con
  `conversacion_id` y `evento_id` adentro. `mensaje` es la propiedad de
  `contratos/entrada.schema.json`, que no tiene ninguno de los dos. Se traduce de una a otra en el
  paso 1.
- **El campo del contrato es `respuesta.objecion_detectada`**, no `objecion`. El esquema angosto de
  `wire_schema.py` usa el mismo nombre.

---

## 11 · Los nombres reales de `pruebas/`

Mismo defecto que § 1, un directorio más abajo. `40-pruebas.md` prescribía nueve nombres que no
existen y quien lo siguiera se estrellaba en el paso 1. **Corré `ls pruebas/` y
`pytest pruebas --collect-only -q`: manda el disco.**

| Nombre inventado | Qué hay en el árbol |
|---|---|
| `pruebas/dobles.py` | `pruebas/proveedor_falso.py` |
| `pruebas/test_verificaciones.py` | no existe: eso vive en `test_contrato.py` y `test_caso_01.py` |
| `pruebas/test_webhook.py` | no existe: eso vive en `test_firmas.py` y `test_idempotencia.py` |
| `caso-02-enojo.entrada.json` | `caso-02.entrada.json`, con `caso-02.historial.json` al lado |
| `caso-02-precio.entrada.json` | `caso-02b.entrada.json` · `caso-02b.historial.json` |
| `caso-02-palabra.entrada.json` | `caso-02c.entrada.json` · `caso-02c.historial.json` |
| `test_enojo_escala`, `test_precio_fuera_de_rango_escala`, `test_palabra_clave_escala`, `test_sale_exactamente_un_mensaje`, `test_segundo_turno_no_sale_nada` | las nueve funciones de `test_caso_02.py`, todas parametrizadas |
| `test_handoff_en_borrador_queda_redactado` | la mitad `borrador` de `test_sale_un_mensaje_en_automatico_y_ninguno_en_borrador` |
| `test_presupuesto_inventado_se_fuerza_a_nulo` | `test_2_un_presupuesto_sin_evidencia_en_el_mensaje_se_fuerza_a_nulo` |

Tres cuentas que también estaban mal, y la regla para no volver a escribirlas mal:

- **`StubModel` tiene seis salidas sin argumentos**, no cuatro: `canonica`, `presupuesto_inventado`,
  `presupuesto_con_evidencia_falsa`, `resumen_largo`, `objecion_fabricada` y `callado`. Más una
  fábrica que sí lleva argumentos, `presupuesto_con_evidencia_real(monto, evidencia)`. La lista
  canónica es el bucle de `test_las_salidas_del_stub_validan_contra_el_esquema_angosto`.
- **El esquema angosto tiene once campos**, y el de la objeción se llama `objecion_detectada`. La
  lista está en `CAMPOS_WIRE`, arriba de `pruebas/proveedor_falso.py`.
- **Ningún conteo de pruebas se escribe a mano.** `test_caso_01.py` son once nodos y no seis;
  `test_caso_02.py` crece cada vez que alguien agrega un disparador o un canal. El número que manda
  lo imprime `pytest pruebas --collect-only -q`, y el blueprint dice de dónde sacarlo además de
  decir cuánto daba el día que se escribió.

Dos archivos faltaban de verdad y se escribieron en vez de renombrar la cita: `pruebas/caso-02.md`
—la contraparte en prosa de los fixtures del enojo— y `pruebas/extraer_fixture.py` —el que impide
que la prosa y el `.entrada.json` deriven—.

---

## 12 · El invariante 2 se decide por destino

Diez rondas de revisión encontraron el mismo defecto con caras distintas, y la causa era el
enunciado. El invariante 2 decía «ningún `.post`, `.put`, `.patch`, `.request`, `.stream` o `.send`
fuera de `agente/enviar.py`», y así choca con todo lo que sale del agente y no es un mensaje: la
transcripción de Whisper de `32-multimodal.md` paso 2, la imagen que lee el modelo, Google
Calendar, el CRM, el aviso interno del paso 6, el destino firmado del panel. Cada choque se tapaba
con una excepción, y cada excepción abría un agujero: eximir `agente/http.py` dejó vivir adentro un
segundo camino de salida completo —las dos URL de mensajería escritas y los dos POST— con la
compuerta en verde.

**El enunciado que manda es éste:**

> Ningún mensaje a un contacto sale si no es por `enviar()`.

Se decide **por destino**: no por el verbo, no por el archivo, no por el cliente. Un POST a
`api.openai.com/v1/audio/transcriptions` no es un mensaje. Un GET a
`graph.facebook.com/<version>/<media_id>` tampoco. Un POST a
`graph.facebook.com/<version>/<phone_id>/messages` sí lo es, esté escrito donde esté.

**Lo que marca el chequeo 13 `enviar-unico`:** una URL de mensajería escrita fuera de
`agente/enviar.py`. **Los hallazgos son dos, y los dos dicen lo mismo por dos caminos distintos.**
Leídos de `scripts/auditar.py`, que es el que los emite:

| Hallazgo | Qué encontró |
|---|---|
| `enviar/salida_de_mensajeria` | un nodo que **denota la URL de envío entera**: la constante, el nombre importado de otro módulo, el f-string o la llamada que lo usa. La evidencia empieza nombrándolo: «`URL_MENSAJES` denota el endpoint de envío de Meta …, y esto no es agente/enviar.py» |
| `enviar/segundo_camino` | una **cadena armada** que nombra `graph.facebook.com` sin la ruta al lado: el host partido en dos mitades, o la base suelta. La evidencia empieza «nombra `graph.facebook.com` fuera de agente/enviar.py» |

Medido sobre un árbol de prueba de cuatro módulos: `f"{BASE_META}/123/messages"` y el `post` que lo
usa salen los dos como `enviar/salida_de_mensajeria`, uno por línea;
`"https://graph." + "facebook.com/v21.0"` sale como `enviar/segundo_camino`; y
`"/inbox/conversations/{id}/messages"`, aunque sea una constante suelta y sin llamada al lado, sale
como `enviar/salida_de_mensajeria`, porque esa ruta ya denota el envío de Zernio. Un renglón reporta
una sola vez y el nodo de más afuera es el que habla.

`enviar/sin_modulo` es el tercer id y no mira URL ninguna: sale cuando `agente/` está en el árbol y
`agente/enviar.py` no.

| Destino | ¿Se marca? |
|---|---|
| `graph.facebook.com/<version>/<id>/messages` | **sí**: es el envío de Meta |
| `zernio.com/api/v1/inbox/conversations…` | **sí**: es el envío de Zernio, con `/{id}/messages` o sin —la ruta pelada abre la conversación con plantilla, y eso también le llega a una persona— |
| `graph.facebook.com/<version>/<media_id>` | no: es la bajada del medio |
| `api.openai.com/v1/audio/transcriptions` | no: es la transcripción |
| la API de Anthropic, la de Google Calendar, la base del CRM | no |
| `SLACK_WEBHOOK_URL` | no: el aviso va a tu equipo, no a un contacto |
| el destino que da de alta `POST /api/webhooks-salientes` | no: lo escribe quien instala |

Los ids que decidían por verbo —`enviar/salida_suelta` y `enviar/salida_suelta_sin_verbo`— dejaron
de salir, y hoy no están escritos en `scripts/auditar.py`: `grep -n salida_suelta scripts/auditar.py`
no imprime nada. Un archivo que los siga anticipando en un «Si falla» manda a buscar un id que la
compuerta no puede emitir.

**Las tres cosas que la regla vieja no podía tener juntas, y ésta sí:**

- **No hay lista de eximidos.** No hace falta: un mensaje escrito adentro de `agente/http.py` se
  marca igual que en cualquier otro archivo. Ese es el agujero que la excepción abrió y que ninguna
  ronda vio, porque la excepción estaba escrita a propósito.
- **No hay que resolver de dónde salió el cliente.** La regla vieja tenía que reconocer el objeto
  —importado del módulo del cliente, construido con httpx ahí mismo, ligado en un `async with`—, y
  un mensaje mandado con un cliente nuevo, o con `urllib`, no lo era. Por destino, la librería no
  cambia nada.
- **Un GET a la URL de envío también cuenta.** `request("GET", …)` estaba fuera de la tupla de
  verbos y pasaba entero.

**Lo que esta regla no ve, dicho y no escondido.** Si el host viaja en una constante y la ruta se
arma en otro archivo —`"/".join([BASE_META, PHONE_ID, "messages"])`—, la cadena armada de ese
renglón es `{}/{}/messages` y no nombra a nadie. Lo que lo tapa no es la compuerta: es § 4, que deja
`BASE_META` y `BASE_ZERNIO` adentro de `agente/enviar.py` con un solo módulo importándolas,
`agente/medios.py`, y para la bajada. Un tercer módulo que las importe es lo que hay que mirar a
mano en la revisión, y no lo marca nadie.

---

## 13 · El `crm` de un turno sin confirmar

Dos archivos decían cosas distintas del mismo campo y los dos pasaban la compuerta, porque
`contratos/salida.schema.json` acepta `crm` en nulo y `crm` con la fila adentro, y ninguna prueba
elegía:

| Archivo | Qué decía |
|---|---|
| `34-crm.md`, cabecera y paso 5 | el paso 5 arma la fila igual, no la escribe, y la devuelve en `crm` con `escrito` en falso |
| `40-pruebas.md` paso 7, la pantalla del simulador | `CRM · nada preparado en este turno`, que `panel()` sólo imprime con `crm` en nulo |

**Gana `34-crm.md`: `crm` viene con la fila armada y `escrito` en falso.** El que cambia es
`40-pruebas.md`, y ya cambió —la pantalla imprime
`CRM etapa calificado · próximo paso 2026-03-03 · no escrito (borrador)`—. `34-crm.md` no se toca.

Tres motivos, en orden de peso:

1. **La bandeja necesita la fila.** `/api/pendientes` muestra los borradores de los pasos 3, 4 y 5, y
   `POST /api/pendientes/{id}/aprobar` vuelve a correr el paso con `confirmado: true`; ver § 3. Un
   borrador del paso 5 sin fila no es nada que mostrar ni nada que aprobar: quien opera tiene que ver
   qué etapa y qué próximo paso está por firmar antes de firmarlo.
2. **Es la misma forma que el paso 3.** En `borrador` el 3 devuelve `respuesta` con el texto adentro y
   `enviado` en falso; el 5 devuelve `crm` con la fila adentro y `escrito` en falso. El 4 devuelve
   `cita` en nulo y no rompe la simetría: ahí no hay borrador que armar porque nadie eligió horario, y
   eso lo dice su `motivo` —«no hay horario elegido»—, no el modo.
3. **El nulo ya significa otra cosa, y significar dos es perder las dos.** Lo tiene escrito el propio
   `34-crm.md` en su «Si falla»: «`crm` en nulo. Nulo significa "el paso 5 no corrió"». Con la fila
   adentro en el turno normal, el nulo sigue queriendo decir exactamente eso y nada más.

**Lo que todavía dice lo contrario, y por qué no se movió en esta ronda.** Son tres piezas atadas
entre sí, y ninguna es de quien escribió este apartado:

- `pruebas/fixtures/caso-01.salida-esperada.json` trae `"crm": null`, y también
  `"ventana_abierta": true` en un turno con `"enviado": false` —o sea el campo puesto a mano, que es
  justo lo que prohíbe `31-proveedores.md` paso 1—. Las dos cosas están mal por el mismo motivo.
- `scripts/auditar.py` lleva adentro la misma constante, `SALIDA_BUENA`, para poder correr con el
  árbol vacío, y `test_la_salida_esperada_es_la_misma_que_mira_la_compuerta` las compara byte por
  byte: mover una sin la otra pone roja esa prueba con el mensaje ya escrito, «decidí cuál manda y
  actualizá el otro». Se mueven juntas o no se mueve ninguna.
- `pruebas/test_caso_01.py::test_5_sin_confirmacion_no_se_escribe_la_fila` acepta las dos formas
  —«`crm` puede venir nulo o venir con el borrador de la fila adentro»—, que es lo que dejó vivir el
  desacuerdo tres rondas. Con este apartado escrito, esa aserción pasa a exigir la fila con `escrito`
  en falso.

Mientras las tres no se muevan, el simulador **no** marca `RARO` por un `crm` en nulo: sería poner en
rojo a un build que copió la referencia que el propio kit publica, y eso es un hallazgo con
`atribuible_a` en `kit`, lo que `90-auditoria.md` paso 6 enseña a no hacer.

---

### Paso 1 · Verificá que el contrato se esté cumpliendo

**Objetivo.** Ningún archivo de `blueprint/` cita un nombre muerto, todos declaran su próximo
archivo, y `agente/app.py` no existe en ninguna instrucción.

**Hacé esto.**

```bash
grep -rn --exclude=00-contrato.md "10-preparacion\|30-esqueleto\|32-firmas\|33-enviar\|34-pasos\|35-agenda-crm\|agente/app\.py\|agente\.app" blueprint/ .claude/ *.md
grep -rn --exclude=00-contrato.md "pruebas/dobles\.py\|test_verificaciones\|test_webhook\|caso-02-enojo\|caso-02-precio\|caso-02-palabra\|test_handoff_en_borrador_queda_redactado" blueprint/ .claude/ *.md pruebas/*.md
grep -c "Próximo archivo" blueprint/*.md | grep ":0$"
```

**Tenés que ver.** Los dos primeros comandos, sin salida: no quedó un nombre inventado de
`blueprint/` ni de `pruebas/`, ni un `app.py`. El `--exclude` está porque este archivo nombra los
muertos a propósito, en las tablas de § 1 y § 11.

El tercero, exactamente una línea:

```
blueprint/60-bandeja.md:0
```

Quince de los dieciséis declaran su próximo archivo. `60-bandeja.md` es el único que no, porque
cierra la cadena.

**Si falla.**

- **La primera imprime una línea de `blueprint/30-generacion.md`.** Quedó `agente/app.py`. El
  módulo es `agente/servidor.py` y lo escribe `35-panel-api.md`; ver § 3 y § 4.
- **La primera imprime una línea de `.claude/skills/`.** Una skill cita un archivo que no existe, y
  el chequeo 01 `blueprint-existe` lo va a marcar. Corregí el nombre contra `ls blueprint/`.
- **La segunda imprime algo.** Alguien volvió a escribir un nombre de `pruebas/` que no existe.
  Corregilo contra `ls pruebas/` y `pytest pruebas --collect-only -q`; la tabla está en § 11. Este
  es el que se estrella primero, porque `40-pruebas.md` arranca con un `python -m` a un módulo.
- **La tercera nombra un archivo.** Le falta la línea de cierre. La cadena y el texto exacto están
  en § 2.
- **`grep` no existe (Windows).** Abrí los archivos y buscá con el editor, o corré
  `Select-String -Path blueprint\*.md -Pattern "Próximo archivo"` en PowerShell.

---

## Qué archivo tiene que cambiar qué

| Archivo | Qué cambia |
|---|---|
| `blueprint/00-mapa.md` | La tabla pasa de quince filas a dieciséis y suma `05-arranque.md`, entre `00-contrato.md` y `10-entorno.md`. Los seis nombres inventados salen. El «Próximo archivo» del mapa sigue siendo `00-contrato.md`. El orden de la tabla es el de § 2, con `90` antes de `50`. La fila de `20-entrevista.md` dice «once de las doce preguntas», que es lo que hace ese archivo (§ 4). **Y de esta ronda:** la tabla gana la columna «`fase` en el estado» con el valor literal que cada archivo anota en `.wca-estado.json` —`arranque`, `entorno`, `entrevista`, `tramo-1-listo`, `generacion`, `proveedores`, `multimodal`, `agenda`, `crm`, `panel`, `pruebas`, `despliegue`—, y el paso 1 y el contrato de reanudación cruzan contra ésa y no contra «Fase». Cruzar contra «Fase» no encontraba nunca nada: ningún archivo escribe `1`, `2` ni `compuerta`, así que toda reanudación caía en la rama «lo escribió otra versión del kit». Los cinco que no anotan `fase` —los dos del principio, la compuerta, la bandeja y `25-playbook.md`, que es sub-paso de la fase 2 y se entra dos veces— lo dicen en su celda, con el motivo. |
| `blueprint/05-arranque.md` | **Nuevo, y es la fase 0.** Es lo que lee `/start`: mide el sistema, el Python del rango de `PINES.md`, el Claude Code del piso que declara `.claude-plugin/plugin.json`, y que el árbol sea un clon de git y no un ZIP. **No instala nada**: sólo mide. Después declara lo que cuesta y lo que tarda, y hace elegir destino —local o Railway— y proveedor —`demo`, `meta` o `zernio`—. Anota `fase` en `arranque` y cierra con `**Próximo archivo:** blueprint/10-entorno.md`. Entra en la cadena entre `00-contrato.md` y `10-entorno.md`, y por eso el «Próximo archivo» de `00-contrato.md` pasó de `10-entorno.md` a éste. |
| `blueprint/10-entorno.md` | El comando del cierre pasa a `.venv/bin/python scripts/auditar.py` y sigue esperando salteados, no `pass`. Glosario en la primera aparición de: webhook, compuerta, invariante. La línea de cierre dice once preguntas en tres tramos y nombra a Q4 aparte (§ 4). |
| `blueprint/20-entrevista.md` | Q11 suma `META_APP_SECRET` con su trampa (§ 7). La bajada de medios se recorta a una línea y remite a `32` (§ 6). El comando del paso 13, al venv. Cierra con `**Próximo archivo:** blueprint/25-playbook.md`. |
| `blueprint/25-playbook.md` | Cierra con `**Próximo archivo:** blueprint/30-generacion.md`, y al lado la excepción de `/playbook`. El «Si falla» del paso 4 deja de decir que por el camino B la copia no existe: el `cp` del paso 1 va en los tres caminos, y lo que ese remedio usa igual es la plantilla y no la copia. |
| `blueprint/30-generacion.md` | Pierde los pasos 4, 5, 8 y 9: pasan a remitir (§ 4). El árbol de la cabecera nombra el dueño de cada línea y dice `agente/servidor.py`, no `app.py`. `normalizar_url()` y `url_sincrona()` entran en el paso de `base.py` (§ 8). El paso de `config.py` fija las nueve claves y nombra `modo_efectivo()` (§ 9). Los dos comandos, al venv. El paso 2 deja escrito que `agente/__init__.py` queda vacío y que la única forma de traer la instancia es `from agente.ajustes import ajustes` (§ 4). Cierra con `**Próximo archivo:** blueprint/31-proveedores.md`. |
| `blueprint/31-proveedores.md` | Queda como dueño único de `enviar.py` y `proveedores/`. El paso 4 nombra `META_APP_SECRET` en `verificar_meta(...)`. El párrafo de medios del paso 5 se recorta y remite a `32`. Los dos comandos, al venv. El chequeo `enviar-unico` se describe por destino y no por verbo, con los dos ids que la compuerta emite hoy (§ 12). La cabecera de `enviar.py` importa `from agente.ajustes import ajustes` y no `from agente import ajustes` (§ 4). |
| `blueprint/32-multimodal.md` | Suma el paso de cierre que escribe `agente/pasos/paso_1`, `paso_2`, `paso_3`, `paso_6` y `avisar_interno()` al final de `agente/enviar.py`. `agente/integraciones/aviso.py` sigue sin existir, y el motivo pasa a ser § 4 y no el chequeo 13 (§ 12). El invariante 2 se enuncia por destino en los cuatro lugares donde el archivo lo nombra, y el POST a `api.openai.com` del paso 2 deja de chocar con la compuerta. Es el dueño único de la bajada de medios (§ 6). El comando, al venv. El «Si falla» del paso 2 deja de anticipar `enviar/salida_suelta`: ese id salió de la compuerta y el que se lee hoy es `enviar/salida_de_mensajeria` (§ 12). |
| `blueprint/33-agenda.md` | El paso 4 usa `url_sincrona()` y escribe la conducta detenida con Postgres (§ 8), con el bloque literal. La viñeta de `psycopg2` deja de ser un modo de falla y pasa a ser lo declarado. El comando, al venv. **Y de esta ronda:** el paso 2 escribe la rama `service_account` entera —el JWT de cinco reclamos, la firma con `PyJWT`, el cuerpo `jwt-bearer` del `POST`— con sus cuatro tiempos; la tabla del paso 1 dice que las dos credenciales andan y cuál conviene a un negocio; el «Si falla» suma las dos que salen mal seguro, el calendario sin compartir —404 sobre un calendario que estás mirando— y el reloj corrido —`invalid_grant` con la credencial recién bajada—; y queda escrito qué afirmar de la rama nueva y con qué doble, porque las pruebas son de otro dueño. |
| `blueprint/34-crm.md` | El paso 2 pierde el bloque de código de `normalizar_url()` —se va a `30`— y se queda con la verificación, más una línea sobre `url_sincrona()` y por qué conserva `sslmode`. **De § 13 no cambia nada**: su forma del `crm` —la fila armada, `escrito` en falso— es la que manda. Lo único suyo que sigue pendiente es el total de pytest escrito a mano de la línea 259, que va sin el entero; la tabla de dueños está en `40-pruebas.md` paso 8. |
| `blueprint/35-panel-api.md` | La tabla de rutas de § 3, verbatim. `exigir_token` suma el `?token=` de la query. Sigue siendo el dueño de `servidor.py` y de `panel/panel.py`. Sale la línea «si la fase 3 dejó `agente/app.py`, renombralo ahora»: con este contrato la fase 3 no lo deja. El «Tenés que ver» del paso 1 es el comando de § 3 y no `sorted({r.path for r in app.routes})`, que con estos pines revienta con `AttributeError`. El `cliente.post(destino, …)` del webhook saliente deja de necesitar defensa: el destino lo escribe quien instala y no es una URL de mensajería (§ 12). |
| `blueprint/40-pruebas.md` | El comando del paso 8, al venv. Cierra con `**Próximo archivo:** blueprint/90-auditoria.md`. Y los nombres de `pruebas/`, que citaba inventados: es `proveedor_falso.py` y no `dobles.py`; no hay `test_verificaciones.py` ni `test_webhook.py` —eso vive en `test_contrato.py`, `test_firmas.py` y `test_idempotencia.py`—; los fixtures del 02 son `caso-02`, `caso-02b` y `caso-02c`, no `-enojo/-precio/-palabra`; `StubModel` tiene seis salidas sin argumentos y una fábrica, no cuatro; y los conteos de pruebas salen de `pytest --collect-only -q`, no de un entero escrito a mano. Ver § 11. Y el «Tenés que ver» del paso 2 pide `inspect.signature(c.correr_ciclo, eval_str=True)`: sin `eval_str` la salida es `(entrada: 'dict', *, modelo, deps) -> 'dict'`, con las comillas, porque todo módulo del árbol abre con `from __future__ import annotations` y ahí las anotaciones son cadenas. Ver `blueprint/31-proveedores.md` paso 1. **Hecho en esta ronda**, con tres cosas más: el paso 5 fija el orden de los tres disparadores —`palabra_clave`, `precio_fuera_de_rango`, `enojo`— que no estaba escrito en ningún archivo; las dos pantallas del paso 7 se rederivaron llamando a `panel()` y `revisiones()` de verdad y perdieron los tres renglones que ningún build puede imprimir (§ 13 y la ventana de 24 h); y el grep de totales del paso 8 pasa de lista a tabla con dueño por línea. |
| `blueprint/50-despliegue.md` | El paso 5 deja de decir «si `env.example` no lo nombra, declaralo»: ahora lo nombra, y es `META_APP_SECRET` (§ 7). El párrafo de medios del paso 6 remite a `32`. Cierra con `**Próximo archivo:** blueprint/60-bandeja.md`. |
| `blueprint/60-bandeja.md` | Explicita que el modo lo proyecta `modo_efectivo()` y no `entrada_desde_config()` (§ 9). |
| `blueprint/90-auditoria.md` | `**Hacé esto**` del paso 1 y el `--json` del paso 5, al venv. El «Si falla» de «casi todo salteado» explica el `parcial` con salida 3. La ficha del chequeo 13 se reescribe por destino: los hallazgos son `enviar/salida_de_mensajeria` y `enviar/segundo_camino`, sin la lista de verbos y sin los dos archivos eximidos (§ 12). `enviar/salida_suelta` sale del «Si falla» del paso 3: la compuerta ya no lo emite. Cierra con `**Próximo archivo:** blueprint/50-despliegue.md`. |
| `scripts/auditar.py` | El chequeo 13 `enviar-unico` decide por destino: marca la URL de mensajería esté donde esté escrita, deja de mirar el verbo, el cliente y el archivo, y `EXIMIDOS_DE_ENVIAR` desaparece con los dos ids que decidían por verbo (§ 12). **Ya está hecho**, y los dos ids que emite hoy son los de la tabla de § 12. Queda una sola cosa, y es de § 13: la constante `SALIDA_BUENA` pasa a traer el `crm` con la fila y `escrito` en falso, y `ventana_abierta` en nulo. |
| `pruebas/fixtures/caso-01.salida-esperada.json` · `pruebas/test_caso_01.py` | Las otras dos piezas del mismo movimiento de § 13, que van con la de arriba en un solo cambio: el fixture pasa a traer el `crm` armado y `ventana_abierta` en nulo —hoy dice `true` con `enviado: false`—, y `test_5_sin_confirmacion_no_se_escribe_la_fila` deja de aceptar las dos formas y exige la fila con `escrito` en falso. Los tres se mueven juntos o `test_la_salida_esperada_es_la_misma_que_mira_la_compuerta` se pone roja. |
| `CLAUDE.md` | El invariante 2 se enuncia por destino: «ningún mensaje a un contacto sale si no es por `enviar()`», con la ventana de 24 h, el chequeo de baneo y el no escribir primero como lo que hace ese único camino (§ 12). |
| `env.example` | Suma `META_APP_SECRET` en el bloque de Meta, con la ruta y la trampa (§ 7). El comentario de `ZERNIO_ACCOUNT_ID` agrega «en el paso 1, después del 200». Pasa de 17 variables activas a 18. |
| `.claude/settings.json` | Suma `Bash(.venv/bin/python scripts/auditar.py:*)` a `allow`. |
| `.claude/skills/revisar/SKILL.md` | **No cambia.** El comando inyectado y `allowed-tools` tienen que seguir coincidiendo carácter por carácter (§ 5). |
| `.claude/skills/publicar/SKILL.md` | «Se despliega con `pass`» deja de alcanzar: suma la condición del índice de git —lo que un `git clone` entrega tiene que ser el árbol que la compuerta auditó— y qué hace la skill cuando no se cumple. |
| `PINES.md` | **El driver síncrono no cambia**: se declara detenido, no se fija (§ 8). Lo que sí entró en esta ronda son los dos pines que destraban la otra detención, la de RS256: `PyJWT==2.13.0` y `cryptography==50.0.0`, verificados contra PyPI el 2026-08-14, con la elección contra `google-auth` argumentada y medida ahí mismo. Pasa de 28 pines a 30, y `plantillas/infra/requirements.txt` con él —lo que obliga a `scripts/hash_plantillas.py --escribir`, o el chequeo 02 falla con `manifiesto/kit_viejo`—. |
| `PENDIENTES.md` | Suma dos entradas: el recordatorio de 24 h con Postgres, y `META_APP_SECRET` como credencial nueva del camino `meta`. |
| `.gitignore` | Suma `/config/playbook-base.yaml`, anclado, con el comentario de por qué ese archivo sí y el resto de `config/` no (§ 4). |
| `plantillas/` | Los siete archivos son verbatim y el `MANIFIESTO.json` los hashea. Se tocan dos: el comentario de cabecera de `plantillas/config/playbook-base.yaml`, que describía un flujo viejo —«el paso 2 lo copia»— y ahora dice lo que dice `25-playbook.md` —copia en el paso 1, en los tres caminos—, y `plantillas/infra/requirements.txt`, que suma las dos líneas de RS256 de `PINES.md`. Toda edición acá, aunque sea un comentario, exige `scripts/hash_plantillas.py --escribir`, o el chequeo 02 falla con `manifiesto/kit_viejo`. |

**Próximo archivo:** `blueprint/05-arranque.md`, la fase 0: mide el terreno, dice lo que cuesta y
lo que tarda, y te hace elegir destino. No instala nada; el intérprete, las 30 dependencias y la
clave los deja `blueprint/10-entorno.md`, que es a donde manda el 05 al cerrar.

> **El número cambió en esta ronda y está escrito a mano en seis lugares más.** Eran 28 hasta que
> `PINES.md` sumó `PyJWT` y `cryptography` para destrabar la rama `service_account` del paso 4.
> Dicen 28 todavía: `README.md`, `plantillas/README.md`, `blueprint/00-mapa.md`,
> `blueprint/10-entorno.md` —cuatro veces— y dos mensajes de `scripts/auditar.py`. Ninguno es de
> este archivo y la compuerta no compara ese número contra nada, así que no se pone rojo solo.
> Manda `PINES.md`, y quien los cuenta es el chequeo 05, que lo imprime en su propio renglón:
>
> ```
> [ok      ] 05 pines   30 pines en 1 archivo(s), MODELO=claude-opus-5, imagen python:3.12-slim
> ```
>
> No sirve `grep -c '=='` sobre `requirements.txt`: da 31, porque el comentario de la cabecera
> nombra el `==` de la regla.
