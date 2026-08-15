# Mapa del blueprint

Éste es el índice, y es lo único que se lee entero. Después abrís **un archivo por fase**.

## Los quince archivos

**El número del nombre no es el orden.** El orden es la columna «Fase», y cada archivo lo repite
al cerrar con su línea `**Próximo archivo:**`. Los nombres de esta tabla son los del disco: corré
`ls blueprint/` y tienen que darte estos quince. Si en algún lado leés un nombre que no está acá,
no lo busques ni lo inventes: `blueprint/00-contrato.md` § 1 tiene la tabla que traduce cada
nombre muerto al real.

| # | Archivo | Fase | Qué deja hecho |
|---|---|---|---|
| 1 | `blueprint/00-mapa.md` | primero | qué archivo abrir y cómo se retoma |
| 2 | `blueprint/00-contrato.md` | primero | el desempate: nombres, orden, rutas y dueños |
| 3 | `blueprint/10-entorno.md` | 1 | Python del rango de `PINES.md`, `.venv` con las 28 dependencias, la clave |
| 4 | `blueprint/20-entrevista.md` | 2 | once de las doce preguntas contestadas y guardadas, en tres tramos |
| 5 | `blueprint/25-playbook.md` | 2 | Q4: objeciones con respuesta, tono y tratamiento (`tú`/`vos`/`usted`) |
| 6 | `blueprint/30-generacion.md` | 3 | plantillas por hash, el árbol de `agente/`, un cliente HTTP con `timeout=`, la salida y el prompt |
| 7 | `blueprint/31-proveedores.md` | 3 | `meta`, `zernio` o `demo`, el único `enviar()`, la firma sobre el **cuerpo crudo** y el dedupe por id |
| 8 | `blueprint/32-multimodal.md` | 3 | el audio transcripto, la imagen leída, y los cuerpos de los pasos 1, 2, 3 y 6 |
| 9 | `blueprint/33-agenda.md` | 4 | el evento y el recordatorio 24 h antes |
| 10 | `blueprint/34-crm.md` | 4 | la tabla `leads` y el paso 5 escribiendo en ella, en `borrador` |
| 11 | `blueprint/35-panel-api.md` | 4 | `agente/servidor.py` con sus diez rutas, la API detrás de su token y el panel |
| 12 | `blueprint/40-pruebas.md` | 5 | `agente/ciclo.py`, y `caso-01.md` contra `demo` con sus seis aserciones |
| 13 | `blueprint/90-auditoria.md` | compuerta | `auditar.py` en `pass` y `EVIDENCIA/gates.json` escrito |
| 14 | `blueprint/50-despliegue.md` | 6 | local o Railway arriba y el webhook dado de alta |
| 15 | `blueprint/60-bandeja.md` | después | los borradores de a uno y los cinco pisos de `/soltar` |

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
nadie definió. Están los veinticinco en `blueprint/00-contrato.md` § 10, una línea cada uno y en
castellano llano. La regla: **cada término se explica la primera vez que aparece en cada archivo**
—entre guiones largos y con la remisión pegada— y después, en ese archivo, se usa pelado.

Los dos que ya usaste en la tabla de arriba:

- **cuerpo crudo** — los bytes exactos de la petición, tal como llegaron por el cable, antes de
  parsearlos. La firma se calcula sobre eso y sobre nada más.
- **compuerta** — `scripts/auditar.py`. Veintitrés chequeos, tres veredictos, y nada se publica sin
  `pass`.

## Contrato de reanudación

Después de cada paso de fase y de cada archivo escrito se actualiza `.wca-estado.json`: la fase
en curso, las respuestas de la entrevista y el **sha256 de cada archivo escrito**. Es local y no
va a git. Ningún valor de credencial va ahí: van los nombres de las variables y si están puestas.

Si se corta, `/seguir` reconcilia contra el disco antes de escribir: por cada archivo anotado, si
existe y si el hash coincide. **Un archivo que cambió no se reescribe en silencio, nunca.** Se
dice qué cambió, qué se perdería, y se espera confirmación archivo por archivo.

## La regla de oro

Leé un archivo por fase, no los quince. Cargarlos todos gasta el contexto que la construcción
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

**Tenés que ver.** Una de dos.

`SIN ESTADO`: la construcción es nueva. Seguí la cadena desde arriba: abrí
`blueprint/00-contrato.md`, que son diez apartados de referencia y un paso de verificación, y de
ahí a `blueprint/10-entorno.md`, que es la fase 1 y el primer archivo que hace algo en esta
máquina.

O un JSON con `fase` y `archivos`: quedó a medias. Buscá esa fase en la tabla de arriba, abrí ese
archivo, ése solo, y seguí el procedimiento de `/seguir`.

**Si falla.**

- `Expecting value`, o el JSON sale cortado: quedó a medio escribir. No lo borres, renombralo a
  `.wca-estado.json.roto` y arrancá por `blueprint/10-entorno.md`. Lo ya construido se detecta
  leyendo el árbol, no el estado.
- `fase` trae un nombre que no está en la tabla: lo escribió otra versión del kit. Decí qué valor
  trae y esperá, no adivines la equivalencia.
- `fase` trae un **nombre de archivo** que no aparece en `ls blueprint/`. Son los seis nombres
  muertos que quedaron dando vueltas de una versión anterior del kit, y cada uno tiene su
  equivalente real en la tabla de `blueprint/00-contrato.md` § 1. Traducilo ahí, no adivines.
- `cat` no existe (Windows sin shell POSIX): leé el archivo con la herramienta Read, y seguí con
  el mismo shell el resto de la construcción.

---

**Próximo archivo:** `blueprint/00-contrato.md`. Es el desempate cuando dos archivos dicen cosas
distintas sobre lo mismo, y cierra mandándote a `blueprint/10-entorno.md`, que es donde arranca la
construcción de verdad.
