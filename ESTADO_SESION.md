# Estado de sesión — dónde quedamos

**Para qué existe:** Fabián trabaja con dos sesiones de Claude en paralelo (para
estirar tokens). Este archivo es el traspaso entre ellas: lo último que se hizo,
lo que quedó a medias, y qué sigue. Se lee al empezar y se actualiza al terminar.

**Reglas de uso:**
- Solo el estado ACTUAL. Lo histórico va a `HISTORIAL_MEJORAS.md`, no aquí.
- Sobrescribir, no acumular. Si crece más de una pantalla, sobra texto.
- **Riesgo real de las dos sesiones en paralelo:** si ambas editan el mismo
  archivo, la segunda pisa a la primera sin avisar. Antes de tocar código que
  la otra sesión pudo haber cambiado, `git diff` primero.

---

## Actualizado: 10 ago 2026 — Kimi implementó los 6 hallazgos del video ganador

**Esto lo hizo la sesión de Kimi.** Contexto: el Short "Cómo salir de deudas y
dejar de 'pelar cable' este 2026 🔥" (`shorts/wjBlLC3whJE`) rindió increíble;
diagnóstico: título/tema buscable + slang local, no la transición cómic
(retención~vistas = -0.127 en nuestros datos). Fórmula guardada en
`SERIES_PELAR_CABLE.md` + memoria de Kimi.

- **`pipeline.py`**: (1) frame-miniatura horneado en los últimos 0.2s
  (`append_thumb_frame`, default ON, `--no-thumb-frame` para salirse) — elegir
  ese frame con el selector de la app móvil al publicar. (2) Check anti-slop
  `_check_antislop_similarity` en la batería de lints: avisa si el guion
  comparte ≥10% de shingles de 5 palabras con los últimos 10 renders. **Ya se
  estrenó:** detectó que el video de quincena de hoy (sesión de Claude) y el
  `korex-quincena.json` de Kimi eran el mismo guion — Kimi borró el duplicado y
  escribió el episodio 2 en su lugar (`scripts/korex-tarjeta-minimo.json`).
- **`performance_report.py`**: columnas nuevas `shares_per_1000_views`,
  `subs_per_1000_views`, `target_emotion`, `twist_phrase` (de `guion.json`) +
  secciones de insights por shares y por emoción.
- **`feedback_digest.py`** (nuevo): loop datos→prompt del ROADMAP §2.7. Leer
  `performance_report.csv` y escribir `FEEDBACK_DIGEST.md` para la revisión
  mensual del prompt.
- **`mine_topics.py`** (nuevo): minería de temas. OJO: Reddit 403-ea esta red
  (verificado hoy); la fuente que funciona es el autocompletado de YouTube
  (`--no-reddit` para saltar Reddit). 104 candidatos en `topics_mined.txt`.
- **`SERIES_PELAR_CABLE.md`**: plan de 5 episodios con la fórmula ganadora.
  Ep. 1 = el quincena ya renderizado hoy (sin publicar aún); ep. 2 listo en
  `scripts/korex-tarjeta-minimo.json`.
- **Pendiente manual**: token de Analytics caducado — correr
  `py performance_report.py` una vez y el navegador re-autoriza solo; después
  `py feedback_digest.py` para llenar las secciones 1-2 del digest.

---

## Actualizado: 12 ago 2026 — KOREX largo, referentes medidos y el idioma de Tadeo

### Lo que está BLOQUEADO ahora mismo (leer primero)

`output/2026-08-12-dos-sueldos/` tiene **la voz lista (8m47s, Qwen clonado a 145
wpm)** y **47 de 52 imágenes, pero TODAS en 9:16** — el vídeo es largo y las
necesita en **16:9**.

Dos cosas se cruzaron:
1. `_shared_session` aplicaba el aspecto **solo al crear** la sesión y luego lo
   ignoraba; una sesión abierta antes para Shorts imponía el vertical. **Ya está
   arreglado**, pero sin verificar.
