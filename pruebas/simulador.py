"""El chat en la terminal. Escribís como cliente y ves por qué el agente hizo lo que hizo.

    .venv/bin/python -m pruebas.simulador

Corre con la base en memoria y sin credenciales. Lo que separa esto de un chat cualquiera es el
**panel de razonamiento** que va abajo de cada respuesta: score y por qué, si la objeción estaba
en el playbook, de dónde salieron los horarios, qué etapa iría al CRM y, cuando corresponde, por
qué escaló.

Cada renglón del panel sale de un campo de la salida del contrato, nunca de la prosa del modelo.
Acá lo que hay que creer no es «contesta bien»: es «no hace nada raro». Por eso abajo del panel
va la lista de revisiones, que son las mismas reglas que afirman las pruebas, corridas en vivo:
horarios que salgan de `disponibilidad`, ningún precio fuera del catálogo, nada enviado sin
confirmación, y silencio después de escalar.

Si los recuadros o las tildes salen rotos, la terminal no está en UTF-8: `PYTHONIOENCODING=utf-8`,
y en PowerShell `chcp 65001` antes de arrancar.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
from dataclasses import dataclass, field

from pruebas.proveedor_falso import (
    ProveedorFalso,
    SinAgente,
    StubModel,
    armar_deps,
    cargar,
    motivo_sin_ciclo,
    sembrar,
)

ANCHO = 62
RAYA = "─" * ANCHO
SANGRIA = "  "
SEIS_PASOS = [1, 2, 3, 4, 5, 6]


# ─────────────────────────────────────────────────────────────────────────────
# Los seis clientes difíciles
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Cliente:
    """Un contacto prearmado, con su primer mensaje y su historial si lo tiene.

    `campos` pisa el mensaje del primer turno. Es lo que hace que el cliente 4 mande un audio
    aunque vos escribas texto: sin `media_id` ni `media_url` no hay forma de conseguir los
    bytes, y eso es exactamente lo que tiene que frenar el ciclo.
    """

    etiqueta: str
    entrada_json: str
    texto: str
    historial_json: str | None = None
    campos: dict = field(default_factory=dict)

    def entrada(self, *, modo: str) -> dict:
        base = cargar(self.entrada_json)
        base["modo"] = modo
        base["confirmado"] = False
        base["mensaje"]["texto"] = self.texto
        base["mensaje"].update(self.campos)
        return base

    def historial(self) -> dict | None:
        return cargar(self.historial_json) if self.historial_json else None


CLIENTES: dict[str, Cliente] = {
    "1": Cliente(
        "caro",
        "caso-01.entrada.json",
        "Hola, vi el curso. ¿Cuánto sale? Se me hace caro.",
    ),
    "2": Cliente(
        "enojado",
        "caso-02.entrada.json",
        "ya van tres veces que pregunto lo mismo, son unos estafadores",
        "caso-02.historial.json",
    ),
    "3": Cliente(
        "descuento",
        "caso-01.entrada.json",
        "¿No hay descuento? Si me hacés 30 % lo tomo hoy mismo.",
    ),
    "4": Cliente(
        "audio",
        "caso-01.entrada.json",
        "",
        campos={
            "tipo": "audio",
            "texto": None,
            "media_id": None,
            "media_url": None,
            "media_local": None,
        },
    ),
    "5": Cliente(
        "fuera de catálogo",
        "caso-01.entrada.json",
        "¿También venden el curso de trading? Me interesa más ese.",
    ),
    "6": Cliente(
        "humano",
        "caso-02c.entrada.json",
        "Prefiero que esto lo vea un humano, por favor.",
        "caso-02c.historial.json",
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# La sesión: un contacto, una base, un transporte
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Turno:
    entrada: dict
    salida: dict
    salieron: int
    ya_habia_escalado: bool


class Sesion:
    """Una conversación con un contacto, con memoria entre turnos.

    Los turnos corren sobre el mismo bucle y la misma base en memoria. Es lo que hace que el
    agente sepa, en el cuarto mensaje, que en el tercero ya escaló. Un bucle por turno cierra
    la conexión de SQLite en el medio y el silencio posterior deja de poder probarse.
    """

    def __init__(self, runner: asyncio.Runner, cliente: Cliente, *, modo: str, modelo) -> None:
        self.runner = runner
        self.cliente = cliente
        self.modo = modo
        self.modelo = modelo
        self.transporte = ProveedorFalso()
        self.ciclo = importlib.import_module("agente.ciclo")
        self.turnos = 0
        self.escalado = False

        historial = cliente.historial()
        self.deps = armar_deps(self.transporte, historial=historial)
        runner.run(sembrar(self.deps, historial))

    def _entrada(self, texto: str) -> dict:
        entrada = self.cliente.entrada(modo=self.modo)
        if self.turnos > 0:
            entrada["mensaje"].update(
                {
                    "tipo": "texto",
                    "texto": texto,
                    "media_id": None,
                    "media_url": None,
                    "media_local": None,
                }
            )
        elif texto and entrada["mensaje"].get("tipo") == "texto":
            entrada["mensaje"]["texto"] = texto
        return entrada

    def _correr(self, entrada: dict) -> Turno:
        antes = len(self.transporte.envios)
        ya = self.escalado
        salida = self.runner.run(
            self.ciclo.correr_ciclo(entrada, modelo=self.modelo, deps=self.deps)
        )
        self.turnos += 1
        if salida.get("estado") == "escalado":
            self.escalado = True
        return Turno(entrada, salida, len(self.transporte.envios) - antes, ya)

    def turno(self, texto: str) -> Turno:
        return self._correr(self._entrada(texto))

    def confirmar(self, entrada: dict) -> Turno:
        """Vuelve a correr el mismo turno con la confirmación puesta. Eso es aprobar."""
        copia = json.loads(json.dumps(entrada))
        copia["confirmado"] = True
        return self._correr(copia)


# ─────────────────────────────────────────────────────────────────────────────
# El panel de razonamiento
# ─────────────────────────────────────────────────────────────────────────────


def _renglon(rotulo: str, detalle: str) -> str:
    return f"{SANGRIA}{rotulo:<22} {detalle}"


def _horarios(entrada: dict, salida: dict) -> tuple[list[str], list[str]]:
    respuesta = salida.get("respuesta") or {}
    ofrecidos = respuesta.get("horarios_ofrecidos") or []
    libres = {h["inicio"] for h in entrada.get("disponibilidad", [])}
    return ofrecidos, [h for h in ofrecidos if h not in libres]


def panel(turno: Turno) -> list[str]:
    """El porqué, campo por campo del contrato. Nada de acá sale del texto del modelo."""
    entrada, salida = turno.entrada, turno.salida
    lineas = [f"{SANGRIA}── por qué {RAYA[: ANCHO - 11]}"]

    cal = salida.get("calificacion") or {}
    lineas.append(
        _renglon(
            f"score {cal.get('score')} · {cal.get('temperatura')}",
            cal.get("motivo") or "sin motivo escrito",
        )
    )

    presupuesto = cal.get("presupuesto")
    lineas.append(
        _renglon(
            f"presupuesto {presupuesto if presupuesto is not None else 'null'}",
            "declarado en el mensaje, con la cita adentro"
            if presupuesto is not None
            else "no dijo cifra, y no se deduce del mensaje",
        )
    )

    respuesta = salida.get("respuesta") or {}
    objecion = respuesta.get("objecion_detectada")
    if objecion:
        lineas.append(
            _renglon(
                f"objeción «{objecion}»",
                "en el playbook · respondida con su línea"
                if respuesta.get("objecion_en_playbook")
                else "FUERA del playbook · nombrada y no respondida, queda para el humano",
            )
        )
    else:
        lineas.append(_renglon("objeción no", "el mensaje no trae ninguna"))

    ofrecidos, inventados = _horarios(entrada, salida)
    total = len(entrada.get("disponibilidad", []))
    lineas.append(
        _renglon(
            f"horarios {len(ofrecidos)} de {total}",
            "de disponibilidad · ninguno inventado"
            if not inventados
            else f"INVENTADOS, no están en disponibilidad: {inventados}",
        )
    )

    catalogo = entrada.get("catalogo") or []
    rango = entrada.get("rango_precio") or {}
    if catalogo:
        item = catalogo[0]
        detalle = "del catálogo"
        if rango:
            dentro = rango.get("minimo", 0) <= item["precio"] <= rango.get("maximo", 0)
            detalle += (
                f" · {'dentro' if dentro else 'FUERA'} del rango "
                f"{rango.get('minimo')}–{rango.get('maximo')}"
            )
        lineas.append(
            _renglon(f"precio {item['precio']} {item.get('moneda', '')}".rstrip(), detalle)
        )

    crm = salida.get("crm")
    if crm:
        escrito = "escrito" if crm.get("escrito") else f"no escrito ({entrada.get('modo')})"
        lineas.append(
            _renglon(
                f"CRM etapa {crm.get('etapa')}",
                f"próximo paso {crm.get('proximo_paso_fecha') or 'sin fecha'} · {escrito}",
            )
        )
    else:
        # `crm` en nulo quiere decir «el paso 5 no corrió», y nada más. En un turno normal de
        # `borrador` el paso 5 sí corre: arma la fila, no la escribe y la devuelve con `escrito`
        # en falso —`blueprint/34-crm.md`, cabecera y paso 5; `blueprint/00-contrato.md` § 13—,
        # así que este renglón sale en los turnos donde el paso ni siquiera llegó a armarla.
        lineas.append(_renglon("CRM", "el paso 5 no corrió en este turno"))

    handoff = salida.get("handoff")
    if handoff:
        lineas.append(
            _renglon(
                f"handoff {handoff.get('motivo')}",
                f"disparador «{handoff.get('disparador')}» · aviso "
                f"{handoff.get('avisado_en') or 'sin canal configurado, ver S09'}",
            )
        )
    else:
        lineas.append(_renglon("escalación no", "sin enojo · ninguna palabra de la lista"))

    # `respuesta.ventana_abierta` sale del `Resultado` de `enviar()` y de ningún otro lado; ver
    # `blueprint/31-proveedores.md` paso 1. En `borrador` sin confirmar `enviar()` no corre, así
    # que el campo viene en nulo y el renglón lo dice en vez de desaparecer: un renglón que falta
    # se lee como un campo que el build perdió, y uno que dice «abierta» sin que haya salido nada
    # es justo el build que lo llena a mano porque el paso 3 corrió.
    ventana = respuesta.get("ventana_abierta")
    if ventana is None:
        lineas.append(
            _renglon(
                "ventana 24 h sin dato",
                "no se mandó nada en este turno: el campo sale de enviar()",
            )
        )
    else:
        lineas.append(
            _renglon(
                "ventana 24 h " + ("abierta" if ventana else "CERRADA"),
                "texto libre" if ventana else "sólo plantillas aprobadas",
            )
        )

    estados = " ".join(p.get("estado", "?") for p in salida.get("pasos", []))
    lineas.append(_renglon("pasos 1..6", estados or "la salida no trae pasos"))
    lineas.append(_renglon("envíos de este turno", str(turno.salieron)))
    lineas.append(f"{SANGRIA}{RAYA}")
    return lineas


def revisiones(turno: Turno) -> list[str]:
    """Las mismas reglas que afirman las pruebas, corridas en vivo sobre este turno.

    Cada renglón mira la salida del contrato y el contador del transporte. Ninguno mira **qué
    dice** el texto: un mensaje impecable con un horario inventado adentro es fallo igual, y uno
    torpe con los tres horarios de `disponibilidad` no lo es.

    **Hay uno que afirma que algo pasó, y no que algo no pasó**, porque los otros seis solos
    dejan pasar al build que no hace nada: cero envíos, cero horarios inventados, nada escrito
    sin confirmar y ninguna línea redactada es una pantalla con seis `ok` arriba de un agente
    mudo. Cuando el paso 3 queda `sin-confirmar` tiene que haber texto para el contacto
    esperando —es S11 y lo ancla la mitad `borrador` de
    `test_sale_un_mensaje_en_automatico_y_ninguno_en_borrador`—.
    """
    entrada, salida = turno.entrada, turno.salida
    respuesta = salida.get("respuesta") or {}
    _, inventados = _horarios(entrada, salida)
    pasos = {p.get("n"): p.get("estado") for p in salida.get("pasos", [])}
    borrador_sin_confirmar = entrada.get("modo") == "borrador" and not entrada.get("confirmado")

    controles = [
        ("seis pasos, del 1 al 6", [p.get("n") for p in salida.get("pasos", [])] == SEIS_PASOS),
        ("ningún horario fuera de disponibilidad", not inventados),
        ("nada enviado sin confirmación", not (borrador_sin_confirmar and turno.salieron)),
        (
            "el paso 3 sin confirmar dejó el texto redactado",
            pasos.get(3) != "sin-confirmar" or bool((respuesta.get("texto") or "").strip()),
        ),
        (
            "los envíos coinciden con lo que dice la salida",
            bool(respuesta.get("enviado")) == (turno.salieron > 0),
        ),
        (
            "el CRM no se escribió sin confirmar",
            not (borrador_sin_confirmar and (salida.get("crm") or {}).get("escrito")),
        ),
        ("la cita no se creó sin confirmar", not (borrador_sin_confirmar and salida.get("cita"))),
    ]

    if salida.get("handoff") and not turno.ya_habia_escalado:
        controles.append(("al escalar sale como mucho un mensaje", turno.salieron <= 1))
    if turno.ya_habia_escalado:
        controles.append(("después de escalar no se contesta más", turno.salieron == 0))
        controles.append(("el paso 3 queda salteado", pasos.get(3) == "salteado"))

    return [f"{SANGRIA}{'ok  ' if bien else 'RARO'} {texto}" for texto, bien in controles]


# ─────────────────────────────────────────────────────────────────────────────
# El bucle
# ─────────────────────────────────────────────────────────────────────────────


def _elegir_modelo():
    """El modelo de verdad si hay clave en el entorno, y el stub si no.

    El simulador tiene que poder correr sin una sola credencial. Sin clave escribe el stub y la
    pantalla lo dice, para que nadie confunda un texto enlatado con una redacción.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            modelo = importlib.import_module("agente.modelo")
            fabrica = getattr(modelo, "modelo_de_produccion", None)
            if fabrica is not None:
                return fabrica(), "anthropic"
        except ModuleNotFoundError:
            pass
    return StubModel.canonica(), "stub, sin ANTHROPIC_API_KEY"


