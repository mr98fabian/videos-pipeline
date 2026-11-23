# MISIÓN 0001 — Sistema de videos KoreX (Remotion + mix pro)

Estado: en-auditoria (Fase 1 entregada; la Fase 2 espera el OK de Fabian) · Rama: `feat/sistema-videos-korex`
(sale de `chore/oficina-y-git`) · Autor: Fabian / Mijo · Ejecutor: Claude (Opus)

Especificación: el "PROMPT MAESTRO — Construcción del sistema de videos KoreX",
pegado por Fabian el 22 nov 2026. Reemplaza al prompt v2 y a la adenda v3.

---

## Fase 0 — Inventario

### Lo que ya existe y se reutiliza
| Pieza | Dónde | Uso en el sistema nuevo |
|---|---|---|
| Guion JSON + validaciones (1:1, twist 25-75 %, un beat `*`, `lint_enie.py`) | `pipeline.py` (lints), `kx_cast.strip_beat/is_beat` | Igual, sin cambios |
| Voz `qw_korex` con marcas de tiempo por palabra | `pipeline.generate_audio` → `words.json` | Fuente única de timing (karaoke, pizarra, SFX) |
| Puente guion → manifest → Remotion → mezcla | `korex_motion.py` (prototipo del 21 nov, sin commitear) | Se conserva el esqueleto: corte por oración, manifest, render, mezcla, reuso del render si el manifest no cambia |
| QA del artefacto en modo motion | `korex_qa.py check_motion` (sin commitear) | Base de la Fase 7: duración, sincronía con el TTS, color, movimiento, bucle, sonido |
| Enganche en el pipeline + `--korex-legacy` | `pipeline.py` (sin commitear) | Igual |
| Proyecto Remotion 4.0.495 | `motion_graphics/` | Igual; composición nueva |
| Hoja madre de Tadeo (vista frontal, 3/4, perfil, espalda + 6 expresiones) | `assets/kx_cast/tadeo/_hojas/model_sheet.png` | **Plano de referencia del rig vectorial** (Fase 2) |
| 34 poses raster con alfa | `assets/kx_cast/tadeo/*.png` | Referencia de acting y respaldo del animatic; no del rig final |
| Transcripción local | `faster-whisper` (instalado, MIT) | QA post-render (Fase 7) |

### Lo que se construye nuevo
Design tokens · karaoke con `@remotion/captions` (`createTikTokStyleCaptions`) · rig
paramétrico de Tadeo en SVG · motor de pizarra (trazo de ancho variable) · las 6
plantillas · cadena de voz + ducking en Remotion + máster a −14 LUFS en 2 pasadas ·
modo animatic · gate Día 0 con Whisper y la hoja de poses.

### Lo que se descarta del prototipo del 21 nov
Las transiciones whip, el parallax de doodles, la paleta gris y los gráficos tipo
blueprint. Contradicen la biblia: solo dos transiciones, paleta INK/PAPER + rojo, y la
explicación va en pizarra.

### LEGACY (código intacto, sin invocar para KoreX)
`flow_automation.py`, `flow_projects.py` (ya no se ata sin `--flow`), `wan_animate.py`,
`korex_fill.py`, `korex_animate.py`, `korex_engine.py` + `KorexVideo.jsx`, la
composición prototipo `KorexMotion.jsx` (quedará como referencia o se borra en la
Fase 4) y, en KoreX, los flags `--flow`/`--wan-hero`/`--flow-animate`/`--reusar-imagenes`.

---

## Conflictos que Fabian debe resolver antes de la Fase 1

1. **Acento rojo vs. "estrictamente blanco y negro".** La biblia nueva admite un rojo
   deuda en ≤8 % de los píxeles y nunca sobre Tadeo. La regla vigente del canal es B/N
   puro: el piloto del 21 nov midió saturación 0 y la QA falla con cualquier color.
   **Propuesta:** aceptar el rojo, pero solo en la pizarra y el número héroe. La QA
   medirá dos cosas: el porcentaje de píxeles rojos (≤8 %) y que no haya color en la
   caja del personaje.

2. **140-155 palabras no alcanzan los 58 s.** Medido con `qw_korex` en el piloto: 176
   palabras = 59,2 s, o sea 2,97 palabras/s. Con 155 palabras saldrían unos 52 s.
   **Propuesta:** subir el rango a 165-185 palabras. La alternativa es dejar 155 y
   escribir unos 6 s de silencios en el guion, pero eso son ~18 holds de 10 frames y
   frena el ritmo.

3. **El sobregiro no hay que "alargarlo": hay que reescribirlo.** Ya dura 59,2 s
   medidos con la voz real (la cifra de "~56 s" era una estimación vieja). Pero el mix
   pide otra estructura: el cálculo del cargo dibujándose en la pizarra entre los
   segundos 6 y 18, la escalada en pizarra y una sola acción entre 46 y 56. Así que el
   guion se reescribe y vuelve a tu aprobación.

