"""La puerta del panel: `PANEL_TOKEN`, las ocho rutas que no se abren sin él, y `/salud`.

El defecto que este archivo existe para hacer fallar es una línea que falta:

    router = APIRouter()                    # ← sin dependencies=[Depends(exigir_token)]

Se lee bien. Arranca. Contesta. Y publica en la URL pública de Railway, desde el primer
despliegue, los teléfonos, los scores y los resúmenes del CRM de los clientes del negocio.
Medido sobre un build que estaba en verde, con esa sola línea recortada:

    159 passed · auditar: PASS · 0 errores · 0 avisos · 0 salteados
    GET /api/leads sin token → 200 [{"contacto_id":"bsu_…","numero":"5215500000000",…
    GET /panel      sin token → 200

Ni un nodo de la suite tocaba `/panel`, `/api/*` ni `exigir_token`, y el chequeo 14 de la
compuerta pedía que `panel/panel.py` existiera sin pedirle un solo símbolo. Es la pieza que
`blueprint/35-panel-api.md` describe con más énfasis —«el default abierto es el que nadie nota
hasta que ya pasó»— y era la única sin una aserción encima.

## Las cinco cosas que se afirman, y por qué la última es la que importa

1. **Sin token, 401.** En las ocho rutas, no en una elegida a mano.
2. **Con el token equivocado, 401.** Incluido el que es prefijo del bueno: `startswith` abre y
   `hmac.compare_digest` no.
3. **Con el token bueno, 200**, y por los tres lugares que `blueprint/00-contrato.md` § 3 manda
   leer: la cabecera, la cookie y el `?token=` de la query.
4. **La comparación es en tiempo constante, contada por AST.** `"compare_digest" in fuente` sigue
   en verde con el uso real reemplazado por `==`, porque la palabra vive en los comentarios; un
   nodo de llamada no lo puede fingir un comentario. Es lo mismo que hace `pruebas/test_firmas.py`
   con `agente/firmas.py`, un archivo más abajo.
5. **Ninguna ruta bajo `/api/` contesta sin pasar por `exigir_token`.** Ésta se hace preguntándole
   a la app **qué tiene montado**, y no leyendo una lista escrita acá: así atrapa al build que se
   olvida el router entero y también al que monta una ruta suelta con `@app.get("/api/…")`, que es
   el que una lista fija no vería nunca. Su contracara está en la misma prueba: `/salud` y
   `/webhook/{proveedor}` tienen que seguir contestando **sin** token, porque Railway no manda
   cabeceras y el despliegue se muere en el chequeo de salud.

Y una sexta que no es del panel pero vive en el mismo módulo y en el mismo blueprint:
`/salud` tiene que poder nombrar una **requerida** del proveedor configurado. Con
`faltan = [v for v in OPCIONALES …]` —sin sumar `requeridas`— la lista nunca puede nombrar a
`META_APP_SECRET`, y el «Tenés que ver» del paso 4 de `blueprint/50-despliegue.md` —«con el
proveedor en `meta`, `META_APP_SECRET` no puede estar en esa lista»— pasa **por vacío**: no está
en la lista porque la lista no la mira. Un servicio que no verifica una sola firma da verde.

Y una séptima, que es la otra mitad de la misma puerta: **lo que escribió un desconocido por
WhatsApp se escapa antes de entrar al HTML.** El paso 8 de `blueprint/35-panel-api.md` lo llama
«el camino más corto que existe para perder el panel entero» y lo deja verificado con un
`curl | grep` que no corre nadie; sacando el `html.escape` del panel, la suite daba `199 passed` y
el chequeo 21 `panel-cerrado` seguía en `[ok]`. Un `<script>` adentro de un resumen del CRM corre
en el navegador de quien lee la bandeja, y ahí vive la cookie del token: la puerta se abre desde
adentro, y ninguna de las seis de arriba lo ve.

## Nada de acá pide una credencial ni toca la red

`PANEL_TOKEN` acá es una constante inventada de este archivo, con `prueba` adentro, que no abre
nada en ningún lado. El `TestClient` de starlette habla con la app por ASGI y no construye un
socket: la guarda `sin_red` de `pruebas/conftest.py` sigue puesta y no se toca.
"""

from __future__ import annotations

import ast
import importlib
import sys
from types import SimpleNamespace

import pytest

from pruebas.proveedor_falso import RAIZ, motivo_sin_servidor, olvidar_el_build

# ─────────────────────────────────────────────────────────────────────────────
# El módulo del panel, y por qué hay que olvidarlo entre prueba y prueba
# ─────────────────────────────────────────────────────────────────────────────

PANEL = "panel/panel.py"

# Los dos tokens tienen el mismo largo a propósito. `exigir_token` rechaza por largo antes de
# comparar —menos de 32 caracteres es 503, no 401—, así que un token equivocado más corto se
# rechazaría por el largo y la prueba no diría nada sobre la comparación, que es lo que se afirma.
TOKEN = "token-de-prueba-del-panel-" + "a" * 24
OTRO_TOKEN = "token-de-prueba-del-panel-" + "b" * 24

