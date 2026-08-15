"""Los dobles de la suite: el transporte falso, el modelo que miente a pedido y el arnés.

Nada de este archivo abre un socket ni lee una credencial. Es la condición para que la suite
entre en la compuerta; ver `blueprint/40-pruebas.md`.

## Por qué el doble envuelve el transporte y no `enviar()`

**Invariante 2: todo lo que sale del agente pasa por un solo `enviar()`.** Un doble que
reemplace `enviar()` deja afuera justo lo que hay que probar: la ventana de 24 horas —el plazo
desde el último mensaje del contacto en el que WhatsApp deja contestar texto libre—, el chequeo
de baja y la regla de no escribir primero. Todas viven adentro de `enviar()`.

Así que `ProveedorFalso` se pone un escalón más abajo: es el transporte HTTP que usa el cliente
único de `agente/http.py`. `enviar()` corre entero y lo que sale queda anotado acá.

**Eso pide una cosa del build, y hasta esta ronda no se cumplía: los tres proveedores tienen que
llegar al cable.** Un proveedor con un `return` antes del `.post` es invisible desde acá, y no se
lee como «este proveedor no manda» sino como «el agente no contesta»: `envios` da `[]` y cae la
aserción de otro. Le pasaba a `demo`, que es el que el kit manda poner —`blueprint/20-entrevista.md`
paso 4—, así que el build fiel al blueprint llegaba a once nodos rojos y el mismo build con
`WHATSAPP_PROVIDER=meta` a 154 en verde. Se arregló en `enviar()`, no acá: ver
`blueprint/31-proveedores.md`, paso 1.

## El único lugar donde se decide la forma de `deps`

`agente/ciclo.py` todavía no está escrito, así que la forma exacta de `deps` no se puede leer
del disco. `armar_deps()` es el único lugar de la suite que la decide: el día que el build
aterrice y no coincida, se corrige acá y no en cinco archivos de prueba.

Mientras `agente/` no exista, todo el arnés levanta `SinAgente` con el motivo escrito. Las
pruebas lo traducen a un salteo con ese texto adentro. Un salteo con motivo no es un aprobado,
y se lee distinto de una prueba que pasa por vacía.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PRUEBAS = Path(__file__).resolve().parent
FIXTURES = PRUEBAS / "fixtures"

# El corte entre «esto es un mensaje al contacto» y «esto es un aviso al equipo» se hace **por
# host**, y recién después por el destinatario que la llamada declara. Nunca buscando una cadena
# adentro del cuerpo.
#
# El aviso interno que el kit manda escribir sale por un webhook entrante de Slack —`SUPUESTOS.md`
# S09, `blueprint/32-multimodal.md` paso 5, y `env.example` en el bloque de la escalación—, y ahí
# el canal no aparece por ningún lado de la llamada: viaja adentro de la URL secreta, que es lo que
# dice el comentario de `SLACK_WEBHOOK_URL`, «cada webhook queda atado a un canal: para avisar en
# otro canal se genera otro webhook». El cuerpo es `{"text": …}` y nada más. Buscando el nombre del
# canal en la URL o en el cuerpo, ese aviso no aparece nunca y el paso 6 se lee como si no hubiera
# avisado, con el build haciendo exactamente lo que el kit prescribe.
HOST_SLACK = "hooks.slack.com"

# Los tres hosts de envío salen de `BASE_META`, `BASE_ZERNIO` y `BASE_DEMO` de `agente/enviar.py`;
# las rutas, de `RUTA_META`, `RUTA_LIBRE` y `RUTA_ABRIR`. Se piden los dos y no uno:
#
# - la ruta sola se come la llamada al modelo, que es un POST a `api.anthropic.com/v1/messages` y
#   trae `/messages` igual que el envío. Con el transporte enchufado abajo del cliente único
#   —`enchufar_transporte()`, que es como corren las pruebas del webhook— esa llamada la ve el
#   doble en cada prueba, y contada como envío el dedupe queda afirmado sobre el mensaje al modelo;
# - el host solo deja pasar la bajada de medios, que también vive en `graph.facebook.com`.
#
# `demo.invalid` está en la lista por lo mismo que los otros dos y no por ser de mentira: con el
# `return` temprano afuera, `demo` sale por el mismo cliente y por las mismas rutas, y un envío que
# el doble no cuenta es un envío que nadie audita. El TLD `.invalid` está reservado por la RFC 2606
# y no resuelve: es lo que hace que ese destino no pueda salir a internet aunque nadie doble el
# transporte.
#
# Juntos dicen «esto es un mensaje», nunca «a quién va»: eso lo decide `_va_al_canal()`.
HOSTS_DE_MENSAJERIA = ("graph.facebook.com", "zernio.com", "demo.invalid")
RUTAS_DE_MENSAJE = ("/messages", "/inbox/conversations")

# Los nombres con los que un cuerpo de envío dice a quién va. `to` es el de la Cloud API de Meta,
# el mismo que `pruebas/test_caso_02.py` imprime cuando el conteo de envíos falla. Se leen como
# campo del cuerpo parseado y nunca como subcadena: un número que aparezca adentro del texto del
# mensaje no cambia a quién va dirigido.
CAMPOS_DE_DESTINO = ("to", "para", "destinatario", "recipient", "phone_number", "numero")

# Cómo se reconoce un envío con plantilla aprobada, que es lo único que WhatsApp deja salir con la
# ventana de 24 horas cerrada. Los dos proveedores lo dicen distinto y por eso se miran los dos:
# Zernio y `demo` abren la conversación por `RUTA_ABRIR` —`/inbox/conversations` pelada, sin
# `/messages` al final— y Meta usa el mismo endpoint de siempre con `type: "template"` adentro del
# cuerpo. El aviso al canal interno por número sale siempre así: ese número nunca le escribió al
# negocio, así que su ventana está cerrada por definición. Ver `blueprint/31-proveedores.md` paso 1.
RUTA_DE_PLANTILLA = "/inbox/conversations"
CAMPOS_DE_PLANTILLA = ("template", "plantilla")

# Lo que sobra cuando un número de teléfono se escribe a mano.
_SEPARADORES_DE_NUMERO = " -()+. ‑–"


def numero_de_whatsapp(valor: str | None) -> str | None:
    """Los dígitos de `valor` si es un número de WhatsApp, o `None` si no lo es.

    `contratos/entrada.schema.json` deja dos formas para `canal_interno`: «un canal de Slack, o un
    número interno de WhatsApp si no hay Slack». La primera trae letras y arranca con `#`; la
    segunda es dígitos, con o sin `+`, con espacios o con guiones. Comparar por dígitos es lo que
    hace que `+52 155 0000 0099` y `5215500000099` sean el mismo destino y no dos.
    """
    if not valor:
        return None
    limpio = "".join(c for c in str(valor).strip() if c not in _SEPARADORES_DE_NUMERO)
    return limpio if limpio.isdigit() else None


# Los once campos del esquema angosto, en el orden de `plantillas/contratos/wire_schema.py`.
# El modelo emite esto y nada más: `pasos`, `estado`, `enviado`, `escrito`, `cita`, `handoff` y
# `horarios_ofrecidos` los decide el código. Lo que no se pregunta no se puede mentir.
CAMPOS_WIRE = (
    "intencion",
    "score",
    "presupuesto",
    "presupuesto_evidencia",
    "urgencia",
    "motivo",
    "texto",
    "objecion_detectada",
    "resumen",
    "proximo_paso",
    "proximo_paso_fecha",
)


# ─────────────────────────────────────────────────────────────────────────────
# Qué falta para correr contra el build
# ─────────────────────────────────────────────────────────────────────────────


class SinAgente(RuntimeError):
    """El build todavía no está en el árbol. Trae el motivo legible en `str(e)`."""


def _falta(*relativos: str) -> list[str]:
    return [r for r in relativos if not (RAIZ / r).is_file()]


def motivo_sin_ciclo() -> str:
    """Por qué no se puede correr `correr_ciclo`, o cadena vacía si se puede."""
    faltan = _falta("agente/__init__.py", "agente/ciclo.py")
    if not faltan:
        return ""
    return (
        f"falta el build: no existe {', '.join(faltan)}. `correr_ciclo(entrada, *, modelo, "
        f"deps)` la escribe blueprint/40-pruebas.md paso 2, y llega recién después de las "
        f"fases 3 y 4. Corré /armar-cerrador y volvé a esta suite."
    )


def motivo_sin_servidor() -> str:
    """Por qué no se puede levantar el webhook, o cadena vacía si se puede."""
    faltan = _falta("agente/__init__.py", "agente/servidor.py")
    if faltan:
        return (
            f"falta el build: no existe {', '.join(faltan)}. `agente/servidor.py` y sus diez "
            f"rutas las escribe blueprint/35-panel-api.md; ver blueprint/00-contrato.md § 3."
        )
    try:
        importlib.import_module("fastapi.testclient")
    except ModuleNotFoundError as e:
        return (
            f"falta {e.name} en este intérprete: sin cliente de prueba no hay forma de "
            f"reproducir una entrega firmada contra el webhook. Corré esto con el `.venv` del "
            f"proyecto, que instala requirements.txt entero."
        )
    return ""


def exigir_ciclo() -> None:
    motivo = motivo_sin_ciclo()
    if motivo:
        raise SinAgente(motivo)


# ─────────────────────────────────────────────────────────────────────────────
# La variable del aviso interno: falsa, inyectada por fixture y por ningún otro lado
# ─────────────────────────────────────────────────────────────────────────────

# El aviso del paso 6 sale por el webhook entrante de Slack que trae `SLACK_WEBHOOK_URL`, y sin esa
# variable el paso queda `fallado` con el motivo —`SUPUESTOS.md` S09, `blueprint/32-multimodal.md`
# paso 5—. O sea que un build FIEL al blueprint, corrido en una suite que no pone nada, no avisa
# nunca: ocho nodos del caso 02 se ponen rojos por hacer exactamente lo prescrito, y la única
# salida que le queda a quien construye es escribir una URL de webhook adentro del árbol.
#
# **Esto no es una credencial.** Es una URL inventada, con la forma de una de Slack y con `TEST`
# adentro de los dos identificadores, que no existe del otro lado y que además nunca sale del
# proceso: `ProveedorFalso` reemplaza el transporte del cliente único, así que el POST se anota acá
# y no abre un socket. Ninguna corrida de esta suite pide una credencial, que es lo que promete
# `blueprint/40-pruebas.md`.
#
# Va por fixture y no por `os.environ` a nivel de módulo para que se deshaga sola al terminar cada
# prueba, y para que `sin_variable()` pueda sacarla en la prueba que afirma S09.
SLACK_WEBHOOK_DE_PRUEBAS = (
    "https://hooks.slack.com/services/T00000000TEST/B00000000TEST/pruebas-sin-credencial"
)


def olvidar_el_build() -> None:
    """Saca `agente*` de `sys.modules` para que el próximo import relea el entorno.

    Hace falta porque los ajustes se leen **una vez, al importar** —es lo que hace
    pydantic-settings, y lo que hace cualquier módulo con una constante arriba—. Sin esto, la
    variable que pone la fixture no se ve: para cuando corre `pruebas/test_caso_02.py`, otro
    archivo de la suite ya importó el build con el entorno de antes, y el módulo cacheado se queda
    con el valor viejo. Poner la variable sin olvidar el build deja la fixture sin efecto en media
    suite, y el rojo se lee como un defecto del build.
    """
    for nombre in [m for m in sys.modules if m == "agente" or m.startswith("agente.")]:
        del sys.modules[nombre]


@pytest.fixture
def slack_de_pruebas(monkeypatch) -> Iterator[str]:
    """Pone `SLACK_WEBHOOK_URL` con la URL inventada, y deja el build listo para releerla."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", SLACK_WEBHOOK_DE_PRUEBAS)
    olvidar_el_build()
    yield SLACK_WEBHOOK_DE_PRUEBAS
    # Antes de que `monkeypatch` saque la variable, para que el próximo import la relea sin ella.
    olvidar_el_build()


