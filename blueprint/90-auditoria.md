# 90 · La auditoría

**La compuerta.** Entrás con la suite en verde; salís con `EVIDENCIA/gates.json` escrito y el
veredicto en `pass`. Es lo que corre `/revisar`. Por cada chequeo: qué prueba, por qué existe y
cómo se arregla.

La compuerta —`scripts/auditar.py`: veintitrés chequeos, tres veredictos, y nada se publica sin
`pass`; ver `blueprint/00-contrato.md` § 10— **no toca la red, nunca.** `/revisar` la corre con un
comando inyectado: si ese comando cuelga, **la skill se aborta y Claude no ve nada**, y la
protección desaparece justo cuando hacía falta —un chequeo contra Meta con mala conexión espera dos
minutos un timeout de TCP—. Cada subproceso lleva timeout y un entorno sin lo que parece secreto:
uno que intentara autenticarse no tendría con qué. Probar un token parece una mejora obvia y no lo
es: va en `/probar`.

Este archivo corre **antes** de `50-despliegue.md`. Lleva el 90 porque también es el que `/revisar`
abre cualquier día, no porque vaya último.

---

### Paso 1 · Corré la compuerta

**Objetivo.** Los veintitrés chequeos corrieron y el veredicto está en disco.

**Hacé esto.**

```bash
.venv/bin/python scripts/auditar.py            # macOS, Linux, WSL
```

```powershell
.venv\Scripts\python.exe scripts\auditar.py    # Windows con PowerShell o cmd
```

**El intérprete es del proyecto, no del sistema, y esto no es estilo.** El `python3` del sistema no
trae `jsonschema` ni `pydantic`. Sin `jsonschema`, `contrato-control` saltea; `contrato-control` es
exigible siempre, así que entra en `exigidos_sin_correr`, el veredicto baja a `parcial` y la salida
es 3. O sea: con `python3` este paso no puede dar el `pass` que el paso siguiente exige. Ver
`blueprint/00-contrato.md` § 5.

**Tenés que ver.** El árbol, una línea por chequeo y el resumen:

```
auditar · whatsapp-closer-agentkit · construido

  [ok      ] 01 blueprint-existe   16 archivo(s) citados por 28, todos con contenido
  ...
  [ok      ] 21 panel-cerrado      NN router(s) y app(s) leídos, N con `exigir_token` puesto · t
  [ok      ] 22 rutas-del-contrato 10 rutas · 11 métodos, los de la tabla de blueprint/00-contr
  [ok      ] 23 censo-de-campos    43 campos declarados: NN afirmados por una prueba que se pu

auditar: PASS · 0 errores · 0 avisos · 0 salteados
  evidencia: /ruta/al/proyecto/EVIDENCIA/gates.json
```

**Los números que cada línea trae al lado son los de tu corrida, no una meta.** Suben y bajan con el
árbol —cuántos módulos tiene tu `agente/`, cuántos archivos del núcleo hay en el índice, cuántos
nodos junta la suite—, y las líneas que este archivo pega de ejemplo están para que reconozcas la
forma, no para que las iguales. Lo que sí se compara contra lo escrito es el `[ok]` de cada una y el
veredicto del final. Por qué el kit dejó de escribir esos totales, en `blueprint/40-pruebas.md`,
Paso 8.

Son veintitrés líneas numeradas de `01` a `23`, en el orden del `REGISTRO` de `scripts/auditar.py`,
y la última línea trae la ruta absoluta del `gates.json`, no la relativa. **El `21`, el `22` y el
`23` están al final y no al lado del 14 a propósito**: los demás archivos del blueprint citan los
chequeos por número —«el chequeo 13», «el chequeo 02»— y meter uno en el medio los corre a todos de
lugar. Cada chequeo nuevo entra por el final, siempre.

Cuando hay salteados se cuela un renglón más antes de la evidencia —«un salteado no es un
aprobado: leé el motivo de cada uno»—, y con `parcial` otro más que los nombra.

Tres veredictos, tres salidas: `pass` 0, `parcial` 3, `fail` 2. `parcial` es «no encontré nada, y
algo que tenía que mirarse no se miró», y con `parcial` no se publica. Un salteado no es un
aprobado: cada uno imprime su motivo, y el resumen te vuelve a avisar que los leas.

**Si falla.**

- **Casi todo salteado, y abajo `parcial: contrato-control tenía que correr en este árbol y
  salteó`.** Corriste con el Python del sistema. Medido en el kit sin construir y sin `.venv`:
  `python3 scripts/auditar.py` da `PARCIAL · 0 errores · 0 avisos · 14 salteados` y sale 3. Los
  tres que se suman a los once legítimos son los que no tienen con qué correr en ese intérprete:
  `11 wire-schema` sin pydantic, `17 contrato-control` sin jsonschema y `19 pruebas` sin pytest.
  **Cero errores y no publica**, que es la parte que confunde: no falló nada, no se miró todo.
  Volvé a correrlo con el comando de arriba.
- **`.venv/bin/python: no such file or directory`.** El entorno no está creado: volvé a
  `blueprint/10-entorno.md`. En Git Bash sobre Windows la ruta es
  `.venv/Scripts/python.exe scripts/auditar.py`.
- **Se cuelga.** Nada de acá abre un socket. El único que ejecuta código del proyecto es `firmas`,
  cortado a los 60 s; la suite, a los 120.
