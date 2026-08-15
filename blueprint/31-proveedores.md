# 31 · Los proveedores

Fase 3. Por dónde entra un mensaje y por dónde sale. Son tres —`meta`, `zernio` y `demo`— contra una
sola interfaz. Va después de `blueprint/30-generacion.md`, que ya dejó el núcleo de `agente/`: el
cliente HTTP, la base y el emisor del contrato.

Un mensaje entra por el webhook —el aviso automático que el proveedor le manda a tu servidor cuando
pasa algo; ver `blueprint/00-contrato.md` § 10— y sale por una sola función.

**Invariante 2, y acá se escribe entero: ningún mensaje a un contacto sale si no es por
`enviar()`.** Se decide por el **destino**, no por el verbo ni por el archivo: un POST a
`api.openai.com/v1/audio/transcriptions` no es un mensaje, y un POST a
`graph.facebook.com/<ver>/<id>/messages` sí lo es, esté donde esté escrito. Por eso las constantes
de destino viven acá y en ningún otro módulo, y por eso el paso 1 es la salida y no el primer
proveedor. Las tres guardas —ventana de 24 horas, chequeo de baneo, nunca escribirle primero
a quien no escribió— **se especifican en este archivo y en ninguno más**. Los otros seis archivos
que las nombran remiten acá.

**Invariante 3: un solo cliente HTTP**, en `agente/http.py`, con `timeout=`. **Invariante 1: las
firmas se verifican sobre el cuerpo crudo** —los bytes exactos de la petición, tal como llegaron por
el cable, antes de parsearlos; en FastAPI, `await request.body()`—, con el módulo que ya se copió a
`agente/firmas.py`; no se reescribe. Una firma es un HMAC —una huella criptográfica del cuerpo
calculada con un secreto compartido: el que manda la calcula, el que recibe la recalcula y compara;
ver `blueprint/00-contrato.md` § 10—. **Invariante 4: ninguna credencial en el árbol**; acá se
nombran variables y los valores los escribe quien instala.

---

### Paso 1 · Escribí el único camino de salida

**Objetivo.** Existe `agente/enviar.py` con todos los destinos de envío y las tres guardas escritas,
ningún otro módulo nombra un host de envío, los tres proveedores salen por el mismo cliente, y una
negativa sale como dato y no como excepción.

Este archivo lo escribís entero acá, y después se le agrega una sola función: `avisar_interno()`, el
aviso al canal interno del paso 6, que la escribe `blueprint/32-multimodal.md` paso 5 al final del
mismo archivo. Va ahí porque comparte los destinos: cuando el canal interno es un número, ese aviso
**sale por esta misma `enviar()`**, con `a_numero_interno` puesto. No es un segundo camino ni una
excepción al invariante 2: es el mismo camino, con una guarda eximida y declarada. Lo que va a tu
equipo por Slack no toca esta función, porque no es un mensaje de WhatsApp.

**Hacé esto.** Escribí el archivo entero. Es el paso más largo del kit y el que menos se puede
resumir: lo que se pierde cuando una de estas guardas falta no es una respuesta, es el número de
WhatsApp del negocio, y recuperarlo son semanas.

