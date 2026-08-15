"""La bandeja: la fila del pendiente, aprobar, rechazar, y el id que no existe.

**En el modo por defecto del kit, éste es el único camino por el que un borrador se convierte en
un mensaje a un cliente.** `blueprint/00-contrato.md` § 3 lo dice en una línea:
`POST /api/pendientes/{id}/aprobar` «vuelve a correr el paso con `confirmado: true`». Todo lo que
el paso 3 redacta en `borrador` sale por acá o no sale.

Y hasta esta ronda no lo miraba nadie. Lo que había era esto, y las dos cosas juntas:

| Lo que existía | Qué dejaba pasar |
|---|---|
| el chequeo 22 `rutas-del-contrato` de `scripts/auditar.py` | que las tres rutas estén **montadas**. Un handler que devuelve 404 siempre las tiene montadas igual |
| `pruebas/test_panel.py` | que las tres pidan token, y que `pagina()` escape una lista de pendientes **fabricada a mano** en la propia prueba |

Ninguna fila de `pendientes` se escribe en ningún nodo de la suite, así que **un build donde nada
escribe esa tabla pasa entero**: `/api/pendientes` devuelve `[]` porque no hay nada, aprobar
devuelve 404 para todo id porque no hay nada que aprobar, y las dos respuestas se leen como
correctas. El agente redacta, guarda en ningún lado, y quien opera abre la bandeja vacía todos los
días sin que una sola aserción se ponga roja.

## Las cinco cosas que se afirman, cada una en las dos direcciones

1. **Un turno en `borrador` escribe la fila.** Y la fila es la de **este** turno: el `texto` es el
   que quedó en `respuesta.texto` de esta salida y el `contacto_id` es el de este mensaje. Contra
   eso una lista enlatada no puede acertar. La otra dirección corre en la misma prueba: mientras la
   fila está pendiente, **nada salió al cable**.
2. **Aprobar manda, una vez.** Sale exactamente un mensaje más, por el endpoint de mensajería del
   proveedor y con la `Idempotency-Key` sacada del contenido, que es la huella de `enviar()`: el
   panel no manda, vuelve a correr el paso. La otra dirección es la misma prueba con la otra acción:
   **rechazar no manda nada**.
3. **Resolver dos veces no manda dos veces.** El segundo `POST` devuelve 409 con `ya_resuelto` y la
   cuenta de envíos no se mueve. Se prueba también en el cruce —rechazar y después aprobar—, que es
   la misma compuerta (`update … where estado = 'pendiente'`) por el lado que más duele: un borrador
   que alguien frenó no puede salir después por un segundo clic.
4. **Un id que no existe da 404 y no 500.** Con su control positivo pegado al lado, que es lo único
   que separa un 404 honesto de un build que contesta 404 a todo porque nunca tuvo un pendiente: el
   id que **sí** existe, en la misma corrida, contesta 200.
5. **Las tres rutas son las que ya conoce la compuerta.** Ese nodo corre sin build y sin red, y es
   lo que impide que este archivo se lea verde contra otras rutas si alguien mueve la tabla.

## Cómo corre esto, y por qué el ciclo y la API ven la misma base

El turno se corre con `correr_turnos()` —el arnés de `pruebas/proveedor_falso.py`, con la entrada
del caso 01 y `StubModel` inyectado— y la bandeja se pide con el `TestClient` sobre
`agente/servidor.py`. Los dos leen la misma base porque `armar_deps()` deja su engine como **el
motor en curso de `agente/base.py`**, que es el punto 2 de `blueprint/40-pruebas.md` paso 2 y está
escrito ahí para esto mismo. Medido en esta máquina: un engine `sqlite+aiosqlite://` con
`StaticPool` sobrevive a otro `asyncio.run` y al hilo con su propio bucle que levanta el
`TestClient`, así que el cruce no pierde las filas.

El `TestClient` se construye sin `with`, igual que en `pruebas/test_panel.py`: las rutas del panel
leen la base por `agente/base.py` y no pueden depender de que haya corrido el `lifespan`.

## El modelo se dobla, porque aprobar lo llama

Aprobar vuelve a correr el paso, y el paso llama al modelo —`blueprint/35-panel-api.md` paso 6 lo
dice en su «Si falla»—. Ese camino no recibe ningún `StubModel`: construye el de producción. Así
que el transporte de httpx se dobla por debajo, igual que en `pruebas/test_modelo.py`, y contesta
con los bytes grabados de `pruebas/fixtures/modelo.*.respuesta.json` **con la salida de
`StubModel.canonica()` adentro**. Es la misma salida que ve el turno de `borrador`, y por eso el
texto del borrador y el que sale al aprobar son el mismo texto: si no lo fueran, la comparación de
la prueba 2 mediría el fixture y no el build.

## Nada de acá pide una credencial ni toca la red

`PANEL_TOKEN` y `ANTHROPIC_API_KEY` son constantes inventadas de este archivo, con `prueba` adentro,
que no abren nada en ningún lado. Ninguna sale del proceso: el transporte está doblado por debajo y
la guarda `sin_red` de `pruebas/conftest.py` sigue puesta y no se toca.

**El salteo no va a nivel de módulo.** El nodo de las rutas mira el disco y corre con el árbol sin
construir. Los demás piden el build por la fixture `banco`, que saltea con el motivo escrito, una
prueba a la vez.
"""

