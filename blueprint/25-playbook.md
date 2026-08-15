# 25 · El playbook de cierre

Escribe `config/playbook.yaml`: objeciones con su respuesta, y tono. Es campo obligatorio de la
entrada. Acá entra `/armar-cerrador` después de Q3, y `/playbook` sola para cambiarlo después.

También copia `plantillas/config/playbook-base.yaml` a `config/playbook-base.yaml`. **La copia la
hace el paso 1**, una sola vez y antes de que se elija la letra: existe por A, por B y por C. Es la
única plantilla hasheada que sale de esta fase, y el paso 1 de `blueprint/30-generacion.md` la
verifica byte por byte junto con las otras seis, elijas el camino que elijas. Por eso, cuando algún
paso manda leer el base, la plantilla y la copia son el mismo byte y da igual cuál abras. Editar,
ninguna de las dos: lo que se edita es `config/playbook.yaml`.

Para los tres caminos: ninguna respuesta lleva precio, plazo ni promesa —eso es el catálogo, Q5—;
una objeción que no está acá el agente la nombra y la deja para el humano; y **el playbook va con
el tratamiento de Q3** (`tú`, `vos` o `usted`). Vos leés voseo, el cliente no.

**El piso es el mismo por A, por B y por C.** Dos objeciones del base no son contenido opcional:
«¿Me hacés un descuento?» y «¿Y si no me funciona? / ¿Tienen garantía?». Son la regla de no
inventar escrita como copy: en vez de negar, derivan a una persona con un horario. El camino A las
trae, porque muestra las ocho. Por B y por C se **completan** desde el base cuando el material o la
entrevista no las cubrieron: el paso 5 por el camino B, el paso 6 por el C. Se muestran aparte,
marcadas, con el por qué en una línea, y se espera el "va" por esas dos. Rellenar en silencio no es
completar. **Y si dice que no las quiere, salen**: se sacan y se le dice qué pasa entonces —el
agente nombra esa objeción y te la deja a vos, sin contestarla—. El simulador de la fase 5 trae al
que pide descuento prearmado —`3 descuento` en `.venv/bin/python -m pruebas.simulador`—, y un
playbook sin el piso llega ahí sin nada que contestarle.

**Cuál es cuál se anota, no se adivina.** `config/playbook.yaml` lleva un bloque `piso:` con dos
claves fijas, `descuento` y `garantia`, y cada una apunta a la objeción que quedó escrita. Las dos
se pueden reescribir con las palabras del usuario —por B y por C eso es el punto— y la clave sigue
siendo la misma: «¿Me podés hacer un precio mejor?» es `descuento` aunque no diga la palabra. Lo
escribe el paso 7; el paso 9 cuenta las dos claves y mira que cada una apunte a una objeción que
hable de eso, porque dos anclas puestas de cualquier manera dan la misma cuenta que el piso entero.

**Por dónde entrás.** No siempre por el paso 1.

| Venís de | Empezá por |
|---|---|
| `/armar-cerrador` o `blueprint/20-entrevista.md` | paso 1 |
| `/playbook`, y `config/playbook.yaml` no existe | paso 1 |
| `/playbook`, y existe con huecos abiertos | **paso 8**, que los llena. Q4 no se vuelve a preguntar |
| `/playbook`, y existe y cambia una objeción o el tono —las que trajo `/bandeja resumen`, por ejemplo— | paso 7, con la lista entera en pantalla |
| `/playbook`, y lo rehace entero desde otro camino | paso 1, diciendo antes que el archivo actual se reemplaza |

Con `config/playbook.yaml` en disco, mirá qué quedó abierto antes de preguntar nada, y decilo:

```bash
grep -nE "\{[a-z_0-9]+\}" config/playbook.yaml
```

### Paso 1 · Preguntá Q4 y elegí el camino

**Objetivo.** El base del kit está en disco, hay un camino elegido, y el usuario sabe lo que le
cuesta.

**Hacé esto.** Primero copiá el base, y va en los tres caminos: es una plantilla hasheada en
`plantillas/MANIFIESTO.json`, su destino declarado es `config/playbook-base.yaml`, y el paso 1 de
`blueprint/30-generacion.md` lo compara byte por byte contra la plantilla elijas la letra que
elijas. No se escribe de memoria: una copia por bash es exacta byte a byte, y un Read seguido de un
Write es una paráfrasis.

```bash
mkdir -p config
cp plantillas/config/playbook-base.yaml config/playbook-base.yaml
```

En PowerShell, `New-Item -ItemType Directory -Force config` y
`Copy-Item plantillas/config/playbook-base.yaml config/playbook-base.yaml`.

**Esa copia no se edita nunca.** Una línea cambiada ahí sale como `error del build` en la fase 3.
Lo que se edita es `config/playbook.yaml`, y lo escribe el paso 7.

