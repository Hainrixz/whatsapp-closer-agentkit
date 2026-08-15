---
name: seguir
description: Retoma una construcción a medias — lee el estado, lo reconcilia contra el disco y sigue desde la fase en curso.
disable-model-invocation: true
---

# Seguir

Leé `.wca-estado.json`. Si no está, no hay nada que retomar: decilo y ofrecé `/start`.

Reconciliá contra el disco antes de escribir nada. Por cada archivo anotado en el estado: ¿existe
todavía?, ¿su sha256 sigue coincidiendo? Reportá en una lista los que faltan y los que cambiaron.

Un archivo que tocó el usuario no se reescribe en silencio, nunca. Decí qué cambió, qué se
perdería, y esperá confirmación explícita archivo por archivo.

Las respuestas de la entrevista ya están en el estado. No vuelvas a preguntar nada que ya esté
contestado ahí.

Recién después traducí la fase en curso a un archivo. El campo `fase` del estado guarda una
palabra, no un número: buscá esa palabra en la columna «`fase` en el estado» de la tabla de
`blueprint/00-mapa.md` y abrí el archivo de esa fila. Ése solo, no todos los del mapa.

Una palabra que no esté en esa columna la escribió otra versión del kit. Decí qué valor trae y
esperá, no adivines la equivalencia por parecido.