```python
"""El único camino de salida. Todo lo que le llega a una persona pasa por acá.

Cuatro tiempos, en este orden, y ninguno se saltea desde afuera:

  1. sin un entrante de ese contacto no se manda nada. El agente contesta: no abre
     conversaciones frías y no hace envíos masivos;
  2. `last_inbound_at` de esa conversación decide libre contra plantilla: fuera de las 24 horas
     WhatsApp solo acepta plantillas aprobadas, y sin plantilla no sale nada;
  3. el chequeo de baneo corre sobre el texto que va a salir, antes de mandarlo;
  4. el envío, con `Idempotency-Key` sacada del contenido: la conversación, el paso y el sha256
     del cuerpo, con el hash adentro de la clave y no encima de todo junto.

CLAUDE.md nombra las tres guardas en otro orden porque las enumera. Acá se ordenan por lo que
deciden: primero lo que no necesita mirar el texto.

Los tres proveedores recorren los cuatro tiempos enteros y salen por el mismo `CLIENTE`. `demo`
no tiene atajo: lo único que cambia es su base y quién contesta del otro lado.

Y una persona más del otro lado: tu compañero. Cuando `canal_interno` es un número de WhatsApp,
`avisar_interno()` —al final de este archivo— entra por acá con `a_numero_interno` puesto. Meta
no distingue el número de tu compañero del de un cliente: los dos son salientes del mismo número
de negocio, los dos caen bajo la ventana de 24 horas y los dos pesan en la calificación. Con
`a_numero_interno` cambia **una** cosa y está declarada abajo, en el tiempo 1.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from agente.ajustes import ajustes
from agente.base import anotar_saliente, conversacion, marcar_baja
from agente.http import CLIENTE

BASE_META = "https://graph.facebook.com/v21.0"    # la Graph API no es un pin de pip: va acá
RUTA_META = "/{phone_number_id}/messages"
BASE_ZERNIO = "https://zernio.com/api/v1"
BASE_DEMO = "https://demo.invalid/v1"    # `.invalid` está reservado y no resuelve nunca: RFC 2606
RUTA_ABRIR = "/inbox/conversations"                 # la abre el negocio: EXIGE plantilla
RUTA_LIBRE = "/inbox/conversations/{id}/messages"   # libre, solo dentro de las 24 h

VENTANA = timedelta(hours=24)
LIMITE_TEXTO = 4096      # el cuerpo de un mensaje de WhatsApp
MAX_SEGUIDOS = 2         # turnos sin respuesta antes de dejar de insistir. Turnos, no mensajes
PALABRAS_DE_BAJA = ("baja", "stop", "no me escribas", "no me escriban", "dejen de escribirme",
                    "no me contacten", "spam")


@dataclass(frozen=True, slots=True)
class Plantilla:
    nombre: str                  # el que Meta aprobó, tal cual
    idioma: str                  # "es_MX", "es_AR": el de la plantilla aprobada, no el del negocio
    variables: tuple[str, ...]   # en orden; otra cantidad es un 132000

    def previsualizacion(self) -> str:
        """Lo que mira el chequeo de baneo. El cuerpo de la plantilla ya lo revisó Meta; lo que
        cambia en cada envío son las variables, así que es lo que hay que mirar."""
        return " ".join(self.variables)


@dataclass(frozen=True, slots=True)
class Resultado:
    """Una negativa es un dato, no una excepción: entra en la salida del paso.

    Con excepción, cada uno de los seis pasos tendría que atraparla y el ciclo terminaría en
    `estado: "detenido"` por una ventana cerrada, que es el caso normal y no una falla.
    """
    enviado: bool
    ventana_abierta: bool | None
    motivo: str | None = None
    id_externo: str | None = None


async def enviar(proveedor, *, conversacion_id: str, paso: int, texto: str | None = None,
                 plantilla: Plantilla | None = None, ahora: datetime | None = None,
                 a_numero_interno: str | None = None) -> Resultado:
    ahora = ahora or datetime.now(timezone.utc)
    conv = await conversacion(conversacion_id)
    interno = a_numero_interno is not None

    # 1 · Nunca primero. Es lo primero porque decide sin mirar el texto ni la hora.
    sin_entrante = conv is None or conv.last_inbound_at is None
    if sin_entrante and not interno:
        return Resultado(False, None,
                         "sin entrante de este contacto: el agente contesta, no inicia")
    # LA EXENCIÓN, y es la única de esta función. Con `a_numero_interno` la falta de entrante no
    # corta el envío: lo obliga a plantilla, abajo. Ese número no te escribió porque lo
    # configuraste vos en Q9 y no tiene por qué escribirle nunca a su propio bot. La guarda no se
    # saltea: se cambia por el mecanismo que WhatsApp da para que el negocio escriba primero, que
    # es la plantilla aprobada por RUTA_ABRIR. Sin plantilla, esto se sigue negando.

    # 2 · La ventana, y con ella libre contra plantilla.
    if sin_entrante:                            # sólo el canal interno llega acá
        abierta = False                         # sin entrante no hay ventana: es plantilla o nada
    elif conv.window_expires_at is not None:    # Zernio la manda en `data.windowExpiresAt`
        abierta = ahora < conv.window_expires_at
    else:                                       # Meta no la manda: se calcula
        abierta = ahora - conv.last_inbound_at < VENTANA

    if abierta:
        cuerpo, ruta = texto, RUTA_LIBRE
    elif plantilla is None and interno:
        return Resultado(False, False,
                         f"el aviso interno al {a_numero_interno} no sale sin plantilla aprobada: "
                         f"ese número nunca le escribió al negocio, así que la ventana de 24 h "
                         f"está cerrada y WhatsApp sólo acepta plantillas. Ver "
                         f"blueprint/32-multimodal.md paso 5")
    elif plantilla is None:
        return Resultado(False, False,
                         f"la ventana de 24 h se cerró el "
                         f"{(conv.last_inbound_at + VENTANA):%Y-%m-%d %H:%M} UTC y no hay plantilla "
                         f"aprobada para el paso {paso}: ese mensaje no sale. Se dice ahora y no "
                         f"después. Ver PENDIENTES.md → 3")
    else:
        cuerpo, ruta = plantilla.previsualizacion(), RUTA_ABRIR

    # 3 · El chequeo de baneo, sobre el texto que va a salir.
    if conv is not None and conv.baja_en is None and pide_la_baja(conv.ultimo_entrante):
        conv = await marcar_baja(conv.conversacion_id, ahora)   # la baja es para siempre
    motivo = revisar_baneo(cuerpo, conv)
    if motivo:
        return Resultado(False, abierta, motivo)

    # 4 · El envío. Los tres proveedores salen por acá, por el mismo cliente y sin ninguna rama
    # que se saltee los tres tiempos de arriba.
    huella = hashlib.sha256(cuerpo.encode()).hexdigest()
    clave = f"{conversacion_id}|{paso}|{huella}"   # el hash es del texto, y va adentro de la clave
    # La forma del cuerpo la sabe el proveedor. `a=` va sólo en el camino interno: ahí el
    # destinatario no sale de la conversación, y un proveedor que no lo acepte falla ruidoso en
    # ese camino en vez de mandarle el aviso a otro.
    sobre = (proveedor.sobre(conv, cuerpo, plantilla, a=a_numero_interno) if interno
             else proveedor.sobre(conv, cuerpo, plantilla))
    r = await CLIENTE.post(destino(proveedor.nombre, conversacion_id, ruta), json=sobre,
                           timeout=10.0,
                           headers={**proveedor.cabeceras(), "Idempotency-Key": clave})
    if r.status_code >= 400:
        return Resultado(False, abierta, f"{proveedor.nombre} {r.status_code}: {r.text[:200]}")
    await anotar_saliente(conversacion_id, huella, ahora)
    return Resultado(True, abierta, None, proveedor.id_externo(r.json()))


def destino(nombre: str, conversacion_id: str, ruta: str) -> str:
    """La URL de envío. Es lo único que cambia entre los tres proveedores, y no la sabe ninguno.

    `demo` tiene base propia y las mismas dos rutas que `zernio`. No es una excepción ni un
    atajo: llega acá después de los mismos tres tiempos, con la misma `Idempotency-Key` y por el
    mismo `CLIENTE`. Lo único que cambia es quién contesta del otro lado, y eso es un transporte
    —ver el paso 3—, no una rama de esta función.

    Toma el `conversacion_id` y no la conversación: por RUTA_ABRIR todavía no hay fila que leer.
    """
    if nombre == "meta":
        return BASE_META + RUTA_META.format(phone_number_id=ajustes.whatsapp_phone_number_id)
    return {"zernio": BASE_ZERNIO, "demo": BASE_DEMO}[nombre] + ruta.format(id=conversacion_id)


def pide_la_baja(entrante: str | None) -> bool:
    texto = (entrante or "").strip().lower()
    return any(p in texto for p in PALABRAS_DE_BAJA)


def revisar_baneo(texto: str | None, conv) -> str | None:
    """Devuelve el motivo por el que ese texto no sale, o `None` si puede salir.

    Cinco reglas, todas mecánicas y todas locales: acá no se consulta a nadie. Las dos primeras
    miran el texto y nada más; las tres de abajo necesitan la fila de la conversación. Adentro de
    cada mitad van en orden de qué tan rápido bajan la calificación del número. No es pura
    prolijidad: Meta baja la calificación por bloqueos y reportes de los contactos, y la baja, el
    repetido y la insistencia son exactamente lo que hace que alguien te bloquee.
    """
    if not texto or not texto.strip():
        return "el texto vino vacío"
    if len(texto) > LIMITE_TEXTO:   # esto no es baneo, es un 400, y vive acá por ser el único lugar
        return f"el texto tiene {len(texto)} caracteres y WhatsApp admite {LIMITE_TEXTO}"
    if conv is None:
        # Sólo se llega acá por el canal interno y sólo en el primer aviso de esa fila: al
        # contacto lo cortó el tiempo 1. La fila la abre el `anotar_saliente()` de abajo, y desde
        # el segundo aviso las tres reglas que siguen corren enteras.
        return None
    if conv.baja_en is not None:
        return (f"el contacto pidió la baja el {conv.baja_en:%Y-%m-%d}: no se le escribe más, "
                f"tampoco con confirmación desde la bandeja")
    if hashlib.sha256(texto.encode()).hexdigest() == conv.ultimo_saliente_hash:
        return "es el mismo texto que ya se mandó en esta conversación"
    if conv.salientes_seguidos >= MAX_SEGUIDOS:
        return (f"van {conv.salientes_seguidos} turnos seguidos sin respuesta del contacto: "
                f"no se insiste más")
    return None
```

**Dos líneas de esa cabecera valen para todo el árbol y no sólo para este archivo.**

- `from agente.ajustes import ajustes` **es la única forma de traer la instancia**, acá y en
  cualquier módulo. `agente/__init__.py` queda vacío y no reexporta nada, así que
  `from agente import ajustes` te deja el módulo en la mano y el primer atributo que leas se cae con
  `AttributeError: module 'agente.ajustes' has no attribute ...`. Lo escribe
  `blueprint/30-generacion.md` paso 2 y el dueño de la regla es `blueprint/00-contrato.md` § 4.
- `from __future__ import annotations` **abre este archivo y los que siguen**, como en los dos
  módulos que ya copiaste verbatim. Con eso las anotaciones son cadenas en runtime:
  `inspect.signature()` las imprime entre comillas, y por eso la verificación de la firma de
  `correr_ciclo` —`blueprint/40-pruebas.md` paso 2, la única del kit que compara una firma impresa—
  tiene que pedir `eval_str=True`. La regla y la medición están en `blueprint/00-contrato.md` § 4.

La `Plantilla` la arma quien llama, y hoy la usa uno solo: el recordatorio del paso 4, que lee su
nombre y sus variables de `config/agenda.yaml`. Ver `blueprint/33-agenda.md`, paso 5.

**Lo que `enviar()` lee de `agente/base.py`**, que lo escribió el archivo anterior. No calcula nada
de esto: lo consulta.

| Función | Qué le da |
|---|---|
| `conversacion(id)` | `last_inbound_at`, `window_expires_at`, `ultimo_entrante`, `ultimo_saliente_hash`, `salientes_seguidos`, `baja_en` |
| `marcar_baja(id, ahora)` | deja la baja escrita y devuelve la conversación al día |
| `anotar_saliente(id, hash, ahora)` | guarda el hash del último saliente y suma uno a `salientes_seguidos` **la primera vez que ve ese `ahora`**. **Crea la fila si no está** |

