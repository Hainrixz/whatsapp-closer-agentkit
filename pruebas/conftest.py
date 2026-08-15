"""Lo compartido por la suite: el esquema del disco, los fixtures y el arnés del ciclo.

Dos reglas de este archivo.

**El esquema se lee del disco, siempre.** Una copia embebida en una prueba deriva junto con la
aserción que la usa: el día que alguien afloje `contratos/salida.schema.json`, la copia lo
acompaña y nadie se entera. Acá se lee el archivo, y si el archivo no está, la prueba falla.

**Nada de acá pide una credencial.** `pruebas/caso-01.md` lo dice explícito: el caso corre sin
`${WHATSAPP_TOKEN}`, sin `${GOOGLE_CALENDAR_ID}` y sin `${SUPABASE_URL}`, a propósito. Lo que se
mide es la llamada que el agente prepara, no la respuesta del servicio.

**Y nada de acá toca la red.** Lo afirma `sin_red`, más abajo, que es autouse y corre en todos los
nodos. Sin esa guarda, «esta suite no sale a internet» era una promesa escrita en una docstring: un
build que se olvide de doblar el transporte, o un proveedor que arme mal su destino, salía al mundo
real desde una corrida de pruebas y lo único que se veía era una prueba lenta.

**El proveedor no se toca acá.** Esta suite corre con el que haya en el entorno, que es el que el
kit manda poner —`demo`, `blueprint/20-entrevista.md` paso 4— y en verde con ése. Poner otro desde
acá taparía el defecto en vez de arreglarlo: la corrida diría «154 passed» sobre una configuración
que no es la de nadie.

**Y la suite entera corre parada en el instante del corpus.** El reloj del ciclo es el de la
máquina —`blueprint/40-pruebas.md` paso 2 lo decide y dice por qué—, así que un fixture fechado en
marzo de 2026 envejece: leído en agosto, la ventana de 24 horas está cerrada y el turno que el caso
existe para probar no puede salir. La respuesta del kit es `freeze_time`, abajo, y no fechas
relativas adentro de los fixtures. Los fixtures se quedan como están en el disco.
"""

from __future__ import annotations

import json
import socket
from datetime import datetime

import pytest

from pruebas.proveedor_falso import (
    RAIZ,
    ProveedorFalso,
    SinAgente,
    StubModel,
    cargar,
    correr_turnos,
)

ESQUEMA_SALIDA = RAIZ / "contratos/salida.schema.json"
SALIDA_ESCRITA = RAIZ / "pruebas/salida-caso-01.json"


def instante_del_corpus() -> datetime:
    """Cuándo pasó lo que cuentan los fixtures: el `recibido_en` del mensaje del caso 01.

    Sale del disco y no de un literal escrito acá. El corpus declara su propio instante en el
    único campo que ya lo declaraba —`mensaje.recibido_en`, el momento en que llegó el mensaje—, y
    todo lo demás está escrito alrededor: la `disponibilidad` del caso 01 es de ese mismo día por
    la tarde, y las ventanas de los cuatro historiales se cierran después. Si alguien vuelve a
    fechar el corpus, el reloj de la suite lo sigue solo.
    """
    return datetime.fromisoformat(cargar("caso-01.entrada.json")["mensaje"]["recibido_en"])


# ─────────────────────────────────────────────────────────────────────────────
# El reloj, parado donde el corpus dice que pasaron las cosas
# ─────────────────────────────────────────────────────────────────────────────


def cargar_pydantic_v1() -> None:
    """Trae `pydantic.v1` a `sys.modules` **antes** de que el reloj se congele.

    **Qué arregla.** Una ruta de FastAPI con cualquier parámetro anotado —`proveedor: str` del
    webhook, `limite: int = 50` de `/api/conversaciones`— hace que FastAPI llame a
    `create_model_field()`, que llama a `annotation_is_pydantic_v1()`, que hace
    `from pydantic import v1` la primera vez que se lo piden. La anotación de retorno llega al
    mismo lugar por el modelo de respuesta. Si ese import cae adentro del `freeze_time` de abajo,
    `datetime.date` ya es `freezegun.api.FakeDate`, cuya metaclase no es `type`, y
    `pydantic/v1/types.py` no puede declarar su `ConstrainedDate`:

        TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict)
        subclass of the metaclasses of all its bases
          pydantic/v1/types.py:1180  class ConstrainedDate(date, metaclass=ConstrainedNumberMeta)

    No revienta la ruta: revienta el `import` del módulo entero, así que se lleva puestos a
    `pruebas/test_panel.py`, `pruebas/test_idempotencia.py` y `pruebas/test_bandeja.py` de una
    vez. Sobre un build fiel al blueprint eran 31 nodos rojos, con una traza que no nombra ni a
    FastAPI ni a freezegun.

    **Por qué acá y no como regla de estilo en el blueprint.** La regla que había —«ninguna ruta
    lleva anotación de retorno»— no alcanza y además no es el disparador. Medido en esta máquina,
    con Python 3.14.6, fastapi 0.141.1, pydantic 2.13.4 y freezegun 1.5.5, declarando rutas
    adentro de un `freeze_time`:

        -> str · -> dict · x: str = None · x: int = 50 · id: int   TypeError: metaclass conflict
        sólo `request: Request` · sin ningún parámetro             ok
        con `pydantic.v1` cargado antes de congelar, todas         ok

    Importado acá, el módulo queda en `sys.modules` y el import perezoso de FastAPI no lo vuelve a
    ejecutar: las rutas se escriben como en cualquier otro proyecto. Ver
    `blueprint/35-panel-api.md` paso 1, que es donde está la misma medición del lado de quien
    construye.

    Sin pydantic en el intérprete no hay nada que precargar, y tampoco hay FastAPI que lo importe:
    se ignora, igual que la ausencia de freezegun.
    """
    try:
        import pydantic.v1  # noqa: F401
    except ModuleNotFoundError:
        pass


