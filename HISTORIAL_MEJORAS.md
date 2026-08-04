# Historial de mejoras — HiddenFacts / ImPixxel

Bitácora cronológica de cada ciclo **investigación → cambio aplicado → dónde se publicó**.
No repite lo que ya está en `RETENTION_CHECKLIST.md` (reglas de guion) ni en memoria
(decisiones/preferencias) — esto es el registro de causa→efecto para poder mirar atrás
y cruzar "qué cambiamos" con "qué pasó con las vistas/retención" en `PROGRESO_CANAL.md`.

Formato por entrada:
```
## AAAA-MM-DD — Título corto
**Investigación/fuente:** de dónde salió la idea (video, canal, doc, feedback del usuario)
**Cambio aplicado:** qué se tocó en el código/guion/config, en una frase
**Dónde se publicó:** video(s)/canal afectado, o "pendiente" si aún no sale a producción
**Qué esperamos ver:** la hipótesis a validar (para revisar en la próxima auditoría)
```

---

## 2026-07-31 (tarde) — Auditoría del líder del formato: 175s, título = primera línea, y registro cálido
**Investigación/fuente:** los 50 vídeos más recientes de **Reddit Gossipz** (`@reddit_gossipz`, 196k subs, 416M vistas, mediana de **233.371 vistas por vídeo**), más el transcript completo de su vídeo #1 (1,66M). Es el líder medible de nuestro formato exacto
**Hallazgos medidos (no impresiones):**
- **Duración: los 50 vídeos caen entre 163s y 179s, mediana 176s. Ni uno solo corto.** Están pegados al techo de 3 min de Shorts. Nosotros veníamos de 38-43s y habíamos subido a 90s esa misma mañana → `TARGET_SECONDS` a **175s** (~710 palabras a nuestro ritmo de 4,07 wps). Ojo: ellos hablan a **5,78 wps**, así que su guion de 175s tiene ~1000 palabras — se copia la DURACIÓN, no el conteo de palabras
- **Cadencia: 2 vídeos diarios**, sostenida
- **Título: 0/10 de su top empiezan con "Why".** 7/10 son primera persona ("I…"/"My…"), 2/10 abren con cita textual, y la curiosidad se genera **truncando la frase a media idea con "…"**, no preguntando. Además el título **es literalmente la primera línea hablada**, copiada tal cual → regla **9d**. Esto ANULA para el canal de historias la parte de la regla 9 (petición del usuario del 30 jul) que obligaba al TÍTULO a empezar con "Why"; el guion hablado puede seguir cualquiera de las dos formas
- **Sus 3 mayores éxitos NO son de venganza**, son de **reversión emocional**: alguien no reconocido que por fin recibe reconocimiento (1,66M el padrastro llamado "papá" tras 17 años; 974k recuperar la vista el día de la boda; 919k "mi padrastro es más hombre que tú"). Nuestros 7 guiones eran **todos** de traición/castigo → regla **9e**, alternar registros
**Corrección de lo que se implementó por la mañana — la evidencia contradijo dos cosas:**
- **`_check_but_therefore` estaba mal calibrado.** Su vídeo #1 tiene **0/27 conectores = 0%** y es el más visto del nicho. El consejo de Parker/Stone viene de comedia narrativa larga y no transfiere a este formato, que es acumulación de viñetas, no cadena causal. Umbral bajado de 0,30 a 0,12 y degradado a aviso suave. Anotado: si 3-5 competidores más dan ~0%, hay que **borrar el check**, no seguir bajándole el umbral
- **`_check_sentence_rhythm` estaba mal en la dirección contraria.** Por la mañana escribí que nuestros datos NO respaldaban la regla (black_tom, el de mejor retención, tenía la menor variación: 3,7). El líder la desmiente: desviación **6,1**, frases de 2 a 24 palabras, con remates de dos palabras ("Same game.", "Never scanned."). Nuestros guiones estaban entre 3,7 y 4,8, todos por debajo. Umbral **subido** de 3,5 a 5,0
**Dónde se publicó:** pendiente. Primer guion con las tres reglas nuevas: `scripts/janitor-graduation.json` (751 palabras/~175s, registro cálido, título truncado en primera persona, desviación de ritmo 10,9)
**Qué esperamos ver:** si el formato largo (175s) sostiene retención, es la palanca más grande de todas las tocadas hoy — pasa de ~40s a ~175s de tiempo visto por espectador, y en Shorts 2026 el factor de reparto principal son los segundos absolutos vistos

## 2026-07-31 — Regla 9c (cuerpo del guion) + duración a 90s medida, no estimada
**Investigación/fuente:** estudio de 4 vídeos más de `@kallawaymarketing` (Master Storyteller `t5Z-Q1bg1tU`, Dopamine Ladder `jtmstMt4WLc`, 6 Power Words `S9FlxFv9dxg`, Irresistible Hooks). La regla 9b del 30 jul solo arreglaba las tres primeras frases; todo lo que venía después seguía sin regla
**Cambio aplicado:** regla **9c** con tres partes, y sus lints (`_check_but_therefore`, `_check_sentence_rhythm`), que como siempre importan más que el prompt porque nuestros guiones entran por `--script-file` y no pasan por Claude:
- **(a) But/therefore, nunca "and then"** (Trey Parker/Matt Stone). Entre dos beats debe caber "pero" o "por lo tanto". Medido en nuestros 8 guiones: íbamos a 2-4 conectores de 10-26 oraciones (~25%); el lint avisa por debajo del 30%. No se busca el 100%, que sonaría robótico
- **(b) Variar longitud de frase** (Gary Provost). **Implementado como aviso suave a propósito: nuestros propios datos NO lo respaldan.** El vídeo con mejor retención medida (`black_tom`, 151% a los 0:30) es justo el de MENOR variación (desviación 3,7, la más baja de los 8). Está anotado en el código que si tras 3-5 vídeos más la correlación sigue ausente, hay que borrar el check en vez de arrastrarlo por inercia
- **(c) Head-fake antes del pago**: el pico de dopamina cae JUSTO ANTES de la respuesta, no en la respuesta. Dar pistas, dejar que el espectador se acerque, desviar una vez, y recién ahí entregar el pago real. Una desviación, no tres. Sin esto la historia es una recta de pregunta a respuesta y el medio se aplana, que es donde la gente se va
**Descartado a propósito:** la fórmula de 6 palabras de gancho (sujeto/acción/objetivo/contraste) — ya la cubre la regla 9 para nuestro formato; y el nivel 5 "afecto al creador" — el propio Kallaway dice que el faceless casi no puede alcanzarlo, es un techo estructural, no algo que arregle una regla
**Duración 60s → 90s:** medida, no estimada. `ffprobe` sobre 4 vídeos reales del 30 jul dio **4,07 palabras/segundo** con `--trim-silence` (3,65 sin recortar), así que **355-375 palabras = ~90s finales**. Actualizadas las 4 referencias del prompt más `TARGET_SECONDS`. De paso se corrigió `WPS_MIN/MAX`, que estaban en 2,3-2,7 de otra configuración y hacían saltar el aviso de pacing en TODOS los guiones aunque estuvieran bien. Respaldo del cambio: los canales de referencia de este formato (Reddit Gossipz 196k subs/416M vistas, La Hemeroteca) rinden con Shorts de 2:47-2:59; el "punto dulce 30-45s" de `CLAUDE.md` se midió para HiddenFacts, que es otro formato
**Dónde se publicó:** pendiente, aplica desde el próximo guion
**Qué esperamos ver:** el hueco que estas reglas atacan es la caída del segundo 3-8 medida en `-79EJI_BSsE` (el primer vídeo de la serie, hecho antes de todas estas reglas)

