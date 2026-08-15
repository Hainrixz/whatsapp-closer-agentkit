# 40 · Las pruebas

**Fase 5.** Entrás con `agente/` construido; salís con la suite en verde y el simulador corrido.

Nada de acá pide una credencial. Los casos corren sin `${WHATSAPP_TOKEN}`, sin
`${GOOGLE_CALENDAR_ID}` y sin `${SUPABASE_URL}`, a propósito: lo que se mide es la llamada que el
agente prepara, no la respuesta del servicio.

Tres piezas. Una función pura `correr_ciclo()` sobre SQLite en memoria, sin FastAPI y sin red. Un
modelo **inyectado**, que también sabe devolver salida mala. Y el simulador, que es donde alguien
mira la pantalla y decide si esto sale a atender clientes.

Si venís de `/probar` y la suite ya está verde, andá al Paso 7.

---

### Paso 1 · Extraé el fixture de la prosa

**Objetivo.** El JSON de `caso-01.md` vive en un archivo que el código lee, y un chequeo impide que
los dos deriven.

**Hacé esto.** `pruebas/extraer_fixture.py` lee `pruebas/<caso>.md`, toma la primera cerca de JSON
del archivo —la de **Entrada.**— y con `--escribir` la guarda en
`pruebas/fixtures/<caso>.entrada.json`. Sin bandera compara y sale 1 si difieren; `--verificar` es la
forma explícita de lo mismo. El caso es un argumento posicional y por defecto es `caso-01`.

Escribe **verbatim**, nunca con `json.dumps`: el bloque sale al fixture byte por byte, que es por qué
`caso-01.entrada.json` conserva el espaciado compacto del `.md`. Y compara por `json.loads` de los
dos lados: igualdad de objeto, no de bytes. Es el único lugar del kit donde comparar significados es
lo correcto; los `.raw` de esa misma carpeta son lo contrario y no se regeneran nunca con
`json.dumps`. Ver `pruebas/fixtures/README.md`.

Dos casos tienen prosa y fixture, así que se corre dos veces:

```bash
.venv/bin/python -m pruebas.extraer_fixture --escribir
.venv/bin/python -m pruebas.extraer_fixture && echo FIXTURE-AL-DIA
.venv/bin/python -m pruebas.extraer_fixture caso-02 --verificar
```

**Tenés que ver.**

```
escrito pruebas/fixtures/caso-01.entrada.json
caso-01: la prosa y el fixture dicen lo mismo
FIXTURE-AL-DIA
caso-02: la prosa y el fixture dicen lo mismo
```

`caso-02.md` embebe la entrada del enojo, que es la de `caso-02.entrada.json`. Las otras dos
—`caso-02b` y `caso-02c`— son ese mismo objeto con otro `mensaje` y no tienen prosa propia, así que
el extractor no las mira.

**Si falla.**

- `no encontré un bloque json en caso-01.md`: alguien movió el bloque o cambió el cercado. Si movés
  el bloque, movés el extractor; no lo dejes buscando a ciegas.
- `difieren en 'modo': la prosa dice … y el fixture dice …`, o en cualquier otra clave: decidí cuál
  manda y actualizá el otro. Editar los dos a la vez es cómo se pierde la referencia.
- `falta pruebas/fixtures/caso-01.entrada.json`: corriste la comparación antes que la escritura.
- `No module named pruebas.extraer_fixture`: falta `pruebas/__init__.py`, o estás fuera de la raíz.
- Windows: `.venv\Scripts\python.exe -m pruebas.extraer_fixture`. Vale para todo lo que sigue.

---

### Paso 2 · `correr_ciclo`, la función pura

**Objetivo.** Los seis pasos corren de punta a punta sin FastAPI, sin red y sin credenciales, y
devuelven el objeto del contrato.

**Hacé esto.** En `agente/ciclo.py`:

```python
async def correr_ciclo(entrada: dict, *, modelo, deps) -> dict:
```

`modelo` es cualquier objeto con el método que usa `agente/modelo.py`. `deps` trae base, calendario,
CRM y aviso interno. Nada de adentro construye un cliente ni lee `os.environ`.

**Qué es «ahora» para un ciclo: el reloj de la máquina, leído una vez arriba de todo.**
`correr_ciclo()` lo lee al empezar —`datetime.now(timezone.utc)`—, lo guarda y lo baja por
parámetro a todo lo que decide con la hora: `enviar(…, ahora=ahora)`, `marcar_baja(id, ahora)`,
`anotar_saliente(id, hash, ahora)` y el recordatorio del paso 4. Una sola lectura por turno: dos
lecturas del mismo ciclo pueden caer una de cada lado de la ventana, y ahí el motivo que queda
escrito no explica nada.

**`mensaje.recibido_en` no es el reloj.** Es cuándo llegó el mensaje: el extremo desde el que se
cuenta la ventana de 24 horas, no el instante contra el que se compara. Las dos lecturas son
razonables y hasta esta ronda ninguna estaba escrita: cinco construcciones del kit leyeron los
mismos archivos, cuatro tomaron `recibido_en` como «ahora» y una tomó el reloj. Las cuatro pasaron
la suite, la quinta se llevó una tanda de nodos en rojo, y ninguno de esos rojos era un defecto
suyo.

**Por qué gana el reloj**, en orden de peso:

1. **Con `recibido_en` la guarda de la ventana no se puede negar nunca.** La cuenta queda
   `recibido_en < recibido_en + 24 h`, que es verdadera siempre. Una guarda que no puede decir que
   no, no es una guarda, y ésta es de las que cuidan el número del negocio.
2. **El ciclo se retoma a mano, y eso está escrito.** `CLAUDE.md`, en «Cómo se dispara»: «también
   se invoca a mano para retomar una conversación desde la etapa escrita en el CRM». Ahí no entra
   ningún mensaje nuevo y `recibido_en` es el de cuando llegó: con la otra lectura, un chat de
   anteayer se contesta en texto libre y del otro lado eso es un `131047`.
3. **La entrega tarde es lo normal, no la rareza.** El proveedor entrega al-menos-una-vez y
   reintenta hasta siete veces, y después de una caída la cola se vacía con `recibido_en` viejos.
   La misma falla, sin que nadie haya retomado nada a mano.
4. **El árbol ya lo decía en el único lugar donde alguien lo pensó.**
   `pruebas/test_camino_feliz.py`, en `entrada_para_agendar()`: «`recibido_en` se pone en el
   momento de la corrida y no se deja el del fixture: la ventana de 24 horas se cuenta desde el
   último entrante, y con un mensaje de marzo de 2026 la confirmación del paso 4 no puede salir por
   más que el build esté bien». Esa frase sólo es cierta con el reloj de la máquina; con la otra
   lectura, esa línea y `proximos_horarios()` son dos mecanismos que no hacen nada.

**Lo que cuesta, y quién lo paga.** Con el reloj de la máquina los fixtures envejecen: el corpus
está fechado el 2 de marzo de 2026 y cualquier otro día los cuatro historiales quedan fuera de
ventana, así que un build **correcto** no manda nada y todo lo que cuente envíos desde el ciclo da
cero. **Lo paga la suite y no los fixtures.** `pruebas/conftest.py` para el reloj de la sesión
entera en el instante del corpus con `freeze_time`, y ese instante sale del disco —el
`mensaje.recibido_en` del caso 01— y no de un literal escrito en la prosa. Los fixtures se quedan
byte por byte como están, que es lo que `pruebas/extraer_fixture.py` compara contra
`pruebas/caso-01.md` y `caso-02.md`: con fechas relativas adentro, la prosa y el fixture no pueden
volver a decir lo mismo.

Dos cosas de esa fixture que no se ven leyéndola, las dos medidas en esta máquina con
freezegun 1.5.5 y Python 3.14.6:

- **`real_asyncio=True` no es adorno.** El arnés corre los turnos adentro de un `asyncio.run`, y
  bajo un reloj congelado el reloj de asyncio también se congela: una espera con plazo no vence
  nunca. Medido, con `asyncio.run()` sobre un `asyncio.wait_for(asyncio.sleep(0.05), timeout=0.5)`:
  sin la bandera sigue corriendo a los 8 segundos y hay que matarlo; con la bandera vuelve en los
  0,05 de siempre. **La suite no falla, se cuelga**, y la compuerta la corta a los 120 segundos con
  `pruebas/colgadas`, que es un hallazgo que no nombra ni el reloj ni la fixture.
- **Va con `scope="session"`.** Una fixture de sesión se arma antes que cualquiera de función, así
  que un `freeze_time` por prueba dejaría afuera a `salida_caso_01` —que también es de sesión y es
  la que corre el ciclo del caso 01—, y esa salida es justo la que el chequeo 16 valida.

Que el reloj esté parado de verdad lo afirma un nodo y no un comentario:
`pruebas/test_enviar.py::test_la_suite_corre_parada_en_el_instante_del_corpus`, que corre sin build.
Y la dirección que esta decisión habilita —la ventana **cerrada** vista desde el ciclo, que con la
otra lectura no existe— la afirma `test_ventana_el_ciclo_retomado_un_dia_despues_no_contesta_libre`,
que para el reloj 25 horas después sin tocar el fixture.

**El punto de reinicio es `deps`, y hay que escribirlo.** La base es `sqlite+aiosqlite://` sin
archivo —en memoria, con `StaticPool`— y se migra **por prueba**. Eso no pasa solo: en todo el
camino de `correr_ciclo` no hay una llamada a `migrar()`, y el arnés no la hace. Lo que el arnés
llama, una vez por prueba, es `armar_deps()`, y antes de armar el suyo lo busca en dos lugares
—`agente.ciclo.armar_deps` primero, `agente.base.armar_deps` después, con `transporte=` e
`historial=` por nombre—. Escribí una de las dos, y que las cuatro cosas queden así:

1. **Un engine nuevo por llamada, colgado de `deps`.** Lo que no puede pasar es que dos `deps`
   compartan uno: ése es el que arrastra filas de una prueba a la siguiente.
2. **Ese engine además queda como el motor en curso de `agente/base.py`.** Es la mitad que hasta
   ahora no estaba escrita en ningún lado, y sin ella los dos archivos se contradicen:
   `blueprint/31-proveedores.md` paso 1 escribe `from agente.base import anotar_saliente,
   conversacion, marcar_baja` a nivel de módulo y **`enviar()` no recibe `deps`**. O sea que en cada
   ciclo hay dos lectores de la base —el que entra por `deps` y el que entra por ese import—, y si
   el segundo sigue mirando el engine de la aplicación, la prueba corre contra dos bases. Se mide
   así, sacando el reemplazo de un build entero: la verificación de acá abajo termina en
   `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: contactos`, siempre
   en el mismo nodo y en todas las corridas.
   `agente/base.py` guarda ese motor en curso y expone cómo reemplazarlo —en el build medido,
   `armar_motor(url)`, `usar_motor(engine)` y `motor()`—. Ese archivo lo escribe
   `blueprint/30-generacion.md` (§ 4 del contrato): si tu `base.py` no trae el reemplazo, va ahí,
   al lado de `migrar(engine=None)`, que ya lleva el engine por parámetro por este mismo motivo.
3. **`correr_ciclo()` migra el engine que vino en `deps`**, antes de tocar una tabla y una sola vez
   por `deps` —una bandera en el objeto alcanza—. `migrar(engine=None)` recibe ese engine; sin
   argumento sigue siendo el de la aplicación, que es como lo llaman las fases 3 y 4.
