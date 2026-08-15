---
name: conectar
description: Agrega, cambia o rota una credencial, incluido pasar de un proveedor a otro entre meta, zernio y demo.
disable-model-invocation: true
---

# Conectar

Leé `blueprint/20-entrevista.md`, **tramo 3 · Q10 a Q12 · desde `/conectar`**, y seguilo. Ahí
están las tres preguntas —el proveedor, sus credenciales y qué más conectar— y el paso 13, que
cierra anotando en `.wca-estado.json` qué variables quedaron puestas y cuáles no.

El detalle de cada proveedor —la firma, las rutas y sus variables— está en
`blueprint/31-proveedores.md`: abrí la sección de `meta`, `zernio` o `demo` cuando el tramo 3 te
mande ahí. No mezcles las variables de uno con las del otro.

`demo` no pide credenciales. No es un transporte falso: reproduce entregas grabadas, los mismos
bytes crudos y la misma cabecera de firma. Sirve para probar el camino entero antes de conectar.

Los valores los escribe quien instala, en `.env`. Vos nombrás la variable, decís de dónde se
saca y verificás que esté puesta. Nunca la imprimís ni la copiás a otro archivo.

Cambiar de proveedor cambia la verificación de firma. Corré `/revisar` después.
