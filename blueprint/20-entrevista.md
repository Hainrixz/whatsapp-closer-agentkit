# 20 · La entrevista

Doce preguntas numeradas. Once se hacen acá, en tres tramos, y cada tramo tiene su comando. La que
falta —Q4, cómo cerrás— tiene archivo propio y tres caminos: la hace `blueprint/25-playbook.md`,
que es el próximo archivo y el dueño único de `config/playbook.yaml`.

Un kit que pregunta doce cosas antes de mostrar algo se muere en la sexta. Por eso los tramos no
son un orden bonito: **cada uno termina con algo que anda más que antes, y se puede parar ahí.**

| Tramo | Comando | Preguntas | De dónde sale la respuesta | Con qué te deja |
|---|---|---|---|---|
| 1 | `/armar-cerrador` | Q1, Q2, Q3 | de tu cabeza | marca y trato, con el playbook a un archivo de distancia |
| 2 | `/configurar` | Q5 a Q9 | de tu cabeza | precios reales, horarios reales y la escalación |
| 3 | `/conectar` | Q10, Q11, Q12 | cinco consolas ajenas | WhatsApp de verdad, agenda, CRM y aviso |

**Las tres reglas.** Una pregunta por mensaje. Cada respuesta se escribe en `.wca-estado.json`
**antes** de preguntar la siguiente: si se corta la luz en la novena, las ocho anteriores están.
Ningún valor de credencial pasa por una tool call.

Vos le hablás de vos a quien instala. El agente le habla a los clientes con el trato de Q3, que
puede no ser el tuyo.

## Tramo 1 · Q1 a Q3 · desde `/armar-cerrador`

### Paso 1 · Abrí el estado

**Objetivo.** Existe `.wca-estado.json` y ninguna respuesta anterior se perdió.

**Hacé esto.** Si ya existe, no preguntes nada: pasá al procedimiento de `/seguir`. Si no,
escribilo: `{ "version": 1, "fase": "entrevista", "respuestas": {}, "archivos": {} }`

**Tenés que ver.** El archivo en la raíz, con esas cuatro claves y `respuestas` vacío.

**Si falla.** Existe y no es JSON válido: renombralo a `.wca-estado.json.roto`, decilo y arrancá
de cero, no lo repares adivinando. No tenés permiso de escritura: parás, porque sin ese archivo
la entrevista no sobrevive a un corte.

### Paso 2 · Q1 y Q2 · Identidad

**Objetivo.** El agente sabe de qué negocio habla y con qué nombre firma.

**Hacé esto.** Dos preguntas, una por mensaje, la primera guardada antes de la segunda.

> ¿Qué vende tu negocio, y cómo se llama? Con una línea alcanza: «vendo cursos de bienes raíces
> en México, la marca se llama Terra».

> ¿Con qué nombre firma tus mensajes? Si no querés uno, escribí «sin nombre» y contesta como el
> negocio.

Q2 es salteable: guardás `null`. Si contesta tres párrafos, resumilos en `negocio` y `que_vende` y
mostrale en una línea lo que entendiste.

**Tenés que ver.** `"q1": {"negocio": "Terra", "que_vende": "..."}, "q2": {"agente": "Sofi"}`.

**Si falla.** Da sólo el nombre: repreguntá qué vende, una vez; si sigue vacío guardá `null` y
seguí, el agente se presenta sin nombre. Contesta con el enlace al sitio: decí que desde acá no
navegás. Manda un emoji o una frase larga: cortá a 24 caracteres y confirmá.

### Paso 3 · Q3 · El tratamiento

**Objetivo.** Queda elegido cómo le habla el agente a un cliente, en un solo lugar.

**Hacé esto.** Preguntá, literal:

> ¿Cómo le habla tu marca a un cliente? Elegí uno:
>
> 1. **tú** — México, Colombia, Perú, Chile, España
> 2. **vos** — Argentina, Uruguay, Paraguay, Costa Rica
> 3. **usted** — trato formal, y lo normal en buena parte de Colombia y Centroamérica con alguien
>    que escribe por primera vez

