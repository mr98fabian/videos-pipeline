# Checklist de retención para guiones manuales (HiddenFacts / ImPixxel)

El `SCRIPT_PROMPT` de `pipeline.py` ya aplica estas reglas en modo `--auto`. Los guiones
que se escriben a mano (JSON en `scripts/`) DEBEN cumplir lo mismo, porque para Shorts la
distribución la deciden señales genuinas de retención, no la miniatura (no hay click en el
feed de Shorts).

## Reglas del campo `script`

1. **Hook en la 1ª frase.** Número concreto, afirmación audaz o curiosity gap. Nada de
   warm-up ("In this video…", "Let me tell you about…"). Los primeros ~1-1.5s deciden el
   swipe: es el mayor punto de abandono. La escena 0 recibe además un zoom de entrada
   automático (`hook=True`).
2. **Re-hook cada ~15s.** "But here's the part nobody mentions…", "and then it got worse".
   Explota el efecto Zeigarnik (el cerebro fija la información sin resolver) para evitar el
   abandono a mitad de video, no solo al inicio.
3. **Cierre en LOOP con repetición LÉXICA EXACTA** (no solo temática). La última frase
   debe repetir la(s) misma(s) palabra(s) del hook de apertura, no solo la misma idea.
   Ej: hook *"Hitler's own men didn't recognize him"* → cierre *"...and by the end, even
   Hitler's own men didn't recognize **him**."* La repetición literal es lo que hace que
   el empalme final→inicio (loop seam del audio) se perciba como bucle real y no como
   "otro video empezando" — dispara re-watch (>100% de reproducción, la señal más fuerte
   en Shorts).
4. **Nunca CTA hablado.** Nada de "subscribe", "sígueme", "cuéntame en los comentarios"
   dentro del `script`. Anunciar el cierre provoca un Cliff (caída dura de retención) justo
   en esa frase — el cerebro cierra el video mentalmente antes del final real. El CTA va
   100% en `description`, nunca en el audio.
5. **Beats de ≤4s + sincronía beat-1.** Un visual claro por frase (o dos). Cada
   `search_term` = un beat en el orden de aparición. El **primer** `search_term` debe
   nombrar literalmente el sujeto de la primera frase hablada — cualquier desfase entre
   la primera palabra oída y la primera imagen se procesa como incongruencia antes de que
   el swipe sea consciente. Evitar frases que necesiten más de ~4s del mismo plano.
6. **Densidad (WPS).** Frase corta. Frase corta. Una frase larga que aporte matiz. Frase
   corta. Una pregunta cada 4-6 frases. Objetivo 2.3-2.7 palabras/segundo — por debajo se
   siente lento (riesgo Hump), por encima se pierden palabras en mute.

## Duración: probar versión corta

- **Variante corta (test de completion rate): ~85-100 palabras ≈ <35s.** Más densa, sube el
  % completado, que es la métrica clave del feed de Shorts.
- Variante estándar: 110-130 palabras ≈ 45-55s.
- `track_video.py` registra `duration_sec`; cruzar contra `youtube_api.py retention` y
  `averageViewPercentage` para validar cuál retiene mejor por tema.

## CTA en pantalla (nunca hablado)

Si se quiere probar un CTA de "suscríbete", usar SIEMPRE `pipeline.py --cta-text "..." 
--cta-position start|middle|end` — texto superpuesto con fade in/out de 3s, nunca
narrado. El CTA hablado ya está confirmado que genera un "Cliff" de retención (regla de
arriba, "Nunca CTA hablado"); el de texto es la forma segura de probar si la posición
(inicio/medio/final) mueve algo sin arriesgar ese Cliff. Test en curso (17 jul 2026):
mismo guion de Coca-Cola, 3 videos idénticos salvo la posición del CTA, programados en
días distintos (21/23/25 jul) para no leerse como contenido duplicado entre sí.

## Título: nombrar al antagonista/institución famosa cuando aplique