`salientes_seguidos` lo vuelve a cero el entrante, en `agente/base.py`, y no acá: el contador mide
cuántas veces hablaste sin que te contesten.

**Y «veces» son turnos, no mensajes. Se decide acá porque hasta esta ronda no lo decidía ningún
archivo.** Un turno que agenda manda dos —la respuesta del paso 3 y la confirmación de la cita; ver
`blueprint/33-agenda.md` paso 3— y eso es una sola vez que hablaste. `correr_ciclo()` lee el reloj
una vez arriba de todo y se lo baja a los seis pasos, así que esos dos salientes entran acá con el
mismo `ahora`: **`anotar_saliente()` suma uno la primera vez que ve ese `ahora` en esa conversación,
y en las siguientes sólo guarda el hash.** El recordatorio del paso 4 dispara con el suyo —el del
momento en que corre— y por eso cuenta como otra vez.

Contado por mensaje, con `MAX_SEGUIDOS = 2`, el turno que agenda deja el contador en el umbral y el
recordatorio no sale nunca: la regla 5 lo corta antes de mirar la ventana, y lo que queda es un
agente que agendó bien y no avisó la noche anterior. Lo afirma
`pruebas/test_camino_feliz.py::test_recordatorio_el_trabajo_que_dispara_manda_por_enviar`, en su
mitad «dentro de la ventana».

**Esta ronda le pide dos cosas a `agente/base.py`**, que lo escribe `blueprint/30-generacion.md`
paso 3. La primera es ese «crea la fila si no está». Es lo que hace que el aviso al canal interno
tenga estado desde el segundo aviso: su fila no la abre ningún entrante —nadie le escribe a su
propio bot— así que la abre el saliente. Sin eso, el repetido no se mira nunca y el mismo aviso
puede salir dos veces. La fila del canal interno no tiene contacto: esa columna admite nulo.

La segunda es la que hace posible contar por turno: **la fila recuerda el `ahora` del último
saliente anotado, en `ultimo_saliente_en`, al lado de `ultimo_saliente_hash`**. Admite nulo, la
escribe el mismo `anotar_saliente()` y no la lee nadie más. Sin esa columna, `anotar_saliente()` no
tiene con qué saber si ese `ahora` ya pasó por acá, y el contador vuelve a ser por mensaje sin que
se note hasta el primer turno que agenda. La tabla de `conversaciones` la escribe
`blueprint/30-generacion.md`; acá se declara qué necesita la guarda y para qué.

**Cinco cosas del cuerpo que parecen detalle y no lo son.**

- **`ahora` entra por parámetro.** Sin eso las tres guardas no se pueden probar sin esperar 24
  horas. Las prueba `pruebas/test_enviar.py`, cada una en las dos direcciones y llamando a esta
  función de frente; ver `blueprint/40-pruebas.md`, Paso 2. Un `datetime.now()` metido adentro deja
  esas pruebas sin forma de correr. El conteo de nodos lo imprime
  `pytest pruebas/test_enviar.py --collect-only -q`, no un entero escrito acá.
- **Quién se lo pasa, y qué no es.** El `or datetime.now(timezone.utc)` de la primera línea es el
  default y no la fuente: **quien llama lo trae**. Desde un ciclo, `ahora` es el reloj que
  `correr_ciclo()` leyó una vez arriba de todo y baja a todos los pasos —una lectura por turno—;
  desde el recordatorio del paso 4, el de ese momento. **Lo que nunca se le pasa acá es
  `mensaje.recibido_en`**, que es cuándo llegó el mensaje y no qué hora es: con eso, la cuenta del
  tiempo 2 queda `recibido_en < recibido_en + 24 h` y esta guarda no se puede negar nunca. La
  decisión entera, con el porqué y con lo que le cuesta a los fixtures, está en
  `blueprint/40-pruebas.md` paso 2; acá alcanza con saber de dónde sale el valor que entra.
- **`enviar()` no recibe `deps`, y los tres nombres de `agente.base` se importan a nivel de
  módulo.** Es el `from agente.base import anotar_saliente, conversacion, marcar_baja` de la
  cabecera, y se queda así: a `enviar()` la llaman los seis pasos, la bandeja del panel y el
  recordatorio de la agenda, y un contenedor de dependencias que hay que arrastrar por todas esas
  llamadas es el que alguien se saltea en la próxima. La consecuencia cae dos fases más adelante y
  conviene saberla ahora: **el punto de reinicio de la suite no puede ser un parámetro de esta
  función, tiene que ser el motor en curso de `agente/base.py`**, que `armar_deps()` reemplaza
  antes de cada prueba. Sin ese reemplazo, el ciclo escribe en la base de `deps` y `enviar()` lee la
  de la aplicación —dos bases en la misma prueba—. Ver `blueprint/40-pruebas.md`, paso 2, que es
  donde eso está escrito entero.
- **`ventana_abierta` del `Resultado` es el campo `respuesta.ventana_abierta` del contrato**, y
  `enviado` es `respuesta.enviado`. Salen de acá y de ningún otro lado. Ponerlos a mano porque el
  paso corrió es la falla que se lee como «`enviado: true` y no llegó nada».
- **El proveedor no conoce ninguna URL.** Sabe la forma del cuerpo (`sobre`), sus cabeceras y dónde
  viene el id en la respuesta. El destino lo elige `enviar()`.
- **Ninguna rama devuelve antes del `.post`.** Había una, la de `demo`, y es la que dejaba once
  nodos en rojo a quien seguía el kit al pie de la letra. Está contada acá abajo, con nombre.

**La `Idempotency-Key` lleva el hash adentro, y no es un hash de todo junto.** La forma es
`f"{conversacion_id}|{paso}|{sha256(cuerpo)}"`: tres piezas separadas, y el sha256 sobre el texto y
nada más. Es lo que dicen `blueprint/00-contrato.md` § 10, `blueprint/35-panel-api.md` paso 6 y
`blueprint/60-bandeja.md` —«conversación, paso y hash del texto»—, y hasta esta ronda el
bloque de arriba hacía otra cosa: `sha256(f"{conv}|{paso}|{cuerpo}")`, un solo hash encima de
las tres.

Las dos formas son determinísticas y las dos cambian cuando cambia el texto, así que
`pruebas/test_idempotencia.py` pasa con cualquiera de las dos. Lo que la forma vieja no puede hacer
es **contener** el hash del texto, y eso es lo que se lee del otro lado: un sha256 no contiene a
otro sha256. `pruebas/test_bandeja.py` exige `huella(fila["texto"]) in envio.idempotency_key`, o sea
que la clave del mensaje que salió al aprobar traiga adentro la huella del borrador que se aprobó.
Es la forma de saber que ese mensaje lo mandó `enviar()` con ese texto y no el handler del panel por
su cuenta. Con la clave hasheada entera, quien copie el bloque se lleva ese nodo en rojo.

`huella` sale una sola vez y se usa dos: la clave de este envío y el `ultimo_saliente_hash` que
`anotar_saliente()` deja para la regla 4 del turno siguiente. El mismo hash del mismo texto, y no
dos cuentas que se pueden desincronizar.

**El canal interno por número: qué guarda corre, cuál se exime y por qué.**

Cuando `canal_interno` es un número de WhatsApp, el aviso del paso 6 entra por esta función con
`a_numero_interno` puesto. **Una exención, escrita en el cuerpo, y ninguna más.** Una exención
tácita es lo que dejó vivir un segundo camino de salida entero con la compuerta en verde; ésta se
declara acá, se explica en dos renglones y la afirma
`test_el_aviso_al_numero_interno_sale_por_plantilla_y_con_clave_del_contenido`.