- **`auditoria/excepcion`.** Un chequeo levantó una excepción y los otros veintidós corrieron
  igual. Es un defecto de `scripts/auditar.py`, nuestro, no tuyo.

---

### Paso 2 · Los diez que corren sin `agente/`

**Objetivo.** Sabés qué prueba cada chequeo del kit y cómo se arregla, antes y después de construir.

**Hacé esto.** Leé las líneas 01, 02, 03, 04, 05, 07, 08, 09, 11 y 20. Ninguno pregunta por
`agente/`: corren en un árbol recién clonado igual que en uno construido. El 20 es el único de los
diez que además espera una fase —la 2, que escribe `config/playbook.yaml`—.

- **01 blueprint-existe** — cada `blueprint/NN-*.md` que citan `CLAUDE.md`, un `SKILL.md` u otro
  blueprint existe **y pesa más de cero bytes**. Es el chequeo que faltaba, y va primero por lo que
  cuesta y por lo que tapa: las once skills no traen el procedimiento adentro, traen la cita. Sin el
  archivo citado el comando **no falla**: abre, no encuentra nada y construye de memoria, que es lo
  único que este kit pide no hacer. Los otros veintidós dan verde igual, porque ninguno mira ahí.
  Existir tampoco alcanza: cero bytes es el estado real de un archivo mientras otro proceso lo
  escribe, y con `is_file()` a secas pasaba en verde. El caso inverso —un blueprint que no cita
  nadie— es aviso, `blueprint/sin_citar`: no rompe nada, pero no hay comando que lo abra.
- **02 manifiesto** — cada plantilla contra su sha256, y cada archivo copiado contra su plantilla.
  Delega en `scripts/hash_plantillas.py`, que ya distingue los dos casos: ver **Si falla**.
- **03 railway-arranque** — que ningún `railway.json` traiga `startCommand`, ni en la plantilla ni
  en el de la raíz, ni al primer nivel ni adentro de `environments`: una ausencia no se verifica por
  hash. Esa clave pisa el `CMD`, que resuelve `${PORT:-8000}` al arrancar porque Railway inyecta el
  puerto y lo cambia en cada despliegue; con el puerto a mano la app escucha en otro lado, el
  healthcheck no contesta y sólo se lee `service unavailable`. Sacá la clave.
- **04 claudemd-tam** — `CLAUDE.md` ≤ 2600 bytes: se paga en cada turno. El 2600 es el techo, que
  es lo que hay que saber; el tamaño de hoy lo imprime el chequeo al lado.
- **05 pines** — `==` en toda línea de `requirements.txt` y cada número igual al de `PINES.md`, más
  el `MODELO` de `env.example` y el `FROM` del Dockerfile, que son los otros dos números fijados que
  no viven en `requirements.txt`. Un `>=` instala lo que salió ayer: corregí `PINES.md` y copiá
  desde ahí, nunca al revés.
- **07 deps-drivers** — `+(\w+)://` en las cadenas de todo el proyecto, no en los imports:
  `asyncpg` no aparece en ninguno —vive adentro de `postgresql+asyncpg://`— y con SQLite esa línea
  nunca corre. Los `.py` se miran por su árbol, con las cinco formas de armar una cadena ya pegadas
  —`+`, `%`, `.format()`, `join`, f-string— y sin docstrings; todo lo demás como texto plano, porque
  la `DATABASE_URL` vive en `alembic.ini`, en `docker-compose.yml` o en `railway.json`. En un `.md`
  el hallazgo baja a aviso: un párrafo no abre una conexión. El aviso `drivers/interpolado` dice que
  el nombre llega por configuración y hay que buscarlo ahí. Corre siempre, pero con `agente/` en el
  árbol su salteo pesa: ver el Paso 5.
- **08 secretos** — los patrones de credencial que trae la compuerta, sobre lo rastreado **y lo
  que todavía no**, más
  `.env` ignorado y sin rastrear —son dos preguntas distintas— y `env.example` sin un solo valor
  escrito. Si aparece una: sacala, `git rm --cached .env` y rotala igual.
- **09 gitignore-anclado** — archivo por archivo, no carpeta por carpeta, si git ignora algo del
  núcleo. `SKILL.md`, `*.raw` o `auditar.py` sin anclar se llevan las skills, los fixtures o la
  compuerta entera sin tocar una sola ruta de directorio, y quien clona no recibe nada de eso.
  Anclá el patrón con `/`.
- **11 wire-schema** — el esquema angosto que sale hacia el modelo, contra su golden. Dos formas de
  romperse: una palabra que la salida estructurada rechaza da 400, y un golden viejo no falla nada,
  sólo deja de ser lo que alguien revisó. Se renderiza en un subproceso con pydantic; si no está en
  ningún intérprete, saltea con el motivo escrito y **no** mueve el veredicto. Se regenera con
  `.venv/bin/python plantillas/contratos/wire_schema.py`.
- **20 playbook** — `config/playbook.yaml` valida contra el fragmento `playbook` de
  `contratos/entrada.schema.json`, no le quedan huecos con llaves sin llenar, y el piso de dos
  claves —`descuento` y `garantia`— ancla una objeción que existe **y que habla de eso**. La clave
  sola se falsifica en dos renglones: dos claves apuntando a «Ahora no tengo un minuto» daban
  `piso: 2 de 2` con el piso vacío. Saltea mientras el archivo no exista, porque lo escribe el paso
  7 de `blueprint/25-playbook.md` en la fase 2; con `agente/` en el árbol ese salteo mueve el
  veredicto, porque `playbook` es campo obligatorio de la entrada y sin él no arranca un ciclo.

