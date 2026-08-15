# 10 · El entorno

Fase 1. Acá no se escribe una sola línea del agente: se verifica que **esta** máquina pueda
construirlo, y se deja el intérprete, las dependencias y la clave en su lugar.

**Por qué no hay `start.sh`.** Un script de arranque es la única pieza que contradice la tesis
del kit. No corre en Windows sin traducción, esconde el motivo del fallo detrás de un `set -e`, y
cuando algo sale mal deja a quien instala mirando una línea roja y ninguna salida. Acá cada paso
dice qué tiene que aparecer en pantalla y qué hacer cuando aparece otra cosa. El comando lo
adaptás vos al sistema; el script no adaptaba nada.

Los seis pasos van en orden. No pases al siguiente sin cumplir **Tenés que ver**.

Dos palabras que vas a leer todo el tiempo de acá en adelante, definidas una sola vez. Las dos
están en `blueprint/00-contrato.md` § 10, junto con el resto del glosario:

- **invariante** — una de las seis reglas de `CLAUDE.md` que ningún archivo del kit puede romper.
  Cada una tiene su chequeo.
- **compuerta** — `scripts/auditar.py`. Veintitrés chequeos, tres veredictos, y nada se publica sin
  `pass`.

**Invariante 6, que se repite acá porque acá se instalan versiones: todas salen de `PINES.md` y
de ningún otro lado.** El rango de Python, las 30 dependencias y el modelo. Si estás por escribir
un número de versión, primero leelo de ahí.

**Invariante 4, que también vive acá: ninguna credencial en el árbol.** El valor lo escribe quien
instala. Nunca pasa por una tool call tuya. Ver el paso 6.

---

### Paso 1 · Detectá el sistema operativo

**Objetivo.** Sabés en qué sistema estás y, con eso, dónde va a vivir el intérprete del entorno
virtual: `bin/` o `Scripts/`. Todo lo que sigue depende de esta respuesta.

**Hacé esto.** Empezá por acá, que funciona en macOS, Linux, WSL y Git Bash:

```bash
uname -s -m && uname -r
```

Si `uname` no existe, estás en PowerShell o en `cmd`. Corré esta otra:

```powershell
"$env:OS $env:PROCESSOR_ARCHITECTURE"
```

**Tenés que ver.** Una de estas cinco, y con eso elegís columna para el resto del archivo:

