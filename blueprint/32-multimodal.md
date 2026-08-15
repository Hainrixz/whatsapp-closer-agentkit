# 32 · Audio e imagen

Fase 3. Lo que entra y no es texto, y cuatro de los seis cuerpos de paso. Va después de
`blueprint/31-proveedores.md`.

**Este archivo es el dueño único de la bajada de medios.** Vive en `agente/medios.py`, la llama el
paso 1 **al desencolar, después del 200**, y nunca el handler del webhook —el webhook es el aviso
automático que WhatsApp le manda a tu servidor cuando entra un mensaje; ver
`blueprint/00-contrato.md` § 10—. Ningún otro archivo vuelve a especificar el procedimiento:
`31-proveedores.md` paso 5 y `50-despliegue.md` paso 6 lo nombran en una línea y remiten acá. La
regla entera, con la tabla de quién dice qué, está en `blueprint/00-contrato.md` § 6.

**El audio se transcribe con la API de Whisper (`OPENAI_API_KEY`); sin esa clave el paso 1 se
detiene con el motivo escrito.** **La imagen la lee el modelo de Anthropic que ya está
configurado: no hace falta ninguna credencial extra.** Lo segundo sorprende, y por eso va acá
arriba: no hay `VISION_API_KEY` que conseguir.

**Invariante 3** —un invariante es una de las seis reglas de `CLAUDE.md` que ningún archivo puede
romper, y cada una tiene su chequeo en la compuerta, que es `scripts/auditar.py`; ver
`blueprint/00-contrato.md` § 10—: **un solo cliente HTTP, con `timeout=` en la llamada.**

**Invariante 2: ningún mensaje a un contacto sale si no es por `enviar()`** —tampoco el «no pude
escuchar tu audio»—. Se decide **por destino**: lo que la compuerta marca es una URL de mensajería
escrita fuera de `agente/enviar.py`, con el verbo que sea y en el archivo que sea. Este archivo
manda escribir dos salidas que no son mensajes —la transcripción de Whisper y la imagen que lee el
modelo— y ninguna de las dos es un hallazgo. La tercera, el aviso interno del paso 6, tiene dos
formas: por Slack no es un mensaje de WhatsApp y tampoco es un hallazgo; **por número interno sí lo
es, y por eso sale por `enviar()`** —paso 5, y `blueprint/31-proveedores.md` paso 1—. La regla
entera está en `blueprint/00-contrato.md` § 12.

---

### Paso 1 · Bajá el medio al desencolar, no en el handler

**Objetivo.** Existe `agente/medios.py`, la bajada corre como primera acción del paso 1 —después del
200 y fuera del handler—, y la ruta del archivo queda en `mensaje.media_local`.

**Hacé esto.** El módulo que `31-proveedores.md` anticipa. **No escribe el host: importa
`BASE_META` y `BASE_ZERNIO` de `agente/enviar.py`**, que es donde `blueprint/00-contrato.md` § 4
los puso. Bajar un medio no es mandar un mensaje y la compuerta no lo marca
—`{BASE_META}/{media_id}` no es una URL de mensajería, § 12—: el import se pide igual, por un
motivo más chico. La versión de la Graph escrita en dos archivos se desincroniza la primera vez que
alguien sube una y no la otra, y eso se lee como un 400 raro meses después.

En Zernio es una llamada: `GET {BASE_ZERNIO}/whatsapp/media/{media_id}?accountId=…` con
`Authorization: Bearer sk_…`. **No es un enlace público**: sin la cabecera devuelve 401, y
pasárselo pelado a una API de visión devuelve 401 del otro lado. En Meta son dos:
`GET {BASE_META}/{media_id}` trae un JSON con `url` y `mime_type`, y esa `url` —que vive en el CDN,
no en la Graph— se baja **también** con el `Authorization`, y caduca en minutos.