4. **El reinicio cae entre pruebas, no entre turnos.** `correr_turnos()` arma un `deps` y corre
   todos los turnos adentro del mismo `asyncio.run`: por eso el segundo turno de caso-02 sabe del
   primero, y por eso caso-01 sigue viendo un contacto nuevo.

**Del punto 3, la trampa que ocho corridas de pytest no encuentran.** Si en vez de la bandera en el
objeto llevás un registro de los motores ya migrados, va `weakref.WeakSet` y **nunca** un `set[int]`
de `id(engine)`. Un revisor lo escribió con `id()`, la compuerta se lo marcó y la suite se lo pasó
igual, ocho veces seguidas. CPython reusa las direcciones: en cuanto el `deps` de la prueba anterior
muere, el motor de la siguiente puede caer en la misma, y ahí un motor **nuevo** se lee como «ya
migrado». Nadie lo migra, y la primera tabla que se toque contesta
`sqlite3.OperationalError: no such table: contactos`. En el build donde apareció fue el motor #28 de
400.

Medido en esta máquina, creando y descartando engines de `sqlite+aiosqlite://` uno por vez, sin
nada más adentro:

```
Python 3.14.6 · SQLAlchemy 2.0.52
200 motores creados y descartados, uno por vez
  set[int] con id():  174 id() distintos · 26 falsos «ya migrado» · el primero en el #42
  weakref.WeakSet:      0 vivos          ·  0 falsos «ya migrado»
```

Tres corridas seguidas del mismo script dieron 171, 179 y 174 id() distintos, y el primer choque en
el motor #38, #29 y #42. Por eso no hay un número para comparar: lo que se lee es que no es cero y
que se mueve solo. Un `id()` identifica mientras el objeto está vivo, y este registro lo guarda
justo para después de que deja de estarlo. `WeakSet` guarda el objeto y suelta la entrada cuando
muere, que es exactamente la pregunta que se está haciendo; los cero vivos de la segunda línea son
eso, y no un registro que no anotó nada.

Sin ese punto, un engine migrado una vez y compartido arrastra las filas de una prueba a la
siguiente **y la suite puede salir verde igual**: cada prueba de caso-02 vuelve a sembrar su
historial y tapa la fuga. Se paga después, como una prueba que pasa sola y falla en la suite —o al
revés—, y ahí ya no hay forma de saber cuál la rompió. Medido: con el reemplazo sacado y un
`wca.db` de una corrida anterior en el árbol, la suite entera cae en **un solo nodo**,
`test_1_el_contacto_es_nuevo_y_se_indexa_por_contacto_id`, en `contacto["nuevo"] is True`. Uno solo,
que es lo que la hace difícil de leer.

El webhook —el aviso automático que el proveedor le manda a tu servidor cuando entra un mensaje; ver
`blueprint/00-contrato.md` § 10— es un adaptador delgado encima: verifica la firma sobre el **cuerpo
crudo** —los bytes exactos que llegaron, antes de parsearlos—, deduplica por id de evento, contesta
2xx y recién ahí llama a esto. Se prueba aparte y no vuelve a probar los seis pasos: eso ya está
escrito en el árbol, en `pruebas/test_firmas.py` —la firma y el alta— y en
`pruebas/test_idempotencia.py` —el dedupe a la entrada y la `Idempotency-Key` a la salida—. Los dos
saltean con el motivo escrito hasta que exista `agente/servidor.py`. No hace falta que agregues un
archivo nuevo; si tu adaptador necesita más, va ahí.

**Invariante 3: un solo cliente HTTP, con `timeout=` explícito.** `deps` no es la puerta para un
segundo. **Invariante 2: todo lo que sale pasa por un solo `enviar()`.** Los dobles no reemplazan
`enviar()`: envuelven el transporte que `enviar()` usa, así la ventana de 24 h, el chequeo de baneo y
la regla de no escribir primero corren enteras en cada prueba que manda algo.

**Que corran no es que alguien las mire.** Son dos afirmaciones distintas, y el chequeo 13
`enviar-unico` de la compuerta sólo hace la primera: prueba que hay **una sola puerta**, no que la
puerta mire algo. Las tres guardas las afirma **`pruebas/test_enviar.py`**, cada una en
las dos direcciones —que muerda cuando tiene que morder, y que no corte de más cuando el build hace
lo correcto—. Llama a `enviar()` de frente, con `ahora` por parámetro, que es justo para lo que ese
parámetro existe: sin él la ventana no se puede probar sin esperar 24 horas. Los instantes y el
estado de la conversación salen de `window_expires_at`, `baja_en` y `salientes_seguidos` de los
historiales de `pruebas/fixtures/`, así que no dependen del reloj de la máquina. Los tres nodos de
ese archivo que sí corren el ciclo —el ciclo no recibe `ahora`— dependen del reloj y por eso está
la fixture de sesión que lo para; ver acá arriba. Sin ese archivo, un
build que escribe fuera de la ventana —o a quien pidió la baja, o a quien nunca escribió— pasa la
suite entera con la compuerta en verde, y lo que se pierde no es una respuesta: es el número de
WhatsApp del negocio. Cuántos nodos son lo imprime
`.venv/bin/python -m pytest pruebas/test_enviar.py --collect-only -q`, y por qué ese número no está
escrito acá, el Paso 8.

**Tenés que ver.**

```bash
.venv/bin/python -c "import inspect, agente.ciclo as c
print(inspect.signature(c.correr_ciclo, eval_str=True))"
grep -rn "AsyncClient(\|httpx\." agente/ciclo.py
```

La primera línea imprime `(entrada: dict, *, modelo, deps) -> dict`. El grep no imprime nada.

**El `eval_str=True` no es adorno, y es la tercera ronda que se cae.** Todo módulo del árbol abre
con `from __future__ import annotations` —`blueprint/00-contrato.md` § 4—, así que en runtime las
anotaciones son cadenas y `inspect.signature()` las imprime entre comillas. Medido en esta máquina,
con Python 3.14.6, sobre esa misma firma:

```
(entrada: 'dict', *, modelo, deps) -> 'dict'      inspect.signature(f)
(entrada: dict, *, modelo, deps) -> dict          inspect.signature(f, eval_str=True)
```

Sin la bandera, un build **correcto** imprime la primera y no coincide con la línea que este paso
manda esperar: la media hora que sigue se va en buscar un defecto que no existe. Lo que no se hace
es sacarle el `from __future__` a `agente/ciclo.py` para que la firma imprima linda: deja un módulo
con otra regla que los demás, y el que hereda el árbol tiene que descubrir cuál era.

Y el punto de reinicio, que es lo único de este paso que no se ve leyendo el archivo. Dos ciclos con
dos `deps`, la misma entrada, y el segundo tiene que llegar a una base vacía:

```bash
.venv/bin/python - <<'PY'
import asyncio

import agente.ciclo as ciclo
from pruebas.proveedor_falso import ProveedorFalso, StubModel, armar_deps, cargar

entrada = cargar("caso-01.entrada.json")

def un_ciclo():
    async def _correr():
        deps = armar_deps(ProveedorFalso())
        return await ciclo.correr_ciclo(entrada, modelo=StubModel.canonica(), deps=deps)
    return asyncio.run(_correr())

for n in (1, 2):
    c = un_ciclo()["contacto"]
    print(f"ciclo {n}: nuevo={c['nuevo']} mensajes_previos={c['mensajes_previos']}")
PY
```

```
ciclo 1: nuevo=True mensajes_previos=0
ciclo 2: nuevo=True mensajes_previos=0
```

**Las dos líneas iguales son el punto.** Con el engine colgado del módulo, el segundo ciclo lee lo
que dejó el primero y sale `ciclo 2: nuevo=False mensajes_previos=1`: eso es la fuga, medida en un
comando y antes de que la tape el historial sembrado de caso-02.

Antes de que exista `agente/ciclo.py` los tres comandos terminan en
`ModuleNotFoundError: No module named 'agente'` —el segundo, en `No such file or directory`—. Eso es
lo correcto en el kit sin construir, y es lo mismo que dice el motivo con el que saltea la suite.

**Si falla.**

- La firma sale `(entrada: 'dict', *, modelo, deps) -> 'dict'`, con las comillas: te faltó
  `eval_str=True`. El build está bien; el comando, no.
- `sqlite3.OperationalError: no such table`: la base en memoria muere al cerrarse la conexión. Un solo
  engine por prueba, con `StaticPool`.
- `ciclo 2: nuevo=False mensajes_previos=1`: el mismo engine sobrevivió a los dos `deps`. Construilo
  adentro de `armar_deps()`, uno por llamada. No lo tapes borrando filas al final de cada prueba:
  eso es limpiar, no reiniciar, y se olvida en la primera tabla que alguien agregue.
- **`sqlite3.OperationalError: no such table: contactos`, siempre en el mismo nodo y en todas las
  corridas**: el engine nuevo se colgó de `deps` y no se dejó como el motor en curso de
  `agente/base.py`. El ciclo migró el de `deps` y los pasos leyeron el de la aplicación. Es el
  punto 2 de arriba.
- **El mismo `no such table: contactos`, en un nodo distinto cada vez y no siempre.** Ése no es el
  punto 2: es el registro de motores migrados escrito con `id(engine)`. Volvé a correr y va a caer
  en otro lado, o no caer. `weakref.WeakSet`, y el párrafo de arriba tiene la medición.
- **Lo que separa a esos dos es que uno se repite y el otro se mueve, y no un archivo en la raíz.**
  Este archivo mandaba mirar si aparecía un `wca.db`, y ese síntoma dejó de distinguir: **aparece
  igual en un build sano**, porque hay más de un nodo que levanta la base sin `DATABASE_URL` puesta
  y ahí la URL por defecto es `sqlite:///./wca.db`. Encima `.gitignore` trae `*.db`, así que el
  archivo no pone nada en rojo y nadie se entera de que está. En esta ronda se sacó de esa cuenta
  el que era de este kit: la fixture `mandar` de `pruebas/test_enviar.py` llamaba a `migrar()`
  antes de `armar_deps()` y migraba el motor de la aplicación —ahora es al revés—. Lo que queda es
  del build, y es normal: correlo dos veces y mirá si cae en el mismo nodo.
- `TypeError: armar_deps() got an unexpected keyword argument 'transporte'`: tu fábrica tiene otra
  firma. El arnés la llama con `transporte=` e `historial=`, y eso se decide en un solo lugar,
  `pruebas/proveedor_falso.py`.
- El ciclo pide una variable de entorno: sacala de ahí y pasala por `deps`.
- `RuntimeError: no running event loop`: falta `@pytest.mark.asyncio`, o `asyncio_mode` en la
  configuración de pytest-asyncio.
- El grep imprime algo: hay un cliente adentro del ciclo. Importá el de `agente/http.py`; lo mira el
  chequeo `http-unico`.

---

### Paso 3 · El modelo se inyecta, y también miente a pedido

**Objetivo.** Las pruebas corren sin llamar a la API, y existe la forma de devolver salida
deliberadamente mala.

**Hacé esto.** Nada: ya está escrito, en `pruebas/proveedor_falso.py`. **El archivo no se llama
`dobles.py`**, y ahí adentro viven las tres piezas del arnés: `ProveedorFalso` —el transporte—,
`StubModel` —el modelo— y `armar_deps()` —el único lugar de la suite que decide la forma de `deps`—.
Lo que te toca acá es leerlo y, si tu build aterriza con otra forma de `deps`, corregirlo ahí y en
ningún otro archivo.

