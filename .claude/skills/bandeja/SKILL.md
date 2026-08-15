---
name: bandeja
description: Abre la bandeja de borradores: mostrás de a uno con su razonamiento y decidís si sale, se corrige o se salta.
disable-model-invocation: true
---

# Bandeja

Leé `blueprint/60-bandeja.md` y seguilo.

De a uno, nunca en lote. Con cada borrador va el panel de razonamiento, y son tres cosas: el
score con el motivo de por qué ese y no otro, si la objeción estaba en el playbook o el agente
la nombró y la dejó para vos, y de qué hueco de `disponibilidad` salió cada uno de los tres
horarios.

Cuatro respuestas: `va`, `no`, `corregí <texto>`, `saltar`. Nada más.

`bandeja resumen` cuenta cuántos salieron tal cual y, sobre todo, lista **las objeciones que
aparecieron y no están en el playbook**. Esa lista es el producto de este comando: convierte
dos semanas de esperar en dos semanas de construir el playbook.
