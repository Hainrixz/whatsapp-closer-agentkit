# 60 · La bandeja y el paso a automático

**Después de la fase 6.** Entrás con el agente en `borrador`; salís con los borradores resueltos
de a uno, el par viejo/nuevo guardado, y el paso 3 en `automatico` si los números dan. Se abre
cada día: acá entran `/bandeja` y `/soltar`, y acá vuelve `/playbook`.

**Invariante 2:** aprobar no manda; vuelve a correr el paso con `confirmado` en verdadero y manda
el único `enviar()` —la ventana de 24 horas, que es el plazo desde el último mensaje del contacto en
el que WhatsApp deja contestar texto libre (ver `blueprint/00-contrato.md` § 10); el baneo; y nunca
escribirle primero a quien no escribió—. **Invariante
3:** el aviso interno sale por `agente/http.py`, con `timeout=`. **Invariante 5:** en el panel va
de qué ítem del catálogo salió cada precio.

---

### Paso 1 · Escribí `config/cerrador.yaml`

**Objetivo.** Los números de la compuerta existen en disco y se editan sin tocar código.

**Hacé esto.**

```yaml
modo:
  paso_3: borrador       # responder
  paso_4: borrador       # agendar
  paso_5: borrador       # escribir en el CRM
bandeja:
  aviso_agrupado_min: 10 # junta los avisos de esa ventana en un mensaje
soltar:
  dias_minimos: 7
  borradores_revisados: 20
  sin_corregir_de_los_ultimos_20: 16
  precios_fuera_del_catalogo: 0
  horarios_fuera_de_agenda: 0
```

**Los cinco números son razonables y no están medidos.** Decilo cuando los muestres. Siete días y
no catorce porque lo que madura no es el calendario, son los borradores.

**Los tres modos viven acá; el contrato de entrada tiene uno solo, porque describe una llamada.**
Las dos cosas son ciertas y no chocan, y la costura tiene nombre: **`modo_efectivo()`**, en
`agente/config.py`, devuelve el más conservador de `paso_3`, `paso_4` y `paso_5`, y eso es lo que
viaja en la entrada. Así una salida vieja no se lee como si todo hubiera estado suelto.

Quién escribe qué, para que nadie lo cablee en el lugar de al lado:

| Función | Devuelve | Cuándo |
|---|---|---|
| `entrada_desde_config()` | **nueve claves y ninguna más**, y `modo` no es una de ellas | al armar la entrada |
| `modo_efectivo()` | `borrador` o `automatico`: el más conservador de los tres | por ciclo |

`modo` lo inserta `agente/servidor.py` en cada ciclo, junto con `mensaje` y `confirmado`. Y si este
archivo todavía no está en disco —o sea, en toda la fase 3— `modo_efectivo()` devuelve `borrador`:
el default no depende de que exista un archivo. Ver `blueprint/00-contrato.md` § 9.

**Tenés que ver.** El archivo, y `modo_efectivo()` devolviendo `borrador`.

**Si falla.** Ya existe: no lo pises, mostrá qué cambia y esperá. `yaml.scanner.ScannerError`:
tabulaciones, YAML no las acepta. `No module named 'yaml'`: la versión de `PINES.md`, no de memoria.

---

### Paso 2 · El borrador cae en la bandeja y se avisa una vez

**Objetivo.** Cada redacción del paso 3 en `borrador` queda guardada, legible y anunciada.

**Hacé esto.** El paso escribe la fila en `pendientes` y después `bandeja/<id>.md`. **La fila
manda; el archivo es para leerlo sin abrir el panel.** Si discrepan, gana la fila: el disco de
Railway se borra en cada despliegue y la base no. Con el borrador va su panel: la objeción y si
estaba en el playbook, cada precio con su ítem del catálogo, cada horario con su hueco de
`disponibilidad`, y el score con el motivo.

```bash
grep -q '^/bandeja/' .gitignore || printf '\n/bandeja/\n' >> .gitignore
```

Eso son mensajes de tus clientes. Sin esa línea terminan en un commit, y de ahí no se sacan.

