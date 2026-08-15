"""El puente entre la prosa de un caso y el fixture que lee el código.

`pruebas/caso-01.md` y `pruebas/caso-02.md` traen la entrada del caso adentro de un bloque
```json. Las pruebas no leen ese bloque: leen `pruebas/fixtures/<caso>.entrada.json`. Son dos
copias del mismo objeto y sin un chequeo derivan, que es como se pierde la referencia: la prosa
dice una cosa, la suite prueba otra y las dos están en verde.

Este módulo hace las dos mitades:

    python -m pruebas.extraer_fixture --escribir     # la prosa manda: escribe el fixture
    python -m pruebas.extraer_fixture                # compara, y sale 1 si difieren

Sin bandera compara. `--verificar` es la forma explícita de lo mismo, para cuando el comando se
lee en un script y «sin bandera» no se entiende solo.

## Dos reglas de este archivo

**Se escribe verbatim, nunca con `json.dumps`.** El bloque de la prosa sale al fixture byte por
byte. Es lo que hace que `pruebas/fixtures/caso-01.entrada.json` conserve el espaciado compacto
del `.md` en vez de quedar reformateado, y es la misma disciplina que `pruebas/fixtures/README.md`
exige para los `.raw`: ahí un `json.dumps` deja el fixture inerte y la firma recalculada.

**Se compara por `json.loads`, no por bytes.** Igualdad de objeto. Este es el único lugar del kit
donde comparar significados es lo correcto: una tilde escapada distinto o una sangría movida no
cambian la entrada del caso. Los `.raw` de esa misma carpeta son exactamente lo contrario, y por
eso no pasan por acá.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PRUEBAS = Path(__file__).resolve().parent
RAIZ = PRUEBAS.parent
FIXTURES = PRUEBAS / "fixtures"

# La primera cerca de JSON del archivo, que es la de **Entrada.**. No greedy: corta en el primer
# cierre, así un `.md` con más de un bloque sigue devolviendo el primero.
CERCA = re.compile(r"^```json\n(.*?)^```", re.DOTALL | re.MULTILINE)


class SinBloque(RuntimeError):
    """El `.md` del caso no trae una cerca de JSON donde el extractor la busca."""


# ─────────────────────────────────────────────────────────────────────────────
# Las dos rutas y el bloque
# ─────────────────────────────────────────────────────────────────────────────


def ruta_prosa(caso: str) -> Path:
    return PRUEBAS / f"{caso}.md"


def ruta_fixture(caso: str) -> Path:
    return FIXTURES / f"{caso}.entrada.json"


def bloque(caso: str) -> str:
    """El texto del primer bloque ```json de `pruebas/<caso>.md`, tal como está escrito."""
    prosa = ruta_prosa(caso)
    if not prosa.is_file():
        raise SinBloque(f"no existe {prosa.relative_to(RAIZ)}")

    # `\r\n` normalizado a `\n`: un cuerpo HTTP no pasa por acá, y un fixture con retornos de
    # carro adentro rompe la comparación en la máquina siguiente.
    texto = prosa.read_text(encoding="utf-8").replace("\r\n", "\n")
    encontrado = CERCA.search(texto)
    if encontrado is None:
        raise SinBloque(
            f"no encontré un bloque json en {caso}.md. El extractor busca la primera cerca "
            f"```json del archivo, que es la de **Entrada.**. Si movés el bloque, movés el "
            f"extractor: no lo dejes buscando a ciegas."
        )
    return encontrado.group(1)


def objeto(caso: str) -> Any:
    """El bloque de la prosa parseado. Levanta `json.JSONDecodeError` si la prosa quedó rota."""
    return json.loads(bloque(caso))


# ─────────────────────────────────────────────────────────────────────────────
# Dónde difieren, dicho por ruta y no por diff
# ─────────────────────────────────────────────────────────────────────────────


def _corto(valor: Any, tope: int = 60) -> str:
    texto = json.dumps(valor, ensure_ascii=False)
    return texto if len(texto) <= tope else texto[: tope - 1] + "…"