4. **El rig de 12-18 poses × 8-10 expresiones × 4 miradas no existe en capas.** Las
   34 poses son imágenes planas.
   **Propuesta:** redibujar a Tadeo como SVG por partes a partir de la hoja madre
   (cabeza, orejas, antifaz, ojos con pupila, cejas, bocas, torso, brazos con guante,
   piernas, cola), con las proporciones fijadas en tokens. Antes de animar nada,
   entrego una **hoja de poses** para tu aprobación, porque un Tadeo vectorial que no
   se parezca es el fallo duro nº 1.
   **Riesgo:** es la pieza más larga del plan y la que más puede tener que iterarse.

5. **La zona segura cambia la composición.** La caja de 840×960 deja fuera de juego
   todo lo que está bajo y = 1248. El karaoke y el CTA del prototipo quedaban debajo
   de esa línea; ahora van dentro de la caja.

6. **Licencias.** `@remotion/sfx` y los componentes de Remotion están bajo la licencia
   de Remotion, que es gratis para personas y equipos de hasta 3. Earshot, Remocn y
   remotion-bits son MIT, y video-shotcraft es Apache-2.0: de esos se toma la técnica,
   no el contenido.
   Para la alineación de respaldo no se usa el modelo por defecto de WhisperX
   (no comercial), sino uno Apache-2.0 o MIT. Primero hay que verificar la licencia
   exacta de ese modelo.

7. **Repo público.** Esta rama sale de la Misión 0, que sigue sin push porque
   `videos-pipeline` es público. Hasta que decidas qué hacer con el repo, esta
   misión tampoco se empuja.

---

## Plan por fases (cada ⏸ es una parada para tu OK)

| Fase | Entrega | Cómo se verifica | Parada |
|---|---|---|---|
| 1 | Tokens (paleta, 2 tipografías, grano, boiling line) + karaoke TikTok-style | Composición de prueba con un guion real; Whisper confirma el texto de cada página | — |
| 2 | Rig vectorial de Tadeo + presets de spring + acting (mirada → cabeza → cuerpo, parpadeo 42/58, idle con dos senos) | **Hoja de poses** (poses × expresiones × miradas) junto a la hoja madre | ⏸ apruebas el Tadeo vectorial |
| 3 | Pizarra: trazo relleno de ancho variable, frenado en los vértices, jitter con semilla, draw-on por palabra, "mito → X → verdad" | Hoja de frames del trazo; el mismo seed da el mismo trazo | — |
| 4 | 6 plantillas (Hook, Pizarra, Héroe, Giro, CTA, Cierre-bucle) + las 2 transiciones oficiales | Hoja de contacto por plantilla; frame 1 = último frame | — |
| 5 | Sonido: cadena de voz fija, SFX en el frame de aterrizaje, ducking por interpolación, máster −14 LUFS en 2 pasadas | `loudnorm` medido; SFX alineados a los frames de aterrizaje | — |
| 6 | Modo animatic a baja resolución con la voz final | Render < 2 min | — |
| 7 | Gate Día 0: hoja de contacto + hoja de poses, Whisper post-render, 4 fallos duros, H.264 CRF 18 | El gate bloquea la subida si hay un fallo duro | — |
| 8.1 | Guion del sobregiro reescrito al mix, con la cifra calculada por script | `lint_enie`, 1:1, twist, beat, cifra verificada | ⏸ apruebas el guion |
| 8.2 | Piloto: animatic → render → QA → subida NO LISTADO por API | Hoja de contacto + gate Día 0 | ⏸ apruebas el look |

Cada fase cierra con su entrada en `HISTORIAL_MEJORAS.md` y un commit en esta rama.

## Reporte

### Fase 1 — Núcleo Remotion (tokens + karaoke) · 23 nov 2026

**Qué se hizo**
- `motion_graphics/src/kx/tokens.js`: los design tokens como constantes. Paleta
  cerrada INK `#111111` / PAPER `#F4F1EA` / DEBT `#C8102E` (≤8 %), zona segura
  840×960 (x 48-888, y 288-1248), tamaños de tipo, parámetros del karaoke, del
  grano y del boil.
- `fonts.js`: las 2 tipografías vía `@remotion/google-fonts` (ambas OFL): Archivo
  800/900 para números, títulos y karaoke; Permanent Marker para la pizarra.
- `texture.jsx`: `FilmGrain` (ruido acromático multiplicado, cambia cada frame),
  `Boil`/`BoilDefs` (boiling line: desplazamiento que cambia cada 3 frames y
  cicla 3 dibujos) y `PaletteLockDefs` (duotono INK→PAPER para rasters).
- `paginate.js` + `KxCaptions.jsx`: karaoke con `createTikTokStyleCaptions`
  (`combineTokensWithinMilliseconds = 800`), 72 px, peso 800, palabra activa
  invertida (PAPER sobre INK), franja dentro de la zona segura (y 1008-1248).