Después preguntá, literal:

> Q4. Me falta tu forma de cerrar, para que conteste como vos. Tres maneras de dármela:
> **A · base** — uso el playbook base que traigo, con ocho objeciones; lo leés y lo aprobás. Un
> minuto.
> **B · subo** — dejás tu PDF, tu curso o una llamada transcrita en `knowledge/closer/`. Cuatro.
> **C · no-tengo** — te hago seis preguntas. Diez minutos, y es el que mejor sale.

Esperá la letra. No elijas por él.

**Tenés que ver.** `config/playbook-base.yaml` en disco, y `A`, `B` o `C` anotado en
`.wca-estado.json` bajo `playbook.camino`.

**Si falla.** `cp: no such file`: estás fuera de la raíz, verificá con `pwd`. Contesta "el que sea
mejor": decí `C`, sale de sus palabras y no de un molde. Elige `B` con la carpeta vacía: eso es el
paso 3.

### Paso 2 · Camino A · leé el base, transponelo y esperá el "va"

**Objetivo.** El usuario leyó las ocho objeciones que va a contestar su agente, y dijo que sí.

**Hacé esto.** Abrí con Read `config/playbook-base.yaml` —el que copiaste en el paso 1— y mostrá
las ocho objeciones enteras, transpuestas al tratamiento de Q3. El texto sale de ese archivo y de
ningún otro lado: acá no hay una copia pegada que algún día diga otra cosa.

Transponer cambia los verbos, no sólo el pronombre: `necesitás` → `necesitas` → `necesita`,
`pensalo` → `piénsalo` → `piénselo`. Con `vos` no toques nada: el archivo ya viene en voseo.

Los huecos entre llaves se llenan con lo que ya está contestado, y los que no, se dicen:

| Hueco | Sale de | Cuándo |
|---|---|---|
| `{negocio}` | Q1 | ya está contestado: llenalo |
| `{producto}` · `{precio}` | Q5 | tramo 2, todavía no |
| `{horario_1}` | Q7 | tramo 2, todavía no |

Los tres que faltan van como hueco, en pantalla y en el archivo del paso 7. Decilo en una línea:
los llena el paso 8, y `/playbook` entra directo ahí cuando termine `/configurar`. **No los
inventes**: un precio inventado en la objeción del descuento es la promesa que después paga el
negocio.

Cerrá con "¿Va así, o cambiás alguna?" y esperá.

**Tenés que ver.** Las ocho objeciones en pantalla con el tratamiento de Q3, y un "va" explícito o
las líneas cambiadas. Nadie firma lo que no leyó.

**Si falla.** No existe `config/playbook-base.yaml`: te salteaste el `cp` del paso 1, volvé y
copialo. Cambia una respuesta: escribila tal cual la dictó, y eso va al paso 7, no a la copia.
Mete un precio o un "garantizado":
sacalo y decí por qué —las dos últimas objeciones, el descuento y la garantía, están escritas
justo para no prometer eso—. No contesta: sin "va" no hay paso 7.

### Paso 3 · Camino B · leé los archivos y clasificalos

**Objetivo.** Sabés qué hay, qué pudiste leer, y qué es metodología de venta.

**Hacé esto.** Antes de que copie nada, decile una vez: eso no sale de su máquina, `knowledge/`
está en `.gitignore` y no viaja a ningún repositorio ni a ningún servicio.

Después `ls -la knowledge/closer/`. TXT, MD, VTT y SRT con Read, y el origen es la línea o el
timestamp; PDF con Read y `pages`, de a 20, y el origen es la página. DOCX es un zip:

```bash
python3 -c "
import re,sys,zipfile
x=zipfile.ZipFile(sys.argv[1]).read('word/document.xml').decode('utf-8')
print(re.sub(r'<[^>]+>','',re.sub(r'</w:p>','\n',x)))
" knowledge/closer/ARCHIVO.docx
```

**Tenés que ver.** Un renglón por archivo: nombre, formato, páginas o líneas leídas, y si es
metodología de venta o material de negocio.

**Si falla.** Carpeta vacía: ofrecé `A` o `C`, no inventes contenido. Formato fuera de la lista, o
PDF escaneado en blanco: nombralo y pedí que lo convierta; una foto de una lista de precios no es
una lista de precios. **No es metodología de venta** —un catálogo, un contrato, un manual—: decí
qué es y por qué no sirve para cerrar, movelo con `mv` a `knowledge/negocio/`, que es donde sí
sirve, y ofrecé `A` o `C`. Si es una lista de precios, ofrecé cargarla como catálogo y ahorrarle
la Q5.

### Paso 4 · Camino B · extraé en tres pasadas

**Objetivo.** Tenés objeciones, tono y rúbrica, cada uno con su origen al lado.