`StubModel` devuelve lo que valida contra `agente/wire_schema.py`, que son **once campos y ninguno
más**, en este orden:

```
intencion  score  presupuesto  presupuesto_evidencia  urgencia  motivo
texto  objecion_detectada  resumen  proximo_paso  proximo_paso_fecha
```

El campo es `objecion_detectada`, no `objecion`; ver `blueprint/00-contrato.md` § 10. El esquema
angosto no tiene `pasos`, ni `estado`, ni `enviado`, ni `escrito`, ni `cita`, ni `handoff`, ni
`horarios_ofrecidos`, ni `temperatura`: lo que no se pregunta no se puede mentir. Esa lista está
anclada en `CAMPOS_WIRE`, arriba de todo del mismo archivo.

Se inyecta, no se mockea por HTTP. Interceptar el transporte deja adentro el SDK, el reintento y el
formato de la respuesta, y ninguna de las tres es lo que estas pruebas afirman. `caso-01.md` excluye
«el texto exacto que redacta el modelo»: afirmarlo es atarse a una versión del modelo y romper la
suite el día que se sube el pin.

**«Exacto» y «que venga del modelo» son dos cosas, y sólo la primera está excluida.** Sin la
segunda, un build que descarta `wire["texto"]` y manda una línea enlatada pasa la suite entera y en
producción le contesta lo mismo a todos los contactos. La procedencia se afirma sin afirmar el
contenido: `test_3_en_borrador_y_sin_confirmar_redacta_y_no_manda` inyecta
`StubModel.otro_texto(TEXTO_DEL_STUB)`, con una marca reconocible adentro de la frase, y exige que
esa marca aparezca en lo redactado. No compara los textos, no mide el largo y no mira ninguna
palabra que el modelo haya elegido.

**Seis salidas sin argumentos, y cinco son malas a propósito:**

```python
StubModel.canonica()                        # la del camino feliz
StubModel.presupuesto_inventado()           # 15000, y el mensaje no trae ninguna cifra
StubModel.presupuesto_con_evidencia_falsa() # 15000, y cita una frase que no está en el mensaje
StubModel.resumen_largo()                   # cinco párrafos, la conversación entera pegada
StubModel.objecion_fabricada()              # una objeción que no está en el playbook
StubModel.callado()                         # `texto` en nulo, para los caminos donde no se escribe
```

Y una séptima que no es una salida fija sino una fábrica, porque necesita el monto y la cita:

```python
StubModel.presupuesto_con_evidencia_real(90000, "Tengo 90000 para invertir")
```

Es la otra mitad de la guarda del presupuesto, y hace falta: sin ella, un build que devuelva
`presupuesto` en nulo **siempre** pasaría la prueba del presupuesto inventado sin verificar nada.

Las malas existen para probar que las verificaciones del código muerden. `anclar_presupuesto()` exige
una subcadena literal del mensaje con cifras adentro —las dos puertas, `presupuesto_inventado` sin
evidencia y `presupuesto_con_evidencia_falsa` con una evidencia que no está—, y sin eso fuerza nulo y
escribe el descarte en `motivo`. El resumen se corta en tres líneas. La objeción se busca exacta
contra `playbook.objeciones`, y si no está, `objecion_en_playbook` queda en falso y se la nombra sin
responderla.

**Tenés que ver.** Las que anclan esto hoy, con sus nombres reales:

```bash
.venv/bin/python -m pytest pruebas/test_contrato.py -q -k stub_validan
.venv/bin/python -m pytest pruebas/test_caso_01.py::test_2_un_presupuesto_sin_evidencia_en_el_mensaje_se_fuerza_a_nulo -v
```

```
pruebas/test_contrato.py::test_las_salidas_del_stub_validan_contra_el_esquema_angosto PASSED
pruebas/test_caso_01.py::test_2_un_presupuesto_sin_evidencia_en_el_mensaje_se_fuerza_a_nulo PASSED
```

La primera recorre las seis salidas, las valida contra el golden y exige que cada una emita los once
campos exactos. Corre siempre, con o sin build. La segunda es la única prueba de **conducta** de las
tres guardas: inyecta `presupuesto_inventado()`, exige el nulo con el descarte escrito, y después
inyecta `presupuesto_con_evidencia_real()` y exige que el monto sobreviva. Saltea con el motivo
escrito hasta que exista `agente/ciclo.py`.

**Lo que hoy no está anclado, y va dicho en voz alta.** `resumen_largo()`, `objecion_fabricada()` y
`callado()` existen y validan contra el esquema angosto, pero ninguna prueba las inyecta en el ciclo.
Hay dos aserciones cerca que parecen cubrir el corte del resumen y no lo hacen:
`test_5_sin_confirmacion_no_se_escribe_la_fila` y
`test_el_resumen_del_crm_resume_y_no_devuelve_el_agravio` cuentan las líneas de lo que salió, pero con
la salida canónica adentro, que ya viene con tres. Ninguna puede ponerse roja por un recorte que no
recorta. Está anotado en `PENDIENTES.md` con la forma exacta de las tres pruebas que faltan; son las
primeras que conviene agregar cuando el ciclo ya esté construido.

**Si falla.**

- Una prueba pasa sin hacer nada: estás inyectando el stub canónico. Comentá una verificación una vez
  y comprobá que su prueba se pone roja. Una prueba que no puede fallar no prueba.
- `presupuesto` sale 15000: falta el ancla. **Invariante 5**: lo que no está en el mensaje ni en el
  catálogo, no existe.
- El stub no valida contra el esquema angosto: la referencia es `agente/wire_schema.golden.json`, y si
  cambió lo dice el chequeo `wire-schema`. Mientras no exista el build se mide contra
  `plantillas/contratos/wire_schema.golden.json`, que es la fuente.
- `armar_deps()` levanta `TypeError` nombrando un parámetro: el build aterrizó con otra forma de
  `deps`. Se corrige en `pruebas/proveedor_falso.py` y en ningún otro lado.

---

### Paso 4 · Las seis aserciones de caso-01

**Objetivo.** `pruebas/test_caso_01.py` afirma una cosa por paso, y ninguna más.

**Hacé esto.** Nada: ya está escrito. Es una función por aserción, con el número de paso adelante en
el nombre, y la entrada sale del fixture del Paso 1 y nunca de un literal pegado.

**Son seis aserciones y no son seis funciones**, y conviene saber por qué antes de contar. Una
aserción se afirma en más de una función cuando tiene dos mitades que se rompen por separado, y una
función se parametriza cuando la misma afirmación tiene varias formas de fallar:

| Paso | Función | Nodos |
|---|---|---|
| 1 | `test_1_el_contacto_es_nuevo_y_se_indexa_por_contacto_id` | 1 |
| 1 | `test_1_un_audio_sin_forma_de_conseguir_los_bytes_se_detiene_con_el_motivo` | 3 |
| 2 | `test_2_el_score_va_de_0_a_100_y_la_temperatura_sigue_a_los_umbrales` | 1 |
| 2 | `test_2_un_presupuesto_sin_evidencia_en_el_mensaje_se_fuerza_a_nulo` | 1 |
| 3 | `test_3_en_borrador_y_sin_confirmar_redacta_y_no_manda` | 1 |
| 3 | `test_3_ofrece_exactamente_tres_horarios_y_todos_salen_de_disponibilidad` | 1 |
| 4 | `test_4_sin_confirmacion_no_hay_cita` | 1 |
| 5 | `test_5_sin_confirmacion_no_se_escribe_la_fila` | 1 |
| 6 | `test_6_no_escala_y_la_salida_valida_con_estado_parcial` | 1 |

Nueve funciones, y los nodos son la suma de la columna. Los tres del paso 1 son las tres formas de
no conseguir los bytes de un audio —sin `media_id` ni `media_url`, un `media_url` caducado, y un
`media_id` cuya bajada devuelve 400—, y las tres frenan igual. La otra mitad de la aserción 6
—cambiar el texto por uno que pida un humano y ver que escala— no está acá: vive en
`pruebas/test_caso_02.py`, con los tres disparadores y en los dos modos. Repetirla acá daría dos
verdes por una sola conducta probada.

Se afirma: contacto indexado por `contacto_id`, con `nuevo` en verdadero y `mensajes_previos` en
cero; `score` de 0 a 100 con `temperatura` coherente y `presupuesto` en nulo; `respuesta.enviado` en
falso con tres horarios que están todos en `disponibilidad`; `cita` en nulo y el paso 4 en
`sin-confirmar`; `crm.escrito` en falso; `handoff` en nulo; `estado` en `parcial`. Y que lo
redactado **venga** del modelo, por la marca que el stub le puso adentro.

No se afirma: el texto del modelo —ni su forma, ni su largo, ni una palabra suya—, los tiempos de
ejecución y cualquier cosa que dependa de una credencial real.

El objeto devuelto se escribe en `pruebas/salida-caso-01.json`, y no lo escribe una prueba: lo escribe
el fixture `salida_caso_01` de `pruebas/conftest.py`, que corre el ciclo una sola vez para las nueve
funciones. El chequeo 16 `contrato` lo valida contra `contratos/salida.schema.json` y además exige
`pasos` con `n` de 1 a 6 en orden, que es la regla que el esquema no puede expresar.

```bash
.venv/bin/python -m pytest pruebas/test_caso_01.py -q
.venv/bin/python -m pytest pruebas/test_caso_01.py --collect-only -q | grep collected
```

**Tenés que ver.** Todo en verde, y ni un nodo más **en ese archivo**: lo que imprime el segundo
comando tiene que ser la suma de la columna «Nodos» de la tabla de arriba, y esa suma es la única
forma escrita de este total. El `grep collected` está porque la última línea de `--collect-only -q`
es la vacía, y un `tail -1` a secas no imprime nada. Si contás funciones son nueve, si contás pasos
son seis, y si contás lo que pytest reporta es la columna sumada. Las tres cuentas salen de la misma
tabla, y si la tercera no cierra, alguien parametrizó una función y no vino a escribirlo acá.

Sin `agente/ciclo.py` en el árbol —o sea, si todavía no corriste las fases 3 y 4— el primer comando
saltea el archivo entero y `pytest -rs` imprime el motivo: `falta el build: no existe
agente/__init__.py, agente/ciclo.py`. Un salteado con motivo no es un aprobado, y se lee distinto de
una prueba vacía. La suite entera es más grande y la contás en el Paso 8.

**Si falla.**

- Cae la 3 por un horario que no está en `disponibilidad`: el paso lo inventó. Acotá a la lista.
  Ofrecer un hueco inventado es fallo aunque el mensaje esté perfecto.
- Cae la 1 con `KeyError: 'numero'`: estás indexando por teléfono. `zernio.raw` trae `phoneNumber`
  nulo y `businessScopedUserId` con valor justamente por esto. Ver S12 en `SUPUESTOS.md`.
- Cae la 3 o la 5 porque algo salió o se escribió: el modo es `borrador` y `confirmado` es falso. Un
  envío sin confirmación es fallo aunque el texto esté bien.
- `contrato/pasos_desordenados`: alguien filtró, reordenó o hizo `append`. Los seis se presiembran en
  `agente/salida.py`; ver `blueprint/30-generacion.md`, paso 6.

---

### Paso 5 · caso-02, el camino del enojo

