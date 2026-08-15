# 05 · El arranque

**Fase 0.** Entrás con un clon recién bajado; salís con el terreno medido, el costo dicho y el
destino elegido.

Acá no se instala nada y no se escribe una sola línea. Esta fase **mide y pregunta**: qué hay en
esta máquina, qué va a costar, dónde va a correr y por dónde van a entrar los mensajes. Instalar es
de la fase 1, y arreglar lo que falte también.

Se entra por dos puertas y las dos pasan por acá: `/start`, que conduce los ocho tiempos de punta a
punta, y `/armar-cerrador`, que construye. Ninguna de las dos empieza en `blueprint/10-entorno.md`
sin haber pasado por este archivo, porque las cuatro respuestas de acá cambian qué se prepara
después.

**Invariante 4:** ninguna credencial se toca en esta fase, y eso incluye no pedirlas. La primera es
la clave de Anthropic, en la fase 1. **Invariante 6:** las versiones salen de `PINES.md` y de ningún
otro lado, así que acá se remite y no se copia un número.

---

### Paso 1 · Mirá el terreno

**Objetivo.** Sabés en diez segundos si a esta máquina le falta algo: sistema, Python, Claude Code y
si el árbol es un clon de git. Las cuatro cosas juntas y en una sola pantalla.

**Hacé esto.** Un solo bloque, que mide y no arregla. En macOS, Linux, WSL y Git Bash:

```bash
echo "sistema: $(uname -s -m)"
echo "python:  $(python3 --version 2>&1)"
echo "claude:  $(claude --version 2>&1)"
echo "git:     $(git rev-parse --is-inside-work-tree 2>&1)"
```

En Windows con PowerShell o `cmd`:

```powershell
"sistema: $env:OS $env:PROCESSOR_ARCHITECTURE"
"python:  $(py -3 --version 2>&1)"
"claude:  $(claude --version 2>&1)"
"git:     $(git rev-parse --is-inside-work-tree 2>&1)"
```

**Tenés que ver.** Cuatro líneas, con estas cuatro etiquetas:

```
sistema: Darwin arm64
python:  Python 3.12.8
claude:  2.1.232 (Claude Code)
git:     true
```

Los valores van a ser otros. Lo que se mira en cada línea:

- **`sistema`** — `Darwin`, `Linux`, `MINGW64_NT…` o `Windows_NT`. Decide dónde va a vivir el
  intérprete del entorno virtual, `bin/` o `Scripts/`, y eso lo resuelve la tabla de los cinco
  sistemas de `blueprint/10-entorno.md` paso 1.
- **`python`** — un número, no un «command not found». Que caiga en el rango lo verifica
  `blueprint/10-entorno.md` paso 2, piso y techo. **El rango vive en `PINES.md` → Python** y no se
  copia acá: un número repetido en dos archivos algún día dice dos cosas distintas.
- **`claude`** — el primer número tiene que ser 2 o más. El piso lo declara
  `.claude-plugin/plugin.json`, clave `engines.claude-code`.
- **`git`** — `true`, pelado. Cualquier otra cosa quiere decir que esto no es un clon.

Anotá las cuatro y seguí. **Medí todo antes de arreglar nada**: si parás en la primera línea que
falla, quien instala descubre lo que le falta de a una cosa por vez.

**Si falla.**

- **`uname: command not found` o `no se reconoce como un comando`.** No es un error, es la
  respuesta: estás en PowerShell o en `cmd`. Corré el segundo bloque.
- **En PowerShell una línea sale en rojo en vez de con un valor.** También es la respuesta: ese
  comando no existe en esta máquina. Anotalo y seguí con las otras tres.
- **`python3: command not found`.** No hay Python, o no está en el PATH. No lo instales desde acá:
  la tabla por sistema —Homebrew, el instalador de python.org, `apt`, `dnf`, `winget`—, la trampa de
  `python3.12-venv` en Debian y la casilla **Add python.exe to PATH** del instalador de Windows
  están en `blueprint/10-entorno.md` paso 2, que es su dueño. Anotá que falta y seguí midiendo.
