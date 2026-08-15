#!/usr/bin/env python3
"""Hashea `plantillas/` y avisa cuando algo se movió sin que nadie lo declare.

Dos modos:

    python3 scripts/hash_plantillas.py --escribir
    python3 scripts/hash_plantillas.py --verificar [--proyecto RUTA]

Y dos fallas que NO son la misma cosa, por eso salen con dos mensajes distintos:

    error del kit    la plantilla cambió y el manifiesto quedó viejo. Lo rompimos nosotros.
    error del build  el archivo generado se apartó de su plantilla. Se arregla copiándola.

Sin esa distinción, alguien debuggea una hora SU proyecto por un defecto NUESTRO.

Códigos de salida:

    0   todo al día
    1   error del kit
    2   error del build
    64  la línea de comandos está mal escrita, que no es ninguna de las dos cosas

Si aparecen los dos, sale 1: mientras el manifiesto esté viejo, no hay contra qué comparar.

El manifiesto no lleva fecha, a propósito. Correr --escribir dos veces sin tocar nada tiene que
dar el mismo archivo byte por byte, o el diff se llena de ruido que nadie lee.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLAS = RAIZ / "plantillas"
MANIFIESTO = PLANTILLAS / "MANIFIESTO.json"

VERSION_MANIFIESTO = 1

# Un placeholder es {{ASI}}: mayúsculas, dígitos y guion bajo. Lo que no calce con esto no es
# un placeholder, es texto, y se copia tal cual.
PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")

# Archivos que viven en plantillas/ y no son plantillas: no se copian a ningún lado.
NO_SON_PLANTILLAS = frozenset({"MANIFIESTO.json", "README.md"})

# Lo que deja el intérprete al importar una plantilla, y lo que deja el sistema al mirar la
# carpeta. No está en git y no se hashea: cambia con la máquina, que es justo lo que este kit
# no quiere adentro.
#
# Se filtran carpetas ocultas y estos nombres, nunca "todo lo que empieza con punto": una
# plantilla se puede llamar `.dockerignore`, y saltearla en silencio sería el defecto exacto
# que este script existe para no tener.
CARPETAS_BASURA = frozenset({"__pycache__", ".git"})
ARCHIVOS_BASURA = frozenset({".DS_Store", "Thumbs.db"})
SUFIJOS_BASURA = (".pyc", ".pyo", ".pyd")

# Adónde va cada carpeta de plantillas dentro del proyecto de quien instala.
#
# La regla es por carpeta y no por archivo para que agregar una plantilla a una fase que ya
# existe no obligue a tocar este script: alcanza con volver a correr --escribir. Una carpeta
# que no esté acá es un error del kit, no un archivo que se copia a cualquier lado.
CARPETAS: dict[str, str] = {
    "infra": "",          # a la raíz del proyecto: requirements.txt, Dockerfile, railway.json
    "seguridad": "agente",  # el paquete de la app
    "contratos": "agente",
    "config": "config",   # el cerrador base, al lado de los YAML de la entrevista
}

# Cuando la regla de la carpeta no alcanza: ruta relativa a plantillas/ → destino exacto.
DESTINOS_A_MANO: dict[str, str] = {}

# Placeholders que cada plantilla tiene permitido traer, por ruta relativa a plantillas/.
# Lo no listado va con la lista vacía: se copia literal, byte por byte. Un {{ASI}} que nadie
# declaró viaja tal cual al proyecto y se descubre en producción.
PLACEHOLDERS_PERMITIDOS: dict[str, list[str]] = {}


# ── lectura ──────────────────────────────────────────────────────────────────


def sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def recorrer() -> list[str]:
    """Rutas relativas a plantillas/, ordenadas. Sin ocultos y sin lo que no es plantilla."""
    encontradas = []
    for ruta in sorted(PLANTILLAS.rglob("*")):
        if not ruta.is_file():
            continue
        rel = ruta.relative_to(PLANTILLAS).as_posix()
        if rel in NO_SON_PLANTILLAS:
            continue
        partes = Path(rel).parts
        carpetas, nombre = partes[:-1], partes[-1]
        if any(c.startswith(".") or c in CARPETAS_BASURA for c in carpetas):
            continue
        if nombre in ARCHIVOS_BASURA or rel.endswith(SUFIJOS_BASURA):
            continue
        encontradas.append(rel)
    return encontradas


def destino_de(rel: str) -> str | None:
    """Dónde se copia. None si no hay regla, que es un error del kit y no un default."""
    if rel in DESTINOS_A_MANO:
        return DESTINOS_A_MANO[rel]
    partes = Path(rel).parts
    if len(partes) < 2:
        return None
    carpeta = partes[0]
    if carpeta not in CARPETAS:
        return None
    base = CARPETAS[carpeta]
    resto = "/".join(partes[1:])
    return f"{base}/{resto}" if base else resto


def placeholders_de(datos: bytes) -> list[str]:
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError:  # plantilla binaria: no lleva placeholders
        return []
    return sorted(set(PLACEHOLDER.findall(texto)))


def construir() -> tuple[dict[str, object], list[str]]:
    """El manifiesto que le corresponde al disco de ahora, y lo que falta declarar."""
    problemas: list[str] = []
    entradas: list[dict[str, object]] = []

    for rel in recorrer():
        destino = destino_de(rel)
        if destino is None:
            problemas.append(
                f"plantillas/{rel} no tiene destino: declará la carpeta en CARPETAS, "
                f"o el archivo en DESTINOS_A_MANO, en scripts/hash_plantillas.py"
            )
            continue

        datos = (PLANTILLAS / rel).read_bytes()
        permitidos = PLACEHOLDERS_PERMITIDOS.get(rel, [])
        hallados = placeholders_de(datos)
        sobran = [p for p in hallados if p not in permitidos]
        faltan = [p for p in permitidos if p not in hallados]
        if sobran:
            problemas.append(
                f"plantillas/{rel} trae placeholders sin declarar: {', '.join(sobran)} "
                f"— uno sin declarar se copia literal y se descubre en producción"
            )
        if faltan:
            problemas.append(
                f"plantillas/{rel} declara placeholders que ya no están: {', '.join(faltan)}"
            )

        entradas.append(
            {
                "ruta": f"plantillas/{rel}",
                "sha256": sha256(datos),
                "bytes": len(datos),
                "destino": destino,
                "placeholders": list(permitidos),
            }
        )

    destinos: dict[str, str] = {}
    for e in entradas:
        anterior = destinos.get(str(e["destino"]))
        if anterior:
            problemas.append(
                f"dos plantillas se copian al mismo destino {e['destino']}: "
                f"{anterior} y {e['ruta']}"
            )
        destinos[str(e["destino"])] = str(e["ruta"])

    manifiesto: dict[str, object] = {
        "version": VERSION_MANIFIESTO,
        "algoritmo": "sha256",
        "plantillas": sorted(entradas, key=lambda e: str(e["ruta"])),
    }
    return manifiesto, problemas


def serializar(manifiesto: dict[str, object]) -> str:
    return json.dumps(manifiesto, indent=2, ensure_ascii=False) + "\n"


# ── comparación ──────────────────────────────────────────────────────────────


def coincide(plantilla: bytes, generado: bytes, placeholders: list[str]) -> bool:
    """El generado es la plantilla, salvo por lo que ocupó el lugar de cada placeholder."""
    if not placeholders:
        return plantilla == generado
    try:
        molde = plantilla.decode("utf-8")
        salida = generado.decode("utf-8")
    except UnicodeDecodeError:
        return plantilla == generado
    # Un {{ASI}} que sobrevivió a la copia no es un valor: es la sustitución que no ocurrió.
    # Sin esta línea, el comodín de abajo lo da por bueno y el archivo llega así a producción.
    if PLACEHOLDER.search(salida):
        return False

    partes = PLACEHOLDER.split(molde)
    tokens = PLACEHOLDER.findall(molde)

    # El mismo placeholder dos veces tiene que haber quedado con el mismo valor las dos veces:
    # la segunda va por retrorreferencia, no por comodín. Un {{DOMINIO}} que salió distinto en
    # dos líneas es un archivo editado a mano, no una copia.
    grupos: dict[str, str] = {}
    patron = re.escape(partes[0])
    for token, literal in zip(tokens, partes[1:]):
        if token in grupos:
            patron += f"(?P={grupos[token]})"
        else:
            grupos[token] = f"g{len(grupos)}"
            patron += f"(?P<{grupos[token]}>.+?)"
        patron += re.escape(literal)

    return re.fullmatch(patron, salida, flags=re.DOTALL) is not None


# Los dos remedios del lado del kit. El de arriba es el común: el manifiesto quedó viejo. El de
# abajo aparece cuando --escribir no arregla nada porque falta una decisión, no un hash.
REMEDIO_ESCRIBIR = "corré hash_plantillas.py --escribir"
REMEDIO_DECLARAR = "declaralo en scripts/hash_plantillas.py y después corré --escribir"


def error_kit(detalles: list[str], remedio: str = REMEDIO_ESCRIBIR) -> None:
    print(f"error del kit: {remedio}")
    for linea in detalles:
        print(f"  {linea}")


def error_build(detalles: list[str]) -> None:
    print("error del build: volvé a copiarlo")
    for linea in detalles:
        print(f"  {linea}")


# ── modos ────────────────────────────────────────────────────────────────────


def escribir() -> int:
    manifiesto, sin_declarar = construir()
    if sin_declarar:
        error_kit(sin_declarar, REMEDIO_DECLARAR)
        print("  no se escribió nada: un manifiesto que ya sabemos que está mal no sirve")
        return 1

    texto = serializar(manifiesto)
    antes = MANIFIESTO.read_text(encoding="utf-8") if MANIFIESTO.exists() else None
    MANIFIESTO.write_text(texto, encoding="utf-8")

    cuantas = len(manifiesto["plantillas"])  # type: ignore[arg-type]
    if antes == texto:
        print(f"{cuantas} plantillas. El manifiesto ya estaba al día.")
    else:
        print(f"{cuantas} plantillas. Manifiesto regenerado: plantillas/MANIFIESTO.json")
    return 0


def verificar(proyecto: Path | None) -> int:
    manifiesto, sin_declarar = construir()
    problemas: list[str] = []

    if not MANIFIESTO.exists():
        error_kit(["plantillas/MANIFIESTO.json no existe"])
        return 1
    try:
        guardado = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        error_kit([f"plantillas/MANIFIESTO.json no es JSON válido: {exc}"])
        return 1

    if guardado.get("version") != VERSION_MANIFIESTO:
        problemas.append(
            f"el manifiesto dice version {guardado.get('version')} y el script escribe "
            f"version {VERSION_MANIFIESTO}"
        )

    viejas = {str(e.get("ruta")): e for e in guardado.get("plantillas", [])}
    nuevas = {str(e["ruta"]): e for e in manifiesto["plantillas"]}  # type: ignore[union-attr]

    for ruta in sorted(nuevas.keys() - viejas.keys()):
        problemas.append(f"{ruta} existe y no está en el manifiesto")
    for ruta in sorted(viejas.keys() - nuevas.keys()):
        problemas.append(f"{ruta} está en el manifiesto y no existe")
    for ruta in sorted(nuevas.keys() & viejas.keys()):
        vieja, nueva = viejas[ruta], nuevas[ruta]
        if vieja.get("sha256") != nueva["sha256"]:
            problemas.append(
                f"{ruta} cambió y el manifiesto quedó viejo\n"
                f"    manifiesto  {vieja.get('sha256')}\n"
                f"    en disco    {nueva['sha256']}"
            )
            continue
        if vieja.get("destino") != nueva["destino"]:
            problemas.append(
                f"{ruta} cambió de destino: {vieja.get('destino')} → {nueva['destino']}"
            )
        if vieja.get("placeholders") != nueva["placeholders"]:
            problemas.append(f"{ruta} cambió la lista de placeholders permitidos")

    if sin_declarar or problemas:
        if sin_declarar:
            error_kit(sin_declarar, REMEDIO_DECLARAR)
        if problemas:
            error_kit(problemas)
        return 1

    print(f"{len(nuevas)} plantillas al día con el manifiesto.")
    if proyecto is None:
        return 0
    return verificar_build(manifiesto, proyecto)


def verificar_build(manifiesto: dict[str, object], proyecto: Path) -> int:
    detalles: list[str] = []
    revisados = 0

    for e in manifiesto["plantillas"]:  # type: ignore[union-attr]
        origen = RAIZ / str(e["ruta"])
        destino = proyecto / str(e["destino"])
        if not destino.exists():
            detalles.append(f"falta {e['destino']} en {proyecto}\n    cp {e['ruta']} {destino}")
            continue
        revisados += 1
        permitidos = [str(p) for p in e["placeholders"]]  # type: ignore[union-attr]
        if coincide(origen.read_bytes(), destino.read_bytes(), permitidos):
            continue
        detalles.append(
            f"{e['destino']} no coincide con {e['ruta']}\n"
            f"    la plantilla no se reescribe: se copia\n"
            f"    cp {e['ruta']} {destino}"
        )

    if detalles:
        error_build(detalles)
        return 2

    print(f"{revisados} archivos generados iguales a su plantilla.")
    return 0


class Parser(argparse.ArgumentParser):
    """argparse sale con 2 cuando la invocación está mal, y 2 acá significa error del build.

    Dos cosas distintas con el mismo número es exactamente lo que este script existe para
    evitar, así que un error de uso sale con 64.
    """

    def error(self, message: str):  # noqa: D102
        self.print_usage(sys.stderr)
        print(f"error de uso: {message}", file=sys.stderr)
        raise SystemExit(64)


def main() -> int:
    parser = Parser(description="Hashea plantillas/ y avisa cuando algo se movió sin declararse.")
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument(
        "--escribir", action="store_true", help="regenera plantillas/MANIFIESTO.json"
    )
    modo.add_argument(
        "--verificar", action="store_true", help="sale distinto de cero si algo cambió"
    )
    parser.add_argument(
        "--proyecto",
        type=Path,
        default=None,
        help="raíz del proyecto generado: compara cada archivo copiado contra su plantilla",
    )
    args = parser.parse_args()

    if not PLANTILLAS.is_dir():
        error_kit([f"no existe {PLANTILLAS}"])
        return 1

    if args.escribir:
        if args.proyecto is not None:
            parser.error("--proyecto solo va con --verificar")
        return escribir()
    return verificar(args.proyecto)


if __name__ == "__main__":
    sys.exit(main())
