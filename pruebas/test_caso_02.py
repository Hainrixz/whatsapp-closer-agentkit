"""Caso 02 · el camino de la escalación, en los dos modos y con los tres disparadores.

**Por qué corre también en `automatico`.** En `borrador` esta prueba sola no probaría nada: no
sale nada en ningún caso, y el verde sería idéntico con el paso 6 roto. El punto es que la
escalación calle al agente **aun cuando está autorizado a mandar**. Por eso todo lo de acá está
parametrizado sobre los dos modos: el de `automatico` es el que muerde, y el de `borrador` ancla
S11 —la línea de handoff no tiene vía rápida, se redacta y espera confirmación como cualquier
otro envío—.

**Por qué los envíos se cuentan en el transporte.** El bug que este archivo existe para atrapar
es el del paso 3 que redactó y mandó, y recién después corrió el 6. Un contador que lea lo que
el agente dice que hizo no lo ve. El doble de transporte sí.

**Ninguna aserción vive adentro de un `for` sin que antes se afirme que la lista trae algo.** Un
bucle sobre una lista vacía no corre, y lo de adentro se lee verde sin haberse ejecutado nunca:
así pasaban las tres aserciones del aviso interno, contra un build que no mandaba ninguno.

**Y la cuenta se afirma exacta, no contra otra cuenta.** «Los mismos avisos en los dos modos» es
cierto con dos y dos, y ahí lo que se ve del otro lado es el canal de escalaciones repitiendo todo.
Cada lista que sale del transporte se cuenta contra un número escrito, no contra su hermana.

**Y ninguna lista de lo que el fixture dice se escribe a mano acá.** Las palabras con las que el
contacto agrede se leen de los fixtures, no de una tupla pegada arriba: una tupla derivada del
`mensaje.texto` de un fixture no sabe nada del historial que ese mismo fixture trae al lado, y el
build que arrastra el historial al CRM le pasa por debajo.

Los tres fixtures salen del disco y llevan su historial al lado: el caso del enojo es el tercer
mensaje de una conversación, no el primero.

**El salteo no va a nivel de módulo.** `test_el_fixture_del_enojo_trae_el_agravio_en_las_dos_fuentes`
mira los fixtures y no toca el build, así que tiene que correr también con el árbol sin construir:
es lo único que avisa cuando el fixture y la aserción dejaron de decir lo mismo. Las otras piden
el build por la fixture `correr`, que saltea con el mismo motivo escrito. El conteo no se escribe
acá: lo imprime `pytest pruebas/test_caso_02.py --collect-only -q`.

**La variable del aviso la pone una fixture, con una URL inventada.** El paso 6 avisa por
`SLACK_WEBHOOK_URL` y sin esa variable queda `fallado` con el motivo (S09). Sin ponerla, un build
que hace exactamente lo que el blueprint prescribe se lleva ocho nodos rojos de este archivo, y la
única salida que le queda a quien construye es escribir una URL de webhook en el árbol. La pone
`slack_de_pruebas`; no es una credencial y nunca sale del proceso. Y lo que S09 promete lo afirma
`test_sin_la_variable_de_slack_el_paso_6_queda_fallado_con_el_motivo`, que la saca a propósito.
El `pytestmark` que la aplica es `usefixtures` y no un salteo: la fixture no pide el build, así
que el guardián de los fixtures sigue corriendo con el árbol sin construir.

**El aviso se afirma por dónde salió, no sólo por cuántos fueron.** `avisos` cuenta cualquier POST
a `hooks.slack.com`, así que un build que le manda todo a Slack y **nunca lee `canal_interno`**
pasaba los ocho nodos del aviso —los tres del canal de Slack y los cinco del número interno— sin
haber mirado el campo una sola vez. Con `canal_interno` en un número, el aviso tiene que ser un
mensaje a ese número y los POST a Slack tienen que ser cero. Eso es
`afirmar_el_destino_del_aviso()`, y lo usan las dos pruebas del aviso.

**Y las dos formas de `canal_interno` no se comportan igual, que es lo que esta ronda arregla.**
Un canal de Slack es un POST a `hooks.slack.com`: no es un mensaje de WhatsApp, no toca la
calificación del número y sale en los dos modos. Un número interno es un mensaje de WhatsApp con
todo lo que eso implica —Meta no distingue el número de tu compañero del de un cliente—, así que
cae bajo la promesa del modo: en `borrador` no sale, y en `automatico` sale por `enviar()`, con
plantilla aprobada y con `Idempotency-Key`. Hasta esta ronda salía en los dos modos, por el
endpoint de mensajería y sin ninguna de las cuatro guardas, y era la suite la que lo exigía así.
Ver `SUPUESTOS.md` S09 y S11, y `blueprint/31-proveedores.md` paso 1.
"""

from __future__ import annotations

import re
import unicodedata

import pytest

from pruebas.proveedor_falso import (
    SLACK_WEBHOOK_DE_PRUEBAS,
    ProveedorFalso,
    cargar,
    con,
    con_mensaje,
    numero_de_whatsapp,
    paso,
    sin_variable,
    slack_de_pruebas,  # noqa: F401 · fixture: se usa por nombre desde `pytestmark`
)

# Todo este archivo corre con `SLACK_WEBHOOK_URL` puesta. La única prueba que la necesita afuera
# se la saca ella misma, con `sin_variable()`.
pytestmark = pytest.mark.usefixtures("slack_de_pruebas")

MODOS = ["borrador", "automatico"]

