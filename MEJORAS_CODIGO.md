# Registro de mejoras de código — 17 jul 2026

Rastreo de la auditoría completa (agente Explore, 25 hallazgos) y qué se hizo con cada uno.
Formato: descripción, área, prioridad, y para lo no tocado, sugerencia de solución.

## Aplicado en esta pasada (crítico + alto + dedup clave)

| # | Mejora | Área | Por qué era subóptimo | Por qué así | Impacto esperado |
|---|---|---|---|---|---|
| 1 | `_drawtext_escape()` para watermark y CTA | pipeline.py assemble() | Coma/`%{...}` sin escapar rompía el filtergraph de ffmpeg o permitía inyección de expresiones de drawtext | `str.translate()` con mapa fijo — más simple y rápido que regex, cubre los 5 caracteres reales que rompen el filtro (`\ ' : , %`) | Ningún CTA/watermark con puntuación normal vuelve a abortar el render; cierra el vector de inyección |
| 2 | Sufijo incremental en carpeta de salida (`-2`, `-3`) | pipeline.py main() | Dos videos con mismo título el mismo día se pisaban (voice.mp3/clips/video.mp4) — confirmado con las 3 variantes de CTA de Coca-Cola | Chequeo simple de `(out_dir/"video.mp4").exists()` antes de usar la carpeta, sin cambiar la convención de nombres para el caso normal (1 video/tema/día) | Elimina pérdida de trabajo/créditos cuando se regenera el mismo tema (variantes A/B, reintentos) |
| 3 | `_atomic_write_json()` / `_load_json()` | pipeline.py (4 sitios: used_topics, manifest personajes, gemini_usage) | Lecturas/escrituras completas de archivo sin atomicidad — dos procesos en paralelo (tarea programada + manual) podían pisarse a mitad de escritura | Patrón estándar tmp+`os.replace` (atómico en el mismo filesystem); consolidó de paso 4 variantes casi idénticas de carga/guardado | Cero pérdida de estado (temas usados, contador de gasto, hojas de personaje) bajo concurrencia |
| 4 | `timeout=` en `run()` y `ffprobe_duration()` | pipeline.py, track_video.py | Un ffmpeg/ffprobe colgado bloqueaba una corrida desatendida (tarea programada) para siempre, sin recuperación | Default generoso (600s render, 30s ffprobe) en vez de un valor ajustado a mano por caso — prioriza no romper casos normales sobre detectar cuelgues rápido | Una corrida desatendida nunca queda colgada indefinidamente; falla con error legible en vez de silencio total |
| 5 | Documentar `--` para IDs con guion inicial | track_video.py, youtube_api.py | `-abc123` como positional se interpretaba como flag y argparse fallaba (bug real ya visto esta sesión) | Confirmado que `--` (estándar de argparse) ya resuelve el caso sin tocar la interfaz existente — se agregó solo al epílogo del `--help` | Nadie más tiene que descubrirlo a mano llamando la función Python directo, como se hizo esta sesión |
| 6 | `_claude_json_call()` compartido + guarda StopIteration | pipeline.py (generate_script, generate_ideas, pick_sfx_cues) | 3 copias del mismo patrón Claude+json_schema; `next(...)` sin default lanzaba StopIteration cruda si la respuesta solo traía bloque `thinking` | Un solo helper con `next(..., None)` + error legible, reusado con `with_retries()` ya existente en el archivo | Un guion no se cae con traceback opaco si Claude agota el presupuesto de pensamiento; menos código que mantener |
| 7 | `_yt_execute()` con retry/backoff | youtube_api.py (10+ llamadas `.execute()`, incl. upload por chunks) | Ninguna llamada a la API de YouTube reintentaba ante 429/500/503 transitorios; un upload resumible fallaba a mitad sin reintentar el chunk | Wrapper único que distingue error transitorio (403/429/500/503) de error real (400/404), 3 intentos con backoff de 5s | Menos abortes por fallos transitorios de Google, especialmente en uploads largos y en `_effective_publish_times` (que se llama en cada guardrail) |
| 8 | Guardas `.get()` en indexado de respuestas | youtube_api.py (_effective_publish_times, update_video, get_channel_id) | Indexado directo (`resp["items"][0]`) lanzaba KeyError/IndexError crudo ante respuesta vacía | `.get()` con default + `SystemExit` con mensaje claro cuando el caso es genuinamente un error de uso (video_id inválido, cuenta sin canal) | Errores de configuración se leen como mensaje claro, no como traceback de Python |
| 9 | UTF-8 forzado en stdout/stderr | pipeline.py, youtube_api.py, track_video.py | En Windows con tarea programada, stdout hereda cp1252; un título/comentario con emoji rompía la corrida DESPUÉS de gastar créditos | `sys.stdout.reconfigure(encoding="utf-8")` al inicio de cada script — arreglo de una línea que ya se había hecho a mano varias veces esta sesión con `io.TextIOWrapper` | Elimina una clase entera de fallos ya vistos repetidamente en producción |
| 10 | Linter de guion ampliado (`_check_script_lint`) | pipeline.py, junto a `_check_pacing` | Dos reglas ya validadas con datos reales (ñ en voz español, antagonista/institución en el título) dependían de que alguien se acordara a mano | Solo avisos (igual que `_check_pacing`), heurísticas baratas sin nueva llamada a Claude/API | Recordatorio automático de dos reglas ya confirmadas que suben retención/pronunciación, sin bloquear ni encarecer la corrida |

