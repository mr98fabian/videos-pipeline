# Cómo mantienen los dibujantes profesionales un personaje idéntico

**Por qué existe este documento (9 ago 2026):** Tadeo "se ve raro". No es una
impresión: la biblioteca tiene **38 láminas y al menos cuatro Tadeos distintos**.
El diagnóstico y el arreglo salen de cómo resuelve esto un estudio de animación
de verdad, que lleva noventa años con el mismo problema — cientos de dibujantes,
miles de dibujos, un solo personaje.

---

## 1. La auditoría: qué está mal hoy, medido sobre las 38 láminas

| Rasgo | Debería ser constante | Qué hay |
|---|---|---|
| Altura en cabezas | una sola | de ~3 (chibi) a ~4,5 |
| Valor del pecho/hocico | uno | blanco, gris y crema |
| Antifaz | una forma | banda fina de bandido **y** parches enormes tipo gafas |
| Orejas | una forma | redondas lisas y puntiagudas con mechones |
| Anillos de la cola | un número | 3, 4 y 5 |
| Ropa | ninguna | desnudo, con pantalón, con chaqueta |
| Contorno | limpio | limpio **y** con mechones de pelo erizados |

**El caso peor es el más visible.** Las láminas `grito_*` — las que abren y
cierran el vídeo, o sea los dos fotogramas que más gente ve — son un personaje
distinto: hocico anguloso, ceja de villano, dos filas de dientes, pelaje erizado.
El resto del vídeo es un mapache redondeado y amable. Ese salto es exactamente
lo que se lee como "raro".

**Causa raíz, y no es el prompt:** cada lámina se generó **por separado** a
partir de una descripción de texto. Un modelo de imagen no "recuerda" un
personaje; vuelve a dibujarlo desde cero cada vez. Treinta y ocho generaciones
independientes son treinta y ocho interpretaciones, por muy buena que sea la
descripción. La solución no es describir mejor.

---

## 2. Cómo lo resuelve un estudio: el personaje es un DOCUMENTO, no un dibujo

Desde los años treinta, ningún estudio deja la identidad de un personaje en manos
de la memoria del dibujante. La deja escrita en un paquete de láminas — el
*character model pack* — que es material de producción obligatorio. Lo estándar,
y lo que le falta a Tadeo, es esto:

**a) Turnaround (hoja de giro).** El personaje de frente, tres cuartos, perfil y
espalda, **a la misma altura y alineado por líneas guía horizontales**: coronilla,
ojos, barbilla, hombros, cintura, rodilla. Es la lámina madre. Sin ella cada
dibujante (o cada generación) inventa el volumen de la cabeza al girarla.

**b) Gráfico de proporción.** La altura se mide **en cabezas**, no en píxeles, y
se fija: los personajes cómicos de los treinta viven entre 3 y 5 cabezas, y esa
cifra no se negocia entre planos. Se anotan también las relaciones internas
(ancho del antifaz en ojos, tamaño del ojo respecto a la cabeza).

**c) Construcción, no contorno.** La regla de Preston Blair (*Cartoon Animation*,
la referencia del oficio para este estilo): el personaje se construye con sólidos
simples — esferas, peras, cilindros — y **el contorno es la consecuencia**. Un
personaje construido se puede redibujar desde cualquier ángulo y sigue siendo él.
Un personaje calcado del contorno se rompe en cuanto gira la cabeza.

**d) Hoja de expresiones.** Nueve o doce caras **en una sola lámina, al mismo
tamaño**. Que estén juntas no es maquetación: es lo que las obliga a compararse
entre sí. Es la diferencia entre "nueve caras del mismo personaje" y "nueve
personajes con la misma descripción".

**e) Hoja de bocas / fonemas.** Para diálogo. Aquí no aplica: **Tadeo no habla**,
hay un solo narrador en off (decisión de `BRANDING_KOREX.md`).