**Tenés que ver.** `ls bandeja/` con un archivo por pendiente, y un aviso por tanda de diez
minutos, con el conteo y nada del texto.

**Si falla.** Sin aviso: falta `SLACK_WEBHOOK_URL`, el borrador se guardó igual y lo que se pierde
es el aviso —ese valor lo escribe quien instala en `.env`, nunca una tool call—. El ciclo se pasa
de cinco segundos: avisás adentro, y el aviso va después del 200, desde la cola. Treinta avisos en
una hora: `aviso_agrupado_min` en 0. `bandeja/` vacío tras un despliegue: disco efímero, leé la
fila.

---

### Paso 3 · `/bandeja` · de a uno, y cuatro respuestas

**Objetivo.** Un borrador por pantalla con todo para decidir, y cada decisión con rastro.

**Hacé esto.** Mostrá esto, y esperá.

```
Borrador 3 de 7 · bsu_01HZK3M9QX7T2VW4 · hace 4 min

 Cliente   Me interesa pero está caro, ¿no tienen algo más económico?

 Borrador  Entiendo. ¿Contra qué lo estás comparando? Con eso te digo si
           el Plan Base te sirve. Si querés lo vemos en 20 minutos:
           martes 11:00, martes 16:30 o miércoles 09:00.

 Objeción  "Está caro" · en el playbook
 Precios   Plan Base, MXN 4 800 · catálogo, ítem 1
 Horarios  19/08 11:00 ← franja mar 09:00-13:00
           19/08 16:30 ← franja mar 14:00-18:00
           20/08 09:00 ← franja mié 09:00-13:00
 Score     71 · caliente · dijo presupuesto y preguntó precio en el primer mensaje
 Ventana   abierta, quedan 19 h

va · no · corregí <texto> · saltar
```

`va` vuelve a correr el paso 3 con `confirmado: true` —la bandeja no manda, manda `enviar()`—.
`no` lo cierra sin mandar y le pedís el motivo en una línea. `corregí <texto>` manda el texto del
usuario tal cual **y guarda el par viejo/nuevo** en la tabla `correcciones`: es lo más valioso que
produce esta etapa, y por eso no vive en un archivo. `saltar` lo deja pendiente. Nada más.

El borrador está en el tratamiento de Q3 —acá, `vos`—. El panel te habla a vos. No se mezclan.

**Tenés que ver.** Un borrador, no siete. Y tras un `corregí`, una fila nueva en `correcciones`.

**Si falla.** Sin pendientes: decilo con el número y nada más. Panel vacío o `Objeción: —`: el
paso 3 no guardó el razonamiento, y sin eso esto es un botón de aprobar a ciegas; arreglá el paso.
`enviado: true` y no llegó nada: `enviar()` se negó por la ventana de 24 horas, y afuera hace falta
plantilla aprobada. `corregí` mandó sin guardar el par: es la falla silenciosa de este archivo, no
rompe nada hoy y en dos semanas el resumen sale vacío. La corrección viene en otro tratamiento que
el de Q3: decilo y preguntá antes de mandar.

---

### Paso 4 · `/bandeja resumen` · lo que devuelve la espera

**Objetivo.** El usuario sale con algo que no tenía: las objeciones que su playbook no cubre, con
la respuesta que él mismo escribió.

**Hacé esto.** El riesgo del modo borrador es el día 4: aprobó veinte, todos estaban bien, y siente
que hace el trabajo del agente. Ahí suelta sin leer, o abandona. Esto lo contesta.

