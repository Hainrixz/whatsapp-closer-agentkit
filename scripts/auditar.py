#!/usr/bin/env python3
"""La compuerta. Corre en la máquina de quien clona, no en la nuestra.

Se invoca sola como `/revisar` y como última fase de `/armar-cerrador`. Es lo único que separa
un kit que anda de un kit que se lee bien, así que cada chequeo de acá es mecánico: un comando
que sale 0 o 1, o una aserción sobre un archivo. Ninguno dice "revisá el código".

## CERO RED, CERO CREDENCIALES

Nada de este archivo abre un socket ni lee un secreto. No es prolijidad: es la condición para
que la compuerta exista.

`/revisar` corre esto con un comando inyectado en la skill. Si el comando cuelga o sale
distinto de cero, **la skill entera se aborta y Claude no ve nada** — o sea, la protección
desaparece justo cuando hacía falta. Un chequeo que intente alcanzar a Meta o a Anthropic con
mala conexión se queda dos minutos esperando un timeout de TCP, y ahí ya no hay reporte.

A alguien le va a parecer una mejora obvia agregar "y de paso verificamos que el token de Meta
ande de verdad". No. Eso va en `/probar`, que corre cuando vos decidís y puede tardar lo que
quiera. Acá no.

Por lo mismo, cada subproceso que se lanza lleva timeout y un entorno con las variables que
parecen secreto sacadas: si un chequeo alguna vez intentara autenticarse, no tendría con qué.
Son tres, y los tres ejecutan código **del build**, que es literalmente lo que están auditando:
`wire_schema`, `firmas` y el validador del contrato. Ninguno se importa en este proceso.

Nada más se ejecuta. `PINES.md` se lee acá adentro con `re`, porque lo que hace falta de él son
datos: una lista de `nombre==version`, una línea `MODELO=`, una imagen y una fecha. Ejecutar un
archivo para conseguir datos fue el agujero, y aislarlo no lo cerraba: una lista negra de
variables por nombre tapa las cinco que alguien nombró y deja pasar la clave privada, la
contraseña de producción y el webhook, y el código igual escribe en disco, sale a la red y cuelga
hasta que el timeout lo corte. La lista de modelos vigentes es una constante de este archivo por
lo mismo. `scripts/verificar_pines.py` se queda, se corre a mano y sale a PyPI: eso último es
exactamente por qué la compuerta no tiene por qué invocarlo.

## Qué mira, en orden

Del más barato y diagnóstico al más caro. Los que necesitan `agente/` —o sea, que la
construcción ya haya corrido— **saltean** con el motivo escrito mientras no exista: alguien va a
correr `/revisar` antes de construir, y eso es legítimo. Con `agente/` en el árbol ya no lo es, y
ahí el salteo pesa: ver el veredicto `parcial`, abajo.

    01 blueprint-existe  cada `blueprint/NN-*.md` citado está en el árbol y no está vacío
    02 manifiesto        cada plantilla contra su sha256, y el build contra la plantilla
    03 railway-arranque  la clave que NO va en railway.json: un startCommand pisa el CMD
    04 claudemd-tam      CLAUDE.md ≤ 2600 bytes: se paga en cada turno
    05 pines             `==` en toda línea, los números de PINES.md, el modelo y la imagen
    06 deps-imports      cada raíz importada mapea a una distribución fijada
    07 deps-drivers      el driver que vive adentro de una URL y ningún import declara
    08 secretos          siete patrones de credencial, y `.env` ignorado y sin rastrear
    09 gitignore-anclado ningún patrón se lleva el núcleo verbatim, y el núcleo está rastreado
    10 modelo            los `claude-*` vigentes, y los cuatro parámetros que dan 400
    11 wire-schema       el esquema angosto y su golden
    12 http-unico        un solo cliente HTTP, con timeout
    13 enviar-unico      ninguna URL de mensajería fuera de `agente/enviar.py`
    14 agente-completo   cada módulo del piso, con los símbolos que la tabla promete
    15 cache-estatico    nada variable en el prefijo del prompt de sistema
    16 contrato          las salidas validan, vienen del build, y los pasos son 1..6
    17 contrato-control  cinco mutaciones que el validador TIENE que rechazar
    18 firmas            los dos fixtures crudos, con el espaciado torcido intacto
    19 pruebas           `pytest pruebas -q`: piso de nodos, techo de salteos, y por qué
    20 playbook          el bloque valida, y el piso contesta descuento y garantía
    21 panel-cerrado     toda ruta de `/api/` detrás de `exigir_token`, y `/salud` afuera
    22 rutas-del-contrato las diez rutas de la tabla de § 3, y ninguna más
    23 censo-de-campos   cada campo del contrato de salida: afirmado, o escrito por qué no

El primero va primero por lo que cuesta y por lo que tapa. Las diez skills dicen «leé
`blueprint/NN-*.md` y seguilo»: sin ese archivo el comando es un cascarón, y los otros
veintidós chequeos no preguntan por él ni una vez.

`agente-completo` es el que faltaba y el que dejaba pasar un árbol de mentira: los demás miran
los módulos que hay, así que un `agente/` con dos archivos adentro los pasa todos. Ese chequeo
es el único que pregunta por los que no están.

`censo-de-campos` hace lo mismo un piso más arriba: los veintidós de arriba miran el árbol, y
ninguno pregunta si la suite **afirma** lo que el contrato declara. Siete rondas seguidas
encontraron un campo declarado que ninguna prueba ataba a nada —`contacto.numero` en vacío,
`objecion_en_playbook` siempre en falso, `urgencia` fija en nulo—, y las siete veces la compuerta
dijo `PASS` con la suite entera en verde. Es el único chequeo que se apoya en una corrida que se
pide aparte, `--censo`, porque medirlo cuesta una suite por campo.

## Uso

    python3 scripts/auditar.py                      # texto
    python3 scripts/auditar.py --formato json       # o --json
    python3 scripts/auditar.py --raiz /otra/copia
    python3 scripts/auditar.py --publicando         # antes de `git push`: ver el chequeo 09
    python3 scripts/auditar.py --censo              # la corrida cara del chequeo 23
    python3 scripts/auditar.py --censo --campo crm/proximo_paso    # uno solo, sin escribir nada

Escribe `EVIDENCIA/gates.json` siempre, pase o falle. Son tres veredictos y tres salidas:

    pass     0   corrió todo lo que en este árbol podía correr, y no encontró nada
    parcial  3   no encontró nada, pero algo que tenía que correr no corrió
    fail     2   encontró por lo menos un error

`parcial` existe porque un salteado no es un aprobado. `contrato-control` es el control negativo
de la validación entera: cuando saltea, "todo verde" no se distingue de "no se está validando
nada", y eso no se despliega. Lo mismo para los que necesitan `agente/` cuando `agente/` ya está.
Los avisos no mueven el veredicto, y se imprimen igual.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Nada de este script tiene por qué dejar __pycache__ en el árbol de quien clona.
sys.dont_write_bytecode = True

RAIZ = Path(__file__).resolve().parents[1]
EVIDENCIA = Path("EVIDENCIA/gates.json")

LIMITE_CLAUDEMD = 2600
SEGUNDOS_CORTO = 60
# La suite entera. Más que esto y `/revisar` deja de ser una compuerta y pasa a ser una espera:
# lo que tarde más va a `/probar`, que corre cuando vos querés.
SEGUNDOS_PRUEBAS = 120

# Los cuatro parámetros que la API rechaza con 400. Ver PINES.md → Modelo.
PROHIBIDOS_DEL_MODELO = ("budget_tokens", "temperature", "top_p", "top_k")

# Un id de modelo tiene esta forma. El filtro por familia es a propósito: sin él, un literal
# como "claude-code" o "claude-anatomy" se reporta como modelo retirado y el que audita
# aprende a ignorar el chequeo, que es la única forma de romperlo del todo.
MODELO_LITERAL = re.compile(r"claude-[a-z0-9.-]*(?:opus|sonnet|haiku|instant)[a-z0-9.-]*")

# Cómo se cita un archivo del blueprint: `blueprint/00-mapa.md`, con o sin comillas alrededor.
# Los diez comandos del kit no traen procedimiento adentro: traen esta cita.
CITA_BLUEPRINT = re.compile(r"blueprint/((?:[\w.-]+/)*[\w.-]+\.md)")

# El driver vive adentro de una cadena de conexión y ningún import lo nombra. Ver PINES.md.
DRIVER_EN_URL = re.compile(r"\+(\w+)://")

# El mismo driver, pero puesto en la cadena desde afuera: `postgresql+%s://`, `+{}://`,
# `+{drv}://`. Acá el nombre no está escrito en ningún lado del código, así que el chequeo no
# puede decir cuál es: lo dice como aviso y lo busca donde sí está escrito, que es la
# configuración —y por eso el barrido de texto mira el repo entero y no solo `agente/`.
DRIVER_INTERPOLADO = re.compile(r"\+(%s|%\([\w]+\)s|\{[\w.\[\]]*\})://")

# Un pin es `nombre==version`, con extras opcionales. Cualquier otra cosa no es un pin.
LINEA_FIJADA = re.compile(r"^[A-Za-z0-9._-]+(\[[a-z,]+\])?==")

# Los otros dos números fijados que NO viven en requirements.txt: el modelo, que `env.example`
# repite, y la imagen base, que el Dockerfile repite. Los dos salen de PINES.md igual que los 28
# pines, y los dos se comparan igual. Ver PINES.md → Modelo y → Python.
MODELO_EN_ENV = re.compile(r"^\s*MODELO\s*=\s*([^\s#]+)")
IMAGEN_EN_PINES = re.compile(r"`(python:[A-Za-z0-9._-]+)`")
FROM_DOCKERFILE = re.compile(r"^\s*FROM\s+(\S+)", re.MULTILINE)

# Cómo se lee PINES.md. Los pines viven adentro de bloques de código, y solo cuentan los bloques
# que no declaran lenguaje: el bloque `python` de PINES.md trae una cadena de conexión y el `bash`
# trae la línea con la que se corre `verificar_pines.py` a mano. Ninguno es una lista de versiones.
CERCA_DE_PINES = re.compile(r"^\s*```(.*)$")
INFO_DE_PINES = frozenset({"", "text", "txt", "ini", "requirements"})
PIN_EN_PINES = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9._-]*)\s*==\s*([A-Za-z0-9][A-Za-z0-9._+!-]*)\s*(?:#.*)?$")
MODELO_EN_PINES = re.compile(r"^\s*MODELO\s*=\s*([A-Za-z0-9._-]+)\s*(?:#.*)?$")
FECHA_EN_PINES = re.compile(r"Verificado contra PyPI el (\d{4}-\d{2}-\d{2})")

# Los modelos vigentes. Es una lista escrita a mano porque no hay de dónde sacarla: un modelo
# retirado no lo informa ningún registro de paquetes, y se actualiza acá cuando sale una familia
# nueva. La misma tupla está en `scripts/verificar_pines.py`, y esa repetición es a propósito: la
# alternativa era ejecutar ese archivo para leerle tres cadenas, que es de donde salió la fuga.
MODELOS_VIGENTES = ("claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5")

# La clave que `railway.json` no tiene que traer. Ver plantillas/README.md: una ausencia no se
# puede verificar por hash, así que se busca aparte.
CLAVE_DE_ARRANQUE = "startCommand"

# Los dos endpoints de mensajería, que es lo que el invariante 2 protege. Un POST a cualquiera de
# los dos le llega a una persona por WhatsApp; un POST a cualquier otro lado, no. El chequeo 13 se
# decide con esta tabla y con nada más: no por el verbo, no por el archivo, no por el cliente.
#
#   Meta    https://graph.facebook.com/<version>/<phone_number_id>/messages
#   Zernio  https://zernio.com/api/v1/inbox/conversations/<id>/messages
#
# El de Zernio se reconoce por el camino y no por el host: la base viaja en una constante que a
# veces no se puede resolver, y `/inbox/conversations` no aparece en ninguna otra API de este kit.
ENDPOINT_ZERNIO = "/inbox/conversations"
ENDPOINT_META = re.compile(r"graph\.facebook\.com/[^\s\"']*/messages")
HOST_META = "graph.facebook.com"

# Las variables que se le sacan a cualquier subproceso. Un chequeo que quisiera autenticarse
# contra algo no encontraría con qué, y eso es justamente lo que queremos.
NOMBRE_SECRETOSO = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|CREDENCIAL|API_?KEY|_KEY|SIGNATURE)",
    re.IGNORECASE,
)

# Nombres de parámetro que traen datos de la petición. Un f-string del prompt de sistema que
# lea de acá pone la tasa de acierto del caché en cero.
DEL_REQUEST = frozenset(
    {"request", "req", "evento", "event", "mensaje", "msg", "payload", "body", "cuerpo",
     "entrada", "webhook", "contacto", "chat", "texto", "conversacion"}
)

# Raíz importada → distribución que la provee, solo para las que no coinciden por nombre.
# El resto se resuelve normalizando (minúsculas y `_` → `-`), que es lo que hace pip.
IMPORT_A_DISTRIBUCION = {
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
    "jose": "python-jose",
    "jwt": "PyJWT",
    "bs4": "beautifulsoup4",
    "PIL": "pillow",
    "attr": "attrs",
    "googleapiclient": "google-api-python-client",
    "google": "google-api-python-client",
    "psycopg2": "psycopg2-binary",
    "sklearn": "scikit-learn",
}

# Funciones y módulos donde vive el constructor del prompt de sistema. El chequeo
# `cache-estatico` mira adentro de esto y de nada más, así que la regla se dice acá y en voz
# alta: si tu constructor no se llama así, el chequeo saltea y te lo avisa por pantalla.
NOMBRE_DE_PROMPT = re.compile(r"(?i)(prompt|sistema|system)")


# ─────────────────────────────────────────────────────────────────────────────
# Hallazgos y chequeos
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Hallazgo:
    """Misma forma que en `validar_artefacto.py` y `verificar_pines.py`: un solo objeto para
    todo el linaje de compuertas, así el que lee tres reportes lee siempre lo mismo."""

    id: str
    nivel: str  # "error" | "aviso"
    evidencia: str
    archivo: str = ""
    linea: int = 0
    atribuible_a: str = ""  # "kit" | "build" | "entorno"

    def dict(self) -> dict:
        return asdict(self)


@dataclass
class Chequeo:
    id: str
    titulo: str
    estado: str = "pass"  # "pass" | "fail" | "salteado"
    motivo: str = ""
    hallazgos: list[Hallazgo] = field(default_factory=list)

    def dict(self) -> dict:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "estado": self.estado,
            "motivo": self.motivo,
            "hallazgos": [h.dict() for h in self.hallazgos],
        }


class Reporte:
    """Lo que cada chequeo va llenando. Saltear no es pasar, y se dice con otra palabra."""

    def __init__(self, id: str, titulo: str) -> None:
        self.chequeo = Chequeo(id=id, titulo=titulo)
        self.nota = ""

    def error(self, id: str, evidencia: str, archivo: str = "", linea: int = 0,
              atribuible_a: str = "kit") -> None:
        self.chequeo.hallazgos.append(Hallazgo(id, "error", evidencia, archivo, linea, atribuible_a))

    def aviso(self, id: str, evidencia: str, archivo: str = "", linea: int = 0,
              atribuible_a: str = "kit") -> None:
        self.chequeo.hallazgos.append(Hallazgo(id, "aviso", evidencia, archivo, linea, atribuible_a))

    def saltear(self, motivo: str) -> None:
        self.chequeo.estado = "salteado"
        self.chequeo.motivo = motivo

    def decir(self, nota: str) -> None:
        """Una línea para el resumen cuando el chequeo pasa. No es un hallazgo."""
        self.nota = nota

    def cerrar(self) -> Chequeo:
        if any(h.nivel == "error" for h in self.chequeo.hallazgos):
            self.chequeo.estado = "fail"
        elif self.chequeo.estado != "salteado":
            self.chequeo.estado = "pass"
            self.chequeo.motivo = self.nota
        return self.chequeo


# ─────────────────────────────────────────────────────────────────────────────
# Contexto y utilidades
# ─────────────────────────────────────────────────────────────────────────────


def _leer_pines(texto: str) -> dict:
    """`PINES.md` convertido en datos: los pines, el modelo, la imagen base y la fecha.

    Treinta líneas de `re` que no importan nada y no ejecutan nada. Antes esto era una llamada a
    `scripts/verificar_pines.py`, que sabe parsear el archivo y además sale a PyPI: para conseguir
    cuatro datos la compuerta ejecutaba un módulo entero, con lo que ese módulo dijera adentro.
    Meterlo en un subproceso con timeout y una lista negra de variables por nombre no alcanzaba
    —la clave privada de Google, la `DATABASE_URL` de producción y el webhook de Slack pasan
    enteros, y el código sigue escribiendo en disco y colgando hasta el corte—, así que no se
    ejecuta nada. Los dos usos eran datos desde el principio.
    """
    pines: list[dict] = []
    modelo, modelo_linea = None, 0
    dentro, aceptar = False, False
    for n, linea in enumerate(texto.splitlines(), 1):
        cerca = CERCA_DE_PINES.match(linea)
        if cerca:
            dentro = not dentro
            aceptar = dentro and cerca.group(1).strip().lower() in INFO_DE_PINES
            continue
        if not (dentro and aceptar):
            continue
        m = PIN_EN_PINES.match(linea)
        if m:
            pines.append({"nombre": m.group(1), "pin": m.group(2), "linea": n})
            continue
        m = MODELO_EN_PINES.match(linea)
        if m:
            modelo, modelo_linea = m.group(1), n
    fecha = FECHA_EN_PINES.search(texto)
    return {
        "pines": pines,
        "modelo": modelo,
        "modelo_linea": modelo_linea,
        # La imagen base y la fecha se nombran en la prosa, no adentro de un bloque.
        "imagenes": sorted(set(IMAGEN_EN_PINES.findall(texto))),
        "verificado_el": fecha.group(1) if fecha else None,
    }


class Contexto:
    def __init__(self, raiz: Path, *, publicando: bool = False) -> None:
        self.raiz = raiz
        self.agente = raiz / "agente"
        self.hay_agente = self.agente.is_dir()
        # `--publicando`: esta corrida es la que autoriza un `git push` del kit. Lo que en medio
        # de una construcción es aviso —el núcleo todavía sin agregar al índice— acá es error.
        # Ver el chequeo 09.
        self.publicando = publicando
        self.interprete = _elegir_interprete(raiz)
        # El del proyecto primero y el que está corriendo esto después. Dos chequeos necesitan
        # pydantic y jsonschema, y en una máquina cualquiera puede estar cualquiera de los dos:
        # las dependencias fijadas viven en `.venv`, pero alguien puede tenerlas en el sistema.
        # Probar los dos es más barato que saltear un chequeo que sí podía correr.
        self.interpretes = [self.interprete]
        if sys.executable and sys.executable != self.interprete:
            self.interpretes.append(sys.executable)
        self._archivos: list[Path] | None = None
        self._pines = None
        self._pines_leido = False
        self._pines_problema = ""
        # Lo prende el chequeo `manifiesto` cuando un archivo generado se apartó de su
        # plantilla. Desde ahí, nada de `agente/` se ejecuta: ya sabemos que ese archivo no es
        # el que enviamos.
        self.build_derivado = False

    # El árbol .py del agente, que es sobre lo que corren la mitad de los chequeos.
    def modulos(self) -> list[Path]:
        if not self.hay_agente:
            return []
        return [p for p in sorted(self.agente.rglob("*.py")) if "__pycache__" not in p.parts]

    def rel(self, ruta: Path) -> str:
        try:
            return ruta.relative_to(self.raiz).as_posix()
        except ValueError:
            return str(ruta)

    def archivos_del_repo(self) -> list[Path]:
        """Lo que el próximo commit se va a llevar: rastreado y sin rastrear.

        `git ls-files` a secas mira solo lo rastreado, y en un kit recién clonado o recién
        armado eso puede ser media docena de archivos. Un secreto en un archivo todavía sin
        agregar entra al primer commit igual.
        """
        if self._archivos is not None:
            return self._archivos
        codigo, salida = _correr(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=self.raiz, texto=False,
        )
        if codigo != 0:
            self._archivos = []
            return self._archivos
        nombres = [n for n in salida.split("\0") if n]
        self._archivos = [self.raiz / n for n in nombres]
        return self._archivos

    def requirements(self) -> list[Path]:
        """El del kit y, si ya se construyó, el que quedó en la raíz."""
        candidatos = [self.raiz / "plantillas/infra/requirements.txt", self.raiz / "requirements.txt"]
        return [p for p in candidatos if p.is_file()]

    def pines(self) -> dict | None:
        """El `PINES.md` **del árbol auditado**, leído con el parser de esta compuerta.

        Las dos mitades vienen del lugar correcto, que antes no pasaba: el archivo sale de
        `--raiz` y el parser sale de acá. Antes el parser salía de
        `Path(__file__).with_name("verificar_pines.py")` —el del script invocado, no el del árbol
        auditado—, así que auditar una copia con el parser roto usaba el parser sano de esta copia
        y daba verde.

        Un PINES.md que no rinde un solo pin es un problema y se dice: es el estado de un archivo
        al que le movieron los bloques o le cambiaron la forma, y antes apagaba en silencio la
        comparación entera mientras el chequeo seguía saliendo en verde.
        """
        if self._pines_leido:
            return self._pines
        self._pines_leido = True
        archivo = self.raiz / "PINES.md"
        if not archivo.is_file():
            self._pines_problema = "no hay PINES.md en la raíz"
            return None
        leido = _leer_pines(_texto(archivo))
        if not leido["pines"]:
            self._pines_problema = (
                "no hay una sola línea `nombre==version` adentro de un bloque de código: o el "
                "archivo está vacío, o los bloques quedaron marcados con un lenguaje que no es "
                "una lista de versiones")
            return None
        self._pines = leido
        return self._pines

    def pines_problema(self) -> str:
        """Por qué no se pudo leer PINES.md. Vacío mientras nadie haya preguntado."""
        return self._pines_problema


def _elegir_interprete(raiz: Path) -> str:
    """El intérprete del proyecto si hay uno, y si no el que está corriendo esto.

    Después de `/armar-cerrador` las dependencias fijadas viven en `.venv`, no en el Python del
    sistema. Sin esta línea, `wire-schema` y `contrato` saltean para siempre por falta de
    pydantic aunque el proyecto las tenga instaladas al lado.
    """
    for rel in (".venv/bin/python3", ".venv/bin/python", "venv/bin/python3",
                ".venv/Scripts/python.exe"):
        cand = raiz / rel
        if cand.is_file():
            return str(cand)
    return sys.executable


def _entorno_sin_secretos() -> dict:
    return {k: v for k, v in os.environ.items() if not NOMBRE_SECRETOSO.search(k)} | {
        "PYTHONDONTWRITEBYTECODE": "1"
    }


def _correr(cmd: list[str], *, cwd: Path, timeout: int = SEGUNDOS_CORTO, entrada: str | None = None,
            texto: bool = True, entorno: dict | None = None) -> tuple[int, str]:
    """Un subproceso con timeout y sin credenciales. Nunca levanta: devuelve (código, salida).

    Una compuerta que revienta con un rastreo de pila no es una compuerta que falla: es una que
    no corrió, y el reporte queda a medias.

    `entorno` agrega variables **encima** del entorno sin secretos, nunca abajo: lo usa el censo
    para bajarle el campo y el mutante a su plugin. No es una puerta para meter credenciales —lo
    que se agrega se lee en la llamada, y las tres que hay son rutas y un nombre de campo—.
    """
    try:
        r = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, timeout=timeout, check=False,
            input=(entrada.encode("utf-8") if entrada is not None else None),
            env=_entorno_sin_secretos() | (entorno or {}),
        )
    except FileNotFoundError:
        return 127, f"no encontré `{cmd[0]}` en esta máquina"
    except subprocess.TimeoutExpired:
        return 124, f"`{cmd[0]}` pasó de {timeout} s y lo corté"
    except OSError as e:
        return 126, f"no pude lanzar `{cmd[0]}`: {e}"
    crudo = r.stdout + r.stderr
    if not texto:
        return r.returncode, crudo.decode("utf-8", "replace")
    return r.returncode, crudo.decode("utf-8", "replace").strip()


# Acá vivía `_cargar_modulo`, que importaba un archivo por ruta y lo ejecutaba en el proceso de
# la compuerta. No quedó ningún uso legítimo: los tres módulos que se ejecutan —wire_schema,
# firmas y el validador del contrato— entran por un driver en `-c`, con el timeout y el entorno
# sin secretos de `_correr`, y los tres son código del build, que es lo que se está auditando.
# `verificar_pines` ya no es ninguna de las dos cosas: de él hacían falta datos, y los datos se
# parsean. La función no se deja "por si acaso": una que ejecuta código arbitrario en este proceso
# es una trampa esperando a alguien.


def _texto(ruta: Path) -> str:
    try:
        return ruta.read_bytes().decode("utf-8", "replace")
    except OSError:
        return ""


# Lo que no es del proyecto aunque esté adentro de la carpeta. Se nombra una vez y lo usan los
# dos chequeos que recorren el árbol con rglob en vez de preguntarle a git.
CARPETAS_QUE_NO_SE_MIRAN = frozenset(
    {".git", ".venv", "venv", "node_modules", "__pycache__", ".ruff_cache", ".mypy_cache",
     ".pytest_cache", ".tox", "EVIDENCIA", "site-packages"}
)


def _es_ruido(partes: tuple[str, ...]) -> bool:
    return any(p in CARPETAS_QUE_NO_SE_MIRAN for p in partes)


def _normalizar(nombre: str) -> str:
    return re.sub(r"[-_.]+", "-", nombre.strip().lower())


def _arbol(ruta: Path) -> tuple[ast.Module | None, str]:
    try:
        return ast.parse(_texto(ruta), filename=str(ruta)), ""
    except SyntaxError as e:
        return None, f"línea {e.lineno}: {e.msg}"


def _prosa_suelta(arbol: ast.Module) -> set[int]:
    """Toda cadena que es un statement suelto, para no confundir prosa con código.

    Antes esto miraba sólo el primer statement de cada cuerpo, que es donde va el docstring de
    manual. Era muy angosto, y el caso que lo rompió es del propio kit: `blueprint/31-proveedores.md`
    paso 3 manda escribir dos piezas en `agente/proveedores/demo.py` —el proveedor y su
    transporte—, cada una con su prosa. La segunda cae como segunda cadena del módulo, y esa
    prosa nombra `graph.facebook.com` para advertir que un transporte de demostración que
    conteste ese host es un agente que cree que mandó y no mandó. O sea: la advertencia salía
    marcada como el defecto que advierte, y el kit sólo pasaba si la prosa se escribía primero.

    Una cadena que es un statement se evalúa y se tira. No puede ser una URL en uso, esté en la
    posición que esté: para usarla hay que asignarla o pasarla, y ahí ya no es un `ast.Expr`.
    """
    return {id(n.value) for n in ast.walk(arbol)
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, str)}


def _literales(arbol: ast.Module, *, sin_prosa: bool = False):
    """(línea, texto) de cada literal de cadena, incluidas las partes constantes de un f-string.

    Se miran los literales y no el archivo entero a propósito: un comentario que explica por
    qué NO se hace algo no es hacerlo, y este kit escribe código muy comentado. Un chequeo que
    reporta el comentario que dice "no pases temperature" enseña a ignorar el chequeo.
    """
    saltear = _prosa_suelta(arbol) if sin_prosa else set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            if id(nodo) in saltear:
                continue
            yield nodo.lineno, nodo.value


# Hasta acá baja `_pegado`, y ni un nivel más. `"a" + "b" + "c" + …` se anida una vez por
# término: mil términos son mil llamadas anidadas y el intérprete corta en ~1000 con
# RecursionError. Seis kilobytes de fuente alcanzan, que es lo que emite cualquier generador que
# arma un prompt largo con `+`. Ninguna cadena de conexión escrita a mano tiene cincuenta
# términos, y lo que sí los tiene no es una URL: pasado el tope esto devuelve None y los pedazos
# de adentro se miran igual, porque el recorrido pasa por todos los nodos del árbol.
TOPE_PEGADO = 50

# `%s`, `%r`, `%d` y `%(nombre)s`. Un molde con ancho —`"%9999999d"`— no se resuelve: formatearlo
# pide esa cantidad de bytes, y esto corre en la máquina de quien clona.
SPEC_POR_CIENTO = re.compile(r"%(?:%|\(\w+\)[srd]|[srd])")

# Lo mismo del otro lado: `{}`, `{0}` y `{nombre}`, nada más. Sin `:` no hay ancho, y sin `.` ni
# `[` no se le pide un atributo a nadie.
CAMPO_FORMAT = re.compile(r"\{[^{}]*\}")
CAMPO_FORMAT_SIMPLE = re.compile(r"^\{\w*\}$")

# Lo que devuelve `_valor_literal` cuando el valor no está escrito ahí mismo. None no sirve: un
# `None` literal es un valor válido.
SIN_VALOR = object()


def _pegado(nodo: ast.AST, *, literales: bool = False, profundidad: int = 0) -> str | None:
    """La cadena que arma esta expresión, con `{}` donde el valor viene de afuera.

    Una constante suelta es media cadena. `"postgresql+" + "asyncpg://…"` es la otra mitad, y
    mirando literal por literal no aparece ninguna de las dos enteras: la de la izquierda no
    tiene `://` y la de la derecha no tiene `+`. Lo mismo con `%`, con `.format()`, con
    `"".join([...])` y con un f-string. Son cinco formas de escribir la misma línea, y cuatro se
    escapaban del chequeo que la busca.

    Con `literales=True` se resuelve además la interpolación cuyo argumento está escrito ahí
    mismo: `"postgresql+%s://" % "drivertres"` sale como `postgresql+drivertres://`. Sin eso el
    nombre del driver estaba a la vista en el mismo renglón y el chequeo igual lo reportaba como
    aviso, diciendo «acá no se lee cuál es». El aviso queda para lo que de verdad viene de
    afuera. No se ejecuta nada: `ast.literal_eval` reconoce literales y nada más.

    Devuelve None cuando la expresión no es una cadena que se pueda armar acá.
    """
    if profundidad > TOPE_PEGADO:
        return None
    hijo = {"literales": literales, "profundidad": profundidad + 1}
    if isinstance(nodo, ast.Constant):
        return nodo.value if isinstance(nodo.value, str) else None
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        izquierda, derecha = _pegado(nodo.left, **hijo), _pegado(nodo.right, **hijo)
        return None if izquierda is None or derecha is None else izquierda + derecha
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Mod):
        # `"postgresql+%s://…" % drv`: el molde es la izquierda y el `%s` queda a la vista.
        molde = _pegado(nodo.left, **hijo)
        return _por_ciento(molde, nodo.right) if literales else molde
    if isinstance(nodo, ast.JoinedStr):
        partes = []
        for parte in nodo.values:
            if isinstance(parte, ast.Constant) and isinstance(parte.value, str):
                partes.append(parte.value)
            else:
                partes.append(_campo_de_fstring(parte) if literales else "{}")
        return "".join(partes)
    if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
        if nodo.func.attr == "format":
            plantilla = _pegado(nodo.func.value, **hijo)
            return _formateado(plantilla, nodo) if literales else plantilla
        if nodo.func.attr == "join" and len(nodo.args) == 1:
            separador = _pegado(nodo.func.value, **hijo)
            elementos = nodo.args[0]
            if separador is None or not isinstance(elementos, (ast.List, ast.Tuple)):
                return None
            return separador.join(_pegado(e, **hijo) or "{}" for e in elementos.elts)
    return None


def _valor_literal(nodo: ast.AST):
    """El valor de una expresión escrita ahí mismo, o `SIN_VALOR`.

    `ast.literal_eval` no ejecuta nada: reconoce números, cadenas, tuplas, listas y diccionarios
    de literales, y levanta con cualquier otra cosa. Lo que venga de una variable, de una llamada
    o de la configuración no pasa por acá, y ese es justo el caso que se sigue diciendo como
    aviso.
    """
    try:
        valor = ast.literal_eval(nodo)
    except Exception:  # noqa: BLE001
        return SIN_VALOR
    if isinstance(valor, (str, int, float, bool, tuple, list, dict)) or valor is None:
        return valor
    return SIN_VALOR


def _por_ciento(molde: str | None, argumento: ast.AST) -> str | None:
    """`"postgresql+%s://" % "drivertres"`, ya resuelto. El molde solo, si no se puede."""
    # Si después de sacar los cuatro moldes que sabemos formatear todavía queda un `%`, el molde
    # tiene algo que no entendemos y no se toca.
    if molde is None or "%" in SPEC_POR_CIENTO.sub("", molde):
        return molde
    valor = _valor_literal(argumento)
    if valor is SIN_VALOR:
        return molde
    try:
        return molde % valor
    except Exception:  # noqa: BLE001
        return molde


def _formateado(plantilla: str | None, llamada: ast.Call) -> str | None:
    """Lo mismo para `.format()`: se resuelve solo si TODOS los argumentos son literales.

    Con uno solo que venga de afuera se devuelve la plantilla tal cual y el hallazgo vuelve a ser
    el aviso, que es lo correcto: ahí el nombre del driver de verdad no está escrito acá.
    """
    if plantilla is None or not _campos_simples(plantilla):
        return plantilla
    posicionales = []
    for a in llamada.args:
        valor = _valor_literal(a)
        if valor is SIN_VALOR:
            return plantilla
        posicionales.append(valor)
    nombrados = {}
    for k in llamada.keywords:
        valor = _valor_literal(k.value)
        if k.arg is None or valor is SIN_VALOR:
            return plantilla
        nombrados[k.arg] = valor
    try:
        return plantilla.format(*posicionales, **nombrados)
    except Exception:  # noqa: BLE001
        return plantilla


def _campos_simples(plantilla: str) -> bool:
    """Ningún campo con `:`, `!`, `.` ni `[`.

    No es prolijidad: `"{:>99999999}".format("x")` pide cien megabytes antes de que nadie pueda
    mirar el resultado, y esto corre en la máquina de quien clona. Un molde así no se resuelve, y
    el renglón sigue saliendo como aviso.
    """
    sin_escapes = plantilla.replace("{{", "").replace("}}", "")
    return all(CAMPO_FORMAT_SIMPLE.match(campo) for campo in CAMPO_FORMAT.findall(sin_escapes))


def _campo_de_fstring(parte: ast.AST) -> str:
    """El pedazo variable de un f-string, cuando el valor está escrito ahí mismo."""
    if (not isinstance(parte, ast.FormattedValue) or parte.format_spec is not None
            or parte.conversion not in (-1, None)):
        return "{}"
    valor = _valor_literal(parte.value)
    if valor is SIN_VALOR:
        return "{}"
    try:
        return str(valor)
    except Exception:  # noqa: BLE001
        return "{}"


def _cadenas(arbol: ast.Module, *, sin_prosa: bool = True, literales: bool = True):
    """(línea, texto) de cada cadena del módulo, ya armada. Ver `_pegado`.

    Trae de más a propósito: `"a" + "b"` sale tres veces —`a`, `b` y `ab`— porque el recorrido
    pasa por los tres nodos. Quien llama deduplica por (archivo, línea), que es más barato que
    llevar la cuenta de qué nodo ya se miró.

    Con `literales=False` se pide la versión sin resolver, que sirve para una sola cosa: comparar
    los dos conjuntos y saber en qué líneas la interpolación se pudo resolver acá mismo.
    """
    saltear = _prosa_suelta(arbol) if sin_prosa else set()
    for nodo in ast.walk(arbol):
        if id(nodo) in saltear:
            continue
        texto = _pegado(nodo, literales=literales)
        if texto is not None:
            yield getattr(nodo, "lineno", 0), texto


def _raiz_del_nombre(nodo: ast.AST) -> str:
    while isinstance(nodo, (ast.Attribute, ast.Subscript, ast.Call)):
        nodo = nodo.value if isinstance(nodo, (ast.Attribute, ast.Subscript)) else nodo.func
    return nodo.id if isinstance(nodo, ast.Name) else ""


def _fuente(nodo: ast.AST) -> str:
    try:
        return ast.unparse(nodo)[:80]
    except Exception:  # noqa: BLE001
        return type(nodo).__name__


# ─────────────────────────────────────────────────────────────────────────────
# 01 · blueprint-existe
# ─────────────────────────────────────────────────────────────────────────────


def chequeo_blueprint_existe(c: Contexto, r: Reporte) -> None:
    """Lo único que leen los diez comandos, y hasta hoy ningún chequeo preguntaba si estaba.

    Cada `SKILL.md` dice «leé `blueprint/NN-*.md` y seguilo»: el procedimiento no vive en la
    skill, vive en el archivo citado. Si ese archivo no está, el comando no falla —abre, no
    encuentra nada y construye de memoria, que es lo único que el kit pide no hacer—, y los
    otros veintidós chequeos dan verde igual porque ninguno mira ahí.

    Un rglob y una diferencia de conjuntos. Va primero por eso: es el más barato del registro y
    el que tapa a todos los demás.

    Existir no alcanza: se pide **tamaño mayor que cero**. Un archivo de cero bytes no es una
    hipótesis, es el estado real mientras otro proceso lo está escribiendo, y con `is_file()` a
    secas pasaba en verde. El comando lo abre, no encuentra nada y construye de memoria, que es
    exactamente lo que este chequeo existe para no dejar pasar.
    """
    citantes = _archivos_que_citan(c)
    citados: dict[str, list[str]] = {}
    for archivo in citantes:
        rel = c.rel(archivo)
        for n, linea in enumerate(_texto(archivo).splitlines(), 1):
            for cita in CITA_BLUEPRINT.findall(linea):
                citados.setdefault(cita, []).append(f"{rel}:{n}")

    carpeta = c.raiz / "blueprint"
    if not citados:
        r.saltear("ningún SKILL.md, CLAUDE.md ni blueprint/ cita un archivo de blueprint/: no hay "
                  "nada que exigir, y eso ya es raro")
        return

    faltan = 0
    for cita in sorted(citados):
        destino = carpeta / cita
        donde = ", ".join(citados[cita][:4])
        if destino.is_file() and _tamano(destino) > 0:
            continue
        faltan += 1
        if destino.is_file():
            r.error("blueprint/citado_y_vacio",
                    f"`blueprint/{cita}` existe y mide cero bytes, y lo citan {donde}. Es el "
                    f"estado en el que queda un archivo mientras alguien lo está escribiendo: el "
                    f"comando lo abre, no encuentra el procedimiento y construye de memoria, "
                    f"igual que si faltara. Existir no es estar",
                    f"blueprint/{cita}", 0, "kit")
            continue
        r.error("blueprint/citado_y_ausente",
                f"`blueprint/{cita}` no existe, y lo citan {donde}. Ahí adentro está el "
                f"procedimiento entero de esa fase: la skill dice «leé eso y seguilo», así que "
                f"sin el archivo el comando queda en cascarón y construye de memoria. Nada más "
                f"lo reporta: el comando abre igual y no tira un solo error",
                f"blueprint/{cita}", 0, "kit")

    # El caso inverso no rompe nada, y por eso es aviso: un archivo que no cita nadie no lo abre
    # ningún comando. O falta la cita, o sobra el archivo.
    if carpeta.is_dir():
        for archivo in sorted(carpeta.rglob("*.md")):
            if archivo.relative_to(carpeta).as_posix() not in citados:
                r.aviso("blueprint/sin_citar",
                        "existe y no lo cita ningún SKILL.md, ningún CLAUDE.md ni ningún otro "
                        "blueprint: no hay comando que lo abra, así que nadie lo va a leer",
                        c.rel(archivo), 0, "kit")
    if not faltan:
        r.decir(f"{len(citados)} archivo(s) citados por {len(citantes)}, todos con contenido")


def _tamano(ruta: Path) -> int:
    try:
        return ruta.stat().st_size
    except OSError:
        return 0


def _archivos_que_citan(c: Contexto) -> list[Path]:
    """Los que mandan a leer `blueprint/`: `CLAUDE.md`, cada `SKILL.md`, y los blueprints.

    Los blueprints también citan blueprints —`00-mapa.md` manda a la fase siguiente, y una fase
    manda a la de al lado— y esa cita se lee igual que la de una skill: el que la sigue abre el
    archivo y espera encontrar el procedimiento. Sin leerlos, un blueprint que apunta a otro que
    no existe no lo ve nadie, y la cadena se corta en el medio de una construcción.
    """
    encontrados = []
    claudemd = c.raiz / "CLAUDE.md"
    if claudemd.is_file():
        encontrados.append(claudemd)
    for skill in sorted(c.raiz.rglob("SKILL.md")):
        if _es_ruido(skill.relative_to(c.raiz).parts):
            continue
        encontrados.append(skill)
    carpeta = c.raiz / "blueprint"
    if carpeta.is_dir():
        encontrados += sorted(carpeta.rglob("*.md"))
    return encontrados


# ─────────────────────────────────────────────────────────────────────────────
# 02 · manifiesto
# ─────────────────────────────────────────────────────────────────────────────


def chequeo_manifiesto(c: Contexto, r: Reporte) -> None:
    """Delega en `scripts/hash_plantillas.py`, que ya hashea cada entrada y ya distingue los dos
    casos. Reimplementar el sha256 acá sería una segunda copia de la misma regla, que es
    exactamente lo que este kit no quiere: el día que las dos difieran, ninguna vale."""
    script = c.raiz / "scripts/hash_plantillas.py"
    manifiesto = c.raiz / "plantillas/MANIFIESTO.json"
    if not script.is_file():
        r.error("manifiesto/sin_script", "falta scripts/hash_plantillas.py: sin él no hay contra "
                "qué comparar las plantillas", "scripts/hash_plantillas.py")
        return
    if not manifiesto.is_file():
        r.error("manifiesto/ausente", "falta plantillas/MANIFIESTO.json: corré "
                "`python3 scripts/hash_plantillas.py --escribir`", "plantillas/MANIFIESTO.json")
        return

    cmd = [c.interprete, str(script), "--verificar"]
    if c.hay_agente:
        # Solo cuando ya se construyó: sin `agente/` no hay build que comparar y el script
        # reportaría como faltante cada archivo que todavía no tiene por qué existir.
        cmd += ["--proyecto", str(c.raiz)]
    codigo, salida = _correr(cmd, cwd=c.raiz)
    resumen = salida.strip() or "(sin salida)"

    if codigo == 0:
        r.decir(resumen.splitlines()[0] if resumen else "")
        return
    if codigo == 1:
        r.error("manifiesto/kit_viejo",
                "la plantilla cambió y el manifiesto quedó viejo. Lo rompimos nosotros: "
                f"corré `python3 scripts/hash_plantillas.py --escribir`. {_recorte(resumen)}",
                "plantillas/MANIFIESTO.json", 0, "kit")
        return
    if codigo == 2:
        # El aviso al resto de la corrida: el chequeo `firmas` no ejecuta un archivo de `agente/`
        # después de esto. Probamos que ese archivo no es el que enviamos; correrlo igual sería
        # ejecutar código del que ya sabemos que no sabemos nada.
        c.build_derivado = True
        r.error("manifiesto/build_derivado",
                "un archivo generado se apartó de su plantilla. No es un defecto tuyo ni del "
                f"kit: se arregla copiando la plantilla otra vez. {_recorte(resumen)}",
                "agente", 0, "build")
        return
    r.error("manifiesto/no_corrio", f"hash_plantillas.py salió con {codigo}: {_recorte(resumen)}",
            "scripts/hash_plantillas.py", 0, "entorno")


def _recorte(texto: str, largo: int = 400) -> str:
    plano = " · ".join(l.strip() for l in texto.splitlines() if l.strip())
    return plano[:largo]


# ─────────────────────────────────────────────────────────────────────────────
# 03 · railway-arranque
# ─────────────────────────────────────────────────────────────────────────────


def chequeo_railway_arranque(c: Contexto, r: Reporte) -> None:
    """La clave que `railway.json` NO tiene que traer, y que ningún hash puede pedir.

    Un hash ve lo que cambió; una ausencia no. Si alguien agrega `startCommand`, el chequeo
    `manifiesto` dice "no coincide" y no nombra la causa, y si el `railway.json` del build se
    escribió sin copiar la plantilla, el manifiesto ni lo mira. Por eso esto se busca aparte: lo
    dice `plantillas/README.md`, y hasta hoy no lo hacía nadie.

    `startCommand` pisa el `CMD` del Dockerfile, que es
    `sh -c "exec uvicorn ... --port ${PORT:-8000}"`. Railway inyecta `PORT` y el valor cambia
    entre despliegues: con el puerto escrito a mano la app escucha en otro lado, el healthcheck
    no contesta nunca y lo único que se lee es `service unavailable`.
    """
    archivos = [p for p in (c.raiz / "plantillas/infra/railway.json", c.raiz / "railway.json")
                if p.is_file()]
    if not archivos:
        r.saltear("no hay ningún railway.json: ni la plantilla ni el del build")
        return

    for archivo in archivos:
        rel = c.rel(archivo)
        texto = _texto(archivo)
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError as e:
            r.error("railway/json_invalido",
                    f"no es JSON válido: {e}. Railway no lee nada de acá y despliega con los "
                    f"valores por defecto, sin healthcheck y sin decir una palabra",
                    rel, e.lineno, "kit")
            continue
        for donde in _claves_anidadas(datos, CLAVE_DE_ARRANQUE):
            r.error("railway/start_command",
                    f"trae `{CLAVE_DE_ARRANQUE}` en `{donde}` y eso pisa el `CMD` del Dockerfile. "
                    f"El CMD resuelve `${{PORT:-8000}}` en el shell al arrancar porque Railway "
                    f"inyecta el puerto y cambia entre despliegues; con el puerto escrito a mano "
                    f"la app escucha en otro lado, el healthcheck no contesta nunca y lo único "
                    f"que vas a leer es `service unavailable`. Sacá la clave",
                    rel, _linea_de(texto, CLAVE_DE_ARRANQUE), "kit")
    r.decir(f"{len(archivos)} railway.json sin `{CLAVE_DE_ARRANQUE}`")


def _claves_anidadas(nodo, clave: str, ruta: str = ""):
    """Dónde aparece una clave, a cualquier profundidad.

    Railway la acepta en `deploy` y también adentro de cada entorno de `environments`, así que
    mirar el primer nivel no alcanza: la misma clave, un nivel más abajo, hace exactamente lo
    mismo.
    """
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            sitio = f"{ruta}.{k}" if ruta else str(k)
            if k == clave:
                yield sitio
            yield from _claves_anidadas(v, clave, sitio)
    elif isinstance(nodo, list):
        for i, v in enumerate(nodo):
            yield from _claves_anidadas(v, clave, f"{ruta}[{i}]")


def _linea_de(texto: str, aguja: str) -> int:
    i = texto.find(f'"{aguja}"')
    return texto[:i].count("\n") + 1 if i >= 0 else 0


# ─────────────────────────────────────────────────────────────────────────────
# 04 · claudemd-tam
# ─────────────────────────────────────────────────────────────────────────────


def chequeo_claudemd_tam(c: Contexto, r: Reporte) -> None:
    archivo = c.raiz / "CLAUDE.md"
    if not archivo.is_file():
        r.error("claudemd/ausente", "no hay CLAUDE.md: es lo único que vuelve entero después de "
                "una compactación", "CLAUDE.md")
        return
    tam = archivo.stat().st_size
    if tam > LIMITE_CLAUDEMD:
        r.error("claudemd/grande",
                f"CLAUDE.md mide {tam} bytes y el techo es {LIMITE_CLAUDEMD}: se paga en cada "
                f"turno, aunque nadie lo use. Sobran {tam - LIMITE_CLAUDEMD} bytes",
                "CLAUDE.md", 0, "kit")
        return
    r.decir(f"{tam} bytes de {LIMITE_CLAUDEMD}")


# ─────────────────────────────────────────────────────────────────────────────
# 05 · pines
# ─────────────────────────────────────────────────────────────────────────────


def chequeo_pines(c: Contexto, r: Reporte) -> None:
    """Los pines de requirements.txt, más los dos números fijados que no viven ahí.

    `MODELO` está escrito en PINES.md y otra vez en `env.example`; la imagen base, en PINES.md y
    otra vez en el `FROM` del Dockerfile. Cada uno de esos pares es exactamente el defecto que
    PINES.md existe para prevenir —un número repetido en dos archivos algún día dice dos cosas
    distintas— y hasta hoy los 28 de requirements.txt eran los únicos comparados.
    """
    pines = c.pines()
    declarados: dict[str, str] = {}
    if pines:
        declarados = {_normalizar(p["nombre"]): p["pin"] for p in pines["pines"]}

    archivos = c.requirements()
    cuantas = 0
    for archivo in archivos:
        rel = c.rel(archivo)
        for n, cruda in enumerate(_texto(archivo).splitlines(), 1):
            linea = cruda.strip()
            if not linea or linea.startswith("#"):
                continue
            if not LINEA_FIJADA.match(linea):
                r.error("pines/sin_fijar", _por_que_no_es_pin(linea), rel, n, "kit")
                continue
            cuantas += 1
            if not declarados:
                continue
            nombre = re.split(r"\[|==", linea, maxsplit=1)[0]
            version = linea.split("==", 1)[1].split("#")[0].strip()
            clave = _normalizar(nombre)
            if clave not in declarados:
                r.error("pines/fuera_de_pines",
                        f"`{nombre}` está fijado acá y no aparece en PINES.md. Toda versión sale "
                        f"de ahí y de ningún otro lado", rel, n, "kit")
            elif declarados[clave] != version:
                r.error("pines/desacuerdo",
                        f"`{nombre}` dice {version} acá y {declarados[clave]} en PINES.md. "
                        f"Un número repetido en dos archivos algún día dice dos cosas distintas",
                        rel, n, "kit")
    modelo = _modelo_repetido(c, r, pines)
    imagen = _imagen_repetida(c, r, pines)
    hay_pines_md = (c.raiz / "PINES.md").is_file()
    if not (archivos or modelo or imagen or hay_pines_md):
        r.saltear("no hay PINES.md, ni requirements.txt, ni env.example, ni Dockerfile: nada que "
                  "comparar")
        return

    if not pines:
        # Error y no aviso: un aviso no mueve el veredicto, así que romper `verificar_pines.py`
        # apagaba en silencio la comparación de los 28 pines y la del MODELO, y el reporte salía
        # igual de verde que uno que sí comparó. La forma de cada línea se verificó igual, pero
        # eso no es lo que este chequeo promete.
        r.error("pines/sin_pines_md",
                f"no pude leer PINES.md: {c.pines_problema()}. Verifiqué la forma de cada línea, "
                f"pero no que los números, el MODELO ni la imagen base coincidan con la fuente: "
                f"eso es la mitad del chequeo, y sin este hallazgo el reporte no la distingue de "
                f"una corrida que sí comparó", "PINES.md", 0, "kit")
    fecha = (pines or {}).get("verificado_el")
    r.decir(f"{cuantas} pines en {len(archivos)} archivo(s)"
            + (f", MODELO={modelo}" if modelo else "")
            + (f", imagen {imagen}" if imagen else "")
            + (f", verificado el {fecha}" if fecha else ""))


def _modelo_repetido(c: Contexto, r: Reporte, pines: dict | None) -> str:
    """`MODELO=` de `env.example` contra el de PINES.md.

    El comentario de `env.example` decía "si lo cambiás acá, cambialo también ahí". Eso es una
    instrucción para un humano atento, y un humano atento no es una compuerta: el kit es prompts,
    y un modelo distinto los sigue distinto sin tirar un solo error.
    """
    ejemplo = c.raiz / "env.example"
    declarado = (pines or {}).get("modelo")
    if not ejemplo.is_file() or not declarado:
        return ""
    for n, cruda in enumerate(_texto(ejemplo).splitlines(), 1):
        m = MODELO_EN_ENV.match(cruda)
        if not m:
            continue
        valor = m.group(1)
        if valor != declarado:
            r.error("pines/modelo_desacuerdo",
                    f"`MODELO={valor}` en env.example y `MODELO={declarado}` en PINES.md. El "
                    f"modelo sale de PINES.md y de ningún otro lado, y un cambio de modelo vuelve "
                    f"a correr el bucle de auditoría", "env.example", n, "kit")
            return ""
        return valor
    return ""


def _imagen_repetida(c: Contexto, r: Reporte, pines: dict | None) -> str:
    """El `FROM` del Dockerfile contra la imagen que PINES.md fija.

    Es el mismo par repetido que `MODELO`, con la misma consecuencia: tu laptop corre una versión
    de Python y el contenedor otra, que es donde vive el "anda en mi máquina".
    """
    dockerfiles = [p for p in (c.raiz / "plantillas/infra/Dockerfile", c.raiz / "Dockerfile")
                   if p.is_file()]
    if not dockerfiles:
        return ""
    declaradas = list((pines or {}).get("imagenes") or ())
    if not declaradas:
        r.aviso("pines/imagen_sin_fuente",
                "PINES.md no nombra ninguna imagen `python:...`, así que el `FROM` del Dockerfile "
                "no tiene contra qué compararse", "PINES.md", 0, "kit")
        return ""
    if len(declaradas) > 1:
        r.error("pines/imagen_ambigua",
                f"PINES.md nombra {declaradas} y no se sabe cuál es la fijada. Va una sola: con "
                f"dos, el Dockerfile puede traer cualquiera y las dos parecen correctas",
                "PINES.md", 0, "kit")
        return ""

    fijada = declaradas[0]
    for archivo in dockerfiles:
        rel = c.rel(archivo)
        texto = _texto(archivo)
        for m in FROM_DOCKERFILE.finditer(texto):
            imagen = m.group(1)
            if not imagen.startswith("python"):
                continue  # una etapa intermedia con otra base no es la imagen del runtime
            if imagen != fijada:
                r.error("pines/imagen_desacuerdo",
                        f"`FROM {imagen}` acá y PINES.md fija `{fijada}`. La imagen se fija por lo "
                        f"mismo que los 28 pines: sin ruedas para esa versión algo se compila "
                        f"desde fuente, y lo que anda en tu máquina no es lo que corre en el "
                        f"contenedor", rel, texto[:m.start()].count("\n") + 1, "kit")
    return fijada


def _por_que_no_es_pin(linea: str) -> str:
    if ">=" in linea or ">" in linea:
        return (f"`{linea}` usa un piso, no un pin: dice «esta o cualquiera que venga después», "
                f"y las que vienen después no las probó nadie")
    if "~=" in linea:
        return f"`{linea}` usa `~=`, que deja flotar el último número. Se fija con `==`"
    if linea.startswith("-"):
        return f"`{linea}` es una opción de pip: acá va una lista plana de `nombre==version`"
    return f"`{linea}` no fija versión: sin `==` se instala lo que haya salido ayer"


# ─────────────────────────────────────────────────────────────────────────────
# 06 · deps-imports
# ─────────────────────────────────────────────────────────────────────────────


def chequeo_deps_imports(c: Contexto, r: Reporte) -> None:
    if not c.hay_agente:
        r.saltear("no existe agente/: esto corre después de /armar-cerrador")
        return
    fijadas = _distribuciones_fijadas(c)
    if not fijadas:
        r.saltear("no hay requirements.txt contra el que comparar")
        return

    locales = _paquetes_locales(c)
    estandar = set(sys.stdlib_module_names)
    cuantas = 0
    for modulo in c.modulos():
        arbol, error = _arbol(modulo)
        rel = c.rel(modulo)
        if arbol is None:
            r.error("deps/no_parsea", f"no puedo leer el árbol: {error}", rel, 0, "build")
            continue
        for raiz, linea in _raices_importadas(arbol):
            if raiz in estandar or raiz in locales:
                continue
            cuantas += 1
            distribucion = _normalizar(IMPORT_A_DISTRIBUCION.get(raiz, raiz))
            if distribucion not in fijadas:
                r.error("deps/import_sin_pin",
                        f"importa `{raiz}` y ninguna distribución fijada lo provee. Fijalo en "
                        f"PINES.md y en requirements.txt, o sacá el import: en la máquina de "
                        f"quien clona esto es un ModuleNotFoundError al arrancar",
                        rel, linea, "build")
    r.decir(f"{cuantas} imports de terceros, todos fijados")


def _raices_importadas(arbol: ast.Module):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield alias.name.split(".")[0], nodo.lineno
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:  # relativo: es del propio paquete
                continue
            if nodo.module:
                yield nodo.module.split(".")[0], nodo.lineno


def _distribuciones_fijadas(c: Contexto) -> set[str]:
    fijadas: set[str] = set()
    for archivo in c.requirements():
        for linea in _texto(archivo).splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "==" not in linea:
                continue
            fijadas.add(_normalizar(re.split(r"\[|==", linea, maxsplit=1)[0]))
    return fijadas


def _paquetes_locales(c: Contexto) -> set[str]:
    locales = {"agente", "panel", "pruebas", "tests", "config", "scripts"}
    for hijo in c.raiz.iterdir():
        if hijo.name.startswith("."):
            continue
        locales.add(hijo.stem if hijo.suffix == ".py" else hijo.name)
    return locales


# ─────────────────────────────────────────────────────────────────────────────
# 07 · deps-drivers
# ─────────────────────────────────────────────────────────────────────────────


def chequeo_deps_drivers(c: Contexto, r: Reporte) -> None:
    """El chequeo que atrapa `asyncpg`.

    `asyncpg` no se importa nunca por nombre: vive adentro de `postgresql+asyncpg://`. Por eso
    el análisis de imports del chequeo anterior no lo ve, y por eso el kit de referencia se
    publicó sin él: con SQLite andaba perfecto, porque con SQLite esa línea nunca corre.

    Se mira el proyecto entero, de dos maneras, porque la cadena se escribe en dos lugares
    distintos y ninguna de las dos formas sirve para el otro:

    · cada `.py` por su árbol, con las cinco formas de armar la cadena pegadas antes de buscar
      —ver `_pegado`— y sin los docstrings. Es lo que agarra al driver escrito a mano;
    · todo lo demás como texto plano. Es lo que agarra al driver que viene de configuración:
      `DATABASE_URL` no vive en un `.py`, vive en `alembic.ini`, en `docker-compose.yml`, en
      `railway.json`. PINES.md promete «las cadenas del proyecto» y esas son cadenas del
      proyecto. Mirar solo `agente/**/*.py` dejaba los tres afuera.

    El barrido acepta algún falso positivo en prosa. Para un chequeo cuya falla es un
    `ModuleNotFoundError` en el primer despliegue el intercambio es ése, y se paga barato: en un
    `.md` el hallazgo baja a aviso, porque un párrafo no abre una conexión.
    """
    fijadas = _distribuciones_fijadas(c)
    if not fijadas:
        r.saltear("no hay requirements.txt contra el que comparar")
        return

    encontrados: set[str] = set()
    vistos: set[tuple[str, int]] = set()

    def revisar(driver: str, rel: str, linea: int, nivel: str, cadena: str = "") -> None:
        encontrados.add(driver)
        if _normalizar(driver) in fijadas or (rel, linea) in vistos:
            return
        vistos.add((rel, linea))
        detalle = f"la cadena `{cadena[:60]}` pide" if cadena else "pide"
        decir = r.error if nivel == "error" else r.aviso
        decir("drivers/sin_pin",
              f"{detalle} el driver `{driver}` y no está fijado en requirements.txt. No aparece "
              f"en ningún import, así que nada más lo va a ver: el despliegue muere con "
              f"ModuleNotFoundError la primera vez que esa línea corra",
              rel, linea, "build")

    def por_arbol(arbol: ast.Module, rel: str) -> None:
        """Un `.py`: las cadenas ya pegadas y sin los docstrings.

        Un párrafo que cuenta cómo se arma la URL no arma ninguna URL, y este kit escribe más
        prosa que código. El árbol es lo único que distingue las dos cosas.

        Dos vueltas y no una. `"postgresql+%s://" % "drivertres"` sale armada, pero el molde
        —`postgresql+%s://`— es una constante suelta del mismo renglón y sale también: sin
        separar las vueltas, la misma línea se reportaba dos veces, una como error con el nombre
        adentro y otra como aviso diciendo que no se lee cuál es. El error primero, y el aviso
        solo en las líneas donde no se pudo resolver nada.
        """
        armadas = set(_cadenas(arbol, sin_prosa=True))
        crudas = set(_cadenas(arbol, sin_prosa=True, literales=False))
        resueltas = {linea for linea, _ in armadas - crudas}
        for linea, cadena in sorted(armadas):
            for driver in DRIVER_EN_URL.findall(cadena):
                revisar(driver, rel, linea, "error", cadena)
        for linea, cadena in sorted(armadas):
            if linea in resueltas:
                # El nombre estaba escrito en el mismo renglón: o ya salió como error, o el
                # driver está fijado. En los dos casos el aviso sobra.
                continue
            if DRIVER_INTERPOLADO.search(cadena) and (rel, linea) not in vistos:
                vistos.add((rel, linea))
                r.aviso("drivers/interpolado",
                        f"`{cadena[:60]}` arma el driver desde afuera, así que acá no se lee cuál "
                        f"es. Verificá que el que llegue por configuración esté fijado: el que no "
                        f"esté no lo ve ningún import, y revienta en el despliegue",
                        rel, linea, "build")

    def por_texto(contenido: str, rel: str, nivel: str) -> None:
        """Todo lo que no es Python, línea por línea.

        No se transcribe la línea encontrada a propósito: una cadena de conexión trae usuario y
        contraseña, y esto se escribe en EVIDENCIA/gates.json. Con el archivo, la línea y el
        nombre del driver alcanza para arreglarlo.
        """
        for n, linea in enumerate(contenido.splitlines(), 1):
            for driver in DRIVER_EN_URL.findall(linea):
                revisar(driver, rel, n, nivel)

    for archivo in _archivos_para_barrido(c):
        rel = c.rel(archivo)
        # El guardia va por archivo y no por chequeo. Un solo `.py` con una expresión anidada más
        # allá de lo que aguanta el intérprete se llevaba puesto el barrido entero: el
        # `postgresql+driverfantasma://` del archivo siguiente desaparecía, y el mensaje culpaba a
        # `scripts/auditar.py` sin nombrar el archivo que lo causó. Así se pierde un archivo,
        # queda dicho cuál, y los demás se barren igual.
        try:
            if archivo.suffix == ".py":
                arbol, _ = _arbol(archivo)
                if arbol is not None:
                    por_arbol(arbol, rel)
                    continue
                # Un `.py` que no parsea se cae al barrido de texto. Es peor —vuelve a leer los
                # docstrings como si fueran código— y es lo único que queda: `deps-imports` ya
                # reporta aparte que ese archivo no tiene árbol.
            contenido = _texto(archivo)
            if "\x00" in contenido:  # binario: lo que salga de acá no es una cadena de conexión
                continue
            por_texto(contenido, rel, "aviso" if archivo.suffix.lower() in (".md", ".rst", ".txt")
                      else "error")
        except RecursionError:
            r.error("drivers/muy_anidado",
                    "este archivo anida expresiones más de lo que aguanta el intérprete y no "
                    "pude barrerlo: si adentro hay una cadena de conexión con el driver puesto, "
                    "acá no se ve. Los demás archivos se barrieron igual",
                    rel, 0, "build")
    r.decir(f"{len(encontrados)} driver(s) en cadenas de conexión: {', '.join(sorted(encontrados)) or 'ninguno'}")


# Los archivos donde `+driver://` es la regla escrita y no una cadena que alguien va a abrir. Sin
# esta lista el chequeo se reporta a sí mismo: PINES.md documenta el patrón y este archivo
# explica el chequeo en su propio docstring.
DOCUMENTAN_EL_PATRON = frozenset({"PINES.md", "scripts/auditar.py"})

# Lo que el build deja afuera del commit a propósito —ver .gitignore— y sí se despliega. El
# barrido tiene que mirarlo igual: la `DATABASE_URL` con el driver adentro vive justo acá.
SALIDAS_DEL_BUILD = ("agente", "panel", "alembic", "requirements.txt", "Dockerfile",
                     "docker-compose.yml", "railway.json", "Procfile", "alembic.ini")


def _archivos_para_barrido(c: Contexto) -> list[Path]:
    """Lo que va al próximo commit, más lo que el build deja fuera de él y igual se despliega.

    `.env` no entra por ninguna de las dos vías —git lo ignora y no está en la lista—, y así
    tiene que seguir: este archivo no lee secretos.
    """
    yo = Path(__file__).resolve()
    candidatos = list(c.archivos_del_repo())
    for nombre in SALIDAS_DEL_BUILD:
        ruta = c.raiz / nombre
        if ruta.is_dir():
            candidatos += list(ruta.rglob("*"))
        elif ruta.is_file():
            candidatos.append(ruta)

    barrido: list[Path] = []
    for archivo in dict.fromkeys(candidatos):
        rel = c.rel(archivo)
        if rel in DOCUMENTAN_EL_PATRON or _es_ruido(tuple(rel.split("/"))):
            continue
        try:
            if not archivo.is_file() or archivo.stat().st_size > 2_000_000:
                continue
            if archivo.resolve() == yo:
                continue
        except OSError:
            continue
        barrido.append(archivo)
    return barrido


# ─────────────────────────────────────────────────────────────────────────────
# 08 · secretos
# ─────────────────────────────────────────────────────────────────────────────

# Los patrones se arman por pedazos a propósito. Escritos enteros, este archivo se encontraría a
# sí mismo en cada corrida y el chequeo nacería con un falso positivo permanente.
#
# El webhook entrante de Slack es una credencial y no una dirección: quien tiene esa URL postea en
# ese canal, sin token, sin cabecera y sin nada más. Es además la que más nombra este kit
# —`SLACK_WEBHOOK_URL` es el aviso interno del paso 6—, así que es la que más chance tiene de
# quedar pegada en un archivo mientras alguien prueba. El último tramo pide 16 caracteres o más
# porque ahí Slack pone 24: con menos, el que matchea es el marcador de posición declarado del kit
# —`.../T00000000TEST/B00000000TEST/pruebas-sin-credencial`, que vive en `SUPUESTOS.md`, en
# `blueprint/40-pruebas.md` y en `pruebas/proveedor_falso.py`— y el chequeo nace con tres falsos
# rojos que enseñan a ignorarlo.
PATRONES_DE_SECRETO = (
    ("anthropic", re.compile("sk-" + "ant-" + r"[A-Za-z0-9_\-]{8,}")),
    ("stripe", re.compile("sk" + "_live" + r"_[A-Za-z0-9]{8,}")),
    ("meta", re.compile("EAA" + r"[A-Za-z0-9]{20,}")),
    ("slack", re.compile("xoxb" + r"-[A-Za-z0-9-]{10,}")),
    ("webhook-entrante-de-slack",
     re.compile("hooks." + "slack.com" + r"/services/T[A-Za-z0-9]+/B[A-Za-z0-9]+/[A-Za-z0-9]{16,}")),
    ("webhook", re.compile("whsec" + r"_[A-Za-z0-9]{8,}")),
    ("clave-privada", re.compile("-----" + "BEGIN" + r"[A-Z ]*PRIVATE KEY-----")),
)

VALOR_SECRETOSO = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.+)$")


def chequeo_secretos(c: Contexto, r: Reporte) -> None:
    archivos = c.archivos_del_repo()
    if not archivos:
        r.saltear("git no listó ningún archivo: ¿esto es un repo?")
        return

    yo = Path(__file__).resolve()
    for archivo in archivos:
        if not archivo.is_file():
            continue
        rel = c.rel(archivo)
        try:
            if archivo.stat().st_size > 2_000_000:
                continue
        except OSError:
            continue
        contenido = _texto(archivo)
        for nombre, patron in PATRONES_DE_SECRETO:
            for m in patron.finditer(contenido):
                if archivo.resolve() == yo:
                    continue
                linea = contenido[: m.start()].count("\n") + 1
                r.error("secretos/credencial",
                        f"parece una credencial de {nombre} escrita en el árbol. Ninguna va acá: "
                        f"los valores viven en `.env`, que no se versiona. Rotala igual, que ya "
                        f"estuvo en un archivo", rel, linea, "kit")

    # `.env` tiene que estar ignorado Y sin rastrear. Son dos cosas distintas: un archivo que ya
    # entró a la historia sigue rastreado aunque después lo agregues al .gitignore.
    #
    # `--no-index` pregunta por el patrón y no por el estado del archivo. Sin esa bandera, git
    # contesta «no está ignorado» para cualquier archivo rastreado —porque a lo rastreado el
    # .gitignore no se le aplica—, y los dos chequeos dirían lo mismo por el motivo equivocado.
    codigo, _ = _correr(["git", "check-ignore", "--no-index", "-q", "--", ".env"], cwd=c.raiz)
    if codigo != 0:
        r.error("secretos/env_no_ignorado",
                "`.env` no está ignorado por git: la primera credencial que escribas entra al "
                "próximo commit", ".gitignore", 0, "kit")
    codigo, _ = _correr(["git", "ls-files", "--error-unmatch", "--", ".env"], cwd=c.raiz)
    if codigo == 0:
        r.error("secretos/env_rastreado",
                "`.env` está rastreado por git. Sacalo con `git rm --cached .env` y rotá todo lo "
                "que tenga adentro: lo que entró a la historia se queda ahí", ".env", 0, "kit")

    ejemplo = c.raiz / "env.example"
    if ejemplo.is_file():
        for n, cruda in enumerate(_texto(ejemplo).splitlines(), 1):
            m = VALOR_SECRETOSO.match(cruda.strip())
            if m and NOMBRE_SECRETOSO.search(m.group(1)) and m.group(2).strip():
                r.error("secretos/ejemplo_con_valor",
                        f"`{m.group(1)}` viene con valor en env.example. Acá van los nombres y "
                        f"nada más", "env.example", n, "kit")
    r.decir(f"{len(archivos)} archivos revisados, {len(PATRONES_DE_SECRETO)} patrones")


# ─────────────────────────────────────────────────────────────────────────────
# 09 · gitignore-anclado
# ─────────────────────────────────────────────────────────────────────────────


# El núcleo verbatim: lo que quien clona tiene que recibir sí o sí. Las plantillas salen del
# manifiesto, que las lista una por una; estos directorios no los lista ningún archivo del kit y
# el razonamiento es el mismo. Van como directorio a propósito: un patrón que se lleva `scripts/`
# se lleva la compuerta entera, y mirar solo las seis plantillas seguiría diciendo "todo bien".
#
# Acá NO va nada que el .gitignore ignore a propósito —`agente/`, `knowledge/*`, `EVIDENCIA/`,
# el `requirements.txt` de la raíz—: eso es salida de la construcción, no núcleo.
NUCLEO_VERSIONADO = (
    "scripts/",
    ".claude/skills/",
    "blueprint/",
    "agents/",
    "contratos/",
    "pruebas/fixtures/",
)


def chequeo_gitignore_anclado(c: Contexto, r: Reporte) -> None:
    """Un patrón sin anclar se lleva puesto el núcleo verbatim y nadie se entera.

    `seguridad/` a secas no matchea *esa* carpeta: matchea cualquiera con ese nombre, a
    cualquier profundidad, incluida `plantillas/seguridad/`. El kit se publicaría sin
    `firmas.py` y el defecto aparecería recién cuando alguien clone.

    Vale igual para todo lo demás que se publica y no está en el manifiesto: un `scripts/` sin
    anclar se lleva la compuerta, un `.claude/skills/` sin anclar se lleva los diez comandos, y
    en los dos casos el kit clonado arranca sin decir nada.

    Se preguntan los **archivos**, uno por uno, y no solo las carpetas. Un patrón de directorio
    lo agarra cualquiera de las dos formas, pero un patrón que se lleva el contenido no toca
    ninguna ruta de carpeta y pasaba entero: con `SKILL.md`, `*.raw` y `auditar.py` en el
    `.gitignore`, git ignoraba las diez skills, los dos fixtures de firma y esta compuerta, y el
    chequeo decía «12 rutas del núcleo versionadas».

    **Son dos preguntas distintas y hasta hoy se hacía una sola.** `git check-ignore --no-index`
    pregunta si el `.gitignore` se lleva la ruta; no pregunta si la ruta está rastreada. Un
    archivo que ningún patrón ignora y que nadie agregó nunca no aparece en esa salida, así que
    el chequeo imprimía «57 rutas del núcleo versionadas» con 3 de esas 57 adentro de HEAD y 54
    afuera. La frase del hallazgo —«el que clona recibe el kit sin ella y no hay error que lo
    diga»— describía exactamente lo que estaba pasando en este árbol, y el chequeo decía ok.

    La segunda mitad es `git ls-files`, y las dos se reportan por separado.

    **Sin rastrear puede ser error, y hasta hoy no podía.** Con 49 de 52 rutas del núcleo fuera del
    índice este chequeo decía `[ok]`, el veredicto salía `PASS` y `.claude/skills/publicar/SKILL.md`
    despliega «con `pass` y con nada más»: o sea que la compuerta autorizaba publicar un kit que se
    clona con tres archivos adentro. Se sube a error en dos casos, y el primero es el que cierra el
    agujero de verdad:

    - **con `--publicando`**, que es la corrida que autoriza el `git push`. Ahí el árbol ya no está
      «en medio de una construcción»: es el estado que va a recibir el que clone, y una ruta del
      núcleo fuera del índice es exactamente el kit incompleto. `/publicar` tiene que invocar la
      compuerta con esa bandera; mientras no lo haga, la corrida a secas sigue diciendo el número.
    - **con `agente/` en el árbol**, porque ahí la excusa se venció: la construcción ya corrió, y el
      núcleo lo trajo un `git clone` que lo deja rastreado. Sin rastrear en ese árbol quiere decir
      que alguien copió el kit a mano o borró del índice, y el próximo clon no recibe eso.

    Se eligió la bandera además del `agente/` y no en vez de él porque los dos casos son distintos y
    el que duele es el primero: el kit que se publica **no** tiene `agente/` —eso es salida de la
    construcción, y está en `.gitignore`—, así que la regla del `agente/` sola no toca nunca al árbol
    desde el que se publica. Cuál de las dos corrió se lee en el hallazgo.

    Fuera de esos dos casos queda como aviso, con el número exacto y la palabra: en medio de una
    construcción lo normal es que la mitad del núcleo todavía no esté agregada, y un rojo ahí es un
    rojo que se aprende a ignorar.
    """
    candidatas = ["plantillas/infra/Dockerfile"] + list(NUCLEO_VERSIONADO)
    manifiesto = c.raiz / "plantillas/MANIFIESTO.json"
    if manifiesto.is_file():
        try:
            datos = json.loads(_texto(manifiesto))
            candidatas += [str(e["ruta"]) for e in datos.get("plantillas", [])]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    # Las carpetas se preguntan igual, y no es redundante: una carpeta vacía —o todavía sin
    # escribir— no tiene ningún archivo que la represente, y el patrón que se la lleva es el
    # mismo que mañana se lleva lo que alguien ponga adentro.
    candidatas += [c.rel(p) for p in _archivos_del_nucleo(c)]
    candidatas = sorted(set(candidatas))

    # `--no-index` es lo que hace que esto sirva. Sin la bandera, git contesta «no está
    # ignorado» para todo lo que ya está rastreado, así que en cuanto `plantillas/` entra al
    # primer commit el chequeo pasa siempre y deja de mirar el patrón. El daño no es que se
    # borre lo rastreado: es que la próxima plantilla que alguien agregue no la levanta ningún
    # `git add .`, y el kit se publica sin ella sin un solo error.
    ignoradas: list[str] = []
    for tanda in _en_tandas(candidatas, 200):
        codigo, salida = _correr(
            ["git", "check-ignore", "--no-index", "-v", "--"] + tanda, cwd=c.raiz)
        if codigo not in (0, 1):
            r.saltear(f"git check-ignore no corrió: {_recorte(salida, 120)}")
            return
        ignoradas += [l for l in salida.splitlines() if l.strip()]

    for linea in ignoradas:
        # formato: <archivo-del-patron>:<línea>:<patrón>\t<ruta ignorada>
        partes = linea.split("\t")
        origen = partes[0] if partes else linea
        ruta = partes[-1] if len(partes) > 1 else "?"
        r.error("gitignore/nucleo_ignorado",
                f"`{ruta}` está ignorada por el patrón de {origen}. Es parte del núcleo verbatim: "
                f"ignorada, el que clona recibe el kit sin ella y no hay error que lo diga. "
                f"Anclá el patrón con `/` al principio", ".gitignore", 0, "kit")

    # La segunda mitad, que es la que faltaba: rastreo real.
    rastreadas, problema = _rutas_rastreadas(c)
    if problema:
        r.aviso("gitignore/sin_rastreo",
                f"no pude preguntar qué está rastreado: {problema}. Queda mirado el patrón y sin "
                f"mirar el rastreo, que son dos cosas distintas", ".gitignore", 0, "entorno")
        if not ignoradas:
            r.decir(f"{len(candidatas)} rutas del núcleo —archivos y carpetas— sin patrón que las "
                    f"ignore; el rastreo no se pudo verificar")
        return

    # `archivos` y `candidatas` no cuentan lo mismo y por eso las dos cuentas van con su palabra al
    # lado. `candidatas` trae las seis carpetas del núcleo y las rutas del manifiesto además de los
    # archivos, porque el patrón que se lleva una carpeta vacía es el mismo que mañana se lleva lo
    # que alguien ponga adentro; el rastreo, en cambio, sólo se le puede preguntar a un archivo: git
    # no versiona directorios. Mezclarlas dejaba el titular en «58 rutas del núcleo» arriba de un
    # aviso que decía «49 de 52», y 3 + 49 no daba 58: eran dos denominadores con el mismo nombre.
    archivos = [ruta for ruta in candidatas if (c.raiz / ruta).is_file()]
    carpetas = len(candidatas) - len(archivos)
    sin_rastrear = sorted(ruta for ruta in archivos if ruta not in rastreadas)
    if sin_rastrear:
        muestra = ", ".join(sin_rastrear[:6])
        cola = f", y {len(sin_rastrear) - 6} más" if len(sin_rastrear) > 6 else ""
        cabeza = (f"{len(sin_rastrear)} de {len(archivos)} archivos del núcleo verbatim están **sin "
                  f"rastrear**: git no los tiene en el índice, así que hoy no salen en ningún clon. "
                  f"Ningún patrón los ignora —eso ya se miró aparte—, sencillamente nadie los "
                  f"agregó: {muestra}{cola}.")
        if c.publicando:
            r.error("gitignore/nucleo_sin_rastrear",
                    f"{cabeza} Esta corrida es la que autoriza publicar —corriste con "
                    f"`--publicando`—, así que esto es error y no aviso: lo que no está en el "
                    f"índice no viaja en el clon, y el que instale el kit lo recibe sin eso. "
                    f"`git add -A` y volvé a correr", ".gitignore", 0, "kit")
        elif c.hay_agente:
            r.error("gitignore/nucleo_sin_rastrear",
                    f"{cabeza} Con `agente/` en el árbol la construcción ya corrió, y el núcleo lo "
                    f"trae un `git clone` que lo deja rastreado: acá ya no vale «todavía lo estoy "
                    f"escribiendo». O este árbol se copió a mano, o alguien lo sacó del índice; en "
                    f"los dos casos el próximo clon no recibe esos archivos",
                    ".gitignore", 0, "kit")
        else:
            r.aviso("gitignore/nucleo_sin_rastrear",
                    f"{cabeza} Es aviso y no error porque el árbol está en medio de una "
                    f"construcción y `agente/` todavía no existe; antes de publicar, `git add` y "
                    f"corré `scripts/auditar.py --publicando`, donde esto es error",
                    ".gitignore", 0, "kit")
    if not ignoradas:
        r.decir(f"{len(archivos)} archivos del núcleo: {len(archivos) - len(sin_rastrear)} "
                f"rastreados, {len(sin_rastrear)} sin rastrear · {carpetas} carpeta(s) y ruta(s) "
                f"más, 0 ignoradas por patrón")


def _rutas_rastreadas(c: Contexto) -> tuple[set[str], str]:
    """Lo que git tiene en el índice, o el motivo por el que no se pudo preguntar.

    `--cached` a secas, sin `--others`: acá la pregunta es justo la contraria a la de
    `archivos_del_repo()`. Allá interesa lo que el próximo commit se va a llevar —rastreado y sin
    rastrear, porque un secreto sin agregar entra igual—; acá interesa lo que un `git clone`
    entrega hoy, que es solamente lo rastreado.
    """
    codigo, salida = _correr(["git", "ls-files", "-z", "--cached"], cwd=c.raiz, texto=False)
    if codigo != 0:
        return set(), _recorte(salida.strip(), 120) or f"git salió con {codigo}"
    return {n for n in salida.split("\0") if n}, ""


def _archivos_del_nucleo(c: Contexto) -> list[Path]:
    """Cada archivo real de los seis directorios del núcleo.

    Se pregunta por el archivo y no por la carpeta porque los patrones que más duelen son los
    que no nombran ninguna carpeta: `SKILL.md`, `*.raw`, `auditar.py`. Los tres dejan la ruta del
    directorio intacta y se llevan lo de adentro.
    """
    encontrados: list[Path] = []
    for nombre in NUCLEO_VERSIONADO:
        carpeta = c.raiz / nombre
        if not carpeta.is_dir():
            continue
        for ruta in sorted(carpeta.rglob("*")):
            if _es_ruido(ruta.relative_to(c.raiz).parts):
                continue
            try:
                if ruta.is_file():
                    encontrados.append(ruta)
            except OSError:
                continue
    return encontrados


def _en_tandas(elementos: list[str], tamano: int):
    """De a tandas, para que el `git check-ignore` de un árbol grande no pase el largo máximo de
    una línea de comando."""
    for i in range(0, len(elementos), tamano):
        yield elementos[i:i + tamano]


# ─────────────────────────────────────────────────────────────────────────────
# 10 · modelo
# ─────────────────────────────────────────────────────────────────────────────


def chequeo_modelo(c: Contexto, r: Reporte) -> None:
    if not c.hay_agente:
        r.saltear("no existe agente/: esto corre después de /armar-cerrador")
        return
    # La lista de vigentes es una constante de este archivo, así que el chequeo corre aunque
    # PINES.md no se haya podido leer: lo único que se pierde ahí es la comparación contra el
    # modelo declarado, y `pines` ya reporta ese caso como error. Antes la lista salía del mismo
    # subproceso que leía PINES.md, y un archivo ilegible apagaba también esto.
    vigentes = set(MODELOS_VIGENTES)
    declarado = (c.pines() or {}).get("modelo")

    cuantos = 0
    for modulo in c.modulos():
        arbol, _ = _arbol(modulo)
        if arbol is None:
            continue
        rel = c.rel(modulo)
        # Sin docstrings, igual que `_parametros_prohibidos` acá abajo. Los dos miran el mismo
        # párrafo y tienen que decir lo mismo: un docstring que cuenta que el kit de referencia
        # quedó fijado en un modelo viejo está contando eso, no fijando nada.
        for linea, literal in _literales(arbol, sin_prosa=True):
            for hallado in MODELO_LITERAL.findall(literal):
                cuantos += 1
                if hallado not in vigentes:
                    r.error("modelo/retirado",
                            f"`{hallado}` no está entre los modelos vigentes {sorted(vigentes)}. "
                            f"El kit de referencia quedó fijado en uno de la generación anterior "
                            f"y nadie lo notó hasta que alguien leyó el archivo",
                            rel, linea, "build")
                elif declarado and hallado != declarado:
                    r.aviso("modelo/distinto_de_pines",
                            f"`{hallado}` es vigente pero PINES.md dice `{declarado}`. El modelo "
                            f"sale de ahí y de ningún otro lado", rel, linea, "build")
        for linea, nombre, donde in _parametros_prohibidos(arbol):
            r.error("modelo/parametro_400",
                    f"pasa `{nombre}` ({donde}). Los cuatro —budget_tokens, temperature, top_p y "
                    f"top_k— devuelven 400 con este modelo. Ver PINES.md → Modelo",
                    rel, linea, "build")
    r.decir(f"{cuantos} literal(es) de modelo, ninguno retirado")


def _parametros_prohibidos(arbol: ast.Module):
    """Los cuatro, como argumento con nombre o como clave de un diccionario.

    Se mira el árbol y no el texto: el kit escribe código comentado, y el comentario que
    explica por qué estos cuatro no van no es pasarlos.
    """
    saltear = _prosa_suelta(arbol)
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.keyword) and nodo.arg in PROHIBIDOS_DEL_MODELO:
            yield nodo.value.lineno, nodo.arg, "argumento con nombre"
        elif (isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)
                and nodo.value in PROHIBIDOS_DEL_MODELO and id(nodo) not in saltear):
            yield nodo.lineno, nodo.value, "clave de diccionario"


# ─────────────────────────────────────────────────────────────────────────────
# 11 · wire-schema
# ─────────────────────────────────────────────────────────────────────────────

_DRIVER_WIRE = r'''
import importlib.util, json, sys

ruta, golden = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("wire_schema", ruta)
mod = importlib.util.module_from_spec(spec)
# El registro en sys.modules va ANTES de ejecutarlo. `use_attribute_docstrings=True` hace que
# pydantic lea el archivo con inspect para sacar el docstring de cada campo, e inspect busca el
# archivo por sys.modules[cls.__module__]. Sin esta línea revienta con "is a built-in class".
sys.modules["wire_schema"] = mod
spec.loader.exec_module(mod)

texto_golden = open(golden, encoding="utf-8").read()
esquema_golden = json.loads(texto_golden)
vivo = mod.esquema_wire()
rendido = json.dumps(vivo, indent=2, ensure_ascii=False) + "\n"

print(json.dumps({
    "faltas_golden": mod.verificar_wire_schema(esquema_golden),
    "faltas_vivo": mod.verificar_wire_schema(vivo),
    "deriva": rendido != texto_golden,
}, ensure_ascii=False))
'''


def chequeo_wire_schema(c: Contexto, r: Reporte) -> None:
    """El esquema angosto es lo único que sale hacia el modelo, y tiene dos formas de romperse.

    Una: que traiga alguna de las palabras que las salidas estructuradas rechazan, y ahí la API
    devuelve 400. Otra: que el golden quede viejo, y ahí no falla nada: lo que se manda deja de
    ser lo que alguien revisó, y eso no tiene síntoma.
    """
    modulo = c.raiz / "plantillas/contratos/wire_schema.py"
    golden = c.raiz / "plantillas/contratos/wire_schema.golden.json"
    if not modulo.is_file() or not golden.is_file():
        r.saltear("falta plantillas/contratos/wire_schema.py o su golden")
        return

    codigo, salida = 0, ""
    for interprete in c.interpretes:
        codigo, salida = _correr(
            [interprete, "-c", _DRIVER_WIRE, str(modulo), str(golden)], cwd=c.raiz
        )
        if not (codigo != 0 and "ModuleNotFoundError" in salida and "pydantic" in salida):
            break
    if codigo != 0:
        if "ModuleNotFoundError" in salida and "pydantic" in salida:
            r.saltear("falta pydantic: el esquema se renderiza con pydantic, que está fijado en "
                      "PINES.md. Corré esto con el `.venv` del proyecto, o después de "
                      "/armar-cerrador")
            return
        r.error("wire/no_corrio", f"no pude renderizar el esquema: {_recorte(salida)}",
                "plantillas/contratos/wire_schema.py", 0, "entorno")
        return

    try:
        datos = json.loads(salida.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        r.error("wire/salida_ilegible", f"el driver devolvió algo que no es JSON: "
                f"{_recorte(salida)}", "plantillas/contratos/wire_schema.py", 0, "entorno")
        return

    for falta in datos["faltas_golden"]:
        r.error("wire/golden_invalido",
                f"el golden trae algo que la salida estructurada rechaza: {falta}",
                "plantillas/contratos/wire_schema.golden.json", 0, "kit")
    for falta in datos["faltas_vivo"]:
        r.error("wire/esquema_invalido",
                f"el esquema que se le manda al modelo rechaza: {falta}. Devuelve 400",
                "plantillas/contratos/wire_schema.py", 0, "kit")
    if datos["deriva"]:
        r.error("wire/golden_viejo",
                "el esquema se movió y el golden no. Una versión distinta de pydantic renderiza "
                "distinto, y eso tiene que hacer ruido acá y no en producción: corré "
                "`python3 plantillas/contratos/wire_schema.py`",
                "plantillas/contratos/wire_schema.golden.json", 0, "kit")
    if not (datos["faltas_golden"] or datos["faltas_vivo"] or datos["deriva"]):
        r.decir("esquema limpio y golden sin deriva")


# ─────────────────────────────────────────────────────────────────────────────
# 12 · http-unico
# ─────────────────────────────────────────────────────────────────────────────

CLIENTES_HTTP = ("AsyncClient", "Client")


def chequeo_http_unico(c: Contexto, r: Reporte) -> None:
    """Un solo cliente HTTP, con timeout explícito. Sin timeout, httpx espera para siempre: el
    webhook de Zernio pide 2xx en menos de 5 segundos y reintenta hasta siete veces."""
    if not c.hay_agente:
        r.saltear("no existe agente/: esto corre después de /armar-cerrador")
        return

    permitido = (c.agente / "http.py").resolve()
    cuantos = 0
    for modulo in c.modulos():
        arbol, _ = _arbol(modulo)
        if arbol is None:
            continue
        rel = c.rel(modulo)
        desde_httpx = _nombres_importados_de(arbol, "httpx")
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            if not _es_cliente_httpx(nodo.func, desde_httpx):
                continue
            cuantos += 1
            if modulo.resolve() != permitido:
                r.error("http/cliente_suelto",
                        f"`{_fuente(nodo.func)}(` fuera de agente/http.py. Un cliente por módulo "
                        f"son N configuraciones de timeout, N pools y N lugares donde arreglar "
                        f"lo mismo", rel, nodo.lineno, "build")
                continue
            if not any(k.arg == "timeout" for k in nodo.keywords):
                r.error("http/sin_timeout",
                        "el cliente de agente/http.py se construye sin `timeout=`. Sin timeout "
                        "httpx espera para siempre, y el webhook tiene 5 segundos",
                        rel, nodo.lineno, "build")
    if cuantos == 0:
        r.decir("todavía no hay ningún cliente httpx")
    else:
        r.decir(f"{cuantos} construcción(es), todas en agente/http.py")


def _nombres_importados_de(arbol: ast.Module, modulo: str) -> set[str]:
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module == modulo and not nodo.level:
            for alias in nodo.names:
                nombres.add(alias.asname or alias.name)
    return nombres


def _es_cliente_httpx(func: ast.AST, desde_httpx: set[str]) -> bool:
    if isinstance(func, ast.Attribute) and func.attr in CLIENTES_HTTP:
        return _raiz_del_nombre(func) == "httpx"
    if isinstance(func, ast.Name) and func.id in CLIENTES_HTTP:
        return func.id in desde_httpx
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 13 · enviar-unico
# ─────────────────────────────────────────────────────────────────────────────

# El agujero por el que se caían todas las rondas anteriores: `EXIMIDOS_DE_ENVIAR`,
# `METODOS_QUE_ESCRIBEN` y la resolución del nombre del cliente. Los tres salieron, y con ellos la
# lista de excepciones. Por qué está en el docstring de `chequeo_enviar_unico`, y se resume en una
# línea: el invariante 2 no habla de verbos ni de archivos, habla de **a dónde va**.
#
# Cuántas veces se vuelve a resolver la tabla entera antes de darla por firme. Una constante se
# arma con otra y la otra puede venir importada, así que cada pasada resuelve un eslabón más:
# `BASE_META` en `enviar.py` → `URL_MENSAJES` ahí mismo → el nombre importado en el paso → el uso.
# Son cuatro y no un `while`, porque dos constantes definidas una en función de la otra colgarían
# la compuerta, y una compuerta que cuelga es peor que cualquier hallazgo.
PASADAS_DE_CONSTANTES = 4

# Lo que se pone donde el valor no está escrito en ningún archivo del árbol: el id del teléfono que
# sale de una variable de entorno, el `conversacion_id` que llega en la petición. La URL igual queda
# reconocible —`https://graph.facebook.com/v21.0/{}/messages`— porque lo que la identifica es el
# host y el camino, no el pedazo que cambia en cada envío.
HUECO = "{}"


def _punteado(nodo: ast.AST) -> str:
    """`agente.enviar.URL_MENSAJES` como texto, o cadena vacía si hay algo que no es un nombre."""
    partes: list[str] = []
    while isinstance(nodo, ast.Attribute):
        partes.append(nodo.attr)
        nodo = nodo.value
    if not isinstance(nodo, ast.Name):
        return ""
    partes.append(nodo.id)
    return ".".join(reversed(partes))


def _resolver_url(nodo: ast.AST, entorno: dict[str, str], profundidad: int = 0) -> str:
    """La cadena que denota esta expresión, con `{}` donde el valor no se lee en el árbol.

    Es `_pegado` con una diferencia que es todo el chequeo: acá un nombre **se resuelve** contra la
    tabla de constantes del paquete, y lo que no se puede resolver no anula la cadena entera, queda
    como hueco. Las cuatro formas que hasta hoy eran invisibles son todas la misma:

        # agente/enviar.py       URL_MENSAJES = f"{BASE_META}/{ajustes.whatsapp_phone_number_id}/messages"
        # agente/pasos/paso_3.py await deps.http.post(URL_MENSAJES, json=cuerpo)

    Mirando literales no hay nada que ver en el segundo archivo: la URL no está escrita ahí. Con la
    tabla, `URL_MENSAJES` resuelve a `https://graph.facebook.com/v21.0/{}/messages` y el destino
    queda a la vista, que es lo único que el invariante 2 pregunta.

    No se ejecuta nada y no se importa nada: se lee el árbol sintáctico y se pegan cadenas.
    """
    if profundidad > TOPE_PEGADO:
        return HUECO
    hondo = profundidad + 1
    if isinstance(nodo, ast.Constant):
        return nodo.value if isinstance(nodo.value, str) else HUECO
    if isinstance(nodo, ast.Name):
        return entorno.get(nodo.id, HUECO)
    if isinstance(nodo, ast.Attribute):
        # `enviar.URL_MENSAJES` y `agente.enviar.URL_MENSAJES`, que es la misma constante con el
        # módulo adelante. `ajustes.whatsapp_phone_number_id` no está en la tabla: queda hueco.
        punteado = _punteado(nodo)
        if punteado in entorno:
            return entorno[punteado]
        corto = punteado.split(".")[-2:]
        return entorno.get(".".join(corto), HUECO) if len(corto) == 2 else HUECO
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        return (_resolver_url(nodo.left, entorno, hondo)
                + _resolver_url(nodo.right, entorno, hondo))
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Mod):
        # `"%s/%s/messages" % (base, id)`: el molde ya trae el camino, que es lo que se mira.
        return _resolver_url(nodo.left, entorno, hondo)
    if isinstance(nodo, ast.JoinedStr):
        partes = []
        for parte in nodo.values:
            adentro = parte.value if isinstance(parte, ast.FormattedValue) else parte
            partes.append(_resolver_url(adentro, entorno, hondo))
        return "".join(partes)
    if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
        if nodo.func.attr == "format":
            return _resolver_url(nodo.func.value, entorno, hondo)
        if (nodo.func.attr == "join" and len(nodo.args) == 1
                and isinstance(nodo.args[0], (ast.List, ast.Tuple))):
            separador = _resolver_url(nodo.func.value, entorno, hondo)
            return separador.join(
                _resolver_url(e, entorno, hondo) for e in nodo.args[0].elts)
    return HUECO


def _asignaciones_de_modulo(arbol: ast.Module) -> dict[str, ast.AST]:
    """Nombre → expresión, sólo para lo que se asigna a nivel de módulo.

    Adentro de una función no se mira: ahí el nombre vive un rato y no es una constante que otro
    archivo pueda importar. Lo que sí se mira ahí es el uso, y de eso se ocupa el bucle del chequeo.
    """
    tabla: dict[str, ast.AST] = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign):
            for destino in nodo.targets:
                if isinstance(destino, ast.Name):
                    tabla[destino.id] = nodo.value
        elif (isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name)
                and nodo.value is not None):
            tabla[nodo.target.id] = nodo.value
    return tabla


def _modulo_importado(rel: str, nodo: ast.ImportFrom, indice: set[str]) -> str:
    """A qué archivo del árbol apunta un `from … import …`, o cadena vacía.

    Las relativas se resuelven contra la carpeta del que importa, que es lo que las hace no
    ambiguas: `from .base import X` adentro de `agente/proveedores/` es `agente/proveedores/base.py`
    y no `agente/base.py`, y las dos existen en este kit.
    """
    partes = [p for p in (nodo.module or "").split(".") if p]
    if nodo.level:
        candidato = "/".join(rel.split("/")[:-nodo.level] + partes) + ".py"
        return candidato if candidato in indice else ""
    for i in range(len(partes)):
        sufijo = "/".join(partes[i:]) + ".py"
        for otro in sorted(indice):
            if otro == sufijo or otro.endswith("/" + sufijo):
                return otro
    return ""


def _carpeta_del_import(rel: str, nodo: ast.ImportFrom) -> str:
    """La carpeta contra la que se resuelve `from … import <módulo>`.

    `from agente import enviar` y `from . import enviar` no importan un nombre: importan el módulo
    de al lado, y lo que se lee después es `enviar.URL_MENSAJES`.
    """
    partes = [p for p in (nodo.module or "").split(".") if p]
    if nodo.level:
        return "/".join(rel.split("/")[:-nodo.level] + partes)
    return "/".join(partes)


def _tabla_de_constantes(arboles: dict[str, ast.Module]) -> dict[str, dict[str, str]]:
    """Por módulo, cada nombre de nivel de módulo resuelto a la cadena que denota.

    Se hace de a pasadas porque una constante se arma con otra —`RUTA_META` con `BASE_META`— y
    porque la de al lado puede venir importada: sin las dos mitades, la URL de envío no aparece
    entera en ningún archivo, que es exactamente cómo se escondía.
    """
    indice = set(arboles)
    crudas = {rel: _asignaciones_de_modulo(arbol) for rel, arbol in arboles.items()}
    # De dónde sale cada nombre importado: `local → (archivo de origen, nombre de allá)`.
    traidos: dict[str, dict[str, tuple[str, str]]] = {}
    alias: dict[str, dict[str, str]] = {}
    for rel, arbol in arboles.items():
        traidos[rel], alias[rel] = {}, {}
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom):
                origen = _modulo_importado(rel, nodo, indice)
                carpeta = _carpeta_del_import(rel, nodo)
                for a in nodo.names:
                    if origen:
                        traidos[rel][a.asname or a.name] = (origen, a.name)
                    # `from agente import enviar` y `from . import enviar`: lo importado es el
                    # módulo, y después se lee `enviar.URL_MENSAJES`.
                    hermano = f"{carpeta}/{a.name}.py" if carpeta else f"{a.name}.py"
                    if hermano in indice:
                        alias[rel][a.asname or a.name] = hermano
            elif isinstance(nodo, ast.Import):
                for a in nodo.names:
                    candidato = a.name.replace(".", "/") + ".py"
                    for otro in sorted(indice):
                        if otro == candidato or otro.endswith("/" + candidato):
                            alias[rel][a.asname or a.name] = otro
                            alias[rel][a.name] = otro
                            break

    resueltas: dict[str, dict[str, str]] = {rel: {} for rel in arboles}
    for _ in range(PASADAS_DE_CONSTANTES):
        for rel in arboles:
            entorno = dict(resueltas[rel])
            for local, (origen, alla) in traidos[rel].items():
                if alla in resueltas.get(origen, {}):
                    entorno[local] = resueltas[origen][alla]
            for nombre_alias, destino in alias[rel].items():
                for nombre, valor in resueltas.get(destino, {}).items():
                    entorno[f"{nombre_alias}.{nombre}"] = valor
            for nombre, nodo in crudas[rel].items():
                entorno[nombre] = _resolver_url(nodo, entorno)
            resueltas[rel] = entorno
    return resueltas


def _es_mensajeria(url: str) -> str:
    """Qué endpoint de mensajería denota esta URL, o cadena vacía. Ver la tabla de arriba."""
    plana = url.lower()
    if ENDPOINT_META.search(plana):
        return "el endpoint de envío de Meta (`graph.facebook.com/<version>/<id>/messages`)"
    if ENDPOINT_ZERNIO in plana:
        return "el endpoint de envío de Zernio (`/inbox/conversations/…`)"
    return ""


# Los nodos que pueden denotar una URL. El recorrido pasa por todos y el más de afuera de cada línea
# es el que reporta: `f"{BASE}/{id}/messages"` es un JoinedStr y adentro tiene tres nodos más.
NODOS_CON_URL = (ast.Constant, ast.Name, ast.Attribute, ast.BinOp, ast.JoinedStr, ast.Call)


def chequeo_enviar_unico(c: Contexto, r: Reporte) -> None:
    """El invariante de mayor consecuencia del producto, enunciado por **destino**.

    Todo mensaje a un contacto sale por un solo `enviar()` que consulta la ventana de 24 horas,
    corre el chequeo de baneo y se niega a escribirle primero a quien no escribió. Un segundo
    camino de envío se salta las tres cosas, y lo que se pierde no es una respuesta: es el número
    de WhatsApp del negocio. Recuperarlo son semanas.

    **La regla: una URL de mensajería sólo puede aparecer en `agente/enviar.py`.** Los endpoints son
    dos y están escritos arriba, en `ENDPOINT_META` y `ENDPOINT_ZERNIO`. Un `.post` a
    `api.openai.com/v1/audio/transcriptions` no es un mensaje y no se marca; un `.post` a
    `graph.facebook.com/<ver>/<id>/messages` sí lo es, esté escrito donde esté escrito y salga por
    el cliente que salga.

    **Por qué cambió, que es lo único que importa de este docstring.** Antes decía «ningún
    `.post/.put/.patch/.request/.send/.stream` fuera de `agente/enviar.py`», y eso choca con todo lo
    que sale del agente y no es un mensaje: la transcripción de Whisper que manda escribir
    `blueprint/32-multimodal.md` paso 2, la lectura de la imagen, Google Calendar, el CRM, el aviso
    interno a tu equipo. Cada choque se arreglaba agregando un archivo a la lista de eximidos, y
    cada eximido abría un agujero del tamaño del archivo: eximir `agente/http.py` dejó vivir adentro
    un segundo camino de salida completo —las dos URL de mensajería escritas y los dos POST— con la
    compuerta en verde. Enunciada por destino, la regla no necesita lista de eximidos, no necesita
    saber de dónde salió el cliente, y agarra sola las cuatro formas que eran invisibles:

        # agente/pasos/paso_3_responder.py   await deps.http.post(URL_MENSAJES, json=cuerpo)
        # agente/proveedores/meta.py         self.cliente.post(URL_MENSAJES, json=cuerpo)
        # cualquiera                         async def r(cliente, …): await cliente.post(URL_MENSAJES, …)
        # cualquiera                         urlopen(Request(URL_MENSAJES, data=…, method="POST"))

    Las cuatro pasaban enteras porque el chequeo perseguía al cliente —`deps.http` no es un nombre
    importado del módulo del cliente, `self.cliente` tampoco, un parámetro tampoco, y `urllib` no es
    httpx— y porque la URL no está escrita en ese archivo. Con la tabla de constantes del paquete,
    `URL_MENSAJES` resuelve a la URL de Meta y las cuatro se marcan sin preguntar por dónde salen.
    La primera es la más probable: `correr_ciclo(entrada, *, modelo, deps)` es la firma que manda
    `blueprint/40-pruebas.md` paso 2, y `armar_deps()` arma justo ese objeto.

    **Y la regla vieja que sí se queda: la URL partida en dos cadenas.** Nombrar el host de envío
    fuera de `agente/enviar.py` es error aunque no haya ninguna llamada al lado, porque un archivo
    de constantes de envío que no es `enviar.py` se importa desde cualquier lado y el `post` que lo
    usa no se ve en ningún grep:

        BASE_META = "https://graph." + "facebook.com/v21.0"

    Ninguna de las dos mitades nombra el host y la suma sí. Por eso se miran las cadenas **armadas**
    —`_cadenas`— y no los literales crudos, y por eso ahí no se resuelven constantes de otros
    módulos: `agente/medios.py` importa `BASE_META` de `enviar.py` a propósito —lo manda
    `blueprint/32-multimodal.md` paso 1— y sustituirle el valor lo convertiría en un falso rojo
    permanente.

    **Lo que esta regla no ve. Los dos casos, medidos, y no el que se venía nombrando.**

    Lo que se nombraba como punto ciego —el host importado de `enviar.py` y la ruta armada en un
    tercer módulo— **no lo es**: la tabla de constantes cruza los módulos del paquete, así que el
    nombre importado se resuelve y la línea sale marcada.

        # agente/otro.py   from agente.enviar import BASE_META
        #                  "/".join([BASE_META, pid, "messages"])      → SE MARCA

    Los dos que sí son ciegos son otros, y los dos son el mismo caso: el host **no está escrito en
    ninguna cadena del árbol**, así que no hay nada que resolver ni nada que leer.

        # 1 · el host viene del entorno
        HOST = os.getenv("WA_HOST")
        f"https://{HOST}/{VER}/{pid}/messages"                          → no se marca
        # `_resolver_url` devuelve `https://{}/{}/{}/messages`, que no nombra a nadie.

        # 2 · el host viene de un YAML de config/
        cfg = yaml.safe_load(open("config/salida.yaml"))
        cfg["base"] + "/" + pid + cfg["ruta"]                           → no se marca
        # Un `Subscript` no es un nombre de módulo: queda hueco, y la suma también.

    Marcarlos pediría ejecutar el módulo, o leer `config/*.yaml` y `.env` y resolverlos contra el
    árbol. Lo primero está prohibido acá —esta compuerta no importa ni ejecuta nada del build—; lo
    segundo mueve el secreto de dónde va la URL a un archivo que no se versiona, y sigue sin cubrir
    el valor que se resuelve recién en Railway. Es el límite honesto de una regla estática: **el
    invariante 2 se sostiene sobre las URL que están escritas en el código.** Un host que entra por
    variable de entorno o por configuración lo mira una persona en la revisión, y no lo marca nadie.

    Lo que baja la probabilidad de que ese caso exista no es la compuerta: es
    `blueprint/00-contrato.md` § 4, que deja `BASE_META` y `BASE_ZERNIO` adentro de
    `agente/enviar.py` —el chequeo 14 `agente-completo` exige los dos símbolos ahí— y le da un solo
    importador legítimo, `agente/medios.py`, para la bajada del medio. Con las dos bases escritas
    donde van, un módulo que arma un host desde el entorno para mandar un mensaje no está tomando un
    atajo: está escribiendo un segundo camino a mano.
    """
    if not c.hay_agente:
        r.saltear("no existe agente/: esto corre después de /armar-cerrador")
        return

    dueno = (c.agente / "enviar.py").resolve()
    # `panel/` entra además de `agente/`: es código del build, lo escribe el mismo blueprint que
    # `servidor.py`, y un botón «reactivar esta conversación» en la bandeja es un mensaje a un
    # contacto como cualquier otro. El resto de los chequeos mira sólo `agente/` y por eso ahí
    # nadie hubiera visto nada.
    fuentes = list(c.modulos())
    panel = c.raiz / "panel"
    if panel.is_dir():
        fuentes += [p for p in sorted(panel.rglob("*.py")) if "__pycache__" not in p.parts]
    arboles: dict[str, ast.Module] = {}
    for modulo in fuentes:
        arbol, _ = _arbol(modulo)
        if arbol is not None:
            arboles[c.rel(modulo)] = arbol
    constantes = _tabla_de_constantes(arboles)

    for rel, arbol in arboles.items():
        if (c.raiz / rel).resolve() == dueno:
            continue
        entorno = constantes.get(rel, {})
        vistas: set[int] = set()

        # Por destino. El recorrido es ancho primero, así que el nodo más de afuera de cada línea
        # es el que reporta y los pedazos de adentro quedan callados. Los docstrings quedan afuera
        # por lo mismo que en el resto de este archivo: un docstring que explica cuál es la URL de
        # envío no manda nada, y un chequeo que reporta la explicación enseña a ignorar el chequeo.
        docs = _prosa_suelta(arbol)
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, NODOS_CON_URL) or id(nodo) in docs:
                continue
            linea = getattr(nodo, "lineno", 0)
            if linea in vistas:
                continue
            cual = _es_mensajeria(_resolver_url(nodo, entorno))
            if not cual:
                continue
            for adentro in ast.walk(nodo):
                vistas.add(getattr(adentro, "lineno", 0))
            r.error("enviar/salida_de_mensajeria",
                    f"`{_fuente(nodo)}` denota {cual}, y esto no es agente/enviar.py. Da igual el "
                    f"verbo, el cliente y el archivo: lo que decide es a dónde va. Una URL de "
                    f"mensajería acá quiere decir que hay —o que va a haber— un mensaje que no "
                    f"pasa por `enviar()`, o sea que no consulta la ventana de 24 h, no corre el "
                    f"chequeo de baneo y no se niega a escribirle primero a quien no escribió. Lo "
                    f"que se pierde es el número del negocio, y son semanas. La URL va adentro de "
                    f"agente/enviar.py y el envío se pide con `enviar(...)`",
                    rel, linea, "build")

        # Y la URL partida en dos cadenas, que no depende de que haya una llamada.
        for linea, cadena in sorted(set(_cadenas(arbol, sin_prosa=True))):
            if linea in vistas:
                continue
            motivo = ""
            if ENDPOINT_ZERNIO in cadena:
                motivo = f"nombra `{ENDPOINT_ZERNIO}`"
            elif ENDPOINT_META.search(cadena):
                motivo = "arma la URL de envío de Meta"
            elif HOST_META in cadena:
                motivo = f"nombra `{HOST_META}`"
            if motivo:
                vistas.add(linea)
                r.error("enviar/segundo_camino",
                        f"{motivo} fuera de agente/enviar.py. Con o sin la ruta al lado: las URL "
                        f"de envío viven en un solo archivo, y una constante escrita acá se importa "
                        f"desde cualquier lado sin que el `post` que la usa se vea en ningún grep. "
                        f"Si es una constante, va adentro de agente/enviar.py; si necesitás la base "
                        f"para bajar un medio, importala de ahí",
                        rel, linea, "build")

    if not dueno.is_file():
        # Error y no aviso: con `agente/` en el árbol la construcción ya corrió, y un build sin
        # `enviar.py` no tiene ese solo lugar por donde sale todo. Como aviso no fallaba nada.
        r.error("enviar/sin_modulo",
                "no existe agente/enviar.py y la construcción ya corrió. El invariante es que "
                "todo lo que sale pasa por un solo lugar: sin ese archivo no hay tal lugar, y "
                "cada módulo que mande algo lo va a mandar a su manera",
                "agente/enviar.py", 0, "build")
    # Ningún eximido, y por eso no hay lista que imprimir: la regla es por destino, así que el
    # dueño es uno solo y todo lo demás se mira igual, incluido `agente/http.py`.
    r.decir(f"{max(len(arboles) - 1, 0)} módulo(s) revisados contra los dos endpoints de "
            f"mensajería · dueño: agente/enviar.py · sin eximidos")


# ─────────────────────────────────────────────────────────────────────────────
# 14 · agente-completo
# ─────────────────────────────────────────────────────────────────────────────

# Dónde está escrita la promesa. La tabla se sigue leyendo —lo que ella agregue se exige igual, así
# que un módulo nuevo no necesita tocar este archivo—, pero ya no es lo único: abajo está el piso.
TABLA_DE_MODULOS = "blueprint/30-generacion.md"

# ─── El piso ─────────────────────────────────────────────────────────────────
#
# Ruta → lo que esa ruta tiene que traer escrito adentro. En un archivo son símbolos de nivel de
# módulo; en un directorio, nombres de archivo.
#
# **Un token que termina en `()` es una llamada, no un símbolo**: tiene que aparecer adentro del
# módulo, y se compara por la hoja del nombre, con los alias resueltos —`html.escape()` matchea
# `html.escape(x)`, `escape(x)` y el `e(x)` de un `e = html.escape`—, así que no prescribe cómo se
# escribió el import ni si el nombre se acortó adentro del cuerpo. Existe porque el nombre a secas
# no alcanza en dos filas de esta tabla: `def modelo_de_produccion(): raise NotImplementedError`
# define el símbolo, mide más de cero bytes y parsea. La contracara del mismo agujero es
# `agente/simbolo_vaciado`, que mira el cuerpo de los símbolos que sí son símbolos.
#
# **Por qué existe.** Este chequeo leía su especificación entera de `blueprint/30-generacion.md`, o
# sea de un archivo que el mismo agente que construye puede editar. Sacarle tres filas a esa tabla
# bajaba trece errores a diez y nada lo notaba: el chequeo decía «14 módulo(s) de la tabla, todos en
# el árbol» y el veredicto salía en verde con tres módulos menos. Un chequeo cuya vara la escribe el
# auditado no es una vara.
#
# Se eligió el piso duro y no el sha256 de la tabla en `plantillas/MANIFIESTO.json` por tres
# motivos: el manifiesto hashea archivos verbatim que se copian tal cual —una tabla de prosa que se
# edita en cada ronda no es eso, y cada corrección de una tilde pediría `hash_plantillas.py
# --escribir`—; el hash diría «la tabla cambió» y no «falta `agente/servidor.py`», que es lo que hay
# que leer; y sobre todo, el hash vive en un archivo que también se puede editar, así que mueve el
# problema un archivo más allá en vez de cerrarlo. El piso está acá adentro, en la compuerta, que es
# lo único que el build no escribe.
#
# **Los símbolos no se inventan acá**: cada uno está prometido por escrito, y al lado va dónde.
PISO_DE_MODULOS: dict[str, tuple[str, ...]] = {
    # 30-generacion.md, paso 2: «una clase `Ajustes(BaseSettings)` y una sola instancia».
    "agente/__init__.py": (),
    "agente/ajustes.py": ("Ajustes", "ajustes"),
    # 30-generacion.md, paso 2: las dos funciones, y 00-contrato.md § 9.
    "agente/config.py": ("entrada_desde_config", "modo_efectivo"),
    # `pruebas/proveedor_falso.py` parcha `http.TRANSPORTE` y levanta `SinAgente` si no está: sin
    # ese nombre no hay forma de mirar lo que sale del webhook sin abrir un socket.
    "agente/http.py": ("TRANSPORTE",),
    # 30-generacion.md, paso 3, con el bloque de código de las dos funciones de URL, `migrar()` y
    # `registrar_evento()`; y 00-contrato.md § 8.
    "agente/base.py": ("normalizar_url", "url_sincrona", "RecordatorioSinDriver", "migrar",
                       "registrar_evento"),
    # 30-generacion.md, paso 4: «`anclar_presupuesto()` exige una subcadena literal del mensaje».
    # El símbolo se exige y **no se escribe acá**: llega importado. Ver `DELEGADOS`, abajo.
    "agente/salida.py": ("anclar_presupuesto",),
    # 30-generacion.md, paso 5, y el «Tenés que ver» que compara `p() == p()`.
    "agente/prompt.py": ("prompt_de_sistema",),
    # `pruebas/simulador.py`, en `_elegir_modelo()`:
    #
    #     fabrica = getattr(modelo, "modelo_de_produccion", None)
    #
    # Esta fila pedía cero símbolos, así que un `agente/modelo.py` que llamara a su fábrica de
    # cualquier otra forma pasaba el chequeo entero y el simulador nunca encontraba el nombre. Y
    # la falla es muda: `getattr(..., None)` no levanta nada, el simulador se cae al stub y la
    # cabecera dice «modelo stub, sin ANTHROPIC_API_KEY» **con la clave cargada**. Quien lo mire
    # va a ir a buscar la variable de entorno, que está bien.
    #
    # Es el único símbolo del piso que no promete ninguna prosa: hoy `grep -rn
    # modelo_de_produccion blueprint/ scripts/ *.md` no imprime una línea, y quien construya fiel
    # al blueprint no tiene de dónde sacar el nombre. Quien lo prometa por escrito que lo escriba
    # en `blueprint/30-generacion.md` paso 5; mientras tanto la exigencia vive acá, que es donde
    # el build no la puede editar, y falla ruidoso en vez de fallar en silencio.
    #
    # **Y el nombre solo no alcanzaba acá más que en ningún otro archivo**, porque éste es el módulo
    # que la suite no puede cubrir por diseño: `StubModel` se inyecta justo para no ejecutar la
    # llamada real. `def modelo_de_produccion(): raise NotImplementedError` definía el símbolo,
    # medía más de cero bytes y parseaba, y el árbol entero seguía en verde. Eso lo cierra
    # `agente/simbolo_vaciado`, que mira el cuerpo.
    #
    # Lo que **no** se pide acá es la llamada a `esquema_wire()`, aunque sea lo único que
    # `blueprint/30-generacion.md` paso 5 promete del cuerpo. El esquema tiene que viajar adentro
    # del pedido; de qué módulo salió no lo fija ningún archivo, y un build que lo arme en otro
    # lado y lo pase por parámetro es fiel. Que el pedido lo lleve entero —los once campos, por la
    # forma que el build haya elegido— lo afirma `pruebas/test_modelo.py` desde esta ronda, que es
    # donde se puede afirmar mirando el pedido y no el import.
    "agente/modelo.py": ("modelo_de_produccion",),
    # 31-proveedores.md paso 1 (`enviar`), 32-multimodal.md paso 1 (las dos bases) y paso 5
    # (`avisar_interno`).
    "agente/enviar.py": ("enviar", "avisar_interno", "BASE_META", "BASE_ZERNIO"),
    "agente/medios.py": (),
    # El `CMD` del Dockerfile dice `uvicorn agente.servidor:app`, y ese archivo es verbatim.
    "agente/servidor.py": ("app",),
    # 00-contrato.md § 4 y 40-pruebas.md paso 2: `correr_ciclo(entrada, *, modelo, deps)`.
    "agente/ciclo.py": ("correr_ciclo",),
    # 35-panel-api.md paso 4, y 00-contrato.md § 3 regla 3: la dependencia va sobre el router
    # entero, con `Depends`, nunca ruta por ruta. Esta fila pedía el archivo y **ningún** símbolo,
    # que es como un `panel/panel.py` con un `#` adentro pasaba el chequeo 14 y el kit entero
    # decía que estaba bien. Los dos nombres los verifica además el chequeo 21 `panel-cerrado`:
    # acá se pide que existan, allá que hagan lo que prometen.
    #
    # Y `html.escape()`, que es la tercera cosa de este archivo y la que no tenía vara ninguna.
    # `blueprint/35-panel-api.md` paso 8 lo dice con todas las letras: el panel muestra texto que
    # escribió un desconocido por WhatsApp, un mensaje con `<script>` adentro corre en el navegador
    # de quien lee la bandeja, y ahí vive la cookie del token —«el camino más corto que existe para
    # perder el panel entero»—. Se pide la **llamada** y no el import: `import html` sin una sola
    # llamada pasa cualquier chequeo que pregunte por el nombre, y sacar la llamada es exactamente
    # lo que nadie ve. Que se aplique a **todo** lo que viene del chat no lo mira esta fila; eso es
    # del chequeo 21 y de `pruebas/test_panel.py`. Acá se cierra el caso de que no esté ninguna.
    #
    # La forma se compara igual que allá, con los alias resueltos. `pruebas/test_panel.py` cuenta
    # el `e(x)` de un `e = html.escape` y explica por qué —un panel que escapa bien escrito así no
    # puede salir rojo—, y esta fila pedía la hoja pelada: el mismo build daba `231 passed` y
    # `auditar: FAIL · 1 error`. La compuerta y la suite no pueden pedir dos cosas distintas del
    # mismo renglón, y la que cede es la compuerta. Ver `_alias_de()`.
    "panel/panel.py": ("router", "exigir_token", "html.escape()"),
    # Los directorios, con los archivos que 00-contrato.md § 4 nombra uno por uno. Adentro no se
    # piden símbolos: cómo se llama cada cuerpo lo decide el dueño de ese archivo, no la compuerta.
    "agente/proveedores/": ("__init__.py", "base.py", "demo.py", "meta.py", "zernio.py"),
    "agente/pasos/": ("paso_1_contexto.py", "paso_2_calificar.py", "paso_3_responder.py",
                      "paso_4_agenda.py", "paso_5_crm.py", "paso_6_handoff.py"),
    "agente/integraciones/": ("calendario.py", "crm.py"),
    "pruebas/*.py": (),
}

# Los símbolos del piso que **no** se escriben en el archivo que los expone: llegan importados del
# módulo que ya los tiene escritos, y escribirlos de nuevo es el hallazgo.
#
# **Por qué existe.** `_simbolos_de_modulo()` cuenta lo importado, así que la delegación ya pasaba
# el chequeo; lo que faltaba era exigirla. Leído desde el build, `PISO_DE_MODULOS` pide
# `anclar_presupuesto` en `agente/salida.py` y la lectura obvia de un hallazgo que dice «no define
# `anclar_presupuesto`» es sentarse a escribir la guarda. Pero esa guarda ya está escrita entera
# —las dos compuertas, la subcadena literal y las cifras— en `plantillas/contratos/wire_schema.py`,
# que el paso 1 de `blueprint/30-generacion.md` copia verbatim a `agente/wire_schema.py` y que el
# chequeo 02 `manifiesto` hashea byte por byte. O sea que la compuerta inducía un duplicado: dos
# versiones de la misma regla, las dos en verde, que se separan en la primera corrección —alguien
# afloja la comparación de la evidencia en una de las dos y la otra sigue diciendo lo que decía—.
#
# **Se resolvió del lado de la compuerta y no sacando el símbolo del piso**, porque sacarlo deja
# `agente/salida.py` sin un solo símbolo exigido, que es exactamente el estado en el que un archivo
# con un `#` adentro pasaba el chequeo 14 entero. El símbolo se queda; lo que cambia es que se pide
# por el nombre importado y se prohíbe volver a escribirlo.
#
# La forma se prescribe una sola, igual que `from agente.ajustes import ajustes` en
# `blueprint/00-contrato.md` § 4: `from agente.wire_schema import anclar_presupuesto`. Con
# `import agente.wire_schema` el nombre no queda a la vista del módulo y no hay qué exigir.
DELEGADOS: dict[tuple[str, str], str] = {
    # 00-contrato.md § 4: `agente/wire_schema.py` es verbatim y no se edita nunca.
    ("agente/salida.py", "anclar_presupuesto"): "agente/wire_schema.py",
}

# Una fila de la tabla: la ruta prometida es el primer token de la línea, adentro de un bloque de
# código. `agente/pasos/` con la barra es un directorio; `pruebas/*.py` es un glob; el resto son
# archivos. Las líneas de continuación —las que empiezan con espacios y siguen describiendo la fila
# de arriba— no traen ruta y no matchean.
FILA_DE_MODULO = re.compile(r"^(agente|panel|pruebas)/[\w./*-]*$")

# La cerca de un bloque de código en markdown. La misma forma que `CERCA_DE_PINES`, con otro
# nombre porque acá no se está leyendo PINES.md: compartir la constante ataba dos parsers que no
# tienen por qué moverse juntos.
CERCA_DE_BLOQUE = re.compile(r"^\s*```")

# El bloque de las copias tiene otra forma —`plantillas/x → agente/x`— y no se lee acá: esos siete
# archivos ya los exige el chequeo 02 `manifiesto` con `--proyecto`, hash por hash, y los nombra
# uno por uno con el `cp` que los arregla. Dos chequeos pidiendo lo mismo es un hallazgo duplicado
# y una regla con dos dueños.
FLECHA_DE_COPIA = "→"


def _simbolos_de_modulo(arbol: ast.Module) -> set[str]:
    """Los nombres que este módulo deja disponibles, mirando sólo el nivel de módulo.

    Se cuenta también lo importado: un `__init__.py` que reexporta es una forma legítima de dejar
    un nombre a la vista, y exigir un `def` en ese archivo sería la compuerta decidiendo cómo se
    organiza el paquete. Lo que se exige es que el nombre exista, no dónde se escribió.
    """
    nombres: set[str] = set()
    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nombres.add(nodo.name)
        elif isinstance(nodo, ast.Assign):
            nombres |= {t.id for t in nodo.targets if isinstance(t, ast.Name)}
        elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            nombres.add(nodo.target.id)
        elif isinstance(nodo, (ast.Import, ast.ImportFrom)):
            nombres |= {(a.asname or a.name).split(".")[0] for a in nodo.names}
    return nombres


def _alias_de(arbol: ast.Module, hoja: str) -> set[str]:
    """Todo nombre que en este módulo apunta a esa función, con sus alias.

    Las tres formas que dan la misma función y que un build escribe de verdad: `from html import
    escape`, `from html import escape as e`, y `e = html.escape` para no repetirla doce veces
    adentro del armado. La primera ya la resolvía la hoja del nombre; las otras dos no, medido, y
    la del `e = html.escape` ligado adentro de `pagina()` es la que puso en rojo a un panel que
    escapaba bien.

    Se resuelve por la hoja, igual que la llamada: un `from lo_que_sea import escape as e` liga `e`
    lo mismo. La cadena se sigue hasta que deja de crecer, así que `esc = e` también cuenta. Los
    destinos que no son un nombre pelado —`self.escape = …`— no ligan nada acá.
    """
    nombres = {hoja}
    asignaciones: list[ast.Assign] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom):
            nombres |= {a.asname for a in nodo.names if a.name == hoja and a.asname}
        elif isinstance(nodo, ast.Assign):
            asignaciones.append(nodo)
    crecio = True
    while crecio:
        crecio = False
        for nodo in asignaciones:
            valor = nodo.value
            apunta = ((isinstance(valor, ast.Attribute) and valor.attr == hoja)
                      or (isinstance(valor, ast.Name) and valor.id in nombres))
            if not apunta:
                continue
            destinos = {t.id for t in nodo.targets if isinstance(t, ast.Name)} - nombres
            if destinos:
                nombres |= destinos
                crecio = True
    return nombres


def _llama_a(arbol: ast.Module, punteado: str) -> int:
    """La línea donde este módulo **llama** a esa función, o 0. Se compara por la hoja del nombre.

    `html.escape` matchea `html.escape(x)`, `escape(x)` y el `e(x)` de un `e = html.escape`: son
    las tres formas de tener la misma función a mano según cómo se haya escrito el import. La
    compuerta no prescribe cuál: lo que pide es que la llamada esté, no cómo entró el nombre al
    módulo.

    **Por qué resuelve los alias.** El nodo de `pruebas/test_panel.py` que cuenta este mismo
    escapado por AST los resuelve a propósito y lo dice en su propio texto —«sin los alias, esta
    prueba se pone roja contra un panel que escapa bien, que es peor que no tenerla»—. Con la hoja
    a secas, la compuerta rechazaba justo la forma que la suite bendice por escrito: medido, un
    panel con `e = html.escape` adentro de `pagina()` daba la suite entera en verde y
    `auditar: FAIL · 1 error`, o sea un build que escapa bien y no publica. Una compuerta que
    contradice a la suite no agrega una vara: agrega una discusión, y la pierde el que construyó
    bien.

    Es a propósito una vara baja. Afirma que la llamada **existe**, no que se aplique a todo lo que
    hay que aplicarla: un `escape` puesto sobre una cadena y olvidado en la de al lado la pasa. Lo
    que cierra es el caso de esta ronda, que es la llamada que desaparece entera —el módulo vaciado,
    o la línea que alguien saca porque «rompía el formato»— y que ninguna prueba de la suite ve.
    """
    hoja = punteado.split(".")[-1]
    nombres = _alias_de(arbol, hoja)
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        if isinstance(f, ast.Attribute) and f.attr == hoja:
            return nodo.lineno
        if isinstance(f, ast.Name) and f.id in nombres:
            return nodo.lineno
    return 0


def _cuerpo_vaciado(arbol: ast.Module, simbolo: str) -> int:
    """La línea del `raise` de una función del piso cuyo cuerpo es sólo eso, o 0.

    ```python
    def modelo_de_produccion():
        raise NotImplementedError
    ```

    Eso define el símbolo, mide más de cero bytes, parsea, y no hace nada. Con el símbolo pedido a
    secas, ésa era la forma de vaciar un módulo del piso dejando el árbol entero en verde: la suite
    no lo toca —`StubModel` se inyecta justo para no ejecutar la llamada real— y el chequeo miraba
    el nombre y no el cuerpo.

    Un `raise` solo no es ilegítimo en cualquier función; en **éstas** sí. Los símbolos del piso son
    los puntos de entrada del árbol —`enviar`, `correr_ciclo`, `app`, `modelo_de_produccion`—: si
    alguno levanta y nada más, lo que hay no es un build a medias, es un build que no existe.
    """
    for nodo in arbol.body:
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) or nodo.name != simbolo:
            continue
        cuerpo = [n for n in nodo.body
                  if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                          and isinstance(n.value.value, str))]
        if len(cuerpo) == 1 and isinstance(cuerpo[0], ast.Raise):
            return cuerpo[0].lineno
    return 0


def _escrito_aca(arbol: ast.Module, simbolo: str) -> int:
    """La línea donde este módulo **escribe** el símbolo, o 0 si sólo lo trae de afuera.

    Un `def`, un `class` o una asignación a nivel de módulo. Importarlo no es escribirlo, y esa es
    justo la diferencia que `DELEGADOS` mide.
    """
    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if nodo.name == simbolo:
                return nodo.lineno
        elif isinstance(nodo, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == simbolo for t in nodo.targets):
                return nodo.lineno
        elif (isinstance(nodo, ast.AnnAssign)
                and isinstance(nodo.target, ast.Name) and nodo.target.id == simbolo):
            return nodo.lineno
    return 0


def _llega_de(arbol: ast.Module, simbolo: str, origen: str) -> bool:
    """`from <origen> import <simbolo>`, con el módulo escrito entero o relativo.

    Se aceptan `from agente.wire_schema import anclar_presupuesto` y
    `from .wire_schema import anclar_presupuesto`, que dan el mismo objeto. Un `as` que le cambie
    el nombre no cuenta: el símbolo que se exige es el que el resto del árbol va a buscar.
    """
    punteado = origen[:-3].replace("/", ".") if origen.endswith(".py") else origen.replace("/", ".")
    hoja = punteado.split(".")[-1]
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.ImportFrom):
            continue
        modulo = nodo.module or ""
        if modulo != punteado and not (nodo.level and modulo in (hoja, punteado)):
            continue
        if any(a.name == simbolo and (a.asname or a.name) == simbolo for a in nodo.names):
            return True
    return False


def chequeo_agente_completo(c: Contexto, r: Reporte) -> None:
    """Cada módulo del piso está en el árbol, y trae escritos los símbolos que promete.

    Este chequeo faltaba entero, y su ausencia es la que dejaba pasar un agente de mentira: sin
    `servidor.py`, sin `modelo.py`, sin `medios.py`, sin `pasos/`, sin `config.py`, sin calendario
    y sin CRM, la compuerta daba `pass`. Ninguno de los otros veintidós pregunta si un módulo
    existe —`enviar.py` de rebote y nada más—: `http-unico` mira los que hay, `cache-estatico`
    mira los que hay, `modelo` mira los que hay. Un árbol con dos archivos adentro de `agente/`
    los pasa todos, porque en dos archivos no hay dónde esconder un segundo cliente HTTP.

    **Preguntaba por el nombre y por «más de cero bytes», nunca por si adentro había algo.** Trece
    `printf '#\\n'` —doce archivos de dos bytes y un `__init__.py` vacío— lo llevaban de trece
    errores a `[ok]`, y con eso quedaban en verde el resto de los chequeos: los demás
    miran lo que hay, y en doce archivos de dos bytes no hay nada que mirar.
    Ahora cada archivo del piso trae la lista de los símbolos que tiene que definir y se pregunta
    por AST: un `#` no define `correr_ciclo`, y `mkdir` no escribe `paso_3_responder.py`.

    **Y la lista ya no sale sólo de un archivo que el auditado puede editar.** La tabla de
    `blueprint/30-generacion.md` se sigue leyendo y lo que ella agregue se exige igual —un módulo
    nuevo no tiene que pasar por acá—, pero el piso está en `PISO_DE_MODULOS`, adentro de la
    compuerta. Si una fila del piso desaparece de la tabla, eso mismo es el hallazgo: quien
    construya siguiendo la tabla recortada no va a escribir ese módulo.

    Un directorio del piso se cumple con los archivos que tiene nombrados; uno que venga sólo de la
    tabla, con cualquier `.py` adentro. Adentro de los directorios no se piden símbolos: cómo se
    llama cada cuerpo lo decide el dueño de ese archivo.

    **Y desde esta ronda mira el cuerpo, no sólo el nombre.** Preguntar por el símbolo cierra el
    archivo con un `#` adentro y no cierra el `def` cuyo cuerpo es `raise`, que define el nombre,
    mide más de cero bytes y parsea. La diferencia importa en los dos módulos que la suite **no
    puede** cubrir: `agente/modelo.py`, donde `StubModel` se inyecta justo para no ejecutar la
    llamada real, y el `html.escape` de `panel/panel.py`. Los dos se vaciaban así con el árbol
    entero en verde. Van dos hallazgos: `agente/llamada_prometida` para los tokens con `()`, y
    `agente/simbolo_vaciado` para una función del piso que sólo levanta.

    **Y un símbolo del piso puede estar prometido en un archivo y escrito en otro.** Ésos están en
    `DELEGADOS`, y ahí la exigencia se da vuelta: el archivo tiene que traerlo importado y **no**
    puede volver a escribirlo. Pedir el nombre a secas era la compuerta induciendo un duplicado
    —`anclar_presupuesto` ya está entera en el `wire_schema.py` que se copia verbatim, así que
    «no define `anclar_presupuesto`» se lee como «escribila»—, y dos copias de la misma regla se
    separan en la primera corrección, con las dos en verde.
    """
    if not c.hay_agente:
        r.saltear("no existe agente/: esto corre después de /armar-cerrador")
        return

    tabla = c.raiz / TABLA_DE_MODULOS
    prometidos: list[str] = []
    if not tabla.is_file():
        r.error("agente/sin_tabla",
                f"no existe `{TABLA_DE_MODULOS}` y ahí vive la lista de módulos que el build tiene "
                f"que dejar escritos. Queda el piso de la compuerta, que se exige igual; lo que no "
                f"hay es la parte que la tabla agrega. El chequeo 01 `blueprint-existe` ya lo va a "
                f"estar diciendo por su lado", TABLA_DE_MODULOS, 0, "kit")
    else:
        prometidos = _modulos_prometidos(_texto(tabla))
        if not prometidos:
            r.error("agente/tabla_ilegible",
                    f"leí `{TABLA_DE_MODULOS}` y no saqué una sola ruta de módulo. O la tabla "
                    f"cambió de forma —las filas empiezan con la ruta, adentro de un bloque de "
                    f"código—, o el archivo quedó a medias. El piso se exige igual, pero quien "
                    f"construya siguiendo esa tabla no tiene qué escribir",
                    TABLA_DE_MODULOS, 0, "kit")

    # Lo que el piso pide y la tabla ya no nombra. No es un detalle de forma: la tabla es lo que
    # lee quien construye, así que una fila borrada es un módulo que nadie va a escribir, y hasta
    # hoy eso bajaba la cuenta de errores en vez de subirla.
    if prometidos:
        recortadas = [ruta for ruta in PISO_DE_MODULOS if ruta not in prometidos]
        if recortadas:
            r.error("agente/tabla_recortada",
                    f"la tabla de {TABLA_DE_MODULOS} ya no nombra {len(recortadas)} ruta(s) del "
                    f"piso: {', '.join(recortadas)}. Quien construya siguiendo esa tabla no las va "
                    f"a escribir, y este chequeo las exige igual porque el piso vive en la "
                    f"compuerta. O volvés a poner la fila, o el piso de scripts/auditar.py cambia "
                    f"con el mismo commit y se dice por qué", TABLA_DE_MODULOS, 0, "kit")

    rutas = list(PISO_DE_MODULOS) + [p for p in prometidos if p not in PISO_DE_MODULOS]
    faltan = 0
    for ruta in rutas:
        exigidos = PISO_DE_MODULOS.get(ruta, ())
        destino = c.raiz / ruta
        if ruta.endswith("/"):
            # Un `__init__.py` de cero bytes es un paquete válido y es como se escribe la mitad de
            # ellos; para el resto, cero bytes es el archivo que quedó a medias.
            adentro = ({p.name for p in destino.iterdir()
                        if p.is_file() and (_tamano(p) > 0 or p.name == "__init__.py")}
                       if destino.is_dir() else set())
            # Sin nombres declarados, la exigencia es la de siempre: que haya algo escrito.
            sin_escribir = sorted(set(exigidos) - adentro) if exigidos else (
                [] if any(p.is_file() and _tamano(p) > 0
                          for p in destino.rglob("*.py")) else ["cualquier .py"])
            if destino.is_dir() and not sin_escribir:
                continue
            faltan += 1
            que = (f"no tiene escrito(s): {', '.join(sin_escribir)}" if destino.is_dir()
                   else "no existe")
            r.error("agente/directorio_prometido",
                    f"`{ruta}` {que}. Un directorio vacío es un `mkdir`, no un build: lo que iba "
                    f"adentro no se escribió y nada más lo reporta. Los nombres salen del piso de "
                    f"scripts/auditar.py, que los toma de blueprint/00-contrato.md § 4",
                    ruta, 0, "build")
            continue
        if "*" in ruta:
            padre, patron = ruta.rsplit("/", 1)
            carpeta = c.raiz / padre
            if carpeta.is_dir() and any(carpeta.glob(patron)):
                continue
            faltan += 1
            r.error("agente/glob_prometido",
                    f"`{ruta}` no matchea un solo archivo y está prometido", ruta, 0, "build")
            continue
        # Un `__init__.py` de cero bytes es un paquete válido y es como se escribe la mitad de
        # ellos: ahí el tamaño no dice nada. Para el resto sí, y el tamaño tampoco alcanza: lo que
        # se pregunta es qué define.
        if not destino.is_file():
            faltan += 1
            r.error("agente/modulo_prometido",
                    f"`{ruta}` no existe, y está prometido escrito. Con `agente/` en el árbol la "
                    f"construcción ya corrió: un módulo prometido y ausente es una fase que no se "
                    f"hizo, y la mitad de los otros chequeos van a dar verde igual porque miran lo "
                    f"que hay", ruta, 0, "build")
            continue
        if _tamano(destino) == 0 and destino.name != "__init__.py":
            faltan += 1
            r.error("agente/modulo_prometido",
                    f"`{ruta}` mide cero bytes, y está prometido escrito. Con `agente/` en el "
                    f"árbol la construcción ya corrió", ruta, 0, "build")
            continue
        if not exigidos:
            continue
        arbol, problema = _arbol(destino)
        if arbol is None:
            faltan += 1
            r.error("agente/modulo_ilegible",
                    f"`{ruta}` no parsea ({problema}), así que no puedo decir si define "
                    f"{', '.join(exigidos)}. Un módulo que no parsea tampoco importa en runtime",
                    ruta, 0, "build")
            continue
        # Los tokens con `()` al final no son símbolos: son llamadas que tienen que aparecer
        # adentro del módulo. Se separan acá y se miran abajo, con su propio hallazgo.
        llamadas = [s[:-2] for s in exigidos if s.endswith("()")]
        simbolos = [s for s in exigidos if not s.endswith("()")]
        delegados = {s: DELEGADOS[(ruta, s)] for s in simbolos if (ruta, s) in DELEGADOS}
        disponibles = _simbolos_de_modulo(arbol)
        sin_definir = [s for s in simbolos if s not in disponibles and s not in delegados]
        roto = False
        for punteado in llamadas:
            if _llama_a(arbol, punteado):
                continue
            roto = True
            r.error("agente/llamada_prometida",
                    f"`{ruta}` no llama a `{punteado}()` ni una vez, y está prometida. Es la "
                    f"exigencia que mira adentro del cuerpo y no el nombre, porque acá el nombre no "
                    f"alcanza: importar algo y no llamarlo nunca pasa cualquier chequeo que "
                    f"pregunte por el símbolo. Se pide la llamada y no el import: la hoja del "
                    f"nombre —`{punteado.split('.')[-1]}(…)`— matchea escrita de las tres formas, "
                    f"`{punteado}(x)`, `{punteado.split('.')[-1]}(x)` y el `e(x)` de un "
                    f"`e = {punteado}`, así que la compuerta no te está eligiendo ni el import ni "
                    f"el nombre corto. Si la escribiste de alguna de esas tres y esto salió igual, "
                    f"el hallazgo es del kit y no tuyo. El motivo de cada llamada está "
                    f"al lado de su fila, en el piso de scripts/auditar.py",
                    ruta, 0, "build")
        for simbolo in simbolos:
            linea = _cuerpo_vaciado(arbol, simbolo)
            if not linea:
                continue
            roto = True
            r.error("agente/simbolo_vaciado",
                    f"`{ruta}` define `{simbolo}` y su cuerpo entero es un `raise`. Eso pasa el "
                    f"nombre, el tamaño y el parseo, y no hace nada: es la forma más barata que "
                    f"queda de vaciar un módulo del piso con el árbol en verde. Los símbolos del "
                    f"piso son los puntos de entrada —`enviar`, `correr_ciclo`, `app`, "
                    f"`modelo_de_produccion`—: uno que sólo levanta no es un build a medias, es un "
                    f"build que no está", ruta, linea, "build")
        if sin_definir:
            roto = True
            r.error("agente/simbolo_prometido",
                    f"`{ruta}` existe y no define {', '.join(sin_definir)}. Existir no es estar "
                    f"escrito: un archivo con un `#` adentro pasa cualquier chequeo que pregunte "
                    f"por el nombre y por el tamaño, y el que lo importe se lleva un ImportError "
                    f"en la primera entrega real. Cada símbolo de esta lista está prometido por "
                    f"escrito, y el piso de scripts/auditar.py dice dónde", ruta, 0, "build")
        for simbolo, origen in delegados.items():
            linea = _escrito_aca(arbol, simbolo)
            if linea:
                roto = True
                r.error("agente/simbolo_duplicado",
                        f"`{ruta}` escribe `{simbolo}` y esa regla ya está escrita entera en "
                        f"`{origen}`, que se copia verbatim y que el chequeo 02 `manifiesto` "
                        f"hashea byte por byte. Quedan dos versiones de lo mismo, las dos en "
                        f"verde, y se separan en la primera corrección: alguien afloja una y la "
                        f"otra sigue diciendo lo que decía, sin que nada se ponga rojo. Borrá "
                        f"este cuerpo y poné `from {origen[:-3].replace('/', '.')} import "
                        f"{simbolo}`", ruta, linea, "build")
                continue
            if not _llega_de(arbol, simbolo, origen):
                roto = True
                r.error("agente/simbolo_sin_delegar",
                        f"`{ruta}` tiene que exponer `{simbolo}` y no lo trae de `{origen}`. El "
                        f"símbolo no se escribe acá: la línea es "
                        f"`from {origen[:-3].replace('/', '.')} import {simbolo}`, y se prescribe "
                        f"una sola forma por lo mismo que `from agente.ajustes import ajustes` en "
                        f"blueprint/00-contrato.md § 4 —con `import "
                        f"{origen[:-3].replace('/', '.')}` el nombre no queda a la vista del "
                        f"módulo y el que lo importe de acá se lleva un ImportError",
                        ruta, 0, "build")
        if roto:
            faltan += 1

    if not faltan:
        exigencias = [s for v in PISO_DE_MODULOS.values() for s in v]
        cuantas = len(exigencias)
        llamadas_del_piso = sum(1 for s in exigencias if s.endswith("()"))
        r.decir(f"{len(rutas)} ruta(s) —{len(PISO_DE_MODULOS)} del piso de la compuerta, "
                f"{len(rutas) - len(PISO_DE_MODULOS)} más de {TABLA_DE_MODULOS}— y {cuantas} "
                f"exigencia(s): {cuantas - llamadas_del_piso} símbolo(s) y archivo(s) y "
                f"{llamadas_del_piso} llamada(s), todas en el árbol")


def _modulos_prometidos(texto: str) -> list[str]:
    """Las rutas de la tabla de módulos, en orden y sin repetir.

    Sólo adentro de bloques de código: la prosa del archivo nombra `agente/servidor.py` una docena
    de veces y ninguna de esas menciones es una fila de la tabla.
    """
    encontrados: list[str] = []
    dentro = False
    for linea in texto.splitlines():
        if CERCA_DE_BLOQUE.match(linea):
            dentro = not dentro
            continue
        if not dentro or FLECHA_DE_COPIA in linea:
            continue
        partes = linea.split()
        if not partes or linea[:1].isspace():
            continue
        ruta = partes[0]
        if FILA_DE_MODULO.match(ruta) and ruta not in encontrados:
            encontrados.append(ruta)
    return encontrados


# ─────────────────────────────────────────────────────────────────────────────
# 15 · cache-estatico
# ─────────────────────────────────────────────────────────────────────────────

RELOJ = frozenset({"now", "utcnow", "today", "time", "time_ns", "monotonic", "perf_counter"})
MODULOS_VARIABLES = frozenset({"uuid", "random", "secrets"})


def chequeo_cache_estatico(c: Contexto, r: Reporte) -> None:
    """Un `datetime.now()` en el prefijo del prompt pone la tasa de acierto del caché en cero.

    Para siempre y sin un solo error visible: el prefijo cambia en cada petición, así que nunca
    hay nada que reusar. La factura sube y la latencia también, y no hay nada roto que mirar.

    Se revisa el constructor del prompt de sistema, que acá se identifica por nombre: una
    función cuyo nombre diga `prompt`, `sistema` o `system`, o cualquier función de un módulo
    que se llame así. Si no encuentra ninguna lo dice y saltea, en vez de fingir que revisó.
    """
    if not c.hay_agente:
        r.saltear("no existe agente/: esto corre después de /armar-cerrador")
        return

    revisadas = 0
    for modulo in c.modulos():
        arbol, _ = _arbol(modulo)
        if arbol is None:
            continue
        rel = c.rel(modulo)
        modulo_de_prompt = bool(NOMBRE_DE_PROMPT.search(modulo.stem))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not (modulo_de_prompt or NOMBRE_DE_PROMPT.search(nodo.name)):
                continue
            revisadas += 1
            for hallazgo in _variable_en_el_prefijo(nodo):
                linea, que, detalle = hallazgo
                r.error("cache/prefijo_variable",
                        f"`{nodo.name}()` {detalle} ({que}). El prefijo del prompt tiene que ser "
                        f"idéntico byte por byte en cada petición o el caché no acierta nunca, y "
                        f"eso no tira ningún error: solo sube la factura", rel, linea, "build")
    if revisadas == 0:
        r.saltear("no encontré ningún constructor de prompt de sistema en agente/: nombrá esa "
                  "función con `prompt` o `sistema` para que esto la revise")
        return
    r.decir(f"{revisadas} constructor(es) de prompt revisados")


def _variable_en_el_prefijo(fn: ast.FunctionDef | ast.AsyncFunctionDef):
    parametros = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
    sospechosos = {p for p in parametros if p in DEL_REQUEST}
    for nodo in ast.walk(fn):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
            base = _raiz_del_nombre(nodo.func)
            if nodo.func.attr in RELOJ:
                yield nodo.lineno, _fuente(nodo.func), "lee el reloj"
            elif base in MODULOS_VARIABLES:
                yield (nodo.lineno, _fuente(nodo.func),
                       f"usa `{base}`, que devuelve algo distinto cada vez")
        elif isinstance(nodo, ast.JoinedStr):
            for parte in nodo.values:
                if not isinstance(parte, ast.FormattedValue):
                    continue
                raiz = _raiz_del_nombre(parte.value)
                if raiz in sospechosos:
                    yield (nodo.lineno, _fuente(parte.value),
                           "interpola en el prefijo un valor que viene de la petición")


# ─────────────────────────────────────────────────────────────────────────────
# 16 y 17 · contrato y contrato-control
# ─────────────────────────────────────────────────────────────────────────────

_DRIVER_CONTRATO = r'''
import json, sys

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:
    print(json.dumps({"error": "falta jsonschema"}))
    raise SystemExit(0)

esquema = json.load(open(sys.argv[1], encoding="utf-8"))
try:
    Draft202012Validator.check_schema(esquema)
except Exception as e:
    print(json.dumps({"error": "el esquema no es un JSON Schema válido: %s" % e}))
    raise SystemExit(0)

validador = Draft202012Validator(esquema)
casos = json.loads(sys.stdin.read())
salida = []
for nombre, doc in casos:
    errores = []
    for e in validador.iter_errors(doc):
        ruta = "/".join(str(p) for p in e.absolute_path) or "#"
        errores.append("%s: %s" % (ruta, e.message))
    salida.append([nombre, errores])
print(json.dumps({"resultados": salida}, ensure_ascii=False))
'''

# La salida buena, sacada de "Salida esperada" de `pruebas/caso-01.md`: estado `parcial`, `cita`
# en nulo, `crm` con la fila armada y `escrito` en falso, los pasos 3, 4 y 5 sin confirmar. Vive
# acá adentro y no en un archivo del proyecto a propósito: es el patrón contra el que se mide el
# validador mismo, y tiene que existir aunque todavía no se haya construido nada.
#
# **`crm` con la fila y `ventana_abierta` en nulo son la forma que manda**, y es de
# `blueprint/00-contrato.md` § 13: el nulo de `crm` significa «el paso 5 no corrió» y no puede
# significar además «corrió y no escribió», y `ventana_abierta` sale del `Resultado` de `enviar()`
# —que en un turno en borrador no se llama— y no se pone a mano. Esta constante y
# `pruebas/fixtures/caso-01.salida-esperada.json` se mueven juntas: las compara byte por byte
# `pruebas/test_contrato.py::test_la_salida_esperada_es_la_misma_que_mira_la_compuerta`.
SALIDA_BUENA: dict = {
    "version": "1",
    "estado": "parcial",
    "contacto": {
        "numero": "5215500000000",
        "id": "bsu_01HZK3M9QX7T2VW4",
        "nuevo": True,
        "mensajes_previos": 0,
    },
    "calificacion": {
        "score": 62,
        "temperatura": "tibio",
        "intencion": "precio del curso",
        "presupuesto": None,
        "urgencia": "media",
        "motivo": "Preguntó precio y puso una objeción que está en el playbook.",
    },
    "respuesta": {
        "texto": "El curso sale 12000 MXN y se puede en tres partes. ¿Te va alguno de estos horarios?",
        "enviado": False,
        "objecion_detectada": "Está caro",
        "objecion_en_playbook": True,
        "horarios_ofrecidos": [
            "2026-03-02T11:00:00-06:00",
            "2026-03-02T17:00:00-06:00",
            "2026-03-03T10:00:00-06:00",
        ],
        "ventana_abierta": None,
    },
    "cita": None,
    "crm": {
        "etapa": "calificado",
        "resumen": (
            "Preguntó el precio del curso de bienes raíces.\n"
            "Se le respondió la objeción de precio y se le ofrecieron tres horarios.\n"
            "Falta que elija uno."
        ),
        "proximo_paso": "Confirmar horario",
        "proximo_paso_fecha": "2026-03-03",
        "escrito": False,
    },
    "handoff": None,
    "pasos": [
        {"n": 1, "estado": "hecho", "motivo": None},
        {"n": 2, "estado": "hecho", "motivo": None},
        {"n": 3, "estado": "sin-confirmar", "motivo": "modo borrador: falta confirmación"},
        {"n": 4, "estado": "sin-confirmar", "motivo": "no hay horario elegido"},
        {"n": 5, "estado": "sin-confirmar", "motivo": "modo borrador: falta confirmación"},
        {"n": 6, "estado": "salteado", "motivo": "no hay motivo de escalación"},
    ],
    "pregunta": None,
    "supuestos": ["S03"],
}

SEIS_PASOS = [1, 2, 3, 4, 5, 6]


def _validar_documentos(c: Contexto, casos: list[tuple[str, dict]]) -> tuple[dict | None, str]:
    esquema = c.raiz / "contratos/salida.schema.json"
    if not esquema.is_file():
        return None, "falta contratos/salida.schema.json"

    ultimo = "no probé ningún intérprete"
    for interprete in c.interpretes:
        codigo, salida = _correr(
            [interprete, "-c", _DRIVER_CONTRATO, str(esquema)], cwd=c.raiz,
            entrada=json.dumps(casos, ensure_ascii=False),
        )
        if codigo != 0:
            ultimo = f"el validador no corrió: {_recorte(salida)}"
            continue
        try:
            datos = json.loads(salida.splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            ultimo = f"el validador devolvió algo que no es JSON: {_recorte(salida)}"
            continue
        if "error" in datos:
            ultimo = str(datos["error"])
            continue
        return {nombre: errores for nombre, errores in datos["resultados"]}, ""
    return None, ultimo


def _fixtures_de_salida(c: Contexto) -> list[Path]:
    """Los fixtures de salida del agente, si alguien ya los escribió.

    Se buscan por nombre —`salida*.json` o `*.salida.json`— y no por «todo json de la carpeta»,
    porque ahí adentro también viven las fichas de firma, que no son salidas del agente.
    """
    carpeta = c.raiz / "pruebas"
    if not carpeta.is_dir():
        return []
    encontrados = set(carpeta.rglob("salida*.json")) | set(carpeta.rglob("*.salida.json"))
    return sorted(encontrados)


def _codigo_que_escribe_la_salida(c: Contexto) -> tuple[str, float]:
    """El `.py` más nuevo de `agente/` y `pruebas/`, con su mtime. Vacío si no hay ninguno.

    Es el mismo conjunto de archivos que hashea `_huella_del_censo`, y por el mismo motivo: son
    los que deciden qué documento devuelve una corrida del ciclo. Si uno de ellos se movió después
    de que la salida se escribió, esa salida la produjo otro árbol.
    """
    nuevo, cuando = "", 0.0
    for carpeta in ("agente", "pruebas"):
        base = c.raiz / carpeta
        if not base.is_dir():
            continue
        for ruta in base.rglob("*.py"):
            if _es_ruido(ruta.parts):
                continue
            try:
                marca = ruta.stat().st_mtime
            except OSError:
                continue
            if marca > cuando:
                nuevo, cuando = c.rel(ruta), marca
    return nuevo, cuando


# Margen para el reloj y para el sistema de archivos. Una corrida que empieza en el mismo segundo
# en el que se guardó el último `.py` no es evidencia de nada raro: es una edición seguida de un
# `pytest`. Lo que se busca es el archivo que quedó días atrás, no el que quedó milisegundos atrás.
SEGUNDOS_DE_HOLGURA = 2.0


def _sin_corrida_detras(c: Contexto, salida: Path) -> tuple[str, str]:
    """Por qué ninguna corrida de este árbol pudo escribir esta salida, con su id. Vacío si sí.

    **El defecto que este reemplazo cierra, y que era peor que el que tapaba.** Acá vivía
    `_copias_del_kit()`, que marcaba `contrato/salida_copiada` cuando el documento de la salida era
    igual al de un fixture de `pruebas/fixtures/`. Sirvió para lo que vino a cerrar —`cp
    pruebas/fixtures/caso-01.salida-esperada.json pruebas/salida-caso-01.json` daba
    `[ok] 1 salida(s) válidas` con `agente/` **ausente** del árbol— y en el camino puso roja la cosa
    equivocada: un revisor construyó el agente, su `pruebas/salida-caso-01.json` —escrito por la
    fixture `salida_caso_01` corriendo `correr_ciclo`— salió igual, documento por documento, al
    archivo que el kit publica como la salida que el agente **tiene que** producir, y el chequeo lo
    marcó. Medido en la misma ronda: cambiando una palabra adentro de un `motivo` —misma conducta,
    la suite igual de verde— el renglón volvía a `[ok]`. O sea que la compuerta premiaba al build
    cuya prosa se apartaba de la referencia y castigaba al que la reproducía, que es exactamente al
    revés de lo que el kit pide.

    **Por qué la igualdad no podía distinguir.** «Lo copió sin correr» y «corrió y le dio bien»
    producen el mismo documento cuando el build es correcto. Ninguna comparación de contenido
    —bytes, documento, o documento con tolerancia— separa esos dos casos, porque el contenido es
    idéntico en los dos por construcción. Lo que los separa es otra cosa: **si hubo una corrida**.

    **Qué evidencia de una corrida tiene la compuerta.** Dos, las dos del árbol y ninguna del
    archivo:

    1. **Que exista quién la escriba.** `pruebas/salida-caso-01.json` lo escribe la fixture de
       sesión `salida_caso_01` de `pruebas/conftest.py`, y esa fixture arranca llamando a
       `correr_turnos(...)`, que sin `agente/ciclo.py` levanta `SinAgente` y saltea. En un árbol sin
       build **ninguna corrida** deja una salida en `pruebas/`: la que esté ahí la puso un editor.
       Ése es el `cp` medido, y sigue rojo.
    2. **Que la corrida sea de este árbol.** La fixture reescribe el archivo **cada vez** que la
       suite corre con el build puesto, así que su mtime se mueve con cada corrida. Una salida más
       vieja que el `.py` más nuevo de `agente/` o de `pruebas/` no la escribió ninguna corrida del
       código que hay hoy en disco. Es la misma regla que `_huella_del_censo` aplica a
       `EVIDENCIA/censo.json`, y por el mismo motivo: la evidencia de una corrida envejece cuando
       el árbol se mueve, y una foto vieja dice que alguien miró un código que ya no está.

    La comparación de la 2 es contra el código y no contra el reloj de pared, a propósito: en un
    árbol que nadie tocó desde la última corrida, `/revisar` de cualquier día sigue en verde.

    **Lo que esto no ve, dicho y no escondido.** Un `cp` hecho recién, en un árbol con el build,
    pasa. No hay forma de distinguirlo mirando el archivo, y lo que lo cierra no es este chequeo
    sino el 19: `pytest pruebas -q -rs` corre en la misma corrida de la compuerta y la fixture
    reescribe `pruebas/salida-caso-01.json` con lo que devolvió el ciclo. O sea que una copia
    sobrevive exactamente una corrida de la compuerta, y la siguiente lee la salida de verdad. Lo
    que se ganó a cambio es que un build que reproduce la referencia —el caso bueno, el que el kit
    pide— deje de salir rojo.
    """
    if not (c.raiz / "agente/ciclo.py").is_file():
        por_que = (
            "no hay `agente/ciclo.py` en el árbol. La escribe la fixture de sesión "
            "`salida_caso_01` de pruebas/conftest.py, que arranca con `correr_turnos(...)` y "
            "sin el build levanta `SinAgente` y saltea: acá ninguna corrida de la suite pudo "
            "escribir una salida, así que ésta la dejó un editor. Un `cp` del fixture del kit "
            "sobre este nombre validaba siempre —es la referencia contra la que se mide— y "
            "ponía en verde el único chequeo que dice «el ciclo corrió una vez»"
        )
        return "contrato/salida_sin_corrida", por_que
    try:
        escrita = salida.stat().st_mtime
    except OSError as e:
        return "contrato/salida_sin_fecha", f"no se pudo leer su fecha: {e}"
    nuevo, cuando = _codigo_que_escribe_la_salida(c)
    if nuevo and cuando - escrita > SEGUNDOS_DE_HOLGURA:
        por_que = (
            f"es más vieja que el código que la produce: `{nuevo}` se guardó "
            f"{_hace_cuanto(cuando - escrita)} después. La fixture `salida_caso_01` reescribe "
            f"este archivo en cada corrida de la suite, así que una salida más vieja que "
            f"`agente/` o `pruebas/` no la escribió ninguna corrida de este árbol: quedó de "
            f"otro código, o la dejó un editor. Corré `pytest pruebas -q` antes de la "
            f"compuerta, que es el orden del paso 8 de blueprint/40-pruebas.md"
        )
        return "contrato/salida_vieja", por_que
    return "", ""


def _hace_cuanto(segundos: float) -> str:
    """`3600.0` → `1 h`. Para que la evidencia diga «días» y no un flotante."""
    if segundos >= 86400:
        return f"{segundos / 86400:.1f} día(s)"
    if segundos >= 3600:
        return f"{segundos / 3600:.1f} h"
    if segundos >= 60:
        return f"{segundos / 60:.1f} min"
    return f"{segundos:.0f} s"


def chequeo_contrato(c: Contexto, r: Reporte) -> None:
    """Las salidas de los fixtures contra el esquema, más la regla que el esquema no dice.

    El esquema fija seis elementos en `pasos` y `n` entre 1 y 6. No dice que sean distintos ni
    que estén ordenados: `[1,1,1,1,1,1]` valida perfecto y no significa nada.

    Y atrás de cada salida tiene que haber una corrida de este árbol. **No** se mira si el
    documento coincide con la referencia del kit: coincidir es lo que hace un build correcto. Ver
    `_sin_corrida_detras`.
    """
    fixtures = _fixtures_de_salida(c)
    if not fixtures:
        r.saltear("todavía no hay fixtures de salida en pruebas/ (`salida*.json`). El control "
                  "negativo, `contrato-control`, corre igual")
        return

    casos: list[tuple[str, dict]] = []
    documentos: dict[str, dict] = {}
    for fixture in fixtures:
        rel = c.rel(fixture)
        id_sin_corrida, por_que = _sin_corrida_detras(c, fixture)
        if id_sin_corrida:
            r.error(id_sin_corrida, por_que, rel, 0, "build")
            continue
        try:
            doc = json.loads(_texto(fixture))
        except json.JSONDecodeError as e:
            r.error("contrato/json_invalido", f"no es JSON válido: {e}", rel, 0, "kit")
            continue
        casos.append((rel, doc))
        documentos[rel] = doc

    if not casos:
        return
    resultados, problema = _validar_documentos(c, casos)
    if resultados is None:
        if "jsonschema" in problema:
            r.saltear("falta jsonschema en este intérprete: sin él el contrato de los seis pasos "
                      "no tiene validador. Corré esto con el `.venv` del proyecto")
            return
        r.error("contrato/no_corrio", problema, "contratos/salida.schema.json", 0, "entorno")
        return

    for rel, errores in resultados.items():
        for e in errores:
            r.error("contrato/no_valida", f"no valida contra salida.schema.json: {e}",
                    rel, 0, "kit")
        enes = [p.get("n") for p in documentos[rel].get("pasos", [])]
        if enes != SEIS_PASOS:
            r.error("contrato/pasos_desordenados",
                    f"`pasos` trae {enes} y tiene que traer {SEIS_PASOS}. El esquema fija seis "
                    f"elementos con `n` entre 1 y 6, pero no dice que sean distintos ni que "
                    f"estén en orden: seis pasos «1» validan y no significan nada",
                    rel, 0, "kit")
    r.decir(f"{len(casos)} salida(s) válidas, con los seis pasos en orden")


# Cinco mutaciones sobre la salida buena. Cada una tiene que ser rechazada por el esquema, y la
# sexta por la regla que el esquema no puede expresar.
def _mutaciones(buena: dict) -> list[tuple[str, dict, str]]:
    import copy

    def clonar() -> dict:
        return copy.deepcopy(buena)

    sin_paso = clonar()
    sin_paso["pasos"] = sin_paso["pasos"][:5]

    score_alto = clonar()
    score_alto["calificacion"]["score"] = 101

    clave_rara = clonar()
    clave_rara["etapa_siguiente"] = "cerrar"

    estado_raro = clonar()
    estado_raro["estado"] = "listo"

    paso_cero = clonar()
    paso_cero["pasos"][0]["n"] = 0

    desordenado = clonar()
    desordenado["pasos"] = [dict(p, n=1) for p in desordenado["pasos"]]

    return [
        ("falta un paso", sin_paso, "esquema"),
        ("score 101", score_alto, "esquema"),
        ("clave desconocida", clave_rara, "esquema"),
        ("estado 'listo'", estado_raro, "esquema"),
        ("paso n=0", paso_cero, "esquema"),
        ("seis pasos con n=1", desordenado, "auditor"),
    ]


def chequeo_contrato_control(c: Contexto, r: Reporte) -> None:
    """El control negativo. Sin esto, «todo verde» no se distingue de «no se está validando nada».

    Un validador mal cableado —el esquema que no carga, el `iter_errors` que nunca se recorre,
    el `additionalProperties` que se perdió en una edición— hace pasar cualquier cosa, y el
    reporte se ve idéntico al de una corrida que sí revisó.
    """
    mutaciones = _mutaciones(SALIDA_BUENA)
    casos = [("buena", SALIDA_BUENA)] + [(n, d) for n, d, _ in mutaciones if _ == "esquema"]
    resultados, problema = _validar_documentos(c, casos)
    if resultados is None:
        if "jsonschema" in problema:
            r.saltear("falta jsonschema en este intérprete: sin él el contrato de los seis pasos "
                      "no tiene validador. Corré esto con el `.venv` del proyecto")
            return
        r.error("control/no_corrio", problema, "contratos/salida.schema.json", 0, "entorno")
        return

    if resultados.get("buena"):
        r.error("control/buena_rechazada",
                f"el esquema rechaza la salida del camino feliz de pruebas/caso-01.md: "
                f"{resultados['buena'][0]}. O el esquema se apretó de más, o la salida esperada "
                f"del caso quedó vieja", "contratos/salida.schema.json", 0, "kit")

    rechazadas = 0
    for nombre, documento, quien in mutaciones:
        if quien == "esquema":
            rechazada = bool(resultados.get(nombre))
        else:
            rechazada = [p.get("n") for p in documento["pasos"]] != SEIS_PASOS
        if rechazada:
            rechazadas += 1
        else:
            r.error("control/mutacion_aceptada",
                    f"la mutación «{nombre}» pasó el validador, y tenía que rebotar. Mientras "
                    f"esto no rebote, un reporte en verde no prueba nada: puede ser que no se "
                    f"esté validando nada", "contratos/salida.schema.json", 0, "kit")
    r.decir(f"{rechazadas}/{len(mutaciones)} mutaciones rechazadas")


# ─────────────────────────────────────────────────────────────────────────────
# 18 · firmas
# ─────────────────────────────────────────────────────────────────────────────

# Los dos fixtures de firma del kit, por nombre y no por `glob`. Uno por proveedor: son las dos
# entregas grabadas, con las cabeceras y el espaciado que mandó cada uno. El eje de la cuenta sale
# de acá para que no se pueda re-anclar borrando un archivo. Ver el docstring del chequeo.
FIXTURES_DE_FIRMA = ("meta", "zernio")


_DRIVER_FIRMAS = r'''
import importlib.util, json, sys

spec = importlib.util.spec_from_file_location("firmas", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
# El registro en sys.modules va ANTES de ejecutarlo, por lo mismo que en el driver del wire
# schema: las anotaciones se resuelven mirando sys.modules[cls.__module__].
sys.modules["firmas"] = mod
spec.loader.exec_module(mod)


def par(cabecera):
    n = cabecera.strip().lower()
    if n == str(getattr(mod, "CABECERA_META", "")).lower():
        return mod.verificar_meta, mod.firmar_meta
    if n == str(getattr(mod, "CABECERA_ZERNIO", "")).lower():
        return mod.verificar_zernio, mod.firmar_zernio
    return None


salida = []
for nombre, ficha_ruta, crudo_ruta in json.loads(sys.stdin.read()):
    ficha = json.load(open(ficha_ruta, encoding="utf-8"))
    # Los bytes se leen acá adentro y no viajan por ningún JSON: el fixture entero es el
    # espaciado torcido, y un round trip por otro formato es exactamente lo que lo borra.
    crudo = open(crudo_ruta, "rb").read()
    cabecera = str(ficha.get("cabecera", ""))
    dupla = par(cabecera)
    if dupla is None:
        salida.append([nombre, {"cabecera": cabecera}])
        continue
    verificar, firmar = dupla
    secreto, firma = ficha.get("secreto", ""), ficha.get("firma", "")
    try:
        reserializado = json.dumps(json.loads(crudo)).encode("utf-8")
    except Exception:
        reserializado = None
    try:
        salida.append([nombre, {
            "no_reproduce": firmar(crudo, secreto=secreto) != firma,
            "valida_no_pasa": not verificar(crudo, cabecera=firma, secreto=secreto),
            "alterado_pasa": bool(verificar(crudo + b" ", cabecera=firma, secreto=secreto)),
            "reserializa": bool(reserializado is not None and verificar(
                reserializado, cabecera=firma, secreto=secreto)),
        }])
    except Exception as e:
        salida.append([nombre, {"levanto": "%s: %s" % (type(e).__name__, e)}])
print(json.dumps({"resultados": salida}, ensure_ascii=False))
'''


def chequeo_firmas(c: Contexto, r: Reporte) -> None:
    """Los fixtures crudos, con el espaciado torcido intacto.

    Tres casos por fixture, y el que importa es el tercero. Los `.raw` traen sangrías que no son
    múltiplos de nada, un tabulador, y la misma vocal escapada de dos formas en el mismo cuerpo.
    Ninguna combinación de banderas de `json.dumps` devuelve esos bytes, así que una
    implementación que reserialice el cuerpo **no puede** reproducir el MAC.

    Corre en subproceso, con timeout y sin credenciales, igual que `wire-schema` y `contrato`.
    Este es el único chequeo que ejecuta código del proyecto, y uno de los dos archivos que
    ejecuta —`agente/firmas.py`— lo escribió la construcción, no nosotros. Importarlo en el
    proceso de la compuerta le daba el `os.environ` entero y todo el tiempo del mundo: un
    `input()` o un `time.sleep(3600)` arriba de ese archivo colgaba `/revisar` para siempre, que
    es el modo de falla que este script entero existe para no tener.

    **Cuántas comprobaciones tienen que correr está fijado, y si corren menos es error.** El
    número es `fixtures × módulos`, y el chequeo lo dice entero: «4 de 4». Antes sólo se imprimía
    el que había salido, así que el día que dejó de poder ejecutarse `agente/firmas.py` la línea
    bajó de `4 comprobación(es)` a `2` y el chequeo siguió en `[ok]`: la mitad de las
    comprobaciones apagada, el mismo verde, y nada que leer salvo un número más chico que nadie
    tenía contra qué comparar. Media suite que no corre no es media suite que pasa.

    **Y el eje de los fixtures está anclado, que era la mitad que faltaba.** `esperadas` se
    calculaba como `len(casos) × len(módulos)` con `casos` armado por `glob`, así que el «N de N»
    se re-anclaba solo: borrando `zernio.meta.json` la línea pasaba a «2 de 2» y seguía en verde,
    y borrando los dos pares el chequeo salteaba entero. Los dos nombres están escritos abajo, en
    `FIXTURES_DE_FIRMA`, y son parte del núcleo verbatim: si uno no está, no es que haya menos que
    comprobar, es que falta un archivo del kit. Lo que alguien agregue de más se suma al eje.
    """
    carpeta = c.raiz / "pruebas/fixtures"
    presentes = sorted(carpeta.glob("*.meta.json")) if carpeta.is_dir() else []
    nombres = [p.name[: -len(".meta.json")] for p in presentes]
    for nombre in FIXTURES_DE_FIRMA:
        if nombre in nombres:
            continue
        r.error("firmas/fixture_ausente",
                f"falta `pruebas/fixtures/{nombre}.meta.json` y su `.raw`. Es núcleo verbatim del "
                f"kit: la entrega grabada de {nombre}, con el espaciado torcido que hace que una "
                f"implementación que reserializa el cuerpo no pueda reproducir el MAC. Sin ese par "
                f"no hay menos que comprobar: hay una mitad del invariante 1 sin comprobar",
                f"pruebas/fixtures/{nombre}.meta.json", 0, "kit")
    extras = [p for p in presentes if p.name[: -len(".meta.json")] not in FIXTURES_DE_FIRMA]
    fixtures = [p for p in presentes if p.name[: -len(".meta.json")] in FIXTURES_DE_FIRMA] + extras
    eje = len(FIXTURES_DE_FIRMA) + len(extras)

    # Cuáles TIENEN que correr, no cuáles están. La lista de antes filtraba por `is_file()` y ahí
    # se iba el chequeo: sin `agente/firmas.py` en disco, ese módulo desaparecía de la cuenta sin
    # un hallazgo y la línea pasaba de `4 comprobación(es)` a `2`, en verde. La plantilla está
    # siempre —es del kit—; la copia del build está en cuanto `agente/` está.
    esperados = [c.raiz / "plantillas/seguridad/firmas.py"]
    if c.hay_agente:
        esperados.append(c.agente / "firmas.py")
    modulos = [p for p in esperados if p.is_file()]
    if c.build_derivado:
        # El chequeo del manifiesto ya dijo que un archivo generado no coincide con su plantilla.
        # Cuál se apartó no se sabe acá, y ejecutar el de `agente/` con esa duda encima es
        # ejecutar un archivo que acabamos de probar que no es el que enviamos. Se prueba la
        # plantilla, que sí está hasheada.
        # `esperados` NO se toca acá: lo que no se corre queda contado como lo que no se corrió.
        # Bajarle el número esperado a la corrida es la forma exacta en que este chequeo se apagó
        # solo la vez pasada.
        generado = (c.agente / "firmas.py").resolve()
        modulos = [p for p in modulos if p.resolve() != generado]
        r.aviso("firmas/build_derivado",
                "no ejecuté agente/firmas.py: el manifiesto dice que algún archivo generado se "
                "apartó de su plantilla, y un archivo que no es el que enviamos no se corre. "
                "Copiá la plantilla otra vez y volvé a correr esto", "agente/firmas.py", 0, "build")
    if not modulos:
        r.saltear("no encuentro firmas.py ni en plantillas/seguridad/ ni en agente/")
        return

    casos: list[list[str]] = []
    donde: dict[str, tuple[str, str]] = {}
    for ficha_json in fixtures:
        nombre = ficha_json.name[: -len(".meta.json")]
        crudo_path = ficha_json.with_name(f"{nombre}.raw")
        if not crudo_path.is_file():
            r.error("firmas/sin_crudo", f"la ficha {ficha_json.name} no tiene su `.raw` al "
                    "lado", c.rel(ficha_json), 0, "kit")
            continue
        try:
            json.loads(_texto(ficha_json))
        except json.JSONDecodeError as e:
            r.error("firmas/ficha_ilegible", f"{e}", c.rel(ficha_json), 0, "kit")
            continue
        casos.append([nombre, str(ficha_json), str(crudo_path)])
        donde[nombre] = (c.rel(ficha_json), c.rel(crudo_path))
    if not casos:
        r.error("firmas/sin_fixtures",
                f"no quedó un solo par `.meta.json` + `.raw` que correr en pruebas/fixtures/. El "
                f"eje son {eje}, y con cero corridas este chequeo no dice nada sobre el invariante "
                f"1: el cuerpo crudo se verifica tal como llegó", "pruebas/fixtures", 0, "kit")
        return

    corridos = 0
    for ruta in modulos:
        rel = c.rel(ruta)
        codigo, salida = _correr([c.interprete, "-c", _DRIVER_FIRMAS, str(ruta)], cwd=c.raiz,
                                 entrada=json.dumps(casos, ensure_ascii=False))
        if codigo == 124:
            r.error("firmas/colgado",
                    f"importarlo no termina y lo corté a los {SEGUNDOS_CORTO} s: algo corre al "
                    f"importar este archivo y se queda esperando. Adentro de `/revisar` eso "
                    f"cuelga la skill entera y no hay reporte, que es peor que cualquier "
                    f"hallazgo", rel, 0, "build")
            continue
        if codigo != 0:
            r.error("firmas/no_importa",
                    f"el subproceso que importa este módulo y firma con él salió con {codigo}: "
                    f"{_recorte(salida)}", rel, 0, "kit")
            continue
        try:
            datos = json.loads(salida.splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            r.error("firmas/salida_ilegible",
                    f"el driver devolvió algo que no es JSON: {_recorte(salida)}",
                    rel, 0, "entorno")
            continue

        for nombre, res in datos["resultados"]:
            ficha_rel, crudo_rel = donde.get(nombre, (rel, nombre))
            etiqueta = f"{nombre} · {crudo_rel}"
            if "cabecera" in res:
                r.error("firmas/cabecera_desconocida",
                        f"la ficha dice `{res['cabecera']}` y no sé qué proveedor es",
                        ficha_rel, 0, "kit")
                continue
            if "levanto" in res:
                r.error("firmas/levanto",
                        f"{etiqueta}: firmar o verificar levantó {res['levanto']}. Un cuerpo que "
                        f"llega y hace reventar la verificación es un 500 en el webhook",
                        rel, 0, "kit")
                continue
            corridos += 1
            if res["no_reproduce"]:
                r.error("firmas/no_reproduce",
                        f"{etiqueta}: la firma guardada no es la de estos bytes. O el `.raw` se "
                        f"tocó, o el módulo firma distinto", rel, 0, "kit")
            if res["valida_no_pasa"]:
                r.error("firmas/valida_no_pasa",
                        f"{etiqueta}: el cuerpo correcto con su firma correcta da inválido",
                        rel, 0, "kit")
            if res["alterado_pasa"]:
                r.error("firmas/alterado_pasa",
                        f"{etiqueta}: un cuerpo alterado con la misma cabecera da VÁLIDO. Eso es "
                        f"cualquiera escribiéndole a tu número", rel, 0, "kit")
            if res["reserializa"]:
                r.error("firmas/reserializa",
                        f"{etiqueta}: el cuerpo REserializado valida contra la firma del cuerpo "
                        f"crudo. O el fixture perdió el espaciado torcido —y quedó inerte—, o la "
                        f"verificación no está mirando los bytes que llegaron. Las dos cosas "
                        f"devuelven 401 en el 100% de las entregas reales", rel, 0, "kit")

    esperadas = eje * len(esperados)
    if corridos < esperadas:
        ausentes = [c.rel(p) for p in esperados if not p.is_file()]
        salteados = [c.rel(p) for p in esperados if p.is_file() and p not in modulos]
        if ausentes:
            detalle = f" No está en disco: {', '.join(ausentes)}."
        elif salteados:
            detalle = f" No lo corrí, y arriba está por qué: {', '.join(salteados)}."
        else:
            detalle = " Están los dos archivos, así que se cayeron corriendo: el motivo está arriba."
        r.error("firmas/faltan_comprobaciones",
                f"corrieron {corridos} de {esperadas} comprobaciones: faltaron "
                f"{esperadas - corridos}. Son {eje} fixture(s) por {len(esperados)} "
                f"módulo(s) ({', '.join(c.rel(p) for p in esperados)}), y cada par tiene que dar "
                f"sus cuatro respuestas.{detalle} Lo que no corrió no pasó, y media suite apagada "
                f"salía igual de verde que la entera",
                "pruebas/fixtures", 0, "kit")
    r.decir(f"{corridos} de {esperadas} comprobación(es): {eje} fixture(s) × "
            f"{len(esperados)} módulo(s)")


# ─────────────────────────────────────────────────────────────────────────────
# 19 · pruebas
# ─────────────────────────────────────────────────────────────────────────────

# Cómo imprime pytest un salteo con `-rs`: `SKIPPED [12] pruebas/test_x.py:33: el motivo`.
#
# **El número de línea es opcional, y esa es una corrección y no un detalle.** Un
# `pytestmark = pytest.mark.skip(...)` de módulo entero —la forma más barata de apagar un archivo
# de pruebas— imprime `SKIPPED [12] pruebas/test_x.py: el motivo`, sin línea, y con `:\d+`
# obligatorio esa salida no matcheaba una sola vez. El chequeo se ponía rojo igual, por
# `salteos_sin_motivo`, o sea rojo por accidente y con el hallazgo equivocado: quien apagaba la
# suite entera de un renglón leía «no pude leer el motivo» en vez de «esto no probó nada».
SALTEO_DE_PYTEST = re.compile(r"^SKIPPED\s+\[(\d+)\]\s+([^\s:]+(?::\d+)?):\s*(.*)$")
RESUMEN_SALTEADOS = re.compile(r"(\d+)\s+skipped")
RESUMEN_PASADOS = re.compile(r"(\d+)\s+passed")

# El piso de nodos que tienen que pasar. Este árbol, sin `agente/` y sin una sola credencial, da 49
# —`pytest pruebas -q` lo imprime; eran 45 antes de las dos tandas de esta ronda—, y con el build en
# el árbol sólo puede subir: los que hoy saltean por «falta el build» pasan a correr. El piso está
# bien abajo de esos 49 a propósito: no mide la suite, mide que la suite exista. Sin él,
# `0 passed, 2 skipped` es una corrida en verde, y ese es el estado exacto de un árbol al que le
# borraron `pruebas/` y le dejaron dos nodos apagados.
#
# **Lo que este número no mide, dicho y no escondido.** Un build entero da 217 en esta ronda —daba
# 176—; el piso en 30 deja tirar ciento ochenta y siete nodos sin que la compuerta se mueva, así que
# no es una vara de nada
# —es un detector de suite ausente, y ése es todo su trabajo—. Subirlo a un número parecido al real
# es la pelea que este kit ya perdió tres veces: el total depende del árbol (con build y sin build
# son dos números distintos) y de la parametrización, así que un piso alto pone en rojo el build de
# quien construye por una cuenta nuestra. Lo que sí es una vara, porque es una lista y no una suma,
# es `ARCHIVOS_DE_PRUEBA`, acá abajo.
PISO_DE_NODOS = 30

# Los archivos de prueba del kit, por nombre. `blueprint/40-pruebas.md` paso 8 los llama «la lista
# de archivos» y agrega, con todas las letras, que ésa es la afirmación que no es un número. Era
# también la afirmación que ningún chequeo hacía.
#
# **La lista sale de `ls pruebas/test_*.py`, no de la prosa ni de esta ronda.** Fueron siete, después
# ocho con `test_camino_feliz.py`, después nueve con `test_modelo.py`, después diez con
# `test_bandeja.py`, y hoy son once: `test_campos.py`, el que afirma los nueve campos del contrato
# de salida que nadie afirmaba y que vaciaron `SIN_ASERCION`. Los dos últimos entraron acá con el
# aviso puesto —`pruebas/archivo_sin_exigir`, que es el que existe para que la lista no envejezca
# sola—: se agregó el archivo, saltó el aviso, y el renglón entró con el mismo commit.
#
# **Y ya no envejece sola en la dirección barata.** Era la cuarta cosa de este kit que se mantenía a
# mano, y dos rondas seguidas se agregó un archivo de prueba sin agregar el renglón. Ahora
# `_exigir_los_archivos_de_prueba()` mira las dos direcciones: la que falta es error —eso no
# cambió—, y el `test_*.py` que está en el disco y no en esta tupla sale como **aviso**, con el
# nombre. Aviso y no error a propósito: agregar una prueba es lo correcto, y poner en rojo a quien
# la agrega es enseñar a no agregarla. Lo que el aviso dice es que ese archivo hoy se puede borrar
# sin que nada se mueva, y que el renglón va acá con el mismo commit.
#
# **Qué tapaba.** Rompiendo la comparación del token del panel **y borrando `pruebas/test_panel.py`**
# el árbol vuelve a dar `159 passed · auditar: PASS · 0 errores · 0 avisos · 0 salteados`. La
# regresión que el chequeo 21 `panel-cerrado` vino a cerrar se reabre borrando un archivo: el
# chequeo 14 pide `pruebas/*.py` con un glob y con seis archivos el glob matchea igual, el 19 corre
# la suite que quedó y `159 passed` no se distingue de `176 passed` sin un número al lado. Un
# archivo de prueba borrado no baja ningún chequeo a rojo, y es la forma más barata que hay de
# apagar una verificación entera.
#
# **Por qué la lista vive acá y no se lee de la prosa.** Por lo mismo que `PISO_DE_MODULOS`: una
# vara que escribe el auditado no es una vara. La prosa de `blueprint/40-pruebas.md` se puede
# editar desde adentro de la construcción; esto no.
#
# Se piden por nombre y con algo escrito adentro. Un archivo de cero bytes colecciona cero nodos y
# no lo reporta nadie: pytest no falla, el total baja y el desglose por archivo lo mira una persona.
ARCHIVOS_DE_PRUEBA = (
    "test_bandeja.py",
    "test_campos.py",
    "test_camino_feliz.py",
    "test_caso_01.py",
    "test_caso_02.py",
    "test_contrato.py",
    "test_enviar.py",
    "test_firmas.py",
    "test_idempotencia.py",
    "test_modelo.py",
    "test_panel.py",
)

# El techo de salteos «sólo en vivo», y lo que cada uno tiene que nombrar.
#
# `sólo en vivo` era el único motivo que no pesaba nunca y no se gateaba contra nada: cambiándole el
# motivo a los 109 salteos de este árbol, el chequeo pasaba de rojo a `[ok]` con la suite entera
# apagada. Ahora un salteo en vivo tiene que decir **qué** le falta, y la lista es cerrada: son las
# credenciales de `env.example`, que es la única razón legítima para que algo viva en `/probar` y no
# acá. Inventar un marcador nuevo es editar esta tupla, que se lee en el diff.
#
# Y hay techo, porque la lista sola se falsifica igual pegándole `WHATSAPP_TOKEN` a cien motivos: en
# `/probar` viven un puñado de nodos —el envío real, el alta del webhook, el calendario y el CRM
# contra la cuenta de verdad—, no una suite entera. Con más que esto, lo que hay no es una suite con
# excepciones: es una suite apagada con una excusa.
MARCADORES_EN_VIVO = (
    "ANTHROPIC_API_KEY", "WHATSAPP_TOKEN", "WHATSAPP_VERIFY_TOKEN", "META_APP_SECRET",
    "ZERNIO_API_KEY", "ZERNIO_WEBHOOK_SECRET", "ZERNIO_ACCOUNT_ID", "GOOGLE_CALENDAR_ID",
    "GOOGLE_SERVICE_ACCOUNT_JSON", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "OPENAI_API_KEY",
    "SLACK_WEBHOOK_URL",
)
TECHO_EN_VIVO = 8

# Los dos motivos que un salteo puede declarar, y no hay un tercero.
#
# `sólo en vivo` es el único que no pesa nunca: la prueba necesita una credencial de verdad o red,
# y eso vive en `/probar` por diseño —el docstring de este chequeo lo dice desde el primer día—.
#
# `falta el build` pesa según el árbol: mientras `agente/` no exista es lo correcto y se dice como
# aviso; con `agente/` en el árbol es error, porque quiere decir que el build está a medias y que
# la suite en verde no probó una sola línea de él.
SALTEO_SIN_BUILD = re.compile(
    r"(?i)(falta el build|no existe agente|todavía no existe agente|no hay agente/|"
    r"cuando `?agente/`? existe|todavía no hay salidas escritas)")
SALTEO_EN_VIVO = re.compile(
    r"(?i)(sólo en vivo|solo en vivo|only live|necesita una credencial|credencial de verdad|"
    r"va en /probar|esto va a /probar)")


def _contar_salteados(c: Contexto, r: Reporte, salida: str) -> str:
    """Los salteos de la suite, clasificados por lo que declaran. Ver el docstring de arriba.

    `44 passed, 100 skipped` salía como `[ok]` y como una sola línea de resumen. Contar es la
    mitad del trabajo; la otra mitad es leer el motivo, porque los tres casos —en vivo, falta el
    build, y no declara nada— no valen lo mismo y no se distinguen por el número.
    """
    total = 0
    for linea in salida.splitlines():
        m = RESUMEN_SALTEADOS.search(linea)
        if m:
            total = int(m.group(1))
    if not total:
        return "0 salteados"

    en_vivo, sin_build, mudos = 0, 0, []
    leidos = 0
    for linea in salida.splitlines():
        m = SALTEO_DE_PYTEST.match(linea.strip())
        if not m:
            continue
        cuantos, donde, motivo = int(m.group(1)), m.group(2), m.group(3)
        leidos += cuantos
        if SALTEO_SIN_BUILD.search(motivo):
            sin_build += cuantos
        elif SALTEO_EN_VIVO.search(motivo):
            en_vivo += cuantos
            if not any(marca in motivo for marca in MARCADORES_EN_VIVO):
                r.error("pruebas/en_vivo_sin_marcador",
                        f"{cuantos} nodo(s) saltean en {donde} diciendo que son «sólo en vivo» y "
                        f"no nombran qué les falta: «{_recorte(motivo, 160)}». El motivo tiene que "
                        f"traer la variable de `env.example` que necesitan —"
                        f"{', '.join(MARCADORES_EN_VIVO[:3])}, …—, y la lista está en "
                        f"`MARCADORES_EN_VIVO`. Sin eso, «sólo en vivo» es la frase con la que se "
                        f"apaga la suite entera sin que nada se ponga rojo: es el único motivo que "
                        f"no pesa, así que es el único que hay que poder verificar",
                        "pruebas", 0, "kit")
        else:
            mudos.append((cuantos, donde, motivo))

    if en_vivo > TECHO_EN_VIVO:
        r.error("pruebas/en_vivo_de_mas",
                f"{en_vivo} nodo(s) saltean por «sólo en vivo» y el techo es {TECHO_EN_VIVO}. En "
                f"`/probar` viven un puñado de nodos —el envío real, el alta del webhook, el "
                f"calendario y el CRM contra la cuenta de verdad—, no una suite. Con este número, "
                f"lo que hay no es una suite con excepciones: es una suite apagada con una excusa, "
                f"y como «sólo en vivo» es el motivo que no pesa, sin techo esto salía `[ok]`",
                "pruebas", 0, "kit")

    if leidos < total:
        r.error("pruebas/salteos_sin_motivo",
                f"pytest declara {total} salteado(s) y sólo pude leer el motivo de {leidos}. Sin "
                f"el motivo no se puede decir si lo que no corrió era `sólo en vivo` o era la "
                f"suite entera esperando un build que no está", "pruebas", 0, "kit")

    for cuantos, donde, motivo in mudos:
        r.error("pruebas/salteo_no_declarado",
                f"{cuantos} nodo(s) saltean en {donde} sin declarar por qué: «{_recorte(motivo, 160)}». "
                f"El único salteo que no pesa es el que dice `sólo en vivo` —ése se fue a "
                f"/probar—; cualquier otro es una prueba que no probó nada y nadie lo va a leer "
                f"en un `[ok]`", "pruebas", 0, "kit")

    if sin_build and c.hay_agente:
        r.error("pruebas/salteados_con_build",
                f"{sin_build} de {total} salteado(s) dicen que falta el build, y `agente/` está en "
                f"el árbol. O sea: la construcción corrió, la suite salió verde y esos nodos no "
                f"probaron una sola línea del build. Un `[ok] {total - sin_build} passed` con esto "
                f"adentro es la corrida en la que menos hay que confiar: mirá `agente-completo`, "
                f"que dice qué módulo falta", "pruebas", 0, "build")
    elif sin_build:
        r.aviso("pruebas/salteados_sin_build",
                f"{sin_build} de {total} salteado(s) esperan el build y `agente/` todavía no "
                f"existe: correcto por ahora, y aviso y no error por eso mismo. En cuanto "
                f"`agente/` esté en el árbol, cada uno de estos {sin_build} es un error",
                "pruebas", 0, "build")
    return (f"{total} salteado(s): {en_vivo} sólo en vivo, {sin_build} esperando el build, "
            f"{sum(n for n, _, _ in mudos)} sin declarar")


def _exigir_los_archivos_de_prueba(c: Contexto, r: Reporte) -> None:
    """Los de `ARCHIVOS_DE_PRUEBA`, por nombre y con algo escrito adentro, y la cuenta al revés.

    `atribuible_a` es `kit`: estos archivos llegan con el `git clone` y quien construye no los
    escribe —`blueprint/40-pruebas.md` lo dice así: «vos no agregás pruebas en esta fase, las ponés
    en verde»—. Si falta uno, o alguien lo borró o el clone quedó a medias, y en los dos casos lo
    que hay que leer no es «arreglá tu build».

    La otra dirección es la que hacía envejecer la lista sola: un `test_*.py` que está en el disco y
    no en la tupla no lo exige nadie, así que borrarlo mañana no cuesta un solo error. Sale como
    aviso y con el nombre. No es error porque agregar una prueba es lo correcto y ponerse rojo por
    eso enseña a no agregarla; lo que el aviso pide es el renglón en `ARCHIVOS_DE_PRUEBA`, con el
    mismo commit.
    """
    carpeta = c.raiz / "pruebas"
    sueltos = sorted(p.name for p in carpeta.glob("test_*.py")
                     if p.is_file() and p.name not in ARCHIVOS_DE_PRUEBA)
    if sueltos:
        r.aviso("pruebas/archivo_sin_exigir",
                f"{len(sueltos)} archivo(s) de prueba en el disco que la compuerta no exige: "
                f"{', '.join(sueltos)}. Hoy se pueden borrar y ningún chequeo se mueve, que es "
                f"exactamente el agujero que `ARCHIVOS_DE_PRUEBA` vino a cerrar para los otros "
                f"{len(ARCHIVOS_DE_PRUEBA)}. Si vino con el kit, el renglón va en esa tupla, en "
                f"scripts/auditar.py, con el mismo commit que trajo el archivo; si lo escribiste "
                f"vos para tu build, dejalo y sabé que la vara no lo cuida",
                "pruebas", 0, "kit")
    faltan = [n for n in ARCHIVOS_DE_PRUEBA
              if not (carpeta / n).is_file() or _tamano(carpeta / n) == 0]
    if not faltan:
        return
    r.error("pruebas/archivo_de_la_suite",
            f"faltan {len(faltan)} de los {len(ARCHIVOS_DE_PRUEBA)} archivos de la suite: "
            f"{', '.join(faltan)}. No son tuyos: llegan con el `git clone` y esta fase los pone en "
            f"verde, no los escribe. Borrar uno es la forma más barata de apagar una verificación "
            f"entera sin que nada se ponga rojo —medido: rompiendo la comparación del token del "
            f"panel y borrando `pruebas/test_panel.py`, el árbol da `159 passed` y "
            f"`auditar: PASS · 0 errores · 0 avisos · 0 salteados`, con `GET /api/leads` sin token "
            f"devolviendo la tabla del CRM—. El glob `pruebas/*.py` del chequeo 14 no lo ve: con "
            f"seis archivos matchea igual. Recuperalos con `git checkout -- pruebas/`; la lista "
            f"está en blueprint/40-pruebas.md paso 8 y la vara en `ARCHIVOS_DE_PRUEBA`",
            "pruebas", 0, "kit")


def chequeo_pruebas(c: Contexto, r: Reporte) -> None:
    """La suite, con el mismo entorno sin credenciales que todo lo demás de este archivo.

    No es un descuido: `pruebas/caso-01.md` dice que el caso corre sin `${WHATSAPP_TOKEN}`, sin
    `${GOOGLE_CALENDAR_ID}` y sin `${SUPABASE_URL}`, a propósito. Lo que se mide es la llamada
    que el agente prepara, no la respuesta del servicio. Una prueba que necesite una credencial
    de verdad va en `/probar`, que corre cuando vos querés y puede tardar lo que quiera.

    Ese último renglón era prosa y ahora es regla, porque mirando sólo `codigo == 0` la línea de
    este chequeo llegó a decir `[ok] 18 pruebas · 44 passed, 100 skipped`: ciento de ciento
    cuarenta y cuatro nodos no corrieron y el veredicto no se movió. Un salteo por «falta el
    build» es legítimo mientras `agente/` no exista y deja de serlo en cuanto existe: ahí quiere
    decir que el build está a medias y que la suite en verde no probó nada de él, que es
    exactamente el árbol contra el que esta compuerta tiene que ponerse roja. El único salteo que
    no pesa nunca es el declarado **sólo en vivo**, que es el que se fue a `/probar` por diseño.

    Se corre con `-rs` para que pytest imprima el motivo de cada salteo: sin el motivo no hay
    forma de distinguir los tres casos, y un salteo sin motivo es el cuarto —y es error, porque
    nadie puede decir qué dejó de probarse—.

    **Tres números que no salen de la corrida**, porque un número que la corrida elige no es una
    vara: el piso de nodos que pasan (`PISO_DE_NODOS`), el techo de salteos en vivo
    (`TECHO_EN_VIVO`) y la lista cerrada de lo que un salteo en vivo tiene que nombrar
    (`MARCADORES_EN_VIVO`). Los tres existen por el mismo agujero: `sólo en vivo` era el único
    motivo que no pesaba, así que cambiarle el motivo a los salteos llevaba este chequeo de rojo a
    `[ok]` con la suite entera apagada, y `0 passed` no lo notaba nadie.

    **Y un cuarto, que es una lista y no un número: `ARCHIVOS_DE_PRUEBA`.** Los tres de arriba
    miran la corrida, y la corrida no puede decir qué no corrió porque no está: un `pruebas/`
    al que le falta un archivo colecciona menos nodos, pasa todos los que quedan y sale
    `[ok]`. Se verifica antes de correr nada, porque es lo único que sigue siendo cierto cuando la
    suite se cuelga o revienta.
    """
    carpeta = c.raiz / "pruebas"
    _exigir_los_archivos_de_prueba(c, r)
    if not carpeta.is_dir() or not list(carpeta.rglob("test_*.py")):
        r.saltear("no hay pruebas/test_*.py todavía")
        return
    codigo, salida = _correr([c.interprete, "-m", "pytest", "pruebas", "-q", "-rs"],
                             cwd=c.raiz, timeout=SEGUNDOS_PRUEBAS)
    cola = "\n".join(salida.splitlines()[-12:])
    if codigo == 0:
        detalle = _contar_salteados(c, r, salida)
        pasados = 0
        for linea in salida.splitlines():
            m = RESUMEN_PASADOS.search(linea)
            if m:
                pasados = int(m.group(1))
        if pasados < PISO_DE_NODOS:
            r.error("pruebas/piso_de_nodos",
                    f"pasaron {pasados} nodo(s) y el piso es {PISO_DE_NODOS}. Este mismo árbol sin "
                    f"`agente/` y sin una sola credencial da 49, y con el build sólo puede subir: "
                    f"un número abajo del piso quiere decir que la suite no está entera, no que "
                    f"esta corrida fue chica. `pytest pruebas --collect-only -q` dice cuántos "
                    f"nodos hay; el resto lo dice el motivo de cada salteo, arriba",
                    "pruebas", 0, "build")
        resumen = _recorte(salida.splitlines()[-1] if salida else "", 90)
        r.decir(f"{resumen} · {detalle} · piso: {pasados} de {PISO_DE_NODOS}")
        return
    if codigo == 5:
        r.aviso("pruebas/vacias", "pytest no encontró ninguna prueba que correr", "pruebas", 0, "kit")
        return
    if "No module named pytest" in salida:
        r.saltear("falta pytest en este intérprete: corré esto con el `.venv` del proyecto")
        return
    if codigo == 124:
        r.error("pruebas/colgadas",
                f"{salida}. Una suite que tarda más de {SEGUNDOS_PRUEBAS} s no entra en la "
                f"compuerta: lo lento va a /probar", "pruebas", 0, "build")
        return
    r.error("pruebas/fallan", _recorte(cola, 600), "pruebas", 0, "build")


# ─────────────────────────────────────────────────────────────────────────────
# 20 · playbook
# ─────────────────────────────────────────────────────────────────────────────

PLAYBOOK = "config/playbook.yaml"

# Las dos claves fijas del piso. Ver `blueprint/25-playbook.md`: no son contenido opcional, son la
# regla de no inventar escrita como copy. El simulador de la fase 5 trae al que pide descuento
# prearmado, y un playbook sin el piso llega ahí sin nada que contestarle.
CLAVES_DEL_PISO = ("descuento", "garantia")

# El mismo trabajo que hace el heredoc del paso 9 de `blueprint/25-playbook.md`, con la misma
# forma y —esto es lo que faltaba— con las mismas quince líneas: `SENTIDO` y `habla_de()`.
#
# Sin ellas, el piso se contaba preguntando `decl.get(clave) in textos`, o sea «la clave apunta a
# una objeción que existe», y eso se falsifica en dos renglones. Medido contra los mismos cuatro
# fixtures, un playbook de dos objeciones —«Ahora no tengo un minuto» y «Mandame informacion»— con
# el piso apuntando a esas dos salía `pass · piso: 2 de 2` sin contestar ni un descuento ni una
# garantía: la compuerta que vino a mecanizar el heredoc era más débil que el heredoc.
#
# `SENTIDO` es qué hace que una objeción SEA la del descuento o la de la garantía, escrita con las
# palabras que sean. No es la palabra de la clave: «¿Me podés hacer un precio mejor?» es la del
# descuento y no dice «descuento» en ningún lado, y por eso el piso se cuenta por la clave y nunca
# buscando la palabra adentro del texto. «caro» no está en la lista a propósito: «Está caro» es otra
# de las ocho objeciones del base, y anclarla en `piso` era justo la línea que daba `2 de 2` con el
# piso vacío.
#
# **`SENTIDO` se pregunta sobre `objecion` y sobre nada más.** Preguntarlo sobre
# `objecion + " " + respuesta` —que es como estaba— deja la misma falsificación de antes con dos
# palabras más de trabajo, porque la respuesta la escribe la misma persona y ahí la palabra entra
# gratis, incluso negando lo que nombra. Medido, con este playbook entero:
#
#     - objecion: "Ahora no tengo un minuto"
#       respuesta: "Te escribo mañana. Acá no hacemos descuento por apuro."
#     - objecion: "Mandame informacion"
#       respuesta: "Te la mando. Garantia de respuesta en el dia."
#     piso: {descuento: "Ahora no tengo un minuto", garantia: "Mandame informacion"}
#
# daba `[ok] 20 playbook  2 objeciones · piso: 2 de 2 · huecos: ninguno` y la corrida `PASS`, con el
# agente sin una sola línea para contestar un descuento. Sobre `objecion` sola, las dos salen
# `playbook/piso_no_habla`.
#
# Y no es un recorte que agregue falsos rojos: `SENTIDO` ya estaba escrita contra la forma de la
# objeción y no contra la de la respuesta. Los dos ejemplos con los que el paso 9 de
# `blueprint/25-playbook.md` justifica la lista —«¿Me podés hacer un precio mejor?» y «¿Y si no me
# sirve? ¿Me devuelven la plata?»— matchean por el `objecion` solo, sin mirar una palabra de lo que
# se contesta.
#
# Corre en subproceso como todo lo que necesita una dependencia, sin red y sin credenciales.
_DRIVER_PLAYBOOK = r'''
import json, re, sys, unicodedata
import yaml

CLAVES = ("descuento", "garantia")
SENTIDO = {
    "descuento": ("descuent", "rebaj", "promo", "oferta", "cupon", "mas barato",
                  "precio mejor", "mejor precio", "bajar el precio", "precio especial"),
    "garantia": ("garant", "devuelv", "devolucion", "reembols", "no me sirve",
                 "no me funciona", "si no sirve", "si no funciona", "de vuelta"),
}


def plano(texto):
    """Minusculas y sin tildes: «garantia» y «garantia» son la misma palabra."""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower())
                   if not unicodedata.combining(c))


def habla_de(texto, clave):
    return any(marca in texto for marca in SENTIDO[clave])


crudo = open(sys.argv[1], encoding="utf-8").read()
cfg = yaml.safe_load(crudo) or {}
frag = json.load(open(sys.argv[2], encoding="utf-8"))["properties"]["playbook"]

salida = {"errores": [], "objeciones": 0, "piso": [], "sacadas": [], "sueltas": [], "colgadas": [],
          "mudas": [], "vacias": [], "sin_bloque": False,
          "huecos": sorted(set(re.findall(r"\{[a-z_0-9]+\}", crudo)))}
bloque = cfg.get("playbook")
if not isinstance(bloque, dict):
    salida["errores"].append("no hay un bloque `playbook:` adentro del archivo")
else:
    try:
        import jsonschema
        for e in jsonschema.Draft202012Validator(frag).iter_errors(bloque):
            ruta = "/".join(str(p) for p in e.absolute_path) or "#"
            salida["errores"].append("%s: %s" % (ruta, e.message))
    except ImportError:
        salida["sin_jsonschema"] = True
    objs = [o for o in (bloque.get("objeciones") or []) if isinstance(o, dict)]
    salida["objeciones"] = len(objs)
    # Sobre `objecion` y nada más: es lo que el piso ancla, y es lo único que la persona no puede
    # reescribir sin cambiar cuál es la objeción. Ver el comentario de `SENTIDO`, arriba.
    textos = {o.get("objecion"): plano(str(o.get("objecion", ""))) for o in objs}
    # Lo único de la respuesta que una regla estática puede decidir: que haya algo escrito.
    dichas = {o.get("objecion"): str(o.get("respuesta") or "").strip() for o in objs}
    crudo_piso = cfg.get("piso")
    salida["sin_bloque"] = not isinstance(crudo_piso, dict)
    decl = crudo_piso if isinstance(crudo_piso, dict) else {}
    for clave in CLAVES:
        anclada = decl.get(clave)
        if clave in decl and anclada is None:
            salida["sacadas"].append(clave)
        elif anclada is None:
            escrita = next((o for o, t in textos.items() if habla_de(t, clave)), None)
            salida["sueltas"].append([clave, escrita])
        elif anclada not in textos:
            salida["colgadas"].append([clave, anclada])
        elif not habla_de(textos[anclada], clave):
            salida["mudas"].append([clave, anclada])
        elif not dichas.get(anclada):
            salida["vacias"].append([clave, anclada])
        else:
            salida["piso"].append(clave)
print(json.dumps(salida, ensure_ascii=False))
'''


def chequeo_playbook(c: Contexto, r: Reporte) -> None:
    """El playbook valida contra el contrato, y el piso de dos objeciones está anclado.

    Hasta hoy la compuerta no miraba el playbook una sola vez: `grep -c playbook` sobre este
    archivo daba 2, y las dos adentro de una salida de ejemplo. Lo que sostiene el piso es el
    heredoc del paso 9 de `blueprint/25-playbook.md`, o sea una persona que se acuerda de
    copiarlo y pegarlo. Un playbook que no valida no es un archivo feo: es la entrada del agente
    —`playbook` es campo obligatorio del contrato— y lo que se cae es el ciclo entero.

    El piso se cuenta por la clave y nunca por la palabra adentro del texto, que es el falso rojo
    que ya está documentado allá: «¿Me podés hacer un precio mejor?» es `descuento` y no dice
    «descuento» en ningún lado. **Y además se mira el contenido, porque la clave sola se falsifica
    en dos renglones**: un `piso:` que apunta a «Ahora no tengo un minuto» y a «Mandame
    informacion» tiene las dos claves, las dos apuntan a algo, y daba `piso: 2 de 2` sin contestar
    ni un descuento ni una garantía. Eso lo resuelve `SENTIDO` —ver `_DRIVER_PLAYBOOK`—, que es la
    lista que ya usaba el heredoc del paso 9 y que a esta compuerta le faltaba entera.

    **`SENTIDO` se pregunta sobre `objecion`, no sobre `objecion + respuesta`.** Con la respuesta
    adentro, las mismas dos objeciones de arriba volvían a dar `piso: 2 de 2` con dos palabras más
    de trabajo —«Acá no hacemos descuento por apuro», «Garantia de respuesta en el dia»—, que es la
    misma falsificación negando lo que nombra. El `objecion` es lo que el piso ancla y es lo único
    que no se puede reescribir sin cambiar cuál es la objeción.

    Seis desenlaces por clave: apunta a una objeción que está, que habla de lo suyo y que tiene algo
    escrito al lado —cuenta—; está en `null` —la sacó el usuario a propósito, y eso es aviso porque
    es una decisión suya—; falta; apunta a un texto que ya no existe; apunta a uno que existe y no
    habla de eso; o apunta al correcto con la `respuesta` vacía, que el esquema deja pasar porque no
    le pone largo mínimo. Los cuatro últimos son error, y los cuatro terminan igual: el agente llega
    a la objeción más frecuente del negocio sin nada que contestar.

    **Lo que este chequeo no puede decidir, y hay que decirlo con todas las letras.** Que la
    respuesta anclada *conteste* la objeción es una pregunta sobre prosa, y ninguna regla estática
    la responde: `objecion: "¿Me haces un descuento?"` con `respuesta: "No."` cuenta como piso y
    esta compuerta no tiene con qué objetar. Lo que sí queda garantizado, y es lo que hay que leer
    cuando el renglón dice `piso: 2 de 2`:

    1. el bloque `playbook:` valida contra el fragmento del contrato de entrada;
    2. las dos claves del piso existen y cada una nombra un `objecion` que está en la lista;
    3. ese `objecion` es reconociblemente el del descuento y el de la garantía, por `SENTIDO` y
       sobre el texto de la objeción sola;
    4. hay una `respuesta` no vacía escrita al lado;
    5. no quedan huecos con llaves sin llenar en ningún lado del archivo.

    Nada más que eso. Si la respuesta es mala, lo ve una persona leyendo `config/playbook.yaml`, o
    el simulador de la fase 5, que trae al que pide descuento prearmado.
    """
    archivo = c.raiz / PLAYBOOK
    esquema = c.raiz / "contratos/entrada.schema.json"
    if not archivo.is_file():
        r.saltear(f"todavía no existe {PLAYBOOK}: lo escribe el paso 7 de "
                  f"blueprint/25-playbook.md, en la fase 2")
        return
    if not esquema.is_file():
        r.error("playbook/sin_contrato",
                "falta contratos/entrada.schema.json: sin el fragmento `playbook` no hay contra "
                "qué validar", "contratos/entrada.schema.json", 0, "kit")
        return

    salida, problema = "", ""
    for interprete in c.interpretes:
        codigo, bruto = _correr([interprete, "-c", _DRIVER_PLAYBOOK, str(archivo), str(esquema)],
                                cwd=c.raiz)
        if codigo == 0:
            salida = bruto
            break
        problema = _recorte(bruto, 300)
        if "No module named" not in bruto:
            break
    if not salida:
        if "No module named" in problema:
            r.saltear(f"falta PyYAML en este intérprete: {problema}")
            return
        r.error("playbook/no_se_pudo_leer", f"el driver salió con error: {problema}",
                PLAYBOOK, 0, "build")
        return

    try:
        datos = json.loads(salida.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        r.error("playbook/salida_ilegible", f"el driver devolvió algo que no es JSON: "
                f"{_recorte(salida)}", PLAYBOOK, 0, "entorno")
        return

    if datos.get("sin_jsonschema"):
        r.aviso("playbook/sin_jsonschema",
                "falta jsonschema en este intérprete: conté el piso y los huecos, y el bloque no "
                "se validó contra el contrato. Corré esto con el `.venv` del proyecto",
                PLAYBOOK, 0, "entorno")
    for e in datos["errores"]:
        r.error("playbook/no_valida",
                f"{e}. `playbook` es campo obligatorio de contratos/entrada.schema.json: un bloque "
                f"que no valida no entra al ciclo, y el agente arranca sin nada que contestarle a "
                f"una objeción", PLAYBOOK, 0, "build")

    for clave, anclada in datos["colgadas"]:
        r.error("playbook/piso_colgado",
                f"`piso.{clave}` nombra un texto que no está en la lista de objeciones —"
                f"«{_recorte(str(anclada), 80)}»—: la reescribieron después de anclarla. Copiá en "
                f"esa clave el `objecion` que quedó, tal cual", PLAYBOOK, 0, "build")
    for clave, anclada in datos["mudas"]:
        r.error("playbook/piso_no_habla",
                f"`piso.{clave}` apunta a «{_recorte(str(anclada), 80)}», que está en la lista y no "
                f"habla de {clave}. Las dos claves existen, las dos apuntan a algo y la cuenta "
                f"decía `2 de 2` con el piso vacío: la objeción anclada no deriva ni un descuento "
                f"ni una condición de garantía, así que el agente llega ahí sin nada que "
                f"contestar. Se mira el `objecion`, en minúsculas y sin tildes, contra la lista "
                f"`SENTIDO` de blueprint/25-playbook.md paso 9 —y no la `respuesta`, porque meter "
                f"ahí la palabra es gratis y no cambia cuál es la objeción—. Dos arreglos, según "
                f"cuál sea el caso: si el ancla apunta a la objeción equivocada, copiá en esa "
                f"clave el `objecion` que sí es; si la objeción del {clave} está escrita con "
                f"palabras que `SENTIDO` no tiene, decilo en pantalla y sumá esa palabra a la "
                f"tupla, que para eso está a la vista", PLAYBOOK, 0, "build")
    for clave, anclada in datos.get("vacias", []):
        r.error("playbook/piso_sin_respuesta",
                f"`piso.{clave}` apunta a «{_recorte(str(anclada), 80)}», que es la objeción "
                f"correcta y no tiene `respuesta` escrita: está vacía o son espacios. El fragmento "
                f"`playbook` de contratos/entrada.schema.json la pide `string` y no le pone largo "
                f"mínimo, así que valida; lo que no hay es qué mandar. Escribí la respuesta en el "
                f"paso 7 de blueprint/25-playbook.md", PLAYBOOK, 0, "build")
    for clave, escrita in datos["sueltas"]:
        pista = (f" La que habla de {clave} y quedó sin anclar es «{_recorte(str(escrita), 80)}»: "
                 f"copiala tal cual." if escrita else
                 f" Y no hay ninguna objeción escrita que hable de {clave}: esto no se arregla en "
                 f"el paso 7, se vuelve al paso 5 o al 6 y se escribe.")
        r.error("playbook/piso_sin_anclar",
                f"el piso no ancla `{clave}`: `config/playbook.yaml` lleva un bloque `piso:` con "
                f"las dos claves fijas, y cada una apunta a la objeción que quedó escrita.{pista} "
                f"Sin eso nadie puede decir si la objeción está o se perdió entre el paso 2 y el "
                f"7, y el simulador la trae prearmada. Ver blueprint/25-playbook.md paso 9",
                PLAYBOOK, 0, "build")
    for clave in datos["sacadas"]:
        r.aviso("playbook/piso_sacado",
                f"`piso.{clave}` está en `null`: la sacaron a propósito y está bien, pero el "
                f"agente va a nombrar esa objeción sin contestarla. Que figure en "
                f"`.wca-estado.json` con el motivo", PLAYBOOK, 0, "build")

    if datos["huecos"]:
        r.error("playbook/huecos_abiertos",
                f"quedan huecos sin llenar: {', '.join(datos['huecos'])}. Eso es lo que termina "
                f"leyendo el cliente, con las llaves puestas. Los llena el paso 8 de "
                f"blueprint/25-playbook.md, y `{{precio}}` sale del catálogo y de ningún otro lado",
                PLAYBOOK, 0, "build")

    sin_bloque = " (sin bloque piso)" if datos.get("sin_bloque") else ""
    sacadas = (f" (sacadas a propósito: {', '.join(datos['sacadas'])})" if datos["sacadas"] else "")
    r.decir(f"{datos['objeciones']} objeciones · piso: {len(datos['piso'])} de "
            f"{len(CLAVES_DEL_PISO)}{sacadas}{sin_bloque} · huecos: "
            f"{', '.join(datos['huecos']) or 'ninguno'}")


# ─────────────────────────────────────────────────────────────────────────────
# 21 · panel-cerrado
# ─────────────────────────────────────────────────────────────────────────────
#
# La puerta del panel, mirada por estructura. El invariante es de una línea:
#
#     router = APIRouter(dependencies=[Depends(exigir_token)])
#
# y sin ella el panel queda en la URL pública de Railway, desde el primer despliegue, publicando
# los teléfonos, los scores y los resúmenes del CRM de los clientes del negocio. Medido sobre un
# build que estaba en verde, recortando esa sola línea: `159 passed`, `PASS · 0 errores · 0 avisos
# · 0 salteados`, y `GET /api/leads` sin token devolviendo la tabla entera.
#
# Los nombres que se buscan. `exigir_token` y `router` son los que fija `blueprint/35-panel-api.md`
# paso 4 y repite `blueprint/00-contrato.md` § 3; el chequeo 14 exige que `panel/panel.py` los
# defina, y éste exige que estén puestos donde sirven.
DEPENDENCIA_DEL_PANEL = "exigir_token"
ROUTER_DEL_PANEL = "router"
MODULO_DEL_PANEL = "panel/panel.py"

# Los caminos que la tabla de `blueprint/00-contrato.md` § 3 marca con «Token: sí», y los dos que
# marca con «no». Se comparan por prefijo sobre el camino literal escrito en el decorador, ya con
# el `prefix=` de su router adelante.
CAMINOS_CON_TOKEN = ("/api", "/panel")
CAMINOS_SIN_TOKEN = ("/salud", "/webhook")

# Los verbos con los que se monta una ruta. `api_route` y `websocket` entran por lo mismo que los
# otros: montan, y lo que se pregunta es de qué cuelgan.
VERBOS_DE_RUTA = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "trace",
                            "api_route", "websocket"})
ALTAS_DE_RUTA = frozenset({"add_api_route", "add_route", "add_websocket_route",
                           "add_api_websocket_route"})

# Cuántas veces se vuelve a resolver el árbol de montajes antes de darlo por firme. Un router se
# incluye adentro de otro y el de afuera se incluye en la app, así que cada pasada resuelve un
# eslabón. Es un tope y no un `while` por lo mismo que `PASADAS_DE_CONSTANTES`: dos routers que se
# incluyan mutuamente colgarían la compuerta, y una compuerta que cuelga es peor que un hallazgo.
PASADAS_DE_MONTAJE = 4


@dataclass
class _Fabrica:
    """Un `APIRouter(...)` o un `FastAPI(...)` asignado a nivel de módulo."""

    rel: str
    nombre: str
    tipo: str  # "router" | "app"
    prefijo: str
    propia: bool  # trae `dependencies=[Depends(exigir_token)]` en el constructor
    linea: int


@dataclass
class _Montaje:
    """Un `padre.include_router(hijo, prefix=…, dependencies=[…])`."""

    padre: tuple[str, str] | None
    hijo: tuple[str, str] | None
    prefijo: str
    protegido: bool
    rel: str
    linea: int


def _kw(llamada: ast.Call, nombre: str) -> ast.AST | None:
    for kw in llamada.keywords:
        if kw.arg == nombre:
            return kw.value
    return None


def _texto_kw(llamada: ast.Call, nombre: str) -> str:
    nodo = _kw(llamada, nombre)
    return nodo.value if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) else ""


def _pide_el_token(llamada: ast.Call) -> bool:
    """`dependencies=[Depends(exigir_token)]` adentro de esta llamada.

    Se aceptan las formas de escribirlo que dan el mismo objeto: `Depends(exigir_token)` con el
    nombre importado, y `Depends(panel.exigir_token)` con el módulo adelante. Lo que no se acepta
    es una lista armada en otra variable: ahí no se puede leer qué hay adentro, y un `dependencies=`
    que no se puede leer no es una puerta que se pueda afirmar.
    """
    nodo = _kw(llamada, "dependencies")
    for elemento in getattr(nodo, "elts", []):
        if not isinstance(elemento, ast.Call):
            continue
        if _punteado(elemento.func).split(".")[-1] != "Depends":
            continue
        argumentos = list(elemento.args) + [k.value for k in elemento.keywords]
        if any(_punteado(a).split(".")[-1] == DEPENDENCIA_DEL_PANEL for a in argumentos):
            return True
    return False


def _camino_de_ruta(llamada: ast.Call) -> str:
    """El camino literal del decorador, o cadena vacía si no está escrito ahí."""
    nodo = llamada.args[0] if llamada.args else _kw(llamada, "path")
    return nodo.value if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) else ""


def _fabricas_del_modulo(rel: str, arbol: ast.Module) -> dict[str, _Fabrica]:
    fabricas: dict[str, _Fabrica] = {}
    for nodo in arbol.body:
        valor = nodo.value if isinstance(nodo, (ast.Assign, ast.AnnAssign)) else None
        if not isinstance(valor, ast.Call):
            continue
        cual = _punteado(valor.func).split(".")[-1]
        if cual not in ("APIRouter", "FastAPI"):
            continue
        destinos = (nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target])
        for destino in destinos:
            if isinstance(destino, ast.Name):
                fabricas[destino.id] = _Fabrica(
                    rel, destino.id, "router" if cual == "APIRouter" else "app",
                    _texto_kw(valor, "prefix"), _pide_el_token(valor), nodo.lineno)
    return fabricas


def _traidos(rel: str, arbol: ast.Module, indice: set[str]) -> dict[str, tuple[str, str]]:
    """`local → (archivo de origen, nombre de allá)` para lo que llega por `from … import …`."""
    traidos: dict[str, tuple[str, str]] = {}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom):
            origen = _modulo_importado(rel, nodo, indice)
            if origen:
                for a in nodo.names:
                    traidos[a.asname or a.name] = (origen, a.name)
    return traidos


# El método HTTP de cada forma de montar. El decorador lo dice en el nombre —`@x.get`— salvo en las
# genéricas, que lo llevan en `methods=`.
METODO_DEL_VERBO = {v: v.upper() for v in
                    ("get", "post", "put", "patch", "delete", "head", "options", "trace")}
VERBOS_DE_WEBSOCKET = frozenset({"websocket", "add_websocket_route", "add_api_websocket_route"})
# El método que no se pudo leer: un `api_route(...)` sin `methods=` literal. **No se supone `GET`**,
# que es lo que haría fastapi: lo que no se puede afirmar no se afirma, y sale como una fila que la
# tabla del contrato no tiene, o sea como un hallazgo y no como un silencio.
METODO_ILEGIBLE = "?"


def _metodos_de_ruta(atributo: str, llamada: ast.Call) -> tuple[str, ...]:
    if atributo in METODO_DEL_VERBO:
        return (METODO_DEL_VERBO[atributo],)
    if atributo in VERBOS_DE_WEBSOCKET:
        return ("WEBSOCKET",)
    nodo = _kw(llamada, "methods")
    leidos = tuple(sorted({e.value.upper() for e in getattr(nodo, "elts", [])
                           if isinstance(e, ast.Constant) and isinstance(e.value, str)}))
    return leidos or (METODO_ILEGIBLE,)


@dataclass
class _Mapa:
    """El árbol de montajes de la app, ya resuelto: quién cuelga de quién, con qué prefijo delante
    y detrás de qué puerta.

    Lo leen los dos chequeos del servidor —el 21 pregunta si cada ruta pasa por `exigir_token`, el
    22 si el juego de rutas es el de la tabla de `blueprint/00-contrato.md` § 3— y se resuelve una
    vez para los dos. Nada de acá importa ni ejecuta un módulo del build: es AST y nada más.
    """

    arboles: dict[str, ast.Module]
    fabricas: dict[tuple[str, str], _Fabrica]
    traidos: dict[str, dict[str, tuple[str, str]]]
    montajes: list[_Montaje]
    protegida: dict[tuple[str, str], bool]
    prefijos: dict[tuple[str, str], set[str]]

    def buscar(self, rel: str, nombre: str) -> tuple[str, str] | None:
        """La fábrica que denota este nombre acá: la local, o la que llegó importada."""
        corto = nombre.split(".")[-1]
        for clave in ((rel, nombre), (rel, corto)):
            if clave in self.fabricas:
                return clave
        for candidato in (nombre, corto):
            origen = self.traidos.get(rel, {}).get(candidato)
            if origen and origen in self.fabricas:
                return origen
        return None

    def caminos(self, clave: tuple[str, str], literal: str) -> list[str]:
        base = self.prefijos.get(clave) or {self.fabricas[clave].prefijo}
        return [p + literal for p in base]

    def rutas(self, rel: str, arbol: ast.Module) -> list[tuple[str, ast.Call, int, tuple[str, ...]]]:
        """`(objeto sobre el que se monta, llamada, línea, métodos)` de este archivo."""
        encontradas: list[tuple[str, ast.Call, int, tuple[str, ...]]] = []
        for nodo in ast.walk(arbol):
            for dec in getattr(nodo, "decorator_list", []):
                if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr in VERBOS_DE_RUTA):
                    encontradas.append((_punteado(dec.func.value), dec, dec.lineno,
                                        _metodos_de_ruta(dec.func.attr, dec)))
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                    and nodo.func.attr in ALTAS_DE_RUTA):
                encontradas.append((_punteado(nodo.func.value), nodo, nodo.lineno,
                                    _metodos_de_ruta(nodo.func.attr, nodo)))
        return encontradas


def _leer_montaje(c: Contexto) -> _Mapa:
    """`agente/` y `panel/` leídos enteros, y el árbol de montajes resuelto."""
    fuentes = list(c.modulos())
    panel = c.raiz / "panel"
    if panel.is_dir():
        fuentes += [p for p in sorted(panel.rglob("*.py")) if "__pycache__" not in p.parts]
    arboles: dict[str, ast.Module] = {}
    for modulo in fuentes:
        arbol, _ = _arbol(modulo)
        if arbol is not None:
            arboles[c.rel(modulo)] = arbol

    indice = set(arboles)
    fabricas: dict[tuple[str, str], _Fabrica] = {}
    traidos: dict[str, dict[str, tuple[str, str]]] = {}
    for rel, arbol in arboles.items():
        traidos[rel] = _traidos(rel, arbol, indice)
        for nombre, fabrica in _fabricas_del_modulo(rel, arbol).items():
            fabricas[(rel, nombre)] = fabrica

    m = _Mapa(arboles, fabricas, traidos, [], {clave: f.propia for clave, f in fabricas.items()},
              {clave: ({""} if f.tipo == "app" else set()) for clave, f in fabricas.items()})

    for rel, arbol in arboles.items():
        for nodo in ast.walk(arbol):
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                    and nodo.func.attr == "include_router"):
                hijo = m.buscar(rel, _punteado(nodo.args[0])) if nodo.args else None
                m.montajes.append(_Montaje(
                    m.buscar(rel, _punteado(nodo.func.value)), hijo,
                    _texto_kw(nodo, "prefix"), _pide_el_token(nodo), rel, nodo.lineno))

    # Quién queda protegido y bajo qué prefijos, resuelto de a pasadas porque un router se incluye
    # adentro de otro y el de afuera recién después en la app.
    for _ in range(PASADAS_DE_MONTAJE):
        for clave, fabrica in fabricas.items():
            suyos = [x for x in m.montajes if x.hijo == clave]
            if not suyos:
                continue
            if not m.protegida[clave]:
                # Todos los montajes, no alguno: un router montado dos veces, una protegida y otra
                # no, contesta abierto por la segunda.
                m.protegida[clave] = all(
                    x.protegido or (x.padre is not None and m.protegida.get(x.padre, False))
                    for x in suyos)
            for x in suyos:
                arriba = m.prefijos.get(x.padre, {""}) if x.padre else {""}
                m.prefijos[clave] |= {p + x.prefijo + fabrica.prefijo for p in arriba}
    return m


def chequeo_panel_cerrado(c: Contexto, r: Reporte) -> None:
    """Ninguna ruta bajo `/api/` cuelga de otra cosa que del router con `exigir_token` puesto.

    **Por qué existe.** El chequeo 14 pedía que `panel/panel.py` existiera y no le pedía un solo
    símbolo. El 13 mira destinos de mensajería, el 12 clientes httpx, y ninguno de los veinte que
    había preguntaba por la puerta del panel. Con `router = APIRouter()` —una línea recortada— el kit
    entero decía que estaba bien: `159 passed`, `PASS · 0 errores · 0 avisos · 0 salteados`, y
    `GET /api/leads` sin token devolviendo teléfonos, scores y resúmenes del CRM en una URL
    pública. Es la pieza que `blueprint/35-panel-api.md` describe con más énfasis —«el default
    abierto es el que nadie nota hasta que ya pasó»— y era la única sin nada encima.

    **Las tres reglas, y la tercera no es un adorno.**

    1. El `router` de `panel/panel.py` lleva `dependencies=[Depends(exigir_token)]`.
    2. Toda ruta bajo `/api/` o `/panel` cuelga de un router protegido. Montada sobre la app con
       `@app.get("/api/…")` queda fuera del router, y por lo tanto fuera de la puerta, aunque el
       router esté perfecto: es el build que la regla 1 sola no ve.
    3. `/salud` y `/webhook/{proveedor}` **no** pueden colgar de ese router. Es el arreglo apurado
       que sale de leer el rojo de las otras dos —meter todo adentro— y se paga en el despliegue:
       Railway no manda cabeceras, el chequeo de salud da 401 y el despliegue se muere sin decir
       por qué.

    **La dependencia se acepta en dos lugares y no en uno.** En el `APIRouter(...)`, que es la
    forma que el blueprint prescribe, y en el `include_router(...)` que lo monta, que da el mismo
    objeto y no es un atajo. Lo que no se acepta es ruta por ruta: es seguro hoy y abierto mañana,
    porque la ruta que alguien agregue nace sin nada, y sale con su propio hallazgo para que se lea
    la diferencia. La protección se hereda hacia adentro, igual que en fastapi: un router incluido
    adentro de uno protegido queda protegido.

    **No se importa ni se ejecuta nada del build**, como en el resto de este archivo: se lee el
    árbol sintáctico. El precio está dicho abajo, en `panel/ruta_sin_router`: una ruta montada en
    un bucle, o sobre un objeto que no se puede resolver leyendo, no se puede afirmar desde acá.
    Lo que sí las ve es `pruebas/test_panel.py`, que le pregunta a la app **montada** qué tiene
    colgado y pide cada ruta sin token; esta compuerta corre esa suite en el chequeo 19. Son las
    dos mitades: acá se nombra la causa, allá se prueba la conducta.
    """
    if not c.hay_agente:
        r.saltear("no existe agente/: esto corre después de /armar-cerrador")
        return

    mapa = _leer_montaje(c)
    fabricas, protegida = mapa.fabricas, mapa.protegida

    montada_alguna = False
    for rel, arbol in mapa.arboles.items():
        # Las que no se pueden resolver salen juntas y una sola vez por archivo: la causa es una
        # —el objeto sobre el que se montan no es una fábrica que se pueda leer— y ocho renglones
        # repitiéndola tapan el hallazgo que sí dice qué arreglar.
        sin_duenno: list[tuple[str, str, int]] = []
        for objeto, llamada, linea, _ in mapa.rutas(rel, arbol):
            literal = _camino_de_ruta(llamada)
            if not literal.startswith("/"):
                continue
            clave = mapa.buscar(rel, objeto)
            if clave is None:
                if literal.startswith(CAMINOS_CON_TOKEN):
                    montada_alguna = True
                    sin_duenno.append((objeto or _fuente(llamada), literal, linea))
                continue
            for camino in mapa.caminos(clave, literal):
                if camino.startswith(CAMINOS_CON_TOKEN):
                    montada_alguna = True
                    if protegida[clave]:
                        continue
                    if _pide_el_token(llamada):
                        r.error("panel/dependencia_por_ruta",
                                f"`{camino}` trae `Depends({DEPENDENCIA_DEL_PANEL})` en la ruta y "
                                f"su router no lo trae. Hoy cierra y mañana no: la ruta que "
                                f"alguien agregue a ese router nace sin nada, y nadie la va a "
                                f"mirar dos veces porque las de al lado están bien. Va sobre el "
                                f"router entero —`APIRouter(dependencies=[Depends("
                                f"{DEPENDENCIA_DEL_PANEL})])`— y nunca ruta por ruta; ver "
                                f"blueprint/35-panel-api.md paso 4", rel, linea, "build")
                        continue
                    donde = ("la app, o sea afuera del router del panel"
                             if fabricas[clave].tipo == "app"
                             else f"`{fabricas[clave].nombre}`, que es un router sin la "
                                  f"dependencia puesta")
                    r.error("panel/ruta_suelta",
                            f"`{camino}` cuelga de {donde}, así que no pasa por "
                            f"`{DEPENDENCIA_DEL_PANEL}`. Eso es el panel abierto en la URL pública "
                            f"de Railway desde el primer despliegue: lo que se publica ahí son los "
                            f"teléfonos, los scores y los resúmenes del CRM de los clientes del "
                            f"negocio, y nadie se entera hasta que ya pasó. Va sobre el router "
                            f"entero, con `Depends`, y nunca ruta por ruta; ver "
                            f"blueprint/00-contrato.md § 3 y blueprint/35-panel-api.md paso 4",
                            rel, linea, "build")
                elif camino.startswith(CAMINOS_SIN_TOKEN) and protegida[clave]:
                    r.error("panel/publica_con_token",
                            f"`{camino}` cuelga del router del panel y tiene que quedar afuera. "
                            f"`/salud` es el `healthcheckPath` de `railway.json` y Railway no "
                            f"manda cabeceras: adentro del router contesta 401, el despliegue se "
                            f"muere ahí y lo único que se lee es `service unavailable`. El GET de "
                            f"`/webhook/{{proveedor}}` es el alta de Meta, que la hace Meta y sin "
                            f"token. Ver blueprint/35-panel-api.md paso 2", rel, linea, "build")

        if sin_duenno:
            objetos = ", ".join(sorted({o for o, _, _ in sin_duenno}))
            cuales = ", ".join(f"`{camino}` (línea {n})" for _, camino, n in sin_duenno[:4])
            r.error("panel/ruta_sin_router",
                    f"{len(sin_duenno)} ruta(s) bajo `/api/` o `/panel` se montan sobre "
                    f"`{objetos}`, que no puedo resolver leyendo el árbol, así que no puedo decir "
                    f"si pasan por `{DEPENDENCIA_DEL_PANEL}`: {cuales}. Acá no se importa ni se "
                    f"ejecuta nada del build, y una ruta que no se puede afirmar cerrada se trata "
                    f"como abierta. Montalas con `@router.<verbo>(...)` sobre el `router` de "
                    f"{MODULO_DEL_PANEL}, que es un nombre asignado a nivel de módulo y se lee "
                    f"desde acá; ver blueprint/35-panel-api.md paso 4",
                    rel, sin_duenno[0][2], "build")

    del_panel = fabricas.get((MODULO_DEL_PANEL, ROUTER_DEL_PANEL))
    if del_panel is None:
        if (c.raiz / MODULO_DEL_PANEL).is_file():
            r.error("panel/sin_router",
                    f"{MODULO_DEL_PANEL} no asigna `{ROUTER_DEL_PANEL} = APIRouter(...)` a nivel "
                    f"de módulo. `agente/servidor.py` lo importa por ese nombre y "
                    f"blueprint/00-contrato.md § 3 lo verifica con `from panel.panel import router "
                    f"as panel`: sin él no hay router del panel que proteger",
                    MODULO_DEL_PANEL, 0, "build")
        # Si el archivo no está, el chequeo 14 `agente-completo` ya lo dice con el `cp` que lo
        # arregla. Dos chequeos diciendo lo mismo es un hallazgo duplicado.
    elif not protegida[(MODULO_DEL_PANEL, ROUTER_DEL_PANEL)]:
        r.error("panel/router_abierto",
                f"el `{ROUTER_DEL_PANEL}` de {MODULO_DEL_PANEL} se construye sin "
                f"`dependencies=[Depends({DEPENDENCIA_DEL_PANEL})]` y tampoco se lo pone el "
                f"`include_router` que lo monta. Es **la** línea del panel: sin ella el kit entero "
                f"da verde —`159 passed`, `PASS · 0 errores · 0 avisos · 0 salteados`— y "
                f"`GET /api/leads` sin token devuelve los teléfonos, los scores y los resúmenes "
                f"del CRM de los clientes del negocio en una URL pública. Ver "
                f"blueprint/35-panel-api.md paso 4", MODULO_DEL_PANEL, del_panel.linea, "build")

    if not montada_alguna:
        r.error("panel/sin_rutas_de_api",
                "no encontré una sola ruta bajo `/api/` ni `/panel` escrita en el árbol, y "
                "`agente/` está construido. O el panel no se escribió —la tabla de las diez rutas "
                "está en blueprint/00-contrato.md § 3—, o se monta de una forma que este chequeo "
                "no sabe leer, y en los dos casos lo que no se puede enumerar no se puede afirmar "
                "cerrado", MODULO_DEL_PANEL, 0, "build")
        return

    cerradas = sum(1 for clave, f in fabricas.items() if f.tipo == "router" and protegida[clave])
    r.decir(f"{len(fabricas)} router(s) y app(s) leídos, {cerradas} con "
            f"`{DEPENDENCIA_DEL_PANEL}` puesto · toda ruta de `/api/` y `/panel` detrás del token")


# ─────────────────────────────────────────────────────────────────────────────
# 22 · rutas-del-contrato
# ─────────────────────────────────────────────────────────────────────────────

MODULO_DEL_SERVIDOR = "agente/servidor.py"

# La tabla de `blueprint/00-contrato.md` § 3, fila por fila. Once métodos sobre diez caminos:
# `/webhook/{proveedor}` comparte camino entre el GET y el POST.
#
# **El nombre del parámetro no se compara**: `{proveedor}` y `{id}` entran acá como `{}` y el
# camino montado se normaliza igual antes de comparar. Un build que escriba
# `/api/conversaciones/{contacto_id}` montó la ruta de la tabla con otro nombre adentro, y eso no
# es una ruta de más; lo que sí lo es es `/tablero`.
RUTAS_DEL_CONTRATO: tuple[tuple[str, str], ...] = (
    ("GET", "/salud"),
    ("GET", "/webhook/{}"),
    ("POST", "/webhook/{}"),
    ("GET", "/panel"),
    ("GET", "/api/conversaciones"),
    ("GET", "/api/conversaciones/{}"),
    ("GET", "/api/leads"),
    ("GET", "/api/pendientes"),
    ("POST", "/api/pendientes/{}/aprobar"),
    ("POST", "/api/pendientes/{}/rechazar"),
    ("POST", "/api/webhooks-salientes"),
)

PARAMETRO_DE_CAMINO = re.compile(r"\{[^{}]*\}")


def _camino_canonico(camino: str) -> str:
    """El camino con los nombres de parámetro borrados y sin la barra final.

    `/api/conversaciones/{contacto_id}/` y `/api/conversaciones/{id}` son la misma fila de la
    tabla. `/tablero` no es ninguna.
    """
    return PARAMETRO_DE_CAMINO.sub("{}", camino).rstrip("/") or "/"


def chequeo_rutas_del_contrato(c: Contexto, r: Reporte) -> None:
    """El juego de rutas montadas es el de la tabla de § 3, y no hay una más.

    **Por qué existe.** `blueprint/00-contrato.md` § 3 dice «Las rutas son éstas y no hay otras», y
    hasta hoy ningún chequeo contaba las rutas montadas ni preguntaba si sobraba alguna. La suite
    tampoco: `test_las_ocho_rutas_detras_del_token_estan_montadas` verifica que las diez **estén**,
    nunca que no haya once. El comando de § 3 que imprime `10 rutas · 11 métodos` lo mira una
    persona, y una persona no lo mira en cada corrida.

    Doce renglones alcanzaban para pasar la compuerta entera con el panel abierto: un
    `@app.get("/tablero")` que devuelve `listar_leads()` y `listar_conversaciones()` deja
    `GET /api/leads` en 401, `GET /panel` en 401 y `GET /tablero` en **200**, con los números, las
    etapas, los scores y los resúmenes del CRM adentro, y el árbol sigue en `176 passed · PASS ·
    0 errores · 0 avisos · 0 salteados`. El chequeo 21 no lo ve porque decide por el prefijo del
    camino —`CAMINOS_CON_TOKEN`— y `/tablero` no empieza con ninguno de los dos.

    **Por eso la vara es la tabla entera y no una lista de prefijos.** Una puerta atada al prefijo
    cierra el caso que alguien ya vio; comparar contra la tabla cierra la clase: cualquier ruta que
    no esté escrita en § 3 es un hallazgo, se llame `/tablero`, `/debug` o `/api2/leads`, y no hace
    falta que nadie la anticipe.

    **Qué se compara.** El par (método, camino) de cada ruta montada, con el prefijo de su router
    ya adelante y con los nombres de parámetro normalizados. Cada fila que sobra sale con su
    archivo y su línea; las que faltan salen juntas en un solo hallazgo, porque la causa es una.

    **Lo que no ve, dicho y no escondido.** Un camino que no está escrito como literal en el
    decorador —`@router.get(RUTA_LEADS)`— no se puede leer desde acá y no entra en la cuenta. No se
    reporta: la misma forma la usan decoradores que no montan nada —`@mock.patch("agente.enviar")`
    tiene `patch` en el nombre y una cadena que no empieza con `/`— y un chequeo que grite ahí es
    un chequeo que se apaga. Lo que sí las ve es `pruebas/test_panel.py`, que le pregunta a la app
    **montada** qué tiene colgado; esta compuerta corre esa suite en el chequeo 19 y exige el
    archivo por nombre en `ARCHIVOS_DE_PRUEBA`. Son las dos mitades.
    """
    if not c.hay_agente:
        r.saltear("no existe agente/: esto corre después de /armar-cerrador")
        return
    if not (c.raiz / MODULO_DEL_SERVIDOR).is_file():
        # El chequeo 14 `agente-completo` ya lo dice, y con la fase que lo escribe al lado. Dos
        # chequeos diciendo lo mismo es un hallazgo duplicado.
        r.saltear(f"todavía no existe {MODULO_DEL_SERVIDOR}: lo escribe blueprint/35-panel-api.md, "
                  f"y el chequeo 14 lo está diciendo")
        return

    mapa = _leer_montaje(c)
    montadas: dict[tuple[str, str], list[tuple[str, int]]] = {}
    for rel, arbol in mapa.arboles.items():
        for objeto, llamada, linea, metodos in mapa.rutas(rel, arbol):
            literal = _camino_de_ruta(llamada)
            if not literal.startswith("/"):
                continue
            clave = mapa.buscar(rel, objeto)
            # Sin fábrica que resolver no hay prefijo que anteponer, y el literal es lo que hay. Se
            # compara igual: una ruta de más escrita sobre un objeto ilegible sigue siendo una ruta
            # de más, y el chequeo 21 ya reporta aparte que no se pudo resolver de qué cuelga.
            for camino in (mapa.caminos(clave, literal) if clave else [literal]):
                for metodo in metodos:
                    montadas.setdefault((metodo, _camino_canonico(camino)), []).append((rel, linea))

    del_contrato = set(RUTAS_DEL_CONTRATO)
    for fila in sorted(montadas):
        if fila in del_contrato:
            continue
        metodo, camino = fila
        rel, linea = montadas[fila][0]
        cual = (f"`{camino}` se monta con un método que no pude leer —un `api_route(...)` sin "
                f"`methods=` literal—, así que no puedo decir cuál es"
                if metodo == METODO_ILEGIBLE else f"`{metodo} {camino}` está montada")
        r.error("rutas/de_mas",
                f"{cual} y no está en la tabla de blueprint/00-contrato.md § 3, que dice «Las "
                f"rutas son éstas y no hay otras». Once métodos sobre diez caminos, y ésta es la "
                f"que sobra. Una ruta de más es la forma barata de dejar el panel abierto sin "
                f"tocar el panel: `@app.get(\"/tablero\")` devolviendo `listar_leads()` deja "
                f"`/api/leads` en 401 y los mismos datos en 200, y el chequeo 21 no la ve porque "
                f"decide por el prefijo del camino. Borrala, o entra en la tabla de § 3, en la de "
                f"blueprint/35-panel-api.md y en `RUTAS_DEL_CONTRATO` con el mismo commit",
                rel, linea, "build")

    faltan = [f for f in RUTAS_DEL_CONTRATO if f not in montadas]
    if faltan:
        cuales = ", ".join(f"`{metodo} {camino}`" for metodo, camino in faltan)
        r.error("rutas/faltan",
                f"{len(faltan)} de las {len(RUTAS_DEL_CONTRATO)} filas de la tabla de "
                f"blueprint/00-contrato.md § 3 no están montadas en ningún archivo de `agente/` ni "
                f"de `panel/`: {cuales}. Con `{MODULO_DEL_SERVIDOR}` en el árbol la fase que las "
                f"escribe ya corrió. Si están montadas con el camino en una constante en vez de un "
                f"literal, este chequeo no las puede leer y hay que escribirlas literales; el "
                f"comando que las lista está en § 3", MODULO_DEL_SERVIDOR, 0, "build")

    if not faltan and len(montadas) == len(RUTAS_DEL_CONTRATO):
        caminos = {camino for _, camino in montadas}
        r.decir(f"{len(caminos)} rutas · {len(montadas)} métodos, los de la tabla de "
                f"blueprint/00-contrato.md § 3 y ninguno más")


# ─────────────────────────────────────────────────────────────────────────────
# 23 · censo-de-campos
# ─────────────────────────────────────────────────────────────────────────────

ESQUEMA_DE_SALIDA = "contratos/salida.schema.json"
CENSO = Path("EVIDENCIA/censo.json")

# Cada mutante corre la suite entera una vez. Con el build en el árbol eso son segundos, no
# minutos, pero el corte existe igual: una corrida colgada es un campo que no se midió, y eso se
# dice, no se espera.
SEGUNDOS_CENSO = 180

# Dos mutantes por campo, y el segundo sólo cuando el primero salió verde. Existe por un modo de
# falla concreto: si el valor que inyecta el censo es justo el que la prueba espera —`urgencia`
# en nulo mutada a `"alta"` contra un nodo que afirma `"alta"`— el verde no quiere decir «nadie
# lo mira», quiere decir «le pegué al valor esperado». El segundo intento entra por el otro
# extremo de la lista de candidatos. Dos no cierran el agujero del todo y no se dice que lo
# cierren: lo hacen chico y cuestan sólo en los campos que salieron verdes, que son los que
# importan.
INTENTOS_POR_CAMPO = 2

# Los valores que el censo inyecta cuando el esquema pide una cadena. Son plausibles a propósito
# —una fecha con forma de fecha, un día con forma de día—: un mutante con basura adentro pone
# rojo cualquier `datetime.fromisoformat()` que lo toque, y eso se lee como «alguien lo afirma»
# cuando lo único que pasó es que alguien lo parsea. Las fechas caen una y dos semanas después
# del corpus, así que no coinciden por casualidad con ningún fixture.
FECHAS_DEL_CENSO = ("2026-03-09T15:30:00-03:00", "2026-03-16T09:00:00-03:00")
DIAS_DEL_CENSO = ("2026-03-09", "2026-03-16")
CADENAS_DEL_CENSO = ("censo-uno", "censo-dos")


# La lista explícita de campos que hoy no afirma nadie, con el motivo al lado. Es la otra mitad
# del chequeo: un campo declarado en `contratos/salida.schema.json` o lo pone rojo una prueba, o
# está acá con una línea que dice por qué no.
#
# **Hoy está vacía, y eso es un dato medido y no una aspiración.** El censo sobre un build, con la
# suite en `253 passed`, da `40 afirmado · 3 no_mutable · 0 sin_asercion` sobre los 43 campos que
# declara el esquema. Los 3 los fija el esquema —`version` es un `const`; `contacto` y
# `calificacion` son objetos con propiedades obligatorias, y sus hojas se miden una por una—. Los
# otros 40 tienen por lo menos un nodo que se pone rojo cuando ese campo, y sólo ése, cambia de
# valor.
#
# **Los nueve que estaban acá se cerraron con aserciones, no con renglones.** Eran
# `calificacion/intencion`, `calificacion/urgencia`, `respuesta/objecion_detectada`,
# `respuesta/objecion_en_playbook`, `crm/resumen`, `crm/proximo_paso`, `crm/proximo_paso_fecha`,
# `pregunta` y `supuestos`: cinco medidos a mano en rondas anteriores y cuatro que encontró el
# primer censo real. Los nueve los afirma `pruebas/test_campos.py`, que los mira **de a uno y por
# el valor**, en las dos direcciones cuando el campo tiene dos. El peor era
# `respuesta/objecion_en_playbook` —dice si el playbook se buscó o no, que es lo único que separa
# este agente de un bot de menú— y hoy lo afirma un nodo que manda la **misma** objeción contra dos
# playbooks y exige dos respuestas distintas: un build que lo devuelva fijo, en falso o en
# verdadero, se pone rojo en una de las dos.
#
# Cada uno se verificó además como se verificaron los cinco de las rondas viejas: rompiendo el
# campo en un build y mirando la suite. Trece mutantes de mano —los dos sentidos de
# `objecion_en_playbook`, la objeción fija, la intención fija, la urgencia en nulo, el resumen
# enlatado, el resumen sin recortar, el próximo paso y su fecha descartados, la pregunta siempre
# nula, la pregunta siempre puesta, la pregunta con dos preguntas, los supuestos vacíos y un
# supuesto inventado— y los trece ponen rojo un nodo de `pruebas/test_campos.py` y ninguno de otro
# archivo.
#
# **Qué es un motivo y qué no**, para cuando alguien tenga que volver a escribir un renglón acá.
# «todavía no» no es un motivo; «el corpus nunca produce una cita, así que no hay dónde mirar» sí
# lo es. Lo que la línea tiene que dejar es lo que alguien necesita para decidir si eso está bien:
# quién lo mediría, con qué entrada, y qué se pierde mientras tanto. Menos de 40 caracteres lo
# rechaza el propio chequeo, con `censo/lista_sin_motivo`.
#
# **Por qué vive acá y no en un archivo de datos.** Por lo mismo que `ARCHIVOS_DE_PRUEBA` y
# `PISO_DE_MODULOS`: una vara que el auditado edita sin que se note no es una vara. Agregar un
# renglón acá es tocar la compuerta, y eso se lee en el diff. Silenciar el chequeo es posible —es
# escribir el motivo—, y ese es todo el punto: que quede escrito una vez en vez de descubrirse
# para siempre.
#
# **Con la lista vacía, un campo nuevo del esquema sale como error el mismo día.** Eso es lo que se
# quería: `censo/campo_sin_asercion` con el valor que se inyectó, y quien lo lea decide si escribe
# la aserción o el renglón. Las dos cierran el chequeo y sólo una es trabajo de verdad.
SIN_ASERCION: dict[str, str] = {}


def _campos_declarados(sub: dict, prefijo: str = "") -> list[tuple[str, dict]]:
    """Cada propiedad declarada del esquema, con su subesquema. `*` abre los ítems de un arreglo.

    Sale del archivo y no de una lista escrita a mano: un campo nuevo en
    `contratos/salida.schema.json` aparece acá el mismo día, que es justo lo que no pasaba.
    """
    campos: list[tuple[str, dict]] = []
    propiedades = sub.get("properties")
    if isinstance(propiedades, dict):
        for nombre, hijo in propiedades.items():
            if not isinstance(hijo, dict):
                continue
            ruta = f"{prefijo}/{nombre}" if prefijo else nombre
            campos.append((ruta, hijo))
            campos.extend(_campos_declarados(hijo, ruta))
    items = sub.get("items")
    if isinstance(items, dict) and isinstance(items.get("properties"), dict):
        campos.extend(_campos_declarados(items, f"{prefijo}/*"))
    return campos


def _tipos(sub: dict) -> list[str]:
    tipo = sub.get("type")
    if isinstance(tipo, str):
        return [tipo]
    return [t for t in (tipo or []) if isinstance(t, str)]


def _ejemplo(sub: dict):
    """Un valor mínimo que valida contra `sub`. Para armar los ítems de un arreglo."""
    if "const" in sub:
        return sub["const"]
    if isinstance(sub.get("enum"), list) and sub["enum"]:
        return sub["enum"][0]
    tipos = _tipos(sub)
    if "object" in tipos:
        obligatorias = sub.get("required") or []
        propiedades = sub.get("properties") or {}
        return {k: _ejemplo(propiedades.get(k, {})) for k in obligatorias}
    if "array" in tipos:
        return [_ejemplo(sub.get("items", {}))] * int(sub.get("minItems", 0))
    if "boolean" in tipos:
        return False
    if "integer" in tipos:
        return int(sub.get("minimum", 0))
    if "number" in tipos:
        return float(sub.get("minimum", 0))
    if "string" in tipos:
        return _cadenas_validas(sub)[0]
    return None


def _cadenas_validas(sub: dict) -> list[str]:
    formato = sub.get("format")
    if formato == "date-time":
        return list(FECHAS_DEL_CENSO)
    if formato == "date":
        return list(DIAS_DEL_CENSO)
    return list(CADENAS_DEL_CENSO)


def _enteros_validos(sub: dict) -> list[int]:
    minimo = sub.get("minimum")
    maximo = sub.get("maximum")
    piso = int(minimo) if isinstance(minimo, (int, float)) else 0
    techo = int(maximo) if isinstance(maximo, (int, float)) else piso + 30
    return sorted({piso, techo, min(techo, piso + 1)})


def _candidatos(sub: dict) -> list:
    """Los valores que el censo puede poner en ese campo **sin salirse del esquema**.

    Es la mitad que hace que el método no se pueda fingir. Un mutante que rompe el esquema pone
    rojo a cualquier prueba que valide el documento contra `contratos/salida.schema.json`, y eso
    es exactamente la trampa: la validación no afirma el campo, afirma la forma. Todo lo que sale
    de acá valida, así que el único nodo que se puede poner rojo es el que mira **el valor**.

    Vacío quiere decir que el esquema no admite ningún otro valor —un `const`, o un objeto con
    propiedades obligatorias, donde el único mutante posible sería inventar el objeto entero—. Eso
    no es un hueco: es un campo que el esquema ya fija, y el censo lo dice con otra palabra.
    """
    if "const" in sub:
        return []
    if isinstance(sub.get("enum"), list):
        return list(sub["enum"])
    tipos = _tipos(sub)
    candidatos: list = []
    if "object" in tipos and not (sub.get("required") or []):
        candidatos.append({})
    if "array" in tipos:
        minimo = int(sub.get("minItems", 0))
        if minimo == 0:
            candidatos.append([])
        candidatos.append([_ejemplo(sub.get("items", {}))] * max(minimo, 1))
    if "boolean" in tipos:
        candidatos += [True, False]
    if "integer" in tipos:
        candidatos += _enteros_validos(sub)
    elif "number" in tipos:
        candidatos += [1234.0, 4321.0]
    if "string" in tipos:
        candidatos += _cadenas_validas(sub)
    if "null" in tipos:
        candidatos.append(None)
    return candidatos


def _huella_del_censo(raiz: Path) -> str:
    """sha256 de lo que hace que un censo siga valiendo: el contrato, el build y la suite.

    Sin esto el censo es una foto que envejece sola: se corre una vez, después alguien cambia el
    paso 3 o borra una aserción, y la compuerta sigue leyendo el mismo `EVIDENCIA/censo.json` en
    verde. Con esto, cualquier `.py` de `agente/` o de `pruebas/` que se mueva deja la evidencia
    vieja y el chequeo vuelve a saltear —o sea, el veredicto vuelve a `parcial` hasta que alguien
    corra el censo otra vez—.
    """
    h = hashlib.sha256()
    rutas = [raiz / ESQUEMA_DE_SALIDA]
    for carpeta in ("agente", "pruebas"):
        base = raiz / carpeta
        if base.is_dir():
            rutas += [p for p in sorted(base.rglob("*.py")) if not _es_ruido(p.parts)]
    for ruta in rutas:
        try:
            h.update(ruta.relative_to(raiz).as_posix().encode("utf-8"))
            h.update(ruta.read_bytes())
        except OSError:
            h.update(b"<ilegible>")
    return h.hexdigest()


def _leer_censo(c: Contexto) -> tuple[dict | None, str]:
    """El `EVIDENCIA/censo.json` del árbol, o por qué no sirve."""
    archivo = c.raiz / CENSO
    if not archivo.is_file():
        return None, (
            f"el censo no corrió en este árbol: no hay {CENSO.as_posix()}. Corrélo con "
            f"`{_como_correr(c)} --censo`, que necesita el build y tarda lo que tarde la suite "
            f"por cada campo")
    try:
        datos = json.loads(_texto(archivo))
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"{CENSO.as_posix()} no es JSON legible: {e}. Volvé a correr `--censo`"
    if not isinstance(datos, dict) or not isinstance(datos.get("campos"), list):
        return None, f"{CENSO.as_posix()} no tiene la forma que escribe `--censo`. Corrélo otra vez"
    return datos, ""


def _como_correr(c: Contexto) -> str:
    """El comando que hay que copiar y pegar, en la forma que prescribe § 5 del contrato.

    No es `c.interprete`: ése resuelve a `.venv/bin/python3`, y el kit prescribe
    `.venv/bin/python` —o `.venv\\Scripts\\python.exe` en Windows— en los once lugares donde el
    comando está escrito. Dos formas del mismo comando dando vueltas es cómo empieza la próxima
    tabla de desempate.
    """
    if (c.raiz / ".venv/Scripts/python.exe").is_file():
        return ".venv\\Scripts\\python.exe scripts\\auditar.py"
    if (c.raiz / ".venv/bin/python").is_file():
        return ".venv/bin/python scripts/auditar.py"
    return f"{c.interprete} scripts/auditar.py"


def chequeo_censo_campos(c: Contexto, r: Reporte) -> None:
    """Cada campo del contrato de salida: o lo afirma una prueba, o está escrito por qué no.

    **El defecto que cierra.** `contratos/salida.schema.json` declara cuarenta y pico de campos y
    la suite los afirma de a uno, a mano, cuando alguien se acuerda. Siete rondas seguidas
    encontraron el mismo agujero con otro campo adentro: `contacto.numero` en cadena vacía,
    `objecion_en_playbook` siempre en falso, `urgencia` fija en nulo, `crm.proximo_paso`
    descartado. Los siete se midieron igual —romper el campo en el build y mirar la suite entera
    quedar en verde—, y los siete pasaron con la compuerta en `PASS`. Escribir la aserción número
    treinta y uno no arregla eso: la ronda que viene aparecen tres campos más. Lo que lo arregla es
    preguntar por los que **no** están, que es lo mismo que hace el chequeo 14 con los módulos.

    **Cómo se establece que una prueba afirma un campo, y por qué no se puede fingir.** No por
    nombre y no por leer la suite. Se mide: `--censo` corre la suite una vez por campo con **un
    solo cambio** en el documento que devuelve `correr_ciclo` —el valor de ese campo, y nada más—,
    y mira si algún nodo se pone rojo.

    El valor que inyecta **valida contra el mismo esquema**: otro miembro del `enum`, otro entero
    adentro del rango, otra fecha con forma de fecha. Ahí está todo el asunto. Una prueba que sólo
    valida el documento contra `contratos/salida.schema.json` no se puede poner roja con un mutante
    que valida, así que la validación —que es la trampa en la que este kit ya cayó: cuarenta campos
    «cubiertos» porque el documento entero validaba— no cuenta como aserción de nadie. Sólo se pone
    rojo el nodo que mira el valor.

    **Qué garantiza.** Que un campo marcado `afirmado` tiene por lo menos un nodo que se pone rojo
    cuando ese campo, y sólo ese campo, cambia de valor en la salida. O sea que la aserción existe
    y que se puede poner roja, que es la única definición de prueba que este kit acepta.

    **Qué no garantiza, y hay que decirlo entero:**

    - **No dice que la aserción sea la correcta.** Un nodo que exija `score == 0` sale `afirmado`
      igual que uno que verifique los umbrales. El censo mide que alguien mira, no que mire bien.
    - **Mide el corpus que hay.** `sin_asercion` quiere decir «ningún nodo de esta suite, con estos
      fixtures y sobre este build». Un campo que sólo aparece en un caso que nadie escribió sale
      `sin_asercion` y lo que falta es el caso, no la aserción.
    - **Mira una sola superficie: el documento de salida.** Una prueba que afirma lo que salió al
      cable —el texto que vio el transporte, la fila que vio el CRM— y nunca lee la salida no
      cuenta acá, y hace bien en existir: son dos cosas distintas y el contrato declara ésta.
    - **Un rojo puede ser un reventón y no una aserción.** Si el mutante hace explotar un
      `fromisoformat()`, el nodo se pone rojo sin afirmar nada. Por eso los valores son plausibles
      —fecha por fecha, enum por enum—, y por eso el censo guarda cuál inyectó: el rojo se puede
      volver a leer.
    - **Dos mutantes por campo, no todos.** Si el primero sale verde se prueba uno más, por el otro
      extremo de la lista. Le pega al valor que la prueba espera es un modo de falla real y esto lo
      hace chico, no lo elimina.
    - **No mira nada de la entrada.** `contratos/entrada.schema.json` no tiene censo, y uno de los
      siete agujeros —ignorar `mensaje.recibido_en`— vivía justo ahí.

    **Lo que hace este chequeo con eso.** Nada caro: lee `EVIDENCIA/censo.json`, lo cruza contra
    los campos que declara el esquema hoy y contra `SIN_ASERCION`, y marca al que no está en
    ninguno de los dos lados. La corrida cara es `--censo` y se pide aparte, por lo mismo que
    `/probar` está aparte de `/revisar`.

    Sin evidencia **saltea**, y está en `EXIGIBLES_CON_AGENTE`: con el build en el árbol, un censo
    que no corrió deja el veredicto en `parcial`, que es exactamente lo que es —«no encontré nada,
    y algo que tenía que mirarse no se miró»—. No es `fail`: no hay ningún hallazgo. Es la línea
    que impide que la próxima ronda vuelva a leer `PASS` sobre cuarenta campos que nadie contó.
    """
    esquema_ruta = c.raiz / ESQUEMA_DE_SALIDA
    if not esquema_ruta.is_file():
        r.error("censo/sin_esquema",
                f"falta {ESQUEMA_DE_SALIDA}: sin el contrato de salida no hay campos que censar, "
                f"y los otros dos chequeos que lo leen —16 y 17— tampoco pueden correr",
                ESQUEMA_DE_SALIDA, 0, "kit")
        return
    try:
        esquema = json.loads(_texto(esquema_ruta))
    except (json.JSONDecodeError, ValueError) as e:
        r.error("censo/esquema_ilegible", f"{ESQUEMA_DE_SALIDA} no es JSON legible: {e}",
                ESQUEMA_DE_SALIDA, 0, "kit")
        return

    campos = _campos_declarados(esquema)
    declarados = {ruta for ruta, _ in campos}

    # Primero la lista, que se puede mirar sin evidencia y es la que envejece sola.
    for ruta, motivo in SIN_ASERCION.items():
        if ruta not in declarados:
            r.error("censo/campo_inventado",
                    f"`{ruta}` está en `SIN_ASERCION` y el esquema no lo declara. O se renombró el "
                    f"campo y la lista quedó vieja, o el renglón nunca nombró nada: en los dos "
                    f"casos hay un campo real sin motivo escrito y uno inventado tapándolo",
                    "scripts/auditar.py", 0, "kit")
        if len(motivo.strip()) < 40:
            r.error("censo/lista_sin_motivo",
                    f"`{ruta}` está en `SIN_ASERCION` con un motivo de {len(motivo.strip())} "
                    f"caracteres. Una lista de campos sin motivo es la misma lista de huecos que "
                    f"había antes, ahora con permiso: el renglón tiene que decir quién lo "
                    f"afirmaría, "
                    f"con qué entrada, y qué se pierde mientras tanto",
                    "scripts/auditar.py", 0, "kit")

    datos, problema = _leer_censo(c)
    if datos is None:
        r.saltear(problema)
        return

    huella = _huella_del_censo(c.raiz)
    if datos.get("huella") != huella:
        r.saltear(
            f"{CENSO.as_posix()} se corrió sobre otro árbol: el contrato, `agente/` o `pruebas/` "
            f"cambiaron desde entonces ({datos.get('corrida', 'sin fecha')}). Un censo viejo dice "
            f"que alguien miró un código que ya no está. Corré `{_como_correr(c)} --censo` de "
            f"nuevo")
        return

    medidos = {ch.get("campo"): ch for ch in datos["campos"] if isinstance(ch, dict)}
    afirmados = [ruta for ruta in declarados
                 if medidos.get(ruta, {}).get("veredicto") == "afirmado"]
    sin_medir = [ruta for ruta in sorted(declarados) if ruta not in medidos]
    if sin_medir:
        r.error("censo/campo_sin_censar",
                f"{len(sin_medir)} campo(s) que el esquema declara y el censo no midió: "
                f"{', '.join(sin_medir[:6])}{' …' if len(sin_medir) > 6 else ''}. Es un censo a "
                f"medias, y un censo a medias no distingue «nadie lo afirma» de «no lo conté»",
                ESQUEMA_DE_SALIDA, 0, "kit")

    for ruta in sorted(declarados):
        medido = medidos.get(ruta)
        if medido is None:
            continue
        veredicto = medido.get("veredicto")
        if veredicto == "afirmado":
            if ruta in SIN_ASERCION:
                r.aviso("censo/motivo_vencido",
                        f"`{ruta}` está en `SIN_ASERCION` y el censo lo encontró afirmado por "
                        f"`{medido.get('nodo', 'un nodo')}`. Alguien escribió la prueba y no sacó "
                        f"el renglón: sacalo, o la lista pasa a ser una lista de cosas que ya no "
                        f"son ciertas", "scripts/auditar.py", 0, "kit")
            continue
        if veredicto == "no_mutable":
            continue
        if veredicto == "indeterminado":
            r.aviso("censo/campo_indeterminado",
                    f"`{ruta}` no se pudo medir: {_recorte(medido.get('detalle', ''), 200)}. No es "
                    f"un hueco ni un aprobado, es una corrida que no salió; volvé a correr "
                    f"`{_como_correr(c)} --censo --campo {ruta}`",
                    ESQUEMA_DE_SALIDA, 0, "entorno")
            continue
        if ruta in SIN_ASERCION:
            continue
        if veredicto == "no_alcanzado":
            r.error("censo/campo_sin_corpus",
                    f"`{ruta}`: el censo vio {medido.get('documentos', 0)} salida(s) del build y "
                    f"no pudo cambiarlo en ninguna —{_recorte(medido.get('detalle', ''), 200)}—. "
                    f"No es "
                    f"que nadie lo afirme: es que no hay una sola corrida de la suite donde el "
                    f"campo exista, así que la aserción no tiene dónde pararse. Lo que falta es la "
                    f"entrada que lo produce, y hasta que esté, este campo del contrato no lo mira "
                    f"nadie. Escribila, o escribí el renglón en `SIN_ASERCION`",
                    ESQUEMA_DE_SALIDA, 0, "build")
            continue
        r.error("censo/campo_sin_asercion",
                f"`{ruta}`: el censo cambió su valor en {medido.get('mutados', 0)} salida(s) del "
                f"build —a `{_recorte(str(medido.get('valor')), 60)}`, que valida contra el mismo "
                f"esquema— y la suite entera siguió verde. O sea: ningún nodo mira ese campo, y un "
                f"build que lo devuelva fijo pasa la compuerta. Cerralo con la aserción que falta, "
                f"o escribí el renglón en `SIN_ASERCION` de `scripts/auditar.py` diciendo quién lo "
                f"afirmaría y qué se pierde mientras tanto. Las dos cierran el chequeo y sólo "
                f"una es trabajo de verdad",
                ESQUEMA_DE_SALIDA, 0, "build")

    listados = [ruta for ruta in SIN_ASERCION if ruta in declarados]
    no_mutables = [ruta for ruta in declarados
                   if medidos.get(ruta, {}).get("veredicto") == "no_mutable"]
    r.decir(f"{len(declarados)} campos declarados: {len(afirmados)} afirmados por una prueba que "
            f"se puede poner roja, {len(listados)} sin aserción y con motivo escrito, "
            f"{len(no_mutables)} que el esquema ya fija")


# ─────────────────────────────────────────────────────────────────────────────
# El censo: la corrida cara, aparte de la compuerta
# ─────────────────────────────────────────────────────────────────────────────

# El plugin de pytest que hace el único cambio. Se escribe en un directorio temporal, se pasa con
# `-p`, y se borra al terminar: no vive en el árbol de nadie y no se versiona.
#
# **Por qué un gancho de importación y no un `monkeypatch`.** `pruebas/proveedor_falso.py` tiene
# `olvidar_el_build()`, que saca `agente*` de `sys.modules` para que el próximo import relea el
# entorno —lo usan las pruebas del aviso interno—. Un parche puesto sobre el módulo se pierde en
# ese momento y el resto de la corrida mide sin mutante, o sea verde de mentira. El gancho envuelve
# `correr_ciclo` **cada vez** que `agente.ciclo` se ejecuta, así que sobrevive a los reimports y
# también al `from agente.ciclo import correr_ciclo` de cualquier módulo del build: para cuando ese
# `from` corre, el atributo ya está envuelto.
#
# `functools.wraps` no es cosmética: `inspect.signature()` sigue `__wrapped__`, así que la
# verificación de la firma de `correr_ciclo` que pide `blueprint/40-pruebas.md` paso 2 ve la firma
# real y no la del envoltorio. Sin eso, el censo pondría rojo ese nodo con cada mutante y **todos**
# los campos saldrían `afirmado`.
_PLUGIN_CENSO = r'''"""Cambia un solo campo de lo que devuelve `correr_ciclo`, y nada más.

