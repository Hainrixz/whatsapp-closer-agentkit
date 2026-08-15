# Plantillas

Lo que hay acá se copia con `cp`. No se reescribe, no se adapta, no se mejora.

Una implementación plausible pero mal escrita de estos archivos es indetectable. Instala,
construye, despliega, y falla después, con un error que no nombra a nadie: el pin de `starlette`,
el `exec` del `CMD`, `asyncpg` que no aparece en ningún `import`, la clave que **no** está en
`railway.json`. Nada de eso se nota leyendo el archivo generado. Por eso van por hash y no por
criterio.

La lista completa —ruta, hash, destino y placeholders permitidos de cada una— está en
`MANIFIESTO.json`. Es el registro; esta página no lo repite.

## Infra

| Plantilla | Va a | Qué sostiene |
|---|---|---|
| `infra/requirements.txt` | `requirements.txt` | Los 28 pines de `PINES.md`, todos con `==` |
| `infra/Dockerfile` | `Dockerfile` | `python:3.12-slim` fijada y el `CMD` en forma shell |
| `infra/railway.json` | `railway.json` | Builder, healthcheck y política de reinicio |

Tres decisiones de `railway.json` que se pueden querer cambiar, y lo que cuestan:

- `healthcheckTimeout: 120` — segundos. Alcanza para levantar y migrar, y falla rápido si no.
- `numReplicas: 1` — el recordatorio de 24 h lo programa APScheduler **adentro del proceso**.
  Con dos réplicas, el mismo recordatorio sale dos veces.
- `restartPolicyType: "ON_FAILURE"` — reinicia cuando el proceso muere, no en loop eterno.

## La regla

Cada edición a una plantilla exige volver a correr:

```bash
python3 scripts/hash_plantillas.py --escribir
```

Si no, `--verificar` sale en rojo con **error del kit**, que es lo correcto: el manifiesto quedó
viejo por algo nuestro. El otro mensaje, **error del build**, dice que el archivo generado se
apartó de su plantilla y se arregla copiándola de nuevo. Son dos mensajes distintos a propósito:
sin esa diferencia, alguien debuggea una hora su proyecto por un defecto del kit.

## Por qué `railway.json` no tiene `startCommand`

Porque pisa el `CMD` del Dockerfile.

El `CMD` es `sh -c "exec uvicorn … --port ${PORT:-8000}"`. Railway inyecta `PORT` y el valor
cambia entre despliegues; el shell lo resuelve al arrancar. Un `startCommand` con el puerto
escrito a mano deja la app escuchando en otro lado: el healthcheck no contesta nunca y lo único
que vas a leer es `service unavailable`, sin un error que diga qué pasó.

Una ausencia no se puede verificar por hash. Si alguien agrega la clave, el hash cambia y el
manifiesto lo ve, pero el mensaje solo dice "no coincide" y no nombra la causa; y si el
`railway.json` del proyecto se escribió sin copiar esta plantilla, el manifiesto ni lo mira. Por
eso la compuerta la busca aparte: es el chequeo `railway-arranque` de `scripts/auditar.py`, y
mira esta plantilla y el `railway.json` del build, a cualquier profundidad de la clave.

A mano es esto:

```bash
grep -q '"startCommand"' railway.json && echo "railway.json trae startCommand: pisa el CMD"
```

## Una plantilla nueva

El destino sale de la carpeta, no del archivo: `CARPETAS`, en `scripts/hash_plantillas.py`, dice
adónde va cada una dentro del proyecto de quien instala. Agregar un archivo a una carpeta que ya
está declarada no pide tocar código: alcanza con `--escribir`. Una carpeta nueva sí se declara
primero, y hasta que se declare el script se detiene y dice cuál es.
