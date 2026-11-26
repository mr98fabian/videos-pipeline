# Especificación de las 9 láminas de pose de Tadeo (método trazado)

Diseño (Fable), 25 nov 2026. **Aprobada por Fabian el 25 nov 2026**, con las cinco decisiones de la
sección 0. **No genera nada.** Después una misión aparte (Sonnet)
genera las láminas con `scripts/generar_lamina.py` (`gemini-nano-banana-2.1`) y las traza con `kx_trazo.py`.

## 0. Decisiones que necesito que apruebes

1. **Las 9 poses salen de los guiones, no de la biblioteca.** Conté los `character_terms` de los 7 guiones
   con `series` (6 de «Pelando cable», incluido el piloto del sobregiro, y 1 de «Historias de dinero»). Usan
   exactamente 9 poses; son las de esta lista. `bolsillos`, `picaro`, `senalando` y `pensando` no aparecen en
   ninguno, así que no van (`senalando` ya tiene además la lámina de la API que aprobaste).
2. **`explicando` y `codicia` se regeneran aunque ya tienen lámina vieja.** Las viejas son hojas compuestas
   (cuerpo + cabezas + manos sueltas), de otra familia de proporciones, y la de `codicia` lleva un fajo de
   billetes pegado al dibujo. No se pueden trazar con el mismo criterio que las nuevas.
3. **Corrijo un criterio del encargo.** «Solape ≥ 0,95 contra la hoja madre» no puede cumplirlo una pose
   distinta del neutro: un brazo alzado ya no solapa. Propongo dos niveles (sección 2):
   - *trazo contra su propia lámina*: IoU ≥ 0,95 y marcas ±3 %, automático, como hoy con la madre;
   - *lámina contra la madre*: solo proporciones que no dependen de la pose.
4. **La tolerancia lámina-madre no está medida.** Propongo ±8 % y calibrarla con `pointing_api.png`, que ya
   aprobaste: si esa lámina no cabe en ±8 %, la tolerancia se ajusta a ella antes de generar las 9.
5. **Cuerpo de frente en las 9.** La cabeza la pone el rig y solo existe de frente (gira un falso 3/4 corto).
   Un cuerpo en 3/4 con cabeza frontal se rompe; por eso ningún prompt pide 3/4, aunque `pointing_api` lo sea.

## 1. Las 9 poses y su uso en guion

Usos = veces que aparece en los 7 guiones de serie (entre paréntesis, en los 24 guiones KOREX).

| # | Pose | Usos | Momento del guion |
|---|---|---|---|
| 1 | `decidido` | 17 (36) | La regla o la orden: «Con eso activado, la tarjeta simplemente se rechaza si no hay fondos» (piloto) |
| 2 | `confundido` | 13 (38) | La situación que no cuadra: «Traes cinco dólares en la cuenta, y compras un café de seis» (piloto) |
| 3 | `orgulloso` | 10 (17) | El que se cree a salvo, o el banco satisfecho: «El banco te lo deja pasar» (piloto) |
| 4 | `estafado` | 8 (26) | El golpe: «Uno pide una tarjeta y le dicen que no» |
| 5 | `grito` | 4 (14) | El gancho o la alarma: «Te negaron la tarjeta» |
| 6 | `explicando` | 3 (32) | El giro explicado: «Y aquí está el secreto que nadie te explica…» |
| 7 | `codicia` | 3 (11) | El impulso de gastar: «Uno ve algo, le gusta, y lo compra en el momento» |
| 8 | `asombro` | 2 (9) | El dato que sorprende: «…y el desconocido es riesgo» |
| 9 | `triunfo` | 1 (12) | La abundancia o la victoria: «Autos nuevos, viajes a Miami…» |

El piloto (sobregiro) solo usa `confundido`, `orgulloso` y `decidido`, dos veces cada una: esas tres van primero.

## 2. Marcas de trazado (valen para las 9)

### 2.1 Qué se traza y qué no

- De cada lámina se traza **el cuerpo**: torso, brazos, guantes, piernas, pies y cola.
- **La cabeza de la lámina no se traza.** Sirve para colocar la del rig y luego se descarta. Por eso cada
  lámina debe traer la cabeza de frente y completa: sin ella no hay dónde anclar.