- **Imprime una versión y está fuera del rango de `PINES.md`.** No la persigas todavía. El rango se
  verifica entero —con el techo, que es el que sorprende— en `blueprint/10-entorno.md` paso 2, y
  ahí está qué hacer con una demasiado nueva y con una demasiado vieja. Instalar una del rango no
  obliga a desinstalar la que tenés.
- **Imprime una versión y no es la que se va a usar.** Máquina con varias, que es lo común en una
  que ya se usó para algo. No elijas acá: `blueprint/10-entorno.md` paso 2 las lista todas con su
  ruta y explica con cuál quedarse.
- **`claude: command not found`, y sin embargo esta sesión está corriendo.** Pasa con la instalación
  nativa fuera del PATH del shell, o cuando Claude Code corre dentro de un IDE. No lo persigas:
  pedile a quien instala que escriba `/status` en la sesión y te dicte el número.
- **El primer número de `claude` es menor que 2.** Se actualiza con `claude update`, y el detalle
  está en `blueprint/10-entorno.md` paso 3. Por qué importa acá: con una versión vieja las skills
  del kit se leen como texto plano, no tiran un solo error, y la compuerta no corre. La protección
  desaparece justo cuando hacía falta, y en silencio.
- **`fatal: not a git repository`.** Bajaste un ZIP en vez de clonar. Pará acá: el ZIP llega sin
  `.git`, y tres verificaciones del kit preguntan a git —que `.env` esté ignorado, el chequeo de
  secretos y el de `knowledge/`—. Con un ZIP no fallan: saltean. Cloná y volvé a empezar:

  ```bash
  git clone https://github.com/Hainrixz/whatsapp-closer-agentkit.git
  ```
- **`sistema` imprime algo que no está en la lista** (`SunOS`, `FreeBSD`, Android en Termux). No hay
  instrucción probada para ese sistema y no la voy a inventar. Preguntá con qué gestor de paquetes
  instala Python, anotá la respuesta y seguí con ella; el procedimiento está en
  `blueprint/10-entorno.md` paso 1.

---

### Paso 2 · Decí lo que cuesta y lo que tarda

**Objetivo.** Quien instala sabe qué va a pagar por mes y qué trámite no depende de este repo,
**antes** de poner una hora acá adentro.

**Hacé esto.** Este paso no corre ningún comando. Mostrá estos números tal cual y esperá que diga
que siguen. Están verificados el **2026-08-13** y su dueño es `blueprint/50-despliegue.md`,
§ «Lo que sale, con fecha»:

- **Railway.** El plan Hobby son USD 5 por mes que **incluyen** USD 5 de uso: debajo pagás 5, arriba
  pagás el uso. Contá el Postgres como un segundo servicio prendido las 24 horas: con base vivís
  alrededor del límite, no muy por debajo.
- **El modelo.** Entre **3 y 5 centavos de dólar por mensaje**, y entre **0.30 y 0.50** una
  conversación de diez idas y vueltas. Con caché de prompt cae a la mitad. Lo que no se ve: el
  thinking adaptativo viene prendido por default y se factura como salida, y el historial crece en
  cada turno, así que el décimo mensaje cuesta más que el primero. Cuál es el modelo lo fija
  `PINES.md`; el desglose por token está en `blueprint/50-despliegue.md`.
- **WhatsApp.** Si el cliente escribió primero y contestás dentro de la ventana de 24 horas —el
  plazo desde el último mensaje del contacto en el que WhatsApp deja contestar texto libre; ver
  `blueprint/00-contrato.md` § 10—, hoy ese mensaje no se cobra. Las plantillas sí, por mensaje
  entregado y por país. Un cerrador que solo contesta casi no paga; el recordatorio de 24 horas
  antes de la cita sí, porque sale fuera de la ventana. **El 1 de octubre de 2026 esto cambia:**
  Meta pasa a cobrar por mensaje de negocio, incluidas las respuestas de servicio y las utility
  adentro de la ventana.
- **Estos números se mueven.** Decilo así, con esas palabras: mirá las páginas de precios antes de
  prometerle un costo a alguien. Un archivo fechado no es una cotización.

