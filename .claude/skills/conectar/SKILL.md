---
name: conectar
description: Agrega, cambia o rota una credencial, incluido pasar de un proveedor a otro entre meta, zernio y demo.
disable-model-invocation: true
---

# Conectar

Leé `blueprint/31-proveedores.md` y seguí la sección del proveedor que corresponda: `meta`,
`zernio` o `demo`. Cada uno tiene su firma, sus rutas y sus variables. No mezcles las de uno
con las del otro.

`demo` no pide credenciales. No es un transporte falso: reproduce entregas grabadas, los mismos
bytes crudos y la misma cabecera de firma. Sirve para probar el camino entero antes de conectar.

Los valores los escribe quien instala, en `.env`. Vos nombrás la variable, decís de dónde se
saca y verificás que esté puesta. Nunca la imprimís ni la copiás a otro archivo.

Cambiar de proveedor cambia la verificación de firma. Corré `/revisar` después.
