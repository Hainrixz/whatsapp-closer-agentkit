# 34 · El CRM

**Fase 4.** Entrás con los seis pasos escritos; salís con la tabla `leads` y el paso 5 escribiendo
en ella.

El paso 5 escribe en la base: **el default es `borrador`** —el modo en que los pasos que escriben
redactan, muestran y esperan confirmación explícita; ver `blueprint/00-contrato.md` § 10—. Muestra
las columnas que va a tocar y espera. Sin confirmación, `crm.escrito` queda en falso y el paso, en
`sin-confirmar`. Pasar a `automatico` lo decide quien instala, nunca el agente.

**Invariante 3** —un invariante es una de las seis reglas de `CLAUDE.md` que ningún archivo puede
romper, cada una con su chequeo en la compuerta `scripts/auditar.py`; ver
`blueprint/00-contrato.md` § 10—: el camino de Supabase es HTTP y sale por `agente/http.py`, con
`timeout=`. **Invariante 4:** acá se nombran `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`; los valores
los escribe quien instala en `.env`. Nada de este archivo pasa por `enviar()`: el CRM no es una
persona.

---

### Paso 1 · Creá la tabla `leads`

**Objetivo.** Existe una tabla indexada por `contacto_id`, con las seis etapas del contrato.

**Hacé esto.** Supabase → SQL Editor → Run. Contra un Postgres propio, `psql -f`.

```sql
create table if not exists leads (
  contacto_id        text primary key,
  numero             text,
  nombre             text,
  etapa              text not null default 'nuevo'
    check (etapa in ('nuevo','calificado','agendado','cerrado','perdido','escalado')),
  score              integer check (score between 0 and 100),
  temperatura        text check (temperatura in ('caliente','tibio','frio')),
  resumen            text,
  proximo_paso       text,
  proximo_paso_fecha date,
  cita_evento_id     text,
  dueno              text,    -- lo escribe una persona. El agente no lo toca nunca.
  notas              text,    -- idem.
  creado_en          timestamptz not null default now(),
  actualizado_en     timestamptz not null default now()
);
create index if not exists leads_etapa_idx  on leads (etapa, actualizado_en desc);
create index if not exists leads_numero_idx on leads (numero);
alter table leads enable row level security;
```

**La clave es `contacto_id` —el `businessScopedUserId`, el identificador que el proveedor le da a un
contacto dentro de tu negocio; ver `blueprint/00-contrato.md` § 10— y no el número:** el teléfono
puede venir nulo y no es estable, así que lleva índice y nunca `unique`. Las etapas van como `check`
y no como `enum`, que se cambia con un `alter type` y una migración. Sin políticas, el RLS —las
políticas de fila de Postgres, § 10 otra vez— deja la tabla invisible para la clave `anon`; la
`service_role` las saltea, y por eso es la que va en `.env`.

**Tenés que ver.** `Success. No rows returned`, y la tabla en el Table Editor.

**Si falla.**

- **`relation "leads" already exists`.** Lo cubren los `if not exists`. Si le falta una columna,
  `alter table leads add column if not exists ...`. No la borres: tiene filas.
- **`type "timestamptz" does not exist`.** Le diste este DDL a SQLite. En local la tabla la crea
  `migrar()` de `agente/base.py` con los tipos del dialecto.
- **La tabla existe y el paso 5 no deja fila.** Estás con la `anon`: el `insert` vuelve 403 con
  `42501` y el `select` devuelve `[]`. Las dos cosas se leen como "no está".

---

### Paso 2 · Verificá las dos formas de la URL de la base

**Objetivo.** La cadena que te da el proveedor arranca sin editarla a mano, y el recordatorio del
archivo 33 sabe de antemano si puede existir.

**Hacé esto.** No escribas nada acá: las dos funciones ya están en `agente/base.py` desde la fase 3,
y el bloque de código vive en `blueprint/30-generacion.md`, en el paso de `base.py` —está ahí para
que el módulo quede entero antes de que alguien lo importe—. Lo que le toca a este archivo es
verificarlas, y las dos juntas: el jobstore de `blueprint/33-agenda.md` ya usó la síncrona, y el
upsert del Paso 3 va a usar la otra.

| Función | Devuelve | `sslmode` y compañía |
|---|---|---|
| `normalizar_url(cruda)` | `postgresql+asyncpg://…` · `sqlite+aiosqlite:///./wca.db` | los descarta |
| `url_sincrona(cruda)` | `sqlite:///./wca.db` · con Postgres levanta `RecordatorioSinDriver` | los conserva |

**Son dos y no una.** `normalizar_url()` es la del proyecto: el motor de SQLAlchemy es async y pide
`+asyncpg` o `+aiosqlite`. `url_sincrona()` existe para un solo cliente, el jobstore de APScheduler
del archivo 33, que es síncrono y revienta con una URL async. Unificarlas rompe uno de los dos
caminos, siempre: la decisión y la tabla completa están en `blueprint/00-contrato.md` § 8.