**Objetivo.** Con el agente autorizado a mandar, la escalación lo calla: sale exactamente un mensaje,
y ninguno después.

**Hacé esto.** Nada: `pruebas/caso-02.md` y `pruebas/test_caso_02.py` ya están en el árbol, y los
fixtures también. **Los fixtures no llevan el disparador en el nombre** —los nombres que este archivo
citaba y no existen están en `blueprint/00-contrato.md` § 11—: son tres entradas numeradas con su
historial al lado, porque el enojo es el tercer mensaje de una conversación y no el primero. Un caso
del enojo que arranque como primer mensaje deja de probar lo que existe para probar.

| Disparador | Entrada | Historial | `handoff.motivo` |
|---|---|---|---|
| enojo | `caso-02.entrada.json` | `caso-02.historial.json` | `enojo` |
| precio | `caso-02b.entrada.json` | `caso-02b.historial.json` | `precio_fuera_de_rango` |
| palabra | `caso-02c.entrada.json` | `caso-02c.historial.json` | `palabra_clave` |

**Los tres se evalúan en un orden fijo y se para en el primero que da: 1 `palabra_clave`,
2 `precio_fuera_de_rango`, 3 `enojo`.** Hasta esta ronda ese orden no estaba escrito en ningún
archivo del kit, y por eso va acá con el motivo al lado.

**Por qué no lo atrapaba nadie.** Los tres fixtures no chocan: el del enojo no trae ninguna palabra
de la lista —«Una porquería de servicio», y `palabras_escalacion` es `humano`, `persona real`,
`reclamo`, `abogado`, `estafa`, `cancelar`—, el de precio no está enojado y el de la palabra no
nombra ningún monto. O sea que el orden no lo ejerce ninguna prueba:
`test_escala_con_el_motivo_que_corresponde` da verde con cualquiera de los seis órdenes posibles, y
`test_los_tres_disparadores_son_distintos` sólo pide tres distintos. Medido en dos builds del mismo
blueprint: el mensaje sugerido del cliente 2 del simulador —«ya van tres veces que pregunto lo
mismo, son unos estafadores»— dispara los dos a la vez, porque `estafa` está en la lista y el
insulto está en el texto; uno escaló como `palabra_clave` y el otro como `enojo`, los dos con la
compuerta en verde. Cada build imprime una pantalla distinta ahí.

**El criterio es de lo literal a lo inferido**, y no es una preferencia de estilo. `palabras_escalacion`
la escribe quien instala —Q8 de `blueprint/20-entrevista.md`— y `handoff.motivo` es lo que enruta la
conversación del otro lado. Un negocio que puso «abogado» en la lista para que las amenazas legales
lleguen a quien corresponde las ve llegar como `enojo` si el enojo gana, porque una amenaza legal
casi siempre viene enojada: la configuración queda tapada justo en el caso para el que se escribió.
Al revés se pierde menos —`enojo` es el atrapa-todo, y el `disparador` sigue trayendo la palabra que
lo activó, así que el que abre el chat ve el insulto igual—. `precio_fuera_de_rango` va segundo por
lo mismo: un monto leído del mensaje es más literal que un tono, y menos literal que un pedido
explícito del contacto.

**El `enum` de `contratos/salida.schema.json` no es una precedencia.** Ahí los tres valores están en
el orden `enojo`, `precio_fuera_de_rango`, `palabra_clave`, que es el orden en que se escribieron y
no dice nada de cuál gana. Leerlo como precedencia es el camino más corto al `enojo` primero.

**Y `handoff.disparador`, con `motivo` en `palabra_clave`, trae la palabra de `palabras_escalacion`
que dio, no el token que tipeó el contacto**: «estafa» y no «estafadores». La lista es la
configuración, y quien lee la escalación quiere saber cuál de sus reglas se activó: «estafa» apunta
a un renglón que puede editar, «estafadores» no apunta a nada. Con el monto es al revés y ya estaba
escrito así —el disparador trae el número que vino en el mensaje—, porque el rango no tiene un
renglón que nombrar. Las dos formas siguen pasando `test_el_disparador_dice_que_lo_activo`, que pide
`humano` adentro del disparador y lo encuentra en las dos: por eso hacía falta decidirlo acá.

**Dónde vive en el código, y qué falta.** El cuerpo del paso 6 lo escribe `blueprint/32-multimodal.md`
en su paso de cierre, y ahí los tres disparadores están enumerados sin orden —«enojo, un precio fuera
de `rango_precio` y una palabra de `palabras_escalacion`»—, que es de donde sale la mitad del
problema. La regla la fija este archivo, que es el que decide qué afirma `pruebas/test_caso_02.py`, y
lo que le falta a `32-multimodal.md` es una línea que remita acá en vez de volver a enumerarlos: es
suyo y no se tocó en esta ronda.

**En código el orden todavía no está afirmado**, y tampoco se afirmó acá: la prueba que falta es un
cuarto fixture con el mensaje que dispara los dos —el del cliente 2— y una sola aserción,
`handoff.motivo == "palabra_clave"` con `disparador` conteniendo `estafa`. Es lo primero que hay que
agregarle a `pruebas/test_caso_02.py`; mientras no esté, esta prosa es lo único que lo sostiene, y
un build que evalúe al revés sale verde.

**Corre en `automatico`, no en `borrador`.** En `borrador` esta prueba no prueba nada: no sale nada en
ningún caso, y el verde es idéntico con el paso 6 roto. El punto es que la escalación calle al agente
**aun cuando está autorizado a mandar**. Los tres fixtures traen `modo` en `automatico`, y las pruebas
lo parametrizan sobre los dos: el de `automatico` es el que muerde, el de `borrador` ancla S11.

Y una decisión que `caso-02.md` deja escrita porque se lee al revés del 01: **el paso 4 queda en
`salteado`, no en `sin-confirmar`.** `sin-confirmar` quiere decir «te estoy esperando», y acá no va a
pasar nunca: la conversación ya salió del agente y nadie va a confirmar un horario que nunca se
ofreció. Esperar algo que no va a pasar deja la bandeja llena de pendientes que nadie puede cerrar.

Las aserciones, por fixture: `handoff.motivo` con el disparador que corresponde, `handoff.disparador`
con lo que lo activó, `crm.etapa` en `escalado`, `estado` en `escalado`, y el aviso al canal interno
con número, motivo y enlace al chat. Y la que atrapa el bug: **exactamente un mensaje saliente**.
Contá los envíos que vio el doble de transporte, no los que el agente dice que hizo.

**El aviso interno también se cuenta, y también es exactamente uno.** «Los mismos en los dos modos»
no alcanza: `2 == 2` es cierto, y lo que se ve del otro lado es el canal de escalaciones con cada
aviso duplicado. Van dos cuentas, una por modo, y las dos dicen uno.

**La variable del aviso la pone un fixture, y no es una credencial.** El paso 6 avisa sólo con
`SLACK_WEBHOOK_URL` puesta: sin ella, estas aserciones cuentan cero avisos contra un build que hace
todo bien, y el archivo entero deja de medir lo que dice medir. La suite la inyecta con una URL
inventada —`https://hooks.slack.com/services/T00000000TEST/B00000000TEST/pruebas-sin-credencial`—
que nunca sale del proceso, porque el transporte está doblado y el aviso se reconoce por el host.
Sigue siendo cierto que nada de acá pide una credencial. Y con el fixture en la mano queda probada
la otra mitad, que antes no la afirmaba nadie: **sin la variable, el paso 6 va a `fallado` con el
motivo y el `handoff` igual queda escrito en la salida.** Ver `S09` en `SUPUESTOS.md`.

Y `crm.resumen` no puede traer nada de lo que escribió el contacto, **ni de este turno ni del
historial**. Las dos fuentes, porque son dos: el insulto del turno está en `mensaje.texto` y el de
antes está en `conversacion.ultimo_entrante` y en `mensajes`. Un build que arme el resumen
arrastrando el historial no toca `mensaje.texto` ni una vez. Lo que la prueba busca no está escrito
a mano: se lee de los dos fixtures, así que cambiar el fixture cambia la aserción.

Después, la que sólo se puede probar en dos turnos: **el silencio posterior.** Se manda un cuarto
mensaje del contacto y se vuelve a correr el ciclo. Cero envíos nuevos, ni para despedirse.

**El estado de escalación se lee de la conversación, no del CRM.** No es una preferencia: la fila
del CRM la escribe el paso 5, que en `borrador` no escribe nada —`crm.escrito` en falso—, y este
silencio se exige en los **dos** modos. Un ciclo que pregunte por la etapa `escalado` de la tabla
`leads` contesta de nuevo en `borrador` y calla sólo en `automatico`, o sea que falla justo en el
modo que trae puesto el kit. Va en la conversación, que es de este proceso: el paso 6 la marca
cuando escala —instante, motivo y disparador— y el paso 1 del turno siguiente la lee y deja el 3 en
`salteado` con el motivo escrito. `crm.etapa` sigue diciendo `escalado` y se sigue afirmando: es lo
que el CRM va a mostrar cuando se escriba, no la memoria entre turnos.

Eso suma tres columnas a `conversaciones`, y esa tabla la escribe `blueprint/30-generacion.md`
(§ 4 del contrato): si tu `agente/base.py` no las trae, van ahí, al lado de las cuatro que ya
existen para las guardas de `enviar()`.

```bash
.venv/bin/python -m pytest pruebas/test_caso_02.py -q
.venv/bin/python -m pytest pruebas/test_caso_02.py --collect-only -q | sed 's/\[.*//' | sort -u
```

**Tenés que ver.** Doce funciones, diez parametrizadas sobre los tres disparadores y los dos modos
o los dos canales, y dos sin parametrizar. El segundo comando imprime la lista sin la
parametrización, y el total le queda arriba porque el `sort` lo pone primero:

```
NN tests collected in 0.00s
pruebas/test_caso_02.py::test_con_el_canal_interno_por_whatsapp_el_aviso_no_se_cuenta_como_envio
pruebas/test_caso_02.py::test_el_aviso_interno_no_depende_del_modo
pruebas/test_caso_02.py::test_el_aviso_por_slack_sale_a_la_url_que_trae_la_variable
pruebas/test_caso_02.py::test_el_crm_queda_en_escalado
pruebas/test_caso_02.py::test_el_cuarto_mensaje_despues_de_escalar_no_agrega_envios
pruebas/test_caso_02.py::test_el_disparador_dice_que_lo_activo
pruebas/test_caso_02.py::test_el_fixture_del_enojo_trae_el_agravio_en_las_dos_fuentes
pruebas/test_caso_02.py::test_el_resumen_del_crm_resume_y_no_devuelve_el_agravio
pruebas/test_caso_02.py::test_escala_con_el_motivo_que_corresponde
pruebas/test_caso_02.py::test_los_tres_disparadores_son_distintos
pruebas/test_caso_02.py::test_sale_un_mensaje_en_automatico_y_ninguno_en_borrador
pruebas/test_caso_02.py::test_sin_la_variable_de_slack_el_paso_6_queda_fallado_con_el_motivo
```

**El `NN` es lo único de ese bloque que no está escrito acá, y es a propósito.** Lo
imprime la corrida —la última línea de `--collect-only -q`, que el `sort` de este comando deja
arriba— y crece cada vez que alguien agrega un disparador o un canal. Las doce funciones sí van
escritas: ésas las decide este archivo, y una que aparezca o desaparezca de la lista es un cambio
que alguien tomó. La regla entera y por qué se eligió están en el Paso 8.

