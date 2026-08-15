# 50 · El despliegue y el alta del webhook

**Fase 6.** Entrás con `/revisar` en `pass` —`parcial` quiere decir que un chequeo no corrió— y salís
con el servicio en una URL pública y el proveedor entregando mensajes de verdad.

El webhook —el aviso automático que el proveedor le manda a tu servidor cuando entra un mensaje; ver
`blueprint/00-contrato.md` § 10— es lo último que se enchufa, y el alta del webhook es el trámite de
decirle al proveedor a qué URL avisar. Las dos rutas ya existen en el servicio y son
`/webhook/meta` y `/webhook/zernio`: el proveedor va en la ruta, las dos se dan de alta, y un POST
dirigido al que no está configurado devuelve 404. La tabla entera está en
`blueprint/35-panel-api.md`.

**Invariante 4:** ninguna credencial pasa por una tool call tuya, y las plataformas invitan a lo
contrario. **Invariante 6:** la imagen y las versiones salen de `PINES.md`.

## Los tres destinos

**La laptop** sirve para la primera entrega y nada más: se cierra la tapa, el proceso se duerme, el
túnel se cae y los mensajes de esas horas no llegan.

**Un Mac Mini** gana cuando ya está prendido, cuando la base con los chats no puede salir de la
oficina, y cuando el volumen es alto: no pagás por uso. Pierde sin dominio propio, sin nadie que lo
reinicie un domingo, y donde el corte de luz de la oficina es el SLA: el reinicio en fallo y el
chequeo de salud que Railway da por cinco dólares, ahí los escribís vos.

**Railway** es el default. Preguntá y anotá la elección; no la elijas vos. Dos instancias contra la
misma base contestan dos veces a la misma persona.

---

### Paso 1 · Local: el servicio y el túnel

**Objetivo.** El webhook llega desde afuera, y sabés cuándo esa URL deja de existir.

**Hacé esto.** El servicio en una terminal:

```bash
.venv/bin/uvicorn agente.servidor:app --host 0.0.0.0 --port 8000
```

Y en otra, un túnel. Las dos opciones reales, **una o la otra**, cada una con su instalación aparte:

```bash
cloudflared tunnel --url http://localhost:8000   # sin cuenta, URL en trycloudflare.com
ngrok http 8000                                   # pide cuenta y authtoken
```

**Tenés que ver.** Una URL `https://…` del túnel, y `curl -s https://<url>/salud` devolviendo el
mismo JSON que `localhost:8000/salud`. Si no coincide, el túnel apunta a otro lado.

**Si falla.**

- **La URL cambia en cada arranque.** Normal en un túnel rápido, y deja el alta apuntando a una
  dirección muerta. Para que dure: túnel con nombre y dominio propio, o Railway.
- **Cerraste la laptop y no llega nada.** macOS suspende el proceso. `caffeinate -is` sirve con la
  tapa abierta; con la tapa cerrada y sin corriente, no hay comando.
- **`cloudflared: command not found`.** Declaralo y detenete: `brew install cloudflared` o el paquete
  oficial. No lo sustituyas por otro túnel sin decirlo.
- **502 en el túnel.** Uvicorn quedó en `127.0.0.1`. Va en `--host 0.0.0.0`.

---

### Paso 2 · Railway: el `railway.json` que no se completa

**Objetivo.** Railway construye con el `Dockerfile` del kit y el chequeo de salud contesta.

**Hacé esto.** Copiá `plantillas/infra/railway.json` y `plantillas/infra/Dockerfile` a la raíz,
verbatim. Después `railway login`, `railway init`, `railway up`.

**`railway.json` no trae `deploy.startCommand`, y esa ausencia es la pieza.** Quien la vea va a
querer completarla: un `startCommand` pisa el `CMD` del `Dockerfile`, que resuelve `${PORT:-8000}` en
el shell al arrancar. Railway inyecta `PORT` y el valor cambia entre despliegues; con el puerto a
mano la app escucha en otro lado y lo único que leés es `service unavailable`. Por eso `auditar.py`
trae el chequeo `railway-arranque`: un hash ve lo que cambió, una ausencia no.