@contextmanager
def sin_variable(nombre: str) -> Iterator[None]:
    """Corre el bloque con `nombre` fuera del entorno y con el build releído desde cero.

    Es la otra mitad de `slack_de_pruebas`: sin esto no hay forma de afirmar lo que promete S09
    —sin la variable, el paso 6 queda `fallado` con el motivo—, porque la fixture la pone para
    todo el archivo. Sacarla del entorno no alcanza: el build ya la leyó al importarse.
    """
    previo = os.environ.pop(nombre, None)
    olvidar_el_build()
    try:
        yield
    finally:
        if previo is not None:
            os.environ[nombre] = previo
        olvidar_el_build()


# ─────────────────────────────────────────────────────────────────────────────
# El transporte falso
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Llamada:
    """Una petición HTTP que salió del agente, tal como la vio el transporte."""

    metodo: str
    url: str
    ruta: str
    host: str
    cabeceras: dict[str, str]  # claves en minúscula, como las normaliza HTTP
    cuerpo: bytes

    @property
    def datos(self) -> Any:
        """El cuerpo parseado, o None si no es JSON. Para mirar, nunca para firmar."""
        try:
            return json.loads(self.cuerpo)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    @property
    def idempotency_key(self) -> str | None:
        return self.cabeceras.get("idempotency-key")

    @property
    def texto(self) -> str:
        """El cuerpo como texto, para mirar qué dice un aviso sin adivinar la forma del cuerpo.

        Es para las aserciones que revisan el contenido —que el aviso nombre al contacto, el
        motivo y el enlace al chat—, nunca para decidir a dónde va la llamada. Eso se decide por
        host y por destinatario declarado; ver `ProveedorFalso._va_al_canal`.
        """
        return self.cuerpo.decode("utf-8", "replace")

    @property
    def destinatario(self) -> str | None:
        """A quién dice ir esta llamada, leído como campo del cuerpo y nunca como subcadena.

        Devuelve `None` cuando el cuerpo no lo declara, que es el caso de la ruta libre de Zernio:
        ahí el destino viaja en el `conversacion_id` de la URL, que la suite no conoce.
        """
        datos = self.datos
        if not isinstance(datos, dict):
            return None
        for campo in CAMPOS_DE_DESTINO:
            valor = datos.get(campo)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
        return None

    @property
    def es_plantilla(self) -> bool:
        """Si esta llamada sale con una plantilla aprobada en vez de con texto libre.

        Se mira por los dos caminos, porque los dos proveedores lo dicen distinto: la ruta que abre
        la conversación —`RUTA_ABRIR` de Zernio y de `demo`— y el `type: "template"` del cuerpo,
        que es como lo dice Meta sobre el mismo endpoint de siempre.

        Un envío con plantilla no se afirma por prolijidad: es lo único que WhatsApp acepta con la
        ventana de 24 horas cerrada, y la ventana del canal interno está cerrada siempre. Un aviso
        interno que salga en texto libre es el `131047` que el equipo lee del otro lado.
        """
        if self.ruta.rstrip("/").endswith(RUTA_DE_PLANTILLA):
            return True
        datos = self.datos
        if not isinstance(datos, dict):
            return False
        if str(datos.get("type") or "").lower() == "template":
            return True
        return any(datos.get(campo) for campo in CAMPOS_DE_PLANTILLA)