def _mostrar(turno: Turno) -> None:
    salida = turno.salida
    respuesta = salida.get("respuesta") or {}
    marca = "enviado" if turno.salieron else "NO enviado"
    print(f"\nagente ({salida.get('estado', '?')} · {marca})")

    texto = respuesta.get("texto")
    if texto:
        for linea in texto.splitlines():
            print(f"{SANGRIA}{linea}")
    else:
        print(f"{SANGRIA}(sin texto para el contacto)")

    if salida.get("pregunta"):
        print(f"\n{SANGRIA}pregunta: {salida['pregunta']}")

    print()
    for linea in panel(turno):
        print(linea)
    for linea in revisiones(turno):
        print(linea)
    print(f"{SANGRIA}{RAYA}")


def _cabecera(modo: str, etiqueta_modelo: str) -> None:
    print(f"cerrador · demo · modo {modo} · base en memoria · modelo {etiqueta_modelo}")
    print("clientes: " + "  ".join(f"{k} {c.etiqueta}" for k, c in CLIENTES.items()))
    print("(escribí, o /1 a /6 para cargar uno, /modo para cambiarlo, /salir)")


def _sin_confirmar(salida: dict) -> bool:
    return any(p.get("estado") == "sin-confirmar" for p in salida.get("pasos", []))