`healthcheckPath` es `/salud`, y Railway **deja el despliegue viejo sirviendo hasta que el nuevo
contesta**: eso salva el ACK de cinco segundos de Zernio mientras desplegás.

**Tenés que ver.** `Deployed` en el tablero, y en `railway logs` un `Uvicorn running on
http://0.0.0.0:8080`. El número va a ser otro; que no sea 8000 es la señal de que `PORT` se resolvió.

**Si falla.**

- **`service unavailable`, el chequeo nunca pasa.** Apareció un `startCommand`, o el `Dockerfile`
  perdió la forma shell con `exec`. Copiá los dos archivos otra vez y no los edites.
- **No usó el `Dockerfile`.** El `railway.json` no quedó en la raíz, o le falta
  `"builder": "DOCKERFILE"`, y entonces adivina el runtime.
- **404 en el chequeo.** Es `/salud`, sin barra final y sin `/health`.
- **Se cae a los dos minutos en `Deploying`.** `/salud` toca la base sin timeout propio; ver
  `blueprint/35-panel-api.md`, paso 2.

---

### Paso 3 · Railway: Postgres, y el `sslmode` que asyncpg no entiende

**Objetivo.** La base es Postgres, el driver existe, y la URL llega como ese driver la acepta.

**Hacé esto.** `railway add --database postgres`. En el servicio de la app **referenciá** la variable
`DATABASE_URL` del servicio de Postgres en vez de copiar el valor: copiado a mano queda viejo la
primera vez que Railway rota la credencial.

Dos cosas van en el código y no en el tablero: la URL se reescribe a `postgresql+asyncpg://`, y
`sslmode` se saca de la cadena antes de conectar —lo entiende psycopg, no asyncpg, y llega como
argumento suelto hasta reventar—. Eso lo hace `normalizar_url()`, en `agente/base.py`, y el TLS se
pide por `connect_args`.

**Con Postgres el recordatorio de 24 horas queda detenido, y se dice al agendar.** El jobstore de
APScheduler es síncrono: pide la URL sin `+asyncpg`, o sea un driver síncrono, y ese driver **no
está fijado en `PINES.md`**. No se inventa uno acá: un pin que nadie verificó contra PyPI rompe el
invariante 6. Entonces `url_sincrona()` levanta `RecordatorioSinDriver`, el paso 4 deja
`cita.recordatorio_programado` en falso con el motivo escrito, y **la cita y la confirmación por
WhatsApp salen igual**. Con SQLite el recordatorio funciona entero, porque `sqlite3` es de la
biblioteca estándar y no hay nada que fijar. Cómo se levanta la detención —tres archivos que se
mueven juntos, ninguno de ellos un paso de tu construcción— está en `blueprint/00-contrato.md` § 8.
Si elegís Postgres, anotá en `PENDIENTES.md` que ese recordatorio no sale.

**Tenés que ver.** En `curl -s https://<tu-dominio>/salud`, `"base":"postgres"`. Si dice `sqlite`,
escribe en un archivo que el próximo despliegue se lleva puesto.

**Si falla.**

- **`ModuleNotFoundError: No module named 'asyncpg'`.** `asyncpg` está fijado en `PINES.md` y en
  `requirements.txt`, así que si lo ves, la imagen se construyó con otro `requirements.txt`: copiá
  el del kit otra vez y volvé a desplegar. El nombre vive adentro de la cadena y ningún import lo
  nombra, así que con SQLite esa línea nunca corrió y el error aparece recién acá.
- **`connect() got an unexpected keyword argument 'sslmode'`.** Es el párrafo de arriba.
- **`RecordatorioSinDriver` al agendar.** No es un defecto: es la detención declarada. La cita salió
  igual. Decíselo a quien instala en vez de tapar la excepción.
- **`password authentication failed` después de andar bien.** Copiaste el valor en vez de referenciar
  la variable del servicio.

---

### Paso 4 · Las variables, sin que ninguna pase por una tool call

**Objetivo.** El servicio tiene lo que necesita y ningún valor quedó en el transcripto.

