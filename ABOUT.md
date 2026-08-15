# El About de GitHub

Este archivo **no se aplica solo**. Es el texto para que lo copie quien publique el repo.

**Nadie corrió ninguno de los comandos de abajo.** Están escritos para copiar y pegar, y quedan
para vos. Revisá cada uno antes de darle enter: todos tocan la configuración del repo en
GitHub.

Repo: `Hainrixz/whatsapp-closer-agentkit` · rama por defecto en GitHub: `main`

---

## 0 · El orden, y qué rompe si se hace en otro

Los comandos de §1, §2 y §3 dan por sentado un repo público, con push, y con Pages prendido. Hoy
no se cumple ninguna de las tres. Esto es lo que se midió el 2026-08-14, con lectura y sin
escritura:

```console
$ gh repo view Hainrixz/whatsapp-closer-agentkit --json visibility,pushedAt,description,homepageUrl,repositoryTopics
{"description":"Agente que atiende cada chat entrante de WhatsApp con perfil de setter y closer: califica, responde objeciones, agenda y deja todo escrito en el CRM.","homepageUrl":"","pushedAt":"2026-08-04T03:57:28Z","repositoryTopics":null,"visibility":"PRIVATE"}

$ gh api repos/Hainrixz/whatsapp-closer-agentkit/pages
gh: Not Found (HTTP 404)

$ git ls-tree --name-only origin/main
.claude-plugin
CITAS.md
CLAUDE.md
README.md
agents
contratos
env.example
pruebas

$ git branch -avv
  main                9993441 [origin/main] whatsapp-closer-agent 0.1.0
* v1-closer           9993441 whatsapp-closer-agent 0.1.0
  remotes/origin/HEAD -> origin/main
  remotes/origin/main 9993441 whatsapp-closer-agent 0.1.0
```

Leelo así: en GitHub está el árbol de la versión 0.1.0, ocho entradas. **No están `blueprint/`,
`scripts/`, `plantillas/`, `docs/`, `LICENSE` ni este archivo.** Y la rama local es `v1-closer`,
que todavía no se empujó a ningún lado.

El orden son seis pasos y cada uno habilita al siguiente:

| # | Paso | Sin el anterior |
|---|---|---|
| 1 | `git add` y commit | no hay qué empujar |
| 2 | push a `main` | `main` sigue siendo 0.1.0: sin `docs/`, sin `LICENSE`, sin blueprint |
| 3 | visibilidad a público | Pages desde un repo privado depende del plan de la cuenta |
| 4 | topics y descripción (§1 y §2) | se aplican igual en privado, pero no los ve ni los indexa nadie |
| 5 | Pages desde `docs/` (§3) | apuntado a un `/docs` que no está en la rama, el sitio no tiene qué servir |
| 6 | homepage (§3) | la URL que ponés en el About devuelve 404 |

### Paso 1 · Commiteá

Todo el kit está sin commitear. `git status --short` hoy imprime más de veinte líneas.

```bash
git add -A
git commit -m "kit v1.0.0"
```

**Tenés que ver.** `git status --short` sin salida, y el árbol nuevo con las carpetas que
importan:

```bash
git status --short
git ls-tree --name-only HEAD
```

`blueprint`, `docs`, `plantillas`, `scripts`, `LICENSE` y `ABOUT.md` tienen que estar en esa
lista. Si falta alguna, la está tapando `.gitignore`; comprobalo con
`git check-ignore -v docs/index.html`.

### Paso 2 · Empujá

La rama local es `v1-closer` y la de GitHub es `main`. Son la misma altura hoy —las dos en
`9993441`—, así que esto no es un merge, es un push:

```bash
git push origin v1-closer:main
```

**Tenés que ver.** El sha de GitHub igual al tuyo, y `docs/index.html` alcanzable por la API:

```bash
git rev-parse HEAD
gh api repos/Hainrixz/whatsapp-closer-agentkit/commits/main --jq .sha
gh api repos/Hainrixz/whatsapp-closer-agentkit/contents/docs/index.html --jq .size
```