Guardás uno de esos tres valores exactos. Aclarale que esto no cambia cómo te hablo yo a vos:
cambia cómo le escribe el agente a sus clientes.

**Tenés que ver.** `"q3": {"tratamiento": "vos"}` en el estado.

**Si falla.** Contesta «el que sea» o nada: poné `tú`, el de cobertura más ancha, y decí cuál
quedó. Contesta «depende del cliente»: es uno para todo el agente, no uno por contacto; que elija
el de la mayoría, se cambia con `/configurar`.

### Paso 4 · Cerrá el tramo 1 y pasá al playbook

**Objetivo.** `config/marca.yaml` está escrito, hay un `.env` sobre `demo`, y quien instala sabe
que lo único que le falta para hablar con su cerrador es el archivo siguiente.

**Hacé esto.** Escribí `config/marca.yaml` con `negocio`, `que_vende`, `agente` y `tratamiento`.
Si no hay `.env`, copiá `env.example` y dejá `WHATSAPP_PROVIDER=demo`. Marcá
`"fase": "tramo-1-listo"` y decí esto:

> Ya tenés la marca y el trato. Falta cómo cerrás, que es lo que separa esto de un bot de menú:
> son tres caminos y lleva entre un minuto y diez. Sigo con eso, y cuando esté corré `/probar`
> para hablar con él.

**`config/playbook.yaml` no lo escribe este archivo.** Lo escribe `blueprint/25-playbook.md` en su
paso 7, que es su dueño único, y lo hace después de preguntar Q4 con sus tres caminos. Dejar acá
una versión provisional con `tono: null` para pisarla dos pantallas más tarde es lo que tenía a dos
archivos discutiendo por el mismo YAML.

**Tenés que ver.** `config/marca.yaml` en disco con las cuatro claves, y la línea
`WHATSAPP_PROVIDER=demo` en `.env`. Esa línea es la que va a quedar puesta cuando corras la suite en
la fase 5, y la suite tiene que dar verde con ella: si hay que cambiarla por `meta` para que pase,
el defecto está en `enviar()` y no en tu instalación —ver `blueprint/31-proveedores.md`, paso 1—.

**Si falla.** No existe `config/`: creala, se versiona a propósito. Ya hay un `.env` con otro
proveedor: no lo pises, decí cuál está puesto y preguntá. Falta PyYAML: no importa, este archivo se
escribe como texto. Quiere correr `/probar` ahora: todavía no valida, porque
`playbook.objeciones` tiene `minItems: 1` en `contratos/entrada.schema.json` y sin una sola
objeción la entrada entera rebota; decilo en una línea y seguí al playbook.

## Tramo 2 · Q5 a Q9 · desde `/configurar`

**Cinco preguntas y ninguna consola ajena.** Todo lo que sigue sale de tu cabeza y de lo que ya
sabés de tu negocio: no hay que abrir una cuenta, ni copiar una clave, ni esperar la aprobación de
nadie. Se puede hacer entero de un tirón.

Todo es salteable. Cada salteo tiene una consecuencia y se dice al saltearlo, no después.

### Paso 5 · Q5 · El catálogo con precios

**Objetivo.** Existe la lista de lo que se vende con su precio, confirmada por quien vende.

**Hacé esto.** Preguntá, literal:

> ¿Qué vendés y a qué precio? Cuatro formas, agarrá la que te sirva:
>
> 1. Escribilo acá, un producto por línea con su precio.
> 2. Dejá el archivo en `knowledge/negocio/` y decime cómo se llama. Leo PDF, DOCX, TXT y MD.
>    Esa carpeta está adentro del proyecto: es la misma carpeta desde la que abriste Claude Code,
>    la que tiene `README.md` y `blueprint/` adentro. Copiá el archivo ahí con el Finder o el
>    Explorador, como cualquier otro archivo.
> 3. Mandame la foto del menú o de la lista de precios. Se pega igual que un texto: arrastrá la
>    imagen a la ventana donde me escribís, o copiala y pegala con **Ctrl+V** —en macOS también
>    Ctrl+V; Cmd+V pega texto, no imágenes—. Si tu terminal no la acepta, guardala en
>    `knowledge/negocio/` y usá la opción 2.
> 4. Vendés una sola cosa: decime cuál y cuánto sale.

Después, y esto no se saltea, **mostrale la tabla que entendiste**:

```
| Producto               | Precio | Moneda |
| Curso de bienes raíces |  12000 | MXN    |

¿Está bien así? Corregí la línea que esté mal, o decime «está bien».
```

No escribas `config/negocio.yaml` hasta que confirme. Pedirle un formato estructurado a alguien
que nunca estructuró un dato es donde se pierde la gente; darle una tabla para corregir, no.

La foto la leo yo y de ahí sale la tabla: lo que vale es la tabla confirmada, no la imagen. El
archivo queda en `knowledge/negocio/`, que está en `.gitignore` porque puede tener datos de
clientes o material con licencia de otro.

**Tenés que ver.** La tabla en pantalla, un «está bien», y recién después las filas en el YAML.

**Si falla.** Da un rango («de 5000 a 12000»): eso no es un precio, el contrato pide un número;
guardá el piso y contale que la banda va en Q6. No dice la moneda: preguntá una vez y si no
contesta dejala afuera, es opcional, no la deduzcas del país. El PDF tiene 200 páginas: pedí las
del listado. El archivo no está donde dijo: listá `knowledge/negocio/` y mostrale qué hay. **No
encuentra la carpeta del proyecto**: imprimí la ruta absoluta con `pwd` —`Get-Location` en
PowerShell— y pasásela; la carpeta es ésa más `/knowledge/negocio`. **La imagen no llega**: no
insistas con el pegado, ofrecé la opción 2, que funciona en cualquier terminal.

### Paso 6 · Q6 · El rango de precio

**Objetivo.** El paso 6 del agente sabe cuándo un monto se le va de las manos.

**Hacé esto.** Preguntá, literal:

> ¿Abajo de qué monto no te conviene vender, y arriba de qué monto preferís meterte vos? Dos
> números.

Salteable: en nulo se apaga ese disparador y quedan el enojo y las palabras clave. Decilo así.

**Tenés que ver.** `"q6": {"minimo": 8000, "maximo": 40000}`, o `null` explícito.

**Si falla.** Da un solo número: preguntá cuál de los dos es. El máximo es menor que el mínimo:
decilo y pedí de nuevo. Vienen en otra moneda que el catálogo: el rango se compara contra el
precio del catálogo, tiene que ser la misma.

### Paso 7 · Q7 · La disponibilidad real

**Objetivo.** Existen horarios que existen.

**Hacé esto.** Preguntá, literal:

> ¿Qué días y a qué horas atendés, y cuánto dura una reunión? Por ejemplo: «lunes a viernes de 10
> a 13 y de 16 a 19, media hora cada una». Decime la zona horaria si no es la de esta computadora.

Expandís la franja a horarios concretos de los próximos cinco días hábiles, cada uno en ISO 8601
**con offset**, más `opciones: 3` (cuántos ofrece el paso 3, entre 1 y 5).

**Los horarios que ofrece el paso 3 salen de `disponibilidad` y de ningún otro lado.** Uno
inventado es fallo de la aserción 3 de `pruebas/caso-01.md`, aunque el mensaje esté perfecto.

**Tenés que ver.** En `config/agenda.yaml`, cada franja con su offset:

```yaml
franjas:
  - inicio: 2026-03-02T11:00:00-06:00
    duracion_min: 30
```

