"""El esquema angosto: lo único que sale hacia el modelo.

`contratos/salida.schema.json` es el contrato de validación y no se le puede pasar al modelo,
por dos motivos distintos.

El primero es mecánico. Las salidas estructuradas de Anthropic rechazan `minimum`, `maximum`,
`minItems`, `maxItems`, `minLength`, `maxLength`, `multipleOf` y `pattern`, no aceptan `type`
como lista —los nulos van con `anyOf`— y exigen `additionalProperties: false` con un `required`
que nombre todas las propiedades. El esquema de validación usa cuatro de esas ocho palabras
—`minimum`, `maximum`, `minItems`, `maxItems`— y catorce `type` en lista. Son 31 violaciones,
y `verificar_wire_schema()` las nombra una por una.

El segundo importa más: **el modelo no emite ningún campo que el código pueda calcular o
verificar.** `pasos`, `estado`, `respuesta.enviado`, `crm.escrito`, `cita`, `handoff` y
`horarios_ofrecidos` los decide el código. Pedirle `enviado` al modelo es invitarlo a reportar
un mensaje que no mandó, y no hay prompt que arregle eso: lo que no se pregunta no se puede
mentir.

Lo que queda acá es lo que solo el modelo puede saber: qué quiere el contacto, qué tan cerca
está de comprar, qué objeción puso y qué se le contesta.

Los rangos no van en el esquema, van en `@field_validator`. `Field(ge=..., le=...)` se renderiza
como `minimum`/`maximum` y volvería a meter las palabras prohibidas. Los tipos son planos y el
código acota lo que llega.

Para regenerar el golden:

    python3 plantillas/contratos/wire_schema.py

Escribe `wire_schema.golden.json` al lado y sale con 1 si el esquema tiene una violación.

Para que la compuerta lo revise sin tocar el árbol:

    python3 plantillas/contratos/wire_schema.py --verificar

Compara contra el golden y sale con 1 en cuanto hay deriva. Una versión distinta de pydantic
renderiza distinto, y eso tiene que hacer ruido acá y no en producción.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

GOLDEN = Path(__file__).with_name("wire_schema.golden.json")

SCORE_MINIMO = 0
SCORE_MAXIMO = 100


# ─────────────────────────────────────────────────────────────────────────────
# El modelo
# ─────────────────────────────────────────────────────────────────────────────


class SalidaWire(BaseModel):
    """Lo que el modelo emite en una vuelta del cerrador.

    Todo lo demás de la salida —los seis pasos, el estado, si el mensaje salió, si la fila se
    escribió, la cita, el handoff y los horarios ofrecidos— lo decide el código a partir de
    esto. No lo reportes acá.
    """

    # `use_attribute_docstrings` es lo que convierte el docstring de cada campo en su
    # `description`. Sin eso los campos viajan pelados y el modelo adivina qué le estás
    # pidiendo. `extra="forbid"` es lo que rinde el `additionalProperties: false` que la API
    # exige.
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    intencion: str | None
    """Qué quiere el contacto, en tres o cuatro palabras. Nulo si el mensaje no alcanza."""

    score: int
    """Qué tan cerca está de comprar, de 0 a 100, con lo que dice el mensaje y el historial.
    Los cortes de temperatura los aplica el código con los umbrales de la entrada."""

    presupuesto: float | None
    """Monto que el contacto declaró, en la moneda del catálogo. Nulo si no lo dijo. No lo
    deduzcas ni lo estimes: si no hay un número dicho, va nulo y el score se calcula sin él."""

    presupuesto_evidencia: str | None
    """La subcadena LITERAL del mensaje del contacto donde aparece ese monto, copiada carácter
    por carácter y con el número adentro. El código comprueba las dos cosas —que esté en el
    mensaje y que traiga cifras—; si falla alguna, tira el presupuesto a nulo. Nulo cuando
    `presupuesto` es nulo."""

    urgencia: Literal["alta", "media", "baja"] | None
    """Qué tan apurado está, por lo que dice. Nulo si no hay señal."""

    motivo: str | None
    """Una línea: por qué ese score y no otro."""

    texto: str | None
    """La respuesta para el contacto, con el tono del playbook. Responde la objeción que
    encontraste y cierra con los horarios que te pasaron, sin agregar ninguno. Ningún precio
    que no esté en el catálogo. Nulo cuando no corresponde escribirle nada."""

    objecion_detectada: str | None
    """La objeción del contacto, con las palabras del playbook si es una de ahí. Si no está en
    el playbook nombrala igual: el código la marca como fuera de playbook y la deja para el
    humano. Nulo si no hubo objeción."""

    resumen: str | None
    """Tres líneas para el CRM: qué quería, qué se le respondió, qué falta. Nunca la
    conversación entera."""

    proximo_paso: str | None
    """Qué hay que hacer después, en una línea. Nulo si no hay uno claro."""

    proximo_paso_fecha: str | None
    """La fecha de ese próximo paso, `AAAA-MM-DD`. El código la parsea y lo que no parsea queda
    nulo."""

    # ── Los rangos, acá y no en el esquema ──────────────────────────────────

    @field_validator("score", mode="after")
    @classmethod
    def _acotar_score(cls, valor: int) -> int:
        """0 a 100. Un 120 no es un error del que valga la pena morirse: se acota."""
        return max(SCORE_MINIMO, min(SCORE_MAXIMO, valor))

    @field_validator("presupuesto", mode="after")
    @classmethod
    def _acotar_presupuesto(cls, valor: float | None) -> float | None:
        """Un presupuesto negativo no existe. Vale más el nulo que el número raro."""
        if valor is None or valor < 0:
            return None
        return valor

    @field_validator(
        "intencion",
        "presupuesto_evidencia",
        "motivo",
        "texto",
        "objecion_detectada",
        "resumen",
        "proximo_paso",
        mode="after",
    )
    @classmethod
    def _vaciar_es_nulo(cls, valor: str | None) -> str | None:
        """Una cadena vacía o de puros espacios es un nulo escrito de otra forma."""
        if valor is None:
            return None
        recortado = valor.strip()
        return recortado or None

    @field_validator("proximo_paso_fecha", mode="after")
    @classmethod
    def _fecha_o_nulo(cls, valor: str | None) -> str | None:
        """`AAAA-MM-DD` o nulo. Lo parsea el código, no lo promete el esquema."""
        if valor is None:
            return None
        try:
            return date.fromisoformat(valor.strip()).isoformat()
        except ValueError:
            return None

    @model_validator(mode="after")
    def _presupuesto_sin_evidencia_no_vale(self) -> SalidaWire:
        """Mitad de la aserción 2 de `pruebas/caso-01.md`, la que se puede ver sin el mensaje.

        La otra mitad —que la evidencia esté de verdad adentro del texto— la hace
        `anclar_presupuesto()`, que sí tiene el mensaje a mano.
        """
        if self.presupuesto is not None and self.presupuesto_evidencia is None:
            self.presupuesto = None
        if self.presupuesto is None:
            self.presupuesto_evidencia = None
        return self


# ─────────────────────────────────────────────────────────────────────────────
# El ancla: lo que convierte "no inventes números" en algo comprobable
# ─────────────────────────────────────────────────────────────────────────────


def anclar_presupuesto(
    wire: SalidaWire, texto_del_contacto: str | None
) -> tuple[float | None, str | None]:
    """Devuelve `(presupuesto, descarte)` después de buscar la evidencia en el mensaje.

    `descarte` es nulo cuando el presupuesto sobrevivió, y una línea para `motivo` cuando no.

    Son dos compuertas, y hacen falta las dos.

    **Que esté en el mensaje.** La comparación es literal: `evidencia in texto`. Sin acentos
    normalizados, sin comillas arregladas, sin espacios colapsados. Si el modelo no puede copiar
    la subcadena tal cual, no la está leyendo del mensaje.

    **Que traiga cifras.** Sin esto la primera compuerta se pasa sola: en `pruebas/caso-01.md`
    el contacto escribe "se me hace caro" y no dice ningún monto, así que un modelo puede
    devolver los 12000 del catálogo con "se me hace caro" de evidencia —subcadena perfectamente
    literal— y colar como presupuesto declarado un precio que puso el negocio.

    Lo que esto sí deja pasar: un monto escrito con letras, "tengo cinco mil", queda en nulo. Es
    el lado correcto para equivocarse. El contrato lo dice en `calificacion.presupuesto`: nunca
    se inventa, y el score se calcula sin ese factor.

    Es la aserción 2 de `pruebas/caso-01.md` —"inventar un número es fallo"— pasada de
    estadística a mecánica.
    """
    if wire.presupuesto is None:
        return None, None

    evidencia = (wire.presupuesto_evidencia or "").strip()
    if not evidencia:
        return None, "Presupuesto descartado: vino sin evidencia."

    if not texto_del_contacto or evidencia not in texto_del_contacto:
        return None, "Presupuesto descartado: la evidencia no está en el mensaje del contacto."

    if not any(c.isdigit() for c in evidencia):
        return None, "Presupuesto descartado: la evidencia no trae ninguna cifra."

    return wire.presupuesto, None


# ─────────────────────────────────────────────────────────────────────────────
# El esquema renderizado
# ─────────────────────────────────────────────────────────────────────────────


def esquema_wire() -> dict[str, Any]:
    """El esquema que se le manda al modelo, ya listo.

    Se le sacan los `title`: pydantic los deriva del nombre de la propiedad, así que repiten
    algo que el modelo ya tiene a la vista, y se pagan en cada petición.
    """
    return _sin_titulos(SalidaWire.model_json_schema())


def _sin_titulos(nodo: Any) -> Any:
    if isinstance(nodo, dict):
        return {k: _sin_titulos(v) for k, v in nodo.items() if k != "title"}
    if isinstance(nodo, list):
        return [_sin_titulos(x) for x in nodo]
    return nodo


# ─────────────────────────────────────────────────────────────────────────────
# El verificador. Lo usa la compuerta.
# ─────────────────────────────────────────────────────────────────────────────

#: Las ocho que rechazan las salidas estructuradas de Anthropic, más las dos de la misma
#: familia que pydantic emite cuando alguien escribe `gt=` o `lt=` en vez de `ge=` o `le=`.
PALABRAS_PROHIBIDAS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
    }
)

#: Claves cuyo valor es un subesquema.
_SUBESQUEMA = (
    "items",
    "not",
    "if",
    "then",
    "else",
    "contains",
    "propertyNames",
    "additionalItems",
    "unevaluatedItems",
    "additionalProperties",
)

#: Claves cuyo valor es una lista de subesquemas.
_LISTA_DE_SUBESQUEMAS = ("anyOf", "allOf", "oneOf", "prefixItems")

#: Claves cuyo valor es un mapa nombre → subesquema. El mapa NO es un esquema: una propiedad
#: se puede llamar `pattern` sin que eso sea la palabra prohibida, y por eso se recorre el
#: valor y nunca el mapa.
_MAPA_DE_SUBESQUEMAS = (
    "properties",
    "$defs",
    "definitions",
    "patternProperties",
    "dependentSchemas",
)


def verificar_wire_schema(esquema: dict[str, Any]) -> list[str]:
    """Devuelve la lista de violaciones. Vacía significa que el esquema se le puede mandar.

    Busca cuatro cosas:

    1. Las palabras que las salidas estructuradas rechazan.
    2. `type` como lista, que es como se escriben los nulos en JSON Schema y no acá.
    3. Objetos sin `additionalProperties: false`.
    4. Objetos cuyo `required` no nombra todas las propiedades.

    Cada violación viene con la ruta, para que el diff diga dónde y no solo qué.
    """
    faltas: list[str] = []
    _recorrer(esquema, "#", faltas)
    return faltas


def _recorrer(nodo: Any, ruta: str, faltas: list[str]) -> None:
    if not isinstance(nodo, dict):
        return

    for palabra in sorted(PALABRAS_PROHIBIDAS & nodo.keys()):
        faltas.append(f"{ruta}: `{palabra}` no lo acepta la salida estructurada")

    tipo = nodo.get("type")
    if isinstance(tipo, list):
        faltas.append(f"{ruta}: `type` es una lista {tipo}; los nulos van con `anyOf`")

    if _es_objeto(nodo):
        if nodo.get("additionalProperties") is not False:
            faltas.append(f"{ruta}: objeto sin `additionalProperties: false`")
        propiedades = nodo.get("properties") or {}
        requeridas = set(nodo.get("required") or ())
        sueltas = [n for n in propiedades if n not in requeridas]
        if sueltas:
            faltas.append(
                f"{ruta}: `required` no nombra {', '.join(sorted(sueltas))}; "
                "las tiene que nombrar a todas"
            )

    for clave in _SUBESQUEMA:
        if clave in nodo:
            hijo = nodo[clave]
            if isinstance(hijo, list):  # `items` en forma de tupla, de drafts viejos
                for i, sub in enumerate(hijo):
                    _recorrer(sub, f"{ruta}/{clave}/{i}", faltas)
            else:
                _recorrer(hijo, f"{ruta}/{clave}", faltas)

    for clave in _LISTA_DE_SUBESQUEMAS:
        for i, sub in enumerate(nodo.get(clave) or ()):
            _recorrer(sub, f"{ruta}/{clave}/{i}", faltas)

    for clave in _MAPA_DE_SUBESQUEMAS:
        mapa = nodo.get(clave)
        if isinstance(mapa, dict):
            for nombre, sub in mapa.items():
                _recorrer(sub, f"{ruta}/{clave}/{nombre}", faltas)


def _es_objeto(nodo: dict[str, Any]) -> bool:
    tipo = nodo.get("type")
    if tipo == "object":
        return True
    if isinstance(tipo, list) and "object" in tipo:
        return True
    return "properties" in nodo


# ─────────────────────────────────────────────────────────────────────────────


def _rendido() -> str:
    return json.dumps(esquema_wire(), indent=2, ensure_ascii=False) + "\n"


def _main(argv: list[str]) -> int:
    solo_verificar = "--verificar" in argv
    esquema = esquema_wire()

    faltas = verificar_wire_schema(esquema)
    for falta in faltas:
        print(f"  {falta}")
    if faltas:
        print(f"verificar_wire_schema: {len(faltas)} violaciones")
        return 1
    print("verificar_wire_schema: []")

    if solo_verificar:
        if not GOLDEN.exists():
            print(f"falta {GOLDEN}: corré este módulo sin --verificar")
            return 1
        if GOLDEN.read_text(encoding="utf-8") != _rendido():
            print(f"{GOLDEN} quedó viejo: el esquema se movió y el golden no")
            return 1
        print(f"{GOLDEN.name}: sin deriva")
        return 0

    GOLDEN.write_text(_rendido(), encoding="utf-8")
    print(f"escrito {GOLDEN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
