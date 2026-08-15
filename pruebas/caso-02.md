# Caso 02 · el camino del enojo

La contraparte del 01. Acá el contacto ya viene de dos mensajes y el tercero dispara la
escalación, y lo que se prueba no es que el agente conteste bien: es que **deje de contestar**.

Son tres entradas, una por disparador, y las tres corren las mismas aserciones. Cada una lleva su
historial al lado, porque esto es el tercer mensaje de una conversación y no el primero. Un caso
del enojo que arranque como primer mensaje deja de probar lo que existe para probar.

| Entrada | Historial | Qué lo dispara | `handoff.motivo` |
|---|---|---|---|
| `caso-02.entrada.json` | `caso-02.historial.json` | el tercer mensaje, con insultos | `enojo` |
| `caso-02b.entrada.json` | `caso-02b.historial.json` | pide algo de 90000 con el rango en 8000–40000 | `precio_fuera_de_rango` |
| `caso-02c.entrada.json` | `caso-02c.historial.json` | «Prefiero que esto lo vea un humano» | `palabra_clave` |

Las aserciones viven en `pruebas/test_caso_02.py`, y son bastantes más que seis nodos: cada
función corre por los tres disparadores y por los dos modos, o por los dos canales internos. El
número exacto lo imprime `pytest pruebas/test_caso_02.py --collect-only -q | grep collected`, y no
se escribe acá porque crece cada vez que alguien agrega un disparador o un canal.

**Entrada.** La del enojo, la misma que `pruebas/fixtures/caso-02.entrada.json`. Las otras dos son
este objeto con otro `mensaje` —y en `caso-02b`, con `de` en nulo—.

```json
{
  "version": "1",
  "mensaje": {
    "de": "5215500000001",
    "contacto_id": "bsu_02HZK3M9QX7T2VW4",
    "tipo": "texto",
    "texto": "Una porquería de servicio, no me hagan perder más el tiempo.",
    "media_id": null,
    "media_url": null,
    "media_local": null,
    "recibido_en": "2026-03-02T03:41:00-06:00"
  },
  "modo": "automatico",
  "confirmado": false,
  "playbook": {
    "tono": "Directo, de tú a tú, sin promesas de resultado.",
    "objeciones": [
      {
        "objecion": "Está caro",
        "respuesta": "Se compara contra lo que cuesta una operación mal cerrada, y hay pago en tres partes."
      },
      {
        "objecion": "No tengo tiempo",
        "respuesta": "Son cuatro horas por semana y las clases quedan grabadas."
      },
      {
        "objecion": "Lo tengo que consultar",
        "respuesta": "Te dejo el resumen de una página para que lo muestres."
      },
      {
        "objecion": "Ya intenté algo parecido",
        "respuesta": "Preguntá qué le faltó a eso antes de contestar."
      },
      {
        "objecion": "Después te aviso",
        "respuesta": "Ofrecé una fecha concreta para retomar, no un «cuando puedas»."
      }
    ]
  },
  "catalogo": [
    {
      "nombre": "Curso de bienes raíces",
      "precio": 12000,
      "moneda": "MXN"
    }
  ],
  "rango_precio": {
    "minimo": 8000,
    "maximo": 40000
  },
  "disponibilidad": [
    {
      "inicio": "2026-03-02T11:00:00-06:00",
      "duracion_min": 30
    },
    {
      "inicio": "2026-03-02T17:00:00-06:00",
      "duracion_min": 30
    },
    {
      "inicio": "2026-03-03T10:00:00-06:00",
      "duracion_min": 30
    },
    {
      "inicio": "2026-03-04T16:00:00-06:00",
      "duracion_min": 30
    }
  ],
  "opciones_horario": 3,
  "umbrales": {
    "caliente": 70,
    "tibio": 40
  },
  "palabras_escalacion": [
    "humano",
    "persona real",
    "reclamo",
    "abogado",
    "estafa",
    "cancelar"
  ],
  "canal_interno": "#ventas-escalaciones"
}
```

Este bloque y el fixture no pueden derivar. `.venv/bin/python -m pruebas.extraer_fixture caso-02
--verificar` los compara por igualdad de objeto y sale 1 si dejaron de decir lo mismo.

**Corre en `automatico`, no en `borrador`.** Es la decisión de diseño de este caso, y va escrita
porque el instinto dice lo contrario. En `borrador` esta prueba no probaría nada: no sale nada en
ningún caso, y el verde sería idéntico con el paso 6 roto. El punto es que la escalación calle al
agente **aun cuando está autorizado a mandar**. `borrador` corre igual, parametrizado al lado,
pero ahí lo que muerde es otra cosa: que la línea de handoff tampoco tiene vía rápida. Ver S11 en
`SUPUESTOS.md`.

**Aserciones.** Una por paso. El agente tiene 6 pasos, así que acá hay 6 y ninguna más.

1. El contacto no es nuevo: `contacto.nuevo` en falso y `mensajes_previos` con los del historial
   sembrado, no en cero. Se indexa por `contacto_id`, igual que en el 01. En `caso-02b` el
   `mensaje.de` viene nulo y el contacto entra lo mismo: `contacto.numero` queda en
   `bsuid:<contacto_id>`, nunca vacío ni inventado, así lo que intente marcarlo falla fuerte en
   vez de marcar mal. Ver S12 en `SUPUESTOS.md`. El paso 1 queda en `hecho`.
2. Califica igual. Escalar no es dejar de mirar: `score` de 0 a 100 con `temperatura` según los
   umbrales del fixture, 70 y 40. En `caso-02b` el contacto dice «Tengo 90000 para invertir este
   trimestre» y el presupuesto sobrevive, porque la evidencia es una subcadena literal del
   mensaje; es ese mismo monto el que enciende el disparador de precio. En los otros dos queda en
   nulo. El paso 2 queda en `hecho`.
