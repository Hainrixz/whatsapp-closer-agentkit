# Mapa del blueprint

Éste es el índice, y es lo único que se lee entero. Después abrís **un archivo por fase**.

## Los dieciséis archivos

**El número del nombre no es el orden.** El orden es la columna «Fase», y cada archivo lo repite
al cerrar con su línea `**Próximo archivo:**`. Los nombres de esta tabla son los del disco: corré
`ls blueprint/` y tienen que darte estos dieciséis. Si en algún lado leés un nombre que no está
acá, no lo busques ni lo inventes: `blueprint/00-contrato.md` § 1 tiene la tabla que traduce cada
nombre muerto al real.

La columna «`fase` en el estado» es la otra traducción, y va para el otro lado: de lo que quedó
escrito en `.wca-estado.json` al archivo que hay que abrir para seguir. Sin ella, `/seguir` lee
una palabra y no tiene con qué cruzarla.

| # | Archivo | Fase | `fase` en el estado | Qué deja hecho |
|---|---|---|---|---|
| 1 | `blueprint/00-mapa.md` | primero | no escribe | qué archivo abrir y cómo se retoma |
| 2 | `blueprint/00-contrato.md` | primero | no escribe | el desempate: nombres, orden, rutas y dueños |
| 3 | `blueprint/05-arranque.md` | 0 | `arranque` | el terreno medido, el costo dicho y el destino elegido |
| 4 | `blueprint/10-entorno.md` | 1 | `entorno` | Python del rango de `PINES.md`, `.venv` con las 30 dependencias, la clave |
| 5 | `blueprint/20-entrevista.md` | 2 | `entrevista`, después `tramo-1-listo` | once de las doce preguntas contestadas y guardadas, en tres tramos |
| 6 | `blueprint/25-playbook.md` | 2 | no escribe: es sub-paso de la fase 2 y se entra dos veces | Q4: objeciones con respuesta, tono y tratamiento (`tú`/`vos`/`usted`) |
| 7 | `blueprint/30-generacion.md` | 3 | `generacion` | plantillas por hash, el árbol de `agente/`, un cliente HTTP con `timeout=`, la salida y el prompt |
| 8 | `blueprint/31-proveedores.md` | 3 | `proveedores` | `meta`, `zernio` o `demo`, el único `enviar()`, la firma sobre el **cuerpo crudo** y el dedupe por id |
| 9 | `blueprint/32-multimodal.md` | 3 | `multimodal` | el audio transcripto, la imagen leída, y los cuerpos de los pasos 1, 2, 3 y 6 |
| 10 | `blueprint/33-agenda.md` | 4 | `agenda` | el evento y el recordatorio 24 h antes |
| 11 | `blueprint/34-crm.md` | 4 | `crm` | la tabla `leads` y el paso 5 escribiendo en ella, en `borrador` |
| 12 | `blueprint/35-panel-api.md` | 4 | `panel` | `agente/servidor.py` con sus diez rutas, la API detrás de su token y el panel |
| 13 | `blueprint/40-pruebas.md` | 5 | `pruebas` | `agente/ciclo.py`, y `caso-01.md` contra `demo` con sus seis aserciones |
| 14 | `blueprint/90-auditoria.md` | compuerta | no escribe | `auditar.py` en `pass` y `EVIDENCIA/gates.json` escrito |
| 15 | `blueprint/50-despliegue.md` | 6 | `despliegue` | local o Railway arriba y el webhook dado de alta |
| 16 | `blueprint/60-bandeja.md` | después | no escribe | los borradores de a uno y los cinco pisos de `/soltar` |

Tres lecturas que parecen al revés y son correctas:

- **`blueprint/00-contrato.md` no es una fase.** Es la referencia de desempate, y no se lee entera
  para construir: se abre cuando hay una duda de nombre, de orden, de ruta o de dueño. Está de
  segunda porque conviene saber que existe antes de necesitarla.
- **`blueprint/90-auditoria.md` corre antes que `blueprint/50-despliegue.md`.** El 50 arranca con
  «entrás con `/revisar` en `pass`», y el 90 cierra con «con `pass`, y sólo con `pass`, seguís a
  `/publicar`». Lleva el 90 porque también es el archivo que `/revisar` abre cualquier día, no
  porque vaya último.
- **`blueprint/25-playbook.md` se entra dos veces**: desde `blueprint/20-entrevista.md` en la
  primera corrida, y desde `/playbook` cualquier otro día. En el segundo caso no hay próximo
  archivo: se vuelve a quien llamó.

## Los cuatro tiempos

Cada paso viene así: **Objetivo**, qué queda cierto. **Hacé esto**, el comando, copiable. **Tenés
que ver**, la salida literal, no "debería andar". **Si falla**, cada modo de falla con su arreglo.

El cuarto existe porque las computadoras son distintas. Un paso sin **Si falla** te deja frente a
una pantalla que dice que no y ninguna salida. No pases al siguiente sin cumplir **Tenés que ver**.

## El glosario

El kit usa «webhook», «cuerpo crudo», «dedupe» y una veintena más de términos que en su momento
nadie definió. Están los veintiocho en `blueprint/00-contrato.md` § 10, una línea cada uno y en
castellano llano. La regla: **cada término se explica la primera vez que aparece en cada archivo**
—entre guiones largos y con la remisión pegada— y después, en ese archivo, se usa pelado.

Los dos que ya usaste en la tabla de arriba:

- **cuerpo crudo** — los bytes exactos de la petición, tal como llegaron por el cable, antes de
  parsearlos. La firma se calcula sobre eso y sobre nada más.