## No abordado — registro para iteraciones futuras

| # | Hallazgo | Área | Prioridad | Sugerencia |
|---|---|---|---|---|
| 18 | Funciones >100 líneas (`assemble` ~137, `acquire_media` ~102, `pick_sfx_cues` ~112) | pipeline.py | Media | Dividir `assemble()` en sub-pasos (normalizar clips / construir filtro de audio / construir filtro de video / render) cuando se vuelva a tocar por otra razón — no vale la pena un refactor puramente cosmético ahora mismo |
| 19 | `GOOD_WINDOW_*` (franja horaria) aplicado a todos los canales por igual | youtube_api.py | Media | Mover a un dict `{"default": (1,13), "impixxel": None}` cuando haya suficiente data de ImPixxel para calibrar su propia franja (hoy contaminada por ads, ver memoria) |
| 20 | `except Exception` demasiado amplios (Pexels, Nano Banana, Veo, Lyria, trim de silencio) | pipeline.py | Baja | Ya degradan con gracia (fallback conocido); solo vale la pena acotar el tipo de excepción si empiezan a esconder bugs reales de programación, no fallos de red |
| 21-22 | Config hardcodeada (voces/estilo/watermark por canal) y constantes mágicas (costos, volúmenes de audio, geometría CTA) | pipeline.py, youtube_api.py | Baja | Un módulo `config.py` con un dict por canal se vuelve valioso cuando haya un 3er canal — con 2 canales el costo de indirección no se justifica todavía |
| 23 | Deuda ya documentada en comentarios (tope de 4 SFX cues, DEFAULT_CLIPS por calibrar) | pipeline.py | Baja | Sin acción — ya está anotada donde corresponde, no es deuda oculta |
| 25 | `MediaFileUpload(chunksize=-1)` sube en una sola request, sin reanudación real por chunk | youtube_api.py | Baja | Cambiar a un chunksize fijo (ej. 10MB) si empiezan a fallar uploads grandes por conexión inestable; con Shorts (<60s, archivos chicos) el riesgo actual es bajo |
| — | Lyria/Veo sin retry (decisión explícita, no pendiente) | pipeline.py | N/A | Ya degradan con gracia a fallback conocido (biblioteca local / imagen estática); reintentar un 400 Bad Request no ayuda — solo reconsiderar si empiezan a fallar por 429/503 en vez de 400 |

## Verificación realizada
- `ast.parse` sobre los 3 archivos tras cada fase — sin errores de sintaxis.
- Smoke test end-to-end (`pipeline.py --no-pexels --no-sfx` con caracteres adversarios
  `, : % {}` en watermark y CTA) — render completo exitoso, confirma sanitización de
  drawtext y el sufijo incremental de carpeta (creó `-2` en vez de pisar la corrida anterior).
- `youtube_api._effective_publish_times()` ejecutado en vivo tras agregar `_yt_execute` —
  autenticación y guardrails siguen funcionando.
- `track_video.py --help` confirma el mensaje sobre `--` para IDs con guion inicial.
