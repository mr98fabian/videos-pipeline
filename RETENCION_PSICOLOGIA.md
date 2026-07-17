# Psicología de la retención en Shorts/TikTok/Reels — y qué hacer con eso

Investigación con fuentes reales, mismo estándar que `MINIATURAS.md`: ✅ verificado (estudio/fuente citada) vs ⚠️ consenso de industria sin paper duro detrás. Objetivo: entender el mecanismo, no solo la receta, para poder adaptarla cuando cambie el algoritmo.

---

## 1. Los primeros 1-2 segundos: la decisión ya está tomada antes de pensar

- El cerebro evalúa contraste, movimiento, caras y anomalías visuales en **100-150ms** — antes de la decisión consciente (ya documentado en `MINIATURAS.md`, aplica igual al frame 1 del video, no solo a la miniatura).
- **Dato duro de Paddy Galloway** (consultor detrás de MrBeast, con acceso a datos reales de cientos de canales): los Shorts de mejor rendimiento retienen **70-90%** de la gente que entra vs. las que hacen swipe inmediato. Eso es el techo real — no "todo el mundo se queda", sino que los mejores pierden solo 10-30% en el instante 1. ✅ — [Retention Rabbit / análisis Paddy Galloway](https://www.retentionrabbit.com/blog/ultimate-guide-youtube-audience-retention)
- **50-60% de los abandonos totales de un Short ocurren en los primeros 3 segundos.** Si tu curva de retención cae en picada ahí, el problema es el gancho, no el resto del video — no sirve de nada pulir el minuto 2 si la gente ya se fue en el segundo 1. ✅ — [Shortimize](https://www.shortimize.com/blog/how-to-analyze-youtube-shorts-performance)

**Traducción operativa:** el frame 1 de cada Short debe tener ya movimiento/cara/color-contrastante — nunca un plano estático "de calentamiento". Nuestro pipeline hoy arranca con Ken Burns (zoom lento) en la primera escena; eso es exactamente el tipo de arranque "flojo" que pierde el primer segundo.

---

## 2. El mecanismo real: no es "contenido interesante", es una máquina tragamonedas

- Investigación clásica (Schultz et al., y trabajo posterior en adicciones conductuales): el cerebro **no libera dopamina porque encontró algo que le gusta — la libera porque *podría* encontrar algo que le gusta.** La recompensa impredecible dispara más dopamina que la predecible. ✅ — [ScienceDirect, Clark & Zack 2023](https://www.sciencedirect.com/science/article/pii/S0306460323000217)
- Esto es literalmente el mismo mecanismo de refuerzo de una máquina tragamonedas: **variable-ratio reinforcement schedule.** TikTok/Shorts no te enganchan por ser buenos — te enganchan porque nunca sabes si el siguiente scroll trae el video que sí va a valer la pena. ✅ (consenso extenso en literatura de adicciones conductuales) — [Screenwise](https://screenwiseapp.com/guides/dopamine-hits-why-short-form-video-is-so-addictive)
- Neuroimagen: contenido personalizado por el algoritmo activa el área tegmental ventral y la corteza prefrontal medial **más** que contenido genérico no personalizado — el "para ti" no es marketing, es literalmente un gatillo neuroquímico más fuerte. ✅ — [MindLAB Neuroscience](https://mindlabneuroscience.com/youtube-shorts-reward-loops-neuroscience/)

**Traducción operativa:** el algoritmo YA hace el trabajo de "variable reward" entre videos (eso no lo controlamos). Lo que sí controlamos es la variable reward *dentro* de un mismo video: cada 2-4 segundos algo tiene que cambiar/sorprender para simular ese mismo patrón de recompensa impredecible dentro del Short, no solo entre Shorts.

---

## 3. Zeigarnik / loops abiertos: por qué un final "sin cerrar" retiene más

- Efecto Zeigarnik (Bluma Zeigarnik, camareros recordaban pedidos sin completar mejor que los completados): una tarea inconclusa genera tensión mental que solo se resuelve al completarla. El cerebro trata lo "no resuelto" como una alarma activa. ✅ (efecto psicológico establecido, décadas de replicación) — [PodIntelligence](https://www.podintelligence.com/blog/zeigarnik-effect-for-engaging-storytelling/)
- Aplicado a video: abrir con una afirmación fuerte SIN la respuesta inmediata, mostrar un visual inesperado que genera "¿qué es esto?", y sembrar preguntas a mitad del video que se resuelven cerca del final — no al principio. ⚠️ (aplicación de un efecto real, sin estudio específico sobre Shorts, pero es el mecanismo usado explícitamente por guionistas de retención de alto nivel).
- El cierre que **rima con la apertura** (misma frase/pregunta, reencuadrada con lo que el viewer ya sabe) fuerza el replay — esto es lo que ya tenemos en el `SCRIPT_PROMPT` del pipeline en inglés ("close with a line that directly echoes the opening hook") — confirmado como técnica real, no invención nuestra.

**Traducción operativa:** cada guion (Skick incluido) debe tener 1-2 "re-hooks" a mitad de camino (tipo "pero espera, ahí no termina" / "y ahí fue cuando..."), no solo el hook inicial y el cierre. Hoy nuestros guiones de Skick son lineales sin re-hook a mitad.

---

## 4. Ritmo audiovisual: cuánto debe durar cada plano

- **Benchmark real de cortes**: los Shorts de alto rendimiento cambian de plano **cada 2-4 segundos.** Clips de menos de 1 segundo ya son estándar en 2026, no experimentales — pero solo funcionan si el viewer entiende la imagen instantáneamente (sin ambigüedad). ✅ — [air.io](https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8)
- El patrón real no es "todo rápido siempre": es estimular → calmar → re-enganchar. Ráfagas de cortes rápidos seguidas de un respiro, no una ametralladora constante (eso cansa igual que la monotonía). ✅ — mismo source.
- Regla de corte: **cortar durante el movimiento, no después** — evita el "tartamudeo visual" y mantiene la energía continua. ✅ — mismo source.
- El cerebro no procesa caos, procesa *patrones*. La velocidad funciona solo si la claridad se mantiene — cortes rápidos sin intención se sienten como ruido, no como ritmo. ✅ — [Brandefy, psicología de la edición](https://brandefy.com/psychology-of-video-editing/)

**Traducción operativa — este es el hallazgo con más impacto directo en nuestro pipeline:** hoy generamos **5 clips estáticos para ~45s de audio** → **~9 segundos por escena**. Eso es **2-4x más lento** que el benchmark de retención (2-4s por corte). Es la brecha más grande entre lo que sabemos que funciona y lo que estamos construyendo.

---

## 5. Por qué los subtítulos palabra-por-palabra funcionan (lo que ya hacemos bien)

- Dual coding: presentar la misma información en dos canales (audio + texto sincronizado) mejora la codificación y sostiene la atención más que un solo canal — mecanismo cognitivo bien establecido, aplicado de forma directa por los subtítulos "Hormozi-style" que ya usamos. ⚠️ (el principio de dual coding es sólido en literatura de aprendizaje; su aplicación específica a retención en Shorts es práctica de industria, no paper directo).
- Además resuelve el consumo sin sonido (50%+ de las vistas en móvil en espacios públicos) — sin esto se pierde la mitad de la audiencia potencial en el segundo 1.

**Ya lo tenemos bien implementado** (ASS word-level, estilo Hormozi) — no tocar, es una de las piezas que ya está al nivel del benchmark.

---

## 6. Diferencias reales por plataforma (no tratar todo igual)

| Plataforma | Qué pesa más en el algoritmo | Implicación práctica |
|---|---|---|
| YouTube Shorts | **Rewatch/loop** — un video visto 2 veces cuenta como AVD >100%, señal fuertísima | El cierre debe empujar al replay inmediato (loop perfecto: el último frame conecta con el primero) |
| TikTok | Completion rate + shares | Videos más cortos y un final que dé ganas de compartir (remate cómico/sorpresa, no cliffhanger sin resolver) |
| Instagram Reels | Saves + shares por encima de completion puro | Contenido "guardable" (tips, formato reusable) rinde distinto que la pura comedia |

⚠️ Diferenciación de industria ampliamente reportada, sin white-paper público de las plataformas que lo confirme con números exactos — tratar como orientación direccional, no ley.

---

## 7. Benchmarks de retención — cómo saber si un video "funciona" de verdad

- Retención buena en Shorts: **80-95%** en general. Shorts <30s deben apuntar a **>90%**; los que llegan a 60s son exitosos con **75-85%**. ✅ — [Fluxnote](https://fluxnote.io/guides/good-audience-retention-youtube-shorts), [Opus](https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention)
- Tasa de "swipe-away" objetivo: **por debajo de 25%** en Shorts <30s. ✅ — mismo grupo de fuentes.
- **Nuestro dato real (auditoría 11 jul):** 42.9% "se quedaron para mirar" / 57.1% descartado. Eso es **muy por debajo** del benchmark de industria (que apunta a <25% de descarte) — confirma con datos propios que el problema de gancho/ritmo es real, no una sospecha.

---

## 8. Los límites: qué es "hackear" de forma sostenible vs. lo que te penaliza

- YouTube ya mide **"Quality CTR"** (2026): evalúa qué pasa en los 30s posteriores al clic, no solo si hubo clic. Miniaturas/hooks con alto CTR pero mala retención dañan el posicionamiento — el mismo principio aplica al hook del video: prometer algo que el resto del video NO cumple es detectado y penalizado. Ya documentado en `MINIATURAS.md` §5, se confirma que el mismo principio corre para el guion, no solo la miniatura.
- La ética operativa real: los mecanismos de arriba (ritmo, loops, re-hooks) son técnicas de **claridad y estructura**, no de engaño — cambian *cómo* se cuenta algo verdadero, no *qué tan cierto* es. El límite se cruza cuando el hook promete algo que el video no entrega (clickbait clásico) — eso sí está penalizado y va a seguir estándolo.

---

## 9. Tabla operativa — mecanismo → acción → dónde se implementa

| Mecanismo | Acción concreta | Dónde |
|---|---|---|
| Primeros 1-2s deciden todo | Primer plano SIEMPRE con movimiento/acción, nunca Ken Burns lento de calentamiento | `pipeline.py::acquire_media` — reordenar escenas o forzar que la 1ra tenga más movimiento |
| Variable reward cada 2-4s | Más escenas por Short (de 5 a 8-12 para 45s) o zooms/punch-ins sincronizados a los beats del guion | `pipeline.py::assemble` — aumentar `--clips` default, o añadir punch-ins con FFmpeg entre escenas |
| Zeigarnik / re-hooks | Añadir 1-2 "pero espera" a mitad del guion, no solo hook inicial + cierre | `SCRIPT_PROMPT` (pipeline.py) y guiones de Skick — instrucción ya parcial en inglés, falta versión ES para Skick |
| Ritmo: cortar en movimiento | Evitar transición en momentos estáticos del guion | Al escribir `search_terms`, alternar quietud/acción entre escenas consecutivas |
| Dual coding (ya lo tenemos) | No tocar — subtítulos word-level ya implementados | `generate_subtitles()` — sin cambios |
| Loop perfecto para YouTube Shorts | El último frame/línea debe conectar visualmente o narrativamente con el primero | Guion: última línea rima con la primera (ya en `SCRIPT_PROMPT`); falta reforzarlo visualmente (mismo fondo/pose en 1ra y última escena) |
| Quality CTR / no romper la promesa | El gancho del guion debe resolverse de verdad antes del segundo 45 | Revisión manual de guion antes de generar — chequeo rápido: ¿la última línea responde la pregunta de la primera? |

---

## 10. Repos verificados (README leído directamente, no solo resultado de búsqueda)

| Repo | Qué hace realmente | ¿Sirve para nosotros? |
|---|---|---|
| **[video-use](https://github.com/browser-use/video-use)** (16.7K estrellas) | Edita **material grabado real** leyendo transcripciones (no genera desde cero); corta muletillas/silencios, aplica color, subtítulos, fades. Requiere API key de ElevenLabs (pago) para transcripción. | ✅ Para cuando edites VODs de gameplay real (como Gnaughty Gnomes/Nocturne) en vez de contenido generado con IA — arquitectura compatible con nuestros timestamps de edge-tts si migráramos la transcripción. NO aplica a los Shorts de Skick (ahí no hay footage real que editar). |
| **[Remotion Agent Skill](https://www.remotion.dev/docs/ai/skills)** (oficial, 25K+ instalaciones) | Framework de video programático en React — tipografía cinética, captions animados, motion graphics reales. Corre junto a FFmpeg, no lo reemplaza. | ⚠️ Inversión grande: requiere stack Node.js/React nuevo en un proyecto 100% Python hoy. Vale la pena solo si el cuello de botella pasa a ser "los subtítulos/gráficos se ven planos" — no es la prioridad actual (la prioridad es ritmo de corte, sección 4). |

**Decisión:** no migrar nada todavía. El ritmo de corte (sección 4, ya implementado en `pipeline.py`) es la mejora de mayor impacto y no requería ningún repo externo — era un parámetro nuestro mal calibrado.

## Fuentes citadas
- [Retention Rabbit — guía de retención YouTube, datos Paddy Galloway](https://www.retentionrabbit.com/blog/ultimate-guide-youtube-audience-retention)
- [Shortimize — cómo analizar rendimiento de Shorts](https://www.shortimize.com/blog/how-to-analyze-youtube-shorts-performance)
- [ScienceDirect — reward variability y adicción conductual (Clark & Zack 2023)](https://www.sciencedirect.com/science/article/pii/S0306460323000217)
- [Screenwise — el "slot machine" del video corto](https://screenwiseapp.com/guides/dopamine-hits-why-short-form-video-is-so-addictive)
- [MindLAB Neuroscience — Shorts y circuitos de recompensa](https://mindlabneuroscience.com/youtube-shorts-reward-loops-neuroscience/)
- [PodIntelligence — efecto Zeigarnik aplicado a storytelling](https://www.podintelligence.com/blog/zeigarnik-effect-for-engaging-storytelling/)
- [air.io — edición avanzada de retención, cortes por segundo](https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8)
- [Brandefy — psicología de la edición de video](https://brandefy.com/psychology-of-video-editing/)
- [Fluxnote](https://fluxnote.io/guides/good-audience-retention-youtube-shorts) / [Opus](https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention) — benchmarks de retención 2026
- Datos propios: `PROGRESO_CANAL.md`, auditoría 11 jul 2026 (42.9% retención inicial vs. benchmark <25% de descarte)