# disparador → (fixture de entrada, fixture de historial, `handoff.motivo` esperado)
DISPARADORES = {
    "enojo": ("caso-02.entrada.json", "caso-02.historial.json", "enojo"),
    "precio": ("caso-02b.entrada.json", "caso-02b.historial.json", "precio_fuera_de_rango"),
    "palabra": ("caso-02c.entrada.json", "caso-02c.historial.json", "palabra_clave"),
}

# El cuarto mensaje del contacto, el que llega después de que el agente ya escaló.
CUARTO_MENSAJE = "¿Hola? Sigo esperando una respuesta."

# Las dos formas de `canal_interno` que permite `contratos/entrada.schema.json`: «un canal de
# Slack, o un número interno de WhatsApp si no hay Slack». La segunda sale por el mismo
# `/messages` que el mensaje al contacto, y es la que rompía el conteo mientras el corte del
# doble de transporte era por ruta. Los fixtures traen la primera, así que sin esta tabla el
# caso que el contrato documenta no lo prueba nadie.
CANALES = {
    "slack": "#ventas-escalaciones",
    "numero-interno": "5215500000099",
}

# Las raíces con las que se **reconoce** un agravio, en minúscula y sin tildes. Esto no es lo que
# la aserción busca en el resumen: lo que busca sale de los fixtures —el mensaje del turno y el
# historial entero— y lo arma `agravios_de()`. La lista escrita a mano sólo sabe reconocer; el
# fixture decide. Así, cambiar el insulto del fixture cambia la aserción, y las dos no pueden
# divergir. Un insulto nuevo que ninguna raíz reconozca pone roja a
# `test_el_fixture_del_enojo_trae_el_agravio_en_las_dos_fuentes`, que es el aviso de sumar la raíz
# acá, no un permiso para que el CRM lo copie.
RAICES_DE_AGRAVIO = (
    "porquer",
    "ladron",
    "ratero",
    "chorro",
    "estaf",
    "fraude",
    "basur",
    "mierd",
    "chant",
    "verguenz",
    "inutil",
    "incompetent",
)


def plano(texto: str | None) -> str:
    """Minúscula y sin tildes: «porquería» y «porqueria» son la misma palabra.

    El agravio no deja de serlo porque a quien lo escribió se le fue la tilde, y el resumen no
    deja de traerlo porque el build se la sacó.
    """
    descompuesto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def textos_del_historial(historial: dict) -> list[str]:
    """Lo que el contacto escribió antes de este turno.

    Las dos formas en las que el historial lo guarda: `conversacion.ultimo_entrante`, que es lo
    que un build lee para armar contexto rápido, y los `mensajes` con `direccion` en `entrante`.
    Lo saliente no entra: el agravio es del contacto.
    """
    conversacion = historial.get("conversacion") or {}
    previos = [
        m.get("texto") or ""
        for m in (historial.get("mensajes") or [])
        if m.get("direccion") == "entrante"
    ]
    return [t for t in [conversacion.get("ultimo_entrante") or "", *previos] if t.strip()]


def textos_del_contacto(entrada: dict, historial: dict) -> list[str]:
    """Las dos fuentes juntas: el mensaje de este turno y todo el historial."""
    del_turno = entrada["mensaje"].get("texto") or ""
    return ([del_turno] if del_turno.strip() else []) + textos_del_historial(historial)


def agravios_de(textos: list[str]) -> list[str]:
    """Las palabras con las que el contacto agrede, tal como están escritas en los fixtures.

    Devuelve la palabra entera y no la raíz, para que el mensaje del fallo diga qué se filtró al
    CRM. Se ordena para que el reporte sea estable entre corridas.
    """
    encontrados: dict[str, str] = {}
    for texto in textos:
        for palabra in re.findall(r"[^\W\d_]+", texto, flags=re.UNICODE):
            if any(raiz in plano(palabra) for raiz in RAICES_DE_AGRAVIO):
                encontrados.setdefault(plano(palabra), palabra)
    return [encontrados[clave] for clave in sorted(encontrados)]


def escalar(correr, disparador: str, modo: str, *, turnos: int = 1, canal: str | None = None,
            confirmado: bool = False):
    """Corre el caso hasta `turnos` mensajes del contacto y devuelve `(salidas, transporte)`."""
    entrada_json, historial_json, _ = DISPARADORES[disparador]
    base = con(cargar(entrada_json), modo=modo, confirmado=confirmado)
    if canal is not None:
        base = con(base, canal_interno=canal)
    entradas = [base]
    if turnos > 1:
        entradas.append(con_mensaje(base, texto=CUARTO_MENSAJE))
    return correr(entradas, historial=cargar(historial_json))


def contacto_de(entrada: dict) -> str:
    """El ancla de identidad: el `contacto_id`, que nunca falta. El número puede venir nulo."""
    return entrada["mensaje"]["contacto_id"]


