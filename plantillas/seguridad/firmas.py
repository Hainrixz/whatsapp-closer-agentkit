"""Verificación de firmas de webhook. Meta y Zernio.

Python 3.11+. Sin dependencias: solo `hmac` y `hashlib` de la biblioteca estándar.

## Por qué todo acá toma bytes y nunca un dict

El que firma calcula el MAC sobre **los bytes exactos que puso en el cable**. No sobre el
significado del JSON: sobre los octetos, con el espaciado que tengan, con las tildes escapadas
como se le haya ocurrido escaparlas, con el orden de claves que haya elegido.

En cuanto parseás ese cuerpo perdés todo eso. `json.loads` te devuelve un dict que ya no
recuerda si la sangría era de dos o de cuatro espacios, ni si la `á` venía como `\\u00e1` o como
dos bytes UTF-8. `json.dumps` de ese dict produce **otros bytes**, y otros bytes producen otro
MAC.

Este es el defecto que este archivo existe para prevenir:

    # MAL. Se lee bien. Pasa todas las pruebas que escribiría quien lo escribió.
    # Falla el 100% de las entregas reales, con un 401 que el que manda nunca te muestra.
    firma_ok = verificar(json.dumps(await request.json()), cabecera)

    # BIEN.
    firma_ok = verificar(await request.body(), cabecera)

Por eso las funciones de acá rechazan `str`, `dict` y `list` con un `TypeError` en vez de
convertirlos por cortesía. No es rigidez: es el único momento en que ese error todavía se puede
ver. Si lo dejamos pasar, aparece recién en producción y no dice qué pasó.

Un molde con un hash adentro no prueba que el código sea correcto. Los fixtures de
`pruebas/fixtures/` sí: traen bytes crudos con espaciado que `json.dumps` no puede producir, y
una implementación que reserializa **no puede** reproducir el MAC. Ver el README de esa carpeta.

## Por qué `hmac.compare_digest` y nunca `==`

`==` sobre cadenas corta en el primer byte distinto. El tiempo que tarda filtra cuántos
caracteres del principio acertaste, y eso alcanza para adivinar una firma byte por byte contra
un servicio que responde rápido. `compare_digest` compara en tiempo constante.
"""

from __future__ import annotations

import hashlib
import hmac

__all__ = [
    "CABECERA_META",
    "CABECERA_ZERNIO",
    "CABECERA_EVENTO_ZERNIO",
    "PREFIJO_META",
    "TIPO_RESPUESTA_ALTA",
    "AltaRechazada",
    "firmar_meta",
    "verificar_meta",
    "firmar_zernio",
    "verificar_zernio",
    "responder_alta_meta",
]


# ─────────────────────────────────────────────────────────────
# Nombres de cabecera. Acá y en ningún otro lado.
# ─────────────────────────────────────────────────────────────

CABECERA_META = "X-Hub-Signature-256"
"""Meta firma cada entrega acá. El valor es `sha256=<hex>`."""

PREFIJO_META = "sha256="
"""Meta escribe el prefijo. Zernio no. Es la única diferencia de formato entre los dos."""

CABECERA_ZERNIO = "X-Zernio-Signature"
"""Zernio firma acá. Hex minúscula pelado, sin prefijo."""

CABECERA_EVENTO_ZERNIO = "X-Zernio-Event-Id"
"""Id del evento. Zernio entrega al-menos-una-vez y reintenta hasta 7 veces: el handler
deduplica por este valor o el mismo lead recibe la misma respuesta cuatro veces."""

TIPO_RESPUESTA_ALTA = "text/plain; charset=utf-8"
"""El `Content-Type` con el que se contesta la verificación GET de Meta. Ver
`responder_alta_meta`."""


_Crudo = bytes | bytearray | memoryview
_Secreto = str | bytes


class AltaRechazada(ValueError):
    """La verificación GET del webhook no cuadra: modo distinto de `subscribe`, o token que no
    coincide. Se contesta 403 y no se devuelve el challenge."""


# ─────────────────────────────────────────────────────────────
# Guardas
# ─────────────────────────────────────────────────────────────


