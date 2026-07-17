"""Faceless Shorts pipeline: tema -> video vertical listo para subir.

Etapas:
  1. SCRIPT    Claude API (guion + search terms + titulo + descripcion)
  2. AUDIO     edge-tts (mp3 + timestamps por palabra, gratis)
  3. MEDIA     Pexels API (clips verticales) o gradientes generados (fallback)
  4. SUBS      ASS word-level estilo Hormozi, quemados en el video
  5. ASSEMBLY  FFmpeg puro: 1080x1920 @ 30fps, CRF 21, AAC 192k

Uso:
  py pipeline.py "the 50/30/20 budget rule"
  py pipeline.py --script-file sample_script.json      (sin Claude API)
  py pipeline.py "topic" --no-pexels                   (fondos de gradiente)
  py pipeline.py --ideas                               (genera 5 temas nuevos)

Claves (archivo .env o variables de entorno):
  ANTHROPIC_API_KEY   requerida salvo que uses --script-file
  PEXELS_API_KEY      opcional; sin ella se usan fondos de gradiente
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import subprocess
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).parent
OUTPUT_ROOT = ROOT / "output"
LOG_DIR = ROOT / "logs"
USED_TOPICS_FILE = ROOT / "used_topics.json"

MODEL = "claude-opus-4-8"
DEFAULT_VOICE = "en-US-AndrewNeural"
DEFAULT_RATE = "+8%"
DEFAULT_CLIPS = 10  # ~4-5s/escena en un Short de 45s. Antes 5 (~9s/escena) -- muy
                    # por debajo del benchmark de retencion de 2-4s por corte
                    # (ver RETENCION_PSICOLOGIA.md secc. 4). Subir aun mas si el
                    # guion tiene muchos beats cortos.
WIDTH, HEIGHT, FPS = 1080, 1920, 30

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "script": {
            "type": "string",
            "description": "Voiceover text, word-for-word, 110-130 words, no markdown",
        },
        "search_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "8-12 concrete, visual stock-footage queries (objects/scenes, not concepts). "
                            "More, shorter scenes beat fewer long ones -- retention research shows "
                            "high-performing Shorts cut every 2-4 seconds, not every 8-9.",
        },
        "title": {"type": "string", "description": "YouTube Shorts title, <90 chars, curiosity-driven"},
        "description": {"type": "string", "description": "YouTube description with 3-5 hashtags at the end"},
        "music_mood": {
            "type": "string",
            "description": "Short text prompt (English) describing instrumental background music matching "
                            "this script's tone, for an AI music generator. E.g. 'upbeat quirky ukulele pop, "
                            "playful and light' or 'tense minimal synth, building suspense'. No vocals.",
        },
    },
    "required": ["script", "search_terms", "title", "description", "music_mood"],
    "additionalProperties": False,
}

SCRIPT_PROMPT = """\
Create a viral YouTube Short script about: {topic}

Context: personal-finance channel for a US/English-speaking audience. Assume 50% of
viewers watch on mute (subtitles are burned in). Target 40-50 seconds of spoken content.

Role: you are a scriptwriter whose Shorts consistently retain viewers past the 3-second mark.

Voice: second person throughout ("you", "your paycheck", "your bank account") — never
"we" or "I". This is proven to retain viewers better than third-person narration.

Rhythm (follow this cadence, it is not optional): short sentence. Short sentence. One
longer sentence that adds depth or nuance. Short sentence. A question, roughly every
4-6 sentences, to keep the viewer mentally engaged.

Instructions:
1. Open with a hook in the first sentence: a curiosity gap, a bold claim, or a surprising
   number. The first 1-2 seconds decide whether the viewer swipes away (this is the single
   biggest drop-off point in short-form video) — the opening must never be a slow warm-up.
2. Deliver value with the "slippery slide": second-best point first, best point early.
3. Add 1-2 mini re-hooks ("but here's the part nobody mentions...", "and then it got worse")
   roughly every 15 seconds — this exploits the Zeigarnik effect (the brain fixates on
   unresolved information) to prevent mid-video drop-off, not just at the very start.
4. Close with a line that repeats the EXACT key word or phrase from the opening hook
   (not just the same theme — the literal word), reframed by what the viewer now knows.
   Example: hook "Hitler's own men didn't recognize him" -> closer "...and by the end,
   even Hitler's own men didn't recognize HIM." The literal repetition is what makes the
   final-to-first splice read as a real loop instead of "a new video starting" — this
   drives rewatches (>100% watched), the strongest retention signal Shorts rewards.
5. NEVER speak a call-to-action ("subscribe", "follow for more", "let me know below") inside
   the script. Announcing the video is ending causes a hard drop-off right at that line
   (viewers mentally close out before the real ending) — the CTA belongs ONLY in the
   description, never in spoken audio.
6. Write the script as a sequence of short, punchy visual beats (one clear image/moment
   per sentence or two) rather than long flowing paragraphs — each beat should map to a
   distinct scene change every 2-4 seconds of spoken audio, matching how high-retention
   Shorts are cut. Avoid any beat that would need more than ~4 seconds of the same visual.
   The FIRST search_term must literally depict the subject of the first spoken sentence —
   any mismatch between the first words heard and the first image shown reads as
   incongruence before the viewer consciously processes it, and the thumb is already
   swiping by then.

Pick ONE of these proven angle templates to frame the topic (whichever fits best):
- "Why can't you ___?" — explains a universal money frustration through a real rule or bias
- "You never noticed that ___" — reveals a hidden mechanic in something the viewer does weekly
- "The ___ effect" — names a real, citable phenomenon and mirrors it onto the viewer's habits
- "What if your ___ is ___?" — a provocative reframe grounded in a concrete number or rule

Constraints:
- 110-130 words. Conversational, spoken English. Fragments are fine.
- Actionable and specific: real numbers, real rules, real examples.
- NO markdown, NO emojis, NO "in this video", NO headers. Ready to voice as-is.
- search_terms must be things a stock-footage site can match visually:
  "person counting dollar bills" yes, "financial freedom" no. One term per scene,
  in the order the scenes should appear.
- description: open with a 1-2 sentence hook mirroring the script's tone, one sentence
  teasing the reframe, then 3-5 hashtags on their own line at the end.
"""

IDEAS_PROMPT = """\
Generate 5 viral YouTube Shorts topic ideas for a personal-finance channel (US/English
audience). Use these proven angle templates, picking whichever fits each idea best:
- "Why can't you ___?" — a universal money frustration explained through a real rule/bias
- "You never noticed that ___" — a hidden mechanic in a weekly financial habit
- "The ___ effect" — a real, citable phenomenon mirrored onto money behavior
- "What if your ___ is ___?" — a provocative reframe grounded in a concrete number/rule