**Si falla.** Contesta «cuando sea»: sin franja el paso 3 no ofrece nada, pedí una. No dice la
zona horaria: usá la de la máquina y escribí el offset igual, explícito — una hora sin offset
leída en otro huso mueve la cita y nadie se entera hasta que el cliente no aparece. Ya tiene
Google Calendar: preguntá igual, `disponibilidad` es lo que el agente tiene permitido ofrecer, no
todo lo que el calendario tenga libre. Saltea: el paso 3 responde sin horarios y el 4 no agenda.

### Paso 8 · Q8 y Q9 · Escalación y canal interno

**Objetivo.** El paso 6 del agente sabe qué lo dispara y a dónde avisa.

**Hacé esto.** Dos preguntas, una por mensaje.

> ¿Qué palabra en un mensaje tiene que hacer que el agente se calle y te llame? Vienen puestas
> estas seis: humano, persona real, reclamo, abogado, estafa, cancelar. Agregá las tuyas o decime
> «así está bien».

> ¿Dónde te aviso cuando eso pasa? Un canal de Slack como `#ventas-escalaciones`, o un número
> interno de WhatsApp.

Guardás la lista **entera**, no sólo lo que agregó: reemplaza al default y conviene verla completa.

**Tenés que ver.** En `config/negocio.yaml`, `escalacion` con la lista completa y `canal_interno`
con el canal o `null`.

**Si falla.** Propone una palabra muy común («precio», «caro»): eso escala casi todos los chats,
decíselo y confirmá antes de guardarla. Saltea el canal: la escalación ocurre igual —el agente
deja de responder y la etapa queda en `escalado`— y lo que se pierde es el aviso, que alguien va
a leer de la salida a mano. Escribir el nombre del canal no conecta Slack: eso necesita
`SLACK_WEBHOOK_URL`, que es una credencial y va en el tramo 3, con `/conectar`.

### Paso 9 · Proyectá el YAML al contrato y cerrá `/configurar`

**Objetivo.** Cada respuesta aterriza en un archivo, a la entrada del agente llega sólo lo que
acepta, y quien instala termina el tramo con un cerrador que dice sus precios y ofrece sus
horarios.

**Hacé esto.** `contratos/entrada.schema.json` es `additionalProperties: false`: una clave de más
—`negocio`, `agente`, `tratamiento`— y la entrada entera rebota. Por eso la entrevista escribe
YAML amigable en `config/` y alguien lo **proyecta**. No se pasa tal cual:

```
config/playbook.yaml  playbook.objeciones[] → playbook.objeciones[]  (objecion, respuesta)
config/playbook.yaml  playbook.tono         → playbook.tono          (una sola cadena)
config/playbook.yaml  piso, rubrica         → NO van al contrato
config/negocio.yaml   catalogo[]            → catalogo[]             (nombre, precio, moneda)
config/negocio.yaml   rango                 → rango_precio.minimo / .maximo
config/negocio.yaml   escalacion[]          → palabras_escalacion[]
config/negocio.yaml   canal_interno         → canal_interno
config/agenda.yaml    franjas[]             → disponibilidad[]  (inicio con offset, duracion_min)
config/agenda.yaml    opciones              → opciones_horario  (1 a 5, default 3)
config/marca.yaml     negocio, agente       → NO van al contrato
```

**`config/playbook.yaml` es el único de los cuatro que ya viene con la forma del contrato, y esa
forma es una sola.** `objeciones` y `tono` van **anidados** bajo `playbook:`; `piso:` y `rubrica:`
van afuera, al mismo nivel que `playbook:`, y se quedan en `config/`. No hay una variante con
`objeciones` y `tono` al tope del archivo: el chequeo 20 de la compuerta lee el bloque `playbook:` y
lo valida contra este fragmento. Un archivo escrito plano no falla al escribirlo, falla acá, con el
contenido perfecto y la fase 2 dada por terminada:

```
playbook/no_valida  no hay un bloque `playbook:` adentro del archivo
```

