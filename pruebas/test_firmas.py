"""Las firmas, contra los bytes crudos de `pruebas/fixtures/`.

El defecto que este archivo existe para hacer fallar:

    # Se lee bien. Pasa todas las pruebas que escribiría quien lo escribió.
    # Falla el 100 % de las entregas reales, con un 401 que el que manda nunca te muestra.
    firma_ok = verificar(json.dumps(await request.json()), cabecera)

El que firma calcula el HMAC —la huella criptográfica calculada con un secreto compartido; ver
`blueprint/00-contrato.md` § 10— sobre los octetos exactos que puso en el cable. Reserializar
—parsear el JSON y volver a escribirlo— cambia el espaciado y el escapado de las tildes,
produce otros bytes y por lo tanto otro MAC.

Los dos `.raw` traen el espaciado torcido a propósito: sangrías que no son múltiplo de nada, un
tabulador, espacios antes de los dos puntos y al final de una línea, una línea en blanco adentro
de un objeto, y la misma vocal escrita de las dos formas —`Fern\\u00e1ndez` escapada y `raíces`
con la `á` literal—. No hay combinación de banderas de `json.dumps` que devuelva esos bytes: con
`ensure_ascii=True` cambia la tilde literal, con `ensure_ascii=False` cambia la escapada.

Por eso la prueba que importa es la tercera: **el cuerpo crudo con espaciado no canónico,
correctamente firmado, tiene que verificar**. Una implementación que reserializa no puede pasar
esa. La prueba no revisa el código: lo hace fallar.

Las comprobaciones corren sobre los dos módulos que firman —la plantilla verbatim de
`plantillas/seguridad/firmas.py` y el `agente/firmas.py` copiado de ahí— por los dos fixtures.
Antes de construir son dos, porque el segundo módulo todavía no existe.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from pruebas.proveedor_falso import FIXTURES, RAIZ

# ─────────────────────────────────────────────────────────────────────────────
# Los módulos que firman, y los dos fixtures
# ─────────────────────────────────────────────────────────────────────────────

RUTAS_DE_FIRMAS = {
    "plantilla": RAIZ / "plantillas/seguridad/firmas.py",
    "build": RAIZ / "agente/firmas.py",
}

PROVEEDORES = ["meta", "zernio"]


def _cargar_modulo(nombre: str, ruta: Path):
    spec = importlib.util.spec_from_file_location(f"firmas_{nombre}", ruta)
    modulo = importlib.util.module_from_spec(spec)
    # El registro en sys.modules va ANTES de ejecutarlo: las anotaciones se resuelven mirando
    # `sys.modules[cls.__module__]`.
    sys.modules[f"firmas_{nombre}"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(params=list(RUTAS_DE_FIRMAS), scope="session")
def firmas(request):
    """El módulo de firmas, una vez por cada copia que exista en el árbol."""
    ruta = RUTAS_DE_FIRMAS[request.param]
    if not ruta.is_file():
        pytest.skip(
            f"todavía no existe {ruta.relative_to(RAIZ)}. Se copia verbatim desde "
            f"plantillas/seguridad/firmas.py en blueprint/30-generacion.md paso 1, y no se "
            f"reescribe nunca."
        )
    return _cargar_modulo(request.param, ruta)


@pytest.fixture(params=PROVEEDORES)
def entrega(request):
    """Una entrega grabada: los bytes crudos y la ficha con su firma real."""
    nombre = request.param
    crudo = (FIXTURES / f"{nombre}.raw").read_bytes()  # read_bytes, nunca read_text
    ficha = json.loads((FIXTURES / f"{nombre}.meta.json").read_text(encoding="utf-8"))
    return nombre, crudo, ficha


def verificador(firmas, proveedor: str):
    return firmas.verificar_meta if proveedor == "meta" else firmas.verificar_zernio


def firmador(firmas, proveedor: str):
    return firmas.firmar_meta if proveedor == "meta" else firmas.firmar_zernio


# ─────────────────────────────────────────────────────────────────────────────
# Las tres comprobaciones
# ─────────────────────────────────────────────────────────────────────────────


def test_la_firma_correcta_verifica(firmas, entrega) -> None:
    proveedor, crudo, ficha = entrega
    assert verificador(firmas, proveedor)(
        crudo, cabecera=ficha["firma"], secreto=ficha["secreto"]
    ), (
        f"la firma grabada de {proveedor}.raw no verifica contra sus propios bytes. O el "
        f"fixture se regeneró con json.dumps, o el módulo cambió de algoritmo."
    )


def test_el_cuerpo_alterado_con_la_misma_cabecera_no_verifica(firmas, entrega) -> None:
    """Un byte de más y el MAC es otro. Eso es todo lo que protege el webhook."""
    proveedor, crudo, ficha = entrega
    verificar = verificador(firmas, proveedor)

    alterado = crudo + b" "
    assert not verificar(alterado, cabecera=ficha["firma"], secreto=ficha["secreto"])

    volteado = bytearray(crudo)
    volteado[-2] ^= 0x01
    assert not verificar(bytes(volteado), cabecera=ficha["firma"], secreto=ficha["secreto"])


def test_el_cuerpo_crudo_con_espaciado_torcido_verifica_y_el_reserializado_no(
    firmas, entrega
) -> None:
    """La que importa. Una implementación que reserializa no puede pasar esta.

    Primero se comprueba que el fixture siga siendo lo que dice ser: que ninguna combinación de
    banderas de `json.dumps` reproduzca esos bytes. Un fixture regenerado queda inerte y a
    partir de ahí el reserializador pasa la prueba, que es lo único que esta carpeta existía
    para impedir.
    """
    proveedor, crudo, ficha = entrega
    verificar = verificador(firmas, proveedor)

    datos = json.loads(crudo)
    canonicos = {
        json.dumps(datos, ensure_ascii=a, separators=s).encode("utf-8")
        for a in (True, False)
        for s in ((",", ":"), (", ", ": "))
    }
    assert crudo not in canonicos, (
        f"{proveedor}.raw se puede reproducir con json.dumps. Alguien lo regeneró y el fixture "
        f"quedó inerte: desde acá una implementación que reserializa pasa esta prueba."
    )

    assert verificar(crudo, cabecera=ficha["firma"], secreto=ficha["secreto"]), (
        "el cuerpo crudo con el espaciado tal como llegó tiene que verificar"
    )
    for reserializado in canonicos:
        assert not verificar(
            reserializado, cabecera=ficha["firma"], secreto=ficha["secreto"]
        ), "el cuerpo reserializado verificó, y con eso el invariante 1 no está protegido"


def test_la_firma_se_calcula_sobre_los_mismos_bytes_que_grabo_el_fixture(firmas, entrega) -> None:
    """El firmador y el verificador miran lo mismo, y el prefijo es el de cada proveedor."""
    proveedor, crudo, ficha = entrega
    calculada = firmador(firmas, proveedor)(crudo, secreto=ficha["secreto"])

    assert calculada == ficha["firma"]
    if proveedor == "meta":
        assert calculada.startswith(firmas.PREFIJO_META)
    else:
        assert "=" not in calculada, "Zernio va sin prefijo: hex minúscula pelado"


# ─────────────────────────────────────────────────────────────────────────────
# Las guardas del módulo
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("ya_parseado", [{"a": 1}, "{}", ["a"]])
def test_lo_ya_parseado_levanta_typeerror_y_no_devuelve_falso(firmas, entrega, ya_parseado) -> None:
    """Un False acá se confunde con un atacante y se investiga durante horas."""
    proveedor, _, ficha = entrega
    with pytest.raises(TypeError):
        verificador(firmas, proveedor)(
            ya_parseado, cabecera=ficha["firma"], secreto=ficha["secreto"]
        )


def test_la_entrega_sin_firma_no_verifica(firmas, entrega) -> None:
    """Un webhook público sin firma es cualquiera escribiéndole a tu número."""
    proveedor, crudo, ficha = entrega
    assert not verificador(firmas, proveedor)(crudo, cabecera=None, secreto=ficha["secreto"])
    assert not verificador(firmas, proveedor)(crudo, cabecera="", secreto=ficha["secreto"])


def _llamadas_a_compare_digest(arbol: ast.AST) -> list[ast.Call]:
    """Las llamadas a `hmac.compare_digest` del módulo, contadas como nodos y no como texto.

    Se aceptan las dos formas de escribirla: `hmac.compare_digest(...)` con el módulo importado, y
    `compare_digest(...)` con `from hmac import compare_digest`. Cualquier otra cosa que se llame
    `compare_digest` y no venga de `hmac` no cuenta.
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