class ProveedorFalso:
    """El transporte que usa el cliente único de `agente/http.py` durante las pruebas.

    Anota cada petición y contesta 200 sin salir a la red. No inventa un segundo cliente: se
    enchufa al que ya existe, así el chequeo `http-unico` de la compuerta sigue valiendo.

    `envios` son los mensajes al contacto y `avisos` los del paso 6 al canal interno. **La
    separación es por destino —host y destinatario declarado—, no por ruta y no por buscar una
    cadena adentro del cuerpo.** Eso es lo único que la hace cierta con las dos formas que
    documenta `contratos/entrada.schema.json`: `canal_interno` es «un canal de Slack, o un número
    interno de WhatsApp si no hay Slack».

    - **Slack.** El aviso se postea a `hooks.slack.com` con `{"text": …}` y **sin el canal en
      ninguna parte de la llamada**: el canal viaja adentro de la URL secreta del webhook. Se
      reconoce por el host, que es lo único que hay. No es un mensaje de WhatsApp, no toca la
      calificación del número y no depende del modo: sale en los dos.
    - **Un número interno de WhatsApp.** El aviso sale por `enviar()`, por el mismo endpoint de
      envío que el mensaje al contacto, así que lo único que los separa es el destinatario que el
      cuerpo declara. Cortando por ruta contaba como un segundo envío —«exactamente un envío» rojo
      por algo que no es un bug del agente— y el aviso se dejaba de auditar en silencio.

    **Contar los dos por separado no alcanza, y por eso está `por_whatsapp`.** El aviso por número
    es un mensaje de WhatsApp con todo lo que eso implica, así que cae bajo la promesa del modo:
    en `borrador` no sale, igual que la línea al contacto. Esa promesa se afirma sobre la suma.

    El destino que se declara desde afuera es uno solo, el canal interno, con `apuntar(entrada)`,
    que llama `correr_turnos()` por cada entrada del bucle. Al contacto no se lo declara: con la
    ruta libre de Zernio va direccionado por el `conversacion_id` de la URL, que la suite no
    conoce, así que se lo define por descarte —mensajería que no va al canal—. El aviso de Slack
    no necesita ese `apuntar`: se reconoce igual aunque nadie haya declarado nada.

    Se cuenta lo que vio el transporte, no lo que el agente dice que hizo, que es justo la
    diferencia que atrapa el bug de los dos mensajes.
    """

    def __init__(self, *, responder=None) -> None:
        self.llamadas: list[Llamada] = []
        self._responder = responder
        self.canales: set[str] = set()

    def apuntar(self, entrada: dict) -> None:
        """Le dice al doble cuál es el canal interno de este ciclo.

        Se acumula, no se pisa: los turnos de un mismo bucle pueden traer otra entrada, y el
        aviso del primer turno tiene que seguir contándose como aviso en el segundo.
        """
        canal = entrada.get("canal_interno")
        if canal:
            self.canales.add(str(canal))

    @property
    def numeros_internos(self) -> set[str]:
        """Los `canal_interno` declarados que son un número de WhatsApp, en dígitos.

        Los que son un canal de Slack no entran acá, y no hacen falta: ese aviso se reconoce por
        el host y no por el nombre del canal, que no viaja en ninguna parte de la llamada.
        """
        return {n for n in (numero_de_whatsapp(c) for c in self.canales) if n}

    # ── la interfaz de httpx ──────────────────────────────────────────────

    def handle_request(self, request):  # httpx.BaseTransport
        return self._resolver(request)

    async def handle_async_request(self, request):  # httpx.AsyncBaseTransport
        return self._resolver(request)

    async def aclose(self) -> None:
        return None

    def close(self) -> None:
        return None

    # `httpx.AsyncClient` entra al transporte con `async with` en cuanto alguien abre el cliente
    # así —`async with httpx.AsyncClient(transport=…)`, que es la forma de manual—. Sin estos
    # cuatro, el build correcto revienta con `AttributeError: 'ProveedorFalso' object has no
    # attribute '__aenter__'`, que se lee como un defecto del kit y no del build. Son los mismos
    # que trae `httpx.AsyncBaseTransport`; no se hereda de ella para no importar httpx al
    # importar este módulo.
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_) -> None:
        return None

    # ── lo que la suite mira ──────────────────────────────────────────────

    def _es_mensajeria(self, llamada: Llamada) -> bool:
        """Si esa llamada publica un mensaje por el endpoint de envío del proveedor.

        Host y ruta, los dos. Dice «esto es un mensaje», nunca «a quién va».
        """
        if llamada.metodo != "POST":
            return False
        host = llamada.host or ""
        if not any(host == h or host.endswith("." + h) for h in HOSTS_DE_MENSAJERIA):
            return False
        return any(ruta in llamada.ruta for ruta in RUTAS_DE_MENSAJE)

    def _va_al_canal(self, llamada: Llamada) -> bool:
        """Si esa llamada le habla al canal interno del equipo.

        Las dos formas del contrato, y ninguna depende de que el nombre del canal aparezca en el
        cuerpo:

        - **un POST a `hooks.slack.com` es un aviso interno**, siempre. El canal vive adentro de
          la URL del webhook y no se puede leer desde acá; tampoco hace falta, porque a ese host
          no le sale otra cosa que el aviso del paso 6;
        - **un mensaje cuyo destinatario declarado es el canal interno**, cuando ése es un número
          de WhatsApp. Ahí sale por el mismo endpoint que el mensaje al contacto y lo único que
          los separa es a quién va.

        Al contacto no se lo busca: con la ruta libre de Zernio va direccionado por el
        `conversacion_id` de la URL y el cuerpo no declara ningún destinatario, así que se lo
        define por descarte. Buscar el número del contacto en el cuerpo sería el mismo error otra
        vez: el aviso interno lo nombra adentro del texto y trae su `wa.me` al lado.
        """
        if llamada.metodo != "POST":
            return False
        if llamada.host == HOST_SLACK:
            return True
        if not self._es_mensajeria(llamada):
            return False
        return numero_de_whatsapp(llamada.destinatario) in self.numeros_internos

    @property
    def por_whatsapp(self) -> list[Llamada]:
        """**Todo** lo que salió por WhatsApp: al contacto y al canal interno, junto.

        Es `envios + avisos_por_whatsapp`, y existe porque hay una promesa que se afirma sobre la
        suma y no sobre ninguna de las dos mitades: en `borrador` no sale **nada** por WhatsApp.
        Contando sólo `envios`, el aviso interno por número quedaba afuera de esa cuenta y salía
        en el modo cuya promesa entera es que no sale nada sin confirmar —medido: uno, por el
        endpoint de mensajería, sin ventana, sin baneo y sin `Idempotency-Key`—.

        Del otro lado del cable las dos mitades son la misma cosa: Meta no distingue el número de
        tu compañero del de un cliente. Los dos son salientes del mismo número de negocio, los dos
        caen bajo la ventana de 24 horas y los dos pesan en la calificación.
        """
        return [ll for ll in self.llamadas if self._es_mensajeria(ll)]

    @property
    def envios(self) -> list[Llamada]:
        """Los mensajes que salieron al contacto: los de mensajería que no van al canal."""
        return [
            ll for ll in self.llamadas if self._es_mensajeria(ll) and not self._va_al_canal(ll)
        ]

    @property
    def avisos(self) -> list[Llamada]:
        """Lo que salió al canal interno: el aviso del paso 6, por Slack o por WhatsApp.

        No es «todo lo que no fue al contacto». Con esa definición el upsert del paso 5 entraba
        acá, y como en `borrador` no se escribe la fila, el conteo pasaba a depender del modo:
        justo lo contrario de lo que afirma la prueba que la usa.
        """
        return [ll for ll in self.llamadas if self._va_al_canal(ll)]

    @property
    def avisos_por_slack(self) -> list[Llamada]:
        """Los avisos que salieron por el webhook entrante de Slack.

        `avisos` no distingue por dónde salió, y esa es justo la diferencia que hace falta para
        ver si el build **leyó** `canal_interno` o si le manda todo a Slack pase lo que pase. Lo
        segundo pasa los ocho nodos del aviso sin haber mirado nunca el campo, y del otro lado el
        equipo que no tiene Slack no se entera de una sola escalación.
        """
        return [ll for ll in self.llamadas if ll.metodo == "POST" and ll.host == HOST_SLACK]

    @property
    def avisos_por_whatsapp(self) -> list[Llamada]:
        """Los avisos que salieron por el mismo `/messages` que el mensaje al contacto.

        Son los que van al `canal_interno` cuando ése es un número interno y no un canal de Slack.
        Se reconocen por el destinatario que el cuerpo declara, que es lo único que los separa del
        mensaje al contacto.
        """
        return [ll for ll in self.llamadas if ll.host != HOST_SLACK and self._va_al_canal(ll)]

    @property
    def hosts(self) -> set[str]:
        return {ll.host for ll in self.llamadas}

    def _resolver(self, request):
        import httpx

        cuerpo = request.read() or b""
        self.llamadas.append(
            Llamada(
                metodo=request.method.upper(),
                url=str(request.url),
                ruta=request.url.path,
                host=request.url.host,
                cabeceras={k.lower(): v for k, v in request.headers.items()},
                cuerpo=cuerpo,
            )
        )
        if self._responder is not None:
            estado, datos = self._responder(request)
            return httpx.Response(estado, json=datos, request=request)
        # La forma mínima que devuelven los dos proveedores al aceptar un mensaje.
        return httpx.Response(
            200,
            json={"messages": [{"id": f"wamid.FALSO{len(self.llamadas):04d}"}]},
            request=request,
        )


