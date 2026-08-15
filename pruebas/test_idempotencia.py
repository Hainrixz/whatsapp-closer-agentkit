"""Idempotencia, que son dos trabajos distintos y se prueban por separado.

**A la entrada, el dedupe.** El proveedor entrega al-menos-una-vez: el mensaje llega, y puede
llegar varias veces. Zernio reintenta hasta siete. Sin dedupe —descartar la entrega repetida— el
mismo cliente recibe la misma respuesta cuatro veces. La reproducción de acá manda el mismo
evento firmado tres veces: los tres tienen que contestar 200, tiene que quedar **una** fila, y
los envíos no pueden crecer después del primero.

Los tres 200 no son un detalle. Un 500 en la repetida hace que el proveedor siga reintentando, y
un 409 «ya lo tengo» también cuenta como fallo del lado de Meta: la entrega repetida es normal y
se contesta que sí.

**A la salida, la `Idempotency-Key`.** Va sacada del contenido —conversación, paso y hash del
texto— y no de un uuid nuevo por intento. Con un uuid nuevo no es idempotencia: es un contador,
y el reintento del cliente HTTP manda el mismo mensaje dos veces con dos claves distintas.

Todo esto necesita el servidor construido. Mientras no esté, cada prueba saltea con el motivo
escrito. Un salteo con motivo no es un aprobado.
"""

from __future__ import annotations

import importlib
import json

import pytest

from pruebas.proveedor_falso import (
    FIXTURES,
    ProveedorFalso,
    SinAgente,
    StubModel,
    cargar,
    correr_turnos,
    enchufar_transporte,
    huella,
    motivo_sin_ciclo,
    motivo_sin_servidor,
)

# La entrega grabada de Zernio: trae `phoneNumber` en nulo y `businessScopedUserId` con valor,
# que es el caso de abril de 2026. Un handler que indexe por número se rompe con este fixture
# antes de romperse con un cliente.
PROVEEDOR = "zernio"
CABECERA_EVENTO = "X-Zernio-Event-Id"


@pytest.fixture(scope="session")
def entrega() -> tuple[bytes, dict]:
    crudo = (FIXTURES / f"{PROVEEDOR}.raw").read_bytes()
    ficha = json.loads((FIXTURES / f"{PROVEEDOR}.meta.json").read_text(encoding="utf-8"))
    return crudo, ficha


@pytest.fixture
def cliente(monkeypatch, entrega):
    """El servidor con el proveedor de la entrega grabada y su secreto de prueba.

    El secreto sale de la ficha del fixture. Está escrito ahí a propósito: no firma nada real y
    no abre ninguna cuenta. El de verdad vive en `.env` y no entra a este árbol.
    """
    motivo = motivo_sin_servidor()
    if motivo:
        pytest.skip(motivo)

    _, ficha = entrega
    monkeypatch.setenv("WHATSAPP_PROVIDER", PROVEEDOR)
    monkeypatch.setenv("ZERNIO_WEBHOOK_SECRET", ficha["secreto"])
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")

    from fastapi.testclient import TestClient

    servidor = importlib.reload(importlib.import_module("agente.servidor"))
    with TestClient(servidor.app) as cli:
        yield cli


def entregar(cliente, crudo: bytes, ficha: dict):
    """Una entrega, con los bytes crudos tal cual y su firma real. Nunca reserializados."""
    evento = json.loads(crudo)["eventId"]
    return cliente.post(
        f"/webhook/{PROVEEDOR}",
        content=crudo,
        headers={
            ficha["cabecera"]: ficha["firma"],
            CABECERA_EVENTO: evento,
            "Content-Type": "application/json",
        },
    )


def filas_del_evento(evento_id: str) -> int:
    """Cuántas filas quedaron con ese `evento_id`, mirando el esquema que haya.

    Se inspeccionan las tablas y se cuenta en las que tengan una columna `evento_id`, en vez de
    escribir a mano el nombre de una tabla que todavía no existe. El día que el build llegue con
    otro nombre, esta cuenta lo sigue.
    """
    base = importlib.import_module("agente.base")
    contar = getattr(base, "contar_evento", None)
    if contar is not None:
        return contar(evento_id)
    pytest.skip(
        "`agente/base.py` no expone `contar_evento(evento_id)`. Sin una forma de contar las "
        "filas del almacén, «una sola fila» no se puede afirmar: escribila en el build o "
        "ajustá esta prueba a la que haya."
    )


# ─────────────────────────────────────────────────────────────────────────────
# A la entrada: el mismo evento tres veces
# ─────────────────────────────────────────────────────────────────────────────


def test_la_misma_entrega_tres_veces_contesta_200_las_tres(cliente, entrega) -> None:
    crudo, ficha = entrega
    codigos = [entregar(cliente, crudo, ficha).status_code for _ in range(3)]
    assert codigos == [200, 200, 200], (
        f"la reproducción devolvió {codigos}. La entrega repetida es normal —al-menos-una-vez, "
        f"hasta siete reintentos— y se contesta que sí. Un 409 o un 500 en la segunda hace que "
        f"el proveedor siga reintentando."
    )


def test_la_misma_entrega_tres_veces_deja_una_sola_fila(cliente, entrega) -> None:
    crudo, ficha = entrega
    for _ in range(3):
        entregar(cliente, crudo, ficha)
    evento = json.loads(crudo)["eventId"]
    assert filas_del_evento(evento) == 1, (
        "el dedupe no está: quedaron varias filas del mismo evento y el contacto va a recibir "
        "la misma respuesta una vez por reintento."
    )