**Y esto es lo que de verdad cambia el plan: lo que tarda no es el código.** Desplegar son minutos;
cargar variables y dar de alta el webhook, media hora si las credenciales ya existen. Lo que no
depende de este repo es la **verificación del negocio en Meta: entre uno y cinco días hábiles** con
los papeles en orden, y **hasta treinta** cuando falta algo o el primer intento se rechaza. Sin eso
el número queda en modo de prueba, hablándole solo a los teléfonos que agregues a mano. Las
plantillas se aprueban aparte, normalmente en horas, y se rechazan sin gran explicación.

Por eso este repo no promete «menos de 30 minutos». El repo se despliega en minutos; el negocio se
verifica en días. Son dos relojes distintos y uno no lo maneja nadie de este lado.

**Ofrecé arrancar el trámite ahora, literal:**

> La verificación de Meta tarda días y no depende de este repo, así que conviene arrancarla antes
> de tocar el código: entrás a **developers.facebook.com** con la cuenta del negocio y la dejás
> andando. Mientras tanto seguimos, porque las próximas cinco fases no necesitan una sola
> credencial de WhatsApp.
>
> ¿La arrancás vos ahora, o la dejamos para más adelante?

Anotá la respuesta en `.wca-estado.json` como `meta_verificacion_iniciada`, en verdadero o en falso.
Si la arrancó hoy, la fase 6 la va a encontrar resuelta; si no, la fase 6 es donde se choca contra
la espera, y para entonces conviene que nadie se sorprenda.

**Tenés que ver.** Dos respuestas de quien instala: que los números están vistos, y si arrancó el
trámite de Meta o no. Este paso no cambia un solo archivo del disco.

**Si falla.**

- **«¿Y si no quiero pagar nada todavía?».** Se llega hasta el final de la fase 5 sin gastar en
  Railway ni en WhatsApp. Lo único que se paga desde el arranque es el saldo de la API de Anthropic,
  y una suscripción de Claude no es saldo de API: son dos cosas distintas y se pagan por separado.
  Está escrito en `blueprint/10-entorno.md` paso 6.
- **«Los números no coinciden con lo que dice la página».** Ganan las páginas. Decilo sin discutir,
  usá los de la página y anotá que este archivo quedó viejo.
- **No tiene empresa verificable, o no tiene los papeles.** Entonces `meta` no está disponible
  todavía, y decirlo ahora vale más que descubrirlo en la fase 6. La construcción entera sigue con
  `demo`; `zernio` es la otra puerta y cobra por cuenta conectada en vez de por mensaje. Anotalo.
- **Quiere arrancar el trámite y no sabe por dónde.** El alta se hace en developers.facebook.com con
  la cuenta del negocio, y la verificación la pide el Business Manager. Acá se arranca y nada más:
  el alta de la app, los permisos y cada credencial con su trampa son del tramo 3 de
  `blueprint/20-entrevista.md`, y no se adelantan.
- **Quiere números cerrados para cotizarle a un cliente.** No los hay en este archivo y no los voy a
  inventar: el costo del modelo depende de cuántos chats y de qué largo, y el de WhatsApp cambia el
  1 de octubre de 2026. Lo que sí se puede hacer es medirlo: la fase 5 corre el simulador y ahí se
  ve el gasto real de una conversación completa.

---

### Paso 3 · Elegí el destino

**Objetivo.** Está decidido dónde va a correr el servicio cuando esté listo, y lo decidió quien
instala.

**Hacé esto.** Preguntá, literal, y esperá:

> ¿Dónde va a correr el cerrador cuando esté listo?
>
> 1. **Railway** — el default. USD 5 por mes, con reinicio en fallo y chequeo de salud incluidos.
> 2. **Tu laptop** — sirve para la primera entrega y nada más.
> 3. **Un Mac Mini propio** — si ya está prendido y la base con los chats no puede salir de la
>    oficina.

Los tres en una línea cada uno, para que la respuesta sea informada. **La laptop:** se cierra la
tapa, el proceso se duerme, el túnel se cae y los mensajes de esas horas no llegan. **El Mac Mini:**
gana cuando ya está prendido y cuando el volumen es alto, porque no pagás por uso; pierde sin
dominio propio y sin nadie que lo reinicie un domingo, y el reinicio en fallo y el chequeo de salud
que Railway da por cinco dólares ahí los escribís vos. **Railway:** el default, y por eso no hace
falta defenderlo.