@pytest.fixture(scope="session", autouse=True)
def parado_en_el_instante_del_corpus():
    """Corre la sesión entera con el reloj en el instante del corpus.

    **Qué arregla.** El reloj del ciclo es el de la máquina: `correr_ciclo()` lo lee una vez y lo
    baja por parámetro, y `mensaje.recibido_en` es cuándo llegó el mensaje, no qué hora es. La
    decisión y el porqué están en `blueprint/40-pruebas.md` paso 2. La consecuencia cae acá: los
    fixtures están fechados el 2 de marzo de 2026 y la ventana de 24 horas se cuenta contra el
    reloj, así que leídos cualquier otro día están todos fuera de ventana. Un build correcto no
    manda nada, y todo lo que cuente envíos desde el ciclo se pone rojo por el almanaque.

    **Por qué congelar y no mover las fechas.** Las dos formas arreglan lo mismo. Congelar deja
    los fixtures byte por byte como están en el disco, que es lo que `pruebas/extraer_fixture.py`
    compara contra la prosa de `pruebas/caso-01.md` y `caso-02.md`: con fechas relativas adentro,
    el fixture y la prosa no pueden volver a decir lo mismo. Y deja el corpus legible como lo que
    es, la foto de un momento —el mensaje entra a las 03:41, los horarios libres son de ese mismo
    día a las 11:00— en vez de un archivo con la aritmética adentro.

    **Se para acá y no en cada prueba** para que también cubra a `salida_caso_01`, que es de
    sesión: una fixture de sesión se arma **antes** que cualquiera de función, así que un
    `freeze_time` por prueba la dejaría afuera, corriendo el ciclo con el reloj de hoy. Autouse de
    sesión se arma primero que todo lo demás, incluida ella.

    `real_asyncio=True` es lo que deja el reloj de asyncio real. Sin eso, `asyncio.run()` corre con
    un `time.monotonic()` congelado y cualquier espera con plazo —el arnés de los turnos, el
    cliente de prueba de FastAPI— no vence nunca: la suite no falla, se cuelga, y la compuerta la
    corta a los 120 segundos con `pruebas/colgadas`.

    Sin `freezegun` en el intérprete la sesión corre igual, con el reloj de la máquina, y quien lo
    dice es un nodo y no un `warning` que nadie lee:
    `pruebas/test_enviar.py::test_la_suite_corre_parada_en_el_instante_del_corpus` se pone rojo y
    trae el motivo adentro. Saltear la suite entera acá sería peor: los nodos que comparan fixtures
    contra fixtures no miran la hora, y son justo los que tienen que correr con el árbol sin
    construir.

    **Antes de congelar se carga `pydantic.v1`.** Es lo que deja declarar rutas con parámetros
    anotados adentro de la suite en vez de que el import del servidor reviente con un
    `TypeError: metaclass conflict`. El porqué y la medición están en `cargar_pydantic_v1()`, acá
    arriba. Va antes del `with` y no adentro: lo que importa es que el módulo esté cargado cuando
    el reloj todavía es el de la máquina.
    """
    try:
        from freezegun import freeze_time
    except ModuleNotFoundError:
        yield None
        return
    cargar_pydantic_v1()
    with freeze_time(instante_del_corpus(), real_asyncio=True) as reloj:
        yield reloj


# ─────────────────────────────────────────────────────────────────────────────
# La red, cerrada con llave
# ─────────────────────────────────────────────────────────────────────────────


