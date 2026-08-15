# Cerrador de WhatsApp · blueprint

Este archivo se paga en cada turno y es lo único que vuelve entero después de una
compactación. Lo que sobra acá sobra siempre.

No construyas de memoria: leé `blueprint/00-mapa.md` y seguí los archivos en orden, uno por
fase.

## Los seis pasos son el contrato

```
1 · Recibí el mensaje y traé el contexto
2 · Detectá la intención y calificá
3 · Respondé con el tono de marca y ofrecé horarios   ← le escribe a una persona
4 · Agendá y confirmá                                  ← escribe en la agenda
5 · Escribí en el CRM                                  ← escribe en la base
6 · Pasá el chat a un humano cuando corresponde
```

`pasos` trae **seis elementos, siempre**, aunque cinco queden salteados. Es lo que deja ver
dónde se cortó el ciclo.

Los pasos 3, 4 y 5 escriben afuera. El default es `borrador`: redactan, muestran y esperan
confirmación explícita. Pasar a `automatico` lo decide quien instala, nunca vos.

La forma exacta está en `contratos/`.

## Invariantes

1. Las firmas se verifican sobre el **cuerpo crudo**, con `hmac.compare_digest`. Reserializar
   el JSON para firmarlo pasa todas las pruebas y falla todas las entregas reales.
2. Ningún mensaje a un contacto sale si no es por `enviar()`: ventana de 24 horas, chequeo
   de baneo, y nunca escribirle primero a quien no escribió.
3. Un solo cliente HTTP, con `timeout=` explícito.
4. Ninguna credencial en el árbol. Los secretos los escribe quien instala, nunca una tool call.
5. Ningún precio ni plazo que no esté en el catálogo. Ninguna objeción que no esté en el
   playbook: se nombra y se deja para el humano.
6. Las versiones y el modelo salen de `PINES.md` y de ningún otro lado.

Nada queda listo sin `scripts/auditar.py` en verde.

## Los comandos

```
/armar-cerrador  construye            /probar     simulador de chat
/seguir          retoma a medias      /revisar    corre la compuerta
/playbook        estrategia de cierre /bandeja    aprobar borradores
/conectar        credenciales         /soltar     pasar a automático
/publicar        desplegar
/configurar      Q5 a Q9: catálogo, rango de precio, disponibilidad, escalación, canal interno
```

Viven en `.claude/skills/`, cada uno apunta a su `blueprint/`.

## Registro

Voseo con quien instala. Frases cortas, cero jerga, cero superlativos. Si algo no se puede
hacer, decilo con el motivo en vez de rodearlo.

El agente le habla a los clientes con el tratamiento elegido en la entrevista — `tú`, `vos` o
`usted` — que no tiene por qué ser el tuyo.
