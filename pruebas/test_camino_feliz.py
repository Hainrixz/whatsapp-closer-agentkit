"""Las cuatro superficies donde el kit promete algo y hasta esta ronda nadie miraba que pasara.

La suite prueba con cuidado que las cosas **no** pasen —no se manda sin confirmar, no se escribe
fuera de la ventana, no se abre `/api/` sin token— y casi nada de que las cosas **sí** pasen. En
una tarde salieron cinco builds huecos con la suite entera en verde y la compuerta en `pass`, y
cuatro son de este archivo:

| Lo que se vació | Quién lo mira ahora |
|---|---|
| `agente/medios.py` reducido a tres `raise` | acá |
| `agente/integraciones/calendario.py` entero, a puros `raise` | acá |
| `cita.evento_id = "evt-inventado"`, sin Google | acá |
| `crm.escrito = True` sin escribir nada | acá |
| `recordatorio_programado = True` siempre | acá |
| una ruta `/tablero` con los mismos datos, sin token | el chequeo 22 `rutas-del-contrato` |

Los cuatro de acá tienen la misma forma: **un booleano o un identificador que el código se escribe
a sí mismo.** Este archivo los ata a algo que el build no controla —los bytes que sirvió el doble,
el identificador que devolvió el calendario, la fila que vio el transporte, el trabajo que quedó
en el scheduler— y por eso ninguno se puede contestar con una constante.

**Cómo se doblan los servicios.** Igual que el transporte de WhatsApp y por el mismo motivo: un
doble que reemplace `agente/medios.py`, `agente/integraciones/calendario.py` o
`agente/integraciones/crm.py` deja afuera justo lo que hay que probar. Así que el doble se pone un
escalón más abajo, en el transporte del cliente único de `agente/http.py`, y arriba corre el
módulo de verdad. `ServiciosFalsos` hereda de `ProveedorFalso` —el mismo doble, la misma
anotación de llamadas— y le agrega el otro lado del cable de Graph, del CDN de Meta, de Zernio, de
Whisper, de OAuth de Google, de Calendar y de PostgREST. Sin red: `conftest.py` la cierra con
llave para todos los nodos.

**Los valores de las variables son falsos y se inyectan por fixture.** Es el mismo camino que
`SLACK_WEBHOOK_DE_PRUEBAS` de `pruebas/proveedor_falso.py`, y por el mismo motivo: sin
`OPENAI_API_KEY` un build fiel al blueprint **no transcribe** —`blueprint/32-multimodal.md` paso
2—, así que una suite que no la ponga mide la detención y nunca el camino feliz. Ninguno de esos
valores existe del otro lado y ninguno sale del proceso. Sigue siendo cierto que nada de esta
suite pide una credencial, que es lo que promete `blueprint/40-pruebas.md`.

**Dos direcciones, siempre.** Cada cosa que se afirma que pasa tiene al lado la corrida donde no
tiene que pasar, y es la que impide aprobar a un build que dice que sí a todo:

| Sí pasa | No pasa |
|---|---|
| el audio se baja y se transcribe | sin `OPENAI_API_KEY` no hay transcripción, y no se inventa |
| la imagen arma su bloque | y no pide ninguna credencial de visión |
| la cita trae el id que devolvió el calendario | sin confirmación, o sin horario elegido, no se llama a Google |
| el `freeBusy` va pegado al insert | con el hueco ocupado no se crea nada y se vuelve a ofrecer |
| el CRM escribe la fila | si el servicio la rechaza, `escrito` queda en falso |
| el recordatorio queda agendado | con Postgres queda declarado detenido, y la cita sale igual |

**La mitad «sí se agenda» es alcanzable desde esta ronda, y antes no lo era.** El paso 4 pide dos
cosas —confirmación explícita y `mensaje.horario_elegido`— y hasta esta ronda el contrato de
entrada no tenía por dónde recibir la segunda: había `opciones_horario`, que dice cuántos horarios
ofrecer, y ningún campo para cuál aceptó el contacto. Con esa mitad inalcanzable, todo lo que
`exigir_cita_coherente()` afirma del lado de «hay cita» no lo afirmaba nadie, y
`agente/integraciones/calendario.py` entero —`crear_evento`, `libre`, `agenda()`,
`programar_recordatorio`— se podía vaciar a puros `raise` con la suite en verde y la compuerta en
`pass`. El campo está en `contratos/entrada.schema.json` y el mecanismo entero en
`blueprint/33-agenda.md` paso 3.

**El token de Google tiene dos caminos y acá corren los dos.** Con una credencial
`authorized_user` —un `refresh_token`, un `POST` y ninguna firma— el paso 4 llega hasta el final
hoy, sin esperar ningún pin. Con una `service_account` el token pide un JWT firmado con RS256 y
ninguna librería que lo haga está en `PINES.md`, así que esa rama queda declarada y detenida: la
prueba de esa forma exige `cita` en nulo, el motivo escrito y **cero llamadas a Google**. Ver
`blueprint/33-agenda.md` pasos 1 y 2.

**Lo que este archivo no afirma:** el texto que redacta el modelo, ni nada que dependa de una
credencial real. Cuántos mensajes salen en un turno es de `pruebas/test_enviar.py` y de
`pruebas/test_caso_02.py`, con una excepción que vive acá porque es parte de la cita: un turno que
agenda manda dos —la respuesta del paso 3 y la confirmación—, y eso se cuenta en la prueba del
`evento_id`.

**El salteo no va a nivel de módulo.** `test_los_fixtures_de_medios_dicen_lo_mismo_que_el_disco`
mira los fixtures y no toca el build, así que corre también con el árbol sin construir: es lo que
avisa cuando el fixture y estas aserciones dejaron de decir lo mismo. Las demás piden el build por
la fixture `correr`, que saltea con el motivo escrito, una prueba a la vez.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib
import inspect
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from pruebas.proveedor_falso import (
    FIXTURES,
    RAIZ,
    Llamada,
    ProveedorFalso,
    StubModel,
    cargar,
    con,
    con_mensaje,
    olvidar_el_build,
    paso,
)

# ─────────────────────────────────────────────────────────────────────────────
# Las cinco superficies, con el nombre que va a salir impreso cuando una se rompa
# ─────────────────────────────────────────────────────────────────────────────

MEDIO = "el medio que sí se baja"
AUDIO = "el audio que sí se transcribe"
IMAGEN = "el bloque de imagen que sí se arma"
CITA = "la cita que sí creó el calendario"
CRM = "la fila que sí se escribió"
RECORDATORIO = "el recordatorio que sí quedó agendado"

# Dónde se arregla cada una. Quien lea el rojo tiene que saber qué archivo abrir sin buscar en
# otro lado, que es la regla de `pruebas/test_enviar.py`.
DONDE = {
    MEDIO: (
        "`agente/medios.py`; la especificación entera está en "
        "blueprint/32-multimodal.md paso 1"
    ),
    AUDIO: "`agente/medios.py`; ver blueprint/32-multimodal.md paso 2",
    IMAGEN: (
        "`agente/medios.py` y el turno de usuario del prompt; "
        "ver blueprint/32-multimodal.md paso 3"
    ),
    CITA: (
        "`agente/integraciones/calendario.py` y `agente/pasos/paso_4_agenda.py`; "
        "ver blueprint/33-agenda.md pasos 3 y 6"
    ),
    CRM: (
        "`agente/integraciones/crm.py` y `agente/pasos/paso_5_crm.py`; "
        "ver blueprint/34-crm.md pasos 3 y 5"
    ),
    RECORDATORIO: (
        "`agente/integraciones/calendario.py`; "
        "ver blueprint/33-agenda.md paso 4 y blueprint/00-contrato.md § 8"
    ),
}


def roto(superficie: str, detalle: str) -> str:
    """El mensaje de un fallo. Nombra la superficie, no «el ciclo»."""
    return f"\nHUECO · {superficie}\n{detalle}\nSe arregla en {DONDE[superficie]}."


# ─────────────────────────────────────────────────────────────────────────────
# Lo que sale del disco
# ─────────────────────────────────────────────────────────────────────────────

FICHA = cargar("medios.ficha.json")
AUDIO_FICHA = FICHA["audio"]
IMAGEN_FICHA = FICHA["imagen"]


def _bytes_del_fixture(nombre: str) -> bytes:
    """Los bytes de un fixture, o vacío si no está.

    Vacío y no una excepción: un fixture faltante tiene que salir como el rojo con motivo de
    `test_los_fixtures_de_medios_dicen_lo_mismo_que_el_disco`, no como un error de colección que
    se lleva puesto el archivo entero y no nombra a nadie.
    """
    ruta = FIXTURES / nombre
    return ruta.read_bytes() if ruta.is_file() else b""


AUDIO_BYTES = _bytes_del_fixture(AUDIO_FICHA["archivo"])
IMAGEN_BYTES = _bytes_del_fixture(IMAGEN_FICHA["archivo"])

# Los cuatro tipos de imagen que acepta la API de Anthropic, y el que este fixture usa a propósito
# no es el que se adivina. Ver `blueprint/32-multimodal.md` paso 3.
TIPOS_DE_IMAGEN = ("image/jpeg", "image/png", "image/gif", "image/webp")

# Un pedazo del texto que redacta `StubModel.canonica()`, para separar el mensaje del paso 3 de la
# confirmación de la cita que escribe el paso 4 cuando los dos salen en el mismo turno. Va sin
# tildes a propósito: el cuerpo viaja como JSON y las tildes salen escapadas —«ó» se escribe
# `ó`—, así que una marca con tilde no se encuentra adentro de `Llamada.texto` aunque haya
# salido perfecta. Es la misma regla de `pruebas/test_enviar.py`.
MARCA_DEL_MODELO = "12000 MXN"


# ─────────────────────────────────────────────────────────────────────────────
# Los valores falsos, todos con TEST adentro y ninguno vivo del otro lado
# ─────────────────────────────────────────────────────────────────────────────

OPENAI_DE_PRUEBAS = "sk-TEST-pruebas-sin-credencial"
WHATSAPP_TOKEN_DE_PRUEBAS = "EAAG-TEST-pruebas-sin-credencial"
WHATSAPP_PHONE_ID_DE_PRUEBAS = "100000000000TEST"
ZERNIO_KEY_DE_PRUEBAS = "sk_TEST_pruebas_sin_credencial"
ZERNIO_CUENTA_DE_PRUEBAS = "acc_TEST_pruebas"
CALENDARIO_DE_PRUEBAS = "agenda-de-pruebas@group.calendar.google.com"
SUPABASE_DE_PRUEBAS = "https://proyecto-de-pruebas.supabase.co"
SUPABASE_KEY_DE_PRUEBAS = "service-role-TEST-pruebas-sin-credencial"

# Las dos credenciales de Google del paso 4. `GOOGLE_SERVICE_ACCOUNT_JSON` nombra el archivo en los
# dos casos y lo que decide cuál es el `type` de adentro, que es lo mismo que mira `google.auth` de
# verdad. Los dos archivos los escribe la prueba en su `tmp_path` y ninguno entra al árbol. Ver
# `blueprint/33-agenda.md` paso 1.

# **La que llega hasta el final hoy.** El token sale de `POST oauth2.googleapis.com/token` con
# `grant_type=refresh_token` y un formulario: sin JWT, sin RS256 y sin ninguna librería que
# `PINES.md` no fije. Es lo que hace que la mitad «sí se agenda» de este archivo sea alcanzable.
#
# Ninguno de los tres valores existe del otro lado, los tres llevan `TEST` adentro y ninguno sale
# del proceso: el doble contesta el token sin abrir un socket.
USUARIO_DE_PRUEBAS = {
    "type": "authorized_user",
    "client_id": "000000000000-TEST.apps.googleusercontent.com",
    "client_secret": "TEST-pruebas-sin-credencial",
    "refresh_token": "TEST-refresh-de-pruebas-sin-credencial",
}

# **La que queda declarada y detenida.** Es un archivo que el paso abre para leer `client_email` y
# firmar el token.
#
# **`private_key` no lleva la armadura PEM, y no es un descuido.** Un bloque `PRIVATE KEY` escrito
# en el árbol lo marca el chequeo 08 `secretos` de la compuerta, y lo marca con razón: no puede
# distinguir el de mentira del que alguien pegó sin querer. Medido: con la armadura puesta acá, el
# auditor cierra en `FAIL · 1 error` con `secretos/credencial`.
#
# La consecuencia va dicha y no escondida: **este archivo no se puede firmar.** Es justamente la
# conducta que se afirma con él —`blueprint/33-agenda.md` paso 2 deja esa rama detenida mientras
# `PINES.md` no fije una librería que firme RS256—. El día que se fije, la clave la va a tener que
# **generar la prueba** en su `tmp_path` con esa misma librería —un par RSA nuevo por corrida, que
# no es una credencial de nadie— y esta constante se reemplaza por eso.
SERVICIO_DE_PRUEBAS = {
    "type": "service_account",
    "project_id": "cerrador-de-pruebas",
    "private_key_id": "TEST",
    "private_key": "sin clave: este fixture no firma nada, ver el comentario de arriba",
    "client_email": "cerrador-de-pruebas@cerrador-de-pruebas.iam.gserviceaccount.com",
    "client_id": "000000000000000000000",
    "token_uri": "https://oauth2.googleapis.com/token",
}

CREDENCIALES = {"usuario": USUARIO_DE_PRUEBAS, "servicio": SERVICIO_DE_PRUEBAS}

TOKEN_DEL_PROVEEDOR = {
    "meta": WHATSAPP_TOKEN_DE_PRUEBAS,
    "zernio": ZERNIO_KEY_DE_PRUEBAS,
}

# Los dos proveedores cuya bajada de medios está escrita. `demo` no entra: `blueprint/32-multimodal
# .md` paso 1 escribe la llamada de Meta y la de Zernio, y ninguna de `demo`, así que sobre `demo`
# no hay forma escrita contra la cual afirmar. Está anotado como hallazgo.
PROVEEDORES_CON_BAJADA = ("meta", "zernio")


# ─────────────────────────────────────────────────────────────────────────────
# Los hosts del otro lado del cable
# ─────────────────────────────────────────────────────────────────────────────

HOST_GRAPH = "graph.facebook.com"
HOST_CDN = "lookaside.fbsbx.com"          # el CDN donde Meta deja el archivo, no la Graph
HOST_ZERNIO = "zernio.com"
HOST_OPENAI = "api.openai.com"
HOST_OAUTH = "oauth2.googleapis.com"
HOST_CALENDARIO = "www.googleapis.com"
HOST_SUPABASE = urlsplit(SUPABASE_DE_PRUEBAS).hostname


class ServiciosFalsos(ProveedorFalso):
    """El otro lado del cable de todo lo que el ciclo llama y no es un mensaje.

    Hereda de `ProveedorFalso` para no tener un segundo doble: la anotación de llamadas, la
    separación entre `envios` y `avisos` y la respuesta por defecto de mensajería quedan como
    están, y acá abajo sólo se contesta lo que ese doble no conoce.

    Cada cosa que el build no puede adivinar viaja con un valor de esta corrida:

    - **el identificador del evento** es el que devuelve el calendario, y cambia por corrida. Una
      constante escrita en el build no lo puede acertar;
    - **la URL del CDN de Meta** la da la primera llamada y también cambia por corrida. Un build
      que se la invente no consigue los bytes;
    - **los bytes del medio** salen de `pruebas/fixtures/` y se comparan contra lo que quedó en
      disco y contra lo que viajó a la transcripción.
    """

    def __init__(
        self,
        *,
        evento_id: str = "evt-de-esta-corrida",
        respuesta_del_crm: tuple[int, Any] = (201, []),
        transcripcion: str | None = None,
        ocupado: bool = False,
    ) -> None:
        super().__init__()
        self.evento_id = evento_id
        self.respuesta_del_crm = respuesta_del_crm
        # Si el hueco que se está por reservar aparece ocupado en `freeBusy`. Calendar deja crear
        # eventos superpuestos —no hay reserva atómica—, así que ésta es la única forma de
        # distinguir un build que comprueba de uno que ofrece con fe.
        self.ocupado = ocupado
        self.transcripcion = (
            transcripcion if transcripcion is not None else AUDIO_FICHA["transcripcion"]
        )
        # Lo que el doble sirvió, por si alguien lo quiere contar. Se anota acá y no se deduce de
        # `llamadas`: lo que importa no es a dónde fue la petición, es qué se le contestó.
        self.descriptores: list[Llamada] = []
        self.bajadas: list[Llamada] = []
        self.transcripciones: list[Llamada] = []
        self.tokens: list[Llamada] = []
        self.freebusy: list[Llamada] = []
        self.eventos: list[Llamada] = []
        self.filas: list[Llamada] = []
        self.medios = {
            AUDIO_FICHA["media_id"]: (AUDIO_BYTES, AUDIO_FICHA["mime_type"]),
            IMAGEN_FICHA["media_id"]: (IMAGEN_BYTES, IMAGEN_FICHA["mime_type"]),
        }
        # La URL que la primera llamada de Meta devuelve. Lleva el id de la corrida adentro, así
        # que un build que arme la URL del CDN por su cuenta se queda sin bytes.
        self.cdn = {
            media_id: (
                f"https://{HOST_CDN}/whatsapp_business/attachments/"
                f"?mid={media_id}&ext={evento_id}&hash={evento_id}"
            )
            for media_id in self.medios
        }

    # ── el otro lado ──────────────────────────────────────────────────────

    def cuando(self, llamada: Llamada) -> int:
        """En qué lugar de la corrida salió esa llamada, contando desde cero.

        Se compara por identidad contra `llamadas`, que es la lista ordenada de todo lo que salió:
        los mismos objetos están en `freebusy` y en `eventos`, así que dos llamadas con el mismo
        cuerpo no se confunden. Existe para afirmar un orden —`freeBusy` **antes** del `POST` a
        `events`— que no se ve en la salida de un turno que salió bien.
        """
        for i, x in enumerate(self.llamadas):
            if x is llamada:
                return i
        return -1

    def _medio_de(self, llamada: Llamada) -> str | None:
        """El `media_id` que esa petición está pidiendo, o None si no pide ninguno."""
        for media_id in self.medios:
            if media_id in llamada.url:
                return media_id
        return None

    def _servir(self, llamada: Llamada):
        import httpx

        host, ruta = llamada.host or "", llamada.ruta or ""

        if host == HOST_OPENAI and "/audio/transcriptions" in ruta:
            self.transcripciones.append(llamada)
            return httpx.Response(200, json={"text": self.transcripcion})

        if host == HOST_OAUTH:
            self.tokens.append(llamada)
            return httpx.Response(
                200,
                json={
                    "access_token": f"ya29.TEST.{self.evento_id}",
                    "expires_in": 3599,
                    "token_type": "Bearer",
                },
            )

        if host == HOST_CALENDARIO and "freeBusy" in ruta:
            self.freebusy.append(llamada)
            cuerpo = llamada.datos if isinstance(llamada.datos, dict) else {}
            # El bloque ocupado se devuelve sobre la misma ventana que se preguntó, así que
            # solapa siempre, venga como venga armada la consulta.
            ocupado = (
                [
                    {
                        "start": cuerpo.get("timeMin") or "1970-01-01T00:00:00Z",
                        "end": cuerpo.get("timeMax") or "2999-01-01T00:00:00Z",
                    }
                ]
                if self.ocupado
                else []
            )
            return httpx.Response(
                200, json={"calendars": {CALENDARIO_DE_PRUEBAS: {"busy": ocupado}}}
            )

        if host == HOST_CALENDARIO and ruta.endswith("/events"):
            self.eventos.append(llamada)
            cuerpo = llamada.datos if isinstance(llamada.datos, dict) else {}
            return httpx.Response(
                200,
                json={
                    "kind": "calendar#event",
                    "id": self.evento_id,
                    "status": "confirmed",
                    "htmlLink": f"https://www.google.com/calendar/event?eid={self.evento_id}",
                    "summary": cuerpo.get("summary"),
                    "start": cuerpo.get("start"),
                    "end": cuerpo.get("end"),
                },
            )

        if host == HOST_SUPABASE:
            self.filas.append(llamada)
            estado, datos = self.respuesta_del_crm
            return httpx.Response(estado, json=datos)

        media_id = self._medio_de(llamada)
        if media_id is not None:
            datos, tipo = self.medios[media_id]
            # Meta son dos llamadas: la Graph devuelve un JSON con la URL y el `mime_type`, y los
            # bytes viven en el CDN. Zernio es una sola y devuelve los bytes.
            if host == HOST_GRAPH and llamada.url.split("?")[0].endswith(media_id):
                self.descriptores.append(llamada)
                return httpx.Response(
                    200,
                    json={
                        "id": media_id,
                        "url": self.cdn[media_id],
                        "mime_type": tipo,
                        "sha256": hashlib.sha256(datos).hexdigest(),
                        "file_size": len(datos),
                        "messaging_product": "whatsapp",
                    },
                )
            if host == HOST_CDN or "/media/" in ruta:
                self.bajadas.append(llamada)
                return httpx.Response(200, content=datos, headers={"Content-Type": tipo})

        return None

    def _resolver(self, request):
        # `super()` anota la llamada y arma la respuesta de mensajería. Lo que sigue sólo la
        # reemplaza cuando este doble sabe contestar algo mejor.
        respuesta = super()._resolver(request)
        propia = self._servir(self.llamadas[-1])
        if propia is None:
            return respuesta
        propia.request = request
        return propia


# ─────────────────────────────────────────────────────────────────────────────
# El entorno: variables falsas, y el build releído después de ponerlas
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    """Pone variables de entorno falsas y deja el build listo para releerlas.

    `olvidar_el_build()` no es ceremonia: los ajustes se leen **una vez, al importar**, así que
    una variable puesta después de que otro archivo de la suite importó `agente` no la ve nadie.
    Es el mismo cuidado que toma `slack_de_pruebas` en `pruebas/proveedor_falso.py`.

    Un valor en `None` saca la variable. Es como se afirma la dirección «sin la credencial».
    """

    def _poner(**variables: str | None) -> Path:
        for nombre, valor in variables.items():
            if valor is None:
                monkeypatch.delenv(nombre, raising=False)
            else:
                monkeypatch.setenv(nombre, str(valor))
        olvidar_el_build()
        return tmp_path

    yield _poner
    # Antes de que `monkeypatch` devuelva el entorno, para que el próximo import lo relea limpio.
    olvidar_el_build()


def credencial_de_google(tmp_path: Path, forma: str = "usuario") -> str:
    """Escribe la credencial de Google en el directorio de la prueba y devuelve la ruta.

    Absoluta, que es lo que pide `blueprint/33-agenda.md` paso 1: con una ruta relativa el
    servicio arranca en otro directorio y lee `FileNotFoundError`.

    `forma` es `usuario` —la que anda hoy— o `servicio` —la que queda detenida—. El nombre del
    archivo lleva la forma adentro para que un rojo diga cuál se estaba usando sin abrir nada.
    """
    import json

    ruta = tmp_path / f"credencial-de-google-{forma}.json"
    ruta.write_text(json.dumps(CREDENCIALES[forma], indent=2), encoding="utf-8")
    return str(ruta)


def entorno_de_medios(entorno, proveedor: str, *, openai: str | None = OPENAI_DE_PRUEBAS) -> None:
    """El entorno de la bajada: el proveedor elegido y su token, más la clave de la transcripción.

    El token no es un extra: la bajada del medio va **con** `Authorization` —no es un enlace
    público, y sin la cabecera devuelve 401—, así que sin él no hay camino feliz que probar. Ver
    `blueprint/32-multimodal.md` paso 1.
    """
    entorno(
        WHATSAPP_PROVIDER=proveedor,
        WHATSAPP_TOKEN=WHATSAPP_TOKEN_DE_PRUEBAS,
        WHATSAPP_PHONE_NUMBER_ID=WHATSAPP_PHONE_ID_DE_PRUEBAS,
        ZERNIO_API_KEY=ZERNIO_KEY_DE_PRUEBAS,
        ZERNIO_ACCOUNT_ID=ZERNIO_CUENTA_DE_PRUEBAS,
        OPENAI_API_KEY=openai,
    )


def entorno_de_agenda(entorno, tmp_path: Path, *, base: str, credencial: str = "usuario") -> None:
    """El entorno del paso 4: el calendario, la credencial de Google y la base del jobstore."""
    entorno(
        GOOGLE_CALENDAR_ID=CALENDARIO_DE_PRUEBAS,
        GOOGLE_SERVICE_ACCOUNT_JSON=credencial_de_google(tmp_path, credencial),
        DATABASE_URL=base,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Las entradas, armadas del fixture y nunca de un literal pegado
# ─────────────────────────────────────────────────────────────────────────────


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def instante(cadena: str) -> datetime:
    """Un `date-time` del contrato como momento, para comparar sin pelear con el formato.

    `2026-03-02T11:00:00-06:00` y `2026-03-02T17:00:00Z` son el mismo instante. Comparar las
    cadenas convertiría un cambio de formato en un fallo, y eso no es lo que se afirma.
    """
    return datetime.fromisoformat(cadena).astimezone(timezone.utc)


def proximos_horarios(
    cuantos: int = 4, *, dentro_de_dias: int = 30, dentro_de_horas: int = 0
) -> list[dict]:
    """Huecos libres en el futuro, contados desde el reloj de la máquina y no desde el fixture.

    Es la excepción a la regla de `pruebas/test_enviar.py` —«los instantes salen de los
    fixtures»— y tiene su motivo: el recordatorio se programa 24 horas **antes** de la cita, y
    APScheduler descarta un trabajo `date` cuya hora ya pasó, con un `misfire_grace_time` de un
    segundo. Con la disponibilidad de marzo de 2026 que traen los fixtures, la mitad «sí quedó
    agendado» de este archivo dejaría de medir nada el día siguiente a esa fecha, sin ponerse
    roja. Lo que sí sale del fixture es todo lo demás.

    `dentro_de_horas` existe para una sola cosa, y es la ventana de 24 horas: una cita dentro de
    treinta horas tiene el recordatorio dentro de seis, o sea **adentro** de la ventana que abrió
    el mensaje de este turno, y una dentro de treinta días lo tiene claramente afuera. Son los dos
    lados de `test_recordatorio_el_trabajo_que_dispara_manda_por_enviar`.
    """
    base = (ahora() + timedelta(days=dentro_de_dias, hours=dentro_de_horas)).replace(
        minute=0, second=0, microsecond=0
    )
    return [
        {"inicio": (base + timedelta(hours=n)).isoformat(), "duracion_min": 30}
        for n in range(cuantos)
    ]


def entrada_con_medio(cual: str) -> dict:
    """La entrada del caso 01 con un audio o una imagen adentro, y el contacto de la ficha.

    El contacto es propio para que la carpeta `medios/<contacto_id>/` que este archivo mira, y
    borra, no sea la de ningún otro caso.
    """
    ficha = AUDIO_FICHA if cual == "audio" else IMAGEN_FICHA
    return con_mensaje(
        cargar("caso-01.entrada.json"),
        tipo=cual if cual == "audio" else "imagen",
        texto=None,
        media_id=ficha["media_id"],
        media_url=None,
        media_local=None,
        contacto_id=FICHA["contacto_id"],
        de=FICHA["numero"],
        recibido_en=ahora().isoformat(),
    )


# Cuál de los huecos elige el contacto. **No es el primero a propósito**: un build que agende
# `disponibilidad[0]` porque hay confirmación acierta con el índice 0 y se pone rojo con éste. Es
# la misma idea que los dos identificadores de evento de la prueba del `evento_id`.
HUECO_ELEGIDO = 2


def entrada_para_agendar(
    *, elegido: int | None = HUECO_ELEGIDO, dentro_de_dias: int = 30, dentro_de_horas: int = 0
) -> dict:
    """La entrada del caso 01 autorizada a agendar, con horarios que todavía no pasaron.

    Las dos cosas que el paso 4 pide, juntas y explícitas: `confirmado` en verdadero y
    `mensaje.horario_elegido` con uno de los huecos de `disponibilidad`. Con `elegido=None` se
    arma la entrada sin horario, que es la otra dirección: confirmada y sin nada que agendar.

    `recibido_en` se pone en el momento de la corrida y no se deja el del fixture: la ventana de
    24 horas se cuenta desde el último entrante, y con un mensaje de marzo de 2026 la
    confirmación del paso 4 no puede salir por más que el build esté bien. Lo que se está
    midiendo acá es el calendario, no la ventana; la ventana la mide
    `pruebas/test_enviar.py`.

    `dentro_de_dias` y `dentro_de_horas` viajan tal cual a `proximos_horarios()`: los usa el nodo
    del recordatorio para poner la cita de los dos lados de la ventana de 24 horas.
    """
    horarios = proximos_horarios(dentro_de_dias=dentro_de_dias, dentro_de_horas=dentro_de_horas)
    entrada = con_mensaje(
        cargar("caso-01.entrada.json"),
        recibido_en=ahora().isoformat(),
        horario_elegido=None if elegido is None else horarios[elegido]["inicio"],
    )
    return con(
        entrada,
        modo="automatico",
        confirmado=True,
        disponibilidad=horarios,
    )


def elegido_de(entrada: dict) -> str:
    """El horario que esa entrada dice que el contacto aceptó."""
    return entrada["mensaje"]["horario_elegido"]


# ─────────────────────────────────────────────────────────────────────────────
# Lo que se mira del disco y del modelo
# ─────────────────────────────────────────────────────────────────────────────


def carpeta_de_medios(contacto_id: str) -> Path:
    return RAIZ / "medios" / contacto_id


@pytest.fixture
def medios_limpios():
    """Borra la carpeta del contacto de estas pruebas, antes y después.

    Sólo la de ese contacto: `medios/` es de quien corre el kit y ahí caen notas de voz y fotos de
    sus clientes. Antes, además, porque un archivo de una corrida anterior haría pasar la
    aserción del disco sin que se haya bajado nada.
    """
    carpeta = carpeta_de_medios(FICHA["contacto_id"])
    shutil.rmtree(carpeta, ignore_errors=True)
    yield carpeta
    shutil.rmtree(carpeta, ignore_errors=True)


def archivo_bajado(contacto_id: str, media_id: str) -> Path | None:
    """El archivo que dejó la bajada, o None si no quedó ninguno.

    Se acepta el nombre pelado y el nombre con extensión: `blueprint/32-multimodal.md` paso 1
    escribe `medios/<contacto_id>/<media_id>` y un build que le agregue la extensión del
    `mime_type` sigue cumpliendo lo que la regla persigue, que es que el archivo quede indexado
    por el medio y no por el número.
    """
    carpetas = [carpeta_de_medios(contacto_id), Path.cwd() / "medios" / contacto_id]
    for carpeta in carpetas:
        if not carpeta.is_dir():
            continue
        for ruta in sorted(carpeta.iterdir()):
            if ruta.is_file() and (ruta.name == media_id or ruta.name.startswith(media_id + ".")):
                return ruta
    return None


def _recorrer(nodo: Any, camino: tuple[str, ...] = ()):
    """Cada nodo de una estructura anidada, con el camino de claves que lleva hasta él."""
    yield camino, nodo
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            yield from _recorrer(valor, camino + (str(clave),))
    elif isinstance(nodo, (list, tuple)):
        for i, valor in enumerate(nodo):
            yield from _recorrer(valor, camino + (str(i),))


def lo_que_vio_el_modelo(stub: StubModel):
    """Todo lo que se le pasó al modelo, nodo por nodo, con su camino.

    El nombre del método que usa `agente/modelo.py` no está escrito en ningún archivo del disco y
    `StubModel` contesta a cualquiera, así que acá tampoco se adivina: se mira lo que quedó
    anotado en `llamadas`, sea cual sea el nombre y la forma del prompt.
    """
    for llamada in stub.llamadas:
        yield from _recorrer({"args": llamada["args"], "kwargs": llamada["kwargs"]})


def texto_que_vio_el_modelo(stub: StubModel) -> str:
    return "\n".join(str(nodo) for _, nodo in lo_que_vio_el_modelo(stub) if isinstance(nodo, str))


def bloques_de_imagen(stub: StubModel) -> list[tuple[tuple[str, ...], dict]]:
    """Los bloques de imagen que llegaron al modelo, con el camino por el que llegaron."""
    return [
        (camino, nodo)
        for camino, nodo in lo_que_vio_el_modelo(stub)
        if isinstance(nodo, dict) and nodo.get("type") == "image"
    ]


# Las claves que nombran el prefijo del sistema. Una imagen ahí adentro pone la tasa de acierto
# del caché de prompt en cero, sin ningún error visible. Ver `blueprint/32-multimodal.md` paso 3.
CLAVES_DE_PREFIJO = ("system", "sistema", "prefijo", "system_prompt")


def autorizacion(llamada: Llamada) -> str:
    return llamada.cabeceras.get("authorization", "")


# ─────────────────────────────────────────────────────────────────────────────
# La guarda de este archivo: los fixtures y el disco tienen que seguir diciendo lo mismo
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("cual", ["audio", "imagen"])
def test_los_fixtures_de_medios_dicen_lo_mismo_que_el_disco(cual: str) -> None:
    """Corre sin build, y es lo que impide que este archivo se lea verde sin medir nada.

    Todo lo que las pruebas de abajo comparan —los bytes que se sirven, el `mime_type` que decide
    el bloque de imagen, la marca que tiene que aparecer en la transcripción— sale de
    `medios.ficha.json`. Si la ficha y los bytes dejan de coincidir, las de abajo se ponen rojas
    por un motivo que no es el que dicen probar. Acá se ponen rojas primero, barato y con el
    motivo escrito.
    """
    ficha = AUDIO_FICHA if cual == "audio" else IMAGEN_FICHA
    archivo = FIXTURES / ficha["archivo"]

    assert archivo.is_file(), (
        f"falta pruebas/fixtures/{ficha['archivo']}, que es de donde salen los bytes que sirve el "
        f"doble. Sin él, la bajada no tiene qué bajar y la comparación contra el disco no tiene "
        f"contra qué comparar."
    )
    datos = archivo.read_bytes()
    assert hashlib.sha256(datos).hexdigest() == ficha["sha256"], (
        f"{ficha['archivo']} cambió y `medios.ficha.json` sigue con el sha256 viejo. Los dos se "
        f"mueven juntos: la ficha es lo que la prueba lee y el archivo es lo que el doble sirve."
    )
    assert len(datos) == ficha["bytes"], (
        f"{ficha['archivo']} tiene {len(datos)} bytes y la ficha dice {ficha['bytes']}."
    )
    assert ficha["media_id"] and ficha["mime_type"], (
        f"la ficha de {cual} perdió `media_id` o `mime_type`. El primero es el nombre del archivo "
        f"que la bajada deja en disco; el segundo es lo único de donde puede salir el "
        f"`media_type` del bloque de imagen."
    )

    if cual == "audio":
        assert ficha["marca"] in ficha["transcripcion"], (
            f"la transcripción de la ficha dejó de traer «{ficha['marca']}». Esa marca es lo "
            f"único que la prueba busca adentro del prompt para saber que la transcripción llegó "
            f"al modelo: sin ella no hay forma de distinguir el texto transcrito del texto que el "
            f"build pudo haber escrito solo."
        )
        assert datos[:4] == b"OggS", (
            f"{ficha['archivo']} dejó de ser un Ogg: empieza con {datos[:4]!r}. WhatsApp manda "
            f"las notas de voz en OGG/Opus y Whisper las acepta tal como llegan, sin conversión "
            f"previa; ver S07 en SUPUESTOS.md."
        )
        return

    assert ficha["mime_type"] in TIPOS_DE_IMAGEN, (
        f"`{ficha['mime_type']}` no es uno de los cuatro tipos que acepta la API: "
        f"{', '.join(TIPOS_DE_IMAGEN)}."
    )
    assert ficha["mime_type"] != "image/jpeg", (
        "el fixture de imagen volvió a ser jpeg. Es webp a propósito: jpeg es lo que un build "
        "adivina —WhatsApp manda fotos en jpeg— y con jpeg en el fixture la aserción del "
        "`media_type` se pone verde sin que nadie haya leído el `mime_type` de la bajada."
    )
    assert datos[:4] == b"RIFF" and datos[8:12] == b"WEBP", (
        f"{ficha['archivo']} dejó de ser un WebP: {datos[:12]!r}. El `media_type` tiene que "
        f"cuadrar con los bytes o la API contesta 400 `Could not process image`."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1 · El medio que sí se baja, y el audio que sí se transcribe
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("proveedor", PROVEEDORES_CON_BAJADA)
def test_medio_el_audio_se_baja_una_vez_y_se_transcribe(
    correr, entorno, medios_limpios, proveedor: str
) -> None:
    """La dirección que nadie miraba: el audio que **sí** llega a texto.

    Las tres pruebas del audio que ya existen —`test_caso_01.py`, las tres formas de no conseguir
    los bytes— son las tres formas de **no** conseguirlos. Con esas tres solas,
    `agente/medios.py` puede ser veinte líneas donde `bajar()` y `transcribir()` levantan
    `SinMedio` y la suite entera sale verde con la compuerta en `pass`: las tres siguen pasando,
    porque el build que nunca consigue los bytes es exactamente el que ellas describen.

    Lo que se afirma acá no lo puede escribir el build solo: los bytes salen de
    `pruebas/fixtures/`, y la URL del CDN de Meta la elige el doble en cada corrida.
    """
    entorno_de_medios(entorno, proveedor)
    ficha = AUDIO_FICHA
    doble = ServiciosFalsos()
    stub = StubModel.canonica()

    salidas, _ = correr([entrada_con_medio("audio")], modelo=stub, transporte=doble)
    salida = salidas[0]

    primero = paso(salida, 1)
    assert primero["estado"] == "hecho", roto(
        MEDIO,
        f"llegó un audio con `media_id` y el paso 1 quedó en «{primero['estado']}»: "
        f"«{primero.get('motivo')}». El proveedor contestó con los bytes; lo que no hubo fue "
        f"bajada. Un build donde `bajar()` sólo levanta pasa las tres pruebas del audio de "
        f"test_caso_01.py, porque ésas describen justamente ese build.",
    )
    assert salida["estado"] != "detenido", roto(
        MEDIO,
        f"el ciclo se detuvo con un audio que sí se podía bajar: «{primero.get('motivo')}». "
        f"`detenido` es para las tres formas de no conseguir los bytes, y ésta no es ninguna.",
    )

    # ── los bytes ────────────────────────────────────────────────────────
    assert doble.bajadas, roto(
        MEDIO,
        f"el transporte no vio una sola bajada. Las llamadas que salieron fueron "
        f"{[(ll.metodo, ll.url) for ll in doble.llamadas]}. El medio se baja al recibirlo, como "
        f"primera acción del paso 1 y después del 200: Meta suelta el archivo a los pocos días y "
        f"desde ahí esa llamada devuelve 400 para siempre.",
    )
    assert len(doble.bajadas) == 1, roto(
        MEDIO,
        f"los bytes del medio se bajaron {len(doble.bajadas)} veces en un solo ciclo: "
        f"{[ll.url for ll in doble.bajadas]}. Se baja una vez, la ruta queda en "
        f"`mensaje.media_local` y el resto del ciclo lee esa ruta sin volver a llamar al "
        f"proveedor.",
    )

    quedo = archivo_bajado(FICHA["contacto_id"], ficha["media_id"])
    assert quedo is not None, roto(
        MEDIO,
        f"no quedó ningún archivo en medios/{FICHA['contacto_id']}/{ficha['media_id']}. El "
        f"archivo queda ahí y la ruta en `mensaje.media_local`, que es propiedad declarada de "
        f"`mensaje` en contratos/entrada.schema.json y hoy no la afirma ningún otro nodo. "
        f"Acordate de `/medios/` en .gitignore, anclado con `/`.",
    )
    assert quedo.read_bytes() == AUDIO_BYTES, roto(
        MEDIO,
        f"el archivo que quedó en {quedo} no son los bytes que sirvió el proveedor: bajaron "
        f"{len(AUDIO_BYTES)} bytes y quedaron {len(quedo.read_bytes())}. Lo que se guarda es la "
        f"respuesta de la bajada, no el `media_id` ni la URL.",
    )

    # ── quién autorizó la bajada ─────────────────────────────────────────
    esperado = TOKEN_DEL_PROVEEDOR[proveedor]
    autorizadas = doble.bajadas + doble.descriptores
    sin_cabecera = [ll for ll in autorizadas if esperado not in autorizacion(ll)]
    assert sin_cabecera == [], roto(
        MEDIO,
        f"{len(sin_cabecera)} llamada(s) de la bajada salieron sin el `Authorization` del "
        f"proveedor: {[(ll.url, autorizacion(ll)) for ll in sin_cabecera]}. **No es un enlace "
        f"público**: sin la cabecera devuelve 401, y pasarle ese enlace pelado a una API de "
        f"visión devuelve 401 del otro lado.",
    )

    if proveedor == "meta":
        assert len(doble.descriptores) == 1, roto(
            MEDIO,
            f"en Meta son dos llamadas y el doble vio {len(doble.descriptores)} a la Graph: "
            f"`GET {{BASE_META}}/{{media_id}}` trae un JSON con `url` y `mime_type`, y esa `url` "
            f"—que vive en el CDN, no en la Graph— se baja también con el `Authorization`.",
        )
        assert doble.bajadas[0].url == doble.cdn[ficha["media_id"]], roto(
            MEDIO,
            f"los bytes se pidieron a {doble.bajadas[0].url} y la primera llamada había "
            f"devuelto {doble.cdn[ficha['media_id']]}. Esa URL la da el proveedor en cada "
            f"bajada y caduca en minutos: armarla por tu cuenta anda hoy y devuelve 404 mañana.",
        )
    else:
        cuenta = parse_qs(urlsplit(doble.bajadas[0].url).query).get("accountId", [])
        assert cuenta == [ZERNIO_CUENTA_DE_PRUEBAS], roto(
            MEDIO,
            f"la bajada de Zernio salió a {doble.bajadas[0].url}, sin `accountId`. "
            f"`ZERNIO_ACCOUNT_ID` es obligatoria y no se deduce de la clave: sin ella la URL "
            f"queda a medias y la bajada vuelve 401.",
        )

    # ── la transcripción ─────────────────────────────────────────────────
    assert len(doble.transcripciones) == 1, roto(
        AUDIO,
        f"el transporte vio {len(doble.transcripciones)} llamadas a la transcripción y tenía que "
        f"ver una: {[ll.url for ll in doble.llamadas if ll.host == HOST_OPENAI]}. El audio se "
        f"transcribe con la API de Whisper, con el cliente único y con `timeout=`.",
    )
    peticion = doble.transcripciones[0]
    assert AUDIO_BYTES in peticion.cuerpo, roto(
        AUDIO,
        f"la transcripción salió sin los bytes del audio adentro: el cuerpo tiene "
        f"{len(peticion.cuerpo)} bytes y el archivo {len(AUDIO_BYTES)}. Le pasaste el `media_id` "
        f"o la URL en vez de los bytes, que es el mismo defecto que deja `media_local` en nulo.",
    )
    assert FICHA["transcripcion_modelo"].encode() in peticion.cuerpo, roto(
        AUDIO,
        f"la petición no nombra el modelo `{FICHA['transcripcion_modelo']}`. El id del "
        f"transcriptor es un literal de `agente/medios.py`: PINES.md fija el modelo que redacta, "
        f"no éste.",
    )
    assert b"temperature" not in peticion.cuerpo, roto(
        AUDIO,
        "la petición de transcripción lleva `temperature`. La API la acepta y el chequeo "
        "`modelo/parametro_400` la marca igual: mira los argumentos con nombre de todo `agente/`, "
        "no sólo la llamada a Anthropic.",
    )

    visto = texto_que_vio_el_modelo(stub)
    assert ficha["marca"] in visto, roto(
        AUDIO,
        f"la transcripción no llegó al modelo: «{ficha['marca']}» no aparece en nada de lo que se "
        f"le pasó. El audio se bajó y se transcribió, y el texto se perdió entre el paso 1 y el "
        f"prompt: el agente está contestando sin saber qué decía la nota de voz. La "
        f"transcripción va a `mensaje.texto` y de ahí al turno de usuario.",
    )


def test_medio_sin_la_clave_de_whisper_no_se_inventa_una_transcripcion(
    correr, entorno, medios_limpios
) -> None:
    """La otra dirección, y la que separa «no pude» de «me lo imaginé».

    Sin `OPENAI_API_KEY` nadie adivina qué decía el audio. Lo que muerde acá es el build que
    devuelve una transcripción igual —del nombre del archivo, de un texto fijo, de lo que sea—:
    eso es una invención, y una invención con la que el agente contesta se lee como si hubiera
    entendido.
    """
    entorno_de_medios(entorno, "meta", openai=None)
    doble = ServiciosFalsos()
    stub = StubModel.canonica()

    salidas, _ = correr([entrada_con_medio("audio")], modelo=stub, transporte=doble)
    salida = salidas[0]

    primero = paso(salida, 1)
    assert primero["estado"] == "fallado", roto(
        AUDIO,
        f"no hay `OPENAI_API_KEY` y el paso 1 quedó en «{primero['estado']}». Sin la clave el "
        f"ciclo se detiene con el motivo escrito: «Llegó un audio de … y no lo puedo transcribir: "
        f"falta OPENAI_API_KEY».",
    )
    motivo = (primero.get("motivo") or "")
    assert "OPENAI_API_KEY" in motivo, roto(
        AUDIO,
        f"el paso 1 falló y el motivo no nombra la variable que falta: «{motivo}». Ese renglón lo "
        f"lee quien atiende el negocio y tiene que poder arreglarlo: se pone la clave en .env y "
        f"se reprocesa, o se escucha el audio y se contesta desde /bandeja.",
    )
    assert salida["estado"] == "detenido", roto(
        AUDIO,
        f"el estado quedó en «{salida['estado']}». Con el audio sin transcribir el agente no "
        f"atendió el mensaje: no lo pudo leer.",
    )
    assert doble.transcripciones == [], roto(
        AUDIO,
        f"salió una llamada a la transcripción sin clave: "
        f"{[ll.url for ll in doble.transcripciones]}.",
    )
    assert doble.envios == [], roto(
        AUDIO, f"se detuvo y le escribió igual: {[(e.ruta, e.texto) for e in doble.envios]}."
    )
    assert AUDIO_FICHA["marca"] not in texto_que_vio_el_modelo(stub), roto(
        AUDIO,
        f"sin la clave puesta, «{AUDIO_FICHA['marca']}» llegó igual al modelo. Eso es una "
        f"transcripción inventada, y es fallo de la aserción 1 de pruebas/caso-01.md.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2 · El bloque de imagen que sí se arma
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("proveedor", PROVEEDORES_CON_BAJADA)
def test_imagen_el_bloque_llega_al_modelo_y_no_pide_ninguna_credencial_de_vision(
    correr, entorno, medios_limpios, proveedor: str
) -> None:
    """`bloque_de_imagen()` no se llamaba en ningún nodo de la suite.

    Se corre **sin** `OPENAI_API_KEY` a propósito, y ésa es la segunda dirección: la imagen la lee
    el modelo de Anthropic que ya está configurado, así que no hay ninguna credencial extra que
    conseguir. Un build que mande la imagen a transcribir, o que se detenga por falta de una clave
    de visión, se pone rojo acá.

    Las tres reglas del bloque se afirman las tres, porque las tres se rompen por separado y
    ninguna se ve desde afuera: los bytes en base64 y nunca la URL del proveedor, el `media_type`
    del `mime_type` de la bajada y nunca de la extensión, y el bloque en el turno de usuario y
    nunca en el prefijo del sistema.
    """
    entorno_de_medios(entorno, proveedor, openai=None)
    ficha = IMAGEN_FICHA
    doble = ServiciosFalsos()
    stub = StubModel.canonica()

    salidas, _ = correr([entrada_con_medio("imagen")], modelo=stub, transporte=doble)
    salida = salidas[0]

    primero = paso(salida, 1)
    assert primero["estado"] == "hecho", roto(
        IMAGEN,
        f"llegó una imagen con `media_id` y el paso 1 quedó en «{primero['estado']}»: "
        f"«{primero.get('motivo')}». Las imágenes no necesitan ninguna credencial nueva; si el "
        f"motivo nombra OPENAI_API_KEY, el build está mandando la foto a transcribir.",
    )
    assert doble.transcripciones == [], roto(
        IMAGEN,
        f"la imagen salió hacia la transcripción: {[ll.url for ll in doble.transcripciones]}. La "
        f"lee el modelo que ya está configurado; no hay `VISION_API_KEY` que conseguir y Whisper "
        f"no mira imágenes.",
    )

    quedo = archivo_bajado(FICHA["contacto_id"], ficha["media_id"])
    assert quedo is not None and quedo.read_bytes() == IMAGEN_BYTES, roto(
        MEDIO,
        f"la imagen no quedó en medios/{FICHA['contacto_id']}/{ficha['media_id']} con los bytes "
        f"que sirvió el proveedor. El bloque se arma desde ese archivo.",
    )

    bloques = bloques_de_imagen(stub)
    assert bloques, roto(
        IMAGEN,
        f"al modelo no le llegó ningún bloque de imagen. Lo que se le pasó fue "
        f"{[ll['metodo'] for ll in stub.llamadas]} y adentro no hay un solo nodo con "
        f"`type: image`. `bloque_de_imagen()` puede estar escrita y no llamarse nunca: hasta esta "
        f"ronda ningún nodo de la suite la ejercitaba, así que el agente miraba fotos sin verlas.",
    )
    camino, bloque = bloques[0]

    fuente = bloque.get("source") or {}
    assert fuente.get("type") == "base64", roto(
        IMAGEN,
        f"el bloque salió con `source.type = {fuente.get('type')!r}`. Nunca `url` con el enlace "
        f"del proveedor: no es público y devuelve 401 del lado de Anthropic. Van los bytes en "
        f"base64.",
    )
    try:
        datos = base64.b64decode(fuente.get("data") or "", validate=True)
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            roto(
                IMAGEN,
                f"`source.data` no es base64 válido: {type(e).__name__}: {e}. Lo que hay adentro "
                f"empieza con {str(fuente.get('data'))[:40]!r}.",
            )
        )
    assert datos == IMAGEN_BYTES, roto(
        IMAGEN,
        f"el bloque lleva {len(datos)} bytes y la imagen que bajó tiene {len(IMAGEN_BYTES)}. Lo "
        f"que va en base64 son los bytes de `media_local`, no el `media_id` ni la URL.",
    )
    assert fuente.get("media_type") == ficha["mime_type"], roto(
        IMAGEN,
        f"el bloque declara `media_type = {fuente.get('media_type')!r}` y la bajada devolvió "
        f"`{ficha['mime_type']}`. Sale del `mime_type` de la bajada y no de la extensión del "
        f"archivo: un sticker webp declarado jpeg vuelve 400 `Could not process image`.",
    )
    prefijo = [c for c in camino if c.lower() in CLAVES_DE_PREFIJO]
    assert prefijo == [], roto(
        IMAGEN,
        f"el bloque viajó adentro de {'/'.join(camino)}, o sea en el prefijo del sistema. El "
        f"prefijo tiene que ser idéntico byte por byte en cada petición: una imagen ahí pone la "
        f"tasa de acierto del caché en cero sin un solo error visible. Va en el turno de usuario.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3 · La cita, que sólo existe si la creó el calendario
# ─────────────────────────────────────────────────────────────────────────────


def exigir_cita_coherente(salida: dict, doble: ServiciosFalsos, evento_id: str) -> dict:
    """La cita existe **si y sólo si** el calendario la creó. Devuelve la cita.

    Se llama con una entrada que trae las dos cosas que el paso 4 pide —confirmación y
    `mensaje.horario_elegido`—, así que acá no agendar es un fallo y no una rama:

    - **no hay cita** → el paso 4 no hizo su trabajo con todo lo que necesitaba. Un
      `agente/integraciones/calendario.py` vaciado a puros `raise` cae acá;
    - **hay cita sin llamada al calendario** → el identificador se lo escribió el código.
      `cita.evento_id = "evt-inventado"` sin Google cae acá;
    - **hay cita con otro identificador** → el `evento_id` no salió de la respuesta.

    Hasta esta ronda esta función devolvía `None` cuando no había cita, y con eso las tres
    afirmaciones de arriba no corrían nunca: la mitad «sí se agenda» era inalcanzable porque el
    contrato de entrada no tenía por dónde recibir el horario elegido. La dirección contraria
    —cuándo **no** se agenda— es de `exigir_sin_cita()`, que es su par y se usa cuatro veces
    abajo.
    """
    cita = salida.get("cita")
    cuarto = paso(salida, 4)

    assert cita is not None, roto(
        CITA,
        f"la entrada traía confirmación y horario elegido, y la salida vuelve con `cita` en nulo: "
        f"paso 4 «{cuarto['estado']}», motivo «{cuarto.get('motivo')}». Las llamadas que salieron "
        f"fueron {[(ll.metodo, ll.host + ll.ruta) for ll in doble.llamadas]}. Con las dos cosas "
        f"puestas el paso 4 agenda: es su camino feliz y es alcanzable. Si el motivo nombra RS256, "
        f"el build está firmando un JWT con una credencial `authorized_user`, que no lleva clave "
        f"privada y no firma nada: el token sale de un `POST` con `grant_type=refresh_token`. Ver "
        f"blueprint/33-agenda.md pasos 1 y 2.",
    )
    assert doble.eventos, roto(
        CITA,
        f"la salida trae `cita` con `evento_id = {cita.get('evento_id')!r}` y el calendario no "
        f"recibió una sola llamada. Las llamadas que salieron fueron "
        f"{[(ll.metodo, ll.host + ll.ruta) for ll in doble.llamadas]}. Un identificador que el "
        f"código se escribe a sí mismo es una cita que no existe: queda en la salida, en el "
        f"panel, en `leads.cita_evento_id` y en la confirmación que le llega al contacto, y el "
        f"día de la reunión no hay nada en la agenda.",
    )
    assert cita.get("evento_id") == evento_id, roto(
        CITA,
        f"el calendario devolvió `{evento_id}` y la salida dice `{cita.get('evento_id')!r}`. El "
        f"`evento_id` es el que trae la respuesta de Google, y es el que después se usa para no "
        f"crear un segundo evento en el reintento.",
    )
    return cita


def exigir_sin_cita(salida: dict, doble: ServiciosFalsos, porque: str) -> None:
    """El par de la de arriba: no se agendó, no se llamó a Google, y el paso 4 dice por qué.

    Las tres cosas juntas, porque se rompen por separado. Un build puede dejar `cita` en nulo y
    haber creado el evento igual —ahí el contacto tiene una cita que nadie va a ver, y el próximo
    ciclo crea un segundo evento—, y puede no crear nada y no decir por qué, que es la diferencia
    entre una decisión y un olvido.

    `porque` es qué faltaba, y se imprime: quien lea el rojo tiene que saber cuál de las cuatro
    direcciones se rompió sin contar las pruebas.
    """
    cuarto = paso(salida, 4)
    a_google = [ll for ll in doble.llamadas if ll.host in (HOST_CALENDARIO, HOST_OAUTH)]

    assert a_google == [], roto(
        CITA,
        f"{porque}, y salieron {len(a_google)} llamada(s) a Google: "
        f"{[ll.metodo + ' ' + ll.host + ll.ruta for ll in a_google]}. El paso 4 escribe afuera: "
        f"decide antes de tocar el cable.",
    )
    assert salida.get("cita") is None, roto(
        CITA,
        f"{porque}, y quedó una cita igual: {salida.get('cita')}. Sin llamada al calendario, eso "
        f"es un identificador que el código se escribió a sí mismo.",
    )
    assert cuarto["estado"] != "hecho", roto(
        CITA,
        f"{porque}, y el paso 4 dice «hecho»: {cuarto}. `hecho` en el paso 4 quiere decir que el "
        f"evento existe y que el contacto se enteró.",
    )
    assert cuarto.get("motivo"), roto(
        CITA,
        f"{porque}, el paso 4 no agendó y no dijo por qué: {cuarto}. Ese renglón es lo único que "
        f"tiene quien abra /bandeja para saber qué falta.",
    )


def test_cita_el_evento_id_sale_de_la_respuesta_del_calendario_y_no_de_una_constante(
    correr, entorno, tmp_path
) -> None:
    """Dos corridas, dos identificadores distintos, y la cita tiene que seguir al calendario.

    Con una sola corrida, una constante escrita en el build acierta si alguien la copió del
    fixture. Con dos, la única forma de acertar las dos es leer la respuesta. Es la misma idea del
    presupuesto anclado de `pruebas/test_caso_01.py`: no alcanza con que el valor sea plausible,
    tiene que venir de donde dice venir.

    **Es el camino feliz del paso 4 y es alcanzable**: entrada con `confirmado` en verdadero y
    con `mensaje.horario_elegido`, y credencial `authorized_user`, que saca el token con un `POST`
    y no firma nada. Las dos corridas tienen que agendar; que no agenden es rojo, no una rama.

    Y de paso muerde el otro lado del mismo hueco: el evento se crea en el horario que el
    contacto eligió y no en el primero que había libre.
    """
    entrada = entrada_para_agendar()
    elegido = instante(elegido_de(entrada))
    hueco = next(h for h in entrada["disponibilidad"] if instante(h["inicio"]) == elegido)
    citas = []

    assert MARCA_DEL_MODELO in StubModel.canonica().salida["texto"], (
        f"«{MARCA_DEL_MODELO}» dejó de estar en el texto de `StubModel.canonica()`. Es lo único "
        f"que separa el mensaje del paso 3 de la confirmación de la cita cuando los dos salen en "
        f"el mismo turno; se recalcula contra `pruebas/proveedor_falso.py`."
    )

    for evento_id in ("evt_de_la_primera_corrida", "evt_de_la_segunda_corrida"):
        entorno_de_agenda(entorno, tmp_path, base=f"sqlite:///{tmp_path}/wca-{evento_id}.db")
        doble = ServiciosFalsos(evento_id=evento_id)
        salidas, _ = correr([entrada], modelo=StubModel.canonica(), transporte=doble)
        salida = salidas[0]
        cita = exigir_cita_coherente(salida, doble, evento_id)
        citas.append(cita)

        cuerpo = doble.eventos[-1].datos or {}
        assert "attendees" not in cuerpo, roto(
            CITA,
            f"el evento salió con `attendees`: {cuerpo.get('attendees')}. Una cuenta de servicio "
            f"no puede invitar a nadie sin delegación de dominio y la API lo rechaza con "
            f"403 `forbiddenForServiceAccounts`; y con cualquiera de las dos credenciales no "
            f"tenemos el mail del contacto. Por eso la confirmación sale por WhatsApp.",
        )
        assert doble.freebusy, roto(
            CITA,
            "se creó el evento sin consultar `freeBusy`. Calendar deja crear eventos "
            "superpuestos: no hay reserva atómica, así que la comprobación va pegada al insert y "
            "no al momento de ofrecer. Sin eso se pisa una reserva ajena.",
        )
        assert doble.cuando(doble.freebusy[-1]) < doble.cuando(doble.eventos[-1]), roto(
            CITA,
            f"el `freeBusy` salió **después** del `POST` a `events`: la consulta fue la llamada "
            f"número {doble.cuando(doble.freebusy[-1])} de la corrida y el evento la "
            f"{doble.cuando(doble.eventos[-1])}. Comprobar después de crear no comprueba nada: el "
            f"evento ya está encima del ajeno. La comprobación va pegada al insert.",
        )
        assert cita.get("inicio"), roto(
            CITA,
            f"el evento se creó y la cita volvió sin `inicio`: {cita}. Es de donde sale la hora "
            f"del recordatorio y lo único que dice para cuándo quedó.",
        )
        assert instante(cita["inicio"]) == elegido, roto(
            CITA,
            f"el contacto eligió {elegido_de(entrada)!r} y la cita quedó en {cita['inicio']!r}. "
            f"El horario lo elige el contacto y viaja en `mensaje.horario_elegido`: la "
            f"confirmación autoriza, no elige. Agendar el primer hueco libre de "
            f"`disponibilidad` es la cita a la que no va a ir nadie.",
        )
        assert cita.get("duracion_min") == hueco["duracion_min"], roto(
            CITA,
            f"la cita quedó de {cita.get('duracion_min')!r} minutos y el hueco elegido dice "
            f"{hueco['duracion_min']}. La duración sale del `duracion_min` de ese hueco y no de "
            f"un default.",
        )
        assert cita.get("confirmacion_enviada") is True, roto(
            CITA,
            f"el evento existe y `confirmacion_enviada` dice "
            f"{cita.get('confirmacion_enviada')!r}. El cliente no recibe el mail de Google: si la "
            f"confirmación por WhatsApp no sale, tiene una cita y no lo sabe.",
        )
        # Dos: la respuesta del paso 3 y la confirmación de la cita. Ver blueprint/33-agenda.md
        # paso 3. Se cuenta acá y no en `pruebas/test_enviar.py` porque es la cuenta del turno que
        # agenda; la del turno que no agenda —uno— vive allá, sobre el caso 01 pelado.
        assert len(doble.envios) == 2, roto(
            CITA,
            f"salieron {len(doble.envios)} mensajes al contacto en un turno que agendó y tenían "
            f"que ser dos —la respuesta del paso 3 y la confirmación de la cita—: "
            f"{[e.texto for e in doble.envios]}. Con uno solo, o el paso 3 no contestó o la "
            f"confirmación no salió y `confirmacion_enviada` está mintiendo.",
        )
        del_modelo = [e for e in doble.envios if MARCA_DEL_MODELO in e.texto]
        assert len(del_modelo) == 1, roto(
            CITA,
            f"de los dos mensajes, {len(del_modelo)} traen «{MARCA_DEL_MODELO}», que es lo que "
            f"redactó el modelo para el paso 3: {[e.texto for e in doble.envios]}. La "
            f"confirmación de la cita la escribe el paso 4 y dice otra cosa; mandar dos veces lo "
            f"mismo es además lo que frena la regla 4 de `enviar()`.",
        )

    assert citas[0]["evento_id"] != citas[1]["evento_id"], roto(
        CITA,
        f"las dos corridas devolvieron `{citas[0]['evento_id']}` y el calendario había contestado "
        f"con dos identificadores distintos. Eso es una constante del build, no el id del evento.",
    )


@pytest.mark.parametrize(
    "con_horario",
    [False, True],
    ids=["sin horario elegido", "con el horario ya elegido"],
)
def test_cita_sin_confirmacion_no_se_llama_al_calendario(
    correr, entorno, tmp_path, con_horario: bool
) -> None:
    """La dirección que ya se afirmaba a medias: `cita` en nulo, y ahora también el silencio.

    `test_caso_01.py::test_4_sin_confirmacion_no_hay_cita` mira la salida y no el cable, así que
    un build que cree el evento y después lo omita de la salida pasa esa prueba con un evento
    creado en la agenda de verdad. Lo que no se hace no deja rastro: acá se cuenta el rastro.

    **Las dos formas, y la segunda es nueva.** Con `mensaje.horario_elegido` puesto, el paso 4
    tiene todo lo que necesita menos el permiso, y ahí es donde un build apurado agenda igual: el
    campo nuevo no puede convertirse en una puerta de atrás a la confirmación explícita. Es el
    requisito 3 del encargo de esta ronda y no se toca.
    """
    entorno_de_agenda(entorno, tmp_path, base=f"sqlite:///{tmp_path}/wca.db")
    doble = ServiciosFalsos(evento_id="evt_que_no_tenia_que_existir")

    horarios = proximos_horarios()
    entrada = con_mensaje(
        cargar("caso-01.entrada.json"),
        recibido_en=ahora().isoformat(),
        horario_elegido=horarios[HUECO_ELEGIDO]["inicio"] if con_horario else None,
    )
    entrada = con(entrada, modo="borrador", confirmado=False, disponibilidad=horarios)
    salidas, _ = correr([entrada], modelo=StubModel.canonica(), transporte=doble)
    salida = salidas[0]

    falta = "el horario está elegido y falta la confirmación" if con_horario else "no hay nada"
    exigir_sin_cita(salida, doble, f"en `borrador`, sin confirmar y {falta}")
    assert paso(salida, 4)["estado"] == "sin-confirmar", roto(
        CITA,
        f"el paso 4 quedó en «{paso(salida, 4)['estado']}» y tenía que quedar en «sin-confirmar»: "
        f"te está esperando.",
    )


def test_cita_confirmada_y_sin_horario_elegido_no_agenda_y_dice_cual_falta(
    correr, entorno, tmp_path
) -> None:
    """El otro requisito, solo. La confirmación autoriza; no elige.

    Es la conducta del primer turno del caso 01 y la que trae
    `pruebas/fixtures/caso-01.salida-esperada.json`: el contacto todavía no dijo cuál de los tres
    horarios le sirve, así que no hay nada que agendar por más que el permiso esté dado.

    Lo que muerde acá es el build que, con la confirmación puesta, agenda el primer hueco libre de
    `disponibilidad`. Esa cita nunca la aceptó nadie: el contacto se entera por la confirmación de
    WhatsApp de una reunión que no eligió, y el día de la cita no aparece.

    Y el motivo tiene que nombrar el horario y no el modo: en `automatico` y confirmado, «falta
    confirmación» sería falso, y quien lea `/bandeja` saldría a buscar un permiso que ya está.
    """
    entorno_de_agenda(entorno, tmp_path, base=f"sqlite:///{tmp_path}/wca.db")
    doble = ServiciosFalsos(evento_id="evt_que_nadie_eligio")

    salidas, _ = correr(
        [entrada_para_agendar(elegido=None)], modelo=StubModel.canonica(), transporte=doble
    )
    salida = salidas[0]

    exigir_sin_cita(salida, doble, "hay confirmación y no hay horario elegido")
    motivo = (paso(salida, 4).get("motivo") or "").lower()
    assert "horario" in motivo, roto(
        CITA,
        f"el paso 4 no agendó porque nadie eligió horario y el motivo dice «{motivo}». El texto "
        f"es «no hay horario elegido» —ése y no el del modo—: acá hay confirmación, así que "
        f"«falta confirmación» manda a quien lea /bandeja a dar un permiso que ya dio.",
    )
    assert len(doble.envios) == 1, roto(
        CITA,
        f"salieron {len(doble.envios)} mensajes en un turno que no agendó y tenía que salir uno "
        f"—el del paso 3—: {[e.texto for e in doble.envios]}. Un segundo mensaje acá es la "
        f"confirmación de una cita que no existe.",
    )


def test_cita_el_hueco_que_se_ocupo_entre_ofrecer_y_confirmar_no_se_pisa(
    correr, entorno, tmp_path
) -> None:
    """`freeBusy` dice que está ocupado, y no se crea nada.

    Calendar **deja** crear eventos superpuestos: no hay reserva atómica, así que la única
    diferencia entre un build que comprueba y uno que ofrece con fe es qué hace con la respuesta.
    Un build que llame a `freeBusy` y no lea lo que contesta pasa la mitad de arriba de este
    archivo —ahí sólo se exige que la llamada exista y que vaya antes— y se pone rojo acá.

    Lo que se pierde cuando falla es la reunión de otro: el hueco lo tomó alguien en el minuto
    que pasó entre que se ofreció y que el contacto contestó, y ahora hay dos personas citadas a
    la misma hora. Ver `blueprint/33-agenda.md` paso 6.
    """
    entorno_de_agenda(entorno, tmp_path, base=f"sqlite:///{tmp_path}/wca.db")
    doble = ServiciosFalsos(evento_id="evt_encima_del_ajeno", ocupado=True)

    salidas, _ = correr([entrada_para_agendar()], modelo=StubModel.canonica(), transporte=doble)
    salida = salidas[0]

    assert doble.freebusy, roto(
        CITA,
        f"el hueco estaba ocupado y el build no preguntó: no salió una sola consulta a "
        f"`freeBusy`. Las llamadas fueron "
        f"{[ll.metodo + ' ' + ll.host + ll.ruta for ll in doble.llamadas]}.",
    )
    assert doble.eventos == [], roto(
        CITA,
        f"`freeBusy` contestó que el hueco está ocupado y el evento se creó igual, por "
        f"{[ll.url for ll in doble.eventos]}. Ahí quedaron dos personas citadas a la misma hora, "
        f"y la que reservó primero no se entera. Preguntar y no mirar la respuesta es lo mismo "
        f"que no preguntar.",
    )
    assert salida.get("cita") is None, roto(
        CITA,
        f"no se creó ningún evento y la salida trae una cita igual: {salida.get('cita')}.",
    )
    cuarto = paso(salida, 4)
    assert cuarto["estado"] == "fallado", roto(
        CITA,
        f"el hueco estaba ocupado y el paso 4 quedó en «{cuarto['estado']}». Es `fallado` con el "
        f"motivo: no es que falte una confirmación, es que ese horario ya no existe.",
    )
    assert cuarto.get("motivo"), roto(
        CITA, f"el hueco estaba ocupado y el paso 4 no dijo nada: {cuarto}."
    )


def test_cita_con_cuenta_de_servicio_y_sin_la_libreria_de_rs256_queda_detenido(
    correr, entorno, tmp_path
) -> None:
    """La rama declarada y detenida, afirmada como cualquier otra conducta.

    Con una credencial `service_account` el token pide un JWT firmado con RS256, y ninguna
    librería que lo haga está en `PINES.md` —`google`, `cryptography` y `jwt` no están ni ahí ni
    en `plantillas/infra/requirements.txt`—. Esa rama queda declarada y detenida:
    `blueprint/33-agenda.md` paso 2.

    «Detenido» es una decisión y tiene forma: `cita` en nulo, cero llamadas a Google y el motivo
    escrito. Lo que no es es silencio, y tampoco es una excepción que se lleve puesto el ciclo:
    los pasos 1, 2, 3, 5 y 6 corren igual y el contacto recibe la respuesta del paso 3.

    Si algún día `PINES.md` fija la librería, esta prueba se pone roja y ahí se convierte en la
    otra mitad del camino feliz, con un par RSA generado en el `tmp_path`. Se cambia entonces, no
    antes.
    """
    entorno_de_agenda(
        entorno, tmp_path, base=f"sqlite:///{tmp_path}/wca.db", credencial="servicio"
    )
    doble = ServiciosFalsos(evento_id="evt_que_nadie_puede_firmar")

    salidas, _ = correr([entrada_para_agendar()], modelo=StubModel.canonica(), transporte=doble)
    salida = salidas[0]

    exigir_sin_cita(salida, doble, "la credencial es `service_account` y RS256 no está fijado")
    assert paso(salida, 4)["estado"] == "fallado", roto(
        CITA,
        f"el paso 4 quedó en «{paso(salida, 4)['estado']}». Con la rama detenida es `fallado` con "
        f"el motivo: no falta un permiso, falta una librería que el kit decidió no fijar.",
    )
    assert [p["n"] for p in salida.get("pasos", [])] == [1, 2, 3, 4, 5, 6], roto(
        CITA,
        f"la detención del paso 4 se llevó puesto el ciclo: quedaron "
        f"{[p.get('n') for p in salida.get('pasos', [])]}. Los otros cinco corren igual, que es "
        f"la diferencia entre una conducta declarada y una excepción sin atrapar.",
    )
    assert len(doble.envios) == 1, roto(
        CITA,
        f"con el paso 4 detenido salieron {len(doble.envios)} mensajes y tenía que salir uno, el "
        f"del paso 3: {[e.texto for e in doble.envios]}. El contacto tiene que recibir la "
        f"respuesta aunque la cita no se pueda crear; lo que no puede recibir es la confirmación "
        f"de una cita que no existe.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4 · El recordatorio, que sólo está programado si quedó un trabajo
# ─────────────────────────────────────────────────────────────────────────────


def base_del_build():
    """`agente/base.py`, o el salteo con el motivo escrito.

    Este nodo llega antes que el calendario: `agente/base.py` existe desde la fase 3 y las dos
    formas de la URL están ahí desde entonces. Por eso no pasa por la fixture `correr`, que pide
    el ciclo entero.
    """
    if not (RAIZ / "agente" / "base.py").is_file():
        pytest.skip(
            "falta el build: no existe agente/base.py. `normalizar_url()` y `url_sincrona()` las "
            "escribe blueprint/30-generacion.md en el paso de `base.py`, y las verifica "
            "blueprint/34-crm.md paso 2. Corré /armar-cerrador y volvé a esta suite."
        )
    try:
        return importlib.import_module("agente.base")
    except ModuleNotFoundError as e:
        pytest.skip(f"falta el build: {e}")


def test_recordatorio_las_dos_formas_de_la_url_de_la_base() -> None:
    """La decisión de `blueprint/00-contrato.md` § 8, afirmada donde todavía se puede afirmar.

    `cita.recordatorio_programado` sólo existe cuando el paso 4 llegó a crear un evento, y hoy no
    llega: `blueprint/33-agenda.md` paso 2 lo deja declarado y detenido mientras `PINES.md` no
    fije una librería que firme RS256. O sea que el booleano del recordatorio no se puede medir
    hoy, y lo que sí se puede medir es el mecanismo que lo decide, que ya está en el árbol desde
    la fase 3.

    Medido: con el paso 4 detenido, un build con `recordatorio_programado = True` siempre pasa la
    prueba de acá abajo, porque esa línea no llega a correr nunca. Este nodo es lo que igual se
    pone rojo si alguien «unifica» las dos funciones, que es el camino por el que la § 8
    desaparece sin que nadie lo decida.

    Las dos direcciones son las dos bases, y son la misma tabla de `blueprint/34-crm.md` paso 2.
    """
    base = base_del_build()
    for nombre in ("normalizar_url", "url_sincrona", "RecordatorioSinDriver"):
        assert hasattr(base, nombre), roto(
            RECORDATORIO,
            f"`agente/base.py` no expone `{nombre}`. Son dos funciones y una excepción, no una "
            f"sola función: el motor del proyecto es async y pide `+asyncpg` o `+aiosqlite`, y el "
            f"jobstore de APScheduler es síncrono y revienta con esa misma URL. Unificarlas rompe "
            f"uno de los dos caminos, siempre.",
        )

    assert base.normalizar_url("postgres://u:p@h:5432/db?sslmode=require") == (
        "postgresql+asyncpg://u:p@h:5432/db"
    ), roto(
        RECORDATORIO,
        f"`normalizar_url()` devolvió "
        f"{base.normalizar_url('postgres://u:p@h:5432/db?sslmode=require')!r}. Tiene que arreglar "
        f"`postgres://` —que es lo que entregan Railway y Supabase, y que SQLAlchemy no carga "
        f"desde la 1.4— y descartar `sslmode`, que asyncpg no entiende como parámetro de la "
        f"cadena.",
    )
    assert base.normalizar_url("sqlite:///./wca.db") == "sqlite+aiosqlite:///./wca.db", roto(
        RECORDATORIO,
        f"`normalizar_url()` devolvió {base.normalizar_url('sqlite:///./wca.db')!r} para SQLite.",
    )

    assert base.url_sincrona("sqlite:///./wca.db") == "sqlite:///./wca.db", roto(
        RECORDATORIO,
        f"`url_sincrona()` devolvió {base.url_sincrona('sqlite:///./wca.db')!r}. El jobstore es "
        f"síncrono: esa URL va **sin** `+aiosqlite`. Con la forma async el servicio no levanta, "
        f"y lo que se lee es `InvalidRequestError: The asyncio extension requires an async "
        f"driver`.",
    )

    with pytest.raises(base.RecordatorioSinDriver) as fallo:
        base.url_sincrona("postgres://u:p@h:5432/db?sslmode=require")
    motivo = str(fallo.value).lower()
    assert any(p in motivo for p in ("driver", "pines", "recordatorio")), roto(
        RECORDATORIO,
        f"`url_sincrona()` levantó `RecordatorioSinDriver` sin decir por qué: «{fallo.value}». "
        f"Ese "
        f"texto es lo que termina en `pasos[3].motivo` y lo que lee quien se pregunta por qué el "
        f"recordatorio no salió.",
    )


def trabajos_agendados() -> list:
    """Los trabajos que el scheduler tiene pendientes, leídos del build y no de la salida.

    Es la verificación que `blueprint/33-agenda.md` paso 4 escribe con todas las letras. Existe
    porque `cita.recordatorio_programado` es un booleano que el paso se escribe a sí mismo: sin
    mirar el scheduler, «programado» y «no programado» son la misma corrida.
    """
    try:
        calendario = importlib.import_module("agente.integraciones.calendario")
    except ModuleNotFoundError as e:
        pytest.fail(
            roto(
                RECORDATORIO,
                f"no pude importar `agente.integraciones.calendario`: {e}. Es el módulo donde "
                f"vive el paso 4 entero, evento, `freeBusy` y recordatorio.",
            )
        )
    agenda = getattr(calendario, "agenda", None)
    if agenda is None:
        pytest.fail(
            roto(
                RECORDATORIO,
                "`agente/integraciones/calendario.py` no expone `agenda()`. Es el nombre con el "
                "que el paso 4 llega al scheduler —`agenda().add_job(...)`— y el único lugar "
                "desde donde se puede ver si un recordatorio quedó de verdad.",
            )
        )
    return list(agenda().get_jobs())


def cuando_corre(trabajo) -> datetime | None:
    """Cuándo va a correr ese trabajo, sin depender de que el scheduler esté arrancado.

    `next_run_time` queda en nulo mientras el scheduler no arrancó; el `run_date` del disparador
    está siempre. Se miran los dos y manda el que haya.
    """
    momento = getattr(getattr(trabajo, "trigger", None), "run_date", None)
    return momento or getattr(trabajo, "next_run_time", None)


@pytest.mark.parametrize(
    "base",
    ["sqlite", "postgres"],
    ids=["sobre SQLite queda agendado", "sobre Postgres queda detenido"],
)
def test_recordatorio_programado_solo_si_quedo_un_trabajo_en_el_scheduler(
    correr, entorno, tmp_path, base: str
) -> None:
    """Las dos conductas de `blueprint/00-contrato.md` § 8, cada una con su mitad.

    Sobre SQLite el recordatorio funciona entero y `recordatorio_programado` en verdadero tiene
    que tener un trabajo atrás, con el id de la cita y a 24 horas del inicio. Sobre Postgres
    `url_sincrona()` levanta `RecordatorioSinDriver` —el jobstore de APScheduler es síncrono y el
    driver síncrono no está fijado en PINES.md—, así que el campo queda en falso **con el motivo
    escrito**, y la cita y la confirmación salen igual.

    La § 8 entera se puede mentir en un booleano, y hasta esta ronda no había un solo nodo que
    mirara el scheduler.
    """
    url = (
        f"sqlite:///{tmp_path}/wca.db"
        if base == "sqlite"
        else "postgres://usuario:clave@servidor:5432/base?sslmode=require"
    )
    entorno_de_agenda(entorno, tmp_path, base=url)
    doble = ServiciosFalsos(evento_id=f"evt_del_recordatorio_{base}")
    entrada = entrada_para_agendar()

    salidas, _ = correr([entrada], modelo=StubModel.canonica(), transporte=doble)
    salida = salidas[0]
    cita = exigir_cita_coherente(salida, doble, doble.evento_id)

    programado = cita.get("recordatorio_programado")
    cuarto = paso(salida, 4)

    if base == "postgres":
        assert programado is False, roto(
            RECORDATORIO,
            f"sobre Postgres `recordatorio_programado` dice {programado!r}. El jobstore de "
            f"APScheduler 3 es síncrono y pide un driver que PINES.md no fija: `url_sincrona()` "
            f"levanta `RecordatorioSinDriver` y el paso lo deja en falso. Un verdadero acá es la "
            f"noche anterior a la cita sin recordatorio y nadie avisado.",
        )
        motivo = (cuarto.get("motivo") or "").lower()
        assert any(p in motivo for p in ("driver", "recordatorio", "apscheduler", "postgres")), (
            roto(
                RECORDATORIO,
                f"el recordatorio no se pudo programar y el paso 4 no dice por qué: "
                f"«{cuarto.get('motivo')}». El motivo va en `pasos[3].motivo` y no adentro de "
                f"`cita`, que es `additionalProperties: false` con cinco propiedades.",
            )
        )
        assert cuarto["estado"] == "hecho", roto(
            RECORDATORIO,
            f"el paso 4 quedó en «{cuarto['estado']}». Con Postgres el evento existe y el "
            f"contacto se enteró: lo que no quedó es el recordatorio, y eso se lee en las dos "
            f"claves de `cita`, no en el estado del paso.",
        )
        assert cita.get("confirmacion_enviada") is True, roto(
            RECORDATORIO,
            "sin recordatorio, la cita y la confirmación por WhatsApp salen igual. Acá no salió "
            "la confirmación: el freno del recordatorio se llevó puesto el paso entero.",
        )
        return

    assert programado is True, roto(
        RECORDATORIO,
        f"sobre SQLite `recordatorio_programado` dice {programado!r}: «{cuarto.get('motivo')}». "
        f"`sqlite3` es de la biblioteca estándar y no hay nada que fijar, así que acá el "
        f"recordatorio funciona entero.",
    )

    trabajos = trabajos_agendados()
    esperado = f"recordatorio:{cita['evento_id']}"
    encontrados = [t for t in trabajos if t.id == esperado]
    assert encontrados, roto(
        RECORDATORIO,
        f"`recordatorio_programado` dice verdadero y en el scheduler no hay ningún trabajo "
        f"`{esperado}`. Hay {[t.id for t in trabajos]}. El id es estable a propósito, con "
        f"`replace_existing=True`: es lo que impide dos recordatorios para la misma cita.",
    )
    momento = cuando_corre(encontrados[0])
    assert momento is not None, roto(
        RECORDATORIO,
        f"el trabajo `{esperado}` quedó sin hora. Un `date` sin `run_date` no corre nunca.",
    )
    assert cita.get("inicio"), roto(
        RECORDATORIO,
        f"la cita volvió sin `inicio`: {cita}. El recordatorio se cuenta 24 horas antes de esa "
        f"hora; sin ella no hay contra qué comparar.",
    )
    inicio = instante(cita["inicio"])
    assert momento.tzinfo is not None, roto(
        RECORDATORIO,
        f"el trabajo quedó agendado a las {momento} sin `tzinfo`. APScheduler lo toma en la zona "
        f"del scheduler, que en un contenedor es UTC: el recordatorio sale a la hora equivocada.",
    )
    diferencia = inicio - momento
    assert diferencia == timedelta(hours=24), roto(
        RECORDATORIO,
        f"la cita empieza {inicio} y el recordatorio quedó para {momento}: van {diferencia} y "
        f"tienen que ser 24 horas.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4b · El cuerpo del recordatorio: qué pasa cuando el trabajo dispara
# ─────────────────────────────────────────────────────────────────────────────

# Cuántos mensajes deja el turno que agenda, antes de que el recordatorio dispare: la respuesta del
# paso 3 y la confirmación de la cita. Lo afirma
# `test_cita_el_evento_id_sale_de_la_respuesta_del_calendario_y_no_de_una_constante`; acá se usa
# como línea de base para contar lo que agrega el disparo y nada más.
ENVIOS_DEL_TURNO_QUE_AGENDA = 2


def barrido_del_build():
    """`barrer_recordatorios()` de `agente/integraciones/calendario.py`, o el rojo con el motivo.

    Es el nombre por el que se llega al barrido del arranque, igual que `agenda()` es el nombre por
    el que se llega al scheduler y `TRANSPORTE` el nombre por el que se llega al transporte. Sin un
    nombre fijo, «el barrido no es opcional» de `blueprint/33-agenda.md` paso 4 no tiene por dónde
    entrar una aserción, y eso fue lo que estuvo tres rondas.
    """
    try:
        calendario = importlib.import_module("agente.integraciones.calendario")
    except ModuleNotFoundError as e:
        pytest.fail(
            roto(RECORDATORIO, f"no pude importar `agente.integraciones.calendario`: {e}.")
        )
    barrer = getattr(calendario, "barrer_recordatorios", None)
    if barrer is None:
        pytest.fail(
            roto(
                RECORDATORIO,
                "`agente/integraciones/calendario.py` no expone `barrer_recordatorios()`. Es el "
                "barrido del arranque: un trabajo `date` cuya hora pasó mientras el servicio "
                "estuvo caído se descarta solo, porque el `misfire_grace_time` por defecto es de "
                "un segundo. Sin el barrido, un despliegue en el momento equivocado se lleva "
                "puesto el recordatorio de cada cita que había pendiente, y no lo dice nadie: "
                "`cita.recordatorio_programado` quedó en verdadero el día que se agendó.",
            )
        )
    return barrer


def disparar(trabajo):
    """Corre el trabajo **en su propia hora**, como lo correría el scheduler.

    El nodo del scheduler prueba que **quedó** un trabajo con el id y la hora correctos; esto es
    lo otro, que ese trabajo **haga** algo cuando le toque. Un `recordar()` que sea un `return`
    pelado deja el árbol entero en verde y la noche anterior a la cita no pasa nada.

    Se llama por `func` y `args`, que es la API pública de APScheduler y lo que el scheduler usa:
    así la prueba no tiene que saber cómo se llama la función ni desde qué módulo se importó.

    **El viaje en el tiempo no es un adorno.** `recordar()` no sabe cuál era su `run_date`: le
    pregunta al reloj, y `enviar()` compara ese reloj contra `last_inbound_at` para decidir si la
    ventana de 24 horas está abierta. Corrido en el instante del corpus —que es donde
    `pruebas/conftest.py` para la sesión entera— el recordatorio de una cita a treinta días saldría
    con la ventana recién abierta, o sea que la mitad «fuera de la ventana» de este archivo mediría
    lo contrario de lo que dice medir. Es el mismo `freeze_time` anidado que ya usa
    `pruebas/test_enviar.py`.
    """
    freeze_time = pytest.importorskip(
        "freezegun",
        reason=(
            "falta freezegun en este intérprete. Sin él no hay forma de correr el trabajo del "
            "recordatorio en su propia hora, y `enviar()` decide la ventana de 24 horas contra el "
            "reloj: en el instante del corpus la ventana está abierta siempre y la mitad «fuera de "
            "la ventana» de esta prueba pasaría por vacío. Está en PINES.md; corré esto con el "
            "`.venv` del proyecto."
        ),
    ).freeze_time

    funcion = getattr(trabajo, "func", None)
    assert callable(funcion), roto(
        RECORDATORIO,
        f"el trabajo `{getattr(trabajo, 'id', '?')}` no tiene una función que se pueda llamar: "
        f"`func` es {funcion!r}. Un trabajo sin cuerpo queda en el scheduler, se ve en "
        f"`get_jobs()` y no manda nada.",
    )
    momento = cuando_corre(trabajo)
    assert momento is not None, roto(
        RECORDATORIO,
        f"el trabajo `{trabajo.id}` quedó sin hora. Un `date` sin `run_date` no corre nunca.",
    )
    with freeze_time(momento, real_asyncio=True):
        resultado = funcion(*(getattr(trabajo, "args", ()) or ()))
        return asyncio.run(resultado) if inspect.isawaitable(resultado) else resultado


def trabajo_del_recordatorio(evento_id: str):
    """El trabajo `recordatorio:{evento_id}`, o el rojo con la lista de lo que sí hay."""
    esperado = f"recordatorio:{evento_id}"
    trabajos = trabajos_agendados()
    encontrados = [t for t in trabajos if t.id == esperado]
    assert encontrados, roto(
        RECORDATORIO,
        f"en el scheduler no hay ningún trabajo `{esperado}`. Hay {[t.id for t in trabajos]}.",
    )
    return encontrados[0]


@pytest.mark.parametrize(
    "cuando",
    ["dentro de la ventana", "fuera de la ventana"],
)
def test_recordatorio_el_trabajo_que_dispara_manda_por_enviar(
    correr, entorno, tmp_path, cuando: str
) -> None:
    """El segundo camino de salida del kit, que hasta esta ronda no tenía una sola aserción.

    `grep -rn recordar pruebas/ scripts/auditar.py` no imprimía una línea. Lo que sí estaba era el
    nodo del scheduler, que afirma que **quedó** un trabajo con el id estable y a 24 horas del
    inicio; nadie afirmaba que ese trabajo **mande** algo al dispararse. Un `recordar()` que sea un
    `return` pelado deja el árbol en `PASS · 0 errores · 0 avisos · 0 salteados`, y el contacto
    llega al día de la cita sin haber recibido nada.

    Y no alcanza con que mande: tiene que mandar **por `enviar()`**, que es lo que dice la lista
    «Si falla» del paso 5 de `blueprint/33-agenda.md` —«El recordatorio salió sin pasar por
    `enviar()`. Ese es el segundo camino»— y lo que hasta ahora no tenía nada atrás. Las dos
    direcciones son las dos posiciones de la cita respecto de la ventana de 24 horas, que es la
    guarda que decide:

    - **cita dentro de treinta horas** → el recordatorio cae dentro de la ventana que abrió el
      mensaje de este turno, así que sale, y sale con la `Idempotency-Key` sacada del contenido.
      Esa cabecera la pone `enviar()` y no la lleva un `.post` escrito adentro de
      `agente/integraciones/calendario.py`: es la huella de haber pasado por la única puerta;
    - **cita dentro de treinta días** → el recordatorio cae 29 días después del último mensaje del
      contacto, o sea con la ventana cerrada. Ahí WhatsApp sólo acepta plantillas aprobadas: lo que
      salga tiene que ser una plantilla, y si no hay ninguna dada de alta no sale nada y se dice.
      **Texto libre acá es el segundo camino**, y lo que se pierde no es un aviso: es el número de
      WhatsApp del negocio.

    Las dos van sobre SQLite, que es donde el recordatorio existe: con Postgres queda declarado
    detenido y no hay trabajo que disparar. Ver `blueprint/00-contrato.md` § 8.
    """
    entorno_de_agenda(entorno, tmp_path, base=f"sqlite:///{tmp_path}/wca.db")
    doble = ServiciosFalsos(evento_id=f"evt_del_disparo_{cuando.replace(' ', '_')}")
    adentro = cuando == "dentro de la ventana"
    entrada = entrada_para_agendar(
        dentro_de_dias=0 if adentro else 30, dentro_de_horas=28 if adentro else 0
    )

    salidas, _ = correr([entrada], modelo=StubModel.canonica(), transporte=doble)
    cita = exigir_cita_coherente(salidas[0], doble, doble.evento_id)

    assert cita.get("recordatorio_programado") is True, roto(
        RECORDATORIO,
        f"sobre SQLite `recordatorio_programado` dice {cita.get('recordatorio_programado')!r}: "
        f"«{paso(salidas[0], 4).get('motivo')}». Sin trabajo programado no hay nada que disparar, "
        f"y esta prueba mediría cero contra cero.",
    )
    trabajo = trabajo_del_recordatorio(cita["evento_id"])
    antes = len(doble.envios)
    assert antes == ENVIOS_DEL_TURNO_QUE_AGENDA, roto(
        RECORDATORIO,
        f"el turno que agendó dejó {antes} mensaje(s) y tenían que ser "
        f"{ENVIOS_DEL_TURNO_QUE_AGENDA} —la respuesta del paso 3 y la confirmación de la cita—: "
        f"{[e.texto for e in doble.envios]}. La cuenta de acá abajo se hace contra esta línea.",
    )

    disparar(trabajo)
    nuevos = doble.envios[antes:]

    if adentro:
        assert len(nuevos) == 1, roto(
            RECORDATORIO,
            f"el trabajo `{trabajo.id}` disparó y dejó {len(nuevos)} mensaje(s) al contacto: "
            f"{[e.texto for e in nuevos]}. La cita es dentro de treinta horas y el contacto "
            f"escribió recién, así que el recordatorio cae adentro de la ventana y sale. Con cero, "
            f"el trabajo quedó agendado y su cuerpo no manda nada: `recordatorio_programado` está "
            f"diciendo que sí sobre una función vacía.",
        )
        assert nuevos[0].idempotency_key, roto(
            RECORDATORIO,
            f"el recordatorio salió sin `Idempotency-Key`: {dict(nuevos[0].cabeceras)}. Esa "
            f"cabecera la pone `enviar()` y sale del contenido —conversación, paso y hash del "
            f"texto—. Que no esté quiere decir que este mensaje no pasó por `enviar()`, o sea que "
            f"salió por un segundo camino: sin la ventana de 24 horas, sin el chequeo de baneo y "
            f"sin la regla de no escribirle primero a quien no escribió. **Invariante 2.**",
        )
        return

    libres = [e for e in nuevos if not e.es_plantilla]
    assert libres == [], roto(
        RECORDATORIO,
        f"la cita es dentro de treinta días, así que el recordatorio cae 29 días después del "
        f"último mensaje del contacto y la ventana está cerrada; salió texto libre igual, por "
        f"{[(e.ruta, e.texto) for e in libres]}. Fuera de la ventana WhatsApp sólo acepta "
        f"plantillas aprobadas, y esto no se lee como un error del envío: se lee como la "
        f"calificación del número bajando. Si el recordatorio no pasa por `enviar()`, esta guarda "
        f"no corre; ver blueprint/33-agenda.md paso 5.",
    )


def test_barrido_el_arranque_vuelve_a_dejar_el_trabajo_que_el_misfire_se_llevo(
    correr, entorno, tmp_path
) -> None:
    """«El barrido al arrancar no es opcional», con algo atrás.

    Esa frase estuvo tres rondas en `blueprint/33-agenda.md` paso 4 con **cero** referencias en
    `pruebas/` y en `scripts/auditar.py`. Lo que tapaba: un trabajo `date` cuya hora pasó mientras
    el servicio estuvo caído se descarta solo —el `misfire_grace_time` por defecto es de un
    segundo—, así que un despliegue en el momento equivocado se lleva puesto el recordatorio de
    cada cita pendiente. Nadie se entera: `cita.recordatorio_programado` quedó en verdadero el día
    que se agendó y en la salida sigue diciendo que sí.

    El scheduler vaciado es la reproducción exacta de ese descarte, y es lo único que hace falta
    para que la pregunta tenga respuesta: después del barrido, ¿el trabajo está o no está?

    Las dos direcciones:

    - **vuelve**: con el mismo id estable y a la misma hora. Un barrido que reprograme con otro id
      deja dos recordatorios para la misma cita la próxima vez que alguien lo corra;
    - **no duplica**: correrlo dos veces deja un trabajo y no dos, que es para lo que están el id
      estable y `replace_existing=True`. Y no manda nada, porque este recordatorio todavía no
      vence: barrer no es mandar.
    """
    entorno_de_agenda(entorno, tmp_path, base=f"sqlite:///{tmp_path}/wca.db")
    doble = ServiciosFalsos(evento_id="evt_del_barrido")

    salidas, _ = correr(
        [entrada_para_agendar()], modelo=StubModel.canonica(), transporte=doble
    )
    cita = exigir_cita_coherente(salidas[0], doble, doble.evento_id)
    trabajo = trabajo_del_recordatorio(cita["evento_id"])
    esperado, hora = trabajo.id, cuando_corre(trabajo)
    envios_antes = len(doble.envios)

    barrer = barrido_del_build()

    # Lo que hace el `misfire_grace_time` de un segundo con el servicio caído, sin esperar a que
    # pase la hora: el trabajo deja de estar.
    importlib.import_module("agente.integraciones.calendario").agenda().remove_all_jobs()
    assert [t for t in trabajos_agendados() if t.id == esperado] == [], (
        f"`remove_all_jobs()` no vació el scheduler: sigue estando `{esperado}`. Sin el scheduler "
        f"vacío esta prueba no reproduce nada y el barrido pasaría por vacío."
    )

    for vuelta in (1, 2):
        resultado = barrer()
        if inspect.isawaitable(resultado):
            asyncio.run(resultado)

        vueltos = [t for t in trabajos_agendados() if t.id == esperado]
        assert vueltos, roto(
            RECORDATORIO,
            f"corrió el barrido (vuelta {vuelta}) y el trabajo `{esperado}` no volvió al "
            f"scheduler. Hay {[t.id for t in trabajos_agendados()]}. El barrido recorre las citas "
            f"futuras sin recordatorio enviado y reprograma las que todavía sirven: sin eso, el "
            f"recordatorio de esta cita no existe más y nada lo dice.",
        )
        assert len(vueltos) == 1, roto(
            RECORDATORIO,
            f"después de {vuelta} barrido(s) hay {len(vueltos)} trabajos con el id `{esperado}`. "
            f"El id es estable y va con `replace_existing=True` justamente para esto: cada "
            f"arranque volvería a agregar el mismo recordatorio y el contacto recibiría uno por "
            f"despliegue.",
        )
        assert cuando_corre(vueltos[0]) == hora, roto(
            RECORDATORIO,
            f"el barrido reprogramó `{esperado}` para {cuando_corre(vueltos[0])} y estaba para "
            f"{hora}. La hora sale de la cita —24 horas antes del inicio— y no del momento en que "
            f"arrancó el servicio.",
        )

    assert len(doble.envios) == envios_antes, roto(
        RECORDATORIO,
        f"el barrido dejó {len(doble.envios) - envios_antes} mensaje(s) al contacto: "
        f"{[e.texto for e in doble.envios[envios_antes:]]}. Este recordatorio todavía no vence, "
        f"así que se reprograma y no se manda. Mandar lo que todavía no vence es el aviso que "
        f"llega un mes antes, y con dos arranques seguidos son dos.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5 · El CRM, que sólo escribió si hay una fila escrita
# ─────────────────────────────────────────────────────────────────────────────

# Las tres columnas que el agente no toca nunca. `creado_en` es la fecha del primer contacto; las
# otras dos las escribe una persona. Ver `blueprint/34-crm.md` paso 3.
COLUMNAS_AJENAS = ("dueno", "notas", "creado_en")

# El rechazo que Supabase devuelve con la clave `anon`: el insert vuelve 403 con `42501` y la fila
# no queda. Es el modo de falla que `blueprint/34-crm.md` paso 1 nombra, y el que hace visible al
# build que da la escritura por hecha sin mirar la respuesta.
RECHAZO_DEL_SERVICIO = (
    403,
    {
        "code": "42501",
        "message": 'new row violates row-level security policy for table "leads"',
        "details": None,
        "hint": None,
    },
)


@pytest.mark.parametrize(
    "caso",
    ["el servicio la escribe", "el servicio la rechaza", "sin SUPABASE_URL"],
)
def test_crm_escrito_solo_si_la_fila_se_escribio(correr, entorno, tmp_path, caso: str) -> None:
    """`crm.escrito` lo decide la respuesta del servicio, y nunca el código que armó el dict.

    Las tres corridas son la misma entrada con el mismo modo, y lo único que cambia es qué pasa
    del otro lado. Un build que ponga `escrito = True` al terminar de armar la fila pasa la
    primera y se pone rojo en las otras dos, que es exactamente lo que hay que ver: la fila que no
    se escribió y el agente diciendo que sí.

    La tercera no es un error del servicio, es el camino sin credencial de
    `blueprint/34-crm.md` paso 5: la fila se arma igual, se devuelve en `crm` y alguien la copia a
    mano. Perderla es el daño que no se ve.
    """
    entorno(
        SUPABASE_URL=None if caso == "sin SUPABASE_URL" else SUPABASE_DE_PRUEBAS,
        SUPABASE_SERVICE_KEY=None if caso == "sin SUPABASE_URL" else SUPABASE_KEY_DE_PRUEBAS,
        GOOGLE_CALENDAR_ID=None,
        DATABASE_URL=f"sqlite:///{tmp_path}/wca.db",
    )
    doble = ServiciosFalsos(
        respuesta_del_crm=RECHAZO_DEL_SERVICIO if caso == "el servicio la rechaza" else (201, [])
    )
    entrada = entrada_para_agendar()

    salidas, _ = correr([entrada], modelo=StubModel.canonica(), transporte=doble)
    salida = salidas[0]
    crm = salida.get("crm")
    quinto = paso(salida, 5)

    assert crm is not None, roto(
        CRM,
        f"`crm` volvió en nulo. Nulo quiere decir «el paso 5 no corrió», y acá corrió: la "
        f"diferencia es la fila que alguien tiene que poder copiar. El caso es «{caso}».",
    )

    if caso == "el servicio la escribe":
        assert doble.filas, roto(
            CRM,
            f"el transporte no vio ninguna escritura al CRM. Las llamadas que salieron fueron "
            f"{[(ll.metodo, ll.host + ll.ruta) for ll in doble.llamadas]}. El camino de Supabase "
            f"es HTTP y sale por el cliente único de `agente/http.py`, con `timeout=`.",
        )
        peticion = doble.filas[-1]
        assert "/rest/v1/leads" in peticion.ruta, roto(
            CRM,
            f"la escritura salió a {peticion.url}. Por PostgREST la tabla `leads` es "
            f"`POST /rest/v1/leads?on_conflict=contacto_id`.",
        )
        assert "on_conflict=contacto_id" in peticion.url, roto(
            CRM,
            f"la escritura salió sin `on_conflict=contacto_id`: {peticion.url}. Sin eso no hay "
            f"upsert: hay un insert que falla con la fila ya puesta, o dos filas.",
        )
        preferencia = peticion.cabeceras.get("prefer", "")
        assert "merge-duplicates" in preferencia, roto(
            CRM,
            f"la escritura salió con `Prefer: {preferencia!r}`. PostgREST hace el upsert con "
            f"`resolution=merge-duplicates`; sin esa cabecera el conflicto se ignora y la fila "
            f"vieja se queda como estaba.",
        )
        cuerpo = peticion.datos
        fila = cuerpo[0] if isinstance(cuerpo, list) and cuerpo else cuerpo
        assert isinstance(fila, dict), roto(
            CRM, f"el cuerpo de la escritura no trae una fila: {peticion.texto[:200]!r}."
        )
        assert fila.get("contacto_id") == entrada["mensaje"]["contacto_id"], roto(
            CRM,
            f"la fila se escribió con `contacto_id = {fila.get('contacto_id')!r}` y el mensaje "
            f"trae `{entrada['mensaje']['contacto_id']}`. La clave es `contacto_id` y no el "
            f"número: el teléfono puede venir nulo y no es estable.",
        )
        ajenas = [c for c in COLUMNAS_AJENAS if c in fila]
        assert ajenas == [], roto(
            CRM,
            f"la fila lleva {ajenas}. `creado_en` es la fecha del primer contacto y `dueno` y "
            f"`notas` las escribe una persona: mandarlas es el daño que no se ve, porque la tabla "
            f"sigue andando y el vendedor asignado desapareció.",
        )
        assert crm.get("escrito") is True, roto(
            CRM,
            f"el servicio aceptó la fila y `crm.escrito` dice {crm.get('escrito')!r}.",
        )
        assert quinto["estado"] == "hecho", roto(
            CRM, f"la fila se escribió y el paso 5 quedó en «{quinto['estado']}»."
        )
        return

    assert crm.get("escrito") is False, roto(
        CRM,
        f"caso «{caso}»: la fila no se escribió y `crm.escrito` dice {crm.get('escrito')!r}. "
        f"`escrito` lo decide la respuesta del servicio, no el código que armó el diccionario. "
        f"El transporte vio {len(doble.filas)} escritura(s) y contestó "
        f"{doble.respuesta_del_crm[0]}.",
    )
    assert quinto["estado"] == "fallado", roto(
        CRM,
        f"caso «{caso}»: el paso 5 quedó en «{quinto['estado']}» y tenía que quedar en «fallado» "
        f"con el motivo. `hecho` acá es reportar el armado como escritura.",
    )
    assert quinto.get("motivo"), roto(
        CRM, f"caso «{caso}»: el paso 5 falló y no dijo por qué: {quinto}."
    )
    assert crm.get("resumen"), roto(
        CRM,
        f"caso «{caso}»: la fila volvió sin `resumen`. Se arma igual y se devuelve entera, para "
        f"que se pueda copiar a mano o volver a correr el paso 5 desde /bandeja: no se pierde "
        f"nada.",
    )

    if caso == "sin SUPABASE_URL":
        assert doble.filas == [], roto(
            CRM,
            f"sin `SUPABASE_URL` salieron {len(doble.filas)} escritura(s): "
            f"{[ll.url for ll in doble.filas]}. Sin credencial no se escribe en ningún lado.",
        )