# ─────────────────────────────────────────────────────────────────────────────
# El modelo inyectado, que también miente a pedido
# ─────────────────────────────────────────────────────────────────────────────


class _Respuesta:
    """Lo que devuelve cualquier método del stub. Se puede llamar y se puede esperar.

    El nombre del método que usa `agente/modelo.py` todavía no está escrito en ningún archivo
    del disco. En vez de adivinarlo y romper el día que se decida, el stub contesta a cualquier
    nombre y anota cuál le pidieron, en `StubModel.metodos_pedidos`.
    """

    def __init__(self, stub: StubModel, nombre: str) -> None:
        self._stub = stub
        self._nombre = nombre

    def __call__(self, *args: Any, **kwargs: Any) -> dict:
        self._stub.llamadas.append({"metodo": self._nombre, "args": args, "kwargs": kwargs})
        return dict(self._stub.salida)

    def __await__(self):
        async def _yo() -> dict:
            return self()

        return _yo().__await__()


@dataclass
class StubModel:
    """El modelo de las pruebas. Devuelve un dict del esquema angosto y nada más.

    Se inyecta, no se intercepta por HTTP. Interceptar el transporte deja adentro el SDK, el
    reintento y el formato de la respuesta, y ninguna de las tres es lo que estas pruebas
    afirman. `pruebas/caso-01.md` excluye a propósito «el texto exacto que redacta el modelo»:
    afirmarlo ata la suite a una versión del modelo y la rompe el día que se sube el pin.

    Tres de las cuatro salidas son malas a propósito. Son las que prueban que las tres
    verificaciones del código muerden.
    """

    salida: dict
    llamadas: list[dict] = field(default_factory=list)

    @property
    def metodos_pedidos(self) -> list[str]:
        return [ll["metodo"] for ll in self.llamadas]

    def __getattr__(self, nombre: str) -> _Respuesta:
        if nombre.startswith("_"):
            raise AttributeError(nombre)
        return _Respuesta(self, nombre)

    def __call__(self, *args: Any, **kwargs: Any) -> dict:
        return _Respuesta(self, "__call__")(*args, **kwargs)

    # ── las cuatro salidas ────────────────────────────────────────────────

    @classmethod
    def canonica(cls) -> StubModel:
        """La del camino feliz de `pruebas/caso-01.md`."""
        return cls(
            {
                "intencion": "precio del curso",
                "score": 62,
                "presupuesto": None,
                "presupuesto_evidencia": None,
                "urgencia": "media",
                "motivo": "Preguntó precio y puso una objeción que está en el playbook.",
                "texto": (
                    "El curso sale 12000 MXN y se puede en tres partes. "
                    "¿Te va alguno de estos horarios?"
                ),
                "objecion_detectada": "Está caro",
                "resumen": (
                    "Preguntó el precio del curso de bienes raíces.\n"
                    "Se le respondió la objeción de precio y se le ofrecieron tres horarios.\n"
                    "Falta que elija uno."
                ),
                "proximo_paso": "Confirmar horario",
                "proximo_paso_fecha": "2026-03-03",
            }
        )

    @classmethod
    def presupuesto_inventado(cls) -> StubModel:
        """Declara 15000 y el mensaje del caso 01 no trae ninguna cifra.

        Prueba la guarda, no el modelo. `anclar_presupuesto()` exige una subcadena literal del
        mensaje con cifras adentro; sin eso el presupuesto se fuerza a nulo y el descarte queda
        escrito en `calificacion.motivo`. **Invariante 5**: lo que no está en el mensaje ni en
        el catálogo, no existe.
        """
        stub = cls.canonica()
        stub.salida["presupuesto"] = 15000
        stub.salida["presupuesto_evidencia"] = None
        return stub

    @classmethod
    def presupuesto_con_evidencia_falsa(cls) -> StubModel:
        """Declara 15000 y cita una frase que no está en el mensaje. Misma guarda, otra puerta."""
        stub = cls.canonica()
        stub.salida["presupuesto"] = 15000
        stub.salida["presupuesto_evidencia"] = "tengo 15000 para invertir"
        return stub

    @classmethod
    def presupuesto_con_evidencia_real(cls, monto: float, evidencia: str) -> StubModel:
        """Declara un monto y cita la subcadena literal del mensaje donde aparece.

        Es la otra mitad de la guarda. Sin esta, un build que devuelva `presupuesto` en nulo
        siempre pasaría la prueba del presupuesto inventado sin verificar nada.
        """
        stub = cls.canonica()
        stub.salida["presupuesto"] = monto
        stub.salida["presupuesto_evidencia"] = evidencia
        return stub

    @classmethod
    def resumen_largo(cls) -> StubModel:
        """Cinco párrafos: la conversación entera pegada. El código lo corta en tres líneas."""
        stub = cls.canonica()
        stub.salida["resumen"] = "\n".join(
            f"Párrafo {n} del resumen, con la conversación entera adentro." for n in range(1, 6)
        )
        return stub

    @classmethod
    def objecion_fabricada(cls) -> StubModel:
        """Una objeción que no está en el playbook del caso.

        La búsqueda es exacta contra `playbook.objeciones`. Si no está, `objecion_en_playbook`
        queda en falso y la objeción se nombra sin responderla: eso es material para el humano,
        no una falla.
        """
        stub = cls.canonica()
        stub.salida["objecion_detectada"] = "Prefiero esperar a que baje el dólar"
        return stub

    @classmethod
    def otro_texto(cls, texto: str) -> StubModel:
        """La canónica con otro texto **saliente**.

        La `Idempotency-Key` se calcula sobre conversación, paso y hash del texto que sale. Para
        ver que cambia hay que cambiar eso y no el mensaje del contacto: con el mismo stub en
        las dos corridas el texto saliente es idéntico, y dos claves distintas sólo saldrían de
        un uuid, que es lo que la otra prueba prohíbe.
        """
        stub = cls.canonica()
        stub.salida["texto"] = texto
        return stub

    @classmethod
    def callado(cls) -> StubModel:
        """Sin texto. Para los caminos donde no corresponde escribirle nada al contacto."""
        stub = cls.canonica()
        stub.salida["texto"] = None
        return stub


