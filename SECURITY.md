# Seguridad

Este repo no trae la aplicación: trae las instrucciones para construirla. Eso cambia dónde
puede estar un problema y cambia a quién le toca arreglarlo, así que va dicho primero.

## Lo que se reporta acá

Un defecto en el kit, que se le va a copiar a todos los que lo clonen:

- **Una firma que se verifica mal.** El invariante es que se comprueba sobre el cuerpo crudo
  y con `hmac.compare_digest`. Reserializar el JSON para firmarlo pasa todas las pruebas y
  falla todas las entregas reales, y un webhook que acepta una firma que no debería aceptar
  deja que cualquiera le hable a tu agente.
- **Un camino por el que sale un mensaje sin pasar por `enviar()`.** Ahí viven la ventana de
  24 horas, el chequeo de baneo y la regla de no escribirle primero a quien no escribió.
- **Una ruta de `/api/` que quedó fuera del `PANEL_TOKEN`.** El chequeo 21 lo mira, y si
  encontrás una que se le escapa, eso es un agujero al panel entero.
- **Una credencial que el blueprint escribe en un archivo del árbol**, o que termina en un
  log, en el CRM o en un mensaje al contacto.
- **Una plantilla de `plantillas/` cuyo sha256 no es el que dice `MANIFIESTO.json`.**
- **Un paso del blueprint que le hace bajar y correr algo de la red** a quien construye, sin
  decirlo.

## Lo que no se reporta acá

- **Tu credencial filtrada.** Si publicaste tu `WHATSAPP_TOKEN` o tu `META_APP_SECRET` en un
  issue, en un video o en una captura, esto no lo arregla nadie desde acá: **rotalo ahora** en
  el panel de Meta y volvé después. Un token que se hizo público hay que dar de baja, no
  borrar del post.
- **Un problema del código que Claude escribió en tu máquina.** No es el mismo árbol que el
  mío: el blueprint dice qué construir, y de la fase 30 en adelante lo que hay en `agente/` lo
  escribió tu corrida. Contalo igual, con la salida de la compuerta, y si resulta que el
  blueprint lo induce, ahí sí pasa a ser un defecto del kit.
- **Un fallo de WhatsApp, de Meta, de Zernio, de Google o de Anthropic.** Eso va al proveedor.

## Cómo se reporta

**En privado, nunca en un issue.** Un issue es público desde el segundo cero y no se puede
despublicar.

[**Abrir un aviso privado**](https://github.com/Hainrixz/whatsapp-closer-agentkit/security/advisories/new)

Si esa página no te carga, escribime por el canal donde estés viendo esto y decí sólo que es
de seguridad, sin el detalle. El detalle va después, en privado.

Poné, si lo tenés:

- el archivo y la línea, o el paso del blueprint;
- qué logra alguien con eso, en una frase;
- cómo se reproduce **sin credenciales de verdad** — con `WHATSAPP_PROVIDER=demo` alcanza para
  casi todo, porque reproduce entregas grabadas con los mismos bytes crudos y la misma cabecera
  de firma;
- la salida de `scripts/auditar.py`, que no abre sockets ni lee secretos.

## Qué esperar

Esto lo mantiene una persona, no una empresa: no hay guardia ni acuerdo de tiempos. Lo que sí
hay es esto, y lo cumplo o lo digo.

| | |
|---|---|
| Acuso recibo | dentro de 72 horas |
| Te digo si lo tomo como defecto del kit, y por qué | dentro de 7 días |
| Arreglo, con el chequeo que lo detecte de ahora en más | según qué sea, y te lo cuento |

Un arreglo de seguridad entra con la prueba que lo agarra. Un parche sin prueba lo vuelve a
abrir la siguiente ronda.

**Crédito.** Si querés, va tu nombre en el aviso y en `CITAS.md`. Si preferís que no, tampoco.
Decilo cuando reportás.

**Nada de programas de recompensa.** No hay plata de por medio y no la va a haber. Lo digo de
entrada para que nadie pierda el tiempo.

## Las versiones que miro

La última publicada. No hay ramas de soporte hacia atrás: el kit se clona entero y se vuelve a
clonar entero.

## Antes de publicar tu construcción

Tres cosas que no son defectos del kit y que igual te pueden costar caro, porque el kit no
las puede comprobar por vos:

1. **`.env` fuera del árbol.** Está en `.gitignore` y el chequeo 08 revisa siete patrones de
   credencial en cada archivo. Comprobalo igual antes del primer push:
   `git ls-files | grep -i env`.
2. **`knowledge/` también está ignorado**, y no por prolijidad: ahí caen los documentos crudos
   que subiste, que pueden tener datos de tus clientes y material de otro autor.
3. **`PANEL_TOKEN` largo y propio.** El panel expone las conversaciones enteras. Si lo dejás
   corto, lo que se filtra no es el kit: son los chats de tu gente.