Sin `agente/ciclo.py` saltean todos menos uno, con el motivo escrito. **El que no es
`test_el_fixture_del_enojo_trae_el_agravio_en_las_dos_fuentes`**, y corre siempre a propósito: no
toca el build, mira los dos fixtures del enojo y afirma que el historial trae un agravio que el
mensaje del turno no trae. Es lo que avisa —barato, sin build, con el motivo escrito— cuando el
fixture y la aserción del resumen dejaron de decir lo mismo. Por eso el salteo de este archivo no va
en un `pytestmark` de módulo: lo pone la fixture `correr`, una prueba a la vez.

Dos que no son obvias por el nombre. `test_el_aviso_interno_no_depende_del_modo` corre por los **dos
canales** que permite `contratos/entrada.schema.json` —un canal de Slack, o un número interno de
WhatsApp cuando no hay Slack—, y el segundo sale por el mismo `/messages` que el mensaje al contacto:
si el doble de transporte corta por ruta, ese aviso se cuenta como envío y el conteo del mensaje único
da dos. Y `test_el_resumen_del_crm_resume_y_no_devuelve_el_agravio` exige que la fila diga qué pasó y
no cómo lo dijo: ni el mensaje de este turno ni nada del historial se copian al CRM, ni pegados
enteros ni por la palabra suelta con la que agredió.

**Si falla.**

- Salen dos mensajes: el paso 3 redactó y mandó, y recién después corrió el 6. La escalación se decide
  antes de redactar, no después.
- El segundo turno contesta: el ciclo no está leyendo la escalación de la conversación. Sin memoria
  entre turnos el silencio no se sostiene, y ése es el bug que este caso existe para atrapar.
- **El segundo turno calla en `automatico` y contesta en `borrador`.** Lo estás leyendo del CRM, y
  en `borrador` esa fila no se escribió. Va en la conversación; es el párrafo de arriba.
- Los tres escalan con el mismo `handoff.disparador`: lo dejaste fijo. Tiene que traer la palabra
  encontrada, o el monto que quedó fuera del rango.
- **La suite da verde y el cliente 2 del simulador escala como `enojo`.** No es un defecto del
  fixture: es un mensaje que dispara dos reglas y tu build las evalúa en otro orden. El orden es
  `palabra_clave`, `precio_fuera_de_rango`, `enojo`, y está arriba con el motivo.
- El de precio no escala: `rango_precio` vino nulo, y con nulo ese disparador queda apagado a
  propósito. Ponelo en el fixture.
- Corriste en `borrador` y dio verde: no probaste nada. Mirá el `modo` de los tres fixtures.
- Con el canal interno en un número de WhatsApp salen dos: el doble de transporte está cortando por
  ruta y ese aviso viaja por el mismo `/messages`. El corte tiene que ser por destino —el host, y
  después el destinatario que el cuerpo declara—, no por el camino. Es lo que mide
  `test_con_el_canal_interno_por_whatsapp_el_aviso_no_se_cuenta_como_envio`.
- Con el aviso por `SLACK_WEBHOOK_URL` salen cero, y el mensaje del fallo acusa al build de no
  avisar cuando avisó. Dos causas, y se miran en este orden. Una: el fixture no puso la variable, y
  entonces el build hizo lo correcto —paso 6 `fallado` con el motivo— y la aserción está midiendo
  otra cosa. Otra: el doble está buscando el nombre del canal adentro de la llamada y ahí no está.
  Un webhook entrante de Slack se postea a `hooks.slack.com` con `{"text": …}` y el canal viaja
  adentro de la URL secreta —`env.example`: «cada webhook queda atado a un canal»—. Ese aviso se
  reconoce por el host, que es lo único que hay. Ver `SUPUESTOS.md` S09 y
  `blueprint/32-multimodal.md` paso 5.

---

### Paso 6 · S11, la línea de handoff no saltea el borrador

**Objetivo.** La política queda escrita, con su contrapunto, y anclada por una prueba.

**Hacé esto.** El mensaje que le avisa al contacto que lo sigue una persona es un envío como
cualquier otro. En `borrador` queda redactado esperando confirmación, igual que el del paso 3. No
tiene vía rápida, y no se pierde nada: el aviso al canal interno no es un envío al contacto, sale
siempre, así que el humano se entera igual.

El contrapunto va escrito al lado, porque es bueno. Un operador razonable quiere lo contrario: con la
bandeja cerrada, el contacto enojado se queda sin ninguna respuesta hasta que alguien abra el chat, y
el silencio frente a un reclamo también es una respuesta, peor que la línea. Quien decide eso es el
negocio. Elegimos el default que se deshace con una línea de configuración y no el que se descubre
con un cliente.

```bash
grep -n "^## S11" SUPUESTOS.md
.venv/bin/python -m pytest pruebas/test_caso_02.py -k borrador -q
```

Si el `grep` no devuelve nada, escribí S11 con los cuatro tiempos de ese archivo —qué asumí, por qué,
dónde vive, cómo se corrige— más el contrapunto de arriba. Hoy está escrito y el `grep` lo encuentra.

**Tenés que ver.** El `grep` imprime una línea, con el número que tenga el archivo ese día:

```
193:## S11 · La línea de handoff del paso 6 no saltea la compuerta de `borrador`
```

**No hay ninguna prueba dedicada al handoff en borrador**, y el nombre que este archivo le inventaba
está en `blueprint/00-contrato.md` § 11. La conducta la ancla la mitad `borrador` de
`test_sale_un_mensaje_en_automatico_y_ninguno_en_borrador`, que en esa rama exige tres cosas juntas:
cero envíos en el transporte, `respuesta` no nula con texto adentro, y `respuesta.enviado` en falso.
Las tres, porque «cero envíos» sola también daría verde con el paso 6 sin redactar nada.

Y del `pytest`, casi la mitad de los nodos del archivo seleccionados y la otra mitad deseleccionada
—en verde con el build, y salteados con el motivo escrito en un árbol sin `agente/`, que es lo mismo
que hace el archivo entero—. Los dos números los imprime la corrida. Ojo con esa cuenta, porque el
filtro no es el que
parece: **`-k borrador` no selecciona sólo los nodos de ese modo**. El nombre de esa función lleva la
palabra `borrador` adentro, así que entran también sus nodos de `automatico`. Lo que el filtro deja
afuera son los nodos `automatico` de las **otras** funciones y las que no se parametrizan por modo.

**Si falla.**

- S11 no está en `SUPUESTOS.md`: escribilo antes de seguir. Un default sin registrar, dentro de seis
  meses, parece un olvido y alguien lo «arregla».
- La prueba pasa con el paso 6 forzado a `automatico`: estás probando la excepción y no el default.
- Para tu negocio querés lo contrario: escribilo como excepción explícita en el paso 6, con el motivo
  al lado. Una excepción sin motivo escrito se borra en la primera limpieza.

---

### Paso 7 · El simulador

**Objetivo.** Escribís como cliente en la terminal y ves, bajo cada respuesta, por qué el agente hizo
lo que hizo.

**Hacé esto.** `pruebas/simulador.py` levanta `correr_ciclo` con el proveedor `demo` y la base en
memoria, y corre un ciclo por cada línea que escribís. Sin red y sin credenciales. `demo` no es un
transporte falso: reproduce entregas grabadas con los mismos bytes crudos, la misma cabecera de firma
y el mismo camino de dedupe. Ver `blueprint/31-proveedores.md`, paso 3.

Seis clientes difíciles prearmados: el que dice que está caro, el que se enoja, el que pide descuento,
el que manda un audio, el que pregunta por algo que no vendés, el que pide hablar con una persona.

Lo que lo separa de un chat cualquiera es **el panel de razonamiento** bajo cada respuesta: score y
por qué, si la objeción estaba en el playbook, de dónde salieron los horarios, qué etapa iría al CRM
y, cuando corresponde, por qué escaló. Cada renglón del panel sale de un campo de la salida del
contrato, no de la prosa del modelo. Acá lo que hay que creer no es «contesta bien»: es «no hace nada
raro».

```bash
.venv/bin/python -m pruebas.simulador
```

**Tenés que ver.** El primer renglón de la cabecera nombra el modelo, porque sin
`ANTHROPIC_API_KEY` en el entorno el simulador escribe con el stub y eso tiene que estar a la vista:
nadie puede confundir un texto enlatado con una redacción.

**Las dos pantallas de acá abajo están derivadas, no transcritas**, y va dicho porque es el único
lugar del archivo donde eso pasa: el kit se publica sin `agente/` y ahí el simulador no abre
ninguna pantalla —imprime el motivo por `stderr` y sale con 2—, así que nadie de este lado corrió
un ciclo. Lo que tenés que comparar contra tu corrida son **los renglones y de qué campo sale cada
uno**, no el texto que redactó el modelo ni las horas.

**Cómo se derivaron, que en esta ronda cambió.** Las de las rondas anteriores se escribieron a mano,
y tres rondas seguidas se colaron renglones que ningún build puede imprimir. Éstas salen de llamar a
`panel()` y
`revisiones()` de `pruebas/simulador.py` —las funciones de verdad, sin copiar— con la entrada que
arma `Cliente.entrada()` desde los fixtures y con el objeto del contrato armado campo por campo
desde `StubModel.canonica()`. Lo único que queda a mano es ese objeto, que es justo lo que
`correr_ciclo` tiene que devolver. Si vas a tocar un renglón de acá, movelo así y no con el editor:
un renglón escrito a mano no lo desmiente nadie hasta que alguien construye el kit entero.

Tres renglones que estaban acá y salieron, porque el código no los puede imprimir así:

- **`ventana 24 h abierta · texto libre` en las dos pantallas.** `respuesta.ventana_abierta` sale
  del `Resultado` de `enviar()` y no se pone a mano porque el paso corrió —`blueprint/31-proveedores.md`
  paso 1, y el mensaje de `test_ventana_la_salida_del_ciclo_dice_que_estaba_abierta`—. Las dos
  pantallas son de `borrador` sin confirmar, o sea que `enviar()` no corrió y el campo viene en
  nulo. Ahora el renglón lo dice, en vez de desaparecer: **un renglón que falta se lee como un
  campo que el build perdió, y uno que dice «abierta» sin que haya salido nada es exactamente el
  build que lo llena a mano.** Apretá enter para aprobar y ese mismo renglón pasa a `abierta` o a
  `CERRADA` según lo que haya devuelto `enviar()`, que es cuando el campo existe.
- **`CRM · nada preparado en este turno`.** Chocaba con `blueprint/34-crm.md` —«sin confirmación,
  `crm.escrito` queda en falso y el paso, en `sin-confirmar`»— y con el Paso 4 de este mismo
  archivo, que afirma `crm.escrito` en falso y para eso necesita un `crm` que no sea nulo. Ganó el
  34: el paso 5 arma la fila igual, no la escribe y la devuelve. `crm` en nulo queda para lo que el
  34 ya dice que significa, «el paso 5 no corrió». El desempate entero está en
  `blueprint/00-contrato.md` § 13.
- **`próximo paso 2026-03-02`.** Ese renglón sale de `crm.proximo_paso_fecha`, que sale del wire,
  que con el stub es un dict fijo con `"proximo_paso_fecha": "2026-03-03"`. Ningún build que pase
  el campo del modelo puede imprimir el 02. Era el más caro de los tres: esta pantalla existe para
  enseñar que cada renglón sale de un campo y no de la prosa, y el ejemplo no lo cumplía.