# Las ocho de `blueprint/00-contrato.md` § 3 con «Token: sí», con el nombre del parámetro borrado:
# `{id}` o `{contacto_id}` es la misma ruta, y pedir el nombre exacto sería un rojo por una
# palabra. Lo que se compara es la forma del camino.
RUTAS_CON_TOKEN = {
    "/panel",
    "/api/conversaciones",
    "/api/conversaciones/{}",
    "/api/leads",
    "/api/pendientes",
    "/api/pendientes/{}/aprobar",
    "/api/pendientes/{}/rechazar",
    "/api/webhooks-salientes",
}

# Las dos que **no** llevan token, y no es un olvido: Railway no manda cabeceras y el alta de Meta
# la hace Meta. Si alguna de estas dos se cuela adentro del router, el despliegue se muere en el
# chequeo de salud o el alta del webhook no ocurre nunca.
RUTAS_SIN_TOKEN = {"/salud", "/webhook/{}"}

# Hasta dónde se baja buscando `exigir_token` adentro del árbol de dependencias de una ruta, y
# hasta dónde se desarma un router incluido adentro de otro. Es un tope y no un `while` por lo
# mismo que en `scripts/auditar.py`: una suite que cuelga es peor que cualquier rojo.
HONDO = 6


def _olvidar_el_panel() -> None:
    """Saca `agente*` y `panel*` de `sys.modules` para que el próximo import relea el entorno.

    `olvidar_el_build()` hace la mitad —`agente*`— y acá hace falta la otra: `panel/panel.py`
    construye el `router` **al importarse**, y `exigir_token` cuelga de ese objeto. Un módulo
    cacheado deja al `PANEL_TOKEN` que puso otra prueba, y el rojo aparece en cualquier lado menos
    donde está la causa.
    """
    olvidar_el_build()
    for nombre in [m for m in sys.modules if m == "panel" or m.startswith("panel.")]:
        del sys.modules[nombre]


@pytest.fixture(autouse=True)
def _build_limpio():
    """Cada nodo de este archivo importa el build desde cero y no le deja nada al que sigue."""
    _olvidar_el_panel()
    yield
    _olvidar_el_panel()


def _motivo_sin_panel() -> str:
    """Por qué no se puede levantar el panel, o cadena vacía si se puede."""
    motivo = motivo_sin_servidor()
    if motivo:
        return motivo
    if not (RAIZ / PANEL).is_file():
        return (
            f"falta el build: no existe {PANEL}. El router del panel, `exigir_token` y las ocho "
            f"rutas detrás del token los escribe blueprint/35-panel-api.md, paso 4; la tabla "
            f"entera está en blueprint/00-contrato.md § 3."
        )
    return ""