| Lo que imprime | Sistema | El venv queda en | Cómo lo llamás |
|---|---|---|---|
| `Darwin arm64` o `Darwin x86_64` | macOS | `.venv/bin/` | `.venv/bin/python` |
| `Linux x86_64`, y `uname -r` **sin** `microsoft` | Linux | `.venv/bin/` | `.venv/bin/python` |
| `Linux x86_64`, y `uname -r` **con** `microsoft` | WSL | `.venv/bin/` | `.venv/bin/python` |
| `MINGW64_NT-...`, `MSYS_NT-...` o `CYGWIN_NT-...` | Windows con Git Bash | `.venv/Scripts/` | `.venv/Scripts/python.exe` |
| `Windows_NT AMD64` | Windows con PowerShell o cmd | `.venv\Scripts\` | `.venv\Scripts\python.exe` |

Anotá cuál es. Vas a usar esa fila cuatro veces más.

**Si falla.**

- **`uname: command not found` o `no se reconoce como un comando`.** No es un error: es la
  respuesta. Estás en PowerShell o en `cmd`. Corré la línea de `$env:OS`.
- **Git Bash reportando `MINGW64_NT`.** No lo trates como Linux. El shell es bash, pero el Python
  es el de Windows y el venv se arma con `Scripts/`, no con `bin/`. Es el error más silencioso de
  esta fase: todos los comandos de las guías de Linux "andan" hasta que uno no encuentra el
  intérprete.
- **WSL con el repo en `/mnt/c/...`.** Funciona, pero lento y con permisos que después molestan.
  Decilo en una línea y preguntá si prefiere mover el proyecto adentro del sistema de archivos de
  Linux, en `~`. Si dice que no, seguí igual y anotalo.
- **Imprime algo que no está en la tabla** (`SunOS`, `FreeBSD`, `Android` en Termux). No hay
  instrucción probada para ese sistema y no la voy a inventar. Preguntá, en una línea: «¿Qué
  sistema es y con qué gestor de paquetes instalás Python?». Seguí con la respuesta, anotala en
  `.wca-estado.json`, y en cada paso que siga usá el equivalente que te den.

---

### Paso 2 · Python del rango de `PINES.md`

**Objetivo.** Hay un intérprete entre 3.11 y 3.14, y sabés su **ruta completa**. No alcanza con
que exista: el paso 5 lo va a llamar por ruta.

**Hacé esto.** El rango es `>=3.11,<3.15` y sale de `PINES.md` → Python. Se verifica entero, piso
y techo:

```bash
python3 -c "import sys;v=sys.version_info;print(sys.executable);print('%d.%d.%d' % v[:3], 'sirve' if v[:2] in [(3,11),(3,12),(3,13),(3,14)] else 'NO sirve: PINES.md pide >=3.11,<3.15')"
```

En Windows con PowerShell o cmd, lo mismo con el lanzador:

```powershell
py -3 -c "import sys;v=sys.version_info;print(sys.executable);print('%d.%d.%d' % v[:3], 'sirve' if v[:2] in [(3,11),(3,12),(3,13),(3,14)] else 'NO sirve: PINES.md pide >=3.11,<3.15')"
```

**Tenés que ver.** Dos líneas. La primera es la ruta, la segunda termina en `sirve`:

```
/opt/homebrew/opt/python@3.12/bin/python3.12
3.12.8 sirve
```

Copiá la primera línea. De acá en adelante, donde este archivo diga `python3`, usá esa ruta.

**Si falla.**

- **Dice `NO sirve` con 3.15 o más nuevo.** El techo no es prudencia: `pydantic-core` y `asyncpg`
  publican ruedas hasta `cp314`. Arriba de eso, pip intenta compilar desde fuente y el paso 5 se
  cae con un error de compilador que no nombra a ninguno de los dos. Instalá una del rango; no
  hace falta desinstalar la que tenés.
- **Dice `NO sirve` con 3.10 o anterior.** El piso lo impone `websockets 17.0.1`, y el kit usa
  `asyncio.TaskGroup`, `except*`, `datetime.UTC` y `tomllib`, que no existen antes de 3.11.
- **`python3: command not found`.** No hay Python, o no está en el PATH. Instalalo:

  | Sistema | Comando |
  |---|---|
  | macOS con Homebrew | `brew install python@3.12` |
  | macOS sin Homebrew | Instalador de python.org, elegí 3.12 |
  | Debian / Ubuntu | `sudo apt update && sudo apt install python3.12 python3.12-venv` |
  | Fedora | `sudo dnf install python3.12` |
  | Windows | `winget install Python.Python.3.12` |

  Tres advertencias que valen el renglón. En Debian y Ubuntu, **`python3.12-venv` no es opcional**:
  sin ese paquete el paso 5 se cae con `ensurepip is not available`. Si `apt` contesta
  `E: Unable to locate package python3.12`, esa versión no está en los repos de tu distro; se
  agrega con `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update` y se repite. Y en el
  instalador de Windows hay que marcar **Add python.exe to PATH**, que viene desmarcado.
- **Hay varias versiones instaladas.** Es lo más común en una máquina que ya se usó para algo.
  Listalas antes de elegir:

  ```bash
  which -a python3 python3.11 python3.12 python3.13 python3.14   # macOS, Linux, Git Bash
  pyenv versions                                                  # si hay pyenv
  brew list --versions | grep python                              # si hay Homebrew
  ```

  ```powershell
  py -0p                                                          # Windows: cada intérprete con su ruta
  ```

  Elegí **una** del rango y quedate con su ruta completa. Con pyenv, además, fijala para esta
  carpeta con `pyenv local 3.12.8`, que escribe un `.python-version` y evita que el intérprete
  cambie sin que nadie lo toque. Si hay empate, elegí **3.12**: es la del contenedor
  (`plantillas/infra/Dockerfile` fija `python:3.12-slim`), así tu máquina y el despliegue corren la
  misma. Ese "anda en mi máquina" es el que este kit existe para evitar.
- **La que encontraste es la del sistema** (`/usr/bin/python3` en macOS o en Debian). Sirve si cae
  en el rango, pero preferí otra si hay: el paso 5 la usa solamente para crear el venv, y una
  actualización del sistema operativo puede reemplazarla debajo del venv que ya creaste.

---

### Paso 3 · Claude Code 2.0.0 o más nuevo

**Objetivo.** La versión que está leyendo esto soporta los mecanismos con los que el kit está
armado.

**Hacé esto.**

```bash
claude --version
```

El piso es **2.0.0**, y sale de `.claude-plugin/plugin.json`, clave `engines.claude-code`. No lo
inventes ni lo subas a mano: si algún día cambia, cambia ahí primero.

**Tenés que ver.** El número y el nombre, así:

```
2.1.232 (Claude Code)
```

El tuyo va a ser otro. Lo que se mira es el primer número: tiene que ser 2 o más.

Por qué importa, en concreto. El kit se apoya en cuatro cosas que en una versión vieja no existen:
las skills de proyecto en `.claude/skills/<nombre>/SKILL.md`, el `disable-model-invocation: true`
que llevan los once comandos para que los dispare quien instala y no el modelo, el `allowed-tools`
del frontmatter, y el bloque `` ```! `` que inyecta la salida de un comando en el cuerpo de la
skill junto con `${CLAUDE_PROJECT_DIR}`. Los cuatro los usa `/revisar`. En una versión vieja nada
de eso tira un error: la skill se lee como texto plano y la compuerta no corre. O sea, la
protección desaparece exactamente cuando hacía falta, y en silencio.

