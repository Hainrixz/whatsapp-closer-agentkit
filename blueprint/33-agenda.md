# 33 · La agenda y el recordatorio

Fase 4. El paso 4: crear el evento, confirmarlo y dejar programado el recordatorio de 24 horas
antes. Va después de `blueprint/32-multimodal.md`. Todo vive en
`agente/integraciones/calendario.py`.

**El paso 4 escribe afuera, así que el default es `borrador`** —el modo en que los pasos que
escriben redactan, muestran y esperan confirmación explícita; ver `blueprint/00-contrato.md` § 10—:
muestra horario, duración y con quién, y espera. Sin confirmación no se crea nada, `cita` queda en
nulo y el paso en `sin-confirmar`. **Invariante 2** —un invariante es una de las seis reglas de
`CLAUDE.md` que ningún archivo puede romper, cada una con su chequeo en la compuerta
`scripts/auditar.py`; ver `blueprint/00-contrato.md` § 10—, **repetido acá porque acá se le escribe
dos veces a una persona —la confirmación y el recordatorio—: las dos salen por `enviar()`.**
**Invariante 3: el cliente de `agente/http.py`, con `timeout=`.**

**Para agendar hacen falta dos cosas y no una, y la segunda estuvo sin escribir tres rondas.** La
confirmación explícita dice *que sí*; `mensaje.horario_elegido` dice *cuál*. Sin el primero no se
agenda porque nadie autorizó; sin el segundo no se agenda porque nadie eligió, y elegir por el
contacto —el primer hueco libre, el más cercano, el que sea— es exactamente la cita a la que no va
a ir nadie. El campo está en `contratos/entrada.schema.json`, adentro de `mensaje`, y el Paso 3 lo
escribe entero: de dónde sale, quién lo llena y qué pasa cuando no está.

**Una advertencia que va arriba y no al final: con Postgres el recordatorio de 24 horas queda
detenido.** El jobstore de APScheduler es síncrono y el driver síncrono no está fijado en
`PINES.md`. La cita se crea y la confirmación sale igual. Con SQLite el recordatorio anda entero. El
Paso 4 lo escribe con todas las letras y la decisión está en `blueprint/00-contrato.md` § 8.

---

### Paso 1 · La credencial de Google, que tiene dos formas y no una

**Objetivo.** Algo puede crear eventos en `GOOGLE_CALENDAR_ID`, y lo sabés ahora y no cuando el
paso 4 diga que sí y el evento no aparezca.

**Hacé esto.** Primero, una sola vez: `console.cloud.google.com` → APIs y servicios → habilitar
**Google Calendar API**. Después, elegí una de las dos credenciales. **`GOOGLE_SERVICE_ACCOUNT_JSON`
nombra el archivo en los dos casos** —la variable ya existe y no se agrega ninguna—, y lo que
decide cuál es el `type` de adentro, que es lo mismo que mira `google.auth` de verdad. La ruta va
absoluta.

| `type` del archivo | Qué es | Estado hoy |
|---|---|---|
| `authorized_user` | tu propia cuenta de Google, con un `refresh_token` | **anda**: el token se saca con un POST y no se firma nada |
| `service_account` | un usuario de Google que es un programa y no una persona, que se autentica con un archivo JSON; ver `blueprint/00-contrato.md` § 10 | **anda desde esta ronda**: el token pide un JWT firmado con RS256 —una firma con clave privada; § 10 otra vez— y `PINES.md` fija `PyJWT` y `cryptography`. Ver el Paso 2 |

**Cuál de las dos elegís, dicho una vez y no repetido abajo.** `authorized_user` es tu cuenta: se
consigue en cinco minutos y se cae el día que cambiés la contraseña, que te vayas de la empresa o
que pases seis meses sin usarla. `service_account` es un usuario que no es nadie: sobrevive a las
tres cosas, y a cambio hay que compartirle el calendario a mano una vez. **Para un negocio va
`service_account`**; `authorized_user` sirve para probar hoy y para una agenda que sea tuya de
verdad.

**Con `authorized_user`.** El archivo tiene cuatro claves y ninguna más:

```json
{
  "type": "authorized_user",
  "client_id": "…apps.googleusercontent.com",
  "client_secret": "…",
  "refresh_token": "…"
}
```

Sale de una de estas dos, la que te quede más a mano:

1. `gcloud auth application-default login --scopes=https://www.googleapis.com/auth/calendar`, que
   lo deja escrito en `~/.config/gcloud/application_default_credentials.json`. Copialo a donde
   apunte `GOOGLE_SERVICE_ACCOUNT_JSON`.
2. Sin `gcloud`: Cloud Console → Credenciales → **ID de cliente de OAuth**, tipo «App de
   escritorio». Con ese `client_id` y ese `client_secret`, una vuelta por
   `developers.google.com/oauthplayground` con «Use your own OAuth credentials» y el alcance
   `https://www.googleapis.com/auth/calendar` te devuelve el `refresh_token`. Los tres valores
   van al JSON de arriba.

**El calendario no hace falta compartirlo**: los eventos los crea tu propia cuenta, así que
`GOOGLE_CALENDAR_ID` puede ser `primary` o cualquiera donde ya escribís.

**Con `service_account`.** IAM → Cuentas de servicio → crear → Claves → Agregar clave → JSON.
`.gitignore` ya lo tapa con `*-service-account*.json`. De las diez claves que trae ese archivo, el
Paso 2 usa cuatro: `client_email`, `private_key`, `private_key_id` y `token_uri`. Y **la que casi
nadie hace:** `calendar.google.com` → el calendario → Configuración y uso compartido → Compartir
con determinadas personas → agregar la dirección de la cuenta de servicio → permiso **Hacer
cambios en los eventos**. La dirección sale del JSON sin abrirlo en pantalla:

```bash
.venv/bin/python -c "import json,os;print(json.load(open(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']))['client_email'])"
```

**Tenés que ver.** El `type` que elegiste, y nada más:

```bash
.venv/bin/python -c "import json,os;print(json.load(open(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']))['type'])"
```

```
authorized_user
```

Con `service_account`, además, la dirección terminada en `.iam.gserviceaccount.com` listada en
Google con «Hacer cambios en los eventos». El `private_key` y el `refresh_token` no se imprimen
nunca.

**Si falla.**

- **El playground te devolvió `access_token` y ningún `refresh_token`.** Falta
  `access_type=offline` con `prompt=consent`: sin los dos, Google te da el token de una hora y
  ninguno para renovarlo. `gcloud` los manda solo.
- **Andaba y a los siete días dejó de andar, con `invalid_grant`.** Tu app de OAuth quedó en
  estado «Prueba» en la pantalla de consentimiento: ahí Google caduca los `refresh_token` a los
  siete días. Publicala, o usá el camino de `gcloud`, cuyo cliente ya está publicado. Un
  `refresh_token` que no se usa en seis meses también caduca, y ése es el otro `invalid_grant`.