Lo escribe `scripts/auditar.py --censo` en un directorio temporal. No es parte del kit.
"""
from __future__ import annotations

import functools
import inspect
import json
import os
import sys
from pathlib import Path

CAMPO = os.environ["CENSO_CAMPO"].split("/")
CANDIDATOS = json.loads(os.environ["CENSO_CANDIDATOS"])
INFORME = Path(os.environ["CENSO_INFORME"])

CUENTA = {
    "documentos": 0, "mutados": 0, "presente": 0, "padre_ausente": 0,
    "sin_candidato": 0, "mutante_invalido": 0, "base_invalida": 0, "valores": [],
}

try:
    from jsonschema import Draft202012Validator

    _validador = Draft202012Validator(
        json.loads(Path(os.environ["CENSO_ESQUEMA"]).read_text(encoding="utf-8")))
except Exception:  # noqa: BLE001
    _validador = None

AUSENTE = object()


def _apuntar() -> None:
    INFORME.write_text(json.dumps(CUENTA, ensure_ascii=False), encoding="utf-8")


def _texto(valor) -> str:
    return json.dumps(valor, sort_keys=True, ensure_ascii=False)


def _padres(doc, camino):
    """Cada diccionario donde el campo tiene que vivir. `*` abre un elemento por ítem."""
    actuales = [doc]
    for paso in camino[:-1]:
        siguientes = []
        for nodo in actuales:
            if paso == "*":
                if isinstance(nodo, list):
                    siguientes.extend(nodo)
            elif isinstance(nodo, dict):
                hijo = nodo.get(paso, AUSENTE)
                if hijo is not AUSENTE and hijo is not None:
                    siguientes.append(hijo)
        actuales = siguientes
    return [n for n in actuales if isinstance(n, dict)]


def _mutar(doc):
    if not isinstance(doc, dict):
        return doc
    CUENTA["documentos"] += 1
    if _validador is not None and next(_validador.iter_errors(doc), None) is not None:
        CUENTA["base_invalida"] += 1
    copia = json.loads(json.dumps(doc))
    padres = _padres(copia, CAMPO)
    if not padres:
        CUENTA["padre_ausente"] += 1
        _apuntar()
        return doc
    clave = CAMPO[-1]
    puestos = []
    for padre in padres:
        actual = padre.get(clave, AUSENTE)
        if actual is not AUSENTE:
            CUENTA["presente"] += 1
        elegido = AUSENTE
        for candidato in CANDIDATOS:
            if actual is AUSENTE or _texto(candidato) != _texto(actual):
                elegido = candidato
                break
        if elegido is AUSENTE:
            CUENTA["sin_candidato"] += 1
            continue
        padre[clave] = elegido
        puestos.append(_texto(elegido))
    if not puestos:
        _apuntar()
        return doc
    if _validador is not None and next(_validador.iter_errors(copia), None) is not None:
        # Un mutante que no valida pone rojo a cualquier prueba que valide el documento, y eso
        # no afirma el campo: afirma la forma. Se descarta y se cuenta.
        CUENTA["mutante_invalido"] += 1
        _apuntar()
        return doc
    CUENTA["mutados"] += 1
    for valor in puestos:
        if valor not in CUENTA["valores"] and len(CUENTA["valores"]) < 8:
            CUENTA["valores"].append(valor)
    _apuntar()
    return copia


def _envolver(modulo) -> None:
    real = getattr(modulo, "correr_ciclo", None)
    if real is None or getattr(real, "_censo", False):
        return
    if inspect.iscoroutinefunction(real):

        @functools.wraps(real)
        async def envuelto(*a, **kw):
            return _mutar(await real(*a, **kw))

    else:

        @functools.wraps(real)
        def envuelto(*a, **kw):
            resultado = real(*a, **kw)
            if inspect.isawaitable(resultado):

                async def _esperar():
                    return _mutar(await resultado)

                return _esperar()
            return _mutar(resultado)

    envuelto._censo = True
    modulo.correr_ciclo = envuelto


class _Cargador:
    def __init__(self, real):
        self._real = real

    def create_module(self, spec):
        return self._real.create_module(spec)

    def exec_module(self, modulo):
        self._real.exec_module(modulo)
        _envolver(modulo)

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)


class _Buscador:
    def find_spec(self, nombre, ruta=None, destino=None):
        if nombre != "agente.ciclo":
            return None
        for buscador in list(sys.meta_path):
            if buscador is self:
                continue
            encontrar = getattr(buscador, "find_spec", None)
            spec = encontrar(nombre, ruta, destino) if encontrar else None
            if spec is not None and spec.loader is not None:
                spec.loader = _Cargador(spec.loader)
                return spec
        return None


def pytest_configure(config):
    sys.meta_path.insert(0, _Buscador())
    modulo = sys.modules.get("agente.ciclo")
    if modulo is not None:
        _envolver(modulo)
    _apuntar()
'''

FALLA_DE_PYTEST = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)")


def _correr_mutante(c: Contexto, temporal: Path, campo: str, candidatos: list) -> dict:
    """La suite entera con un solo campo cambiado. Devuelve qué pasó, sin interpretarlo."""
    informe = temporal / "informe.json"
    informe.write_text("{}", encoding="utf-8")
    entorno = {
        "PYTHONPATH": str(temporal),
        "CENSO_CAMPO": campo,
        "CENSO_CANDIDATOS": json.dumps(candidatos, ensure_ascii=False),
        "CENSO_INFORME": str(informe),
        "CENSO_ESQUEMA": str(c.raiz / ESQUEMA_DE_SALIDA),
    }
    codigo, salida = _correr(
        [c.interprete, "-m", "pytest", "pruebas", "-q", "-x", "-rfE", "-p", "censo_plugin"],
        cwd=c.raiz, timeout=SEGUNDOS_CENSO, entorno=entorno)
    try:
        cuenta = json.loads(informe.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        cuenta = {}
    rojos = [m.group(1) for m in
             (FALLA_DE_PYTEST.match(l.strip()) for l in salida.splitlines()) if m]
    return {"codigo": codigo, "salida": salida, "cuenta": cuenta, "rojos": rojos}


def _veredicto_del_mutante(corrida: dict) -> tuple[str, str]:
    """De una corrida a un veredicto, con el detalle que hay que leer si no es de los dos."""
    cuenta = corrida["cuenta"]
    mutados = int(cuenta.get("mutados", 0))
    if corrida["codigo"] == 1 and corrida["rojos"]:
        if not mutados:
            return "indeterminado", (
                "la suite se puso roja y el censo no llegó a cambiar ni un documento: el rojo no "
                "es del mutante")
        return "afirmado", corrida["rojos"][0]
    if corrida["codigo"] == 0:
        if not mutados:
            return "no_alcanzado", (
                f"{cuenta.get('documentos', 0)} salida(s) vistas y ninguna mutada: "
                f"{cuenta.get('padre_ausente', 0)} sin el objeto que lo contiene, "
                f"{cuenta.get('sin_candidato', 0)} sin otro valor válido, "
                f"{cuenta.get('mutante_invalido', 0)} con un mutante que no validaba")
        return "sin_asercion", ""
    return "indeterminado", _recorte(
        "\n".join(corrida["salida"].splitlines()[-6:]) or f"pytest salió con {corrida['codigo']}",
        300)


def correr_censo(c: Contexto, *, solo: str = "") -> dict:
    """Mide, campo por campo, si alguna prueba se puede poner roja por él. Ver el chequeo 23.

    Corre aparte de la compuerta porque cuesta una suite entera por campo. Lo que deja escrito es
    `EVIDENCIA/censo.json`, y el chequeo 23 lo lee.
    """
    esquema_ruta = c.raiz / ESQUEMA_DE_SALIDA
    if not esquema_ruta.is_file():
        return {"corrio": False, "motivo": f"falta {ESQUEMA_DE_SALIDA}"}
    esquema = json.loads(_texto(esquema_ruta))
    campos = _campos_declarados(esquema)
    if solo:
        campos = [(ruta, sub) for ruta, sub in campos if ruta == solo]
        if not campos:
            return {"corrio": False, "motivo": f"`{solo}` no es un campo declarado del esquema"}

    if not (c.raiz / "agente/ciclo.py").is_file():
        return {"corrio": False, "motivo": (
            f"el censo necesita el build: no existe agente/ciclo.py, así que no hay ninguna salida "
            f"que mutar y los {len(campos)} campos declarados quedan sin medir. La mitad estática "
            f"—la lista `SIN_ASERCION` contra el esquema— sí corre en el chequeo 23 sin build")}

    print(f"censo · {len(campos)} campo(s) de {ESQUEMA_DE_SALIDA}")
    print("  base · pytest pruebas -q, sin mutante")
    codigo, salida = _correr([c.interprete, "-m", "pytest", "pruebas", "-q"],
                             cwd=c.raiz, timeout=SEGUNDOS_CENSO)
    ultima = salida.splitlines()[-1] if salida else ""
    if codigo != 0:
        return {"corrio": False, "motivo": (
            f"la suite no está verde sin mutante: `{_recorte(ultima, 120)}`. Sobre una base "
            f"roja el censo no distingue el rojo del mutante del que ya estaba: no mide nada")}
    print(f"  base · {_recorte(ultima, 90)}")

    # La fixture `salida_caso_01` escribe `pruebas/salida-caso-01.json` en cada corrida, y de ahí
    # la levanta el chequeo 16. La última corrida del censo la dejaría escrita con un mutante
    # adentro: se guarda antes y se restaura después.
    escrita = c.raiz / "pruebas/salida-caso-01.json"
    antes = escrita.read_bytes() if escrita.is_file() else None

    resultados: list[dict] = []
    temporal = Path(tempfile.mkdtemp(prefix="censo-"))
    try:
        (temporal / "censo_plugin.py").write_text(_PLUGIN_CENSO, encoding="utf-8")
        for i, (ruta, sub) in enumerate(campos, 1):
            candidatos = _candidatos(sub)
            if not candidatos:
                motivo = ("`const`: el esquema no admite otro valor" if "const" in sub else
                          "objeto con propiedades obligatorias: el único mutante sería inventarlo "
                          "entero, y sus hojas se miden una por una")
                resultados.append({"campo": ruta, "veredicto": "no_mutable", "detalle": motivo})
                print(f"  [{i:02}/{len(campos)}] {ruta:34} no mutable · {motivo}")
                continue
            veredicto, detalle, cuenta, valor = "indeterminado", "", {}, None
            for intento in range(INTENTOS_POR_CAMPO):
                orden = candidatos if intento == 0 else list(reversed(candidatos))
                corrida = _correr_mutante(c, temporal, ruta, orden)
                cuenta = corrida["cuenta"]
                valores = cuenta.get("valores") or []
                valor = valores[0] if valores else None
                veredicto, detalle = _veredicto_del_mutante(corrida)
                # El segundo intento existe sólo para el verde: si el primer mutante le pegó al
                # valor que la prueba esperaba, entrar por el otro extremo lo destapa.
                if veredicto != "sin_asercion" or len(candidatos) == 1:
                    break
            mutados = int(cuenta.get("mutados", 0))
            resultados.append({
                "campo": ruta,
                "veredicto": veredicto,
                "nodo": detalle if veredicto == "afirmado" else "",
                "detalle": "" if veredicto == "afirmado" else detalle,
                "documentos": int(cuenta.get("documentos", 0)),
                "mutados": mutados,
                "presente": int(cuenta.get("presente", 0)),
                "valor": valor,
            })
            cola = detalle or f"{mutados} salida(s) mutada(s) a {valor}"
            print(f"  [{i:02}/{len(campos)}] {ruta:34} {veredicto:14} {_recorte(cola, 90)}")
    finally:
        shutil.rmtree(temporal, ignore_errors=True)
        if antes is not None:
            escrita.write_bytes(antes)
        elif escrita.is_file():
            escrita.unlink()

    return {
        "corrio": True,
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "huella": _huella_del_censo(c.raiz),
        "interprete": c.interprete,
        "base": _recorte(ultima, 120),
        "campos": resultados,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Orquestación
# ─────────────────────────────────────────────────────────────────────────────

REGISTRO = [
    # Va primero: es lo único que leen los diez comandos, y cuesta un rglob.
    ("blueprint-existe", "cada blueprint/NN-*.md citado existe y no está vacío",
     chequeo_blueprint_existe),
    ("manifiesto", "cada plantilla contra su sha256", chequeo_manifiesto),
    ("railway-arranque", "railway.json sin startCommand", chequeo_railway_arranque),
    ("claudemd-tam", f"CLAUDE.md ≤ {LIMITE_CLAUDEMD} bytes", chequeo_claudemd_tam),
    ("pines", "los números de PINES.md, el modelo y la imagen base", chequeo_pines),
    ("deps-imports", "cada import mapea a una distribución fijada", chequeo_deps_imports),
    ("deps-drivers", "el driver que vive adentro de una URL", chequeo_deps_drivers),
    ("secretos", "ninguna credencial en el árbol", chequeo_secretos),
    ("gitignore-anclado", "el núcleo verbatim sigue versionado", chequeo_gitignore_anclado),
    ("modelo", "modelos vigentes y los cuatro parámetros que dan 400", chequeo_modelo),
    ("wire-schema", "el esquema angosto y su golden", chequeo_wire_schema),
    ("http-unico", "un solo cliente HTTP, con timeout", chequeo_http_unico),
    ("enviar-unico", "todo lo que sale pasa por agente/enviar.py", chequeo_enviar_unico),
    ("agente-completo", "cada módulo que promete la tabla de 30-generacion.md",
     chequeo_agente_completo),
    ("cache-estatico", "nada variable en el prefijo del prompt", chequeo_cache_estatico),
    ("contrato", "las salidas validan y los pasos vienen 1..6", chequeo_contrato),
    ("contrato-control", "cinco mutaciones que tienen que rebotar", chequeo_contrato_control),
    ("firmas", "los fixtures crudos, con el espaciado intacto", chequeo_firmas),
    ("pruebas", "pytest pruebas -q", chequeo_pruebas),
    ("playbook", "el playbook valida y el piso está anclado", chequeo_playbook),
    # Va último y no al lado del 14 a propósito: los otros catorce archivos del blueprint citan los
    # chequeos por número —«el chequeo 13», «el chequeo 02»— y meterlo en el medio los corre a
    # todos de lugar.
    ("panel-cerrado", "toda ruta de /api/ detrás de exigir_token", chequeo_panel_cerrado),
    # Y éste después del 21 por lo mismo: los números de los chequeos se citan en los otros catorce
    # archivos del blueprint, así que uno nuevo va al final y no en el medio.
    ("rutas-del-contrato", "las diez rutas de § 3, y no hay otras", chequeo_rutas_del_contrato),
    # Y el 23 al final por lo mismo que el 22. Es el único que no mira el árbol sino lo que la
    # suite afirma sobre él, y el único que se apoya en una corrida que se pide aparte.
    ("censo-de-campos", "cada campo del contrato de salida, afirmado o escrito",
     chequeo_censo_campos),
]


# Un salteado no es un aprobado, y no todos pesan igual. Estos son los que, según el estado del
# árbol, no tienen excusa para saltear: si saltean, el veredicto es `parcial` y la salida es 3.
#
# `contrato-control` está siempre. Es el control negativo de la validación entera: mientras no
# corra, un reporte en verde no distingue «validé y está bien» de «no validé nada», y esa es
# justo la corrida en la que menos hay que confiar. Que saltee por falta de `jsonschema` no lo
# hace menos grave: es la condición exacta en la que su ausencia importa más.
#
# `blueprint-existe` también. Saltea cuando ningún SKILL.md ni CLAUDE.md cita un archivo de
# `blueprint/`, y eso no es «no aplica»: los diez comandos del kit no traen procedimiento
# adentro, lo citan. Sin una sola cita, o el kit dejó de ser este kit, o nadie miró.
#
# Y `firmas`, que no estaba en ninguna de las dos listas: apagarlo del todo —sin fixtures o sin un
# `firmas.py` que ejecutar— no llegaba ni a `parcial`. Los dos fixtures y la plantilla son núcleo
# verbatim del kit, así que están desde el primer `git clone` y antes de que exista `agente/`: acá
# no hay ninguna fase que esperar, y un salteo quiere decir que falta un archivo nuestro.
SIEMPRE_EXIGIBLES = frozenset({"contrato-control", "blueprint-existe", "firmas"})

# Y estos en cuanto `agente/` existe. Saltear porque todavía no se construyó es legítimo y está
# escrito así; saltear con el build en el árbol quiere decir que nadie miró el build.
#
# Los cuatro que se sumaron son los que tapaban al agente de mentira. `pruebas` saltea cuando no
# hay `test_*.py` o cuando falta pytest, y con un build en el árbol eso quiere decir que la suite
# entera no corrió. `wire-schema` y `contrato` saltean por falta de pydantic o de jsonschema, o
# por falta de fixtures de salida: con `agente/` construido, un contrato que no se validó nunca es
# la misma corrida en la que menos hay que confiar que `contrato-control`. Y `agente-completo`
# saltea sólo sin `agente/`: si saltea con `agente/` puesto, es que reventó adentro.
# `playbook` va por lo mismo, y con una razón propia: saltea cuando no existe `config/playbook.yaml`,
# y ese archivo lo escribe la fase 2 —antes que `agente/`—. Con el build en el árbol y sin él, o se
# salteó una fase entera o alguien lo borró; en los dos casos `entrada_desde_config()` arma una
# entrada sin un campo obligatorio del contrato. Sin esta línea el chequeo nuevo vuelve a ser lo que
# había antes: nadie mirando el playbook, ahora con un renglón que dice `salteado`.
#
# `panel-cerrado` va por lo mismo y con una razón propia: saltea sólo sin `agente/`, así que un
# salteo con el build en el árbol quiere decir que reventó adentro, y lo que dejó de mirarse es si
# el panel está abierto en una URL pública.
#
# `rutas-del-contrato` tiene un salteo legítimo más —`agente/servidor.py` todavía sin escribir, o
# sea el build a mitad de camino—, y ahí el chequeo 14 ya está en rojo por su cuenta, así que el
# veredicto no depende de esta línea. Con el servidor escrito, un salteo quiere decir que reventó
# adentro y que nadie contó las rutas.
#
# Y `censo-de-campos`, que es el que esta ronda agrega y el que más se parece a `contrato-control`:
# saltea cuando el censo no corrió, y un censo que no corrió es «nadie contó los campos del
# contrato». Sin esta línea el chequeo nuevo es opcional, y opcional es lo que fueron las siete
# rondas anteriores: la corrida sale `PASS`, el hueco sigue adentro y se descubre en la ronda que
# viene con otro campo. Con ella, la primera corrida después del build sale `parcial` y dice el
# comando exacto. `parcial` y no `fail` a propósito: no hay ningún hallazgo, hay algo sin mirar.
EXIGIBLES_CON_AGENTE = frozenset({
    "deps-imports", "deps-drivers", "modelo", "http-unico", "enviar-unico", "cache-estatico",
    "agente-completo", "pruebas", "wire-schema", "contrato", "playbook", "panel-cerrado",
    "rutas-del-contrato", "censo-de-campos",
})


def _exigidos_sin_correr(c: Contexto, chequeos: list[Chequeo]) -> list[str]:
    """Los salteados que en este árbol tenían que haber corrido."""
    exigidos = set(SIEMPRE_EXIGIBLES) | (EXIGIBLES_CON_AGENTE if c.hay_agente else set())
    return [ch.id for ch in chequeos if ch.estado == "salteado" and ch.id in exigidos]


def auditar(raiz: Path, *, publicando: bool = False) -> dict:
    c = Contexto(raiz, publicando=publicando)
    chequeos: list[Chequeo] = []
    for id_, titulo, funcion in REGISTRO:
        r = Reporte(id_, titulo)
        try:
            funcion(c, r)
        except Exception as e:  # noqa: BLE001
            # Un chequeo que revienta no puede llevarse puesto el reporte entero: el resto sí
            # corrió y esa información es la que alguien necesita para arreglar algo.
            r.error("auditoria/excepcion",
                    f"el chequeo `{id_}` levantó {type(e).__name__}: {e}. Es un defecto de "
                    f"scripts/auditar.py, no de lo que estaba mirando",
                    "scripts/auditar.py", 0, "kit")
        chequeos.append(r.cerrar())

    hallazgos = [h for ch in chequeos for h in ch.hallazgos]
    errores = [h for h in hallazgos if h.nivel == "error"]
    salteados = [ch for ch in chequeos if ch.estado == "salteado"]
    faltan = _exigidos_sin_correr(c, chequeos)
    if errores:
        veredicto = "fail"
    elif faltan:
        # Ni `pass` ni `fail`, igual que `sin_verificar` en verificar_pines.py cuando no hay red:
        # no encontré nada, y parte de lo que tenía que mirar no se miró. Decir `pass` acá es
        # decir que se revisó algo que no se revisó, y `/publicar` gatea con eso.
        veredicto = "parcial"
    else:
        veredicto = "pass"
    return {
        "repo": str(raiz),
        "corrida": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "veredicto": veredicto,
        "errores": len(errores),
        "avisos": len(hallazgos) - len(errores),
        "salteados": len(salteados),
        "exigidos_sin_correr": faltan,
        "construido": c.hay_agente,
        "publicando": c.publicando,
        "interprete": c.interprete,
        "chequeos": [ch.dict() for ch in chequeos],
        "hallazgos": [h.dict() for h in hallazgos],
    }


MARCA = {"pass": "ok      ", "fail": "FALLA   ", "salteado": "salteado"}


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _imprimir(r: dict) -> None:
    estado_arbol = "construido" if r["construido"] else "sin agente/: todavía no se construyó"
    if r.get("publicando"):
        estado_arbol += " · publicando"
    print(f"auditar · {Path(r['repo']).name} · {estado_arbol}")
    print()
    for i, ch in enumerate(r["chequeos"], 1):
        cola = ch["motivo"] or ""
        print(f"  [{MARCA[ch['estado']]}] {i:02} {ch['id']:18} {cola[:78]}")
        for h in ch["hallazgos"]:
            marca = "ERROR" if h["nivel"] == "error" else "aviso"
            sitio = f"{h['archivo']}:{h['linea']}" if h["archivo"] else "—"
            print(f"      [{marca}] {h['id']:28} {sitio:34} {h['evidencia'][:150]}")
    print()
    print(f"auditar: {r['veredicto'].upper()} · {_plural(r['errores'], 'error', 'errores')} · "
          f"{_plural(r['avisos'], 'aviso', 'avisos')} · "
          f"{_plural(r['salteados'], 'salteado', 'salteados')}")
    # Un salteado no es un aprobado, y cada uno dice arriba por qué salteó. Que se lea eso y no
    # solo el veredicto es la diferencia entre una compuerta y un sello.
    if r["salteados"]:
        print("  un salteado no es un aprobado: leé el motivo de cada uno.")
    faltan = r.get("exigidos_sin_correr") or []
    if faltan:
        uno = len(faltan) == 1
        verbo = "tenía que correr en este árbol y salteó" if uno else \
                "tenían que correr en este árbol y saltearon"
        cuales = ", ".join(faltan)
        if r["veredicto"] == "parcial":
            print(f"  parcial: {cuales} {verbo}. Con `parcial` no se publica: arreglá el motivo "
                  f"de arriba y volvé a correr.")
        else:
            # En rojo el veredicto ya lo dice todo, pero esto no se pierde: son los chequeos que
            # tampoco miraron nada, así que arreglar los errores de arriba no alcanza.
            print(f"  además, {cuales} {verbo}: arreglar lo de arriba no lo vuelve verde.")


def _escribir_evidencia(destino: Path, datos: dict) -> str:
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return ""
    except OSError as e:
        return f"no pude escribir {destino}: {e}"


def _main_censo(raiz: Path, args) -> int:
    """`--censo`: la corrida cara. Deja `EVIDENCIA/censo.json` y no emite veredicto.

    Sale 0 si midió, y 1 si no pudo medir —sin build, o con la suite roja de entrada—. No devuelve
    ni 2 ni 3 a propósito: el veredicto lo da la corrida normal, leyendo lo que esto dejó escrito.
    """
    c = Contexto(raiz)
    censo = correr_censo(c, solo=args.campo)
    if not censo.get("corrio"):
        print(f"censo: no se pudo medir. {censo.get('motivo', '')}")
        return 1

    cuenta: dict[str, int] = {}
    for campo in censo["campos"]:
        cuenta[campo["veredicto"]] = cuenta.get(campo["veredicto"], 0) + 1
    print()
    print("censo: " + " · ".join(f"{n} {v}" for v, n in sorted(cuenta.items())))
    sueltos = [ch["campo"] for ch in censo["campos"]
               if ch["veredicto"] in ("sin_asercion", "no_alcanzado")
               and ch["campo"] not in SIN_ASERCION]
    if sueltos:
        print(f"  {len(sueltos)} campo(s) sin aserción y sin motivo escrito: "
              f"{', '.join(sueltos)}.")
        print("  El chequeo 23 los va a marcar uno por uno en la corrida normal.")

    if args.campo:
        # Una medición de un solo campo no es un censo: pisar la evidencia entera con ella dejaría
        # a los otros cuarenta y dos sin medir y al chequeo 23 en rojo por algo que sí se midió.
        print("\n  --campo: medición suelta, no se escribe EVIDENCIA/censo.json")
        return 0
    destino = raiz / CENSO
    problema = _escribir_evidencia(destino, censo)
    print(f"  {problema}" if problema else f"  evidencia: {destino}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="La compuerta del cerrador de WhatsApp. Sin red y sin credenciales.")
    p.add_argument("--raiz", type=Path, default=RAIZ, help="raíz del kit (default: este repo)")
    p.add_argument("--formato", choices=("texto", "json"), default="texto")
    p.add_argument("--json", action="store_true", help="atajo de --formato json")
    # Sin `type=Path` a propósito: `Path("")` es `Path(".")`, que es un directorio, así que
    # `--evidencia ""` —lo que el propio `help` ofrece para no escribir nada— terminaba
    # intentando escribir el reporte encima de la carpeta actual y contestando «Is a directory».
    # La cadena vacía se mira antes de convertirla.
    p.add_argument("--evidencia", default=None,
                   help=f"dónde escribir el reporte (default: {EVIDENCIA}). Vacío para no escribir")
    # La corrida que autoriza el `git push` del kit. Lo único que cambia es el chequeo 09: una ruta
    # del núcleo verbatim fuera del índice de git pasa de aviso a error, porque acá ya no hay
    # ninguna construcción en curso —es el estado que va a recibir el que clone—.
    p.add_argument("--publicando", action="store_true",
                   help="antes de publicar: el núcleo sin rastrear pasa de aviso a error")
    # La corrida cara, aparte: una suite entera por campo del contrato de salida. No corre los 23
    # chequeos; deja `EVIDENCIA/censo.json` y el chequeo 23 lo lee en la corrida normal. Ver el
    # docstring de `chequeo_censo_campos`.
    p.add_argument("--censo", action="store_true",
                   help="mide campo por campo si alguna prueba se puede poner roja por él")
    p.add_argument("--campo", default="",
                   help="con --censo: un solo campo, por ruta (ej: respuesta/objecion_en_playbook)")
    args = p.parse_args(argv)

    raiz = args.raiz.resolve()
    if not raiz.is_dir():
        print(f"No existe el directorio {raiz}", file=sys.stderr)
        return 1

    if args.censo:
        return _main_censo(raiz, args)
    if args.campo:
        print("--campo es de --censo: solo, no hace nada. Ver el chequeo 23", file=sys.stderr)
        return 1

    r = auditar(raiz, publicando=args.publicando)

    escribir = args.evidencia != ""
    destino = Path(args.evidencia) if args.evidencia is not None else raiz / EVIDENCIA
    problema = _escribir_evidencia(destino, r) if escribir else ""

    if args.json or args.formato == "json":
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        _imprimir(r)
        if escribir:
            print(f"  {problema}" if problema else f"  evidencia: {destino}")

    # Tres veredictos, tres salidas. `parcial` sale distinto de 0 a propósito: quien la invoque
    # desde un script tiene que poder frenar sin leer el texto, y `/publicar` gatea con esto.
    return {"pass": 0, "parcial": 3, "fail": 2}[r["veredicto"]]


if __name__ == "__main__":
    sys.exit(main())