# ─────────────────────────────────────────────────────────────────────────────
# El arnés: deps, y los turnos adentro de un solo bucle
# ─────────────────────────────────────────────────────────────────────────────


def armar_deps(transporte: ProveedorFalso, *, historial: dict | None = None) -> Any:
    """Arma el `deps` de `correr_ciclo`. Es el único lugar de la suite que decide su forma.

    Se prueban primero los constructores que el build podría traer. Ninguno existe todavía, así
    que hoy siempre cae en el último caso: un objeto con los cuatro nombres que
    `blueprint/40-pruebas.md` paso 2 le pide a `deps` —base, calendario, CRM y aviso interno—
    más el transporte y el historial sembrado.

    Si el build aterriza con otra forma, se corrige acá. El día que eso pase, las pruebas van a
    fallar con un TypeError que nombra el parámetro, no van a pasar de más.

    **El transporte va abajo del cliente único antes de que se construya ningún proveedor.** Con
    `WHATSAPP_PROVIDER=demo`, `elegir()` deja el transporte de demostración en ese mismo lugar si
    lo encuentra vacío —`blueprint/31-proveedores.md`, paso 2—, y el que llega primero manda. Es
    el orden natural: `deps` se arma antes del ciclo, y el proveedor se elige adentro. Si alguna
    vez se invierte, lo que se ve es un doble que no anota nada, y eso se lee igual que un agente
    que no contesta.
    """
    for modulo, nombre in (("agente.ciclo", "armar_deps"), ("agente.base", "armar_deps")):
        try:
            fabrica = getattr(importlib.import_module(modulo), nombre)
        except (ModuleNotFoundError, AttributeError):
            continue
        return fabrica(transporte=transporte, historial=historial)

    return SimpleNamespace(
        transporte=transporte,
        historial=historial,
        base=None,
        calendario=None,
        crm=None,
        aviso=None,
    )


