# Supuestos

Doce decisiones que el kit tomó por vos porque no estabas para tomarlas. Ninguna es una
opinión sobre tu negocio: son defaults que había que elegir para que el agente arrancara.

Cada una dice qué se asumió, por qué, dónde vive y cómo se cambia. Todas se cambian.

Los identificadores viajan en `supuestos` de la salida: cada corrida deja escrito cuáles
aplicó, así no hay que adivinar por qué el agente hizo lo que hizo.

---

## S01 · El modo por defecto es `borrador`

**Qué asumí.** Que los pasos 3, 4 y 5 arrancan mostrando lo que van a hacer y esperando una
confirmación explícita, de a uno.

**Enunciado por lo que sale y no por qué paso lo manda: en `borrador` no sale ningún mensaje de
WhatsApp.** Los tres pasos de arriba son los que escriben afuera, y por eso son los que se
enumeran; pero el aviso del paso 6, cuando `canal_interno` es un número, también es un mensaje de
WhatsApp y también espera. Enumerar pasos deja lugar para un cuarto que no está en la lista, y ahí
estuvo: un aviso interno saliendo en `borrador`. Ver S09.

**Por qué.** El paso 3 le escribe a un cliente tuyo, el 4 toca tu agenda y el 5 toca tu base.
La primera semana nadie sabe todavía cómo redacta este agente con tu playbook. Un borrador que
no te gustó se corrige; un mensaje que ya salió, no.

**Dónde.** `contratos/entrada.schema.json` → `modo`, con `borrador` de default. El paso 3 del
prompt en `agents/whatsapp-closer-agent.md`. La regla está en `CLAUDE.md`.

**Cómo se corrige.** Corré `/soltar`: muestra los números de la bandeja y pasa el paso 3 a
`automatico`. Los pasos 4 y 5 se sueltan de a uno y después. También se fuerza desde la entrada
con `"modo": "automatico"`, que es la vía cuando el kit corre sin nadie mirando.

---

## S02 · El playbook lo escribe quien vende

**Qué asumí.** Que el kit no trae objeciones cargadas. `playbook.objeciones` es campo obligatorio
de la entrada y lo llena el negocio.

**Por qué.** Una objeción respondida mal cierra peor que una objeción no respondida. La respuesta
a "está caro" depende de tu margen, de tu forma de pago y de contra quién te comparan, y nada de
eso lo sabe el kit. Un playbook genérico convierte esto en el bot de menú que se quiso evitar.

**Dónde.** `contratos/entrada.schema.json` → `playbook`, en `required`. La skill `/playbook`.

**Cómo se corrige.** Corré `/playbook`. Cinco objeciones con su respuesta alcanzan para arrancar.
Después, `bandeja resumen` lista las objeciones que aparecieron y no estaban: esa lista es el
playbook de la segunda semana, y sale de tus conversaciones y no de una plantilla.

---

## S03 · El score va de 0 a 100, con cortes en 70 y 40

**Qué asumí.** Caliente desde 70, tibio entre 40 y 69, frío abajo de 40.

**Por qué.** Hacía falta una escala y dos cortes para que "caliente" signifique algo que se pueda
revisar después. Los números son de arranque: nadie midió todavía tu tasa de cierre por tramo.

**Dónde.** `contratos/entrada.schema.json` → `umbrales`. `contratos/salida.schema.json` →
`calificacion.score` y `calificacion.temperatura`. El paso 2 del prompt.

**Cómo se corrige.** Mandá `umbrales` en la entrada. Cuando tengas doscientas conversaciones,
mirá qué score traían las que cerraron y mové los cortes ahí. Hasta entonces, dos tramos mal
puestos son mejores que ninguno.

---

## S04 · Tres horarios, dentro de los próximos cinco días hábiles

**Qué asumí.** Que el paso 3 cierra ofreciendo tres huecos, y que salen de los próximos cinco
días hábiles.

**Por qué.** Una lista larga hace que el contacto no elija ninguno y conteste "después te aviso".
Y lo que se agenda a tres semanas se cae: el que preguntó a las tres de la mañana ya no se
acuerda de qué preguntó.

**Dónde.** `contratos/entrada.schema.json` → `opciones_horario`, con 3 de default y techo de 5.
`contratos/salida.schema.json` → `respuesta.horarios_ofrecidos`. La aserción 3 de
`pruebas/caso-01.md`.