**f) "No-no sheet".** La lámina que más se parece a un test automático: los
errores típicos dibujados **mal**, tachados en rojo, al lado del acierto. Los
estudios grandes las repartían precisamente porque describir el acierto no
impide el error. Nuestro equivalente son las negaciones literales del prompt.

**g) Prueba de silueta.** Rellenar el personaje de negro. Si no se reconoce, el
diseño falla — pasa antes que cualquier detalle. Es la prueba de aceptación más
barata que existe y no necesita ojo entrenado.

---

## 3. La otra mitad: la pose, no el diseño

Un personaje puede estar perfectamente on-model y aun así verse muerto. Lo que
lo arregla es oficio de pose, no de diseño:

- **Línea de acción.** Una sola curva legible que atraviesa el cuerpo entero.
  Una pose sin ella se lee como un muñeco de pie.
- **Una idea por pose.** Si hay que explicar la pose con dos frases, el plano
  dura menos que la explicación.
- **Asimetría.** Los dos brazos iguales y las dos rodillas iguales son la firma
  del dibujo genérico — y es justo lo que devuelve un modelo de imagen cuando el
  prompt no manda una pose concreta.
- **Silueta legible también en la pose**, no solo en el diseño: manos y props
  fuera del cuerpo, nunca superpuestos al torso.

---

## 4. Aplicación al pipeline (esto es lo que se cambia)

La conclusión operativa es que **la consistencia no puede depender de la
generación**. Dos mecanismos, y el orden importa:

1. **Reusar píxeles antes que reusar palabras.** Una pose ya aprobada se guarda
   y se vuelve a pegar tal cual (es lo que ya hace `kx_cast`, y es la razón de
   que la animación de recortes funcione desde South Park). Cero deriva por
   definición: el archivo es el mismo.
2. **Cuando haya que dibujar algo nuevo, el modelo no parte del texto: parte de
   la hoja.** El turnaround aprobado va como imagen de referencia — igual que un
   dibujante nuevo recibe el model pack antes de tocar un lápiz.

Cambios concretos derivados de este estudio:

- **Generar la hoja madre de Tadeo** (turnaround + proporción + expresiones en
  una sola imagen) y guardarla en `assets/kx_cast/tadeo/_hojas/model_sheet.png`.
  Se aprueba una vez y manda sobre todo lo demás.
- **`kx_cast.CHARACTER_LOCK` deja de ser prosa y pasa a ser especificación
  medible**: altura en cabezas, número de anillos de la cola, forma del antifaz,
  valor del pecho, dedos del guante, prohibiciones explícitas (sin ropa, sin
  mechones en el contorno, sin dientes individuales).
- **Retirar las láminas fuera de modelo**, empezando por las de `grito`, que son
  las de la escena 0 y la del cierre. Van a `_rechazadas/` y se regeneran desde
  la hoja madre.
- **Puerta de aceptación de una lámina nueva**: prueba de silueta + comparación
  lado a lado con la hoja madre. Si hay que dudar, está fuera de modelo.

**Reparto secundario (10 ago 2026).** La Bruja del Banco tiene ya su propia
hoja madre en `assets/characters/bruja-del-banco/`. Su caso enseña algo distinto
al de Tadeo: el diseño aprobado **existía** desde el principio —una BANQUERA con
traje de raya diplomática, sombrero picudo y libro de contabilidad— pero el
pipeline nunca lo usaba, porque ella se nombra dentro del `search_term` y no en
`character_terms`. Sin referencia, cada plano inventaba una bruja de cuento
distinta. Ahora `kx_cast.secondary_refs()` detecta su nombre en el texto de la
escena y engancha su hoja y su bloque de identidad.

**Lo que este estudio NO promete:** que el modelo acierte a la primera. Promete
que el fallo se detecte antes de montar y que la referencia sea siempre la misma.
La consistencia de verdad la sigue dando reusar el PNG aprobado.
