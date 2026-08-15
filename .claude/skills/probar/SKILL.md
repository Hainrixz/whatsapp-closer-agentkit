---
name: probar
description: Abre el simulador de chat en la terminal y corre el caso contra el cerrador, sin credenciales.
disable-model-invocation: true
---

# Probar

Leé `blueprint/40-pruebas.md` y seguilo. El procedimiento vive ahí, no acá.

El simulador escribe como un contacto y muestra qué contesta el agente. Corre con el proveedor
`demo`, que no es un transporte falso: reproduce entregas grabadas, los mismos bytes crudos y la
misma cabecera de firma. No pide credenciales y lo que pasa acá vale.

Tres cosas que mirar:

- `pasos` trae seis elementos. Si trae cinco, el ciclo se cortó y la salida no valida.
- Con el modo en `borrador`, los pasos 3, 4 y 5 quedan en `sin-confirmar` y no escriben nada.
- Los horarios ofrecidos salen de `disponibilidad`. Uno que no esté ahí es fallo.

Cuando el caso pasa, corré `/revisar`. Un caso en verde no es la compuerta en verde.