**Cómo se corrige.** `opciones_horario` acepta de 1 a 5. La ventana la ponés vos: el agente
ofrece huecos de `disponibilidad` y de ningún otro lado, así que mandando solo los que querés
que se ofrezcan, la ventana es la que vos mandaste. Un horario que no esté en esa lista es fallo
del agente, no una mejora.

---

## S05 · Google Calendar por cuenta de servicio, y la confirmación por WhatsApp

**Qué asumí.** Que el paso 4 crea el evento con una cuenta de servicio sobre
`GOOGLE_CALENDAR_ID`, y que al contacto se le avisa por WhatsApp. No hay invitación de
calendario y el contacto no queda como invitado del evento.

**Por qué.** Una cuenta de servicio sin delegación de dominio no puede invitar a nadie: la API
rechaza el invitado. Si la invitación fuera el aviso, el contacto no se enteraría nunca de la
cita que acaba de aceptar. Por eso la confirmación sale por el mismo chat, y el recordatorio de
24 horas antes también.

**Dónde.** `contratos/salida.schema.json` → `cita.recordatorio_programado`. `env.example` →
`GOOGLE_CALENDAR_ID` y `GOOGLE_SERVICE_ACCOUNT_JSON`. `PINES.md` → la nota de APScheduler.

**Cómo se corrige.** Con delegación de dominio en Workspace, la cuenta de servicio sí puede
invitar, y ahí conviene poner al contacto como invitado. Eso lo habilita quien administra el
Workspace, no el agente. Ojo con el recordatorio: cae casi siempre fuera de la ventana de 24
horas de WhatsApp, así que necesita una plantilla aprobada. Ver `PENDIENTES.md`.

---

## S06 · El CRM es una tabla `leads`

**Qué asumí.** Que el paso 5 escribe una fila por contacto en una tabla `leads` de Supabase o
Postgres, con etapa, resumen, próximo paso y fecha, indexada por el identificador del contacto.

**Por qué.** Había que elegir una forma concreta para que el paso 5 se pudiera probar. Supabase
es lo más común entre quienes pidieron esto y abajo es Postgres, así que apuntar a otra base es
cambiar dos variables y no reescribir el paso.

**Dónde.** `contratos/salida.schema.json` → `crm`. `env.example` → `SUPABASE_URL`,
`SUPABASE_SERVICE_KEY` y `DATABASE_URL`.

**Cómo se corrige.** Si tu CRM es HubSpot, Pipedrive o una planilla, dejá las variables sin
poner: el paso 5 devuelve la fila en la salida con `crm.escrito` en falso y la carga alguien más.
Escribir contra otra API es trabajo de `/conectar`, no de `/configurar`.

---

## S07 · Los audios se transcriben con la API de Whisper

**Qué asumí.** Que el paso 1 transcribe con `OPENAI_API_KEY` antes de leer el mensaje.

**Por qué.** Por WhatsApp entra mucho audio y había que elegir un transcriptor. Whisper acepta el
formato en que llega el audio de Meta sin conversión previa, que es un paso menos que puede
fallar en la máquina de quien instala.

**Dónde.** `env.example` → `OPENAI_API_KEY`. El paso 1 del prompt. La aserción 1 de
`pruebas/caso-01.md`.

**Cómo se corrige.** Cambiá el transcriptor por el que uses. Lo que no se toca es la conducta sin
credencial: un audio que no se puede transcribir detiene el ciclo con el motivo escrito. El
agente no adivina qué decía, y un `media_id` no se le pasa nunca a una API de visión.

---

## S08 · La lista de palabras de escalación

**Qué asumí.** Seis palabras de arranque: humano, persona real, reclamo, abogado, estafa,
cancelar.

**Por qué.** Son las que suelen aparecer justo antes de que una conversación se rompa. Es un
default para que el paso 6 exista desde el primer mensaje, no una lista buena para tu rubro: en
cobranzas "reclamo" aparece en todos los chats, y escalar todo es lo mismo que no escalar nada.

**Dónde.** `contratos/entrada.schema.json` → `palabras_escalacion`. El paso 6 del prompt.

**Cómo se corrige.** Mandá tu lista: reemplaza la de arriba entera, no se suma. `/configurar` la
pregunta. Revisala al mes con las conversaciones que escalaste a mano y que el agente no marcó.

---

## S09 · El aviso interno sale por un webhook de Slack

**Qué asumí.** Que el paso 6 avisa con `SLACK_WEBHOOK_URL` al canal que pusiste en
`canal_interno`.