Each idea must be a short, curiosity-driven title under 70 characters, specific enough
to script in under 130 words (one clear rule, mechanism, or number — not a broad theme).
Avoid topics already in this list: {existing_topics}
"""

IDEAS_SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 5,
            "description": "5 short, specific, curiosity-driven video topic titles",
        }
    },
    "required": ["ideas"],
    "additionalProperties": False,
}


def log(stage: str, msg: str) -> None:
    print(f"[{stage}] {msg}", flush=True)


def run(cmd: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Comando fallo ({cmd[0]}):\n{result.stderr[-2000:]}")


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def with_retries(fn, *args, attempts: int = 3, delay: float = 10.0, **kwargs):
    """Reintenta llamadas de red (Claude, edge-tts) para que fallos transitorios
    no arruinen una corrida desatendida (tarea programada)."""
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            log("retry", f"{fn.__name__} intento {attempt}/{attempts} fallo: {e}")
            if attempt < attempts:
                time.sleep(delay)
    raise last_exc


# ------------------------------------------------------------- AUTO TOPICS

def _load_used_topics() -> set[str]:
    if USED_TOPICS_FILE.exists():
        return set(json.loads(USED_TOPICS_FILE.read_text(encoding="utf-8")))
    return set()


def _mark_topic_used(topic: str) -> None:
    used = _load_used_topics()
    used.add(topic)
    USED_TOPICS_FILE.write_text(json.dumps(sorted(used), indent=2, ensure_ascii=False), encoding="utf-8")


def pick_next_topic() -> str:
    """Elige el siguiente tema no usado de topics.txt. Si se agotaron, genera 5 mas
    con Claude y los agrega al archivo. Nunca repite un tema ya producido."""
    topics_path = ROOT / "topics.txt"
    used = _load_used_topics()
    lines = [
        line.strip() for line in topics_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ] if topics_path.exists() else []

    remaining = [t for t in lines if t not in used]
    if remaining:
        return remaining[0]

    log("auto", "topics.txt agotado; generando 5 ideas nuevas con Claude...")
    ideas = with_retries(generate_ideas, lines)
    with topics_path.open("a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(ideas) + "\n")
    log("auto", f"5 ideas nuevas agregadas a topics.txt")
    return ideas[0]


# ---------------------------------------------------------------- 1. SCRIPT

def generate_script(topic: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    log("script", f"Generando guion con {MODEL}...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": SCRIPT_SCHEMA}},
        messages=[{"role": "user", "content": SCRIPT_PROMPT.format(topic=topic)}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    log("script", f"{len(data['script'].split())} palabras, {len(data['search_terms'])} search terms")
    return data


def generate_ideas(existing_topics: list[str]) -> list[str]:
    import anthropic

    client = anthropic.Anthropic()
    log("ideas", f"Generando 5 ideas con {MODEL}...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": IDEAS_SCHEMA}},
        messages=[{
            "role": "user",
            "content": IDEAS_PROMPT.format(existing_topics=", ".join(existing_topics) or "none"),
        }],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["ideas"]


# ----------------------------------------------------------------- 2. AUDIO

async def _tts(script: str, voice: str, rate: str, mp3_path: Path) -> list[tuple[float, float, str]]:
    import edge_tts

    words: list[tuple[float, float, str]] = []
    communicate = edge_tts.Communicate(script, voice, rate=rate, boundary="WordBoundary")
    with open(mp3_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000
                end = (chunk["offset"] + chunk["duration"]) / 10_000_000
                words.append((start, end, chunk["text"]))
    return words


KOKORO_DIR = ROOT / "tools" / "kokoro_tts"
# Prefijos de voz Kokoro -> si --voice empieza con uno de estos, se usa Kokoro
# (voz local, mas natural, gratis e ilimitada) en vez de edge-tts.
KOKORO_VOICE_PREFIXES = ("em_", "ef_", "am_", "af_", "bm_", "bf_")


def _kokoro_tts(script: str, voice: str, wav_path: Path, speed: float = 1.0) -> list[tuple[float, float, str]]:
    """Corre tools/kokoro_tts/synth.py en su propio venv (Python 3.12; Kokoro
    no compila aun en 3.14). Timestamps de palabra son una ESTIMACION por
    longitud de caracter, no timing acustico real -- ver synth.py."""
    text_file = wav_path.with_suffix(".txt")
    words_file = wav_path.with_suffix(".words.json")
    text_file.write_text(script, encoding="utf-8")
    run([
        "uv", "run", "--directory", str(KOKORO_DIR), "synth.py",
        "--text-file", str(text_file), "--voice", voice,
        "--out", str(wav_path), "--words-out", str(words_file),
        "--speed", str(speed),
    ])
    words_raw = json.loads(words_file.read_text(encoding="utf-8"))
    return [(float(s), float(e), w) for s, e, w in words_raw]


WPS_MIN, WPS_MAX = 2.3, 2.7  # rango reportado como optimo para narracion clara en mute


def _check_pacing(script: str, target_seconds: float = 45.0) -> None:
    """Avisa ANTES de gastar creditos de TTS/Nano Banana si la densidad de
    palabras-por-segundo del guion cae fuera de [WPS_MIN, WPS_MAX]. No bloquea,
    solo informa (igual que el resto de logs del pipeline) -- ver
    RETENTION_CHECKLIST.md."""
    word_count = len(script.split())
    wps = word_count / target_seconds
    if wps < WPS_MIN:
        target_words = round(WPS_MIN * target_seconds)
        log("pacing", f"AVISO: {word_count} palabras / {target_seconds:.0f}s = "
                       f"{wps:.2f} wps (lento, riesgo de curva 'Hump'). "
                       f"Considera subir a ~{target_words} palabras.")
    elif wps > WPS_MAX:
        target_words = round(WPS_MAX * target_seconds)
        log("pacing", f"AVISO: {word_count} palabras / {target_seconds:.0f}s = "
                       f"{wps:.2f} wps (denso, se pierden palabras en mute). "
                       f"Considera bajar a ~{target_words} palabras.")
    else:
        log("pacing", f"{word_count} palabras / {target_seconds:.0f}s = {wps:.2f} wps (OK)")


def _rate_to_kokoro_speed(rate: str) -> float:
    """Reusa el mismo --rate de edge-tts ('+8%', '-15%') como velocidad para
    Kokoro, asi no hace falta un flag nuevo: '+0%' o vacio = 1.0 normal."""
    try:
        pct = float(rate.strip().replace("%", ""))
        return max(0.5, min(2.0, 1.0 + pct / 100))
    except (ValueError, AttributeError):
        return 1.0


def generate_audio(script: str, voice: str, rate: str, out_dir: Path) -> tuple[Path, list]:
    if voice.startswith(KOKORO_VOICE_PREFIXES):
        wav_path = out_dir / "voice.wav"
        speed = _rate_to_kokoro_speed(rate)
        log("audio", f"Sintetizando voz con Kokoro (local, voz {voice}, speed {speed})...")
        words = _kokoro_tts(script, voice, wav_path, speed=speed)
        # convertir a mp3 para que el resto del pipeline (assemble, etc) sea igual
        mp3_path = out_dir / "voice.mp3"
        run(["ffmpeg", "-y", "-i", str(wav_path), "-ar", "44100", str(mp3_path)])
    else:
        mp3_path = out_dir / "voice.mp3"
        log("audio", f"Sintetizando voz ({voice}, rate {rate})...")
        words = asyncio.run(_tts(script, voice, rate, mp3_path))

    if not words:
        raise RuntimeError("TTS no devolvio timestamps de palabras")

    # Recorta el silencio de la COLA para que el autoloop del Short empalme
    # apretado (final->inicio) y dispare re-watches (>100% de reproduccion, la
    # senal mas fuerte en Shorts). Solo afecta despues de la ultima palabra, asi
    # que no desincroniza los subtitulos (sus timestamps caen antes del silencio).
    trimmed = out_dir / "voice_trim.mp3"
    try:
        run(["ffmpeg", "-y", "-i", str(mp3_path), "-af",
             "areverse,silenceremove=start_periods=1:start_silence=0.1:"
             "start_threshold=-45dB,areverse", str(trimmed)])
        trimmed.replace(mp3_path)
    except Exception as e:
        log("audio", f"trim de silencio final omitido: {e}")

    dur = ffprobe_duration(mp3_path)
    log("audio", f"{dur:.1f}s de audio, {len(words)} palabras")
    if dur > 58:
        log("audio", "AVISO: el audio supera 58s; el Short puede exceder 60s")
    return mp3_path, words


# ------------------------------------------------------------ 3. SUBTITLES

def _ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int(seconds % 3600 // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


SUB_LINE_CHARS = 14  # max chars por linea a fontsize 96 sin acercarse a los bordes


def _split_index(tokens: list[str]) -> int:
    """Indice de token donde insertar el salto \\N para 2 lineas balanceadas;
    len(tokens) (sin salto, una sola linea) si todo cabe en SUB_LINE_CHARS.
    WrapStyle 2 no auto-envuelve, por eso el corte es explicito (feedback del
    usuario: los bloques largos se salian de pantalla)."""
    if len(" ".join(tokens)) <= SUB_LINE_CHARS or len(tokens) < 2:
        return len(tokens)
    best_i, best_diff = 1, float("inf")
    for i in range(1, len(tokens)):
        diff = abs(len(" ".join(tokens[:i])) - len(" ".join(tokens[i:])))
        if diff < best_diff:
            best_i, best_diff = i, diff
    return best_i


# Colores ASS (formato BBGGRR): palabra activa amarilla, resto blanco.
_CAP_ACTIVE = r"{\c&H00FFFF&}"
_CAP_WHITE = r"{\c&HFFFFFF&}"


def generate_subtitles(words: list[tuple[float, float, str]], out_dir: Path) -> Path:
    # Karaoke palabra-por-palabra: agrupa en bloques cortos (max 3 palabras / 18
    # chars, texto-como-imagen: lectura instantanea sin "leer" gramaticalmente)
    # para conservar contexto de 2 lineas, pero emite UN evento por palabra con
    # la activa resaltada en amarillo -- fija la mirada (clave con ~50% viendo
    # en mute) y sube la retencion en Shorts.
    chunks: list[list[tuple[float, float, str]]] = []
    buf: list[tuple[float, float, str]] = []
    for w in words:
        buf.append(w)
        if len(buf) >= 3 or len(" ".join(x[2] for x in buf)) >= 18:
            chunks.append(buf)
            buf = []
    if buf:
        chunks.append(buf)

    events = []
    for ci, chunk in enumerate(chunks):
        # fin de display del bloque: hasta el inicio del siguiente (anti-parpadeo)
        chunk_end = chunk[-1][1]
        if ci + 1 < len(chunks):
            chunk_end = max(chunk_end, chunks[ci + 1][0][0])
        tokens = [x[2].upper().replace("\\", "").replace("{", "").replace("}", "")
                  for x in chunk]
        split = _split_index(tokens)
        for wi, (ws, _we, _w) in enumerate(chunk):
            start = ws
            end = chunk[wi + 1][0] if wi + 1 < len(chunk) else chunk_end
            if end <= start:
                end = start + 0.05
            parts = [f"{_CAP_ACTIVE}{t}{_CAP_WHITE}" if j == wi else t
                     for j, t in enumerate(tokens)]
            line1 = " ".join(parts[:split])
            line2 = " ".join(parts[split:])
            text = line1 + ("\\N" + line2 if line2 else "")
            events.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Cap,,0,0,0,,{text}")

    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Arial Black,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,2,60,60,640,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"

    ass_path = out_dir / "subs.ass"
    ass_path.write_text(ass, encoding="utf-8")
    log("subs", f"{len(events)} eventos karaoke ({len(chunks)} bloques)")
    return ass_path


# ---------------------------------------------------------------- 4. MEDIA

GRADIENTS = [
    ("0x0f2027", "0x2c5364"), ("0x1a2a6c", "0x3a6073"), ("0x232526", "0x414345"),
    ("0x141e30", "0x243b55"), ("0x2c3e50", "0x4ca1af"), ("0x000428", "0x004e92"),
]


def _gradient_clip(index: int, duration: float, path: Path) -> None:
    c0, c1 = GRADIENTS[index % len(GRADIENTS)]
    run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"gradients=s={WIDTH}x{HEIGHT}:d={duration:.2f}:c0={c0}:c1={c1}:speed=0.03:r={FPS}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        str(path),
    ])


def _pexels_download(term: str, path: Path, api_key: str) -> bool:
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": term, "per_page": 5, "orientation": "portrait", "size": "medium"},
            headers={"Authorization": api_key},
            timeout=30,
        )
        r.raise_for_status()
        for video in r.json().get("videos", []):
            if video.get("duration", 0) < 4:
                continue
            files = [f for f in video.get("video_files", [])
                     if f.get("height", 0) >= 1280 and f.get("width", 0) <= f.get("height", 0)]
            if not files:
                continue
            best = min(files, key=lambda f: abs(f["height"] - HEIGHT))
            with requests.get(best["link"], stream=True, timeout=120) as dl:
                dl.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in dl.iter_content(1 << 16):
                        f.write(chunk)
            return True
    except Exception as e:
        log("media", f"Pexels fallo para '{term}': {e}")
    return False


NANOBANANA_MODEL = "gemini-2.5-flash-image"
# Neutral a proposito: NO fuerza "photo-realistic" porque eso arruina estilos
# especificos (ej. splash art de videojuegos). Cada prompt define su propio estilo.
# Guardrails de composicion: el personaje quedaba "lanzado"/descentrado en escenas
# de accion; esto fuerza encuadre estable sin perder la pose que pida la escena.
NANOBANANA_STYLE_SUFFIX = (
    ", vertical 9:16 portrait composition, character centered in frame and fully "
    "visible, stable and grounded pose appropriate to the scene (not falling, not "
    "tilted at a weird angle, not cropped at the edges), no text, no watermark, no logos"
    ", anatomically correct: exactly two arms and two hands per human figure, five "
    "fingers per hand, no extra or missing limbs, no distorted or merged body parts, "
    "no nonsensical objects"
    ", if a human figure's face is visible, eyes looking slightly toward the lower-"
    "center of frame (where captions appear), with rim light separating the subject "
    "silhouette from the background"
)

SKICK_REFERENCE = ROOT / "assets" / "skick" / "skick_reference.png"
LOL_CHAMPIONS_DIR = ROOT / "assets" / "lol_db" / "champions"


def _champion_references(term: str) -> list[Path]:
    """Detecta nombres de campeones de LoL mencionados en la escena y devuelve
    sus splash oficiales como referencia de fidelidad (mismo mecanismo que
    SKICK_REFERENCE, pero soporta VARIOS personajes en una misma escena --
    necesario para historias de lore con mas de un protagonista, ej. Yasuo
    y Yone en el mismo duelo)."""
    if not LOL_CHAMPIONS_DIR.exists():
        return []
    refs = []
    term_lower = term.lower()
    for splash in LOL_CHAMPIONS_DIR.glob("*_splash.jpg"):
        champ_id = splash.stem.replace("_splash", "")
        # \b no basta con ids que empiezan/terminan en caracter no-alfanumerico
        # (ninguno aqui), pero evita matches parciales dentro de otra palabra
        # (ej. "vi" dentro de "victorious", "sion" dentro de "vision", "nami"
        # dentro de "dynamic" -- visto en produccion, genero hojas de personaje
        # de sobra para campeones que no aparecian en el guion).
        if re.search(rf"\b{re.escape(champ_id.lower())}\b", term_lower):
            refs.append(splash)
    return refs


ROBLOX_SHEETS_DIR = ROOT / "assets" / "lol_db" / "roblox_sheets"


def _champion_id(splash: Path) -> str:
    return splash.stem.replace("_splash", "")


def _character_sheet_prompt(champ_id: str, style_directive: str) -> str:
    return (
        f"A Roblox game character reference sheet for a custom avatar based on "
        f"{champ_id.title()} from League of Legends. Show the SAME avatar three "
        "times side by side on a plain neutral gray background: front view, "
        "3/4 view, and side view, all in a neutral standing pose with arms "
        "relaxed. This is a character turnaround sheet, not a scene -- no "
        "background environment, no props, no action. "
        f"MANDATORY ART STYLE: {style_directive}. Blocky cylinder/box limbs, "
        "simple flat face, voxel proportions, cel-shaded Roblox game aesthetic "
        "applied identically to all three views. Keep the character's identity "
        "(hair, face markings, outfit colors, weapon, silhouette) clearly "
        "recognizable from the reference image but fully rebuilt in Roblox "
        "blocks -- ignore the reference image's painted art style completely. "
        "Vertical 9:16, no text, no labels."
    )


CHARACTERS_DIR = ROOT / "assets" / "characters"
CHARACTERS_MANIFEST = CHARACTERS_DIR / "manifest.json"
# palabras que marcan una FASE distinta del mismo personaje (ej. Viego rey vs
# Viego fantasma) -- si ninguna aparece en la escena, se usa la fase "default"
PHASE_KEYWORDS = ["ghost", "spectral", "skeletal", "phantom", "undead", "ruined",
                  "child", "young", "prisoner", "warden", "possessed", "corrupted"]

_CHARACTER_PATTERN = re.compile(r"^([A-Za-zÀ-ÿ][\w' -]*?) character:", re.IGNORECASE)


def _detect_named_character(term: str) -> tuple[str, str] | None:
    """Detecta el patron '<Nombre> character: ...' al inicio de un search_term
    (convencion ya usada para Skick, generalizada a cualquier personaje
    recurrente -- campeones de lore, figuras historicas de HiddenFacts,
    secundarios de sketches). Devuelve (nombre, fase) o None si no aplica.
    La fase es la primera palabra de PHASE_KEYWORDS que aparece en el texto,
    o 'default' si el personaje aparece en su forma base."""
    m = _CHARACTER_PATTERN.match(term.strip())
    if not m:
        return None
    name = m.group(1).strip()
    term_lower = term.lower()
    phase = next((kw for kw in PHASE_KEYWORDS if kw in term_lower), "default")
    return name, phase


def _character_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _load_characters_manifest() -> dict:
    if CHARACTERS_MANIFEST.exists():
        try:
            return json.loads(CHARACTERS_MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_characters_manifest(data: dict) -> None:
    CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    CHARACTERS_MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_named_character_sheet(name: str, phase: str, style_directive: str,
                                api_key: str, seed_term: str, api_key_style_id: str = "") -> Path | None:
    """Hoja de personaje PERSISTENTE (entre videos, no solo dentro de una
    corrida) para cualquier personaje recurrente -- marca personal reconocible
    en ambos canales. Primera vez que aparece un personaje/fase: se genera y
    se guarda en assets/characters/<slug>/<fase>_<estilo>.png + se registra en
    manifest.json. Veces siguientes (mismo video u otro futuro): se reusa tal
    cual, igual que ya pasa con los campeones de LoL (ver _get_character_sheet)."""
    slug = _character_slug(name)
    char_dir = CHARACTERS_DIR / slug
    char_dir.mkdir(parents=True, exist_ok=True)
    style_key = re.sub(r"[^a-z0-9]+", "-", style_directive.lower())[:40]
    sheet_path = char_dir / f"{phase}_{style_key}.png"

    manifest = _load_characters_manifest()
    entry = manifest.setdefault(slug, {"name": name, "phases": {}})

    if sheet_path.exists():
        log("media", f"personaje '{name}' fase '{phase}': reusando de base de datos")
        return sheet_path

    # Skick ya tenia una referencia fija de antes de esta base de datos
    # generica (assets/skick/skick_reference.png) -- sembrar la fase default
    # con esa imagen en vez de generar una nueva, para no crear una segunda
    # version distinta del personaje ya establecido
    if slug == "skick" and phase == "default" and SKICK_REFERENCE.exists():
        import shutil
        shutil.copyfile(SKICK_REFERENCE, sheet_path)
        entry["phases"][f"{phase}_{style_key}"] = sheet_path.name
        manifest[slug] = entry
        _save_characters_manifest(manifest)
        log("media", f"personaje 'Skick' fase 'default': sembrado desde la referencia original")
        return sheet_path

    # si ya existe la fase "default" de este personaje, la usamos como
    # referencia de identidad para que la fase nueva (ej. fantasma) mantenga
    # la misma cara/silueta reconocible en vez de reinventar al personaje
    default_key = f"default_{style_key}"
    seed_ref = None
    if phase != "default" and default_key in entry["phases"]:
        candidate = char_dir / f"{entry['phases'][default_key]}"
        if candidate.exists():
            seed_ref = candidate

    log("media", f"generando hoja de personaje NUEVA para '{name}' fase '{phase}' "
                  "(se guarda para siempre, se reusa en todos los videos futuros)...")
    prompt = (
        f"A character reference sheet/turnaround for '{name}', shown three times "
        "side by side on a plain neutral background: front view, 3/4 view, and "
        "side view, same pose, arms relaxed, no action, no props, no environment. "
        f"MANDATORY ART STYLE: {style_directive}. "
        f"Character description/context: {seed_term}. "
        "Keep the identity (face, outfit, colors, silhouette) clearly consistent "
        "across the three views. Vertical 9:16, no text, no labels."
    )
    ok = _nanobanana_generate_image(prompt, sheet_path, api_key, reference_image=seed_ref, attempts=3)
    if not ok:
        return None
    entry["phases"][f"{phase}_{style_key}"] = sheet_path.name
    manifest[slug] = entry
    _save_characters_manifest(manifest)
    return sheet_path


def _get_character_sheet(splash: Path, style_directive: str, api_key: str) -> Path | None:
    """Genera (o reutiliza) una 'hoja de personaje' Roblox: el mismo avatar en 3
    poses fijas sobre fondo neutro, generada UNA vez por campeon+estilo y cacheada
    en disco. Usarla como referencia (en vez del splash pintado original) mantiene
    consistente el diseño del personaje entre escenas y evita que el modelo copie
    el estilo pintado del splash en escenas atmosfericas (ver memoria
    estilo-roblox-nanobanana)."""
    ROBLOX_SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    champ_id = _champion_id(splash)
    cache_key = re.sub(r"[^a-z0-9]+", "-", style_directive.lower())[:40]
    sheet_path = ROBLOX_SHEETS_DIR / f"{champ_id}_{cache_key}.png"
    if sheet_path.exists():
        log("media", f"hoja de personaje '{champ_id}': reusando cache")
        return sheet_path

    log("media", f"generando hoja de personaje para '{champ_id}' (una vez, se reusa en todas las escenas)...")
    prompt = _character_sheet_prompt(champ_id, style_directive)
    ok = _nanobanana_generate_image(prompt, sheet_path, api_key, reference_image=splash, attempts=3)
    return sheet_path if ok else None


USAGE_LOG_PATH = ROOT / "gemini_usage.json"
COST_PER_IMAGE = 0.04
COST_PER_SONG = 0.08


def _track_gemini_usage(kind: str, success: bool) -> None:
    """Registra cada llamada a Nano Banana/Lyria en gemini_usage.json (por dia),
    para poder avisar gasto estimado y fallos por cuota sin depender de una API
    de balance que Gemini no expone al key de consumidor."""
    today = datetime.now().strftime("%Y-%m-%d")
    data = {}
    if USAGE_LOG_PATH.exists():
        try:
            data = json.loads(USAGE_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    day = data.setdefault(today, {"images_ok": 0, "images_failed": 0,
                                   "songs_ok": 0, "songs_failed": 0})
    key = f"{'images' if kind == 'image' else 'songs'}_{'ok' if success else 'failed'}"
    day[key] += 1
    USAGE_LOG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _usage_summary_today() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    if not USAGE_LOG_PATH.exists():
        return ""
    data = json.loads(USAGE_LOG_PATH.read_text(encoding="utf-8")).get(today)
    if not data:
        return ""
    cost = data["images_ok"] * COST_PER_IMAGE + data["songs_ok"] * COST_PER_SONG
    fails = data["images_failed"] + data["songs_failed"]
    msg = (f"hoy: {data['images_ok']} imagenes + {data['songs_ok']} canciones "
           f"OK (~${cost:.2f} estimado)")
    if fails:
        msg += f", {fails} llamadas fallidas (posible limite de cuota/creditos agotados)"
    return msg


def _nanobanana_generate_image(prompt: str, path: Path, api_key: str,
                                reference_image: Path | None = None,
                                reference_images: list[Path] | None = None,
                                style_directive: str | None = None,
                                attempts: int = 2) -> bool:
    """reference_image: un solo personaje (uso original, Skick). reference_images:
    varios personajes a la vez (lore multi-personaje). style_directive: estilo de
    arte OBLIGATORIO para todo el frame -- va como PRIMERA instruccion, por encima
    de la de fidelidad, porque el modelo tiende a copiar el estilo del splash de
    referencia en escenas atmosfericas si no se le subordina explicitamente
    (visto en el video de Yasuo Roblox: escenas de bosque/niebla revirtieron al
    estilo pintado de LoL). attempts>1: reintento ante fallos transitorios de API."""
    all_refs = list(reference_images or [])
    if reference_image:
        all_refs.insert(0, reference_image)
    all_refs = [r for r in all_refs if r and r.exists()]

    parts = []
    if style_directive:
        parts.append({"text": f"MANDATORY ART STYLE: {style_directive}. This art style applies "
                               "to EVERY element of the frame -- characters, background, props, "
                               "lighting, atmosphere -- with zero exceptions, no matter how "
                               "dramatic or moody the scene is. Never revert to the art style "
                               "of any reference image."})
    if all_refs:
        n = len(all_refs)
        ref_word = "the reference image" if n == 1 else f"each of the {n} reference images"
        if style_directive:
            fidelity = (f"The reference images define each character's IDENTITY only -- face, "
                        f"hair, outfit, silhouette, identifying features from {ref_word} -- NOT "
                        "the art style. Re-render every character fully in the mandatory art "
                        "style above while keeping their identity clearly recognizable. If "
                        "multiple reference images are given, each corresponds to a different "
                        "character appearing together as described in the scene.")
        else:
            fidelity = (f"CRITICAL: keep every character's design 100% faithful to {ref_word} "
                        "provided (same face, same outfit, same silhouette, same identifying "
                        "features) - only change pose/expression/background/art-style-treatment "
                        "to match the scene described below. If multiple reference images are "
                        "given, each corresponds to a different character that should appear "
                        "together as described in the scene.")
        parts.append({"text": fidelity})
    parts.append({"text": prompt + NANOBANANA_STYLE_SUFFIX})
    for ref in all_refs:
        parts.append({
            "inlineData": {
                "mimeType": "image/png" if ref.suffix.lower() == ".png" else "image/jpeg",
                "data": base64.b64encode(ref.read_bytes()).decode("ascii"),
            }
        })

    for attempt in range(attempts):
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{NANOBANANA_MODEL}:generateContent",
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": parts}],
                    "generationConfig": {"imageConfig": {"aspectRatio": "9:16"}},
                },
                timeout=60,
            )
            r.raise_for_status()
            resp_parts = r.json()["candidates"][0]["content"]["parts"]
            for part in resp_parts:
                if "inlineData" in part:
                    path.write_bytes(base64.b64decode(part["inlineData"]["data"]))
                    _track_gemini_usage("image", True)
                    return True
            raise RuntimeError("respuesta sin imagen")
        except Exception as e:
            if attempt < attempts - 1:
                log("media", f"Nano Banana fallo (intento {attempt + 1}), reintento en 5s: {e}")
                time.sleep(5)
            else:
                log("media", f"Nano Banana fallo para '{prompt[:60]}...': {e}")
                _track_gemini_usage("image", False)
    return False


def _static_image_clip(image_path: Path, duration: float, path: Path, zoom_in: bool = True,
                        punch: bool = False, hook: bool = False) -> None:
    """Convierte una imagen fija en un clip con efecto Ken Burns (zoom lento, gratis).
    Alterna zoom-in/zoom-out entre clips para variar el movimiento visual.
    punch=True: quieto los primeros ~60% y zoom rapido "golpe" el resto -- usar
    en la escena del remate/giro comico para dar un acento visual.
    hook=True: golpe de entrada -- zoom-in rapido en el primer ~20% y luego se
    asienta, para ganar la decision de swipe del primer segundo en la escena 1
    (la palanca #1 de retencion en Shorts)."""
    frames = max(int(round(duration * FPS)), 1)
    if hook:
        rush = max(int(frames * 0.2), 1)
        zexpr = f"if(lt(on,{rush}),1.0+(0.15/{rush})*on,1.15)"
    elif punch:
        hold = max(int(frames * 0.6), 1)
        zexpr = f"if(lt(on,{hold}),1.0,min(1.0+0.045*(on-{hold}),1.35))"
    else:
        zexpr = "min(zoom+0.0015,1.18)" if zoom_in else "if(eq(on,1),1.18,max(zoom-0.0015,1.0))"
    vf = (
        f"scale={WIDTH * 2}:{HEIGHT * 2}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='{zexpr}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',setsar=1"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-t", f"{duration:.2f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        str(path),
    ])


VEO_MODEL = "veo-3.1-fast-generate-preview"
VEO_CLIP_SECONDS = 8  # duracion fija que exige la API al partir de una imagen


def _veo_animate_image(image_path: Path, motion_prompt: str, api_key: str,
                       poll_timeout: float = 240.0) -> bytes | None:
    """Anima una imagen fija con Veo (image-to-video). Cuesta ~$0.80-1.20 por clip
    de 8s (tier Fast) -- usar solo en clips puntuales (--veo-hero), no en todos."""
    try:
        img_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{VEO_MODEL}:predictLongRunning",
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "instances": [{
                    "prompt": motion_prompt,
                    "image": {"bytesBase64Encoded": img_b64, "mimeType": "image/png"},
                }],
                "parameters": {"aspectRatio": "9:16"},
            },
            timeout=60,
        )
        r.raise_for_status()
        op_name = r.json()["name"]

        deadline = time.time() + poll_timeout
        while time.time() < deadline:
            time.sleep(10)
            poll = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/{op_name}",
                headers={"x-goog-api-key": api_key}, timeout=30,
            )
            poll.raise_for_status()
            data = poll.json()
            if data.get("done"):
                uri = data["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
                dl = requests.get(uri, headers={"x-goog-api-key": api_key}, timeout=120, allow_redirects=True)
                dl.raise_for_status()
                return dl.content
        log("media", f"Veo timeout esperando animacion de '{image_path.name}'")
    except Exception as e:
        log("media", f"Veo fallo para '{motion_prompt[:60]}...': {e}")
    return None


def _scene_boundaries(words: list[tuple[float, float, str]], n_clips: int,
                       audio_dur: float) -> list[float]:
    """Duracion de cada escena de modo que los cortes caigan en FIN DE FRASE
    (palabra terminada en ./!/?) en vez de en puntos equidistantes -- antes la
    imagen cambiaba a mitad de frase y se percibia como desfase voz/imagen
    (feedback del usuario). Para cada corte ideal (i*dur/n) se elige el fin de
    frase mas cercano; si una frase abarca varios cortes se cae al fin de
    palabra mas cercano para no dejar escenas vacias."""
    sentence_ends = [w[1] for w in words if w[2].rstrip('"\')').endswith((".", "!", "?", "…"))]
    word_ends = [w[1] for w in words]
    cuts: list[float] = []
    prev = 0.0
    for i in range(1, n_clips):
        ideal = audio_dur * i / n_clips
        # candidatos posteriores al corte anterior Y anteriores al final del
        # audio (margen 0.5s en ambos lados) -- sin el limite superior, la
        # ULTIMA palabra del guion (que tambien termina en '.') se colaba como
        # candidato y un corte interno terminaba clavado en audio_dur, dejando
        # escenas de duracion 0 al final (visto en produccion con guiones
        # cortos / pocas frases).
        cands = [t for t in sentence_ends if prev + 0.5 < t < audio_dur - 0.5] or \
                [t for t in word_ends if prev + 0.5 < t < audio_dur - 0.5]
        if cands:
            cut = min(cands, key=lambda t: abs(t - ideal))
        else:
            # sin mas palabras/frases disponibles (guion corto, muchas escenas):
            # repartir el tiempo restante en partes iguales para las escenas
            # que faltan, garantizando avance monotono (visto en produccion:
            # el fallback anterior podia devolver un corte ANTERIOR a 'prev'
            # y generar una duracion negativa de escena)
            remaining_clips = n_clips - i + 1
            cut = prev + (audio_dur - prev) / remaining_clips
        cuts.append(cut)
        prev = cut
    bounds = [0.0] + cuts + [audio_dur]
    return [bounds[i + 1] - bounds[i] for i in range(n_clips)]


def acquire_media(search_terms: list[str], n_clips: int, durations: list[float],
                  out_dir: Path, media_source: str, veo_hero_index: int | None = None,
                  punch_index: int | None = None, style: str | None = None) -> list[Path]:
    """media_source: 'pexels' | 'nanobanana' | 'gradient'. Siempre cae a gradiente si falla.
    veo_hero_index: si se da (y hay GEMINI_API_KEY), ese clip se anima con Veo en vez de
    quedar estatico -- modo hibrido: barato en general, impacto en el momento clave.
    punch_index: escena que recibe el zoom "golpe" (quieta y luego zoom rapido) para
    acentuar el remate/giro comico -- por defecto la penultima escena (ver
    RETENCION_PSICOLOGIA.md, feedback "falta energia visual").
    style: estilo de arte obligatorio para TODAS las escenas (campo "style" del
    guion JSON) -- ej. 'Roblox blocky voxel avatars and environments'."""
    if punch_index is None:
        punch_index = max(n_clips - 2, 0)
    clips_dir = out_dir / "clips"
    clips_dir.mkdir(exist_ok=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    clips: list[Path] = []

    terms = (search_terms * ((n_clips // max(len(search_terms), 1)) + 1))[:n_clips]

    # Con estilo (ej. Roblox) generamos primero una hoja de personaje por cada
    # campeon mencionado en CUALQUIER escena, una sola vez, y la reusamos como
    # referencia en todas las escenas -- evita que el diseño del personaje
    # varie entre escenas y que el modelo copie el estilo pintado del splash
    # (ver memoria estilo-roblox-nanobanana).
    sheet_cache: dict[str, Path] = {}
    named_char_cache: dict[tuple[str, str], Path] = {}
    if media_source == "nanobanana" and gemini_key and style:
        all_splashes = {s for t in search_terms for s in _champion_references(t)}
        for splash in all_splashes:
            sheet = _get_character_sheet(splash, style, gemini_key)
            if sheet:
                sheet_cache[_champion_id(splash)] = sheet

        # base de datos de personajes recurrentes (marca personal, ver
        # convencion '<Nombre> character: ...' generalizada de Skick) --
        # persistente entre videos via assets/characters/manifest.json
        for t in search_terms:
            detected = _detect_named_character(t)
            if detected:
                name, phase = detected
                if (name, phase) not in named_char_cache:
                    sheet = _get_named_character_sheet(name, phase, style, gemini_key, seed_term=t)
                    if sheet:
                        named_char_cache[(name, phase)] = sheet

    for i, term in enumerate(terms):
        raw = clips_dir / f"raw_{i}.mp4"
        got = False

        if media_source == "nanobanana" and gemini_key:
            img_path = clips_dir / f"nb_{i}.png"
            detected = _detect_named_character(term)
            if detected and detected in named_char_cache:
                char_ref = named_char_cache[detected]
            elif "skick" in term.lower():
                char_ref = SKICK_REFERENCE  # fallback si el guion no usa 'Skick character:'
            else:
                char_ref = None
            raw_champ_refs = _champion_references(term)
            if sheet_cache:
                champ_refs = [sheet_cache.get(_champion_id(s), s) for s in raw_champ_refs]
            else:
                champ_refs = raw_champ_refs
            gen_term = term
            if i == 0:
                # pattern interrupt (segundo 0-1): encuadre inesperado que rompe lo
                # "familiar" del feed antes de que el pulgar decida seguir scrolleando
                gen_term += (", unexpected framing: extreme low angle or dramatically "
                             "disproportionate scale between subject and surroundings")
            elif i % 2 == 1:
                # movimiento organico (humo/polvo/tela) alternado con el Ken Burns
                # mecanico -- el ojo sigue mucho mas el movimiento fluido/organico
                # que el zoom rigido (percepcion de movimiento biologico)
                gen_term += (", include drifting smoke, dust, mist, or fabric/hair "
                             "moving gently in the scene")
            if _nanobanana_generate_image(gen_term, img_path, gemini_key, reference_image=char_ref,
                                          reference_images=champ_refs, style_directive=style):
                if i == veo_hero_index:
                    log("media", f"clip {i + 1}/{n_clips}: animando con Veo (~$1, puede tardar ~1-2 min)...")
                    video_bytes = _veo_animate_image(img_path, term, gemini_key)
                    if video_bytes:
                        raw.write_bytes(video_bytes)
                        got = True
                        log("media", f"clip {i + 1}/{n_clips}: Veo OK")
                    else:
                        log("media", f"clip {i + 1}/{n_clips}: Veo fallo, cae a imagen estatica")
                if not got:
                    _static_image_clip(img_path, durations[i] + 1.0, raw, zoom_in=(i % 2 == 0),
                                        punch=(i == punch_index), hook=(i == 0))
                    got = True
                    log("media", f"clip {i + 1}/{n_clips}: Nano Banana '{term}'")
        elif media_source == "pexels" and pexels_key:
            got = _pexels_download(term, raw, pexels_key)
            if got:
                log("media", f"clip {i + 1}/{n_clips}: Pexels '{term}'")

        if not got:
            log("media", f"clip {i + 1}/{n_clips}: gradiente (fallback)")
            _gradient_clip(i, durations[i] + 1.0, raw)
        clips.append(raw)
    return clips


LYRIA_MODEL = "lyria-3-clip-preview"  # clips fijos de 30s; suficiente para loopear de fondo


def _lyria_generate_music(mood_prompt: str, out_path: Path, api_key: str) -> bool:
    """Genera musica instrumental con Lyria 3 via Gemini API (~$0.08/cancion,
    misma GEMINI_API_KEY que Nano Banana). Devuelve False y deja usar la
    biblioteca local (assets/music/) como fallback si algo falla."""
    try:
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "model": LYRIA_MODEL,
                "input": f"{mood_prompt}. Instrumental only, no vocals.",
                "response_format": {"type": "audio"},
            },
            timeout=90,
        )
        r.raise_for_status()
        data = r.json()
        for step in data.get("steps", []):
            if step.get("type") != "model_output":
                continue
            for block in step.get("content", []):
                if block.get("type") == "audio" and block.get("data"):
                    out_path.write_bytes(base64.b64decode(block["data"]))
                    _track_gemini_usage("song", True)
                    return True
    except Exception as e:
        log("music", f"Lyria fallo: {e}")
        _track_gemini_usage("song", False)
    return False


SFX_DIR = ROOT / "assets" / "sfx"


def _list_sfx() -> list[Path]:
    if not SFX_DIR.exists():
        return []
    return [p for p in SFX_DIR.iterdir()
            if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")]


def _load_sfx_manifest() -> dict:
    """assets/sfx/manifest.json: descripcion de que suena en cada archivo y
    que conceptos del guion lo justifican. Sin manifest, dict vacio."""
    path = SFX_DIR / "manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("sfx", {})
    except Exception:
        return {}


def pick_sfx_cues(words: list[tuple[float, float, str]],
                   tone: str | None = None,
                   script: str | None = None,
                   search_terms: list[str] | None = None) -> list[tuple[float, Path]]:
    """Usa Claude para colocar SFX SOLO donde la narracion describe literalmente
    el evento sonoro (espada, trueno, golpe...) -- feedback del usuario: los
    efectos 'decorativos' parecen puestos por ponerlos. Cada cue debe citar la
    palabra disparadora (trigger_word, validada contra la palabra real del
    guion). Recibe el guion completo con puntuacion, el manifest de que suena
    en cada archivo, y los search_terms (que se VE en cada escena). Max 4 cues;
    0 es una respuesta valida. Sin API key o sin efectos, lista vacia."""
    sfx_files = _list_sfx()
    if not sfx_files or not os.getenv("ANTHROPIC_API_KEY"):
        return []

    import anthropic

    schema = {
        "type": "object",
        "properties": {
            "cues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "word_index": {"type": "integer"},
                        "sfx_file": {"type": "string"},
                        "trigger_word": {"type": "string",
                                          "description": "la palabra EXACTA del guion (en word_index o adyacente) que describe el evento sonoro"},
                    },
                    "required": ["word_index", "sfx_file", "trigger_word"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["cues"],
        "additionalProperties": False,
    }
    word_list = [w[2] for w in words]
    manifest = _load_sfx_manifest()
    catalog = {f.name: manifest.get(f.name, {"suena_como": f.stem}) for f in sfx_files}
    tone_line = f"\nTono/musica de este video: {tone!r}\n" if tone else ""
    script_line = f"\nGuion completo (con puntuacion):\n{script}\n" if script else ""
    scenes_line = (f"\nQue se VE en pantalla en cada escena (en orden):\n"
                   f"{json.dumps(search_terms, ensure_ascii=False)}\n") if search_terms else ""
    prompt = (
        "Eres editor de sonido para Shorts de gaming. Tu regla es de DISENO DE "
        "SONIDO DIEGETICO: un efecto solo puede sonar si la narracion en ese punto "
        "DESCRIBE LITERALMENTE el evento que produce ese sonido (se menciona una "
        "espada -> puede sonar una espada; se menciona un golpe/caida -> impacto; "
        "trueno/tormenta -> trueno). NUNCA coloques un efecto 'para dar energia' o "
        "'de ambientacion' si la palabra narrada en ese momento no describe el "
        "evento: eso se percibe como puesto por ponerlo, y es exactamente lo que "
        "hay que evitar.\n\n"
        "Para cada cue devuelve trigger_word: la palabra EXACTA del guion (la de "
        "word_index o una inmediatamente adyacente) que describe el evento sonoro. "
        "Si no puedes citar una palabra concreta que lo justifique, NO pongas el cue.\n\n"
        "Ademas: (1) el efecto debe cuadrar con el tono del momento (nada comico/"
        "cartoon en un momento triste o dramatico, nada dramatico en un gag); "
        "(2) el efecto tambien debe ser coherente con lo que se VE en la escena "
        "activa en ese momento; (3) maximo 4 cues y minimo 4 palabras de distancia "
        "entre cues; (4) devolver 0 cues es una respuesta correcta si el guion no "
        "narra eventos sonoros.\n"
        f"{tone_line}{script_line}{scenes_line}\n"
        f"Palabras con su indice 0-based (usa el indice de la palabra exacta donde "
        f"debe sonar): {json.dumps(word_list, ensure_ascii=False)}\n\n"
        f"Catalogo de efectos (nombre EXACTO de archivo -> que suena y cuando usarlo): "
        f"{json.dumps(catalog, ensure_ascii=False)}"
    )
    # max_tokens generoso: con thinking adaptive a veces el presupuesto se
    # consume pensando y no deja espacio para el bloque de texto final
    # (StopIteration silenciosa al buscarlo) -- visto en produccion.
    client = anthropic.Anthropic()
    data = None
    for attempt in range(2):
        try:
            response = client.messages.create(
                model=MODEL, max_tokens=4000, thinking={"type": "adaptive"},
                output_config={"format": {"type": "json_schema", "schema": schema}},
                messages=[{"role": "user", "content": prompt}],
            )
            text = next(b.text for b in response.content if b.type == "text")
            data = json.loads(text)
            break
        except Exception as e:
            log("sfx", f"Seleccion de SFX fallo intento {attempt + 1} ({type(e).__name__}): {e}")
    if data is None:
        return []

    def _norm(w: str) -> str:
        return re.sub(r"[^\wáéíóúñü]", "", w.lower())

    name_to_path = {f.name: f for f in sfx_files}
    cues = []
    for cue in data.get("cues", []):
        idx = cue.get("word_index", -1)
        fname = cue.get("sfx_file", "")
        trigger = cue.get("trigger_word", "")
        if not (0 <= idx < len(words) and fname in name_to_path):
            continue
        # el trigger_word debe ser una palabra REAL del guion en word_index o
        # inmediatamente adyacente -- descarta cues decorativos inventados
        window = [_norm(words[j][2]) for j in range(max(0, idx - 1), min(len(words), idx + 2))]
        if _norm(trigger) not in window:
            log("sfx", f"cue descartado: '{trigger}' no esta junto a la palabra {idx} "
                        f"('{words[idx][2]}')")
            continue
        cues.append((words[idx][0], name_to_path[fname]))
        log("sfx", f"  {words[idx][0]:6.2f}s  {fname}  <- '{trigger}'")
    cues.sort(key=lambda c: c[0])
    cues = cues[:4]  # tope duro (la API no soporta maxItems en el schema)
    log("sfx", f"{len(cues)} efectos de sonido colocados (regla: solo eventos narrados)")
    return cues


# ------------------------------------------------------------- 5. ASSEMBLY

def assemble(clips: list[Path], audio: Path, ass_path: Path, out_dir: Path,
             music_mood: str | None = None,
             sfx_cues: list[tuple[float, Path]] | None = None,
             durations: list[float] | None = None,
             watermark: str | None = "ImPixxel",
             cta_text: str | None = None,
             cta_position: str | None = None) -> Path:
    """durations: duracion por escena (de _scene_boundaries, cortes en fin de
    frase). Sin ella, reparto uniforme (comportamiento anterior)."""
    audio_dur = ffprobe_duration(audio)
    if durations is None:
        durations = [audio_dur / len(clips)] * len(clips)
    norm_paths = []

    for i, clip in enumerate(clips):
        norm = out_dir / "clips" / f"seg_{i}.mp4"
        seg = durations[i]
        clip_dur = ffprobe_duration(clip)
        loop_args = ["-stream_loop", "-1"] if clip_dur < seg else []
        run([
            "ffmpeg", "-y", *loop_args, "-i", str(clip), "-t", f"{seg:.3f}",
            "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                   f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", str(norm),
        ])
        norm_paths.append(norm)

    concat_list = out_dir / "clips" / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.name}'\n" for p in norm_paths), encoding="utf-8"
    )
    concat_path = out_dir / "clips" / "concat.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list.name,
         "-c", "copy", concat_path.name], cwd=out_dir / "clips")

    # cwd = out_dir con rutas relativas: evita escapar rutas de Windows en el filtro ass
    final = out_dir / "video.mp4"
    sfx_cues = sfx_cues or []

    music = None
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key and music_mood:
        lyria_path = out_dir / "music_lyria.mp3"
        log("music", f"Generando musica con Lyria 3: {music_mood!r}...")
        if _lyria_generate_music(music_mood, lyria_path, gemini_key):
            music = lyria_path
        else:
            log("music", "Lyria fallo, uso biblioteca local de musica")
    if not music:
        music = _pick_music()

    watermark_filter = (
        f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='{watermark}'"
        ":fontcolor=white@0.55:fontsize=34:borderw=2:bordercolor=black@0.4"
        ":x=w-text_w-28:y=110,"
    ) if watermark else ""

    cta_filter = ""
    if cta_text and cta_position:
        # CTA como texto en pantalla, NUNCA narrado -- test de posicion
        # (inicio/medio/final) sin arriesgar el "Cliff" de retencion del CTA
        # hablado (ver RETENTION_CHECKLIST.md). 3s de aparicion con fade.
        cta_dur = 3.0
        if cta_position == "start":
            cta_start = 0.5
        elif cta_position == "end":
            cta_start = max(audio_dur - cta_dur - 0.5, 0)
        else:  # "middle"
            cta_start = max(audio_dur / 2 - cta_dur / 2, 0)
        cta_end = cta_start + cta_dur
        safe_text = cta_text.replace("'", "’").replace(":", "\\:")
        cta_filter = (
            f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='{safe_text}'"
            ":fontcolor=white:fontsize=44:borderw=3:bordercolor=black@0.6"
            ":x=(w-text_w)/2:y=h-320"
            f":alpha='if(lt(t,{cta_start}),0,if(lt(t,{cta_start+0.3}),(t-{cta_start})/0.3,"
            f"if(lt(t,{cta_end-0.3}),1,if(lt(t,{cta_end}),({cta_end}-t)/0.3,0))))'"
            f":enable='between(t,{cta_start},{cta_end})',"
        )

    video_filter = f"[0:v]ass={ass_path.name},{watermark_filter}{cta_filter}null[v];"

    # inputs: 0=video concat, 1=voz, [2=musica], luego un input por cada sfx
    inputs = ["-i", str(Path("clips") / "concat.mp4"), "-i", audio.name]
    next_idx = 2
    music_idx = None
    if music:
        inputs += ["-i", str(music)]
        music_idx = next_idx
        next_idx += 1
    sfx_idxs = []
    for _, sfx_path in sfx_cues:
        inputs += ["-i", str(sfx_path)]
        sfx_idxs.append(next_idx)
        next_idx += 1

    audio_labels = []
    audio_filters = ""
    if music:
        fade_dur = min(2.5, audio_dur / 4)
        fade_out_start = max(audio_dur - fade_dur, 0)
        audio_filters += (
            "[1:a]asplit=2[voice_mix][voice_trigger];"
            f"[{music_idx}:a]aloop=loop=-1:size=2e9,volume=0.06,"
            f"afade=t=in:st=0:d={fade_dur:.2f},"
            f"afade=t=out:st={fade_out_start:.2f}:d={fade_dur:.2f}[bg];"
            "[bg][voice_trigger]sidechaincompress="
            "threshold=0.03:ratio=8:attack=20:release=400[bg_ducked];"
        )
        audio_labels += ["[voice_mix]", "[bg_ducked]"]
    else:
        audio_filters += "[1:a]anull[voice_mix];"
        audio_labels += ["[voice_mix]"]

    for k, ((ts, _), idx) in enumerate(zip(sfx_cues, sfx_idxs)):
        ms = int(ts * 1000)
        audio_filters += f"[{idx}:a]adelay={ms}|{ms},volume=0.2[sfx{k}];"
        audio_labels.append(f"[sfx{k}]")

    audio_filters += (
        f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:"
        "duration=first:dropout_transition=0:normalize=0,"
        "loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
    )

    label = "musica + " if music else ""
    label += f"{len(sfx_cues)} sfx" if sfx_cues else "sin sfx"
    log("assembly", f"Render final (subtitulos + voz + {label})...")
    run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", video_filter + audio_filters,
        "-map", "[v]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-shortest", final.name,
    ], cwd=out_dir)
    return final