**Hacé esto.** Los nombres salen de `env.example`. Los valores los escribe quien instala, de dos
formas y de ninguna otra: en el tablero, Variables → New Variable, pegando en el navegador; o con el
prefijo `! ` en el prompt, que corre la línea en bash sin que vos generes una tool call.

```
! railway variable set ANTHROPIC_API_KEY='sk-ant-...'
```

**Vos no corrés `railway variable set` con un valor real, nunca:** una tool call queda en el
transcripto y el transcripto se guarda. Si te dictan una clave, no la escribas; decí cuál de las dos
formas usar. `.env` tampoco se sube: ya está en `.gitignore`, agregalo a `.railwayignore`.

**Las de Meta son tres, y se confunden todo el tiempo.** Con `WHATSAPP_PROVIDER=meta` van las tres,
y `META_APP_SECRET` es la que más se olvida porque no se usa para mandar nada:

| Variable | Para qué | De dónde sale |
|---|---|---|
| `WHATSAPP_TOKEN` | autoriza a mandar mensajes | el token de la app de WhatsApp |
| `WHATSAPP_VERIFY_TOKEN` | sólo para el alta del webhook | lo inventás vos |
| `META_APP_SECRET` | **verifica la firma de cada entrega** | Configuración → Básica → Clave secreta de la app |

`env.example` nombra las tres. Sin `META_APP_SECRET` cargada en Railway el servicio desplegado no
verifica una sola firma y contesta 401 en todas las entregas, con cara de secreto mal copiado. Con
`zernio` no hace falta: ahí firma `ZERNIO_WEBHOOK_SECRET`. Ver `blueprint/00-contrato.md` § 7.

**Tenés que ver.** En `/salud`, `faltan` vacío o solo con las opcionales que este negocio no usa.
Con el proveedor en `meta`, `META_APP_SECRET` no puede estar en esa lista: es una requerida del
proveedor, y `/salud` las nombra igual que a las opcionales. Las tres listas —`SIEMPRE`,
`POR_PROVEEDOR` y `OPCIONALES`— están en `blueprint/35-panel-api.md`, paso 2.

```bash
curl -s https://<tu-dominio>/salud
```

**Miralo antes y después de cargarla, y no sólo después.** «No está en `faltan`» tiene dos causas
y desde afuera se leen igual: que esté cargada, o que la lista no la mire. Si `faltan` la nombra
antes y deja de nombrarla después, el criterio se cumplió; si no la nombró nunca, este paso pasó
por vacío y el 401 aparece recién cuando entra el primer mensaje de verdad.

Ese es un modo de falla del código y no del despliegue: con `faltan = [v for v in OPCIONALES …]`
—sin sumar `requeridas`— ninguna requerida puede salir nunca en esa lista, y el kit entero da
verde. El control positivo local está en `blueprint/35-panel-api.md`, paso 2, y lo afirman los
nodos `test_salud_*` de `pruebas/test_panel.py`. Corrélos antes de subir:

```bash
.venv/bin/python -m pytest pruebas/test_panel.py -q -k salud
```

**Si falla.**

- **`faltan` nombra una que sí cargaste.** Está en otro entorno, o en el servicio de Postgres en vez
  del de la app: son dos listas distintas.
- **`faltan` nombra `META_APP_SECRET` y el proveedor es `meta`.** No pases al paso 5. El alta del
  webhook va a dar verde igual —ese trámite usa `WHATSAPP_VERIFY_TOKEN`— y el 401 aparece recién
  cuando entra el primer mensaje de verdad. Cargala con una de las dos formas de arriba y volvé a
  mirar `/salud`.
- **`faltan` no la nombró nunca, ni con el servicio recién creado y sin una sola variable.** No es
  que esté cargada: la lista no la mira. Corré el control positivo de `blueprint/35-panel-api.md`,
  paso 2, y arreglá la comprensión de `/salud` antes de seguir. Este paso, tal como está escrito,
  no distingue los dos casos por sí solo.
- **401 del modelo con la clave puesta.** Se pegó con un salto de línea o con comillas adentro del
  valor. Compará el largo antes de dudar de la clave.