- `kx_captions.py`: fuente de timing. Primero los `words.json` del TTS; si no
  existen, respaldo con faster-whisper. Incluye el gemelo Python de `paginate`.
- `kx_gate.py`: comprobaciones sobre el MP4 (base de la Fase 7): barrido de
  paleta, zona segura, Whisper por página y hoja de contacto.
- `kx_nucleo.py` + composición `KxNucleo`: el render de prueba de 14,9 s con la
  voz real `qw_korex` (primeras 3 oraciones del piloto del sobregiro).

**Criterios de aceptación — evidencia** (`misiones/evidencia/0001-fase1/`:
`contactsheet.png` en git; `gate.json`; el resto en `output/2026-11-23-kx-nucleo/`)
1. **Render con paleta y karaoke sincronizado: cumple.** 14,9 s, 447 frames,
   render en 32 s. Whisper transcribe el MP4 renderizado (no la voz bruta) y
   confirma **15/15 páginas al 100 %** dentro de su ventana. Deriva palabra a
   palabra Whisper↔TTS: mediana 108 ms, p90 160 ms. Es el margen propio de
   Whisper; el karaoke usa el TTS, que es exacto por construcción.
2. **Barrido de color: cumple.**
   - Frame sin pérdida (`remotion still` con el héroe en pantalla): 0,002 %
     fuera de paleta, rojo 1,1 %, 0 píxeles de color en la caja del personaje.
   - MP4 codificado (89 frames a 6 fps): peor frame con 0,034 % fuera de
     paleta, rojo máximo 1,6 % y color en la caja del personaje 0,0 %.
   - Zona segura: 0 píxeles oscuros fuera de la caja en todos los frames.
3. **Ni Flow ni Wan: cumple.** El render es `npx remotion render`. `grep` de
   flow/wan/korex_engine/animate/fill en los 9 archivos nuevos: solo aparece el
   comentario que lo dice.

**Fallos encontrados y su arreglo** (todos los cazó la QA, no el ojo)
- Páginas de 1 palabra ("seis.", "El", "Y") y una página que cruzaba una coma.
  Arreglo: después de `createTikTokStyleCaptions` se corta por cláusula
  (`. , : ; ? !`), cada cláusula se parte en trozos de 2-4 palabras eligiendo
  los cortes donde Remotion detectó una pausa, y las sueltas se pegan a la
  vecina. Resultado: 15 páginas, todas de 2-4 palabras.
- El karaoke se salía de la zona segura (una línea de 4 palabras no envolvía).
  Arreglo: flex-wrap entre palabras y ninguna palabra se parte.
- El "$35" rebasaba x = 888 durante 4 frames por el rebote del spring. Arreglo:
  160 px. La regla general (el rebote cabe en la caja) la encodea la Fase 4.
- Primer barrido: 0,4 % "fuera de paleta". Era ringing del H.264 (negros más
  negros que INK, blancos más blancos que PAPER) y submuestreo 4:2:0 en los
  bordes del rojo. Arreglo de la medición, no del diseño: se clasifica por
  tono. Cuenta como neutro lo que está sobre la recta INK→PAPER, extendida un
  6 % por extremo; como deuda, lo de tono rojo ±30°; el resto, fuera de
  paleta. El frame sin pérdida confirma que el diseño era limpio.
- Whisper oye "sobre giro". Se reúnen los compuestos cuando la unión existe en
  el guion.

**Desviaciones declaradas**
- **WhisperX → faster-whisper.** El alineador por defecto de WhisperX para
  español es VOXPOPULI de torchaudio, que es CC BY-NC. faster-whisper es MIT,
  con pesos Whisper MIT, ya está instalado y no arrastra torch (~2 GB). Su
  precisión, medida aquí: mediana de 108 ms. Basta para respaldo y QA, no para
  un karaoke fino. Si algún día falta `words.json` y hace falta precisión de
  karaoke, la opción es WhisperX con `jonatasgrosman/wav2vec2-large-xlsr-53-spanish`,
  pero antes hay que verificar su licencia. Ese camino no está construido.
- **Rojo deuda.** La spec de esta fase fija "≤8 % y nunca sobre un personaje",
  así que se aplica tal cual. Esto resuelve el conflicto 1 de la Fase 0.
- **Las páginas no cruzan comas.** Es más estricto que la spec (2-4 palabras),
  pero va en la misma dirección.
- **Paginación duplicada a propósito** (JS para pantalla, Python para la QA).
  `kx_nucleo` las ejecuta las dos y falla si difieren: hoy son idénticas.
- `still_hero.png` no va en git (1,5 MB; `*.png` está ignorado). La hoja de
  contacto sí, con `-f`.

**Pendiente**
- **Fase 2 (rig de Tadeo): no empieza sin el OK de Fabian a esta fase.**
- Siguen abiertos de la Fase 0: el conflicto 2 (largo del guion), el 4 (el rig
  con hoja de poses) y el 7 (repo público, sin push).

**Rama / PR:** `feat/sistema-videos-korex`, sin push ni PR (el repo es público).
