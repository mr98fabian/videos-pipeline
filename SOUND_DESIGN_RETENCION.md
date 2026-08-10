# Sound design y retención: ducking, SFX, silencios y LUFS para Shorts

Investigación multiidioma — agosto 2026
Idiomas consultados: inglés, japonés (日本語), chino (中文), español

> Las fuentes japonesas resultaron las más quirúrgicas en parámetros concretos (tempo de corte, LUFS, SFX). Las chinas aportaron la neurociencia del BGM. Las inglesas, el ducking técnico con FFmpeg (directamente implementable en `pipeline.py`).

---

## 1. Ducking con FFmpeg `sidechaincompress` (EN) — implementable ya

El ducking (bajar la música cuando habla la voz) se hace con el filtro `sidechaincompress`: la voz entra como "sidechain" y comprime el BGM automáticamente.

Tabla de parámetros recomendados por tipo de contenido:

| Tipo de contenido | Umbral voz | BGM objetivo | Attack | Release |
|---|---|---|---|---|
| Tutorial / explicación | -20 dB | -35 dBFS | 100 ms | 500 ms |
| Documental / storytelling | -18 dB | -30 dBFS | 200 ms | 800 ms |
| Tech news rápido / Shorts dinámico | -22 dB | -38 dBFS | 50 ms | 300 ms |

Para nuestro caso (Shorts de ritmo rápido, voz TTS + BGM): usar la fila 3. Release corto (300 ms) para que la música vuelva rápido entre frases y el video no se sienta "vacío" en las pausas.

Concepto a implementar en `pipeline.py` (mezcla de audio):

```bash
ffmpeg -i video.mp4 -i bgm.mp3 -filter_complex \
  "[1:a][0:a]sidechaincompress=threshold=0.02:ratio=8:attack=50:release=300:makeup=1[bgm_ducked]; \
   [0:a][bgm_ducked]amix=inputs=2:duration=first[aout]" \
  -map 0:v -map "[aout]" -c:v copy out.mp4
```

(Los valores exactos de threshold hay que ajustarlos al nivel real de nuestra voz TTS; medir primero con `volumedetect`.)

## 2. Parámetros de retención de las fuentes japonesas (JA) — las joyas del documento

De artículos japoneses de edición para YouTube/Shorts:

- **Tempo dorado de corte**: 1 corte visual cada **2-3 segundos**. La misma imagen más de **5 segundos** sube el abandono de forma medible.
- **SFX ANTES del momento clave**: colocar el efecto de sonido justo *antes* (no sobre) del dato/giro funciona como pre-señal de atención ("algo viene") y sube la retención en ese punto.
- **Pausas de 0.2-0.5 s al cambiar de tema**: micro-silencios que delimitan bloques; el cerebro los usa para "guardar" lo anterior y prepararse. Sin ellos, el TTS encadenado fatiga.
- **Normalización**: **-14 LUFS** integrado, pico verdadero **-1.0 dBTP** (estándar de plataformas).
- **Estímulo constante**: elementos audiovisuales cambiando cada ~3 segundos ≈ **+10% de retención** reportado.

## 3. Neurociencia del BGM (ZH)

Artículo chino sobre por qué el BGM de TikTok/抖音 "engancha":

- **120-140 BPM** = 1.5-2× el ritmo cardíaco en reposo → el cuerpo entra en estado de alerta suave y el dedo no desliza.
- Activa el sistema dopaminérgico (recompensa anticipada, no consumada — el mismo mecanismo del loop de scroll).
- **Armonía simple y repetitiva** = baja carga cognitiva → deja ancho de banda mental para el contenido. BGM complejo compite con la voz y baja comprensión.

Regla práctica: BGM de 120-140 BPM, loop simple, sin melodía protagonista, con ducking agresivo bajo la voz.

## 4. El silencio como arma (ES)

De las fuentes en español (edición al beat): cortar al beat del BGM funciona pero **no abusar** — el silencio bien puesto pesa como un golpe musical. Un corte seco de TODO el audio (voz + música) justo antes del giro del guion multiplica el impacto del remate. Máximo 1-2 silencios dramáticos por Short de 60 s; más, pierde efecto.

## 5. Síntesis operativa por capas de audio

| Capa | Regla |
|---|---|
| Voz TTS | Protagonista, siempre inteligible, -14 LUFS como referencia de mezcla |
| BGM | 120-140 BPM, simple, -8 a -12 dB bajo la voz con ducking (attack 50 ms / release 300 ms) |
| SFX | 1 efecto ANTES de cada momento clave (giro, dato, remate); volumen puntual, nunca constante |
| Silencios | 0.2-0.5 s entre bloques temáticos; 1 silencio total dramático antes del giro principal |
| Visual (aunque no es audio) | Corte cada 2-3 s; nada estático >5 s |

---

## Aplicación concreta al pipeline

1. **`pipeline.py` — mezcla de audio**: añadir etapa de ducking con `sidechaincompress` (parámetros fila 3 de la tabla) y normalización final con `loudnorm=I=-14:TP=-1.0`.
2. **`pipeline.py` — SFX**: definir 3-5 SFX de la casa (whoosh, ding, golpe grave) y regla de inserción: 0.1-0.3 s *antes* del segundo donde empieza el giro/dato clave. Los timestamps de "momento clave" deben venir del guion (declarados, ver `PSICOLOGIA_COMPARTIR.md`).
3. **Biblioteca de BGM**: filtrar/curar tracks a 120-140 BPM, armonía simple. Etiquetar por energía.
4. **Micro-pausas**: si el TTS permite SSML/pausas, insertar `<break time="300ms"/>` al cambiar de bloque temático (ver `VOZ_TTS_EMOCIONAL.md`).
5. **Validar contra datos propios**: tras aplicar ducking+SFX en los próximos N videos, comparar retención contra la línea base actual (70.9% en banda media). Regla del proyecto: nuestros datos mandan sobre benchmarks externos.

## Fuentes consultadas

- Guías EN de ducking con FFmpeg `sidechaincompress` (tabla de parámetros por tipo de contenido) — EN
- Artículos japoneses de edición para YouTube/Shorts: tempo dorado 2-3 s, SFX pre-momento clave, pausas 0.2-0.5 s, -14 LUFS / -1.0 dBTP, estímulo cada 3 s ≈ +10% retención — JA
- Artículo chino sobre neurociencia del BGM de 抖音/TikTok (120-140 BPM, dopamina, baja carga cognitiva) — ZH
- Fuentes ES de edición al beat y uso del silencio — ES