- **La clave se pegó en el chat.** No sale del transcripto. Revocala, creá otra, repetí el paso.

---

### Paso 5 · Meta: el alta, y el token idéntico carácter por carácter

**Objetivo.** Meta valida la URL y empieza a entregar mensajes.

**Hacé esto.** developers.facebook.com → tu app → WhatsApp → Configuración → Webhooks → Editar. URL
`https://<tu-dominio>/webhook/meta` —esa ruta exacta, con el proveedor adentro: es la que el
servicio tiene dada de alta—, y como token de verificación **el mismo valor que
`WHATSAPP_VERIFY_TOKEN` en el entorno del servicio**. Verificar, guardar, y después suscribir el
campo `messages`: sin esa suscripción el alta queda verde y no llega un solo mensaje.

Meta valida con un GET que trae `hub.challenge`, y el servicio lo devuelve tal cual y como **texto
plano**. Ese GET no lleva token del panel: es público a propósito.

**Tenés que ver.** El webhook verificado en la consola, y en `railway logs` un `GET /webhook/meta`
con 200 en el momento en que apretaste Verificar.

**Si falla.**

- **"No se pudo validar la URL de devolución de llamada o el token de verificación."** Es el único
  mensaje que da Meta y no dice cuál de las dos cosas falló. En orden: **el token no es idéntico** —un
  espacio al final en `.env`, una comilla adentro, un salto de línea al pegarlo—, y se compara por
  largo, no a ojo, contra el campo de la consola:
  `.venv/bin/python -c "from dotenv import dotenv_values;print(len(dotenv_values('.env')['WHATSAPP_VERIFY_TOKEN']))"`;
  devolviste el `hub.challenge` como JSON y las comillas son dos bytes de más; la URL no termina en
  `/webhook/meta` o va en http; `WHATSAPP_PROVIDER` dice otra cosa y da 404. Reproducilo local con el
  `curl` de `blueprint/35-panel-api.md`, paso 3, antes de volver a la consola.
- **Verificado, y no llega nada.** Falta suscribir `messages`.
- **401 en cada entrega.** La firma se verifica con el **App Secret** de la aplicación, que no es
  `WHATSAPP_TOKEN` ni `WHATSAPP_VERIFY_TOKEN`: es `META_APP_SECRET`, y va cargada en Railway como
  las otras dos. Volvé al paso 4. Está tapada detrás de «Mostrar» y Meta te vuelve a pedir la
  contraseña de la cuenta, así que se copia mal seguido: compará por largo, no a ojo.

---

### Paso 6 · Zernio: el alta, y el primer mensaje real

**Objetivo.** Zernio entrega, la firma verifica, y un mensaje de verdad queda en la bandeja.

**Hacé esto.** zernio.com → panel → Desarrolladores → Webhooks. URL
`https://<tu-dominio>/webhook/zernio`, suscribí el evento de mensaje entrante, guardá. **El secreto
se muestra una sola vez**: copialo a `ZERNIO_WEBHOOK_SECRET` con una de las formas del paso 4; si lo
perdiste, generá otro y reiniciá, porque el viejo deja de firmar. Después, con el proveedor que sea,
escribile al número del negocio desde tu teléfono.

**Tenés que ver.** `POST /webhook/<proveedor>` con 200 en menos de cinco segundos, y con el comando
`/bandeja` un borrador del paso 3 con su panel de razonamiento. **Nadie recibió respuesta todavía, y
eso es correcto:** el default es `borrador`.

**Si falla.**

- **401 en cada entrega.** Mirá el formato antes que el valor: hex minúscula pelada, sin el `sha256=`
  de Meta, y sobre el cuerpo crudo. Reserializar pasa las pruebas locales y falla las entregas reales.
- **La misma persona contestada cuatro veces.** Contestaste 200 después del modelo. El orden es
  cuerpo, firma, dedupe por `X-Zernio-Event-Id`, 200, y recién ahí el modelo.
