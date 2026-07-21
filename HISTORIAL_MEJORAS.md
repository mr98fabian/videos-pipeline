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

## 2026-07-20 — Bug crítico: seg_punch_rest truncaba videos a 23.6s
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
