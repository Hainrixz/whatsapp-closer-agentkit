# Caso 01 · camino feliz

**Entrada.**

```json
{
  "version": "1",
  "mensaje": {
    "de": "5215500000000",
    "contacto_id": "bsu_01HZK3M9QX7T2VW4",
    "tipo": "texto",
    "texto": "Hola, vi el curso de bienes raíces. ¿Cuánto sale? Me interesa pero se me hace caro y no sé si tengo tiempo.",
    "media_id": null,
    "media_url": null,
    "media_local": null,
    "recibido_en": "2026-03-02T03:41:00-06:00"
  },
  "modo": "borrador",
  "confirmado": false,
  "playbook": {
    "tono": "Directo, de tú a tú, sin promesas de resultado.",
    "objeciones": [
      { "objecion": "Está caro", "respuesta": "Se compara contra lo que cuesta una operación mal cerrada, y hay pago en tres partes." },
      { "objecion": "No tengo tiempo", "respuesta": "Son cuatro horas por semana y las clases quedan grabadas." },
      { "objecion": "Lo tengo que consultar", "respuesta": "Te dejo el resumen de una página para que lo muestres." },
      { "objecion": "Ya intenté algo parecido", "respuesta": "Preguntá qué le faltó a eso antes de contestar." },
      { "objecion": "Después te aviso", "respuesta": "Ofrecé una fecha concreta para retomar, no un «cuando puedas»." }
    ]
  },
  "catalogo": [{ "nombre": "Curso de bienes raíces", "precio": 12000, "moneda": "MXN" }],
  "rango_precio": { "minimo": 8000, "maximo": 40000 },
  "disponibilidad": [
    { "inicio": "2026-03-02T11:00:00-06:00", "duracion_min": 30 },
    { "inicio": "2026-03-02T17:00:00-06:00", "duracion_min": 30 },
    { "inicio": "2026-03-03T10:00:00-06:00", "duracion_min": 30 },
    { "inicio": "2026-03-04T16:00:00-06:00", "duracion_min": 30 }
  ],
  "canal_interno": "#ventas-escalaciones"
}
```

El mensaje, el playbook y la agenda de arriba son sintéticos. Reemplazalos por una conversación
tuya cuando quieras: las seis aserciones no cambian, porque salen de los pasos y no del caso.
Ver S10 en `SUPUESTOS.md`.

**Aserciones.** Una por paso. El agente tiene 6 pasos, así que acá hay 6 y ninguna más.

1. Devuelve el contacto con `nuevo` en verdadero y `mensajes_previos` en cero, porque ese
   contacto no tiene historial. Indexa por `contacto_id`, no por `numero`: el teléfono puede
   faltar y el identificador no.

   Y con `tipo` en `audio`, si no hay forma de conseguir los bytes, no arranca: lo dice con el
   motivo y no adivina qué decía el audio. Son tres formas de no conseguirlos y las tres
   frenan igual — `media_id` y `media_url` ambos en nulo, un `media_url` que ya caducó, o un
   `media_id` cuya bajada devuelve 400 porque Meta ya soltó el archivo. Esa última no se
   recupera nunca, y por eso el medio se baja al recibirlo y no cuando hace falta. Un
   `media_id` no se le pasa jamás a una API de visión: sin la credencial puesta devuelve 401.
2. Califica con `score` entre 0 y 100 y `temperatura` coherente con los umbrales. Con esta
   entrada `presupuesto` queda en nulo: el contacto no declaró monto y no se deduce del
   mensaje. Inventar un número es fallo aunque el score quede razonable.
3. **Antes de mandar, pregunta.** Con `modo` en `borrador` y `confirmado` en falso, deja el
   texto en `respuesta` con `enviado` en falso y no manda nada. El texto responde la objeción
   de precio, que sí está en el playbook, y ofrece exactamente 3 horarios de la lista de
   disponibilidad. Un horario que no esté en `disponibilidad` es fallo.

   Y ese texto **viene del modelo**. No se afirma cuál es —eso está excluido más abajo—, se
   afirma que sea el que el modelo devolvió: el stub redacta con una marca adentro de la frase y
   la marca tiene que aparecer en lo redactado. Descartar lo que devolvió el modelo y mandar una
   línea enlatada es fallo aunque la línea esté bien escrita: un agente que le contesta lo mismo
   a todos los contactos no está redactando.
