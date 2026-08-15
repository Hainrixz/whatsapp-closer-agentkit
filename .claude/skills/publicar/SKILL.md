---
name: publicar
description: Despliega local o en Railway y da de alta el webhook contra el proveedor que elegiste.
disable-model-invocation: true
---

# Publicar

Leé `blueprint/50-despliegue.md` y seguilo.

Antes de arrancar hay dos condiciones, y son distintas: una mira el disco y la otra mira lo que
git entrega.

## 1 · La compuerta en `pass`

Corré `/revisar`. Se despliega con `pass` y con nada más.

`fail` es obvio. `parcial` no: el reporte no encontró nada, y eso es distinto de que no haya
nada. Quiere decir que un chequeo que en este árbol tenía que correr no corrió —falta
`jsonschema`, falta el `.venv`, falta una dependencia— y el que saltea siempre incluye
`contrato-control`, que es el control negativo de la validación entera. Con ese salteado, un
reporte en verde no distingue "validé y está bien" de "no validé nada". Corré la compuerta con
el `.venv` del proyecto, mirá el motivo que imprime cada salteado y volvé cuando diga `pass`.

## 2 · El índice de git trae el árbol entero

`pass` dice que el árbol del disco está completo. No dice nada de lo que viaja. Las dos cuentas:

```bash
git ls-files | wc -l                              # lo que entrega un git clone
git ls-files --others --exclude-standard | wc -l  # lo que está en el disco y no viaja
```

Corridas sobre el árbol donde se escribió esta skill, el 2026-08-14, dieron esto:

```
       9
      73
```

Nueve archivos versionados y setenta y tres afuera del índice: `blueprint/` entero, las diez
skills de `.claude/` y su `settings.json`, los tres de `scripts/` —la compuerta incluida—,
`plantillas/` con el núcleo verbatim, `pruebas/`, `PINES.md`. Un clon de eso no puede construir
nada, y la compuerta corrida sobre el disco da `pass` igual, porque el disco sí está completo. Las
dos cosas son ciertas a la vez, y por eso hay que preguntar las dos.

Estas dos cuentas miran el árbol entero. La compuerta mide lo mismo con otra vara, sólo sobre el
núcleo: 52 archivos, 3 rastreados. Es el mismo agujero.

**La condición es que la segunda cuenta dé cero.** Todo lo que no está ignorado a propósito está
en el índice. Lo ignorado a propósito tiene su motivo escrito al lado en `.gitignore`: `.env` y
las claves, lo que escribe la construcción —`/agente/`, `/panel/`, el `Dockerfile`, el
`railway.json`—, `/knowledge/` y `/config/playbook-base.yaml`. Nada más.

**Cuando no da cero, no se publica.** En este orden:

1. **Mostrá la lista entera, sin recortar.** Es exactamente lo que le falta al clon.

   ```bash
   git ls-files --others --exclude-standard
   ```

2. **Mirá que no haya un secreto adentro del índice.**

   ```bash
   git ls-files | grep -E '(^|/)\.env|\.pem$|service-account'
   ```

   Si esto imprime algo, se para todo acá y no se publica nada. Hay una credencial versionada, y
   eso no se arregla con un commit más: hay que sacarla del historial y rotar la clave. Es el
   invariante 4, y es el único caso de esta sección donde el arreglo no es agregar archivos.
   Sin salida, seguí.

3. **Proponé el arreglo y esperá el sí.** Ni `git add` ni `git commit` salen sin que quien
   publica los confirme.

   ```bash
   git add -A
   git status --short
   ```

   El `status` va entre el `add` y el commit a propósito: es la última vez que se puede mirar qué
   quedó adentro. Si aparece algo que no esperabas —material que subiste a `knowledge/`, un
   volcado de la base, una carpeta de otro autor—, el arreglo es `.gitignore` y `git restore
   --staged`, no el commit.

4. **Commiteá y volvé a contar.** Con la segunda cuenta en cero, seguí con el despliegue.

**Lo tocado y sin commitear no frena nada, y se dice igual.** `git status --porcelain` con líneas
`M` no impide desplegar —`railway up` sube el directorio, no el commit— pero deja el clon distinto
del árbol que auditaste. Decí cuántos archivos son y dejá que decida quien publica.

**Si el árbol no es un repo de git**, esto no se puede verificar. Decilo con esas palabras y
seguí: el despliegue anda igual, y lo que no hay es de dónde volver a sacar el kit.

**La compuerta ya lo ve, y no lo frena.** Sale adentro del chequeo 09, que queda en `[ok]` con un
aviso al lado:

```
  [ok      ] 09 gitignore-anclado  52 archivos del núcleo: 3 rastreados, 49 sin rastrear · 6 carpeta(s) y ruta(s)
      [aviso] gitignore/nucleo_sin_rastrear .gitignore:0   49 de 52 archivos del núcleo verbatim
      están **sin rastrear**: git no los tiene en el índice, así que hoy no salen en ningún clon.
```

Veredicto `PASS`, salida 0. Un aviso no frena la compuerta: la frena esta sección. Si en tu kit
ese hallazgo ya sale como error, mejor —`/revisar` te para antes y acá no hay nada que hacer—.
Mientras salga como aviso, `pass` no dice nada del índice.

## Después

Preguntá dónde: local o Railway. En Railway la base es Postgres, y `asyncpg` tiene que estar
fijado en `PINES.md`. Con SQLite anda perfecto y no se nota, así que esto revienta recién en el
primer despliegue, con un `ModuleNotFoundError` que no nombra a nadie.

Después, el alta del webhook. Con `meta`, la verificación es un GET que responde el
`hub.challenge` como texto plano, nunca como JSON. Con `zernio`, el handler contesta 2xx en
menos de 5 segundos o el evento vuelve, hasta siete veces.

Ninguna credencial se escribe desde acá. Los valores los pone quien instala, en `.env`.