def _banco(monkeypatch, **entorno) -> SimpleNamespace:
    """La app importada de cero con este entorno, o un salteo con el motivo escrito.

    El entorno se pone **antes** de importar y el build se olvida en el medio: `agente/ajustes.py`
    lee `.env` y el entorno una sola vez, cuando se importa, y `panel/panel.py` arma el router
    también al importarse.

    Una variable «que falta» se escribe como cadena vacía y no sacándola del entorno. Son la misma
    cosa para el código —`/salud` pregunta `if not os.getenv(v)` y `exigir_token` compara contra
    `os.getenv(...) or ""`— y sólo la primera forma sobrevive a un `.env` en disco: `load_dotenv`
    no pisa lo que ya está en el entorno, pero sí completa lo que falta, así que sacar la variable
    la deja volver por la puerta de atrás y la prueba se pone roja por el `.env` de quien corre.
    """
    motivo = _motivo_sin_panel()
    if motivo:
        pytest.skip(motivo)
    for nombre, valor in {"PANEL_TOKEN": TOKEN, "WHATSAPP_PROVIDER": "demo", **entorno}.items():
        monkeypatch.setenv(nombre, valor)
    _olvidar_el_panel()
    servidor = importlib.import_module("agente.servidor")
    panel = importlib.import_module("panel.panel")
    from fastapi.testclient import TestClient

    # Las cookies se ponen sobre el cliente y no sobre la petición: por petición, starlette avisa
    # que lo va a sacar y que la persistencia entre pedidos es ambigua. Un cliente por pedido
    # además deja cada aserción sola: sin esto, un `/panel?token=…` que deja la cookie abriría la
    # ruta que se pide después «sin token» y la prueba pasaría por la puerta de atrás.
    return SimpleNamespace(
        app=servidor.app,
        servidor=servidor,
        panel=panel,
        cliente=lambda **kw: TestClient(servidor.app, **kw),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Qué hay montado: se le pregunta a la app, no a una lista
# ─────────────────────────────────────────────────────────────────────────────


def _rutas_montadas(objetos, hondo: int = 0) -> list:
    """Toda ruta montada en la app, con su camino final y sus dependencias ya resueltas.

    `app.routes` no alcanza y no es un detalle: con fastapi 0.141.1 y starlette 1.3.1
    —`PINES.md`— `include_router` no copia las rutas del router adentro de `app.routes`, mete
    **un** objeto `_IncludedRouter` que las envuelve, y ese objeto no tiene `.path`. Leyendo
    `app.routes` a secas, las ocho rutas del panel no existen y esta suite entera pasaría por
    vacío, que es exactamente el estado del que venimos. Ver `blueprint/00-contrato.md` § 3.

    `effective_candidates()` las devuelve con el prefijo del `include_router` ya aplicado y con
    las dependencias del router adentro de `dependant`, que es lo que hace que esto vea también al
    router incluido con `dependencies=` en el `include_router` en vez de en el `APIRouter`. No
    aplana los anidados: un router adentro de otro vuelve a salir como `_IncludedRouter`, y por eso
    esto es recursivo.

    Un objeto que no sea ninguna de las dos cosas revienta la prueba con su tipo adentro del
    mensaje. Es a propósito: lo que no se puede enumerar no se puede afirmar, y una prueba de
    seguridad que no encuentra rutas tiene que ponerse roja y no verde.
    """
    montadas = []
    for ruta in objetos:
        efectivas = getattr(ruta, "effective_candidates", None)
        if callable(efectivas):
            assert hondo < HONDO, (
                f"routers incluidos anidados más de {HONDO} veces. O hay un ciclo, o el panel "
                f"se armó de una forma que esta prueba no sabe leer."
            )
            montadas += _rutas_montadas(efectivas(), hondo + 1)
        elif hasattr(ruta, "path"):
            montadas.append(ruta)
        else:
            raise AssertionError(
                f"no sé enumerar un `{type(ruta).__name__}` montado en la app. Con los pines de "
                f"PINES.md son `APIRoute` o `_IncludedRouter`, y de los dos se saca el camino. Si "
                f"fastapi cambió de forma, se arregla acá: hasta que se arregle, ninguna de las "
                f"pruebas de la puerta del panel está mirando nada."
            )
    return montadas


def _forma(camino: str) -> str:
    """`/api/conversaciones/{contacto_id}` → `/api/conversaciones/{}`."""
    return "/".join("{}" if p.startswith("{") and p.endswith("}") else p
                    for p in camino.split("/"))


def _pide_token(camino: str) -> bool:
    return camino == "/panel" or camino.startswith(("/panel/", "/api"))


def _concreto(camino: str) -> str:
    """El camino con los parámetros llenos, para poder pedirlo de verdad."""
    return "/".join("1" if p.startswith("{") and p.endswith("}") else p
                    for p in camino.split("/"))


def _verbo(ruta) -> str:
    """Un método por el que pedir esta ruta. `HEAD` y `OPTIONS` no cuentan: los pone starlette.

    Una ruta sin `methods` —un websocket— cae en `GET`: no es el pedido que le corresponde, pero
    contesta con el código de la puerta igual, y lo que se mide acá es la puerta. Que reviente con
    un `AttributeError` en su lugar sería el rojo que no dice nada.
    """
    declarados = set(getattr(ruta, "methods", None) or {"GET"})
    metodos = sorted(declarados - {"HEAD", "OPTIONS"}) or sorted(declarados)
    return "GET" if "GET" in metodos else metodos[0]


def _cuelga_de(ruta, nombre: str, hondo: int = 0) -> bool:
    """Si `nombre` está en el árbol de dependencias de esta ruta, a la profundidad que sea."""
    if hondo >= HONDO:
        return False
    for dep in getattr(ruta.dependant, "dependencies", []):
        llamada = getattr(dep, "call", None)
        if getattr(llamada, "__name__", "") == nombre:
            return True
        if _cuelga_de(SimpleNamespace(dependant=dep), nombre, hondo + 1):
            return True
    return False


def _guardadas(app) -> list:
    return [r for r in _rutas_montadas(app.routes) if _pide_token(r.path)]


def _una_guardada(app) -> str:
    """Un camino concreto de los que piden token, para las pruebas que se conforman con uno.

    Con la lista vacía revienta acá y con el motivo escrito. Antes se llevaba un `min() arg is an
    empty sequence` desde adentro de otra aserción, que es el rojo que no dice nada: la causa es
    que el router del panel no está montado, y así se lee.
    """
    guardadas = _guardadas(app)
    assert guardadas, (
        "la app no tiene una sola ruta montada bajo `/api/` ni `/panel`. Falta el "
        "`app.include_router(panel_router)` de blueprint/35-panel-api.md, paso 1: el router puede "
        "estar perfecto y no contestar nada si nadie lo monta."
    )
    return _concreto(min(guardadas, key=lambda r: r.path).path)


# ─────────────────────────────────────────────────────────────────────────────
# Las ocho rutas están montadas, y las dos públicas también
# ─────────────────────────────────────────────────────────────────────────────


def test_las_ocho_rutas_detras_del_token_estan_montadas(monkeypatch) -> None:
    """Sin esto, todo lo que sigue pasa por vacío.

    Un bucle sobre cero rutas es verde, y verde por no haber mirado nada es el estado del que
    viene este archivo. La lista sale de la tabla de `blueprint/00-contrato.md` § 3.
    """
    banco = _banco(monkeypatch)
    montadas = {_forma(r.path) for r in _rutas_montadas(banco.app.routes)}

    faltan = sorted(RUTAS_CON_TOKEN - montadas)
    assert not faltan, (
        f"la app no tiene montada(s) {len(faltan)} de las ocho rutas del panel: "
        f"{', '.join(faltan)}. Lo que sí montó: {', '.join(sorted(montadas))}. La tabla está en "
        f"blueprint/00-contrato.md § 3 y la escribe blueprint/35-panel-api.md, pasos 5 a 8."
    )
    publicas = sorted(RUTAS_SIN_TOKEN - montadas)
    assert not publicas, (
        f"faltan las rutas públicas {', '.join(publicas)}. `/salud` es el chequeo de salud de "
        f"Railway y `/webhook/{{proveedor}}` es el alta del proveedor: sin ellas el despliegue no "
        f"arranca y el alta del webhook es un 404."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1 · Sin token, 401 · en todas
# ─────────────────────────────────────────────────────────────────────────────


def test_sin_token_ninguna_ruta_del_panel_contesta(monkeypatch) -> None:
    """La que más consecuencia tiene de todo el archivo, y se pide ruta por ruta.

    No se elige `/api/leads` a mano: se le pregunta a la app qué tiene montado bajo `/api/` y se
    pide **cada una** sin credencial. Así se cae también el build que deja una ruta suelta con
    `@app.get("/api/…")` mientras el router sigue protegido, que es el caso que una lista escrita
    a mano no vería nunca.
    """
    banco = _banco(monkeypatch)
    abiertas = []
    for ruta in _guardadas(banco.app):
        respuesta = banco.cliente().request(_verbo(ruta), _concreto(ruta.path))
        if respuesta.status_code != 401:
            abiertas.append(f"{_verbo(ruta)} {ruta.path} → {respuesta.status_code}")

    assert not abiertas, (
        "estas rutas contestan sin token: " + " · ".join(abiertas) + ". El panel queda en una URL "
        "pública de Railway desde el primer despliegue: lo que se publica ahí son los teléfonos, "
        "los scores y los resúmenes del CRM de los clientes del negocio. La dependencia va sobre "
        "el router entero —`APIRouter(dependencies=[Depends(exigir_token)])`— y nunca ruta por "
        "ruta; ver blueprint/35-panel-api.md, paso 4."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2 · Con el token equivocado, 401
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "equivocado, por_que",
    [
        (OTRO_TOKEN, "otro token del mismo largo"),
        (TOKEN[:-1], "el bueno sin el último carácter: `startswith` abriría, `compare_digest` no"),
        (TOKEN + "x", "el bueno con un carácter de más"),
        (TOKEN.upper(), "el bueno en mayúsculas, que es lo que abre si hay un `.lower()` de por medio"),
    ],
)
def test_el_token_equivocado_no_abre_nada(monkeypatch, equivocado: str, por_que: str) -> None:
    """Y por los tres lugares donde `exigir_token` lo lee, no sólo por la cabecera."""
    banco = _banco(monkeypatch)
    ruta = _una_guardada(banco.app)

    entradas = {
        "cabecera": ({"headers": {"Authorization": f"Bearer {equivocado}"}}, {}),
        "cookie": ({}, {"cookies": {"wca_panel": equivocado}}),
        "query": ({"params": {"token": equivocado}}, {}),
    }
    for donde, (como, del_cliente) in entradas.items():
        respuesta = banco.cliente(**del_cliente).get(ruta, **como)
        assert respuesta.status_code == 401, (
            f"`{ruta}` contestó {respuesta.status_code} con {por_que}, entrado por {donde}. Un "
            f"token que no es el token es 401 por los tres lugares. Si esto abre, la comparación "
            f"no es `hmac.compare_digest(esperado, dado)`: mirá si quedó un `startswith`, un "
            f"`in`, o un `.lower()` de por medio."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3 · Con el token bueno, 200 · por los tres lugares
# ─────────────────────────────────────────────────────────────────────────────


def test_el_token_bueno_abre_el_panel_por_los_tres_lugares(monkeypatch) -> None:
    """La cabecera, la cookie y el `?token=` de la query, en ese orden.

    El tercero no es una comodidad: el navegador entra la primera vez por `/panel?token=…` y sin
    esa rama ese primer ingreso da 401, la cookie no se llega a poner nunca y el panel no se abre
    ni una vez. Ver `blueprint/00-contrato.md` § 3, regla 3.
    """
    banco = _banco(monkeypatch)
    entradas = {
        "cabecera `Authorization: Bearer`": (
            {"headers": {"Authorization": f"Bearer {TOKEN}"}}, {}),
        "cookie `wca_panel`": ({}, {"cookies": {"wca_panel": TOKEN}}),
        "parámetro `?token=`": ({"params": {"token": TOKEN}}, {}),
    }
    for donde, (como, del_cliente) in entradas.items():
        respuesta = banco.cliente(**del_cliente).get("/panel", **como)
        assert respuesta.status_code == 200, (
            f"`/panel` con el token bueno entrado por la {donde} contestó "
            f"{respuesta.status_code}, y tiene que ser 200. Con 503 el `PANEL_TOKEN` no le llegó "
            f"al handler; con 401 ese lugar no se está leyendo. Son tres y el que falta casi "
            f"siempre es el de la query."
        )


def test_con_el_token_bueno_la_api_deja_de_dar_401(monkeypatch) -> None:
    """Que la puerta se abra en todas, y no sólo en la que se probó.

    Lo que se afirma acá es la **puerta**, no el handler: una ruta que consulta la base puede
    reventar en un árbol sin migrar, y eso no es un defecto de la puerta. Lo que no puede devolver
    es 401 ni 403 con el token bueno puesto.

    **Tolerar eso hay que pedirlo, y hasta esta ronda no estaba pedido.** El `TestClient` de
    starlette re-levanta la excepción del handler por default: un handler que revienta no llega a
    devolver 500, corta el pedido con la traza y este nodo se pone rojo por la base sin migrar. El
    párrafo de arriba decía que un 500 no es un defecto de la puerta e inducía a leer ese rojo como
    otra cosa; costó una corrida entera. `raise_server_exceptions=False` es lo que convierte esa
    excepción en el 500 que este nodo sí sabe ignorar.

    Va sobre este cliente y sobre ninguno más del archivo. Los otros nodos afirman códigos que la
    app devuelve de verdad —401, 503, 200—, y ahí tapar una excepción del handler sería cambiar un
    rojo honesto por un verde que no promete nada.
    """
    banco = _banco(monkeypatch)
    cerradas = []
    for ruta in _guardadas(banco.app):
        respuesta = banco.cliente(raise_server_exceptions=False).request(
            _verbo(ruta), _concreto(ruta.path), headers={"Authorization": f"Bearer {TOKEN}"}
        )
        if respuesta.status_code in (401, 403, 503):
            cerradas.append(f"{_verbo(ruta)} {ruta.path} → {respuesta.status_code}")

    assert not cerradas, (
        "con el token bueno estas rutas siguen cerradas: " + " · ".join(cerradas) + ". Un 503 es "
        "`PANEL_TOKEN` vacío o de menos de 32 caracteres del lado del servidor; un 401 con el "
        "token correcto suele ser la cabecera leída como `bearer` en minúscula, o un valor con un "
        "salto de línea pegado. Compará los largos antes de dudar del valor."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4 · La comparación, contada por AST y no por texto
# ─────────────────────────────────────────────────────────────────────────────


def _llamadas_a_compare_digest(arbol: ast.AST) -> list[ast.Call]:
    """Las llamadas a `hmac.compare_digest`, contadas como nodos y no como texto.

    Las dos formas de escribirla: `hmac.compare_digest(...)` con el módulo importado y
    `compare_digest(...)` con `from hmac import compare_digest`. Es la misma función que usa
    `pruebas/test_firmas.py` sobre `agente/firmas.py`, escrita igual a propósito: son dos archivos
    distintos con el mismo defecto posible, y la lectura tiene que ser la misma.
    """
    return [
        n
        for n in ast.walk(arbol)
        if isinstance(n, ast.Call)
        and (
            (
                isinstance(n.func, ast.Attribute)
                and n.func.attr == "compare_digest"
                and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "hmac"
            )
            or (isinstance(n.func, ast.Name) and n.func.id == "compare_digest")
        )
    ]


def _funcion(arbol: ast.AST, nombre: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for n in ast.walk(arbol):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == nombre:
            return n
    return None


def test_el_token_se_compara_en_tiempo_constante() -> None:
    """`==` sobre cadenas corta en el primer byte distinto, y ese tiempo filtra el token.

    Se cuenta por AST y no con `"compare_digest" in fuente`. La palabra aparece en la prosa de
    `blueprint/35-panel-api.md` y en cualquier comentario que explique por qué va, así que la
    búsqueda por texto sigue en verde con el uso real reemplazado por `==` y cero comparaciones en
    tiempo constante en el archivo. Medido: con `if esperado != dado:` en vez de
    `compare_digest`, la suite daba `159 passed` y la compuerta `PASS · 0/0/0`.

    Un nodo de llamada no lo puede fingir un comentario. Esta prueba no revisa el código: lo hace
    fallar.
    """
    motivo = _motivo_sin_panel()
    if motivo:
        pytest.skip(motivo)

    ruta = RAIZ / PANEL
    fuente = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(ruta))

    funcion = _funcion(arbol, "exigir_token")
    assert funcion is not None, (
        f"{PANEL} no define `exigir_token()`. Es la dependencia que cuelga del router entero y la "
        f"única puerta del panel; la escribe blueprint/35-panel-api.md, paso 4."
    )
    assert _llamadas_a_compare_digest(funcion), (
        f"en {PANEL}, `exigir_token()` compara el token sin `hmac.compare_digest`. `==` sobre "
        f"cadenas corta en el primer byte distinto: el tiempo de respuesta filtra cuántos "
        f"caracteres del principio adivinó quien está probando, y eso alcanza para reconstruir el "
        f"token byte por byte contra un servicio que contesta rápido. La palabra `compare_digest` "
        f"sigue apareciendo {fuente.count('compare_digest')} vez/veces en el archivo: lo que se "
        f"cuenta acá son nodos de llamada, no apariciones de texto."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5 · Ninguna ruta de /api/ cuelga de otra cosa que del router con la dependencia
# ─────────────────────────────────────────────────────────────────────────────


def test_toda_ruta_bajo_api_pasa_por_exigir_token(monkeypatch) -> None:
    """La estructural, que dice **por qué** está abierta y no sólo que lo está.

    La de arriba pide cada ruta y mira el código; ésta mira de qué cuelga cada una. Las dos hacen
    falta: la de arriba se cae con cualquier forma de abrir la puerta, y ésta nombra la causa
    —`@app.get("/api/…")` montado sobre la app, o un `include_router` sin la dependencia— en vez
    de dejar un 200 sin explicación.

    Y su contracara, en la misma prueba: `/salud` y `/webhook/{proveedor}` **no** pueden colgar de
    `exigir_token`. Es el arreglo apurado que se hace después de leer el rojo de arriba —meter todo
    adentro del router— y se paga en el despliegue: Railway no manda cabeceras, el chequeo de salud
    da 401 y el despliegue se muere sin decir por qué.
    """
    banco = _banco(monkeypatch)
    montadas = _rutas_montadas(banco.app.routes)
    assert montadas, "la app no tiene una sola ruta montada: no hay nada que afirmar acá"

    sueltas = [f"{_verbo(r)} {r.path}" for r in montadas
               if _pide_token(r.path) and not _cuelga_de(r, "exigir_token")]
    assert not sueltas, (
        "estas rutas están montadas sin `exigir_token` en su cadena de dependencias: "
        + " · ".join(sueltas) + ". Va sobre el router entero —`APIRouter(dependencies="
        "[Depends(exigir_token)])`— y nunca ruta por ruta, para que la que agregues mañana nazca "
        "protegida. Una ruta de `/api/` montada con `@app.get(...)` sobre la app queda fuera del "
        "router y por lo tanto fuera de la puerta, aunque el router esté bien."
    )

    coladas = [f"{_verbo(r)} {r.path}" for r in montadas
               if _forma(r.path) in RUTAS_SIN_TOKEN and _cuelga_de(r, "exigir_token")]
    assert not coladas, (
        "estas rutas públicas se colaron adentro del router del panel: " + " · ".join(coladas)
        + ". `/salud` es el chequeo de salud de Railway, que no manda cabeceras: adentro del "
        "router el despliegue se muere ahí. Y el GET de `/webhook/{proveedor}` es el alta de Meta, "
        "que la hace Meta y sin token. Ver blueprint/35-panel-api.md, paso 2."
    )


def test_el_token_vacio_cierra_el_panel_y_no_toca_salud(monkeypatch) -> None:
    """Vacío es 503, no «abierto». El default abierto es el que nadie nota hasta que ya pasó.

    Se prueba con la variable vacía y con una de menos de 32 caracteres, que es la que sale de
    inventar el valor a mano en vez de generarlo con `secrets.token_urlsafe(32)`.
    """
    for valor, cual in [("", "vacío"), ("corto-123", "de 9 caracteres")]:
        banco = _banco(monkeypatch, PANEL_TOKEN=valor)
        ruta = _una_guardada(banco.app)

        respuesta = banco.cliente().get(ruta)
        assert respuesta.status_code == 503, (
            f"con `PANEL_TOKEN` {cual}, `{ruta}` contestó {respuesta.status_code} y tiene que ser "
            f"503. Un 200 acá quiere decir que el panel está abierto para cualquiera que dé con "
            f"la URL, y con 401 nadie va a entender por qué el token correcto no entra. El piso "
            f"son 32 caracteres y el valor se genera: "
            f"`.venv/bin/python -c \"import secrets; print(secrets.token_urlsafe(32))\"`."
        )

        salud = banco.cliente().get("/salud")
        assert salud.status_code == 200, (
            f"con `PANEL_TOKEN` {cual}, `/salud` contestó {salud.status_code}. Nunca 503 y nunca "
            f"401: ese chequeo dice «el proceso atiende», no «está bien configurado». Railway mata "
            f"el despliegue con cualquier otra cosa, y con él el panel que te iba a decir qué falta."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6 · `/salud` puede nombrar una requerida del proveedor configurado
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "proveedor, requerida",
    [
        ("meta", "META_APP_SECRET"),
        ("meta", "WHATSAPP_TOKEN"),
        ("zernio", "ZERNIO_WEBHOOK_SECRET"),
        ("zernio", "ZERNIO_ACCOUNT_ID"),
    ],
)
def test_salud_nombra_la_requerida_del_proveedor_que_falta(
    monkeypatch, proveedor: str, requerida: str
) -> None:
    """El «Tenés que ver» de `blueprint/50-despliegue.md`, paso 4, dejando de pasar por vacío.

    Ese paso dice: «con el proveedor en `meta`, `META_APP_SECRET` no puede estar en esa lista».
    Con `faltan = [v for v in OPCIONALES if not os.getenv(v)]` —o sea sin sumar `requeridas`— el
    criterio se cumple **porque la lista nunca la mira**, y un servicio desplegado sin el App
    Secret cargado, que no verifica una sola firma y contesta 401 en todas las entregas, da verde.
    Medido: `159 passed` y `PASS · 0 errores · 0 avisos · 0 salteados`.

    Esta prueba es el control positivo que faltaba: con la variable fuera, el nombre **tiene** que
    aparecer. Sin ella, «no está en `faltan`» no distingue «está cargada» de «no se mira».
    """
    banco = _banco(monkeypatch, WHATSAPP_PROVIDER=proveedor, **{requerida: ""})
    respuesta = banco.cliente().get("/salud")

    assert respuesta.status_code == 200, (
        f"`/salud` contestó {respuesta.status_code} y tiene que ser 200 siempre, aunque falte la "
        f"mitad de las credenciales. Un 503 acá hace que Railway mate el despliegue: la lista "
        f"informa, el código de estado no."
    )
    cuerpo = respuesta.json()
    assert requerida in cuerpo.get("faltan", []), (
        f"con `WHATSAPP_PROVIDER={proveedor}` y `{requerida}` sin cargar, `/salud` no la nombra en "
        f"`faltan`: {cuerpo.get('faltan')}. La comprensión tiene que recorrer `requeridas + "
        f"OPCIONALES` y `requeridas` se arma **adentro del handler**, contra el proveedor "
        f"configurado. Si sólo recorre `OPCIONALES`, ninguna requerida puede aparecer nunca y el "
        f"criterio del paso 4 de blueprint/50-despliegue.md pasa por vacío en vez de por bueno."
    )


def test_salud_deja_de_nombrar_lo_que_si_esta_cargado(monkeypatch) -> None:
    """La otra mitad: una lista que nombra todo siempre tampoco sirve de nada."""
    banco = _banco(monkeypatch, WHATSAPP_PROVIDER="meta", META_APP_SECRET="secreto-de-prueba")
    cuerpo = banco.cliente().get("/salud").json()

    assert "META_APP_SECRET" not in cuerpo.get("faltan", []), (
        f"`META_APP_SECRET` está cargada y `/salud` la sigue nombrando en `faltan`: "
        f"{cuerpo.get('faltan')}. O la lista está escrita a mano en vez de mirar el entorno, o el "
        f"handler lee `os.environ` antes de que `python-dotenv` cargue el `.env`."
    )
    assert cuerpo.get("proveedor") == "meta", (
        f"`/salud` dice que el proveedor es {cuerpo.get('proveedor')!r} y el entorno decía `meta`. "
        f"`POR_PROVEEDOR` se resolvió una vez al importar, con otro valor de `WHATSAPP_PROVIDER`: "
        f"se arma adentro del handler, en cada llamada."
    )
    assert cuerpo.get("modo") in ("borrador", "automatico"), (
        f"`/salud` devolvió `modo`={cuerpo.get('modo')!r}. Son dos, y el default es `borrador`."
    )


def test_salud_no_pide_token(monkeypatch) -> None:
    """Sin cabecera y sin cookie, 200. Railway no manda ninguna de las dos."""
    banco = _banco(monkeypatch)
    respuesta = banco.cliente().get("/salud")
    assert respuesta.status_code == 200, (
        f"`/salud` sin token contestó {respuesta.status_code}. Es el `healthcheckPath` de "
        f"`railway.json` y Railway no manda cabeceras: adentro del router del panel, el despliegue "
        f"se muere en el chequeo de salud y lo único que se lee es `service unavailable`."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7 · Lo que escribió un desconocido se escapa antes de entrar al HTML
# ─────────────────────────────────────────────────────────────────────────────

# Lo que un contacto puede escribir por WhatsApp y termina en la bandeja. No es un ejemplo
# rebuscado: el resumen del CRM lo redacta el modelo leyendo lo que mandó el contacto, y el texto
# del borrador del paso 3 también.
GUION = "<script>alert(1)</script>"
GUION_ESCAPADO = "&lt;script&gt;alert(1)&lt;/script&gt;"

# La otra mitad, la que se pierde con `html.escape(valor, quote=False)`: adentro de un atributo no
# hace falta abrir una etiqueta, alcanza con cerrar la comilla. `html.escape` escapa las comillas
# por default, y el default es lo que hay que dejar quieto.
COMILLAS = '" onmouseover="alert(1)'


def _datos_envenenados() -> dict:
    """Las tres vistas del paso 8, con texto de un desconocido en los campos que lo traen.

    Las filas tienen la forma que devuelven las rutas de `/api/`: la de `leads` es la tabla del
    archivo 34 —`resumen` es una de sus columnas—, y las otras dos son la conversación y el
    borrador que muestra la bandeja.
    """
    return {
        "leads": [
            {
                "contacto_id": "bsu_01HZK3M9QX7T2VW4",
                "numero": None,
                "nombre": f"Ana {COMILLAS}",
                "etapa": "calificado",
                "score": 62,
                "temperatura": "tibio",
                "resumen": f"Preguntó el precio del curso. {GUION}",
                "proximo_paso": "Confirmar horario",
                "proximo_paso_fecha": "2026-03-03",
            }
        ],
        "conversaciones": [
            {
                "contacto_id": "bsu_01HZK3M9QX7T2VW4",
                "ultimo_mensaje": f"hola, cuánto sale {GUION}",
                "estado": "abierta",
                "score": 62,
            }
        ],
        "pendientes": [
            {
                "id": 1,
                "paso": 3,
                "estado": "pendiente",
                "contacto_id": "bsu_01HZK3M9QX7T2VW4",
                "texto": f"El curso sale 12000 MXN. {GUION}",
            }
        ],
    }


def _pagina(panel, datos: dict) -> str:
    """El HTML de `GET /panel` armado con estas filas, sin base y sin navegador.

    Se llama a `pagina()` de frente porque es el cuerpo de esa respuesta y porque así se pueden
    poner filas envenenadas sin migrar una base. El nombre es una convención de esta suite: si el
    build usa otro, se cambia acá y en ningún otro lado. Lo escribe `blueprint/35-panel-api.md`
    paso 8.
    """
    armar = getattr(panel, "pagina", None)
    assert callable(armar), (
        "`panel/panel.py` no define `pagina(datos)`. Es la función que arma el HTML entero de "
        "`GET /panel` a partir de las filas de `/api/`, y es por donde esta suite le pone enfrente "
        "un resumen con `<script>` adentro. Sin ella, el escapado del paso 8 de "
        "blueprint/35-panel-api.md no lo verifica nada: es un `curl | grep` que no corre nadie."
    )
    for intento in (lambda: armar(datos), lambda: armar(**datos)):
        try:
            html = intento()
        except TypeError:
            continue
        assert isinstance(html, str) and html.strip(), (
            f"`pagina()` devolvió {type(html).__name__} y tiene que devolver el HTML entero como "
            f"cadena, que es lo que se manda en el cuerpo de la respuesta."
        )
        return html
    raise AssertionError(
        "no supe llamar a `pagina()`. La convención es `pagina(datos)`, con `datos` trayendo "
        "`leads`, `conversaciones` y `pendientes` tal como los devuelven las rutas de `/api/`; "
        "la escribe blueprint/35-panel-api.md paso 8."
    )


def test_el_panel_escapa_lo_que_escribio_un_desconocido(monkeypatch) -> None:
    """Los dos sentidos: el `<script>` no sale crudo, y el texto igual se ve, escapado.

    El primero solo no alcanza: un panel que no muestre nada tampoco tiene el `<script>` adentro,
    y pasaría por vacío. El segundo es el control positivo —el texto llegó a la página— y el
    primero es la promesa.
    """
    banco = _banco(monkeypatch)
    html = _pagina(banco.panel, _datos_envenenados())

    assert GUION not in html, (
        f"el HTML del panel trae `{GUION}` crudo. Ese texto lo escribió un desconocido por "
        f"WhatsApp y corre en el navegador de quien lee la bandeja, que es donde vive la cookie "
        f"`wca_panel`: es el camino más corto que existe para perder el panel entero. Todo lo que "
        f"viene de un chat pasa por `html.escape` antes de entrar al HTML; ver "
        f"blueprint/35-panel-api.md, paso 8."
    )
    assert GUION_ESCAPADO in html, (
        f"el HTML del panel no trae `{GUION_ESCAPADO}` en ninguna parte. O el panel no muestra "
        f"ninguno de los campos que escribe un contacto —y entonces la aserción de arriba pasa por "
        f"vacío y no promete nada—, o lo está borrando en vez de escaparlo. Escapar no es sacar: "
        f"quien lee la bandeja tiene que ver qué dijo el contacto, con las etiquetas a la vista."
    )


def test_el_panel_escapa_tambien_las_comillas(monkeypatch) -> None:
    """`html.escape(valor, quote=False)` deja abierta la mitad que no necesita una etiqueta."""
    banco = _banco(monkeypatch)
    html = _pagina(banco.panel, _datos_envenenados())

    assert COMILLAS not in html, (
        f"el HTML del panel trae `{COMILLAS}` crudo. Adentro de un atributo —un `title=`, un "
        f"`value=`, un `data-…`— no hace falta abrir una etiqueta: alcanza con cerrar la comilla. "
        f"`html.escape` escapa las comillas por default; alguien le pasó `quote=False`."
    )


def _es_html_escape(nodo: ast.AST) -> bool:
    """`html.escape` escrito con el módulo adelante."""
    return (
        isinstance(nodo, ast.Attribute)
        and nodo.attr == "escape"
        and isinstance(nodo.value, ast.Name)
        and nodo.value.id == "html"
    )


def _nombres_de_html_escape(arbol: ast.AST) -> set[str]:
    """Todo nombre que en este archivo apunta a `html.escape`, con sus alias.

    Las tres formas que dan la misma función y que un build escribe de verdad:
    `from html import escape`, `from html import escape as e`, y `e = html.escape` para no
    repetirla doce veces adentro del armado. Sin los alias, esta prueba se pone roja contra un
    panel que escapa bien, que es peor que no tenerla.
    """
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module == "html" and not nodo.level:
            nombres |= {a.asname or a.name for a in nodo.names if a.name == "escape"}
        elif isinstance(nodo, ast.Assign) and _es_html_escape(nodo.value):
            nombres |= {d.id for d in nodo.targets if isinstance(d, ast.Name)}
    return nombres


def test_el_html_se_escapa_con_html_escape_contado_por_ast(monkeypatch) -> None:
    """Contado como nodo de llamada, por lo mismo que `compare_digest` un archivo más arriba.

    `\"html.escape\" in fuente` sigue en verde con el escapado reemplazado por tres `.replace()`
    escritos a mano, porque la palabra vive en los comentarios que explican por qué va. Y el
    escapado a mano es el defecto de siempre: se olvida el `&` primero —y entonces `&amp;lt;` se
    vuelve a leer como `<`—, o se olvidan las comillas.
    """
    motivo = _motivo_sin_panel()
    if motivo:
        pytest.skip(motivo)

    ruta = RAIZ / PANEL
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    alias = _nombres_de_html_escape(arbol)
    llamadas = [
        n
        for n in ast.walk(arbol)
        if isinstance(n, ast.Call)
        and (
            _es_html_escape(n.func)
            or (isinstance(n.func, ast.Name) and n.func.id in alias)
        )
    ]

    assert llamadas, (
        f"en {PANEL} no hay una sola llamada a `html.escape`. El HTML lo arma este archivo con un "
        f"`<style>` y un `<script>` adentro y sin paso de build, así que no hay ningún motor de "
        f"plantillas que escape por vos: si no está escrito acá, no pasa. Ver "
        f"blueprint/35-panel-api.md, paso 8."
    )