**Hacé esto.** Tres pasadas separadas sobre el mismo material.

**1 · objeciones.** Pares "lo que dice el cliente" → "qué contestar": en una transcripción, el
turno del cliente y el siguiente del vendedor; en un curso, las listas y las preguntas frecuentes.
Dos líneas por respuesta, con las palabras del material. Si trae precio o plazo, sacalo.

**2 · tono.** Tres medidas, no impresiones: largo típico en palabras, si pregunta o si afirma
(contá los signos de interrogación), si usa el nombre.

**3 · rúbrica.** Si trae un marco de calificación, mapealo a los tres factores del paso 2 y decí
el mapeo en pantalla. BANT: `Budget` → presupuesto, `Timeline` → urgencia, `Need` → encaje.
`Authority` no entra en los tres y no se pierde: se vuelve la objeción "lo tengo que consultar".
Otro marco, los mismos tres, y decí qué quedó afuera.

**Tenés que ver.** Un conteo antes de mostrar nada: cuántas objeciones, cuántas líneas de tono, y
qué marco.

**Si falla — extracción flaca, menos de 3 objeciones usables.** Decí cuántas salieron y ofrecé
tres salidas, sin elegir por él: `completar`, las ocho de `plantillas/config/playbook-base.yaml`
reescritas en el tono que extrajiste —se lee la plantilla, y la copia que el paso 1 dejó también
por este camino, `config/playbook-base.yaml`, queda como quedó: ésa no se edita nunca—;
`preguntame`, las preguntas del paso 6 sólo para lo que falta; `así`, seguir con esas pocas.
Elija lo que elija, el piso lo completa el paso 5: esas dos no dependen de esta elección.
**Nunca rellenes en silencio:** un playbook que él cree suyo y no lo es se descubre con un
cliente adentro.

### Paso 5 · Camino B · mostrá la extracción y esperá aprobación

**Objetivo.** El usuario vio de dónde salió cada línea, y qué dejaste afuera.

**Hacé esto.** Numerada, con el origen al lado de cada par, y `NO SAQUÉ` al final:

```
1. "Está caro"  ← curso-ventas.pdf, p. 41
   → ¿Contra qué lo comparas?
2. "Lo tengo que consultar"  ← llamada-marzo.vtt, 00:14:20
   → ¿Qué te van a preguntar?

NO SAQUÉ
- Cap. 7, prospección en frío (p. 88-104): es cómo conseguir el chat, no cómo cerrarlo.
- Los casos de éxito (p. 12-19): traen cifras de resultado, y eso no se promete por chat.
```

**Y completá el piso.** Mirá si entre lo que extrajiste hay una objeción de descuento y una de
garantía. La que falte sale del base —`config/playbook-base.yaml`, la copia que el paso 1 dejó
también por este camino—, transpuesta al tratamiento de Q3, con `{negocio}` llenado desde Q1 y los
otros tres huecos abiertos para el paso 8. Va en un bloque aparte, marcado:

```
AGREGUÉ DEL BASE
- "¿Me hacés un descuento?" — no estaba en el material. En vez de negar, deriva a una persona: el
  descuento lo firma alguien, y prometerlo por chat lo termina pagando el negocio.
- "¿Y si no me funciona? / ¿Tienen garantía?" — no estaba en el material. Por lo mismo.
```

La que ya cubrías queda como la escribiste y se dice cuál: la tuya no se pisa. Podés reescribirlas
en el tono que extrajiste; lo que no se toca es la derivación ni el hueco del precio. Reescrita o
tal como vino del base, la que quede es la que el paso 7 ancla en `piso:`.

Cerrá con "¿Lo dejo así, cambiás alguna, o falta una que siempre te dicen?", y preguntá aparte por
las dos que agregaste.

**Tenés que ver.** Aprobación explícita, y un "va" propio para el bloque `AGREGUÉ DEL BASE` si
hubo. El origen lo hace confiar; `NO SAQUÉ` evita que en un mes pregunte dónde quedó el capítulo 7.

**Si falla.** "Esa no la digo así": ponés su frase, sin discutir. Reclama algo que no extrajiste:
agregalo con su origen y sacalo de `NO SAQUÉ`. Aprueba una parte: escribí esa y volvé al paso 4.
No quiere las dos del piso: salen, y decile qué pasa entonces —está en la cabecera de este
archivo—.

### Paso 6 · Camino C · las seis preguntas

**Objetivo.** Tenés las objeciones, el tono, la rúbrica y el freno, dichos por el usuario.

**Hacé esto.** De a una, en este orden, esperando cada respuesta:

> **C1.** ¿Qué es lo primero que te dicen cuando les pasás el precio? Copiame la frase como te la
> escriben.
> **C2.** Cuando te dicen eso, ¿qué contestás vos? La frase, no la idea.
> **C3.** ¿Cuál es la excusa que más te repiten para no cerrar hoy, y qué le contestás?
> **C4.** Abrí tu WhatsApp y pegame tres mensajes que vos ya le mandaste a un cliente. Los que
> encuentres primero, sin editarlos.
> **C5.** Cuando te escribe alguien nuevo, ¿en qué te fijás para saber si vale la pena? Tres cosas.
> **C6.** ¿Qué tema no querés que conteste solo, y preferís que te lo pase a vos?

C4 sostiene el resto: nadie sabe describir su propia voz, y todo el mundo tiene tres mensajes en
el historial. De ahí sale el tono. De C5 salen los tres factores del paso 2; de C6, la escalación.

**Y completá el piso, que las seis preguntas no cubren.** Ninguna pregunta por descuento ni por
garantía, y son dos objeciones que salen caras si el agente improvisa. Terminada C6, hacé lo mismo
que el camino B: leé `config/playbook-base.yaml` —la copia que el paso 1 dejó por este camino—,
transponé esas dos al tratamiento de Q3, llená `{negocio}` desde Q1 y dejá los otros tres huecos
para el paso 8. Mostralas en un bloque `AGREGUÉ DEL BASE` con el por qué en una línea, y pedí el
"va" por esas dos aparte. Si en C1 o en C3 ya te dijo cómo contesta el descuento, esa queda como la
dictó y se lo decís: esa misma es la que va en `piso.descuento`, y del base no entra otra.

**Tenés que ver.** Las seis respuestas, C1 a C3 armadas como pares objeción → respuesta, el bloque
`AGREGUÉ DEL BASE` con lo que faltaba del piso, y un "va" antes del paso 7.

**Son cuatro objeciones, y ése es el número normal por este camino**: una de C1 más C2, otra de C3,
y las dos del piso. Tres si en C1 o en C3 ya te contestó el descuento, porque esa cuenta como el
piso y no se agrega dos veces. Decí el número en pantalla, porque cuatro al lado de las ocho del
camino A parece que se perdió algo, y no se perdió nada: las seis preguntas preguntan por dos
objeciones, no por ocho.

**Si falla.** **C2 contestada con una teoría** ("le explico el valor"): insistí **una vez** —"Dame
la frase que le escribís, tal cual la mandás"—, y si vuelve la teoría, tomala así y seguí. Sin
mensajes a mano en C4: pedí uno solo. Contesta las seis en un bloque: separalas y confirmá cuál es
cuál. No quiere las dos del piso: salen, y decile qué pasa entonces —está en la cabecera de este
archivo—.

### Paso 7 · Escribí `config/playbook.yaml`

**Objetivo.** Existe el archivo, con el tratamiento de Q3 y sin nada que el usuario no aprobó.

**Hacé esto.** `mkdir -p config` y escribí.

**Camino A.** El contenido ya lo tenés: las **ocho** objeciones de `config/playbook-base.yaml` con
el tratamiento de Q3 y los huecos que llenaste en el paso 2, más el bloque `rubrica` de ese mismo
archivo, con los cambios que haya pedido y ninguno más. Los huecos de Q5 y Q7 que todavía no tienen
respuesta van como hueco: los llena el paso 8. El `piso:` sale de la séptima y la octava, ya
transpuestas al tratamiento de Q3: se copian de ahí, no del base.

**Caminos B y C.** Sale de lo que extrajiste o de lo que dictó, más las dos del piso que aprobó en
el paso 5 o en el 6.

**La forma es una sola y es ésta, por A, por B y por C.** Cambia el contenido, no la estructura:

```yaml
playbook:
  tono: |
    Directo y corto. Una idea por mensaje. Pregunta antes de proponer.
  objeciones:
    # curso-ventas.pdf, p. 41
    - objecion: "Está caro"
      respuesta: "¿Contra qué lo comparas?"
    # del base, reescrita con sus palabras
    - objecion: "¿Me podés hacer un precio mejor?"
      respuesta: "El de lista de {producto} es {precio}, y el descuento lo firma una persona."
    # del base, reescrita con sus palabras
    - objecion: "¿Y si no me sirve? ¿Me devuelven la plata?"
      respuesta: "Las condiciones las confirma una persona de {negocio}, con lo que esté por escrito."
piso:
  descuento: "¿Me podés hacer un precio mejor?"
  garantia: "¿Y si no me sirve? ¿Me devuelven la plata?"
rubrica:
  presupuesto: "Lo dice o se deduce. Si no, va en nulo."
```