- Anclas que `kx_trazo` saca de cada lámina: punto de la barbilla, eje de la cabeza (línea barbilla–entre
  las orejas, que da su inclinación base) y altura de cabeza `H` (puntas de oreja a barbilla). La cabeza del
  rig se escala con `H` y se apoya en la barbilla.

### 2.2 Lámina contra la hoja madre (proporciones)

Medidas de la madre, de `traza.js` (alto total 1000 u). Se expresan contra `H` = 392 u para que valgan
también con el cuerpo agachado o estirado.

| Marca | Madre | En la lámina |
|---|---|---|
| Cabeza / alto total, de pie y erguido | 0,39 | solo en poses erguidas (1, 3, 6, 8) |
| Ancho de panza / `H` | 0,62 | todas |
| Grosor del brazo / `H` | 0,17 | todas, medido a mitad del brazo |
| Largo del brazo (hombro–muñeca) / `H` | 0,60 | todas, a lo largo de la curva |
| Largo del guante / `H` | 0,60 | guante abierto; el puño no se mide |
| Largo del pie / `H` | 0,61 | todas |
| Ancho máximo de la cola / `H` | 0,48 | todas |
| Anillos de la cola | alternos, oscuro en la punta | 5 a 7 visibles |

Tolerancia propuesta: ±8 %, a calibrar con `pointing_api.png` (decisión 4). Los anillos se cuentan, no se miden.

### 2.3 Trazo contra su lámina

Igual que la barra I2-3 actual, pero con la lámina como referencia: IoU ≥ 0,95, tinta en los dos sentidos
≥ 97 %, área de tinta 0,97–1,03. Lo exige el test por pose; sin eso la pose no entra en la biblioteca.

## 3. Prompt

`generar_lamina.py` arma el prompt como bloque común + párrafo de pose. La misión de generación sustituye el
bloque `ESTILO` por este y añade los 9 párrafos a `POSES`. En inglés: el modelo siguió bien el de `pointing`.

### 3.1 Bloque común (sustituye a `ESTILO`)

```
The attached image is the MODEL SHEET of the character "Tadeo", a cartoon raccoon.
Draw ONE new full-body pose of exactly this character.

Identity (copy from the model sheet, do not redesign): same head shape and size relative to the body,
same dark eye mask, same large round eyes with a white highlight, same small black nose, same chest tuft,
same white four-finger gloves with rolled cuffs, same dark feet, same striped tail with alternating rings.
Body proportions as on the sheet: big head (about 40% of his standing height), short legs, long thin
rubber-hose arms of constant thickness with no elbows or muscles, pear-shaped body with a belly patch
clearly lighter than the fur.

View: his BODY FACES THE VIEWER (front view, not three-quarter, not profile). His HEAD FACES THE VIEWER,
fully visible, not covered by a hand or an arm. Both feet and the whole tail are visible; the tail comes out
on the viewer's right side, as on the sheet.

Style: 1930s rubber-hose cartoon. Bold black ink outline with the same line weight as the model sheet.
Flat grayscale fills only: strictly black, white and gray. No color, no gradients, no hatching, no texture,
no cast shadow, no ground line.

Framing: the whole character inside the frame with empty margin on every side, centered, on a pure white
background. A single figure only: no text, no labels, no props, no extra poses, no head studies, no
turnaround, no borders.
```

### 3.2 Riesgo sin verificar

La prueba salió apaisada (1200 × 896). Para un cuerpo de pie conviene vertical. No sé si este modelo acepta
relación de aspecto por `generateContent`; la misión de generación lo comprueba en la doc antes de gastar.

## 4. Las 9 láminas

En cada una: postura · marcas propias (además de las de la sección 2) · párrafo de pose · aceptación visual.
«Izquierda» y «derecha» son siempre las del espectador.

### 4.1 `decidido`

- **Postura:** tronco inclinado un poco hacia delante, pies separados (más abiertos que en la madre). Puño
  izquierdo apoyado en la cadera, codo hacia fuera. Puño derecho cerrado y alzado al frente, a la altura del
  hombro. Cola levantada, sin tocar el suelo. Cabeza de frente, sin ladear.
- **Marcas propias:** separación entre tobillos ≈ 1,2 × la de la madre; el puño derecho queda entre el
  hombro y la mejilla, sin tapar la cara.
