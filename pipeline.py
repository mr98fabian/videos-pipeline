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
import shutil
import subprocess
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path

import requests

import sticker_library

# Windows con tarea programada suele heredar stdout en cp1252; un titulo con
# emoji o caracter fuera de ese charset lanza UnicodeEncodeError y tumba la
# corrida DESPUES de haber gastado creditos de TTS/imagenes/musica (visto
# repetidas veces esta sesion). Forzar UTF-8 lo elimina de raiz.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
# Estilo visual FIJO del canal (27 jul 2026). Bug real: SCRIPT_SCHEMA nunca
# tuvo un campo "style", asi que data.get("style") dependia de que Claude lo
# inventara por su cuenta -- salio vacio en un video real y las imagenes
# perdieron el sepia Nickelodeon. Segun CLAUDE.md esto NUNCA debe variar por
# video, asi que ahora es una constante de codigo, no algo que el modelo decide.
HIDDENFACTS_STYLE = (
    "1990s Nickelodeon rubber-hose cartoon style, exaggerated comic-book "
    "expressions with big unsettling eyes, thick wobbly hand-drawn black "
    "outlines, snappy low-frame animation feel. Color palette: sepia, dusty "
    "burnt yellow, aged parchment, dark brown shadows instead of pure black. "
    "Heavy vintage film grain and scratched-film texture overlaid, retro "
    "documentary aesthetic, slightly distorted, high contrast, hand-drawn "
    "sketch look. No bright saturated colors. Only human characters, never "
    "humanoid animals."
)
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
            "description": "Voiceover text, word-for-word, 110-130 words, no markdown. "
                            "*** HARD RULE: NOTHING EXPLANATORY AFTER THE PAYOFF *** The payoff is "
                            "the sentence that delivers what the hook promised (the twist, the "
                            "result, the reveal). The moment it lands, the story is OVER for the "
                            "viewer -- any further background, dates, aftermath or 'and that is why "
                            "...' sentence is dead weight and they leave right there, taking the "
                            "last seconds of retention with them. After the payoff you may write "
                            "ONLY: (a) at most one short dry acid remark, if it hits HARDER than the "
                            "payoff itself, (b) the share trigger, (c) the closing question. Never a "
                            "new fact, never a recap, never extra context. If a detail matters, it "
                            "belongs BEFORE the payoff, not after it. "
                            "*** HARD RULE: THE SCRIPT MUST LOOP *** The last sentence has to close using the SAME KEY WORDS as the hook, so that when the Short restarts the viewer does not perceive a cut and watches it again. Measured on this channel (26 jul 2026): the only video with a real loop holds a 3.76 -> 2.89 audience ratio (watched ~3 times through, -23% across the whole video), while videos closing with a summary sentence ('and so...', 'that is how...') fall to 0.95 and 0.08. A summary tells the viewer it is over; a loop hides the seam. Example that works: hook 'almost nobody today remembers why' -> close 'then quietly vanished from the pages of history'. NEVER close with a recap or a moral. "
                            "*** PLANTILLA UNICA DEL CANAL: replicar Black Tom *** Es el unico video con re-watch real (3,76 -> 2,89) y de el se copian TRES cosas, no solo el loop: (1) el ancla es un ICONO FAMOSO que el espectador reconoce al instante y puede ver hoy (la Estatua de la Libertad), no un personaje historico que hay que presentar; (2) la consecuencia SIGUE VISIBLE HOY -- la antorcha lleva cerrada desde entonces -- asi que el espectador puede comprobarlo el mismo ('ever since', 'to this day', 'still closed'); (3) el loop lexico y visual. Si el tema no tiene un icono reconocible con una huella visible hoy, el guion no alcanza este patron: buscar otro angulo del mismo hecho hasta encontrarlo.",
        },
        "search_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "8-12 concrete, visual queries (objects/scenes, not concepts). "
                            "More, shorter scenes beat fewer long ones -- retention research shows "
                            "high-performing Shorts cut every 2-4 seconds, not every 8-9. "
                            "CUT-OUT FRIENDLY (the engine isolates the subject as a die-cut sticker): "
                            "each MIDDLE term should show ONE clear subject as a FULL or HALF figure "
                            "with a clean silhouette, doing one readable action, on an uncluttered "
                            "background -- e.g. 'a soldier crouching in a trench, full figure' NOT "
                            "'a soldier's face in extreme close-up'. Extreme face close-ups isolate "
                            "as ugly floating heads. The ONLY exception is the FIRST (and its echo, "
                            "the last) term: a single intense face close-up there is encouraged for "
                            "the thumbnail scroll-stop -- the engine renders those as a clean taped "
                            "photo, not a cut-out. "
                            "*** THE LAST TERM MUST CHAIN INTO THE FIRST *** Not merely resemble it: the closing image has to be a frame the first image could cut back to without a visible seam (same place, same light, same framing, later moment). That visual loop is half of the re-watch effect measured on this channel. Example: opens on a night explosion in the harbor, closes on the same harbor still smoldering. "
                            "MULTI-SUBJECT: in 3-4 of the middle terms, ask for TWO or THREE figures "
                            "(or a figure plus a key object) STANDING CLEARLY APART, not touching and "
                            "not overlapping -- e.g. 'two officers standing apart facing each other "
                            "across an empty room, full figures'. The engine cuts each one out "
                            "separately and makes them ACT on each other (one shoves, the other "
                            "topples), which only works if they do not overlap in the image.",
        },
        "title": {"type": "string", "description": "YouTube Shorts title, <90 chars, curiosity-driven"},
        "description": {"type": "string", "description": "YouTube description with 3-5 hashtags at the end"},
        "music_mood": {
            "type": "string",
            "description": "Short text prompt (English) describing instrumental background music matching "
                            "this script's tone, for an AI music generator. E.g. 'upbeat quirky ukulele pop, "
                            "playful and light' or 'tense minimal synth, building suspense'. No vocals.",
        },
        "hook_card": {
            "type": "string",
            "description": "A ~6-10 word on-screen premise card shown for the first 2.2s (high-contrast "
                            "text over the video, separate from narration/subtitles). States the video's "
                            "premise as a curiosity gap -- withholds the resolution the script itself "
                            "reveals. E.g. 'A king survived a gun built to kill him.' Never restates the "
                            "hook sentence word-for-word; it should read like a caption someone would pause "
                            "on, not a subtitle.",
        },
    },
    "required": ["script", "search_terms", "title", "description", "music_mood", "hook_card"],
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

Tone — THE VOICE IS A CYNICAL ARCHIVIST: a jaded investigator who has read too many
files and narrates history with dry contempt, like a friend telling you the most insane
true story they found on Wikipedia at 4 a.m. Deadpan, acidic, never impressed. This voice
is the channel's brand; funny/absurd gets SHARED, which is what grows the channel:
- ACIDIC SATIRE THAT PUNCHES UP. Aim the acid at POWER — dictators' egos, government
  cover-ups, corporate greed, propaganda, pompous officialdom. Black humor at the expense
  of the powerful and the absurd is fair game and it is what gets shared. NEVER punch down:
  victims of the events are always protected, never the joke.
- The humor comes from the ABSURDITY of the TRUE fact, delivered deadpan — never jokes,
  puns, or breaking the documentary voice. A short, dry punch-line tag at the end of a
  sentence is the tool ("...in exchange for soda.", "Marketing."). The narration is TTS
  and flat, so the wit must live in the WORDING (irony, understatement, juxtaposition).
- When a pompous official euphemism appears AND it fits naturally (don't force it), puncture
  it with the blunt translation ("'strategic redeployment' — they ran."). Occasional, not
  every video.
- SCALE IT INVERSELY TO GRAVITY. Light topics (odd deals, naming quirks, con artists,
  bureaucratic absurdity, pointless traditions) → full acid. Grave topics (genocide,
  executions, massacres, war dead) → NO jokes; the acid, if any, points ONLY at the
  perpetrator, never the victims, and mostly you pull back to bitter irony and restraint.
  The `music_mood` you pick signals which end you are on.

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
7. search_terms MUST have exactly one entry per sentence of the script, in order, same
   count as the number of sentences (count periods/!/?). This is a hard rule: the video
   assembly cuts to a new image at each sentence boundary, so a mismatched count forces a
   cut mid-sentence, which reads as the image and the voice telling two different things
   at once. If you want a bookend/loop visual (last image echoes the first), repeat the
   first search_term as an EXTRA sentence's worth at the end and add one more short closing
   sentence to the script to match it -- never add an extra search_term without an extra
   sentence to anchor it.
8. hook_card: write it as a separate curiosity-gap caption, not a copy of the first spoken
   sentence. It should promise the shape of the story without giving the twist away, so a
   viewer who only reads the card (sound off, 2 seconds) still feels compelled to keep
   watching.

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


def run(cmd: list[str], cwd: Path | None = None, timeout: float = 600.0) -> None:
    """timeout=600s por defecto: un ffmpeg colgado (input corrupto, stream_loop
    infinito) no debe bloquear una corrida desatendida (tarea programada) para
    siempre -- antes no habia limite y el proceso podia quedar colgado indefinidamente."""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Comando colgado >{timeout:.0f}s ({cmd[0]}), abortado: {' '.join(cmd[:4])}...") from e
    if result.returncode != 0:
        raise RuntimeError(f"Comando fallo ({cmd[0]}):\n{result.stderr[-2000:]}")


def ffprobe_duration(path: Path, timeout: float = 30.0) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True, timeout=timeout,
    )
    return float(out.stdout.strip())


def _atomic_write_json(path: Path, data) -> None:
    """Escribe a un .tmp y luego renombra (os.replace es atomico en el mismo
    filesystem) -- evita que dos procesos escribiendo el mismo manifest.json
    (ej. tarea programada solapada con una corrida manual) se pisen a mitad
    de escritura y corrompan used_topics.json / manifest de personajes /
    gemini_usage.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path, default):
    """Carga JSON con guarda contra archivo corrupto/inexistente -- unifica
    las ~4 variantes de 'leer dict o default' que habia sueltas por el archivo."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


_DRAWTEXT_SPECIAL = str.maketrans({
    "\\": "\\\\", "'": "’", ":": "\\:", ",": "\\,", "%": "\\%",
})


def _drawtext_escape(text: str) -> str:
    """Escapa texto para usarlo dentro de un filtro drawtext de ffmpeg.
    Sin esto, una coma parte el filtergraph completo (cada ',' separa
    filtros en -filter_complex) y '%{...}' dispara expansion de expresiones
    de drawtext (vector de inyeccion real) -- visto al agregar el CTA de
    texto en pantalla, que puede traer titulos/frases con puntuacion normal."""
    return text.translate(_DRAWTEXT_SPECIAL)


def _wrap_caption(text: str, width_chars: int = 26) -> str:
    """Envuelve el parrafo de caption estatico en lineas cortas para que quepa
    en el ancho del frame vertical -- drawtext no auto-envuelve texto."""
    import textwrap
    return "\n".join(textwrap.wrap(text, width=width_chars))


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
    return set(_load_json(USED_TOPICS_FILE, []))


def _mark_topic_used(topic: str) -> None:
    used = _load_used_topics()
    used.add(topic)
    _atomic_write_json(USED_TOPICS_FILE, sorted(used))


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

