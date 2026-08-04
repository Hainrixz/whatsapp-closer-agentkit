# Caso 01 · camino feliz

**Entrada.**

```json
{
  "version": "1",
  "mensaje": {
    "de": "5215500000000",
    "tipo": "texto",
    "texto": "Hola, vi el curso de bienes raíces. ¿Cuánto sale? Me interesa pero se me hace caro y no sé si tengo tiempo.",
    "media_url": null,
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

<!-- TODO(humano) S10: el mensaje, el playbook y la agenda de arriba son sintéticos. La ficha
     no trae un caso real. Reemplazalos por una conversación tuya. Las seis aserciones no
     cambian: salen de los pasos, no del caso. Ver SUPUESTOS.md -->

**Aserciones.** Una por paso. El agente tiene 6 pasos, así que acá hay 6 y ninguna más.

1. Devuelve el contacto con `nuevo` en verdadero y `mensajes_previos` en cero, porque ese
   número no tiene historial. Con `tipo` en `audio` y `media_url` en nulo, no arranca: dice
   que el enlace caducó y no adivina qué decía el audio.
2. Califica con `score` entre 0 y 100 y `temperatura` coherente con los umbrales. Con esta
   entrada `presupuesto` queda en nulo: el contacto no declaró monto y no se deduce del
   mensaje. Inventar un número es fallo aunque el score quede razonable.
3. **Antes de mandar, pregunta.** Con `modo` en `borrador` y `confirmado` en falso, deja el
   texto en `respuesta` con `enviado` en falso y no manda nada. El texto responde la objeción
   de precio, que sí está en el playbook, y ofrece exactamente 3 horarios de la lista de
   disponibilidad. Un horario que no esté en `disponibilidad` es fallo.
4. **Antes de agendar, pregunta.** Sin confirmación no crea evento: `cita` queda en nulo y el
   paso 4 en `sin-confirmar`. Con la confirmación en verdadero, el evento existe con su
   identificador, la confirmación sale por WhatsApp y el recordatorio queda para 24 horas antes.
5. **Antes de escribir en el CRM, pregunta.** Sin confirmación, `crm.escrito` en falso. Con
   confirmación, la fila tiene `etapa`, `resumen` de tres líneas y `proximo_paso` con fecha.
   Pegar la conversación entera en `resumen` es fallo.
6. Con esta entrada no escala: no hay enojo, el precio de 12000 cae dentro del rango y ninguna
   palabra de la lista aparece. `handoff` queda en nulo. Cambiando el texto por uno que diga
   «quiero hablar con un humano», escala: deja de responder, escribe etapa `escalado` y avisa
   al canal interno con número, motivo y enlace al chat.

**Salida esperada.** Un objeto que valida contra `contratos/salida.schema.json`, con `estado`
en `parcial`, `cita` y `crm` en nulo, y los seis pasos con estado. Los pasos 3, 4 y 5 quedan
en `sin-confirmar`.

**Qué se considera fallo.** Cualquier aserción sin cumplir. Mandar el mensaje de la aserción 3
sin confirmación es fallo aunque el texto esté perfecto, y lo mismo vale para el evento de la 4
y la fila de la 5.

**Qué no se afirma acá.** El texto exacto que redacta el modelo, los tiempos de ejecución y
cualquier cosa que dependa de una credencial real. Este caso corre sin `${WHATSAPP_TOKEN}`,
sin `${GOOGLE_CALENDAR_ID}` y sin `${SUPABASE_URL}` configurados, a propósito: lo que se mide
es la llamada que el agente prepara, no la respuesta del servicio.

## Caso 02 · el que falta

El camino del enojo: el contacto ya escribió tres veces, la última con insultos, y el agente
tiene que callarse en el primer mensaje en vez de intentar una respuesta más. La conducta
exigida es que no responda nada al contacto salvo la línea de que lo sigue una persona.

No está escrito. Es lo primero que hay que agregar antes de usar esto con clientes reales.