**Si falla.**

- **El primer número es menor que 2.** Actualizá y volvé a correr `claude --version`:

  ```bash
  claude update                                   # revisa e instala si hay algo
  claude install stable                           # instalación nativa
  npm install -g @anthropic-ai/claude-code@latest # si se instaló por npm
  ```
- **`claude: command not found`, y sin embargo la sesión está corriendo.** Pasa con la instalación
  nativa fuera del PATH del shell, o cuando Claude Code corre dentro de un IDE. No lo persigas:
  pedile a quien instala que escriba `/status` en la sesión y te dicte el número. Con eso seguís.
- **`claude update` dice que está al día y la versión sigue vieja.** Hay dos instalaciones y gana
  la del PATH. Listalas con `which -a claude` (o `Get-Command -All claude` en PowerShell), sacá la
  vieja o corregí el orden del PATH.
- **`/revisar` pide permiso para cada comando.** La carpeta no está confiada, así que
  `.claude/settings.json` no se aplicó. Salí, volvé a abrir Claude Code en esta carpeta y aceptá.
  `claude doctor` lee los archivos de configuración sin el prompt y sirve para confirmar cuál
  levantó.

---

### Paso 4 · El árbol de trabajo

**Objetivo.** Existen `knowledge/closer/` y `knowledge/negocio/`, y git ignora lo que caiga
adentro salvo el `.gitkeep`.

**Hacé esto.**

```bash
mkdir -p knowledge/closer knowledge/negocio        # macOS, Linux, WSL, Git Bash
```

```powershell
New-Item -ItemType Directory -Force knowledge/closer, knowledge/negocio | Out-Null
```

Y verificá que el `.gitignore` haga lo que dice:

```bash
git check-ignore --no-index -- .env knowledge/closer/notas.pdf knowledge/closer/.gitkeep
```