- **404 sobre un calendario que estás mirando.** Con `service_account`, el id está bien y falta
  compartirlo. Es el pendiente 4 de `PENDIENTES.md` y no se detecta desde el código: la conexión
  da OK igual. Con `authorized_user` no puede pasar: es tu propio calendario.
- **403 al crear, con el calendario ya compartido.** Quedó en «Ver todos los eventos».
- **`KeyError: 'client_email'`.** Le pediste el correo de la cuenta de servicio a un archivo
  `authorized_user`, que no lo tiene. El `type` es el que manda.
- **`FileNotFoundError`.** Ruta relativa y el servicio arranca en otro directorio. Absoluta.
- **403 `accessNotConfigured`.** Falta habilitar la Calendar API, o lo habilitaste en otro
  proyecto.

---

### Paso 2 · El token: dos cuerpos sobre el mismo POST

**Objetivo.** El paso 4 tiene un token con qué llamar al calendario, con cualquiera de las dos
credenciales del Paso 1.

**Hacé esto.** Los dos caminos terminan en el mismo lugar —`POST
https://oauth2.googleapis.com/token`, que devuelve `access_token`— y lo que cambia es el cuerpo.

**Con `authorized_user`, un formulario y nada más.** Sin firma, sin JWT y sin tocar la librería de
RS256: `httpx` alcanza, y es el cliente único de `agente/http.py` con `timeout=`.

```
grant_type=refresh_token
client_id=<del JSON>
client_secret=<del JSON>
refresh_token=<del JSON>
```

La respuesta trae `access_token` y `expires_in` —3599 segundos, o sea una hora— y **ningún
`refresh_token` nuevo**: el que tenés en el archivo se sigue usando. El token se cachea en memoria
hasta un minuto antes de `expires_in` y se renueva solo; pedir uno por evento funciona y es una
llamada de más en cada cita.

**Con `service_account`, un JWT firmado con RS256** con la clave privada del JSON. RS256 no se
firma con la biblioteca estándar, y hasta la ronda pasada ninguna librería que lo hiciera estaba en
`PINES.md`: por eso esta rama estuvo declarada y detenida. **Ya no.** `PINES.md` fija
`PyJWT==2.13.0` y `cryptography==50.0.0`, y el motivo de que sean ésas y no `google-auth` está
escrito ahí, con la medición al lado. Mirá qué hay antes de escribir:

```bash
.venv/bin/python -c "import importlib.util as u; print([n for n in ('google','cryptography','jwt') if u.find_spec(n)] or 'NINGUNA')"
```

```
['cryptography', 'jwt']
```

Con eso, la rama se escribe así. El JWT son cinco reclamos y ninguno más, la firma es una línea, y
el `POST` es el mismo cliente único de `agente/http.py` con `timeout=`:

```python
import time

import jwt  # PyJWT: la distribución se llama PyJWT y la raíz que se importa es `jwt`

ahora = int(time.time())
reclamos = {
    "iss": credencial["client_email"],                    # …@….iam.gserviceaccount.com
    "scope": "https://www.googleapis.com/auth/calendar",
    "aud": credencial["token_uri"],                       # https://oauth2.googleapis.com/token
    "iat": ahora,
    "exp": ahora + 3600,                                  # una hora es el techo de Google
}
assertion = jwt.encode(
    reclamos,
    credencial["private_key"],
    algorithm="RS256",
    headers={"kid": credencial["private_key_id"]},        # opcional; ver abajo
)
```

Y el cuerpo del `POST`, que es lo único que cambia contra el otro camino:

```
grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
assertion=<el JWT de arriba>
```

Cuatro cosas que no son estilo:

- **`aud` sale de `token_uri` y no de una constante escrita al lado.** Es el mismo valor, y viene
  del archivo por lo mismo que el `client_email`: el día que Google cambie ese endpoint para las
  cuentas de servicio, el JSON nuevo lo trae y el código no se entera.
- **`exp` no pasa de una hora desde `iat`.** Google rechaza el JWT que pida más, y el
  `access_token` que devuelve dura 3599 segundos igual. El caché es el mismo del otro camino:
  en memoria, hasta un minuto antes de vencer.
- **`kid` es opcional.** Va porque deja escrito adentro del token cuál de las claves de la cuenta
  firmó, y una cuenta de servicio puede tener varias. Sin él Google acepta igual.
- **`sub` no va.** Ese reclamo es el de la delegación de dominio —actuar en nombre de una persona
  de tu Workspace—, y este paso no la usa: el evento lo crea la cuenta de servicio sobre un
  calendario que vos le compartiste. Es la misma decisión que deja el evento sin `attendees`; ver
  el Paso 3.

**La clave privada no se imprime, no se registra y no entra al árbol.** Sale de `json.load()` del
archivo que nombra `GOOGLE_SERVICE_ACCOUNT_JSON` y va directo a `jwt.encode()`. Un bloque `PRIVATE
KEY` escrito en cualquier archivo del repo lo marca el chequeo 08 `secretos`, y lo marca con razón:
no puede distinguir el de mentira del que alguien pegó sin querer.

**Por qué hay dos caminos y no uno, dicho acá y no descubierto abajo.** Hasta hace dos rondas el
único camino escrito era el del JWT, y con la librería sin fijar eso dejaba al **paso 4 sin ningún
camino feliz**: `cita`, sus cinco propiedades y la etapa `agendado` del CRM eran superficies del
contrato que ninguna corrida podía alcanzar. Un agente de seis pasos con uno que no puede correr no
se publica. Y lo peor no era la detención: era lo que la detención tapaba. Medido: con
`cita.evento_id = "evt-inventado"` y sin una sola llamada a Google, la suite entera quedaba en
verde y la compuerta cerraba en `PASS · 0 errores · 0 avisos · 0 salteados`, porque la mitad «sí se
agenda» de `pruebas/test_camino_feliz.py` no era alcanzable y no exigía nada.

El `refresh_token` destrabó eso primero, sin fijar ningún pin. Esta ronda se fijaron los dos pines
y la rama del JWT también anda. **Los dos caminos quedan, y no sobra ninguno**: el que se elige
está en la tabla del Paso 1, y `authorized_user` sigue siendo el único que no pide compartir un
calendario a mano.

**Tenés que ver.** `['cryptography', 'jwt']` en la sonda de arriba, y el `type` del Paso 1. Con
`authorized_user` el paso 4 anda sin tocar ninguna de las dos; con `service_account` las dos tienen
que estar.

Y el token de verdad, que es lo que este paso promete. Sobre el camino del JWT, sin salir a la red,
con un par RSA generado al momento:

```bash
.venv/bin/python -c "
import time, jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
par = rsa.generate_private_key(public_exponent=65537, key_size=2048)
clave = par.private_bytes(serialization.Encoding.PEM,
                          serialization.PrivateFormat.PKCS8,
                          serialization.NoEncryption()).decode()
ahora = int(time.time())
reclamos = {'iss': 'cerrador@mi-proyecto.iam.gserviceaccount.com',
            'scope': 'https://www.googleapis.com/auth/calendar',
            'aud': 'https://oauth2.googleapis.com/token',
            'iat': ahora, 'exp': ahora + 3600}
token = jwt.encode(reclamos, clave, algorithm='RS256')
print(jwt.get_unverified_header(token))
print(jwt.decode(token, par.public_key(), algorithms=['RS256'],
                 audience='https://oauth2.googleapis.com/token') == reclamos)"
```

```
{'alg': 'RS256', 'typ': 'JWT'}
True
```

Si eso corre, la firma anda y lo que falte después es de Google y no de tu máquina.

**Si falla.**

- **`NotImplementedError: Algorithm 'RS256' could not be found. Do you have cryptography
  installed?`** Está `PyJWT` y falta `cryptography`. Las dos están en `PINES.md` y en
  `requirements.txt`, así que esto quiere decir que el `.venv` se armó a mano o a medias: volvé a
  `blueprint/10-entorno.md` paso 5. `PyJWT` sin el extra instala y firma HS256; RS256 pide la otra.
- **`jwt.exceptions.InvalidKeyError: Could not parse the provided public key.`** La clave privada
  llegó rota. Dice «public key» y es la privada: el mensaje es de la librería y no se puede
  arreglar. La causa casi siempre es la misma —el PEM viajó con los `\n` escritos como dos
  caracteres en vez de saltos de línea, que es lo que pasa cuando alguien lo mueve del JSON a una
  variable de entorno—. Se lee del archivo con `json.load()` y no se toca. Medido en esta máquina,
  con PyJWT 2.13.0, sobre una clave válida con los saltos escapados:

  ```
  InvalidKeyError : Could not parse the provided public key.
  ```
- **404 sobre un calendario que estás mirando.** Es el que sale seguro la primera vez con
  `service_account`, y no es del token: el token salió bien. El calendario no está compartido con
  la dirección de la cuenta de servicio, y esa dirección no es la tuya —termina en
  `.iam.gserviceaccount.com`—, así que el calendario que vos ves en pantalla para ella no existe.
  Se arregla en `calendar.google.com`, no en el código: Configuración y uso compartido → Compartir
  con determinadas personas → la dirección del `client_email` → **Hacer cambios en los eventos**.
  Es el pendiente 4 de `PENDIENTES.md`, el Paso 1 de este archivo lo pide, y no se detecta desde el
  código: pedir el token da 200 igual. Con `authorized_user` no puede pasar, que es la única cosa
  que ese camino tiene de más.
- **`400 invalid_grant` con `service_account`, y la credencial recién bajada.** El reloj de la
  máquina está corrido. El JWT lleva `iat` y `exp`, Google los compara contra su propio reloj y con
  unos minutos de diferencia rechaza. Se lee como «credencial mal copiada» y no lo es: la misma
  credencial anda en otra máquina. Comparalo con `date -u` contra cualquier reloj de red y
  sincronizá; en un contenedor pasa cuando la máquina anfitriona durmió. El adelanto es peor que el
  atraso: un `iat` en el futuro lo rechaza sin margen.
- **`400 invalid_client`.** Con `authorized_user`, el `client_secret` es de otro `client_id`. Con
  `service_account`, la clave que firmó ya no está en la cuenta: alguien la borró desde IAM →
  Claves. Bajá una nueva; el JSON viejo no se recupera.
- **`400 invalid_grant` con `authorized_user`.** El `refresh_token` caducó: siete días si la
  pantalla de consentimiento quedó en «Prueba», seis meses sin usarlo. Ver el Paso 1.
- **`400 invalid_scope`, o un token que después da 403 en todo.** El `scope` del JWT no es
  `https://www.googleapis.com/auth/calendar`. Con `.readonly` el token sale y el `insert` del Paso 3
  rebota.
- **Un token nuevo en cada llamada.** El caché quedó afuera. Anda, y son dos llamadas por cita en
  vez de una: la de más se ve en `pruebas/test_camino_feliz.py`, que cuenta lo que salió al cable.

**Lo que hay que afirmar de esta rama, y con qué doble.** Las pruebas del camino nuevo no se
escriben acá, y esto es lo que tienen que decir. El doble es el mismo de siempre —el transporte de
`agente/http.py`, sin red y sin credenciales— y la clave la **genera la prueba** en su `tmp_path`,
un par RSA por corrida: una clave pegada en el árbol la marca el chequeo 08 y con razón.

| Qué se afirma | Cómo |
|---|---|
| con `service_account` el paso 4 agenda | el ciclo devuelve `cita` con el `evento_id` que dio el doble, igual que con `authorized_user` |
| el cuerpo del token es el del JWT y no el del formulario | lo que salió al cable trae `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer` y un `assertion`, y no trae `refresh_token` |
| el `assertion` está firmado con esa clave y no es una cadena cualquiera | la prueba lo verifica con la pública del par que generó, y compara los cinco reclamos |
| `aud` sale de `token_uri` | se le cambia el `token_uri` al JSON de la prueba y el `aud` del JWT cambia con él |
| el token se cachea | dos citas en la misma corrida, una sola llamada a `oauth2.googleapis.com/token` |

Y una que se borra: `test_cita_con_cuenta_de_servicio_y_sin_la_libreria_de_rs256_queda_detenido`
afirmaba la detención y su propio docstring dice qué hacer hoy —«si algún día `PINES.md` fija la
librería, esta prueba se pone roja y ahí se convierte en la otra mitad del camino feliz»—. Ese día
es éste.

---

### Paso 3 · El horario elegido, el evento y la confirmación por WhatsApp

**Objetivo.** Con confirmación explícita y con un horario elegido existe el evento con su
identificador, y el contacto se entera por el chat.

**Primero: cuál horario.** `mensaje.horario_elegido` es el segundo requisito del paso 4 y hasta
esta ronda no existía en ningún lado. Sin él, `contratos/entrada.schema.json` —que es
`additionalProperties: false` en los dos niveles— no tenía por dónde recibir el horario que el
contacto aceptó: había `opciones_horario`, que dice cuántos ofrecer, y ningún campo para cuál
aceptó. O sea que el paso 4 no podía agendar nada ni aunque la librería de RS256 estuviera fijada.

Se llena por dos caminos y por ningún otro:

