# knowledge · lo que sabe tu negocio

Acá dejás los documentos crudos que el kit lee para escribir `config/playbook.yaml`. Es la
carpeta que hace que el agente conteste como vos y no como un bot de menú.

Nada de lo que pongas acá se sube a git. Mirá la última sección antes de copiar archivos.

## Qué va en cada subcarpeta

**`closer/` — cómo se vende.** La metodología, no los datos. El PDF del curso de ventas que
compraste, la transcripción de la llamada que sí cerró, tu guion de descubrimiento, la lista de
objeciones con la respuesta que te funciona, las notas de la capacitación del equipo.

De acá salen el tono, las preguntas de calificación y las respuestas a objeciones.

**`negocio/` — qué se vende.** El catálogo con precios, las condiciones de pago, los plazos de
entrega, las políticas de garantía y devolución, las preguntas frecuentes, la lista de a quién
sí y a quién no le vendés.

De acá salen los precios y los límites. El agente no inventa ninguno de los dos: un precio que
no está en este material no existe para él.

## Qué formatos se leen

```
PDF   DOCX   TXT   MD   VTT   SRT
```

`VTT` y `SRT` son subtítulos: sirven para meter una llamada grabada o un video de capacitación
sin transcribirla vos.

Lo que esté en otro formato hay que convertirlo antes. Una imagen de una lista de precios no
cuenta como lista de precios.

## Qué sale de acá

Un solo archivo: `config/playbook.yaml`. Tono, objeciones con su respuesta, catálogo, rango de
precio y palabras de escalación.

Ese archivo sí se versiona, porque es tuyo y es corto, y porque conviene ver en el historial qué
cambió cuando el agente empieza a contestar distinto. Podés editarlo a mano cuando quieras: el
kit no lo pisa sin avisarte.

## Esto no se sube a git

`knowledge/` está en `.gitignore`. Solo viajan este README y los tres `.gitkeep`.

Dos motivos, y cualquiera de los dos alcanza:

1. **Puede tener datos de clientes.** Una transcripción de llamada lleva nombres, teléfonos y a
   veces números de una operación. Eso no va a un repositorio, ni siquiera privado.
2. **Puede ser material de otro autor.** El curso que compraste tiene licencia para vos, no para
   publicarlo. Subirlo lo publica.

Si vas a compartir tu configuración con alguien, compartí `config/playbook.yaml`. Ahí está lo
que el agente usa, escrito por vos, sin el material crudo atrás.