**Y una que no se descubre sola: dos instancias contra la misma base contestan dos veces a la misma
persona.** Si va a probar en la laptop y desplegar en Railway, que apague una.

Esta elección no cambia nada de las fases 1 a 5: se pregunta acá porque cambia qué hay que tener
listo, no qué se construye. El procedimiento del despliegue es de `blueprint/50-despliegue.md`.

**Si eligió Railway**, y sólo entonces, medí el CLI. Es el mismo comando en los tres sistemas:

```bash
railway --version
```

**Tenés que ver.** La elección anotada. Y si fue Railway, una línea con un número de versión. Cuál
sea no importa: **el CLI de Railway no tiene versión fijada en `PINES.md`, y acá no se le inventa
un pin.** Alcanza con que responda.

**Si falla.**

- **`railway: command not found`, o `no se reconoce como un comando`.** El CLI no está instalado, y
  `blueprint/50-despliegue.md` paso 2 corre `railway login`, `railway init` y `railway up` dando por
  sentado que sí: sin esto, la fase 6 se corta en el primer comando. Instalalo desde la página del
  CLI en la documentación de Railway —`docs.railway.com`, sección CLI—, que lista el comando por
  sistema: Homebrew en macOS, npm en cualquiera con Node, y un script para Linux. Después volvé a
  correr `railway --version`. No fijes una versión ni copies un comando de memoria: el instalador
  cambia y la página es la que manda.
- **Contesta, pero con una versión vieja.** Dejala. No hay piso escrito para este CLI en ningún
  archivo del kit, y perseguir un número que nadie fijó es inventarse un requisito. Si más tarde
  `railway up` falla con un mensaje del propio CLI, ahí se actualiza; ese tramo es de
  `blueprint/50-despliegue.md` paso 2.
- **No contesta, y quien instala no quiere instalar nada todavía.** Se puede: el CLI hace falta
  recién en la fase 6. Anotá que falta y seguí, pero anotalo, porque en la fase 6 va a aparecer de
  nuevo y ahí ya no es salteable.
- **No decide.** No elijas vos. Anotá `sin decidir` y seguí: las fases 1 a 5 no dependen de esto, y
  la fase 6 vuelve a preguntar. Un destino elegido por el agente es un destino que quien instala
  descubre cuando ya está pagando.
- **Quiere las dos, probar en la laptop y desplegar en Railway.** Se puede, no al mismo tiempo
  contra la misma base. Repetile la línea de las dos instancias y que decida cuál apaga.

---

### Paso 4 · Elegí el proveedor

**Objetivo.** Queda anotado por dónde van a entrar y salir los mensajes, y arrancás la construcción
sin una sola credencial de WhatsApp.

**Hacé esto.** Preguntá, literal:

> ¿Por dónde entran los mensajes?
>
> 1. **`demo`** — sin credenciales. Es el que te recomiendo para arrancar.
> 2. **`meta`** — WhatsApp Cloud API directo.
> 3. **`zernio`** — la pasarela sobre Meta.

**Y decilo con todas las letras: las fases 1 a 5 corren enteras con `demo`.** La suite y la
compuerta dan verde así, y ninguna fase posterior te va a pedir otro proveedor para seguir. Al
final de la fase 5 vas a estar hablando con tu cerrador en el simulador sin haber tocado una
credencial de WhatsApp. Las credenciales se piden recién en la **fase 6**, con `/conectar`
—`blueprint/20-entrevista.md`, tramo 3, de Q10 a Q12—, que es el tramo que cruza cinco consolas
ajenas y el que conviene dejar para cuando las cuentas estén abiertas.

`demo` tampoco es un transporte falso, y esto importa para que la elección no se lea como una
maqueta: reproduce entregas grabadas desde `pruebas/fixtures/`, con los mismos bytes crudos, la
misma cabecera de firma y el mismo camino de deduplicación, y a la salida recorre el mismo camino
que `meta` y `zernio` —las tres guardas, la clave de idempotencia y el mismo cliente HTTP—. Lo único
distinto es el destino. Ver `blueprint/31-proveedores.md`, pasos 1 y 3.