# Las tres funciones que comparan un secreto contra algo que llegó de afuera, y por lo tanto las
# tres que tienen que comparar en tiempo constante. Ver `blueprint/00-contrato.md` § 10.
COMPARAN_SECRETOS = ("verificar_meta", "verificar_zernio", "responder_alta_meta")


def test_la_comparacion_es_en_tiempo_constante(firmas) -> None:
    """`==` sobre cadenas corta en el primer byte distinto, y ese tiempo filtra la firma.

    Se cuenta por AST y no por `"compare_digest" in fuente`. La palabra aparece tres veces en el
    docstring de este mismo módulo —el apartado «Por qué `hmac.compare_digest` y nunca `==`» está
    escrito ahí—, así que la búsqueda por texto sigue en verde con los tres usos reales
    reemplazados por `==` y cero comparaciones en tiempo constante en el archivo. Un nodo de
    llamada no lo puede fingir un comentario.
    """
    ruta = Path(firmas.__file__)
    cual = ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta
    fuente = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(fuente, filename=str(ruta))

    llamadas = _llamadas_a_compare_digest(arbol)
    assert len(llamadas) >= len(COMPARAN_SECRETOS), (
        f"{cual} tiene {len(llamadas)} llamada(s) a `hmac.compare_digest` y necesita al menos "
        f"{len(COMPARAN_SECRETOS)}, una por cada función que compara un secreto contra algo que "
        f"llegó de afuera: {', '.join(COMPARAN_SECRETOS)}. La palabra sigue apareciendo "
        f"{fuente.count('compare_digest')} vez/veces en el archivo, casi toda en el docstring: lo "
        f"que se cuenta acá son nodos de llamada, no apariciones de texto."
    )

    for nombre in COMPARAN_SECRETOS:
        funcion = _funcion(arbol, nombre)
        assert funcion is not None, (
            f"{cual} no define `{nombre}()`. El módulo se copia verbatim desde "
            f"plantillas/seguridad/firmas.py y no se reescribe nunca; ver "
            f"blueprint/30-generacion.md paso 1."
        )
        assert _llamadas_a_compare_digest(funcion), (
            f"en {cual}, `{nombre}()` compara sin `hmac.compare_digest`. `==` sobre cadenas corta "
            f"en el primer byte distinto: el tiempo de respuesta filtra cuántos caracteres del "
            f"principio adivinó quien está probando, y eso alcanza para reconstruir una firma "
            f"byte por byte contra un servicio que contesta rápido. Se arregla en "
            f"plantillas/seguridad/firmas.py, que es el original, y se vuelve a copiar."
        )