**Tenés que ver.** Las diez en `[ok]`, con su cuenta al lado:

```
  [ok      ] 07 deps-drivers       2 driver(s) en cadenas de conexión: aiosqlite, asyncpg
  [ok      ] 09 gitignore-anclado  52 archivos del núcleo: 52 rastreados, 0 sin rastrear · 6 carpeta(s) y ruta(s)
  [ok      ] 20 playbook           8 objeciones · piso: 2 de 2 · huecos: ninguno
```

La línea del 09 sale cortada —el reporte recorta el motivo a 78 caracteres, y lo que falta es «más,
0 ignoradas por patrón»—, y dice **dos** cuentas y no una, porque son dos preguntas: cuántos
archivos del núcleo están en el índice de git —lo que un `git clone` entrega hoy— y cuántas rutas
se lleva un patrón del `.gitignore`. Los 52 suben y bajan con el árbol; lo que no puede cambiar es
el `0 sin rastrear` y el `0 ignoradas`. Si clonaste el kit los dos ceros salen solos; si bajaste un
ZIP y armaste el repo a mano, el primero sale distinto y abajo aparece el aviso
`gitignore/nucleo_sin_rastrear` con la lista. Con `agente/` en el árbol —o con `--publicando`— ese
aviso es error.

**Si falla.** El manifiesto dice **dos cosas distintas**:

- **`manifiesto/kit_viejo`** — la plantilla cambió y el manifiesto quedó viejo. Lo rompimos
  nosotros: `python3 scripts/hash_plantillas.py --escribir`. No toques tu build.
- **`manifiesto/build_derivado`** — un archivo generado se apartó de su plantilla: volvé a copiar la
  plantilla sobre el archivo de `agente/`.

Sin esa distinción se debuggea una hora el build propio por un defecto nuestro. Y con el build
derivado, `firmas` tampoco ejecuta `agente/firmas.py`: ese archivo ya no es el que enviamos.

Los otros dos que se leen mal:

- **`blueprint/citado_y_ausente` o `citado_y_vacio`** — corregí el nombre contra `ls blueprint/`, o
  terminá de escribir el archivo. La tabla de los seis nombres que no existen está en
  `blueprint/00-contrato.md` § 1.
- **`pines/desacuerdo`** — el número está escrito en dos lados y ya dicen cosas distintas. Gana
  `PINES.md`, siempre.

---

### Paso 3 · Los ocho que esperan el build

**Objetivo.** Los que necesitan `agente/` corrieron y ninguno saltea.

**Hacé esto.** Leé las líneas 06, 10, 12, 13, 14, 15, 21 y 22. Sin `agente/` los ocho saltean con el
mismo motivo escrito —«esto corre después de `/armar-cerrador`»— y eso es legítimo. Con `agente/` en
el árbol deja de serlo: ver el Paso 5.

- **06 deps-imports** — cada raíz importada por un `.py` de `agente/` mapea a una distribución
  fijada; si no, es un `ModuleNotFoundError` al arrancar en la máquina de quien clona.
- **10 modelo** — los literales `claude-*` contra los vigentes —`claude-opus-5`, `claude-sonnet-5`,
  `claude-haiku-4-5`—, aviso si el literal es vigente pero distinto del `MODELO` de `PINES.md`, y
  error por los cuatro parámetros que devuelven 400: `temperature`, `top_p`, `top_k` y
  `budget_tokens`, como argumento con nombre o como clave de diccionario. Los docstrings no cuentan:
  contar que el kit viejo usaba otro modelo no es fijarlo.
- **12 http-unico** — un solo cliente, en `agente/http.py`, con `timeout=`. Construir un
  `httpx.AsyncClient` en otro módulo es error; construirlo ahí sin `timeout=` también. Sin timeout
  httpx espera para siempre, y el webhook de Zernio pide 2xx en menos de 5 s con hasta siete
  reintentos.
- **13 enviar-unico** — el invariante de mayor consecuencia, y **se decide por destino**: no por el
  verbo, no por el cliente, no por el archivo. El enunciado es «ningún mensaje a un contacto sale si
  no es por `enviar()`», así que lo que marca es **una URL de mensajería escrita fuera de
  `agente/enviar.py`**, esté escrita como esté y salga por donde salga. Un POST a
  `api.openai.com/v1/audio/transcriptions` no es un mensaje y no se marca; un GET a
  `graph.facebook.com/<version>/<media_id>` tampoco; y `graph.facebook.com/<version>/<id>/messages`
  sí, y `zernio.com/api/v1/inbox/conversations…` también, con `/{id}/messages` o sin. Los
  hallazgos son dos: `enviar/salida_de_mensajeria`, un nodo que **denota la URL entera** —la
  constante, el nombre importado de otro módulo, el f-string o la llamada que lo usa—, y
  `enviar/segundo_camino`, una **cadena armada** que nombra el host sin la ruta al lado, porque
  `"https://graph." + "facebook.com/v21.0"` no lo nombra en ninguna de sus dos mitades. Más
  `enviar/sin_modulo`, que no mira ninguna URL: sale cuando la construcción corrió y
  `agente/enviar.py` no está. Un segundo
  camino de salida no consulta la ventana de 24 h ni el baneo, y lo que se pierde es el número del
  negocio. **No hay lista de eximidos**: el dueño es `agente/enviar.py` y todo lo demás se mira
  igual, incluido `agente/http.py` —adentro de esa excepción, mientras existió, vivió un segundo
  camino de salida entero con la compuerta en verde—. Y el aviso interno del paso 6 es
  `avisar_interno()` adentro de `enviar.py` y no un módulo aparte **por el mapa de dueños y no por
  este chequeo**: un POST a `SLACK_WEBHOOK_URL` va a tu equipo y no a un contacto, así que no lo
  marca nadie. Ver `blueprint/00-contrato.md` § 12 —el enunciado y la tabla de destinos— y § 4.
