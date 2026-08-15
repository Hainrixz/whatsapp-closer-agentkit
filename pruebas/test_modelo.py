"""La única llamada real al modelo, mirada contra bytes grabados. Sin credencial y sin red.

El defecto que este archivo existe para hacer fallar no es una línea mal escrita: es una orilla
que ninguna otra prueba puede tocar. `agente/modelo.py` se vacía a un `raise` y el árbol sigue en
`199 passed · PASS · 0 errores · 0 avisos · 0 salteados`, porque la suite entera inyecta
`StubModel` justamente para no ejecutar esa función. Adentro de ella viven el nombre del método
del SDK, la forma del pedido, `thinking`, `output_config` y la extracción de la respuesta, y el
chequeo 10 `modelo` de la compuerta sólo hace grep de literales de modelo y de los cuatro
parámetros que dan 400. Un build cuyo `modelo_de_produccion()` devuelva algo roto se publica en
verde y muere en el primer mensaje real.

## Cómo se cubre: igual que las firmas

`pruebas/test_firmas.py` no revisa el código de `verificar_meta()`: le pone enfrente los bytes de
una entrega grabada y lo hace fallar si reserializa. Acá es lo mismo, del otro lado del cable:
`pruebas/fixtures/modelo.*.respuesta.json` son los bytes de una respuesta de la API de Anthropic,
con un bloque `thinking` primero, un `text` después y la salida recién en el tercero. Una
implementación que lea `content[0]` —o el primer `text`— no puede pasar. La prueba no revisa el
código: lo hace fallar.

**Esos bytes están transcritos de la forma vigente de la API, no capturados de una entrega real.**
Es la diferencia honesta contra `meta.raw` y `zernio.raw`: para escribirlos no se hizo ninguna
llamada y no se usó ninguna credencial, así que pinchan una extracción mal escrita pero no pueden
delatar que la API haya cambiado de forma. Cuando alguien tenga una entrega real grabada, se
reemplazan los bytes y esta prueba empieza a valer también para eso. No llevan `.raw`, y no es
descuido: en `pruebas/fixtures/` ese sufijo es el cuerpo crudo de una entrega **firmada** —lo que
mira el chequeo 18 de la compuerta, que exige su `.meta.json` al lado y sus cuatro comprobaciones
en `pruebas/test_firmas.py`—, y acá no hay ninguna firma que verificar.

## Las dos formas del pedido, y por qué se aceptan las dos

`blueprint/30-generacion.md` paso 5 manda la llamada con `esquema_wire()` y no fija cómo viaja ese
esquema. Las dos formas que la API vigente ofrece son la herramienta con `input_schema` y las
salidas estructuradas con `output_config.format`; `plantillas/contratos/wire_schema.py` nombra a
las segundas en `PALABRAS_PROHIBIDAS`. Elegir una acá pondría en rojo a un build fiel que eligió la
otra, así que el doble mira **qué declaró el pedido** y contesta con el fixture que le corresponde.
Lo que se afirma en los dos caminos es lo mismo: el pedido lleva el esquema angosto entero, y la
salida sale del bloque donde de verdad está.

## Nada de acá pide una credencial ni toca la red

`ANTHROPIC_API_KEY` es una constante inventada de este archivo, con `prueba` adentro, que no abre
nada en ningún lado. El transporte de httpx se dobla por debajo —los dos, el síncrono y el
asíncrono— así que ni el SDK ni el cliente único de `agente/http.py` construyen un socket, y la
guarda `sin_red` de `pruebas/conftest.py` sigue puesta y no se toca.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from pruebas.proveedor_falso import CAMPOS_WIRE, FIXTURES, RAIZ, olvidar_el_build

MODULO = "agente/modelo.py"
FABRICA = "modelo_de_produccion"
PINES = RAIZ / "PINES.md"

# La clave es de mentira y está escrita acá a propósito, igual que el secreto de
# `pruebas/fixtures/meta.meta.json`: no firma nada, no autoriza nada y no sale del proceso. La de
# verdad vive en `.env` y no entra a este árbol.
#
# **No tiene la forma de una clave de Anthropic, y eso también es a propósito.** El chequeo 08
# `secretos` de la compuerta busca ese prefijo en todo el árbol y marca `secretos/credencial`; una
# clave de mentira con la forma de una de verdad enseña a ignorar ese hallazgo, que es el único
# que avisa cuando alguien pega la buena. El SDK no valida el formato: le alcanza con que no esté
# vacía.
CLAVE_DE_PRUEBA = "clave-de-prueba-sin-credencial-no-usar-en-produccion"

# Los cuatro que devuelven 400 con este modelo. Se buscan **en todo el cuerpo**, no sólo arriba:
# `budget_tokens` viaja adentro de `thinking` y ahí no lo ve una lectura de primer nivel.
PROHIBIDOS = ("budget_tokens", "temperature", "top_p", "top_k")

# Los cinco niveles que acepta `output_config.effort`.
NIVELES_DE_EFFORT = ("low", "medium", "high", "xhigh", "max")

# El turno de sistema y el de usuario con los que esta suite llama al modelo. No salen de
# `agente/prompt.py`: lo que se mide es el pedido que arma `agente/modelo.py`, no el texto que
# hornea el prefijo estático, que ya tiene su propia verificación en el paso 5.
SISTEMA = "Sos el cerrador de prueba. Este texto no se afirma en ningún lado."
MENSAJES = [{"role": "user", "content": "¿Cuánto sale el curso? Me parece caro."}]


# ─────────────────────────────────────────────────────────────────────────────
# Los pines, leídos del disco
# ─────────────────────────────────────────────────────────────────────────────


def _pines() -> str:
    return PINES.read_text(encoding="utf-8") if PINES.is_file() else ""


def _modelo_de_pines() -> str:
    """`MODELO=` de `PINES.md`, que es la fuente única del kit. Invariante 6."""
    hallado = re.search(r"^MODELO=(\S+)", _pines(), re.MULTILINE)
    return hallado.group(1) if hallado else ""


def _effort_de_pines() -> str:
    """El nivel que `PINES.md` → Modelo escribe al lado de `output_config`."""
    hallado = re.search(r'"effort"\s*:\s*"(\w+)"', _pines())
    return hallado.group(1) if hallado else ""


# ─────────────────────────────────────────────────────────────────────────────
# Qué falta para correr
# ─────────────────────────────────────────────────────────────────────────────


def _motivo_sin_modelo() -> str:
    """Por qué no se puede llamar al modelo, o cadena vacía si se puede."""
    if not (RAIZ / MODULO).is_file():
        return (
            f"falta el build: no existe {MODULO}. `{FABRICA}()` la escribe "
            f"blueprint/30-generacion.md paso 5, y es la única llamada real al modelo del "
            f"árbol. Corré /armar-cerrador y volvé a esta suite."
        )
    try:
        importlib.import_module("anthropic")
    except ModuleNotFoundError as e:
        return (
            f"falta {e.name} en este intérprete. Es el SDK con el que se habla con el modelo y "
            f"está fijado en PINES.md. Corré esto con el `.venv` del proyecto."
        )
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# El doble: un transporte que graba el pedido y contesta con los bytes de disco
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Pedido:
    """La petición que salió hacia la API, tal como la vio el transporte."""

    metodo: str
    url: str
    ruta: str
    host: str
    cabeceras: dict[str, str]
    cuerpo: bytes

    @property
    def datos(self) -> dict:
        try:
            valor = json.loads(self.cuerpo)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return valor if isinstance(valor, dict) else {}


class ApiFalsa:
    """El transporte de httpx durante estas pruebas. Graba lo que sale y devuelve bytes de disco.

    Se enchufa por debajo de `httpx.HTTPTransport` y `httpx.AsyncHTTPTransport`, que es el único
    lugar por donde pasan las dos formas de llamar: el cliente que construye el SDK de anthropic
    por su cuenta, y el cliente único de `agente/http.py` si el build decidió postear a mano. No
    hace falta saber cuál eligió: los dos terminan acá y ninguno abre un socket.
    """

    def __init__(self) -> None:
        self.pedidos: list[Pedido] = []
        self.salida: dict | None = None  # para pisar la salida del fixture en una prueba

    # ── la interfaz de httpx ──────────────────────────────────────────────

    def handle_request(self, request):  # httpx.BaseTransport
        return self._resolver(request)

    async def handle_async_request(self, request):  # httpx.AsyncBaseTransport
        return self._resolver(request)

    async def aclose(self) -> None:
        return None

    def close(self) -> None:
        return None

    # Los mismos seis que `ProveedorFalso`, y por el mismo motivo, que ese archivo ya deja escrito:
    # un cliente de httpx **entra y sale del transporte**, no sólo le pasa peticiones. `async with
    # httpx.AsyncClient(transport=…)` le pide `__aenter__` y `__aexit__`, y `aclose()` del cliente
    # le pide `aclose()` al transporte. Medido en esta ronda contra las dos formas de escribir
    # `agente/http.py`, con este mismo archivo y sin estos métodos:
    #
    #   con `async with`   AttributeError: 'ApiFalsa' object has no attribute '__aenter__'
    #   sin `async with`   AttributeError: 'ApiFalsa' object has no attribute 'aclose'
    #
    # Los once nodos de este archivo en rojo por las dos, y las dos son formas correctas de
    # escribir el cliente único: la única que pasaba sin esto es la que se olvida de cerrarlo. Eso
    # se lee como un defecto del kit, no del build, y encima premia al build que gotea clientes.
    # Son los mismos que trae `httpx.AsyncBaseTransport`; no se hereda de ella para no cambiar lo
    # que este doble acepta el día que httpx le agregue un método.
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_) -> None:
        return None

    # ── lo que la suite mira ──────────────────────────────────────────────

    @property
    def al_modelo(self) -> list[Pedido]:
        """Los POST al endpoint de mensajes. Lo demás —si algún día lo hay— no es esta llamada."""
        return [p for p in self.pedidos if p.metodo == "POST" and p.ruta.endswith("/v1/messages")]

    @property
    def pedido(self) -> Pedido:
        pedidos = self.al_modelo
        assert pedidos, (
            f"`{FABRICA}()` no hizo ninguna petición a `/v1/messages`. Lo que sí salió: "
            f"{[f'{p.metodo} {p.url}' for p in self.pedidos] or 'nada'}. Si no salió nada, la "
            f"función devolvió un enlatado y no llamó al modelo, que es exactamente el estado "
            f"que esta prueba existe para atrapar."
        )
        return pedidos[-1]

    # ── el cuerpo ─────────────────────────────────────────────────────────

    def _resolver(self, request):
        cuerpo = request.read() or b""
        self.pedidos.append(
            Pedido(
                metodo=request.method.upper(),
                url=str(request.url),
                ruta=request.url.path,
                host=request.url.host,
                cabeceras={k.lower(): v for k, v in request.headers.items()},
                cuerpo=cuerpo,
            )
        )
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=self._respuesta(self.pedidos[-1]),
            request=request,
        )

    def _respuesta(self, pedido: Pedido) -> bytes:
        """Los bytes que contesta: el fixture que corresponde a la forma que pidió el build.

        Se elige por lo que el pedido declaró y no por una preferencia de esta suite. Un build que
        manda el esquema angosto como herramienta recibe la respuesta con `tool_use`; uno que lo
        manda por `output_config.format` recibe la del bloque de texto con el JSON adentro. Ver la
        cabecera de este archivo.
        """
        nombre = "modelo.tool-use.respuesta.json"
        if not _esquema_por_herramienta(pedido.datos) and _esquema_por_formato(pedido.datos):
            nombre = "modelo.salida-estructurada.respuesta.json"
        crudo = (FIXTURES / nombre).read_bytes()
        if self.salida is None:
            return crudo
        return _con_otra_salida(crudo, self.salida)


def _con_otra_salida(crudo: bytes, salida: dict) -> bytes:
    """Los mismos bytes con otra salida adentro, en el bloque donde de verdad viaja.

    Es el control positivo de la extracción: sin él, un build que devuelva la salida del fixture
    escrita a mano pasaría igual, y la prueba estaría comparando una constante contra sí misma.
    """
    documento = json.loads(crudo)
    for bloque in documento["content"]:
        if bloque.get("type") == "tool_use":
            bloque["input"] = salida
            return json.dumps(documento, ensure_ascii=False).encode("utf-8")
    for bloque in documento["content"]:
        if bloque.get("type") == "text" and bloque.get("text", "").lstrip().startswith("{"):
            bloque["text"] = json.dumps(salida, ensure_ascii=False)
            return json.dumps(documento, ensure_ascii=False).encode("utf-8")
    raise AssertionError(f"el fixture no trae ningún bloque con la salida adentro: {crudo!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Cómo viaja el esquema angosto, en las dos formas
# ─────────────────────────────────────────────────────────────────────────────


def _propiedades(nodo: Any) -> set[str]:
    esquema = nodo if isinstance(nodo, dict) else {}
    propiedades = esquema.get("properties")
    return set(propiedades) if isinstance(propiedades, dict) else set()


def _esquema_por_herramienta(cuerpo: dict) -> set[str]:
    """Las propiedades del `input_schema` de la herramienta que trae el esquema angosto."""
    for herramienta in cuerpo.get("tools") or []:
        if not isinstance(herramienta, dict):
            continue
        propiedades = _propiedades(herramienta.get("input_schema"))
        if propiedades & set(CAMPOS_WIRE):
            return propiedades
    return set()


def _esquema_por_formato(cuerpo: dict) -> set[str]:
    """Las propiedades de `output_config.format.schema`, que es la otra forma."""
    formato = (cuerpo.get("output_config") or {}).get("format")
    return _propiedades((formato or {}).get("schema"))


def _esquema_declarado(cuerpo: dict) -> set[str]:
    return _esquema_por_herramienta(cuerpo) | _esquema_por_formato(cuerpo)


def _valores(nodo: Any):
    """Cada `(clave, valor)` del cuerpo, a la profundidad que sea."""
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            yield clave, valor
            yield from _valores(valor)
    elif isinstance(nodo, list):
        for elemento in nodo:
            yield from _valores(elemento)


# ─────────────────────────────────────────────────────────────────────────────
# Llamar al modelo del build
# ─────────────────────────────────────────────────────────────────────────────


def _metodo_unico(modelo: Any):
    """El único método público de la clase, cuando el objeto no se puede llamar de frente."""
    publicos = [
        nombre
        for nombre, valor in inspect.getmembers(type(modelo), callable)
        if not nombre.startswith("_")
    ]
    return getattr(modelo, publicos[0]) if len(publicos) == 1 else None


def _resolver(resultado: Any) -> Any:
    return asyncio.run(resultado) if inspect.isawaitable(resultado) else resultado


def _invocar(modelo: Any) -> Any:
    """Le pide una vuelta al modelo, con la convención de `blueprint/30-generacion.md` paso 5.

    Se prueban las formas que dan el mismo objeto —con nombre y posicional— y, si el objeto no se
    puede llamar, su único método público. Si ninguna anda, revienta acá y con el motivo escrito:
    el nombre es una convención de esta suite, y si el build usa otro se cambia en este archivo y
    en ningún otro lado. Es lo mismo que hace `enchufar_transporte()` con `http.TRANSPORTE`.
    """
    intentos = []
    if callable(modelo):
        intentos += [
            lambda: modelo(sistema=SISTEMA, mensajes=MENSAJES),
            lambda: modelo(SISTEMA, MENSAJES),
        ]
    metodo = _metodo_unico(modelo)
    if metodo is not None:
        intentos += [
            lambda: metodo(sistema=SISTEMA, mensajes=MENSAJES),
            lambda: metodo(SISTEMA, MENSAJES),
        ]

    errores = []
    for intento in intentos:
        try:
            return _resolver(intento())
        except TypeError as e:
            errores.append(str(e))

    detalle = " · ".join(errores) or "el objeto no se puede llamar y no tiene un solo método público"
    raise AssertionError(
        f"no supe llamar al modelo que devuelve `{FABRICA}()`. La convención es "
        f"`modelo(sistema=…, mensajes=…)` y devuelve el dict de los once campos del esquema "
        f"angosto —o algo que se pueda esperar y devuelva eso—; la escribe "
        f"blueprint/30-generacion.md paso 5, y es la misma con la que `agente/ciclo.py` llama al "
        f"`StubModel` de las pruebas. Lo que se probó falló así: {detalle}"
    )


@pytest.fixture
def banco(monkeypatch):
    """El modelo del build, importado de cero, con el transporte doblado y una clave falsa.

    El entorno se pone **antes** de importar: `agente/ajustes.py` lee `.env` y el entorno una sola
    vez, al importarse. Una variable «que falta» se escribe como cadena vacía y no sacándola, por
    lo mismo que en `pruebas/test_panel.py`: `load_dotenv` completa lo que falta, así que sacarla
    la deja volver por la puerta de atrás y la prueba se pone roja por el `.env` de quien corre.
    """
    motivo = _motivo_sin_modelo()
    if motivo:
        pytest.skip(motivo)

    api = ApiFalsa()
    monkeypatch.setattr(
        httpx.HTTPTransport, "handle_request", lambda self, request: api.handle_request(request)
    )

    async def _async(self, request):
        return await api.handle_async_request(request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _async)

    monkeypatch.setenv("ANTHROPIC_API_KEY", CLAVE_DE_PRUEBA)
    monkeypatch.setenv("WHATSAPP_PROVIDER", "demo")
    olvidar_el_build()
    modulo = importlib.import_module("agente.modelo")

    # El cliente único también, si el build postea por ahí en vez de por el SDK. Los dos caminos
    # terminan en la misma grabadora, así que ninguna prueba de este archivo depende de cuál eligió.
    try:
        http = importlib.import_module("agente.http")
    except ModuleNotFoundError:
        pass
    else:
        if hasattr(http, "TRANSPORTE"):
            monkeypatch.setattr(http, "TRANSPORTE", api)

    fabrica = getattr(modulo, FABRICA, None)
    assert fabrica is not None, (
        f"{MODULO} no define `{FABRICA}()`. Es el nombre que busca `pruebas/simulador.py` con "
        f"`getattr(modelo, '{FABRICA}', None)`, y la falla es muda: el simulador se cae al stub y "
        f"la cabecera dice «modelo stub, sin ANTHROPIC_API_KEY» con la clave cargada. Lo escribe "
        f"blueprint/30-generacion.md paso 5."
    )

    api.modelo = fabrica()
    api.correr = lambda: _invocar(api.modelo)
    yield api
    olvidar_el_build()


@pytest.fixture(scope="session")
def ficha() -> dict:
    """`pruebas/fixtures/modelo.ficha.json`: qué hay que extraer de los bytes grabados."""
    return json.loads((FIXTURES / "modelo.ficha.json").read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# 1 · La llamada ocurre, y va a donde dice
# ─────────────────────────────────────────────────────────────────────────────


def test_la_fabrica_llama_a_la_api_una_sola_vez(banco) -> None:
    """Sin esto, todo lo que sigue pasa por vacío: un enlatado no hace ningún pedido."""
    banco.correr()

    assert len(banco.al_modelo) == 1, (
        f"`{FABRICA}()` hizo {len(banco.al_modelo)} pedidos a `/v1/messages` por una sola vuelta: "
        f"{[p.url for p in banco.al_modelo]}. Uno de más es un reintento escrito a mano encima "
        f"del que ya trae el SDK, y se paga dos veces en cada mensaje."
    )
    pedido = banco.pedido
    assert pedido.host == "api.anthropic.com", (
        f"el pedido salió a `{pedido.host}` y no a `api.anthropic.com`. El único destino que la "
        f"compuerta **no** marca como segundo camino de salida es la API de Anthropic; ver "
        f"blueprint/00-contrato.md § 12."
    )


def test_la_llamada_usa_la_clave_del_entorno_y_no_una_escrita_en_el_arbol(banco) -> None:
    """La credencial viaja, y es la que puso el entorno. Invariante 4 leído desde afuera."""
    banco.correr()
    cabeceras = banco.pedido.cabeceras

    assert any(CLAVE_DE_PRUEBA == v for v in cabeceras.values()), (
        f"el pedido no lleva la clave que puso el entorno. Las cabeceras que mandó: "
        f"{sorted(cabeceras)}. O el build escribió una clave adentro del árbol —y entonces está "
        f"en git—, o construye el cliente antes de leer `ANTHROPIC_API_KEY`. La clave sale de "
        f"`agente/ajustes.py` y de ningún otro lado."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2 · La forma del pedido
# ─────────────────────────────────────────────────────────────────────────────


def test_el_pedido_lleva_el_modelo_de_pines(banco) -> None:
    """Invariante 6: el modelo sale de `PINES.md` y de ningún otro lado.

    El chequeo 10 de la compuerta ya mira los literales del árbol. Esto mira otra cosa y por eso
    hace falta igual: qué modelo viaja **en el cuerpo del pedido**. Un literal correcto en un
    archivo que nadie llama, o un `MODELO` leído del entorno y pisado más abajo, pasan el grep y
    se caen acá.
    """
    banco.correr()
    esperado = _modelo_de_pines()
    assert esperado, "PINES.md no declara `MODELO=`. Es la fuente única del kit; ver invariante 6."

    dicho = banco.pedido.datos.get("model")
    assert dicho == esperado, (
        f"el pedido va con `model={dicho!r}` y PINES.md fija `{esperado}`. Un modelo de la "
        f"generación anterior se lee igual de bien y cuesta lo mismo escribirlo: el kit de "
        f"referencia quedó fijado en `claude-sonnet-4-6` y nadie lo notó hasta que alguien leyó "
        f"el archivo."
    )


def test_el_pedido_pide_thinking_adaptive(banco) -> None:
    """Explícito y no omitido, que es lo que dice `PINES.md` → Modelo.

    En Opus 5 adaptive es el default, así que omitirlo hoy no cambia nada y por eso nadie lo nota.
    Lo que cambia es mañana: con otro modelo de la familia, omitirlo significa **sin** thinking, y
    eso no da error, da respuestas peores.
    """
    banco.correr()
    thinking = banco.pedido.datos.get("thinking")

    assert isinstance(thinking, dict) and thinking.get("type") == "adaptive", (
        f"el pedido manda `thinking={thinking!r}`. Va `{{'type': 'adaptive'}}`, escrito y no "
        f"omitido. `{{'type': 'enabled', 'budget_tokens': N}}` devuelve 400 con este modelo, y "
        f"`{{'type': 'disabled'}}` sólo se acepta con `effort` en `high` o menos."
    )


def test_el_pedido_no_lleva_ninguno_de_los_cuatro_parametros_que_dan_400(banco) -> None:
    """Los cuatro, a la profundidad que sea: `budget_tokens` viaja adentro de `thinking`."""
    banco.correr()
    hallados = sorted(
        {clave for clave, _ in _valores(banco.pedido.datos) if clave in PROHIBIDOS}
    )

    assert not hallados, (
        f"el pedido manda {', '.join(hallados)}. Los cuatro —budget_tokens, temperature, top_p y "
        f"top_k— devuelven 400 con este modelo, y el 400 llega en el primer mensaje real, no en "
        f"la construcción. Ver PINES.md → Modelo. Se sacan, no se comentan al lado."
    )


def test_el_pedido_declara_el_effort_de_pines(banco) -> None:
    """`output_config.effort`, con el nivel que fija `PINES.md`.

    No lo mira ningún chequeo de la compuerta: `output_config` no es un literal de modelo ni uno
    de los cuatro que dan 400, así que un build que lo omita entero pasa en verde y corre en el
    nivel por default, que hoy es otro y cuesta otra cosa.
    """
    banco.correr()
    esperado = _effort_de_pines()
    assert esperado, "PINES.md → Modelo no declara ningún `effort`. Es la fuente única del kit."

    dicho = (banco.pedido.datos.get("output_config") or {}).get("effort")
    assert dicho == esperado, (
        f"el pedido va con `output_config.effort={dicho!r}` y PINES.md fija `{esperado!r}`. Los "
        f"cinco niveles son {', '.join(NIVELES_DE_EFFORT)}, el default de la API es `high`, y "
        f"omitirlo no da error: da otra factura."
    )


def test_el_pedido_lleva_el_esquema_angosto_entero(banco) -> None:
    """Los once campos de `esquema_wire()`, por la forma que el build haya elegido.

    Los dos caminos valen —la herramienta con `input_schema` y `output_config.format`—; lo que no
    vale es mandar el esquema recortado. Un campo que no se pide no vuelve, y el código que lo lee
    se cae después, en el paso que lo necesita.
    """
    banco.correr()
    declarado = _esquema_declarado(banco.pedido.datos)
    faltan = sorted(set(CAMPOS_WIRE) - declarado)

    assert not faltan, (
        f"el pedido no declara {len(faltan)} de los once campos del esquema angosto: "
        f"{', '.join(faltan)}. Lo que sí declaró: {', '.join(sorted(declarado)) or 'nada'}. El "
        f"esquema sale de `esquema_wire()` de `agente/wire_schema.py`, que se copia verbatim y no "
        f"se edita nunca; ver blueprint/30-generacion.md paso 5."
    )


def test_el_pedido_no_prefilla_el_turno_assistant(banco) -> None:
    """Un turno `assistant` al final devuelve 400 con este modelo, y es la forma vieja de forzar
    JSON. La reemplazan la herramienta y `output_config.format`, que es lo que ya se afirmó arriba.
    """
    banco.correr()
    mensajes = banco.pedido.datos.get("messages") or []
    assert mensajes, "el pedido va sin `messages`. La API lo rechaza con 400."

    ultimo = mensajes[-1].get("role") if isinstance(mensajes[-1], dict) else None
    assert ultimo != "assistant", (
        "el pedido termina con un turno `assistant`. Eso es un prefill, y con este modelo "
        "devuelve 400. Ver PINES.md → Modelo: «Tampoco prefill de turno assistant»."
    )


def test_el_pedido_acota_la_salida_con_max_tokens(banco) -> None:
    """`max_tokens` es obligatorio en la API: sin él el pedido no sale, sale 400."""
    banco.correr()
    tope = banco.pedido.datos.get("max_tokens")

    assert isinstance(tope, int) and tope > 0, (
        f"el pedido manda `max_tokens={tope!r}`. Es obligatorio y tiene que ser un entero "
        f"positivo. Con `thinking` prendido, ese tope cubre el pensamiento **y** la respuesta: si "
        f"queda corto, la salida se corta a la mitad y el esquema angosto no valida."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3 · La extracción: de dónde sale la salida
# ─────────────────────────────────────────────────────────────────────────────


def test_la_salida_sale_del_bloque_donde_de_verdad_esta(banco, ficha) -> None:
    """El nodo que cubre la orilla. `content[0]` es el bloque de pensamiento, no la respuesta.

    Los bytes grabados traen tres bloques y la salida está en el tercero. Una extracción que lea
    `content[0]`, o `content[0].text`, o el primer bloque de texto, devuelve el pensamiento vacío
    o la prosa suelta, y de ahí sale un ciclo que no valida contra el esquema angosto con un
    mensaje que no nombra al modelo.
    """
    salida = banco.correr()

    assert isinstance(salida, dict), (
        f"el modelo devolvió un {type(salida).__name__} y tiene que devolver el dict de los once "
        f"campos del esquema angosto. Lo que devolvió: {salida!r}. Devolver la respuesta del SDK "
        f"entera deja que cada paso se arregle solo con la forma de la API, que es justo lo que "
        f"`agente/modelo.py` existe para no repartir."
    )
    assert salida == ficha["salida"], (
        f"lo que devolvió el modelo no es lo que trae la respuesta grabada.\n"
        f"  esperado: {json.dumps(ficha['salida'], ensure_ascii=False, sort_keys=True)}\n"
        f"  devuelto: {json.dumps(salida, ensure_ascii=False, sort_keys=True, default=str)}\n"
        f"La salida vive en {ficha['respuestas']['tool_use']['donde_vive_la_salida']} cuando el "
        f"esquema viaja como herramienta, y en "
        f"{ficha['respuestas']['salida_estructurada']['donde_vive_la_salida']} cuando viaja por "
        f"`output_config.format`. En los dos casos el primer bloque es `thinking`, y en Opus 5 "
        f"viene con el texto vacío: leer `content[0]` no da error, da nada."
    )


def test_la_salida_sigue_a_la_respuesta_y_no_a_una_constante(banco, ficha) -> None:
    """El control positivo. Sin él, un `return` con la salida escrita a mano pasaría la de arriba.

    Se cambian dos campos adentro de los mismos bytes y se pide otra vuelta: lo que devuelve el
    modelo tiene que moverse con la respuesta.
    """
    otra = dict(ficha["salida"])
    otra["score"] = 91
    otra["texto"] = "Te reservo el jueves a las 10."
    banco.salida = otra

    salida = banco.correr()

    assert salida == otra, (
        f"la respuesta grabada trae `score=91` y otro texto, y el modelo devolvió "
        f"{json.dumps(salida, ensure_ascii=False, sort_keys=True, default=str)}. Si devuelve "
        f"siempre lo mismo, no está leyendo la respuesta: está devolviendo un enlatado, y el "
        f"agente contesta lo mismo a todo el mundo sin que nada se ponga rojo."
    )