**Por qué.** Es el canal interno más común entre quienes pidieron esto, y un webhook entrante no
pide OAuth ni una app aprobada: se crea en dos minutos y no hay nada que revisar.

**Dónde.** `env.example` → `SLACK_WEBHOOK_URL`. `contratos/entrada.schema.json` →
`canal_interno`. `contratos/salida.schema.json` → `handoff.avisado_en`. La función es
`avisar_interno()` y vive en `agente/enviar.py`, que es el dueño de todo lo que sale del proceso
hacia una persona; ver `blueprint/32-multimodal.md` paso 5.

**Sin la variable, el paso 6 queda `fallado` con el motivo escrito.** La escalación pasa igual: el
`handoff` queda en la salida con su disparador, `crm.etapa` va a `escalado` y `avisado_en` queda
nulo. Lo que se pierde es el aviso, no el handoff, y el ciclo lo dice en vez de seguir como si
hubiera avisado.

**Y la otra forma de `canal_interno` no se comporta igual.** El contrato permite «un canal de
Slack, o un número interno de WhatsApp si no hay Slack», y esas dos cosas son distintas del lado de
Meta:

| `canal_interno` | Qué es | En `borrador` | Cuesta |
|---|---|---|---|
| `#ventas-escalaciones` | un POST a un webhook entrante | **sale** | nada: no sale del número del negocio |
| `5215500000099` | un mensaje de WhatsApp | **no sale**: espera confirmación | plantilla aprobada, y calificación del número |

**Meta no distingue el número de tu compañero del de un cliente.** Los dos son salientes del mismo
número de negocio, los dos caen bajo la ventana de 24 horas y los dos pesan en la calificación. Por
eso el aviso por número sale por `enviar()` como cualquier otro mensaje —con la ventana, el chequeo
de baneo y la `Idempotency-Key`— y por eso no sale en `borrador`: el modo promete que nada sale sin
confirmación explícita, y «esto es interno» es una distinción que del otro lado no existe.

Dos consecuencias que conviene saber antes de poner un número ahí. **Necesita una plantilla
aprobada**, `escalacion_interna`, porque ese número nunca le escribió al negocio y su ventana de 24
horas está cerrada siempre; el cuerpo a dar de alta está en `blueprint/32-multimodal.md` paso 5, y
hasta que Meta la apruebe el paso 6 queda `fallado` con el motivo. Y **en `borrador` la escalación
se lee del panel**, no del teléfono de tu compañero: el paso 6 queda `sin-confirmar` y el aviso sale
con el mismo `confirmado: true` que deja salir la línea del paso 3.

Hasta esta ronda el aviso por número salía en los dos modos, por el endpoint de mensajería, sin
ventana, sin chequeo de baneo, sin la guarda de no escribir primero y sin `Idempotency-Key`. Medido
en `borrador`: cero mensajes al contacto y un `POST .../inbox/conversations/interno-…/messages`.
No era un defecto de un build: era lo que este kit prescribía y lo que su suite exigía.

**Y eso ahora lo afirma una prueba, sin ninguna credencial.** La suite inyecta por fixture una
`SLACK_WEBHOOK_URL` inventada —`https://hooks.slack.com/services/T00000000TEST/B00000000TEST/pruebas-sin-credencial`—
que nunca sale del proceso porque el transporte está doblado: el doble cuenta el aviso por el host y
no abre un socket. No es una credencial, es una URL con la forma correcta, así que sigue siendo
cierto que nada de `pruebas/` pide una clave. Con la variable puesta se cuenta el aviso —uno, en los
dos modos—; sin ella se afirma el `fallado` con el motivo. Antes de esto, la mitad de arriba no la
podía probar nadie, y la única salida que le quedaba a quien construía era escribir una URL de
webhook adentro del árbol.

**Cómo se corrige.** Para avisar por otro lado —un número interno de WhatsApp, un correo— se cambia
el destino del paso 6 con `/conectar`. El aviso por WhatsApp sale por el mismo `/messages` que el
mensaje al contacto y no se cuenta como envío al contacto: lo separa el destinatario, no la ruta.
El default sigue siendo Slack, y con lo de arriba se entiende por qué: es el único de los dos que
no gasta la calificación del número ni depende de una plantilla aprobada.

---

## S10 · El caso de prueba usa un fixture sintético

**Qué asumí.** Que el mensaje, el playbook, el catálogo y la agenda de `pruebas/caso-01.md` los
escribimos nosotros. No es una conversación de nadie.