Ese archivo lo escribe `blueprint/25-playbook.md` paso 7, que es su dueño único y muestra la misma
forma; acá sólo se proyecta lo que viaja.

**El tratamiento tampoco es un campo del contrato**: viaja adentro de `playbook.tono`, que es
texto libre. El nombre del negocio y el del agente no están ahí en absoluto: viven sólo en el
prompt de sistema, horneados en el prefijo estático. No los interpoles desde la petición — el
chequeo `cache-estatico` falla y, peor, el caché del prompt deja de acertar sin tirar un solo
error.

`mensaje`, `modo` y `confirmado` no salen de la entrevista ni de `config/`: los pone
`agente/servidor.py` en cada ciclo, cuando entra el mensaje. `version` y `umbrales` tampoco se
preguntan, pero sí salen de `config/`: `umbrales` queda en 70 y 40 y se cambia a mano. Nueve
claves de `config/` más tres del servidor son las doce propiedades del contrato de entrada, ni una
más — `contratos/entrada.schema.json` no acepta la trece.

Después corré la compuerta —`scripts/auditar.py`, veintitrés chequeos y nada se publica sin `pass`;
ver `blueprint/00-contrato.md` § 10—, **con el Python del venv**:

```bash
.venv/bin/python scripts/auditar.py            # macOS, Linux, WSL
```

```powershell
.venv\Scripts\python.exe scripts\auditar.py    # Windows con PowerShell o cmd
```

```bash
.venv/Scripts/python.exe scripts/auditar.py    # Git Bash sobre Windows
```

Y cerrá el tramo diciendo esto, que es lo que cambió:

> Listo. Ahora el cerrador dice tus precios y ofrece tus horarios, y escala solo con tus palabras.
> Corré `/probar` y hablá con él. Cuando tengas a mano las cuentas de WhatsApp, Google, Supabase y
> Slack, `/conectar` lo enchufa al mundo real.

**Tenés que ver.** Los tres YAML en `config/`, y en la salida del comando el veredicto `pass` con
varios salteados. `16 contrato-control` tiene que decir `[ok]`: es el control negativo, el que
distingue «validé y está bien» de «no validé nada». `15 contrato` sigue en `salteado` porque
todavía no hay fixtures de salida en `pruebas/`, y eso es correcto en la fase 2: los escribe
`blueprint/40-pruebas.md`.

**Si falla.**

- **`16 contrato-control` dice `salteado` por falta de `jsonschema`.** Lo corriste con el Python
  del sistema. Repetilo con el del venv, que es el de los tres bloques de arriba. Con ese salteo
  el veredicto entero baja a `parcial` y la salida es 3: un salteado no es un aprobado.
- **El veredicto es `fail` con un hallazgo de `08 secretos`.** Se escribió una credencial en el
  árbol. Pará, decí qué archivo es, y que se rote ese valor: el tramo 3 es el único que toca
  credenciales, y ninguna se escribe fuera de `.env`.
- **Un campo del contrato no valida.** Leé el campo que nombra el hallazgo: casi siempre es una
  clave del YAML que se coló sin proyectar, o un precio que quedó como texto en vez de número.

## Tramo 3 · Q10 a Q12 · desde `/conectar`

**Esto te va a llevar a cinco sitios**: Meta o Zernio, Google Cloud, Supabase, Slack y Anthropic.
Cada uno con su cuenta, su pantalla y su forma de esconder la clave. Si no los tenés abiertos,
hacé el primer tramo hoy y éste cuando tengas las cuentas: lo que ya configuraste no se pierde, y
mientras tanto el cerrador sigue andando sobre `demo`.

Todo lo de este tramo es salteable salvo `ANTHROPIC_API_KEY`.

### Paso 10 · Q10 · El proveedor

**Objetivo.** Queda elegido por dónde entran y salen los mensajes.

**Hacé esto.** Preguntá, literal:

> ¿Por dónde entran los mensajes?
>
> 1. **`demo`** — sin credenciales. Es el que te recomiendo hoy.
> 2. **`meta`** — WhatsApp Cloud API directo.
> 3. **`zernio`** — la pasarela sobre Meta.
>
> Con `demo` tenés el cerrador andando hoy y conectás WhatsApp el fin de semana. La verificación
> de negocio de Meta puede tardar días, y es la pared contra la que se muere una instalación por
> la mitad.

Elijas el que elijas, los mensajes entran por un webhook —el aviso automático que el proveedor le
manda a tu servidor cuando entra un mensaje; ver `blueprint/00-contrato.md` § 10—, y de ahí salen
dos cosas que dependen de esta respuesta: la firma que se verifica y el dedupe. El procedimiento
entero de cada proveedor está en `blueprint/31-proveedores.md`, que es su dueño.

`demo` no es un transporte falso: reproduce entregas grabadas desde `pruebas/fixtures/`, con los
mismos bytes crudos, la misma cabecera de firma y el mismo camino de deduplicación. Y a la salida
recorre el mismo camino que `meta` y `zernio` —las tres guardas, la `Idempotency-Key` y el mismo
cliente HTTP—: lo único distinto es su destino, `demo.invalid`, que contesta un transporte que trae
el kit. `.invalid` está reservado por la RFC 2606 y ningún resolver lo puede mapear a una
dirección, así que `demo` no sale a internet ni el día que ese transporte falte. Ver
`blueprint/31-proveedores.md`, pasos 1 y 3.

**Tenés que ver.** Una sola línea `WHATSAPP_PROVIDER=demo` —o `meta`, o `zernio`— en `.env`.

**Si falla.** Ya tiene el número aprobado: seguí a `meta` sin discutir, para eso preguntaste.
Elige `meta` o `zernio` y no tiene las credenciales a mano: dejá `demo`, anotá la elección y volvé
cuando las tenga. Cambia de proveedor después: cambia la verificación de firma, corré `/revisar`.

### Paso 11 · Q11 · Las credenciales del proveedor

**Objetivo.** Las variables del proveedor elegido están en `.env`, escritas por quien instala.

**Hacé esto.** **Ninguna credencial pasa por una tool call ni se escribe en el árbol.** Dos vías,
las dos las ejecuta la persona: que lo escriba con el prefijo `!` de bash, para que corra en su
terminal y no entre como texto mío — `! printf 'WHATSAPP_TOKEN=%s\n' 'el-valor' >> .env` — o que
abra `.env` en su editor y lo pegue. Vos nombrás la variable, decís de dónde sale y verificás que
esté puesta sin mirar el valor: `grep -o '^[A-Z_][A-Z0-9_]*=.' .env | cut -d= -f1`

Las trampas van **antes** de que las pise:

- **`WHATSAPP_TOKEN`.** El que aparece primero en la pantalla de la API dura 24 horas: alcanza
  para la primera prueba y al otro día el agente devuelve 401 sin decir por qué. El permanente
  sale de un usuario del sistema del Business Manager, con `whatsapp_business_messaging`.
- **`WHATSAPP_VERIFY_TOKEN`.** Lo inventás vos y tiene que quedar **idéntico** en `.env` y en el
  panel de Meta. La verificación llega como GET y se responde `hub.challenge` en **texto plano**:
  como JSON no sirve, Meta compara la respuesta cruda.
- **`META_APP_SECRET`.** Obligatoria con `WHATSAPP_PROVIDER=meta`, y es la que verifica que la
  entrega sea de Meta y no de cualquiera. Sale de developers.facebook.com → tu app →
  Configuración → Básica → **Clave secreta de la app**: está tapada detrás de «Mostrar» y te
  vuelve a pedir la contraseña de la cuenta. **La trampa**: no es `WHATSAPP_TOKEN` —ése autoriza a
  mandar— ni `WHATSAPP_VERIFY_TOKEN` —ése lo inventás vos y sólo sirve para el alta—. Son tres
  valores distintos de la misma pantalla de Meta, y el error de usar uno por otro se lee siempre
  igual: 401 en cada entrega, con cara de secreto mal copiado. Con `zernio` o `demo` no hace falta.
