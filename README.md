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
py pipeline.py --script-file sample_script.json

# Sin Pexels (fondos de gradiente)
py pipeline.py "topic" --no-pexels

# Genera 5 ideas de tema nuevas (angulos virales probados)
py pipeline.py --ideas

# Modo automatico: elige el siguiente tema no usado de topics.txt y corre todo
# (genera 5 ideas nuevas solas si topics.txt se agota). Nunca repite un tema.
py pipeline.py --auto

# Opciones: --voice en-US-AriaNeural --rate "+5%" --clips 6
```

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
  -Argument '-ExecutionPolicy Bypass -File "C:\Users\Khine\Desktop\Workspace\Proyectos_Software\Videos\scripts\run_auto.ps1"'
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00AM
Register-ScheduledTask -TaskName "FacelessShorts-Daily" -Action $action -Trigger $trigger `
  -Description "Genera 1 YouTube Short automatico por dia"
```

Para quitarla: `Unregister-ScheduledTask -TaskName "FacelessShorts-Daily" -Confirm:$false`

## Notas

- Voces alternativas: `py -m edge_tts --list-voices | findstr en-US`
- La subida automática vía YouTube Data API deja los videos en privado hasta pasar
  la auditoría de Google; por eso el MVP termina en carpeta local (publicación manual ~30s).
- Blueprint y decisiones del proyecto: `C:\Users\Khine\.claude\plans\quiero-crear-un-canal-fluttering-wadler.md`