from __future__ import annotations

import ast
import importlib
import json
import sys
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from pruebas.proveedor_falso import (
    FIXTURES,
    RAIZ,
    Llamada,
    ProveedorFalso,
    SinAgente,
    StubModel,
    cargar,
    con,
    correr_turnos,
    enchufar_transporte,
    huella,
    motivo_sin_ciclo,
    motivo_sin_servidor,
    olvidar_el_build,
    paso,
)

# ─────────────────────────────────────────────────────────────────────────────
# Las tres superficies, con el nombre que va a salir impreso cuando una se rompa
# ─────────────────────────────────────────────────────────────────────────────

FILA = "la fila del pendiente que sí se escribe"
APROBAR = "el borrador que sí sale al aprobarlo"
CIERRE = "el pendiente que se resuelve una sola vez"

DONDE = {
    FILA: (
        "el paso que redacta y `agente/base.py`; la fila la escribe el paso, no el panel: "
        "ver blueprint/60-bandeja.md paso 2"
    ),
    APROBAR: (
        "`panel/panel.py`, la ruta de aprobar; ver blueprint/35-panel-api.md paso 6. El que "
        "manda sigue siendo el único `enviar()` de `agente/enviar.py`"
    ),
    CIERRE: (
        "`panel/panel.py`, el `update … where estado = 'pendiente'` de aprobar y rechazar; "
        "ver blueprint/35-panel-api.md paso 6"
    ),
}


def roto(superficie: str, detalle: str) -> str:
    """El mensaje de un fallo. Nombra la superficie, no «la bandeja»."""
    return f"\nHUECO · {superficie}\n{detalle}\nSe arregla en {DONDE[superficie]}."


# ─────────────────────────────────────────────────────────────────────────────
# Lo que este archivo da por fijo
# ─────────────────────────────────────────────────────────────────────────────

PANEL = "panel/panel.py"
AUDITOR = RAIZ / "scripts/auditar.py"

# Las tres filas de la tabla de `blueprint/00-contrato.md` § 3 que son la bandeja, con el nombre
# del parámetro borrado: `{id}` o `{pendiente_id}` es la misma ruta. Que sigan siendo éstas lo
# afirma el primer nodo, contra `RUTAS_DEL_CONTRATO` de `scripts/auditar.py`.
RUTAS_DE_LA_BANDEJA = (
    ("GET", "/api/pendientes"),
    ("POST", "/api/pendientes/{}/aprobar"),
    ("POST", "/api/pendientes/{}/rechazar"),
)

# El token tiene más de 32 caracteres a propósito: `exigir_token` devuelve 503 por debajo de eso,
# y un 503 acá se leería como «la bandeja no contesta» en vez de como el token mal puesto.
TOKEN = "token-de-prueba-de-la-bandeja-" + "a" * 24

# No tiene la forma de una clave de Anthropic, y es por lo mismo que en `pruebas/test_modelo.py`:
# el chequeo 08 `secretos` de la compuerta busca ese prefijo en todo el árbol, y una clave de
# mentira con la forma de una de verdad enseña a ignorar el único hallazgo que avisa cuando alguien
# pega la buena. El SDK no valida el formato: le alcanza con que no esté vacía.
CLAVE_DEL_MODELO = "clave-de-prueba-sin-credencial-no-usar-en-produccion"

# Un id que no existe en ninguna base recién creada. Va numérico a propósito: con `{id}: int` en la
# ruta, un id que no es un número lo rebota FastAPI con 422 antes de llegar al handler, y eso no
# dice nada del 404 que esta prueba viene a mirar.
ID_QUE_NO_EXISTE = 987654321

# Lo mínimo que trae cada fila de `GET /api/pendientes`. Es la forma que `pruebas/test_panel.py` le
# pone enfrente a `pagina()` —«con la forma exacta en que los devuelven las rutas de `/api/`»— y la
# que fija `blueprint/35-panel-api.md` paso 6. Se pide que estén, no que sean las únicas: con el
# borrador va su panel de razonamiento, y eso son más claves.
CAMPOS_DEL_PENDIENTE = ("id", "paso", "estado", "contacto_id", "texto")