1. **El paso 1, en el turno siguiente.** El contacto contesta «el martes a las 11 me sirve», y el
   paso 1 cruza esa respuesta contra los horarios que el turno anterior ofreció —los que quedaron
   en `respuesta.horarios_ofrecidos` y en la conversación— y escribe el que coincide. Es el mismo
   lugar y la misma idea que `mensaje.media_local`: un campo del contrato que el paso 1 resuelve y
   deja escrito para el resto del ciclo. **No se interpretan fechas sueltas**: si la respuesta no
   cae sobre uno de los horarios ofrecidos, el campo queda en nulo y el paso 3 vuelve a ofrecer.
2. **La bandeja.** Quien opera abre el borrador del paso 4, elige uno de los horarios y aprueba.
   `POST /api/pendientes/{id}/aprobar` vuelve a correr el paso con `confirmado: true` y con ese
   `horario_elegido` adentro de la misma entrada.

Y tres reglas, cortas:

- **tiene que ser uno de `disponibilidad[].inicio`.** Uno que no esté ahí no se agenda: paso 4
  `fallado` con el motivo. Es la misma regla que `respuesta.horarios_ofrecidos`, del otro lado;
- **la duración sale del `duracion_min` de ese mismo hueco**, no de un default;
- **no reemplaza a la confirmación.** Con el horario elegido y `confirmado` en falso no se agenda:
  el paso 4 muestra el borrador y espera, como cualquier otro paso que escribe afuera.

Sin `horario_elegido` el paso 4 queda en `sin-confirmar` con el motivo **«no hay horario elegido»**
—ése y no el del modo—, `cita` en nulo y el ciclo sigue. Es el estado del primer turno de
`pruebas/caso-01.md` y es lo que trae `pruebas/fixtures/caso-01.salida-esperada.json`.

**Después: el evento.** `POST
https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events`, con el `Authorization:
Bearer` del token del Paso 2. El cuerpo: `summary`, `description` con el resumen de tres líneas, y
`start`/`end` con `dateTime` **con offset** y `timeZone`. El `start` es `horario_elegido` tal como
vino y el `end` es ése más `duracion_min`.

**Sin `attendees`, y por dos motivos que no dependen de qué credencial elegiste.** Una cuenta de
servicio no puede invitar a nadie sin delegación de dominio —la API rechaza el invitado con `403
forbiddenForServiceAccounts`— y, con cualquiera de las dos, **no tenemos el mail del contacto**: la
entrada trae teléfono e identificador y ningún correo. **El cliente no recibe el mail de Google**, y
por eso la confirmación sale por WhatsApp, por `enviar()`, con la ventana abierta —el contacto
acaba de escribir— o sea envío libre. Ver S05 en `SUPUESTOS.md`.

**Un turno que agenda manda dos mensajes y no uno**: la respuesta del paso 3 y la confirmación de
la cita. Las dos por `enviar()`, las dos contadas, y ninguna tercera. Un turno que no agenda manda
uno solo, y eso es lo que cuenta `pruebas/test_enviar.py` sobre el caso 01, que no trae horario
elegido.

**Los dos salen con el mismo `ahora`, y para la regla 5 son una sola vez.** `correr_ciclo()` lee el
reloj una vez arriba de todo y se lo baja a los seis pasos, así que los dos entran a `enviar()` con
el mismo valor y `anotar_saliente()` suma uno solo: `salientes_seguidos` cuenta **turnos y no
mensajes**. La decisión y el mecanismo están en `blueprint/31-proveedores.md` paso 1, que es el
dueño de esa guarda. Contado por mensaje, este turno deja el contador en `MAX_SEGUIDOS` —que son
dos— y el siguiente saliente de esta conversación, que es el recordatorio del Paso 5, no sale
nunca.

**Tenés que ver.** `cita.evento_id` con el id de Google, `cita.inicio` igual al horario elegido,
`cita.confirmacion_enviada` en verdadero, el paso 4 en `hecho`, y el evento en la pantalla del
calendario, sin invitados.

**El `evento_id` sale de la respuesta, y eso se afirma como equivalencia y no como una lista de
campos.** La regla es una sola y vale con las dos credenciales:

> **hay `cita` si y sólo si el calendario creó el evento**, y el `evento_id` es el que devolvió esa
> llamada.

Un identificador que el código se escribe a sí mismo es una cita que no existe: queda en la
salida, en el panel, en `leads.cita_evento_id` y en la confirmación que le llega al contacto, y el
día de la reunión no hay nada en la agenda. Lo ancla
`pruebas/test_camino_feliz.py::test_cita_el_evento_id_sale_de_la_respuesta_del_calendario_y_no_de_una_constante`,
que corre el ciclo **dos veces** con dos identificadores distintos del lado del calendario: con
una sola corrida, una constante copiada del fixture acierta; con dos, la única forma de acertar
las dos es leer la respuesta. Es la misma idea que ancla el presupuesto en
`pruebas/test_caso_01.py`: no alcanza con que el valor sea plausible, tiene que venir de donde
dice venir.

El calendario se dobla igual que el transporte de WhatsApp —por el cliente único de
`agente/http.py`, sin red y sin credenciales—, así que esa prueba no necesita una credencial de
verdad y el Paso 1 de este archivo sigue siendo algo que se hace a mano una vez. La prueba escribe
un `authorized_user` de mentira en su `tmp_path` y el doble contesta el token: **la mitad que
agenda es alcanzable hoy y no espera ningún pin**, que es lo que hace que un `evento_id` inventado
se ponga rojo en vez de pasar desapercibido.

**Si falla.**

- **403 `forbiddenForServiceAccounts`.** Mandaste `attendees`. Sacalo: no se arregla con permisos
  del calendario, se arregla con delegación de dominio o no se arregla.
- **400 `Invalid value for: start.dateTime`.** Hora sin offset y sin `timeZone`. `disponibilidad`
  viene con offset; no lo recortes.
- **`cita` con un `evento_id` y el calendario sin una sola llamada.** El identificador se lo
  escribió el código. Eso no es una cita: es un renglón en el panel y una confirmación al contacto
  sobre una reunión que no está en ninguna agenda.
- **Agendó el primer hueco libre.** Faltó `mensaje.horario_elegido` y el build eligió por el
  contacto. La confirmación autoriza; no elige.
- **El evento quedó y la confirmación no salió.** El contacto tiene cita y no lo sabe: el paso
  queda `fallado` con el `evento_id` escrito, para que el reintento no cree un segundo evento.

---

### Paso 4 · El recordatorio de 24 horas, en proceso

**Objetivo.** El recordatorio sobrevive a un despliegue y a una caída. Y si en tu base no puede
existir, lo sabés al agendar y no la noche anterior a la cita.

**Hacé esto.** APScheduler adentro del servicio, con `SQLAlchemyJobStore` sobre la misma base, y un
trabajo por cita con id estable:

```python
from apscheduler.jobstores.base import JobLookupError

from agente.base import RecordatorioSinDriver, url_sincrona

try:
    jobstore = SQLAlchemyJobStore(url=url_sincrona(os.getenv("DATABASE_URL")))
except RecordatorioSinDriver as e:
    cita["recordatorio_programado"] = False       # la cita y la confirmación salen igual
    paso_4["motivo"] = str(e)                     # el motivo va en el registro del paso
else:
    trabajo_id = f"recordatorio:{evento_id}"
    try:
        agenda().remove_job(trabajo_id)           # con el scheduler parado la bandera no mira
    except JobLookupError:
        pass                                      # no estaba: es el caso normal
    agenda().add_job(recordar, "date", run_date=inicio - timedelta(hours=24),
                     id=trabajo_id, replace_existing=True, args=[evento_id])
```

El motivo va en `pasos[3].motivo` y no adentro de `cita`: `cita` es
`additionalProperties: false` con cinco propiedades y ninguna es un texto libre. Agregarle una
inventa una clave y el chequeo `contrato` la rebota.

**Las tres líneas del `remove_job` no son adorno, y `replace_existing=True` se queda igual.** La
bandera la mira el jobstore, y con el scheduler **parado** el jobstore no llega a verla:
APScheduler 3 hace `self._pending_jobs.append((job, jobstore, replace_existing))` sin preguntar si
ese id ya está, y recién resuelve el reemplazo cuando el scheduler arranca. Parado está en todo el
camino que la suite ejercita, y no por descuido: `programar_recordatorio()` corre adentro de un
`asyncio.run` que se cierra, así que un `AsyncIOScheduler` arrancado se ata a un loop que ya no
existe; y un `BackgroundScheduler` arrancado toma el `run_date` del corpus —marzo de 2026— como
pasado real y dispara el trabajo solo. Sacar el id antes de volver a ponerlo cierra las dos
puertas: parado, porque `remove_job()` sí recorre `_pending_jobs`; arriba, porque el `remove_job()`
no encuentra nada y la bandera sigue siendo la que manda. Medido en esta máquina, con
APScheduler 3.11.3, sobre dos reprogramaciones seguidas del mismo id:

| El bloque | Scheduler parado | Scheduler arrancado |
|---|---|---|
| con `replace_existing=True` a secas | **2 trabajos** | 1 trabajo |
| sacando el id antes de volver a ponerlo | 1 trabajo | 1 trabajo |

El `JobLookupError` atrapado es el caso normal: la primera vez que se programa una cita ese id no
existe, y con el scheduler arrancado tampoco existe casi nunca. Un `remove_job()` sin el `try`
convierte la primera programación de cada cita en una excepción.

**El jobstore —donde el programador de tareas guarda lo que tiene pendiente; ver
`blueprint/00-contrato.md` § 10— de APScheduler 3 es síncrono**, así que esa URL va **sin**
`+asyncpg` y **sin** `+aiosqlite`. Por eso `url_sincrona()` y no `normalizar_url()`, que siempre
devuelve la forma async: `agente/base.py` expone las dos y no una sola. La tabla de las dos está en
`blueprint/00-contrato.md` § 8 y la verificación en `blueprint/34-crm.md`, paso 2.

**Con Postgres el recordatorio queda detenido, y se dice al agendar.** `url_sincrona()` levanta
`RecordatorioSinDriver` porque el driver síncrono no está fijado en `PINES.md`, y fijar un pin que
nadie verificó contra PyPI rompe el invariante 6. El paso 4 deja `cita.recordatorio_programado` en
falso con el motivo escrito, **y la cita y la confirmación por WhatsApp salen igual**. El paso queda
en `hecho`, no en `fallado`: el evento existe y el contacto se enteró; lo que no quedó es el
recordatorio, y se lee en esas dos claves. A vos se te dice así, al agendar y no la noche anterior:

```
la cita del 2026-03-02 11:00 quedó agendada y la confirmación salió; el recordatorio
de 24 horas antes no se pudo programar sobre esta base de datos. Con SQLite anda. Si
estás en Postgres, avisale vos al contacto el día anterior hasta que esto se destrabe.
```

Con SQLite funciona entero: `sqlite3` es de la biblioteca estándar y no hay nada que fijar.
Levantar la detención es un cambio del kit y no un paso de tu construcción —`PINES.md`,
`plantillas/infra/requirements.txt` y `plantillas/MANIFIESTO.json` se mueven juntos, y el
procedimiento está en `blueprint/00-contrato.md` § 8—. **El Paso 2 acaba de hacer ese recorrido
entero con la librería de RS256**, así que hay un ejemplo trabajado de cómo se levanta una: se
verifica contra PyPI, se fija con `==` y con fecha, se instala, y recién ahí se reescribe el
archivo que la esperaba. Lo que no se hace es improvisar el pin.

**El barrido al arrancar no es opcional, y desde esta ronda tiene una aserción encima.** Un trabajo
`date` cuya hora pasó mientras el servicio estuvo caído se descarta solo: el `misfire_grace_time`
por defecto es de un segundo. Al `startup`, recorré las citas futuras sin recordatorio enviado,
mandá las que vencieron y todavía sirven, y reprogramá el resto.

**Se llama `barrer_recordatorios()` y vive en `agente/integraciones/calendario.py`.** El nombre no
es estilo, por lo mismo que `agenda()`: es la única puerta por la que una prueba puede entrar a
preguntar si el barrido existe y qué hace. **Quién la llama no se escribe acá**: la llama
`agente/servidor.py` al arrancar, en la misma función donde se llama `migrar()`, y ese archivo lo
escribe `blueprint/35-panel-api.md` paso 2 —un archivo, un dueño; ver `blueprint/00-contrato.md`
§ 4—.
Escrita, la firma es corta y no recibe nada —lee las citas de la base y el scheduler de
`agenda()`—:

```python
async def barrer_recordatorios() -> int:
    """Reprograma los recordatorios que el arranque encontró sin trabajo. Devuelve cuántos."""
```

Y tres reglas, que son las que la prueba mira:

- **el id que reprograma es el mismo**, `recordatorio:{evento_id}`, y reprograma **por el bloque de
  arriba**: `remove_job()` adentro del `try` y después el `add_job()` con la bandera. Con otro id, o
  con la bandera sola y el scheduler parado, cada arranque suma un recordatorio más para la misma
  cita y el contacto recibe uno por despliegue;
- **la hora sale de la cita**, o sea 24 horas antes de `cita.inicio`, y nunca del momento en que
  arrancó el servicio;
- **barrer no es mandar.** El recordatorio que todavía no vence se reprograma y no sale. Sale sólo
  el que venció mientras el servicio estuvo caído y todavía sirve, y sale por `enviar()` como
  cualquier otro; ver el Paso 5.

