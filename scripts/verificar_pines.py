#!/usr/bin/env python3
"""Compara cada pin de `PINES.md` contra los registros vivos e informa qué se movió.

Un pin se pudre solo. El día que se escribió era la última versión publicada; tres
meses después es la que nadie usa, y el archivo sigue diciendo lo mismo con la
misma cara. Esto es lo que hace que se note.

La lista de paquetes NO vive acá. Vive en `PINES.md` y se lee de ahí en cada
corrida. Duplicarla adentro del script sería el mismo defecto que el archivo
existe para evitar: un número repetido en dos lugares algún día dice dos cosas
distintas, y la compuerta terminaría verificando su propia copia vieja.

Lo único que sí está clavado acá es la lista de modelos vigentes, y está clavado
a propósito. El kit de referencia quedó fijado en un modelo de la generación
anterior y nadie lo notó hasta que alguien leyó el archivo a mano. Un modelo
retirado no lo dice ningún registro de paquetes: hay que preguntarlo contra una
lista, y esa lista se actualiza acá cuando sale una familia nueva.

Qué mira:

  · cada `nombre==version` de los bloques de `PINES.md`, contra PyPI
  · si la última publicada tiene menos de 72 horas (sin reposo: no se fija)
  · si el pin mismo tiene menos de 72 horas (eso rompe la regla del archivo)
  · si el pin ya no existe en PyPI o quedó retirado (yanked)
  · si la fecha de "Verificado contra PyPI el ..." pasó los 90 días
  · si `MODELO=` sigue siendo un modelo vigente

Uso:
    python3 scripts/verificar_pines.py [--json] [--pines PINES.md] [--timeout 10]

Sale 0 cuando pasa y cuando no hubo red, 2 cuando hay errores. Sin red no
revienta: dice qué no pudo verificar y el veredicto queda en `sin_verificar`,
que no es `pass`. La compuerta del modelo sí corre igual, porque no necesita red.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# La única lista clavada en este archivo. Ver el docstring: un modelo retirado no
# lo informa ningún registro de paquetes.
MODELOS_VIGENTES = ("claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5")

REPOSO_HORAS = 72
VENCE_DIAS = 90
API = "https://pypi.org/pypi/{}/json"
AGENTE = "verificar_pines (blueprint whatsapp-closer-agentkit)"
AUSENTE = "no existe en PyPI (404)"

# Un pin es `nombre==version`, con comentario opcional atrás. `>=` no matchea a
# propósito: un piso no es un pin y no se verifica, se rechaza en la auditoría.
PIN = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9._-]*)\s*==\s*([A-Za-z0-9][A-Za-z0-9._+!-]*)\s*(?:#.*)?$")
MODELO = re.compile(r"^\s*MODELO\s*=\s*([A-Za-z0-9._-]+)\s*(?:#.*)?$")
FECHA = re.compile(r"Verificado contra PyPI el (\d{4}-\d{2}-\d{2})")
CERCA = re.compile(r"^\s*```(.*)$")

# Los pines viven en bloques sin lenguaje. El bloque ```python de `PINES.md`
# lleva una cadena de conexión adentro y el ```bash lleva la línea de invocación
# de este mismo script: ninguno de los dos es una lista de versiones.
INFO_DE_PINES = {"", "text", "txt", "ini", "requirements"}


@dataclass
class Hallazgo:
    id: str
    nivel: str            # "error" | "aviso"
    evidencia: str
    archivo: str = ""
    linea: int = 0
    atribuible_a: str = ""

    def dict(self) -> dict:
        return asdict(self)


# ─── Lectura de PINES.md ────────────────────────────────────────────────────
def lineas_de_pines(texto: str):
    """Las líneas de los bloques de código donde viven los pines, con su número."""
    dentro = False
    aceptar = False
    for n, linea in enumerate(texto.splitlines(), 1):
        m = CERCA.match(linea)
        if m:
            if dentro:
                dentro = False
            else:
                dentro = True
                aceptar = m.group(1).strip().lower() in INFO_DE_PINES
            continue
        if dentro and aceptar:
            yield n, linea


def leer(ruta: Path) -> dict:
    texto = ruta.read_text(encoding="utf-8")
    pines: list[dict] = []
    modelo, modelo_linea = None, 0
    for n, linea in lineas_de_pines(texto):
        m = PIN.match(linea)
        if m:
            pines.append({"nombre": m.group(1), "pin": m.group(2), "linea": n})
            continue
        m = MODELO.match(linea)
        if m:
            modelo, modelo_linea = m.group(1), n
    m = FECHA.search(texto)
    return {
        "pines": pines,
        "modelo": modelo,
        "modelo_linea": modelo_linea,
        "verificado_el": m.group(1) if m else None,
    }


# ─── PyPI ───────────────────────────────────────────────────────────────────
def consultar(nombre: str, timeout: float) -> tuple[dict | None, str | None]:
    """(datos, error). El error viaja como texto: acá nadie levanta una excepción.

    Una compuerta que revienta con un rastreo de pila no es una compuerta que
    falla: es una que no corrió. Sin red esto tiene que decir qué no pudo
    verificar, no dejar media salida y un traceback.
    """
    pedido = urllib.request.Request(
        API.format(nombre), headers={"User-Agent": AGENTE, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        # 404 no es «no pude verificar»: es una respuesta, y dice que el paquete
        # no está. Se marca aparte para que no se confunda con la red caída.
        if e.code == 404:
            return None, AUSENTE
        return None, f"PyPI respondió {e.code}"
    except urllib.error.URLError as e:
        return None, f"sin red: {e.reason}"
    except (TimeoutError, OSError) as e:                      # noqa: BLE001
        return None, f"sin red: {e}"
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"respuesta ilegible de PyPI: {e}"


def _momento(marca: str | None) -> datetime | None:
    if not marca:
        return None
    t = marca.strip().replace("Z", "+00:00")
    # Fracciones de más de seis dígitos rompen fromisoformat antes de 3.11.
    t = re.sub(r"(\.\d{6})\d+", r"\1", t)
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def publicacion(datos: dict, version: str) -> tuple[datetime | None, bool, bool]:
    """(cuándo salió, existe, está retirada) para una versión concreta."""
    lanzamientos = datos.get("releases")
    if isinstance(lanzamientos, dict):
        archivos = lanzamientos.get(version)
        existe = version in lanzamientos
    else:
        # Si algún día `releases` desaparece de la respuesta, `urls` sigue
        # trayendo los archivos de la última. Se verifica lo que se puede.
        archivos = datos.get("urls") if version == datos.get("info", {}).get("version") else None
        existe = archivos is not None
    if not archivos:
        return None, existe, False
    retirada = all(a.get("yanked") for a in archivos)
    momentos = [m for m in (_momento(a.get("upload_time_iso_8601") or a.get("upload_time"))
                            for a in archivos) if m]
    return (min(momentos) if momentos else None), True, retirada


def horas_desde(cuando: datetime | None, ahora: datetime) -> float | None:
    if cuando is None:
        return None
    return (ahora - cuando).total_seconds() / 3600


def revisar_paquete(entrada: dict, timeout: float, ahora: datetime) -> dict:
    p = dict(entrada, estado="sin_verificar", error=None, ultima=None,
             ultima_publicada=None, ultima_horas=None, sin_reposo=None,
             movido=None, pin_publicado=None, pin_horas=None,
             pin_existe=None, pin_retirado=None)
    datos, error = consultar(p["nombre"], timeout)
    if datos is None:
        p["error"] = error
        if error == AUSENTE:
            p["estado"] = "ausente"
        return p

    ultima = str(datos.get("info", {}).get("version") or "")
    cuando, _, _ = publicacion(datos, ultima)
    pin_cuando, pin_existe, pin_retirado = publicacion(datos, p["pin"])

    p["estado"] = "verificado"
    p["ultima"] = ultima
    p["ultima_publicada"] = cuando.isoformat() if cuando else None
    p["ultima_horas"] = horas_desde(cuando, ahora)
    p["sin_reposo"] = (p["ultima_horas"] is not None and p["ultima_horas"] < REPOSO_HORAS)
    p["movido"] = bool(ultima) and ultima != p["pin"]
    p["pin_publicado"] = pin_cuando.isoformat() if pin_cuando else None
    p["pin_horas"] = horas_desde(pin_cuando, ahora)
    p["pin_existe"] = pin_existe
    p["pin_retirado"] = pin_retirado
    return p


# ─── Compuerta ──────────────────────────────────────────────────────────────
def hallazgos_de_paquete(p: dict, archivo: str) -> list[Hallazgo]:
    n, linea = p["nombre"], p["linea"]
    if p["estado"] == "ausente":
        return [Hallazgo("pin/inexistente", "error",
                         f"`{n}` no existe en PyPI: revisá el nombre",
                         archivo, linea, "pines")]
    if p["estado"] != "verificado":
        return [Hallazgo("registro/sin_respuesta", "aviso",
                         f"{n}=={p['pin']} quedó sin verificar: {p['error']}",
                         archivo, linea, "entorno")]

    out: list[Hallazgo] = []
    if p["pin_existe"] is False:
        out.append(Hallazgo("pin/version_inexistente", "error",
                            f"{n}=={p['pin']} no existe en PyPI: la última es {p['ultima']}",
                            archivo, linea, "pines"))
    if p["pin_retirado"]:
        out.append(Hallazgo("pin/retirado", "error",
                            f"{n}=={p['pin']} está retirada de PyPI (yanked)",
                            archivo, linea, "pines"))
    if p["pin_horas"] is not None and p["pin_horas"] < REPOSO_HORAS:
        out.append(Hallazgo("pin/sin_reposo", "error",
                            f"{n}=={p['pin']} salió hace {p['pin_horas']:.0f} h: "
                            f"no tuvo reposo, no se fija todavía",
                            archivo, linea, "pines"))
    if p["movido"] and p["sin_reposo"]:
        out.append(Hallazgo("pin/movido_sin_reposo", "aviso",
                            f"{n} está en {p['pin']} y PyPI publica {p['ultima']}, "
                            f"de hace {p['ultima_horas']:.0f} h: no se sube todavía",
                            archivo, linea, "pines"))
    elif p["movido"]:
        out.append(Hallazgo("pin/movido", "aviso",
                            f"{n} está en {p['pin']} y PyPI publica {p['ultima']}"
                            + (f" desde {p['ultima_publicada'][:10]}" if p["ultima_publicada"] else ""),
                            archivo, linea, "pines"))
    return out


def verificar(ruta: Path, timeout: float = 10.0, hilos: int = 8,
              ahora: datetime | None = None) -> dict:
    ahora = ahora or datetime.now(timezone.utc)
    archivo = ruta.name
    leido = leer(ruta)
    hallazgos: list[Hallazgo] = []

    # Duplicados: dos líneas fijando el mismo paquete es la falla que el archivo
    # entero existe para que no pase, y el resolvedor se queda con una sola.
    vistos: dict[str, dict] = {}
    for p in leido["pines"]:
        clave = p["nombre"].lower().replace("_", "-")
        previo = vistos.get(clave)
        if previo:
            hallazgos.append(Hallazgo("pin/duplicado", "error",
                                      f"{p['nombre']} está fijado dos veces: "
                                      f"{previo['pin']} en la línea {previo['linea']} "
                                      f"y {p['pin']} acá",
                                      archivo, p["linea"], "pines"))
        else:
            vistos[clave] = p

    if not leido["pines"]:
        hallazgos.append(Hallazgo("pines/sin_pines", "error",
                                  "no encontré ninguna línea `nombre==version` en los bloques",
                                  archivo, 0, "pines"))

    # La fecha del encabezado.
    dias = None
    if leido["verificado_el"] is None:
        hallazgos.append(Hallazgo("pines/fecha_ausente", "aviso",
                                  "falta la línea `Verificado contra PyPI el AAAA-MM-DD`",
                                  archivo, 0, "pines"))
    else:
        d = _momento(leido["verificado_el"] + "T00:00:00+00:00")
        dias = (ahora - d).days if d else None
        if dias is not None and dias > VENCE_DIAS:
            hallazgos.append(Hallazgo("pines/fecha_vencida", "aviso",
                                      f"la última verificación fue hace {dias} días "
                                      f"(máximo {VENCE_DIAS}): corré esto y actualizá "
                                      f"la fecha del encabezado",
                                      archivo, 0, "pines"))

    # El modelo. Esta compuerta no necesita red y por eso corre siempre.
    modelo = leido["modelo"]
    if modelo is None:
        hallazgos.append(Hallazgo("modelo/ausente", "error",
                                  "no encontré la línea `MODELO=` en ningún bloque",
                                  archivo, 0, "pines"))
    elif modelo not in MODELOS_VIGENTES:
        hallazgos.append(Hallazgo("modelo/retirado", "error",
                                  f"`MODELO={modelo}` no está entre los vigentes "
                                  f"{list(MODELOS_VIGENTES)}: un cambio de modelo vuelve "
                                  f"a correr el bucle de auditoría",
                                  archivo, leido["modelo_linea"], "pines"))

    paquetes: list[dict] = []
    if leido["pines"]:
        with ThreadPoolExecutor(max_workers=max(1, hilos)) as pool:
            paquetes = list(pool.map(lambda p: revisar_paquete(p, timeout, ahora), leido["pines"]))
    sin_verificar = [p for p in paquetes if p["estado"] == "sin_verificar"]
    if paquetes and len(sin_verificar) == len(paquetes):
        # Cuando cayó todo, cayó la red, y son 28 líneas diciendo lo mismo. Una
        # sola dice lo mismo y deja ver el hallazgo del modelo, que sí corrió.
        hallazgos.append(Hallazgo("registro/sin_red", "aviso",
                                  f"no pude consultar PyPI: ninguno de los {len(paquetes)} "
                                  f"paquetes se verificó ({paquetes[0]['error']})",
                                  archivo, 0, "entorno"))
    else:
        for p in paquetes:
            hallazgos += hallazgos_de_paquete(p, archivo)
    errores = [h for h in hallazgos if h.nivel == "error"]
    if errores:
        veredicto = "fail"
    elif paquetes and len(sin_verificar) == len(paquetes):
        # Ni `pass` ni `fail`: la mitad que consulta el registro no corrió, y
        # decir que está bien sería mentir sobre lo que se comparó.
        veredicto = "sin_verificar"
    else:
        veredicto = "pass"

    return {
        "pines": str(ruta),
        "veredicto": veredicto,
        "errores": len(errores),
        "avisos": len(hallazgos) - len(errores),
        "verificado_el": leido["verificado_el"],
        "dias_desde_verificacion": dias,
        "modelo": {
            "declarado": modelo,
            "vigente": modelo in MODELOS_VIGENTES,
            "vigentes": list(MODELOS_VIGENTES),
        },
        "paquetes": paquetes,
        "sin_verificar": len(sin_verificar),
        "hallazgos": [h.dict() for h in hallazgos],
    }


# ─── Salida ─────────────────────────────────────────────────────────────────
def _dias(n: int) -> str:
    return f"{n} día" if n == 1 else f"{n} días"


def _edad(horas: float | None) -> str:
    if horas is None:
        return "sin fecha"
    if horas < 72:
        return f"hace {horas:.0f} h"
    return f"hace {_dias(round(horas / 24))}"


def _imprimir(r: dict) -> None:
    cab = f"PINES.md · {len(r['paquetes'])} paquetes"
    if r["verificado_el"]:
        cab += f" · verificado el {r['verificado_el']}"
        if r["dias_desde_verificacion"] is not None:
            cab += f" (hace {_dias(r['dias_desde_verificacion'])})"
    print(cab)

    m = r["modelo"]
    estado = "vigente" if m["vigente"] else "NO VIGENTE"
    print(f"MODELO={m['declarado']} · {estado}")
    print()

    ancho = max([len(p["nombre"]) for p in r["paquetes"]] + [8])
    apin = max([len(p["pin"]) for p in r["paquetes"]] + [3])
    print(f"  {'paquete':{ancho}}  {'pin':{apin}}  {'última':12}  estado")
    for p in r["paquetes"]:
        if p["estado"] == "ausente":
            nota, ultima = "NO EXISTE en PyPI", "—"
        elif p["estado"] != "verificado":
            nota = f"sin verificar · {p['error']}"
            ultima = "—"
        else:
            ultima = p["ultima"] or "—"
            partes = []
            partes.append("SE MOVIÓ" if p["movido"] else "al día")
            partes.append(_edad(p["ultima_horas"]))
            if p["sin_reposo"]:
                partes.append("sin reposo: no se fija")
            if p["pin_existe"] is False:
                partes.append("el pin no existe en PyPI")
            if p["pin_retirado"]:
                partes.append("el pin está retirado")
            nota = " · ".join(partes)
        print(f"  {p['nombre']:{ancho}}  {p['pin']:{apin}}  {ultima:12}  {nota}")

    print()
    print(f"verificar_pines: {r['veredicto'].upper()} · "
          f"{r['errores']} errores · {r['avisos']} avisos")
    for h in r["hallazgos"]:
        marca = "ERROR" if h["nivel"] == "error" else "aviso"
        sitio = f"{h['archivo']}:{h['linea']}" if h["archivo"] else "—"
        print(f"  [{marca}] {h['id']:26} {sitio:16} {h['evidencia'][:110]}")
    if r["veredicto"] == "sin_verificar":
        print("  no hubo red: nada se comparó contra PyPI. Lo único que corrió fue "
              "la compuerta del modelo.")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Compara los pines de PINES.md contra PyPI y la lista de modelos")
    p.add_argument("--pines", type=Path, default=RAIZ / "PINES.md")
    p.add_argument("--json", action="store_true")
    p.add_argument("--timeout", type=float, default=10.0,
                   help="segundos por consulta a PyPI (default 10)")
    p.add_argument("--hilos", type=int, default=8)
    args = p.parse_args(argv)

    if not args.pines.is_file():
        print(f"No existe {args.pines}", file=sys.stderr)
        return 1

    r = verificar(args.pines, timeout=args.timeout, hilos=args.hilos)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        _imprimir(r)
    # `sin_verificar` no falla la corrida: sin red no hay nada que comparar y no
    # es culpa del archivo. `fail` sí, y el modelo retirado llega hasta acá aunque
    # la red esté caída.
    return 0 if r["veredicto"] in ("pass", "sin_verificar") else 2


if __name__ == "__main__":
    sys.exit(main())