- **compuerta** — `scripts/auditar.py`. Veintitrés chequeos, tres veredictos, y nada se publica sin
  `pass`.

## Contrato de reanudación

Después de cada paso de fase y de cada archivo escrito se actualiza `.wca-estado.json`: la fase
en curso, las respuestas de la entrevista, el **sha256 de cada archivo escrito**, y `version`, el
número de formato del archivo —hoy `1`—, que escribe la fase 0 cuando lo crea. Es local y no va a
git. Ningún valor de credencial va ahí: van los nombres de las variables y si están puestas.

**El campo `fase` no guarda el número de la fase: guarda una palabra.** Esa palabra es la de la
columna «`fase` en el estado», y cada una aparece en una fila y en una sola. `"fase": "crm"` se
traduce a `blueprint/34-crm.md`, no a la fase 4 entera; `"fase": "entorno"` a
`blueprint/10-entorno.md`. Traducir por el número no funciona: ningún archivo escribe `1`, `2` ni
`compuerta`.

Cinco archivos no escriben `fase` y por eso su celda dice «no escribe»: los dos del principio, la
compuerta, la bandeja y `blueprint/25-playbook.md`. Los cuatro primeros porque no son una fase que
se retome. El playbook porque es un sub-paso de la fase 2 al que se entra dos veces —desde la
entrevista y desde `/playbook`—, así que un valor propio dejaría el estado diciendo dos cosas: lo
que anota son sus propias claves, `playbook.camino` y `playbook.listo`. Si se cortó adentro de
alguno de esos cinco, el último valor anotado es el del archivo anterior: abrí ése y seguí su
línea `**Próximo archivo:**`.

**Una palabra que no está en ninguna fila la escribió otra versión del kit.** Decila tal cual y
esperá. No la mapees por parecido: `entorno` y `entrevista` empiezan igual y son dos archivos
distintos.

Si se corta, `/seguir` reconcilia contra el disco antes de escribir: por cada archivo anotado, si
existe y si el hash coincide. **Un archivo que cambió no se reescribe en silencio, nunca.** Se
dice qué cambió, qué se perdería, y se espera confirmación archivo por archivo.

## La regla de oro

Leé un archivo por fase, no los dieciséis. Cargarlos todos gasta el contexto que la construcción
necesita al final. `blueprint/00-contrato.md` es la excepción por el otro lado: no se lee entero
nunca, se abre en la sección que resuelve la duda que tenés.

## Dónde parar

La compuerta es `blueprint/90-auditoria.md`, y corre **antes** del despliegue, no después. Nada
queda listo sin ese `pass`, y un chequeo salteado no es un chequeo aprobado.

---

### Paso 1 · Abrí el estado antes de tocar nada

**Objetivo.** Sabés si la construcción es nueva o quedó a medias, y con qué archivo seguís.

**Hacé esto.**

```bash
cat .wca-estado.json 2>/dev/null || echo "SIN ESTADO"
```

**Tenés que ver.** Una de tres. Que el archivo exista no quiere decir que quedó a medias.

`SIN ESTADO`: la construcción es nueva. Seguí la cadena desde arriba: abrí
`blueprint/00-contrato.md`, que son trece apartados de referencia y un paso de verificación, y de
ahí a `blueprint/05-arranque.md`, que es la fase 0: mide el terreno, dice lo que cuesta y lo que
tarda, y te hace elegir destino. No instala nada. El primero que toca esta máquina es
`blueprint/10-entorno.md`, la fase 1.

Un JSON con `fase` en `arranque` o en `entorno`: sigue siendo la primera corrida. Lo dejaron ahí
`blueprint/05-arranque.md` y `blueprint/10-entorno.md`, que anotan el estado al cerrar su fase, así
que el archivo existe sin que nada haya quedado a medias. No es una reanudación y `/seguir` no va
acá: abrí el archivo de esa fila y seguí la cadena desde ahí.

Un JSON con `fase` en cualquier otra palabra: eso sí quedó a medias. `fase` trae una palabra, no
un número. Buscá esa palabra en la columna «`fase` en el estado» de la tabla de arriba, abrí el
archivo de esa fila, ése solo, y seguí el procedimiento de `/seguir`.

**Si falla.**

- `Expecting value`, o el JSON sale cortado: quedó a medio escribir. No lo borres, renombralo a
  `.wca-estado.json.roto` y arrancá por `blueprint/05-arranque.md`. Repetir la fase 0 no rompe
  nada: mide y pregunta, no instala. Lo ya construido se detecta leyendo el árbol, no el estado.
- `fase` trae una palabra que no está en la columna «`fase` en el estado»: lo escribió otra
  versión del kit. Decí qué valor trae y esperá, no adivines la equivalencia por parecido.
- `fase` trae un **nombre de archivo** que no aparece en `ls blueprint/`. Son los seis nombres
  muertos que quedaron dando vueltas de una versión anterior del kit, y cada uno tiene su
  equivalente real en la tabla de `blueprint/00-contrato.md` § 1. Traducilo ahí, no adivines.
- `cat` no existe (Windows sin shell POSIX): leé el archivo con la herramienta Read, y seguí con
  el mismo shell el resto de la construcción.

---

**Próximo archivo:** `blueprint/00-contrato.md`. Es el desempate cuando dos archivos dicen cosas
distintas sobre lo mismo, y cierra mandándote a `blueprint/05-arranque.md`, la fase 0: el terreno
medido y el destino elegido antes de que se instale nada.
