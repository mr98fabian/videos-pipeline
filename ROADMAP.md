# ROADMAP — Mapa completo de mejoras del canal

Basado en investigación de mercado (julio 2026): algoritmo de Shorts, competencia en finanzas,
calidad de voz, estilo visual y políticas de monetización. Cada mejora indica **por qué**
(con el dato que la respalda), **cómo** implementarla en el pipeline, y su **prioridad**:

- **P0** — antes de publicar los primeros 10 videos (impacto directo en retención)
- **P1** — primeras 4-6 semanas, cuando ya hay datos de analytics
- **P2** — cuando el canal pruebe tracción (>1K subs o un video >100K views)

---

## 0. Reglas del juego 2026 (lo que dicta todo lo demás)

Datos clave del algoritmo que cambian decisiones de diseño:

| Dato (2026) | Implicación para nosotros |
|---|---|
| Retención >65% en Shorts <30s, >50% en 30-60s para distribución amplia | Nuestro target de 40-50s es correcto; el guion debe sostener 25+ segundos |
| Shorts <15s colapsaron en alcance (no pasan la barra de watch time absoluto) | Nunca publicar por debajo de ~30s |
| La decisión de swipe ocurre en el **primer 1 segundo**, no en 3 | El primer frame + primera frase son el 50% del juego |
| Solo vistas completas y **rewatches** cuentan; el loop (cierre que conecta con el inicio) es la palanca #1 | El "cierre en eco" ya está en nuestro prompt — mantenerlo y medirlo |
| Encuestas de satisfacción pesan más que watch time bruto (confirmado por YouTube feb 2026) | Nada de clickbait que el guion no cumpla; valor real y específico |
| Comentarios pesan más que suscripciones en el feed de Shorts | Terminar con una pregunta que provoque respuesta, no solo "follow" |
| **Bonus de audio original** (marzo 2026): voz propia > audio trending para canales <50K subs | Nuestra voz TTS consistente ya califica; añadir música NO trending |
| 85%+ de vistas sin sonido | Subtítulos quemados: ya los tenemos; hacerlos aún más legibles |

**Riesgo de monetización (crítico):** desde dic 2025 YouTube borró ~16 canales / 35M subs por
"AI slop". La regla de riesgo: *"si otro canal puede recrear tu video en una tarde, estás en
zona de peligro"*. Lo que penalizan: voz IA sobre stock footage **sin comentario ni valor
añadido**. Lo que sobrevive: contenido con ángulo editorial propio, números específicos,
estructura narrativa. Nuestra defensa es la sección 2 (guiones) y la sección 4 (visual
diferenciado) — no es opcional, es supervivencia.

---

## 1. IDEAS (qué videos hacer)

**Estado actual:** `topics.txt` manual + modo `--ideas` con 4 plantillas de ángulo.

| # | Mejora | Por qué (dato) | Cómo | Prioridad |
|---|---|---|---|---|
| 1.1 | **Gatillos probados en el prompt de ideas**: afirmación contraria + prueba en 15s, montos específicos NO redondos ("$1,847", no "$2,000"), framing de comparación social ("the average person..."), urgencia de año ("in 2026"), FOMO por edad ("before you turn 30") | Son los 5 gatillos que aparecen repetidamente en los breakouts de finanzas 2026 (OutlierKit) | Añadir los 5 gatillos a `IDEAS_PROMPT` y `SCRIPT_PROMPT` | **P0** |
| 1.2 | **Minería de temas reales**: scrapear títulos top de r/personalfinance, r/povertyfinance y Google Trends semanalmente; Claude convierte dudas reales en ángulos | Los temas con demanda probada superan a los inventados; las preguntas de Reddit son retención garantizada (dolor real) | Script semanal `mine_topics.py` (Reddit JSON API es pública) que alimenta `topics.txt` | **P1** |
| 1.3 | **Espiar outliers de la competencia**: monitorear los Shorts con views/subscriber anómalos en canales del nicho y hacer nuestra versión con mejor ángulo en <48h | "Un paso adelante" real = velocidad de reacción a formatos que explotan, no adivinar | Lista de 10-15 canales; revisar semanal (manual al inicio, YouTube Data API después) | **P1** |
| 1.4 | **Series con identidad** (ej. "Money Rules Nobody Taught You #12") | Las series generan suscripción y binge; los canales top anclan Shorts a franquicias | Campo `series` en script.json; numeración en título | **P2** |

## 2. GUION (la palanca #1 de retención y la defensa anti-slop)

**Estado actual:** prompt con hook, slippery slide, re-hooks, cierre en eco, 2ª persona, cadencia.