## 2026-07-30 — Gancho de 3 tiempos (Kallaway) + herramienta de atribución de cambios
**Investigación/fuente:** vídeo [LmXpbP7dD48](https://www.youtube.com/watch?v=LmXpbP7dD48) de `@kallawaymarketing`, verificado con vidIQ antes de darle peso (428k subs, 93 vídeos largos, varios de 500k-2,5M orgánicos, y su tema *es* hooks/storytelling aplicado sobre sí mismo). Comparados sus 6 puntos contra lo que ya teníamos
**Cambio aplicado:** regla **9b** nueva en `SCRIPT_PROMPT`, sin tocar la 9 que ya estaba validada. Lo que faltaba: nuestra regla solo cubría la PRIMERA frase (la pregunta "Why") y luego entraba directo al setup cronológico, perdiendo el giro. Ahora la apertura son 3 tiempos obligatorios: (a) *context lean* = la pregunta "Why" con el hecho concreto primado, (b) *scroll-stop* = UNA frase corta que debe abrir con palabra de contraste (But/Except/Yet/Although), cuyo único trabajo es contradecir lo que el espectador acaba de asumir, (c) *contrarian snapback* = frase que manda la historia en dirección opuesta al lean. Más dos reglas de forma: **staccato** (los tiempos b y c bajo 12 palabras, porque la densidad de valor por palabra importa justo donde la atención es más cara) y **speed-to-value** (un dato concreto real dentro de los primeros ~4s, sin tocar el loop final). Descartado de su lista: *cult hopping* (referencias a celebridades) — es para contenido educativo, no para historias personales. Lint `_check_hook_beats()` en `pipeline.py` que verifica los 3 tiempos, **necesario porque nuestros guiones entran por `--script-file` y no pasan por el prompt**
**Herramienta nueva:** `experiments.py` — cruza `video_log.csv` contra las métricas reales de YouTube (`video_metrics_batch`) agrupando por variante, para poder responder *qué cambio movió la aguja* en vez de suponerlo. Las variantes **se detectan solas** leyendo el `script.json` de cada carpeta (`hook_why`, `hook_3beat`, `split`): no hay que etiquetar a mano ni acordarse de un flag, así que lo que se mide es lo que el archivo realmente contiene y no lo que creíamos haber hecho. Usa medianas, no promedios, porque con pocos vídeos un solo viral distorsiona el promedio
**Los otros dos huecos, cerrados el mismo día:**
- **Recorte de silencios integrado al pipeline** (`--trim-silence`, `--trim-keep`). Medido: edge-tts deja ~0,4s entre oraciones, **9,58s de 68,68s = 13,9% del vídeo era aire muerto**, y en Shorts manda el tiempo absoluto visto. Herramienta suelta `trim_silence.py` para carpetas ya generadas, y `trim_silence_inplace()` dentro del pipeline. **Lo que importa es DÓNDE se llama:** entre la síntesis de voz y todo lo demás, porque los subtítulos y las duraciones de escena se calculan después y así salen ya sobre el eje recortado. Hacerlo al final sobre el vídeo ya armado desincroniza las imágenes hasta 7s (lo comprobamos en el vídeo del 30 jul: subtítulos bien, escenas cada vez más tarde). No lleva los silencios a cero (`keep=0.10`) porque a cero las palabras se pisan y suena peor que el original. Usa `atrim`+`concat` explícito y no `silenceremove`, porque este último no reporta qué intervalos cortó y sin esa lista el remapeo de subtítulos sería a ciegas. El original queda en `voice_raw.mp3`
- **Gancho visual de 3-5 palabras** (`hook_punch`), el punto 2 de Kallaway y el que más recalca: el gancho visual pesa más que el hablado porque se lee más rápido de lo que se oye, y una card de frase entera se lee demasiado despacio para entrar en la ventana que decide el swipe. Añadido al `SCRIPT_SCHEMA` **en `properties` Y en `required`** — con `additionalProperties: False` un campo que solo esté en uno de los dos se descarta en silencio, que es exactamente el bug que tuvo `style` y por el que un vídeo salió sin estilo
**Dónde se publicó:** pendiente. Tres variantes ya generadas y listas para el A/B: `hook:libre + split` (29 jul), `hook:why + split` (30 jul), `hook:3beat + split` (30 jul)
**Qué esperamos ver:** "se quedaron para mirar" subiendo del 54,8% medido hacia el 70%+. **Aviso honesto de método:** con 1 vídeo por variante esto no distingue señal de ruido — hacen falta 3-5 por variante antes de concluir nada, y `experiments.py` avisa cuántos hay con datos por eso mismo

## 2026-07-29 — Stress-test del pipeline: Pexels devuelve metraje aleatorio y miente en la resolución
**Investigación/fuente:** harness de stress-testing propio (31 casos límite sobre TTS, subtítulos, Pexels, música y hook card), escrito tras el rechazo del usuario a un vídeo por "edición horrible" y clips que no pegaban con la historia. Artefactos en scratchpad de sesión, fuera de `output/`
**Cambio aplicado:** dos avisos nuevos en `_pexels_download` de `pipeline.py`, ninguno bloqueante (la API sigue fallando suave por diseño). (1) **Relevancia:** Pexels NUNCA falla por una query sin sentido — `"xzqvblorptronic nonexistent gibberish 9999"` descargó un render 3D abstracto y la función devolvía `True` como si hubiera acertado; ése es el mecanismo real detrás de "los clips no pegan con la historia", porque un `search_term` mal redactado no da error, da metraje aleatorio y el log dice `[media] clip N/12` igual. Ahora `_pexels_relevance()` cruza las palabras significativas del término (con lista de stopwords, porque "close up" aparece en todos) contra el slug de la URL y los tags, y avisa cuando el solapamiento es cero. (2) **Resolución:** los metadatos de Pexels mienten — el archivo `7299471-hd_1080_1920_30fps.mp4` declara 1080x1920 en el JSON y en su propio nombre, pero el stream real es 720x1280, así que se reescalaba hacia arriba y perdía nitidez sin que nada lo dijera. La comprobación se hace ahora con `ffprobe_resolution()` sobre el archivo YA descargado, nunca sobre el JSON
**Dónde se publicó:** aplica desde el próximo vídeo generado; ningún vídeo existente se rehace (regla de mejoras solo hacia adelante)
**Qué esperamos ver:** que los clips que no corresponden al guion se detecten en el log durante la generación en vez de descubrirse viendo el vídeo terminado. Limitación conocida: el aviso de relevancia da falso positivo con `search_terms` en español (los slugs de Pexels son en inglés), irrelevante mientras los guiones los escriban en inglés
**Lo que sí resistió:** TTS + subtítulos karaoke pasaron 9/9 casos límite (emoji en el texto, `ñ`, puntuación agresiva `--`/`?!`/comillas, palabra única, `$4,500.99`/`300%`/`#wild`) sin un solo evento vacío en el `.ass`; el fallback de música y Lyria con key inválida degradan limpio

## 2026-07-28 — Investigación: el largo faceless y la línea "dinero"
**Investigación/fuente:** vídeo de automatización de YouTube (`a1zBbJ1A22k`, funnel de venta de una academia — la tesis es válida, las cifras de ingresos están infladas ~5x) + verificación de cada canal con vidIQ
**Cambio aplicado:** ninguno en código todavía; es research validado con datos. Tres hallazgos: (1) los dos canales de referencia — `@behindthethroneofficial` (13,1k subs, 13 vídeos, 40-45 min, pico de 290k vistas, +182% vistas y +42% subs en 30d) y `@thedarkhorizonyt` (35,6k subs, 24 vídeos, 16 min, 265k de media) — usan EXACTAMENTE la plantilla Black Tom en largo: icono famoso + consecuencia brutal concreta ("Lincoln's First Lady — Locked in an Asylum by Her Own Son"), imágenes de stock, sin cara, cero Shorts. (2) El nicho de economía tiene el RPM más alto pero saturado como explicación pura: `@theforgottenfortunes` 33 vídeos → 915 vistas TOTALES, `@wheninhistorycreations` 32 vídeos → 1.300 de media. Lo que sí crece es el mismo material contado como relato: `@truthfinance0.1` 18 vídeos → 261k de media, +31% en 30d. (3) De ahí la línea "dinero" para HiddenFacts (Enron, crack del 29, Madoff, Weimar, Bre-X): misma fórmula, mismo motor, pero cae en el pool de anunciantes de finanzas
**Dónde se publicó:** pendiente — decisión de formato largo sin tomar; la línea "dinero" se puede probar ya en Shorts con la fórmula actual
**Qué esperamos ver:** si se hace largo, RPM de 4-10 USD frente al de Shorts y una vía de ingresos que no depende del feed; en la línea "dinero" dentro de Shorts, si los temas financieros retienen igual que los bélicos/espionaje

## 2026-07-27 — Diagnóstico del derrumbe + guardas de publicación
**Investigación/fuente:** YouTube Analytics día a día y por fuente de tráfico, tras notar que las vistas se habían desplomado
**Cambio aplicado:** medido: el feed de Shorts pasó de 31.441 vistas (14-20 jul) a 2.123 (21-23 jul), −93%, con SEIS vídeos cayendo el mismo día — señal de canal, no de contenido. Única variable que cambió: publicación manual desde Studio (el mismo vídeo subido 4 veces + 10 vídeos publicados el 23 jul, cinco en hora y media). Acciones: 6 duplicados a privado (no borrados), calendario rehecho a 1/día 06:00 UTC, `_check_duplicate_title` en `youtube_api.py` que bloquea subir un título ya existente, y `BEST_HOUR = 6` medido con los datos del propio canal (mediana 1.234 vistas a las 05-07h vs 158 a las 20h)
**Dónde se publicó:** 27-31 jul, uno diario a las 06:00 UTC
**Qué esperamos ver:** recuperación progresiva de la distribución del feed a partir del día 3-7 si la causa era el patrón de publicación; si no se mueve en una semana, la causa era otra y hay que buscar en contenido

## 2026-07-27 — Métricas de Shorts 2026 hardcodeadas + arreglo de duración
**Investigación/fuente:** investigación de benchmarks 2026 (watch time desplazó al swipe rate como factor principal)
**Cambio aplicado:** fijado en código porque son umbrales de reparto, no preferencias: suelo duro de 15s en `upload_video` sin escape posible (los Shorts por debajo dejaron de repartirse en 2026 aunque tengan 100% de retención — explica los ultracortos del canal con ~1.400 vistas y CERO subs), punto dulce 30-45s, retención >70% dispara reparto amplio. Además se corrigió el prompt, que pedía 110-130 palabras / 40-50s y producía vídeos de 40s contradiciendo el mínimo de 60s del canal → ahora 190-200 palabras
**Dónde se publicó:** aplica desde el próximo vídeo generado
**Qué esperamos ver:** vídeos de 60s reales; los ultracortos quedan bloqueados de raíz

## 2026-07-27 — Loop obligatorio + plantilla Black Tom (la regla con mejor evidencia)
**Investigación/fuente:** retención avanzada de los 4 últimos vídeos, comparando el que hace 156% de reproducción contra los que no
**Cambio aplicado:** el vídeo de Black Tom sostiene 3,76 → 2,89 de ratio de audiencia (se ve ~3 veces entero); Orden 227 cae a 0,95 y Auschwitz a 0,08. La estructura de los tres era casi idéntica, así que la diferencia son tres cosas, ahora reglas duras en el prompt y en la skill: (1) ancla en un ICONO famoso reconocible al instante, (2) consecuencia SIGUE VISIBLE HOY, (3) loop léxico y visual — última frase con las mismas palabras del gancho y último `search_term` encadenando con el primero. Corolario: retirado el cierre de franquicia (`CLOSE_TAIL = 0`), que ocupaba 3,7s tras la última palabra anunciando el final justo donde el bucle debe ser invisible
**Dónde se publicó:** aplica desde el próximo guion; validado en el vídeo de la Torre Eiffel (primera y última frase idénticas)
**Qué esperamos ver:** más vídeos con reproducción >100%, que es la señal de retención más fuerte que premia Shorts

## 2026-07-27 — Los 2 primeros segundos + capa visual del motor
**Investigación/fuente:** "se quedaron para mirar" 43,9% en Studio (por debajo del 60% donde colapsa el reparto) + benchmarks de gancho 2026 + análisis de tres canales de motion graphics con Remotion
**Cambio aplicado:** sin cold-open (`COLD_FRAMES = 0`) porque los benchmarks son explícitos en que no debe haber intro/logo/música antes de la voz; frame 0 en movimiento (escena 1 abre en ×1.34 y se abre en 0,5s, un frame estático es objetivo de scroll); promesa escrita completa desde el frame 0 vía `HookText` (el caption karaoke aún no ha dicho nada cuando el espectador ya decidió). Capa visual: 6 transiciones de corte rotativas en vez de una sola repetida, boil de fondo (jitter de 1-2px que simula animación a mano), y biblioteca de efectos greenscreen reales (fuego/agua/humo/etc, 10 categorías desde Pixabay, chromakey a alpha, cacheadas de por vida) que se insertan solas según lo que narre cada escena. Se probó y se retiró la sombra proyectada: sobre el papel claro salía como un borrón
**Dónde se publicó:** aplica desde el próximo vídeo generado
**Qué esperamos ver:** "se quedaron para mirar" subiendo del 43,9% hacia el 60-70%; es la métrica que decide si el vídeo se reparte

## 2026-07-23 — MOTOR "ARCHIVO VIVO": giro visual 180° completo (Remotion)
**Investigación/fuente:** rechazo del usuario al look slideshow + entrevista de gustos (collage documental + vector animado + cartoon vivo, sepia evolucionado, ritmo punchy) + análisis video-vox/Extra History/repos Remotion oficiales
**Cambio aplicado:** motor completo en `motion_graphics/src/archivo/` + `archivo_engine.py` + `visual_cache.py`: tablero pergamino sin blur, sticker troquelado vs foto clavada (regla por cobertura rembg 0.08), censura CLASSIFIED que se rasga, hilo rojo de conspiración, zoom-evidencia, impact frames, flips 3D, fichas de personaje, globo 2.5D, latido ambiente, mapa antiguo vivo (arrugándose), cold-open censurado, typewriter, SUBSCRIBE stamp, cierre CASE #N + share-card, captions cinéticos con timestamps reales del TTS. Skills oficiales de Remotion instaladas. Test: Dollfuss regenerado completo (63s) con costo API cero
**Dónde se publicó:** pendiente — los videos del 24-26 jul son el A/B del sistema viejo; el primer video Archivo Vivo será el siguiente (plan: Orden 227 de Stalin en 2 partes, 27-28 jul)
**Qué esperamos ver:** salto en retención/compartidos vs el promedio del canal y vs los 3 videos del sistema viejo — la comparación A/B más importante desde que existe el canal

## 2026-07-22 — Serialización estilo Extra History (series + cadencia + 2 partes)
**Investigación/fuente:** análisis con datos reales de youtube.com/@extrahistory (4,59M subs): sus Shorts van todos con marca de serie, su long-form es numerado por partes, y su bio promete cadencia ("Join us Saturdays")
**Cambio aplicado:** 3 adopciones en la skill canal-hiddenfacts: (1) marca de serie visible en título/card espejando playlists ("WWII Secrets #14"), (2) promesa de cadencia en cierre + bio ("A new historical secret every day", pendiente one-time en Studio), (3) FORMATO #21 en FORMATOS_A_PROBAR.md: historia en 2 partes con cliffhanger, parte 2 a las 24h
**Dónde se publicó:** aplica desde el próximo video; el test de 2 partes es el próximo experimento prioritario
**Qué esperamos ver:** subs/1k vistas por encima del 0,12% actual — las tres palancas dan "razón de volver", que es exactamente lo que el diagnóstico marcó como faltante

## 2026-07-22 — Radar de temas (`topic_radar.py`) para elegir QUÉ producir
**Investigación/fuente:** pedido del usuario de "temas con más probabilidad de viralizar / trends del momento"; reencuadre propio: para Shorts el feed manda (96,7% del tráfico), así que la palanca es resonancia + frescura, no SEO de keywords
**Cambio aplicado:** nuevo `topic_radar.py` que cruza efemérides de Wikipedia (On this day, API gratis sin auth) con los criterios validados del canal (villano nombrable +4, tema del nicho, aniversario redondo, penaliza saturados) → shortlist rankeada. Matcheo por límite de palabra (`\b`) para no confundir "cia" dentro de "official/Valencia"; pausa entre requests por rate-limit. Slot `--outliers` para enchufar la señal de vidIQ (la más fuerte) cuando esté conectado. Integrado como paso `/canal radar` en la skill canal-hiddenfacts
**Dónde se publicó:** herramienta de pre-producción; se corre antes de cada video/tanda
**Qué esperamos ver:** temas con ventaja de timeliness (secreto histórico en su aniversario de la semana) en vez de elegir a dedo de topics.txt; validar si suben vistas vs. temas sin timeliness

## 2026-07-22 — Pop de escala en la palabra activa del caption
**Investigación/fuente:** análisis del sistema video-vox (Santiago Munoz) + template-tiktok de Remotion — la firma de los captions estilo TikTok es que la palabra hablada crece, no solo cambia de color
**Cambio aplicado:** `_CAP_ACTIVE` en `generate_subtitles()` ahora suma `\t(0,90,\fscx113\fscy113)` — la palabra activa sube a 113% en 90ms y se sostiene mientras se pronuncia (el color amarillo ya existía); verificado con render de prueba que crece y no rompe el layout ni a mitad de línea
**Dónde se publicó:** pendiente (aplica a todo video de acá en adelante)
**Qué esperamos ver:** más fijación de mirada en la palabra hablada para el ~50% que ve en mute y no-nativos (meta de alcance universal); mejora de comprensión, no decoración
**Nota:** primero se descartó el SFX en el pop del sticker por la regla de SFX diegético, pero el usuario lo reconsideró — ver la entrada de abajo (misma fecha): se distinguió "SFX narrativo decorativo" (prohibido) de "sonido de edición/collage" (permitido y motivado por la estética de recortes).

## 2026-07-22 — Capa de sonido de entrada de sticker (opt-in, `--sticker-sfx`)
**Investigación/fuente:** reconsideración del usuario tras el análisis de video-vox — se distinguió "SFX narrativo decorativo" (que `pick_sfx_cues` prohíbe con razón) de "sonido de edición/collage" (otra categoría, motivada por la estética de recortes de papel que ya usan los stickers)
**Cambio aplicado:** flag `--sticker-sfx` en `pipeline.py` que mezcla un swish de papel suave (`Paper___book_ManualTurnPage_AP1.1244.mp3`, configurable con `--sticker-sfx-file`) en el frame exacto del pop de cada sticker; volumen bajo (0.16), capa SEPARADA de `pick_sfx_cues`, se omite entero si el `music_mood` es sombrío. Verificado: el sonido aterriza en cada cue (−21 a −16 dB) y las zonas sin cue quedan intactas
**Dónde se publicó:** pendiente — es opt-in para A/B (2-3 videos con y sin, decide oído + retención/shares)
**Qué esperamos ver:** más "juiciness" de audio → retención marginalmente mayor; validar por A/B, no asumir

## 2026-07-22 — Variedad de movimiento Ken Burns (paneos direccionales)
**Investigación/fuente:** feedback visual del usuario — las escenas se sentían clonadas; el zoompan solo alternaba zoom-in/zoom-out y ambos centrados
**Cambio aplicado:** `_static_image_clip()` en `pipeline.py` ahora rota entre 6 movimientos por escena (`move=i`): zoom-in/out centrado + 4 paneos (izq→der, der→izq, arriba→abajo, abajo→arriba) con zoom fijo 1.12 para no mostrar borde negro; verificado con imagen sólida que ningún paneo deja esquina negra
**Dónde se publicó:** pendiente (aplica a todo video generado con `--nanobanana`/`--seedream` de acá en adelante)
**Qué esperamos ver:** menos sensación de "escenas iguales", más energía visual escena a escena sin romper el ritmo de cortes secos


**Investigación/fuente:** revisión rutinaria de duración video vs. audio real
**Cambio aplicado:** `-c copy` sin keyframe en el wipe de entrada rompía el concat; fix reencodeando ese segmento
**Dónde se publicó:** afectó 4 videos ya programados (borrados a tiempo, todavía privados)
**Qué esperamos ver:** N/A — bug de integridad, no de rendimiento

## 2026-07-20 — Formato "solo lectura" (sin narrador, card de texto denso)
**Investigación/fuente:** TubeBuddy — análisis de retención >100% en shorts <30s, técnica de loop narrativo
**Cambio aplicado:** nuevo modo `card_duration` + `silent_card_mode` en `pipeline.py`: sin voz, sin música propia, texto denso que no se termina de leer en un pase
**Dónde se publicó:** Navy Blimp L-8, Toynbee Tiles, Kaspar Hauser (programados 22 jul)
**Qué esperamos ver:** retención/loop más alto que el ultrashort narrado (que tuvo resultados bimodales, 3/12 rompieron 1K y 9/12 flopearon)

## 2026-07-20 — Criterio de guion: misión clara + villano nombrable
**Investigación/fuente:** análisis propio de top videos 28d — "Operation Flipper" (Rommel) tuvo 99% retención vs. 48-77% del resto
**Cambio aplicado:** nueva regla en `criterio-guiones-post-analisis-28d` (memoria) — priorizar hechos con una sola misión/objetivo nombrado
**Dónde se publicó:** Operation Foxley, Operation Anthropoid, Operation Cicero, Operation Long Jump
**Qué esperamos ver:** retención más alta que el promedio del canal (~50%) en estos 4 videos vs. guiones sin esa estructura

## 2026-07-20 — Bug de configuración: idioma del canal HiddenFacts en español
**Investigación/fuente:** video de TubeBuddy sobre 11 configuraciones de canal + auditoría manual en Studio
**Cambio aplicado:** canal corregido a inglés en Studio; `youtube_api.py` ahora fuerza `defaultLanguage`/`defaultAudioLanguage` explícito por video (no depende más del ajuste de canal)
**Dónde se publicó:** todos los uploads de HiddenFacts desde este fix en adelante
**Qué esperamos ver:** mejor clasificación/recomendación por idioma real del contenido (difícil de medir directo, efecto de fondo)

## 2026-07-21 — Prototipo de motion graphics con Remotion (íconos + page-flip)
**Investigación/fuente:** 4 shorts de referencia del usuario (transiciones, íconos animados, texto kinético) + investigación de licencia/viabilidad técnica de Remotion
**Cambio aplicado:** proyecto Remotion nuevo (`motion_graphics/`) con overlay de ícono+texto kinético (spring bounce) y transición page-flip 3D real; compuesto sobre un video vía ffmpeg
**Dónde se publicó:** prototipo en escritorio, NO publicado todavía (`Operation Long Jump`)
**Qué esperamos ver:** pendiente de validar con el usuario si escala a los 9 cortes del video antes de medir cualquier efecto en retención

## 2026-07-21 — Related video manual + música con arco de tensión
**Investigación/fuente:** video externo verificado con vidIQ (305K vistas reales, crecimiento orgánico, 2 años de vida) — consejos de composición/edición/leverage
**Cambio aplicado:** 2 items nuevos en checklist de la skill `canal-hiddenfacts` (`/canal publicar` y `/canal guion`): vincular related video a mano en el Video Element (confirmado que no existe vía API), y formalizar que `music_mood` describa un arco de tensión creciente en vez de un mood plano
**Dónde se publicó:** pendiente (aplica a partir del próximo lote de guiones/subidas)
**Qué esperamos ver:** más tiempo de sesión por espectador (related video) y mejor retención en el tramo final del video (arco de música) — validar en la próxima auditoría, ambos son cambios de bajo costo así que no urge medir aislado

## 2026-07-21 — Matiz del anti-hook: puro vs con ancla verbal
**Investigación/fuente:** creador externo (canal de coaching, cifras de "imperio de canales" NO verificables y descartadas) — pero la técnica hook/anti-hook en sí es real y coincide con lo que ya usamos, confirmado por 3 fuentes independientes ya
**Cambio aplicado:** refinada la regla de in-media-res en `RETENTION_CHECKLIST.md` — anti-hook puro solo cuando la primera imagen es autoexplicativa; nuestro contenido necesita 3-6 palabras de acción cruda + ancla verbal con dato concreto (fecha/nombre) inmediatamente después
**Dónde se publicó:** pendiente (regla de escritura, aplica al próximo guion nuevo)
**Qué esperamos ver:** ningún cambio de vistas medible por sí solo (es un ajuste fino de un patrón que ya usábamos bien) — sirve como criterio explícito para revisar guiones futuros, no como experimento a medir aislado

## 2026-07-21 — Test: 5 videos/día bien espaciados vs. techo diario ~6K
**Investigación/fuente:** dato propio (18 jul, lote de 12 en ráfaga sumó solo 6,529 vistas totales, mayoría en 0-view jail) + pregunta del usuario sobre si hay un techo diario real independiente de la cantidad de videos
**Cambio aplicado:** 5 guiones nuevos (Fortitude, Rabat, Bernhard, Doctors' Plot, Exploding Cigar) programados el mismo día, espaciados exactamente 3h, dentro de la franja 01:00-13:00 UTC
**Dónde se publicó:** 23 jul 2026, HiddenFacts (kF25Duv1Vhk, wzYvbe4QvCQ, ylwPDDcQETY, i-RsT33tc4o, qSPxdEZ3Jf0)
**Qué esperamos ver:** si el total del día se mantiene ~6K (confirma techo diario real) o sube por encima de eso (confirma que el problema anterior era la ráfaga de 35min, no la cantidad) — comparar contra el 18 jul y contra días de 1-2 videos

## 2026-07-21 — Motion graphics: collage de foto real + fixes de transparencia/colisión

- Fix real: `--props` sin `.resolve()` hacia que la ruta de props de Remotion
  dependiera del cwd por casualidad (afectaba tanto a AutoOverlay como al
  collage nuevo); corregido en ambos call sites.
- Fix real: el sticker de icono+SFX (AutoOverlay) caía sobre la banda de
  subtítulos karaoke (MarginV 640) y duplicaba la palabra que el caption ya
  resaltaba; reescrito como sticker de papel + flecha punteada, confinado a
  la franja superior segura (y 0.16-0.44).
- Nuevo: `add_real_photo_collage()` — foto real recortada (estilo "recorte de
  periodico") vía Wikimedia Commons (licencia libre explícita, nunca
  scraping con copyright), `rembg` para el recorte, halftone B/N, halo
  dorado, sello DECLASSIFIED, deriva horizontal continua. Activado por el
  campo opcional del guion `collage_subject` (+ `collage_time` opcional).
- Fix real: el overlay corto (.mov de ~2.4s) arrancaba su propio timeline en
  t=0, así que al llegar el timestamp real de inserción (ej. t=10s) el
  stream ya estaba agotado y el collage nunca aparecía — corregido con
  `setpts=PTS+t0/TB` antes del `overlay`.
- Nuevo: heurística anti-foto-grupal (`_is_single_subject`, conteo de blobs
  conectados en el canal alpha del recorte) — prueba hasta 12 candidatos de
  la búsqueda y descarta automáticamente fotos con más de una persona, sin
  curación manual del término de búsqueda (pedido explícito del usuario:
  automatización 100%, "si no no tiene chiste y contrato un editor de video").

## 2026-07-23 — Suite vidIQ por HTTP directo: gate de títulos + outliers en vivo

- Problema: el MCP de vidIQ exige re-auth OAuth y sus tools no cargan en
  sesiones continuadas — el gate obligatorio de títulos quedaba bloqueado.
- Nuevo `vidiq_tools.py`: cliente JSON-RPC directo contra mcp.vidiq.com/mcp con
  la API key (gitignored). Subcomandos: balance / outliers / xoutliers (TikTok+IG
  con análisis de hook 0-3s) / watch (desglose escena por escena) / transcript /
  similar / comments / radar-terms.
- `topic_radar.py --outliers auto`: capa de outliers en vivo (YouTube +
  TikTok/IG) sin archivo manual; los temas que matchean suben +3 [OUTLIER].
- Gate aplicado a los 5 programados (24-28 jul): títulos 92→95, 90→90, 89→91,
  88→93, 84→92 (híbrido "sugerencia top | Marca de Serie"; la marca resta 2-4
  puntos pero la serialización manda). Descripciones/tags reescritos con
  keyword_research: "world war 2" (580k/mes) > "wwii", #historyfacts (331k/mes)
  > #hiddenfacts, "USS Indianapolis" (56k/mes) añadido.
- Dato clave de channel_performance_trends: mediana 4 vistas a las 12h, despegue
  día 2-7 → ningún veredicto A/B antes del día 3 (regla en skill /canal audit).

## 2026-07-23 — Recorte troquelado: BiRefNet + limpieza de alfa

- Feedback usuario: "la idea (sticker troquelado) es increíble, la ejecución no" —
  bordes dentados, halo amarillo y cabezas flotantes con el rembg u2net por defecto.
- Comparación real de 3 modelos sobre escena con persona: u2net (halo amarillo en el
  pelo, cov 0.36), u2net_human_seg (recorta de más, cov 0.11), birefnet-general
  (bordes crujientes, captura cuerpo completo, cov 0.39). Ganó BiRefNet.
- `visual_cache.cached_cutout` ahora usa birefnet-general (override REMBG_MODEL),
  sesión reusada, modelo en la clave de caché, y `_clean_alpha` erosiona 1px el
  canal alfa (mata la franja fantasma) + anti-alias. CPU ~30-60s/imagen pero se
  cachea de por vida. Validado sobre pergamino: silueta limpia, sin halo.

## 2026-07-23 — Capa de ACCION: lo narrado se actúa en pantalla

- Feedback usuario: "las acciones no quedan claras; me gustaría que lo que dice
  se acompañe de una representación visual" + "no vi animaciones 3D".
- `actionMotion` (components.jsx): el recorte de pose fija se transforma según el
  verbo — explosion/impact (sacude + salta en Z), recoil, topple (se voltea),
  flee (se desliza fuera), sink (se hunde), rise, shoot/lunge. El salto en Z
  (translateZ) hace el 3D visible en los golpes.
- `ActionFX`: FX de cómic sincronizado — estrella de impacto dorada, palabra
  BANG/BOOM/CRASH (SOLO en impactos, elección del usuario), líneas de velocidad.
- Sacudida de cámara en el golpe. `Cutout` acepta action={}.
- `archivo_engine._detect_action`: escanea narración + search_term de cada escena,
  detecta el verbo y engancha la acción al frame en que se dice (sincronía con la
  voz). Override manual: 'action' en visual_beats del JSON. Selectivo (no dispara
  en frases sin acción). Validado contra frases reales de los guiones.
- Aplicado por re-render a Pilecki y Orden 227 (junto con BiRefNet + marginalia).
  Black Tom queda como estaba (decisión usuario).

## 2026-07-24 — Fotos reales de archivo en el motor + fixes de acción

- Feedback usuario: el motor no mostraba fotos reales (solo estaban en el pipeline
  clásico). Reintroducidas: `EvidencePhoto` (foto B&N clavada con chincheta + sello
  "REAL <año>"), `archivo_engine._fetch_real_photo` (Wikimedia, prefiere dominio
  público, cachea por query, reintenta ante 429), `_auto_subject` (nombre propio
  del título) o `real_photo` explícito en el JSON. Proof validado: Castro (foto real
  del discurso) y Bikini (foto real del estallido Baker 1946 junto a la caricatura).
- Fix detección de acción: substring rompía ("fleet"→flee, "falling"→fall, "wide
  shot"→shoot). Ahora regex con límites de palabra y SOLO desde la narración
  (no search_terms, que traen términos de cámara).
- Video nuevo: "The Nuclear Bomb Test That Named Your Swimsuit" (Bikini/Crossroads,
  radar [OUTLIER] 80 aniv), programado 31 jul 01:00 UTC.

## 2026-07-24 — Parallax multiplano 2.5D + push-in + atmósfera (in-engine)

- Pedido usuario: parallax "increíble". Research: multiplano (capas a distinta
  velocidad) + cámara push-in + atmósfera; DepthFlow (2.5D real por mapa de
  profundidad) descartado por ahora (necesita GPU, pipeline nuevo, choca con
  estabilización) → queda como tier fotorreal futuro post-A/B.
- Route A (código puro Remotion, reversible): `parallaxDepth` diferencia el ritmo
  de cada capa por profundidad (fondo 0.12 / GroundCard 0.55 / recorte 1.0);
  `makeCamera` con deriva + push-in continuos de base; `Atmosphere` (motas de
  polvo con parallax, barrido de luz, pulso de viñeta, sin blur).
- Proof aprobado ("así está perfecto"). Aplica SOLO de aquí en adelante (no
  re-render de los programados; Black Tom queda como está; respeta el A/B).

## 2026-07-24 — Vida secundaria del personaje (respiración + balanceo)

- Pedido: animar articulaciones de los personajes. El parallax NO sirve para eso
  (mueve capas planas, no dobla codos). Rigging 2D real descartado (habría que
  segmentar cada PNG generado por IA → no automatizable). IA image-to-video
  (Kling/Hailuo) queda como tier hero post-A/B (créditos, render lento, rompe la
  estética de troquelado, riesgo desmonetización).
- Opción 1 elegida (aprobada "me gustó"): movimiento secundario procedural en el
  Cutout — respiración squash/stretch + balanceo + micro-wobble, pivotando desde
  los pies. Ilusión de vida sin articular, se compone sobre parallax + acción.
  Fijo en el motor para próximos videos (no re-render de programados).

## 1 ago 2026 — Regla 9 reescrita: el gancho se AFIRMA, no se pregunta

**Investigacion.** Estudio de los narradores orales que mejor sostienen atencion
(Garcia Marquez, "Cronica de una muerte anunciada", Chekhov) + diagnostico del
guion de Minecraft, donde la retencion medida se caia entre el segundo 3 y el 8.

**Causa encontrada.** El gancho contenia su propia respuesta: "My dad rebuilt the
same house forty times **because he could not remember he had already built it**".
La subordinada causal cierra el misterio en el segundo 3. A partir de ahi el
video no le debe nada al espectador y todo lo demas es ampliacion, no tension.
Eso explica la caida mejor que cualquier hipotesis de ritmo o de edicion.

**Cambios en codigo.**
- `SCRIPT_PROMPT` regla 9 reescrita entera. Antes: "la primera palabra es Why,
  obligatorio en guion/titulo/hook_card". Ahora: hecho imposible AFIRMADO en
  seco, con (a) cero adjetivos, (b) un dato concreto dentro de la frase — el
  "prime" del hueco de informacion, que ya estaba en la regla vieja y se
  conserva — y (c) un segundo tiempo plegado dentro. Prohibido explicitamente
  resolver el gancho dentro del gancho. Se añade que anunciar el final esta
  permitido y suele ser mejor: la curiosidad por el COMO aguanta 90s, la del
  QUE se gasta en diez.
- `_check_why_opening` -> `_check_open_hook`. Ahora avisa de tres cosas: abrir
  con pregunta, primera frase auto-resuelta (`_RESUELVE_HOOK`), y primera frase
  sin ningun dato concreto. Vive en codigo y no solo en el prompt porque los
  guiones a mano entran por `--script-file` y no pasan por Claude.
- Subtitulos: keywords en rojo (`_CAP_RED`) leidas de `caption_keywords`. Con
  `SUB_CHUNK_WORDS = 1` la palabra activa es la unica en pantalla, asi que el
  amarillo era el 100% del texto y habia dejado de ser jerarquia. Objetivo ~5%
  del guion en rojo. ONE/TWO/THREE quedan fuera del auto-rojo: en ingles son
  relleno gramatical y solas subian el resaltado del 7,4% al 10,6%.
- `counter_overlay.py` nuevo: contador HUD con claves `t=valor` arbitrarias,
  interpolacion lineal truncada y color de acento en el valor final.

**Donde se aplico.** `scripts/grandmother-recipes.json` ->
`output/2026-08-01-grandmother-recipes-wrong/video.mp4` (83,9s, 1080x1920).
Ademas del guion: dos pausas de silencio real insertadas DESPUES del recorte de
silencios (0,55s antes de "Mine had seven", 0,65s antes de "Elena had not
spoken"), cada una con un golpe grave (`enfasis` pasado por `lowpass=300`) y
desaturacion del fondo a 0,15 durante exactamente esos milisegundos. Medido:
saturacion 74-96 -> 16 en los dos beats. El contador CARDS 01/31 aterriza en
31/31 justo sobre la palabra ELENA.

**Hipotesis a medir.** Si la causa era el gancho auto-resuelto, la curva del
segundo 3 al 10 deberia aplanarse. Es lo unico que valida o tumba este cambio;
sin `experiments.py` contra Analytics (token caducado) sigue siendo oficio, no
dato.

## 4 ago 2026 — KOREX: voz humana, Gemini fuera, generacion local y consistencia por reutilizacion

**Investigacion.** Fabian: "la ultima en espanol se escucha super robotica como si
no fuese usado chaterbot". Era literal: `generate_audio` solo enrutaba a Kokoro
(prefijos `em_`/`am_`...) o a edge-tts, asi que TODO guion en espanol caia en
`es-US-AlonsoNeural`. Chatterbox llevaba meses en `tools/` y solo lo llamaba
`viral_lab.py`.

**Cambios.**
- `pipeline.py`: prefijo `cb_es`/`cb_en` -> `_chatterbox_tts()`. Chatterbox no
  devuelve timestamps, asi que se alinea con whisper (`_align_words`, en GPU).
- **`_snap_to_script()`** — bug introducido y corregido el mismo dia: los
  subtitulos se armaban con lo que whisper TRANSCRIBIA, no con el guion, y en
  pantalla aparecian palabras que el narrador no dijo. Ahora el audio manda el
  timing y el guion manda el texto (alineacion por difflib, huecos repartidos).
- **Voz, elegida de oido en tres iteraciones.** (1) Clonar una muestra de edge-tts
  a `exaggeration 0.3` seguia sonando a robot; con **0.45 + cfg 0.3** paso a sonar
  humano — el problema eran los parametros, no el origen sintetico de la muestra.
  (2) Kokoro `em_santa` gusto pero **las voces `em_*` son de Espana** y el acento
  viaja con el timbre. (3) Timbre final `es-MX-JorgeNeural` (base del "espanol
  neutro" de doblaje) en `assets/voice_refs/es.wav`.
- **Gemini eliminado del repo** a pedido explicito: Nano Banana, Lyria, Veo y
  `--flow` fuera de `pipeline.py`, `sticker_library.py` y `rankings.py`;
  `gemini_usage.json` borrado. Sobrevive solo en `viral_lab.py` (analisis de
  video, sin reemplazo equivalente) con caida a `--engine claude`.
- **`comfy_client.py`** — ComfyUI local con **FLUX.1-schnell**, elegido sobre
  FLUX.1-dev porque dev es *non-commercial*: mismo criterio que dejo fuera a
  XTTS-v2 para la voz. Flag `--comfy`. Es la unica via de imagen que queda: PiAPI
  devuelve `insufficient credits` y Gemini ya no existe.
- **`kx_assets.py` / `kx_cast.py`** — fondos y poses cacheados por clave
  SEMANTICA, no por hash de archivo (`visual_cache` cachea derivados; aca lo que
  se cachea es una generacion). Dos videos que mencionen la bolsa comparten
  literalmente el mismo escenario.

**Consistencia de personaje: se descarto el camino obvio.** IP-Adapter y FLUX
Redux estaban sobre la mesa; Redux es non-commercial y SDXL+IP-Adapter costaba
~10GB de pesos para dar un personaje *parecido* en cada escena. El contact sheet
del video anterior mostro el problema real: **Tadeo salia pardo, gris, crema y
tostado dentro del MISMO video**, y eso con Seedream usando imagen de referencia.
Como el motor ya compone al personaje como recorte sobre el set, la consistencia
perfecta sale de reusar el mismo PNG. 33 dibujos de Flow en 10 poses, con
variantes por pose para que no quede congelado, rotadas por indice de escena
(determinista: dos renders del mismo guion deben ser comparables en un A/B).

**Donde se aplico.** Nada renderizado todavia: los tres intentos de
`scripts/korex-interbolsa.json` murieron por falta de imagenes (Gemini 429, luego
PiAPI sin saldo), no por el motor. La voz de 63s si quedo, cacheada por hash.

**Hipotesis a medir.** Que un personaje recurrente e identico entre videos abra
la puerta al nivel 5 del "dopamine ladder" (afecto por el mensajero) que un canal
faceless no alcanza — la explicacion mecanica del cuello medido el 22 jul: 0,12%
de vista->sub con retencion sana. Sin datos aun; es oficio, no dato.