def test_la_misma_entrega_tres_veces_no_hace_crecer_los_envios(cliente, entrega, monkeypatch) -> None:
    """Se cuentan los envíos que vio el transporte, no los que el agente dice que hizo."""
    crudo, ficha = entrega
    doble = ProveedorFalso()
    try:
        enchufar_transporte(doble, monkeypatch)
    except SinAgente as e:
        pytest.skip(str(e))

    entregar(cliente, crudo, ficha)
    despues_del_primero = len(doble.envios)
    entregar(cliente, crudo, ficha)
    entregar(cliente, crudo, ficha)

    assert len(doble.envios) == despues_del_primero, (
        f"los envíos pasaron de {despues_del_primero} a {len(doble.envios)} con dos entregas "
        f"repetidas. Eso es el mismo cliente contestado tres veces."
    )


def test_una_entrega_con_la_firma_de_otro_cuerpo_no_entra(cliente, entrega) -> None:
    """El 401 sale antes de parsear nada: lo que no está firmado no merece ni un json.loads."""
    crudo, ficha = entrega
    respuesta = cliente.post(
        f"/webhook/{PROVEEDOR}",
        content=crudo + b" ",
        headers={ficha["cabecera"]: ficha["firma"], "Content-Type": "application/json"},
    )
    assert respuesta.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# A la salida: la clave que sale del contenido
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(bool(motivo_sin_ciclo()), reason=motivo_sin_ciclo())
def test_todo_envio_lleva_idempotency_key() -> None:
    entrada = cargar("caso-02c.entrada.json")
    entrada["modo"] = "automatico"
    _, doble = correr_turnos(
        [entrada], modelo=StubModel.canonica(), historial=cargar("caso-02c.historial.json")
    )
    assert doble.envios, "no salió ningún mensaje y esta prueba no aplica"

    sin_clave = [e.url for e in doble.envios if not e.idempotency_key]
    assert sin_clave == [], f"salieron sin `Idempotency-Key`: {sin_clave}"


@pytest.mark.skipif(bool(motivo_sin_ciclo()), reason=motivo_sin_ciclo())
def test_la_idempotency_key_sale_del_contenido_y_no_de_un_uuid() -> None:
    """Dos corridas del mismo mensaje tienen que producir la misma clave.

    Con un uuid nuevo por intento las dos claves difieren, la prueba se pone roja acá y no en
    producción, que es donde se ve como el mismo cliente contestado dos veces.
    """
    entrada = cargar("caso-02c.entrada.json")
    entrada["modo"] = "automatico"
    historial = cargar("caso-02c.historial.json")

    claves = []
    for _ in range(2):
        _, doble = correr_turnos(
            [entrada], modelo=StubModel.canonica(), historial=historial
        )
        assert doble.envios, "no salió ningún mensaje y esta prueba no aplica"
        claves.append(doble.envios[0].idempotency_key)

    assert claves[0] == claves[1], (
        f"la misma conversación, el mismo paso y el mismo texto dieron dos claves distintas: "
        f"{claves}. Con un uuid nuevo por intento no es idempotencia, es un contador."
    )


@pytest.mark.skipif(bool(motivo_sin_ciclo()), reason=motivo_sin_ciclo())
def test_la_idempotency_key_cambia_cuando_cambia_el_texto() -> None:
    """La otra mitad: una clave fija sería idempotencia de más y comería el segundo mensaje.

    Lo que cambia entre las dos corridas es el texto **saliente**, que es sobre lo que se
    calcula la clave —conversación, paso y hash del texto—. Cambiar el mensaje del contacto y
    dejar el mismo stub no prueba nada de esto: el texto que sale es idéntico en las dos y un
    build correcto tiene que devolver la misma clave. Con esa forma, la única manera de aprobar
    es calcular la clave sobre el mensaje entrante, o sea lo contrario de lo que este archivo
    dice querer.
    """
    entrada = cargar("caso-01.entrada.json")
    entrada["modo"] = "automatico"
    entrada["confirmado"] = True

    primero = StubModel.canonica()
    segundo = StubModel.otro_texto("Te dejo el martes 3 a las 10, que es el que queda libre.")
    assert primero.salida["texto"] != segundo.salida["texto"], (
        "las dos corridas redactan el mismo texto y esta prueba no aplica"
    )

    claves = []
    for stub in (primero, segundo):
        _, doble = correr_turnos([entrada], modelo=stub)
        assert doble.envios, "no salió ningún mensaje y esta prueba no aplica"
        claves.append(doble.envios[0].idempotency_key)

    assert claves[0] != claves[1], (
        f"dos textos distintos salieron con la misma clave: {claves}. El proveedor va a "
        f"descartar el segundo y el contacto se queda sin respuesta."
    )


def test_la_huella_del_contenido_es_estable() -> None:
    """La pieza que la clave usa adentro, probada sin el build.

    No prueba el agente: prueba que la cuenta que la clave hace es la misma en las dos corridas
    de arriba. Es lo único de este archivo que corre con el árbol sin construir.
    """
    assert huella("hola") == huella("hola")
    assert huella("hola") != huella("hola ")
    assert len(huella("hola")) == 64