async def sembrar(deps: Any, historial: dict | None) -> None:
    """Deja el historial del contacto en la base antes del primer turno.

    Los fixtures `caso-02*.historial.json` traen la conversación previa, el estado de la ventana
    y la fila del CRM. Sin eso, el caso del enojo arranca como si fuera el primer mensaje y deja
    de probar lo que existe para probar.

    El historial viaja por dos caminos y el build tiene que consumir uno: queda en
    `deps.historial`, y si `agente/base.py` expone `sembrar_historial(deps, historial)` se la
    llama acá. Si no consume ninguno, el segundo turno no sabe del primero y las pruebas del
    caso 02 se ponen rojas, que es lo correcto.
    """
    if historial is None:
        return
    try:
        base = importlib.import_module("agente.base")
    except ModuleNotFoundError:
        return
    plantar = getattr(base, "sembrar_historial", None)
    if plantar is None:
        return
    resultado = plantar(deps, historial)
    if asyncio.iscoroutine(resultado):
        await resultado


def correr_turnos(
    entradas: list[dict],
    *,
    modelo: StubModel | None = None,
    transporte: ProveedorFalso | None = None,
    historial: dict | None = None,
) -> tuple[list[dict], ProveedorFalso]:
    """Corre uno o más ciclos seguidos y devuelve las salidas y el transporte que las vio.

    Los turnos corren adentro de **un solo** `asyncio.run`, con un solo `deps` y una sola base
    en memoria. Es lo que hace que el segundo turno sepa del primero: la base en memoria de
    SQLite muere cuando se cierra la conexión, y un `asyncio.run` por turno la cierra en el
    medio. Sin eso, la prueba del silencio posterior daría verde con el agente contestando.
    """
    exigir_ciclo()
    ciclo = importlib.import_module("agente.ciclo")
    doble = transporte if transporte is not None else ProveedorFalso()
    stub = modelo if modelo is not None else StubModel.canonica()
    for entrada in entradas:
        doble.apuntar(entrada)

    async def _todos() -> list[dict]:
        deps = armar_deps(doble, historial=historial)
        await sembrar(deps, historial)
        salidas = []
        for entrada in entradas:
            salidas.append(await ciclo.correr_ciclo(entrada, modelo=stub, deps=deps))
        return salidas

    return asyncio.run(_todos()), doble


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades que usan varias pruebas
# ─────────────────────────────────────────────────────────────────────────────


