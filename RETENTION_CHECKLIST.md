# Checklist de retención para guiones manuales (HiddenFacts / ImPixxel)

## Gancho de los primeros 2 segundos (4 tipos — subir "se quedaron a mirar")

Investigación 19 jul 2026 (Virvid, algoritmo Shorts 2026, psicología: Loewenstein
information gap, Zeigarnik, área fusiforme facial, sistema reticular activador). El % de
"se quedaron a mirar" combina DOS decisiones: swipe en el frame 0 (~1s, refleja) + hook
de retención (~1-3s). Existen **4 tipos de gancho** y veníamos optimizando solo el verbal.
**Meta realista: 60-65% de promedio de canal (el 90% es imposible en tráfico frío; nuestro
techo actual es ~70% con el video de cascos).**

1. **Verbal/conceptual** (ya fuerte): paradoja + revelación retrasada + loop léxico.
2. **Visual (REGLA NUEVA)**: el PRIMER `search_term` debe ser un **primer plano cerrado de
   un rostro humano, expresión intensa, contacto visual directo, sujeto brillante sobre
   fondo oscuro** (alto contraste). El área fusiforme facial reconoce caras en 50-200ms —
   es el freno de scroll más rápido que existe. Abrir con escena amplia desperdicia la
   palanca. `pipeline.py` avisa en el lint si el primer term no parece una cara.
3. **Auditivo (REGLA NUEVA)**: golpe sonoro en el frame 0 (el flag `--intro-stinger`, o
   `--hook-max` que lo incluye) + **arranque in-media-res**: empezar la narración a mitad
   de acción ("A single touch. Four days later, he was dead.") y contextualizar después,
   en vez de "In 1978, a man was waiting...".

   **Matiz confirmado por 3 fuentes independientes (21 jul 2026):** el "anti-hook" puro
   (cero contexto verbal, dejar que la imagen sola comunique la escena) funciona mejor
   cuando la PRIMERA imagen es autoexplicativa por sí sola (una acción o expresión que
   se entiende sin palabras). Nuestro contenido (secretos históricos) casi siempre
   necesita un mínimo de dato concreto (fecha/nombre) para que el misterio tenga sentido
   -- por eso NO conviene ir a un anti-hook 100% puro. Formato recomendado: 3-6 palabras
   de acción cruda primero (sin contexto), después la frase que ancla el dato concreto.
   Ej: "A single touch." (anti-hook puro, la cara del guion ya muestra la escena) +
   "Four days later, he was dead." (ancla el dato). Ya lo veníamos haciendo bien;
   esto formaliza POR QUÉ funciona y cuándo NO estirar el anti-hook más de esas 3-6
   palabras iniciales.
4. **Texto/premise card (FEATURE NUEVA)**: campo `hook_card` en el JSON del guion — una
   premisa de alto contraste (~2.2s, curiosity gap, reteniendo el desenlace) que el
   espectador lee al inicio. Se renderiza como scrim oscuro + texto amarillo grande.

### Flags de gancho en `pipeline.py` (ESTANDAR DE PRODUCCION desde el 19 jul 2026)

`--hook-max` pasó de opt-in de test A/B a **default ON** (usar `--no-hook-max` para
desactivarlo puntualmente). Incluye: stinger auditivo en frame 0 (volumen subido a 0.42),
texto adelantado 150ms, zoom de entrada fuerte (+0.25 en el primer ~12%), flash blanco de
pattern-interrupt (2 frames) y wipe circular de entrada (~0.3s) antes del primer clip.

- `hook_card` (campo del guion, ahora generado automaticamente por `generate_script()` en
  modo `--auto`/`--topic`): la premisa como curiosity gap, NUNCA una copia literal de la
  primera oracion del guion — debe leerse como un caption independiente que retiene el
  desenlace. Si escribís el guion a mano (`--script-file`), agregalo vos mismo siguiendo
  el mismo criterio.