Los dos primeros imprimen la misma línea. El tercero imprime un número, no un 404.

### Paso 3 · Pasalo a público

```bash
gh repo edit Hainrixz/whatsapp-closer-agentkit \
  --visibility public \
  --accept-visibility-change-consequences
```

Esa segunda bandera no es opcional: `gh` 2.97.0 rechaza `--visibility` sin ella.

**Por qué va antes de Pages.** Un repo privado sirve Pages sólo con plan pago. **No pude
verificar el plan de esta cuenta**: el token de `gh` no tiene el scope `user`, así que
`gh api user` vuelve sin la clave `plan`. Con el repo público la pregunta no se hace.

**Tenés que ver.**

```bash
gh repo view Hainrixz/whatsapp-closer-agentkit --json visibility
```

```json
{"visibility":"PUBLIC"}
```

### Paso 4 · Descripción y topics

Los dos comandos están en §1 y §2. Correlos ahora.

**Tenés que ver.**

```bash
gh repo view Hainrixz/whatsapp-closer-agentkit --json description,repositoryTopics
```

`description` tiene que ser la de §1 —hoy todavía es la vieja, la que habla del agente y no del
kit— y `repositoryTopics` tiene que traer veinte nombres, no `null`.

### Paso 5 · Prendé Pages

El comando está en §3. Va acá y no antes por un motivo que se puede leer arriba: el `main` de
GitHub no tiene `docs/`. Pages apuntado a un `/docs` que no está en la rama no tiene qué servir.
Después del paso 2 sí lo tiene.

**Tenés que ver.**

```bash
gh api repos/Hainrixz/whatsapp-closer-agentkit/pages \
  --jq '[.status, .html_url, .source.branch, .source.path] | @tsv'
```

`source.branch` en `main`, `source.path` en `/docs`, y `html_url` en
`https://hainrixz.github.io/whatsapp-closer-agentkit/`. El `status` arranca en `null` o
`building` y pasa a `built` en un minuto o dos. Repetí el comando hasta que diga `built`.

### Paso 6 · Poné la homepage

El comando está en §3, el del `--homepage`. Va último porque escribe en el About una URL que
recién ahora existe.

**Tenés que ver.**

```bash
gh repo view Hainrixz/whatsapp-closer-agentkit --json homepageUrl
curl -sI https://hainrixz.github.io/whatsapp-closer-agentkit/ | head -1
```

El primero devuelve la URL de Pages. El segundo, `HTTP/2 200`. Si devuelve 404, Pages todavía
está en `building`: volvé al paso 5.

---

## 1 · La descripción

GitHub corta el About en 350 caracteres. Esta tiene **320**, contados con:

```bash
printf '%s' "$(sed -n '/^> /s/^> //p' ABOUT.md | head -1)" | wc -m
```

> Repo blueprint para Claude Code: no trae la app, trae las instrucciones para construirla en tu máquina paso a paso. Un agente que atiende cada chat de WhatsApp como setter y closer: califica, responde la objeción, agenda y escribe el CRM. 16 archivos por fase, 30 versiones fijadas, compuerta de 23 chequeos. En español.

El comando que la aplica:

```bash
gh repo edit Hainrixz/whatsapp-closer-agentkit \
  --description "Repo blueprint para Claude Code: no trae la app, trae las instrucciones para construirla en tu máquina paso a paso. Un agente que atiende cada chat de WhatsApp como setter y closer: califica, responde la objeción, agenda y escribe el CRM. 16 archivos por fase, 30 versiones fijadas, compuerta de 23 chequeos. En español."
```

---

## 2 · Los topics

Veinte, que es el máximo que acepta GitHub. Todos en minúscula y con guiones. Están elegidos por
lo que buscaría alguien que quiere esto, y cada uno es cierto sobre el repo: si mañana el kit deja
de usar Whisper, ese topic se cae.