2. Flow volvió a negarse en seco (una prueba con "una silla en un cuarto vacío"
   falló sin generar). Hasta que se recupere no se puede comprobar el arreglo.

**Qué hacer al retomar:**
```powershell
py qa_personaje.py output/2026-08-12-dos-sueldos/storyboard --aspecto 16:9
FLOW_IMAGE_MODEL="Nano Banana Pro" py <scratchpad>/gen_largo.py   # rondas con espera
```
Si siguen saliendo verticales con Flow ya funcionando, el fallo es la pestaña de
aspecto: correr `py flow_automation.py --inspect` y revalidar el selector.

### Lo hecho hoy (todo commiteado)

- **[[ESTUDIO_REFERENTES]]** — Los Ecomonos (429k subs, mediana **245.834**
  vistas, 92% de títulos con la misma firma, solo 4% preguntas) y Zenn (mediana
  31k con un vídeo de 7,85M). Medido con la API y sus transcripciones.
- **Los títulos-pregunta fueron un error mío** y está documentado: el ganador de
  KOREX (9.668 vistas, 85,4%) es una promesa práctica. Los guiones ya llevan la
  firma nueva; **los 5 vídeos subidos siguen con el título viejo**.
- **[[IDIOMA_KOREX]]** — diccionario mapache y el aquelarre (todo el que cobra
  es una bruja). **[[STORYBOARD_KOREX]]** — 絵コンテ, 6-8s por plano, una frase
  un plano. **[[INDEX]]** — los 48 documentos enlazados y la tabla de conflictos.
- **Curva de retención real del ganador**: 97,3% en el segundo 6 y **64,2% en el
  9**. Ahí está el escalón, y el `relativeRetentionPerformance` arranca en 0,13:
  ese vídeo ganó por el título, no por el gancho.
- **PiAPI/Seedance cableado** (`piapi_animate.py`) y bajado a `seedance-2-mini`
  tras medir que el clip costó ~$2. Solo se anima la apertura.
- **Skill `qa-personaje`** + `qa_personaje.py`: comprueba formato/color/lámina/
  repetidas y arma hojas de 6 a 340 px para mirar el personaje.
- Música: fuera el sorteo, entra ragtime **CC0** (etiqueta `korex30s`).

### Pendiente, por orden

1. Desbloquear el 16:9 y completar las 52 imágenes.
2. Revisar imagen a imagen con `qa-personaje` hasta que **todas** sean Tadeo.
3. Montar el largo y **operar el segundo 6-9**, que es donde se cae el canal.
4. Sacar las curvas de los otros 5 vídeos: ver si el escalón se repite.

---

## Actualizado: 9 ago 2026 — Regla 11 (investigaciones multiidioma) aplicada, también a KOREX

**Esto lo hizo la sesión de Kimi, no la de Claude.** Contexto: Fabián pidió
investigaciones profundas multiidioma (EN/ES/ZH/JA/KO) y aplicarlas al pipeline.
Resultado: **9 documentos en la raíz** — `INVESTIGACION_MULTIIDIOMA_2026.md`
(síntesis madre) + 8 temáticos: `PSICOLOGIA_COMPARTIR.md`,
`ANALISIS_OUTLIERS_PROPIOS.md` (**nuestros datos: sweet spot 80-120 palabras,
mediana de shares = 0 en 51 videos**), `SOUND_DESIGN_RETENCION.md`,
`VOZ_TTS_EMOCIONAL.md`, `MINIATURAS_SHORTS_2026.md`,
`HUMOR_LOCALIZACION_LATAM.md`, `SERIES_LORE_PERSONAJES.md`,
`COMENTARIOS_ENGAGEMENT.md`. Cada uno termina con sección de aplicación al
pipeline. **Regla del corpus: nuestros datos medidos ganan sobre benchmarks
externos.**