- `--hook-card-mode {overlay,read}`: `overlay` (default) = el card se superpone mientras ya
  narra desde t=0; `read` = beat de lectura primero (frame congelado 2.2s + solo
  música/stinger, la narración arranca después). Pendiente A/B real entre ambos.
- `--wan-hero PATH`: anima la escena 0 con un video ya generado localmente (Wan 2.2 via
  ComfyUI, gratis, ver setup en memoria) en vez de imagen estática — mismo patrón que
  `--veo-hero` pero sin costo de API. Requiere generar el clip aparte (ComfyUI corriendo
  en `localhost:8188`, workflow `video_wan2_2_5B_ti2v`) antes de correr el pipeline.

### Regla nueva: search_terms debe tener EXACTAMENTE 1 entrada por oración del guion

Bug confirmado con datos reales (19 jul 2026): varios guiones tenían 10 `search_terms`
pero solo 7-8 oraciones. `_scene_boundaries()` solo puede cortar en fin de oración, así que
el conteo de más forzaba al menos un corte a mitad de frase — la imagen cambiaba antes de
que el narrador terminara la idea (desincronía voz/imagen real, no percibida). `_check_script_lint()`
ahora avisa si el conteo no coincide. Si querés un cierre tipo "eco visual" (última imagen
= primera imagen), agregá una oración de cierre extra en el guion para que tenga su propio
search_term, no repitas el término sin una oración que lo sostenga.

### Loop narrativo (recontextualizar el cierre, no solo repetirlo)

Investigación 19 jul 2026 (loop/rewatch como señal de ranking en Shorts 2026): la regla
existente de "cerrar con la palabra literal del gancho" debe además CAMBIAR el significado
de esa frase con lo que el espectador ya sabe, no solo repetirla igual — es lo que hace que
el cierre funcione como loop (dan ganas de re-escuchar la apertura) en vez de sonar a "video
nuevo empezando". Ya está en el prompt de `generate_script()` (paso 4); aplicar el mismo
criterio al escribir guiones a mano.

**Nota técnica de mezcla (investigación TubeBuddy 20 jul 2026):** el crossfade visual del
loop (`LOOP_DUR` en `pipeline.py`) ya está resuelto, pero el canal fuente además hace
coincidir el CLIMAX de un efecto de sonido exactamente con el punto de empalme final→inicio
(el SFX "llega a su punto álgido" justo cuando arranca el loop) — es lo que hace que el oído,
no solo el ojo, perciba el corte como continuo. Evaluar si algún `sfx_cue` cercano al final
del video puede recortarse/ajustarse para que su pico caiga en el frame de loop en vez de
sonar cortado antes.



## Regla nueva (18 jul 2026, aplicar a TODO guion nuevo desde ahora): afilar sin mentir