- **Pose:**
```
Pose "determined": wide firm stance, feet apart, leaning slightly forward. His left hand (viewer's left)
is a closed fist resting on his hip with the elbow out. His right arm is raised to the side with a closed
fist held up at shoulder height, clear of the face. Head upright, facing the viewer, brows down,
mouth closed and firm.
```
- **Aceptación:** en silueta negra se distinguen el puño alzado y el brazo en jarra; los dos puños son
  puños (ningún dedo extendido); el puño alzado no toca la cabeza.

### 4.2 `confundido`

- **Postura:** de pie, peso centrado, hombros encogidos hacia arriba. Los dos brazos doblados, antebrazos
  hacia fuera, guantes abiertos con las palmas hacia arriba a la altura del pecho. Cabeza ladeada unos 10°
  hacia la izquierda. Cola caída en su curva de reposo.
- **Marcas propias:** las dos palmas a la misma altura, entre la panza y el hombro, y fuera de la silueta
  del torso; inclinación del eje de la cabeza 8–12°.
- **Pose:**
```
Pose "confused shrug": standing, shoulders raised in a shrug. Both arms bent with the forearms out to the
sides, both hands open with the palms facing up at chest height, symmetrical. Head tilted about ten degrees
to one side, facing the viewer, one eyebrow raised, small puzzled mouth.
```
- **Aceptación:** se lee «no entiendo» sin ver la cara: dos palmas arriba y hombros subidos; los cuatro
  dedos de cada guante separados y contables.

### 4.3 `orgulloso`

- **Postura:** pecho fuera, tronco echado un poco hacia atrás, erguido. Los dos puños en las caderas, codos
  bien abiertos (brazos en jarra). Pies como en la madre. Cola alzada, punta hacia arriba. Cabeza de frente,
  barbilla alta.
- **Marcas propias:** los dos codos sobresalen del contorno del torso y dejan un hueco de papel visible
  entre brazo y cuerpo a cada lado; cabeza / alto total = 0,39.
- **Pose:**
```
Pose "smug, hands on hips": standing tall, chest out, leaning very slightly back. Both hands are closed
fists resting on his hips, both elbows pointing out, with a clear gap of white background between each arm
and the body. Tail raised. Head facing the viewer, chin up, half-closed eyes, wide closed smile.
```
- **Aceptación:** dos huecos blancos limpios entre brazos y torso; simetría izquierda-derecha; no se
  confunde con `codicia` (aquí las manos están en la cadera, no juntas).

### 4.4 `estafado`

- **Postura:** hundido: hombros caídos, tronco encogido, rodillas un poco flexionadas. Los dos brazos
  cuelgan lacios por delante de los muslos, guantes abiertos con los dedos hacia abajo. Cola caída, tocando
  el suelo. Cabeza baja, de frente.
- **Marcas propias:** las muñecas quedan por debajo de la cadera; el alto total baja a ≈ 0,93 del de la
  madre con la misma `H`; la barbilla más cerca del pecho que en la madre.
- **Pose:**
```
Pose "defeated": slumped, shoulders dropped, knees slightly bent, body sagging. Both arms hang limp
straight down in front of the thighs, hands open and loose with the fingers pointing down. Tail drooping
down to the floor. Head lowered but still facing the viewer, sad eyebrows, mouth turned down.
```
- **Aceptación:** la silueta es más baja y estrecha que la de `orgulloso`; los brazos caen rectos, sin
  curva de fuerza; la cabeza no tapa el pecho más de lo que marca la barbilla.

### 4.5 `grito`

- **Postura:** tronco inclinado hacia delante y estirado, pies firmes. Las dos manos abiertas a los lados de
  la boca haciendo bocina, codos hacia fuera. Cola erizada, alzada. Cabeza de frente.
- **Marcas propias:** las dos manos quedan **a los lados** de las mejillas, fuera del contorno de la cara:
  no deben tapar boca, nariz ni antifaz (la boca la abre el rig).
- **Pose:**
```
Pose "shouting": leaning forward, body stretched up. Both hands are open and cupped at the two sides of
his head like a megaphone, placed beside the cheeks and NOT in front of the face, elbows pointing out.
Tail raised and bristling. Head facing the viewer, mouth wide open shouting, brows down.
```
- **Aceptación:** al tapar la cabeza de la lámina con la del rig no queda ningún guante cortado por ella; los
  dos codos se abren en simetría.

### 4.6 `explicando`

