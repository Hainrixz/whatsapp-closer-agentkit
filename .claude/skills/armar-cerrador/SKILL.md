---
name: armar-cerrador
description: Construye el cerrador de WhatsApp entero, fase por fase, desde el blueprint. Usala en la primera corrida del kit.
disable-model-invocation: true
---

# Armar el cerrador

**Primero buscá `.wca-estado.json` en la raíz.**

Si existe y la construcción quedó a medias, no reinicies. Pasá al procedimiento de `/seguir`,
decí en qué fase quedó y esperá confirmación explícita antes de pisar un solo archivo. Correr
esto dos veces es lo más probable que va a pasar acá, y reiniciar borra el trabajo de quien
instala.

Si no existe, leé `blueprint/00-mapa.md` y seguí las fases en el orden que marca. Un archivo por
fase. Cada uno viene en cuatro tiempos: Objetivo, Hacé esto, Tenés que ver, Si falla. No pases a
la fase siguiente hasta que se cumpla lo que dice "Tenés que ver".

Las versiones y el modelo salen de `PINES.md`, nunca de tu memoria.