**`objeciones` y `tono` van adentro de `playbook:`, y no al tope del archivo.** Es lo que lee el
chequeo 20 de la compuerta —el bloque `playbook:`, validado contra el fragmento del contrato— y es
la forma que ya trae `config/playbook-base.yaml`, así que por el camino A la estructura se copia
tal cual. Escrito plano, con `objeciones` y `tono` arriba de todo, el archivo sale así aunque el
contenido esté perfecto:

```
playbook/no_valida  no hay un bloque `playbook:` adentro del archivo
```

La proyección del paso 9 de `blueprint/20-entrevista.md` lo lee anidado y lo dice con estas mismas
palabras. Una segunda forma no existe.

**El origen va como comentario `#`, nunca como campo**: el fragmento tiene
`additionalProperties: false`, y una clave de más adentro de una objeción tira la validación. Y
**`rubrica` va afuera de `playbook:`**, al mismo nivel. Decile una línea más: lo que quedó ahí son
respuestas reescritas con sus palabras y las de su negocio, no párrafos copiados del material.

**`piso` va afuera de `playbook:` por lo mismo, y va por los tres caminos.** Adentro de una
objeción no entra una clave de más, ni `origen` ni `clave`; el ancla vive arriba, en un bloque de
dos claves fijas —`descuento` y `garantia`— y cada una lleva el `objecion` que quedó escrito,
copiado tal cual. Es lo que hace que el paso 9 sepa que el piso está sin buscar la palabra
«descuento» adentro del texto, que es lo que rompe apenas el usuario lo escribe con sus palabras.
Tres reglas y ninguna más:

- **Se escriben juntas.** Cambiar el texto de la objeción es cambiar las dos líneas, la de arriba y
  el ancla. Un ancla que no calza con ninguna objeción sale en el paso 9 como `el ancla no está en
  la lista`, y una que calza con la objeción equivocada, como `el ancla no habla de …`.
- **La que él sacó va en `null`**, con el motivo al lado como comentario. Sacada a propósito no es
  lo mismo que faltante, y el paso 9 las cuenta distinto.
- **Ni `piso` ni `rubrica` viajan al contrato.** La proyección del paso 9 de
  `blueprint/20-entrevista.md` sólo se lleva `objeciones` y `tono`; estos dos se quedan en
  `config/`.

**Tenés que ver.** El archivo escrito. Éste sí se versiona, al revés de `knowledge/`.

**Si falla.** **Ya existe** —es lo normal si entraste por `/playbook`—: no lo pises, y antes de
proponer nada mirá qué le falta con el `grep` de la cabecera. Si lo único abierto son huecos, acá
no hay nada que reescribir: andá derecho al paso 8, que los llena sin tocar el resto. Si lo que
cambia es una objeción o el tono, mostrá el antes y el después de esa línea sola y esperá
confirmación; lo demás queda como está. `config/` sin permiso de escritura: decí la ruta y el
error, no escribas en otro lado.

### Paso 8 · Llená los huecos con el catálogo y la agenda

**Objetivo.** Ninguna respuesta de `config/playbook.yaml` sale con un `{hueco}` adentro, o los que
quedan están dichos en pantalla y con el comando que los cierra.

**Hacé esto.** Este paso corre solo: no vuelve a preguntar Q4 y no rehace A, B ni C. Empezá por ver
qué quedó abierto.

```bash
grep -nE "\{[a-z_0-9]+\}" config/playbook.yaml
```

Sin salida no hay nada que llenar: seguí al paso 9. Con salida, cada hueco tiene un origen y uno
solo, y ninguno se deduce de otro lado:

| Hueco | Sale de | Clave |
|---|---|---|
| `{negocio}` | `config/marca.yaml` (Q1) | `negocio` |
| `{producto}` | `config/negocio.yaml` (Q5) | `catalogo[].nombre` |
| `{precio}` | `config/negocio.yaml` (Q5) | `precio` y `moneda` **de esa misma fila** |
| `{horario_1}` | `config/agenda.yaml` (Q7) | `franjas[]` |

**Si `config/negocio.yaml` o `config/agenda.yaml` todavía no existen, no llenes nada.** Es lo
normal viniendo de `/armar-cerrador`: Q5 y Q7 son del tramo 2. Decí esta línea, anotá los huecos en
`.wca-estado.json` bajo `playbook.huecos_abiertos`, y seguí al paso 9:

> El playbook quedó con estos huecos: `{producto}`, `{precio}`, `{horario_1}`. Los llena
> `/playbook` cuando termines `/configurar`, y entra directo en el paso que los llena: no te
> vuelve a preguntar nada de lo que ya contestaste.

**`{precio}` sale del catálogo, con su moneda, y de ningún otro lado.** No sale de `rango_precio`
(Q6): esos dos números son para escalar, no son un precio de lista. Y viaja con `{producto}`: el
par sale de la misma fila o no sale.

