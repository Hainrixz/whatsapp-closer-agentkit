# Cerrador de WhatsApp

Atiende cada chat entrante con perfil de setter y closer: califica, responde la objeción,
ofrece horarios que existen, agenda y deja escrito en el CRM en qué quedó.

## El problema

La gente pide una y otra vez un agente de WhatsApp que venda de verdad, no un bot de menú.
Que califique, que responda objeciones, que agende.

Hoy contestan a mano. Y el que escribe a las tres de la mañana se va con el que le contestó
primero.

## Qué hace

1. Recibe el mensaje por el webhook de la API de WhatsApp Cloud y recupera el historial y la
   ficha del contacto. Si viene audio, lo transcribe antes de leerlo.
2. Detecta la intención y califica: presupuesto, urgencia y encaje, con un score de 0 a 100.
3. Responde con el tono de marca, busca la objeción del contacto en el playbook y ofrece tres
   horarios reales de la agenda.
4. Agenda en Google Calendar y manda la confirmación, con el recordatorio programado 24 horas
   antes.
5. Escribe la etapa, el resumen y el próximo paso en el CRM.
6. Si detecta enojo, un precio fuera de rango o una palabra de escalación, deja de responder,
   pasa el chat a una persona y avisa por el canal interno.

Los pasos 3, 4 y 5 escriben afuera: mandan un mensaje, crean un evento y tocan la base. Los
tres piden confirmación explícita y por defecto el agente arranca en modo borrador.

## Qué necesitás conectar

- **API de WhatsApp Business Cloud (Meta)** — es por donde entra y sale todo. Variables:
  `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` y `WHATSAPP_VERIFY_TOKEN`. Sin esto no hay
  producto.
- **API de Google Calendar** — para el paso 4. Variables: `GOOGLE_CALENDAR_ID` y
  `GOOGLE_SERVICE_ACCOUNT_JSON`. Sin ellas el agente propone el horario y te dice que lo
  cargues a mano.
- **Supabase o Postgres** — es el CRM. Variables: `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`.
  Sin ellas el paso 5 devuelve la fila en la salida y no la escribe.
- **Whisper** — para los audios entrantes. Variable: `OPENAI_API_KEY`. Sin ella, un audio
  frena el ciclo con el motivo, no con una transcripción inventada.
- **Slack** — para el aviso del paso 6. Variable: `SLACK_WEBHOOK_URL`. Sin ella la escalación
  igual ocurre, pero el aviso queda en la salida y lo tiene que leer alguien.

Sin ninguna credencial el agente arranca igual, te dice qué le falta y corre los pasos 1 a 3
en borrador. De dónde se saca cada valor está en `env.example`.

## Qué falta construir

Ocho piezas del catálogo que este agente declara usar. Ninguna se generó como stub.

| Pieza | Tipo | Estado | Portante |
|---|---|---|---|
| `conversational-sales-copy` | skill | Especificada en el catálogo, sin construir | No |
| `lead-qualification-intent` | skill | Especificada en el catálogo, sin construir | No |
| `human-handoff-protocol` | skill | Especificada en el catálogo, sin construir | Sí |
| `whatsapp-ban-safety` | skill | Especificada en el catálogo, sin construir | Sí |
| `whatsapp-cloud-mcp` | tool | Especificada en el catálogo, sin construir | Sí |
| `conversational-crm-connector` | tool | Especificada en el catálogo, sin construir | No |
| `chat-scheduler-tool` | tool | Especificada en el catálogo, sin construir | No |
| `conversation-memory-engine` | tool | Especificada en el catálogo, sin construir | No |

Las tres portantes sostienen pasos enteros: sin ellas no hay versión recortada de este agente
que valga la pena instalar. El detalle y el orden en que conviene construirlas está en
`PENDIENTES.md`.

Si alguna no está instalada, el agente lo dice y se detiene en el paso que la necesita. No la
improvisa. Un stub que devuelve nada en silencio hace que el agente parezca andar dos semanas,
y después descubrís que ningún lead quedó escrito en el CRM.

## Cómo se instala

1. Copiá la carpeta `agents/` dentro de `.claude/agents/` de tu proyecto.
2. Copiá `env.example` a `.env` y completá lo que vayas a usar. Empezá por las tres de
   WhatsApp: sin ellas no entra ningún mensaje.
3. Escribí tu playbook de objeciones. Es un campo obligatorio de la entrada y es lo que separa
   este agente de un bot de menú. Cinco objeciones con su respuesta alcanzan para arrancar.
4. Instalá las ocho piezas de la tabla cuando existan. Mientras tanto el agente te avisa cuál
   falta.
5. Corré el caso de `pruebas/caso-01.md` y compará contra las seis aserciones.
6. Dejalo en modo `borrador` las primeras dos semanas. Leé lo que redacta antes de que lo
   mande. Recién después pasalo a `automatico`, si querés.

## Cómo se prueba

El caso está en `pruebas/caso-01.md`, con una aserción por paso. Las aserciones 3, 4 y 5
llaman a los pasos que escriben **sin confirmar** y exigen que el agente no haga nada. Mandar
el mensaje, crear el evento o tocar la fila sin confirmación es fallo aunque el contenido esté
perfecto.

## Lo que este agente NO hace y por qué

- **No inventa precios ni promociones.** Lo que no está en el catálogo que le pasás, no
  existe. Un descuento inventado por un agente lo termina pagando el negocio.
- **No responde objeciones que no estén en tu playbook.** Las nombra y las deja para el humano.
- **No escribe primero.** Contesta a quien le escribió. No hace envíos masivos y no abre
  conversaciones frías: eso es lo que hace que Meta baje el número.
- **No negocia un precio fuera de rango.** Eso escala, siempre.
- **No sigue contestando después de una escalación.** Ni para despedirse.
- **No borra ni reordena nada del CRM.** Agrega y actualiza la fila del contacto.

Hay un límite que no pone el agente sino la plataforma: fuera de la ventana de 24 horas desde
el último mensaje del contacto, WhatsApp solo deja mandar plantillas aprobadas. El recordatorio
del paso 4 cae muchas veces afuera de esa ventana, así que necesita una plantilla dada de alta.

## Cómo se cobra

Setup de 800-2500 USD por negocio + mensualidad de 150-500 USD según volumen de conversaciones; upsell de entrenamiento del playbook cada trimestre

## De dónde salió

Lo pidieron 31 respuestas del corpus. Los cinco identificadores que originaron la ficha están
en `CITAS.md`.

Publicamos el identificador y el número agregado, nunca el texto del comentario ni el usuario
de Instagram. Esa gente contestó una caja de preguntas de una story: no consintió aparecer en
un repositorio público.

## Qué asumió la forja

Diez cosas, todas en `SUPUESTOS.md` con dónde se corrigen. Las dos que más te pueden doler:
el modo `borrador` por defecto, que hace que el agente no conteste solo hasta que vos lo
cambies, y el playbook de cinco objeciones, que la ficha nombra pero no lista, así que lo
tenés que escribir vos.