def cargar(nombre: str) -> dict:
    """Un fixture de `pruebas/fixtures/`, por nombre de archivo."""
    return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))


def con(entrada: dict, **cambios: Any) -> dict:
    """Una copia de la entrada con las claves de primer nivel cambiadas."""
    copia = json.loads(json.dumps(entrada))
    copia.update(cambios)
    return copia


def con_mensaje(entrada: dict, **cambios: Any) -> dict:
    """Una copia de la entrada con `mensaje` cambiado."""
    copia = json.loads(json.dumps(entrada))
    copia["mensaje"].update(cambios)
    return copia


def enchufar_transporte(doble: ProveedorFalso, monkeypatch) -> None:
    """Mete el doble abajo del cliente único de `agente/http.py`, para las pruebas del servidor.

    `correr_ciclo` recibe el transporte por `deps` y no necesita esto. El webhook no: levanta el
    cliente por su cuenta, así que hay que enchufarlo desde afuera.

    Levanta `SinAgente` si el build no expone ninguna de las dos formas. Es a propósito: la
    alternativa —parchar un atributo que no existe con `raising=False`— deja la prueba contando
    cero envíos contra cero y en verde, que es una prueba que no puede fallar.
    """
    try:
        http = importlib.import_module("agente.http")
    except ModuleNotFoundError as e:
        raise SinAgente(f"falta el build: {e}") from e

    if hasattr(http, "TRANSPORTE"):
        # `monkeypatch` lo devuelve solo al terminar la prueba, sin que haya que acordarse.
        monkeypatch.setattr(http, "TRANSPORTE", doble)
        return

    raise SinAgente(
        "`agente/http.py` no expone `TRANSPORTE`. Sin un módulo por donde meter el doble no hay "
        "forma de mirar lo que sale del webhook sin abrir un socket, y una prueba que no puede "
        "ver los envíos no prueba nada. El nombre es una convención de esta suite: si el build "
        "usa otro, se cambia acá y en ningún otro lado. Ver blueprint/30-generacion.md, el paso "
        "de http.py, y el invariante 3: un solo cliente HTTP, con timeout explícito."
    )


def paso(salida: dict, n: int) -> dict:
    """El paso `n` de una salida, buscado por su número y nunca por su posición.

    Buscar por posición esconde el defecto: con la lista filtrada o reordenada, `pasos[2]` deja
    de ser el paso 3 y la aserción empieza a medir otra cosa sin ponerse roja.
    """
    encontrados = [p for p in salida.get("pasos", []) if p.get("n") == n]
    assert len(encontrados) == 1, f"`pasos` no trae un solo paso {n}: {salida.get('pasos')}"
    return encontrados[0]


def huella(texto: str) -> str:
    """El hash que una `Idempotency-Key` sacada del contenido tiene que contener."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()