- **14 agente-completo** — cada módulo del piso está en el árbol **y define adentro los símbolos
  que promete**. Son diecisiete rutas y treinta y un símbolos, y el piso vive en `PISO_DE_MODULOS`,
  adentro de la compuerta, además de leerse de la tabla de `blueprint/30-generacion.md`: una fila
  borrada de esa tabla es un módulo que nadie va a escribir, y sale como
  `agente/tabla_recortada`. Se pregunta por AST y no por el tamaño del archivo, porque un `#` de
  dos bytes no define `correr_ciclo` y con «existe y pesa más de cero» un árbol de trece archivos
  vacíos pasaba en verde.
- **15 cache-estatico** — reloj, `uuid`/`random`/`secrets`, o un f-string que lea un parámetro con
  cara de venir de la petición, adentro del prefijo del prompt de sistema: el caché no acierta
  nunca, no hay nada roto que mirar y la factura sube. Busca funciones —y módulos— cuyo nombre diga
  `prompt`, `sistema` o `system`, y si no encuentra ninguna **saltea y te lo dice** en vez de fingir
  que revisó. Con `agente/` en el árbol ese salteo mueve el veredicto: nombrá la función.
- **21 panel-cerrado** — que ninguna ruta bajo `/api/` ni `/panel` conteste sin pasar por
  `exigir_token`, y que `/salud` y `/webhook/{proveedor}` sigan contestando **sin** token, que es la
  contracara: Railway no manda cabeceras y el despliegue se muere en el chequeo de salud. Es **una
  línea** —`router = APIRouter(dependencies=[Depends(exigir_token)])`—, y sin ella el panel queda
  publicando los teléfonos, los scores y los resúmenes del CRM de los clientes en la URL pública,
  desde el primer despliegue. Medido sobre un build que estaba en verde, recortando esa sola línea:
  la suite entera pasaba y el veredicto salía `PASS · 0 errores · 0 avisos · 0 salteados`, con
  `GET /api/leads` sin token devolviendo la tabla. Se lee por AST, no importando ni ejecutando nada
  del build: se resuelven los `APIRouter(...)` y los `include_router(...)` a nivel de módulo y se
  pregunta de qué cuelga cada camino escrito en un decorador. **Una ruta que no se puede afirmar
  cerrada se trata como abierta**, así que un `dependencies=` armado en otra variable sale como
  error y no como verde. Entró por el final del `REGISTRO` y no al lado del 14 para no correr de
  número a los que ya estaban; hoy tiene al 22 y al 23 detrás, puestos ahí por lo mismo.
  Siete hallazgos, todos `build`: `panel/router_abierto` y `panel/sin_router` por
  el router; `panel/ruta_suelta` y `panel/dependencia_por_ruta` —la que cierra hoy y mañana no,
  porque la ruta que alguien agregue a ese router nace sin nada— por las rutas;
  `panel/ruta_sin_router` por las que no se pueden resolver; `panel/publica_con_token` por `/salud`
  o el webhook metidos adentro; y `panel/sin_rutas_de_api` cuando no hay una sola ruta escrita.
  Lo que se afirma del otro lado —401 sin token, 401 con el token que es prefijo del bueno, 200 por
  los tres lugares que `blueprint/00-contrato.md` § 3 manda leer— vive en `pruebas/test_panel.py`;
  ver `blueprint/35-panel-api.md` paso 4.
- **22 rutas-del-contrato** — el juego de rutas montadas es **el de la tabla de
  `blueprint/00-contrato.md` § 3, entero y sin una más**: diez caminos, once métodos, con el prefijo
  de cada router ya adelante y los nombres de parámetro normalizados, así que
  `/api/conversaciones/{contacto_id}` y `/api/conversaciones/{id}` son la misma fila. El 21 decide
  por el prefijo del camino, así que un `@app.get("/tablero")` de doce renglones que devuelva
  `listar_leads()` deja `/api/leads` en 401 y `/tablero` en **200**, con los números, los scores y
  los resúmenes del CRM adentro, y el árbol sigue en `PASS · 0 errores · 0 avisos · 0 salteados`.
  Por eso la vara es la tabla y no una lista de prefijos: cierra la clase y no el caso que alguien
  ya vio. Dos hallazgos: `rutas/de_mas`, una por renglón con su archivo y su línea, y
  `rutas/faltan`, todas juntas porque la causa es una. Tiene un salteo legítimo más que los otros
  siete —`agente/servidor.py` todavía sin escribir, y ahí el 14 ya está en rojo por su cuenta—. Lo
  que no ve: un camino que no esté escrito como literal en el decorador; eso lo mira
  `pruebas/test_panel.py` preguntándole a la app montada, y esta compuerta corre esa suite en el
  chequeo 19.

