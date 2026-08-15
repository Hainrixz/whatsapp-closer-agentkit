"""Los nueve campos del contrato de salida que hasta esta ronda no afirmaba ningún nodo.

El censo del chequeo 23 —`.venv/bin/python scripts/auditar.py --censo`— corre la suite entera una
vez por campo de `contratos/salida.schema.json`, cambiando **un solo valor** del documento que
devuelve `correr_ciclo`, y mira si algún nodo se pone rojo. Sobre un build con la suite en verde
dio `31 afirmado · 3 no_mutable · 9 sin_asercion`, y éstos eran los nueve:

    calificacion/intencion          calificacion/urgencia
    respuesta/objecion_detectada    respuesta/objecion_en_playbook
    crm/resumen                     crm/proximo_paso
    crm/proximo_paso_fecha          pregunta
    supuestos

Los nueve se podían mentir con la suite entera en verde: un build que los devuelva fijos —vacíos,
nulos, o el mismo literal de siempre— contesta, agenda, escribe en el CRM y pasa la compuerta.

**El peor era `respuesta.objecion_en_playbook`.** Ese campo dice si el playbook se buscó o no, que
es lo único que separa este agente de un bot de menú. Con el campo siempre en falso, la bandeja
muestra todo «para el humano» y nadie se entera; con el campo siempre en verdadero, el agente jura
haber contestado con la línea del playbook y no la miró nunca. Los dos pasaban los 231 nodos.

## La trampa que este archivo esquiva

**Una prueba que sólo valida el documento contra el esquema no afirma nada.** El censo inyecta
valores que **validan contra el mismo esquema** —otro miembro del `enum`, otra fecha con forma de
fecha, otra cadena—, así que el mutante también valida y el nodo que valida sigue verde. Es la
trampa en la que este kit ya cayó una vez: cuarenta y pico de campos «cubiertos» porque el
documento entero validaba.

Acá se mira **el valor**, y en las dos direcciones cuando el campo tiene dos:

| Campo | Qué se afirma | Las dos direcciones |
|---|---|---|
| `calificacion/intencion` | es la que devolvió el modelo, no una constante | dos intenciones marcadas y la nula |
| `calificacion/urgencia` | es la que devolvió el modelo | las cuatro del enum, la nula incluida |
| `respuesta/objecion_detectada` | es la objeción que el modelo nombró | dos objeciones distintas y la nula |
| `respuesta/objecion_en_playbook` | verdadero **si y sólo si** esa objeción está en el playbook de la entrada | la **misma** objeción contra dos playbooks, y dos respuestas distintas |
| `crm/resumen` | es lo que escribió el modelo, cortado en tres líneas | tres líneas pasan enteras, cinco se cortan a tres |
| `crm/proximo_paso` | es el que propuso el modelo, y está cuando el paso 5 corre | sin confirmar y confirmado |
| `crm/proximo_paso_fecha` | la que propuso el modelo, y es futura contra el reloj del ciclo | sin confirmar y confirmado |
| `pregunta` | está sólo cuando el estado es `detenido`, y es una sola | un turno que se detiene y otro que no |
| `supuestos` | identificadores declarados en `SUPUESTOS.md` | ni la lista vacía ni un id que no esté en el archivo |

La fila de `objecion_en_playbook` es la que hace el trabajo: la misma objeción, con el playbook que
la trae y con el playbook que no, tiene que dar dos respuestas distintas. Un build que devuelva el
campo fijo —en falso o en verdadero— pone en rojo una de las dos, y un build que lo derive de la
cadena en vez de del playbook pone en rojo la segunda.

## Cómo se lee un rojo de acá

Cada mensaje de falla dice tres cosas: **qué campo** es, **qué tenía que decir** y **en qué archivo
del build se arregla**. Quien lo lea a las tres de la mañana no tiene que abrir otro archivo para
saber por dónde empezar.

## Lo que este archivo no hace

- **No afirma el texto que redacta el modelo.** `pruebas/caso-01.md` lo excluye a propósito:
  afirmarlo ata la suite a una versión del modelo. Lo que se afirma es la **procedencia**, con una
  marca que el stub pone adentro del valor y que el build tiene que dejar pasar. Es el mismo
  método que `MARCA_DEL_STUB` en `pruebas/test_caso_01.py`.
- **No toca la red y no pide una credencial**, igual que el resto de la suite.
- **No inventa una salida que el modelo de verdad no pueda emitir.** Todo lo que este archivo le
  hace decir al stub sale del esquema angosto, y eso lo afirma el primer nodo del archivo.
- **No mira lo que salió al cable.** Eso es `pruebas/test_enviar.py` y es otra superficie. Acá se
  mira el documento del contrato, que es la superficie que el censo mide.

El número de nodos no se escribe acá: lo imprime `pytest pruebas/test_campos.py --collect-only -q`.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

import pytest

from pruebas.proveedor_falso import (
    RAIZ,
    StubModel,
    con,
    con_mensaje,
    paso,
)

# ─────────────────────────────────────────────────────────────────────────────
# Las marcas: procedencia sin afirmar el texto
# ─────────────────────────────────────────────────────────────────────────────

# Van adentro de valores que se leen como cualquier otro, para que el build los trate igual que a
# uno de verdad, y no se parecen a nada que un build pueda haber escrito de memoria.
MARCA_INTENCION_A = "referencia INT-3W9K"
MARCA_INTENCION_B = "referencia INT-5B1D"
MARCA_OBJECION = "referencia OBJ-6H2L"
MARCA_PROXIMO = "referencia CRM-8T3M"

INTENCIONES = (
    f"precio del curso ({MARCA_INTENCION_A})",
    f"cuándo empieza la próxima camada ({MARCA_INTENCION_B})",
    None,
)

# Las cuatro que declara `contratos/salida.schema.json`. La nula está porque es la que un build
# perezoso deja puesta: «urgencia fija en nulo, 217 passed» es una de las filas de `PENDIENTES.md`.
URGENCIAS = ("alta", "media", "baja", None)

# La misma objeción se prueba contra dos playbooks. Por eso lleva marca: que el campo no salga de
# reconocer una cadena conocida sino de buscarla en el playbook de **esta** entrada.
OBJECION_MARCADA = f"No me alcanza este mes ({MARCA_OBJECION})"
# La que no está en ningún playbook del corpus. No se escribe suelta: es la que trae
# `StubModel.objecion_fabricada()`, y `stub_objecion()` lo verifica antes de usarla.
OBJECION_FUERA = "Prefiero esperar a que baje el dólar"
RESPUESTA_DEL_PLAYBOOK = "Se puede en tres partes y arrancás con la primera."

# Tres líneas, cada una con su marca. Son las que el modelo escribe cuando escribe justo.
MARCAS_DEL_RESUMEN = ("RES-1A", "RES-2B", "RES-3C")
LINEAS_DEL_RESUMEN = tuple(
    f"Línea {i + 1} de lo que escribió el modelo ({marca})."
    for i, marca in enumerate(MARCAS_DEL_RESUMEN)
)
RESUMEN_DE_TRES = "\n".join(LINEAS_DEL_RESUMEN)

PROXIMO_PASO = f"Llamarlo para cerrar el horario ({MARCA_PROXIMO})"
# Dos días después del instante del corpus, y no una de las que inyecta el censo. Cae adentro de la
# `disponibilidad` del caso 01, así que se lee como una fecha que este turno podría haber propuesto.
PROXIMO_PASO_FECHA = "2026-03-04"

SUPUESTOS_MD = RAIZ / "SUPUESTOS.md"
IDENTIFICADOR_DE_SUPUESTO = re.compile(r"^##\s+(S\d{2})\s")


# ─────────────────────────────────────────────────────────────────────────────
# El stub, armado desde la salida canónica y sin tocar `proveedor_falso.py`
# ─────────────────────────────────────────────────────────────────────────────


def wire(**cambios) -> StubModel:
    """La salida canónica del stub con los campos del esquema angosto que pide cada prueba.

    Se arma sobre `StubModel.canonica()` y no sobre un literal pegado acá, por lo mismo que las
    seis salidas de `pruebas/proveedor_falso.py`: el esquema angosto tiene once campos y ninguno
    más, y una salida escrita a mano se desincroniza el día que se agregue el doceavo.

    El `assert` no es prolijidad. Un nombre mal escrito —`objecion` por `objecion_detectada`—
    agregaría una clave que el esquema angosto no declara, y la prueba pasaría a medir un campo
    que el modelo no emite mientras el que quería medir se queda con el valor canónico. Eso se lee
    como «el build lo afirma» y es «la prueba miró para otro lado».
    """
    stub = StubModel.canonica()
    desconocidos = sorted(set(cambios) - set(stub.salida))
    assert not desconocidos, (
        f"{desconocidos} no son campos del esquema angosto. Los once están en `CAMPOS_WIRE`, "
        f"arriba de `pruebas/proveedor_falso.py`."
    )
    stub.salida.update(cambios)
    return stub


def stub_objecion(objecion: str | None) -> StubModel:
    """El stub que nombra esa objeción.

    Para la que no está en ningún playbook del corpus usa `StubModel.objecion_fabricada()`, que ya
    estaba escrita en `pruebas/proveedor_falso.py` y no la inyectaba nadie: era una de las tres
    salidas malas que `PENDIENTES.md` anotaba como escritas y sin correr. El `assert` la ancla, así
    que el día que esa salida cambie de objeción esta prueba lo dice en vez de seguir midiendo
    contra una cadena que quedó suelta acá.
    """
    if objecion == OBJECION_FUERA:
        stub = StubModel.objecion_fabricada()
        assert stub.salida["objecion_detectada"] == OBJECION_FUERA, (
            f"`StubModel.objecion_fabricada()` nombra "
            f"{stub.salida['objecion_detectada']!r} y este archivo espera {OBJECION_FUERA!r}. "
            f"Actualizá `OBJECION_FUERA`, y revisá que la nueva tampoco esté en el playbook de "
            f"`pruebas/fixtures/caso-01.entrada.json`."
        )
        return stub
    return wire(objecion_detectada=objecion)


def salidas_de_este_archivo() -> list[tuple[str, dict]]:
    """Cada salida del stub que este archivo le hace decir al modelo, con su nombre."""
    todas: list[tuple[str, dict]] = []
    for valor in INTENCIONES:
        todas.append((f"intencion={valor!r}", wire(intencion=valor).salida))
    for valor in URGENCIAS:
        todas.append((f"urgencia={valor!r}", wire(urgencia=valor).salida))
    for valor in (OBJECION_MARCADA, OBJECION_FUERA, None):
        todas.append((f"objecion_detectada={valor!r}", stub_objecion(valor).salida))
    todas.append(("resumen de tres líneas", wire(resumen=RESUMEN_DE_TRES).salida))
    todas.append(("resumen largo", StubModel.resumen_largo().salida))
    todas.append((
        "próximo paso con fecha",
        wire(proximo_paso=PROXIMO_PASO, proximo_paso_fecha=PROXIMO_PASO_FECHA).salida,
    ))
    return todas


def con_playbook(entrada: dict, *, incluye_la_marcada: bool) -> dict:
    """La entrada del caso 01 con `OBJECION_MARCADA` en el playbook, o sin ella.

    Es la mitad que hace que `objecion_en_playbook` se pueda afirmar de verdad: la **misma**
    objeción contra los dos playbooks tiene que dar dos respuestas distintas. Con una sola de las
    dos entradas, un build que devuelva el campo fijo pasa.
    """
    playbook = json.loads(json.dumps(entrada["playbook"]))
    if incluye_la_marcada:
        playbook["objeciones"].append(
            {"objecion": OBJECION_MARCADA, "respuesta": RESPUESTA_DEL_PLAYBOOK}
        )
    else:
        playbook["objeciones"] = [
            o for o in playbook["objeciones"] if o["objecion"] != OBJECION_MARCADA
        ]
    return con(entrada, playbook=playbook)


def lineas(texto: str | None) -> list[str]:
    return [x.strip() for x in (texto or "").splitlines() if x.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# 0 · Lo que este archivo le hace decir al modelo, el modelo lo puede decir
# ─────────────────────────────────────────────────────────────────────────────


def test_las_salidas_que_arma_este_archivo_validan_contra_el_esquema_angosto() -> None:
    """Si no validan, estas pruebas afirman una conducta contra una entrada imposible.

    Corre sin el build: mide contra `agente/wire_schema.golden.json` si está, y contra la
    plantilla —que es la fuente— si todavía no se construyó. Es el mismo par que mira
    `pruebas/test_contrato.py::test_las_salidas_del_stub_validan_contra_el_esquema_angosto`, sobre
    las seis salidas que trae `StubModel`; éstas son las de este archivo.
    """
    jsonschema = pytest.importorskip("jsonschema")
    golden = RAIZ / "agente/wire_schema.golden.json"
    if not golden.is_file():
        golden = RAIZ / "plantillas/contratos/wire_schema.golden.json"
    validador = jsonschema.Draft202012Validator(json.loads(golden.read_text(encoding="utf-8")))

    for nombre, salida in salidas_de_este_archivo():
        errores = [e.message for e in validador.iter_errors(salida)]
        assert errores == [], (
            f"la salida «{nombre}» de pruebas/test_campos.py no valida contra el esquema angosto: "
            f"{errores}. Lo que el stub dice tiene que ser algo que el modelo de verdad pueda "
            f"decir, o la aserción de abajo prueba una conducta contra una entrada imposible."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2 · Calificá · `calificacion/intencion` y `calificacion/urgencia`
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("intencion", INTENCIONES)
def test_la_intencion_es_la_que_devolvio_el_modelo(
    entrada_caso_01: dict, correr, intencion: str | None
) -> None:
    """`calificacion.intencion` sale del wire, no de una constante.

    Medido antes de esta ronda: un build que la deja fija en `"algo"` pasaba los 217 nodos. Se
    prueba con dos intenciones distintas y con la nula, que es el otro valor que un build perezoso
    deja puesto. Con una sola no se distingue «la copió» de «le pegó por casualidad».
    """
    salidas, _ = correr([entrada_caso_01], modelo=wire(intencion=intencion))
    devuelta = salidas[0]["calificacion"]["intencion"]

    assert devuelta == intencion, (
        f"`calificacion.intencion`: el modelo devolvió {intencion!r} y la salida dice "
        f"{devuelta!r}. Es uno de los once campos del esquema angosto: el modelo lo emite y el "
        f"código lo copia tal cual. Se arregla en `agente/pasos/paso_2_calificar.py`, donde se "
        f"arma `t.calificacion`, leyendo `wire.intencion` en vez de escribir un valor."
    )


@pytest.mark.parametrize("urgencia", URGENCIAS)
def test_la_urgencia_es_la_que_devolvio_el_modelo(
    entrada_caso_01: dict, correr, urgencia: str | None
) -> None:
    """`calificacion.urgencia` sale del wire, no de un valor fijo.

    Medido antes de esta ronda: fija en nulo, 217 passed. Van las cuatro del `enum` y no una, para
    que ninguna pase por coincidir con la que la prueba esperaba.

    Lo que se pierde cuando este campo miente no es el campo: es el score. La urgencia es uno de
    los factores con los que el modelo lo calcula, así que un score puede salir de un factor que
    nadie leyó nunca.
    """
    salidas, _ = correr([entrada_caso_01], modelo=wire(urgencia=urgencia))
    devuelta = salidas[0]["calificacion"]["urgencia"]

    assert devuelta == urgencia, (
        f"`calificacion.urgencia`: el modelo devolvió {urgencia!r} y la salida dice {devuelta!r}. "
        f"Los cuatro valores que declara `contratos/salida.schema.json` son «alta», «media», "
        f"«baja» y nulo, y el que sale es el que el modelo emitió. Se arregla en "
        f"`agente/pasos/paso_2_calificar.py`, donde se arma `t.calificacion`."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3 · Respondé · `respuesta/objecion_detectada` y `respuesta/objecion_en_playbook`
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("objecion", [OBJECION_MARCADA, OBJECION_FUERA, None])
def test_la_objecion_detectada_es_la_que_nombro_el_modelo(
    entrada_caso_01: dict, correr, objecion: str | None
) -> None:
    """`respuesta.objecion_detectada` sale del modelo, no de una constante.

    Antes de esta ronda el campo aparecía dos veces en el árbol y ninguna era una prueba:
    `pruebas/proveedor_falso.py` lo escribe —es el doble— y `pruebas/simulador.py` lo imprime, y
    una pantalla no se pone roja. Mientras tanto el panel, la bandeja y el CRM mostraban una
    objeción que nadie comparó contra lo que escribió el contacto.

    La procedencia se afirma con la marca adentro del valor, igual que `MARCA_DEL_STUB` en
    `pruebas/test_caso_01.py`: no se afirma el texto del modelo, se afirma que lo que salió pasó
    por lo que el modelo devolvió. La nula va en la lista porque es el otro valor que un build
    puede dejar puesto sin que se note.
    """
    salidas, _ = correr([entrada_caso_01], modelo=stub_objecion(objecion))
    devuelta = salidas[0]["respuesta"]["objecion_detectada"]

    assert devuelta == objecion, (
        f"`respuesta.objecion_detectada`: el modelo nombró {objecion!r} y la salida dice "
        f"{devuelta!r}. La objeción la nombra el modelo —es uno de los once campos del esquema "
        f"angosto— y el paso 3 la copia sin reescribirla: es lo que después lee quien abre la "
        f"bandeja. Se arregla en `agente/pasos/paso_3_responder.py`, donde se arma `t.respuesta`."
    )


@pytest.mark.parametrize(
    ("en_el_playbook", "objecion", "esperado"),
    [
        # La misma objeción, los dos playbooks, dos respuestas distintas. Éstas dos son el par que
        # hace la afirmación: sin la segunda, un build que devuelva el campo siempre en verdadero
        # pasa la primera; sin la primera, uno que lo devuelva siempre en falso pasa la segunda.
        (True, OBJECION_MARCADA, True),
        (False, OBJECION_MARCADA, False),
        # Una objeción que no está en ningún playbook del corpus, y la ausencia de objeción.
        (True, OBJECION_FUERA, False),
        (True, None, False),
    ],
    ids=[
        "está-en-el-playbook",
        "misma-objeción-sin-playbook",
        "fuera-del-playbook",
        "sin-objeción",
    ],
)
def test_objecion_en_playbook_es_verdadero_si_y_solo_si_la_objecion_esta_en_el_playbook(
    entrada_caso_01: dict, correr, en_el_playbook: bool, objecion: str | None, esperado: bool
) -> None:
    """El campo que dice si el playbook se buscó o no. Era el peor de los nueve.

    Medido antes de esta ronda: siempre en falso, 217 passed. Y siempre en verdadero también.
    Los dos lados se ven distinto del otro lado del cable y los dos son graves: con el campo
    clavado en falso, la bandeja muestra todo «para el humano» y el equipo deja de mirarla; con el
    campo clavado en verdadero, el agente jura haber contestado con la línea del playbook y no la
    miró nunca. Lo que ese campo decide es lo único que separa este agente de un bot de menú.

    **La búsqueda es contra el playbook de la entrada, no contra una lista escrita en el build.**
    Por eso los dos primeros casos mandan la misma objeción y cambian el playbook: un build que
    reconozca cadenas conocidas —«está caro», «no tengo tiempo»— pasa el resto de la suite y se
    pone rojo acá, que es exactamente lo que tiene que pasar. La entrada la escribe quien vende,
    y `blueprint/25-playbook.md` es su dueño.
    """
    entrada = con_playbook(entrada_caso_01, incluye_la_marcada=en_el_playbook)
    salidas, _ = correr([entrada], modelo=stub_objecion(objecion))
    respuesta = salidas[0]["respuesta"]
    declaradas = [o["objecion"] for o in entrada["playbook"]["objeciones"]]

    # La misma cuenta, hecha contra la entrada que se acaba de mandar: un fixture que cambie mueve
    # las dos mitades juntas en vez de dejar el `esperado` de arriba mintiendo.
    derivado = bool(respuesta["objecion_detectada"]) and (
        respuesta["objecion_detectada"] in declaradas
    )
    assert derivado is esperado, (
        f"el caso está mal armado: con la objeción {objecion!r} y un playbook de {len(declaradas)} "
        f"objeciones, la cuenta contra la entrada da {derivado} y la tabla dice {esperado}."
    )

    assert respuesta["objecion_en_playbook"] is esperado, (
        f"`respuesta.objecion_en_playbook`: la objeción {objecion!r} "
        f"{'está' if esperado else 'no está'} en el playbook de esta entrada, así que el campo "
        f"tenía que decir {esperado} y dice {respuesta['objecion_en_playbook']}. Es verdadero si y "
        f"sólo si `objecion_detectada` aparece en `playbook.objeciones` de **esta** entrada, y la "
        f"búsqueda es exacta. En falso, el agente la nombra y no la responde: eso es material para "
        f"el humano y no una falla. Se arregla en `agente/pasos/paso_3_responder.py`, en "
        f"`objecion_en_playbook()`."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5 · CRM · `crm/resumen`, `crm/proximo_paso` y `crm/proximo_paso_fecha`
# ─────────────────────────────────────────────────────────────────────────────


def test_el_resumen_del_crm_es_lo_que_escribio_el_modelo(entrada_caso_01: dict, correr) -> None:
    """`crm.resumen` sale del modelo, y cada línea que llega a la fila es una que él escribió.

    Los tres nodos que ya miraban este campo —`test_caso_01.py`, `test_caso_02.py`,
    `test_camino_feliz.py`— afirman la **forma**: que venga escrito, que no pase de tres líneas y
    que no traiga pegado tal cual lo que escribió el contacto. Una cadena cualquiera cumple las
    tres, así que un build que descarte el resumen del modelo y escriba una línea propia pasaba
    los 231 nodos, y quien abre la fila del CRM lee un resumen que nadie ató a la conversación.

    Acá se afirma la procedencia: las tres marcas del modelo tienen que estar, y ninguna línea de
    la fila puede ser de otro lado.
    """
    salidas, _ = correr([entrada_caso_01], modelo=wire(resumen=RESUMEN_DE_TRES))
    crm = salidas[0]["crm"]
    assert crm is not None, (
        "`crm` vino en nulo con el paso 5 corrido. Nulo quiere decir «el paso 5 no corrió»: en un "
        "turno sin confirmar la fila se arma igual y vuelve con `escrito` en falso, para que se "
        "pueda ver y aprobar desde /bandeja. Ver `blueprint/00-contrato.md` § 13 y "
        "`agente/pasos/paso_5_crm.py`."
    )

    escritas = lineas(crm["resumen"])
    faltan = [m for m in MARCAS_DEL_RESUMEN[:3] if m not in (crm["resumen"] or "")]
    assert faltan == [], (
        f"`crm.resumen`: el modelo escribió tres líneas y a la fila no llegaron {faltan}. Lo que "
        f"quedó es «{crm['resumen']}». El resumen son tres líneas —qué quería, qué se le "
        f"respondió, qué falta— y las escribe el modelo: es uno de los once campos del esquema "
        f"angosto. Un resumen que el build redacte por su cuenta le dice lo mismo a quien abra "
        f"cualquier fila. Se arregla en `agente/pasos/paso_5_crm.py`, que lee `wire['resumen']`."
    )

    ajenas = [x for x in escritas if x not in LINEAS_DEL_RESUMEN]
    assert ajenas == [], (
        f"`crm.resumen`: {ajenas} no salió del modelo. Cada línea de la fila es una de las que él "
        f"escribió, recortada a tres por `recortar_resumen()` en `agente/salida.py`. Pegarle algo "
        f"de otro lado —el mensaje del contacto, el historial— es lo que prohíbe la aserción 5 de "
        f"`pruebas/caso-01.md`."
    )


def test_el_resumen_largo_se_corta_en_tres_lineas_y_no_se_pega_entero(
    entrada_caso_01: dict, correr
) -> None:
    """La otra dirección: el modelo escribe de más y la fila se queda con tres.

    Inyecta `StubModel.resumen_largo()` —cinco párrafos, la conversación entera pegada— que estaba
    escrita en `pruebas/proveedor_falso.py` y no la corría nadie: era una de las tres salidas malas
    que `PENDIENTES.md` anotaba como escritas y sin inyectar. Sin esta mitad, un `recortar` que no
    recorta pasa: la salida canónica ya viene con tres líneas, así que contar líneas sobre ella no
    puede ponerse roja nunca.
    """
    stub = StubModel.resumen_largo()
    escribio = lineas(stub.salida["resumen"])
    assert len(escribio) > 3, (
        f"`StubModel.resumen_largo()` devuelve {len(escribio)} líneas y este nodo existe para ver "
        f"el recorte: con tres o menos no hay nada que cortar y la prueba no puede fallar."
    )

    salidas, _ = correr([entrada_caso_01], modelo=stub)
    crm = salidas[0]["crm"]
    assert crm is not None, "`crm` vino en nulo con el paso 5 corrido; ver § 13 del contrato"

    escritas = lineas(crm["resumen"])
    assert len(escritas) == 3, (
        f"`crm.resumen`: el modelo escribió {len(escribio)} líneas y a la fila llegaron "
        f"{len(escritas)}. Son tres: qué quería, qué se le respondió, qué falta. Pegar la "
        f"conversación entera es fallo —aserción 5 de `pruebas/caso-01.md`—. Se arregla en "
        f"`recortar_resumen()` de `agente/salida.py`, que es la que llama "
        f"`agente/pasos/paso_5_crm.py`."
    )
    ajenas = [x for x in escritas if x not in escribio]
    assert ajenas == [], (
        f"`crm.resumen`: {ajenas} no salió del modelo. El recorte se queda con líneas del resumen "
        f"que él escribió; no las reescribe ni las resume otra vez. Ver `agente/salida.py`."
    )


@pytest.mark.parametrize("confirmado", [False, True], ids=["sin-confirmar", "confirmado"])
def test_el_proximo_paso_y_su_fecha_son_los_que_propuso_el_modelo(
    entrada_caso_01: dict, correr, confirmado: bool
) -> None:
    """`crm.proximo_paso` y `crm.proximo_paso_fecha` existen cuando el paso 5 corre.

    Medido antes de esta ronda: los dos descartados, 217 passed. Son la mitad de lo que la bandeja
    muestra para aprobar un borrador del paso 5 —`blueprint/00-contrato.md` § 13—: quien opera
    tiene que ver qué se comprometió y para cuándo **antes** de firmarlo. Con los dos en nulo, la
    bandeja muestra una fila que no dice qué sigue.

    Los dos modos, porque la fila se arma en los dos: sin confirmar vuelve con `escrito` en falso,
    y confirmado la escribe —o deja el motivo por el que no pudo—. En ninguno de los dos se
    descarta lo que el modelo propuso.
    """
    entrada = con(entrada_caso_01, confirmado=confirmado)
    salidas, _ = correr(
        [entrada],
        modelo=wire(proximo_paso=PROXIMO_PASO, proximo_paso_fecha=PROXIMO_PASO_FECHA),
    )
    crm = salidas[0]["crm"]
    assert crm is not None, (
        f"`crm` vino en nulo con `confirmado={confirmado}` y el paso 5 en "
        f"«{paso(salidas[0], 5)['estado']}». Nulo quiere decir «el paso 5 no corrió» y nada más; "
        f"ver `blueprint/00-contrato.md` § 13 y `agente/pasos/paso_5_crm.py`."
    )

    assert crm["proximo_paso"] == PROXIMO_PASO, (
        f"`crm.proximo_paso`: el modelo propuso {PROXIMO_PASO!r} y la fila dice "
        f"{crm['proximo_paso']!r}. Es uno de los once campos del esquema angosto y el paso 5 lo "
        f"copia a la fila. Se arregla en `agente/pasos/paso_5_crm.py`, que lee "
        f"`wire['proximo_paso']`."
    )
    assert crm["proximo_paso_fecha"] == PROXIMO_PASO_FECHA, (
        f"`crm.proximo_paso_fecha`: el modelo propuso {PROXIMO_PASO_FECHA!r} y la fila dice "
        f"{crm['proximo_paso_fecha']!r}. Va junto con `proximo_paso` y sale del mismo lugar: "
        f"`agente/pasos/paso_5_crm.py`. Un próximo paso sin fecha es un pendiente que nadie "
        f"reclama."
    )

    # El reloj del ciclo es el de la máquina, y la suite entera corre parada en el instante del
    # corpus —`parado_en_el_instante_del_corpus`, en `pruebas/conftest.py`—. O sea que esta cuenta
    # no depende del almanaque de quien la corra.
    hoy: date = datetime.now(timezone.utc).date()
    prometida = date.fromisoformat(crm["proximo_paso_fecha"])
    assert prometida >= hoy, (
        f"`crm.proximo_paso_fecha`: la fila promete {prometida} y el reloj del ciclo marca {hoy}. "
        f"Un próximo paso fechado ayer entra al CRM ya vencido: nadie lo va a ver en ninguna "
        f"agenda. La fecha se copia de `wire['proximo_paso_fecha']` en "
        f"`agente/pasos/paso_5_crm.py`."
    )


# ─────────────────────────────────────────────────────────────────────────────
# `pregunta` · lo que el agente devuelve cuando se detiene
# ─────────────────────────────────────────────────────────────────────────────


def test_sin_detenerse_no_hay_pregunta(salida_caso_01: dict) -> None:
    """`pregunta` es nula en todo turno que no termine en `detenido`.

    Antes de esta ronda el único lugar del árbol que lo leía era `pruebas/simulador.py`, la
    pantalla de la fase 5, que no es un nodo y no se pone roja. Es la dirección barata de las dos
    y hace falta igual: sin ella, un build que devuelva siempre la misma pregunta —«¿seguimos?»—
    pasa la compuerta entera con el estado en `parcial`.

    `blueprint/32-multimodal.md` paso 4 lo dice al revés y es lo mismo: «`pregunta` con dos
    preguntas, o con el estado en `parcial`» es un modo de falla.
    """
    assert salida_caso_01["estado"] != "detenido", (
        "el camino feliz del caso 01 terminó en `detenido`. Este nodo mide la otra rama; el "
        "estado y sus motivos los afirma `pruebas/test_caso_01.py`."
    )
    assert salida_caso_01["pregunta"] is None, (
        f"`pregunta`: el turno terminó en «{salida_caso_01['estado']}» y la salida trae "
        f"{salida_caso_01['pregunta']!r}. Es una sola y **sólo** con `detenido`: es lo que el "
        f"agente devuelve cuando para y pregunta, no un comentario al costado. Se arregla en "
        f"`armar_salida()` de `agente/ciclo.py`, que la deja pasar sólo con ese estado."
    )


def test_cuando_se_detiene_devuelve_una_sola_pregunta_de_una_linea(
    entrada_caso_01: dict, correr
) -> None:
    """El turno que se detiene devuelve la pregunta con la que sigue una persona.

    El caso es el de la aserción 1 de `pruebas/caso-01.md`: un audio sin `media_id` ni `media_url`,
    o sea sin forma de conseguir los bytes. Adivinar qué decía es fallo aunque la respuesta suene
    bien, así que el ciclo para. Lo que no puede hacer es parar en silencio: sin `pregunta`, quien
    abre la bandeja ve un turno detenido y ningún renglón que contestar.

    Las tres cosas que se afirman son las que pide `blueprint/32-multimodal.md` paso 4: que esté,
    que se conteste en una línea, y que sea **una sola** —dos preguntas es un modo de falla que ese
    archivo nombra—.
    """
    campos = {
        "tipo": "audio",
        "texto": None,
        "media_local": None,
        "media_id": None,
        "media_url": None,
    }
    salidas, _ = correr([con_mensaje(entrada_caso_01, **campos)])
    salida = salidas[0]

    assert salida["estado"] == "detenido", (
        f"con un audio del que no se pueden conseguir los bytes el ciclo se detiene, y el estado "
        f"dice «{salida['estado']}». Ver la aserción 1 de `pruebas/caso-01.md`."
    )
    pregunta = salida["pregunta"]
    assert isinstance(pregunta, str) and pregunta.strip(), (
        f"`pregunta`: el turno terminó en `detenido` y la salida trae {pregunta!r}. Detenerse sin "
        f"preguntar deja a quien abre la bandeja con un turno frenado y nada que contestar. La "
        f"escribe el cuerpo que detiene el ciclo —acá `agente/pasos/paso_1_contexto.py`, en la "
        f"rama de `SinMedio`— y la deja pasar `armar_salida()` de `agente/ciclo.py`."
    )
    assert len(lineas(pregunta)) == 1, (
        f"`pregunta`: son {len(lineas(pregunta))} líneas y tiene que ser una. «Se tiene que poder "
        f"contestar en una línea» lo dice `contratos/salida.schema.json`. Se arregla donde se "
        f"escribe, en `agente/pasos/paso_1_contexto.py`."
    )
    assert pregunta.count("?") == 1, (
        f"`pregunta`: trae {pregunta.count('?')} signos de cierre y es **una sola** pregunta. "
        f"Quedó «{pregunta}». Dos preguntas en el mismo renglón es el modo de falla que nombra "
        f"`blueprint/32-multimodal.md` paso 4, y ninguna es que el agente se detuvo sin preguntar "
        f"nada."
    )


# ─────────────────────────────────────────────────────────────────────────────
# `supuestos` · lo que el agente dio por sentado
# ─────────────────────────────────────────────────────────────────────────────


def supuestos_declarados() -> set[str]:
    """Los identificadores que declara `SUPUESTOS.md`, leídos del disco.

    Del archivo y no de una lista pegada acá, por lo mismo que el esquema en
    `pruebas/conftest.py`: una copia embebida deriva junto con la aserción que la usa.
    """
    assert SUPUESTOS_MD.is_file(), (
        f"falta {SUPUESTOS_MD.name}. `supuestos` son sus identificadores: sin el archivo no hay "
        f"contra qué comparar lo que el agente dice haber asumido."
    )
    declarados = {
        m.group(1)
        for m in (
            IDENTIFICADOR_DE_SUPUESTO.match(l)
            for l in SUPUESTOS_MD.read_text(encoding="utf-8").splitlines()
        )
        if m
    }
    assert declarados, (
        f"{SUPUESTOS_MD.name} no declara ningún `S01 ·`. O cambió el formato de los títulos, o el "
        f"archivo se vació: en los dos casos esta prueba dejó de medir lo que dice medir."
    )
    return declarados


def test_los_supuestos_son_identificadores_de_supuestos_md_y_no_una_lista_vacia(
    salida_caso_01: dict,
) -> None:
    """`supuestos` es lo que el agente dio por sentado, y se escribe con los ids del archivo.

    Antes de esta ronda `grep -rn supuestos pruebas/*.py` no imprimía nada: el campo no aparecía en
    una sola prueba, ni siquiera para leerlo. Es lo que alguien tiene que poder revisar antes de
    aprobar un borrador desde /bandeja —«¿con qué umbrales calificó esto?»— y con la lista vacía
    esa revisión no existe.

    Las dos mitades hacen falta. Sin la primera, un build que la devuelva vacía pasa; sin la
    segunda, uno que escriba cualquier cadena adentro pasa igual, y un identificador que no está en
    `SUPUESTOS.md` no remite a ningún lado.

    El camino feliz aplica por lo menos uno: **S03**, los cortes del score, que salen de `umbrales`
    en la entrada y con el default de 70 y 40 cuando no viene. Qué otros se suman depende del
    turno, así que acá se afirma que haya uno y que todos remitan, no cuáles.
    """
    declarados = supuestos_declarados()
    aplicados = salida_caso_01["supuestos"]

    assert isinstance(aplicados, list) and aplicados, (
        f"`supuestos`: el turno del caso 01 devolvió {aplicados!r}. Este turno califica con los "
        f"cortes del score, que es el supuesto S03 de `SUPUESTOS.md`, así que la lista no puede "
        f"estar vacía. Es lo que se revisa antes de aprobar un borrador desde /bandeja. Se llena "
        f"en los cuerpos de `agente/pasos/`, sobre `t.supuestos`, y sale en `armar_salida()` de "
        f"`agente/ciclo.py`."
    )

    inventados = sorted(set(aplicados) - declarados)
    assert inventados == [], (
        f"`supuestos`: {inventados} no está declarado en `SUPUESTOS.md`, que declara "
        f"{sorted(declarados)}. El campo son identificadores de ese archivo y nada más: un id que "
        f"no está ahí no remite a ningún lado, y quien lea la fila no tiene dónde ir a ver qué se "
        f"asumió. Se arregla en el cuerpo de `agente/pasos/` que lo agrega a `t.supuestos`."
    )
