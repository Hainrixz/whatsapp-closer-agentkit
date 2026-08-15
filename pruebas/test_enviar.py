"""Las guardas de `enviar()`, cada una en las dos direcciones.

`pruebas/proveedor_falso.py` justifica su diseño entero con esto: un doble que reemplace
`enviar()` deja afuera la ventana de 24 horas, el chequeo de baja y la regla de no escribir
primero, porque las tres viven adentro de `enviar()`. Éste es el archivo que las afirma. Sin él,
el doble envuelve el transporte para ejercitar unas guardas que después no mira nadie, y un build
que escribe fuera de la ventana —o a quien pidió la baja, o a quien nunca escribió— pasa la suite
entera con la compuerta en verde.

**Son cinco reglas y un límite, no tres.** De los cuatro tiempos de `enviar()`, los tres primeros
son guardas: nunca escribir primero (regla 3, tiempo 1), la ventana de 24 horas (regla 1, tiempo
2) y el chequeo de baneo (tiempo 3). El chequeo de baneo es `revisar_baneo()`, y adentro tiene
cinco ramas: el texto vacío, la baja (regla 2), el mismo texto otra vez (regla 4), la insistencia
sin respuesta (regla 5) y el límite de 4096 caracteres —que el blueprint marca aparte a propósito,
«esto no es baneo, es un 400», y por eso acá tampoco lleva número—.

Las tres últimas se pueden borrar dejando `return None`, y hasta esta ronda la suite entera salía
verde con la compuerta en `pass`. Un build que le manda el mismo mensaje tres veces seguidas a
alguien que no contesta pasaba sin una sola aserción roja.

**Y la primera igual, hasta esta ronda.** La rama del texto vacío se borraba entera y no caía
nada: `pytest` seguía dando las mismas 154 y la compuerta seguía en `pass`. Las otras cuatro ya
tenían su nodo; ésa no tenía ninguno. Y no es cosmética. Sin ella `enviar(texto=None)` deja de
devolver un `Resultado` y revienta adentro de `revisar_baneo()` con `AttributeError: 'NoneType'
object has no attribute 'encode'`: el paso que llame con el texto en nulo se lleva puesto el ciclo
entero en vez de recibir una negativa como dato, que es lo contrario de lo que promete `Resultado`.

El texto en nulo no es un caso de laboratorio: llega cuando el modelo no redacta nada para ese
turno. Ese caso lo produce `StubModel.callado()`, que estaba escrito y sólo se validaba contra el
esquema angosto en `pruebas/test_contrato.py`. Acá se lo inyecta en el ciclo, que es para lo que
fue escrito.

El chequeo 13 `enviar-unico` prueba que hay **una sola puerta**. Acá se prueba que la puerta
**mire** algo. Son dos afirmaciones distintas y hacen falta las dos.

Lo que se pierde cuando una de las cinco falla no es una respuesta: es el número de WhatsApp del
negocio, y recuperarlo son semanas. La especificación de todas está en
`blueprint/31-proveedores.md`, paso 1, y en ningún otro archivo.

**Por qué se llama a `enviar()` y no al ciclo.** `ahora` entra por parámetro justamente para esto:
sin él la ventana no se puede probar sin esperar 24 horas. Y hay un motivo más fuerte. Un ciclo lo
dispara un mensaje entrante, o sea que la ventana se acaba de abrir: la ventana **cerrada** no se
alcanza por ese camino en ningún build sano, y exigirla desde el ciclo sería exigir una conducta
que el ciclo no tiene —y contradecir a `pruebas/test_caso_02.py`, que cuenta un envío por
escalación con esos mismos fixtures—. El camino real de la ventana cerrada es el recordatorio del
paso 4, que sale 24 horas antes de la cita y sin ningún entrante nuevo. Lo único que sube al nivel
del ciclo es el campo del contrato, `respuesta.ventana_abierta`, y en la dirección que el ciclo sí
alcanza.

**Los instantes salen de los fixtures.** `window_expires_at`, `baja_en`, `ultimo_saliente_hash` y
`salientes_seguidos` ya estaban en los tres historiales de `pruebas/fixtures/` y no los leía
ninguna prueba. Acá se leen: el «dentro» y el «fuera» son una hora antes y una hora después de lo
que dice el fixture, así que no dependen del reloj de la máquina y no envejecen.

**Eso vale para lo que se llama con `ahora=`, y los dos nodos que corren el ciclo no lo tienen.**
El ciclo no recibe `ahora`: lee el reloj —`blueprint/40-pruebas.md` paso 2— y `mensaje.recibido_en`
es cuándo llegó el mensaje, no qué hora es. Por eso la suite entera corre parada en el instante del
corpus, que lo deja puesto `parado_en_el_instante_del_corpus` de `pruebas/conftest.py`. Que esté
puesto de verdad lo afirma el primer nodo de este archivo, y no un comentario: sin él, los dos
nodos del ciclo se ponen rojos el día que alguien saque `freezegun`, y el rojo se lee como un
defecto del build.

**El cuarto historial es nuevo y existe por una sola razón.** Los tres del caso 02 traen
`salientes_seguidos` en cero, que es el valor que garantiza que la rama de la insistencia no corra
nunca; moverlos rompería las direcciones «sale» de todo este archivo. Así que la insistencia trae
el suyo, `historial-insistencia.json`, con el contador en el umbral. Los tres viejos siguen
clavados en cero y el nuevo clavado en el umbral: eso lo afirma
`test_los_historiales_traen_los_campos_que_estas_pruebas_leen`, fixture por fixture.

**Cada aserción nombra su regla.** Quien lea el rojo a las tres de la mañana tiene que saber cuál
de las cinco se rompió y en qué cuerpo se arregla, sin abrir ningún otro archivo.

**El salteo no va a nivel de módulo.** `test_los_historiales_traen_los_campos_que_estas_pruebas_leen`
mira los fixtures y no toca el build, así que corre también con el árbol sin construir: es lo único
que avisa cuando el fixture y estas aserciones dejaron de decir lo mismo. Las demás piden el build
por las fixtures `mandar` y `correr`, que saltean con el motivo escrito, una prueba a la vez. El
número de nodos no se escribe acá: lo imprime `pytest pruebas/test_enviar.py --collect-only -q`.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
from datetime import datetime, timedelta, timezone

import pytest

from pruebas.conftest import instante_del_corpus
from pruebas.proveedor_falso import (
    FIXTURES,
    RAIZ,
    ProveedorFalso,
    SinAgente,
    StubModel,
    armar_deps,
    cargar,
    con,
    enchufar_transporte,
    huella,
    motivo_sin_ciclo,
    motivo_sin_servidor,
    paso,
    sembrar,
)

# ─────────────────────────────────────────────────────────────────────────────
# Las cinco reglas y el límite, con el nombre que va a salir impreso cuando alguno se rompa
# ─────────────────────────────────────────────────────────────────────────────

VENTANA = "regla 1 · la ventana de 24 horas"
BAJA = "regla 2 · a quien pidió la baja no se le escribe"
PRIMERO = "regla 3 · nunca escribir primero"
REPETIDO = "regla 4 · el mismo texto no se manda dos veces"
INSISTENCIA = "regla 5 · sin respuesta no se insiste más"

# Las dos ramas de `revisar_baneo()` que no llevan número, porque ninguna de las dos es una regla
# de baneo. Son los dos bordes de la misma función: por abajo, el texto que no existe; por arriba,
# el que no entra. Viven ahí porque `enviar()` es el único lugar por donde sale un texto.
#
# La de abajo es además la que hace que un texto en nulo vuelva como `Resultado` en vez de reventar
# adentro de `revisar_baneo()` al hashearlo.
VACIO = "el texto vacío"

# El 400 que devuelve WhatsApp.
LIMITE = "el límite de 4096 caracteres"

# En qué tiempo de `enviar()` vive cada una. El cuerpo está escrito entero en
# `blueprint/31-proveedores.md`, paso 1, y ahí las cuatro etapas están numeradas. Las tres últimas
# son ramas de `revisar_baneo()`, que es lo que el tiempo 3 llama.
TIEMPO = {
    VENTANA: "tiempo 2",
    BAJA: "tiempo 3",
    PRIMERO: "tiempo 1",
    REPETIDO: "tiempo 3, adentro de `revisar_baneo()`",
    INSISTENCIA: "tiempo 3, adentro de `revisar_baneo()`",
    VACIO: "tiempo 3, adentro de `revisar_baneo()`",
    LIMITE: "tiempo 3, adentro de `revisar_baneo()`",
}


def roto(regla: str, detalle: str) -> str:
    """El mensaje de un fallo. Nombra la regla, no «el envío»."""
    return (
        f"\nGUARDA ROTA · {regla}\n{detalle}\n"
        f"Se arregla en `agente/enviar.py`, {TIEMPO[regla]}. El cuerpo con las cuatro etapas en "
        f"orden está en blueprint/31-proveedores.md, paso 1."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Lo que sale del disco
# ─────────────────────────────────────────────────────────────────────────────

HISTORIALES = (
    "caso-02.historial.json",
    "caso-02b.historial.json",
    "caso-02c.historial.json",
)

# El del `palabra_clave`, y se elige por lo que **no** trae: su `ultimo_entrante` es una pregunta
# común. Los otros dos traen el material de la escalación —el insulto, el pedido a medida—, que no
# tiene nada que ver con estas guardas y se leería como si lo tuviera.
HISTORIAL = "caso-02c.historial.json"

# El cuarto, y el único que llega al umbral: el contacto preguntó una vez y después no contestó
# ninguno de los dos mensajes que se le mandaron. Es un fixture aparte y no un valor cambiado en
# los tres de arriba, porque `salientes_seguidos` en cero es lo que deja correr las direcciones
# «sale» de todo este archivo: moverlo ahí las pondría rojas a todas, por una guarda que ninguna
# de ellas está mirando.
HISTORIAL_INSISTENCIA = "historial-insistencia.json"

# Lo que cada historial tiene que traer en `salientes_seguidos`. Los tres viejos en cero, el nuevo
# en el umbral que `agente/enviar.py` declara como `MAX_SEGUIDOS`. El número está clavado en el
# fixture y no se calcula desde el build: si el umbral sube, la prueba de la insistencia lo dice
# con todas las letras en vez de ponerse roja por otra cosa.
UMBRAL_DOCUMENTADO = 2
SALIENTES_ESPERADOS = {
    **{nombre: 0 for nombre in HISTORIALES},
    HISTORIAL_INSISTENCIA: UMBRAL_DOCUMENTADO,
}
TODOS_LOS_HISTORIALES = (*HISTORIALES, HISTORIAL_INSISTENCIA)

UNA_HORA = timedelta(hours=1)

# Las marcas son ASCII a propósito. El cuerpo viaja como JSON y las tildes salen escapadas —«ó» se
# escribe `ó`—, así que una marca con tilde no se encuentra adentro de `Llamada.texto` aunque
# haya salido perfecta.
MARCA_LIBRE = "referencia LB-8K2"
TEXTO_LIBRE = f"Te dejo el martes a las 11 ({MARCA_LIBRE}). ¿Te sirve?"

MARCA_PLANTILLA = "recordatorio RC-3F"

# Los dos textos que la regla 2 no deja salir: uno cualquiera, y el que parece inofensivo.
TEXTO_DE_LA_BAJA = "Listo, te damos de baja. No te escribimos más."

# El pedido, tal como lo escribe una persona. Trae la palabra `baja`, que es la única de
# `PALABRAS_DE_BAJA` que cualquier lista razonable incluye.
PEDIDO_DE_BAJA = "Dame de baja, por favor."

# Pidió la baja antes del último entrante, y después volvió a escribir. Es el caso que importa: la
# baja es para siempre, así que ese mensaje nuevo no la levanta. Ver `revisar_baneo()`, que no
# mira la fecha del entrante sino si `baja_en` está escrito.
FECHA_DE_BAJA = "2026-03-01T19:45:00-06:00"


def instante(cadena: str) -> datetime:
    """Un momento del fixture, en UTC y con `tzinfo`.

    Se normaliza a UTC para que la comparación de `enviar()` no dependa del offset con el que el
    fixture lo escribió, y para no chocar con un build que guarda en UTC.
    """
    return datetime.fromisoformat(cadena).astimezone(timezone.utc)


def cierre_de_la_ventana(nombre: str = HISTORIAL) -> datetime:
    """Cuándo se cierra la ventana de esa conversación, según el disco."""
    return instante(cargar(nombre)["conversacion"]["window_expires_at"])


def dentro_de_la_ventana(nombre: str = HISTORIAL) -> datetime:
    """Una hora antes del cierre: 23 desde el último entrante."""
    return cierre_de_la_ventana(nombre) - UNA_HORA


def fuera_de_la_ventana(nombre: str = HISTORIAL) -> datetime:
    """Una hora después del cierre: 25 desde el último entrante.

    Los dos instantes están elegidos para que las **dos** ramas de la guarda coincidan: la de
    Zernio, que lee `window_expires_at` tal como vino, y la de Meta, que lo calcula sumándole 24
    horas a `last_inbound_at`. Así la prueba no ata al build a una de las dos. Que las dos ramas
    digan lo mismo lo afirma
    `test_los_historiales_traen_los_campos_que_estas_pruebas_leen`.
    """
    return cierre_de_la_ventana(nombre) + UNA_HORA


def historial(nombre: str = HISTORIAL, /, **conversacion) -> dict:
    """El historial del fixture con `conversacion` cambiada. Es una copia: el disco no se toca.

    El nombre va posicional a propósito: así ningún campo de la conversación que se quiera cambiar
    puede chocar con él.
    """
    completo = cargar(nombre)
    completo["conversacion"].update(conversacion)
    return completo


def id_de_la_conversacion(hist: dict) -> str:
    return hist["conversacion"]["conversacion_id"]


def ultimo_saliente(nombre: str = HISTORIAL) -> str:
    """El texto del último mensaje que salió en ese historial.

    Es el que produce `ultimo_saliente_hash`, y por eso es el único texto que la regla 4 tiene que
    frenar. Se lee de `mensajes` y no se escribe acá: un literal pegado en la prueba deriva del
    fixture el día que alguien cambie una coma, y la regla se dejaría de probar en silencio. Que
    los dos sigan diciendo lo mismo lo afirma
    `test_los_historiales_traen_los_campos_que_estas_pruebas_leen`.
    """
    salientes = [m for m in cargar(nombre)["mensajes"] if m["direccion"] == "saliente"]
    return salientes[-1]["texto"]


def texto_de(largo: int) -> str:
    """Un texto de exactamente `largo` caracteres, con `MARCA_LIBRE` adentro para reconocerlo.

    Con `largo` chico no llega a traer la marca: es lo esperado. `TEXTO_MINIMO` la mira por el
    cuerpo parseado, no por subcadena.
    """
    relleno = " y te cuento el resto del plan cuando confirmes."
    completo = TEXTO_LIBRE + relleno * (largo // len(relleno) + 1)
    return completo[:largo]


# El texto más corto que sí puede salir, y el otro lado del corte de `revisar_baneo()` por abajo.
# Sale de `texto_de()` igual que el del límite: las dos puntas de la misma función se leen como lo
# que son y no como dos literales sueltos que alguien mueve por separado.
TEXTO_MINIMO = texto_de(1)


# ─────────────────────────────────────────────────────────────────────────────
# El proveedor mínimo
# ─────────────────────────────────────────────────────────────────────────────


class ProveedorMinimo:
    """Lo único que `enviar()` le pide a un transporte, y nada más.

    `enviar()` le pregunta tres cosas —la forma del cuerpo, sus cabeceras y dónde está el id en la
    respuesta— y ninguna de las tres decide una guarda: «el proveedor no conoce ninguna URL; el
    destino lo elige `enviar()`». Por eso acá alcanza con esto y no hace falta instanciar el de
    verdad, que pediría una credencial que esta suite no tiene ni quiere.

    `nombre` es `zernio` por descarte. `demo` no abre un socket —deja el borrador—, así que el
    transporte no vería nada y las cuentas serían cero contra cero; `meta` necesita
    `WHATSAPP_PHONE_NUMBER_ID` en `ajustes` para armar su URL.
    """

    nombre = "zernio"

    def sobre(self, conv, cuerpo: str, plantilla) -> dict:
        return {"body": cuerpo, "template": None if plantilla is None else plantilla.nombre}

    def cabeceras(self) -> dict[str, str]:
        # Sin `Authorization`. El transporte de las pruebas no valida nada, y una credencial de
        # mentira en el árbol se lee igual que una de verdad el día que alguien la busca.
        return {"Content-Type": "application/json"}

    def id_externo(self, respuesta: dict) -> str | None:
        return (respuesta.get("messages") or [{}])[0].get("id")


# ─────────────────────────────────────────────────────────────────────────────
# El arnés: sembrar una conversación y mandar un mensaje por la única puerta
# ─────────────────────────────────────────────────────────────────────────────

NECESARIOS = ("agente/__init__.py", "agente/base.py", "agente/http.py", "agente/enviar.py")


def motivo_sin_enviar() -> str:
    """Por qué no se puede llamar a `enviar()`, o cadena vacía si se puede.

    Vive acá y no al lado de `motivo_sin_ciclo()` y `motivo_sin_servidor()` en
    `pruebas/proveedor_falso.py` porque este archivo es el único que llama a `enviar()` sin pasar
    por el ciclo. El día que otro lo haga, se muda allá con las otras dos.
    """
    faltan = [r for r in NECESARIOS if not (RAIZ / r).is_file()]
    if not faltan:
        return ""
    return (
        f"falta el build: no existe {', '.join(faltan)}. `agente/enviar.py` con las cinco reglas "
        f"lo escribe blueprint/31-proveedores.md paso 1, y `agente/base.py` y `agente/http.py` "
        f"los escribe blueprint/30-generacion.md paso 3. Corré /armar-cerrador y volvé a esta "
        f"suite."
    )


def constante(nombre: str, por_defecto: int) -> int:
    """Una constante de `agente/enviar.py`, o la que el blueprint documenta si el build no la trae.

    Los dos umbrales —`MAX_SEGUIDOS` y `LIMITE_TEXTO`— los fija el build, así que la prueba los
    lee de ahí en vez de repetirlos: con el número escrito acá, subirlo en un lado dejaría la
    dirección «no sale» midiendo un umbral que ya no existe. El `por_defecto` es para el build que
    borró la rama entera y se llevó la constante puesta: ahí la prueba se pone roja por la rama que
    falta, con el motivo escrito, y no por un `AttributeError`.
    """
    try:
        enviar_mod, _ = _modulos()
    except SinAgente as e:
        pytest.skip(str(e))
    valor = getattr(enviar_mod, nombre, por_defecto)
    return valor if isinstance(valor, int) else por_defecto


def _modulos():
    """`agente.enviar` y `agente.base`, o `SinAgente` con el motivo escrito."""
    motivo = motivo_sin_enviar()
    if motivo:
        raise SinAgente(motivo)
    try:
        return (
            importlib.import_module("agente.enviar"),
            importlib.import_module("agente.base"),
        )
    except ModuleNotFoundError as e:
        raise SinAgente(
            f"falta {e.name} en este intérprete o en el árbol: `agente/enviar.py` está pero no "
            f"importa. Corré esto con el `.venv` del proyecto."
        ) from e


async def _quizas(valor):
    """El resultado, sea una corrutina o un valor pelado. El build decide, no la prueba."""
    return await valor if inspect.isawaitable(valor) else valor


_SIN_DECIR = object()


@pytest.fixture
def mandar(monkeypatch):
    """Siembra un historial y manda un mensaje por `enviar()`. Devuelve `(Resultado, doble)`.

    Todo corre adentro de un solo `asyncio.run`: la base en memoria de SQLite muere cuando se
    cierra la conexión, y sembrar en una corrida y mandar en otra la deja vacía en el medio.

    Saltea con el motivo escrito mientras el build no esté. Un salteo con motivo no es un
    aprobado, y se lee con `pytest -rs`.
    """

    def _mandar(
        hist: dict,
        *,
        ahora: datetime,
        texto: str | None = None,
        plantilla=None,
        paso: int = 3,
        proveedor=_SIN_DECIR,
        conversacion_id=_SIN_DECIR,
        sembrar_primero: bool = True,
    ):
        try:
            enviar_mod, base = _modulos()
        except SinAgente as e:
            pytest.skip(str(e))

        doble = ProveedorFalso()
        try:
            enchufar_transporte(doble, monkeypatch)
        except SinAgente as e:
            pytest.skip(str(e))

        transporte = ProveedorMinimo() if proveedor is _SIN_DECIR else proveedor
        cid = id_de_la_conversacion(hist) if conversacion_id is _SIN_DECIR else conversacion_id

        async def _todo():
            # `armar_deps()` primero, `migrar()` después, y en ese orden a propósito: la fábrica
            # es la que deja el engine de esta prueba como el motor en curso de `agente/base.py`
            # —blueprint/40-pruebas.md paso 2, punto 2—, y `migrar()` sin argumento migra ése. Al
            # revés se migra el motor de la aplicación, que con `DATABASE_URL` sin poner es
            # `sqlite:///./wca.db`: un archivo en la raíz que esta fase no tendría por qué
            # escribir, y las tablas creadas en la base equivocada.
            deps = armar_deps(doble, historial=hist)
            migrar = getattr(base, "migrar", None)
            if migrar is not None:
                await _quizas(migrar())
            if sembrar_primero:
                await sembrar(deps, hist)
                if await _quizas(base.conversacion(cid)) is None:
                    pytest.fail(
                        f"no pude dejar la conversación {cid} en la base. `agente/base.py` no "
                        f"consume `sembrar_historial(deps, historial)`, que es el único camino "
                        f"que la suite tiene para plantar un historial —ver `sembrar()` en "
                        f"pruebas/proveedor_falso.py—. Sin eso, `enviar()` contesta «sin "
                        f"entrante» en todos los casos y el verde de este archivo no querría "
                        f"decir nada."
                    )
            return await enviar_mod.enviar(
                transporte,
                conversacion_id=cid,
                paso=paso,
                texto=texto,
                plantilla=plantilla,
                ahora=ahora,
            )

        return asyncio.run(_todo()), doble

    return _mandar


@pytest.fixture
def plantilla_aprobada():
    """Una `Plantilla` del build, que es lo único que puede salir con la ventana cerrada."""
    try:
        enviar_mod, _ = _modulos()
    except SinAgente as e:
        pytest.skip(str(e))
    Plantilla = getattr(enviar_mod, "Plantilla", None)
    if Plantilla is None:
        pytest.skip(
            "`agente/enviar.py` no expone `Plantilla`. Sin ella no hay nada que se pueda mandar "
            "con la ventana cerrada, y el camino del recordatorio del paso 4 no existe. Ver "
            "blueprint/31-proveedores.md, paso 1."
        )
    return Plantilla(
        nombre="recordatorio_cita",
        idioma="es_MX",
        variables=(MARCA_PLANTILLA, "mañana 11:00"),
    )


def salio_al_cable(doble: ProveedorFalso, marca: str) -> list:
    """Las peticiones que llevan esa marca adentro del cuerpo o de la URL.

    Se mira `llamadas` y no `envios`: `envios` filtra por ruta de mensajería, y acá lo que se
    afirma es que ese texto **no salió por ningún lado**.
    """
    return [ll for ll in doble.llamadas if marca in f"{ll.url} {ll.texto}"]


# ─────────────────────────────────────────────────────────────────────────────
# La guarda de este archivo: el reloj, y lo que los fixtures tienen que seguir trayendo
# ─────────────────────────────────────────────────────────────────────────────


def test_la_suite_corre_parada_en_el_instante_del_corpus() -> None:
    """Corre sin build, y es la que sostiene los dos nodos del ciclo de este archivo.

    El reloj del ciclo es el de la máquina —`blueprint/40-pruebas.md` paso 2—, y los fixtures
    están fechados el 2 de marzo de 2026. Leídos con el reloj de hoy, los cuatro historiales
    quedan fuera de la ventana de 24 horas y un build **correcto** no manda nada: los nodos que
    cuentan envíos se ponen rojos por el almanaque, y lo que se lee es «el agente no contesta».

    Lo que lo evita es `parado_en_el_instante_del_corpus`, la fixture de sesión de
    `pruebas/conftest.py`. Es autouse, así que nadie la pide y nadie la ve: sin este nodo, el día
    que falte `freezegun` —o que alguien la saque— lo único que aparece son otros nodos en rojo
    con un mensaje que acusa al build.
    """
    ahora = datetime.now(timezone.utc)
    corpus = instante_del_corpus().astimezone(timezone.utc)

    assert ahora == corpus, (
        f"la suite está corriendo a las {ahora.isoformat()} y el corpus pasó el "
        f"{corpus.isoformat()}. El reloj no quedó parado, así que la ventana de 24 horas de los "
        f"cuatro historiales está cerrada y todo lo que cuente envíos desde el ciclo va a dar "
        f"cero contra un build que hace lo correcto. Dos causas: falta `freezegun` en este "
        f"intérprete —está fijado en PINES.md, corré esto con el `.venv` del proyecto—, o alguien "
        f"sacó `parado_en_el_instante_del_corpus` de pruebas/conftest.py. La decisión de qué es "
        f"«ahora» para un ciclo está en blueprint/40-pruebas.md paso 2."
    )


@pytest.mark.parametrize("nombre", TODOS_LOS_HISTORIALES)
def test_los_historiales_traen_los_campos_que_estas_pruebas_leen(nombre: str) -> None:
    """Corre sin build, y es lo que impide que este archivo se lea verde sin medir nada.

    Los cinco campos son de los que salen las dos direcciones de cada regla. Si un historial
    pierde uno, o llega con otro valor, las pruebas de abajo se ponen rojas por un motivo que no
    es el que dicen probar. Acá se ponen rojas primero, barato y con el motivo escrito.

    Los cuatro historiales pasan por las mismas aserciones y una sola se abre en dos: los tres del
    caso 02 tienen que traer `salientes_seguidos` en cero y el de la insistencia en el umbral. Es
    la única diferencia entre ellos, y está escrita en `SALIENTES_ESPERADOS` para que no se pueda
    aflojar una sin que se note.
    """
    completo = cargar(nombre)
    conversacion = completo["conversacion"]

    faltan = [
        c
        for c in (
            "last_inbound_at",
            "window_expires_at",
            "baja_en",
            "salientes_seguidos",
            "ultimo_saliente_hash",
        )
        if c not in conversacion
    ]
    assert faltan == [], (
        f"{nombre} dejó de traer {faltan}. Son los campos que `enviar()` consulta y no calcula "
        f"—ver blueprint/30-generacion.md, la tabla de `conversaciones`—, y de los que este "
        f"archivo deriva sus escenarios."
    )

    cierre = instante(conversacion["window_expires_at"])
    ultimo = instante(conversacion["last_inbound_at"])
    assert cierre - ultimo == timedelta(hours=24), (
        f"en {nombre}, `window_expires_at` no es `last_inbound_at` más 24 horas: van "
        f"{cierre - ultimo}. Con eso, la rama que lee el campo tal como vino y la que lo calcula "
        f"dejan de coincidir, y `dentro_de_la_ventana()` cae adentro para una y afuera para la "
        f"otra: la prueba pasaría a medir cuál de las dos ramas eligió el build."
    )

    corpus = instante_del_corpus().astimezone(timezone.utc)
    assert ultimo <= corpus < cierre, (
        f"en {nombre}, la ventana de 24 horas no está abierta en el instante del corpus: el "
        f"último entrante es {ultimo.isoformat()}, la ventana cierra {cierre.isoformat()} y el "
        f"corpus está parado el {corpus.isoformat()}. Las dos mitades del corpus se fechan juntas "
        f"o no se fechan: el reloj de la suite sale del `mensaje.recibido_en` del caso 01 —ver "
        f"`instante_del_corpus()` en pruebas/conftest.py— y con la ventana cerrada ahí, todo lo "
        f"que corra el ciclo sobre este historial cuenta cero envíos contra un build correcto."
    )

    assert conversacion["baja_en"] is None, (
        f"{nombre} llegó con la baja escrita. La mitad «sin baja» de "
        f"`test_baja_a_quien_pidio_la_baja_no_se_le_escribe` sale de acá: con la baja puesta en "
        f"el fixture, esa mitad deja de probar que la guarda no corta de más."
    )

    esperados = SALIENTES_ESPERADOS[nombre]
    if esperados == 0:
        assert conversacion["salientes_seguidos"] == 0, (
            f"{nombre} trae {conversacion['salientes_seguidos']} salientes seguidos. Con dos o "
            f"más, `revisar_baneo()` corta por «no se insiste más» y todas las direcciones «sale» "
            f"de este archivo se ponen rojas por una guarda que no es la que están mirando. El "
            f"historial que llega al umbral a propósito es {HISTORIAL_INSISTENCIA}, y es aparte "
            f"justamente para que estos tres se puedan quedar en cero."
        )
    else:
        assert conversacion["salientes_seguidos"] == esperados, (
            f"{nombre} trae {conversacion['salientes_seguidos']} salientes seguidos y tiene que "
            f"traer {esperados}, que es el `MAX_SEGUIDOS` de blueprint/31-proveedores.md paso 1. "
            f"Con menos, la dirección «no sale» de `test_insistencia_sin_respuesta_no_se_insiste` "
            f"se pone verde sin que la rama llegue a correr: exactamente el agujero que este "
            f"fixture existe para tapar."
        )

    salientes = [m for m in completo["mensajes"] if m["direccion"] == "saliente"]
    assert salientes, (
        f"{nombre} no trae ningún mensaje saliente. `ultimo_saliente()` lo lee de ahí para armar "
        f"la dirección «no sale» de la regla 4, y sin mensajes salientes esa prueba no tiene qué "
        f"repetir."
    )
    assert huella(salientes[-1]["texto"]) == conversacion["ultimo_saliente_hash"], (
        f"en {nombre}, `ultimo_saliente_hash` no es el sha256 del último mensaje saliente. La "
        f"regla 4 compara el hash del texto que va a salir contra esa columna: con el fixture "
        f"descosido, `test_repetido_el_mismo_texto_no_se_manda_dos_veces` manda un texto que la "
        f"guarda no reconoce y se pone roja por el fixture, no por el build. Se recalcula con "
        f"`huella(texto)` sobre el último saliente de `mensajes`."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Regla 1 · la ventana de 24 horas
# ─────────────────────────────────────────────────────────────────────────────


def test_ventana_dentro_de_las_24_horas_el_texto_libre_sale(mandar) -> None:
    """La dirección que no molesta: adentro de la ventana no hace falta ninguna plantilla.

    Sin esta mitad, un build que se niega siempre —o que exige plantilla para todo— pasaría la
    otra sin haber mirado nunca la hora.
    """
    resultado, doble = mandar(historial(), ahora=dentro_de_la_ventana(), texto=TEXTO_LIBRE)

    assert resultado.enviado is True, roto(
        VENTANA,
        f"el contacto escribió hace 23 horas y el mensaje no salió: «{resultado.motivo}». "
        f"Adentro de la ventana el texto libre sale sin plantilla. Una guarda que niega siempre "
        f"no es una guarda: es un agente que no contesta.",
    )
    assert resultado.ventana_abierta is True, roto(
        VENTANA,
        f"la ventana está abierta y el resultado dice `ventana_abierta="
        f"{resultado.ventana_abierta!r}`. Ese campo es `respuesta.ventana_abierta` del contrato y "
        f"sale de acá y de ningún otro lado.",
    )
    assert len(doble.envios) == 1, (
        f"salieron {len(doble.envios)} mensajes por una sola llamada a `enviar()`: "
        f"{[e.ruta for e in doble.envios]}"
    )
    assert salio_al_cable(doble, MARCA_LIBRE), roto(
        VENTANA,
        f"salió algo que no es lo que se mandó a escribir: el cuerpo que vio el transporte es "
        f"«{doble.envios[0].texto}» y no trae «{MARCA_LIBRE}». Adentro de la ventana va el texto "
        f"libre, no una plantilla.",
    )


def test_ventana_fuera_de_las_24_horas_el_texto_libre_no_sale(mandar) -> None:
    """La dirección que muerde. Es lo que Meta cobra con la calificación del número.

    Fuera de la ventana WhatsApp sólo acepta plantillas aprobadas. Sin plantilla no sale nada, y
    la negativa es un dato con el motivo adentro, no una excepción: entra en la salida del paso y
    se lee desde `/bandeja`.
    """
    resultado, doble = mandar(historial(), ahora=fuera_de_la_ventana(), texto=TEXTO_LIBRE)

    filtrado = salio_al_cable(doble, MARCA_LIBRE)
    assert filtrado == [], roto(
        VENTANA,
        f"la ventana se cerró hace una hora y el texto libre salió igual, por "
        f"{[ll.url for ll in filtrado]}. Fuera de las 24 horas WhatsApp sólo acepta plantillas "
        f"aprobadas: eso no se lee como un error del envío, se lee como calificación del número "
        f"bajando.",
    )
    assert resultado.enviado is False, roto(
        VENTANA,
        "no salió nada al cable y el resultado dice `enviado=True`. Eso es lo que después se lee "
        "como «`enviado: true` y no llegó nada».",
    )
    assert resultado.ventana_abierta is False, roto(
        VENTANA,
        f"la ventana está cerrada y el resultado dice `ventana_abierta="
        f"{resultado.ventana_abierta!r}`. Ese campo es `respuesta.ventana_abierta` del contrato: "
        f"en nulo o en verdadero, quien mire la bandeja no tiene forma de saber por qué ese "
        f"mensaje no salió.",
    )
    motivo = (resultado.motivo or "").lower()
    assert "ventana" in motivo or "24" in motivo, roto(
        VENTANA,
        f"no salió y el motivo no nombra la ventana: «{resultado.motivo}». Ese texto termina en "
        f"`pasos[n].motivo`, que lo lee una persona que no sabe qué es una ventana de 24 horas si "
        f"nadie se la nombra.",
    )


def test_ventana_la_salida_del_ciclo_dice_que_estaba_abierta(correr) -> None:
    """El campo del contrato, en la dirección que el ciclo alcanza sin ayuda.

    Un ciclo lo dispara un mensaje entrante: el reloj está a segundos de `mensaje.recibido_en`, la
    ventana se acaba de abrir y `respuesta.ventana_abierta` es verdadero. Que el reloj esté ahí y
    no en el día en que alguien corre la suite lo pone `parado_en_el_instante_del_corpus` de
    `pruebas/conftest.py`, y lo afirma el primer nodo de este archivo. La dirección contraria está
    en el nodo de acá abajo.

    Lo que muerde acá es el build que llena ese campo a mano, o que lo deja en nulo porque nadie
    lo miraba: hoy `contratos/salida.schema.json` lo declara, `blueprint/35-panel-api.md` lo
    muestra y el ejemplo de `scripts/auditar.py` lo trae, y ninguna aserción lo afirmaba.

    **Un envío, y el motivo está escrito abajo.** Un turno que agenda manda dos —la respuesta del
    paso 3 y la confirmación de la cita—, y éste no agenda: la entrada del caso 01 no trae
    `mensaje.horario_elegido`, o sea que el contacto todavía no dijo cuál de los tres horarios le
    sirve. La confirmación autoriza; no elige.

    **Y lo que esta cuenta no mide, dicho y no escondido.** Este nodo corre sin
    `GOOGLE_CALENDAR_ID`, así que un build que elija el horario por el contacto tampoco llega a
    mandar el segundo mensaje: se frena antes, por falta de credencial. Medido en esta ronda, con
    un build que agenda `disponibilidad[0]` cuando nadie eligió: acá sigue en verde. El que lo
    agarra es `pruebas/test_camino_feliz.py::test_cita_confirmada_y_sin_horario_elegido_no_agenda_y_dice_cual_falta`,
    que sí arma el entorno de la agenda y cuenta las llamadas a Google. Lo que esta cuenta afirma
    es lo suyo: que el turno que contesta manda **una** línea al contacto y no dos.
    """
    entrada = con(cargar("caso-01.entrada.json"), modo="automatico", confirmado=True)
    assert entrada["mensaje"].get("horario_elegido") is None, (
        "el fixture del caso 01 empezó a traer `mensaje.horario_elegido`. Con un horario elegido "
        "y la confirmación puesta, el paso 4 agenda y el turno manda dos mensajes: la cuenta de "
        "acá abajo pasa a ser otra. Ver blueprint/33-agenda.md paso 3."
    )
    salidas, doble = correr([entrada], modelo=StubModel.canonica())
    salida = salidas[0]

    assert salida["respuesta"] is not None, "el paso 3 no dejó nada en `respuesta`"
    assert len(doble.envios) == 1, (
        f"salieron {len(doble.envios)} mensajes en automatico y tenía que salir uno: esta prueba "
        f"mira el campo del turno que sí mandó, y este turno no agenda —no hay horario elegido y "
        f"tampoco hay `GOOGLE_CALENDAR_ID`—, así que la confirmación de la cita no existe. Lo que "
        f"salió fue {[e.texto for e in doble.envios]}."
    )
    assert salida["respuesta"]["enviado"] is True
    assert salida["respuesta"]["ventana_abierta"] is True, roto(
        VENTANA,
        f"el mensaje del contacto entró recién y el paso 3 contestó libre, así que la ventana "
        f"estaba abierta; la salida dice `ventana_abierta="
        f"{salida['respuesta']['ventana_abierta']!r}`. Ese campo sale del `Resultado` de "
        f"`enviar()` y no se pone a mano porque el paso corrió. Si `enviar()` ya lo devuelve "
        f"bien —lo afirman las dos pruebas de acá arriba—, lo que lo pierde es el paso 3 al "
        f"armar `respuesta`, en `agente/pasos/paso_3_responder.py`.",
    )


def test_ventana_el_ciclo_retomado_un_dia_despues_no_contesta_libre(correr) -> None:
    """La otra dirección desde el ciclo, y es la que separa las dos lecturas del reloj.

    **Este camino existe y está escrito**: `CLAUDE.md` dice que al ciclo «también se invoca a mano
    para retomar una conversación desde la etapa escrita en el CRM». Ahí no hay ningún entrante
    nuevo: la entrada es la misma que quedó guardada, con su `mensaje.recibido_en` de cuando llegó,
    y lo que cambió es la hora. A las 25 horas la ventana está cerrada y por texto libre no sale
    nada.

    **Lo que muerde es el build que toma `mensaje.recibido_en` como el reloj del ciclo.** Con esa
    lectura la cuenta es `recibido_en < recibido_en + 24 h`, o sea siempre verdadera: la guarda de
    la ventana no puede negarse nunca, y este turno contesta libre un día después. Es la lectura
    que el kit **no** eligió, y el porqué está en `blueprint/40-pruebas.md` paso 2.

    Se para el reloj 25 horas después de `recibido_en` y no se toca el fixture: el corpus se queda
    como está en el disco. Es el mismo `freeze_time` de `pruebas/conftest.py`, anidado.

    Lo que se afirma es lo que vale afuera, no de qué lado se resolvió. Un build puede frenar en el
    paso 3 y otro dejar que corte `enviar()`; las dos son correctas. La que no es correcta es la
    tercera, la que manda el texto libre igual.
    """
    freeze_time = pytest.importorskip(
        "freezegun",
        reason=(
            "falta freezegun en este intérprete. Está fijado en PINES.md y es la única forma de "
            "parar el reloj un día después sin esperar un día. Corré esto con el `.venv` del "
            "proyecto."
        ),
    ).freeze_time

    entrada = con(cargar("caso-01.entrada.json"), modo="automatico", confirmado=True)
    recibido = datetime.fromisoformat(entrada["mensaje"]["recibido_en"])
    un_dia_despues = recibido + timedelta(hours=25)

    with freeze_time(un_dia_despues, real_asyncio=True):
        salidas, doble = correr([entrada], modelo=StubModel.canonica())
    salida = salidas[0]

    libres = [e for e in doble.envios if not e.es_plantilla]
    assert libres == [], roto(
        VENTANA,
        f"el mensaje llegó el {recibido.isoformat()}, el ciclo se retomó 25 horas después y salió "
        f"texto libre igual, por {[e.url for e in libres]}. Fuera de las 24 horas WhatsApp sólo "
        f"acepta plantillas aprobadas. Casi siempre esto es el reloj: si el ciclo usa "
        f"`mensaje.recibido_en` como «ahora», la ventana le da abierta siempre y esta guarda no se "
        f"puede negar nunca. El reloj del ciclo es el de la máquina, se lee una vez arriba de todo "
        f"y baja por parámetro.",
    )

    respuesta = salida.get("respuesta")
    if respuesta is not None:
        assert respuesta.get("ventana_abierta") is not True, roto(
            VENTANA,
            f"pasaron 25 horas desde el último entrante y la salida dice "
            f"`ventana_abierta={respuesta.get('ventana_abierta')!r}`. Ese campo sale del "
            f"`Resultado` de `enviar()`: quien mire la bandeja va a ver un mensaje que no salió "
            f"con la ventana declarada abierta, y va a reintentarlo en vez de dar de alta una "
            f"plantilla.",
        )

    assert [p["n"] for p in salida.get("pasos", [])] == [1, 2, 3, 4, 5, 6], roto(
        VENTANA,
        f"el ciclo no terminó los seis pasos: dejó {[p.get('n') for p in salida.get('pasos', [])]}"
        f". Una ventana cerrada es el caso normal de un chat retomado, no una falla: `enviar()` "
        f"devuelve la negativa como dato y el ciclo sigue.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Regla 2 · a quien pidió la baja no se le escribe
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("baja_en", [None, FECHA_DE_BAJA], ids=["sin baja", "con baja"])
def test_baja_a_quien_pidio_la_baja_no_se_le_escribe(mandar, baja_en) -> None:
    """Las dos direcciones de la misma conversación: lo único que cambia es `baja_en`.

    Con la baja escrita no sale nada, ni siquiera con la ventana abierta y el texto perfecto. Sin
    la baja escrita sale, que es la mitad que impide aprobar a un build que corta siempre.

    El contacto de este historial volvió a escribir después de pedir la baja —`last_inbound_at` es
    posterior a `baja_en`— y aun así no se le contesta. La baja es para siempre: `revisar_baneo()`
    mira si está escrita, no cuándo.
    """
    resultado, doble = mandar(
        historial(baja_en=baja_en), ahora=dentro_de_la_ventana(), texto=TEXTO_LIBRE
    )

    if baja_en is None:
        assert resultado.enviado is True, roto(
            BAJA,
            f"esta conversación no tiene ninguna baja escrita y el mensaje no salió: "
            f"«{resultado.motivo}». Una guarda que corta siempre se ve igual que un agente mudo, "
            f"y deja la otra mitad de esta prueba en verde sin haber mirado `baja_en`.",
        )
        return

    assert doble.llamadas == [], roto(
        BAJA,
        f"el contacto pidió la baja el {baja_en} y esto salió al cable igual: "
        f"{[ll.url for ll in doble.llamadas]}. No se le escribe más, tampoco con confirmación "
        f"desde la bandeja.",
    )
    assert resultado.enviado is False, roto(
        BAJA, "no salió nada al cable y el resultado dice `enviado=True`."
    )
    motivo = (resultado.motivo or "").lower()
    assert "baja" in motivo, roto(
        BAJA,
        f"no salió y el motivo no nombra la baja: «{resultado.motivo}». Quien lo lea en la "
        f"bandeja va a pensar que fue la ventana y va a reintentar con una plantilla.",
    )
    assert resultado.ventana_abierta is not False, roto(
        BAJA,
        "la ventana estaba abierta y el resultado dice `ventana_abierta=False`. Lo que cortó fue "
        "la baja: culpar a la ventana manda a quien lea la bandeja a dar de alta una plantilla "
        "que tampoco puede salir.",
    )


def test_baja_ni_siquiera_sale_la_confirmacion_de_la_baja(mandar) -> None:
    """El mensaje que parece cortesía y es el que hace falta no mandar.

    «Listo, te damos de baja» es un mensaje a alguien que pidió que no le escribieran. Sale por el
    mismo camino que cualquier otro y la guarda no distingue el contenido: mira `baja_en`.
    """
    resultado, doble = mandar(
        historial(baja_en=FECHA_DE_BAJA),
        ahora=dentro_de_la_ventana(),
        texto=TEXTO_DE_LA_BAJA,
    )

    assert doble.llamadas == [], roto(
        BAJA,
        f"salió «{TEXTO_DE_LA_BAJA}» a un contacto dado de baja, por "
        f"{[ll.url for ll in doble.llamadas]}. Confirmar la baja es escribirle: la baja se anota "
        f"en la base y no se contesta.",
    )
    assert resultado.enviado is False, roto(
        BAJA, "no salió nada al cable y el resultado dice `enviado=True`."
    )


def test_baja_pedida_en_el_ultimo_entrante_corta_el_envio(mandar) -> None:
    """La baja recién pedida, que es como llega en la vida real: en el mensaje de este turno.

    `baja_en` viene en nulo y el pedido está en el texto. La guarda lo reconoce, lo deja escrito
    y recién ahí decide. Un build que sólo lea la columna contesta este turno y se da de baja para
    el siguiente: una respuesta de más a alguien que ya pidió que no le escriban.
    """
    resultado, doble = mandar(
        historial(baja_en=None, ultimo_entrante=PEDIDO_DE_BAJA),
        ahora=dentro_de_la_ventana(),
        texto=TEXTO_LIBRE,
    )

    assert doble.llamadas == [], roto(
        BAJA,
        f"el contacto escribió «{PEDIDO_DE_BAJA}» y el agente le contestó igual, por "
        f"{[ll.url for ll in doble.llamadas]}. El pedido se mira sobre el último entrante antes "
        f"de mandar —`pide_la_baja()` y `marcar_baja()`—, no en el turno siguiente. Si tu lista "
        f"de palabras no trae «baja», es `PALABRAS_DE_BAJA` lo que hay que mirar.",
    )
    assert resultado.enviado is False, roto(
        BAJA, "no salió nada al cable y el resultado dice `enviado=True`."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Regla 3 · nunca escribir primero
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "forma",
    ["la conversación no existe", "la conversación no tiene ningún entrante"],
)
def test_primero_a_quien_nunca_escribio_no_se_le_abre_conversacion(mandar, forma: str) -> None:
    """El agente contesta: no abre conversaciones frías y no hace envíos masivos.

    Las dos formas de «nunca escribió», porque se rompen por separado. En la primera no hay fila
    ninguna. En la segunda la fila existe —la creó el CRM, o alguien la abrió desde la bandeja— y
    nadie escribió nunca desde el otro lado: un build que sólo pregunte `conv is None` pasa la
    primera y abre la conversación en la segunda.

    El transporte está enchufado y contesta 200, a propósito. La verificación de
    `blueprint/31-proveedores.md` pasa el proveedor en `None` y se conforma con que la guarda
    decida antes de tocarlo; acá se afirma lo que importa afuera, que es que no salió nada al
    cable. Con el proveedor en nulo, un build sin la guarda se rompe contra el `None` y lo único
    que se ve es un `AttributeError` —cierto, pero es un síntoma, no el envío—.
    """
    comun = {"ahora": dentro_de_la_ventana(), "texto": TEXTO_LIBRE}
    try:
        if forma == "la conversación no existe":
            resultado, doble = mandar(
                historial(),
                sembrar_primero=False,
                conversacion_id="conv_de_alguien_que_nunca_escribio",
                **comun,
            )
        else:
            resultado, doble = mandar(
                historial(last_inbound_at=None, window_expires_at=None, ultimo_entrante=None),
                **comun,
            )
    # Cualquier explosión acá adentro ya es la guarda faltando, así que se traduce en vez
    # de dejar salir una traza que no nombra ninguna regla.
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            roto(
                PRIMERO,
                f"`enviar()` siguió adelante sin preguntar si esa persona escribió alguna vez, y "
                f"se rompió por el camino: {type(e).__name__}: {e}. Con la guarda puesta esta "
                f"llamada devuelve un `Resultado` y no levanta nada: la primera etapa decide sin "
                f"mirar el texto, ni la hora, ni el proveedor, y por eso va primera.",
            )
        )

    assert doble.llamadas == [], roto(
        PRIMERO,
        f"salió una petición a un contacto que nunca escribió ({forma}): "
        f"{[ll.url for ll in doble.llamadas]}. Esto es lo que hace que Meta baje un número, y "
        f"recuperarlo son semanas.",
    )
    assert resultado.enviado is False, roto(
        PRIMERO, "no salió nada al cable y el resultado dice `enviado=True`."
    )
    assert resultado.ventana_abierta is None, roto(
        PRIMERO,
        f"el resultado dice `ventana_abierta={resultado.ventana_abierta!r}`. Sin un entrante no "
        f"hay ventana que mirar: un verdadero o un falso ahí quiere decir que se calculó igual, "
        f"sobre una conversación que nadie abrió.",
    )
    assert resultado.motivo, roto(
        PRIMERO, "se negó y no dijo por qué. La negativa es un dato y viaja con el motivo adentro."
    )


def test_primero_a_quien_escribio_hace_25_horas_si_se_le_manda_la_plantilla(
    mandar, plantilla_aprobada
) -> None:
    """La dirección que no molesta, y el camino real del recordatorio del paso 4.

    «Nunca escribió» y «escribió hace 25 horas» no son lo mismo. El recordatorio sale 24 horas
    antes de la cita, sin ningún entrante nuevo y casi siempre con la ventana cerrada: si la
    primera guarda confunde las dos cosas, la cita queda agendada y nadie recibe el aviso.

    De paso, es la otra salida que la regla 1 permite fuera de la ventana: la plantilla aprobada.
    """
    resultado, doble = mandar(
        historial(), ahora=fuera_de_la_ventana(), paso=4, plantilla=plantilla_aprobada
    )

    assert resultado.enviado is True, roto(
        PRIMERO,
        f"el contacto escribió hace 25 horas y el recordatorio no salió: «{resultado.motivo}». La "
        f"guarda es «sin un entrante de ese contacto», no «sin un entrante reciente»: para eso "
        f"está la ventana, que acá se contesta con la plantilla aprobada.",
    )
    assert len(doble.envios) == 1, (
        f"salieron {len(doble.envios)} peticiones por un recordatorio: "
        f"{[e.url for e in doble.envios]}"
    )
    assert salio_al_cable(doble, MARCA_PLANTILLA), roto(
        VENTANA,
        f"salió algo que no es la plantilla: el cuerpo es «{doble.envios[0].texto}» y no trae "
        f"«{MARCA_PLANTILLA}». Fuera de la ventana lo único que sale es lo que Meta aprobó.",
    )
    assert resultado.ventana_abierta is False, roto(
        VENTANA,
        f"salió por plantilla y el resultado dice `ventana_abierta="
        f"{resultado.ventana_abierta!r}`. La plantilla es la respuesta a la ventana cerrada, no la "
        f"prueba de que estaba abierta.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Regla 4 · el mismo texto no se manda dos veces
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("repetir", [True, False], ids=["el mismo texto", "uno nuevo"])
def test_repetido_el_mismo_texto_no_se_manda_dos_veces(mandar, repetir: bool) -> None:
    """La rama que compara el hash del texto contra `ultimo_saliente_hash`.

    Es la primera de las tres que el kit escribe y ninguna prueba miraba. Se borra dejando
    `return None` y la suite entera sigue verde, con un build que le manda dos veces seguidas
    exactamente el mismo mensaje a la misma persona. Eso no es un duplicado del dedupe de la
    entrada: el dedupe descarta la entrega repetida del proveedor, y esto frena al agente que
    redacta lo mismo otra vez porque el contexto no cambió.

    Las dos direcciones son el mismo historial y lo único que cambia es el texto. Sin la mitad
    «uno nuevo», un build que se niegue siempre —o que compare mal y corte de más— pasaría la
    otra sin haber mirado ningún hash: el agente se queda mudo desde el segundo mensaje.
    """
    texto = ultimo_saliente() if repetir else TEXTO_LIBRE
    resultado, doble = mandar(historial(), ahora=dentro_de_la_ventana(), texto=texto)

    if not repetir:
        assert resultado.enviado is True, roto(
            REPETIDO,
            f"este texto no se mandó nunca en esta conversación y no salió: "
            f"«{resultado.motivo}». La guarda compara el sha256 del texto contra "
            f"`ultimo_saliente_hash`, no contra cualquier cosa que se le parezca.",
        )
        assert salio_al_cable(doble, MARCA_LIBRE), roto(
            REPETIDO,
            f"salió algo que no es lo que se mandó a escribir: el cuerpo que vio el transporte es "
            f"«{doble.envios[0].texto if doble.envios else ''}» y no trae «{MARCA_LIBRE}».",
        )
        return

    assert doble.llamadas == [], roto(
        REPETIDO,
        f"salió otra vez el mismo texto que ya se había mandado —«{texto}»—, por "
        f"{[ll.url for ll in doble.llamadas]}. Recibir dos veces el mismo mensaje es de las cosas "
        f"que hacen que alguien bloquee un número, y el bloqueo es lo que Meta cobra con la "
        f"calificación.",
    )
    assert resultado.enviado is False, roto(
        REPETIDO, "no salió nada al cable y el resultado dice `enviado=True`."
    )
    motivo = (resultado.motivo or "").lower()
    assert any(p in motivo for p in ("mismo texto", "ya se mand", "repet")), roto(
        REPETIDO,
        f"no salió y el motivo no dice que era el mismo texto: «{resultado.motivo}». Quien lo lea "
        f"en la bandeja tiene que entender que el mensaje ya está entregado, no reintentarlo.",
    )
    assert resultado.ventana_abierta is not False, roto(
        REPETIDO,
        "la ventana estaba abierta y el resultado dice `ventana_abierta=False`. Lo que cortó fue "
        "el texto repetido: culpar a la ventana manda a quien lea la bandeja a dar de alta una "
        "plantilla para volver a mandar lo mismo.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Regla 5 · sin respuesta no se insiste más
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("insistir", [True, False], ids=["en el umbral", "uno por debajo"])
def test_insistencia_sin_respuesta_no_se_insiste(mandar, insistir: bool) -> None:
    """La rama de `salientes_seguidos`, sobre el único fixture que llega al umbral.

    El contador lo sube `anotar_saliente()` y lo vuelve a cero el entrante, en `agente/base.py`:
    mide cuántas veces hablaste sin que te contesten. Con la rama borrada, un build le escribe a
    alguien que no contesta todas las veces que el ciclo se dispare, y cada una de esas es un
    reporte de spam esperando.

    Las dos direcciones se paran una a cada lado del umbral que declara el build, no de un número
    escrito acá: en el umbral no sale, uno por debajo sale. Sin la mitad de abajo, un build que
    corte siempre —`>= 0`, o el contador leído al revés— pasaría la otra y el agente no volvería a
    escribir nunca después del primer mensaje.
    """
    umbral = constante("MAX_SEGUIDOS", UMBRAL_DOCUMENTADO)
    assert 1 <= umbral <= UMBRAL_DOCUMENTADO, (
        f"`MAX_SEGUIDOS` de agente/enviar.py es {umbral} y {HISTORIAL_INSISTENCIA} trae "
        f"{UMBRAL_DOCUMENTADO} salientes seguidos: con un umbral más alto el fixture ya no lo "
        f"alcanza y esta prueba mediría otra cosa; con cero el agente no escribe nunca. El "
        f"blueprint lo fija en {UMBRAL_DOCUMENTADO} —blueprint/31-proveedores.md, paso 1—. Si el "
        f"umbral cambió a propósito, se mueve el fixture con él."
    )

    seguidos = UMBRAL_DOCUMENTADO if insistir else umbral - 1
    resultado, doble = mandar(
        historial(HISTORIAL_INSISTENCIA, salientes_seguidos=seguidos),
        ahora=dentro_de_la_ventana(HISTORIAL_INSISTENCIA),
        texto=TEXTO_LIBRE,
    )

    if not insistir:
        assert resultado.enviado is True, roto(
            INSISTENCIA,
            f"van {seguidos} salientes seguidos, el umbral es {umbral} y el mensaje no salió: "
            f"«{resultado.motivo}». La guarda corta en el umbral, no antes: un agente que deja de "
            f"escribir después del primer mensaje no contesta a nadie.",
        )
        assert salio_al_cable(doble, MARCA_LIBRE), roto(
            INSISTENCIA,
            f"salió algo que no es lo que se mandó a escribir: el cuerpo que vio el transporte es "
            f"«{doble.envios[0].texto if doble.envios else ''}» y no trae «{MARCA_LIBRE}».",
        )
        return

    assert doble.llamadas == [], roto(
        INSISTENCIA,
        f"van {seguidos} mensajes seguidos sin que el contacto conteste y salió uno más, por "
        f"{[ll.url for ll in doble.llamadas]}. Insistirle a alguien que no contesta es lo que se "
        f"reporta como spam, y los reportes bajan la calificación del número.",
    )
    assert resultado.enviado is False, roto(
        INSISTENCIA, "no salió nada al cable y el resultado dice `enviado=True`."
    )
    motivo = (resultado.motivo or "").lower()
    assert any(p in motivo for p in ("seguidos", "insist", "sin respuesta")), roto(
        INSISTENCIA,
        f"no salió y el motivo no nombra la insistencia: «{resultado.motivo}». Ese texto termina "
        f"en `pasos[n].motivo`: quien lo lea tiene que ver que el contacto no contestó, no ir a "
        f"buscar un error de envío.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# El texto vacío · la primera rama de `revisar_baneo()`
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "texto",
    [None, "", "   ", TEXTO_MINIMO],
    ids=["el texto en nulo", "la cadena vacía", "sólo espacios", "un solo carácter"],
)
def test_vacio_un_texto_sin_nada_que_decir_no_sale_y_uno_de_un_caracter_si(mandar, texto) -> None:
    """La rama que corta antes de mirar nada, y la que deja pasar un carácter después.

    Es la última de las cinco que se borraba entera sin que cayera un solo nodo. Y la que más
    duele borrar, porque no falla negándose: falla reventando. `revisar_baneo()` hashea el texto
    dos ramas más abajo, así que con `texto=None` y sin esta guarda la llamada muere en
    `AttributeError: 'NoneType' object has no attribute 'encode'` en vez de devolver un
    `Resultado`. Los seis pasos esperan un dato con el motivo adentro; lo que reciben es una
    excepción que ninguno atrapa.

    Las tres formas de «no hay nada que decir» van por separado porque se rompen por separado. El
    corte del blueprint es `not texto or not texto.strip()` —blueprint/31-proveedores.md, paso 1—:
    un build que pregunte sólo `texto is None` pasa la primera y le manda un mensaje en blanco al
    contacto en las otras dos.

    La cuarta dirección se para del otro lado del corte, igual que las del límite y en la punta
    contraria de la misma función. Es la que muerde a un build que se pasó de estricto y pide un
    largo mínimo que WhatsApp no pide.
    """
    hay_texto = bool(texto and texto.strip())

    try:
        resultado, doble = mandar(historial(), ahora=dentro_de_la_ventana(), texto=texto)
    # Sin texto, cualquier explosión acá adentro ya es la rama faltando. Se traduce en vez de dejar
    # salir una traza que no nombra ninguna guarda.
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            roto(
                VACIO,
                f"`enviar(texto={texto!r})` dejó de devolver un `Resultado` y se rompió por el "
                f"camino: {type(e).__name__}: {e}. Con la rama puesta esta llamada vuelve "
                f"`Resultado(enviado=False, ventana_abierta=True, motivo='el texto vino "
                f"vacío')`, que es una negativa como dato. Sin ella, el paso que llame con el "
                f"texto en nulo se lleva puesto el ciclo entero.",
            )
        )

    if hay_texto:
        assert resultado.enviado is True, roto(
            VACIO,
            f"el texto tiene un carácter, que es el mínimo que se puede mandar, y no salió: "
            f"«{resultado.motivo}». El corte es «vacío», no «corto»: WhatsApp no pide ningún "
            f"largo mínimo, y una guarda que exige más deja al agente sin contestar «1».",
        )
        assert len(doble.envios) == 1, (
            f"salieron {len(doble.envios)} mensajes por una sola llamada a `enviar()`: "
            f"{[e.ruta for e in doble.envios]}"
        )
        cuerpo = (doble.envios[0].datos or {}).get("body")
        assert cuerpo == TEXTO_MINIMO, roto(
            VACIO,
            f"salió algo que no es lo que se mandó a escribir: el cuerpo que vio el transporte "
            f"es {cuerpo!r} y tenía que ser {TEXTO_MINIMO!r}. La forma del cuerpo la pone "
            f"`ProveedorMinimo.sobre()`, en este mismo archivo.",
        )
        return

    assert doble.llamadas == [], roto(
        VACIO,
        f"el texto vino {texto!r} y salió una petición igual, por "
        f"{[ll.url for ll in doble.llamadas]}. Un mensaje sin cuerpo vuelve 400 del proveedor, y "
        f"lo que queda escrito en la bandeja es el error del proveedor y no que no había nada que "
        f"decir. El corte es `not texto or not texto.strip()`, no `texto is None`.",
    )
    assert resultado.enviado is False, roto(
        VACIO, "no salió nada al cable y el resultado dice `enviado=True`."
    )
    motivo = (resultado.motivo or "").lower()
    assert any(p in motivo for p in ("vac", "sin texto", "no hay texto")), roto(
        VACIO,
        f"no salió y el motivo no dice que el texto estaba vacío: «{resultado.motivo}». Quien lo "
        f"lea en la bandeja tiene que ver que el turno no tenía nada que decir, no salir a buscar "
        f"un error de envío.",
    )
    assert resultado.ventana_abierta is not False, roto(
        VACIO,
        "la ventana estaba abierta y el resultado dice `ventana_abierta=False`. Lo que cortó fue "
        "el texto vacío: culpar a la ventana manda a quien lea la bandeja a dar de alta una "
        "plantilla para mandar nada.",
    )


def test_vacio_el_ciclo_con_el_modelo_callado_no_manda_nada(correr) -> None:
    """El mismo caso por el camino que lo produce de verdad: el modelo que no redactó nada.

    `StubModel.callado()` existe para esto y hasta esta ronda no lo inyectaba nadie: el único
    lugar del árbol que lo nombraba era `pruebas/test_contrato.py`, y ahí sólo se le mira la
    salida contra el esquema angosto. Un stub que nunca corre no afirma ninguna conducta.

    Se corre en `automatico` y confirmado a propósito. En `borrador` el paso 3 se detiene antes de
    llamar a `enviar()` y el turno terminaría igual sin que la guarda llegue a decidir nada.

    Lo que se afirma es lo que vale afuera y no de qué lado se resolvió: el ciclo termina, no sale
    un solo mensaje al contacto, y el paso 3 deja escrito por qué. Un build puede cortar en
    `agente/pasos/paso_3_responder.py` —«el modelo no redactó nada para este turno»— y otro dejar
    que corte `revisar_baneo()` —«el texto vino vacío»—; las dos son correctas. La que no es
    correcta es la tercera, la del build sin ninguna de las dos, que no termina el ciclo.
    """
    entrada = con(cargar("caso-01.entrada.json"), modo="automatico", confirmado=True)

    try:
        salidas, doble = correr([entrada], modelo=StubModel.callado())
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            roto(
                VACIO,
                f"el modelo no redactó nada y el ciclo se rompió: {type(e).__name__}: {e}. Un "
                f"turno sin texto es un turno normal —el modelo puede no tener nada que "
                f"contestar—, no una falla: termina con los seis pasos y el motivo escrito.",
            )
        )
    salida = salidas[0]

    assert doble.envios == [], roto(
        VACIO,
        f"el modelo no redactó nada y al contacto le llegó algo igual: "
        f"{[(e.ruta, e.texto) for e in doble.envios]}. Se miran `envios` y no `llamadas` porque "
        f"el CRM y el calendario del mismo ciclo sí pueden salir: lo que no puede salir es un "
        f"mensaje.",
    )
    assert [p["n"] for p in salida.get("pasos", [])] == [1, 2, 3, 4, 5, 6], roto(
        VACIO,
        f"el ciclo no terminó los seis pasos: dejó {[p.get('n') for p in salida.get('pasos', [])]}"
        f". Con la rama puesta, `enviar()` devuelve la negativa como dato y el ciclo sigue.",
    )

    tercero = paso(salida, 3)
    assert tercero["estado"] != "hecho", roto(
        VACIO,
        f"el paso 3 quedó en «hecho» sin haber mandado nada: {tercero}. Eso es lo que después se "
        f"lee como «`enviado: true` y no llegó nada».",
    )
    assert tercero.get("motivo"), roto(
        VACIO,
        f"el paso 3 no salió y no dijo por qué: {tercero}. Ese texto es lo único que tiene quien "
        f"abra `/bandeja` para saber que el turno no tenía nada que decir.",
    )
    respuesta = salida.get("respuesta")
    assert respuesta is None or respuesta.get("enviado") is False, roto(
        VACIO,
        f"no salió ningún mensaje y `respuesta` dice `enviado={respuesta.get('enviado')!r}`. Ese "
        f"campo sale del `Resultado` de `enviar()` y no se pone a mano porque el paso corrió.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# El límite de 4096 · no es baneo, es un 400
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("de_mas", [True, False], ids=["uno de más", "justo el límite"])
def test_limite_el_texto_mas_largo_que_el_maximo_no_sale(mandar, de_mas: bool) -> None:
    """La quinta rama de `revisar_baneo()`, y la única que no habla de baneo.

    Un texto más largo que el máximo lo rechaza WhatsApp con un 400. Sin la rama, ese 400 llega
    igual pero desde afuera: el mensaje se da por enviado hasta que el proveedor contesta, el
    motivo que se guarda es el cuerpo del error del proveedor recortado a 200 caracteres, y quien
    mire la bandeja no tiene cómo saber que lo único que pasó es que el resumen se fue de largo.

    Las dos direcciones se paran una a cada lado del límite. La de abajo —exactamente el máximo—
    es la que muerde a un build que escribió `>=` en vez de `>` y recorta un carácter que sí
    entraba.
    """
    limite = constante("LIMITE_TEXTO", 4096)
    assert limite > len(TEXTO_LIBRE), (
        f"`LIMITE_TEXTO` de agente/enviar.py es {limite} y no alcanza ni para el texto de esta "
        f"prueba. WhatsApp admite 4096 caracteres en el cuerpo de un mensaje; ver "
        f"blueprint/31-proveedores.md, paso 1."
    )

    texto = texto_de(limite + 1 if de_mas else limite)
    resultado, doble = mandar(historial(), ahora=dentro_de_la_ventana(), texto=texto)

    if not de_mas:
        assert resultado.enviado is True, roto(
            LIMITE,
            f"el texto tiene exactamente {len(texto)} caracteres, que es el límite, y no salió: "
            f"«{resultado.motivo}». El corte es «más que el límite», no «el límite»: con `>=` se "
            f"pierde un mensaje que WhatsApp aceptaba.",
        )
        assert salio_al_cable(doble, MARCA_LIBRE), roto(
            LIMITE,
            f"salió algo que no es lo que se mandó a escribir: el cuerpo que vio el transporte "
            f"tiene {len(doble.envios[0].texto) if doble.envios else 0} caracteres y no trae "
            f"«{MARCA_LIBRE}».",
        )
        return

    assert doble.llamadas == [], roto(
        LIMITE,
        f"el texto tiene {len(texto)} caracteres, uno más que el límite de {limite}, y salió "
        f"igual por {[ll.url for ll in doble.llamadas]}. Ese envío vuelve 400 y el motivo que "
        f"queda escrito es el error del proveedor, no el largo del texto.",
    )
    assert resultado.enviado is False, roto(
        LIMITE, "no salió nada al cable y el resultado dice `enviado=True`."
    )
    motivo = (resultado.motivo or "").lower()
    assert str(limite) in motivo or "caracteres" in motivo, roto(
        LIMITE,
        f"no salió y el motivo no dice que el texto era demasiado largo: «{resultado.motivo}». "
        f"Con el largo adentro, quien lea la bandeja acorta el mensaje y lo vuelve a mandar; sin "
        f"él, reintenta lo mismo.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Después del 200 · lo que el webhook ya no puede contestar
# ─────────────────────────────────────────────────────────────────────────────
#
# Este nodo mira el webhook y no `enviar()`, y está acá por lo que se pierde cuando falta: el
# camino webhook→ciclo sólo se ejercita cuando `config/playbook.yaml` está en el árbol, o sea
# después de la fase 2, y hasta entonces nadie lo corre. La compuerta tampoco lo alcanza: sin ese
# archivo el chequeo 20 saltea y el veredicto es `parcial`, así que el primer día que alguien pone
# el playbook para llegar al `pass` es el mismo día en que ese camino corre por primera vez. La
# regla que afirma —lo que sale del proceso después de haber contestado— está escrita en
# `blueprint/31-proveedores.md`, paso 5.


@pytest.fixture
def webhook(monkeypatch):
    """El servidor con la entrega grabada de Zernio y su secreto de prueba.

    Es el mismo arnés de `pruebas/test_idempotencia.py`, y está repetido a propósito: ese archivo
    afirma el dedupe y éste afirma qué pasa después del 200. El día que un tercero lo necesite, se
    muda a `pruebas/proveedor_falso.py` con los otros dos motivos.

    El secreto sale de la ficha del fixture. Está escrito ahí a propósito: no firma nada real y no
    abre ninguna cuenta.
    """
    motivo = motivo_sin_servidor()
    if motivo:
        pytest.skip(motivo)

    crudo = (FIXTURES / "zernio.raw").read_bytes()
    ficha = json.loads((FIXTURES / "zernio.meta.json").read_text(encoding="utf-8"))

    monkeypatch.setenv("WHATSAPP_PROVIDER", "zernio")
    monkeypatch.setenv("ZERNIO_WEBHOOK_SECRET", ficha["secreto"])
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")

    from fastapi.testclient import TestClient

    servidor = importlib.reload(importlib.import_module("agente.servidor"))
    with TestClient(servidor.app) as cli:

        def _entregar():
            return cli.post(
                "/webhook/zernio",
                content=crudo,
                headers={
                    ficha["cabecera"]: ficha["firma"],
                    "X-Zernio-Event-Id": json.loads(crudo)["eventId"],
                    "Content-Type": "application/json",
                },
            )

        yield _entregar


class CicloRoto(RuntimeError):
    """Lo que el ciclo levanta en la prueba de acá abajo. Nombre propio para leerlo en el rojo."""


def test_el_ciclo_que_revienta_despues_del_200_no_sube_por_el_webhook(webhook, monkeypatch) -> None:
    """El webhook ya contestó: de ahí para abajo no hay a quién levantarle una excepción.

    El orden del paso 5 de `blueprint/31-proveedores.md` es cuerpo, firma, dedupe, **200**, y
    recién ahí el modelo. O sea que cuando el ciclo corre, la respuesta ya salió: el proveedor
    tiene su 200, la fila del dedupe está escrita y ese evento no vuelve. Una excepción que suba
    desde ahí no la recibe nadie —no hay pedido al que contestarle 500—; lo que hace es matar el
    ciclo a la mitad, sin dejar el paso en `fallado` ni el motivo en ningún lado, y quien abre
    `/bandeja` ve silencio en vez de ver qué se rompió.

    Lo que el ciclo tiene que hacer en su lugar está escrito en el paso 5: atrapar, dejar el motivo
    donde una persona lo lea, y volver.

    **Cómo se rompe el ciclo acá.** Se reemplaza `correr_ciclo` por uno que levanta, en los dos
    lugares donde el handler lo puede haber traído —el módulo y el nombre importado en
    `agente/servidor.py`—, que es la misma convención de `enchufar_transporte()`. Si tu adaptador
    lo trae de otro lado, se cambia en este archivo y en ningún otro.

    **Y por qué se ve en las pruebas antes que en producción.** `TestClient` re-levanta lo que
    suba por el stack ASGI, así que la excepción aparece **en la petición que ya contestó 200**:
    el nodo que falla es cualquiera del webhook y el mensaje no nombra al ciclo. Es lo que se leyó
    como «la suite se rompió al poner `config/playbook.yaml`».
    """
    motivo = motivo_sin_ciclo()
    if motivo:
        pytest.skip(motivo)

    ciclo = importlib.import_module("agente.ciclo")
    servidor = importlib.import_module("agente.servidor")

    async def _revienta(*_a, **_kw):
        raise CicloRoto("el paso 2 no pudo leer la salida del modelo")

    monkeypatch.setattr(ciclo, "correr_ciclo", _revienta)
    if hasattr(servidor, "correr_ciclo"):
        monkeypatch.setattr(servidor, "correr_ciclo", _revienta)

    doble = ProveedorFalso()
    try:
        enchufar_transporte(doble, monkeypatch)
    except SinAgente as e:
        pytest.skip(str(e))

    try:
        respuesta = webhook()
    except CicloRoto as e:
        pytest.fail(
            f"\nel ciclo levantó `{type(e).__name__}: {e}` y la excepción subió hasta el webhook, "
            f"que ya había contestado. Del otro lado eso es un ciclo muerto a la mitad sin nada "
            f"escrito en la bandeja, y de este lado es la suite del webhook en rojo por un defecto "
            f"que no es suyo. `_atender()` —o como se llame lo que corre después del 200— atrapa "
            f"todo, deja el motivo donde una persona lo lea y vuelve. Ver "
            f"blueprint/31-proveedores.md, paso 5."
        )
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            f"\nla entrega se rompió con `{type(e).__name__}: {e}`, y no es el ciclo: el ciclo "
            f"levanta `CicloRoto`. El handler se rompió antes, o corre el ciclo **antes** de "
            f"contestar. El orden es cuerpo, firma, dedupe, 200, y recién ahí el modelo; ver "
            f"blueprint/31-proveedores.md, paso 5."
        )

    assert respuesta.status_code == 200, (
        f"el ciclo levantó y la entrega contestó {respuesta.status_code}. El 200 sale antes del "
        f"modelo y no depende de que el ciclo termine bien: con cualquier otro código Zernio la "
        f"toma por caída y reintenta hasta siete veces, que es la misma persona contestada cuatro "
        f"veces. Ver blueprint/31-proveedores.md, paso 5."
    )
    assert doble.envios == [], (
        f"el ciclo se rompió y al contacto le llegó algo igual: "
        f"{[(e.ruta, e.texto) for e in doble.envios]}."
    )
