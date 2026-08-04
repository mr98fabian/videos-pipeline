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

## Actualizado: 4 ago 2026 — KOREX (línea activa)

Todo el día fue **KOREX** (finanzas satíricas, Tadeo el mapache). Nada subido a
YouTube. Rama `claude/sticker-library-ai-vxifx9`, sin commitear.

### LA TAREA ABIERTA — conectar Google Flow

Objetivo: que Flow (1) genere cada escena **replicando a Tadeo y el fondo** vía
imagen de referencia, y (2) **anime escena por escena** después.

Bloqueado: Flow está logueado en **otra cuenta de Google**, no en el perfil de
Playwright de esta máquina. Por eso el traspaso a la otra sesión.

`flow_automation.py` existe (recuperado de git hoy) pero le faltan justo las dos
capacidades: **no sube imagen de referencia** (es solo texto→imagen) y **no tiene
modo video**. Sus selectores se verificaron el 20 jul, y como la UI de Flow es una
SPA con clases hasheadas, hay que revalidarlos contra el DOM real antes de confiar.

Secuencia: `py flow_automation.py --login` (lo hace Fabián, nunca Claude) → script
de inspección que vuelque botones/placeholders reales → escribir subir-referencia
y modo video sobre selectores verificados.

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
  `insufficient credits`. Solo queda ComfyUI local (`--comfy`) o Flow.
- **FLUX schnell no acepta imagen de referencia** → no da consistencia de
  personaje. Por eso la consistencia se resolvió por reutilización de poses. Para
  fondos sin personaje va perfecto.
- `scripts/korex-interbolsa.json` está validado (12 frases = 12 `search_terms` =
  12 `set_terms`) pero **`character_terms` todavía son descripciones**; hay que
  pasarlas a claves `tadeo/<pose>` para que tome la biblioteca.
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