```
cerrador · demo · modo borrador · base en memoria · modelo stub, sin ANTHROPIC_API_KEY
clientes: 1 caro  2 enojado  3 descuento  4 audio  5 fuera de catálogo  6 humano
(escribí, o /1 a /6 para cargar uno, /modo para cambiarlo, /salir)

vos> Hola, vi el curso. ¿Cuánto sale? Se me hace caro.

agente (parcial · NO enviado)
  El curso sale 12000 MXN y se puede en tres partes. ¿Te va alguno de estos horarios?

  ── por qué ───────────────────────────────────────────────────
  score 62 · tibio       Preguntó precio y puso una objeción que está en el playbook.
  presupuesto null       no dijo cifra, y no se deduce del mensaje
  objeción «Está caro»   en el playbook · respondida con su línea
  horarios 3 de 4        de disponibilidad · ninguno inventado
  precio 12000 MXN       del catálogo · dentro del rango 8000–40000
  CRM etapa calificado   próximo paso 2026-03-03 · no escrito (borrador)
  escalación no          sin enojo · ninguna palabra de la lista
  ventana 24 h sin dato  no se mandó nada en este turno: el campo sale de enviar()
  pasos 1..6             hecho hecho sin-confirmar sin-confirmar sin-confirmar salteado
  envíos de este turno   0
  ──────────────────────────────────────────────────────────────
  ok   seis pasos, del 1 al 6
  ok   ningún horario fuera de disponibilidad
  ok   nada enviado sin confirmación
  ok   el paso 3 sin confirmar dejó el texto redactado
  ok   los envíos coinciden con lo que dice la salida
  ok   el CRM no se escribió sin confirmar
  ok   la cita no se creó sin confirmar
  ──────────────────────────────────────────────────────────────
  enter aprueba y manda · n descarta

vos> /6
cliente 6 · humano · conversación nueva
sugerido: Prefiero que esto lo vea un humano, por favor.

vos> Prefiero que esto lo vea un humano, por favor.

agente (escalado · NO enviado)
  Te sigue una persona del equipo. Ya le pasé la conversación.

  ── por qué ───────────────────────────────────────────────────
  score 62 · tibio       Preguntó precio y puso una objeción que está en el playbook.
  presupuesto null       no dijo cifra, y no se deduce del mensaje
  objeción «Está caro»   en el playbook · respondida con su línea
  horarios 0 de 4        de disponibilidad · ninguno inventado
  precio 12000 MXN       del catálogo · dentro del rango 8000–40000
  CRM etapa escalado     próximo paso 2026-03-03 · no escrito (borrador)
  handoff palabra_clave  disparador «humano» · aviso sin canal configurado, ver S09
  ventana 24 h sin dato  no se mandó nada en este turno: el campo sale de enviar()
  pasos 1..6             hecho hecho sin-confirmar salteado sin-confirmar fallado
  envíos de este turno   0
  ──────────────────────────────────────────────────────────────
  ok   seis pasos, del 1 al 6
  ok   ningún horario fuera de disponibilidad
  ok   nada enviado sin confirmación
  ok   el paso 3 sin confirmar dejó el texto redactado
  ok   los envíos coinciden con lo que dice la salida
  ok   el CRM no se escribió sin confirmar
  ok   la cita no se creó sin confirmar
  ok   al escalar sale como mucho un mensaje
  ──────────────────────────────────────────────────────────────
  enter aprueba y manda · n descarta
  desde acá no se contesta más en este chat
```

**Los tres primeros renglones del panel salen del wire del modelo, y con el stub dicen siempre lo
mismo.** El `score` con su motivo al lado, el `presupuesto` y la objeción: sin `ANTHROPIC_API_KEY`,
`_elegir_modelo()` devuelve `StubModel.canonica()` y nada más, que es un dict fijo —`score` 62,
`objecion_detectada` en «Está caro»—, así que las dos pantallas de arriba muestran esos tres
renglones idénticos aunque una preguntó el precio y la otra pidió un humano. Por eso el motivo de la
segunda habla de precio contra un cliente que no lo nombró: **no es un defecto del build, es el
modelo enlatado que la cabecera anuncia.** Un panel que ahí escriba una frase a la medida de lo que
tipeaste la está sacando del texto y no del campo, que es justo lo que esta pantalla existe para no
hacer. Lo que sí cambia con lo que escribís es todo lo que decide el código —el handoff, los pasos,
los horarios, el CRM, los envíos y las revisiones de abajo—, y ésa es la mitad que hay que mirar.

Cinco cosas más de esas pantallas que no son adorno.

- **El paso 6 de la segunda pantalla dice `fallado`, y está bien.** El simulador corre sin
  credenciales —lo dice su propia cabecera—, así que no hay `SLACK_WEBHOOK_URL`, y sin esa
  variable no hay a dónde mandar el aviso interno: el paso 6 queda `fallado` con el motivo,
  `handoff.avisado_en` queda nulo y el renglón del handoff lo dice al lado —«aviso sin canal
  configurado, ver S09»—. **Lo que decide es la variable, no el canal.** Los seis clientes traen
  `canal_interno` en `#ventas-escalaciones` y el paso 6 queda `fallado` igual; es lo mismo que
  exige `test_sin_la_variable_de_slack_el_paso_6_queda_fallado_con_el_motivo`, que pone el canal y
  saca la variable. Lo que se pierde sin la variable es el aviso, no la escalación: el `handoff`
  queda escrito en la salida y el chat se lee del panel. Ver `SUPUESTOS.md` S09 y
  `blueprint/32-multimodal.md` paso 5.
- **El paso 3 de la segunda pantalla dice `sin-confirmar`, no `salteado`.** La línea que le avisa al
  contacto que lo sigue una persona la redacta el paso 3 —por eso el texto de arriba de ese panel no
  es el del stub, y el de la primera pantalla sí—, y en `borrador` queda redactada esperando
  confirmación como cualquier otro envío: es S11, y lo ancla la mitad `borrador` de
  `test_sale_un_mensaje_en_automatico_y_ninguno_en_borrador`, que exige `respuesta` con texto
  adentro y `respuesta.enviado` en falso. Un paso que redactó no es `salteado`. `salteado` en el 3
  es otra cosa y sale en el turno siguiente: el chat **ya** escaló, no se redacta nada y `respuesta`
  queda nula —el renglón de abajo de todo, «desde acá no se contesta más en este chat»—. Si tu
  pantalla dice `salteado` con una respuesta escrita arriba, el que está mal es el build.
- **El paréntesis de arriba es `estado`**, el campo del contrato, no el modo: `parcial` cuando quedan
  pasos sin confirmar, `escalado` cuando se disparó el 6, `detenido` cuando el agente paró y preguntó.
  El modo se lee en la cabecera y en el `no escrito (borrador)` del renglón del CRM.
- **El bloque de abajo son las revisiones**, las mismas reglas que afirman las pruebas corridas en vivo
  sobre este turno. `RARO` en lugar de `ok` es un hallazgo, y es la única parte de la pantalla que hay
  que mirar rápido. Las dos últimas sólo aparecen cuando el turno escala o cuando ya venía escalado.
  **Una de las siete afirma que algo pasó y no que algo no pasó**, y está a propósito: seis
  negativas seguidas le dan siete `ok` a un agente mudo —cero envíos, cero horarios inventados, nada
  escrito sin confirmar y ninguna línea redactada—. La positiva es «el paso 3 sin confirmar dejó el
  texto redactado», que es la mitad `borrador` de S11 y no mira **qué** dice el texto, sino que haya
  uno esperando confirmación.
- **El cliente 2, el enojado, dispara dos reglas a la vez, y gana `palabra_clave`.** Su texto
  sugerido trae «estafadores» —y `estafa` está en `palabras_escalacion`— arriba de un insulto que
  también dispara el enojo. El orden es el del Paso 5: `palabra_clave`, `precio_fuera_de_rango`,
  `enojo`, se para en el primero que da, y el `disparador` trae la palabra de la lista, «estafa». Si
  tu pantalla ahí dice `handoff enojo`, no es una rareza del simulador: tu build evalúa en otro
  orden. Con el texto del fixture —«Una porquería de servicio», que no trae ninguna palabra de la
  lista— escala como `enojo`, y ahí no hay nada que desempatar. El ejemplo de arriba usa el `/6`
  porque su motivo no depende de lo que se tipee.

Sin `agente/ciclo.py` el simulador no abre una pantalla que conteste sin agente adentro: imprime el
motivo por `stderr` y sale con 2. Es lo correcto, y está dicho ahí mismo: «una pantalla que conteste
sin agente adentro es peor que ninguna».

**Si falla.**

- Los recuadros y las tildes salen rotos: la terminal no está en UTF-8. `PYTHONIOENCODING=utf-8`, y en
  PowerShell `chcp 65001` antes de arrancar.
- El panel muestra un campo que la salida no tiene: lo está sacando del texto del modelo. Todo el
  panel se arma leyendo el objeto del contrato, campo por campo.
- **`ventana 24 h abierta` con `envíos de este turno 0`.** El build está llenando
  `respuesta.ventana_abierta` a mano porque el paso 3 corrió. Ese campo sale del `Resultado` de
  `enviar()`, y en `borrador` sin confirmar `enviar()` no corre: el renglón tiene que decir
  `sin dato`. Es el defecto que `test_ventana_la_salida_del_ciclo_dice_que_estaba_abierta` describe
  en su mensaje, visto desde la pantalla y un turno antes.
- **`CRM · el paso 5 no corrió en este turno` en un turno normal de `borrador`.** El paso 5 arma la
  fila igual, no la escribe y la devuelve en `crm` con `escrito` en falso; el nulo queda para el
  turno donde el paso ni llegó a armarla. Ver `blueprint/34-crm.md` y `blueprint/00-contrato.md`
  § 13. Ojo, porque hay dos archivos del kit que todavía dicen lo contrario: están nombrados en
  el § 13.
- Ofrece un horario que no está en `disponibilidad`: es el mismo fallo de la aserción 3 visto de otra
  forma. No es una mejora del simulador.
- El cliente 4 no arranca y dice que no consiguió el audio: es lo correcto. Son tres formas de no
  conseguir los bytes y las tres frenan igual. Un `media_id` no se le pasa nunca a una API de visión:
  sin cabecera devuelve 401.
- Contesta después de escalar: volvé al Paso 5. Eso es el bug, no una rareza de la pantalla.

---

### Paso 8 · Cerrá la fase con la compuerta

**Objetivo.** La suite entera y los cinco chequeos que la miran están en verde.

**Hacé esto.**

```bash
.venv/bin/python -m pytest pruebas -q
.venv/bin/python scripts/auditar.py --censo
.venv/bin/python scripts/auditar.py
```

En Windows, las tres líneas con `.venv\Scripts\python.exe`. **El intérprete del proyecto no es un
detalle de estilo**: el `python3` del sistema no trae `jsonschema` ni `pydantic`, así que
`contrato-control` saltea, el veredicto baja a `parcial` y la salida es 3. Con ese comando, el `pass`
que este paso espera no sale nunca. Ver `blueprint/00-contrato.md` § 5.