- **El catálogo tiene una fila.** Llenás el par con esa.
- **Tiene varias.** No elijas por él. Mostrá la tabla y preguntá cuál va acá, una sola vez: la
  respuesta es un texto fijo y adentro entra un precio solo. El resto del catálogo le llega al
  agente por la entrada y los otros precios los dice igual; lo que queda fijo es esta línea.
- **Lo que pide no está en el catálogo, o el catálogo está vacío.** No se inventa, y el hueco
  tampoco se deja puesto: `{precio}` sin llenar es lo que termina leyendo el cliente. Dos salidas,
  y elige él: sacar la línea del precio y dejar la derivación, que es lo que esa objeción hace; o
  dejar la objeción afuera hasta que Q5 esté contestada, y entonces el agente la nombra y te la
  deja a vos.

**`{horario_1}` sale de `config/agenda.yaml` y de ningún otro lado, y no se llena con una fecha.**
Va la ventana de `franjas` en palabras —`un horario entre las 10 y las 13`—, que es lo que entra
bien en las dos frases que lo usan. Una fecha concreta acá envejece en cinco días hábiles, y sale
por el paso 3 del agente: un horario que no está en `disponibilidad` cuando el mensaje se manda es
la aserción 3 de `pruebas/caso-01.md` en rojo. Sin `franjas`, sacá la pregunta por el horario y
dejá la derivación.

Mostrá cada línea antes y después, y esperá el "va". Recién ahí editás `config/playbook.yaml`, y
sólo las respuestas que tenían hueco: el tono, la rúbrica y las demás objeciones no se tocan. Si
entraste por `/playbook`, mostrá además la lista entera una vez antes de escribir: es lo que pide
`.claude/skills/playbook/SKILL.md`, y es la única sección de `.wca-estado.json` que este paso toca.

**Tenés que ver.** Una de dos: el `grep` de arriba sin salida y `playbook.huecos_abiertos` en `[]`;
o la lista de los que quedaron, en pantalla y en esa clave, cada uno con su motivo.

**Si falla.** No existe `config/playbook.yaml`: no hay nada que llenar, andá al paso 1. El `grep`
sigue mostrando el mismo hueco después de editar: lo llenaste en `config/playbook-base.yaml`, que
es la copia del base y no se edita nunca; lo que se edita es `config/playbook.yaml`. `{negocio}`
sigue abierto: sale de `config/marca.yaml`, que es del tramo 1 y ya existe, salvo que hayas entrado
acá sin pasar por Q1.

### Paso 9 · Validá contra el contrato

**Objetivo.** El bloque `playbook:` valida contra el fragmento de `contratos/entrada.schema.json`.

**Hacé esto.** Con el Python del proyecto, que es el que tiene `PyYAML` y `jsonschema` desde la
fase 1. En PowerShell es `.venv\Scripts\python.exe` y el bloque va a un archivo: el heredoc es de
bash.

```bash
.venv/bin/python - <<'PY'
import json, re, unicodedata, yaml, jsonschema

CLAVES = ("descuento", "garantia")
# Qué hace que una objeción SEA la del descuento o la de la garantía, escrita con las palabras
# que sean. No es la palabra de la clave: por B y por C reescribirlas es el punto. Y «caro» no
# está en esta lista a propósito: «Está caro» es otra objeción del base, y anclarla en `piso`
# era la línea que daba `piso: 2 de 2` con el piso vacío.
SENTIDO = {
    "descuento": ("descuent", "rebaj", "promo", "oferta", "cupon", "mas barato",
                  "precio mejor", "mejor precio", "bajar el precio", "precio especial"),
    "garantia": ("garant", "devuelv", "devolucion", "reembols", "no me sirve",
                 "no me funciona", "si no sirve", "si no funciona", "de vuelta"),
}


def plano(texto):
    """Minúsculas y sin tildes: «garantía» y «garantia» son la misma palabra."""
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                   if not unicodedata.combining(c))


def habla_de(texto, clave):
    return any(marca in texto for marca in SENTIDO[clave])


crudo = open("config/playbook.yaml", encoding="utf-8").read()
cfg = yaml.safe_load(crudo)
frag = json.load(open("contratos/entrada.schema.json", encoding="utf-8"))["properties"]["playbook"]
jsonschema.Draft202012Validator(frag).validate(cfg["playbook"])

objs = cfg["playbook"]["objeciones"]
textos = {o["objecion"]: plano(o["objecion"] + " " + o["respuesta"]) for o in objs}
bloque = cfg.get("piso")
decl = bloque if isinstance(bloque, dict) else {}

piso, sacadas, hallazgos = [], [], []
for clave in CLAVES:
    anclada = decl.get(clave)
    if clave in decl and anclada is None:
        sacadas.append(clave)
    elif anclada is None:
        escrita = next((o for o, t in textos.items() if habla_de(t, clave)), None)
        hallazgos.append(f"{clave}: escrita y sin anclar → «{escrita}»" if escrita
                         else f"{clave}: falta la objeción")
    elif anclada not in textos:
        hallazgos.append(f"{clave}: el ancla no está en la lista → «{anclada}»")
    elif not habla_de(textos[anclada], clave):
        hallazgos.append(f"{clave}: el ancla no habla de {clave} → «{anclada}»")
    else:
        piso.append(clave)

huecos = sorted(set(re.findall(r"\{[a-z_0-9]+\}", crudo)))
linea = f"playbook: valida · {len(objs)} objeciones · piso: {len(piso)} de 2"
if sacadas:
    linea += " (sacadas a propósito: " + ", ".join(sacadas) + ")"
if not isinstance(bloque, dict):
    linea += " (sin bloque piso)"
print(linea + " · huecos: " + (", ".join(huecos) or "ninguno"))
for hallazgo in hallazgos:
    print("  piso · " + hallazgo)
PY
```