| Tiempo | Con `a_numero_interno` | Por qué |
|---|---|---|
| 1 · nunca primero | **eximido**: no corta, obliga a plantilla | ese número no te escribió porque lo configuraste vos en Q9. No se saltea la guarda: se cambia por el mecanismo que WhatsApp da para escribir primero, que es la plantilla aprobada por `RUTA_ABRIR` |
| 2 · la ventana de 24 h | corre, y da **cerrada** siempre | sin entrante no hay ventana. De ahí sale que el aviso interno por número salga **siempre** con plantilla, y nunca en texto libre |
| 3 · el chequeo de baneo | corre entero desde el segundo aviso de esa fila | el primero no tiene fila que consultar y sólo se le miran el vacío y el largo. Del segundo en adelante, el repetido corta: el mismo aviso reintentado no le llega dos veces a tu compañero |
| 4 · la `Idempotency-Key` | corre igual | sale de la conversación, el paso y el hash del cuerpo. El esquive que esta ronda saca salía sin ninguna |

**La conversación del canal interno es una por chat escalado**, no una por número:
`interno:<numero>:<conversacion_del_contacto>`. Con una sola fila por número, `salientes_seguidos`
llegaría a `MAX_SEGUIDOS` a la tercera escalación del día y el canal se apagaría solo, en silencio,
que es la peor forma de fallar que tiene un canal de avisos. Una fila por chat escalado lo resuelve
sin eximir nada: cada fila ve un aviso, y el repetido sigue mordiendo donde tiene que morder —el
mismo chat avisado dos veces—.

Dos cosas que no son exenciones y conviene decir igual. La baja nunca dispara sobre esas filas,
porque ningún entrante las toca: el canal interno no se apaga con un «stop», se apaga cambiando
`canal_interno`. Y el aviso por Slack no entra por acá en ningún caso: no es un mensaje de
WhatsApp, no sale del número del negocio y no toca su calificación.

**El `return` temprano de `demo`, y por qué ya no está.**

Hasta esta ronda el tiempo 4 arrancaba con `if proveedor.nombre == "demo": return await
proveedor.entregar(sobre, clave)`. O sea: el proveedor que el kit manda poner —`20-entrevista.md`
paso 4 deja `WHATSAPP_PROVIDER=demo`, y el paso 10 lo recomienda— era el único que no llegaba al
cable.

Lo que eso rompe no es una prueba, son tres cosas:

1. **Cualquier doble que envuelva el transporte deja de ver los envíos.** Es como está armada la
   suite —`ProveedorFalso` se enchufa abajo del cliente único, a propósito, para que la ventana, el
   baneo y el dedupe corran de verdad—, así que con `demo` `doble.envios` daba `[]` siempre y once
   nodos caían con `AssertionError: no salió ningún mensaje ... assert []`. Con `meta`, la misma
   suite y el mismo build: 154 en verde. El rojo era del proveedor por defecto, no del build.
2. **La razón escrita de que `demo` exista se contradecía sola.** El paso 3 dice, y sigue
   diciendo, que `demo` reproduce entregas reales grabadas —mismos bytes, misma cabecera, mismo
   camino de deduplicación— porque si fuera un transporte falso el usuario modal no ejercitaría el
   código de seguridad hasta un sábado a solas. Un `return` antes del cable es exactamente ese
   transporte falso.
3. **`demo` quedaba fuera de todo lo que pasa después del `.post`**: la `Idempotency-Key`, el
   manejo del 4xx y `anotar_saliente()`, que es lo que alimenta la regla 4 y la regla 5 del turno
   siguiente.

Ahora `demo` recorre los cuatro tiempos enteros y sale por `CLIENTE`. Quién le contesta está en el
paso 3.

**Tenés que ver.** El chequeo 13 en verde y la primera guarda negándose sin credenciales:

```bash
.venv/bin/python scripts/auditar.py | grep "enviar-unico"
```

```
  [ok      ] 13 enviar-unico       12 módulo(s) revisados
```

El número de módulos cambia con lo que lleves escrito; lo que importa es el `[ok`. Y después:

```bash
.venv/bin/python - <<'PY'
import asyncio
import agente.base as b
from agente.enviar import enviar

async def main():
    await b.migrar()
    return await enviar(None, conversacion_id="no-existe", paso=3, texto="hola")

print(asyncio.run(main()))
PY
```

```
Resultado(enviado=False, ventana_abierta=None, motivo='sin entrante de este contacto: el agente contesta, no inicia', id_externo=None)
```

El proveedor va en `None` a propósito: la guarda decide antes de tocar el transporte. Y los tres
destinos, que tienen que ser tres y distintos:

```bash
.venv/bin/python - <<'PY'
from agente.enviar import destino, RUTA_LIBRE

for n in ("meta", "zernio", "demo"):
    print(n, destino(n, "conv_demo", RUTA_LIBRE))
PY
```

```
meta https://graph.facebook.com/v21.0/<tu phone_number_id>/messages
zernio https://zernio.com/api/v1/inbox/conversations/conv_demo/messages
demo https://demo.invalid/v1/inbox/conversations/conv_demo/messages
```

Y la exención del canal interno, que se ve en que el motivo cambie. Con el mismo `enviar()` y la
misma conversación inexistente, el aviso interno deja de contestar «sin entrante» y pasa a
contestar por la ventana:

```bash
.venv/bin/python - <<'PY'
import asyncio
import agente.base as b
from agente.enviar import enviar

async def main():
    await b.migrar()
    return await enviar(None, conversacion_id="interno:5215500000099:conv_demo", paso=6,
                        texto="Escalación", a_numero_interno="5215500000099")

print(asyncio.run(main()).motivo)
PY
```

```
el aviso interno al 5215500000099 no sale sin plantilla aprobada: ese número nunca le escribió al negocio, así que la ventana de 24 h está cerrada y WhatsApp sólo acepta plantillas. Ver blueprint/32-multimodal.md paso 5
```

El proveedor va en `None` otra vez y por lo mismo: sin plantilla, esto se niega antes de tocar el
transporte. La exención no manda nada por su cuenta —cambia qué guarda decide—, y eso es todo lo
que hace.

**Si falla.**

- **`AttributeError: 'NoneType' object has no attribute 'sobre'`.** El orden quedó al revés: estás
  armando el envío antes de preguntar si esa persona escribió alguna vez.
- **`enviar/sin_modulo`.** `agente/` existe y `agente/enviar.py` no. Escribí el archivo y repetí.
- **`enviar/segundo_camino` en `agente/ajustes.py`.** Nombrar el host afuera ya es el error: la
  constante se importa desde cualquier lado y el `post` que la usa no sale en ningún grep.
- **`enviar/salida_de_mensajeria`.** Un envío a un destino de mensajería escrito fuera de este
  archivo. Se mira a dónde va: un POST a `api.openai.com` o a Google Calendar no es un mensaje y no
  lo marca; uno a `graph.facebook.com/<ver>/<id>/messages`, a `zernio.com/api/v1/inbox/…` o a
  `demo.invalid/v1/inbox/…` sí lo es, esté en el módulo que esté. Si venís de una ronda anterior del
  kit, el id que buscabas era `enviar/salida_suelta`: ése decidía por verbo y no existe más. Los dos
  que la compuerta emite hoy están en `blueprint/00-contrato.md` § 12.
- **El aviso al canal interno contesta «sin entrante de este contacto».** Le falta
  `a_numero_interno` en la llamada, o el `and not interno` del tiempo 1. Es la exención declarada
  arriba, y sin ella un `canal_interno` en un número no avisa nunca.
- **El aviso al canal interno sale en texto libre.** Le pasaste `texto=` en vez de `plantilla=`, y
  la ventana de ese número está cerrada siempre. Del otro lado eso es un `131047` por escalación y
  la calificación gastada igual. La plantilla la arma `avisar_interno()`;
  ver `blueprint/32-multimodal.md` paso 5.
- **`AttributeError: 'NoneType' object has no attribute 'baja_en'`.** `revisar_baneo()` quedó sin
  la rama `conv is None`. Con el canal interno se llega ahí en el primer aviso de cada fila: esa
  fila la abre el saliente y todavía no existe.