Eso lo afirma
`pruebas/test_camino_feliz.py::test_barrido_el_arranque_vuelve_a_dejar_el_trabajo_que_el_misfire_se_llevo`,
que vacía el scheduler —que es la reproducción exacta de lo que hace el `misfire_grace_time` de un
segundo con el servicio caído— y después corre el barrido dos veces: el trabajo tiene que volver
con el mismo id y a la misma hora, tiene que haber uno y no dos, y no puede salir un mensaje.
Hasta esta ronda esta frase tenía cero referencias en `pruebas/` y en `scripts/auditar.py`.

**Por qué no el cron de Railway**, escrito para que nadie lo «simplifique» en tres meses: mínimo de
5 minutos, sólo UTC, y **exige que el proceso termine**. Sirve para un trabajo que arranca, hace y
muere; un recordatorio 24 horas antes de una cita puntual no entra en esa forma, y correría en otra
instancia, sin el scheduler que tiene los trabajos.

**`agenda()` es el nombre por el que se llega al scheduler, y no es un detalle de estilo.**
`agente/integraciones/calendario.py` la expone y el paso 4 agenda por ahí. Es el único lugar desde
el que se puede ver si un recordatorio quedó de verdad: `cita.recordatorio_programado` es un
booleano que el paso se escribe a sí mismo, y sin mirar el scheduler «programado» y «no
programado» son la misma corrida. Con otro nombre, la suite no tiene por dónde entrar; si tu build
usa otro, se cambia acá y en `pruebas/test_camino_feliz.py`, que es la convención que ya sigue
`TRANSPORTE` en `agente/http.py`.

**Tenés que ver.** Con SQLite, un trabajo por cita pendiente; en una base recién creada la salida es
vacía y eso también es correcto. Con Postgres, `RecordatorioSinDriver` con el motivo de arriba: es
la conducta declarada, no una falla que haya que arreglar hoy.

```bash
.venv/bin/python -c "from agente.integraciones.calendario import agenda; [print(j.id, j.next_run_time) for j in agenda().get_jobs()]"
```

```
recordatorio:5m2k4h8p 2026-03-01 10:00:00-06:00
```

Eso mismo lo afirma
`pruebas/test_camino_feliz.py::test_recordatorio_programado_solo_si_quedo_un_trabajo_en_el_scheduler`,
sobre las dos bases: con SQLite, `recordatorio_programado` en verdadero **sólo si** hay un trabajo
`recordatorio:{evento_id}` a 24 horas del inicio y con `tzinfo`; con Postgres, en falso, con el
motivo en `pasos[3].motivo` y con la cita y la confirmación saliendo igual.

**Y una cuenta honesta sobre ese nodo, que cambió en esta ronda:** mientras el paso 4 no tuvo
camino feliz, no había `cita`, así que tampoco había `recordatorio_programado` que mentir —un build
con ese booleano en verdadero siempre pasaba, porque esa línea no llegaba a correr—. Con el camino
de `authorized_user` del Paso 2 y con `mensaje.horario_elegido` en la entrada, la cita existe y el
nodo del scheduler muerde: `recordatorio_programado` en verdadero pide un trabajo
`recordatorio:{evento_id}` de verdad, sobre SQLite. El mecanismo que decide, `url_sincrona()`, se
sigue afirmando aparte en `blueprint/34-crm.md` paso 2, desde la fase 3 y sin esperar al paso 4.

**Si falla.**

- **`InvalidRequestError: The asyncio extension requires an async driver`.** Le pasaste al jobstore
  la URL de `normalizar_url()`. Es `url_sincrona()`. Revienta en el arranque: lo que ves es el
  servicio sin levantar.
- **`No module named 'psycopg2'` con Postgres.** El jobstore se armó sin pasar por `url_sincrona()`,
  que justamente existe para cortar antes con un motivo legible. Volvé al bloque de arriba. Lo
  declarado es `RecordatorioSinDriver`; esta traza es la versión sin declarar del mismo hecho.
- **Dos recordatorios por cita, y en la suite dos trabajos con el mismo id.** Quedó el `add_job()`
  con `replace_existing=True` a secas, sin el `remove_job()` de arriba. Con el scheduler parado la
  bandera no la mira nadie hasta que arranque, y el segundo barrido apila. Se lee así:

  ```
  después de 2 barrido(s) hay 2 trabajos con el id `recordatorio:evt_del_barrido`.
  assert 2 == 1
  ```
- **Dos recordatorios por cita, con un solo trabajo en el scheduler.** Ése es el otro: el servicio
  corre con `--reload` o con dos workers, o sea dos procesos y dos schedulers. El que agenda corre
  con uno solo.
- **Salió a la hora equivocada.** `run_date` sin `tzinfo`: APScheduler lo toma en la zona del
  scheduler, que en un contenedor es UTC.

---

### Paso 5 · El recordatorio sale por `enviar()`, y casi siempre pide plantilla

**Objetivo.** El recordatorio no tiene camino propio, y si no hay plantilla aprobada se dice ahora.

**Hacé esto.** La función que lo dispara es la que el Paso 4 le pasó a `add_job`, se llama
`recordar(evento_id)` y llama a `enviar()` y nada más:

```python
async def recordar(evento_id: str) -> None:
    """El cuerpo del trabajo. Busca la cita, arma el texto y sale por la única puerta."""
```

**Adentro no hay un `.post`, ni un cliente, ni una URL.** Lo único que hay es la llamada a
`enviar()`, con la plantilla si corresponde, y lo que devuelva se anota. Un `recordar()` que sea un
`return` pelado deja el árbol entero en `PASS · 0 errores · 0 avisos · 0 salteados` —el trabajo
quedó agendado, `cita.recordatorio_programado` dice que sí, y la noche anterior a la cita no pasa
nada—, y un `recordar()` que postee por su cuenta manda igual y se saltea las cinco reglas.

`enviar()` mira `last_inbound_at`: una cita agendada hoy para la semana que viene tiene el
recordatorio seis días
después del último mensaje del contacto, o sea **fuera de la ventana de 24 horas** —el plazo desde
el último mensaje del contacto en el que WhatsApp deja contestar texto libre; ver
`blueprint/00-contrato.md` § 10—. Cerrada la ventana, WhatsApp sólo acepta plantillas aprobadas
—textos con huecos que Meta revisó de antemano, § 10 otra vez—; en Zernio eso es
`POST /v1/inbox/conversations`, y sin plantilla da `TEMPLATE_REQUIRED`.