- **Postura:** de pie, relajado. Brazo derecho alzado, doblado, con el guante abierto y la palma hacia
  arriba a la altura de la cabeza, presentando algo a su lado. Brazo izquierdo bajo, guante abierto junto a
  la cadera. Cola en su curva de reposo. Cabeza de frente.
- **Marcas propias:** la palma alzada queda por encima del hombro y fuera del contorno de la cabeza; cabeza
  / alto total = 0,39.
- **Pose:**
```
Pose "presenting": standing relaxed. His right arm (viewer's right) is raised and bent, with the open hand
held palm up at head height beside him, as if presenting something to his side. His left arm hangs low
with an open relaxed hand next to the hip. Head facing the viewer, friendly smile.
```
- **Aceptación:** la mano que presenta deja sitio libre a su lado (ahí va la pizarra); no señala con un
  dedo (eso es `senalando`); el brazo bajo no cruza la panza.

### 4.7 `codicia`

- **Postura:** encorvado hacia delante, cabeza hundida entre los hombros. Las dos manos juntas delante del
  pecho, frotándose, con los dedos entrelazados o una sobre otra. Codos pegados al cuerpo. Cola enroscada.
  Cabeza de frente, baja.
- **Marcas propias:** las dos manos se solapan sobre la panza, por debajo de la barbilla; **sin ningún
  objeto**: ni billetes ni monedas.
- **Pose:**
```
Pose "greedy, rubbing hands": hunched forward, head sunk between the shoulders. Both hands are together in
front of his chest, rubbing each other, one hand over the other, elbows close to the body. He holds
NOTHING: no money, no coins, no objects. Tail curled. Head facing the viewer and lowered, half-closed
eyes, wide sly grin.
```
- **Aceptación:** las manos vacías; se distingue de `orgulloso` en silueta (bulto de manos al centro, sin
  huecos laterales); las manos no suben a tapar la boca.

### 4.8 `asombro`

- **Postura:** echado hacia atrás, estirado, casi de puntillas. Los dos brazos abiertos a los lados a media
  altura, guantes abiertos con los dedos muy separados. Cola alzada y recta. Cabeza de frente.
- **Marcas propias:** las dos manos a la altura de los hombros, lejos del cuerpo (más separadas que en
  `confundido`) y con las palmas hacia el espectador; cabeza / alto total = 0,39.
- **Pose:**
```
Pose "astonished": leaning back, body stretched tall. Both arms flung out to the sides at shoulder height,
both hands wide open with the palms toward the viewer and the fingers spread far apart. Tail raised
straight. Head facing the viewer, eyes very wide, eyebrows high, small round open mouth.
```
- **Aceptación:** no se confunde con `confundido`: aquí las palmas miran al frente y los brazos van
  estirados, no encogidos; los dedos de los dos guantes, contables.

### 4.9 `triunfo`

- **Postura:** salto: los dos pies despegados del suelo, rodillas algo flexionadas, cuerpo estirado. Los
  dos brazos arriba con los puños cerrados por encima de la cabeza. Cola alzada, con rizo. Cabeza de frente.
- **Marcas propias:** los dos puños quedan por encima de las puntas de las orejas y a los lados, sin
  cruzarse por delante de ellas; los pies no comparten línea de suelo.
- **Pose:**
```
Pose "victory jump": jumping in the air, both feet off the ground, knees slightly bent, body stretched.
Both arms raised straight up with closed fists above the head, one on each side, not covering the ears.
Tail raised with a curl. Head facing the viewer, eyes closed in a big open laughing smile.
```
- **Aceptación:** es la silueta más alta de las 9; los puños no tapan las orejas (las orejas las mueve el
  rig); no hay línea de suelo ni sombra bajo los pies.

## 5. Aceptación común (antes de trazar)

Una lámina se descarta y se regenera si falla cualquiera de estas:

1. Hay más de una figura, texto, un objeto o un fondo que no sea blanco.
2. El cuerpo o la cabeza están en 3/4 o de perfil.
3. Algo tapa la cabeza, o falta un pie, una mano o la cola.
4. Aparece color, degradado o sombra proyectada.
5. Un guante no tiene cuatro dedos, o los brazos tienen codo marcado o músculo.
6. Una proporción de la sección 2.2 sale de la tolerancia.

Presupuesto orientativo: a 0,036 USD por imagen y hasta 4 intentos por pose, unos 1,3 USD como máximo.
Los 4 intentos son una estimación mía, no un dato.