`--no-index` no es adorno, y es el mismo motivo por el que lo usa `scripts/auditar.py`: sin esa
bandera git contesta «no está ignorado» para cualquier archivo ya rastreado, y el chequeo pasaría
siempre por la razón equivocada. Con la bandera se pregunta por el patrón, no por el estado del
archivo.

**Tenés que ver.** Las dos carpetas creadas, y exactamente dos líneas de salida:

```
.env
knowledge/closer/notas.pdf
```

`.gitkeep` **no** aparece, y eso es lo correcto: el `.gitignore` lo desexcluye a propósito para
que quien clone reciba las dos subcarpetas y no un `knowledge/` vacío.

Qué va en cada una, para cuando la entrevista pregunte: en `closer/` va **cómo se vende** —el
guion, la transcripción de la llamada que cerró, la lista de objeciones—; en `negocio/` va **qué
se vende** —catálogo con precios, condiciones de pago, plazos—. De ahí salen el tono y los
precios, y un precio que no esté en ese material no existe para el agente. El detalle está en
`knowledge/README.md`.

`config/` no se crea en esta fase. La escribe `/playbook` y esa sí se versiona: es lo único del
árbol que redacta quien instala.

**Si falla.**

- **Las carpetas ya existen con archivos adentro.** No toques nada. `mkdir -p` y `New-Item -Force`
  no borran; seguí al paso 5.
- **`Permission denied` o `Acceso denegado`.** El repo está en una ruta donde el usuario no puede
  escribir: `/Applications`, `C:\Program Files`, un volumen montado de sólo lectura. Movelo a la
  carpeta del usuario y volvé al paso 1. **No uses `sudo` para crear carpetas dentro del repo**:
  te deja archivos de root adentro y el paso 5 falla más tarde, peor y por otro motivo.
- **La salida trae más o menos líneas que esas dos.** Si falta `.env`, o si aparece
  `knowledge/closer/.gitkeep`, el `.gitignore` no es el del kit. Pará y decilo; no lo edites acá.
  Ese archivo es lo único que impide que `knowledge/` viaje a git con datos de clientes o con
  material de otro autor adentro.
- **`fatal: not a git repository`.** Bajaste un ZIP en vez de clonar. El ZIP llega sin `.git`, y
  varias verificaciones de este kit —ésta, el chequeo de secretos y el de plantillas ignoradas—
  usan git. Cloná el repositorio y volvé a empezar.
- **El proyecto está en una carpeta sincronizada** (iCloud Drive, OneDrive, Dropbox). El
  sincronizador sube `knowledge/` a la nube aunque git lo ignore, y algunos desalojan archivos y
  dejan un puntero donde había un PDF. Decilo y preguntá si mueve el proyecto afuera.

---

### Paso 5 · Entorno virtual y dependencias

**Objetivo.** Existe `.venv` con las 30 dependencias de `PINES.md`, cada una en su versión exacta.

**Hacé esto.** Cuatro comandos, en este orden.

**1. Creá el entorno con el intérprete del paso 2, por ruta completa.**

```bash
/ruta/al/python3.12 -m venv .venv
```

**Por qué el venv no es opcional, y no alcanza con el `python3` del sistema.** El Python del
sistema no trae `jsonschema` ni `pydantic`. Sin `jsonschema`, el chequeo `contrato-control` de la
compuerta no corre. Y `contrato-control` es uno de los dos que la compuerta exige siempre: no
correr no lo deja pasar, cae en `exigidos_sin_correr`, el veredicto entero baja a `parcial` y la
salida es 3. Medido en una máquina sin venv: `PARCIAL · 0 errores · 0 avisos · 9 salteados`. O
sea, sin `.venv` el kit no puede llegar nunca al `pass` que él mismo pide como condición para
publicar, y no por un error visible: por un salteado, que es la falla más silenciosa que tiene
esto. Los cuatro comandos de este paso son lo que la evita.