**El recordatorio es otro turno, y por eso la regla 5 no lo corta.** Dispara con su propio reloj —el
`ahora` del momento en que corre, que no es el del ciclo que agendó— así que `anotar_saliente()` lo
cuenta como una vez más de hablar y no como el tercer mensaje del turno anterior. Esa cuenta es por
turno y no por mensaje, y está decidida en `blueprint/31-proveedores.md` paso 1. Contada por
mensaje, el turno que agenda deja `salientes_seguidos` en `MAX_SEGUIDOS` con sus dos salientes y
este recordatorio se niega antes de mirar la ventana, con el motivo de la insistencia: la cita
quedó, la confirmación salió, y la noche anterior no pasa nada. Es lo que mide la primera fila de la
tabla de acá abajo.

El nombre de la plantilla y sus variables van en `config/agenda.yaml`: no es una credencial, es
tuyo y se versiona. Darla de alta y esperar que Meta la apruebe es el pendiente 3 de
`PENDIENTES.md`, y se hace **antes** de la primera cita real.

**Tenés que ver.** Con plantilla y sobre SQLite, `cita.recordatorio_programado` en verdadero. Con
Postgres ya viene en falso desde el Paso 4 y el motivo es el otro: son dos frenos distintos y cada
uno dice el suyo. Sin plantilla, esto, antes de agendar y no después:

```
recordatorio de la cita del 2026-03-02 11:00: cae fuera de la ventana de 24 h.
plantilla `recordatorio_cita_24h`: no dada de alta. Ese recordatorio no va a salir.
La cita y la confirmación sí salen. Ver PENDIENTES.md → 3.
```

**Y el trabajo disparado, que es lo que hasta esta ronda no miraba nadie.**
`grep -rn recordar pruebas/ scripts/auditar.py` no imprimía una línea: el nodo del Paso 4 prueba
que **quedó** un trabajo con el id y la hora correctos, y ninguno probaba que ese trabajo **mande**
algo cuando dispare. Ahora lo hace
`pruebas/test_camino_feliz.py::test_recordatorio_el_trabajo_que_dispara_manda_por_enviar`, que saca
el trabajo del scheduler, lo corre por `func` y `args` como lo correría APScheduler, y afirma las
dos posiciones de la cita respecto de la ventana:

| La cita | El recordatorio cae | Lo que se afirma |
|---|---|---|
| dentro de 30 horas | dentro de la ventana | sale **un** mensaje, con la `Idempotency-Key` que pone `enviar()` |
| dentro de 30 días | con la ventana cerrada | lo que salga es plantilla. Texto libre acá es el segundo camino |

La `Idempotency-Key` —una cabecera con una clave sacada del contenido: conversación, paso y hash
del texto; ver `blueprint/00-contrato.md` § 10— es la huella de haber pasado por la única puerta, y
no la lleva un `.post` escrito adentro de `agente/integraciones/calendario.py`.

**Si falla.**

- **`TEMPLATE_REQUIRED`.** No hay plantilla, o mandaste texto libre por la ruta que abre
  conversación. Las dos rutas no son intercambiables, y quien elige es `enviar()`.
- **`131047` en Meta.** La misma ventana con otro nombre.
- **`132000`.** La plantilla existe, pero le mandaste otra cantidad de variables.
- **El recordatorio salió sin pasar por `enviar()`.** Ese es el segundo camino, y lo que se pierde
  no es un aviso: es el número de WhatsApp del negocio. Se lee así en la prueba de arriba: con la
  cita a treinta días, salió texto libre por el endpoint de mensajería con la ventana cerrada. El
  chequeo 13 `enviar-unico` también lo marca, y **no hace falta que la URL quede escrita acá**:
  alcanza con que `recordar()` importe la ruta de `agente/enviar.py` y la use en el renglón que arma
  el destino, porque la compuerta resuelve el nombre importado hasta la cadena que denota. Medido en
  esta máquina, sobre un árbol de cuatro módulos con `from agente.enviar import RUTA_LIBRE` y un
  `post` con el cliente único:

  ```
  [ERROR] enviar/salida_de_mensajeria  agente/integraciones/calendario.py:9
          `RUTA_LIBRE` denota el endpoint de envío de Zernio (`/inbox/conversations/…`),
          y esto no es agente/enviar.py
  ```

  Lo que la compuerta no ve es más chico de lo que dice `blueprint/00-contrato.md` § 12 en «lo que
  esta regla no ve»: resuelve constantes y nombres importados entre módulos, así que para que no lo
  marque el destino tiene que no estar escrito en ningún renglón —llegar del entorno o de un YAML en
  la corrida—. Esta prueba no descansa en eso igual: mide lo que salió al cable.
- **El trabajo dispara y no sale nada, con la ventana abierta.** `recordar()` quedó en un `return`
  pelado, o atrapa la excepción de `enviar()` y no la anota. El trabajo estaba: lo que faltaba era
  el cuerpo.
- **El trabajo dispara con la ventana abierta y el motivo dice que no se insiste más.** Ése no es
  `recordar()`: es `salientes_seguidos` contado por mensaje. El turno que agendó mandó dos y llegó
  al umbral, así que la regla 5 corta el tercero. Se cuenta una vez por `ahora`, o sea por turno;
  ver `blueprint/31-proveedores.md` paso 1.

---

### Paso 6 · El horario que se ocupó entre que se ofreció y se confirmó

**Objetivo.** No se pisa una reserva ajena. Se vuelve a ofrecer, y se dice con esas palabras.

**Hacé esto.** Calendar **deja** crear eventos superpuestos: no hay reserva atómica. Así que la
comprobación va pegada al `insert` y no al momento de ofrecer:
`POST https://www.googleapis.com/calendar/v3/freeBusy` con `timeMin`, `timeMax` y el calendario. Si
el hueco está ocupado **no se crea nada**: paso 4 `fallado` con el motivo, `cita` en nulo, y el
ciclo vuelve al paso 3, que es borrador y espera confirmación como cualquier otro mensaje.

El texto para el contacto, en el tratamiento elegido en Q3 —acá `tú`; con `vos` o `usted` cambia
entero—, sin disculpas largas y sin un horario que no esté en `disponibilidad`:

> Se me ocupó ese horario mientras confirmabas. Te dejo tres opciones nuevas: martes 2 a las 5 de
> la tarde, miércoles 3 a las 10 de la mañana o jueves 4 a las 4 de la tarde.

Y el aviso para vos:

```
El horario del 2026-03-02 11:00 se ocupó entre que se ofreció y se confirmó. No creé nada.
Paso 4: fallado. Volví a ofrecer 3 de `disponibilidad`. El borrador está en /bandeja.
```

**Tenés que ver.** `respuesta.horarios_ofrecidos` con tres horarios, los tres en `disponibilidad`,
y `cita` en nulo.

Que la comprobación esté **pegada al insert** no se ve en la salida de un turno que salió bien, así
que se mira del otro lado del cable: la prueba de la cita exige que el `POST` a `events` venga
después de un `POST` a `freeBusy` en la misma corrida. Es la única forma de distinguir un build que
comprueba de uno que ofrece con fe.

**Si falla.**

