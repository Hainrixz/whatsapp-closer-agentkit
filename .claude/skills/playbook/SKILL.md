---
name: playbook
description: Escribe o cambia el playbook de objeciones y el tono de cierre, sin tocar ninguna otra parte del kit.
disable-model-invocation: true
---

# Playbook

Leé `blueprint/25-playbook.md` y seguilo.

Toca el playbook y el tono, nada más: ni credenciales, ni proveedor, ni contratos, ni el resto
del estado. Si aparece algo de eso, decilo y mandá a la skill que corresponde.

El playbook es la lista de objeciones con su respuesta, y es campo obligatorio de la entrada. Una
objeción que no figura acá el agente no la contesta: la nombra y la deja para el humano.

Ninguna respuesta puede traer un precio, un plazo ni una promesa que no esté en el catálogo.

Mostrá la lista entera antes de escribirla y actualizá sólo la sección de playbook de
`.wca-estado.json`.
