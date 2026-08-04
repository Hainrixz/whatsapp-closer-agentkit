# Cerrador de WhatsApp

Este archivo está en contexto en cada turno. Todo lo que sobra acá se paga siempre, aunque
nadie lo use. Manténlo corto.

## Qué es este proyecto

Un agente que atiende cada chat entrante de WhatsApp con perfil de setter y closer: califica,
responde objeciones del playbook, agenda y deja la etapa y el próximo paso escritos en el CRM.

Lo construyó `agent-forge` en modo lote desde la ficha `whatsapp-closer-agent` del catálogo.
La procedencia está en `forja.json` y las citas en `CITAS.md`.

## El árbol

```
whatsapp-closer-agent/
├── agents/whatsapp-closer-agent.md   el agente
├── contratos/                         entrada y salida en JSON Schema
├── pruebas/caso-01.md                 una aserción por paso
├── env.example                        nombres de variables, nunca valores
├── README.md                          abre por el problema
├── CITAS.md                           los identificadores del corpus
├── SUPUESTOS.md                       los diez supuestos y cómo se corrigen
├── PENDIENTES.md                      las ocho piezas que faltan
└── forja.json                         procedencia y estado
```

## Cómo se dispara

Por webhook: un mensaje entrante de la API de WhatsApp Cloud abre un ciclo. También se invoca
a mano para retomar una conversación desde la etapa escrita en el CRM.

## Reglas de este proyecto

1. Los seis pasos son el contrato. Si sobra o falta uno, va a `SUPUESTOS.md` antes de tocarlo.
2. Los pasos 3, 4 y 5 escriben afuera. Piden confirmación explícita y no la saltean nunca.
3. El modo por defecto es `borrador`. Cambiarlo a `automatico` es una decisión de quien
   instala, no del agente.
4. Ningún precio, plazo ni promesa que no esté en el catálogo de la entrada.
5. Ninguna credencial en el árbol. Las nueve variables viven en `.env`, que no va a git.
6. Una dependencia que no está instalada se declara y se detiene. No se improvisa.
7. Español neutro con voseo, frases cortas, cero superlativos.

## Qué no hay que hacer acá

- No agregar pasos que no estén en la ficha sin registrarlo.
- No convertir un supuesto en una capacidad del README.
- No poner el texto de un comentario del corpus en ningún archivo.
- No marcar nada como listo sin correr `scripts/validar_artefacto.py`.