**El piso se cuenta por la clave, no por la palabra.** La cuenta mira `piso.descuento` y
`piso.garantia` y verifica que cada una apunte a una objeción que está en la lista. Buscar
«descuento» o «garant» adentro del texto de la objeción daba rojo con un playbook que las tiene:
«¿Me podés hacer un precio mejor?» y «¿Y si no me sirve? ¿Me devuelven la plata?» son las dos, y no
llevan ninguna de las dos palabras. Ese falso rojo caía justo por B y por C, que son los dos
caminos donde reescribirlas es el punto.

**Y se verifica por el contenido, porque la clave sola se falsifica en una línea.** Contar anclas
que existen deja pasar esto:

```yaml
piso:
  descuento: "Está caro"
  garantia: "No tengo tiempo"
```

Las dos objeciones están en la lista, las dos claves apuntan a algo, y la cuenta daba `2 de 2` con
el piso vacío: ninguna de las dos deriva un descuento ni una condición de garantía. Por eso, además
de que el ancla exista, se mira si esa objeción **habla de lo que la clave dice** —sobre `objecion` y
`respuesta` juntas, en minúsculas y sin tildes—. `SENTIDO` es esa lista y viaja adentro del comando:
está a la vista para poder ampliarla. «caro» no está ahí a propósito, porque «Está caro» es otra de
las ocho del base.

**Tenés que ver.** Una línea con las tres cuentas, y una línea más por cada clave del piso que no
quedó anclada. Por el camino A, recién salido del tramo 1, son las ocho del base, el piso entero y
los tres huecos que el paso 8 todavía no puede llenar: una línea y nada debajo.

```
playbook: valida · 8 objeciones · piso: 2 de 2 · huecos: {horario_1}, {precio}, {producto}
```

Cuando el piso no está entero, debajo va el renglón que dice cuál de los cuatro problemas es. Dos
que se leían idénticos y son cosas distintas:

```
playbook: valida · 2 objeciones · piso: 0 de 2 (sin bloque piso) · huecos: ninguno
  piso · descuento: falta la objeción
  piso · garantia: falta la objeción
```

```
playbook: valida · 3 objeciones · piso: 0 de 2 (sin bloque piso) · huecos: {negocio}, {precio}, {producto}
  piso · descuento: escrita y sin anclar → «¿Me podés hacer un precio mejor?»
  piso · garantia: escrita y sin anclar → «¿Y si no me sirve? ¿Me devuelven la plata?»
```

El primero es un playbook al que le faltan las dos objeciones y hay que volver al paso 5 o al 6. El
segundo las tiene escritas con las palabras del usuario y lo único que falta son las dos líneas del
bloque `piso:`, que es trabajo del paso 7. Antes los dos decían `piso: 0 de 2 (sin anclar:
descuento, garantia)` y mandaban al mismo lado.

**El número de objeciones no es el mismo por los tres caminos**, y por C sorprende: son cuatro.
Decilo antes de que lo lea, porque cuatro al lado de ocho parece un playbook a medias y no lo es.

| Camino | Objeciones | De dónde salen |
|---|---|---|
| A | 8 | las ocho del base, aprobadas en el paso 2 |
| B | las que extrajiste más las que le faltaran al piso | con menos de 3 usables, el paso 4 no exige ninguna cantidad: ofrece `completar` —que las lleva a 8—, `preguntame` o `así`, y elige él |
| C | 4, o 3 si en C1 o en C3 ya contestaba el descuento | una de C1 más C2, otra de C3, y las dos del piso |