- **`ZERNIO_ACCOUNT_ID`.** Obligatoria y no se deduce de la clave: sin ella los medios no se bajan,
  y un audio que no se bajó a tiempo no se recupera nunca. El procedimiento entero de la bajada
  está en `blueprint/32-multimodal.md` paso 1, que es su dueño.
- **`ZERNIO_WEBHOOK_SECRET`.** La cabecera es `X-Zernio-Signature`: hex en minúscula y **sin** el
  prefijo `sha256=` que usa Meta.

**Tenés que ver.** El comando imprimiendo los nombres de las variables del proveedor elegido, y
ningún valor en pantalla. Con `meta` son cuatro: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`,
`WHATSAPP_VERIFY_TOKEN` y `META_APP_SECRET`.

**Si falla.** No existe `.env`: copiá `env.example`. No hay `grep` (Windows): que lo abra en el
editor y lo confirme él, no lo imprimas en el chat. Pegó la credencial en el chat: decilo en una
línea, pedile que la rote y no la escribas en ningún archivo. Quedó con comillas o un espacio al
final: el valor las incluye, mostrale la línea para que la corrija. **Falta `META_APP_SECRET` y el
proveedor es `meta`**: no sigas, porque el agente no va a poder verificar una sola firma y lo vas a
descubrir recién en el despliegue, con 401 en todas las entregas.

### Paso 12 · Q12 · Anthropic y qué más conectar

**Objetivo.** El modelo tiene clave, y cada paso que necesita un servicio sabe si lo tiene.

**Hacé esto.** Primero la única que no es salteable:

> Falta `ANTHROPIC_API_KEY`. Es la que hace falta siempre, también en `demo`: el demo se ahorra
> las credenciales de WhatsApp, no el modelo que redacta. `console.anthropic.com` → Settings →
> API keys → Create Key.

`MODELO` sale de `PINES.md` y de ningún otro lado. Después, de a una y sólo por lo que corresponda
a lo ya contestado:

- **Google Calendar**, si Q7 tuvo horarios: `GOOGLE_CALENDAR_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`.
  Crear la cuenta de servicio no alcanza: hay que compartir el calendario con la dirección que
  termina en `.iam.gserviceaccount.com`. Sin eso la conexión da OK y el evento nunca aparece.
- **Supabase**, para el paso 5: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`. Con la clave `anon` el
  paso 5 no falla ruidoso: escribe, la política de fila lo bloquea, y te enterás cuando buscás el
  lead y no está.
- **Slack**, sólo si en Q9 dijo Slack: `SLACK_WEBHOOK_URL`. Cada webhook queda atado a un canal.
- **OpenAI**, sólo si espera audios: `OPENAI_API_KEY`. Sin ella un audio frena el ciclo con el
  motivo escrito, nunca con una transcripción inventada. Las imágenes no la necesitan.

**Tenés que ver.** Por cada variable sin poner, una línea con qué paso queda sin correr: sin
Calendar no corre el 4, sin Supabase el 5 devuelve la fila y no la escribe, sin Slack el 6 escala
igual y el aviso queda en la salida.

**Si falla.** Perdió la clave de Anthropic: no se recupera, se muestra una sola vez al crearla; se
revoca esa y se hace otra. No la pone: parás con el motivo, porque sin modelo no hay agente ni en
`demo`.

### Paso 13 · Cerrá `/conectar`

**Objetivo.** Quien instala sabe qué quedó conectado, qué no, y qué le falta para que entre un
mensaje real.

**Hacé esto.** Escribí en `.wca-estado.json` los **nombres** de las variables puestas y las que
no —ningún valor—, y mostrá el resumen en tres líneas: proveedor elegido, servicios conectados,
servicios sin conectar con el paso que cada uno deja sin correr. Después:

> Con esto el agente ya puede hablar por WhatsApp de verdad. Corré `/revisar`, que verifica la
> firma del proveedor que elegiste, y después seguí con el despliegue.

**Tenés que ver.** El estado con los nombres de las variables y ningún valor, y un `/revisar` que
arranca sin pedir nada más.

**Si falla.** Cambió de proveedor a mitad del tramo: las variables del anterior quedan en `.env` y
no molestan, pero decilo, porque la firma que se verifica es la del que quedó en
`WHATSAPP_PROVIDER`. Quedó todo en `demo` porque no llegaron las cuentas: está bien, es el estado
esperado y no hay nada que compensar después; anotá cuáles faltan y volvé con `/conectar` cuando
estén. La compuerta y la suite corren enteras sobre `demo` y tienen que dar verde así: ninguna fase
posterior te va a pedir que exportes otro proveedor para pasar.

## Dónde aterriza cada respuesta

| Pregunta | Quién la hace | Qué determina | Archivo | Chequeo de `auditar.py` |
|---|---|---|---|---|
| Q1 negocio | `/armar-cerrador` | de qué negocio habla | `config/marca.yaml`, `agente/prompt.py` | 14 cache-estatico: en el prefijo, no interpolado de la petición |
| Q2 nombre del agente | `/armar-cerrador` | con qué firma | `config/marca.yaml`, `agente/prompt.py` | 14 cache-estatico |
| Q3 tratamiento | `/armar-cerrador` | tú / vos / usted en lo que sale | `config/marca.yaml` → `playbook.tono` | 14 cache-estatico, y 18 pruebas sobre el registro |
| Q4 objeciones | `blueprint/25-playbook.md` | qué contesta y qué deja al humano | `config/playbook.yaml` | 15 contrato: `respuesta.objecion_detectada` y `objecion_en_playbook` |
| Q5 catálogo | `/configurar` | los únicos precios que puede decir | `config/negocio.yaml` | 18 pruebas: un precio fuera del catálogo es fallo |
| Q6 rango | `/configurar` | cuándo escala el paso 6 por monto | `config/negocio.yaml` | 15 contrato: `handoff.motivo` = `precio_fuera_de_rango` |
| Q7 disponibilidad | `/configurar` | los horarios del paso 3 | `config/agenda.yaml` | 15 contrato: `horarios_ofrecidos`; 18 pruebas: cada uno en `disponibilidad` |
| Q8 palabras | `/configurar` | el disparador por palabra clave | `config/negocio.yaml` | 15 contrato: `handoff.motivo` = `palabra_clave` |
| Q9 canal interno | `/configurar` | dónde sale el aviso del paso 6 | `config/negocio.yaml` y `.env` | 08 secretos: `.env` ignorado y sin rastrear |
| Q10 proveedor | `/conectar` | qué firma se verifica y por dónde sale | `.env` | 17 firmas: los fixtures crudos reproducen el MAC |
| Q11 credenciales | `/conectar` | que el proveedor conecte | `.env`, nada más | 08 secretos: ninguna credencial en el árbol |
| Q12 Anthropic y el resto | `/conectar` | el modelo, y los pasos 4, 5 y 6 | `.env`, nada más | 10 modelo: el id sale de `PINES.md`, sin los cuatro que dan 400 |

Los números de la última columna son los que imprime la salida de la compuerta, en ese orden. Si
no coinciden con lo que ves, manda la salida del comando.

Ninguna respuesta de la entrevista fija una versión. Todas salen de `PINES.md`.

**Próximo archivo:** `blueprint/25-playbook.md`, que hace Q4 y escribe `config/playbook.yaml`. Es
lo que sigue del tramo 1, en la primera corrida. Los tramos 2 y 3 los abren `/configurar` y
`/conectar` cualquier otro día, y cuando terminan vuelven a quien los llamó.