MOTIVO_DEL_RECHAZO = "eso no lo damos en agosto"

# El contacto del turno, leído del fixture y no escrito acá: es la clave por la que la fila de la
# bandeja se ata a este turno y no a una lista enlatada. Se lee de `mensaje.contacto_id`, que es la
# entrada, y no de `contacto.id` de la salida, que es lo que el build acaba de escribir.
CONTACTO = cargar("caso-01.entrada.json")["mensaje"]["contacto_id"]

# Un pedazo del texto que redacta `StubModel.canonica()`, para reconocerlo adentro del cuerpo que
# vio el transporte. Va sin tildes a propósito: el cuerpo viaja como JSON y las tildes salen
# escapadas —«ó» se escribe `ó`—, así que una marca con tilde no se encuentra adentro de
# `Llamada.texto` aunque haya salido perfecta. Es la misma regla de `pruebas/test_enviar.py`.
MARCA_DEL_MODELO = "12000 MXN"

# La salida que contesta el modelo doblado. Es la misma que ve el turno de `borrador`, así que el
# texto del borrador y el que sale al aprobar tienen que coincidir.
SALIDA_DEL_MODELO = StubModel.canonica().salida

HOST_MODELO = "api.anthropic.com"


# ─────────────────────────────────────────────────────────────────────────────
# El nodo que corre sin build: las rutas son las que ya conoce la compuerta
# ─────────────────────────────────────────────────────────────────────────────


def _constante_del_auditor(nombre: str) -> Any:
    """Una constante literal de `scripts/auditar.py`, leída por AST y sin importar el módulo.

    Se lee y no se importa por lo mismo que `pruebas/test_panel.py` cuenta `compare_digest` por
    nodos: acá no hace falta ejecutar nada, y ejecutar el auditor entero adentro de la suite le
    ataría el resultado a sus efectos de importación.
    """
    arbol = ast.parse(AUDITOR.read_text(encoding="utf-8"), filename=str(AUDITOR))
    for nodo in ast.walk(arbol):
        objetivo = None
        if isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            objetivo = nodo.target.id
        elif (
            isinstance(nodo, ast.Assign)
            and len(nodo.targets) == 1
            and isinstance(nodo.targets[0], ast.Name)
        ):
            objetivo = nodo.targets[0].id
        if objetivo == nombre:
            return ast.literal_eval(nodo.value)
    raise AssertionError(
        f"`scripts/auditar.py` no define `{nombre}` como un literal. Es de donde sale la tabla de "
        f"rutas que este archivo ejercita; si se movió, se mueve también acá."
    )


def test_las_tres_rutas_de_la_bandeja_son_las_que_ya_conoce_la_compuerta() -> None:
    """Corre sin build, y es lo que impide que este archivo pida rutas que no son las del contrato.

    El chequeo 22 `rutas-del-contrato` marca la ruta de más y la que falta contra
    `RUTAS_DEL_CONTRATO`. Este archivo pide tres de esas once por HTTP: si alguien las renombra en
    la tabla y no acá, las pruebas de abajo empezarían a medir un 404 de ruta inexistente y lo
    leerían como el 404 del pendiente que no existe, que es exactamente el defecto que vienen a
    atrapar.
    """
    del_contrato = set(_constante_del_auditor("RUTAS_DEL_CONTRATO"))
    faltan = [f"{metodo} {camino}" for metodo, camino in RUTAS_DE_LA_BANDEJA
              if (metodo, camino) not in del_contrato]

    assert not faltan, (
        f"{', '.join(faltan)} no está en `RUTAS_DEL_CONTRATO` de scripts/auditar.py. La tabla que "
        f"manda es la de blueprint/00-contrato.md § 3, y la escribe blueprint/35-panel-api.md: "
        f"las tres se mueven juntas o este archivo pide una ruta que nadie monta."
    )


# ─────────────────────────────────────────────────────────────────────────────
# El doble: el transporte de siempre, más el otro lado del cable del modelo
# ─────────────────────────────────────────────────────────────────────────────