- **`TypeError: sobre() got an unexpected keyword argument 'a'`.** Un proveedor quedó con la firma
  vieja. Es el camino interno y sólo ese: al contacto sigue saliendo igual. Ver el paso 2.
- **`doble.envios` da `[]` y el build está bien.** Volvió una rama que devuelve antes del `.post`.
  Con el transporte doblado sólo se ve lo que sale por el cable, así que un proveedor que no llega
  ahí se lee como un agente que no contesta. Ver el apartado del `return` temprano de `demo`.
- **`huella(fila["texto"]) in envio.idempotency_key` da falso.** La clave quedó hasheada entera
  —`sha256(f"{conv}|{paso}|{cuerpo}")`— y un sha256 no contiene a otro. Las tres piezas van
  separadas y el hash es del texto: `f"{conversacion_id}|{paso}|{huella}"`, como en el tiempo 4.
- **El recordatorio del paso 4 se niega con «no se insiste más», con la ventana abierta.**
  `anotar_saliente()` está sumando uno por mensaje: el turno que agendó mandó dos y dejó el contador
  en `MAX_SEGUIDOS`. Se suma una vez por `ahora`, o sea por turno; ver la tabla de arriba y
  `blueprint/33-agenda.md` paso 5.
- **La ventana lee cerrada con la ventana abierta, y sin ninguna traza.** `last_inbound_at` se
  guardó sin pasarlo a UTC. El `DateTime` de SQLAlchemy sobre SQLite **no guarda el offset**: se
  come el `-06:00` y escribe la hora de pared. Un `2026-03-01T22:14:00-06:00` vuelve como
  `2026-03-01 22:14:00` sin `tzinfo`, el build le estampa UTC al leer, y desde ahí el entrante
  figura seis horas antes de lo que fue. Medido en esta máquina, con SQLAlchemy 2.0.52:

  ```
  escrito    2026-03-01 22:14:00-06:00 · tzinfo UTC-06:00
  vuelto     2026-03-01 22:14:00 · tzinfo None
  leído  UTC 2026-03-01 22:14:00+00:00 · corrido -1 day, 18:00:00

  ahora      2026-03-03 00:00:00+00:00
  van desde el entrante real: 19:46:00
  ventana con lo que se escribió: abierta
  ventana con lo que volvió:      cerrada
  ```

  **Pasa en las pruebas, no sólo en producción.** Los fixtures traen el offset escrito, y ése es
  justamente el que se pierde. Cae toda una franja de `pruebas/test_enviar.py` —la ventana, la
  baja, el repetido, la insistencia, el vacío y el límite—; el conteo exacto lo imprime
  `pytest pruebas/test_enviar.py -q` y cambia según qué variante escribiste. Todos menos los de
  la ventana caen de rebote: esperan un motivo de `revisar_baneo()`, que es el tiempo 3, y reciben
  el de la ventana cerrada, que devuelve en el tiempo 2. El mensaje sí nombra una fecha —el motivo
  interpola el cierre de la ventana—, pero es la fecha del corpus y no se parece a un problema de
  zona horaria: leerlo no te lleva al offset que se perdió al escribir.

  **Y no sale un solo `TypeError` en toda la corrida.** La traza
  `can't subtract offset-naive and offset-aware datetimes` es de la otra variante, la que deja el
  naive tal cual en vez de estamparle UTC; buscarla acá es buscar algo que no está. La cura es la
  misma de siempre: guardalo en UTC y con `tzinfo`, convirtiendo al escribir y no al leer.
- **El endpoint de medios de Meta también vive en `graph.facebook.com`.** `agente/medios.py` importa
  `BASE_META` de acá; no vuelve a escribir el host. Ver `blueprint/32-multimodal.md`, paso 1.
- **No hay `grep` (Windows).** Corré `.venv\Scripts\python.exe scripts\auditar.py` a secas y leé la
  línea 13.

---

### Paso 2 · La interfaz común

**Objetivo.** Existe `agente/proveedores/base.py`, y un proveedor que se olvide de verificar la
firma no llega a instanciarse.

**Hacé esto.** Una base abstracta y un `Mensaje` plano. **Las funciones toman `bytes`, nunca un
dict**: es lo que hace imposible la implementación que se lee bien y firma sobre
`json.dumps(await request.json())`.

```python
@dataclass(frozen=True, slots=True)
class Mensaje:
    contacto_id: str     # el ancla: `businessScopedUserId` en Zernio, `wa_id` en Meta
    numero: str | None   # puede venir nulo desde abril de 2026
    conversacion_id: str
    tipo: str            # "texto" | "audio" | "imagen"
    texto: str | None
    media_id: str | None
    recibido_en: str     # ISO 8601 con offset
    evento_id: str       # la clave del dedupe de entrada


class Proveedor(ABC):
    nombre: str          # "meta" | "zernio" | "demo": lo lee `enviar()` para elegir el destino

    @abstractmethod
    def parsear_webhook(self, crudo: bytes) -> list[Mensaje]: ...

    @abstractmethod
    def verificar_firma(self, crudo: bytes, cabeceras: Mapping[str, str]) -> bool: ...

    @abstractmethod
    def sobre(self, conv, cuerpo: str, plantilla, *, a: str | None = None) -> dict: ...

    @abstractmethod
    def cabeceras(self) -> dict[str, str]: ...

    @abstractmethod
    def id_externo(self, respuesta: dict) -> str | None: ...

    @final
    async def enviar(self, **kw):
        from agente.enviar import enviar as _enviar   # diferido: enviar.py importa este módulo
        return await _enviar(self, **kw)
```

`verificar_firma` es abstracta: un proveedor nuevo no puede olvidarla porque no instancia.
`parsear_webhook` devuelve lista porque Meta empaqueta varios mensajes en una entrega. `sobre`,
`cabeceras` e `id_externo` son lo que `enviar()` le pide al transporte: la forma del cuerpo, las
cabeceras y dónde leer el id de la respuesta. Ninguna nombra un host.

**El `a` de `sobre()` es el destinatario cuando no sale de la conversación**, y hoy hay uno solo:
el número del canal interno. Con `a=None` —el camino al contacto, que es el de siempre— el destino
lo pone la conversación y esta firma no cambia nada. Va acá y no en un método propio porque en la
Cloud API de Meta el destinatario viaja **adentro del cuerpo** (`to`), y el cuerpo lo arma el
proveedor: sacarlo de acá obligaría a que `enviar()` supiera la forma del sobre de cada uno.

`enviar` es `@final` y delega, así que ningún proveedor tiene una URL de envío adentro ni puede
saltearse una guarda con una implementación propia.

**Los tres proveedores implementan estos cinco métodos y ninguno más.** `demo` no suma ninguno:
tener uno propio es lo que le habilitaba un camino propio adentro de `enviar()`, y ése es el
defecto que esta ronda saca. Lo que `demo` agrega no es un método del proveedor, es un transporte
—paso 3—, que vive un escalón más abajo y al que `enviar()` no le pregunta nada.

`agente/proveedores/__init__.py` expone `elegir(nombre, **kw)`, que devuelve la instancia del
proveedor configurado en `WHATSAPP_PROVIDER` y es lo único que el resto del árbol importa de acá.
Con `demo`, además deja el transporte de demostración bajo el cliente único **si nadie puso otro**:
manda quien corre el proceso. La suite pone su doble antes, y ahí `elegir()` no toca nada.

**Tenés que ver.** Que la base rechace un proveedor incompleto:

```bash
.venv/bin/python - <<'PY'
from agente.proveedores.base import Proveedor
class Roto(Proveedor):
    def parsear_webhook(self, crudo): return []
try: Roto()
except TypeError as e: print("TypeError", "verificar_firma" in str(e))
PY
```

```
TypeError True
```

**Si falla.**

- **`Roto()` se construye.** Falta `ABC` en la herencia, o el `@abstractmethod` quedó abajo de otro
  decorador.