La carpeta se llama `.venv`, exactamente. No es gusto: `scripts/auditar.py` busca el intérprete del
proyecto en `.venv/bin/python3`, `.venv/bin/python`, `venv/bin/python3` y `.venv/Scripts/python.exe`,
en ese orden. Con cualquier otro nombre, dos chequeos de la compuerta saltean para siempre con
«falta pydantic» aunque pydantic esté instalado al lado.

**2. Copiá el `requirements.txt` verbatim.**

```bash
cp plantillas/infra/requirements.txt requirements.txt          # macOS, Linux, WSL, Git Bash
```

```powershell
Copy-Item plantillas/infra/requirements.txt requirements.txt
```

Byte por byte, sin tocar una línea. Es una plantilla hasheada en `plantillas/MANIFIESTO.json`, su
destino declarado es la raíz, y el `Dockerfile` la copia de ahí. **Invariante 6: las versiones
salen de `PINES.md`.** Si una hay que cambiarla, se cambia en `PINES.md`, se regenera la plantilla
y se vuelve a correr la compuerta. Editar este archivo a mano rompe el chequeo 01 y, peor, hace que
tu máquina y el contenedor instalen cosas distintas.

**3. Instalá con el Python del venv, por ruta.**

```bash
.venv/bin/python -m pip install -r requirements.txt            # macOS, Linux, WSL
```

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt    # Windows
```

```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt    # Git Bash sobre Windows
```

Por ruta y no con `activate`, a propósito: activar cambia **ese** shell, y el shell del comando
siguiente puede ser otro. La ruta funciona siempre, y es la misma que después busca la compuerta.
Quien instala puede activar el suyo si va a trabajar a mano —`source .venv/bin/activate`,
`.venv\Scripts\Activate.ps1` en PowerShell, `.venv\Scripts\activate.bat` en cmd—, pero eso es para
su terminal, no para vos.

**4. Verificá.**

```bash
.venv/bin/python --version
.venv/bin/python -m pip check
.venv/bin/python -c "from importlib.metadata import version as v;print(v('fastapi'),v('anthropic'),v('httpx'),v('pydantic'),v('asyncpg'),v('greenlet'))"
```

**Tenés que ver.** Cuatro cosas, y las cuatro:

```
Python 3.12.8
...
Successfully installed ... fastapi-0.141.1 ... anthropic-0.121.0 ...
No broken requirements found.
0.141.1 0.121.0 0.28.1 2.13.4 0.31.0 3.5.5
```

Esos seis números son los de `PINES.md`. Si uno no coincide, el entorno no está listo aunque pip
haya dicho que terminó bien.

`asyncpg` y `greenlet` están en la lista por un motivo. `asyncpg` no aparece en ningún `import`
del proyecto: vive adentro de `postgresql+asyncpg://`, y con SQLite esa línea nunca corre, así que
la falta se descubre recién en el primer despliegue con Postgres. `greenlet` lo declara SQLAlchemy
bajo un marcador de plataforma: en una arquitectura que no esté listada no se instala, nadie avisa,
y el async muere en runtime. Los dos se miran acá porque acá todavía es barato.

**Si falla.**

- **`ensurepip is not available`** (Debian, Ubuntu). Falta el paquete de venv de esa minor:
  `sudo apt install python3.12-venv`. Borrá el `.venv` a medio hacer y volvé al comando 1.
- **`error: externally-managed-environment`.** Estás instalando en el Python del sistema, no en el
  venv. La salida propone `--break-system-packages`: no lo uses, hace exactamente lo que dice.
  Significa que el comando no arrancó con `.venv/bin/python`. Revisá la ruta y repetí. Y nunca
  `sudo pip`: te deja paquetes de root que después no podés actualizar.
