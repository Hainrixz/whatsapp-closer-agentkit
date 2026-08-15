---
name: revisar
description: Corre la compuerta de auditoría y te dice qué falta antes de publicar.
allowed-tools: Bash(python3 ${CLAUDE_PROJECT_DIR}/scripts/auditar.py:*), Bash(true)
disable-model-invocation: true
---

<!-- Dos cosas que parecen de más y no lo son: sin ellas esto falla en silencio.
     `|| true`: si el comando inyectado sale distinto de cero se aborta la invocación entera
     y Claude no ve nada. Y salir distinto de cero es el caso normal, es lo que hace la
     auditoría cuando encuentra algo.
     `allowed-tools`: sin esa línea el chequeo de permisos aborta igual. No las limpies. -->

```!
python3 ${CLAUDE_PROJECT_DIR}/scripts/auditar.py --formato texto || true
```

# Revisar

Leé el reporte de arriba: es la compuerta. Por cada hallazgo decí qué invariante rompe, con
archivo y línea, y arreglalo. En verde, decilo en una línea y parás.