# ─────────────────────────────────────────────────────────────────────────────
# El alta de Meta: el challenge vuelve como texto plano
# ─────────────────────────────────────────────────────────────────────────────


CHALLENGE = "1158201444"
TOKEN = "token-de-alta-de-prueba"


def test_el_alta_devuelve_el_challenge_verbatim(firmas) -> None:
    devuelto = firmas.responder_alta_meta(
        hub_mode="subscribe",
        hub_verify_token=TOKEN,
        hub_challenge=CHALLENGE,
        verify_token=TOKEN,
    )
    assert devuelto == CHALLENGE
    assert isinstance(devuelto, str)


def test_el_challenge_vuelve_como_texto_plano_y_no_como_json(firmas) -> None:
    """`JSONResponse("1158201444")` manda las comillas adentro del cuerpo.

    Son dos bytes de más y alcanzan para que el alta no ocurra. El alta falla sin ningún error
    visible: la pantalla simplemente no se suscribe.
    """
    assert firmas.TIPO_RESPUESTA_ALTA.startswith("text/plain")
    assert json.dumps(CHALLENGE) != CHALLENGE
    assert json.dumps(CHALLENGE) == f'"{CHALLENGE}"'


@pytest.mark.parametrize(
    "campos",
    [
        {"hub_mode": "unsubscribe"},
        {"hub_verify_token": "otro-token"},
        {"hub_verify_token": None},
        {"hub_challenge": None},
    ],
)
def test_el_alta_que_no_cuadra_se_rechaza(firmas, campos: dict) -> None:
    argumentos = {
        "hub_mode": "subscribe",
        "hub_verify_token": TOKEN,
        "hub_challenge": CHALLENGE,
        "verify_token": TOKEN,
    } | campos
    with pytest.raises(firmas.AltaRechazada):
        firmas.responder_alta_meta(**argumentos)


def test_el_alta_con_el_token_propio_vacio_se_rechaza(firmas) -> None:
    """Con el token vacío el alta la pasa cualquiera."""
    with pytest.raises(firmas.AltaRechazada):
        firmas.responder_alta_meta(
            hub_mode="subscribe",
            hub_verify_token="",
            hub_challenge=CHALLENGE,
            verify_token="",
        )


def test_la_ruta_del_alta_contesta_texto_plano(monkeypatch) -> None:
    """La misma regla, ya montada en el servidor. Saltea mientras el build no exista.

    `blueprint/00-contrato.md` § 3: GET `/webhook/{proveedor}` devuelve el `hub.challenge`
    verbatim y como texto plano, sin token. El `WHATSAPP_VERIFY_TOKEN` de acá lo inventamos
    nosotros y no abre nada: es el que se compara contra el `hub.verify_token` del alta.
    """
    from pruebas.proveedor_falso import motivo_sin_servidor

    motivo = motivo_sin_servidor()
    if motivo:
        pytest.skip(motivo)

    import importlib

    from fastapi.testclient import TestClient

    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", TOKEN)
    monkeypatch.setenv("WHATSAPP_PROVIDER", "meta")
    servidor = importlib.reload(importlib.import_module("agente.servidor"))
    cliente = TestClient(servidor.app)
    respuesta = cliente.get(
        "/webhook/meta",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": TOKEN,
            "hub.challenge": CHALLENGE,
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/plain")
    assert respuesta.text == CHALLENGE
    assert '"' not in respuesta.text