- **No hay rueda para tu plataforma.** Se ve como `Building wheel for greenlet (pyproject.toml)
  ... error` o `Failed building wheel for ...`, seguido de un error de compilador. Pip no encontró
  binario para tu combinación de Python, sistema y arquitectura, e intentó compilar. Dos caminos, y
  el primero es el que hay que probar antes:

  ```bash
  .venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
  ```

  Con esa bandera falla al instante y el error nombra el paquete, en vez de compilar diez minutos
  para fallar igual. Si el paquete que nombra es uno de los compilados, rehacé el venv con **3.12**:
  es la de cobertura de ruedas más ancha y la del contenedor. Si aun así hace falta compilar:
  `xcode-select --install` en macOS, `sudo apt install build-essential python3.12-dev` en Debian,
  Build Tools for Visual Studio en Windows.
- **Detrás de un proxy.** Se ve como `ProxyError`, `Connection to pypi.org timed out` o
  `Read timed out`. Poné el proxy y repetí:

  ```bash
  export HTTPS_PROXY=http://host:puerto && export HTTP_PROXY=http://host:puerto
  ```

  ```powershell
  $env:HTTPS_PROXY="http://host:puerto"
  ```

  También se le pasa a pip directo con `--proxy http://host:puerto`, y si la empresa tiene espejo
  interno, con `--index-url https://.../simple`. Si la red corta seguido, `--retries 10 --timeout 60`.
- **`SSLCertVerificationError: unable to get local issuer certificate`.** Hay un proxy que abre el
  TLS en el medio y firma con un certificado de la empresa. Se arregla con el certificado, no
  apagando la verificación: `--cert /ruta/ca-de-la-empresa.pem`, o la variable `PIP_CERT`. Existe
  `--trusted-host pypi.org` y hace que ande; también hace que bajes 30 dependencias por una conexión
  que no podés verificar. Decí las dos cosas y dejá que elija quien instala.
- **Claude Code te pide permiso para el comando de pip.** Es esperable, no es un fallo. El allowlist
  de `.claude/settings.json` cubre `python3 -m pip install -r requirements.txt`, y este comando
  arranca con la ruta del venv, que no es esa cadena. Se acepta una vez.
- **`pip check` lista un conflicto.** No lo arregles instalando otra versión a mano: eso rompe el
  invariante 6 y el chequeo 03 lo va a encontrar igual. Casi siempre es un `.venv` de una corrida
  anterior con otra cosa adentro. Borralo entero y rehacé los cuatro comandos.

---

### Paso 6 · La clave de Anthropic

**Objetivo.** Existe `.env`, git lo ignora, y `ANTHROPIC_API_KEY` está cargada sin que el valor
haya pasado nunca por una tool call.

**Hacé esto.**

**1. Creá el `.env` desde el ejemplo.**

```bash
cp env.example .env            # macOS, Linux, WSL, Git Bash
```

```powershell
Copy-Item env.example .env
```

`env.example` trae los nombres, de dónde se saca cada valor y ninguna credencial. Eso no cambia:
ahí no se escribe un valor nunca, y el chequeo 06 de la compuerta lo verifica.

**2. El valor lo escribe quien instala. Vos no.** Hay dos formas y las dos sirven:

- **Pegarla en el editor.** Abrir `.env`, buscar `ANTHROPIC_API_KEY=` y pegar la clave detrás del
  `=`. Es la que conviene: el valor no pasa por ningún lado más que por el archivo.
- **Escribirla en el prompt con el prefijo `! `**, que corre la línea en bash sin que vos generes
  una tool call:

  ```
  ! printf 'ANTHROPIC_API_KEY=%s\n' 'sk-ant-...' >> .env
  ```

Lo que no se hace, en ningún caso: que te dicten la clave para que la escribas vos con `Write` o
con `Bash`. **Una tool call queda en el transcripto, y el transcripto se guarda.** Ése es el
invariante 4 en la práctica, no en abstracto.

De dónde sale: console.anthropic.com → Settings → API keys → Create Key. Se muestra **una sola
vez**, al crearla. Si se pierde no se recupera: se revoca esa y se hace otra.