MUSIC_DIR = ROOT / "assets" / "music"


def _pick_music() -> Path | None:
    """Elige una pista al azar de assets/music/ (mp3/m4a/wav/ogg). None si esta vacia."""
    if not MUSIC_DIR.exists():
        return None
    tracks = [p for p in MUSIC_DIR.iterdir()
              if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg", ".flac")]
    if not tracks:
        return None
    import random
    return random.choice(tracks)


# ------------------------------------------------------------------- MAIN

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "short"


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un YouTube Short desde un tema")
    parser.add_argument("topic", nargs="?", help="Tema del video (en ingles o espanol)")
    parser.add_argument("--script-file", help="JSON con script/search_terms/title/description (omite Claude)")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--rate", default=DEFAULT_RATE)
    parser.add_argument("--clips", type=int, default=DEFAULT_CLIPS)
    parser.add_argument("--no-pexels", action="store_true", help="Usa gradientes en vez de Pexels")
    parser.add_argument("--no-sfx", action="store_true",
                        help="No coloca efectos de sonido automaticos (requiere ANTHROPIC_API_KEY "
                             "y archivos en assets/sfx/)")
    parser.add_argument("--nanobanana", action="store_true",
                        help="Usa imagenes estaticas generadas con Nano Banana (Gemini) en vez de "
                             "Pexels/gradiente. Requiere GEMINI_API_KEY.")
    parser.add_argument("--veo-hero", type=int, default=None, metavar="N",
                        help="Anima con Veo (image-to-video, ~$1) solo la escena N (0-indexed) "
                             "de --nanobanana; el resto queda estatico. Modo hibrido costo/impacto.")
    parser.add_argument("--watermark", default="ImPixxel",
                        help="Texto de marca de agua (esquina superior derecha). "
                             "Usa '' (vacio) para omitirla, ej. pruebas sueltas sin marca.")
    parser.add_argument("--cta-text", default=None,
                        help="Texto de CTA en pantalla (nunca narrado, evita el 'Cliff' de "
                             "retencion del CTA hablado). Requiere --cta-position.")
    parser.add_argument("--cta-position", choices=["start", "middle", "end"], default=None,
                        help="Donde aparece --cta-text: 'start' (~0.5s), 'middle' (mitad del "
                             "video), o 'end' (ultimos ~3.5s). Test de posicion del CTA.")
    parser.add_argument("--punch-index", type=int, default=None, metavar="N",
                        help="Escena (0-indexed) que recibe el zoom 'golpe' para acentuar el "
                             "remate/giro comico. Por defecto la penultima escena.")
    parser.add_argument("--ideas", action="store_true",
                        help="Genera 5 ideas de tema nuevas (usando topics.txt como referencia) y termina")
    parser.add_argument("--auto", action="store_true",
                        help="Modo automatico: toma el siguiente tema no usado de topics.txt "
                             "(genera mas si se agotan) y corre el pipeline completo. "
                             "Pensado para tareas programadas sin supervision.")
    args = parser.parse_args()

    if args.ideas:
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("ERROR: falta ANTHROPIC_API_KEY. Copia .env.example a .env")
            return 1
        topics_path = ROOT / "topics.txt"
        existing = [
            line.strip() for line in topics_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ] if topics_path.exists() else []
        ideas = generate_ideas(existing)
        print("\nIdeas generadas:")
        for i, idea in enumerate(ideas, 1):
            print(f"  {i}. {idea}")
        print(f"\nAgregalas a topics.txt o corre: py pipeline.py \"{ideas[0]}\"")
        return 0

    if args.script_file:
        data = json.loads(Path(args.script_file).read_text(encoding="utf-8"))
        topic = args.topic or data.get("title", "short")
    elif args.auto:
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("ERROR: falta ANTHROPIC_API_KEY. Copia .env.example a .env")
            return 1
        topic = pick_next_topic()
        log("auto", f"Tema elegido: {topic}")
        try:
            data = with_retries(generate_script, topic)
        except Exception:
            _log_auto_failure(topic)
            return 1
    elif args.topic:
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("ERROR: falta ANTHROPIC_API_KEY (o usa --script-file). Copia .env.example a .env")
            return 1
        topic = args.topic
        data = generate_script(topic)
    else:
        parser.print_help()
        return 1

    if args.nanobanana and not os.getenv("GEMINI_API_KEY"):
        print("ERROR: falta GEMINI_API_KEY. Consiguela gratis en https://aistudio.google.com/apikey")
        return 1

    out_dir = OUTPUT_ROOT / f"{date.today().isoformat()}-{slugify(topic)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    media_source = "nanobanana" if args.nanobanana else ("gradient" if args.no_pexels else "pexels")

    try:
        _check_pacing(data["script"])
        audio_path, words = with_retries(generate_audio, data["script"], args.voice, args.rate, out_dir)
        ass_path = generate_subtitles(words, out_dir)

        audio_dur = ffprobe_duration(audio_path)
        durations = _scene_boundaries(words, args.clips, audio_dur)
        clips = acquire_media(data["search_terms"], args.clips, durations,
                              out_dir, media_source=media_source, veo_hero_index=args.veo_hero,
                              punch_index=args.punch_index, style=data.get("style"))

        sfx_cues = [] if args.no_sfx else pick_sfx_cues(words, tone=data.get("music_mood"),
                                                         script=data.get("script"),
                                                         search_terms=data.get("search_terms"))
        final = assemble(clips, audio_path, ass_path, out_dir,
                          music_mood=data.get("music_mood"), sfx_cues=sfx_cues,
                          durations=durations, watermark=args.watermark or None,
                          cta_text=args.cta_text, cta_position=args.cta_position)
    except Exception:
        if args.auto:
            _log_auto_failure(topic)
        raise

    (out_dir / "title.txt").write_text(data["title"], encoding="utf-8")
    (out_dir / "description.txt").write_text(data["description"], encoding="utf-8")

    if args.auto:
        _mark_topic_used(topic)

    log("done", f"Video listo: {final}")
    log("done", f"Titulo: {data['title']}")
    usage = _usage_summary_today()
    if usage:
        log("gemini", usage)
    return 0


def _log_auto_failure(topic: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"fail_{date.today().isoformat()}.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().isoformat()}] Tema: {topic}\n")
        f.write(traceback.format_exc())
    log("auto", f"FALLO registrado en {log_path} (el tema NO se marca como usado; se reintentara)")


if __name__ == "__main__":
    sys.exit(main())