class TocoLaRed(RuntimeError):
    """Un nodo de la suite intentó salir a la red. Trae a dónde iba."""


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Cierra la red para todos los nodos, y dice a dónde iban cuando alguno lo intenta.

    Se cortan los dos verbos que abren una conexión saliente —`socket.socket.connect` y
    `socket.create_connection`— y también la resolución de nombres, que es lo primero que hace
    httpx y lo que ya delata la intención antes de que haya un paquete en el cable.

    **Por qué es autouse y no una prueba suelta.** Lo que se afirma no es «una llamada no sale»:
    es que **ninguna** sale, en ninguno de los ciento y pico de nodos. Una prueba dedicada sólo
    puede afirmar lo primero, y el día que un proveedor arme mal su destino el rojo aparece en el
    nodo que lo hizo, con el host adentro del mensaje.

    Con `WHATSAPP_PROVIDER=demo` esto además cierra la única pregunta que queda abierta cuando
    `demo` pasa a salir por el cable: sale, sí, pero a `demo.invalid` y contra un transporte
    doblado. El TLD `.invalid` no resuelve ni acá ni en producción —RFC 2606—, así que la guarda
    y el destino dicen lo mismo por dos caminos distintos.

    Lo que **no** corta es nada de lo que pasa adentro del proceso, que es justamente donde vive
    el transporte doblado: `ProveedorFalso` contesta sin construir un socket, así que la suite
    entera sigue corriendo igual de rápido con la red cerrada.
    """

    def _prohibido(a_donde) -> TocoLaRed:
        return TocoLaRed(
            f"esta prueba intentó salir a la red, a {a_donde}. La suite corre sin credenciales y "
            f"sin red: lo que sale del agente lo tiene que ver `ProveedorFalso`, enchufado abajo "
            f"del cliente único de `agente/http.py`. Si esto aparece con `WHATSAPP_PROVIDER=demo`, "
            f"el destino de `demo` dejó de ser `demo.invalid`; ver blueprint/31-proveedores.md, "
            f"pasos 1 y 3. Si aparece en otro nodo, falta doblar el transporte: "
            f"`enchufar_transporte()` en pruebas/proveedor_falso.py."
        )

    def _connect(self, direccion, *a, **kw):
        raise _prohibido(direccion)

    def _create_connection(direccion, *a, **kw):
        raise _prohibido(direccion)

    def _getaddrinfo(host, puerto, *a, **kw):
        raise _prohibido(f"{host}:{puerto}")

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect)
    monkeypatch.setattr(socket, "create_connection", _create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)


# ─────────────────────────────────────────────────────────────────────────────
# El contrato, leído del disco
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def esquema_salida() -> dict:
    """`contratos/salida.schema.json`, tal como está en el árbol."""
    assert ESQUEMA_SALIDA.is_file(), (
        f"falta {ESQUEMA_SALIDA.relative_to(RAIZ)}. Sin el esquema no hay contrato que "
        f"verificar, y una suite en verde sin él no significa nada."
    )
    return json.loads(ESQUEMA_SALIDA.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def validar(esquema_salida: dict):
    """Devuelve una función que valida un documento y lista los errores, en castellano llano.

    Se usa `Draft202012Validator` pelado, igual que el driver de `scripts/auditar.py`. Sin
    verificador de formatos: el auditor tampoco lo usa, y dos validadores con reglas distintas
    dan dos veredictos distintos sobre el mismo archivo.
    """
    jsonschema = pytest.importorskip(
        "jsonschema",
        reason=(
            "falta jsonschema en este intérprete. Sin él el contrato de los seis pasos no "
            "tiene validador y «todo verde» no se distingue de «no se validó nada». Corré "
            "esto con el `.venv` del proyecto."
        ),
    )
    validador = jsonschema.Draft202012Validator(esquema_salida)

    def _validar(documento: dict) -> list[str]:
        errores = []
        for e in validador.iter_errors(documento):
            ruta = "/".join(str(p) for p in e.absolute_path) or "#"
            errores.append(f"{ruta}: {e.message}")
        return errores

    return _validar


# ─────────────────────────────────────────────────────────────────────────────
# Las entradas
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def entrada_caso_01() -> dict:
    """La entrada del camino feliz, del fixture y nunca de un literal pegado en la prueba."""
    return cargar("caso-01.entrada.json")


@pytest.fixture
def transporte() -> ProveedorFalso:
    return ProveedorFalso()


# ─────────────────────────────────────────────────────────────────────────────
# El arnés del ciclo
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def correr():
    """Corre uno o más turnos y devuelve `(salidas, transporte)`.

    Saltea con el motivo escrito mientras `agente/` no exista. Un salteo con motivo no es un
    aprobado: se lee con `pytest -rs` y dice qué falta construir.
    """

    def _correr(
        entradas: list[dict],
        *,
        modelo: StubModel | None = None,
        transporte: ProveedorFalso | None = None,
        historial: dict | None = None,
    ):
        try:
            return correr_turnos(
                entradas, modelo=modelo, transporte=transporte, historial=historial
            )
        except SinAgente as e:
            pytest.skip(str(e))

    return _correr


@pytest.fixture(scope="session")
def salida_caso_01() -> dict:
    """La salida del camino feliz, corrida una sola vez para las nueve aserciones.

    Se escribe en `pruebas/salida-caso-01.json`. De ahí la levanta el chequeo 16 `contrato` de
    la compuerta, que la valida contra el esquema y además exige los seis pasos en orden.
    """
    try:
        salidas, _ = correr_turnos([cargar("caso-01.entrada.json")], modelo=StubModel.canonica())
    except SinAgente as e:
        pytest.skip(str(e))
    salida = salidas[0]
    SALIDA_ESCRITA.write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return salida