def _claude_json_call(max_tokens: int, schema: dict, prompt: str) -> dict:
    """Helper compartido para llamadas a Claude con salida json_schema --
    unifica el patron repetido 3 veces (generate_script, generate_ideas,
    pick_sfx_cues) y corrige un bug real: si la respuesta solo trae un bloque
    'thinking' (presupuesto de pensamiento agotado), next(...) sin default
    lanza StopIteration cruda en vez de un error legible."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise RuntimeError("Claude no devolvio bloque de texto (solo thinking?) -- "
                            "revisar max_tokens/presupuesto de pensamiento")
    return json.loads(text)


def generate_script(topic: str) -> dict:
    log("script", f"Generando guion con {MODEL}...")
    # 2000 se quedaba corto (27 jul 2026): el prompt crecio mucho hoy (loop,
    # plantilla Black Tom, reglas de hook) y el presupuesto de thinking
    # adaptativo se comia todo el budget antes de escribir el bloque de texto
    data = with_retries(_claude_json_call, 4000, SCRIPT_SCHEMA, SCRIPT_PROMPT.format(topic=topic))
    log("script", f"{len(data['script'].split())} palabras, {len(data['search_terms'])} search terms")
    return data


def generate_ideas(existing_topics: list[str]) -> list[str]:
    log("ideas", f"Generando 5 ideas con {MODEL}...")
    prompt = IDEAS_PROMPT.format(existing_topics=", ".join(existing_topics) or "none")
    data = with_retries(_claude_json_call, 1000, IDEAS_SCHEMA, prompt)
    return data["ideas"]


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


def _check_pacing(script: str, target_seconds: float = 60.0) -> None:
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


def _check_script_lint(script: str, title: str, voice: str,
                       search_terms: list[str] | None = None) -> None:
    """Avisos rapidos y baratos (nunca bloquean) sobre reglas ya validadas
    con datos reales esta temporada, para no depender de acordarse a mano:
    (1) palabras con ñ en guiones de voz en espanol -- el TTS las pronuncia
    mal (ver memoria voz-espanol-impixxel); (2) titulo sin nombre propio
    reconocible -- proxy barato de la regla 'antagonista/institucion famosa
    en el titulo' (ver memoria titulo-antagonista-famoso), que correlaciono
    con 1000+ vistas en HiddenFacts; (3) primer search_term sin cara/close-up
    -- el area fusiforme facial reconoce rostros en 50-200ms, es el freno de
    scroll mas rapido; abrir con una escena amplia desperdicia esa palanca (ver
    RETENTION_CHECKLIST.md, gancho visual)."""
    if voice.startswith("es-") and "ñ" in script.lower():
        log("lint", "AVISO: el guion tiene 'ñ' con voz en espanol -- el TTS suele "
                     "pronunciarla mal, considera un sinonimo (ver memoria "
                     "voz-espanol-impixxel).")
    # heuristica barata: alguna palabra que empiece en mayuscula despues de la
    # primera palabra del titulo (nombre propio/institucion), sin serlo TODAS
    # las palabras (titulo en Title Case no cuenta como señal)
    words = title.split()
    if len(words) > 1:
        capitalized = sum(1 for w in words[1:] if w[:1].isupper())
        if capitalized == 0:
            log("lint", "AVISO: el titulo no parece nombrar a nadie/nada propio "
                        "(antagonista, institucion, figura famosa) -- esa señal "
                        "correlaciono con 1000+ vistas en HiddenFacts, considera "
                        "agregarla si el hecho real lo permite (ver memoria "
                        "titulo-antagonista-famoso).")
    if search_terms:
        first = search_terms[0].lower()
        if not any(w in first for w in ("face", "close-up", "close up", "eyes",
                                        "portrait", "staring", "expression")):
            log("lint", "AVISO: el primer search_term no parece un primer plano de "
                        "un rostro -- una cara con contacto visual frena el scroll "
                        "en 50-200ms (gancho visual, ver RETENTION_CHECKLIST.md). "
                        "Considera abrir con un close-up de cara intensa.")
        sentence_count = len([s for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()])
        if len(search_terms) != sentence_count:
            log("lint", f"AVISO: {len(search_terms)} search_terms mas {sentence_count} "
                        "oraciones en el guion -- el corte de escena solo puede caer en "
                        "fin de oracion, un conteo distinto fuerza al menos un corte a "
                        "mitad de frase (imagen y voz desincronizadas, ver investigacion "
                        "de sync narracion/imagen). Igualalos o agrega una oracion de "
                        "cierre extra si el ultimo search_term es un eco/loop visual.")


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
# La activa ademas hace un "pop" de escala: sube a 113% en 90ms y se sostiene
# mientras se pronuncia. El movimiento sobre la palabra hablada fija mas la
# mirada que solo el cambio de color -- clave con ~50% viendo en mute y para
# no-nativos (tecnica estandar de captions estilo TikTok). El reset devuelve las
# demas palabras a blanco y escala 100 para que el efecto no se arrastre.
_CAP_ACTIVE = r"{\c&H00FFFF&\fscx100\fscy100\t(0,90,\fscx113\fscy113)}"
_CAP_WHITE = r"{\c&HFFFFFF&\fscx100\fscy100}"


def generate_subtitles(words: list[tuple[float, float, str]], out_dir: Path,
                       lead_ms: int = 0, offset_ms: int = 0) -> Path:
    # Karaoke palabra-por-palabra: agrupa en bloques cortos (max 3 palabras / 18
    # chars, texto-como-imagen: lectura instantanea sin "leer" gramaticalmente)
    # para conservar contexto de 2 lineas, pero emite UN evento por palabra con
    # la activa resaltada en amarillo -- fija la mirada (clave con ~50% viendo
    # en mute) y sube la retencion en Shorts.
    if lead_ms:
        # adelanta el texto respecto al audio (test: el ojo "lee" el gancho antes
        # de que se oiga, aunque la mayoria vea en mute) -- no afecta el audio.
        lead = lead_ms / 1000
        words = [(max(ws - lead, 0.0), max(we - lead, 0.0), w) for ws, we, w in words]
    if offset_ms:
        # atrasa TODOS los subtitulos por igual -- usado por el modo card 'read':
        # se antepone un segmento de ~2.2s (frame congelado + premise card) antes
        # de que arranque la narracion, asi que los timestamps de las palabras
        # (que salen del audio de voz) hay que correrlos ese mismo tiempo para
        # que sigan sincronizados con la voz ya desplazada.
        off = offset_ms / 1000
        words = [(ws + off, we + off, w) for ws, we, w in words]

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
    return _load_json(CHARACTERS_MANIFEST, {})


def _save_characters_manifest(data: dict) -> None:
    _atomic_write_json(CHARACTERS_MANIFEST, data)


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
    data = _load_json(USAGE_LOG_PATH, {})
    day = data.setdefault(today, {"images_ok": 0, "images_failed": 0,
                                   "songs_ok": 0, "songs_failed": 0})
    key = f"{'images' if kind == 'image' else 'songs'}_{'ok' if success else 'failed'}"
    day[key] += 1
    _atomic_write_json(USAGE_LOG_PATH, data)


def _usage_summary_today() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    data = _load_json(USAGE_LOG_PATH, {}).get(today)
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


_ACTIVE_FLOW_SESSION = None  # seteado por acquire_media: un proyecto de Flow reusado
                             # para todas las escenas de un video (evita reabrir
                             # Chrome/Flow por cada imagen, ver flow_automation.py)


def _flow_or_nanobanana_generate_image(prompt: str, path: Path, api_key: str,
                                        reference_image: Path | None = None,
                                        reference_images: list[Path] | None = None,
                                        style_directive: str | None = None,
                                        attempts: int = 2) -> bool:
    """media_source='flow': genera gratis en Google Flow (nano banana 2) via
    Playwright (flow_automation.py) en vez de pagar la API de Gemini. Cae a
    Nano Banana API automaticamente si Flow falla (selector roto, timeout,
    cuota, sin login) o si la escena necesita reference_image/reference_images/
    style_directive -- Flow en este flujo no soporta consistencia de personaje,
    solo texto a imagen."""
    needs_reference = bool(reference_image or reference_images or style_directive)
    if not needs_reference:
        full_prompt = prompt + NANOBANANA_STYLE_SUFFIX
        if _ACTIVE_FLOW_SESSION is not None:
            ok = _ACTIVE_FLOW_SESSION.generate(full_prompt, path)
        else:
            from flow_automation import flow_generate_image
            aspect = "9:16" if HEIGHT > WIDTH else "16:9"
            ok = flow_generate_image(full_prompt, path, aspect_ratio=aspect)
        if ok:
            log("media", f"Flow OK (gratis) '{prompt[:60]}...'")
            return True
        log("media", f"Flow fallo para '{prompt[:60]}...', cae a Nano Banana API")
    return _nanobanana_generate_image(prompt, path, api_key, reference_image=reference_image,
                                       reference_images=reference_images,
                                       style_directive=style_directive, attempts=attempts)


def _piapi_upload_temp(image_path: Path, api_key: str) -> str:
    """Sube un archivo local al endpoint efimero de PiAPI (se borra solo a las 24h)
    y devuelve una URL publica -- Seedream (via PiAPI) solo acepta image_urls, no
    base64 directo, a diferencia de Nano Banana/Gemini."""
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    r = requests.post(
        "https://upload.theapi.app/api/ephemeral_resource",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={"file_name": image_path.name, "file_data": b64},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("data", {}).get("url") or data["url"]


def _seedream_generate_image(prompt: str, path: Path, api_key: str,
                              reference_image: Path | None = None,
                              reference_images: list[Path] | None = None,
                              style_directive: str | None = None,
                              attempts: int = 2) -> bool:
    """Alternativa a Nano Banana via Seedream (ByteDance) por PiAPI -- mejor
    consistencia de personaje multi-referencia segun benchmarks (ver
    investigacion 19 jul 2026). Misma firma que _nanobanana_generate_image para
    poder intercambiarlas en acquire_media(). image_urls debe ser URL publica,
    por eso cada referencia se sube primero al endpoint efimero de PiAPI."""
    all_refs = ([reference_image] if reference_image else []) + (reference_images or [])
    all_refs = [r for r in all_refs if r]
    full_prompt = prompt + NANOBANANA_STYLE_SUFFIX
    if style_directive:
        full_prompt = (f"CRITICAL: apply this exact art style to the ENTIRE frame, "
                        f"overriding any style in the reference images: {style_directive}. "
                        f"{full_prompt}")

    for attempt in range(attempts):
        try:
            image_urls = [_piapi_upload_temp(ref, api_key) for ref in all_refs]
            payload = {
                "model": "seedream",
                "task_type": "seedream-5-lite",
                "input": {
                    "prompt": full_prompt,
                    "aspect_ratio": "9:16",
                    "output_format": "png",
                },
            }
            if image_urls:
                payload["input"]["image_urls"] = image_urls
            r = requests.post(
                "https://api.piapi.ai/api/v1/task",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                json=payload, timeout=60,
            )
            r.raise_for_status()
            task_id = r.json()["data"]["task_id"]

            for _ in range(60):  # hasta 2 min de polling (2s por intento)
                time.sleep(2)
                poll = requests.get(f"https://api.piapi.ai/api/v1/task/{task_id}",
                                     headers={"X-API-Key": api_key}, timeout=30)
                poll.raise_for_status()
                task = poll.json()["data"]
                status = task.get("status", "").lower()
                if status in ("completed", "success"):
                    output = task.get("output", {})
                    img_url = (output.get("image_urls") or output.get("images") or [None])[0]
                    if not img_url:
                        raise RuntimeError("tarea completa sin imagen de salida")
                    img_resp = requests.get(img_url, timeout=60)
                    img_resp.raise_for_status()
                    path.write_bytes(img_resp.content)
                    return True
                if status in ("failed", "error"):
                    raise RuntimeError(task.get("error", "tarea fallo sin detalle"))
            raise RuntimeError("timeout esperando la tarea de Seedream")
        except Exception as e:
            if attempt < attempts - 1:
                log("media", f"Seedream fallo (intento {attempt + 1}), reintento en 5s: {e}")
                time.sleep(5)
            else:
                log("media", f"Seedream fallo para '{prompt[:60]}...': {e}")
    return False


def _static_image_clip(image_path: Path, duration: float, path: Path, zoom_in: bool = True,
                        punch: bool = False, hook: bool = False, static: bool = False,
                        hook_strong: bool = False, move: int = 0) -> None:
    """Convierte una imagen fija en un clip con efecto Ken Burns (zoom lento, gratis).
    move: indice de escena -- rota entre 6 movimientos distintos (zoom-in/out
    centrado + 4 paneos direccionales) para que dos escenas seguidas nunca se
    sientan clonadas. Antes solo alternaba zoom-in/zoom-out, ambos centrados, y
    todas las escenas se percibian iguales (feedback visual 22 jul 2026). El
    parametro zoom_in quedo obsoleto (lo reemplaza 'move'); se mantiene por
    compatibilidad de firma pero ya no se usa en el modo normal.
    punch=True: quieto los primeros ~60% y zoom rapido "golpe" el resto -- usar
    en la escena del remate/giro comico para dar un acento visual.
    hook=True: golpe de entrada -- zoom-in rapido en el primer ~20% y luego se
    asienta, para ganar la decision de swipe del primer segundo en la escena 1
    (la palanca #1 de retencion en Shorts).
    hook_strong=True: version mas agresiva del golpe de entrada (bajo --hook-max)
    -- +0.25 de zoom comprimido en el primer ~12% de frames; mas movimiento en el
    frame 0, que es lo que el sistema reticular detecta antes que el contenido.
    static=True: sin ningun movimiento (modo caption -- la imagen ya comparte
    el frame con texto fijo, el zoom se sentia inconsistente con esa quietud)."""
    frames = max(int(round(duration * FPS)), 1)
    # x/y por defecto: ventana de recorte centrada (comportamiento clasico).
    # Los paneos la desplazan; usan zoom FIJO porque con zoom bajo (~1.0) no hay
    # "slack" para moverse sin mostrar borde negro -- a z=1.12 el rango valido de
    # x/y es [0, 0.107*iw] con centro en 0.054*iw, asi que un offset de +/-0.04*iw
    # se queda siempre dentro del recorte.
    xexpr = "iw/2-(iw/zoom/2)"
    yexpr = "ih/2-(ih/zoom/2)"
    if static:
        zexpr = "1.0"
    elif hook and hook_strong:
        rush = max(int(frames * 0.12), 1)
        zexpr = f"if(lt(on,{rush}),1.0+(0.25/{rush})*on,1.25)"
    elif hook:
        rush = max(int(frames * 0.2), 1)
        zexpr = f"if(lt(on,{rush}),1.0+(0.15/{rush})*on,1.15)"
    elif punch:
        hold = max(int(frames * 0.6), 1)
        zexpr = f"if(lt(on,{hold}),1.0,min(1.0+0.045*(on-{hold}),1.35))"
    else:
        # progreso lineal -1 -> +1 a lo largo del clip, para los paneos
        prog = f"((2*on/{frames})-1)"
        variant = move % 6
        if variant == 0:      # zoom-in centrado
            zexpr = "min(zoom+0.0015,1.18)"
        elif variant == 1:    # zoom-out centrado
            zexpr = "if(eq(on,1),1.18,max(zoom-0.0015,1.0))"
        elif variant == 2:    # paneo izquierda -> derecha (zoom fijo)
            zexpr = "1.12"
            xexpr = f"iw/2-(iw/zoom/2)+(iw*0.04)*{prog}"
        elif variant == 3:    # paneo derecha -> izquierda
            zexpr = "1.12"
            xexpr = f"iw/2-(iw/zoom/2)-(iw*0.04)*{prog}"
        elif variant == 4:    # paneo arriba -> abajo (zoom fijo)
            zexpr = "1.12"
            yexpr = f"ih/2-(ih/zoom/2)+(ih*0.04)*{prog}"
        else:                 # paneo abajo -> arriba
            zexpr = "1.12"
            yexpr = f"ih/2-(ih/zoom/2)-(ih*0.04)*{prog}"
    vf = (
        f"scale={WIDTH * 2}:{HEIGHT * 2}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='{zexpr}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}:"
        f"x='{xexpr}':y='{yexpr}',setsar=1"
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
                  punch_index: int | None = None, style: str | None = None,
                  static: bool = False, hook_strong: bool = False,
                  wan_hero_path: Path | None = None) -> list[Path]:
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
    piapi_key = os.getenv("PIAPI_API_KEY", "")
    clips: list[Path] = []

    global _ACTIVE_FLOW_SESSION
    flow_session_cm = None
    if media_source == "flow":
        # un proyecto de Flow para TODO el video, no uno por escena -- evita
        # reabrir Chrome/Flow y reconfigurar aspecto/modelo en cada imagen.
        from flow_automation import FlowSession, is_logged_in
        if is_logged_in():
            aspect = "9:16" if HEIGHT > WIDTH else "16:9"
            try:
                flow_session_cm = FlowSession(aspect_ratio=aspect)
                _ACTIVE_FLOW_SESSION = flow_session_cm.__enter__()
                log("media", "Flow: proyecto abierto para este video")
            except Exception as e:
                log("media", f"Flow: no se pudo abrir sesion ({e}), cae a Nano Banana API")
                flow_session_cm = None
                _ACTIVE_FLOW_SESSION = None
        else:
            log("media", "Flow: sin sesion guardada (python flow_automation.py --login), "
                          "cae a Nano Banana API")

    terms = (search_terms * ((n_clips // max(len(search_terms), 1)) + 1))[:n_clips]

    # Con estilo (ej. Roblox) generamos primero una hoja de personaje por cada
    # campeon mencionado en CUALQUIER escena, una sola vez, y la reusamos como
    # referencia en todas las escenas -- evita que el diseño del personaje
    # varie entre escenas y que el modelo copie el estilo pintado del splash
    # (ver memoria estilo-roblox-nanobanana).
    sheet_cache: dict[str, Path] = {}
    named_char_cache: dict[tuple[str, str], Path] = {}
    if media_source in ("nanobanana", "seedream", "flow") and (gemini_key or piapi_key) and style:
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

    try:
        clips = _acquire_clips_loop(terms, n_clips, durations, clips_dir, media_source,
                                     veo_hero_index, punch_index, style, static, hook_strong,
                                     wan_hero_path, gemini_key, piapi_key, pexels_key,
                                     sheet_cache, named_char_cache)
    finally:
        if flow_session_cm is not None:
            try:
                flow_session_cm.__exit__(None, None, None)
            except Exception as e:
                log("media", f"Flow: error cerrando sesion (no critico): {e}")
            _ACTIVE_FLOW_SESSION = None
    return clips


def _acquire_clips_loop(terms, n_clips, durations, clips_dir, media_source,
                         veo_hero_index, punch_index, style, static, hook_strong,
                         wan_hero_path, gemini_key, piapi_key, pexels_key,
                         sheet_cache, named_char_cache) -> list[Path]:
    clips: list[Path] = []
    for i, term in enumerate(terms):
        raw = clips_dir / f"raw_{i}.mp4"
        got = False

        if i == 0 and wan_hero_path is not None:
            # hero local (Wan 2.2 via ComfyUI, gratis) -- mismo patron que
            # veo_hero_index pero sin costo por API, solo la escena 0 para
            # maxima retencion (ver plan de gancho + ComfyUI local).
            run(["ffmpeg", "-y", "-i", str(wan_hero_path),
                 "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                        f"crop={WIDTH}:{HEIGHT},setsar=1",
                 "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                 "-pix_fmt", "yuv420p", str(raw)])
            got = True
            log("media", f"clip 1/{n_clips}: hero local Wan 2.2 OK")

        if not got and media_source in ("nanobanana", "seedream", "flow") and (gemini_key or piapi_key):
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
            gen_fn = (_seedream_generate_image if media_source == "seedream" else
                      _flow_or_nanobanana_generate_image if media_source == "flow" else
                      _nanobanana_generate_image)
            gen_key = piapi_key if media_source == "seedream" else gemini_key
            # CACHE DE ESCENAS GENERICAS: una escena sin nombres propios ni fechas
            # sirve igual en cualquier video -> se genera una vez y se reusa (cero
            # llamada de imagen). Las escenas con personaje de referencia quedan
            # fuera: dependen del sheet, no son intercambiables.
            gen_ok = False
            cache_hit = None
            if not char_ref and not champ_refs:
                try:
                    from visual_cache import scene_cache_lookup, scene_cache_store
                    cache_hit = scene_cache_lookup(gen_term, style)
                except Exception:
                    cache_hit = None
            if cache_hit:
                shutil.copyfile(cache_hit, img_path)
                gen_ok = True
                log("media", f"clip {i + 1}/{n_clips}: escena cacheada (sin coste de API)")
            else:
                gen_ok = gen_fn(gen_term, img_path, gen_key, reference_image=char_ref,
                                reference_images=champ_refs, style_directive=style)
                if gen_ok and not char_ref and not champ_refs:
                    try:
                        scene_cache_store(gen_term, style, img_path)
                    except Exception:
                        pass
            if gen_ok:
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
                    _static_image_clip(img_path, durations[i] + 1.0, raw, move=i,
                                        punch=(i == punch_index), hook=(i == 0), static=static,
                                        hook_strong=hook_strong)
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

# Capa OPCIONAL (--sticker-sfx) de sonido de ENTRADA de sticker: un swish de
# papel suave en el frame exacto en que el sticker hace pop. NO es SFX diegetico
# (no describe un evento de la narracion) -- es el "sonido del collage armandose",
# motivado por la estetica de recortes de papel que ya usan los stickers
# (tarjeta beige + borde de tinta + flecha dibujada a mano). Reglas para que no
# se sienta "puesto por ponerlo": UN solo sonido consistente (firma del canal),
# volumen bajo bajo la narracion, y se OMITE entero si el tono del video es
# sombrio. Capa separada de pick_sfx_cues (que sigue siendo 100% diegetico).
STICKER_SFX_DEFAULT = "Paper___book_ManualTurnPage_AP1.1244.mp3"  # swish de papel, 0.58s
STICKER_SFX_VOLUME = 0.16
_SOMBER_TONE_WORDS = ("sad", "tragic", "mournful", "grief", "sorrow", "solemn",
                       "melancholy", "funeral", "elegy", "lament", "somber", "sombre",
                       "requiem", "heartbreaking")


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
                   search_terms: list[str] | None = None) -> list[tuple[float, Path, str]]:
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
    # consume pensando y no deja espacio para el bloque de texto final --
    # _claude_json_call ya convierte eso en un RuntimeError legible en vez
    # de la StopIteration silenciosa que habia antes.
    try:
        data = with_retries(_claude_json_call, 4000, schema, prompt, attempts=2, delay=3.0)
    except Exception as e:
        log("sfx", f"Seleccion de SFX fallo: {type(e).__name__}: {e}")
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
        cues.append((words[idx][0], name_to_path[fname], trigger))
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
             cta_position: str | None = None,
             intro_stinger: bool = False,
             split_first_clip: bool = False,
             caption_header: str | None = None,
             caption_text: str | None = None,
             caption_keywords: list[str] | None = None,
             hook_card: str | None = None,
             hook_card_mode: str = "overlay",
             hook_punch: bool = False) -> Path:
    """durations: duracion por escena (de _scene_boundaries, cortes en fin de
    frase). Sin ella, reparto uniforme (comportamiento anterior).
    hook_card: premisa en pantalla (~2.2s, alto contraste, curiosity gap) al
    inicio. hook_card_mode: 'overlay' (se superpone mientras ya narra desde t=0)
    o 'read' (beat de lectura primero: frame congelado 2.2s con solo musica/
    stinger, la narracion arranca despues). En modo 'read' el audio de voz debe
    llegar YA desplazado card_dur (la voz se retrasa con adelay aca) y los subs
    tambien (se generan con offset_ms en main). card_dur fijo = 2.2s."""
    HOOK_CARD_DUR = 2.2
    LOOP_DUR = 0.4  # seg -- duracion del crossfade final hacia el frame de apertura
    OVERLAY_VOICE_DELAY = 1.0  # seg -- feedback 20 jul 2026: dar tiempo de leer el
    # card antes de que arranque la narracion, incluso en modo 'overlay' (video ya
    # corriendo). Se logra sosteniendo el ULTIMO frame +1s al final (no se pierde
    # nada de narracion) y retrasando la voz 1s, no los 2.2s completos del modo 'read'.
    read_mode = bool(hook_card) and hook_card_mode == "read"
    overlay_delay_mode = bool(hook_card) and hook_card_mode != "read"
    audio_dur = ffprobe_duration(audio)
    if durations is None:
        durations = [audio_dur / len(clips)] * len(clips)

    if split_first_clip and durations[0] > 1.0:
        # parte la escena 1 en dos mitades del mismo clip -- un corte extra en
        # el primer segundo simula "mas camaras"/ritmo, sin generar media nueva
        # (test: el corte en si es una senal de "esto se mueve rapido").
        half = durations[0] / 2
        clips = [clips[0], clips[0], *clips[1:]]
        durations = [half, half, *durations[1:]]

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

    loop_frame = None
    if hook_punch:
        # loop visual real (investigacion 19-20 jul 2026, canal vidIQ): el ultimo
        # frame del video debe parecerse al primero para que un rewatch/loop se
        # sienta continuo en vez de "arranca un video nuevo" -- YouTube cuenta el
        # loop como señal fuerte de engagement. Se captura el primer frame ORIGINAL
        # (antes del wipe/flash de entrada) para usarlo como destino del loop al
        # final, sin importar que efectos de entrada se apliquen despues.
        loop_frame = out_dir / "clips" / "loop_frame.png"
        run(["ffmpeg", "-y", "-i", str(norm_paths[0]), "-vframes", "1", str(loop_frame)])

    if read_mode:
        # beat de lectura primero: congelar el primer frame del clip 0 durante
        # HOOK_CARD_DUR y anteponerlo. La narracion (voz) se retrasa ese mismo
        # tiempo en el filtro de audio; los subs ya llegan con offset_ms desde
        # main. El premise card se dibuja encima de este segmento (0-2.2s).
        first_frame = out_dir / "clips" / "hookcard_frame.png"
        run(["ffmpeg", "-y", "-i", str(norm_paths[0]), "-vframes", "1",
             str(first_frame)])
        freeze = out_dir / "clips" / "seg_hookcard.mp4"
        _static_image_clip(first_frame, HOOK_CARD_DUR, freeze, static=True)
        norm_paths = [freeze, *norm_paths]

    if overlay_delay_mode:
        # sostiene el ultimo frame +1s al final para compensar el retraso de voz
        # (asi no se corta el ultimo segundo de narracion) -- ver OVERLAY_VOICE_DELAY.
        last_frame = out_dir / "clips" / "hookcard_last_frame.png"
        run(["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(norm_paths[-1]),
             "-vframes", "1", str(last_frame)])
        hold = out_dir / "clips" / "seg_holdend.mp4"
        _static_image_clip(last_frame, OVERLAY_VOICE_DELAY, hold, static=True)
        norm_paths = [*norm_paths, hold]

    if hook_punch:
        # transicion de entrada agresiva (bajo --hook-max): wipe circular muy
        # rapido (~0.3s) desde blanco hacia el primer clip, en vez del corte
        # seco de siempre. Es una anomalia de movimiento adicional en el
        # frame 0 -- el ojo la registra antes de evaluar el contenido, mismo
        # principio que el flash pero con mas "sensacion de impacto".
        entry_clip = norm_paths[0]
        punch_dur = 0.3
        wiped = out_dir / "clips" / "seg_punch_wipe.mp4"
        run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=white:s={WIDTH}x{HEIGHT}:d={punch_dur}:r={FPS}",
            "-i", str(entry_clip),
            "-filter_complex",
            f"[1:v]trim=0:{punch_dur},setpts=PTS-STARTPTS,fps={FPS}[headv];"
            f"[0:v][headv]xfade=transition=circleopen:duration={punch_dur}:offset=0[wv]",
            "-map", "[wv]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", str(wiped),
        ])
        rest = out_dir / "clips" / "seg_punch_rest.mp4"
        run([
            "ffmpeg", "-y", "-i", str(entry_clip), "-ss", f"{punch_dur:.3f}",
            # NUNCA "-c copy" aca -- el clip fuente (libx264 veryfast, GOP largo)
            # suele no tener keyframe en 0.3s, y el copy silenciosamente produce
            # un archivo casi vacio que trunca el concat entero (bug real, visto
            # 20 jul 2026: video final de 23.6s en vez de ~39s). Reencodear.
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", str(rest),
        ])
        norm_paths = [wiped, rest, *norm_paths[1:]]

    if loop_frame is not None:
        # crossfade final hacia el frame de apertura -- el ultimo medio segundo
        # del video se funde con la misma imagen/encuadre con la que arranca,
        # asi al repetirse (loop de YouTube) no se percibe un corte, se siente
        # continuo. Duracion corta para no robarle tiempo a la narracion real.
        loop_dur = LOOP_DUR
        loop_still = out_dir / "clips" / "seg_loop_still.mp4"
        _static_image_clip(loop_frame, loop_dur, loop_still, static=True)
        last_clip = norm_paths[-1]
        looped = out_dir / "clips" / "seg_loop_xfade.mp4"
        last_dur = ffprobe_duration(last_clip)
        xfade_offset = max(last_dur - loop_dur, 0)
        run([
            "ffmpeg", "-y", "-i", str(last_clip), "-i", str(loop_still),
            "-filter_complex",
            f"[0:v]fps={FPS}[v0];[1:v]fps={FPS}[v1];"
            f"[v0][v1]xfade=transition=fade:duration={loop_dur}:offset={xfade_offset:.3f}[v]",
            "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", str(looped),
        ])
        norm_paths = [*norm_paths[:-1], looped]

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

    stinger_path = None
    if intro_stinger:
        # gancho auditivo en el frame 0, independiente de trigger_word (que
        # nunca dispara nada antes de que se diga la primera palabra) -- test
        # de si un whoosh/riser generico al inicio baja el swipe inmediato.
        candidates = [p for p in SFX_DIR.iterdir()
                      if p.suffix.lower() in (".mp3", ".wav")
                      and re.search(r"whoosh|riser|swoosh", p.name, re.I)] if SFX_DIR.exists() else []
        if candidates:
            import random
            stinger_path = random.choice(candidates)

    music = None
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key and music_mood:
        lyria_path = out_dir / "music_lyria.mp3"
        log("music", f"Generando musica con Lyria 3: {music_mood!r}...")
        if _lyria_generate_music(music_mood, lyria_path, gemini_key):
            music = lyria_path
        else:
            log("music", "Lyria fallo, uso biblioteca local de musica")
    # music_mood=None explicito (no "sin music_mood en el guion", eso no pasa --
    # es requerido por el schema) significa "sin musica a proposito" (modo
    # silent_card_mode: el video se sube mudo de musica para agregar despues a
    # mano un audio trending del nicho en el editor de Shorts de Studio, ver
    # memoria musica-trending-videos-solo-lectura). No caer al fallback de
    # libreria local en ese caso.
    if not music and music_mood is not None:
        music = _pick_music()

    watermark_filter = (
        f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='{_drawtext_escape(watermark)}'"
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
        safe_text = _drawtext_escape(cta_text)
        cta_filter = (
            f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='{safe_text}'"
            ":fontcolor=white:fontsize=44:borderw=3:bordercolor=black@0.6"
            ":x=(w-text_w)/2:y=h-320"
            f":alpha='if(lt(t,{cta_start}),0,if(lt(t,{cta_start+0.3}),(t-{cta_start})/0.3,"
            f"if(lt(t,{cta_end-0.3}),1,if(lt(t,{cta_end}),({cta_end}-t)/0.3,0))))'"
            f":enable='between(t,{cta_start},{cta_end})',"
        )

    # premise card: texto de alto contraste ~2.2s al inicio (curiosity gap "solo
    # para leer"). Scrim negro semitransparente sobre el video para maximo
    # contraste + texto grande centrado. Se dibuja en AMBOS modos (overlay/read);
    # en read el frame de abajo esta congelado, en overlay ya corre el video.
    # el TEXTO del card va como eventos ASS (no drawtext): drawtext expande
    # '%{...}' incluso desde textfile, asi que un '100%' en el card rompe la
    # linea. ASS no tiene ese problema y ademas da fade/posicion mas limpios.
    # El scrim oscuro si es un filtro (drawbox), dibujado ANTES del ass para
    # que el texto quede por encima.
    # pattern interrupt: flash blanco de ~2 frames en t=0 (bajo --hook-max) --
    # el sistema reticular activador prioriza anomalias de brillo/contraste
    # sobre contenido "normal", frena el scroll antes de que el ojo evalue
    # la escena en si. Se dibuja ANTES del scrim/ass para quedar debajo del
    # texto del hook_card si coexisten.
    hook_punch_filter = ""
    if hook_punch:
        flash_end = round(2 / FPS, 3)
        hook_punch_filter = (
            f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.9:t=fill"
            f":enable='between(t,0,{flash_end})',"
        )

    hook_card_filter = ""
    if hook_card:
        card_clean = hook_card.replace("\\", "").replace("{", "(").replace("}", ")")
        card_lines = _wrap_caption(card_clean, width_chars=22).split("\n")
        c_gap = 78
        # anclado cerca del TOP (no centrado verticalmente) -- el estilo 'Cap' de
        # los subtitulos karaoke usa MarginV alto (ver Style: Cap en generate_subtitles),
        # lo que los deja cayendo en la franja media/baja del frame. Si el card se
        # centra verticalmente, cae en la MISMA franja y ambos textos se solapan
        # (bug real detectado 19 jul 2026, ver captura de pantalla del usuario).
        c_y0 = 220
        cx = WIDTH // 2
        # scrim SOLO detras del bloque de texto (no el frame completo, feedback
        # del usuario 20 jul 2026 -- el oscurecido total se sentia como "filtro
        # blanco y negro" sobre toda la imagen). Caja centrada en X, ajustada a
        # la altura real del texto con padding.
        box_pad_y = 30
        box_w = min(int(WIDTH * 0.9), 900)
        box_h = len(card_lines) * c_gap + box_pad_y * 2
        box_x = (WIDTH - box_w) // 2
        box_y = c_y0 - c_gap // 2 - box_pad_y
        hook_card_filter = (
            f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:color=black@0.75:t=fill"
            ":enable='between(t,0,2.2)',"
        )
        # revelado progresivo linea por linea (no todo junto) -- investigacion
        # 20 jul 2026: el "hook card hipnotico" tira de la vista siguiendo un
        # ritmo de lectura en vez de dejar escanear todo de una, y la animacion
        # elaborada rinde PEOR que un fade simple, asi que el efecto es solo
        # stagger de tiempo, no de movimiento. Los numeros/datos concretos se
        # resaltan en amarillo sobre texto blanco (mismo patron que caption
        # mode) -- la especificidad es lo que separa un hook fuerte de uno
        # generico segun la misma investigacion.
        line_stagger_s = 0.28
        card_events = []
        for i, line in enumerate(card_lines):
            y = c_y0 + i * c_gap
            start_s = i * line_stagger_s
            line_colored = re.sub(r"\d+", lambda m: f"{{\\c&H4AD2FF&}}{m.group(0)}{{\\c&HFFFFFF&}}", line)
            card_events.append(
                f"Dialogue: 0,{_ass_time(start_s)},0:00:02.20,Cap,,0,0,0,,"
                f"{{\\an5\\pos({cx},{y})\\fs60\\c&HFFFFFF&\\fad(250,200)}}{line_colored}"
            )
        with ass_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(card_events) + "\n")

    if caption_text:
        # modo caption estatico: la imagen ocupa solo la parte inferior del
        # frame, el titulo+parrafo quedan fijos arriba (nunca desaparecen,
        # a diferencia del karaoke) -- el narrador solo lee el titulo corto,
        # el parrafo es puro texto para leer al propio ritmo (evita el "loop
        # mecanico por no dar tiempo a leer" que se vio en el lote ultra-corto
        # de subtitulos karaoke). Se inyecta como Dialogue extra en el MISMO
        # .ass del karaoke (en vez de drawtext) porque ASS soporta color por
        # palabra via {\c&Hbbggrr&} inline -- drawtext es un solo color por
        # llamada, no alcanzaba para resaltar keywords en rojo dentro de la
        # linea.
        def _ass_clean(s: str) -> str:
            return s.replace("\\", "").replace("{", "(").replace("}", ")")

        # feedback 20 jul 2026: letras mas grandes Y que se extiendan mas a lo
        # lateral (antes quedaban en una columna angosta con mucho margen a los
        # costados). width_chars mas alto = lineas mas largas = usa mas ancho
        # del cuadro con el mismo tamano de fuente.
        header_lines = _wrap_caption(_ass_clean(caption_header or ""), width_chars=18).split("\n")

        # bug real (20 jul 2026): al envolver el parrafo, una keyword de varias
        # palabras (ej. "cryptic message") podia terminar partida entre dos
        # lineas -- el regex de resaltado corre POR LINEA, asi que la mitad
        # partida ya no matcheaba y la keyword se quedaba sin marcar en rojo.
        # Fix: unir los espacios internos de cada keyword con un word-joiner
        # invisible (U+2060) ANTES de envolver, para que textwrap la trate
        # como una sola palabra indivisible; se separa recien al pintar rojo.
        body_text = _ass_clean(caption_text)
        JOINER = "⁠"
        joined_keywords = []
        for kw in (caption_keywords or []):
            kw_clean = _ass_clean(kw)
            joined = kw_clean.replace(" ", JOINER)
            body_text = re.sub(re.escape(kw_clean), joined, body_text, flags=re.IGNORECASE)
            joined_keywords.append(joined)

        body_lines = _wrap_caption(body_text, width_chars=38).split("\n")

        RED, WHITE = r"{\c&H0000FF&}", r"{\c&HFFFFFF&}"
        for joined in joined_keywords:
            pattern = re.compile(re.escape(joined), re.IGNORECASE)
            body_lines = [
                pattern.sub(lambda m: f"{RED}{m.group(0).replace(JOINER, ' ')}{WHITE}", line)
                for line in body_lines
            ]

        img_h = int(HEIGHT * 0.62)
        img_y = HEIGHT - img_h

        # feedback 20 jul 2026: el bloque se veia chico y pegado arriba, con
        # mucho negro vacio debajo -- ahora usa fuente grande por defecto y se
        # centra verticalmente en TODA la franja negra disponible (con margen
        # chico), en vez de anclarse fijo cerca del tope. Si no entra ni asi,
        # se encoge fuente/interlineado proporcionalmente (header y body
        # juntos, misma escala) en vez de desbordar sobre la imagen.
        # tamanos medidos con Pillow (arialbd.ttf) contra el ancho real del
        # frame (20 jul 2026) en vez de a ojo: con margen lateral ~5% (972px
        # utiles de 1080), header cabe hasta fs=92 y body hasta width_chars=38
        # a fs=48 sin desbordar horizontalmente en los 3 guiones de prueba.
        margin = 54
        header_size, header_gap = 92, 118
        body_size, body_gap = 48, 62
        block_gap = 50  # separacion entre el header y el body

        total_h = len(header_lines) * header_gap + block_gap + len(body_lines) * body_gap
        available_h = img_y - margin * 2
        if total_h > available_h and available_h > 0:
            scale = available_h / total_h
            header_size = max(int(header_size * scale), 28)
            header_gap = max(int(header_gap * scale), 34)
            body_size = max(int(body_size * scale), 22)
            body_gap = max(int(body_gap * scale), 28)
            block_gap = max(int(block_gap * scale), 20)
            total_h = len(header_lines) * header_gap + block_gap + len(body_lines) * body_gap

        start_y = margin + max((available_h - total_h) / 2, 0)
        header_y0 = int(start_y + header_gap / 2)
        body_y0 = header_y0 + len(header_lines) * header_gap + block_gap

        cx = WIDTH // 2
        caption_events = []
        for i, line in enumerate(header_lines):
            y = header_y0 + i * header_gap
            caption_events.append(
                f"Dialogue: 0,0:00:00.00,0:59:59.00,Cap,,0,0,0,,"
                f"{{\\an5\\pos({cx},{y})\\fs{header_size}\\c&H4AD2FF&}}{line}"
            )
        for i, line in enumerate(body_lines):
            y = body_y0 + i * body_gap
            caption_events.append(
                f"Dialogue: 0,0:00:00.00,0:59:59.00,Cap,,0,0,0,,"
                f"{{\\an5\\pos({cx},{y})\\fs{body_size}\\c&HFFFFFF&}}{line}"
            )
        with ass_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(caption_events) + "\n")

        video_filter = (
            f"color=c=black:s={WIDTH}x{HEIGHT}:d=1[bgbase];"
            f"[0:v]scale={WIDTH}:{img_h}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{img_h}[imgbox];"
            f"[bgbase][imgbox]overlay=0:{img_y}[withimg];"
            f"[withimg]{hook_punch_filter}{hook_card_filter}ass={ass_path.name},"
            f"{watermark_filter}{cta_filter}null[v];"
        )
    else:
        video_filter = (
            f"[0:v]{hook_punch_filter}{hook_card_filter}ass={ass_path.name},"
            f"{watermark_filter}{cta_filter}null[v];"
        )

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

    stinger_idx = None
    if stinger_path:
        inputs += ["-i", str(stinger_path)]
        stinger_idx = next_idx
        next_idx += 1

    # modo card 'read': la narracion arranca despues del beat de lectura, asi que
    # la voz (y los sfx atados a palabras) se retrasan card_ms; la musica y el
    # stinger arrancan en 0 (suenan durante el card). total_dur incluye el card
    # para que el fade-out de la musica caiga al final real, no 2.2s antes.
    voice_delay_s = HOOK_CARD_DUR if read_mode else (OVERLAY_VOICE_DELAY if overlay_delay_mode else 0.0)
    card_ms = int(voice_delay_s * 1000)
    total_dur = audio_dur + voice_delay_s + (LOOP_DUR if hook_punch else 0.0)

    audio_labels = []
    audio_filters = ""
    if card_ms:
        audio_filters += f"[1:a]adelay={card_ms}|{card_ms}[voicesrc];"
        voice_lbl = "[voicesrc]"
    else:
        voice_lbl = "[1:a]"
    if music:
        fade_dur = min(2.5, total_dur / 4)
        fade_out_start = max(total_dur - fade_dur, 0)
        audio_filters += (
            f"{voice_lbl}asplit=2[voice_mix][voice_trigger];"
            f"[{music_idx}:a]aloop=loop=-1:size=2e9,volume=0.06,"
            f"afade=t=in:st=0:d={fade_dur:.2f},"
            f"afade=t=out:st={fade_out_start:.2f}:d={fade_dur:.2f}[bg];"
            "[bg][voice_trigger]sidechaincompress="
            "threshold=0.03:ratio=8:attack=20:release=400[bg_ducked];"
        )
        audio_labels += ["[voice_mix]", "[bg_ducked]"]
    else:
        audio_filters += f"{voice_lbl}anull[voice_mix];"
        audio_labels += ["[voice_mix]"]

    for k, ((ts, _), idx) in enumerate(zip(sfx_cues, sfx_idxs)):
        ms = int(ts * 1000) + card_ms
        audio_filters += f"[{idx}:a]adelay={ms}|{ms},volume=0.2[sfx{k}];"
        audio_labels.append(f"[sfx{k}]")

    if stinger_idx is not None:
        audio_filters += f"[{stinger_idx}:a]atrim=0:0.6,volume=0.42[stinger];"
        audio_labels.append("[stinger]")

    # el mix termina en audio_dur+voice_delay_s -- si hay loop visual al final
    # (hook_punch), el video queda LOOP_DUR mas largo que eso, y sin este padding
    # "-shortest" cortaria justo ese segmento de loop antes de que se vea (bug
    # real detectado 20 jul 2026: el ultimo frame mostraba una escena del medio,
    # no el loop, porque el audio mas corto truncaba el video).
    pad_filter = f",apad=pad_dur={LOOP_DUR}" if hook_punch else ""
    audio_filters += (
        f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:"
        "duration=first:dropout_transition=0:normalize=0,"
        f"loudnorm=I=-14:TP=-1.5:LRA=11{pad_filter}[aout]"
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


# ------------------------------------------------------------- MOTION GRAPHICS

MOTION_DIR = ROOT / "motion_graphics"

# mapeo palabra disparadora (trigger_word de pick_sfx_cues) -> emoji. Heuristica
# por categoria de sonido/concepto, no traduccion literal -- alcanza con que el
# icono refuerce visualmente lo mismo que ya dice el SFX (ver HISTORIAL_MEJORAS.md
# 21 jul 2026, patron "icono+SFX por cada beat" de los videos de referencia).
_EMOJI_CATEGORIES: list[tuple[tuple[str, ...], str]] = [
    (("radio", "transmission", "signal", "broadcast"), "\U0001F4FB"),
    (("shot", "gun", "gunfire", "rifle", "pistol"), "\U0001F4A5"),
    (("sword", "blade", "knife"), "\U0001F5E1"),
    (("explosion", "bomb", "blast"), "\U0001F4A3"),
    (("fire", "burn", "burned", "flame"), "\U0001F525"),
    (("water", "lake", "river", "flood", "drown"), "\U0001F30A"),
    (("money", "cash", "gold", "banknote", "currency", "counterfeit"), "\U0001F4B0"),
    (("key", "lock", "unlock", "locked"), "\U0001F513"),
    (("letter", "paper", "document", "telegram", "note"), "\U0001F4C4"),
    (("phone", "call", "telephone"), "\U0000260E"),
    (("bell", "alarm", "siren"), "\U0001F514"),
    (("clock", "time", "minutes", "hours"), "\U000023F0"),
    (("plates", "engraving", "printing", "press"), "\U0001F5A8"),
    (("glider", "plane", "aircraft", "flight"), "\U00002708"),
    (("kidnap", "kidnapped", "captured", "capture"), "\U0001F6A8"),
    (("dead", "died", "death", "killed"), "\U0001F480"),
    (("never", "found", "unsolved", "mystery"), "\U00002753"),
    (("cigar", "smoke"), "\U0001F6AC"),
]


def _word_to_emoji(word: str) -> str:
    w = re.sub(r"[^a-z]", "", word.lower())
    for keys, emoji in _EMOJI_CATEGORIES:
        if any(k in w for k in keys):
            return emoji
    return "\U00002757"  # exclamacion generica de fallback


# categoria -> query de foto real generica para Wikimedia. Paralelo a
# _EMOJI_CATEGORIES: mismo set de palabras disparadoras, pero acá el valor es
# una BUSQUEDA (no un emoji). El sticker intenta primero foto real recortada
# y cae a emoji solo si no hay resultado libre de un solo sujeto (pedido
# usuario 21 jul 2026: "foto real para todo lo que se pueda").
_PHOTO_QUERY_CATEGORIES: list[tuple[tuple[str, ...], str]] = [
    (("radio", "transmission", "signal", "broadcast"), "vintage military radio"),
    (("shot", "gun", "gunfire", "rifle", "pistol"), "WWII rifle"),
    (("sword", "blade", "knife"), "antique military sword"),
    (("explosion", "bomb", "blast"), "explosion black and white photo"),
    (("fire", "burn", "burned", "flame"), "fire vintage photo"),
    (("water", "lake", "river", "flood", "drown"), None),  # paisaje generico, mejor emoji
    (("money", "cash", "gold", "banknote", "currency", "counterfeit"), "banknote 1940s"),
    (("key", "lock", "unlock", "locked"), "antique lock"),
    (("letter", "paper", "document", "telegram", "note"), "declassified document"),
    (("phone", "call", "telephone"), "vintage telephone"),
    (("bell", "alarm", "siren"), "air raid siren"),
    (("clock", "time", "minutes", "hours"), "antique pocket watch"),
    (("plates", "engraving", "printing", "press"), "vintage printing press"),
    (("glider", "plane", "aircraft", "flight"), "WWII military aircraft"),
    (("kidnap", "kidnapped", "captured", "capture"), None),
    (("dead", "died", "death", "killed"), None),
    (("never", "found", "unsolved", "mystery"), None),
    (("cigar", "smoke"), "cigar vintage photo"),
    (("flag", "banner"), "military flag"),
    (("medal", "award", "decoration"), "military medal"),
    (("uniform", "soldier", "officer"), "WWII soldier uniform"),
    (("tank", "armor", "armored"), "WWII tank"),
    (("ship", "submarine", "boat", "vessel"), "WWII ship"),
]


def _scene_hint(text: str) -> tuple[str, str, str | None]:
    """Escanea el texto de una escena (search_term del guion) y devuelve
    (trigger_word_para_mostrar, emoji_fallback, photo_query|None). Reemplaza
    el matching anterior que solo miraba una palabra suelta (trigger_word de
    SFX) -- ahora cada ESCENA completa se analiza para elegir un sticker
    (1 por escena, ver HISTORIAL_MEJORAS.md 21 jul 2026)."""
    w = re.sub(r"[^a-z ]", "", text.lower())
    for i, (keys, emoji) in enumerate(_EMOJI_CATEGORIES):
        if any(k in w for k in keys):
            display = next((k for k in keys if k in w), keys[0])
            photo_q = _PHOTO_QUERY_CATEGORIES[i][1]
            return display.upper(), emoji, photo_q
    return "", "\U00002757", None


def _photo_sticker(query: str, clips_dir: Path, tag: str) -> str | None:
    """Intenta armar un sticker de FOTO REAL recortada para un objeto/lugar
    generico (no una persona) -- misma fuente (Wikimedia Commons, licencia
    libre) y mismo pipeline de recorte que add_real_photo_collage, pero mas
    chico y sin sesgo 'portrait' (un rifle o una bandera no son retratos).
    Devuelve el nombre de archivo relativo dentro de motion_graphics/public/
    o None si no hay candidato libre de un solo sujeto."""
    candidates = _wikimedia_commons_search(query, bias_portrait=False)
    if not candidates:
        return None
    import urllib.request
    fname = f"scene_sticker_{tag}.png"
    out_path = MOTION_DIR / "public" / fname
    for i, cand in enumerate(candidates[:6]):
        raw_path = clips_dir / f"scene_raw_{tag}_{i}.jpg"
        req = urllib.request.Request(cand["url"], headers={"User-Agent": "HiddenFactsBot/1.0 (contact@example.com)"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_path.write_bytes(resp.read())
        except Exception:
            continue
        if _cutout_and_halftone(raw_path, out_path) == "ok":
            return fname
    return None


def add_scene_stickers(video_path: Path, search_terms: list[str], durations: list[float],
                        out_dir: Path, words: list[tuple[float, float, str]] | None = None,
                        sticker_sfx: bool = False, tone: str | None = None,
                        sticker_sfx_file: str | None = None) -> Path:
    """Sticker por cada palabra clave REALMENTE narrada (words, con timestamp
    real de TTS) usando la libreria pre-generada de sticker_library.py --
    pedido usuario 22 jul 2026: 'asegurate de usarlo en cada palabra clave
    que se diga', no solo 1 por escena. Las escenas que no tienen ninguna
    keyword narrada caen al esquema viejo (foto real recortada de Wikimedia,
    y si no hay candidato, emoji -- ver HISTORIAL_MEJORAS.md 21 jul 2026) para
    no perder densidad visual. Si Remotion/Node no esta disponible o falla,
    devuelve el video sin tocar."""
    if not (MOTION_DIR / "node_modules").exists():
        log("motion", "motion_graphics/node_modules no existe, salteando (correr npm install)")
        return video_path

    clips_dir = out_dir / "clips"
    video_dur = ffprobe_duration(video_path)
    fps = FPS

    library_cues = sticker_library.prepare_render_cues(words, MOTION_DIR / "public") if words else []
    log("motion", f"{len(library_cues)} stickers de la libreria (keywords narradas)")

    cues = list(library_cues)
    t = 0.0
    for i, (term, dur) in enumerate(zip(search_terms, durations)):
        scene_start, scene_end = t, t + dur
        mid = t + dur / 2
        t += dur
        # ya hay un sticker de la libreria narrado en esta escena -- no
        # duplicar con el fallback generico (1 sticker visible a la vez)
        if any(scene_start <= c["time"] < scene_end for c in library_cues):
            continue
        keyword, emoji, photo_query = _scene_hint(term)
        photo = _photo_sticker(photo_query, clips_dir, str(i)) if photo_query else None
        cues.append({"time": mid, "keyword": keyword, "emoji": emoji, "photo": photo})
        if photo:
            log("motion", f"escena {i+1}: foto real ({photo_query})")
        else:
            log("motion", f"escena {i+1}: emoji fallback ({keyword or '?'})")
    cues.sort(key=lambda c: c["time"])

    props = {"cues": cues, "durationInFrames": max(int(round(video_dur * fps)), 1), "fps": fps,
              "width": WIDTH, "height": HEIGHT}
    props_path = clips_dir / "motion_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    # bug real (21 jul 2026): vp8/yuva420p NO preserva canal alpha de forma
    # confiable en este render (ya lo vimos antes con el prototipo manual) --
    # el resultado sale con fondo negro opaco en vez de transparente. ProRes
    # 4444 + yuva444p10le si preserva el alpha real, confirmado con ffprobe
    # en esa prueba. Usar siempre ProRes aca, nunca vp8/webm.
    overlay_path = clips_dir / "motion_overlay.mov"
    # en Windows "npx" es npx.cmd -- subprocess.run(shell=False, default de
    # run()) no lo resuelve y tira WinError 2. shutil.which encuentra el
    # ejecutable real sin necesitar shell=True para todo el resto de run().
    npx_bin = shutil.which("npx") or "npx"
    try:
        run([
            npx_bin, "remotion", "render",
            "--image-format=png", "--pixel-format=yuva444p10le",
            "--codec=prores", "--prores-profile=4444",
            "--props", str(props_path.resolve()),
            "src/index.jsx", "AutoOverlay", str(overlay_path.resolve()),
        ], cwd=str(MOTION_DIR))
    except Exception as e:
        log("motion", f"Render de Remotion fallo, se sigue sin motion graphics: {e}")
        return video_path

    # el resto del pipeline (subida, QA, este mismo main()) asume que el
    # resultado final siempre vive en out_dir/video.mp4 -- se compone a un
    # archivo temporal y se reemplaza in-place, nunca se cambia el nombre.
    # capa opcional de sonido de entrada de sticker (swish de papel en cada pop).
    # Se omite si: el flag esta apagado, no hay cues, no existe el archivo, o el
    # tono del video es sombrio (respeta la misma logica de tono que pick_sfx_cues).
    sfx_path = SFX_DIR / (sticker_sfx_file or STICKER_SFX_DEFAULT)
    somber = bool(tone) and any(w in tone.lower() for w in _SOMBER_TONE_WORDS)
    sfx_cue_times = [c["time"] for c in cues]
    use_sticker_sfx = bool(sticker_sfx and sfx_cue_times and sfx_path.exists() and not somber)
    if sticker_sfx and somber:
        log("motion", "sticker-sfx omitido: tono sombrio")
    elif sticker_sfx and not sfx_path.exists():
        log("motion", f"sticker-sfx omitido: no existe {sfx_path.name}")

    composited = clips_dir / "video_with_motion.mp4"
    try:
        if use_sticker_sfx:
            # un input del sonido por cada pop, retrasado a su tiempo y a volumen
            # bajo; se suma (amix normalize=0) sobre el audio original sin pisarlo.
            inputs = ["-i", str(video_path), "-i", str(overlay_path)]
            fc = "[1:v]format=yuva420p[ov];[0:v][ov]overlay=0:0[v];"
            labels = "[0:a]"
            for k, t in enumerate(sfx_cue_times):
                inputs += ["-i", str(sfx_path)]
                ms = int(round(t * 1000))
                fc += f"[{2 + k}:a]adelay={ms}|{ms},volume={STICKER_SFX_VOLUME}[ssf{k}];"
                labels += f"[ssf{k}]"
            fc += f"{labels}amix=inputs={1 + len(sfx_cue_times)}:normalize=0:duration=first[a]"
            run([
                "ffmpeg", "-y", *inputs,
                "-filter_complex", fc,
                "-map", "[v]", "-map", "[a]",
                "-c:a", "aac", "-b:a", "192k",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                str(composited),
            ])
        else:
            run([
                "ffmpeg", "-y", "-i", str(video_path), "-i", str(overlay_path),
                "-filter_complex",
                "[1:v]format=yuva420p[ov];[0:v][ov]overlay=0:0[v]",
                "-map", "[v]", "-map", "0:a", "-c:a", "copy",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                str(composited),
            ])
    except Exception as e:
        log("motion", f"Composicion ffmpeg fallo, se sigue sin motion graphics: {e}")
        return video_path

    shutil.copyfile(composited, video_path)
    log("motion", f"{len(cues)} stickers agregados (1 por escena)")
    return video_path


# -------------------------------------------------------------- REAL PHOTO COLLAGE

def _wikimedia_commons_search(term: str, bias_portrait: bool = True) -> list[dict]:
    """Busca fotos de dominio publico/CC en Wikimedia Commons para `term`.
    Devuelve una LISTA de candidatos {"url","license","title","artist"}
    (jpg/png con licencia libre), no solo el primero -- add_real_photo_collage
    los prueba en orden y descarta los que no son un retrato de una sola
    persona (ver _is_single_subject), en vez de quedarse con el primer
    resultado aunque sea una foto grupal (bug real detectado 21 jul 2026:
    "Fidel Castro" trajo una foto con Cristina Kirchner). Nunca usa
    buscadores de imagenes tipo Google/Apify -- esos devuelven resultados con
    copyright real, mal encaje para un canal monetizado (riesgo de Content
    ID/strike). Wikimedia/NARA/LoC tienen API propia con licencia explicita
    por archivo (ver HISTORIAL_MEJORAS.md 21 jul 2026)."""
    import urllib.request, urllib.parse
    # se refuerza la query con "portrait" (si no la trae ya) para sesgar la
    # busqueda hacia fotos de una sola persona desde el vamos -- no reemplaza
    # la heuristica de abajo, solo mejora el orden de los candidatos.
    term_q = term
    if bias_portrait and "portrait" not in term.lower():
        term_q = f"{term} portrait"
    q = urllib.parse.quote(term_q)
    url = (f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
           f"&gsrsearch={q}&gsrnamespace=6&gsrlimit=12&prop=imageinfo"
           f"&iiprop=url|extmetadata|mime|size&format=json")
    req = urllib.request.Request(url, headers={"User-Agent": "HiddenFactsBot/1.0 (contact@example.com)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except Exception as e:
        log("collage", f"Busqueda Wikimedia fallo: {e}")
        return []
    candidates = []
    for p in data.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        if "image/jpeg" not in mime and "image/png" not in mime:
            continue
        w, h = ii.get("width", 0), ii.get("height", 0)
        if w < 200 or h < 200:
            continue
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", ""))
        candidates.append({"url": ii.get("url"), "license": lic,
                            "title": p.get("title", ""), "artist": artist})
    return candidates


def _is_single_subject(alpha_channel) -> bool:
    """Heuristica anti-foto-grupal: cuenta blobs grandes en el canal alpha del
    recorte (rembg). Una foto grupal casi siempre produce >1 blob grande
    (personas separadas) o un blob unico demasiado ancho respecto a su alto
    (dos cuerpos pegados). Se usa para descartar candidatos sin intervencion
    manual -- el usuario pidio automatizacion 100%, sin curar terminos de
    busqueda a mano (ver HISTORIAL_MEJORAS.md 21 jul 2026)."""
    import numpy as np
    from skimage import measure
    mask = np.array(alpha_channel) > 40
    if mask.sum() < 500:
        return False
    labeled = measure.label(mask)
    props = measure.regionprops(labeled)
    if not props:
        return False
    total_area = mask.sum()
    big_blobs = [r for r in props if r.area > total_area * 0.08]
    if len(big_blobs) > 1:
        return False
    main = max(props, key=lambda r: r.area)
    y0, x0, y1, x1 = main.bbox
    bbox_w, bbox_h = (x1 - x0), (y1 - y0)
    if bbox_w == 0 or bbox_h == 0:
        return False
    # un retrato/cuerpo de una persona es mas alto que ancho; > 1.35 de ancho
    # relativo a alto es tipico de dos personas paradas una al lado de la otra.
    if bbox_w / bbox_h > 1.35:
        return False
    return True


def _cutout_and_halftone(image_path: Path, out_path: Path) -> str:
    """Recorta el sujeto (rembg, sin API de pago) y aplica look 'foto de
    archivo recortada de periodico' (halftone B/N) preservando el alpha del
    recorte. Devuelve "ok", "no_rembg" o "multi_subject" (nunca lanza) --
    add_real_photo_collage usa el resultado para decidir si probar el
    siguiente candidato de la busqueda."""
    try:
        from rembg import remove
    except ImportError:
        log("collage", "rembg no instalado (py -m pip install rembg onnxruntime), salteando collage")
        return "no_rembg"
    from PIL import Image, ImageOps
    im = Image.open(image_path)
    cutout = remove(im)
    alpha = cutout.split()[3]
    if not _is_single_subject(alpha):
        return "multi_subject"
    rgb = cutout.convert("RGB")
    gray = ImageOps.autocontrast(rgb.convert("L"), cutoff=2)
    small = gray.resize((max(gray.width // 4, 1), max(gray.height // 4, 1)), Image.BILINEAR)
    dotted = small.resize(gray.size, Image.NEAREST)
    halftone = Image.blend(gray, dotted, 0.35)
    out = Image.merge("RGBA", (halftone, halftone, halftone, alpha))
    out.save(out_path)
    return "ok"


def add_real_photo_collage(video_path: Path, collage_subject: str, out_dir: Path,
                            collage_time: float | None = None) -> Path:
    """Inserta una escena de collage con FOTO REAL recortada (estilo 'recorte
    de periodico', pedido por el usuario 21 jul 2026) en un unico momento del
    video (default: ~66% de la duracion, el beat de 'reveal'). Fuente: solo
    Wikimedia Commons con licencia libre explicita -- nunca scraping de
    imagenes con copyright. Si falla cualquier paso (sin resultado, sin
    rembg, sin Remotion), devuelve el video sin tocar."""
    if not (MOTION_DIR / "node_modules").exists():
        log("collage", "motion_graphics/node_modules no existe, salteando (correr npm install)")
        return video_path

    candidates = _wikimedia_commons_search(collage_subject)
    if not candidates:
        log("collage", f"Sin resultado libre en Wikimedia para '{collage_subject}', salteando")
        return video_path

    import urllib.request
    clips_dir = out_dir / "clips"
    photo_path = MOTION_DIR / "public" / "collage_photo.png"
    hit = None
    no_rembg = False
    # prueba candidatos en orden hasta encontrar UNO de una sola persona --
    # nunca se conforma con el primer resultado aunque sea foto grupal (esto
    # es lo que reemplaza la curacion manual del termino de busqueda: el
    # usuario pidio automatizacion 100%, ver HISTORIAL_MEJORAS.md 21 jul 2026).
    for i, cand in enumerate(candidates):
        raw_path = clips_dir / f"collage_raw_{i}.jpg"
        req = urllib.request.Request(cand["url"], headers={"User-Agent": "HiddenFactsBot/1.0 (contact@example.com)"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw_path.write_bytes(resp.read())
        except Exception as e:
            log("collage", f"Descarga fallo para candidato {i} ({cand['title']}): {e}")
            continue
        status = _cutout_and_halftone(raw_path, photo_path)
        if status == "no_rembg":
            no_rembg = True
            break
        if status == "ok":
            hit = cand
            log("collage", f"Candidato {i+1}/{len(candidates)} aceptado: {cand['title']}")
            break
        log("collage", f"Candidato {i+1}/{len(candidates)} descartado (foto grupal/multi-sujeto): {cand['title']}")

    if no_rembg:
        return video_path
    if hit is None:
        log("collage", f"Ningun candidato de '{collage_subject}' paso el filtro de sujeto unico, salteando")
        return video_path

    # credito de atribucion: CC-BY/CC-BY-SA lo exigen -- se guarda para agregar
    # a la descripcion del video, nunca se omite silenciosamente.
    credit_path = out_dir / "collage_credit.txt"
    credit_path.write_text(
        f"Foto: {hit['title']} ({hit['license']}), autor: {hit.get('artist') or 'desconocido'}, "
        f"via Wikimedia Commons — {hit['url']}",
        encoding="utf-8")

    video_dur = ffprobe_duration(video_path)
    scene_dur = 2.4
    t0 = collage_time if collage_time is not None else max(video_dur * 0.66 - scene_dur / 2, 0)
    t0 = min(t0, max(video_dur - scene_dur, 0))

    props = {"photo": "collage_photo.png", "clipping": None, "stampText": "DECLASSIFIED",
              "durationInFrames": int(round(scene_dur * FPS)), "fps": FPS, "width": WIDTH, "height": HEIGHT}
    props_path = clips_dir / "collage_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    overlay_path = clips_dir / "collage_overlay.mov"
    npx_bin = shutil.which("npx") or "npx"
    try:
        run([
            npx_bin, "remotion", "render",
            "--image-format=png", "--pixel-format=yuva444p10le",
            "--codec=prores", "--prores-profile=4444",
            "--props", str(props_path.resolve()),
            "src/index.jsx", "RealCollage", str(overlay_path.resolve()),
        ], cwd=str(MOTION_DIR))
    except Exception as e:
        log("collage", f"Render de Remotion fallo, se sigue sin collage: {e}")
        return video_path

    composited = clips_dir / "video_with_collage.mp4"
    try:
        run([
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(overlay_path),
            "-filter_complex",
            # el overlay .mov arranca SU PROPIO timeline en t=0 (dura solo
            # scene_dur); sin el setpts, al llegar t0 en el video principal el
            # stream corto ya esta agotado (EOF) y el collage nunca aparece --
            # bug real detectado 21 jul 2026 en QA visual. setpts+t0 corre el
            # overlay para que sus frames coincidan con el instante correcto.
            f"[1:v]format=yuva420p,setpts=PTS+{t0}/TB[ov];"
            f"[0:v][ov]overlay=0:0:enable='between(t,{t0},{t0 + scene_dur})'[v]",
            "-map", "[v]", "-map", "0:a", "-c:a", "copy",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            str(composited),
        ])
    except Exception as e:
        log("collage", f"Composicion ffmpeg fallo, se sigue sin collage: {e}")
        return video_path

    shutil.copyfile(composited, video_path)
    log("collage", f"Collage de foto real insertado en t={t0:.1f}s ({hit['title']}, {hit['license']})")
    return video_path


def add_real_photo_collages(video_path: Path, subjects: list[dict], out_dir: Path) -> Path:
    """Version multi-sujeto de add_real_photo_collage -- el guion puede listar
    varias fotos reales ({"subject": ..., "time": opcional}) en vez de una
    sola (pedido usuario 21 jul 2026: 'mas stickers/fotos completas'). Si un
    item no trae "time", se reparte automaticamente y en orden a lo largo del
    video (excluyendo el primer/ultimo 12% para no pisar el hook ni el
    cierre), dejando 2.4s de margen entre cada uno para que no se superpongan."""
    if not subjects:
        return video_path
    video_dur = ffprobe_duration(video_path)
    scene_dur = 2.4
    explicit = [s for s in subjects if s.get("time") is not None]
    auto = [s for s in subjects if s.get("time") is None]
    if auto:
        lo, hi = video_dur * 0.12, video_dur * 0.88
        span = max(hi - lo, 0)
        n = len(auto)
        for i, s in enumerate(auto):
            frac = (i + 1) / (n + 1)
            s["_auto_time"] = lo + span * frac

    ordered = sorted(subjects, key=lambda s: s.get("time", s.get("_auto_time", 0)))
    for s in ordered:
        t = s.get("time", s.get("_auto_time"))
        video_path = add_real_photo_collage(video_path, s["subject"], out_dir, collage_time=t)
    return video_path


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
    parser.add_argument("--no-motion", action="store_true",
                        help="Desactiva los graficos de movimiento automaticos (icono+texto "
                             "kinetico via Remotion) que se agregan por cada sfx_cue detectado.")
    parser.add_argument("--no-collage", action="store_true",
                        help="Desactiva la escena de collage con foto real recortada aunque el "
                             "guion tenga 'collage_subject'.")
    parser.add_argument("--sticker-sfx", action="store_true",
                        help="Capa opcional (opt-in, para A/B): un swish de papel suave en el "
                             "frame en que cada sticker hace pop -- el 'sonido del collage "
                             "armandose', motivado por la estetica de recortes. Volumen bajo, "
                             "se omite entero si el music_mood del video es sombrio. NO toca "
                             "pick_sfx_cues (que sigue siendo puramente diegetico).")
    parser.add_argument("--sticker-sfx-file", default=None, metavar="NOMBRE",
                        help="Nombre de archivo dentro de assets/sfx/ para reemplazar el swish "
                             f"de papel por defecto ({STICKER_SFX_DEFAULT}). Para probar de oido "
                             "otro sonido sin tocar el codigo.")
    parser.add_argument("--nanobanana", action="store_true",
                        help="Usa imagenes estaticas generadas con Nano Banana (Gemini) en vez de "
                             "Pexels/gradiente. Requiere GEMINI_API_KEY.")
    parser.add_argument("--seedream", action="store_true",
                        help="Usa imagenes estaticas generadas con Seedream (ByteDance, via PiAPI) "
                             "en vez de Nano Banana -- mejor consistencia multi-referencia de "
                             "personaje segun benchmarks (ver investigacion 19 jul 2026). Requiere "
                             "PIAPI_API_KEY. Las hojas de personaje siguen usando Nano Banana por "
                             "ahora (requiere tambien GEMINI_API_KEY si el guion usa 'style').")
    parser.add_argument("--flow", action="store_true",
                        help="Genera imagenes gratis en Google Flow (nano banana 2) via "
                             "automatizacion propia (flow_automation.py) en vez de pagar la API "
                             "de Gemini. Requiere login previo: 'python flow_automation.py "
                             "--login'. Cae a Nano Banana API (GEMINI_API_KEY) automaticamente "
                             "si Flow falla o si la escena necesita reference_image/style "
                             "(Flow no soporta consistencia de personaje en este flujo).")
    parser.add_argument("--veo-hero", type=int, default=None, metavar="N",
                        help="Anima con Veo (image-to-video, ~$1) solo la escena N (0-indexed) "
                             "de --nanobanana; el resto queda estatico. Modo hibrido costo/impacto.")
    parser.add_argument("--wan-hero", type=Path, default=None, metavar="PATH",
                        help="Usa un video ya animado localmente (Wan 2.2 via ComfyUI, gratis) "
                             "como escena 0 en vez de generarla; el resto sigue estatico igual "
                             "que --veo-hero pero sin costo de API.")
    parser.add_argument("--watermark", default="",
                        help="Texto de marca de agua (esquina superior derecha). Vacio por "
                             "defecto -- especifica explicitamente '--watermark ImPixxel' para "
                             "ese canal (antes el default era 'ImPixxel' fijo y se colaba por "
                             "error en videos de HiddenFacts, ver bug 19 jul 2026).")
    parser.add_argument("--cta-text", default=None,
                        help="Texto de CTA en pantalla (nunca narrado, evita el 'Cliff' de "
                             "retencion del CTA hablado). Requiere --cta-position.")
    parser.add_argument("--cta-position", choices=["start", "middle", "end"], default=None,
                        help="Donde aparece --cta-text: 'start' (~0.5s), 'middle' (mitad del "
                             "video), o 'end' (ultimos ~3.5s). Test de posicion del CTA.")
    parser.add_argument("--punch-index", type=int, default=None, metavar="N",
                        help="Escena (0-indexed) que recibe el zoom 'golpe' para acentuar el "
                             "remate/giro comico. Por defecto la penultima escena.")
    parser.add_argument("--intro-stinger", action="store_true",
                        help="Agrega un whoosh/riser generico en el frame 0 (gancho auditivo "
                             "independiente de la narracion). Test de primeros 2 segundos.")
    parser.add_argument("--subs-lead-ms", type=int, default=0, metavar="MS",
                        help="Adelanta el texto de los subtitulos MS milisegundos respecto al "
                             "audio (no afecta el audio). Test de primeros 2 segundos.")
    parser.add_argument("--split-first-clip", action="store_true",
                        help="Corta la escena 1 en dos mitades (mismo clip) para agregar un "
                             "corte extra de ritmo en el primer segundo. Test de primeros 2 segundos.")
    parser.add_argument("--hook-max", dest="hook_max", action="store_true", default=True,
                        help="Bundle de gancho de los primeros 2s: activa golpe auditivo en "
                             "frame 0 (stinger), texto adelantado 150ms, zoom de entrada fuerte, "
                             "wipe circular de entrada, y el premise card si el guion trae "
                             "'hook_card'. Default ON desde el 19 jul 2026 (paso de test A/B a "
                             "estandar de produccion). Usa --no-hook-max para desactivarlo.")
    parser.add_argument("--no-hook-max", dest="hook_max", action="store_false",
                        help="Desactiva --hook-max (vuelve al comportamiento clasico sin bundle de gancho).")
    parser.add_argument("--hook-card-mode", choices=["overlay", "read"], default="overlay",
                        help="Modo del premise card (campo 'hook_card' del guion): 'overlay' "
                             "(se superpone mientras ya narra) o 'read' (frame congelado 2.2s, "
                             "solo musica/stinger, la narracion arranca despues).")
    parser.add_argument("--archivo", action="store_true",
                        help="Renderiza con el motor visual 'Archivo Vivo' (Remotion, "
                             "collage documental punchy) en vez del ensamblado FFmpeg "
                             "clasico. Requiere imagenes de escena (--nanobanana/--seedream). "
                             "Ver archivo_engine.py.")
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
    if args.seedream and not os.getenv("PIAPI_API_KEY"):
        print("ERROR: falta PIAPI_API_KEY en .env. Registrate en https://piapi.ai y anda a "
              "Workspace > Settings > API Keys.")
        return 1
    if args.flow:
        if not os.getenv("GEMINI_API_KEY"):
            print("ERROR: --flow necesita GEMINI_API_KEY igual (como fallback si Flow falla).")
            return 1
        from flow_automation import is_logged_in
        if not is_logged_in():
            print("ERROR: no hay sesion de Flow guardada. Corre primero: "
                  "python flow_automation.py --login")
            return 1

    base_slug = f"{date.today().isoformat()}-{slugify(topic)}"
    out_dir = OUTPUT_ROOT / base_slug
    # si la carpeta ya existe (o se crea al mismo tiempo por otra corrida en
    # paralelo), es una corrida DISTINTA con el mismo titulo el mismo dia (ej.
    # mismo guion re-generado con --cta-position distinto) -- usar un sufijo
    # incremental en vez de pisar voice.mp3/clips/video.mp4 de la otra corrida.
    # mkdir(exist_ok=False) es atomico a nivel de SO: si dos procesos compiten
    # por el mismo out_dir, solo uno gana la carpeta base y el otro reintenta
    # con el siguiente sufijo (bug real: dos corridas lanzadas en paralelo
    # esta sesion pasaron el chequeo "existe video.mp4" ANTES de que ninguna
    # hubiera escrito el archivo, y terminaron pisandose los inputs a mitad
    # de render).
    suffix = 2
    while True:
        try:
            out_dir.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            out_dir = OUTPUT_ROOT / f"{base_slug}-{suffix}"
            suffix += 1
    _atomic_write_json(out_dir / "script.json", data)

    media_source = ("flow" if args.flow else
                    "seedream" if args.seedream else
                    "nanobanana" if args.nanobanana else
                    ("gradient" if args.no_pexels else "pexels"))

    # --hook-max: bundle de palancas del gancho de los primeros 2s (opt-in, para
    # A/B). Fuerza stinger + texto adelantado + zoom fuerte; el premise card se
    # activa aparte segun 'hook_card' del guion. Sin el flag, nada cambia.
    hook_card = data.get("hook_card")
    card_duration = data.get("card_duration")
    silent_card_mode = bool(card_duration) and not data.get("script")
    # silent_card_mode: el usuario pidio explicitamente CERO efectos (sin wipe de
    # entrada, sin stinger, sin zoom) -- que se vea practicamente como una imagen
    # fija (feedback 20 jul 2026). El bundle --hook-max no aplica aca.
    intro_stinger = (args.intro_stinger or args.hook_max) and not silent_card_mode
    hook_strong = args.hook_max and not silent_card_mode
    subs_lead = args.subs_lead_ms or (150 if args.hook_max else 0)
    # offset de subs: 2.2s en modo 'read' (narracion arranca tras el card), 1s en
    # 'overlay' (nuevo, feedback 20 jul 2026 -- dar tiempo de leer antes de narrar)
    card_read = bool(hook_card) and args.hook_card_mode == "read"
    subs_offset = 2200 if card_read else (1000 if hook_card else 0)

    # card_duration + sin 'script': modo "solo lectura", sin narrador -- un card
    # de texto denso (mas largo de lo que la narracion permitiria a ritmo de
    # habla) se queda fijo TODA la duracion; el video es corto (tipico 7s) y
    # apuesta a que el viewer no termine de leer en un solo pase y deje que
    # YouTube lo repita solo (loop nativo) para terminar de leer -- pedido
    # 20 jul 2026 tras ver que el ultrashort narrado limita el texto a ~18-20
    # palabras por el ritmo de habla (2.3-2.6 palabras/seg).

    try:
        if silent_card_mode:
            words = []
            audio_path = out_dir / "voice.mp3"
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                 "-t", f"{card_duration:.2f}", "-q:a", "9", "-acodec", "libmp3lame",
                 str(audio_path)])
            ass_path = generate_subtitles(words, out_dir, lead_ms=0, offset_ms=0)
            audio_dur = float(card_duration)
            durations = [audio_dur]
            n_clips = 1
        else:
            _check_pacing(data["script"])
            _check_script_lint(data["script"], data.get("title", ""), args.voice,
                               search_terms=data.get("search_terms"))
            audio_path, words = with_retries(generate_audio, data["script"], args.voice, args.rate, out_dir)
            ass_path = generate_subtitles(words, out_dir, lead_ms=subs_lead, offset_ms=subs_offset)

            audio_dur = ffprobe_duration(audio_path)
            n_clips = args.clips
            durations = _scene_boundaries(words, n_clips, audio_dur)
            if card_duration:
                # script presente PERO se pidio una duracion fija de card (caso
                # hibrido, poco comun) -- fuerza la duracion total en vez de la
                # derivada de la narracion.
                audio_dur = float(card_duration)
                durations = [audio_dur]

        clips = acquire_media(data["search_terms"], n_clips, durations,
                              out_dir, media_source=media_source, veo_hero_index=args.veo_hero,
                              punch_index=args.punch_index, style=data.get("style") or HIDDENFACTS_STYLE,
                              static=bool(data.get("caption_text")) or silent_card_mode,
                              hook_strong=hook_strong,
                              wan_hero_path=args.wan_hero)

        if args.archivo and not silent_card_mode:
            # Motor "Archivo Vivo" (23 jul 2026): la composicion Remotion
            # manifest-driven reemplaza ensamblado FFmpeg + ASS + stickers +
            # collage (ver archivo_engine.py y memoria estilo-archivo-vivo)
            import archivo_engine
            final = archivo_engine.render_from_parts(
                out_dir, data, [(ws, w) for ws, _we, w in words], audio_path)
        else:
            sfx_cues_full = ([] if (args.no_sfx or silent_card_mode) else
                        pick_sfx_cues(words, tone=data.get("music_mood"),
                                      script=data.get("script"),
                                      search_terms=data.get("search_terms")))
            sfx_cues = [(t, p) for t, p, _ in sfx_cues_full]
            # silent_card_mode (sin narrador, card de texto largo): NO generar musica
            # propia -- estos videos se pensaron para reemplazar la musica con un
            # audio trending del nicho, agregado a mano en el editor de Shorts de
            # Studio (ver memoria musica-trending-videos-solo-lectura). Generar
            # musica igual solo gastaria cuota/plata de Lyria para algo que se va a
            # descartar.
            final = assemble(clips, audio_path, ass_path, out_dir,
                              music_mood=(None if silent_card_mode else data.get("music_mood")),
                              sfx_cues=sfx_cues,
                              durations=durations, watermark=args.watermark or None,
                              cta_text=args.cta_text, cta_position=args.cta_position,
                              intro_stinger=intro_stinger,
                              split_first_clip=args.split_first_clip,
                              caption_header=data.get("caption_header"),
                              caption_text=data.get("caption_text"),
                              caption_keywords=data.get("caption_keywords"),
                              hook_card=hook_card, hook_card_mode=args.hook_card_mode,
                              hook_punch=hook_strong)

            # stickers automaticos (21 jul 2026): UNO por escena (search_term), no
            # atado a sfx_cues -- mas denso, y cada uno intenta foto real recortada
            # antes de caer a emoji (ver HISTORIAL_MEJORAS.md). No aplica al modo
            # silent_card_mode (sin escenas narradas) ni si el usuario paso --no-motion.
            if not silent_card_mode and not args.no_motion:
                final = add_scene_stickers(final, data["search_terms"], durations, out_dir, words=words,
                                           sticker_sfx=args.sticker_sfx, tone=data.get("music_mood"),
                                           sticker_sfx_file=args.sticker_sfx_file)

            # collage de foto real (21 jul 2026): campo del guion 'collage_subjects'
            # (lista de {"subject", "time" opcional}) o el viejo 'collage_subject'
            # singular (compatibilidad) -- ver add_real_photo_collages().
            collage_subjects = data.get("collage_subjects")
            if collage_subjects is None and data.get("collage_subject"):
                collage_subjects = [{"subject": data["collage_subject"], "time": data.get("collage_time")}]
            if collage_subjects and not args.no_collage and not silent_card_mode:
                final = add_real_photo_collages(final, collage_subjects, out_dir)
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