Lo único que `demo` no ahorra es la clave de Anthropic: el demo se ahorra WhatsApp, no el modelo que
redacta. Esa se carga en la fase 1, en `blueprint/10-entorno.md` paso 6.

**Tenés que ver.** La elección anotada, y nada escrito en disco todavía. En esta fase `.env` no
existe: lo crea la fase 1, y la línea `WHATSAPP_PROVIDER=` la escribe Q10 en el tramo 3. Acá se
anota la intención. Cuando Q10 llegue y encuentre esta respuesta anotada, la muestra y la confirma
en vez de volver a discutirla.

**Si falla.**

- **Ya tiene el número aprobado y las credenciales a mano.** Anotá `meta` como el destino final y
  seguí: para eso preguntaste. La construcción igual corre sobre `demo` hasta la fase 6 —es el mismo
  código— y `meta` se enchufa cuando el servicio esté arriba.
- **Elige `meta` o `zernio` y no tiene las credenciales.** Anotá el que quiere, dejá `demo` como el
  proveedor con el que se construye, y volvé cuando las tenga. No se detiene la construcción por
  esto: es exactamente la pared contra la que se muere una instalación por la mitad.
- **«¿`demo` no es hacer trampa?».** No, y conviene contestarlo bien porque es la pregunta que hace
  abandonar el kit acá. Es el mismo camino de código con otro destino: si el cerrador contesta bien
  en el simulador, contesta bien en WhatsApp; lo que falta después es transporte, no criterio.
- **Quiere que elijas vos.** El transporte lo elige quien va a pagarlo y quien va a administrar la
  cuenta, no yo. Lo que sí se puede decir en dos líneas: con `meta` el número lo administrás vos y
  no hay intermediario; con `zernio` pagás por cuenta conectada y encima seguís pagando las
  plantillas de Meta. La comparación entera está en `blueprint/31-proveedores.md`, que es su dueño.
- **Cambia de proveedor más adelante.** Se puede, y cambia la verificación de firma y el dedupe.
  Después de cambiarlo, `/revisar`.

---

## Qué quedó hecho

Cuatro respuestas y ningún archivo del proyecto tocado:

1. El terreno medido: sistema, Python, Claude Code y si esto es un clon de git. Lo que falte se
   arregla en la fase 1, no acá.
2. El costo dicho con fecha, y el plazo que no depende de este repo —la verificación de Meta— dicho
   antes de que nadie ponga una hora.
3. El destino elegido por quien instala, y el CLI de Railway medido si eligió Railway.
4. El proveedor anotado, con `demo` como el que deja correr las fases 1 a 5 enteras.

Anotalo en `.wca-estado.json`, como pide el contrato de reanudación de `blueprint/00-mapa.md`:

```json
{
  "version": 1,
  "fase": "arranque",
  "archivos": {},
  "arranque": {
    "sistema": "Darwin arm64",
    "python": "3.12.8",
    "claude_code": "2.1.232",
    "es_clon_de_git": true,
    "costo_aceptado": true,
    "meta_verificacion_iniciada": false,
    "destino": "railway",
    "railway_cli": "presente",
    "proveedor": "demo"
  }
}
```

Ésta es la primera fase que escribe el estado, así que el archivo nace con la forma entera:
`version`, `fase`, `archivos` y la clave de la fase. `archivos` va vacío porque esta fase no
escribió ninguno; de acá en adelante cada archivo se anota ahí con su sha256. La entrevista, más
tarde, le suma `respuestas` sin pisar nada de esto.

**Acá todavía no hay ninguna credencial que anotar, y es a propósito.** Cuando las haya, en el
estado va el nombre de la variable y si está puesta; el valor, nunca.

Lo que esta fase **no** hizo, para que nadie lo dé por hecho: no instaló Python, no creó `.venv`, no
escribió `.env`, no tocó `agente/` y no corrió la compuerta. Todo eso empieza ahora.

**Próximo archivo:** `blueprint/10-entorno.md`, que instala el entorno: el intérprete verificado
piso y techo, `.venv` con las dependencias de `PINES.md`, y la clave de Anthropic cargada sin que
el valor pase por una tool call.