Y decilo, porque confunde a casi todo el mundo: esta clave es para **el agente que vas a
construir**, no para la sesión de Claude Code. Si quien instala entró con una suscripción, el
agente igual necesita su propia clave, porque quien llama a la API después es el servidor del
agente y no el editor. Hace falta siempre, también con `WHATSAPP_PROVIDER=demo`: el demo se ahorra
las credenciales de WhatsApp, no el modelo que redacta.

Las credenciales del proveedor —Meta o Zernio—, las de Google Calendar, las del CRM y las de Slack
**no van acá**. Las pide `/conectar` en `blueprint/20-entrevista.md`, tramo 3, de Q10 a Q12, y cada
una tiene su trampa escrita en `env.example`. Ese tramo cruza cinco consolas ajenas y es el que
conviene dejar para cuando tengas las cuentas abiertas; `/configurar` —Q5 a Q9— no pide ninguna.

**3. Verificá sin imprimir el valor.**

```bash
git check-ignore --no-index -- .env
.venv/bin/python -c "from dotenv import dotenv_values;k=dotenv_values('.env').get('ANTHROPIC_API_KEY') or '';print('ANTHROPIC_API_KEY:','vacia' if not k else '%d caracteres, empieza con sk-ant-: %s' % (len(k), k.startswith('sk-ant-')))"
```

Nunca `cat .env`, nunca `Get-Content .env`, nunca abrirlo con Read. `.claude/settings.json` ya te
niega el Read; el resto depende de vos.

**Tenés que ver.**

```
.env
ANTHROPIC_API_KEY: 108 caracteres, empieza con sk-ant-: True
```

La primera línea confirma que git lo ignora. En la segunda, el número va a ser otro; lo que
importa es que no diga `vacia` y que el `True` esté.

**Si falla.**

- **Dice `vacia`.** El archivo no tiene la línea, o quedó `ANTHROPIC_API_KEY=` sin nada detrás.
  Pedila de nuevo, con cualquiera de las dos formas del punto 2. No la dictes vos.
- **Dice `empieza con sk-ant-: False`.** Se pegó otra cosa: una clave de OpenAI (`sk-...` a secas,
  la de `OPENAI_API_KEY`, que en este archivo va en otra línea) o un token de Meta (`EAA...`).
  Mirá qué variable estás llenando.
- **El número de caracteres es mucho más chico de lo que se pegó.** Se cortó, casi siempre por un
  salto de línea en el medio. La clave va en una sola línea, sin espacios alrededor del `=`.
- **`.env` no aparece en la salida de `check-ignore`.** Pará acá. El `.gitignore` no es el del kit,
  y la próxima credencial que se escriba entra al próximo commit. No se sigue construyendo con eso
  roto.
- **La clave se pegó en el chat por error.** No hay forma de sacarla del transcripto. Revocala en
  console.anthropic.com → API keys, creá otra y repetí este paso. Decilo aunque incomode: una clave
  filtrada que nadie revocó es mucho peor que diez minutos perdidos.
- **Sin saldo.** Esta fase no llama a la API —la primera llamada real la hace `/probar`—, pero el
  error se prepara acá, así que va escrito acá. Cuando la cuenta no tiene crédito, la respuesta es
  ésta, literal:

  ```json
  {"type":"error","error":{"type":"invalid_request_error","message":"Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits."}}
  ```

  Es un **400**, no un 402 ni un 429. Quiere decir que la petición está bien formada y la cuenta no
  tiene con qué pagarla: reintentar no cambia nada, y `tenacity` no la va a salvar porque no es un
  error transitorio. Se arregla en console.anthropic.com → Plans & Billing, comprando créditos. Una
  suscripción de Claude no es saldo de API: son dos cosas distintas y se pagan por separado.
- **401 con `authentication_error` y `invalid x-api-key`.** La clave está mal escrita o fue
  revocada. Volvé al punto 2.
