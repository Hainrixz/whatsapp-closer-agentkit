---
name: start
description: La puerta de entrada del kit — de un clon recién bajado a un cerrador andando, local o en Railway.
disable-model-invocation: true
---

# Start

Ocho tiempos, de un clon recién bajado a alguien hablando con su cerrador.

## Primero el estado, antes de preguntar nada

Buscá `.wca-estado.json` en la raíz. Es lo primero que hacés. **Son tres casos y no dos**, los
mismos que separa el paso 1 de `blueprint/20-entrevista.md`: que el archivo exista no quiere decir
que esto sea una reanudación.

**Si existe y `fase` no es `arranque` ni `entorno`**, es una reanudación. Decilo, pasá al
procedimiento de `/seguir` y seguí desde la fase que trae el estado. Nada que ya esté contestado
ahí se vuelve a preguntar.

**Si existe y `fase` dice `arranque` o `entorno`**, sigue siendo este arranque, cortado a la
mitad: el archivo lo escribió el tiempo 0 o el tiempo 2 de acá abajo, que son las dos primeras
fases que escriben el estado. Seguí por el tiempo que sigue al que quedó anotado y no vuelvas a
preguntar lo que ya está. La traducción de esa palabra al archivo que hay que abrir es la columna
«`fase` en el estado» de `blueprint/00-mapa.md`.

**Si no existe**, la cadena arranca en tres archivos, en este orden:

1. `blueprint/00-mapa.md` — el índice y el contrato de reanudación. Es el que manda `CLAUDE.md`,
   y el único que traduce cada `fase` del estado al archivo que hay que abrir.
2. `blueprint/00-contrato.md` — el desempate: nombres, orden, rutas y dueños. No se lee entero.
3. `blueprint/05-arranque.md` — la fase 0, el tiempo 0 de acá abajo.

El paso 1 de `blueprint/00-mapa.md` vuelve a buscar el estado. Ya lo buscaste: no lo repitas,
decí que salió `SIN ESTADO` y seguí.

## Los ocho tiempos

`/start` no trae procedimiento propio salvo el arranque y el cierre. Abre el archivo que toca,
lo sigue, y no pasa al siguiente hasta que se cumpla lo que ahí dice «Tenés que ver».

Los archivos son los mismos que recorre `/armar-cerrador`, en el mismo orden: `/start` no tiene
una cadena aparte. Lo que agrega alrededor es el arranque —el estado y los tres archivos de acá
arriba—, el corte del tiempo 5 y el cierre del tiempo 7. Y cambia una sola cosa adentro: el orden
del tiempo 3, explicado ahí mismo.

- **0 · El terreno** — `blueprint/05-arranque.md`, después de los dos archivos de arriba. Mide
  sistema, Python en el rango de `PINES.md`, Claude Code, y que el árbol sea un clon de git y no
  un ZIP. No instala nada. Cierra diciendo qué va a costar y cuánto va a tardar.
- **1 · El destino** — `blueprint/05-arranque.md`. Dónde va a vivir, local o Railway, y por
  dónde entran los mensajes: `demo`, `meta` o `zernio`.
- **2 · El entorno** — `blueprint/10-entorno.md`. El `.venv`, las dependencias y la clave.
- **3 · La entrevista** — `blueprint/20-entrevista.md` y `blueprint/25-playbook.md`, en este
  orden y no en otro:
  - **Q1 a Q3** — tramo 1 de `blueprint/20-entrevista.md`: qué vende el negocio, con qué nombre
    firma el agente, y el tratamiento con el que le habla a un cliente (`tú`, `vos` o `usted`).
  - **Q5 a Q9** — tramo 2 del mismo archivo: catálogo con precios, rango de precio,
    disponibilidad, palabras de escalación y canal interno. Cuando el tramo 2 termina vuelve a
    quien lo llamó: acá, a este mismo tiempo 3, que sigue con Q4.
  - **Q4** — `blueprint/25-playbook.md`: las objeciones y el tono.

  **Por qué Q4 va última.** El playbook llena `{producto}` y `{precio}` con lo que contestaron Q5,
  y `{horario_1}` con lo que contestaron Q7. Corrido antes, esos tres huecos quedan abiertos, y el
  cerrador que se muestra en el corte del tiempo 5 no puede decir un precio ni ofrecer un horario.

  **Por qué el tramo 2 corre acá y no otro día.** El «Próximo archivo» del tramo 1 salta directo
  al playbook, y `/start` se aparta de eso a propósito. Esa línea está escrita para
  `/armar-cerrador`, donde Q5 a Q9 las abre `/configurar` cualquier otro día. Acá van seguidas
  porque ninguna de las cinco pide una cuenta ajena: las cinco salen de la cabeza de quien
  instala. Las que sí piden consolas ajenas son Q10 a Q12, y entran en el tiempo 6.
- **4 · La construcción** — `blueprint/30-generacion.md`, y de ahí, en ese orden,
  `blueprint/31-proveedores.md`, `blueprint/32-multimodal.md`, `blueprint/33-agenda.md`,
  `blueprint/34-crm.md` y `blueprint/35-panel-api.md`. Sale el árbol de `agente/`.
- **5 · Que ande** — `blueprint/40-pruebas.md` y `blueprint/90-auditoria.md`. La suite en
  verde, la compuerta en `pass` y el simulador corrido.
- **6 · El destino, ahora de verdad** — `blueprint/50-despliegue.md`. Local: uvicorn y un
  túnel. Railway: el CLI, las variables y el alta del webhook. Q10 a Q12 entran acá, no antes.
  Ese archivo cierra con «**Próximo archivo:** `blueprint/60-bandeja.md`», y ése no es un tiempo
  de `/start`: es el comando `/bandeja`, y corre después del cierre. La cadena termina en el
  tiempo 7.
- **7 · El cierre** — acá abajo.

## Qué se pregunta y qué se decide

Lo del negocio se frena y se pregunta: catálogo, precios, horarios, tono, cuándo pasa a un
humano. Eso no lo podés saber. Lo técnico lo decidís vos y lo declarás: qué elegiste y en qué
archivo se cambia. Nada de menús para lo que tiene una sola respuesta correcta.

## El corte está al final del tiempo 5

Ahí parás y mostrás. Quien instala habla con su cerrador en el simulador **sin una sola
credencial de WhatsApp**. Todo lo caro y lo lento vive después de esa línea.

Con Q5 a Q9 ya contestadas en el tiempo 3, lo que se ve ahí dice precios del catálogo y ofrece
horarios reales. Ése es el corte que vale mostrar: si el tramo 2 quedó sin correr, el simulador
abre igual y el cerrador no tiene con qué contestar cuánto sale.

Antes de seguir al tiempo 6, preguntá si quiere seguir hoy o dejarlo ahí. Dejarlo ahí es una
respuesta válida: `/seguir` lo retoma cualquier otro día.

## Tiempo 7 · El cierre

Al terminar, en pocas líneas:

- **Qué quedó andando**, con el comando exacto para volver a levantarlo.
- **Qué falta**, y qué paso deja sin correr cada cosa que falta.
- **Qué supuestos le tocaron**: los de `SUPUESTOS.md` que aplicaron, por identificador.
- **El próximo comando**: `/bandeja` para resolver los borradores de a uno, `/soltar` cuando
  quiera que conteste solo.

Y decilo con todas las letras: **el default es `borrador`**. El agente redacta, muestra y
espera. Nadie del otro lado recibe nada hasta que lo suelte.