def diferencias(prosa: Any, fixture: Any, ruta: str = "") -> list[str]:
    """Las claves donde los dos objetos dejaron de decir lo mismo, con la ruta adentro.

    Un diff de texto acá no sirve: los dos archivos tienen el mismo contenido con distinto
    formato a propósito. Lo que hace falta saber es qué clave cambió, para decidir cuál manda.
    """
    if isinstance(prosa, dict) and isinstance(fixture, dict):
        hallazgos = []
        for clave in list(prosa) + [k for k in fixture if k not in prosa]:
            aca = f"{ruta}/{clave}" if ruta else str(clave)
            if clave not in fixture:
                hallazgos.append(f"'{aca}' está en la prosa y no en el fixture")
            elif clave not in prosa:
                hallazgos.append(f"'{aca}' está en el fixture y no en la prosa")
            else:
                hallazgos += diferencias(prosa[clave], fixture[clave], aca)
        return hallazgos

    if isinstance(prosa, list) and isinstance(fixture, list):
        if len(prosa) != len(fixture):
            etiqueta = ruta or "la raíz"
            return [
                (
                    f"'{etiqueta}' trae {len(prosa)} elemento(s) en la prosa y "
                    f"{len(fixture)} en el fixture"
                )
            ]
        hallazgos = []
        for i, (a, b) in enumerate(zip(prosa, fixture)):
            hallazgos += diferencias(a, b, f"{ruta}/{i}" if ruta else str(i))
        return hallazgos

    if prosa != fixture:
        etiqueta = ruta or "la raíz"
        return [
            f"'{etiqueta}': la prosa dice {_corto(prosa)} y el fixture dice {_corto(fixture)}"
        ]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Las dos acciones
# ─────────────────────────────────────────────────────────────────────────────


def escribir(caso: str) -> int:
    """La prosa manda: el bloque sale al fixture verbatim."""
    contenido = bloque(caso)
    objeto(caso)  # que no salga un fixture que no parsea
    destino = ruta_fixture(caso)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8")
    print(f"escrito {destino.relative_to(RAIZ)}")
    return 0


def verificar(caso: str) -> int:
    """Compara por igualdad de objeto y sale 1 si la prosa y el fixture derivaron."""
    de_la_prosa = objeto(caso)  # primero la prosa: es la que manda
    destino = ruta_fixture(caso)
    if not destino.is_file():
        print(
            f"falta {destino.relative_to(RAIZ)}. Corré el mismo comando con `--escribir` y "
            f"revisá lo que quedó antes de commitearlo.",
            file=sys.stderr,
        )
        return 1

    guardado = json.loads(destino.read_text(encoding="utf-8"))
    hallazgos = diferencias(de_la_prosa, guardado)
    if hallazgos:
        print(
            f"{caso}: la prosa y el fixture dejaron de decir lo mismo. Decidí cuál manda y "
            f"actualizá el otro; editar los dos a la vez es cómo se pierde la referencia.",
            file=sys.stderr,
        )
        for hallazgo in hallazgos:
            print(f"  difieren en {hallazgo}", file=sys.stderr)
        return 1

    print(f"{caso}: la prosa y el fixture dicen lo mismo")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pruebas.extraer_fixture",
        description=(
            "Extrae la entrada de pruebas/<caso>.md a pruebas/fixtures/<caso>.entrada.json, "
            "o comprueba que las dos digan lo mismo."
        ),
    )
    parser.add_argument(
        "caso",
        nargs="?",
        default="caso-01",
        help="el nombre del caso, sin extensión. Por defecto `caso-01`.",
    )
    parser.add_argument(
        "--escribir",
        action="store_true",
        help="escribe el fixture con el bloque de la prosa, verbatim.",
    )
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="compara y sale 1 si difieren. Es lo que hace sin ninguna bandera.",
    )
    args = parser.parse_args(argv)

    if args.escribir and args.verificar:
        parser.error("`--escribir` y `--verificar` son las dos mitades: corré una por vez.")

    try:
        return escribir(args.caso) if args.escribir else verificar(args.caso)
    except SinBloque as e:
        print(str(e), file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(
            f"el bloque json de {args.caso}.md no parsea: {e}. Es la entrada del caso, así que "
            f"un JSON roto ahí deja la suite entera sin referencia.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