**Tenés que ver.** Los ocho en `[ok]`, y ninguno en `[salteado]`. Por ejemplo:

```
  [ok      ] 12 http-unico         3 construcción(es), todas en agente/http.py
  [ok      ] 13 enviar-unico      NN módulo(s) revisados contra los dos endpoints de mensajería · d
  [ok      ] 14 agente-completo   17 ruta(s) —17 del piso de la compuerta, 0 más de blueprint/30-generacion.md—
  [ok      ] 15 cache-estatico     2 constructor(es) de prompt revisados
  [ok      ] 21 panel-cerrado      NN router(s) y app(s) leídos, N con `exigir_token` puesto · t
  [ok      ] 22 rutas-del-contrato 10 rutas · 11 métodos, los de la tabla de blueprint/00-contr
```

Las líneas del 13 y del 14 salen cortadas: el reporte recorta el motivo a 78 caracteres. Lo que le
falta al 13 es «dueño: agente/enviar.py · sin eximidos» y al 14, «y 31 símbolo(s) y archivo(s)
exigidos, todos en el árbol»; los dos enteros están en `EVIDENCIA/gates.json`. El `NN` del 13 es
cuántos módulos tiene tu `agente/`, así que lo imprime tu corrida: lo que hay que leer de esa línea
no es el número, es el **«sin eximidos»**.

**Si falla.** Cada hallazgo trae archivo y línea, y un `atribuible_a` que casi siempre dice `build`:
esto lo generaste vos en tu máquina, se arregla en tu árbol. `enviar/salida_de_mensajeria` y
`enviar/segundo_camino` no se negocian ni se silencian: mové la URL y el envío a
`agente/enviar.py`. Los dos ids que decidían por verbo —`enviar/salida_suelta` y
`enviar/salida_suelta_sin_verbo`— ya no existen; `grep -n salida_suelta scripts/auditar.py` no
imprime nada, así que un «Si falla» que te mande a buscarlos te manda a buscar un id que la
compuerta no puede emitir.

---

### Paso 4 · Los cinco que prueban que la compuerta prueba

**Objetivo.** El validador rechaza, la firma mira los bytes que llegaron, la suite corrió entera, y
cada campo del contrato o lo afirma un nodo o tiene escrito por qué no.

**Hacé esto.** Leé las líneas 16 a 19, y la 23.

**16 contrato** valida cada `pruebas/**/salida*.json` contra `contratos/salida.schema.json` y agrega
la regla que el esquema no puede decir: `pasos` trae `n` en `[1, 2, 3, 4, 5, 6]`, en ese orden. El
esquema fija seis elementos con `n` entre 1 y 6, no que sean distintos ni ordenados: seis pasos «1»
validan y no significan nada.

Y pregunta una cosa más, que no es sobre el contenido: **que atrás de esa salida haya una corrida
de este árbol**. `pruebas/salida-caso-01.json` lo escribe la fixture de sesión `salida_caso_01` de
`pruebas/conftest.py`, que arranca llamando al ciclo. Sin `agente/ciclo.py` esa fixture saltea, así
que una salida en un árbol sin build la dejó un editor —`contrato/salida_sin_corrida`—; y como la
fixture reescribe el archivo en **cada** corrida de la suite, una salida más vieja que el `.py` más
nuevo de `agente/` o de `pruebas/` no la escribió ninguna corrida del código que hay hoy
—`contrato/salida_vieja`, y se arregla corriendo `pytest pruebas -q` antes de la compuerta—. Lo que
**no** mira es si el documento coincide con `pruebas/fixtures/caso-01.salida-esperada.json`:
coincidir con la referencia es lo que hace un build correcto, y marcarlo premiaba al que se
apartaba de ella.

**17 contrato-control** muta **seis** veces una salida buena que vive adentro de `auditar.py` —no en
un archivo del proyecto, porque es el patrón contra el que se mide el validador mismo— y las seis
tienen que rebotar. Cinco las rechaza el esquema: falta un paso, `score` 101, una clave desconocida,
`estado` en `listo`, un paso con `n = 0`. La sexta —seis pasos con `n = 1`— la rechaza el auditor,
que es justamente la regla que el esquema no puede expresar. Y la salida buena, sin mutar, tiene que
pasar. Para qué: un validador mal cableado —el esquema que no carga, el `iter_errors` que nunca se
recorre, el `additionalProperties` perdido en una edición— hace pasar cualquier cosa, y el reporte
se ve idéntico al de una corrida que sí revisó. Sin esto, **«todo verde» no se distingue de «no se
está validando nada»**; por eso saltearlo ya mueve el veredicto a `parcial`.

**18 firmas** pregunta cuatro cosas por fixture: si la firma guardada se reproduce, si el cuerpo
correcto valida, si uno alterado rebota, y si el cuerpo **reserializado** valida —reserializar es
parsear el JSON y volver a escribirlo; ver `blueprint/00-contrato.md` § 10—. La cuarta es la que
importa: los `.raw` traen sangrías que no son múltiplos de nada, un tabulador y la misma vocal
escapada de dos formas, así que ninguna bandera de `json.dumps` devuelve esos bytes y una
implementación que reserialice **no puede** reproducir el MAC. Corre sobre los dos módulos que
firman —la plantilla y el `agente/firmas.py` copiado de ella—, así que con el build dice
`4 de 4 comprobación(es): 2 fixture(s) × 2 módulo(s)`, y antes de construir,
`2 de 2 comprobación(es): 2 fixture(s) × 1 módulo(s)`.