4. **Antes de agendar, pregunta.** Sin confirmación no crea evento: `cita` queda en nulo y el
   paso 4 en `sin-confirmar`. Con la confirmación en verdadero **y con un horario elegido**, el
   evento existe con su identificador, la confirmación sale por WhatsApp y el recordatorio queda
   para 24 horas antes.

   Son dos requisitos y no uno, y en este turno falta el segundo: el contacto todavía no
   contestó cuál de los tres horarios le sirve, así que `mensaje.horario_elegido` viene en nulo
   y el paso 4 queda `sin-confirmar` con el motivo «no hay horario elegido» —ése y no el del
   modo—. El horario lo escribe el paso 1 en el turno siguiente, cruzando la respuesta del
   contacto contra los horarios que este turno ofreció, o lo escribe quien opera al aprobar el
   borrador desde `/bandeja`. **Elegirlo por su cuenta es fallo**: agendar el primer hueco libre
   porque hay confirmación es exactamente la cita que nadie aceptó. Y con el horario elegido
   pero sin confirmar tampoco se agenda: los dos requisitos son requisitos.

   Y ese identificador **viene del calendario**. Un `evento_id` que el código se escribe a sí
   mismo es una cita que no existe: queda en la salida, en el panel y en la confirmación que le
   llega al contacto, y el día de la reunión no hay nada en la agenda.
5. **Antes de escribir en el CRM, pregunta.** Sin confirmación la fila se arma igual y vuelve en
   `crm` con `escrito` en falso —para que se pueda ver y aprobar desde `/bandeja`—, y no se
   escribe en ningún lado. Con confirmación, la fila tiene `etapa`, `resumen` de tres líneas y
   `proximo_paso` con fecha, y `escrito` lo decide la respuesta del servicio. Pegar la
   conversación entera en `resumen` es fallo.
6. Con esta entrada no escala: no hay enojo, el precio de 12000 cae dentro del rango y ninguna
   palabra de la lista aparece. `handoff` queda en nulo. Cambiando el texto por uno que diga
   «quiero hablar con un humano», escala: deja de responder, escribe etapa `escalado` y avisa
   al canal interno con número, motivo y enlace al chat.

**Salida esperada.** Un objeto que valida contra `contratos/salida.schema.json`, con `estado`
en `parcial`, `cita` en nulo, `crm` con la fila armada y `escrito` en falso, y los seis pasos con
estado. Los pasos 3, 4 y 5 quedan en `sin-confirmar`. Está en
`pruebas/fixtures/caso-01.salida-esperada.json`, y `scripts/auditar.py` lleva adentro la misma
copia para poder correr con el árbol vacío: las dos se mueven juntas.

Dos campos de esa salida se leen mal si no se dicen:

- **`respuesta.ventana_abierta` viene en nulo, no en verdadero.** Sale del `Resultado` de
  `enviar()`, y en borrador el paso 3 no llega a llamarlo. Un verdadero ahí es el campo puesto a
  mano sobre un envío que no ocurrió.
- **`crm` viene con la fila y no en nulo.** El nulo ya significa «el paso 5 no corrió» y no puede
  significar además «corrió y no escribió». Ver `blueprint/00-contrato.md` § 13.

**Qué se considera fallo.** Cualquier aserción sin cumplir. Mandar el mensaje de la aserción 3
sin confirmación es fallo aunque el texto esté perfecto, y lo mismo vale para el evento de la 4
y la fila de la 5.

**Qué no se afirma acá.** El texto exacto que redacta el modelo —ni su forma, ni su largo, ni
una palabra que el modelo haya elegido: afirmarlo ata este caso a una versión del modelo y lo
rompe el día que se sube el pin—, los tiempos de ejecución y cualquier cosa que dependa de una
credencial real. **Que el texto venga del modelo sí se afirma**, y es otra cosa: ver la
aserción 3. Este caso corre sin `${WHATSAPP_TOKEN}`,
sin `${GOOGLE_CALENDAR_ID}` y sin `${SUPABASE_URL}` configurados, a propósito: lo que se mide
es la llamada que el agente prepara, no la respuesta del servicio.

## Caso 02 · el camino del enojo

Está escrito, en `pruebas/caso-02.md`, con sus tres entradas y sus tres historiales. Es la
contraparte de este archivo: acá se prueba que el agente conteste bien, allá que **deje de
contestar**. Corre en `automatico` a propósito, porque en `borrador` no sale nada en ningún caso
y el verde sería idéntico con el paso 6 roto.
