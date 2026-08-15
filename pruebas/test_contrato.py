"""El contrato de salida, y el control negativo que lo hace significar algo.

Dos cosas se prueban acá y son distintas.

**Que las salidas validen.** El esquema se carga desde `contratos/salida.schema.json`, del
disco. Nunca una copia embebida: una copia deriva junto con la aserción que la usa, y el día que
alguien afloje el esquema las dos se mueven juntas y la prueba sigue en verde.

**Que el validador muerda.** Un validador mal cableado —el esquema que no carga, el
`iter_errors` que nunca se recorre, el `additionalProperties` que se perdió en una edición— hace
pasar cualquier cosa, y el reporte se ve idéntico al de una corrida que sí revisó. Por eso las
cinco mutaciones. Sin ellas, «todo verde» no se distingue de «no se está validando nada».

Y la aserción que el esquema no puede hacer: `pasos` tiene seis elementos con `n` entre 1 y 6,
pero el esquema no dice que sean **distintos** ni que estén **ordenados**. Seis pasos «1»
validan perfecto y no significan nada.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys

import pytest

from pruebas.proveedor_falso import CAMPOS_WIRE, FIXTURES, RAIZ, StubModel, cargar

SEIS_PASOS = [1, 2, 3, 4, 5, 6]

SALIDA_ESPERADA = "caso-01.salida-esperada.json"


@pytest.fixture(scope="session")
def salida_buena() -> dict:
    """La salida del camino feliz de `pruebas/caso-01.md`, del disco."""
    return cargar(SALIDA_ESPERADA)


def enes(documento: dict) -> list[int | None]:
    return [p.get("n") for p in documento.get("pasos", [])]


# ─────────────────────────────────────────────────────────────────────────────
# El esquema
# ─────────────────────────────────────────────────────────────────────────────


def test_el_esquema_es_un_json_schema_valido(esquema_salida: dict) -> None:
    """Un esquema roto no rechaza nada, y el reporte se lee igual que uno que sí revisó."""
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(esquema_salida)


def test_el_esquema_sale_del_disco_y_no_de_una_copia(esquema_salida: dict) -> None:
    """La ruta que se lee es la que publica el kit, y trae las claves que el resto asume."""
    assert esquema_salida["$id"].endswith("salida/1.json")
    assert esquema_salida["additionalProperties"] is False
    pasos = esquema_salida["properties"]["pasos"]
    assert pasos["minItems"] == 6 and pasos["maxItems"] == 6


# ─────────────────────────────────────────────────────────────────────────────
# Las salidas
# ─────────────────────────────────────────────────────────────────────────────


def test_la_salida_del_camino_feliz_valida(salida_buena: dict, validar) -> None:
    errores = validar(salida_buena)
    assert errores == [], (
        f"el esquema rechaza la salida del camino feliz de pruebas/caso-01.md: {errores}. "
        f"O el esquema se apretó de más, o la salida esperada del caso quedó vieja."
    )


def test_la_salida_del_camino_feliz_trae_los_seis_pasos_en_orden(salida_buena: dict) -> None:
    """La aserción que el esquema no puede hacer."""
    assert enes(salida_buena) == SEIS_PASOS


def test_la_salida_esperada_es_la_misma_que_mira_la_compuerta(salida_buena: dict) -> None:
    """El fixture y la `SALIDA_BUENA` de `scripts/auditar.py` no pueden derivar.

    Son dos copias del mismo objeto, en dos archivos, por dos motivos distintos: el auditor la
    lleva adentro para poder correr con el árbol vacío, y la suite la lee del disco. Que
    empiecen a decir cosas distintas es exactamente el defecto que este archivo previene, así
    que se ancla acá.
    """
    spec = importlib.util.spec_from_file_location("auditar", RAIZ / "scripts/auditar.py")
    modulo = importlib.util.module_from_spec(spec)
    # El registro en sys.modules va ANTES de ejecutarlo: las anotaciones de las dataclasses se
    # resuelven mirando `sys.modules[cls.__module__]`, y sin esto revienta al importar.
    sys.modules["auditar"] = modulo
    spec.loader.exec_module(modulo)
    assert salida_buena == modulo.SALIDA_BUENA, (
        f"pruebas/fixtures/{SALIDA_ESPERADA} y SALIDA_BUENA de scripts/auditar.py dejaron de "
        f"decir lo mismo. Decidí cuál manda y actualizá el otro."
    )


def test_las_salidas_que_escribio_la_suite_validan(validar) -> None:
    """Cada `salida*.json` de `pruebas/`, que es lo mismo que mira el chequeo 16 de la compuerta."""
    carpeta = RAIZ / "pruebas"
    encontrados = sorted(set(carpeta.rglob("salida*.json")) | set(carpeta.rglob("*.salida.json")))
    if not encontrados:
        pytest.skip(
            "todavía no hay salidas escritas en pruebas/ (`salida*.json`). Las escribe "
            "test_caso_01.py cuando `agente/` existe. El control negativo de este archivo "
            "corre igual."
        )
    for archivo in encontrados:
        rel = archivo.relative_to(RAIZ)
        documento = json.loads(archivo.read_text(encoding="utf-8"))
        assert validar(documento) == [], f"{rel} no valida contra salida.schema.json"
        assert enes(documento) == SEIS_PASOS, (
            f"{rel}: `pasos` trae {enes(documento)} y tiene que traer {SEIS_PASOS}. Alguien "
            f"filtró, reordenó o hizo append. Los seis se presiembran en agente/salida.py."
        )


# ─────────────────────────────────────────────────────────────────────────────
# El control negativo
# ─────────────────────────────────────────────────────────────────────────────


def mutaciones(buena: dict) -> list[tuple[str, dict]]:
    """Cinco salidas malas. Cada una tiene que rebotar contra el esquema."""

    sin_paso = copy.deepcopy(buena)
    sin_paso["pasos"] = sin_paso["pasos"][:5]

    score_alto = copy.deepcopy(buena)
    score_alto["calificacion"]["score"] = 101

    clave_rara = copy.deepcopy(buena)
    clave_rara["etapa_siguiente"] = "cerrar"

    estado_raro = copy.deepcopy(buena)
    estado_raro["estado"] = "listo"

    paso_cero = copy.deepcopy(buena)
    paso_cero["pasos"][0]["n"] = 0

    return [
        ("falta un paso", sin_paso),
        ("score 101", score_alto),
        ("clave desconocida", clave_rara),
        ("estado 'listo'", estado_raro),
        ("paso n=0", paso_cero),
    ]


# Los cinco nombres de `mutaciones()`, escritos otra vez porque la parametrización se resuelve
# antes que las fixtures y ahí no hay `salida_buena` para preguntárselos. Que las dos listas sigan
# diciendo lo mismo lo afirma `test_las_cinco_mutaciones_rebotan_todas`.
NOMBRES_DE_MUTACION = [
    "falta un paso",
    "score 101",
    "clave desconocida",
    "estado 'listo'",
    "paso n=0",
]


@pytest.mark.parametrize("nombre", NOMBRES_DE_MUTACION)
def test_la_mutacion_rebota(nombre: str, salida_buena: dict, validar) -> None:
    documento = dict(mutaciones(salida_buena))[nombre]
    assert validar(documento), (
        f"la mutación «{nombre}» pasó el validador, y tenía que rebotar. Mientras esto no "
        f"rebote, un reporte en verde no prueba nada: puede ser que no se esté validando nada."
    )


def test_las_cinco_mutaciones_rebotan_todas(salida_buena: dict, validar) -> None:
    """Las cinco juntas. Cuatro de cinco no alcanza: la que pasa es la que no se está mirando.

    Primero se cuentan, y después se afirma. `aceptadas == []` es cierto también cuando
    `mutaciones()` devolvió una lista vacía: ahí no rebota nada porque no se probó nada, y el
    verde se lee igual. La cuenta la fija el nombre de esta función.
    """
    todas = mutaciones(salida_buena)
    assert len(todas) == 5, (
        f"`mutaciones()` devolvió {len(todas)} y esta prueba afirma cinco. Con menos, el "
        f"`== []` de abajo pasa sin haber validado esa mutación una sola vez."
    )
    assert {nombre for nombre, _ in todas} == set(NOMBRES_DE_MUTACION), (
        f"los nombres de `mutaciones()` y los de la parametrización dejaron de coincidir: "
        f"{sorted(nombre for nombre, _ in todas)} contra {sorted(NOMBRES_DE_MUTACION)}. La "
        f"mutación que sólo está de un lado no la corre nadie."
    )

    aceptadas = [nombre for nombre, doc in todas if not validar(doc)]
    assert aceptadas == [], f"el validador aceptó {aceptadas}"


def test_seis_pasos_con_n_igual_a_uno_validan_y_por_eso_hace_falta_la_otra_asercion(
    salida_buena: dict, validar
) -> None:
    """La sexta mutación, la que el esquema **no** puede rechazar.

    Que valide no es un defecto del esquema: JSON Schema no tiene cómo decir «distintos y en
    orden» sobre seis objetos. Por eso la regla vive en código, acá y en el chequeo 16 de la
    compuerta, y por eso esta prueba afirma las dos mitades juntas.
    """
    documento = copy.deepcopy(salida_buena)
    documento["pasos"] = [dict(p, n=1) for p in documento["pasos"]]
    assert validar(documento) == [], "si el esquema ya lo rechaza, esta prueba sobra"
    assert enes(documento) != SEIS_PASOS


# ─────────────────────────────────────────────────────────────────────────────
# El esquema angosto, el que ve el modelo
# ─────────────────────────────────────────────────────────────────────────────


def test_las_salidas_del_stub_validan_contra_el_esquema_angosto() -> None:
    """El modelo de las pruebas dice lo que el modelo de verdad puede decir, y nada más.

    `agente/wire_schema.golden.json` es una copia verbatim de `plantillas/contratos/`. Mientras
    el build no exista se mide contra la plantilla, que es la fuente.
    """
    jsonschema = pytest.importorskip("jsonschema")
    golden = RAIZ / "agente/wire_schema.golden.json"
    if not golden.is_file():
        golden = RAIZ / "plantillas/contratos/wire_schema.golden.json"
    esquema = json.loads(golden.read_text(encoding="utf-8"))
    validador = jsonschema.Draft202012Validator(esquema)

    for nombre in (
        "canonica",
        "presupuesto_inventado",
        "presupuesto_con_evidencia_falsa",
        "resumen_largo",
        "objecion_fabricada",
        # Acá se le mira la salida; quien lo corre es
        # `test_vacio_el_ciclo_con_el_modelo_callado_no_manda_nada`, en pruebas/test_enviar.py. Un
        # stub que valida contra el esquema y no lo inyecta nadie no afirma ninguna conducta.
        "callado",
    ):
        salida = getattr(StubModel, nombre)().salida
        errores = [e.message for e in validador.iter_errors(salida)]
        assert errores == [], f"StubModel.{nombre}() no valida contra el esquema angosto: {errores}"
        assert tuple(salida) == CAMPOS_WIRE, (
            f"StubModel.{nombre}() emite {tuple(salida)}. El esquema angosto tiene once campos "
            f"y ninguno más: `pasos`, `enviado`, `escrito`, `cita`, `handoff` y "
            f"`horarios_ofrecidos` los decide el código."
        )


def test_el_esquema_angosto_no_le_pregunta_al_modelo_lo_que_decide_el_codigo() -> None:
    """Lo que no se pregunta no se puede mentir."""
    golden = RAIZ / "plantillas/contratos/wire_schema.golden.json"
    esquema = json.loads(golden.read_text(encoding="utf-8"))
    prohibidos = {
        "pasos",
        "estado",
        "enviado",
        "escrito",
        "cita",
        "handoff",
        "horarios_ofrecidos",
        "temperatura",
    }
    assert prohibidos.isdisjoint(esquema["properties"])


def test_el_fixture_de_la_salida_esperada_esta_donde_dice() -> None:
    """Y no se llama `salida*.json`, para no contarse como una salida del agente.

    El chequeo 16 de la compuerta busca `salida*.json` y `*.salida.json` adentro de `pruebas/`.
    Este archivo es el patrón del control negativo, no una corrida del agente: si entrara en ese
    glob, el auditor diría «2 salidas válidas» con el build sin construir.
    """
    archivo = FIXTURES / SALIDA_ESPERADA
    assert archivo.is_file()
    assert not archivo.name.startswith("salida")
    assert not archivo.name.endswith(".salida.json")