### Cambios en código (compilan, ruff limpio en lo tocado, probados en smoke test)

- **`SCRIPT_SCHEMA` exige 3 campos nuevos**: `target_emotion`
  (awe/surprise/humor/outrage), `twist_phrase` (4-8 palabras literales del giro)
  y `comment_cta` (pregunta de elección para comentario fijado, NUNCA hablada).
- **Regla 11 en `SCRIPT_PROMPT`** (share engineering: emoción de alta
  activación, giro al 30-60%, dato reenarrable en ≤15 palabras, humor que
  golpea hacia arriba). Ojo: el prompt es contexto HiddenFacts; KOREX usa
  guiones a mano, así que ↓
- **Para KOREX: los guiones `scripts/korex-*.json` nuevos hay que ESCRIBIRLOS ya
  con los 3 campos.** El lint `_check_giro_posicion` corre en la rama
  `--script-file` (antes del split de motores) y avisa si faltan o si el giro
  cae fuera de la banda 25-75% — es el mecanismo de enforcement para guiones a
  mano.
- **Ducking/loudnorm aplicado en los DOS motores**: `assemble()` (clásico) y
  **`korex_engine.py`** — el motor KOREX tenía su propia mezcla con los
  parámetros viejos (volume 0.06, attack=20:release=400) y SIN loudnorm. Ahora
  ambos: volume 0.09, attack=50/release=300, loudnorm I=-14/TP=-1.0
  (SOUND_DESIGN_RETENCION.md).
- **`guion.json` se guarda en cada carpeta output** (todas las rutas, incluida
  `--korex`); `post_question_comment.py` lee `comment_cta` de ahí (fallback:
  parsear la descripción como antes).

### KOREX cambió de motor (9 ago, noche) — LEER ANTES DE TOCAR NADA DE KOREX

**El motor de recortes/parallax es de HiddenFacts y SOLO de HiddenFacts.**
Decisión de Fabián, explícita. KOREX se monta por el camino **clásico**: las
imágenes de Flow a pantalla completa. O sea, **sin `--korex`**:

```powershell
py pipeline.py --script-file scripts/korex-tulipanes.json --flow --voice qw_korex
```

Tres cosas más que se arreglaron con él y que valen para todo lo que venga:

1. **Flow iba desincronizado y no se veía.** `count=4` deja tres tiles sueltos
   por prompt; la escena siguiente los tomaba por suyos. Desde la escena 6, cada
   imagen era la del prompt anterior. Arreglado en `flow_automation` con un
   `_consumed` de sesión. **Mirar siempre la hoja de contacto contra el guion**:
   el fallo es silencioso y el vídeo parece correcto.
2. **Tadeo tenía cuatro diseños.** Estudio completo en
   `PERSONAJE_MODEL_SHEET.md`. Ya hay **hoja madre** (turnaround + expresiones)
   en `assets/characters/tadeo/default_model_sheet.png`, y `CHARACTER_LOCK` es
   ahora especificación contable. Las láminas fuera de modelo (`grito_1..5`,
   la hoja vieja a boceto) están en `_rechazadas/`.
3. **La voz oficial no se estaba usando.** Qwen existía en `tools/qwen_tts` pero
   el pipeline no sabía enrutar ahí: todos los Tadeo anteriores salieron con
   Chatterbox. Ahora `--voice qw_korex`.

Y tres cosas mas que salieron de oirlo montado:

4. **La voz cambiaba a mitad del video.** `generate_voice_design` DISEÑA un
   timbre nuevo en CADA llamada y el guion va troceado: cada trozo era otro
   narrador. Ahora se **clona** la muestra congelada del casting
   (`assets/voice_refs/korex_narrador.wav`, modelo `Qwen3-TTS-...-Base` + ICL con
   `korex_narrador.txt`). El `instruct` fija el caracter, no la identidad.