**La del medio es la corrida cara y va una sola vez.** `--censo` corre la suite entera una vez por
cada campo de `contratos/salida.schema.json`, con un solo valor cambiado en el documento que
devuelve `correr_ciclo`, y anota cuáles ponen roja a alguna prueba. Deja `EVIDENCIA/censo.json`, que
es lo que lee `23 censo-de-campos` en la corrida normal. Sin esa evidencia el 23 **saltea**, y con
`agente/` en el árbol un salteo del 23 deja el veredicto en `parcial`: o sea que sin esta línea el
`0 salteados` de abajo no sale nunca. No emite veredicto ni publica nada; sólo escribe la evidencia.

**Tenés que ver.** pytest sin fallas, y del auditor estas cinco líneas y el veredicto:

```
  [ok      ] 16 contrato           1 salida(s) válidas, con los seis pasos en orden
  [ok      ] 17 contrato-control   6/6 mutaciones rechazadas
  [ok      ] 18 firmas             4 de 4 comprobación(es): 2 fixture(s) × 2 módulo(s)
  [ok      ] 19 pruebas            NN passed in 1.4s · 0 salteados · piso: NN de 30
  [ok      ] 23 censo-de-campos    43 campos declarados: NN afirmados por una prueba que se pu

auditar: PASS · 0 errores · 0 avisos · 0 salteados
```

El `43` del 23 lo decide `contratos/salida.schema.json`, que es del kit, así que ése sí va escrito;
los dos `NN` de esa línea —cuántos afirma tu suite y cuántos quedan con el motivo escrito— los
decide tu corrida, por lo mismo que el `NN` del 19. La línea sale cortada a los 78 caracteres del
motivo, como las del 13 y el 14.

**Los tres ceros son alcanzables acá y en ninguna fase anterior**, y conviene saber por qué antes
de mirarlos. Los veintitrés chequeos de la compuerta se reparten así al terminar la fase 5: los
ocho que esperaban el build —06, 10, 12, 13, 14, 15, 21 y 22— corren porque `agente/` está;
`16 contrato` corre porque la corrida de pytest de arriba dejó `pruebas/salida-caso-01.json`
escrito; `19 pruebas` no saltea ni un nodo, porque los que saltean sin build son los que el build
acaba de habilitar; `20 playbook` corre desde la fase 2, que es la que escribió
`config/playbook.yaml`; y `23 censo-de-campos` corre porque la línea del `--censo` dejó
`EVIDENCIA/censo.json` escrito. Si alguno de esos cinco motivos no se cumple, el número que no
cierra te dice cuál.

**El 23 no te cobra los campos que hoy no afirma nadie.** Están escritos uno por uno en la lista
`SIN_ASERCION` de `scripts/auditar.py`, con el motivo al lado, y por eso no salen como error: se
cierran agregando nodos a `pruebas/`, y **vos no agregás pruebas en esta fase, las ponés en
verde**. Son deuda del kit, y están enumerados en `PENDIENTES.md` con quién cierra cada uno. Si tu
corrida marca un campo que **no** está en esa lista, ése sí es del build: el censo le cambió el
valor y ninguna prueba se movió.

**Y el cero de avisos depende de una sola cosa que no se ve**: `09 gitignore-anclado` avisa
—`gitignore/nucleo_sin_rastrear`— mientras haya archivos del núcleo fuera del índice de git.
Clonaste el kit, así que están todos adentro y el aviso no sale; si bajaste un ZIP y armaste el
repo a mano, sale, y con `agente/` en el árbol **no es aviso sino error**. Ver
`blueprint/10-entorno.md`.

La meta cambia con la fase, así que va una por corrida:

| Cuándo | Veredicto | De dónde sale |
|---|---|---|
| recién clonado, con el `.venv` y nada más | `PASS · 0 errores · 1 aviso · 11 salteados` | medido |
| terminada la fase 2, con `config/playbook.yaml` | `PASS · 0 errores · 1 aviso · 10 salteados` | derivado del de arriba |
| terminada esta fase, con `agente/` entero y el `--censo` corrido | `PASS · 0 errores · 0 avisos · 0 salteados` | derivado |

**Los salteados de las dos primeras subieron uno más en esta ronda, de 10 a 11 y de 9 a 10**: la
compuerta sumó el chequeo `23 censo-de-campos`, que saltea mientras no exista `EVIDENCIA/censo.json`
—la ronda anterior había sumado `22 rutas-del-contrato`, y la anterior `21 panel-cerrado`, las dos
por esperar el build—. El `11` está medido acá, sobre un árbol sin `agente/` y sin
`config/playbook.yaml`, con todo agregado al índice de git; el `10` de la segunda fila sale de
restarle `20 playbook`, que con el archivo en el árbol deja de saltear, y su `PASS` depende de que
ese playbook sea el que escribe la fase 2 y no uno cualquiera.

**Si tu corrida trae un aviso de más, mirá cuál antes de buscar el defecto.** En la corrida de esta
ronda salieron dos: el `pruebas/salteados_sin_build` de la tabla, y un
`gitignore/nucleo_sin_rastrear` que es del árbol donde se corrió y no del kit —55 de 58 archivos del
núcleo estaban fuera del índice de git—. Es el mismo que explica el párrafo de arriba: con el kit
clonado no sale, y con `agente/` en el árbol deja de ser aviso y es error. Por eso el `1 aviso` de
la tabla está medido con `git add -A` puesto: sin eso salen dos.

**«Derivado» quiere decir que la última fila no se corrió sobre un árbol construido**, porque el
kit se publica sin `agente/`. Sale de las dos primeras más las condiciones de arriba, chequeo por
chequeo. Si en tu corrida da otra cosa, mandá la línea que no cierra: ganás vos, que tenés el
árbol.

El aviso de las dos primeras es `pruebas/salteados_sin_build`, y dice cuántos nodos esperan el
build. Es el que desaparece solo cuando el build llega: si en esta fase sigue apareciendo, la
compuerta lo sube a error —`pruebas/salteados_con_build`— y el número que trae adentro es la
cuenta de nodos que no probaron una sola línea de lo que construiste.

Los números del bloque se leen mal si nadie los explica, así que van explicados. Y uno de ellos no
está escrito: el `NN`.

---

#### El `NN`, y por qué este archivo dejó de escribir totales

**La regla del kit: el blueprint no escribe un total de nodos. Donde hacía falta el total va el
comando que lo imprime.** Es la tercera ronda que alguien sincroniza esos enteros y la primera que
los saca, así que va el porqué y no sólo la regla.

Un total —la suite entera, un archivo, un `-k`— es la suma de lo que la parametrización decida, y
**nadie es su dueño**: crece cuando se agrega un disparador, un canal o un archivo de pruebas, y
ninguna de esas ediciones pasa por acá. Escrito en la prosa, envejece en silencio hasta que alguien
lo mide, y quien construye lo lee como una meta: la corrida le da otro número, no sabe si le falta
un archivo o si el kit se movió, y la única salida honesta que le queda es preguntar. Medido en las
tres últimas rondas: `154` estaba en cuatro lugares, `20` en dos y `109` en uno, y las tres veces
volvieron a mentir a la ronda siguiente.

Lo que sí se escribe son los números que **decide esta prosa**: las tres formas de no conseguir los
bytes de un audio son tres porque el Paso 4 dice cuáles son, las doce funciones del Paso 5 están
listadas una por una, las seis mutaciones y los dos fixtures por dos módulos son constantes de la
compuerta. Ésos no envejecen solos: para moverlos hay que venir a escribir el cambio acá.

**Y los tres veredictos quedan exactos, que son la otra excepción.** `PASS · 0 errores · 0 avisos ·
0 salteados` al terminar esta fase, `1 aviso · 11 salteados` recién clonado y `10 salteados`
terminada la fase 2 no son conteos: son la condición de terminado. Un cero que se mueve es un
defecto, no un crecimiento, y por eso van escritos y medidos.

**Los salteados de las dos primeras filas son la excepción de la excepción, y hay que decirlo:**
crecen de a uno cada vez que la compuerta suma un chequeo que no puede correr todavía, y eso no pasa
por este archivo. Tres rondas seguidas se movieron por ese motivo: `21`, `22` y ahora `23`. La forma
de no volver a perseguirlos es leerlos como lo que son —«todos los que todavía no tienen qué
mirar, y ninguno más»— y compararlos contra el desglose que imprime la corrida, que dice chequeo por
chequeo cuál saltea y por qué. El único que no crece nunca es el de esta fase, que es cero.

**Cómo se encuentra el que vuelva a colarse.** No hace falta releer dieciséis archivos: un total de
pytest escrito en la prosa se lee siempre igual.

```bash
grep -rn "[0-9] passed\|[0-9] skipped\|[0-9] tests collected\|[0-9] deselected" blueprint/ \
  | grep -v "NN passed"
```

**La lista que imprime no se vacía sola, así que va con dueño y con lo que hay que escribir en cada
caso.** Dos rondas la dejaron como una lista de cuatro archivos y las dos veces siguió imprimiendo
lo mismo: nadie es dueño de una lista, y «pasarlo a esta forma» sin decir a qué forma es una tarea
que cada uno interpreta distinto. Ésta es la tabla, y **cada línea es del dueño del archivo donde
está escrita**, no de este archivo ni de quien corre el grep.

Los enteros no se copian acá adentro —serían cuatro totales nuevos, y el `grep` los encontraría—:
va el lugar, y el número se lee ahí.

**La primera columna es el lugar y ya no el número de línea**, porque el número de línea también
envejece: esta tabla decía `31-proveedores.md:554` y el `grep` de esta ronda lo imprimió en la 664.
Dos cosas que se mantienen a mano en la misma celda es una de más. El `grep` ya trae la línea de
hoy; lo que la tabla tiene que decir es cuál de los bloques del archivo es, que eso no se mueve.

| Dónde | Qué tiene escrito | Qué escribe en su lugar | Dueño |
|---|---|---|---|
| `35-panel-api.md`, paso 1, el hallazgo del `importlib.reload` | dos enteros adentro de un hallazgo medido: cuántos nodos caen y cuántos quedan | el hallazgo sin los dos: qué se rompe y por qué. Cuántos caen lo imprime la corrida de quien lo reproduzca | quien tenga `35-panel-api.md` |
| `35-panel-api.md`, paso 4, el «Tenés que ver» de `pytest pruebas/test_panel.py -q` | el total de ese archivo, a mano, y otra vez en el `tests collected` del renglón de abajo | `NN`. La frase de abajo —«el número que manda lo imprime…»— se queda | quien tenga `35-panel-api.md` |
| `35-panel-api.md`, el bloque de la bandeja, el «Tenés que ver» de `pytest pruebas/test_bandeja.py -q` | el total de ese archivo, a mano | `NN passed`, con el comando al lado | quien tenga `35-panel-api.md` |
| `35-panel-api.md`, el bloque de los tres nodos del escapado | el total con `deselected` del `-k escapa`, y dos veces el total de la suite entera adentro de los hallazgos medidos | `NN`. Los dos de la suite entera, el hallazgo sin el entero | quien tenga `35-panel-api.md` |
| `30-generacion.md`, el paso del modelo, el «Tenés que ver» de `pytest pruebas/test_modelo.py -q` | el total de ese archivo, a mano, y el de la suite entera adentro del hallazgo de al lado | `NN passed`, y el hallazgo sin el entero | quien tenga `30-generacion.md` |

