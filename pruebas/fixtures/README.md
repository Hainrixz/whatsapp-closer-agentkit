# Fixtures de firma

Entregas de webhook grabadas, con sus bytes crudos y la firma real de esos bytes. Son lo que
hace cumplir el invariante 1 de `CLAUDE.md`.

## Los archivos

| Archivo | Qué es |
|---|---|
| `meta.raw` | Cuerpo crudo de una entrega de la API de WhatsApp Cloud. 972 bytes. |
| `meta.meta.json` | El secreto de prueba, el nombre de la cabecera y la firma de esos 972 bytes. |
| `zernio.raw` | Cuerpo crudo de una entrega de Zernio. 789 bytes. |
| `zernio.meta.json` | Lo mismo para Zernio. |

Los `.raw` no terminan en salto de línea. Un cuerpo HTTP no lo trae, y un byte de más cambia
la firma.

El secreto de las dos fichas es `prueba-secreto-no-usar-en-produccion`. Es de prueba y está
escrito ahí a propósito: no firma nada real y no abre ninguna cuenta. El secreto de verdad vive
en `.env` y no entra a este árbol.

## Por qué el espaciado está raro

Los dos `.raw` traen, a propósito:

- Sangrías que no son múltiplos de nada, espacios antes de los dos puntos, un tabulador,
  espacios al final de una línea y una línea en blanco adentro de un objeto.
- La misma vocal escrita de las dos formas en el mismo cuerpo: `Fernández` escapada, y
  `está` con la `á` literal en UTF-8.

Nada de eso lo produce `json.dumps`. Y la segunda parte cierra la puerta por los dos lados: con
`ensure_ascii=True` cambia la tilde literal, con `ensure_ascii=False` cambia la escapada. No hay
combinación de banderas que devuelva estos bytes.

Ese es el punto entero. El defecto que estamos previniendo es este:

```python
# Se lee bien. Pasa todas las pruebas que escribiría quien lo escribió.
# Falla el 100% de las entregas reales, con un 401 que el que manda nunca te muestra.
firma_ok = verificar(json.dumps(await request.json()), cabecera)
```

Una plantilla con un hash adentro no prueba que el código sea correcto: prueba que alguien
escribió un hash. Un fixture con bytes crudos sí, porque una implementación que reserializa
**no puede** reproducir el MAC. La prueba no revisa el código: lo hace fallar.

## Cómo se usan

```python
crudo = (FIXTURES / "meta.raw").read_bytes()          # bytes, siempre
ficha = json.loads((FIXTURES / "meta.meta.json").read_text())

assert verificar_meta(crudo, cabecera=ficha["firma"], secreto=ficha["secreto"])

# y lo que tiene que fallar
reserializado = json.dumps(json.loads(crudo)).encode()
assert not verificar_meta(reserializado, cabecera=ficha["firma"], secreto=ficha["secreto"])
```

`read_bytes`, no `read_text`. Leerlos como texto y volver a codificarlos funciona hoy y deja de
funcionar el día que alguien cambie el `encoding` por default.

El módulo está en `plantillas/seguridad/firmas.py`.

## No los regeneres con `json.dumps`

Un `json.dumps(json.loads(...))` sobre estos archivos deja el JSON idéntico en significado, los
bytes canónicos y la firma recalculada. Todo verde. Y el fixture queda inerte: a partir de ahí
una implementación que reserializa pasa la prueba, que es exactamente lo único que esta carpeta
existía para impedir.

Si tenés que cambiar el contenido, escribí los bytes a mano —con el espaciado torcido
intacto— y recalculá la firma leyendo el archivo en binario:

```bash
python3 - <<'PY'
import hashlib, hmac, pathlib
secreto = b"prueba-secreto-no-usar-en-produccion"
for nombre in ("meta", "zernio"):
    crudo = pathlib.Path(f"pruebas/fixtures/{nombre}.raw").read_bytes()
    print(nombre, hmac.new(secreto, crudo, hashlib.sha256).hexdigest())
PY
```

Meta lleva el prefijo `sha256=` adelante del hex. Zernio no lleva ninguno.

## Qué más traen adentro

Los payloads no son de relleno. `zernio.raw` trae `phoneNumber` en nulo y
`businessScopedUserId` con valor, que es el caso de abril de 2026: alguien con nombre de usuario
de WhatsApp le escribe al negocio sin exponer el teléfono. Un handler que indexe por número se
rompe con este fixture antes de romperse con un cliente.