- **`ImportError` o un ciclo de importación.** El import de `agente.enviar` va adentro del método:
  `enviar.py` importa este módulo para tipar el proveedor.
- **PowerShell no tiene heredoc.** Guardá esas líneas en `verificar.py` y corré
  `.venv\Scripts\python.exe verificar.py`. Vale para los pasos que siguen.

---

### Paso 3 · `demo`

**Objetivo.** El proveedor por defecto reproduce entregas grabadas, sale por el mismo cable que
`meta` y `zernio`, ejercita el mismo código de seguridad que producción, y no toca la red.

**Hacé esto.** Dos piezas en `agente/proveedores/demo.py`: el proveedor y su transporte.

**El proveedor** lee `pruebas/fixtures/`. **No es un transporte falso**: levanta los mismos bytes
crudos con `read_bytes()`, arma la misma cabecera de firma desde el `.meta.json` y llama a la misma
`verificar_firma` que corre contra Meta. Si fuera falso, quien elige `demo` en Q10 —casi todo el
mundo— no ejercitaría el camino de firmas ni el de dedupe hasta un sábado a solas.

Tres reglas. El secreto sale del `.meta.json` y no de `.env`. La clave de dedupe sale del `eventId`
del cuerpo, porque una entrega grabada no trae cabeceras. Y al reproducir se escribe
`last_inbound_at = ahora`, sin tocar un byte del `.raw`.

Implementa los cinco métodos de la base y ninguno más. Su `sobre()` es el de Zernio, porque usa las
dos rutas de Zernio, y su `id_externo()` lee `messages[0].id`.

**El transporte** es lo que contesta del otro lado, y es la mitad que faltaba:

```python
"""El otro lado del cable, para el proveedor `demo`.

Es un transporte de httpx, o sea que se enchufa **abajo** del cliente único. No es un atajo
adentro de `enviar()`: para cuando esto corre, los cuatro tiempos del paso 1 ya corrieron
enteros, la `Idempotency-Key` ya está en las cabeceras y `anotar_saliente()` va a correr con lo
que esto devuelva.

Contesta **solamente** `demo.invalid`, que es el host de `BASE_DEMO` y por lo tanto no se
escribe acá: se importa. Cualquier otro host levanta, y levanta fuerte: un transporte de
demostración que conteste `graph.facebook.com` es un agente que cree que mandó y no mandó.
"""

import itertools
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from agente.enviar import BASE_DEMO

HOST_DEMO = urlsplit(BASE_DEMO).hostname   # "demo.invalid"
ENTREGAS = Path("demo/entregas.jsonl")
_CONTADOR = itertools.count(1)


class TransporteDemo(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.host != HOST_DEMO:
            raise RuntimeError(
                f"el transporte de demostración recibió {request.url.host} y sólo contesta "
                f"{HOST_DEMO}. Algo lo dejó abajo del cliente único con un proveedor que no es "
                f"`demo`, y con eso el agente cree que mandó y no mandó.")
        ENTREGAS.parent.mkdir(parents=True, exist_ok=True)
        with ENTREGAS.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "url": str(request.url),
                "idempotency_key": request.headers.get("idempotency-key"),
                "cuerpo": request.read().decode("utf-8", "replace"),
            }, ensure_ascii=False) + "\n")
        return httpx.Response(
            200, request=request,
            json={"messages": [{"id": f"wamid.DEMO{next(_CONTADOR):04d}"}]})
```

**Por qué `demo.invalid` y no `localhost`.** `.invalid` está reservado por la RFC 2606 y ningún
resolver lo puede mapear a una dirección. O sea que la propiedad «`demo` no sale a internet» no
depende de que el transporte esté puesto: si alguien lo saca, la petición muere en la resolución de
nombre, local, antes de abrir un socket a ningún lado. Con `localhost` sí abriría uno —a tu máquina,
pero uno— y con un host de verdad saldría a internet el día que el transporte falte.

**Dónde queda la entrega.** En `demo/entregas.jsonl`, una línea por envío, con la URL, la
`Idempotency-Key` y el cuerpo. Son mensajes tuyos y de tus clientes, así que la carpeta no se
versiona:

```bash
grep -q '^/demo/' .gitignore || printf '\n/demo/\n' >> .gitignore
```

**No es la bandeja.** La bandeja son los borradores del modo `borrador`, que ni siquiera llegan a
`enviar()`; la escribe `blueprint/60-bandeja.md` y no tiene nada que ver con el proveedor. Con el
`return` temprano las dos cosas se decían con la misma frase —«`entregar()` deja el borrador donde
lo lee `/bandeja`»— y eran mecanismos distintos: uno es el modo, el otro es el transporte.

**Tenés que ver.** El proveedor parseando la entrega grabada:

```bash
.venv/bin/python -c "from agente.proveedores.demo import Demo; m=Demo(caso='zernio').reproducir()[0]; print(m.contacto_id, m.numero, m.evento_id)"
```

```
bsu_01HZK3M9QX7T2VW4 None evt_01JQ8Z3K7Y2M4N6P8R0T2V4X6A
```

Y, lo que esta ronda existe para arreglar, **la suite entera en verde con el proveedor que el kit
manda poner**, sin exportar nada y con el `.env` tal como lo dejó `20-entrevista.md` paso 4:

```bash
grep WHATSAPP_PROVIDER .env
.venv/bin/python -m pytest pruebas -q
```

```
WHATSAPP_PROVIDER=demo
NN passed
```

`NN` es el total que imprime esa misma corrida, y va sin el entero a propósito: acá decía `154`, la
suite creció cuatro rondas seguidas y el número quedó mintiendo cada una de las cuatro. El que manda
lo imprime `pytest pruebas --collect-only -q` y crece con el kit; lo que no se negocia es que no
haya ninguno rojo y que el proveedor sea `demo`. Si tenés que poner
`WHATSAPP_PROVIDER=meta` para que la suite pase, volvió el `return` temprano: ver el paso 1.

**Si falla.**

- **La firma del fixture no verifica.** Casi siempre es `read_text()` en vez de `read_bytes()`, o un
  editor que agregó un salto de línea al final del `.raw`: un cuerpo HTTP no lo trae y un byte de
  más cambia el MAC. `git checkout pruebas/fixtures/`.
- **`enviar()` se niega y pide plantilla.** Correcto: el fixture es de marzo de 2026 y la ventana
  venció. Lo arregla la tercera regla de arriba, no aflojar la guarda.
- **Alguien regeneró los fixtures con `json.dumps`.** Se pierde el espaciado torcido, y desde ahí
  una implementación que reserializa pasa la prueba. Ver `pruebas/fixtures/README.md`.
- **`httpx.ConnectError` nombrando `demo.invalid`.** El transporte no quedó abajo del cliente
  único. Es el modo de falla correcto y por eso el host es `.invalid`: se ve como lo que es, y no
  como una entrega a un servidor ajeno. Revisá `elegir()`, paso 2.
- **`RuntimeError` desde el transporte de demostración.** Quedó puesto con `WHATSAPP_PROVIDER=meta`
  o `zernio`. Es a propósito: contestar por un proveedor real es el peor de los dos errores.
- **La suite verde y `demo/entregas.jsonl` vacío.** No es un defecto: en la suite el que contesta es
  el doble, no este transporte. Los dos ocupan el mismo lugar y por eso `demo` se puede auditar.

---

### Paso 4 · `meta`

**Objetivo.** Las entregas de la Cloud API se verifican y se parsean, y el alta del webhook queda
contestada como texto plano.

**Hacé esto.** Tres piezas en `agente/proveedores/meta.py`.

**Firma.** `from agente.firmas import verificar_meta, responder_alta_meta`. Cabecera
`X-Hub-Signature-256`, valor `sha256=<hex>` sobre el cuerpo crudo. El secreto es
**`META_APP_SECRET`** y se pasa explícito:

```python
verificar_meta(crudo, cabecera=cabeceras[CABECERA_META], secreto=ajustes.meta_app_secret)
```

Es obligatoria con `WHATSAPP_PROVIDER=meta` y se usa acá y en ningún otro archivo. Sale de
developers.facebook.com → tu app → Configuración → Básica → **Clave secreta de la app**, tapada
detrás de «Mostrar», que te vuelve a pedir la contraseña de la cuenta. **No es `WHATSAPP_TOKEN`**
—ése autoriza a mandar— **ni `WHATSAPP_VERIFY_TOKEN`** —ése lo inventás vos y sólo sirve para el
alta—: son tres valores distintos de la misma pantalla. Ver `blueprint/00-contrato.md` § 7.

**Parseo.** El sobre es `entry[].changes[].value.messages[]`, con el contacto en
`value.contacts[].wa_id`. `timestamp` viene en segundos Unix y como cadena. El `evento_id` es el
`id` del mensaje —el `wamid.…`—, estable entre reintentos.

**Alta.** Llega como GET con `hub.mode`, `hub.verify_token` y `hub.challenge`, y se contesta el
challenge verbatim y **como texto plano**:
`PlainTextResponse(responder_alta_meta(...), media_type=TIPO_RESPUESTA_ALTA)`. Un
`JSONResponse("1158201444")` manda las comillas adentro del cuerpo: dos bytes de más, y el alta no
ocurre sin ningún error a la vista.

**Tenés que ver.** Este comando prueba los dos proveedores con credencial, así que sirve también
para el paso 5:

```bash
.venv/bin/python - <<'PY'
import json, pathlib
from agente.proveedores import elegir
for n in ("meta", "zernio"):
    crudo = pathlib.Path(f"pruebas/fixtures/{n}.raw").read_bytes()
    f = json.loads(pathlib.Path(f"pruebas/fixtures/{n}.meta.json").read_text())
    p, cab = elegir(n, secreto=f["secreto"]), {f["cabecera"]: f["firma"]}
    m = p.parsear_webhook(crudo)[0]
    print(n, p.verificar_firma(crudo, cab),
          p.verificar_firma(json.dumps(json.loads(crudo)).encode(), cab), m.contacto_id, m.numero)
PY
```

```
meta True False 5215500000000 5215500000000
zernio True False bsu_01HZK3M9QX7T2VW4 None
```

El `False` vale tanto como el `True`: una implementación que reserializa no puede reproducir el MAC.

**Si falla.**

- **401 en todas las entregas, desde la primera.** `META_APP_SECRET` mal copiada, o el
  `WHATSAPP_TOKEN` puesto en su lugar. Los tres valores se leen parecido y sólo uno firma.
- **`TypeError: … necesita bytes`.** Le pasaste el cuerpo ya parseado. En FastAPI es `await
  request.body()`.
- **`KeyError: 'messages'`.** La entrega trae `statuses`: los recibos de tus propios mensajes, por
  el mismo webhook. Devolvé lista vacía y 200. Tratados como mensajes, el agente se contesta a sí
  mismo en un bucle que no para solo.
- **`131047` al enviar.** Pasaron más de 24 horas desde el último mensaje del contacto. No es
  credenciales: es la ventana, y se contesta con plantilla aprobada.
- **401 al día siguiente, sin cambios.** El token de la pantalla de configuración dura 24 horas. El
  permanente sale de un usuario del sistema del Business Manager con `whatsapp_business_messaging`.
- **El `from` trae un dígito de más** (México, Argentina). No lo normalices: contestá al valor tal
  como llegó. Un número arreglado a mano es un mensaje que se va a otro lado.

---

### Paso 5 · `zernio`

**Objetivo.** El webhook contesta 2xx en menos de 5 segundos, deduplica, los dos caminos de envío
quedan separados, y lo que corre después de esa respuesta no vuelve nunca por acá arriba, ni
siquiera cuando se rompe.

**Hacé esto.** Base `https://zernio.com/api/v1`, `Authorization: Bearer sk_...`. La firma va en
`X-Zernio-Signature`: hex minúscula **sin** el prefijo `sha256=` de Meta. El SDK no se instala: la
verificación necesita el cuerpo crudo, que ningún SDK entrega.

**El presupuesto de 5 segundos**, en este orden y sin nada en el medio:

```
crudo = await request.body()        1. bytes, antes de cualquier parseo
verificar_firma(crudo, cabeceras)   2. 401 si no cuadra: sin firma no merece ni un json.loads
evento_id = cabeceras[...]          3. X-Zernio-Event-Id
INSERT ... ON CONFLICT DO NOTHING   4. si no insertó, ya lo viste: 200 y nada más
return Response(status_code=200)    5. antes del modelo
```

**El trabajo del modelo nunca va en línea.** Los seis pasos corren después de la respuesta. Un ciclo
con una llamada al modelo adentro pasa los 5 segundos, Zernio lo toma por caído y reintenta hasta 7
veces: la entrega es al-menos-una-vez, y el mismo lead recibe la misma respuesta cuatro veces.

**Y lo que pasa cuando ese ciclo revienta: se atrapa todo y no sube nada.** Es la otra mitad del
paso 5 y no estaba escrita en ningún archivo. Del lado 5 del orden de arriba la respuesta **ya
salió**: el 200 está en el cable y la fila del dedupe está escrita, así que ese evento no vuelve.
Una excepción que suba desde ahí no la recibe nadie —no queda ningún pedido al que contestarle
500—; lo único que hace es matar el ciclo a la mitad **sin dejar rastro**: el paso no queda en
`fallado`, el motivo no queda en ningún lado, y quien abre `/bandeja` ve silencio en vez de ver qué
se rompió. Con `BackgroundTask` de starlette el orden es explícito y está medido en esta máquina
con starlette 1.3.1: `Response.__call__` manda `http.response.start`, manda
`http.response.body`, y **recién ahí** hace `await self.background()`.

Lo que va en su lugar, en la función que corre después del 200 —`_atender()`, o como la llames—:

```python
async def _atender(entrada: dict, evento_id: str) -> None:
    try:
        await correr_ciclo(entrada, modelo=modelo_de_produccion(), deps=deps)
    except Exception:              # a propósito: acá no hay a quién levantarle nada
        registro.exception("el ciclo del evento %s murió", evento_id)
        await marcar_ciclo_fallado(entrada, evento_id)   # el motivo, donde una persona lo lea
```

Tres cosas de ese cuerpo, y ninguna es prolijidad:

- **`except Exception` sin filtrar.** No es tapar el error: es no perderlo. Lo que se atrapa se
  escribe en dos lugares —el registro del proceso y la conversación— y ninguno de los dos es «se
  cayó y no sé».
- **No se reintenta acá.** El evento ya está deduplicado: reintentar en línea es correr el modelo
  dos veces sobre el mismo mensaje. El reintento sale de la cola, con el `evento_id` adentro.
- **No se convierte en un código distinto.** El 200 ya salió; devolver otra cosa no es posible y
  buscarlo es lo que lleva a mover el 200 después del modelo, que es el defecto del párrafo de
  arriba.

**Por qué esto no aparece hasta la fase 2, y aparece de golpe.** Sin `config/playbook.yaml` el
camino webhook→ciclo está muerto —el handler no tiene con qué armar la entrada— y además el chequeo
20 de la compuerta saltea, así que el veredicto es `parcial` y nunca `pass`. O sea que **el primer
día en que alguien pone el playbook para llegar al `pass` es el mismo día en que ese camino corre
por primera vez**, y lo que se ve es la suite del webhook en rojo con una excepción del ciclo
adentro. Lo afirma
`pruebas/test_enviar.py::test_el_ciclo_que_revienta_despues_del_200_no_sube_por_el_webhook`, que
reemplaza `correr_ciclo` por uno que levanta y exige el 200 igual. Medido en esta máquina con
fastapi 0.141.1: con la excepción subiendo, `TestClient` la re-levanta **en la petición que ya
había contestado**, así que el nodo que se pone rojo es cualquiera del webhook y su mensaje no
nombra al ciclo por ningún lado.