**19 pruebas** corre `pytest pruebas -q -rs` sin credenciales y con corte a los 120 s, y dos conductas
viven ahí y en ningún chequeo estático. El **dedupe** —descartar la entrega repetida; el proveedor
entrega al-menos-una-vez y reintenta hasta siete veces— y la idempotencia a la salida: ningún
análisis de árbol distingue un `INSERT ... ON CONFLICT DO NOTHING` de un `SELECT` seguido de un
`INSERT`, y sólo el primero aguanta dos reintentos concurrentes, así que el dedupe por
`X-Zernio-Event-Id` y la `Idempotency-Key` sacada del contenido se prueban acá o no se prueban. Y la
**ronda de Postgres**: con SQLite, la reescritura a `postgresql+asyncpg://` y el descarte de
`sslmode` nunca corren. Apuntá `DATABASE_URL` a un Postgres —escrito en `.env`, nunca por una tool
call— y corré la suite otra vez.

**23 censo-de-campos** pregunta lo que ninguno de los otros veintidós pregunta: no si el árbol está
bien armado, sino si **la suite afirma lo que el contrato declara**. Siete rondas seguidas
encontraron un campo declarado que ninguna prueba ataba a nada —`contacto.numero` en vacío,
`objecion_en_playbook` siempre en falso, `urgencia` fija en nulo—, y las siete veces la compuerta
dijo `PASS` con la suite entera en verde. Escribir la aserción que falta no cierra eso: la ronda
que viene aparecen tres campos más. Lo que lo cierra es preguntar por los que **no** están, igual
que hace el 14 con los módulos.

Cómo se establece que una prueba afirma un campo: **no por nombre y no leyendo la suite**. Se mide.
`.venv/bin/python scripts/auditar.py --censo` corre la suite entera una vez por campo con un solo
cambio en el documento que devuelve `correr_ciclo` —el valor de ese campo, y nada más— y mira si
algún nodo se pone rojo. El valor que inyecta **valida contra el mismo esquema**: otro miembro del
`enum`, otro entero adentro del rango, otra fecha con forma de fecha. Ahí está todo el asunto: una
prueba que sólo valida el documento contra `contratos/salida.schema.json` no se puede poner roja con
un mutante que valida, así que validar no cuenta como afirmar. Esa corrida deja
`EVIDENCIA/censo.json` y el chequeo 23 lo lee; **sin esa evidencia saltea**, y con `agente/` en el
árbol el salteo deja el veredicto en `parcial`. Por eso el paso 8 de `blueprint/40-pruebas.md` corre
el `--censo` entre el `pytest` y la compuerta.

Cuatro cosas del 23 que conviene saber antes de leer su línea:

- **La evidencia envejece sola y el chequeo lo dice.** `EVIDENCIA/censo.json` guarda un sha256 del
  contrato, de `agente/` y de `pruebas/`. Cualquiera de los tres que se mueva deja el censo viejo y
  el chequeo vuelve a saltear: un censo de antes de tu último cambio dice que alguien miró un
  código que ya no está.
- **Los campos que hoy no afirma nadie están escritos, no salteados.** Viven en la lista
  `SIN_ASERCION` de `scripts/auditar.py`, cada uno con quién lo afirmaría, con qué entrada y qué se
  pierde mientras tanto. Son deuda del kit —se cierran agregando nodos a `pruebas/`, y la fase 5 no
  agrega nodos—, y por eso no salen como error contra tu build. Están enumerados en `PENDIENTES.md`.
- **Un campo que salga rojo y no esté en esa lista sí es tuyo**: `censo/campo_sin_asercion` trae el
  valor que se inyectó y en cuántas salidas lo cambió. `censo/campo_sin_corpus` es el otro:
  el campo no existe en ninguna salida de la suite, así que lo que falta es la entrada que lo
  produce, no la aserción.
- **`censo/motivo_vencido` es aviso y no error.** Un campo que está en la lista y el censo encontró
  afirmado: alguien escribió la prueba y no sacó el renglón. Sacalo, o la lista pasa a ser una lista
  de cosas que ya no son ciertas.

**Tenés que ver.**

```
  [ok      ] 16 contrato           1 salida(s) válidas, con los seis pasos en orden
  [ok      ] 17 contrato-control   6/6 mutaciones rechazadas
  [ok      ] 18 firmas             4 de 4 comprobación(es): 2 fixture(s) × 2 módulo(s)
  [ok      ] 19 pruebas            NN passed in 1.4s · 0 salteados · piso: NN de 30
  [ok      ] 23 censo-de-campos    43 campos declarados: NN afirmados por una prueba que se pu
```