5. **La musica sonaba alta y el numero no era el problema.** Qwen entrega mas
   bajo que edge-tts y el `loudnorm` final normaliza la MEZCLA, asi que subia el
   fondo para compensar. La voz se normaliza ahora ANTES de mezclar (-16 LUFS) y
   `MUSIC_VOLUME` bajo a 0.05. Con eso el numero vale igual con cualquier TTS.
6. **12 planos en 82s = 6,8s cada uno, un pase de diapositivas.** El guion pasa a
   **24 beats** (frases cortas) -> 3,2s por plano. Las 12 imagenes buenas se
   recolocaron y solo se generaron las 12 intercaladas: regenerar todo cuesta una
   hora de Flow y no hacia falta.

Salida viva: `output/2026-08-09-la-flor-que-costaba-mas-que-una-casa-y-e/video.mp4`,
**76,8s, 24 escenas**. **Nada subido a YouTube.**

### Pendiente (es el siguiente paso)

1. **Publicar el tulipanes como `unlisted`** y mirar shares/comentarios: es lo
   único que valida la regla 11. Hoy es oficio, no dato.
2. **Flow sigue escribiendo letreros garabateados** ("NOTARIO", "AUCTION HALL")
   cuando el `search_term` nombra un objeto con texto. Se quita añadiendo
   "sin texto ni letras" al término, como ya llevan los 12 nuevos.
3. `korex_qa.py` está escrito para el motor viejo (avisa de color en escenas cuya
   imagen ya no se descarta). Hay que reapuntarlo al camino clásico o retirarlo.

---

## Actualizado: 4 ago 2026 — KOREX (línea activa)

Todo el día fue **KOREX** (finanzas satíricas, Tadeo el mapache). Nada subido a
YouTube. Rama `claude/sticker-library-ai-vxifx9`, sin commitear.

### Google Flow conectado — CERRADO (4 ago, tarde)

Las dos capacidades que faltaban están escritas y **probadas contra Flow real**,
no solo compiladas:

```powershell
py pipeline.py --script-file scripts/korex-interbolsa.json --flow --korex
py pipeline.py ... --flow --flow-animate        # + anima cada escena (8s, lento)
py flow_automation.py --inspect                 # revalidar selectores si Google cambia el build
```

- **Referencia de personaje**: un `character_term` con forma `tadeo/<pose>` ahora
  resuelve la lámina de `assets/kx_cast/` y la manda como ingrediente del prompt.
  Verificado en el vídeo de abajo: Tadeo mantiene el diseño entre escenas **y**
  actúa dentro del plano, en vez de ir troquelado encima.
- **Animación**: `animate()` / `--flow-animate` devuelve un mp4 de 8s a partir de
  la imagen de la escena. Probado sobre `clips/nb_1.png`: mismo plano, mismo
  personaje, con movimiento real.