**Parseo.** `event` tiene que ser `message.received` y `data.message.direction`, `inbound`. La
conversación está en `data.conversationId`, y `data.windowExpiresAt` es la respuesta del propio
proveedor sobre la ventana de 24 horas: guardala en `window_expires_at` y dejá que `enviar()` la use
en vez de calcularla. `deliveryAttempt` mayor que 1 es un reintento, no un error.

**Las dos rutas de envío no son intercambiables.** `POST /v1/inbox/conversations` la abre el negocio
y **exige** plantilla aprobada —un texto con huecos que Meta revisó de antemano—; sin ella devuelve
`TEMPLATE_REQUIRED`. `POST /v1/inbox/conversations/{id}/messages` es libre y solo dentro de las 24
horas. Quien elige entre las dos es `agente/enviar.py` mirando `last_inbound_at`, y nadie más: el
cuerpo que lo hace está en el paso 1 de este archivo.

**Medios.** `GET /v1/whatsapp/media/{mediaId}?accountId=...` **con** `Authorization`, y
`ZERNIO_ACCOUNT_ID` es obligatoria y no se deduce de la clave. Cuándo se baja, dónde queda el
archivo y por qué no va en el handler: `blueprint/32-multimodal.md`, paso 1, que es el único que lo
especifica.

**Los Workflows.** Dejá **todos** en pausa antes de conectar, en zernio.com → panel → Workflows. Uno
activo puede consumir los entrantes antes que tu consumidor, y la documentación no dice si suprime
la entrega o compite con ella: esta compuerta falla con cualquiera activo, y las dos posibilidades
se arreglan distinto. Después se mide, no se deduce.

**Tenés que ver.** La fila `zernio` del comando del paso 4, y un `1` por cada mensaje que te mandes
al número con el webhook conectado:

```bash
grep -c "message.received" registro.log
```

**Si falla.**

- **401 permanente que se lee como un secreto mal copiado.** Se copió la función de Meta sin sacar
  el prefijo `sha256=`. Es la única diferencia de formato entre los dos.
- **`TEMPLATE_REQUIRED`.** Si sale desde `enviar()`, la `Plantilla` que le pasaste no está aprobada
  del otro lado: el nombre y el idioma son los de la plantilla que aprobó Meta, no los del negocio.
  Si sale desde cualquier otro módulo, es un segundo camino, y ése es el hallazgo grave.
- **429.** Respetá el `Retry-After` de la respuesta, en segundos. No inventes un backoff propio ni
  reintentes en línea: el reintento sale de la cola, después del 200.
- **El conteo da `0`.** Un workflow consumió la entrega: pausalo y repetí. **Da `2` o más por un
  solo mensaje:** no es supresión, es competencia, y el dedupe por `X-Zernio-Event-Id` es lo único
  que evita la respuesta duplicada. Anotá lo que te dio, con fecha, en `PENDIENTES.md`.
- **El mismo lead contestado cuatro veces.** El dedupe no es atómico: un `SELECT` y después un
  `INSERT` lo pasan los dos reintentos concurrentes. Va un solo `INSERT ... ON CONFLICT DO NOTHING`
  y se decide por si insertó.
- **Un nodo del webhook se pone rojo con una excepción que no es del webhook**, y aparece el mismo
  día en que pusiste `config/playbook.yaml`. Eso es el ciclo re-levantando desde el
  `BackgroundTask`, y el nodo que lo cuenta es cualquiera que haga una entrega: `TestClient`
  re-levanta lo que suba por el stack, y lo hace en la petición que ya contestó 200. Se arregla en
  `_atender()`, con el cuerpo de arriba, y no en la prueba.
- **La entrega contesta 200 y la conversación queda a medias, sin una línea en `/bandeja`.** El
  ciclo murió después del 200 y nadie lo atrapó, o lo atrapó y no escribió nada. El evento ya está
  deduplicado: no vuelve, así que lo que no se escriba en ese momento se pierde para siempre.

---

### Paso 6 · Identidad e idempotencia

**Objetivo.** Todo lo guardado se indexa por un identificador que no puede faltar, y ningún
reintento —de ellos o tuyo— se cobra dos veces.

**Hacé esto.** El ancla es `businessScopedUserId` en Zernio y `wa_id` en Meta. Va en
`mensaje.contacto_id` y es la clave de la conversación, del CRM y del dedupe. **`phoneNumber` puede
venir nulo desde abril de 2026.** Cuando no hay número, `contacto.numero` de la salida lleva
`bsuid:<id>`, con prefijo a propósito para que lo que intente marcarlo falle fuerte en vez de marcar
mal.

La idempotencia son **dos trabajos distintos**, y se escriben separados:

| | Entrada | Salida |
|---|---|---|
| Qué | dedupe de eventos recibidos | `Idempotency-Key` en el envío |
| Clave | `X-Zernio-Event-Id`; el `wamid.…` en Meta; el `eventId` del cuerpo en `demo` | conversación, paso y hash del texto |
| Dónde | tabla propia de `agente/base.py`, antes del 200 | cabecera de la petición, en el tiempo 4 del paso 1 |
| Si falla | el modelo corre dos veces sobre el mismo mensaje | la persona recibe el mismo mensaje dos veces |

La clave de salida es determinística: el mismo borrador reintentado tiene que producir la misma
clave, o el proveedor no puede saber que es el mismo envío. Por eso en el paso 1 es
`f"{conversacion_id}|{paso}|{sha256(cuerpo)}"` y nunca un `uuid`. El hash es del texto y va adentro
de la clave: hasheada entera, la clave deja de contener la huella del borrador, que es por donde la
bandeja verifica que ese mensaje salió por `enviar()`.

**Tenés que ver.** El mismo evento entra una sola vez:

```bash
.venv/bin/python - <<'PY'
import asyncio
import agente.base as b

async def main():
    await b.migrar()
    return await b.registrar_evento("evt_01JQ8Z"), await b.registrar_evento("evt_01JQ8Z")

print(*asyncio.run(main()))
PY
```

```
True False
```

**Si falla.**

- **`TypeError: 'NoneType' object is not subscriptable` al armar la fila del CRM.** Estás indexando
  por número, y el fixture de Zernio trae `phoneNumber` nulo justo para eso. `contacto.numero` vacío
  o con el id pelado se ve igual que un número roto: va con el prefijo `bsuid:` o no va.
- **Las dos veces dice `True`.** La clave cambia entre entregas. `deliveryAttempt` sube en cada
  reintento: si entró en la clave, cada reintento se ve nuevo.
- **La tabla de eventos crece sin fin.** Es un dedupe, no un historial: una fila por evento con su
  fecha, y un barrido de lo de hace más de siete días.
- **`Idempotency-Key` con un uuid nuevo por intento.** Eso no es idempotencia, es un contador. La
  clave sale del contenido.

---

## Qué quedó hecho

`agente/enviar.py` con los destinos de envío —tres bases y tres rutas—, las tres guardas escritas,
ningún destino de mensajería afuera y una sola exención declarada, la del canal interno.
`agente/proveedores/` con la base abstracta y los tres transportes, todos tomando `bytes`, todos
con los mismos cinco métodos y ninguno con un host adentro. Los tres saliendo por el mismo cliente, `demo` incluido, y la suite entera en verde con
`WHATSAPP_PROVIDER=demo`. Cada fixture verificando y su reserializado fallando. El dedupe de entrada
y la clave de salida, separados.

Anotalo en `.wca-estado.json`: `fase` en `proveedores`, el proveedor elegido y el sha256 de cada
archivo escrito.

**Próximo archivo:** `blueprint/32-multimodal.md`, que baja el audio y la imagen, los hace leer, y
escribe los cuerpos de los pasos 1, 2, 3 y 6 encima de este `enviar()`.