**Los `NN` no están escritos acá a propósito**, y son los únicos de estas cinco líneas que no lo
están: el del 19 es el total de la suite, lo imprime la corrida
—`.venv/bin/python -m pytest pruebas --collect-only -q | grep collected`— y crece cada vez que
alguien agrega un canal, un disparador o un archivo de pruebas; los del 23 son cuántos campos afirma
tu suite y cuántos quedan con el motivo escrito, y se mueven con la misma mano. Los demás números
sí van escritos porque los decide la compuerta y no la parametrización: una salida, seis
mutaciones, dos fixtures por dos módulos, y los 43 campos de `contratos/salida.schema.json`. La regla
entera, con por qué se eligió ésta y no que la compuerta compare enteros contra la prosa, está en
`blueprint/40-pruebas.md`, Paso 8, junto con el desglose por archivo.

El `piso: NN de 30` es lo que impide que la suite se apague sin que nada se ponga rojo: el 30 es
`PISO_DE_NODOS`, una constante de la compuerta y no un número que la corrida elija. Este mismo árbol
sin `agente/` y sin una sola credencial ya lo supera; con el build sólo puede subir.

Y la suite entera en verde en las dos rondas, la de SQLite y la de Postgres. Lo que no puede pasar
es que el total baje sin que alguien lo haya decidido: eso quiere decir que se perdió un archivo, y
la lista de los que tienen que estar está en el Paso 8 de `blueprint/40-pruebas.md`.

**Si falla.**

- **`control/mutacion_aceptada`.** Casi siempre un `additionalProperties: false` perdido o un `enum`
  aflojado a `type: string`. **`control/buena_rechazada`** es al revés: el esquema se apretó de más,
  o la salida esperada de `pruebas/caso-01.md` quedó vieja.
- **`contrato/salida_vieja`.** Corriste la compuerta sin correr la suite antes, o la corriste y
  después tocaste un `.py`. Es el orden del paso 8 de `blueprint/40-pruebas.md`: primero `pytest`,
  después el auditor. **`contrato/salida_sin_corrida`** es el otro: hay una salida en `pruebas/`
  y no hay `agente/ciclo.py`, así que no la escribió ninguna corrida.
- **`censo/campo_sin_asercion` o `censo/campo_sin_corpus` con un campo que no está en
  `SIN_ASERCION`.** Ése es tuyo: el censo le cambió el valor y la suite entera siguió verde. Escribí
  la aserción que falta. Si el campo **sí** está en la lista, es deuda del kit y no tenía que salir:
  mandalo, porque entonces la lista y el esquema dejaron de coincidir.
- **`firmas/reserializa`.** O el fixture perdió el espaciado torcido y quedó inerte, o estás
  firmando un `json.dumps` en vez del cuerpo. Las dos dan 401 en el 100% de las entregas reales.
- **`firmas/alterado_pasa`.** No hay `hmac.compare_digest`: es cualquiera escribiéndole a tu número.
- **`firmas/build_derivado`.** Es un aviso, no un error: no se ejecutó `agente/firmas.py` porque el
  manifiesto ya dijo que algún archivo generado se apartó de su plantilla. Copiala otra vez.
- **`Can't load plugin: sqlalchemy.dialects:postgres`.** La cadena entró sin normalizar; y
  **`connect() got an unexpected keyword argument 'sslmode'`** es la otra mitad, la que se olvida
  siempre: reescribiste el esquema y dejaste el parámetro.
- **No hay un Postgres a mano.** Decilo y anotalo en `PENDIENTES.md`: la compuerta no puede saber
  que esa ronda no corrió, porque el 07 es estático y queda verde igual.
- **Saltean por «falta jsonschema».** Es la condición exacta en la que su ausencia importa más, y es
  el Paso 1 otra vez: corriste con el Python del sistema.

---

### Paso 5 · Los diecisiete salteos que mueven el veredicto

**Objetivo.** Sabés cuáles salteos son legítimos y cuáles bajan el veredicto a `parcial`.

**Hacé esto.** Mirá `exigidos_sin_correr` en el resumen, o en `EVIDENCIA/gates.json`. Un salteado
nunca es un aprobado, pero no todos pesan igual: éstos son los diecisiete que, según el estado del
árbol, no tienen excusa. Las dos listas viven en `scripts/auditar.py`: `SIEMPRE_EXIGIBLES`, tres, y
`EXIGIBLES_CON_AGENTE`, catorce. Son ésas las que mandan: si no coinciden con esta tabla, gana el
archivo.

| Chequeo | Cuándo se exige | Por qué |
|---|---|---|
| `blueprint-existe` | **siempre** | sin una sola cita, o el kit dejó de ser este kit, o nadie miró |
| `contrato-control` | **siempre** | es el control negativo de la validación entera |
| `firmas` | **siempre** | los dos fixtures y la plantilla vienen en el clon: acá no hay fase que esperar |
| `deps-imports` | con `agente/` | un import sin pin es un `ModuleNotFoundError` en la máquina de quien clona |
| `deps-drivers` | con `agente/` | el driver que ningún import declara |
| `modelo` | con `agente/` | un modelo retirado no lo avisa ningún registro |
| `wire-schema` | con `agente/` | un esquema angosto que nunca se renderizó da 400 en la primera llamada |
| `http-unico` | con `agente/` | un cliente sin timeout cuelga el webhook |
| `enviar-unico` | con `agente/` | un segundo camino de salida se lleva el número del negocio |
| `agente-completo` | con `agente/` | saltea sólo sin `agente/`: si saltea con el build, reventó adentro |
| `cache-estatico` | con `agente/` | saltea si no encuentra el constructor del prompt, y eso hay que arreglarlo |
| `contrato` | con `agente/` | un contrato que nunca se validó es la corrida en la que menos hay que confiar |
| `pruebas` | con `agente/` | saltea sin `test_*.py` o sin pytest, y con el build eso es la suite entera sin correr |
| `playbook` | con `agente/` | lo escribe la fase 2: sin él con el build puesto, se salteó una fase entera |
| `panel-cerrado` | con `agente/` | saltea sólo sin `agente/`: con el build, o reventó adentro, o nadie miró si el panel está abierto |
| `rutas-del-contrato` | con `agente/` | tiene un salteo legítimo más —`agente/servidor.py` sin escribir, y ahí el 14 ya está rojo—; con el servidor puesto, un salteo quiere decir que nadie contó las rutas |
| `censo-de-campos` | con `agente/` | saltea cuando el censo no corrió, y un censo que no corrió es «nadie contó los campos del contrato». Se destraba con `--censo`, una vez |