def _exigir_bytes(valor: object, funcion: str) -> bytes:
    """Deja pasar bytes y frena cualquier cosa ya parseada, con el motivo escrito.

    Esta guarda es el corazón del archivo. La firma de tipos sola no alcanza: en Python una
    anotación no rechaza nada en tiempo de ejecución, y un dict pasa igual. Acá se rechaza de
    verdad, en el único momento en que el error todavía es visible.
    """
    if isinstance(valor, bytes):
        return valor
    if isinstance(valor, (bytearray, memoryview)):
        return bytes(valor)

    recibido = type(valor).__name__
    raise TypeError(
        f"{funcion}() recibió {recibido} y necesita bytes: el cuerpo crudo, tal como llegó. "
        "En FastAPI o Starlette eso es `await request.body()`. "
        "`json.dumps(await request.json())` reserializa: cambia el espaciado y el escapado de "
        "las tildes, produce otros bytes y por lo tanto otro MAC. Se lee bien, pasa las "
        "pruebas locales y devuelve 401 en todas las entregas reales."
    )


def _secreto_en_bytes(secreto: _Secreto) -> bytes:
    if isinstance(secreto, bytes):
        return secreto
    if isinstance(secreto, str):
        return secreto.encode("utf-8")
    raise TypeError(
        f"El secreto tiene que ser str o bytes, no {type(secreto).__name__}. "
        "Sale de `.env` y nunca de un archivo del repo."
    )


def _normalizar_cabecera(cabecera: str | bytes | None) -> bytes:
    """Deja la cabecera recibida lista para comparar, sin decidir nada sobre su validez.

    Se recorta el espacio de los bordes y se baja a minúscula. Ninguna de las dos cosas afloja
    la verificación: el hex no distingue mayúsculas de minúsculas, así que no se pierde
    entropía, y lo que se evita es un 401 falso si una pasarela intermedia normaliza el valor. Se
    codifica con `replace` para que una cabecera con basura no ASCII haga fallar la comparación
    en vez de reventar con TypeError adentro de `compare_digest`.
    """
    if cabecera is None:
        return b""
    if isinstance(cabecera, (bytes, bytearray, memoryview)):
        cabecera = bytes(cabecera).decode("utf-8", "replace")
    return cabecera.strip().lower().encode("utf-8", "replace")


# ─────────────────────────────────────────────────────────────
# Meta · WhatsApp Cloud API
# ─────────────────────────────────────────────────────────────


def firmar_meta(cuerpo_crudo: _Crudo, /, *, secreto: _Secreto) -> str:
    """Devuelve el valor completo de `X-Hub-Signature-256` para este cuerpo: `sha256=<hex>`.

    `cuerpo_crudo` es posicional a propósito: sin nombre de parámetro que invite a pasarle
    `payload=` o `datos=`, cuesta más equivocarse de cosa.

    Sirve para dos usos y ninguno más: firmar las entregas grabadas del proveedor `demo`, y
    escribir pruebas. Nada de lo que sale del agente se firma con esto.
    """
    octetos = _exigir_bytes(cuerpo_crudo, "firmar_meta")
    hexa = hmac.new(_secreto_en_bytes(secreto), octetos, hashlib.sha256).hexdigest()
    return PREFIJO_META + hexa


def verificar_meta(
    cuerpo_crudo: _Crudo,
    /,
    *,
    cabecera: str | bytes | None,
    secreto: _Secreto,
) -> bool:
    """¿La cabecera `X-Hub-Signature-256` corresponde a estos bytes crudos?

    `cuerpo_crudo` tiene que ser `await request.body()`. Si le pasás el JSON reserializado
    devuelve TypeError, no False: un False acá se confunde con un atacante y se investiga
    durante horas.

    `cabecera` en None —la entrega llegó sin firmar— devuelve False. No devuelve True "porque
    no había nada que verificar": un webhook público sin firma es cualquiera escribiéndole a tu
    número.

    Devuelve un bool. Contestá 401 cuando sea False, y hacelo antes de parsear el cuerpo: lo
    que no está firmado no merece ni un `json.loads`.
    """
    octetos = _exigir_bytes(cuerpo_crudo, "verificar_meta")
    esperado = firmar_meta(octetos, secreto=secreto).encode("ascii")
    return hmac.compare_digest(esperado, _normalizar_cabecera(cabecera))