Y se baja **al recibirlo**, no cuando hace falta: Meta lo suelta a los pocos días —unos siete, a
veces menos— y desde ahí esa llamada devuelve 400 para siempre. Ese 400 no se recupera.

**Dónde corre, que es la mitad que se pierde.** La tensión con el presupuesto de cinco segundos de
Zernio se resuelve por ubicación, no por velocidad: **la bajada no va nunca en el handler** —el
handler es la función que atiende la petición del webhook y contesta el 200—. Va adentro del paso 1,
lo primero que corre el consumidor al desencolar: cuando saca el mensaje de la cola, con el 200 ya
contestado. Puesta en el handler, una nota de voz se come el presupuesto, el proveedor da la entrega
por fallada y reintenta hasta siete veces —entrega al-menos-una-vez, `blueprint/00-contrato.md`
§ 10—, y la misma persona termina contestada cuatro veces.

El archivo queda en `medios/<contacto_id>/<media_id>` y la ruta en `mensaje.media_local`; el resto
del ciclo lee esa ruta y no vuelve a llamar al proveedor. Agregá `/medios/` a `.gitignore`, anclado
con `/`: ahí caen notas de voz y fotos de tus clientes.

**Tenés que ver.** Que el módulo del webhook no nombre la bajada, y el camino único en verde. El
intérprete es el del `.venv` del proyecto y no el `python3` del sistema, que no trae `jsonschema`:
ver `blueprint/00-contrato.md` § 5.

```bash
grep -rl "medios" agente/*.py
.venv/bin/python scripts/auditar.py | grep "enviar-unico"
```

```
agente/medios.py
  [ok      ] 13 enviar-unico       12 módulo(s) revisados
```

El número del chequeo y lo que venga a su derecha cambian con lo que lleves escrito; lo que importa
es el `[ok`. **Sobre el `--json` no se puede hacer este grep**: la salida va indentada y el `id`, el
`titulo` y el `estado` caen en tres líneas distintas, así que un patrón que los pida juntos no
imprime nada nunca —ni con el chequeo en verde ni con el chequeo en rojo—.

Un solo archivo en la primera línea. El que llama vive en `agente/pasos/`, no en la raíz del
paquete: el handler contesta el 200 y no toca un medio.

**Si falla.**

- **`enviar/salida_de_mensajeria` en `agente/medios.py`.** En este módulo quedó escrita una URL de
  mensajería entera: `…/<id>/messages` de Meta, o `…/inbox/conversations/…` de Zernio. Acá se bajan
  medios y no se manda nada. Si lo que te hacía falta era la base, importá `BASE_META` de
  `agente/enviar.py`. Y si el hallazgo es `enviar/segundo_camino`, lo que escribiste fue el host
  pelado: mismo arreglo, mismo import.
- **401 en la bajada.** Falta el `Authorization`, o lo mandaste en la primera llamada de Meta y no
  en la segunda. Las dos lo piden. En Zernio, falta `ZERNIO_ACCOUNT_ID` y la URL queda a medias.
- **400 en Zernio, y siempre el mismo.** Meta ya soltó el archivo: paso 1 `fallado` con el motivo.
  Ver el Paso 4.
- **El proveedor reintenta siete veces la misma entrega.** Bajaste el medio antes del 200 y el
  handler pasó los cinco segundos. Movelo al paso 1, que corre al desencolar.
- **No hay `grep` (Windows).** Corré `.venv\Scripts\python.exe scripts\auditar.py` a secas y leé la
  línea 13. Cambia el intérprete, no el resto del comando: `blueprint/00-contrato.md` § 5.

---

### Paso 2 · El audio se transcribe, o el ciclo para

**Objetivo.** Con la clave puesta, `mensaje.texto` tiene la transcripción. Sin la clave, nadie
adivina qué decía.

**Hacé esto.** `POST https://api.openai.com/v1/audio/transcriptions`, multipart, con el cliente
único:

```python
r = await CLIENTE.post(URL_TRANSCRIPCION,
                       headers={"Authorization": f"Bearer {ajustes.openai_api_key}"},
                       files={"file": (nombre, datos, tipo)},
                       data={"model": "whisper-1"},
                       timeout=60.0)     # sin `temperature`: ver abajo
```

WhatsApp manda las notas de voz en OGG/Opus y Whisper las acepta tal como llegan: no hay
conversión previa, que es un paso menos que puede fallar en tu máquina. Ver S07 en `SUPUESTOS.md`.

**Ese `post` no choca con el invariante 2, y hace falta decirlo.** El destino es `api.openai.com`:
una transcripción no es un mensaje a un contacto, y la compuerta mira el destino. Enunciado por
verbo —«ningún `.post` fuera de `agente/enviar.py`»— este renglón y el chequeo 13 no podían ser los
dos ciertos, y el que se retiró fue el enunciado: `blueprint/00-contrato.md` § 12. Lo mismo vale
para el paso 3, que le manda la imagen al modelo, y para la mitad de `avisar_interno()` que postea
a Slack. La otra mitad, la del número interno, sí es un mensaje de WhatsApp: no se defiende, sale
por `enviar()`.

**No le pases `temperature`.** La API la acepta y el chequeo `modelo` la marca igual:
`modelo/parametro_400` mira los argumentos con nombre de **todo** `agente/`, no sólo la llamada a
Anthropic. Los cuatro prohibidos son `budget_tokens`, `temperature`, `top_p` y `top_k`.

El id del transcriptor es un literal de este módulo: `PINES.md` fija el modelo que redacta, no
éste. Si un día cambia el nombre, acá está escrito dónde tocarlo.

**Tenés que ver.** Con la clave, el texto en `mensaje.texto` y `S07` en `supuestos`. Sin la clave,
esto y nada más:

```
Llegó un audio de 5215500000000 y no lo puedo transcribir: falta OPENAI_API_KEY.
Paso 1: fallado. Pasos 2 a 6: salteados. No adivino qué decía el audio.
Ponés la clave en .env y lo reprocesás, o lo escuchás vos y contestás desde /bandeja.
```

**El renglón nombra al contacto por `mensaje.de`, el número.** Este texto lo lee quien atiende el
negocio, no el kit: un identificador interno pegado ahí no le dice nada a nadie. Cuando el número
viene nulo —el contacto escribe con nombre de usuario de WhatsApp, que desde abril de 2026 pasa—, se
dice con esas palabras y el identificador va etiquetado y al final:

```
Llegó un audio de un contacto que no muestra su número (id interno bsu_01HZK3M9QX7T2VW4) y no lo
puedo transcribir: falta OPENAI_API_KEY.
```

El nombre que muestra WhatsApp no está en el contrato de entrada ni en la dataclass `Mensaje`: no lo
inventes acá. Lo que hay es el número y el `contacto_id`, en ese orden de preferencia.

**Si falla.**