**Las dos que ya salieron de la tabla.** `34-crm.md`, la celda con el total de
`pruebas/test_caso_01.py`. Y `31-proveedores.md`, el «Tenés que ver» del paso 3 con la suite
entera, que decía `154`: la suite creció cuatro rondas seguidas y el número mintió las cuatro.
Ninguna de las dos imprime hoy.

**Y tres que entraron en ésta**, las tres por bloques nuevos y no por una regresión: la bandeja y
el escapado en `35-panel-api.md`, y el del modelo en `30-generacion.md`. Es lo que la regla dice
que va a pasar —un total se escribe cuando alguien mide algo, que es justo cuando el número es
cierto— y por eso el `grep` se corre al cerrar y no al abrir. Hoy todo lo que imprime cae en alguna
fila de esta tabla; una línea que no caiga en ninguna es nueva.

**La forma, en dos reglas, para que no haya que venir a preguntar.** Una: en el bloque de «Tenés que
ver» el total va como `NN passed`, y al lado el comando que lo imprime. Dos: **el renglón de
aclaración de abajo no salva al número de arriba.** Tres de las cuatro líneas que llegaron a estar
en esta tabla ya traían su «el número que manda lo imprime `--collect-only`» debajo del bloque, y
envejecieron igual; la de `34-crm.md` remitía a este archivo, que es la misma falla con otra cara.
Quien construye compara contra lo que está adentro del bloque, que es lo que el archivo le dijo que
iba a ver, y no baja a leer la aclaración hasta que el número no le cierra.

Lo que **no** se toca: un número que decide la prosa. Las tres formas de no conseguir los bytes de un
audio, las doce funciones del Paso 5, las seis mutaciones, los dos fixtures por dos módulos y los tres
veredictos de la compuerta van escritos y no los imprime este grep, porque ninguno se escribe con
`passed` al lado.

`blueprint/40-pruebas.md` y `blueprint/90-auditoria.md` no imprimen ninguna línea. `00-contrato.md`
salió de la lista en esta ronda: su línea citaba el total de `30-generacion.md` para diagnosticarlo,
y la cita se reescribió sin el entero —citar un total ajeno también envejece, porque el día que el
otro archivo cambia la cita queda mintiendo dos veces—.

Corré el `grep` antes de dar una ronda por cerrada. **Una línea que imprima y no esté en esa tabla es
un total nuevo**, y agregarla a la tabla con su dueño es parte de cerrar la ronda.

**La alternativa que no se eligió**, dicha para que nadie la vuelva a proponer sin saber que ya se
miró: que la compuerta lea los enteros de la prosa y falle cuando derivan. Se descartó por tres
motivos. Le pone a `scripts/auditar.py` un parser de markdown que hoy no tiene, y un chequeo frágil
es peor que ninguno. El total real depende del árbol —con build y sin build son dos números, y la
ronda de Postgres es una tercera—, así que la compuerta tendría que saber contra cuál comparar. Y
sobre todo: pondría en rojo el build de quien construye por una frase nuestra, con `atribuible_a`
en `kit`, que es exactamente lo que el Paso 6 de `blueprint/90-auditoria.md` enseña a no hacer.

---

**`NN passed`** es la suite entera, que ya está escrita: **vos no agregás pruebas en esta fase, las
ponés en verde**. Son nueve archivos y el total sale de la parametrización, no de la cantidad de
funciones. Los dos comandos que lo imprimen, el total y el desglose por archivo:

```bash
.venv/bin/python -m pytest pruebas --collect-only -q | grep collected
for f in pruebas/test_*.py; do printf '%-30s' "$f"; \
  .venv/bin/python -m pytest "$f" --collect-only -q | grep collected; done
```

| Archivo | Qué afirma |
|---|---|
| `pruebas/test_camino_feliz.py` | que las cosas **sí** pasen: los medios bajados, el calendario, el CRM y el aviso interno, contra builds huecos |
| `pruebas/test_caso_01.py` | el camino feliz, una aserción por paso · Paso 4 |
| `pruebas/test_caso_02.py` | la escalación, tres disparadores por dos modos · Pasos 5 y 6 |
| `pruebas/test_contrato.py` | el esquema, las seis mutaciones y el esquema angosto · Paso 3 |
| `pruebas/test_enviar.py` | las tres guardas de `enviar()`, en las dos direcciones · Paso 2 |
| `pruebas/test_firmas.py` | la firma sobre el cuerpo crudo y el alta del webhook |
| `pruebas/test_idempotencia.py` | el dedupe a la entrada y la `Idempotency-Key` a la salida |
| `pruebas/test_modelo.py` | la única llamada real al modelo, contra bytes grabados · `blueprint/30-generacion.md` paso 5 |
| `pruebas/test_panel.py` | la puerta del panel: sin token 401, y `/salud` sin token · `blueprint/35-panel-api.md` |

**Lo que sí es una afirmación, y no un número: la lista de archivos.** Son estos nueve y el desglose
tiene que traerlos a los nueve. Un total que **baja** sin que nadie lo haya decidido quiere decir
que se perdió un archivo, y eso se ve acá antes que en ningún entero.

**Y esa afirmación tiene vara desde hace dos rondas: `ARCHIVOS_DE_PRUEBA`, en `scripts/auditar.py`.**
Falta uno y la compuerta lo nombra —borrar `pruebas/test_panel.py` costó once errores en la ronda
pasada, donde antes pasaba entero—. Sobra uno —un `test_*.py` en el disco que
la tupla no conoce— y sale un aviso, porque agregar una prueba es lo correcto y lo que hay que
decir es que esa todavía no la cuida nadie. Esta tabla y esa tupla se mueven juntas: la tupla es la
que manda, porque es la única de las dos que el build no puede editar.

**Antes del build, `pytest pruebas -q` reparte ese mismo total en dos**, y está bien: pasan los que
no tocan `agente/` y saltean los que necesitan `agente/ciclo.py`, `agente/enviar.py` o
`agente/servidor.py`. Cada uno de los que saltean lo hace con el motivo escrito:
`pytest pruebas -q -rs` los lista con el texto adentro. Un salteado con motivo no es un aprobado,
pero tampoco es una
falla: es el kit diciendo qué falta construir. Lo que sí es un problema es un salteado **sin**
motivo, o un `passed` donde antes había un `skipped` y nadie construyó nada.

De los que pasan sin build, la mayoría no toca `agente/` —el esquema, las mutaciones, las firmas—
y **cinco comparan fixtures contra fixtures**:
`test_el_fixture_del_enojo_trae_el_agravio_en_las_dos_fuentes`, que mira los dos del enojo entre
sí, y los cuatro nodos de `test_los_historiales_traen_los_campos_que_estas_pruebas_leen`, uno por
historial —son cuatro, no tres: `historial-insistencia.json` va con los tres de `caso-02`—. Esos
cinco sí van escritos, porque son una lista y no una suma. Si alguno no está, alguien le puso un
`pytestmark` de módulo a `pruebas/test_caso_02.py` o a `pruebas/test_enviar.py`, y esas guardas
dejaron de correr justo cuando más sirven: con el árbol sin construir, que es cuando se editan los
fixtures.

**Y uno más que no compara fixtures sino el reloj contra el corpus**:
`test_la_suite_corre_parada_en_el_instante_del_corpus`, también en `pruebas/test_enviar.py`. Va con
los cinco de arriba y por lo mismo: corre sin build, es barato, y es lo único que avisa cuando la
fixture de sesión que para el reloj dejó de estar puesta. Sin él, lo que se ve es el ciclo contando
cero envíos con un mensaje que acusa al build.

**Los nodos de `pruebas/test_enviar.py`** se reparten en cuatro: las tres guardas —cada una en las
dos direcciones, más las cinco ramas de `revisar_baneo()`, que se rompen por separado—, los cuatro
de los historiales de los que salen, uno por fixture, el del reloj parado, y uno solo que no mira
`enviar()` sino el webhook: `test_el_ciclo_que_revienta_despues_del_200_no_sube_por_el_webhook`,
que está ahí porque lo que afirma es lo que sale del proceso después de haber contestado, y porque
ese camino no lo corre nadie hasta que `config/playbook.yaml` está en el árbol. La regla la escribe
`blueprint/31-proveedores.md`, paso 5. Cuántos son cada uno lo imprime
`.venv/bin/python -m pytest pruebas/test_enviar.py --collect-only -q`, agrupado por función. La
ventana se prueba con `ahora` por parámetro y con el `window_expires_at` del historial, una hora
antes y una hora después: adentro sale el texto libre, afuera no sale y el motivo lo dice, y
`respuesta.ventana_abierta` —el campo del contrato— tiene que decir cuál de las dos era. La baja
corta el envío aun con la ventana abierta, y corta también la línea que confirma la baja. Y a un
contacto sin ningún entrante no se le abre conversación, ni cuando la fila existe con
`last_inbound_at` en nulo. Cada aserción que falla nombra cuál de las tres se rompió y en qué tiempo
de `enviar()` vive; ver el Paso 2.

- **`4 de 4 comprobación(es): 2 fixture(s) × 2 módulo(s)`**: son dos fixtures, `meta` y `zernio`, y
  dos módulos que firman —`plantillas/seguridad/firmas.py` y el `agente/firmas.py` copiado de ahí—.
  Dos por dos. Antes de construir dice `2 de 2 comprobación(es): 2 fixture(s) × 1 módulo(s)`, porque
  el segundo módulo todavía no está.
- **`6/6 mutaciones rechazadas`** son las cinco del control negativo más la sexta, la que el esquema
  **no** puede rechazar —seis pasos con `n` igual a 1— y que por eso se afirma en código. Corre
  siempre, con o sin build: es lo único que distingue «todo verde» de «no se está validando nada».
- **`1 salida(s) válidas`** es `pruebas/salida-caso-01.json`, que escribe el fixture `salida_caso_01`
  de `pruebas/conftest.py`. Antes del build ese archivo no existe y el chequeo 16 saltea.
  `pruebas/fixtures/caso-01.salida-esperada.json` **no** entra en esa cuenta a propósito: no se llama
  `salida*.json` para no contarse como una corrida del agente. Lo vigila
  `test_el_fixture_de_la_salida_esperada_esta_donde_dice`, porque si entrara en ese glob el auditor
  diría «2 salidas válidas» con el build sin construir.

**Si falla.**

- `[salteado] 19 pruebas`: no hay `pruebas/test_*.py`, o falta pytest en ese intérprete. Corré con el
  `.venv` del proyecto. Un salteado no es un aprobado.
- `[salteado] 17 contrato-control`: falta `jsonschema`, o sea que corriste con el Python del sistema.
  Sin él, verde no se distingue de «no se validó nada»: el chequeo es exigible siempre, el veredicto
  sale `parcial` y la salida es 3.
- `pruebas/colgadas`: la suite pasó de 120 segundos y la compuerta la corta. Lo lento va al simulador,
  que corre cuando vos querés.
- `pruebas/fallan`: el hallazgo trae la cola de pytest y un `atribuible_a` con `kit`, `build` o
  `entorno`. Eso dice a quién le toca.
- Veredicto `parcial`: algo que tenía que correr no corrió. Con `parcial` no se publica.

Con esto termina la fase 5.

Anotalo en `.wca-estado.json`: `fase` en `pruebas` y el sha256 de cada archivo escrito.

**Próximo archivo:** `blueprint/90-auditoria.md`, la compuerta, que explica los chequeos uno
por uno. El despliegue viene después de ese `pass`, y no antes.