def responder_alta_meta(
    *,
    hub_mode: str | None,
    hub_verify_token: str | None,
    hub_challenge: str | None,
    verify_token: str,
) -> str:
    """Resuelve la verificación GET del alta del webhook y devuelve el challenge, verbatim.

    Meta da de alta un webhook con un GET que trae `hub.mode`, `hub.verify_token` y
    `hub.challenge`. Si el token coincide, hay que devolver el challenge **tal cual vino**.

    **Devolvelo como texto plano.** Meta compara la respuesta cruda contra lo que mandó:

        # MAL. El alta falla y no aparece ningún error: la pantalla simplemente no se suscribe.
        return {"hub.challenge": challenge}
        return JSONResponse(challenge)

        # BIEN.
        return PlainTextResponse(challenge, media_type=TIPO_RESPUESTA_ALTA)

    `JSONResponse("1158201444")` manda `"1158201444"` con las comillas adentro del cuerpo. Son
    dos bytes de más y alcanzan para que el alta no ocurra.

    Levanta `AltaRechazada` cuando el modo no es `subscribe` o el token no coincide. Ahí se
    contesta 403 y no se devuelve nada más.
    """
    if hub_mode != "subscribe":
        raise AltaRechazada(
            f"`hub.mode` llegó como {hub_mode!r} y tiene que ser 'subscribe'."
        )

    recibido = (hub_verify_token or "").encode("utf-8", "replace")
    propio = verify_token.encode("utf-8")
    if not propio:
        raise AltaRechazada(
            "`WHATSAPP_VERIFY_TOKEN` está vacío. Con el token vacío el alta la pasa cualquiera: "
            "escribilo en `.env` antes de dar de alta el webhook."
        )
    if not hmac.compare_digest(propio, recibido):
        raise AltaRechazada(
            "`hub.verify_token` no coincide con `WHATSAPP_VERIFY_TOKEN`. Tiene que ser idéntico "
            "en los dos lados, carácter por carácter."
        )

    if hub_challenge is None:
        raise AltaRechazada("El GET vino sin `hub.challenge` y no hay nada que devolver.")

    return hub_challenge


# ─────────────────────────────────────────────────────────────
# Zernio · pasarela sobre Meta
# ─────────────────────────────────────────────────────────────


def firmar_zernio(cuerpo_crudo: _Crudo, /, *, secreto: _Secreto) -> str:
    """Devuelve el valor de `X-Zernio-Signature` para este cuerpo: hex minúscula, sin prefijo.

    La diferencia con Meta es de formato y nada más: mismo HMAC-SHA256, mismo cuerpo crudo, sin
    el `sha256=` adelante. Copiar la función de Meta y olvidarse de sacar el prefijo da un 401
    permanente que se lee igual que un secreto mal escrito.
    """
    octetos = _exigir_bytes(cuerpo_crudo, "firmar_zernio")
    return hmac.new(_secreto_en_bytes(secreto), octetos, hashlib.sha256).hexdigest()


def verificar_zernio(
    cuerpo_crudo: _Crudo,
    /,
    *,
    cabecera: str | bytes | None,
    secreto: _Secreto,
) -> bool:
    """¿La cabecera `X-Zernio-Signature` corresponde a estos bytes crudos?

    Mismas reglas que `verificar_meta`: bytes crudos o TypeError, None es False, y el 401 sale
    antes de parsear nada.

    Dos cosas de Zernio que no son de este archivo pero mueren si esto se hace mal. Hay que
    contestar 2xx en menos de 5 segundos, así que la verificación va primero y el trabajo
    después. Y la entrega es al-menos-una-vez: además de la firma, deduplicá por
    `CABECERA_EVENTO_ZERNIO`.
    """
    octetos = _exigir_bytes(cuerpo_crudo, "verificar_zernio")
    esperado = firmar_zernio(octetos, secreto=secreto).encode("ascii")
    return hmac.compare_digest(esperado, _normalizar_cabecera(cabecera))
