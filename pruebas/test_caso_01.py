"""Las aserciones de `pruebas/caso-01.md`, una función por aserción numerada.

El nombre de cada función lleva el número del paso adelante. Cuando el reporte se pone rojo, la
línea que falla nombra el paso roto y no hay que abrir nada para saber por dónde empezar.

La entrada sale de `pruebas/fixtures/caso-01.entrada.json` y nunca de un literal pegado acá. Si
alguien edita la prosa de `caso-01.md`, el extractor mueve el fixture y estas pruebas se mueven
con él.

Lo que este archivo **no** afirma, porque `caso-01.md` lo excluye: el texto exacto que redacta el
modelo, los tiempos de ejecución y cualquier cosa que dependa de una credencial real.

**«Exacto» y «que venga del modelo» no son lo mismo**, y la exclusión es sólo la primera. Afirmar
el texto ata la suite a una versión del modelo y la rompe el día que se sube el pin; no afirmar
nada deja pasar al build que descarta lo que el modelo devolvió y manda una línea enlatada, que es
un agente que no redacta. La procedencia se afirma con una marca que el stub pone adentro del
texto y que el paso 3 tiene que dejar salir; el resto del texto no se mira. Ver
`MARCA_DEL_STUB`.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from pruebas.proveedor_falso import (
    ProveedorFalso,
    StubModel,
    cargar,
    con_mensaje,
    motivo_sin_ciclo,
    paso,
)

pytestmark = pytest.mark.skipif(bool(motivo_sin_ciclo()), reason=motivo_sin_ciclo())

SEIS_PASOS = [1, 2, 3, 4, 5, 6]

# La marca de procedencia. Va adentro de una frase que se lee como cualquier otra respuesta, para
# que el paso 3 la trate igual que a un texto de verdad, y no se parece a nada que un build pueda
# haber escrito de memoria. Se afirma que **aparezca**, no que el texto sea igual: el paso 3 puede
# pegarle los horarios abajo o recortarlo, y eso no es lo que está en discusión.
MARCA_DEL_STUB = "referencia BR-7Q4Z"
TEXTO_DEL_STUB = (
    f"El curso sale 12000 MXN y se puede en tres partes ({MARCA_DEL_STUB}). "
    f"¿Te va alguno de estos horarios?"
)


def instante(cadena: str) -> datetime:
    """Un `date-time` del contrato como instante, para comparar sin pelear con el formato.

    `2026-03-02T11:00:00-06:00` y `2026-03-02T17:00:00Z` son el mismo momento. Comparar las
    cadenas convertiría un cambio de formato en un fallo, y eso no es lo que se está afirmando.
    """
    return datetime.fromisoformat(cadena)


# ─────────────────────────────────────────────────────────────────────────────
# 1 · Recibí
# ─────────────────────────────────────────────────────────────────────────────


def test_1_el_contacto_es_nuevo_y_se_indexa_por_contacto_id(
    salida_caso_01: dict, entrada_caso_01: dict
) -> None:
    """Indexa por `contacto_id`, no por `numero`: el teléfono puede faltar y el ancla no."""
    contacto = salida_caso_01["contacto"]
    assert contacto["id"] == entrada_caso_01["mensaje"]["contacto_id"]
    assert contacto["nuevo"] is True
    assert contacto["mensajes_previos"] == 0
    assert contacto["numero"] == entrada_caso_01["mensaje"]["de"]
    assert paso(salida_caso_01, 1)["estado"] == "hecho"


@pytest.mark.parametrize(
    "forma",
    [
        "sin media_id ni media_url",
        "media_url caducado",
        "media_id que devuelve 400",
    ],
)
def test_1_un_audio_sin_forma_de_conseguir_los_bytes_se_detiene_con_el_motivo(
    entrada_caso_01: dict, correr, forma: str
) -> None:
    """Tres formas de no conseguir los bytes, y las tres frenan igual.

    La tercera no se recupera nunca: Meta suelta el archivo a los pocos días y desde ahí la
    bajada devuelve 400 para siempre. Por eso el medio se baja al recibirlo y no cuando hace
    falta. Y un `media_id` no se le pasa jamás a una API de visión: sin la credencial puesta
    devuelve 401, que es otro modo de adivinar.
    """
    campos = {"tipo": "audio", "texto": None, "media_local": None}
    transporte = ProveedorFalso()
    if forma == "sin media_id ni media_url":
        campos |= {"media_id": None, "media_url": None}
    elif forma == "media_url caducado":
        campos |= {"media_id": None, "media_url": "https://lookaside.example/caducado"}
        transporte = ProveedorFalso(responder=lambda r: (410, {"error": "expired"}))
    else:
        campos |= {"media_id": "1234567890", "media_url": None}
        transporte = ProveedorFalso(responder=lambda r: (400, {"error": "media not found"}))

    salidas, doble = correr([con_mensaje(entrada_caso_01, **campos)], transporte=transporte)
    salida = salidas[0]

    assert salida["estado"] == "detenido", (
        "con un audio que no se puede bajar, el ciclo no arranca. Adivinar qué decía el audio "
        "es fallo aunque la respuesta suene bien."
    )
    assert paso(salida, 1)["estado"] == "fallado"
    assert paso(salida, 1)["motivo"], "el paso 1 falló sin decir por qué"
    assert doble.envios == [], "se detuvo y le escribió igual"
    assert salida.get("respuesta") is None or salida["respuesta"]["enviado"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 2 · Calificá
# ─────────────────────────────────────────────────────────────────────────────


def test_2_el_score_va_de_0_a_100_y_la_temperatura_sigue_a_los_umbrales(
    salida_caso_01: dict, entrada_caso_01: dict
) -> None:
    umbrales = entrada_caso_01.get("umbrales") or {}
    caliente = umbrales.get("caliente", 70)
    tibio = umbrales.get("tibio", 40)

    calificacion = salida_caso_01["calificacion"]
    score = calificacion["score"]
    assert isinstance(score, int) and 0 <= score <= 100

    esperada = "caliente" if score >= caliente else "tibio" if score >= tibio else "frio"
    assert calificacion["temperatura"] == esperada, (
        f"score {score} con cortes {caliente}/{tibio} da «{esperada}» y la salida dice "
        f"«{calificacion['temperatura']}». Los cortes salen de `umbrales` en la entrada."
    )
    assert paso(salida_caso_01, 2)["estado"] == "hecho"


def test_2_un_presupuesto_sin_evidencia_en_el_mensaje_se_fuerza_a_nulo(
    entrada_caso_01: dict, correr
) -> None:
    """Prueba la guarda, no el modelo.

    El stub declara 15000 y el mensaje del caso no trae ninguna cifra. `anclar_presupuesto()`
    exige una subcadena literal del mensaje con cifras adentro; sin eso tira el presupuesto a
    nulo y escribe el descarte. **Invariante 5**: lo que no está en el mensaje ni en el
    catálogo, no existe.

    La prueba tiene dos mitades y las dos hacen falta. Sin la segunda, un build que devuelva
    `presupuesto` en nulo siempre pasaría la primera sin verificar nada, y la guarda quedaría
    sin evidencia.
    """
    salidas, _ = correr([entrada_caso_01], modelo=StubModel.presupuesto_inventado())
    calificacion = salidas[0]["calificacion"]

    assert calificacion["presupuesto"] is None, (
        "el modelo dijo 15000 y el mensaje no trae ninguna cifra. Inventar un número es fallo "
        "aunque el score quede razonable."
    )
    assert calificacion["motivo"], "se descartó el presupuesto y no quedó escrito por qué"

    # La otra mitad: con el monto dicho en el mensaje y la cita literal al lado, sobrevive.
    con_cifra = cargar("caso-02b.entrada.json")
    evidencia = "Tengo 90000 para invertir"
    assert evidencia in con_cifra["mensaje"]["texto"], "el fixture cambió y la cita ya no está"
    salidas, _ = correr(
        [con_cifra],
        modelo=StubModel.presupuesto_con_evidencia_real(90000, evidencia),
        historial=cargar("caso-02b.historial.json"),
    )
    assert salidas[0]["calificacion"]["presupuesto"] == 90000, (
        "el monto está dicho en el mensaje y la cita es literal. Tirarlo a nulo acá quiere "
        "decir que el ancla no mira la evidencia: descarta siempre."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3 · Respondé
# ─────────────────────────────────────────────────────────────────────────────


def test_3_en_borrador_y_sin_confirmar_redacta_y_no_manda(
    entrada_caso_01: dict, correr
) -> None:
    """Antes de mandar, pregunta. Se cuentan los envíos que vio el transporte, no los que el
    agente dice que hizo.

    Y lo que queda redactado es lo que devolvió el modelo. `texto.strip()` sola no lo dice: la
    cumple igual un build que descarta `wire["texto"]` y deja una línea fija, que pasa la suite
    entera y en producción contesta lo mismo a todo el mundo. Por eso el stub redacta con una
    marca adentro y acá se exige que aparezca. **No se afirma el texto**: no se compara contra
    `TEXTO_DEL_STUB`, ni se mide el largo, ni se mira una palabra que el modelo haya elegido.
    Sólo que lo que salió pasó por lo que el modelo devolvió.
    """
    assert entrada_caso_01["modo"] == "borrador"
    assert entrada_caso_01["confirmado"] is False

    salidas, doble = correr([entrada_caso_01], modelo=StubModel.otro_texto(TEXTO_DEL_STUB))
    salida = salidas[0]

    assert salida["respuesta"] is not None, "el paso 3 no dejó el texto redactado"
    assert salida["respuesta"]["texto"].strip(), "redactó un texto vacío"
    assert MARCA_DEL_STUB in salida["respuesta"]["texto"], (
        f"el texto redactado no trae «{MARCA_DEL_STUB}», que es lo único que el modelo puso en "
        f"esta corrida. Lo que quedó redactado es «{salida['respuesta']['texto']}»: el paso 3 "
        f"descartó lo que devolvió el modelo y escribió por su cuenta. Una plantilla fija pasa "
        f"todo lo demás de esta suite y contesta lo mismo a todos los contactos."
    )
    assert salida["respuesta"]["enviado"] is False
    assert doble.envios == [], (
        f"salieron {len(doble.envios)} mensajes sin confirmación. Un envío sin confirmar es "
        f"fallo aunque el texto esté perfecto."
    )
    assert paso(salida, 3)["estado"] == "sin-confirmar"


def test_3_ofrece_exactamente_tres_horarios_y_todos_salen_de_disponibilidad(
    salida_caso_01: dict, entrada_caso_01: dict
) -> None:
    """Un horario que no esté en `disponibilidad` es fallo, aunque el mensaje esté perfecto."""
    cuantos = entrada_caso_01.get("opciones_horario", 3)
    libres = {instante(h["inicio"]) for h in entrada_caso_01["disponibilidad"]}
    ofrecidos = salida_caso_01["respuesta"]["horarios_ofrecidos"]

    assert len(ofrecidos) == cuantos, (
        f"`opciones_horario` pide {cuantos} y el paso 3 ofreció {len(ofrecidos)}"
    )
    assert len(set(ofrecidos)) == len(ofrecidos), "ofreció el mismo horario dos veces"

    inventados = [h for h in ofrecidos if instante(h) not in libres]
    assert inventados == [], (
        f"{inventados} no está en `disponibilidad`. Los horarios salen de ahí y de ningún otro "
        f"lado."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4 · Agendá
# ─────────────────────────────────────────────────────────────────────────────


def test_4_sin_confirmacion_no_hay_cita(salida_caso_01: dict) -> None:
    """Antes de agendar, pregunta."""
    assert salida_caso_01["cita"] is None
    assert paso(salida_caso_01, 4)["estado"] == "sin-confirmar"


# ─────────────────────────────────────────────────────────────────────────────
# 5 · CRM
# ─────────────────────────────────────────────────────────────────────────────


def test_5_sin_confirmacion_no_se_escribe_la_fila(salida_caso_01: dict) -> None:
    """Antes de escribir en el CRM, pregunta.

    `crm` puede venir nulo o venir con el borrador de la fila adentro. Lo que no puede es venir
    con `escrito` en verdadero: eso quiere decir que la fila se escribió sin confirmación.
    """
    crm = salida_caso_01["crm"]
    if crm is not None:
        assert crm.get("escrito") is False
        if crm.get("resumen"):
            lineas = [x for x in crm["resumen"].splitlines() if x.strip()]
            assert len(lineas) <= 3, (
                f"el resumen trae {len(lineas)} líneas. Son tres: qué quería, qué se le "
                f"respondió, qué falta. Pegar la conversación entera es fallo."
            )
    assert paso(salida_caso_01, 5)["estado"] == "sin-confirmar"


# ─────────────────────────────────────────────────────────────────────────────
# 6 · Handoff
# ─────────────────────────────────────────────────────────────────────────────


def test_6_no_escala_y_la_salida_valida_con_estado_parcial(
    salida_caso_01: dict, entrada_caso_01: dict, validar
) -> None:
    """Con esta entrada no hay enojo, el precio cae dentro del rango y no aparece ninguna
    palabra de la lista."""
    assert salida_caso_01["handoff"] is None
    assert paso(salida_caso_01, 6)["estado"] == "salteado"

    assert [p["n"] for p in salida_caso_01["pasos"]] == SEIS_PASOS
    assert salida_caso_01["estado"] == "parcial", (
        "tres pasos quedaron sin confirmar, así que el estado es `parcial`. `ok` acá querría "
        "decir que algo destructivo corrió sin confirmación."
    )
    assert validar(salida_caso_01) == []

    # El precio del catálogo cae adentro del rango, que es por qué el disparador de precio no
    # se activa. Se afirma acá para que el día que alguien cambie el fixture se vea el motivo.
    precio = entrada_caso_01["catalogo"][0]["precio"]
    rango = entrada_caso_01["rango_precio"]
    assert rango["minimo"] <= precio <= rango["maximo"]

    # La otra mitad de la aserción 6 —cambiar el texto por uno que pida un humano y ver que
    # escala— vive en `pruebas/test_caso_02.py`, con los tres disparadores y en los dos modos.
    # Repetirla acá daría dos verdes por una sola conducta probada.