| # | Mejora | Por qué (dato) | Cómo | Prioridad |
|---|---|---|---|---|
| 2.1 | **Hook a 1 segundo, no 3**: primera frase ≤8 palabras, empezar en plena acción ("mostrar el resultado primero, explicar después"), sin frases de contexto | La decisión de swipe es refleja y ocurre a ~1s; los mejores Shorts retienen 70-90% en el primer segundo | Endurecer instrucción de hook en `SCRIPT_PROMPT`: "first sentence ≤8 words, starts mid-action, states the payoff or the paradox" | **P0** |
| 2.2 | **Micro-loops cada 5-8 segundos** ("but here's the twist...") además de los re-hooks de 15s | Técnica documentada de retención: resetea el reloj de atención antes de cada caída | Instrucción explícita en prompt: un giro o tensión nueva cada 2-3 frases | **P0** |
| 2.3 | **Terminar EXACTO en el payoff** — cero despedida, cero "so yeah". La última frase es el eco del hook y corta ahí | "End exactly at the payoff. Don't linger" + el loop perfecto hace que el rewatch se sienta natural (rewatches = señal #1) | Instrucción en prompt + validar que el guion no termine con relleno | **P0** |
| 2.4 | **CTA de comentario, no de follow**: cerrar con pregunta polarizante ("Team renting or team buying?") | Comentarios > suscripciones como señal del feed 2026 | Alternar cierre: 50% eco puro, 50% eco + pregunta | **P1** |
| 2.5 | **Datos citables**: incluir 1 estudio, regla nombrada o estadística real verificable por guion | Diferenciador anti-slop: "valor educativo original" es literalmente el criterio de YouTube para monetizar contenido con IA | Instrucción en prompt + `web_search` tool en la llamada a Claude para verificar el dato (evita alucinaciones en cifras) | **P1** |
| 2.6 | **Generar 3 variantes de hook por guion** y elegir la mejor (Claude como juez con rúbrica) | El hook es tan determinante que vale 2 llamadas extra (~$0.02); es el equivalente barato del A/B testing | `generate_script` produce 3 hooks; segunda llamada elige; costo marginal trivial | **P1** |
| 2.7 | **Feedback loop de analytics**: exportar retención/swipe-rate por video, dárselo a Claude mensualmente para reescribir el prompt | Esto es lo que ningún canal automatizado hace bien: cerrar el ciclo datos→prompt. Ventaja compuesta real | CSV manual de YouTube Studio al inicio; YouTube Analytics API después | **P1** |

## 3. VOZ Y AUDIO

**Estado actual:** edge-tts (en-US-AndrewNeural, +8%), sin música, sin normalización.

| # | Mejora | Por qué (dato) | Cómo | Prioridad |
|---|---|---|---|---|
| 3.1 | **Normalización de loudness a -14 LUFS** | Estándar de YouTube; audio bajo o desparejo mata retención en móvil | Filtro `loudnorm=I=-14:TP=-1.5:LRA=11` en el render final de FFmpeg | **P0** |
| 3.2 | **Música de fondo con ducking** (baja cuando habla la voz), de biblioteca libre, NO trending | El bonus de "audio original" 2026 favorece sonido propio; la música sostiene la energía en pausas de la voz | 5-10 pistas libres (YouTube Audio Library) en `assets/music/`; FFmpeg `sidechaincompress`; volumen -22dB bajo voz | **P0** |
| 3.3 | **Recortar silencios de la voz a casi cero** | "Trim all pauses to zero" — cada pausa >0.4s es una oportunidad de swipe | Detectar gaps entre WordBoundary y acelerar/cortar silencios largos con FFmpeg | **P1** |
| 3.4 | **Upgrade de voz: Chatterbox (open-source, gratis, local)** — en blind test venció a ElevenLabs 65.3% vs 24.5% (test de Resemble) | edge-tts es 8/10; los canales grandes suenan 9.5/10 y la **consistencia vocal da +58% retención** en faceless. Chatterbox da calidad ElevenLabs a costo $0 | Instalarlo local (GPU ayuda); mantener edge-tts como fallback. WordBoundary se pierde → usar WhisperX para timestamps (ya previsto en el diseño) | **P1** |
| 3.5 | **SFX sutiles en transiciones** (whoosh en cambio de escena, "ding" en el dato clave) | Los micro-estímulos auditivos refrescan atención igual que los cortes visuales | Biblioteca de 5-6 SFX; insertarlos en los cortes de clip vía FFmpeg | **P2** |

## 4. VISUAL / MEDIA (el mayor gap actual y el diferenciador anti-slop)

**Estado actual:** Pexels con fallback de gradiente, 5 clips estáticos, corte cada ~8s.

| # | Mejora | Por qué (dato) | Cómo | Prioridad |
|---|---|---|---|---|
| 4.1 | **Beat visual cada 1.5-2.5 segundos** (no cada 8): más clips + zoom lento (Ken Burns) sobre cada clip + punch-ins | La retención colapsa entre el segundo 1.5 y 3.5 si el ojo no tiene "siguiente cosa" que mirar; cortes cada 2-4s es el estándar viral 2026 | Subir `--clips` a 8-10; filtro `zoompan` alternando zoom-in/zoom-out en cada segmento; cortar segmentos en los límites de frase (ya tenemos timestamps) | **P0** |
| 4.2 | **Números como kinetic typography**: cuando el guion dice una cifra, mostrarla GIGANTE animada en pantalla | 86% de los motion graphics de finanzas que convierten abstraen los números en tipografía cinética; "vende la sensación de crecimiento, no la matemática" | Claude marca las cifras clave en el JSON (`key_numbers` con timestamp aproximado); overlay `drawtext` animado en FFmpeg. Es NUESTRO diferenciador técnico — casi nadie lo automatiza | **P0** |
| 4.3 | **Primer frame diseñado**: texto grande del hook (3-6 palabras) visible en t=0, colores saturados | Legible en mute + alta saturación en los primeros segundos correlaciona con retención; el primer frame ES el thumbnail del Short | Overlay del hook-text los primeros 1.5s con estilo propio del canal | **P0** |
| 4.4 | **Palabra clave resaltada en color** en los subtítulos (1 palabra amarilla/verde por bloque) | Word-by-word da un punto de fijación cada 250-400ms; el resalte dirige el ojo al concepto | Claude marca la palabra clave por frase; ASS soporta color inline (`{\c&H18C5F5&}`) | **P1** |
| 4.5 | **Identidad visual de canal**: filtro de color consistente (LUT/curva), esquina con micro-logo, misma fuente siempre | Los canales que escalan combinan stock + identidad propia; la consistencia hace el contenido reconocible (y menos "recreatable en una tarde") | Filtro `curves`/`eq` fijo en el render; PNG de marca de agua | **P1** |
| 4.6 | **Ranking de clips por relevancia**: pedir 3 candidatos a Pexels por escena y que Claude (visión) elija el mejor frame vs el texto de la escena | Ataca directamente el cuello de botella #1 identificado (footage genérico/desconectado) | Descargar thumbnails de candidatos; 1 llamada con visión por video (~$0.01) | **P1** |
| 4.7 | **Fondos B-roll generados por lotes** (biblioteca propia de 100-200 clips de nicho: billetes macro, gráficas animadas, ciudades) mezclados con Pexels | Reduce dependencia de Pexels y repetición visual entre videos; biblioteca propia = estética propia | Generar una sola vez (Runway/Pika por lote, o motion graphics propios); carpeta `assets/broll/` indexada por tag | **P2** |

## 5. ENSAMBLAJE Y EMPAQUETADO

| # | Mejora | Por qué | Cómo | Prioridad |
|---|---|---|---|---|
| 5.1 | **Cortes alineados a frases**: cambiar de clip en el fin de una oración, no a duración fija | El corte sincronizado con el ritmo del habla se siente editado por humano | Usar los timestamps de WordBoundary para calcular puntos de corte | **P1** |
| 5.2 | **Validador automático pre-publicación**: duración 30-58s, loudness OK, subtítulos cubren 100% del audio, primer frame tiene texto, resolución/fps exactos | Cero videos defectuosos publicados cuando esto corra solo | Función `validate()` al final del pipeline; falla ruidosamente | **P1** |
| 5.3 | **Metadata optimizada**: título <70 chars con curiosity gap, descripción con gancho de 2 frases, 15-25 hashtags, tags SEO separados | Estructura de metadata de los canales que rankean | Ampliar el schema del guion con `tags` (lista SEO) | **P1** |
| 5.4 | **Export multi-plataforma**: mismo video para TikTok y Reels (sin marca de agua, metadata por plataforma) | Triplica el alcance del mismo costo de producción; los canales faceless top publican en las 3 | Carpeta `output/.../tiktok/` con variantes; subida manual al inicio | **P2** |

## 6. PUBLICACIÓN Y CRECIMIENTO

| # | Mejora | Por qué | Cómo | Prioridad |
|---|---|---|---|---|
| 6.1 | **Cadencia 1/día a hora fija** (7-9am ET para audiencia US) | Consistencia > volumen; el algoritmo 2026 premia canales con patrón estable | Programador de tareas + revisión de 30s antes de publicar | **P0** |
| 6.2 | **Responder comentarios la primera hora** (o pregunta fijada) | Comentarios pesan más que subs en el feed; el comentario fijado siembra la conversación | 10 min/día; Claude puede generar el comentario fijado en el JSON | **P1** |
| 6.3 | **Batch de fin de semana**: generar 7 videos el domingo, revisar en 15 min, programar la semana | Desacopla producción de publicación; el sistema ya lo permite | Loop en PowerShell sobre 7 temas | **P1** |
| 6.4 | **Funnel a long-form** (el playbook de Humphrey Yang: Shorts alimentan videos de 8-15 min donde está el CPM de $18-30) | Los Shorts pagan ~$4.50 CPM; el dinero real del nicho está en long-form + afiliados (brokers pagan las integraciones más altas) | Fase 2 del canal: mismo pipeline con formato 16:9 y guiones de 1.200 palabras | **P2** |
| 6.5 | **Subida automática vía YouTube Data API** | Elimina el último paso manual | Solo cuando el canal justifique pasar la auditoría de Google | **P2** |

---

## Análisis de competencia (quién gana y cómo les ganamos)

**Quién gana en finanzas 2026:** Humphrey Yang (2M, talking-head + funnel de Shorts a long-form),
Quiet Quest (faceless, B-roll cinematográfico lento + ensayos filosóficos de dinero — el formato
faceless que más rápido escala), Bald Guy Money (550K, autoridad por documentos reales en pantalla).

**Lo que su éxito nos enseña:**
1. El faceless que escala hoy NO es el slideshow con voz robótica — es voz consistente de calidad + estética propia + guiones con tesis.
2. Los Shorts son el canal de adquisición; el long-form es la monetización. Planear la fase 2 desde ahora (misma maquinaria, otro formato).
3. La autoridad se construye con especificidad: cifras exactas, formularios reales, reglas nombradas.

**Nuestras ventajas estructurales (el "paso adelante"):**

| Ventaja | Por qué la competencia no la tiene |
|---|---|
| **Costo marginal ~$0.05/video** | Podemos probar 30 ángulos/mes; un canal manual prueba 4 |
| **Iteración prompt←analytics (2.7)** | Cerrar el loop datos→guion de forma sistemática; los canales manuales iteran por intuición |
| **Kinetic typography automatizada (4.2)** | Nadie lo hace sin editor humano; es visualmente "premium" a costo cero |
| **Velocidad de reacción (1.3)** | Detectar un formato que explota y tener nuestra versión en 24-48h |
| **Multi-canal futuro** | El mismo pipeline puede correr un segundo nicho o idioma con solo cambiar 2 prompts |

**El foso defensivo real** no es el código (cualquiera lo copia) — es la **combinación de
biblioteca visual propia (4.7) + identidad de marca (4.5) + prompt afinado con datos reales de
retención (2.7)**. Esas tres cosas se acumulan con el tiempo y no se copian en una tarde —
que es, literalmente, el criterio de YouTube para no considerarte slop.

---

## Orden de ejecución sugerido

**Sprint 1 (esta semana) — P0, todo dentro de pipeline.py:**
1. Prompt: hook ≤8 palabras / micro-loops / cierre en payoff / gatillos de finanzas (2.1-2.3, 1.1)
2. Audio: loudnorm + música con ducking (3.1, 3.2)
3. Visual: 8-10 clips + zoompan + primer frame con hook-text (4.1, 4.3)
4. Kinetic typography de cifras (4.2)
5. Empezar a publicar 1/día (6.1) — **los datos reales valen más que cualquier mejora restante**

**Sprint 2 (semanas 2-6) — P1, guiado por los primeros analytics:**
resaltado de palabra clave, ranking de clips con visión, variantes de hook, validador,
minería de Reddit, Chatterbox, feedback loop de analytics.

**Fase 2 (con tracción) — P2:** biblioteca B-roll propia, multi-plataforma, series,
long-form funnel, subida por API.

---

## Métricas que mandan (revisar semanal)

| Métrica | Objetivo | Dónde |
|---|---|---|
| "Stayed to watch" (no-swipe) | >70% | YouTube Studio → Shorts |
| Retención promedio | >65% (<30s) / >50% (30-60s) | Analytics por video |
| Rewatch (vistas > duración) | Que exista; señal del loop | APV >100% |
| Comentarios por 1K views | Tendencia creciente | Analytics |
| Views video 10 vs video 1 | Mejora sostenida | Comparativa manual |