- **El chequeo 13 marca este mismo `CLIENTE.post(`.** No es tu build: es una compuerta vieja. La de
  hoy decide por destino, y `api.openai.com` no es un destino de mensajería, así que este `post` no
  le puede salir en ningún hallazgo. Se lee así:

  ```
  [FALLA] 13 enviar-unico
     [ERROR] enviar/salida_suelta   agente/medios.py:100   `CLIENTE.post(` fuera de agente/enviar.py
  ```

  **Ese id es la firma de la compuerta retirada, no un hallazgo tuyo.** `enviar/salida_suelta`
  decidía por verbo y por archivo, y hoy no está escrito en la compuerta:
  `grep -n salida_suelta scripts/auditar.py` no imprime nada. Los dos que sí emite son
  `enviar/salida_de_mensajeria` y `enviar/segundo_camino`. Confirmalo abriendo el chequeo 13 de
  `scripts/auditar.py`: si tiene una tupla de métodos y un `EXIMIDOS_DE_ENVIAR`, es la vieja. El
  enunciado que vale está en `blueprint/00-contrato.md` § 12, y el `post` a `api.openai.com` se
  queda donde está.
- **`modelo/parametro_400` en `agente/medios.py`.** Es el `temperature` de arriba. Sacalo, no lo
  comentes al lado.
- **401 de OpenAI.** La clave es de otro proyecto, o venció. No es la de Anthropic: son dos.
- **413, o `Maximum content size limit exceeded`.** Whisper corta en 25 MB. Una nota de voz no
  llega; un audio reenviado sí, y ahí el paso 1 queda `fallado` con el motivo.
- **Volvió una transcripción sin clave puesta.** Eso es una invención, y es fallo de la aserción 1.
- **`media_local` en nulo y transcripción igual.** Le pasaste el `media_id` en vez de los bytes.

---

### Paso 3 · La imagen la lee el modelo que ya tenés

**Objetivo.** Una imagen entrante se describe sin conectar nada nuevo.

**Hacé esto.** El bloque va en el **turno de usuario**, con los bytes de `media_local` en base64:
`{"type": "image", "source": {"type": "base64", "media_type": tipo, "data": b64}}`.

Tres reglas. **Nunca `source.type = "url"`** con el enlace del proveedor: no es público, 401.
**Nunca en el prefijo del sistema**: el prefijo tiene que ser idéntico byte por byte en cada
petición, y una imagen adentro pone la tasa de acierto del caché en cero sin un error visible. **Y
el `media_type` sale del `mime_type` de la bajada**, no de la extensión que le pusiste al archivo.
Se aceptan `image/jpeg`, `image/png`, `image/gif` y `image/webp`; WhatsApp manda fotos en jpeg y
stickers en webp.

**Tenés que ver.** `grep -rln '"type": "image"' agente/` nombra el paso 1 y ningún otro archivo, y
`.venv/bin/python -c "from agente.prompt import prompt_de_sistema as p; print(p() == p())"` sigue
imprimiendo `True`.

**Si falla.**

- **`cache/prefijo_variable`.** La imagen entró al prefijo del sistema. Va en el turno de usuario.
- **400 `Could not process image`.** El `media_type` no cuadra con los bytes: casi siempre un
  sticker webp guardado como `.jpg`.
- **400 por tamaño.** El límite es 5 MB por imagen y base64 infla cerca de un tercio: una foto de
  4 MB no entra. Reducila, o dejá el paso `fallado` con el motivo.
- **401 desde el lado de Anthropic.** Le pasaste la URL del proveedor en vez de los bytes.

---

### Paso 4 · Las tres formas de no conseguir los bytes

**Objetivo.** Las tres frenan igual, y la salida sigue trayendo seis pasos.

**Hacé esto.** Son las de la aserción 1 de `pruebas/caso-01.md`:

| Qué pasó | Se recupera |
|---|---|
| `media_id` y `media_url`, los dos en nulo | no hay de dónde |
| `media_url` que ya caducó | sí, con `media_id`, si todavía no lo soltaron |
| `media_id` cuya bajada devuelve 400 | **nunca**: Meta ya soltó el archivo |

En las tres, la misma conducta: paso 1 `fallado` con el motivo, pasos 2 a 6 `salteado`, `estado`
en `detenido` y una `pregunta` que se conteste en una línea. Y lo que **no** se hace: contestarle
al contacto «mandámelo por escrito» por un camino aparte. Ese texto es un borrador del paso 3 y
sale por `enviar()` con confirmación, como cualquier otro.

**Tenés que ver.** Seis registros, siempre. El chequeo `contrato` dice `1 salida(s) válidas, con
los seis pasos en orden`.

**Si falla.**

- **Menos de seis pasos.** Alguien cortó el ciclo con un `return` temprano en vez de presembrar los
  seis en `agente/salida.py`. Seis entran y seis salen.
- **`estado` en `ok` con el paso 1 en `fallado`.** No atendiste el mensaje: no lo pudiste leer.
- **`pregunta` con dos preguntas, o con el estado en `parcial`.** Una sola, y sólo con `detenido`.

---

### Paso 5 · Escribí cuatro de los seis cuerpos de paso

**Objetivo.** Existen `agente/pasos/paso_1_contexto.py`, `paso_2_calificar.py`,
`paso_3_responder.py` y `paso_6_handoff.py`, y `agente/enviar.py` tiene una función más:
`avisar_interno()`. Los cuerpos de los pasos 4 y 5 los escriben los dos archivos que siguen, con sus
integraciones.

**Hacé esto.** Un archivo por paso, cada uno mutando **su** registro de la lista que ya presembró
`agente/salida.py` —el paso de `salida.py` está en `blueprint/30-generacion.md`—. Ninguno arma una
lista nueva, ninguno filtra y ninguno hace `append`: seis entran y seis salen.

Van acá y no en `blueprint/30-generacion.md` porque los cuatro importan `enviar()` y `medios.py`, y
recién ahora los dos existen. Escritos antes, importan funciones que todavía no están.

- **Paso 1, contexto.** Primera acción: la bajada del Paso 1 de este archivo. Después traduce el
  `Mensaje` de `agente/proveedores/base.py` al `mensaje` del contrato —son dos cosas distintas con
  el mismo nombre; ver `blueprint/00-contrato.md` § 10— y busca ficha e historial por `contacto_id`.
  Con el teléfono nulo, `contacto.numero` va como `bsuid:<id>`: nunca vacío y nunca un número
  inventado.
- **Paso 2, calificación.** Score de 0 a 100 con el motivo en una línea, `temperatura` coherente
  —caliente desde 70, tibio de 40 a 69, frío abajo de 40— y **`presupuesto` en nulo si el contacto
  no lo dijo**. Invariante 5: lo que no está en el mensaje ni en el catálogo, no existe.
- **Paso 3, respuesta.** Escribe afuera, así que **el default es `borrador`** —redacta, muestra y
  espera confirmación explícita; ver `blueprint/00-contrato.md` § 10—. Con `confirmado` en falso el
  registro queda `sin-confirmar` con el motivo y `respuesta.enviado` no se toca. La objeción sale
  del playbook y se escribe en `respuesta.objecion_detectada`, con ese nombre y no `objecion`. Los
  tres horarios salen de `disponibilidad` y de ningún otro lado. Y sale por `enviar()`: este paso no
  arma su propio envío ni nombra el destino.
- **Paso 6, handoff.** Tres disparadores: enojo, un precio fuera de `rango_precio` y una palabra de
  `palabras_escalacion`. Deja de contestar en ese chat, escribe `handoff` con el disparador y llama
  a `avisar_interno()`, que importa de `agente/enviar.py` y le pasa el `modo` y el `confirmado` de
  la entrada, los mismos dos que mira el paso 3.
- **`avisar_interno()`, y va adentro de `agente/enviar.py`.** Es el aviso a `canal_interno`, y
  `canal_interno` tiene dos formas —«un canal de Slack, o un número interno de WhatsApp si no hay
  Slack», `contratos/entrada.schema.json`—. **Las dos formas no se comportan igual, y la diferencia
  no es un detalle**: una es un POST a un webhook y la otra es un mensaje de WhatsApp.

  | `canal_interno` | Por dónde sale | En `borrador` | Guardas |
  |---|---|---|---|
  | `#un-canal` de Slack | `POST` a `SLACK_WEBHOOK_URL`, con el cliente de `agente/http.py` y `timeout=` | **sale** | ninguna: no sale del número del negocio y no toca su calificación |
  | `5215500000099` | `enviar()`, con `a_numero_interno` | **no sale**: espera confirmación | las cuatro, con una exención declarada |

  **Por qué el número no sale en `borrador`.** Porque es un mensaje de WhatsApp con todo lo que eso
  implica: sale del número del negocio, cae bajo la ventana de 24 horas y pesa en la calificación
  igual que el que le llega a un cliente. Meta no distingue el número de tu compañero del de un
  cliente. El modo promete una cosa sola —nada sale sin confirmación explícita— y una excepción
  para «esto es interno» es una excepción que del otro lado no existe. Se confirma con el mismo
  `confirmado: true` que deja salir la línea del paso 3: una confirmación por turno, y sale todo lo
  que ese turno quería mandar.

  ```python
  PLANTILLA_INTERNA = "escalacion_interna"
  IDIOMA_PLANTILLA_INTERNA = "es"      # el de la plantilla que aprobaste, no el del negocio

  _SEPARADORES = " -()+. ‑–"


  def numero_interno(canal_interno: str | None) -> str | None:
      """Los dígitos de `canal_interno` si es un número de WhatsApp, o `None` si es un canal.

      Por dígitos y no por texto: `+52 155 0000 0099` y `5215500000099` son el mismo destino.
      """
      if not canal_interno:
          return None
      limpio = "".join(c for c in str(canal_interno).strip() if c not in _SEPARADORES)
      return limpio if limpio.isdigit() else None


  def conversacion_interna(numero: str, conversacion_id: str) -> str:
      """La conversación del canal interno para ESTA escalación. Una fila por chat escalado.

      Con una sola fila por número, `salientes_seguidos` llega a `MAX_SEGUIDOS` a la tercera
      escalación del día y el canal se apaga solo y en silencio. Una por chat escalado deja que
      el repetido siga mordiendo donde tiene que morder —el mismo chat avisado dos veces— sin
      eximir nada. Ver `blueprint/31-proveedores.md` paso 1.
      """
      return f"interno:{numero}:{conversacion_id}"


  async def avisar_interno(proveedor, *, canal_interno: str | None, modo: str, confirmado: bool,
                           conversacion_id: str, contacto: str, motivo: str, enlace: str,
                           ahora=None) -> Resultado:
      texto = f"Escalación · {motivo} · {contacto} · {enlace}"
      numero = numero_interno(canal_interno)      # los dígitos, o None si es un canal de Slack

      if numero is None:
          return await _avisar_por_slack(texto)   # no es WhatsApp: no mira el modo

      if modo != "automatico" and not confirmado:
          return Resultado(False, None,
                           "modo borrador: el aviso a tu canal interno es un mensaje de WhatsApp y "
                           "espera confirmación como cualquier otro. Con un canal de Slack sale en "
                           "los dos modos")

      return await enviar(
          proveedor,
          conversacion_id=conversacion_interna(numero, conversacion_id),
          paso=6,
          plantilla=Plantilla(PLANTILLA_INTERNA, IDIOMA_PLANTILLA_INTERNA,
                              (contacto, motivo, enlace)),
          ahora=ahora,
          a_numero_interno=numero,
      )


  async def _avisar_por_slack(texto: str) -> Resultado:
      if not ajustes.slack_webhook_url:
          return Resultado(False, None, "falta SLACK_WEBHOOK_URL: la escalación quedó "
                                        "escrita y el aviso no sale")
      r = await CLIENTE.post(ajustes.slack_webhook_url, json={"text": texto}, timeout=10.0)
      if r.status_code >= 400:
          return Resultado(False, None, f"slack {r.status_code}: {r.text[:200]}")
      return Resultado(True, None)
  ```

  **Va con plantilla y no con texto libre, siempre.** Ese número nunca le escribió al negocio, así
  que su ventana de 24 horas está cerrada y WhatsApp sólo acepta plantillas aprobadas. En texto
  libre no llega: vuelve `131047`, que es lo que hoy lee en cada escalación un equipo con el canal
  en un número. La exención de la guarda «nunca escribir primero» y las tres guardas que sí corren
  están declaradas en `blueprint/31-proveedores.md` paso 1, con su tabla.

  **La plantilla la das de alta vos, con este nombre y este cuerpo.** Meta → WhatsApp Manager →
  Plantillas de mensajes → Crear, categoría **Utilidad**, idioma el que pongas en la constante:

  ```
  nombre:  escalacion_interna
  cuerpo:  Escalación en WhatsApp. Contacto: {{1}}. Motivo: {{2}}. Chat: {{3}}.
  ```

  Hasta que esté aprobada —suele tardar horas— el aviso por número no sale y el paso 6 queda
  `fallado` con el motivo que devuelve el proveedor. La escalación queda escrita igual. **Si no
  querés esperar eso, poné un canal de Slack**: es el camino que el kit soporta de punta a punta y
  el default de `S09`.

  **Sin `SLACK_WEBHOOK_URL` y con un canal de Slack**, el paso 6 queda `fallado` con el motivo y el
  `handoff` igual queda escrito en la salida; ver `S09` en `SUPUESTOS.md`. En `borrador` con un
  número, el paso 6 queda **`sin-confirmar`** con el motivo y `handoff.avisado_en` en nulo: no es
  una falla, es un aviso que espera. La escalación se lee del panel en los dos casos.

  **Por qué acá y no en un módulo propio.** `blueprint/00-contrato.md` § 4 le da un dueño a cada
  archivo, y el dueño de lo que sale del proceso hacia una persona —el contacto o tu equipo— es
  `agente/enviar.py`. Con el aviso por número saliendo por `enviar()`, además, ya no queda nada que
  discutir: la mitad de esta función **es** una llamada a la de arriba. Un
  `agente/integraciones/aviso.py` no rompe la compuerta —un `.post` a `SLACK_WEBHOOK_URL` no es un
  mensaje a un contacto y el chequeo 13 mira el destino, no el verbo ni el archivo,
  `blueprint/00-contrato.md` § 12—: rompe esa tabla, y deja el aviso a un import de distancia de
  volverse el segundo lugar desde donde alguien manda algo.

  Si venís de una ronda anterior del kit, acá decía dos cosas que se retiraron. Que el chequeo 13
  marcaba cualquier `.post` con el cliente compartido fuera de dos archivos eximidos: ese enunciado
  se fue entero, con los eximidos adentro. Y que el aviso interno **no** pasa por `enviar()`: eso
  era cierto para Slack y falso para el número, y escrito sin la distinción dejaba salir un mensaje
  de WhatsApp en `borrador`, sin ventana, sin baneo, sin la guarda de no escribir primero y sin
  `Idempotency-Key`.

  El archivo lo escribió `blueprint/31-proveedores.md` paso 1 y esto es lo único que se le agrega
  después: se suma al final, sin tocar `enviar()` ni las constantes de arriba.

**Tenés que ver.** Los cuatro pasos importan, el aviso está donde va y no manda por su cuenta, sin
ninguna credencial puesta, y el chequeo 13 sigue en verde:

```bash
.venv/bin/python -c "
import importlib, inspect
for m in ('paso_1_contexto','paso_2_calificar','paso_3_responder','paso_6_handoff'):
    importlib.import_module('agente.pasos.' + m)
from agente.enviar import avisar_interno
fuente = inspect.getsource(avisar_interno)
print('los cuatro pasos importan, y el aviso vive en enviar.py')
print('el aviso por número sale por enviar():', 'a_numero_interno' in fuente)
print('y mira el modo:', 'modo' in inspect.signature(avisar_interno).parameters)"
.venv/bin/python scripts/auditar.py | grep "enviar-unico"
```

```
los cuatro pasos importan, y el aviso vive en enviar.py
el aviso por número sale por enviar(): True
y mira el modo: True
```
```
  [ok      ] 13 enviar-unico       14 módulo(s) revisados
```

Las dos líneas nuevas son baratas y atrapan lo que la compuerta no puede: un `avisar_interno()` que
arma su propio POST al endpoint de mensajería no es un hallazgo del chequeo 13 —está escrito
adentro de `agente/enviar.py`, que es su dueño— y sale igual en `borrador`. Lo que lo pone rojo de
verdad es `pruebas/test_caso_02.py`, con el canal interno en un número; esto es el aviso temprano.

Los dos comandos miran cosas distintas y ninguno sobra. El primero se pone rojo si el aviso quedó
en otro módulo, y es el único que atrapa eso: con el aviso en `agente/integraciones/aviso.py`
termina en `ImportError: cannot import name 'avisar_interno'`, y la compuerta no dice nada, porque
ya no decide por archivo. El segundo mira lo otro: que ninguno de los cuatro cuerpos nuevos haya
escrito una URL de mensajería, que es la forma en que un paso le escribe a un contacto sin pasar
por `enviar()`.

En esta fase se verifica que importen, no que pasen: `pruebas/test_caso_01.py` todavía no existe y
lo escribe `blueprint/40-pruebas.md`.

**Si falla.**

- **`ImportError: cannot import name 'avisar_interno' from 'agente.enviar'`.** El aviso quedó en un
  módulo propio. Movelo al final de `agente/enviar.py` y borrá el archivo suelto: § 4 le da un dueño
  a cada archivo y éste ya tiene el suyo. No esperes que la compuerta te lo confirme: un aviso a
  Slack desde otro módulo no es un mensaje a un contacto y el chequeo 13 lo deja pasar. Este
  `ImportError` es todo el aviso que vas a tener, y por eso la primera línea del comando de arriba
  no se saltea.
- **`ImportError: cannot import name 'enviar'`.** Escribiste los pasos antes que `enviar.py`. El
  orden es `blueprint/31-proveedores.md` y después este archivo.
- **`ImportError` circular.** Un paso importa `agente/servidor.py` o el panel. Los pasos no importan
  a ninguno de los dos: son ellos los que importan a los pasos.
- **La salida trae menos de seis registros.** Alguien devolvió una lista nueva en vez de mutar la
  presembrada. Seis entran y seis salen.
- **`enviar/salida_de_mensajeria` en `agente/pasos/`.** Un cuerpo de paso escribió la URL de
  mensajería, o importó de `enviar.py` la constante que la denota. Al contacto le escribe sólo
  `enviar()`, y el aviso interno también: ningún paso nombra un destino de envío.
- **En `borrador` sale un mensaje de WhatsApp al canal interno.** `avisar_interno()` no está
  mirando el `modo`, o el paso 6 no se lo pasa. Ese aviso sale del número del negocio y pesa en su
  calificación igual que el que le llega a un cliente: en `borrador` no sale. Lo pone rojo
  `test_en_borrador_no_sale_ni_un_mensaje_de_whatsapp`, con el canal interno en un número.
- **El aviso por Slack dejó de salir en `borrador`.** Al revés: le pusiste el modo a la rama que no
  lo lleva. Un POST a `hooks.slack.com` no es un mensaje de WhatsApp, no espera confirmación, y es
  lo que hace que en `borrador` una escalación no quede muda.

---

## Qué quedó hecho

`agente/medios.py` bajando al recibir, fuera del handler y con el host importado de `enviar.py`.
El audio transcrito o el ciclo detenido con el motivo. La imagen leída por el modelo que ya
estaba. Los cuerpos de los pasos 1, 2, 3 y 6, los cuatro importando en limpio. Y `avisar_interno()`
al final de `agente/enviar.py`, con sus dos formas separadas —Slack por webhook, en los dos modos;
el número interno por `enviar()`, con plantilla y sólo con confirmación— y el chequeo 13 todavía en
verde. Anotá en `.wca-estado.json` el sha256 de cada archivo escrito.

**Próximo archivo:** `blueprint/33-agenda.md`, que crea la cita y deja el recordatorio programado
—o declarado detenido, según tu base.
