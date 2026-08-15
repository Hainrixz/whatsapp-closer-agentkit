# De dónde salió este producto

Cinco respuestas del corpus originaron la ficha. El catálogo registra 31 pedidos en total para
este producto, que es lo que lo puso arriba en la cola.

Solo publicamos el identificador. Ni el texto del comentario ni el usuario de Instagram salen
del análisis privado: esa gente contestó una caja de preguntas de una story, no consintió
aparecer para siempre en un repositorio público.

El número agregado sí se publica, porque no identifica a nadie.

| Identificador |
|---|
| R0028 |
| R0034 |
| R0035 |
| R0038 |
| R0053 |

## Por qué no hay columna de paráfrasis

En el ejemplo de referencia de esta forja cada identificador lleva al lado una línea escrita
por nosotros sobre qué pedía. Acá no la hay: esta corrida se hizo sin acceso al corpus
privado, y una paráfrasis escrita sin leer el original es una invención con formato de cita.

Lo que sí sabemos, y sale de la ficha y no del corpus: el grupo pedía un agente de WhatsApp
con perfil de vendedor y no un bot de menú, que califique, que responda objeciones y que
agende solo.

Cuando esto se corra en una máquina con `CORPUS.md`, la columna se completa y el verificador
la revisa.

## Cómo se verifica

No acá. El chequeo `citas_resuelven` corre en el árbol de la forja, contra el corpus privado,
y ese árbol no viaja con este kit: `scripts/auditar.py`, que es la compuerta de acá, no lee
`CORPUS.md` ni sale a buscarlo. Comprueba dos cosas del lado de la forja:

1. Que cada `R####` exista en `CORPUS.md`.
2. Que esté entre las citas de esta ficha.

Lo segundo atrapa la cita prestada, que es un artefacto apropiándose de la procedencia de otro
para parecer más pedido de lo que fue.

## Si pediste esto

Si alguna de estas cinco respuestas es tuya y querés que tu nombre aparezca junto al producto,
abrí una discusión en el repositorio y lo agregamos. Por defecto no aparece nadie.