```
Bandeja · 9 días · 31 borradores

  Salieron tal cual     22   71 %
  Los corregiste         7
  Los frenaste           2   "eso no lo damos en agosto"
  Salteados              0

Lo que más corregiste
  1. Los horarios: 5 de 7 veces cambiaste el orden o sacaste el de las 09:00.
     Eso se arregla en config/agenda.yaml, no borrador por borrador.
  2. El cierre: 3 de 7 veces le sacaste la pregunta final.

Objeciones que aparecieron y NO están en tu playbook
  · "¿Lo puedo pagar en cuotas?"        4 veces
    Contestaste: "Sí, en tres pagos sin interés, te paso el enlace."
  · "¿Y si no me sirve, me devuelven?"  2 veces
    Contestaste: "Tenés 15 días para pedir la devolución."
  · "¿Me atiende alguien de acá?"       1 vez
    Sin responder: lo pasaste a una persona.

Con /playbook las sumo a config/playbook.yaml con tus palabras. Dos minutos, y
son siete borradores menos por semana.
```

Las dos semanas dejan de ser una cuarentena: son la etapa donde se termina el playbook.

**Tenés que ver.** Números reales, y la lista de objeciones aunque tenga un renglón.

**Si falla.** Lista vacía con treinta borradores: casi seguro `respuesta.objecion_en_playbook`
nunca se escribió, y eso se lee como "tu playbook está completo", la conclusión más cara del
archivo; verificalo contra la tabla antes de mostrarlo. Sin correcciones todavía: decí el número y
no inventes un consejo.

---

### Paso 5 · `/soltar` · la compuerta informa, no bloquea

**Objetivo.** El usuario ve las cinco condiciones con su valor real, decide, y queda anotado con
qué números decidió.

**Hacé esto.** Dos alcances: `paso-3` y `todo`, que suelta los tres. **Recomendá `paso-3`:** el
agente contesta solo, pero agendar y escribir en el CRM te los sigue preguntando. Agendar mal y
escribir mal en la base son más caros de deshacer que un mensaje, y un mensaje se corrige con otro
mensaje.

```
Soltar · alcance recomendado: paso-3

  ok     Días con la bandeja abierta         9   piso 7
  ok     Borradores revisados               31   piso 20
  falta  De los últimos 20, sin corregir    14   piso 16
  ok     Precios fuera del catálogo          0   piso 0
  ok     Horarios fuera de la agenda         0   piso 0

  (informativo, no es piso: 3 objeciones aparecieron fuera del playbook)

Falta una. De esas seis correcciones, dos fueron por "¿lo puedo pagar en cuotas?",
que no está en tu playbook: si la sumás con /playbook, ese número sube solo.

  soltar igual    lo cambio ahora, con 14 de 20. Es tu negocio.
```

Si no cumple, **ofrecé `soltar igual`** y con esa respuesta lo cambiás sin discutirlo de nuevo.
Bloquear a alguien en su propio proyecto es lo que hace que borren el repo.

Cuando suelta, escribí `modo.paso_3: automatico` y al lado `soltado_con:` con los cinco valores
del momento y la fecha. Decí qué cambia: **el agente le escribe a una persona sin preguntarte.**
Los pasos 4 y 5 no se tocan acá; se sueltan de a uno, con la misma compuerta.

**Tenés que ver.** Las cinco líneas con el valor al lado del piso, nunca un "vas bien". Y después,
`curl -s localhost:8000/salud` con `"modo":"borrador"`: eso lo devuelve `modo_efectivo()`, que es el
más conservador de los tres, y con `paso_4` y `paso_5` todavía en `borrador` sigue diciendo
`borrador`. No es que no se guardó: es que el paso 3 se soltó y los otros dos no.

**Si falla.** Todo en cero con la bandeja llena: contás archivos de `bandeja/` en vez de filas. Los
pisos no salen del YAML: si el archivo no existe usá los del paso 1 y decí que son de fábrica. El
paso 3 sigue dejando borradores: la configuración se lee al arrancar, reinicialo. Para volver
atrás, `/soltar volver`: es una línea del YAML.

---

## Qué quedó hecho

Los borradores se resuelven de a uno con cuatro palabras, cada `corregí` deja el par viejo/nuevo,
`/bandeja resumen` devuelve las objeciones que el playbook no cubre y `/soltar` muestra cinco
números con su piso. Anotá `bandeja.listo` y el sha256 de `config/cerrador.yaml` en
`.wca-estado.json`.