4 ajustes aprobados para maximizar impacto sin pisar reglas de YouTube -- la línea es
siempre "decir la verdad más fuerte", nunca fabricar nada ni simular tracción falsa
(eso sí arriesga el canal entero, ver conversación 18 jul sobre tácticas "poco éticas
pero legales" -- las que violan ToS quedan descartadas aunque sean legales bajo la ley).

1. **Título**: llevar el título a la versión más visceral que siga siendo 100% literal
   -- ej. no "A Man Once Sold a Country" sino "He Convinced an Entire Nation to Sail Into
   a Jungle — a Third of Them Never Came Back". El video SIEMPRE tiene que entregar
   exactamente lo que el título promete (ahí está el límite real de YouTube con clickbait).
2. **Escasez real, no inventada**: si el hecho tiene un elemento real de "esto se ocultó
   X años", subirlo al TÍTULO, no dejarlo solo en el guion. Nunca inventar urgencia falsa
   (ej. "esto se va a borrar pronto" -- eso sí es engañoso y cae en política de spam).
3. **CTA de descripción más polarizante** (nunca hablado, sigue la regla de siempre):
   cambiar preguntas genéricas ("¿sabías esto?") por preguntas que fuercen una postura
   -- ej. "¿le hubieras creído la excusa por 35 años, o hubieras seguido preguntando?".
4. **Ángulo tribal/nosotros-vs-ellos** cuando el hecho real lo permita sin forzar (ya
   validado con Hedy Lamarr y el ángulo #3 de Katyn, US/UK sabían y se callaron).

**Seguimiento:** etiquetar en `video_log.csv` con `outlier_reference` que mencione estos
ajustes (ej. "titulo afilado + CTA polarizante") para poder comparar contra el baseline
de guiones anteriores una vez maduren (48h).

## Pendiente futuro: test cruzado de 3 formatos por tema

## Pendiente futuro: test cruzado de 3 formatos por tema

Idea aprobada (18 jul 2026) para un lote futuro, todavía no ejecutada: por cada tema real
verificado, generar 3 versiones y comparar cuál retiene mejor:
1. **Narrativo largo** (45-60s, 10 clips, karaoke) -- el formato de siempre.
2. **Ultra-corto karaoke** (4-8s, 1 clip, zoom Ken Burns, subtítulo karaoke) -- el lote
   de 12 de esta sesión (Bartali, Winton, Yamaguchi, Ghost Army, York, Farnsworth,
   Sendler, Wallenberg, Pilecki, Sugihara, Bielski, Landmesser).
3. **Caption estático** (`caption_header`/`caption_text`/`caption_keywords` en el JSON del
   guion) -- imagen fija en el 62% inferior, fondo negro, título+párrafo fijos arriba
   (keywords en rojo), subtítulos karaoke de lo narrado sobre la imagen. Narrador lee
   solo una frase corta, el párrafo es para leer al propio ritmo.

**Por qué esperar:** mismo tema x3 versiones es contenido casi-duplicado -- necesita el
mismo criterio de espaciado de 2+ días entre publicaciones que ya usamos en otros tests A/B,
y multiplica el costo de Gemini por 3 por tema. Evaluar primero cómo rinde el lote de 12
ultra-cortos ya publicado antes de comprometer un lote de este tamaño.

## Motivo visual patriótico (ángulo americano, sutil)

Para guiones del ángulo patriótico (héroes/inventores americanos, injusticias corregidas),
agregar al campo `style` una línea como: "a small American flag or subtle red-white-blue
color accent visible in the background where it fits the scene naturally, understated,
never a focal point". Es diseño visual VISIBLE, no oculto -- no existe tal cosa como una
señal "subliminal" que el clasificador de YouTube lea distinto a lo que ve un humano; si
es imperceptible, tampoco sirve de señal. El objetivo es identificación de audiencia +
consistencia visual real entre videos, igual que el estilo sepia ya es la firma del canal.

## Regla dura: ignorar recomendaciones genéricas fuera del nicho

vidIQ (pestaña "Para ti"/"For you") y el matching de YouTube (términos de búsqueda,
contenido sugerido) recomiendan basura fuera de nicho cuando el canal es chico (visto
18 jul 2026: "starcraft 2", "ballerina", "yellowstone", "the amazing world of gumball" —
ninguno tiene que ver con historia/misterio). Es la MISMA causa raíz en los dos casos:
con pocos suscriptores/vistas, ni YouTube ni vidIQ tienen señal propia suficiente para
personalizar de verdad, así que rellenan con volumen genérico alto. Confiar en esas
recomendaciones sin filtrar puede estar activamente perjudicando al canal (dispersar
guiones/keywords hacia temas sin relación).

**Regla:** cualquier keyword/outlier que se use para decidir un guion tiene que venir de
una búsqueda o filtro explícitamente acotado al nicho (historia real, misterio, true
crime, deceptions) -- nunca de una pestaña "para ti"/genérica sin filtrar. Si vidIQ o
YouTube no tienen suficiente dato propio para personalizar, hay que dárselo nosotros via
el query, no confiar en su default.

## Paso 0 (obligatorio antes de escribir cualquier guion): investigación de outliers

Antes de generar un video nuevo, correr `vidiq_outliers` (y opcionalmente
`vidiq_trending_videos`) sobre el nicho del canal para ver qué está reventando ESTA
semana, no confiar solo en las reglas ya validadas. Un outlier real (10x-100x+ el
promedio del canal que lo publicó) vale más señal que 5 videos "correctos" según reglas
viejas. Patrones repetidos observados en outliers de historia/misterio (18 jul 2026):

- **Crossover de nicho** (historia + true crime, historia + gaming) supera por mucho al
  nicho puro — ej. "The Poisoned Umbrella" (true crime + Cold War) >100x, "Ubisoft Hid a
  Real Historical Detail" (historia + gaming) 15x.
- **Listicle-misterio sin spoiler en el título** ("Certain events in history make you
  stop everything and watch", 20x/991K) supera al formato "un hecho nombrado en el
  título" que usamos hoy — la promesa de multiples revelaciones sin decir cuáles sostiene
  la curiosidad todo el video, no solo el hook inicial.
- **Mito-vs-realidad** ("Historical FACTS That Actually False") sigue siendo un formato
  fuerte, ya validado con el video de vikingos.

**Cómo aplicarlo:** no reemplaza las reglas de abajo (hook, loop, CTA nunca hablado, etc.)
— se corre ANTES para elegir el ángulo/formato del guion, y las reglas de abajo siguen
aplicando a cómo se escribe una vez elegido el ángulo. Si un outlier grande aparece en un
crossover de nicho, vale la pena escribir una versión propia rápido (mismo evento
verificado real, nunca copiar guion ajeno) mientras el tema está caliente, en vez de
esperar el próximo ciclo de research programado.

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

2b. **Foreshadow inmediato + transición sin "pacing break"** (investigación TubeBuddy/Jenny
   Hoyos, 20 jul 2026, canal validado con datos reales de retención >100% en shorts <30s).
   Justo después del hook, adelantar en una frase corta CUÁL es el remate/giro (sin revelarlo
   del todo) antes de pasar al desarrollo — ya lo hacemos parcialmente con el hook_card, pero
   aplica también al guion hablado puro. Evitar frases de transición tipo "here's what
   happened" / "let's find out" / "so I did this" — rompen el ritmo justo cuando el
   espectador ya tiene 2 datos frescos en la cabeza (primacía/recencia) y se sienten como un
   segundo inicio. Preferir seguir la oración directamente con el siguiente hecho concreto,
   sin frase-puente.
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

## Duración: mínimo 60s (regla nueva, 21 jul 2026)

**Regla del usuario, reemplaza el objetivo anterior de 45-55s:** de ahora en adelante,
todo guion narrado normal (no el formato "solo lectura" de 7s) apunta a **mínimo 60
segundos, lo más cerca posible de 60s por arriba** — nunca más corto, y no mucho más
largo salvo que el hecho real lo exija. A WPS 2.3-2.7 (ya establecido), eso equivale a
**~140-160 palabras** de guion (antes 110-130). `pipeline.py` ya lo aplica:
`_check_pacing()` cambió su `target_seconds` default de 45.0 a 60.0.

**Por qué el cambio respecto a la regla vieja:** antes se recomendaba probar variantes
MÁS cortas (85-100 palabras, <35s) para subir el % de completado. Esa era una hipótesis
de test A/B, no una conclusión validada con datos propios — el usuario pidió explícitamente
fijar el piso en 60s en su lugar. No revivir la variante corta salvo pedido explícito.

- `track_video.py` registra `duration_sec`; cruzar contra `youtube_api.py retention` y
  `averageViewPercentage` para validar el efecto real de este cambio de piso.

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