**Lo que costó tres vueltas y no hay que volver a descubrir:** el
`input[type=file]` oculto **solo sube el archivo a la biblioteca**; el modelo lo
ignora. La referencia solo cuenta si se engancha por el selector `+` →
*Agregar a la instrucción*. El fallo es silencioso: la llamada devuelve OK y baja
un archivo válido, pero el resultado sale de texto puro (el primer "vídeo de
Tadeo" fue un mapache fotorrealista en un bosque). Todo el detalle en la entrada
del 4 ago de `HISTORIAL_MEJORAS.md`.

**Salida de la corrida real**:
`output/2026-08-04-la-firma-mas-grande-de-colombia-se-cayo-/video.mp4`, 79,3s,
1080x1920. **Nada subido a YouTube.**

### LO QUE ESTÁ ROTO AHORA (4 ago, tarde) — leer antes de tocar Flow

**Flow rechaza generaciones de forma intermitente y no conseguí aislar por qué.**
Gasté muchas vueltas en esto; lo que sigue es lo que está *medido* y lo que está
*descartado*, para no repetir el camino.

Medido y arreglado:
- **Referencia con canal alfa → rechazo.** Misma escena, misma pose, única
  variable el alfa: RGBA falla, aplanada sobre blanco pasa. Las 33 láminas de
  `assets/kx_cast/tadeo/` están recortadas. Arreglado en
  `flow_automation._flatten_alpha` (caché en `assets/cache/flow_refs/`).
- **Mi propio detector de rechazo tumbó una corrida entera.** El regex llevaba
  `error`/`blocked` y hacía match con el blob JSON de Next.js que Flow incrusta
  en la página: 12/12 escenas a gradiente por rechazos inexistentes. Ahora sólo
  busca el texto exacto del tile fallido y sólo dentro de los tiles.

Descartado con datos, no por intuición:
- **No es la velocidad.** Con 60s de enfriamiento entre envíos falla igual.
- **No es cuota.** El diálogo de la cuenta marca **846 créditos**.
- **No es la IP de Disney en el prompt** (el estilo nombra Mickey/Oswald): el A/B
  con estilo limpio falla y pasa en la misma proporción.
- **No es el bloque `CHARACTER_LOCK`** ni la segunda referencia.
- **Recargar el proyecto entre escenas lo empeora** (de 9/12 a 0/12). Ese camino
  ya está probado y revertido; no volver a intentarlo.

Sí bloqueada de verdad: la escena 11 (`cara de pánico gritando directo a cámara,
contacto visual intenso`) falló 6/6. Usa la imagen de la escena 0, que lleva el
**mismo `search_term`** por la regla del bucle — eso es correcto por diseño, no
un parche.

Otro fallo distinto, sin resolver: a veces Flow devuelve una imagen que **no
corresponde al prompt** (`nb_1` salió un primer plano de pánico en vez del piso
de bolsa). Por eso hay que mirar cada imagen antes de montar.

### Dónde retomar

Carpeta viva: `output/2026-08-04-la-firma-mas-grande-de-colombia-se-cayo--8`,
con **10 de 12** escenas. Faltan `nb_1` y `nb_5`.

```powershell
py korex_fill.py output/2026-08-04-la-firma-mas-grande-de-colombia-se-cayo--8
py korex_engine.py output/2026-08-04-la-firma-mas-grande-de-colombia-se-cayo--8
py korex_animate.py output/2026-08-04-la-firma-mas-grande-de-colombia-se-cayo--8 --voice cb_es
```

`korex_fill.py` insiste por rondas sólo en las que faltan (converger por fuera
funciona mejor que reintentar más fuerte dentro de la corrida).
`korex_animate.py` anima cada escena y monta con voz, música con *ducking* y
SFX; **aborta si falta alguna imagen** en vez de montar con huecos.

Sin decidir: si el `--flow-animate` completo (12 escenas × varios minutos) vale
la espera, y si el movimiento real retiene mejor que el Ken Burns. Hoy es
oficio, no dato.

### Terminado hoy

- **Chatterbox cableado** en `pipeline.py` (prefijo `cb_es`/`cb_en`). Antes todo
  guion en español caía en edge-tts y sonaba a robot: Chatterbox estaba en
  `tools/` pero solo lo llamaba `viral_lab.py`.
- **Voz elegida de oído**: timbre `es-MX-JorgeNeural` en `assets/voice_refs/es.wav`,
  `exaggeration 0.45` + `cfg 0.3`. El acento viaja con el timbre, por eso Kokoro
  español (que es de España) no servía.
- **`_snap_to_script()`**: los subtítulos salían de la transcripción de whisper y
  cambiaban palabras del guion. Ahora whisper solo aporta el timing.
- **Gemini eliminado del repo** por pedido de Fabián (Nano Banana, Lyria, Veo,
  `--flow`, `gemini_usage.json`). Sobrevive en `viral_lab.py` para análisis de
  video, con caída automática a `--engine claude`.
- **`comfy_client.py`**: ComfyUI local + FLUX.1-schnell (Apache-2.0, uso comercial
  OK) como generador. Flag `--comfy`. Pesos bajados, 12,3GB.
- **`kx_assets.py`** (fondos) y **`kx_cast.py`** (poses): bibliotecas cacheadas por
  clave semántica, generadas una vez en la vida y compartidas entre videos.
  `korex_engine` las consulta antes de generar nada.
- **Biblioteca de Tadeo sembrada**: 33 dibujos de Flow en 10 poses con variantes,
  recortados con alfa, en `assets/kx_cast/tadeo/`.

### Ojo con esto

- **No hay generador de imágenes de pago.** Gemini borrado y PiAPI/Seedream da
  `insufficient credits`. Quedan ComfyUI local (`--comfy`) y Flow (`--flow`).
- **FLUX schnell no acepta imagen de referencia** → no da consistencia de
  personaje. Para fondos sin personaje va perfecto. Flow sí la acepta, y por eso
  es ahora el camino por defecto de KOREX.
- `scripts/korex-interbolsa.json`: sus `character_terms` ya son claves
  `tadeo/<pose>` (9 de 12 resuelven a lámina de biblioteca; `El Millonario` sigue
  siendo descripción porque no tiene poses dibujadas todavía).
- Los tres renders fallidos de ese video fueron por falta de imágenes, no por el
  motor. La voz está cacheada por hash: regenerar no la vuelve a sintetizar.
- El efecto "TV vieja" que pidió Fabián (ver
  `Downloads/_Slow_and_controlled_animation_of_202608040501.mp4`) es polvo, rayas
  verticales y **esquinas redondeadas con marco** encima de lo que ya hace
  `FilmGrade`. Sin decidir si se sube el grade del motor o lo genera Flow.

---

## Línea anterior: 1 ago 2026 — Mind Checkpoint (en pausa)

Todo el trabajo del día ha sido en **Mind Checkpoint** (`@MindCheckpoint`, ~5
subs): historias inventadas estilo Reddit, faceless, narración sobre **gameplay
CC-BY a pantalla completa 9:16**. El formato split (historia arriba / gameplay
abajo) se descartó: ahora es gameplay a pantalla completa y ya está.

**Nada se ha subido a YouTube.** Todos los vídeos siguen en local.

### Terminado

`output/2026-08-01-visitor-log/video.mp4` — 84,6s, 1080x1920, SAR 1:1. Historia
del registro de visitas del geriátrico. Es la **v2**; la v1 se borró. Verificado
en frames: el contador `READ 40/40` se completa exactamente sobre la última
palabra hablada ("now").

### Los tres cambios de criterio de hoy (ya en código)

**1. Regla 9 reescrita — el gancho se AFIRMA, no se pregunta.** Antes obligaba a
abrir con "Why" en guion/título/hook_card. Retirada. Ahora: hecho imposible
afirmado en seco, con un dato concreto dentro y un segundo tiempo plegado, y
**prohibido resolverlo dentro del propio gancho**. Causa: el guion de Minecraft
abría con *"…forty times **because** he could not remember"* — esa subordinada
cierra el misterio en el segundo 3, justo donde la retención medida se caía.
`_check_why_opening` → **`_check_open_hook`**.

**2. Regla 9f nueva — escalera de premios.** Lo más importante del día. Sale de
la transcripción vía vidIQ de un Short de **1,6M vistas en un canal de 5.320
subs** (`Story Mode On`, vídeo `kmiZss057XE`), el comparable verificado más
cercano a nuestra situación. Su fórmula: abre **en escena** con acción física y
diálogo (la madre le tira el bol de cereales de las manos), injusticia en el
segundo 4 para que el espectador tome bando, escalada con quince cifras
concretas, humillación pública ante la familia, y la revelación es un
**documento** (la app del banco con $15.000). Cierre frío y corto.
La regla exige: **(a)** cold open sobre la consecuencia y luego rebobinar, para
que quien vea 3 segundos ya tenga una promesa y queden dos bucles abiertos;
**(b)** ≥4 premios a intervalos **irregulares**, ninguno separado más de ~20s, el
mayor al final — un ritmo regular le dice al cerebro cuándo puede irse. Se
declara en el JSON como `payoffs` y lo verifica **`_check_payoff_spacing()`**.
Corolario: **el contador debe llenarse TARDE**, cerca del premio final
(goal-gradient). En la v1 se llenaba al 45% y la segunda mitad no daba nada.

**3. Keywords en rojo.** Con `SUB_CHUNK_WORDS = 1` sólo hay una palabra en
pantalla y siempre era la activa, así que el amarillo era el 100% del texto y
había dejado de ser jerarquía. Ahora `caption_keywords` se pintan en rojo
(`_CAP_RED`), objetivo ~5%. ONE/TWO/THREE fuera del auto-rojo: en inglés son
relleno gramatical.

### Herramientas nuevas (raíz, con docstring)

- **`counter_overlay.py`** — contador HUD con claves `t=valor`, rampa lineal
  truncada, color de acento en el valor final. La ruta de la fuente necesita
  comillas **Y** los dos puntos escapados a la vez, o ffmpeg parte el
  filtergraph en `C:`.
- **`build_story_video.py`** — TTS + recorte de silencios + pausas dramáticas +
  `.ass` con rojo, para este formato (no usa la etapa MEDIA del pipeline).
  Imprime los segundos exactos de cada pausa, que son los que van en el
  `enable=` de la desaturación y en los `adelay=` de los golpes.

### Receta de montaje

```powershell
py build_story_video.py scripts/<n>.json output/<carpeta> --pausa "frase literal=0.6"
py scripts/_gen_hook_card.py "<hook_card>" "Mind Checkpoint" output/<carpeta>/hookcard.png assets/mindcheckpoint_rebrand/avatar.png "<hook_punch>"
```

Luego cortar el gameplay, el `-filter_complex` de composición (está entero en la
entrada del 1 ago de `HISTORIAL_MEJORAS.md`) y por último `counter_overlay.py`.
Piezas fijas que no se tocan: zoom de entrada `crop 0.87 → 1.0` en 0,8s (el
frame 0 tiene que moverse); `eq=saturation=0.15:brightness=-0.14` activo **sólo**
durante los silencios; golpe grave = `enfasis*.mp3` con `lowpass=f=300`; música
con `lowpass=f=900` y `volume=0.075`; `amix=normalize=0` + `alimiter` (sin
`normalize=0` la voz se hunde); `setsar=1` en cada rama y `-aspect 9:16`.

### Pre-registro de hipótesis (leer antes de mirar métricas)

`output/2026-08-01-visitor-log/hipotesis.json` tiene las **cinco hipótesis
escritas antes de ver ningún dato**, cada una con el segundo exacto donde cae la
técnica y —lo único que lo hace útil— **qué resultado la desmiente**.

Cuando lleguen las métricas: recorrer las cinco y marcar CONFIRMADA /
DESMENTIDA / SIN DATOS. **Las desmentidas se borran del prompt, no se
reinterpretan.** Ese es todo el motivo de haber escrito la falsación antes.
H4 (el contador) es la más frágil y el propio archivo lo dice: cambia a la vez
que el guion entero, así que un resultado bueno no prueba que sea suyo.

### Qué sigue

1. **Publicar el visitor-log como `unlisted`** y mirar la curva del segundo 3 al
   10. Es lo único que valida las reglas 9 y 9f: hoy son oficio, no dato.
2. **Renovar el token de YouTube Analytics** — está caducado, así que
   `experiments.py` no puede leer métricas y no hay forma de comparar nada.
3. Decidir si se borra `_check_but_therefore`. El umbral ya se bajó a 0,12
   porque el líder del formato mide 0%. Si 3-5 competidores más dan ~0%, fuera.
4. `SUB_CHUNK_WORDS = 1` sin decidir: subirlo a 2-3 haría los subtítulos menos
   entrecortados, pero cambia cómo funciona el contraste rojo/amarillo.

### Montado y esperando créditos

**`hook_machine.py`** — deriva la rúbrica de ganchos **de los datos**, no de mis
prejuicios. Mide los primeros ~45 palabras de N ganadores reales y saca la
distribución: abre con pregunta / se auto-resuelve / lleva cifra / lleva 2º
tiempo / lleva diálogo / abre en acción, más medianas de longitud.

Existe porque las reglas 9, 9b y 9f salieron de que yo leyera **una** sola
transcripción. Esta herramienta puede **desmentirlas**, que es el punto. Aviso
ya detectado al probar las medidas: el ganador de 1,6M (`kmiZss057XE`) **sí abre
con pregunta**, justo lo que la regla 9 prohíbe. Si el corpus lo confirma, la
regla 9 se reescribe.

Bloqueada por créditos: necesita ~20 transcripciones = ~105 créditos y hay 34.
`collect` comprueba el saldo antes y aborta en vez de gastar la mitad.
**Hay una tarea programada (`probar-hook-machine`) que salta el 15 ago** con las
instrucciones completas.

### Limpieza de disco (1 ago)

**54,1 GB -> 22,1 GB.** Borrado: los `clips/` intermedios de 225 carpetas de
`output/` (regenerables), las descargas crudas de Days Gone, los renders de
prueba sueltos, las variantes numeradas `video_vN.mp4`, y **`tools/momask`,
`tools/depthflow` y `tools/animated_drawings`** — colgaban de
`ANIMATE_CHARACTERS = False` en `archivo_engine.py`, el motor de esqueleto
está desactivado. Si alguna vez se reactiva hay que re-clonar los tres repos y
volver a bajar los pesos (~5 GB).

`tools/kokoro_tts` y `tools/chatterbox_tts` **siguen** — son los TTS en uso.

Nota para Windows: los repos clonados traen `.git` de solo lectura y
`shutil.rmtree` falla hasta que se les quita el flag con `os.chmod`.

### Registro de giros (2 ago)

`giros_ganadores.md` -- catalogo las ESTRUCTURAS de giro usadas (no los temas),
inspirado en el sistema de ideas ganadoras de un video de mentoria que
analizamos. Seis formas catalogadas (G1-G6). **Ninguna tiene retencion medida
todavia** -- son diseno aplicado, no dato. Se actualiza con numeros reales en
cuanto los cinco videos de chisme/historia tengan curva, siguiendo la misma
disciplina que hipotesis.json: las desmentidas se sacan de circulacion, nunca
se fabrica un resultado.

### Avisos

- **vidIQ: 34 créditos.** Los renovables entran el **15 ago**. 5 por llamada, o
  sea ~6 tiros. No gastarlos en exploración.
- **yt-dlp bloqueado por YouTube** (detección de bot). Necesita las cookies de
  Chrome con Chrome cerrado del todo. 5 candidatos 2K/60fps de Days Gone sin
  verificar licencia: `rBZgqWanAeY`, `eUFTcYZY0qI`, `JaqUO0VkSmE`,
  `LaRIQwrl6AM`, `k5h8fZEJ0sg`.
- Todo gameplay va con CC-BY verificada y crédito en
  `assets/gameplay/ATRIBUCION.md` **y** en la descripción del vídeo.
- Guiones descartados en `scripts/`: `grandmother-recipes.json` (premisa sin
  riesgo — una receta mal escrita no amenaza a nadie) y `the-hung-up-call.json`
  (bueno, pero tercio central flojo y agujero de credibilidad: el 911 devuelve
  la llamada ante un cuelgue en muchas jurisdicciones).