- **`ANTHROPIC_API_KEY` exportada en el perfil del shell.** No lo hagas y no lo sugieras. El agente
  la lee de `.env`. Una variable global puede cambiar con qué credencial corre la propia sesión de
  Claude Code de quien instala, y eso se descubre a fin de mes.

---

## Qué quedó verificado

Seis cosas, y ninguna de memoria:

1. El sistema operativo, y con él la forma de todo lo que sigue: `bin/` o `Scripts/`.
2. Un Python del rango `>=3.11,<3.15` de `PINES.md`, con su ruta completa anotada.
3. Claude Code 2.0.0 o más nuevo, el piso que declara `.claude-plugin/plugin.json`.
4. `knowledge/closer/` y `knowledge/negocio/` creadas, y git ignorando lo que caiga adentro.
5. `.venv` con las 30 dependencias fijadas, verificadas contra `PINES.md` una por una.
6. `.env` creado, ignorado por git, con la clave de Anthropic cargada y sin haber pasado por una
   tool call.

Anotalo en `.wca-estado.json` antes de seguir, como pide el contrato de reanudación de
`blueprint/00-mapa.md`: `fase` en `entorno`, y una clave `entorno` con el sistema, la ruta del
intérprete, su versión y la versión de Claude Code. Esto suma, no pisa: la clave `arranque` que
dejó la fase 0 queda como está. **Ningún valor de credencial va ahí**: va el nombre de la variable
y si está puesta.

Opcional, y sale barato: corré la compuerta ahora. Con el Python del venv, que es la única forma
que este kit escribe —el del sistema no trae `jsonschema`, y con eso la compuerta no puede pasar de
`parcial`, como dice el paso 5—:

```bash
.venv/bin/python scripts/auditar.py            # macOS, Linux, WSL
```

```powershell
.venv\Scripts\python.exe scripts\auditar.py    # Windows con PowerShell o cmd
```

```bash
.venv/Scripts/python.exe scripts/auditar.py    # Git Bash sobre Windows
```

**Tenés que ver un `pass`, y no significa lo que parece.** Es `pass` con varios chequeos en
`salteado`, porque en la fase 1 `agente/` todavía no existe y la mitad del registro mira ahí
adentro. Lo que sí corre es todo lo que no depende del build: `01 blueprint-existe`,
`02 manifiesto` —que verifica cada plantilla contra su sha256, incluido el `requirements.txt` que
acabás de copiar—, `04 claudemd-tam`, `05 pines`, `08 secretos`, `09 gitignore-anclado` y
`17 contrato-control`. Los números y los nombres son los que imprime la propia salida del
comando; usá ésos y no los de memoria.

`17 contrato-control` es la razón de correr esto con el venv y no con el `python3` del sistema: es
el único chequeo que la compuerta exige siempre, y con el intérprete del sistema saltea por falta
de `jsonschema` y arrastra el veredicto entero a `parcial`. Si lo ves `salteado`, repetí el
comando con la ruta del venv.

Un salteado no es un aprobado, y este `pass` no es el verde final: ése lo da
`blueprint/90-auditoria.md`, después de la fase 5, y ahí no queda ninguno de estos salteados.

Si Claude Code te pide permiso por este comando, es esperable la primera vez. La entrada
`Bash(.venv/bin/python scripts/auditar.py:*)` tiene que estar en `allow`, dentro de
`.claude/settings.json` —ver `blueprint/00-contrato.md` § 5—. Si no está, se acepta a mano una vez
y se anota.

**Próximo archivo:** `blueprint/20-entrevista.md`. Once preguntas repartidas en tres tramos, con
tres comandos distintos: las tres primeras se contestan de memoria y ya dejan un cerrador con el
que se puede hablar. Son once de doce: la que falta es Q4 —cómo cerrás—, que tiene archivo propio,
`blueprint/25-playbook.md`.