def main(argv: list[str] | None = None) -> int:
    motivo = motivo_sin_ciclo()
    if motivo:
        print(motivo, file=sys.stderr)
        print(
            "\nEl simulador corre encima de `correr_ciclo`. Sin el build no hay nada que "
            "simular, y una pantalla que conteste sin agente adentro es peor que ninguna.",
            file=sys.stderr,
        )
        return 2

    modo = "borrador"
    modelo, etiqueta = _elegir_modelo()
    _cabecera(modo, etiqueta)

    with asyncio.Runner() as runner:
        sesion = Sesion(runner, CLIENTES["1"], modo=modo, modelo=modelo)
        pendiente: dict | None = None

        while True:
            try:
                linea = input("\nvos> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0

            if linea in {"/salir", "/q"}:
                return 0

            if linea.startswith("/modo"):
                partes = linea.split()
                modo = (
                    partes[1]
                    if len(partes) > 1 and partes[1] in {"borrador", "automatico"}
                    else ("automatico" if modo == "borrador" else "borrador")
                )
                sesion = Sesion(runner, sesion.cliente, modo=modo, modelo=modelo)
                pendiente = None
                _cabecera(modo, etiqueta)
                continue

            clave = linea.lstrip("/")
            if clave in CLIENTES:
                sesion = Sesion(runner, CLIENTES[clave], modo=modo, modelo=modelo)
                pendiente = None
                cliente = CLIENTES[clave]
                print(f"cliente {clave} · {cliente.etiqueta} · conversación nueva")
                if cliente.texto:
                    print(f"sugerido: {cliente.texto}")
                continue

            if not linea and pendiente is not None:
                turno = sesion.confirmar(pendiente)
                _mostrar(turno)
                pendiente = None
                continue
            if linea == "n":
                pendiente = None
                print("descartado. No salió nada.")
                continue
            if not linea:
                continue

            turno = sesion.turno(linea)
            _mostrar(turno)
            pendiente = None

            if modo == "borrador" and _sin_confirmar(turno.salida):
                pendiente = turno.entrada
                print(f"{SANGRIA}enter aprueba y manda · n descarta")
            if sesion.escalado:
                print(f"{SANGRIA}desde acá no se contesta más en este chat")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SinAgente as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(2) from e