Dato real (Studio, 28 días, HiddenFacts): los 6 videos con 1000+ vistas de la tabla
mencionaban explícitamente un antagonista o institución YA reconocible en el título
("...That Fooled **Hitler**", "...**American Intelligence**"), no un genérico
"engaño histórico". Los que quedaron en 3-7 vistas (mismo estilo, misma duración,
misma franja de calidad de contenido) no nombraban a nadie famoso. Regla: si el hecho
real tiene un antagonista o institución reconocible (Hitler, la Mafia, Rommel, la CIA,
Riot Games, etc.), nombrarlo en el título en vez de mantenerlo genérico — es gancho de
reconocimiento inmediato, no solo curiosidad abstracta. Esto se suma a, no reemplaza,
la franja horaria de publicación (ver `espaciado-publicacion-shorts` en memoria):
ambas señales aparecen juntas en los 6 casos ganadores.

## Idioma / voz

- **HiddenFacts:** guion 100% en inglés, voz default (`en-US-AndrewNeural`).
- **ImPixxel:** guion en español LATAM, `--voice es-MX-JorgeNeural`, evitar palabras con ñ.

## Base de datos de personajes (marca personal reconocible)

Cualquier personaje recurrente (campeones de lore, figuras de HiddenFacts, secundarios de
sketches) debe escribirse en su primer `search_term` de aparición con el prefijo
`"<Nombre> character: <descripcion> -- <accion de la escena>"` (convención ya usada para
Skick, ahora generalizada). El pipeline detecta esto automáticamente y genera una **hoja de
personaje persistente** en `assets/characters/<slug>/` (registrada en `manifest.json`) la
primera vez; todas las apariciones siguientes, en ESTE video y en cualquier video futuro,
reusan la misma hoja — así el personaje se ve igual siempre, sin tener que hacer nada extra.

- **Fases:** si el personaje cambia de forma dentro de su propia historia (ej. Viego rey vs.
  Viego fantasma), incluir la palabra de fase en el texto (`ghost`, `spectral`, `skeletal`,
  `phantom`, `undead`, `child`, `young`, `prisoner`, `warden`, `possessed`, `corrupted` —
  ver `PHASE_KEYWORDS` en `pipeline.py`) y se genera/reusa una hoja separada para esa fase,
  usando la fase "default" como ancla de identidad para que la cara/silueta no cambie.
- No hace falta aprobar manualmente cada hoja nueva — se guarda automático. Si una sale mal,
  basta con borrar el archivo en `assets/characters/<slug>/` y su entrada en `manifest.json`
  para forzar que se regenere la próxima vez.
- Los campeones de LoL con splash oficial (`assets/lol_db/champions/`) ya tenían este
  mecanismo por separado (`_get_character_sheet`, una sola fase); esta base de datos nueva
  es para todo lo demás: personajes sin splash art (secundarios, figuras históricas).

## SEO de tags/descripción (obligatorio antes de subir, no solo el título)

Un tag o frase de descripción sin volumen de búsqueda real vale casi nada aunque "suene bien"
(caso real: "disability fraud" como tag = 0 búsquedas/mes, score 19; "fraud" solo = 87K
búsquedas/mes, score 58 — mismo tema, resultado opuesto). Antes de subir:

1. `vidiq_keyword_research` (gratis) sobre 2-3 términos candidatos del tema del video — no
   adivinar sinónimos, verificar `estimatedMonthlySearch` y `overall` de cada uno.
2. Elegir tags por mejor balance volumen/competencia (`overall`), no por el más "descriptivo".
   Preferir el término genérico de mayor volumen sobre la frase específica de 0 búsquedas
   cuando ambos aplican (ej. "fraud"/"true crime" en vez de "disability fraud").
3. La descripción debe repetir las MISMAS keywords de alto volumen que los tags, no
   parafrasearlas con sinónimos de bajo volumen — vidIQ puntúa la alineación entre ambos.
4. Nunca copiar tags de una plantilla genérica entre temas distintos (caso real detectado:
   un video de Sylas/LoL traía tags de WoW y "anime resumen" pegados de otro guion — basura
   que no aporta nada y puede confundir la categorización del video).
5. Ya usado en `vidiq_score_title` para el título — aplicar el mismo estándar de datos
   reales a tags y descripción, no solo al título.

## Post-subida

- `youtube_api.py comment <id> --text "…"` publica un comentario-pregunta como el canal para
  subir engagement velocity temprano. El **pin es manual** (1 clic en Studio; la API no lo
  permite).
