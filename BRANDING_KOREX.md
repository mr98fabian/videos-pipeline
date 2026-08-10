# Branding de KOREX — La Resistencia Financiera

Canal de **finanzas satíricas en español** (`@KoreXFS`). Protagonista: **Tadeo**,
un mapache. Formato Shorts verticales; el largo llegará después.

**Para qué existe este documento:** que un personaje nuevo, un fondo nuevo o un
guion nuevo salgan siempre con la misma calidad y el mismo mundo, sin depender de
que alguien se acuerde. Aquí está el **porqué**; las cadenas exactas que se le
mandan al modelo viven en el **código**, que es lo único que garantiza que se
apliquen de verdad.

| Qué | Dónde vive la cadena exacta |
|---|---|
| Estilo de personajes | `kx_cast.CAST_STYLE` |
| Bloqueo de identidad de Tadeo | `kx_cast.CHARACTER_LOCK` |
| Reglas de encuadre de la lámina | `kx_cast._CAST_RULES` |
| Vocabulario de poses | `kx_cast.POSES` |
| Estilo de fondos | `kx_assets.SET_STYLE` |
| Reglas del escenario vacío | `kx_assets._SET_RULES` |
| Paleta, tipografía, transiciones | `motion_graphics/src/korex/KorexVideo.jsx` |
| Voz del narrador | `tools/qwen_tts/synth.py` → `KOREX_VOICE` |

**Si este documento y el código se contradicen, manda el código** — y corrige el
documento. Nunca al revés.

---

## 1. El estilo visual (la regla que más caro sale)

**Dibujo animado de los años 30 estilo *rubber hose* (Disney/Fleischer temprano),
blanco y negro, ENTINTADO A MANO.** Trazo de pincel con grosor variable,
sombreado de lápiz con tramas suaves, textura de papel envejecido y grano de
película. Guantes blancos de cuatro dedos.

**Prohibido y por escrito en el prompt:** `NOT flat vector art`, `NOT clean
digital illustration`, `NOT modern cartoon style`.

> **Por qué está en negativo:** `CAST_STYLE` y `SET_STYLE` empezaban con *"Flat
> vector"* y producían un mapache de ilustración vectorial moderna y limpia.
> Rechazado el 3 ago 2026: *"se ve de otro canal"*. La referencia aprobada es la
> prueba del búho leyendo el periódico — línea entintada, sombreado de lápiz,
> papel viejo. Si alguien vuelve a meter *flat* o *vector* en esas constantes,
> vuelve el look rechazado.

### Cómo pedir un personaje nuevo

1. Escribir la pose **en positivo**, describiendo la postura completa.
2. **Las negaciones no construyen una pose.** Medido el 3 ago: a base de *"sin
   dinero, sin gritar, nada en las manos"*, `decidido` y `triunfo` convergieron a
   la misma pose neutra de enfado. Si dos poses se parecen, hay que diferenciarlas
   describiendo **qué hace cada una**, no qué no hace.
3. **Nunca mezclar encuadres.** `grito` pedía *"extreme close-up"* mientras la
   regla global imponía `FULL BODY`: el modelo obedeció a las dos y salió un
   cabezón con cuerpo diminuto. El encuadre lo decide el motor al componer, no el
   prompt de la lámina.
4. Siempre con la lámina canónica como referencia y el `CHARACTER_LOCK` pegado
   **literal**, palabra por palabra. Reformularlo con otras palabras es lo que
   hace derivar el diseño.

### Cómo pedir un fondo nuevo

Escenario **vacío**: sin personajes, sin texto, sin logos. El **centro y el
centro-bajo del cuadro quedan despejados** porque ahí se compone al personaje.
Vertical 9:16, línea de suelo a unos tres cuartos de la altura.

---

## 2. Reparto

| Personaje | Papel | Acento de color |
|---|---|---|
| **Tadeo** | Mapache protagonista. El que se equivoca y aprende. El narrador se burla de él con cariño. | `neutral` — rojo teja |
| **Bruja del Banco** | Villana principal. Traje de raya diplomática, sombrero picudo, libro de contabilidad, pluma. Cobra los intereses **antes** de tocar la deuda. | `witch` — verde enfermizo |
| **Mapache Millonario** | Villano de la riqueza: chistera de seda, esmoquin, bastón, saco de monedas. | `tycoon` — dorado |

**Tadeo no habla.** Hay un solo narrador en off que se dirige a él por su nombre
y describe sus reacciones. Esa fue una decisión explícita: el diálogo a dos voces
exigiría alternar TTS y alinear tiempos, y el formato no lo necesita.

**Consistencia por construcción, no por prompt:** cada pose se genera **una vez
en la vida**, se aprueba a ojo y se guarda en `assets/kx_cast/<personaje>/`. A
partir de ahí todos los vídeos reusan el mismo PNG, así que el personaje es
idéntico por definición. Es como funciona la animación de recortes de verdad
(South Park), no un atajo. Las poses rechazadas se apartan en `_rechazadas/`, no
se borran.

---

## 3. Paleta

Cerrada a tres tonos más **un** acento por escena — el del villano que aparece.
Nunca dos acentos en el mismo cuadro.