**Por qué.** Esta corrida se hizo sin acceso a conversaciones reales, y una conversación real no
se publica sin consentimiento de las dos puntas. Las seis aserciones salen de los seis pasos y
no del caso, así que el caso se puede reemplazar entero sin tocarlas.

**Dónde.** `pruebas/caso-01.md` y `pruebas/caso-02.md`. No confundir con `pruebas/fixtures/*.raw`:
esos son bytes crudos grabados de entregas reales y no se regeneran nunca con `json.dumps`. Los
`*.entrada.json` sí salen de la prosa, y `pruebas/extraer_fixture.py` es el que impide que
deriven.

**Cómo se corrige.** Pegá una conversación tuya en lugar de la entrada, corré
`python -m pruebas.extraer_fixture --escribir` y después `/probar`. Las aserciones no cambian:
salen de los seis pasos y no del caso. El caso 02, el del enojo, ya está escrito.

---

## S11 · La línea de handoff del paso 6 no saltea la compuerta de `borrador`

**Qué asumí.** Que el mensaje que le avisa al contacto que lo sigue una persona es un envío como
cualquier otro. En modo `borrador` queda redactado, esperando confirmación, igual que el del
paso 3. No tiene vía rápida.

**Por qué.** Es el mensaje que sale en el peor momento de la conversación: alguien enojado,
alguien que nombró un abogado, alguien que pidió cancelar. Es el último que conviene dejar salir
sin que lo lea una persona.

**Y el humano se entera igual, si el canal interno es Slack.** Ese aviso no es un mensaje de
WhatsApp: no sale del número del negocio, no depende de esta compuerta y sale en los dos modos.
Hasta esta ronda acá decía «sale siempre», sin condición, y era el argumento entero de este
supuesto. Con `canal_interno` en un número de WhatsApp es falso: ese aviso **sí** es un mensaje de
WhatsApp y en `borrador` tampoco sale —S09 lo explica—. Ahí la escalación se lee del panel, y el
aviso sale con la misma confirmación que deja salir esta línea. La otra mitad de S11 no cambia: la
línea al contacto no tiene vía rápida en ningún caso.

**El contrapunto.** Un operador razonable quiere lo contrario, y tiene un argumento bueno: con la
bandeja cerrada, el contacto enojado se queda sin ninguna respuesta hasta que alguien abra el
chat, y el silencio frente a un reclamo también es una respuesta, peor que la línea. Quien tiene
que decidir eso es el negocio. Elegimos el default que se deshace con una línea de configuración
y no el que se descubre con un cliente. Con el canal interno en un número, el contrapunto pesa más
—nadie se entera hasta que alguien abra el panel—, y por eso el default de S09 sigue siendo Slack.

**Dónde.** El paso 6 del prompt. `contratos/salida.schema.json` → `handoff` y
`respuesta.enviado`. La regla del modo, en `CLAUDE.md`.

**Cómo se corrige.** Con el paso 3 en `automatico` esa línea sale sola, porque es el mismo camino
de envío. Si querés que salga sola y el resto siga en borrador, es una excepción explícita en el
paso 6: escribila como excepción, con el motivo al lado, para que dentro de seis meses no parezca
un olvido.

---

## S12 · La identidad se ancla en `businessScopedUserId`, no en el teléfono

**Qué asumí.** Que el contacto se identifica por `contacto_id` —el `businessScopedUserId` del
proveedor— y que todo lo guardado se indexa por ahí. Cuando no hay teléfono, `contacto.numero`
sale como `bsuid:<id>`.

**Por qué.** Desde abril de 2026 alguien con nombre de usuario de WhatsApp le escribe a un
negocio sin exponer el número, y `phoneNumber` llega nulo. Un handler que indexe por número
pierde el historial de esa gente, o se lo mezcla con el de otra. El prefijo `bsuid:` es para que
lo que intente marcar ese valor falle fuerte en vez de marcar un número equivocado.

**Dónde.** `contratos/entrada.schema.json` → `mensaje.de` y `mensaje.contacto_id`, con la regla
de que tiene que venir uno de los dos. `contratos/salida.schema.json` → `contacto.numero` y
`contacto.id`. El fixture `pruebas/fixtures/zernio.raw`, que trae `phoneNumber` nulo y
`businessScopedUserId` con valor a propósito.

**Cómo se corrige.** Este no se corrige, se respeta. Si tu CRM exige un teléfono válido en esa
columna, guardá el identificador en otra columna y dejá el teléfono vacío. Nunca un número
inventado, nunca el del negocio: esa fila después la llama alguien.