`postgres://` es lo que entregan Railway y Supabase, y SQLAlchemy no lo carga desde la 1.4. Ese
arreglo lo hacen las dos. **El que las separa es el otro:** `sslmode`, `channel_binding`,
`target_session_attrs` y `gssencmode` son palabras clave de libpq, viajan en la misma cadena y
asyncpg las recibe como argumento de `connect()`, así que `normalizar_url()` las descarta —si el
servidor exige TLS, va aparte en `connect_args={"ssl": "require"}`—. El camino síncrono es libpq
puro: ahí `sslmode=require` se entiende, y sacarlo sería quitarle el TLS a la conexión sin decírselo
a nadie. Hoy eso no se llega a ver con Postgres, porque antes levanta `RecordatorioSinDriver`; la
regla está escrita para el día que se fije el driver, y para que nadie las «unifique» de paso.

**Tenés que ver.** Las dos formas, y la excepción declarada:

```bash
.venv/bin/python -c "from agente.base import normalizar_url as n; print(n('postgres://u:p@h:5432/db?sslmode=require'))"
.venv/bin/python -c "from agente.base import url_sincrona as s; print(s('sqlite:///./wca.db'))"
```

```
postgresql+asyncpg://u:p@h:5432/db
sqlite:///./wca.db
```

```bash
.venv/bin/python -c "
from agente.base import RecordatorioSinDriver, url_sincrona
try: url_sincrona('postgres://u:p@h:5432/db?sslmode=require')
except RecordatorioSinDriver: print('RecordatorioSinDriver, que es lo que corresponde hoy')"
```

```
RecordatorioSinDriver, que es lo que corresponde hoy
```

**Y esas tres líneas también las corre la suite, que es lo que hace que no se puedan «unificar» un
martes.** `pruebas/test_camino_feliz.py::test_recordatorio_las_dos_formas_de_la_url_de_la_base`
afirma las cuatro salidas de la tabla y la excepción, y no espera al paso 4: `agente/base.py`
existe desde la fase 3, así que ese nodo corre desde ahí. Hasta esta ronda los tres comandos de
arriba eran prosa —los corría quien construía, una vez, mirando la pantalla— y la decisión de
`blueprint/00-contrato.md` § 8 no tenía una sola aserción atrás. Medido sobre un árbol de prueba:
con `url_sincrona()` devolviendo lo mismo que `normalizar_url()`, y con `normalizar_url()` sin
descartar `sslmode`, ese nodo se pone rojo y ningún otro de la suite se mueve.

**Si falla.**

- **`Can't load plugin: sqlalchemy.dialects:postgres`.** La cadena entró sin normalizar.
- **`connect() got an unexpected keyword argument 'sslmode'`.** Reescribiste el esquema y dejaste el
  parámetro. Es la mitad que se olvida siempre, y la descarta `normalizar_url()`.
- **`ImportError: cannot import name 'url_sincrona'`.** `agente/base.py` quedó con una sola función.
  Volvé al paso de `base.py` de `blueprint/30-generacion.md`: son dos, por § 8.
- **`url_sincrona()` devuelve una URL de Postgres en vez de levantar.** Alguien fijó un driver
  síncrono por su cuenta. Si está verificado contra PyPI y anotado en `PINES.md`, está bien y el
  recordatorio del archivo 33 deja de estar detenido; si no está en `PINES.md`, `deps-imports` lo
  marca y con razón.
- **`ModuleNotFoundError: No module named 'asyncpg'`.** Otro `requirements.txt`. `asyncpg` no está en
  ningún `import`: el chequeo `deps-drivers` busca `+(\w+)://` justo por esto.
- **`unable to open database file`.** Tres barras es relativo y cuatro absoluto; en el contenedor el
  proceso corre sin privilegios y solo escribe en `/app`.

---

### Paso 3 · Escribí el upsert que no pisa lo que escribió una persona

**Objetivo.** El paso 5 agrega y actualiza la fila del contacto con un upsert —un `insert` que, si
la fila ya está, actualiza en vez de fallar; ver `blueprint/00-contrato.md` § 10—. No borra ni
reordena nada.

**Hacé esto.** En `agente/integraciones/crm.py`, un `insert` con su lista de columnas y este
`on conflict`:

```sql
on conflict (contacto_id) do update set
  numero             = coalesce(excluded.numero, leads.numero),
  etapa              = excluded.etapa,
  resumen            = excluded.resumen,
  proximo_paso       = coalesce(excluded.proximo_paso, leads.proximo_paso),
  proximo_paso_fecha = coalesce(excluded.proximo_paso_fecha, leads.proximo_paso_fecha),
  score              = excluded.score,
  temperatura        = excluded.temperatura,
  actualizado_en     = now();
```