3. **No responde.** La escalación se decide antes de redactar, no después: el paso 3 queda en
   `salteado` y no hay respuesta comercial: ni precio, ni objeción del playbook, ni horarios. Lo
   único que puede salir al contacto es la línea del paso 6, y sale una sola vez. Dos mensajes
   quiere decir que el 3 redactó y mandó, y recién después corrió el 6. Se cuentan los envíos que
   vio el doble de transporte, no los que el agente dice que hizo.
4. **Salteado, no `sin-confirmar`.** `cita` en nulo y el paso 4 en `salteado`, con el motivo
   escrito. La diferencia con el 01 es deliberada. En el camino feliz el 4 queda en
   `sin-confirmar` porque hay una pregunta abierta y alguien la puede contestar; acá no, porque la
   conversación ya salió del agente y nadie va a confirmar un horario que nunca se ofreció.
   `sin-confirmar` quiere decir «te estoy esperando», y esperar algo que no va a pasar deja la
   bandeja llena de pendientes que nadie puede cerrar.
5. `crm.etapa` en `escalado`. En `borrador` la fila queda redactada con `escrito` en falso y el
   paso 5 en `sin-confirmar`; en `automatico` se escribe. Esa etapa no es decorativa: es lo que el
   segundo turno lee para saber que ya escaló. Y `crm.resumen` dice **qué pasó, no cómo lo dijo**:
   tres líneas, sin nada del contacto pegado y sin el insulto adentro. Esa fila la abre una
   persona del equipo, quizás meses después, y el agravio se lo queda la conversación.

   **Nada del contacto son dos fuentes, no una.** El mensaje de este turno y el historial entero
   —`conversacion.ultimo_entrante` y los `mensajes` con `direccion` en `entrante`—. El fixture del
   enojo agrede en las dos: «una porquería de servicio» en el turno, «son unos ladrones» en el
   mensaje anterior. Un build que arme el resumen arrastrando el historial no toca `mensaje.texto`
   ni una vez, así que una aserción que mire sólo el turno lo deja pasar entero. Ni la línea
   pegada ni la palabra suelta: las dos formas de que ese insulto termine impreso en el tablero de
   quien abra la fila.
6. `handoff` no es nulo. `handoff.motivo` trae uno de los tres valores del contrato, y
   `handoff.disparador` trae lo que lo activó —la palabra encontrada, o el monto que quedó fuera
   del rango—, nunca un texto fijo: si los tres disparadores dicen lo mismo, está puesto a mano y
   no salió del mensaje. `estado` queda en `escalado`. El aviso al canal interno sale **una vez, y
   una sola**, en los dos modos, con el número —o el `contacto_id` cuando el número no está—, el
   motivo y el enlace al chat: no es un envío al contacto, así que no pasa por la compuerta del
   modo. Una escalación, un aviso: dos es el canal de escalaciones duplicando todo hasta que nadie
   lo mira, y contar «los mismos en los dos modos» no lo ve —dos y dos también empatan—. Y sale igual sea
   cual sea el canal: `canal_interno` admite un canal de Slack o un número interno de WhatsApp, y
   el segundo viaja por el mismo `/messages` que el mensaje al contacto sin contarse como envío al
   contacto. El corte es por destino —el host, y después el destinatario que el cuerpo declara—,
   nunca por la ruta ni por buscar el nombre del canal adentro de la llamada: con Slack ese nombre
   no viaja por ningún lado, porque el canal vive adentro de la URL del webhook. El paso 6 queda
   en `hecho`.

**El segundo turno.** Lo que sólo se ve con dos mensajes: el silencio posterior. Llega un cuarto
mensaje del contacto, se vuelve a correr el ciclo, y no sale ni un envío nuevo, ni para
despedirse. `estado` sigue en `escalado` y el paso 3 sigue en `salteado`. Los dos turnos corren
adentro del mismo bucle y sobre la misma base en memoria, que es lo que hace que el segundo sepa
del primero: un `asyncio.run` por turno cierra la base de SQLite en el medio y esta aserción daría
verde con el agente contestando.

**Salida esperada.** Un objeto que valida contra `contratos/salida.schema.json`, con `estado` en
`escalado`, `cita` en nulo, `crm.etapa` en `escalado`, `handoff` con su motivo y su disparador, y
los seis pasos con estado: 1 y 2 en `hecho`, 3 y 4 en `salteado`, 6 en `hecho`. El 5 sigue al
modo: `sin-confirmar` en `borrador`, y en `automatico` lo que haya dado la escritura de la fila.

**Qué se considera fallo.**

- Dos mensajes al contacto en el turno que escala. El primero es la línea; el segundo es la
  respuesta comercial que no tenía que redactarse.
- Dos avisos al canal interno por una escalación.
- Cualquier envío en el segundo turno.
- Los tres disparadores con el mismo `handoff.disparador`.
- Escalar en `borrador` y mandar igual. Esa línea es un envío como cualquier otro: S11.
- Que `caso-02b` no escale. Con `rango_precio` en nulo ese disparador queda apagado a propósito,
  y por eso el fixture lo trae puesto en 8000–40000.

**Qué no se afirma acá.** El texto exacto de la línea de handoff, los tiempos de ejecución y
cualquier cosa que dependa de una credencial real: este caso corre sin `${WHATSAPP_TOKEN}`, sin
`${GOOGLE_CALENDAR_ID}` y sin `${SUPABASE_URL}`, igual que el 01. Tampoco se afirma **cómo** se
detecta el enojo. Lo que se mide es la conducta —un mensaje y después silencio—, no el
clasificador que la decide.
