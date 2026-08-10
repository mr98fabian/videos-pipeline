# Faceless Shorts Pipeline

Tema → YouTube Short vertical (1080x1920 @ 30fps) listo para subir, sin intervención manual.

```
[1. SCRIPT] → [2. AUDIO] → [3. MEDIA]  → [4. SUBS]     → [5. ASSEMBLY]
 Claude API    edge-tts     Pexels API    ASS word-level   FFmpeg
 (guion+SEO)   (gratis)     (gratis)      (gratis)         1080x1920@30fps
```

## Requisitos

- Python 3.10+ (`py` en Windows) y FFmpeg en el PATH
- `py -m pip install -r requirements.txt`
- Copia `.env.example` a `.env`:
  - `ANTHROPIC_API_KEY` — requerida para generar guiones ([console.anthropic.com](https://console.anthropic.com))
  - `PEXELS_API_KEY` — gratis en [pexels.com/api](https://www.pexels.com/api/); sin ella se usan fondos de gradiente

## Uso

```powershell
# Flujo completo: tema -> video
py pipeline.py "why the 50/30/20 rule fails at low income"

# Sin clave de Anthropic (guion pre-escrito)
py pipeline.py --script-file scripts/sample_script.json

# Sin Pexels (fondos de gradiente)
py pipeline.py "topic" --no-pexels

# Genera 5 ideas de tema nuevas (angulos virales probados)
py pipeline.py --ideas

# Modo automatico: elige el siguiente tema no usado de topics.txt y corre todo
# (genera 5 ideas nuevas solas si topics.txt se agota). Nunca repite un tema.
py pipeline.py --auto

# Opciones: --voice en-US-AriaNeural --rate "+5%" --clips 6
```

## Libreria de stickers (generar una sola vez)

`sticker_library.py` genera 200 stickers con IA (Nano Banana) para las
palabras clave que mas se repiten en los guiones de los tres canales
(finanzas, gamer/Skick, gethiddenfacts) y los guarda en `assets/stickers/`
para reusar en todos los videos futuros, sin regenerar ni pagar el mismo
icono dos veces.

```powershell
py -m pip install rembg onnxruntime   # opcional: recorta el fondo a transparente
py sticker_library.py --list          # ver el catalogo y que falta generar
py sticker_library.py --generate      # genera los que faltan (tarda por el delay entre llamadas)
```

El pipeline los usa automaticamente: cada vez que el guion narra una palabra
clave del catalogo (ej. "money", "lag", "nivel", "explosion"), aparece ese
sticker en el timestamp exacto donde se dice, no solo una vez por escena.
Las escenas sin ninguna keyword narrada siguen usando el fallback anterior
(foto real recortada de Wikimedia o emoji).

## Estudiar que funciono (reporte de rendimiento)

`performance_report.py` cruza `video_log.csv` (topic, estilo, duracion,
keyword_score/title_score de research -- ya se guarda solo al subir cada
video) con las metricas REALES de YouTube Analytics (vistas, retencion,
likes) via API, y exporta un CSV para analizar en Excel/Sheets. Es lo mismo
que bajar el reporte avanzado a mano desde YouTube Studio (Analytics >
Overview > Ver mas > modo avanzado > Descargar), pero automatico y ya
cruzado con los datos de produccion de cada video.

```powershell
py performance_report.py                       # todas las cuentas del log
py performance_report.py --account impixxel    # solo un canal
```

Ademas de generar el CSV, imprime un resumen: retencion alta vs baja, videos
cortos vs largos, y si el keyword_score/title_score de la fase de research
(vidIQ) predijo algo real -- para no tener que armar esas comparaciones a
mano en la planilla cada vez.

## Generar un video con un clic

Doble clic en **`generar_video.bat`** (en la carpeta del proyecto). Internamente corre
`--auto`: toma el siguiente tema no usado de `topics.txt`, genera el video completo, y
guarda un log en `logs/run_<fecha>.log`. Si algo falla (red, clave faltante, etc.), el
error queda registrado en `logs/fail_<fecha>.log` **y el tema no se marca como usado** —
puedes volver a intentar sin perder el tema del día.

`used_topics.json` lleva el registro de qué temas ya se produjeron, para que `--auto`
nunca repita uno.

El resultado queda en `output/AAAA-MM-DD-slug/`:

| Archivo | Contenido |
|---|---|
| `video.mp4` | El Short final (subtítulos quemados, <60s) |
| `title.txt` / `description.txt` | Copiar/pegar al subir |
| `script.json` | Guion + search terms (auditable/editable) |
| `voice.mp3`, `subs.ass`, `clips/` | Intermedios para depurar |

## Flujo diario recomendado

1. Doble clic en `generar_video.bat` (o `py pipeline.py --auto`) — ~2-4 min.
2. Revisa `video.mp4` 30 segundos; publica desde YouTube Studio con `title.txt` y `description.txt`.
3. Cada semana: revisa retención en YouTube Analytics y ajusta el prompt de `SCRIPT_PROMPT` en `pipeline.py`.

## Programarlo para que corra solo (opcional)

Por defecto **no** hay nada programado — el video se genera solo cuando tú lo disparas.
Si más adelante quieres que corra automáticamente todos los días a una hora fija, registra
una tarea programada de Windows (ejemplo: todos los días a las 7:00 AM):

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument '-ExecutionPolicy Bypass -File "<ruta-local-del-proyecto>\scripts\run_auto.ps1"'
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00AM
Register-ScheduledTask -TaskName "FacelessShorts-Daily" -Action $action -Trigger $trigger `
  -Description "Genera 1 YouTube Short automatico por dia"
```

Para quitarla: `Unregister-ScheduledTask -TaskName "FacelessShorts-Daily" -Confirm:$false`

## Notas

- Voces alternativas: `py -m edge_tts --list-voices | findstr en-US`
- La subida automática vía YouTube Data API deja los videos en privado hasta pasar
  la auditoría de Google; por eso el MVP termina en carpeta local (publicación manual ~30s).
- Blueprint y decisiones del proyecto: `<ruta local a tus notas de planificacion>`