Por PostgREST es lo mismo con otra letra —`POST /rest/v1/leads?on_conflict=contacto_id` con
`Prefer: resolution=merge-duplicates`— y ahí **la clave que el paso no calculó no va en el cuerpo**:
PostgREST arma el `set` con las que le mandás, así que una clave en nulo pisa y una ausente deja
quieto. `creado_en`, `dueno` y `notas` quedan afuera a propósito: la primera es la fecha del primer
contacto, y las otras dos las escribe una persona. Nunca un `delete` y después un `insert`.

**Con `SUPABASE_URL` puesta, este camino es HTTP y sale por el cliente único**, así que es el que
la suite dobla y el que se puede afirmar sin una base de verdad:
`pruebas/test_camino_feliz.py::test_crm_escrito_solo_si_la_fila_se_escribio` mira la petición que
vio el transporte y exige las cuatro cosas de arriba —la ruta `/rest/v1/leads`, el
`on_conflict=contacto_id`, el `Prefer` con `merge-duplicates` y la fila con `contacto_id` adentro—
más las tres columnas que **no** pueden viajar. Sin esa última mitad, mandar la fila entera es el
daño que no se ve: la tabla sigue andando y el vendedor asignado desapareció.

**Tenés que ver.** Escribí `pruebas/upsert_manual.py`: dos `guardar()` sobre el mismo
`contacto_id`, la segunda con el número en nulo y otra etapa, y después leé la fila.

```bash
.venv/bin/python -m pruebas.upsert_manual
```

```
1 fila · etapa=agendado · numero=5215500000000 · creado_en sin cambios
```

**Si falla.**

- **`no unique or exclusion constraint matching the ON CONFLICT specification`** (42P10). Falta el
  `primary key`. Sin restricción no hay upsert: hay dos filas.
- **El número quedó nulo.** Pusiste `excluded.numero` sin `coalesce`. El contacto que escribe con
  nombre de usuario te borra el teléfono que ya tenías.
- **`dueno` y `notas` vacías.** Mandaste la fila entera. Es el daño que no se ve: la tabla sigue
  andando y el vendedor asignado desapareció.
- **`no such function: now` (SQLite).** Ahí es `current_timestamp`. Que la columna la maneje
  SQLAlchemy con `onupdate=`, no un literal en el SQL.

---

### Paso 4 · Verificá el resumen de tres líneas por código

**Objetivo.** Ningún resumen con la conversación pegada llega a la base.

**Hacé esto.** El modelo escribe el resumen; el código decide si se escribe.

```python
def verificar_resumen(texto: str) -> list[str]:
    lineas = [l.strip() for l in (texto or "").splitlines() if l.strip()]
    if len(lineas) != 3:
        raise ResumenFueraDeForma(f"{len(lineas)} líneas, tienen que ser tres")
    if any(len(l) > 200 for l in lineas):
        raise ResumenFueraDeForma("una línea pasa de 200 caracteres")
    return lineas
```

Tres líneas y en este orden: qué quería, qué se le respondió, qué falta. **No se trunca:** cortar a
tres se lleva la tercera, la única que dice qué hacer mañana. Cuando no cumple, el paso 5 queda
`fallado` con el motivo, la fila no se escribe y el borrador se queda en la bandeja. Es la aserción
5 y la verifica el código, no una instrucción al modelo: un prompt que pide tres líneas las da casi
siempre, y "casi siempre" acá es una conversación de cuarenta mensajes adentro de una celda. El
resumen lo lee el negocio, no el contacto: va en voseo, no en el tratamiento de la entrevista.

**Tenés que ver.** Con tres renglones devuelve una lista de tres. Con la conversación entera pegada,
`ResumenFueraDeForma`.

**Si falla.**

- **Levanta siempre.** El modelo separa con `. ` y no con saltos. Se verifica acá y se pide en el
  esquema angosto de `agente/wire_schema.py`: las dos cosas, no una.
- **Pasa un párrafo de una sola línea.** Cambiaste el `!=` por un `>`.
- **Da cuatro con un resumen que se ve bien.** Hay un salto adentro de una línea; los renglones en
  blanco ya los descarta el filtro.

---

### Paso 5 · Sin `SUPABASE_URL`, devolvé la fila y no la escribas

**Objetivo.** Sin credencial el ciclo sigue y la fila no se pierde.

**Hacé esto.** Armá la fila igual, no la escribas, devolvela en `crm` con `escrito` en falso, dejá
el paso en `fallado` con el motivo y el `estado` de la salida en `parcial`. Y mostrala tal cual:

```
Paso 5 · CRM — no escrito

  SUPABASE_URL está vacía. La fila quedó armada y no se guardó en ningún lado.

  contacto_id         bsu_01HZK3M9QX7T2VW4
  etapa               calificado
  resumen             Preguntó el precio del curso y dijo que le parece caro.
                      Se le respondió con la objeción de precio del playbook y tres horarios.
                      Falta que elija uno.
  proximo_paso        Confirmar horario
  proximo_paso_fecha  2026-03-03

  Copiala a mano, o poné SUPABASE_URL y SUPABASE_SERVICE_KEY en `.env` y volvé a correr el
  paso 5 desde `/bandeja`. Se arma igual: no se pierde nada.
```

**Tenés que ver.** Esas líneas y el paso 5 en `fallado`.

**Y una tercera rama, que no es ésta y se le parece: el servicio contesta y dice que no.** Sin
credencial no hay llamada; con la clave `anon` la hay, vuelve 403 con `42501` y la fila tampoco
queda. Las dos terminan igual —`escrito` en falso, paso 5 `fallado` con el motivo, la fila
devuelta— y por un camino distinto, así que se escriben las dos. **`escrito` lo decide la
respuesta del servicio y nunca el código que armó el diccionario**, que es la frase que ya estaba
abajo en «Si falla» y que hasta esta ronda no afirmaba nadie: un paso 5 con `escrito = True`
puesto a mano pasaba la suite entera con la compuerta en `pass`.

Las tres las corre `pruebas/test_camino_feliz.py::test_crm_escrito_solo_si_la_fila_se_escribio`,
con la misma entrada y el mismo modo, cambiando sólo lo que pasa del otro lado del cable:

| Del otro lado | `crm.escrito` | Paso 5 | La fila |
|---|---|---|---|
| 201, la fila entró | verdadero | `hecho` | escrita, y el transporte la vio |
| 403 `42501`, RLS la rechaza | falso | `fallado` con el motivo | armada y devuelta en `crm` |
| sin `SUPABASE_URL` | falso | `fallado` con el motivo | armada y devuelta, y cero llamadas |

**Acá todavía no hay suite que correr.** Las pruebas ya están escritas en el árbol —las tres ramas
de arriba viven en `pruebas/test_camino_feliz.py` y la del paso 5 sin confirmar en
`pruebas/test_caso_01.py`—, pero la fase que las corre es la que viene, `blueprint/40-pruebas.md`.
Y hay dos números de pytest en el kit, que son distintos y se confunden. Estos:

| Comando | Cierra en | Dónde se verifica |
|---|---|---|
| `.venv/bin/python -m pytest pruebas/test_caso_01.py -q` | los nodos que suma la tabla del paso 4, que los imprime `--collect-only -q` | `blueprint/40-pruebas.md`, paso 4 |
| `.venv/bin/python -m pytest pruebas -q` | la suite entera; el total sale de `--collect-only -q` | `blueprint/40-pruebas.md`, paso 8, y el chequeo 19 |

Que esta rama sin credencial no rompa la suite se comprueba ahí, no acá: el caso corre sin ninguna
credencial a propósito.

**Si falla.**

- **El paso 5 dice `hecho`.** Reporta el armado como escritura. `escrito` lo decide la respuesta del
  servicio, no el código que armó el diccionario.
- **`crm` en nulo.** Nulo significa "el paso 5 no corrió". Acá corrió y no pudo escribir, y la
  diferencia es la fila que alguien tiene que copiar.
- **`'NoneType' object is not subscriptable`.** Estás armando la fila desde el número; el fixture de
  Zernio lo trae nulo justo para esto. Se arma desde `contacto_id`.

---

## Qué quedó hecho

`leads` con las seis etapas y la clave en `contacto_id`. Las dos formas de la URL verificadas: la
async del proyecto y la síncrona del jobstore, que con Postgres levanta `RecordatorioSinDriver` a
propósito. Un upsert que no toca `creado_en`, `dueno` ni `notas`. El resumen verificado por código.
Y el camino sin credencial, que devuelve la fila en vez de perderla.

Las cuatro cosas de este archivo que la suite mira, para que no haga falta buscarlas: las dos
formas de la URL y su excepción, la forma de la petición del upsert, las tres columnas que no
viajan, y `crm.escrito` atado a la respuesta del servicio. Están en
`pruebas/test_camino_feliz.py`, que es el archivo que corre el camino que **sí** pasa; el que no
pasa —sin confirmación no se escribe la fila— sigue en `pruebas/test_caso_01.py`.

Anotalo en `.wca-estado.json`: `fase` en `crm` y el sha256 de cada archivo escrito.

**Próximo archivo:** `blueprint/35-panel-api.md`, que levanta `agente/servidor.py` con sus diez
rutas y deja la bandeja detrás del token.