`piso: 2 de 2` por los tres caminos, **salvo que las haya sacado él**. Salir por debajo del piso se
puede por A, por B y por C —está en la cabecera de este archivo: si dice que no las quiere, salen, y
se le dice qué pasa entonces—, y entonces la clave queda en `null` y la línea lo dice sola:
`(sacadas a propósito: descuento)`. Lo que no existe es un piso incompleto sin decisión escrita: eso
son los renglones de arriba. `huecos: ninguno` cuando el tramo 2 ya está contestado. Menos de ocho
por el camino A es una objeción que se perdió entre el paso 2 y el 7: volvé al paso 2 y contá contra
`config/playbook-base.yaml`. Después escribí `playbook.listo: true` en `.wca-estado.json` y volvé a
quien te llamó.

**Si falla.**
- `.venv/bin/python: No such file or directory` → todavía no hay venv, y eso es la fase 1:
  `blueprint/10-entorno.md`. En Windows el ejecutable es `.venv\Scripts\python.exe`.
- `No module named 'yaml'` o `'jsonschema'` → lo corriste con el Python del sistema, que no los
  trae. Repetilo con el del venv. Si tampoco están ahí, instalalos con la versión que fija
  `PINES.md`, nunca de memoria:
  ```bash
  .venv/bin/python -m pip install "$(grep -m1 '^PyYAML==' PINES.md)" \
    "$(grep -m1 '^jsonschema==' PINES.md | cut -d' ' -f1)"
  ```
  Si `pip` falla —sin red, o `externally-managed-environment`— revisá a mano lo que pide el
  fragmento: `objeciones` es una lista con al menos un elemento, y cada uno trae `objecion` y
  `respuesta` con texto. Seguí, y dejá dicho que quedó validado a ojo.
- `piso · garantia: escrita y sin anclar → «…»` → la objeción está escrita y el bloque `piso:` no la
  nombra; si además falta el bloque entero, la línea de arriba dice `(sin bloque piso)`. No agregues
  una objeción repetida: copiá en esa clave el `objecion` que quedó, tal cual, y volvé a correr. Es
  lo que pasa cuando reescribiste las dos con tus palabras, que es exactamente lo que el paso 5 y el
  paso 6 te dejan hacer.
- `piso · garantia: falta la objeción` → ahí sí falta: ninguna de las que hay habla de eso. Por el
  camino A no puede pasar, son dos de las ocho. Por B o por C el paso 5 o el 6 no completaron el
  piso; volvé y mostralas. Si él las sacó, esto no es lo que sale: la clave va en `null` y la línea
  la cuenta aparte.
- `piso · descuento: el ancla no está en la lista → «…»` → la clave nombra un texto que después
  cambió, o que nunca llegó a `objeciones`. Se escriben juntas: copiá el `objecion` que quedó.
- `piso · descuento: el ancla no habla de descuento → «Está caro»` → dos casos, en este orden. Uno,
  anclaste otra objeción: «Está caro» no es «¿me hacés un precio mejor?», y el piso está vacío aunque
  las dos claves apunten a algo. Corregí la clave. Dos, es la del descuento de verdad y la escribió
  con una palabra que `SENTIDO` no tiene: agregá esa palabra a la tupla del comando, decí en pantalla
  que la ampliaste y volvé a correr. Lo que no se hace es sacar el chequeo: sin él, dos líneas
  cualesquiera vuelven a dar `2 de 2`.
- `piso: 1 de 2 (sacadas a propósito: descuento)` → las sacó él y está bien: la clave queda en
  `null` con el motivo al lado. Anotá cuál sacó y por qué en `.wca-estado.json`, y que el agente la
  va a nombrar sin contestarla.
- `huecos:` con algo listado y `config/negocio.yaml` ya en disco → el paso 8 no corrió, o corrió
  antes del tramo 2. Volvé al paso 8: ese `{precio}` es lo que lee el cliente.
- `Additional properties are not allowed ('origen' was unexpected)` → se coló un campo adentro de
  una objeción. Pasalo a comentario `#`.
- `'objeciones' is a required property` → quedó vacío. Volvé al paso 4 o al 6.
- `yaml.scanner.ScannerError` → comillas sin cerrar, o un `:` suelto en una respuesta.

---

**Próximo archivo:** `blueprint/30-generacion.md`, que escribe el esqueleto del agente y copia
lo verbatim. Con esto el playbook quedó en `config/playbook.yaml` y validado contra el
fragmento `playbook` de `contratos/entrada.schema.json`.

La excepción: si llegaste acá por `/playbook` —y no construyendo de cero— terminaste. Volvé a
lo que estabas haciendo. La cadena de fases sigue en `30-generacion.md` sólo cuando venís de
`/armar-cerrador`.

Y si quedaron huecos abiertos —Q5 y Q7 son del tramo 2, así que en la primera corrida quedan
siempre— cerrá diciendo cuáles y con qué se cierran: `/configurar` primero, `/playbook` después,
que entra directo en el paso 8 y no vuelve a preguntar nada de esto.