def afirmar_el_destino_del_aviso(
    doble: ProveedorFalso, canal: str, *, donde: str, sale: bool = True
) -> None:
    """Que el aviso haya salido por donde dice `canal_interno`, y por ningún otro lado.

    Contar los avisos no alcanza. `avisos` toma por aviso cualquier POST a `hooks.slack.com` —el
    canal viaja adentro de la URL secreta y no hay otra cosa que mirar—, así que un build que
    **nunca lee `canal_interno`** y le manda todo a Slack cuenta uno en cada nodo y pasa entero,
    incluidos los cinco nodos que existen para el caso del número interno. Del otro lado, el
    equipo que puso un número de WhatsApp porque no tiene Slack no se entera de una sola
    escalación, y la suite lo dio por bueno.

    Por eso el destino se afirma en las dos direcciones: por dónde tenía que salir, y que por el
    otro camino no haya salido nada.

    **Del lado de Slack sólo hay una de las dos**, y es a propósito. El espejo —«y no salió nada
    por WhatsApp»— no se puede poner rojo: con un canal de Slack declarado, `numeros_internos`
    queda vacío y ninguna llamada puede entrar en `avisos_por_whatsapp`. Escrita igual, esa
    aserción sería un verde que no mira nada. El build que además le escribe a un número que nadie
    declaró se ve en el conteo de envíos, que lo cuenta como un mensaje al contacto: medido, se
    lleva los doce nodos de `test_sale_un_mensaje_...` y `test_el_cuarto_mensaje_...`.

    **`sale` es del número y no de Slack.** El aviso por Slack no es un mensaje de WhatsApp y no
    depende del modo: sale siempre, y por eso esa rama no lo mira. El del número sí depende, y con
    `sale=False` lo que se afirma es que no salió ninguno: es la promesa de `borrador` medida sobre
    la mitad que se le escapaba.
    """
    numero = numero_de_whatsapp(canal)

    if numero is None:
        assert len(doble.avisos_por_slack) == 1, (
            f"el `canal_interno` de {donde} es «{canal}», un canal de Slack, y salieron "
            f"{len(doble.avisos_por_slack)} POST a hooks.slack.com. El aviso sale por el webhook "
            f"entrante que trae `SLACK_WEBHOOK_URL`, una vez."
        )
        return

    assert doble.avisos_por_slack == [], (
        f"el `canal_interno` de {donde} es el número {canal} y el aviso salió igual a "
        f"hooks.slack.com. El build no está leyendo `canal_interno`: le manda todo a Slack y el "
        f"conteo de avisos da uno lo mismo. Quien puso un número porque no tiene Slack no se "
        f"entera de ninguna escalación."
    )

    if not sale:
        assert doble.avisos_por_whatsapp == [], (
            f"el `canal_interno` de {donde} es el número {canal} y salieron "
            f"{len(doble.avisos_por_whatsapp)} avisos por WhatsApp sin confirmación. Ese aviso es "
            f"un mensaje de WhatsApp: sale del número del negocio, cae bajo la ventana de 24 h y "
            f"pesa en la calificación igual que el que le llega a un cliente. En `borrador` no "
            f"sale nada por WhatsApp, y el aviso interno no es la excepción. Con un canal de "
            f"Slack sí sale, en los dos modos. Ver SUPUESTOS.md S09."
        )
        return

    # Que ese aviso vaya dirigido al número del `canal_interno` no se vuelve a afirmar: es lo que
    # lo pone en esta lista. `_va_al_canal()` compara el destinatario que el cuerpo declara contra
    # los `canal_interno` declarados, por dígitos, así que una aserción sobre el destino acá sería
    # cierta por construcción. Lo que sí puede fallar —y falla— es que la lista traiga cero.
    assert len(doble.avisos_por_whatsapp) == 1, (
        f"el `canal_interno` de {donde} es el número {canal} y salieron "
        f"{len(doble.avisos_por_whatsapp)} avisos por WhatsApp. Tenía que salir uno, por el mismo "
        f"`/messages` que el mensaje al contacto y dirigido a ese número. Con cero, lo más "
        f"probable es que `enviar()` se haya negado con «sin entrante de este contacto»: ese "
        f"número no te escribió nunca y no tiene por qué, y la exención de esa guarda para el "
        f"canal interno es lo que hace que este aviso exista. Ver blueprint/31-proveedores.md "
        f"paso 1."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Escala, y con el motivo que corresponde
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("disparador", list(DISPARADORES))
def test_escala_con_el_motivo_que_corresponde(correr, disparador: str, modo: str) -> None:
    salidas, _ = escalar(correr, disparador, modo)
    salida = salidas[0]
    _, _, motivo = DISPARADORES[disparador]

    assert salida["handoff"] is not None, "no escaló"
    assert salida["handoff"]["motivo"] == motivo
    assert salida["estado"] == "escalado"


@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("disparador", list(DISPARADORES))
def test_el_disparador_dice_que_lo_activo(correr, disparador: str, modo: str) -> None:
    """La palabra encontrada, o el monto que quedó fuera del rango. Nunca un texto fijo."""
    entrada_json, _, _ = DISPARADORES[disparador]
    salidas, _ = escalar(correr, disparador, modo)
    activador = salidas[0]["handoff"]["disparador"] or ""

    assert activador.strip(), "escaló sin decir qué lo activó"
    if disparador == "precio":
        assert "90000" in activador, (
            f"el disparador de precio tiene que traer el monto que quedó fuera del rango "
            f"{cargar(entrada_json)['rango_precio']}, y trae «{activador}»"
        )
    if disparador == "palabra":
        assert "humano" in activador.lower(), (
            f"el disparador de palabra clave tiene que traer la palabra encontrada, y trae "
            f"«{activador}»"
        )


@pytest.mark.parametrize("modo", MODOS)
def test_los_tres_disparadores_son_distintos(correr, modo: str) -> None:
    """Si los tres dicen lo mismo, está fijo y no lo sacó del mensaje."""
    activadores = [
        escalar(correr, d, modo)[0][0]["handoff"]["disparador"] for d in DISPARADORES
    ]
    assert len(set(activadores)) == 3, f"los tres escalaron con el mismo disparador: {activadores}"


@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("disparador", list(DISPARADORES))
def test_el_crm_queda_en_escalado(correr, disparador: str, modo: str) -> None:
    """La etapa es lo que el CRM va a mostrar cuando la fila se escriba.

    No es de dónde sale la memoria entre turnos: eso vive en la conversación, y por qué está en
    `test_el_cuarto_mensaje_despues_de_escalar_no_agrega_envios`. Acá se afirma la fila, que en
    `borrador` queda preparada y sin escribir.
    """
    salidas, _ = escalar(correr, disparador, modo)
    crm = salidas[0]["crm"]

    assert crm is not None, "escaló y no dejó nada para el CRM"
    assert crm["etapa"] == "escalado"
    if modo == "borrador":
        assert crm["escrito"] is False, "escribió la fila sin confirmación"


@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("disparador", list(DISPARADORES))
def test_el_resumen_del_crm_resume_y_no_devuelve_el_agravio(
    correr, disparador: str, modo: str
) -> None:
    """`crm.resumen` va a la fila del CRM y lo lee una persona del equipo, quizás meses después.

    Dos cosas se afirman acá. Que resuma: tres líneas, y nada del contacto pegado. Y que no le
    devuelva el agravio a nadie: el fixture del enojo trae un insulto, y con el resumen armado
    pegando lo que entró, ese insulto termina en la base y sale impreso en cada tablero que abra
    esa fila. Lo que va a la fila es qué pasó, no cómo lo dijo.

    **Las dos fuentes, y no una.** El insulto de este turno vive en `mensaje.texto`; el del
    tercer mensaje de la conversación vive en el historial, en `conversacion.ultimo_entrante` y
    en `mensajes`. Un build que arme el resumen arrastrando el historial no toca `mensaje.texto`
    ni una vez, así que una aserción derivada sólo del turno lo deja pasar entero: el fixture
    trae «son unos ladrones» ahí y en ningún otro lado.
    """
    entrada_json, historial_json, _ = DISPARADORES[disparador]
    fuentes = textos_del_contacto(cargar(entrada_json), cargar(historial_json))
    agravios = agravios_de(fuentes)

    salidas, _ = escalar(correr, disparador, modo)
    crm = salidas[0]["crm"]
    assert crm is not None, "escaló y no dejó nada para el CRM"

    resumen = crm.get("resumen") or ""
    assert resumen.strip(), "la fila del CRM quedó sin resumen: no le dice nada a quien la abra"
    lineas = [x for x in resumen.splitlines() if x.strip()]
    assert len(lineas) <= 3, f"el resumen trae {len(lineas)} líneas y son tres como mucho"

    llano = plano(resumen)

    assert fuentes, f"el fixture {entrada_json} no trae nada escrito por el contacto"
    for entrante in fuentes:
        assert plano(entrante) not in llano, (
            f"el resumen trae pegado tal cual algo que escribió el contacto: «{entrante}». Son "
            f"tres líneas —qué quería, qué se le respondió, qué falta—, no la conversación."
        )

    # El bucle de abajo recorre lo que el fixture trae. En `precio` y en `palabra` el contacto no
    # agrede y la lista es vacía con razón; en `enojo` no puede serlo, porque ese fixture existe
    # para traer el insulto. Sin esta línea, un fixture editado deja el bucle sin recorrer y el
    # verde no querría decir nada.
    if disparador == "enojo":
        assert agravios, (
            f"el fixture del enojo dejó de traer un agravio que `RAICES_DE_AGRAVIO` reconozca. "
            f"Lo que escribió el contacto es {fuentes}. Sumá la raíz que falta: mientras no "
            f"esté, este bucle recorre una lista vacía y se lee verde sin haber mirado nada."
        )
    for palabra in agravios:
        assert plano(palabra) not in llano, (
            f"«{palabra}» quedó escrito en el resumen que va al CRM. El agravio se lo queda la "
            f"conversación; la fila dice que se enojó y por qué escaló."
        )


def test_el_fixture_del_enojo_trae_el_agravio_en_las_dos_fuentes() -> None:
    """La guarda de la aserción de arriba. Mira los fixtures y no necesita el build.

    Tres cosas, y la tercera es la que importa. Que el mensaje del turno traiga un agravio. Que
    el historial traiga otro. Y que el del historial **no** esté ya en el mensaje del turno:
    mientras eso valga, una aserción derivada sólo del `mensaje.texto` no puede atrapar al build
    que arrastra `conversacion.ultimo_entrante` al `crm.resumen`, y por eso la derivación es de
    las dos fuentes.

    El día que alguien edite el fixture y deje las dos puntas iguales, esta prueba se pone roja
    acá —barata, sin build, con el motivo escrito— en vez de dejar la otra en verde por vacía.
    """
    entrada_json, historial_json, _ = DISPARADORES["enojo"]
    entrada, historial = cargar(entrada_json), cargar(historial_json)

    del_turno = agravios_de([entrada["mensaje"].get("texto") or ""])
    del_historial = agravios_de(textos_del_historial(historial))

    assert del_turno, (
        f"{entrada_json} dejó de traer un agravio en `mensaje.texto`. Es el fixture del enojo: "
        f"si el mensaje no agrede, el caso no prueba lo que dice probar."
    )
    assert del_historial, (
        f"{historial_json} dejó de traer un agravio. El historial es la fuente que toca el build "
        f"que arrastra `conversacion.ultimo_entrante` al resumen: sin agravio ahí, ese build pasa."
    )
    assert {plano(p) for p in del_historial} - {plano(p) for p in del_turno}, (
        f"el historial no agrega ningún agravio que el mensaje del turno no traiga ya: "
        f"{del_historial} contra {del_turno}. Con las dos puntas iguales, una aserción derivada "
        f"sólo del mensaje pasaría igual y no habría manera de ver la diferencia."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cuántos mensajes salen
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("disparador", list(DISPARADORES))
def test_sale_un_mensaje_en_automatico_y_ninguno_en_borrador(
    correr, disparador: str, modo: str
) -> None:
    """En `automatico`, exactamente uno: la línea de que lo sigue una persona.

    Dos mensajes quiere decir que el paso 3 redactó y mandó, y recién después corrió el 6. La
    escalación se decide antes de redactar, no después.

    En `borrador`, ninguno. Esa línea es un envío como cualquier otro y no tiene vía rápida
    (S11). Con `canal_interno` en un canal de Slack no se pierde nada: ese aviso no es un mensaje
    de WhatsApp, sale igual y el humano se entera. Con `canal_interno` en un número tampoco sale
    —es un mensaje de WhatsApp como éste—, y lo que queda es la escalación escrita en la salida,
    que se lee del panel. Los fixtures traen el canal de Slack; el otro caso lo cubren las dos
    pruebas del aviso.
    """
    salidas, doble = escalar(correr, disparador, modo)
    salida = salidas[0]

    if modo == "automatico":
        assert len(doble.envios) == 1, (
            f"salieron {len(doble.envios)} mensajes al contacto y tenía que salir uno solo: "
            f"{[e.ruta for e in doble.envios]}"
        )
        assert salida["respuesta"]["enviado"] is True
    else:
        assert doble.envios == [], (
            f"en borrador no sale nada, y salieron {len(doble.envios)}. S11: la línea de "
            f"handoff no saltea el borrador."
        )
        assert salida["respuesta"] is not None, "en borrador la línea queda redactada"
        assert salida["respuesta"]["texto"].strip()
        assert salida["respuesta"]["enviado"] is False


@pytest.mark.parametrize("canal", list(CANALES))
@pytest.mark.parametrize("disparador", list(DISPARADORES))
def test_el_aviso_interno_sale_por_donde_dice_canal_interno(
    correr, disparador: str, canal: str
) -> None:
    """Uno exacto, por el camino que corresponde a la forma del canal, y con el modo que le toca.

    Y lleva las tres cosas con las que un humano puede abrir el chat sin preguntar nada: quién
    es, por qué escaló y dónde seguirlo.

    **Uno exacto.** No «los mismos de los dos lados»: eso lo cumple un build que manda dos y dos
    —`2 == 2` es cierto— y lo que se ve del otro lado es el canal de escalaciones duplicando cada
    aviso hasta que alguien deja de mirarlo. Y no «al menos uno»: con eso el bucle de abajo corre,
    pero la cuenta que la escalación tiene que respetar —una escalación, un aviso— no la afirma
    nadie. Cero es el otro modo de fallar, y es el que además dejaba las tres aserciones de adentro
    sin ejecutarse una sola vez.

    **Y el modo que le toca a cada forma, que es lo que esta prueba dejó de dar por igual.** Antes
    se llamaba `test_el_aviso_interno_no_depende_del_modo` y exigía uno en los dos modos para las
    dos formas de canal. Con Slack eso sigue siendo cierto y es lo que hace que `borrador` no deje
    a nadie sin enterarse. Con un número interno era falso y encima peligroso: exigía que en
    `borrador` saliera un mensaje de WhatsApp —del número del negocio, bajo la ventana de 24 h y
    pesando en la calificación— en el modo cuya promesa entera es que no sale nada sin confirmar.
    La prueba anclaba el esquive como correcto. Ver `SUPUESTOS.md` S09 y S11.
    """
    entrada_json, _, motivo = DISPARADORES[disparador]
    entrada = con(cargar(entrada_json), canal_interno=CANALES[canal])
    por_slack = numero_de_whatsapp(CANALES[canal]) is None

    _, en_borrador = escalar(correr, disparador, "borrador", canal=CANALES[canal])
    _, en_automatico = escalar(correr, disparador, "automatico", canal=CANALES[canal])

    assert len(en_automatico.avisos) == 1, (
        f"escaló por {motivo} y salieron {len(en_automatico.avisos)} avisos a {CANALES[canal]} "
        f"en automatico, y tenía que salir uno. Con cero el humano no se entera por ningún otro "
        f"lado; con dos el canal de escalaciones se llena de repetidos."
    )
    esperados_en_borrador = 1 if por_slack else 0
    assert len(en_borrador.avisos) == esperados_en_borrador, (
        f"salieron {len(en_borrador.avisos)} avisos en borrador y tenían que ser "
        f"{esperados_en_borrador}. Con un canal de Slack el aviso sale igual —no es un mensaje de "
        f"WhatsApp y no espera confirmación—, y es lo que hace que en `borrador` la escalación no "
        f"quede muda. Con un número interno no sale: ese aviso es un mensaje de WhatsApp como "
        f"cualquier otro."
    )

    afirmar_el_destino_del_aviso(en_automatico, CANALES[canal], donde="automatico")
    afirmar_el_destino_del_aviso(en_borrador, CANALES[canal], donde="borrador", sale=por_slack)

    # El número puede venir nulo —`caso-02b` lo trae así a propósito, porque `phoneNumber` viene
    # nulo desde abril de 2026— y ahí el `contacto_id` es lo único que queda. Se lee como
    # alternativa **sólo cuando está**: con `(entrada["mensaje"]["de"] or "")` la aserción decía
    # `"" in cuerpo`, que es cierto contra cualquier cuerpo, y los dos nodos `[precio-*]` no se
    # podían poner rojos ni contra un aviso vacío.
    numero = entrada["mensaje"]["de"]
    for aviso in en_automatico.avisos:
        cuerpo = aviso.texto
        assert contacto_de(entrada) in cuerpo or (numero is not None and numero in cuerpo), (
            f"el aviso no dice de quién es: no trae el `contacto_id` «{contacto_de(entrada)}» ni "
            f"el número «{numero}». Quien lo lee tiene que poder abrir ese chat sin preguntar."
        )
        assert motivo in cuerpo, "el aviso no dice por qué escaló"
        assert "http" in cuerpo or "wa.me" in cuerpo, "el aviso no trae el enlace al chat"


@pytest.mark.parametrize("modo", MODOS)
def test_con_el_canal_interno_por_whatsapp_el_aviso_no_se_cuenta_como_envio(
    correr, modo: str
) -> None:
    """El caso que el contrato documenta y ningún fixture usa: `canal_interno` sin Slack.

    `contratos/entrada.schema.json` permite «un número interno de WhatsApp si no hay Slack». Ahí
    el aviso sale por el mismo `/messages` que el mensaje al contacto, y lo único que los separa
    es a quién van dirigidos. Con el corte por ruta, este caso contaba dos envíos y cero avisos:
    «exactamente un envío» se ponía rojo por algo que no es un bug del agente, y el aviso interno
    dejaba de auditarse sin que nadie lo viera.

    **Y el aviso tiene que haber salido por ahí.** Contarlo no alcanza: el conteo lo cumple igual
    un build que le manda todo a Slack sin leer `canal_interno` nunca, porque cualquier POST a
    `hooks.slack.com` cuenta como aviso. Ese build pasaba los ocho nodos del aviso —éstos dos y
    los seis de arriba— sin haber mirado el campo una sola vez.

    **En `borrador` la cuenta es cero y cero, y ésa es la mitad que faltaba.** Esta prueba pedía
    un aviso en los dos modos, así que un build que en `borrador` mandaba un mensaje de WhatsApp
    al número interno pasaba en verde: el esquive no era un defecto del build, lo exigía la suite.
    """
    canal = CANALES["numero-interno"]
    salidas, doble = escalar(correr, "enojo", modo, canal=canal)
    sale = modo == "automatico"

    assert salidas[0]["handoff"] is not None, "no escaló y el caso no aplica"
    assert len(doble.avisos) == (1 if sale else 0), (
        f"el aviso al número interno {canal} se contó {len(doble.avisos)} vez/veces en {modo}. El "
        f"corte entre envíos y avisos es por destino —al contacto o al canal interno—, y el modo "
        f"decide si ese aviso sale: por WhatsApp, en `borrador` no sale."
    )
    afirmar_el_destino_del_aviso(doble, canal, donde=f"el turno en {modo}", sale=sale)
    esperados = 1 if sale else 0
    assert len(doble.envios) == esperados, (
        f"salieron {len(doble.envios)} mensajes al contacto y tenían que ser {esperados}: "
        f"{[(e.ruta, (e.datos or {}).get('to')) for e in doble.envios]}"
    )


@pytest.mark.parametrize("canal", list(CANALES))
@pytest.mark.parametrize("disparador", list(DISPARADORES))
def test_en_borrador_no_sale_ni_un_mensaje_de_whatsapp(
    correr, disparador: str, canal: str
) -> None:
    """La promesa entera del modo, medida sobre la suma y no sobre una de las dos mitades.

    `borrador` promete una cosa sola: nada sale sin confirmación explícita. Las pruebas de arriba
    la afirmaban sobre `envios`, que son los mensajes al contacto, y el aviso al canal interno
    quedaba afuera de esa cuenta por ser aviso. Con `canal_interno` en un número eso no era una
    distinción, era un agujero: **del lado de Meta las dos mitades son la misma cosa.** Salen del
    mismo número de negocio, caen bajo la misma ventana de 24 horas y pesan lo mismo en la
    calificación. Medido contra el kit de la ronda anterior, en `borrador`: cero mensajes al
    contacto y **un** POST a `/inbox/conversations/interno-…/messages`, sin ventana, sin chequeo
    de baneo, sin la guarda de no escribir primero y sin `Idempotency-Key`.

    Por eso acá se cuenta `por_whatsapp`, que es la suma. Y por eso el canal de Slack está
    parametrizado al lado: ahí el aviso **sí** sale en `borrador`, y tiene que seguir saliendo. No
    es una excepción al modo, es que un POST a `hooks.slack.com` no es un mensaje de WhatsApp: no
    sale del número del negocio y no toca su calificación. Ver `SUPUESTOS.md` S09 y S11.
    """
    salidas, doble = escalar(correr, disparador, "borrador", canal=CANALES[canal])

    assert salidas[0]["handoff"] is not None, "no escaló y el caso no aplica"
    assert doble.por_whatsapp == [], (
        f"en `borrador`, con `canal_interno` en «{CANALES[canal]}», salieron "
        f"{len(doble.por_whatsapp)} mensajes de WhatsApp: "
        f"{[(ll.ruta, (ll.datos or {}).get('to')) for ll in doble.por_whatsapp]}. En ese modo no "
        f"sale nada por WhatsApp, ni al contacto ni a tu equipo. Si lo que salió es el aviso "
        f"interno, no alcanza con que sea interno: para Meta es un saliente del número del "
        f"negocio igual que cualquier otro."
    )

    if numero_de_whatsapp(CANALES[canal]) is None:
        assert len(doble.avisos_por_slack) == 1, (
            f"salieron {len(doble.avisos_por_slack)} avisos por Slack en `borrador` y tenía que "
            f"salir uno. El aviso por Slack no cambia con esta ronda: no es un mensaje de "
            f"WhatsApp, no espera confirmación, y es lo que hace que en `borrador` la escalación "
            f"no quede muda."
        )


# Las dos formas legítimas de que el aviso al número interno salga: el modo suelto, o la
# confirmación del turno. Son las mismas dos que dejan salir la línea del paso 3, y a propósito:
# ese aviso es un mensaje de WhatsApp y pasa por la misma compuerta.
CUANDO_SALE = {
    "automatico": ("automatico", False),
    "borrador-confirmado": ("borrador", True),
}


@pytest.mark.parametrize("cuando", list(CUANDO_SALE))
def test_el_aviso_al_numero_interno_sale_por_plantilla_y_con_clave_del_contenido(
    correr, cuando: str
) -> None:
    """Cuando el aviso por número sale, sale como lo que es: un mensaje de WhatsApp.

    Tres cosas, y las tres son de las que la suite casi no afirmaba: que **sí** pasan.

    **Que salga.** Ese número nunca le escribió al negocio —lo configuraste vos en Q9—, así que
    `enviar()` se niega ahí mismo si nadie eximió la guarda de no escribir primero. Medido sobre
    la rebanada, sin la exención: cero avisos y el motivo «sin entrante de este contacto: el
    agente contesta, no inicia». O sea que este `== 1` es lo que afirma que la exención existe, y
    es la única prueba que la puede poner en rojo.

    **Que salga con plantilla aprobada.** La contracara de la exención: la guarda no se saltea, se
    cambia por el mecanismo que WhatsApp da para que el negocio escriba primero. Sin entrante la
    ventana de 24 horas está cerrada, y con la ventana cerrada el texto libre no llega: vuelve
    `131047`, que es lo que un equipo con el canal en un número lee hoy en cada escalación.

    **Que salga con `Idempotency-Key`, y sacada del contenido.** El esquive salía sin ninguna. Se
    afirma corriendo la misma escalación dos veces, en dos bases distintas: la clave tiene que ser
    la misma. Con un uuid por intento son dos, y eso no es idempotencia, es un contador.
    """
    canal = CANALES["numero-interno"]
    modo, confirmado = CUANDO_SALE[cuando]

    _, primera = escalar(correr, "enojo", modo, canal=canal, confirmado=confirmado)
    _, segunda = escalar(correr, "enojo", modo, canal=canal, confirmado=confirmado)

    assert len(primera.avisos_por_whatsapp) == 1, (
        f"con el canal interno en {canal} y {cuando}, salieron "
        f"{len(primera.avisos_por_whatsapp)} avisos por WhatsApp y tenía que salir uno. Con cero, "
        f"`enviar()` se negó: ese número no te escribió nunca, y la exención declarada de esa "
        f"guarda para el canal interno es lo que hace que el aviso exista. Ver "
        f"blueprint/31-proveedores.md paso 1."
    )
    aviso = primera.avisos_por_whatsapp[0]

    assert aviso.es_plantilla, (
        f"el aviso al {canal} salió en texto libre: {aviso.ruta} · {aviso.texto[:120]}. Ese "
        f"número nunca escribió, así que su ventana de 24 h está cerrada y WhatsApp sólo acepta "
        f"plantillas aprobadas. En texto libre no llega: vuelve `131047` y la calificación del "
        f"número se gasta igual."
    )
    assert aviso.idempotency_key, (
        "el aviso al canal interno salió sin `Idempotency-Key`. Sale por `enviar()` como "
        "cualquier otro mensaje, y un reintento sin clave le llega dos veces a tu compañero."
    )
    assert aviso.idempotency_key == segunda.avisos_por_whatsapp[0].idempotency_key, (
        f"la misma escalación produjo dos claves distintas: «{aviso.idempotency_key}» y "
        f"«{segunda.avisos_por_whatsapp[0].idempotency_key}». La clave sale de la conversación, "
        f"el paso y el hash del cuerpo; con un uuid nuevo por intento no es idempotencia, es un "
        f"contador."
    )


def test_el_aviso_por_slack_sale_a_la_url_que_trae_la_variable(correr) -> None:
    """El aviso se postea a la URL de `SLACK_WEBHOOK_URL`, y a ninguna otra.

    Es lo que ata las dos puntas de la decisión de esta ronda. La suite pone una URL **inventada**
    por fixture —`SLACK_WEBHOOK_DE_PRUEBAS`, con `TEST` adentro de los dos identificadores— y el
    transporte doblado se la come sin abrir un socket: por eso el aviso se puede afirmar sin
    ninguna credencial y sin salir a la red.

    Lo que se pone rojo acá es el atajo que aparece cuando la suite no pone nada: un build con la
    URL del webhook escrita adentro del árbol. Ese build avisa —`len(avisos) == 1` le da—, y lo
    que hace es mandarle las escalaciones de todos a un canal que no es el de nadie, con la
    credencial versionada. Acá se ve, porque la URL no es la que entró por el entorno.
    """
    _, doble = escalar(correr, "enojo", "automatico", canal=CANALES["slack"])

    assert len(doble.avisos_por_slack) == 1, (
        f"salieron {len(doble.avisos_por_slack)} POST a hooks.slack.com y tenía que salir uno."
    )
    url = doble.avisos_por_slack[0].url
    assert url == SLACK_WEBHOOK_DE_PRUEBAS, (
        f"el aviso salió a «{url}» y la variable del entorno traía «{SLACK_WEBHOOK_DE_PRUEBAS}». "
        f"La URL del webhook llega por `SLACK_WEBHOOK_URL` y por ningún otro lado: escrita en el "
        f"árbol es una credencial versionada, y el canal es el de quien la escribió."
    )


@pytest.mark.parametrize("modo", MODOS)
def test_sin_la_variable_de_slack_el_paso_6_queda_fallado_con_el_motivo(correr, modo: str) -> None:
    """Lo que promete S09, afirmado: sin `SLACK_WEBHOOK_URL` se pierde el aviso, no el handoff.

    `blueprint/32-multimodal.md` paso 5 lo dice con todas las letras: sin la variable el paso 6
    queda `fallado` con el motivo, y el `handoff` igual queda escrito en la salida. `SUPUESTOS.md`
    S09 dice la otra mitad, la del campo: `avisado_en` queda nulo, y lo que se pierde es el aviso
    y no el handoff. Las dos mitades se afirman acá. Es la conducta que decide si una escalación
    sin Slack configurado se lee del panel o se pierde entera, y hasta acá no la afirmaba nadie.

    Las formas de fallar que esto atrapa, todas medidas contra un build que las tiene. El que
    marca el paso 6 en `hecho` sin haber avisado: la salida dice que el equipo se enteró y no se
    enteró nadie. El que sella `avisado_en` con la hora igual, que es lo mismo un campo más abajo.
    El que se cae con la excepción sin escribir el `handoff`: se pierde la escalación por no tener
    configurado un aviso, que es al revés de lo que corresponde. Y el que falla con un motivo que
    no nombra la variable, que deja a quien lo lee sin saber qué poner.

    La variable se saca con `sin_variable()`, que además olvida el build: los ajustes se leen al
    importar, así que sacarla del entorno sin volver a importar no cambia nada.
    """
    with sin_variable("SLACK_WEBHOOK_URL"):
        salidas, doble = escalar(correr, "enojo", modo, canal=CANALES["slack"])
    salida = salidas[0]

    assert salida["handoff"] is not None, (
        "sin `SLACK_WEBHOOK_URL` no quedó `handoff` en la salida. Lo que se pierde sin la "
        "variable es el aviso, no la escalación: el agente deja de contestar igual y alguien "
        "tiene que poder leer del panel que este chat escaló."
    )
    assert doble.avisos == [], (
        f"sin la variable salieron {len(doble.avisos)} avisos. Sin webhook no hay a dónde "
        f"mandarlo, y una URL de reserva escrita en el código sería una credencial en el árbol."
    )

    seis = paso(salida, 6)
    assert seis["estado"] == "fallado", (
        f"sin `SLACK_WEBHOOK_URL` el paso 6 quedó en «{seis['estado']}» y tenía que quedar en "
        f"`fallado`. En `hecho` la salida dice que el equipo se enteró de la escalación, y no se "
        f"enteró nadie: es la diferencia entre un aviso perdido y un aviso perdido en silencio."
    )
    assert "SLACK_WEBHOOK_URL" in (seis.get("motivo") or ""), (
        f"el paso 6 falló con el motivo «{seis.get('motivo')}», que no nombra la variable que "
        f"falta. El motivo se lee del panel y tiene que decir qué poner para que el próximo "
        f"aviso salga."
    )
    assert salida["handoff"].get("avisado_en") is None, (
        f"`handoff.avisado_en` quedó en «{salida['handoff'].get('avisado_en')}» y no salió "
        f"ningún aviso. Ese campo es la hora en la que se avisó; con algo adentro, quien abra la "
        f"fila lo da por avisado."
    )


# ─────────────────────────────────────────────────────────────────────────────
# El silencio posterior, que sólo se ve en dos turnos
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("disparador", list(DISPARADORES))
def test_el_cuarto_mensaje_despues_de_escalar_no_agrega_envios(
    correr, disparador: str, modo: str
) -> None:
    """Después de escalar, el agente no vuelve a escribir en ese chat, ni para despedirse.

    Los dos turnos corren adentro del mismo bucle y sobre la misma base en memoria. Eso es lo
    que hace que el segundo sepa del primero, y **lo que el segundo lee es la conversación, no
    el CRM**: el paso 6 la marca cuando escala —instante, motivo y disparador— y el paso 1 del
    turno siguiente la lee y deja el 3 en `salteado`. Sin memoria entre turnos el silencio no se
    sostiene, y ése es el bug que este caso existe para atrapar.

    **Por qué no puede ser el CRM**, que es el atajo que aparece solo: la fila la escribe el paso
    5, y en `borrador` el paso 5 no escribe nada —`crm.escrito` en falso—. Un ciclo que pregunte
    por la etapa `escalado` de la tabla `leads` calla en `automatico` y contesta en `borrador`, o
    sea que falla justo en el modo que trae puesto el kit, y se lleva los tres nodos
    `[*-borrador]` de esta prueba y ninguno de los `[*-automatico]`. `crm.etapa` sigue diciendo
    `escalado` y se sigue afirmando en `test_el_crm_queda_en_escalado`: es lo que el CRM va a
    mostrar cuando se escriba, no la memoria entre turnos. Ver `blueprint/40-pruebas.md` paso 5.

    En `borrador` el contador de envíos vale cero por otro motivo —no manda nunca—, así que la
    aserción que muerde ahí es la segunda: tampoco redacta una respuesta nueva.
    """
    salidas, doble = escalar(correr, disparador, modo, turnos=2)
    primero, segundo = salidas

    assert primero["handoff"] is not None, "el primer turno no escaló y el caso no aplica"

    esperados = 1 if modo == "automatico" else 0
    assert len(doble.envios) == esperados, (
        f"después de escalar salieron {len(doble.envios)} mensajes en total y tenían que ser "
        f"{esperados}. El segundo turno contestó: el ciclo no está leyendo de la conversación "
        f"que este chat ya escaló. Si esto cae sólo en `[*-borrador]`, lo estás leyendo del CRM, "
        f"y en ese modo la fila no se escribió."
    )

    assert segundo["estado"] == "escalado"
    assert segundo["respuesta"] is None or segundo["respuesta"]["enviado"] is False
    assert paso(segundo, 3)["estado"] == "salteado", (
        "el paso 3 no se saltea en el segundo turno. Desde acá no se contesta más en este chat."
    )