- **Audios e imágenes rotos.** La bajada va con `Authorization` —sin ella es 401— y ocurre al
  recibir el mensaje, no cuando alguien lo necesita: Meta suelta el archivo a los pocos días y desde
  ahí da 400 para siempre. El procedimiento entero vive en `blueprint/32-multimodal.md`, paso 1, y
  no se repite acá.
- **El borrador trae precios que no existen.** Pará: no llegó el catálogo, y ningún precio ni plazo
  sale de otro lado. Revisá `/configurar` antes de aprobar nada.

---

## Lo que sale, con fecha

Verificado el 2026-08-13. Estos números se mueven; mirá las páginas antes de prometerle un costo a
alguien.

- **Railway.** El plan Hobby son USD 5 por mes que **incluyen** USD 5 de uso: debajo pagás 5, arriba
  pagás el uso. Contá el Postgres como un segundo servicio prendido las 24 horas: con base vivís
  alrededor del límite, no muy por debajo.
- **Anthropic.** `claude-opus-5` cuesta USD 5 por millón de tokens de entrada y 25 por millón de
  salida. Un ciclo —un mensaje, los seis pasos, una respuesta— mueve 6 a 8 mil tokens de entrada
  entre prompt e historial, y unos cientos de salida: **3 a 5 centavos de dólar por mensaje**, y 0.30
  a 0.50 una conversación de diez idas y vueltas. Con caché de prompt cae a la mitad. Lo que no se
  ve: el thinking adaptativo viene prendido por default y se factura como salida, y el historial
  crece en cada turno, así que el décimo mensaje cuesta más que el primero.
- **WhatsApp con `meta`.** Hoy, si el cliente escribió primero y contestás dentro de las 24 horas, el
  mensaje no se cobra. Se cobran las plantillas, por mensaje entregado y por país: del orden de USD
  0.01 en India a 0.025 en Estados Unidos, marketing arriba y utility más abajo. Un cerrador que solo
  contesta casi no paga; el recordatorio de 24 horas antes de la cita sí, porque sale fuera de la
  ventana. **El 1 de octubre de 2026 esto cambia:** Meta pasa a cobrar por mensaje de negocio,
  incluidas las respuestas de servicio y las utility adentro de la ventana.
- **WhatsApp con `zernio`.** Cobra por cuenta conectada y no por mensaje: las dos primeras gratis, de
  la tercera a la décima USD 6 por mes cada una. Encima pagás igual las plantillas de Meta.

Las dos sorpresas que enojan: Anthropic crece con la cantidad de chats y no con la de clientes, y las
plantillas aparecen recién cuando empezás a mandar recordatorios.

## Lo que tarda, de verdad

Desplegar son minutos; cargar variables y dar de alta el webhook, media hora si las credenciales ya
existen. **Lo que no depende de este repo es la verificación del negocio en Meta:** entre uno y cinco
días hábiles con los papeles en orden, y hasta treinta cuando falta algo o el primer intento se
rechaza. Sin eso el número queda en modo de prueba, hablándole solo a los teléfonos que agregues a
mano. Las plantillas se aprueban aparte, normalmente en horas, y se rechazan sin gran explicación.

Por eso acá no dice "menos de 30 minutos". El repo se despliega en minutos; el negocio se verifica en
días, y eso conviene empezarlo antes de tocar el código.

## Qué quedó hecho

El servicio arriba con el `Dockerfile` y el `railway.json` sin editar; Postgres por referencia, con
el driver fijado, el `sslmode` fuera de la cadena y el recordatorio de 24 horas declarado detenido si
elegiste Postgres; las variables cargadas sin que ninguna pasara por una tool call, incluida
`META_APP_SECRET` si el proveedor es `meta`; el alta del webhook contra `/webhook/<proveedor>` con el
token idéntico de los dos lados; y una entrega real que terminó en un borrador esperando aprobación.

Anotá en `.wca-estado.json` la `fase` en `despliegue`, el destino, el dominio y el proveedor.
**Ninguna credencial ahí**: el nombre de la variable y si está puesta.

**Próximo archivo:** `blueprint/60-bandeja.md`, que resuelve borradores de a uno y trae la compuerta
numérica de `/soltar`.