| Topic | Por qué |
|---|---|
| `whatsapp` | el canal, y la palabra que más se busca |
| `whatsapp-cloud-api` | uno de los dos proveedores reales |
| `meta-cloud-api` | el mismo, con el nombre que usa Meta |
| `whatsapp-bot` | lo que la gente escribe cuando busca esto |
| `claude-code` | el blueprint lo ejecuta Claude Code, con once comandos |
| `anthropic` | el modelo que redacta y el que lee las imágenes |
| `agent` | la forma del producto |
| `ai-agent` | el término con el que se busca esa forma |
| `blueprint` | la clase de repo: instrucciones, no aplicación |
| `sales` | el perfil del agente |
| `sales-automation` | lo que resuelve |
| `lead-qualification` | el paso 2, con score de 0 a 100 |
| `crm` | el paso 5 |
| `chatbot` | la categoría en la que lo busca quien no conoce la palabra agente |
| `fastapi` | el servidor que se construye |
| `python` | el lenguaje |
| `railway` | el destino de despliegue por defecto |
| `google-calendar` | el paso 4 |
| `whisper` | los audios entrantes |
| `spanish` | el kit entero está en español |

El comando que los aplica, los veinte de una:

```bash
gh repo edit Hainrixz/whatsapp-closer-agentkit \
  --add-topic whatsapp \
  --add-topic whatsapp-cloud-api \
  --add-topic meta-cloud-api \
  --add-topic whatsapp-bot \
  --add-topic claude-code \
  --add-topic anthropic \
  --add-topic agent \
  --add-topic ai-agent \
  --add-topic blueprint \
  --add-topic sales \
  --add-topic sales-automation \
  --add-topic lead-qualification \
  --add-topic crm \
  --add-topic chatbot \
  --add-topic fastapi \
  --add-topic python \
  --add-topic railway \
  --add-topic google-calendar \
  --add-topic whisper \
  --add-topic spanish
```

---

## 3 · La URL del sitio

Va la de GitHub Pages, servida desde `docs/` de la rama por defecto:

```
https://hainrixz.github.io/whatsapp-closer-agentkit/
```

El comando que la pone en el About:

```bash
gh repo edit Hainrixz/whatsapp-closer-agentkit \
  --homepage "https://hainrixz.github.io/whatsapp-closer-agentkit/"
```

Esa URL no existe hasta que Pages esté prendido y apuntando a `docs/`. Si todavía no lo está,
esto lo prende. Corré esto **después** del push del paso 2 —sin `docs/` en la rama no hay qué
servir— y **antes** que el `--homepage` de arriba:

```bash
gh api --method POST repos/Hainrixz/whatsapp-closer-agentkit/pages \
  -f 'source[branch]=main' \
  -f 'source[path]=/docs'
```

Dos cosas de ese comando. Si `main` no es la rama donde va a vivir `docs/`, cambiá ese valor por
la que sea. Y si Pages ya está prendido, devuelve `409 Conflict` en vez de fallar raro: en ese
caso el que corresponde es el de cambiar la fuente, con `PUT` en vez de `POST`.

```bash
gh api --method PUT repos/Hainrixz/whatsapp-closer-agentkit/pages \
  -f 'source[branch]=main' \
  -f 'source[path]=/docs'
```

---

## Cómo se comprueba que quedó

Cada paso tiene su chequeo en §0. Éste es el de cierre, los seis campos juntos:

```bash
gh repo view Hainrixz/whatsapp-closer-agentkit \
  --json visibility,description,homepageUrl,repositoryTopics \
  --jq '[.visibility, (.repositoryTopics|length), .homepageUrl] | @tsv'
gh api repos/Hainrixz/whatsapp-closer-agentkit/pages --jq .status
curl -sI https://hainrixz.github.io/whatsapp-closer-agentkit/ | head -1
```

Tiene que salir `PUBLIC`, `20`, la URL de Pages; después `built`; después `HTTP/2 200`. Y la
descripción, entera, con `gh repo view … --json description`: es la única de las cuatro que no
se comprueba de un vistazo.