- **`freeBusy` devuelve 200 con la lista vacía, siempre.** Mirá `calendars[id].errors`: ese
  endpoint reporta `notFound` **adentro** de un 200. Es el permiso del Paso 1 otra vez.
- **Ofrece huecos ocupados todo el día.** `disponibilidad` sale de `config/agenda.yaml` y no del
  calendario. Si tu agenda real cambió y el YAML no, el `freeBusy` es lo único que lo agarra.
- **Quedan menos de tres huecos.** Ofrecé los que haya y decilo. Completar con uno inventado es
  fallo de la aserción 3, aunque el mensaje esté perfecto.
- **Se creó igual, encima del otro.** La comprobación quedó al ofrecer, no pegada al `insert`.

---

## Qué quedó hecho

La credencial de Google verificada a mano, en cualquiera de sus dos formas. El horario que el
contacto eligió, viajando por `mensaje.horario_elegido` y no adivinado. El evento sin invitados y
la confirmación por WhatsApp. El horario ocupado que no se pisa.

**El paso 4 tiene camino feliz por las dos credenciales, y la segunda es de esta ronda.** Con
confirmación explícita y con un horario elegido, el ciclo crea el evento y devuelve el `evento_id`
que dio Google, tanto con `authorized_user` —el token sale de un formulario— como con
`service_account` —el token sale de un JWT firmado con RS256, que `PyJWT` y `cryptography` ahora
firman—. No quedó ninguna rama detenida en este archivo salvo la del recordatorio con Postgres, que
es del Paso 4 y de otra librería. Lo que ya no existe es la tercera conducta: una `cita` en la
salida sin un evento en el calendario.

**El recordatorio de 24 horas depende de tu base, y esto es lo que quedó:**

- **Con SQLite**, programado en el scheduler del proceso, sobre la misma base, con barrido al
  arrancar y saliendo por `enviar()` como plantilla. **Las tres mitades tienen una aserción cada
  una desde esta ronda**: que quede el trabajo, que el trabajo mande al dispararse, y que el
  barrido lo devuelva cuando el `misfire` se lo llevó. Antes había una sola —la primera—, y las
  otras dos se podían contestar con un `return` pelado y una frase de la prosa.
- **Con Postgres —el camino recomendado del despliegue—, detenido.** `url_sincrona()` levanta
  `RecordatorioSinDriver`, `cita.recordatorio_programado` queda en falso con el motivo escrito, y la
  cita y la confirmación salen igual. Se levanta fijando un driver síncrono en `PINES.md`, que es un
  cambio del kit: la decisión está en `blueprint/00-contrato.md` § 8 y los tres archivos que se
  mueven juntos, en `PENDIENTES.md` → 8.

Y queda una cosa que ninguna prueba de acá cierra: la plantilla del recordatorio aprobada por Meta,
el pendiente 3 de `PENDIENTES.md`, que se da de alta antes de la primera cita real. El pendiente 4,
el calendario compartido, lo cerraste a mano en el Paso 1 si elegiste `service_account`.

**La detención del Paso 2 se levantó en esta ronda, y lo que cambió es esto.** Va escrito con el
detalle de siempre porque tres rondas se leyó como algo que iba a pasar:

1. **`PINES.md` fija `PyJWT==2.13.0` y `cryptography==50.0.0`**, verificados contra PyPI el
   2026-08-14, y `plantillas/infra/requirements.txt` trae las mismas dos líneas. La elección contra
   `google-auth` está argumentada ahí, con la corrida del chequeo 06 al lado: la raíz `google` mapea
   a `google-api-python-client` y sale rojo;
2. **la credencial `service_account` pasa por el mismo Paso 3 que la otra**, sin ninguna rama
   nueva: lo único que cambia es el cuerpo del `POST` al token;
3. **vuelve a hacer falta compartir el calendario a mano** si elegís esa credencial, que es el
   pendiente 4 de `PENDIENTES.md` y lo único que el camino de `authorized_user` no pide;
4. **la prueba de la rama detenida se cae de premisa.** Se reemplaza por la mitad feliz, con un par
   RSA generado por corrida en el `tmp_path`; la tabla de qué afirmar está en el Paso 2.

**Lo que sí hay que mover en el mismo cambio que este archivo**, porque son cuentas escritas en
otros lados y ninguna es mía:

- **`env.example`** describe `GOOGLE_SERVICE_ACCOUNT_JSON` como si sólo pudiera ser una cuenta de
  servicio. Son dos formas y el `type` decide; el nombre de la variable no cambia y no se agrega
  ninguna.
- **`SUPUESTOS.md` S05** se llama «Google Calendar por cuenta de servicio». Sigue siendo cierto lo
  que promete —sin invitados y la confirmación por WhatsApp— y le falta la segunda credencial. El
  supuesto nuevo, el del horario elegido, es un S13 que todavía no está escrito.
- **`blueprint/35-panel-api.md`**: `POST /api/pendientes/{id}/aprobar` vuelve a correr el paso con
  `confirmado: true`, y para el paso 4 tiene que llevar además el horario que eligió quien opera.
  Sin eso, aprobar el borrador del paso 4 desde la bandeja no agenda nada.
- **`blueprint/34-crm.md`**: con el paso 4 andando, la etapa `agendado` de la fila deja de ser
  inalcanzable.
- **`README.md`** todavía anuncia la detención de `service_account` como una limitación del kit,
  en el bloque que arranca «El camino `service_account` de Google Calendar está detenido». Ya no lo
  está. Es lo primero que lee quien evalúa si instalar esto.
- **`PENDIENTES.md` → 4** dice «sólo si vas por `service_account`, que hoy está detenido». El
  pendiente sigue siendo cierto y su motivo cambió: compartir el calendario no espera ninguna
  librería, se hace y listo.
- **`pruebas/test_camino_feliz.py`**: la constante `SERVICIO_DE_PRUEBAS` trae un `private_key` que
  no firma nada a propósito, y
  `test_cita_con_cuenta_de_servicio_y_sin_la_libreria_de_rs256_queda_detenido` afirma la detención.
  Los dos se caen de premisa. El reemplazo está en la tabla del Paso 2.
- **El número de dependencias pasa de 28 a 30**, y está escrito a mano en seis lugares:
  `README.md`, `plantillas/README.md`, `blueprint/00-mapa.md`, `blueprint/10-entorno.md` —cuatro
  veces— y dos mensajes de `scripts/auditar.py`. La compuerta no lo compara contra nada, así que no
  se pone rojo solo.

Anotalo en `.wca-estado.json` y corré la compuerta con el intérprete del proyecto
(`blueprint/00-contrato.md` § 5):

```bash
.venv/bin/python scripts/auditar.py
```

**Próximo archivo:** `blueprint/34-crm.md`, que escribe la fila del paso 5.