Los otros seis pueden saltear sin mover el veredicto, y son los que ni siquiera saltean nunca en un
árbol sano: `manifiesto`, `railway-arranque`, `claudemd-tam`, `pines`, `secretos` y
`gitignore-anclado`. Leelos igual, que cada uno dice por qué salteó.

**Tenés que ver.** Con el build terminado, el `.venv` puesto y el `--censo` corrido, `0 salteados` y
`PASS`.

Antes de construir, con el `.venv` ya creado, `PASS` con **11 salteados**: los ocho del Paso 3, más
`contrato`, que todavía no tiene fixtures de salida, `playbook`, que espera la fase 2, y
`censo-de-campos`, que espera la corrida del `--censo`. Los once tienen su motivo escrito y ninguno
es exigible en un árbol sin `agente/`. Ese `pass` es legítimo y no quiere decir que el agente esté
listo: quiere decir que lo que hoy se podía mirar, se miró.

Terminada la fase 2 son **10**, porque `playbook` ya tiene qué mirar. Las dos corridas traen un
aviso, `pruebas/salteados_sin_build`, con la cuenta de nodos que esperan el build: en un árbol
recién clonado, `PASS · 0 errores · 1 aviso · 11 salteados`.

**Estos tres veredictos sí van escritos con el número exacto**, y son la excepción a lo que dice el
Paso 1 sobre los números de cada línea: no son conteos que crecen, son la condición de terminado.
Un salteado de más es un chequeo que no miró nada. Y el `11` de recién clonado viene subiendo de a
uno por ronda: era `8`, pasó a `9` cuando la compuerta sumó `21 panel-cerrado`, a `10` con
`22 rutas-del-contrato` y a `11` con `23 censo-de-campos`. Si en tu corrida ves otro número, mirá
primero cuántas líneas imprimió el reporte.

Si en vez de eso ves `PARCIAL` y tres salteos de más, no es el árbol: es el intérprete. Volvé al
Paso 1.

**Si falla.**

- **`parcial` con `cache-estatico` adentro.** El constructor del prompt no se llama `prompt` ni
  `sistema` ni `system`. Renombralo: el chequeo mira ahí y en ningún otro lado, y lo dice por
  pantalla en vez de fingir que revisó.
- **`parcial` con `blueprint-existe` adentro.** Ningún `SKILL.md`, ningún `CLAUDE.md` y ningún
  blueprint cita un archivo de `blueprint/`. O borraste las citas, o esto ya no es este kit.
- **`fail` y además una línea de `exigidos_sin_correr`.** Arreglar los errores de arriba no los
  vuelve verdes: esos chequeos tampoco miraron nada. Son dos trabajos.

---

### Paso 6 · Cuando queda roja y no se entiende por qué

**Objetivo.** Sabés si el defecto es del build, del entorno o del kit, sin adivinar.

**Hacé esto.** `.venv/bin/python scripts/auditar.py --json`, y leé `EVIDENCIA/gates.json`, que se
escribe pase o falle. En Windows, `.venv\Scripts\python.exe scripts\auditar.py --json`.

**Tenés que ver.** Un objeto con `veredicto`, `errores`, `avisos`, `salteados`,
`exigidos_sin_correr`, `construido`, `interprete`, `chequeos` y `hallazgos`. Cada hallazgo trae
`atribuible_a`: `build` es lo que se generó en tu máquina, `entorno` es tu Python o tu venv, y
**`kit` somos nosotros**. `interprete` te dice con cuál corrió, que es la mitad de los problemas de
este archivo.

**Si falla.**

- **`auditoria/excepcion`.** Un chequeo levantó una excepción: es un defecto de
  `scripts/auditar.py`, no de lo que miraba. El resto del reporte sirve igual.
- **El hallazgo dice `kit`.** No lo arregles en tu copia: abrí un issue en
  `github.com/Hainrixz/whatsapp-closer-agentkit` con el bloque `hallazgos` de tu `gates.json` —sacá
  antes cualquier cadena de conexión— y la versión de Python que usaste.
- **Verde acá y roto contra Meta.** Es lo esperado: la compuerta no abre un socket. Lo que queda
  por cerrar a mano está en `PENDIENTES.md`.

Con `pass`, y sólo con `pass`, seguís a `/publicar`.

**Próximo archivo:** `blueprint/50-despliegue.md`, que pone el servicio en una URL pública y da de
alta el webhook. No se entra ahí con `parcial`.