def _con_la_salida(crudo: bytes, salida: dict) -> bytes:
    """Los bytes grabados de la respuesta del modelo, con esta salida adentro.

    Se mete en el bloque donde de verdad viaja —`tool_use` en una forma, el `text` con el JSON
    adentro en la otra— y nunca en el primero: los fixtures traen un bloque `thinking` primero a
    propósito, y un build que lea `content[0]` tiene que seguir rompiéndose.
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
    raise AssertionError(
        f"ningún bloque de {documento.get('id')!r} trae la salida adentro. Los fixtures de "
        f"pruebas/fixtures/modelo.*.respuesta.json se movieron; ver pruebas/test_modelo.py."
    )


class ModeloYTransporteFalsos(ProveedorFalso):
    """El transporte de `pruebas/proveedor_falso.py`, más el otro lado del cable del modelo.

    Hereda para no tener un segundo doble: `envios`, `avisos` y la separación por destino quedan
    como están, y acá abajo sólo se contesta lo que ese doble no conoce, que es la llamada a
    `api.anthropic.com/v1/messages` que hace el paso cuando la bandeja lo vuelve a correr.

    La forma de la respuesta la elige el pedido y no esta suite: un build que manda el esquema
    angosto como herramienta recibe el fixture con `tool_use`, y uno que lo manda por
    `output_config.format` recibe el del bloque de texto. Las dos son formas vigentes de la API y
    elegir una acá pondría en rojo a un build fiel que eligió la otra; ver `pruebas/test_modelo.py`.
    """

    def __init__(self) -> None:
        super().__init__()
        self.al_modelo: list[Llamada] = []

    def _servir(self, llamada: Llamada):
        if llamada.host != HOST_MODELO:
            return None
        self.al_modelo.append(llamada)
        cuerpo = llamada.datos if isinstance(llamada.datos, dict) else {}
        por_formato = (cuerpo.get("output_config") or {}).get("format")
        nombre = (
            "modelo.salida-estructurada.respuesta.json"
            if por_formato and not cuerpo.get("tools")
            else "modelo.tool-use.respuesta.json"
        )
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=_con_la_salida((FIXTURES / nombre).read_bytes(), SALIDA_DEL_MODELO),
        )

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
# El banco: el servidor, el transporte doblado y un turno en `borrador`
# ─────────────────────────────────────────────────────────────────────────────


def _olvidar() -> None:
    """Saca `agente*` y `panel*` de `sys.modules`, como hace `pruebas/test_panel.py`.

    `panel/panel.py` construye el `router` **al importarse** y `agente/ajustes.py` lee el entorno
    una sola vez, también al importarse. Un módulo cacheado deja el `PANEL_TOKEN` que puso otra
    prueba, y el rojo aparece en cualquier lado menos donde está la causa.
    """
    olvidar_el_build()
    for nombre in [m for m in sys.modules if m == "panel" or m.startswith("panel.")]:
        del sys.modules[nombre]


def _motivo_sin_bandeja() -> str:
    """Por qué no se puede ejercitar la bandeja, o cadena vacía si se puede."""
    for motivo in (motivo_sin_servidor(), motivo_sin_ciclo()):
        if motivo:
            return motivo
    if not (RAIZ / PANEL).is_file():
        return (
            f"falta el build: no existe {PANEL}. El router del panel y las tres rutas de la "
            f"bandeja las escribe blueprint/35-panel-api.md, pasos 4 y 6; la tabla entera está en "
            f"blueprint/00-contrato.md § 3."
        )
    return ""


@pytest.fixture
def banco(monkeypatch, tmp_path):
    """El servidor importado de cero, el transporte doblado, y un turno en `borrador` a pedido."""
    motivo = _motivo_sin_bandeja()
    if motivo:
        pytest.skip(motivo)

    doble = ModeloYTransporteFalsos()

    # Los dos transportes de httpx, por debajo. Es el único lugar por donde pasan las dos formas de
    # llamar: el cliente que construye el SDK de anthropic por su cuenta —que es el que usa el paso
    # cuando la bandeja lo vuelve a correr— y el cliente único de `agente/http.py`. Ninguno abre un
    # socket, así que la guarda `sin_red` de conftest sigue puesta.
    monkeypatch.setattr(
        httpx.HTTPTransport, "handle_request", lambda self, request: doble.handle_request(request)
    )

    async def _async(self, request):
        return await doble.handle_async_request(request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _async)

    # El entorno se pone **antes** de importar. Una variable que falta se escribe vacía y no se
    # saca, por lo mismo que en `pruebas/test_panel.py`: `load_dotenv` completa lo que falta, así
    # que sacarla la deja volver por la puerta de atrás y la prueba se pone roja por el `.env` de
    # quien corre.
    for nombre, valor in {
        "PANEL_TOKEN": TOKEN,
        "WHATSAPP_PROVIDER": "demo",
        "ANTHROPIC_API_KEY": CLAVE_DEL_MODELO,
        "DATABASE_URL": f"sqlite+aiosqlite:///{tmp_path}/wca.db",
    }.items():
        monkeypatch.setenv(nombre, valor)

    _olvidar()
    servidor = importlib.import_module("agente.servidor")
    panel = importlib.import_module("panel.panel")
    try:
        enchufar_transporte(doble, monkeypatch)
    except SinAgente as e:
        pytest.skip(str(e))

    from fastapi.testclient import TestClient

    # Sin `with`, igual que en `pruebas/test_panel.py`: las rutas del panel leen la base por
    # `agente/base.py` y no pueden depender de que haya corrido el `lifespan`.
    cliente = TestClient(servidor.app, headers={"Authorization": f"Bearer {TOKEN}"})

    def _turno(**cambios: Any) -> dict:
        """Un turno del caso 01 en `borrador`, con `StubModel` y este mismo transporte."""
        entrada = con(cargar("caso-01.entrada.json"), modo="borrador", confirmado=False, **cambios)
        try:
            salidas, _ = correr_turnos([entrada], modelo=StubModel.canonica(), transporte=doble)
        except SinAgente as e:
            pytest.skip(str(e))
        return salidas[0]

    yield SimpleNamespace(
        app=servidor.app, panel=panel, cliente=cliente, doble=doble, turno=_turno
    )
    _olvidar()


# ─────────────────────────────────────────────────────────────────────────────
# Lo que se le pide a la bandeja
# ─────────────────────────────────────────────────────────────────────────────


def pendientes(banco) -> list[dict]:
    """Lo que devuelve `GET /api/pendientes`, con la forma que fija el blueprint.

    Una lista JSON pelada, un objeto por borrador, igual que `/api/leads` del paso 5. Es la misma
    forma que `pruebas/test_panel.py` le pone enfrente a `pagina()` en `datos["pendientes"]`.
    """
    respuesta = banco.cliente.get("/api/pendientes")
    assert respuesta.status_code == 200, roto(
        FILA,
        f"`GET /api/pendientes` contestó {respuesta.status_code} con el token bueno puesto: "
        f"{respuesta.text[:300]!r}. Un 500 acá suele ser la tabla `pendientes` sin migrar; un 401 "
        f"o un 503 es la puerta y lo mira pruebas/test_panel.py.",
    )
    filas = respuesta.json()
    assert isinstance(filas, list), roto(
        FILA,
        f"`GET /api/pendientes` devolvió un {type(filas).__name__} y tiene que devolver una lista "
        f"JSON pelada, un objeto por borrador: {respuesta.text[:300]!r}. Es la misma forma de "
        f"`/api/leads` y la que espera `pagina(datos)` en `datos['pendientes']`; ver "
        f"blueprint/35-panel-api.md pasos 5, 6 y 8.",
    )
    return filas


def pendiente_del_paso(banco, salida: dict, n: int = 3) -> dict:
    """La fila que este turno dejó para el paso `n`. Es la aserción central de este archivo."""
    filas = pendientes(banco)
    delpaso = [f for f in filas if f.get("paso") == n and f.get("estado") == "pendiente"]

    assert delpaso, roto(
        FILA,
        f"el turno corrió en `borrador`, el paso {n} quedó en «{paso(salida, n)['estado']}» y "
        f"`GET /api/pendientes` no trae una sola fila de ese paso. Lo que trae es {filas}. "
        f"Nadie escribió la fila: el paso redacta, muestra y no guarda, así que la bandeja está "
        f"vacía y `POST /api/pendientes/{{id}}/aprobar` no tiene qué aprobar —404 para todo id, "
        f"que es la forma en que este hueco se lee como si estuviera bien—. La escribe el paso, "
        f"no el panel; ver blueprint/60-bandeja.md paso 2. Si la fila sí se está escribiendo, lo "
        f"otro que da este rojo es que la ruta y el ciclo estén leyendo dos bases: `armar_deps()` "
        f"tiene que dejar su engine como el motor en curso de `agente/base.py`, que es el punto 2 "
        f"de blueprint/40-pruebas.md paso 2.",
    )
    fila = delpaso[0]
    faltan = [c for c in CAMPOS_DEL_PENDIENTE if c not in fila]
    assert not faltan, roto(
        FILA,
        f"la fila del paso {n} no trae {faltan}: {fila}. Sin `id` no hay nada que aprobar, sin "
        f"`estado` no se sabe si ya se resolvió, y sin `texto` quien opera aprueba a ciegas.",
    )
    assert fila["contacto_id"] == CONTACTO, roto(
        FILA,
        f"la fila dice `contacto_id = {fila['contacto_id']!r}` y el turno fue de `{CONTACTO}`. "
        f"Una lista que no sigue al turno es una lista enlatada. Y la clave es `contacto_id` y "
        f"nunca el número: el teléfono puede venir nulo desde abril de 2026.",
    )
    return fila


def resolver(banco, id_pendiente, accion: str):
    """`aprobar` o `rechazar` sobre ese id. Devuelve la respuesta cruda, sin mirarla."""
    cuerpo = {"motivo": MOTIVO_DEL_RECHAZO} if accion == "rechazar" else None
    return banco.cliente.post(f"/api/pendientes/{id_pendiente}/{accion}", json=cuerpo)


# ─────────────────────────────────────────────────────────────────────────────
# 1 · Un turno en `borrador` escribe la fila, y mientras tanto no sale nada
# ─────────────────────────────────────────────────────────────────────────────


def test_un_turno_en_borrador_escribe_la_fila_y_no_manda_nada(banco) -> None:
    """Las dos mitades de la misma promesa del modo por defecto.

    El agente redactó y no mandó: eso es lo que promete `borrador`, y lo prueba media suite. Lo
    que no probaba nadie es la otra mitad, que es la que hace que esa promesa sirva de algo: **el
    borrador quedó guardado en algún lado donde se lo pueda ver y aprobar**. Sin la fila, «no
    mandó» y «se perdió» son la misma corrida.

    La fila se ata al turno por dos lados que una lista enlatada no puede acertar: el `texto` es el
    que quedó en `respuesta.texto` de esta salida, y el `contacto_id` es el de este mensaje.
    """
    salida = banco.turno()

    assert banco.doble.por_whatsapp == [], roto(
        FILA,
        f"el turno corrió en `borrador` y salió algo por WhatsApp igual: "
        f"{[(ll.ruta, ll.texto) for ll in banco.doble.por_whatsapp]}. En `borrador` los pasos 3, "
        f"4 y 5 redactan, muestran y esperan confirmación explícita.",
    )
    assert paso(salida, 3)["estado"] == "sin-confirmar", roto(
        FILA,
        f"en `borrador` el paso 3 quedó en «{paso(salida, 3)['estado']}» y tenía que quedar en "
        f"«sin-confirmar»: te está esperando en la bandeja.",
    )
    assert salida["respuesta"] and salida["respuesta"].get("texto"), roto(
        FILA,
        f"el paso 3 no dejó texto en `respuesta`: {salida.get('respuesta')}. Sin texto redactado "
        f"no hay borrador que guardar, y esta prueba mediría una bandeja vacía contra otra.",
    )

    fila = pendiente_del_paso(banco, salida, 3)

    assert fila["texto"] == salida["respuesta"]["texto"], roto(
        FILA,
        f"la fila guardó «{fila['texto']}» y el paso 3 redactó "
        f"«{salida['respuesta']['texto']}». Lo que se guarda es el borrador de este turno: si no "
        f"es el mismo texto, lo que quien opera va a leer en /bandeja no es lo que el agente "
        f"escribió, y va a aprobar una cosa creyendo que aprueba otra.",
    )
    assert fila["estado"] == "pendiente", roto(
        FILA,
        f"la fila nació con `estado = {fila['estado']!r}`. Un borrador sin confirmar nace "
        f"`pendiente`: es lo que mira el `update … where estado = 'pendiente'` de aprobar, y con "
        f"cualquier otro valor ese update no encuentra nada y aprobar no manda nunca.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2 · Aprobar manda una vez; rechazar no manda nada
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("accion", ["aprobar", "rechazar"])
def test_aprobar_manda_por_enviar_y_rechazar_no_manda_nada(banco, accion: str) -> None:
    """Las dos acciones sobre el mismo borrador, y lo único que cambia es cuál se pide.

    Sin la mitad de `aprobar`, un build donde la ruta no hace nada pasa la de `rechazar` sin haber
    mandado nunca un mensaje: «no salió nada» es exactamente lo que hace un handler vacío. Y sin la
    mitad de `rechazar`, nadie mira que frenar un borrador de verdad lo frene.

    **Aprobar no manda desde el panel.** Vuelve a correr el paso con `confirmado` en verdadero, y
    el que manda sigue siendo el único `enviar()`. La huella de haber pasado por ahí es la
    `Idempotency-Key`, que sale del contenido —conversación, paso y hash del texto— y que un `post`
    escrito adentro del handler del panel no lleva. **Invariante 2.**
    """
    salida = banco.turno()
    fila = pendiente_del_paso(banco, salida, 3)
    antes = len(banco.doble.envios)

    respuesta = resolver(banco, fila["id"], accion)
    assert respuesta.status_code == 200, roto(
        APROBAR,
        f"`POST /api/pendientes/{fila['id']}/{accion}` sobre un pendiente que existe contestó "
        f"{respuesta.status_code}: {respuesta.text[:300]!r}. Un 404 acá quiere decir que la ruta "
        f"no encuentra la fila que `GET /api/pendientes` acaba de devolver.",
    )
    cuerpo = respuesta.json()
    assert cuerpo.get("id") == fila["id"] and cuerpo.get("paso") == 3, roto(
        APROBAR,
        f"la respuesta de `{accion}` dice {cuerpo} y el pendiente era el {fila['id']} del paso 3. "
        f"La respuesta nombra el pendiente que se resolvió; ver blueprint/35-panel-api.md paso 6.",
    )

    resueltos = [f["id"] for f in pendientes(banco) if f.get("estado") == "pendiente"]
    assert fila["id"] not in resueltos, roto(
        CIERRE,
        f"después de `{accion}`, el pendiente {fila['id']} sigue en la lista como `pendiente`. "
        f"Quien opera lo vuelve a ver mañana y lo resuelve otra vez; con `aprobar` eso es el mismo "
        f"mensaje dos veces.",
    )

    if accion == "rechazar":
        assert cuerpo.get("estado") == "rechazado", roto(
            APROBAR,
            f"se rechazó y el estado quedó en {cuerpo.get('estado')!r}. Rechazar lo cierra con el "
            f"motivo, y ese estado es lo que después impide que un segundo clic lo apruebe.",
        )
        assert len(banco.doble.envios) == antes, roto(
            APROBAR,
            f"se rechazó el borrador y salieron {len(banco.doble.envios) - antes} mensaje(s) "
            f"igual: {[e.texto for e in banco.doble.envios[antes:]]}. Rechazar lo cierra con "
            f"motivo y no manda nada: es la única respuesta de la bandeja que no toca el cable.",
        )
        return

    assert cuerpo.get("estado") == "aprobado", roto(
        APROBAR, f"se aprobó y el estado quedó en {cuerpo.get('estado')!r}."
    )
    assert cuerpo.get("enviado") is True, roto(
        APROBAR,
        f"se aprobó y la respuesta dice `enviado = {cuerpo.get('enviado')!r}`. Ese campo es lo "
        f"único que le dice a quien acaba de aprobar si el mensaje salió o si `enviar()` se negó.",
    )

    salieron = banco.doble.envios[antes:]
    assert len(salieron) == 1, roto(
        APROBAR,
        f"aprobar un borrador dejó {len(salieron)} mensaje(s) al contacto y tenía que dejar uno: "
        f"{[e.texto for e in salieron]}. Con cero, la bandeja marcó el pendiente como aprobado y "
        f"no volvió a correr el paso: `enviado` está mintiendo y el cliente sigue sin respuesta.",
    )
    envio = salieron[0]
    assert MARCA_DEL_MODELO in envio.texto, roto(
        APROBAR,
        f"salió algo que no es el borrador que se aprobó: el cuerpo que vio el transporte es "
        f"«{envio.texto}» y no trae «{MARCA_DEL_MODELO}».",
    )
    assert envio.idempotency_key, roto(
        APROBAR,
        f"el mensaje salió sin `Idempotency-Key`: {dict(envio.cabeceras)}. `enviar()` la pone "
        f"siempre; que no esté quiere decir que este `post` no pasó por `enviar()`, o sea que el "
        f"panel abrió un segundo camino de salida —sin la ventana de 24 horas, sin el chequeo de "
        f"baneo y sin la regla de no escribir primero—. Lo que se pierde ahí no es una respuesta: "
        f"es el número de WhatsApp del negocio.",
    )
    assert huella(fila["texto"]) in envio.idempotency_key, roto(
        APROBAR,
        f"la `Idempotency-Key` es `{envio.idempotency_key}` y no contiene el sha256 del texto que "
        f"se aprobó. Sale del contenido —conversación, paso y hash del texto—: con un uuid nuevo "
        f"por intento no es idempotencia, es un contador, y el reintento del cliente HTTP manda el "
        f"mismo mensaje dos veces con dos claves distintas.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3 · Resolver dos veces no manda dos veces
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "primera",
    ["aprobar", "rechazar"],
    ids=["aprobar dos veces", "rechazar y después aprobar"],
)
def test_resolver_dos_veces_no_manda_dos_veces(banco, primera: str) -> None:
    """El segundo clic, que es el que llega entre el `select` y el `update` que no era condicional.

    Las dos entradas son la misma compuerta —`update … where estado = 'pendiente'`, y se decide por
    si actualizó y no por un `select` previo— vista por sus dos lados. El cruce es el que más
    duele: un borrador que alguien frenó a propósito no puede salir después porque otra persona
    apretó `va` en la misma pantalla sin recargar.

    Las dos direcciones están adentro: la primera llamada tiene que hacer lo suyo —200, y el envío
    que corresponda a esa acción— y la segunda no. Sin la primera mitad, un build que conteste 409
    a todo pasa esta prueba sin haber mandado nunca nada.
    """
    salida = banco.turno()
    fila = pendiente_del_paso(banco, salida, 3)

    una = resolver(banco, fila["id"], primera)
    assert una.status_code == 200, roto(
        CIERRE,
        f"la primera llamada a `{primera}` contestó {una.status_code}: {una.text[:300]!r}. Esta "
        f"prueba mide qué pasa con la segunda; sin una primera que funcione no mide nada.",
    )
    esperados = 1 if primera == "aprobar" else 0
    assert len(banco.doble.envios) == esperados, roto(
        CIERRE,
        f"después de `{primera}` salieron {len(banco.doble.envios)} mensaje(s) y tenían que salir "
        f"{esperados}: {[e.texto for e in banco.doble.envios]}.",
    )
    ya_salieron = len(banco.doble.envios)

    otra = resolver(banco, fila["id"], "aprobar")
    assert otra.status_code == 409, roto(
        CIERRE,
        f"el pendiente {fila['id']} ya estaba `{primera}do` y `aprobar` volvió a contestar "
        f"{otra.status_code}: {otra.text[:300]!r}. El pendiente resuelto se contesta 409: el "
        f"`update` es condicional y se decide por si actualizó, no por un `select` previo. Entre "
        f"esas dos líneas entra el segundo clic.",
    )
    assert "ya_resuelto" in otra.text, roto(
        CIERRE,
        f"la segunda llamada contestó 409 y el cuerpo no dice `ya_resuelto`: {otra.text[:300]!r}. "
        f"Ese es el motivo que la bandeja muestra para no dejar a quien apretó dos veces "
        f"preguntándose si el mensaje salió una o ninguna.",
    )
    assert len(banco.doble.envios) == ya_salieron, roto(
        CIERRE,
        f"la segunda llamada dejó {len(banco.doble.envios) - ya_salieron} mensaje(s) más al "
        f"contacto: {[e.texto for e in banco.doble.envios[ya_salieron:]]}. Recibir dos veces el "
        f"mismo mensaje es de las cosas que hacen que alguien bloquee un número, y con `rechazar` "
        f"primero es peor: sale un borrador que alguien había frenado a propósito.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4 · Un id que no existe da 404, y el que existe no
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("accion", ["aprobar", "rechazar"])
def test_un_id_que_no_existe_da_404_y_el_que_si_existe_no(banco, accion: str) -> None:
    """El 404 y su control positivo, que es lo único que lo distingue de un 404 para todo.

    **Éste es el nodo que le da sentido a los otros tres.** Un build donde nada escribe la tabla
    contesta 404 a cualquier id, y el 404 que este archivo viene a pedir se lee como si estuviera
    bien. La única forma de separar las dos cosas es pedir las dos en la misma corrida: el id
    inventado tiene que dar 404 y el que `GET /api/pendientes` acaba de devolver, no.

    Y 404, no 500. Una traza sin atrapar en una ruta que resuelve borradores deja a quien opera sin
    saber si el mensaje salió, y en el registro del proxy queda el cuerpo de la petición.
    """
    salida = banco.turno()
    fila = pendiente_del_paso(banco, salida, 3)

    inventado = resolver(banco, ID_QUE_NO_EXISTE, accion)
    assert inventado.status_code != 500, roto(
        CIERRE,
        f"`{accion}` sobre el id {ID_QUE_NO_EXISTE} reventó con 500: "
        f"{inventado.text[:300]!r}. Un pendiente que no está no es un error del servicio: es un "
        f"404. Con un 500, quien opera no sabe si el mensaje salió, y el cuerpo de la traza queda "
        f"en el registro del proxy con el texto del chat adentro.",
    )
    assert inventado.status_code == 404, roto(
        CIERRE,
        f"`{accion}` sobre el id {ID_QUE_NO_EXISTE} contestó {inventado.status_code} y tenía que "
        f"contestar 404: {inventado.text[:300]!r}. Un 200 es peor que un 500: la bandeja dice que "
        f"resolvió algo que no existe.",
    )
    assert banco.doble.envios == [], roto(
        CIERRE,
        f"un id que no existe dejó {len(banco.doble.envios)} mensaje(s) al contacto: "
        f"{[e.texto for e in banco.doble.envios]}.",
    )

    real = resolver(banco, fila["id"], accion)
    assert real.status_code == 200, roto(
        CIERRE,
        f"el pendiente {fila['id']} lo acaba de devolver `GET /api/pendientes` y `{accion}` "
        f"contestó {real.status_code}: {real.text[:300]!r}. Sin esta mitad, el 404 de arriba lo "
        f"pasa igual un build donde la tabla está vacía y la ruta contesta 404 a todo: ahí no hay "
        f"un id que no existe, hay una bandeja que no existe.",
    )