| Uso | Hex |
|---|---|
| Tinta / línea | `#141414` |
| Base del set (crema) | `#EFE7D6` |
| Crema profunda (suelo) | `#DBCEB5` |
| Acento Bruja | `#8FBF4D` |
| Acento Millonario | `#D4A22B` |
| Acento neutro (Tadeo solo) | `#C7472F` |

El **blanco y negro se fuerza en el motor** (`grayscale(1)`), no se le pide al
modelo de imagen: por mucho que el prompt diga *black and white*, devuelve color
—el primer vídeo salió entero marrón—. Así el único color del cuadro es el
acento.

---

## 4. Tipografía y captions

Arial Black 900, mayúsculas. **Ancladas siempre a la misma altura** (`y=1500`),
sin rebotar por la pantalla. La palabra activa va en el acento de la escena; el
resto en tinta, con contorno crema para que se lea sobre el fondo claro.

Las primeras ~7 palabras (la promesa) se pintan **enteras desde el frame 0**: la
decisión de quedarse se toma antes del segundo 1, y una palabra suelta no es una
promesa que se pueda leer.

> Bug real que no debe repetirse: las captions estaban dentro de un `<Sequence>`
> por escena. Como `Sequence` reinicia el frame local a 0 y las palabras traen
> timestamps globales, cada escena repintaba la primera palabra del vídeo — se
> veía "TADEO" sobre la Bruja. Van en **una sola instancia global**.

---

## 5. Movimiento

- **Set fijo** con parallax por capas. No un fondo nuevo a sangre cada 4 s: eso
  es lo que hace que un vídeo parezca "imágenes de IA cosidas".
- **Push-in lento** de cámara. Nada de punch-zooms aleatorios.
- **Squash-stretch** del personaje atado a las sílabas del TTS: habla sin rig.
- Balanceo constante: nunca una pose totalmente quieta.
- En **imagen→vídeo** (si algún día se reactiva) la cámara va **bloqueada**: el
  warp y el morphing entran por darle libertad de cámara al modelo. Hoy la
  animación de Flow está **apagada** (~100 créditos por clip, minutos por escena
  y fallos intermitentes); el movimiento lo pone el motor, gratis.

---

## 6. Transiciones y sonido

Tres cortes **duros** rotando, nunca fundidos lentos, cada uno con su propio
golpe de foley:

| Transición | Sonido |
|---|---|
| Iris (cierra y abre) | `whoosh` |
| Barrido de tinta | `paper` |
| Flash-cut blanco | `impact` |

Un solo sonido repetido en todos los cortes se lee como tic mecánico — por eso
cada transición suena distinta.

Música a `0.06` con `sidechaincompress` contra la voz: se aparta sola cuando
Tadeo habla, en vez de taparlo.

---

## 7. Voz del narrador

Fijada el 3 ago 2026 tras un casting de 21 muestras. Motor **Qwen3-TTS
VoiceDesign**, local y gratis; la cadena exacta es `KOREX_VOICE` y la muestra
congelada está en `assets/voice_refs/korex_narrador.wav`.

**Carácter:** timbre rico y aterciopelado, grave y cálido; mordaz y burlón;
ironía elegante de quien se sabe superior; nunca grita.

**Acento mexicano, y hay que forzarlo:** pedir *"español neutro"* devolvía
castellano peninsular una y otra vez. Solo se corrigió **nombrando México** y
**prohibiendo por su nombre** los rasgos ibéricos (ceceo, *vosotros*, entonación
madrileña). Si se reescribe el instruct, esa parte se conserva.

**La ñ y las tildes se escriben.** Qwen las pronuncia bien. Quitarlas convierte
`años` en `anos`, que es otra palabra y el TTS la lee tal cual — pasó en el
primer guion de Tadeo. `_check_script_lint` lo avisa en cada corrida vía
`lint_enie.py`. Ver la skill `guion-para-voz`.

---

## 8. Tono narrativo

- **Segunda persona**, tipo guía de supervivencia: *"Sobreviviste al mes…"*. El
  narrador le habla al espectador y se burla de Tadeo.
- **Ácido y callejero, no documental.** Referencia de mecanismo: Los Ecomonos
  explica economía con una alegoría animal sostenida; el registro de KOREX es más
  burlón y personal.
- **Explicar como a un niño**, con una analogía cotidiana (el frasco de dulces),
  no con jerga bancaria.
- **Inserts de infografía** (estilo Vox) solo como corte puntual en el dato duro:
  interrumpen la sátira y dan credibilidad. Si se vuelven el lenguaje principal,
  matan la identidad vintage.
- **El guion cierra en bucle**: la última frase enlaza con la primera para que un
  reinicio no tenga costura.
- Sin muertes ni funerales por defecto: el drama sale de que algo pequeño escale.

---

## 9. Antes de dar por bueno un vídeo

1. `py lint_enie.py scripts/<guion>.json` — palabras mutiladas sin ñ.
2. `py korex_qa.py output/<carpeta>` — escenas faltantes, duplicadas o que no
   casan con su clip.
3. Mirar la **hoja de contacto**, no los archivos sueltos: revisar 24 imágenes a
   mano falla, revisar una sola imagen no.
4. Escuchar el audio **entero**. Estos fallos son silenciosos: el archivo se
   genera bien y suena mal.
