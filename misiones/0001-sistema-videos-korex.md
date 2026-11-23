# MISIÓN 0001 — Sistema de videos KoreX (Remotion + mix pro)

Estado: en-curso (Fase 0: inventario + plan, esperando OK) · Rama: `feat/sistema-videos-korex`
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
_(se completa al cerrar la misión)_
