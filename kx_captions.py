"""Fuente de timing del karaoke KoreX → Caption[] de @remotion/captions.

Orden de preferencia (Misión 0001, Fase 1):
  1. Las marcas por palabra del TTS (`words.json` de qw_korex): exactas por
     construcción, gratis, sin modelo.
  2. Respaldo: alineación con faster-whisper (MIT; pesos Whisper MIT) sobre
     el audio. Desviación declarada frente a la spec, que pedía WhisperX: el
     alineador por defecto de WhisperX para español es VOXPOPULI de
     torchaudio, CC BY-NC (no comercial). faster-whisper ya está instalado,
     no arrastra torch y su licencia es permisiva.

`paginate()` es el gemelo en Python de `paginate()` en
motion_graphics/src/kx/KxCaptions.jsx: la QA compara contra las mismas
páginas que se ven en pantalla. Si cambias uno, cambia el otro.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

COMBINE_MS = 800
MIN_WORDS, MAX_WORDS = 2, 4
_SENT_END = re.compile(r"[.!?…:][\"”»)]?$")


def _caption(i: int, text: str, start_s: float, end_s: float, conf: float | None) -> dict:
    ms0, ms1 = round(start_s * 1000), round(end_s * 1000)
    return {"text": (" " if i else "") + text.strip(), "startMs": ms0, "endMs": max(ms1, ms0 + 1),
            "timestampMs": ms0, "confidence": conf}


def from_tts(words: list, until_s: float | None = None) -> list[dict]:
    """words.json ([[start, end, word], ...]) → Caption[]."""
    out = []
    for start, end, text in words:
        if until_s is not None and end > until_s + 0.05:
            break
        out.append(_caption(len(out), text, start, min(end, until_s or end), 1.0))
    return out


def from_whisper(audio: Path, model_size: str = "small") -> list[dict]:
    """Respaldo: transcribe + alinea por palabra con faster-whisper."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(audio), language="es", word_timestamps=True,
                                   vad_filter=False, beam_size=5)
    out = []
    for seg in segments:
        for w in seg.words or []:
            out.append(_caption(len(out), w.word, w.start, w.end, round(w.probability, 3)))
    return out


def get_captions(out_dir: Path, audio: Path | None = None, until_s: float | None = None) -> tuple[list[dict], str]:
    """Devuelve (captions, fuente). Fuente = 'tts' o 'whisper'."""
    words_path = out_dir / "words.json"
    if words_path.exists():
        return from_tts(json.loads(words_path.read_text(encoding="utf-8")), until_s), "tts"
    audio = audio or next((p for p in (out_dir / "voice.wav", out_dir / "voice.mp3") if p.exists()), None)
    if audio is None:
        raise FileNotFoundError(f"sin words.json ni voz en {out_dir}")
    caps = from_whisper(audio)
    if until_s is not None:
        caps = [c for c in caps if c["startMs"] < until_s * 1000]
    return caps, "whisper"


def _tiktok_pages(captions: list[dict]) -> list[list[dict]]:
    """Port de createTikTokStyleCaptions (@remotion/captions 4.0.495)."""
    pages, cur, cur_from, cur_to = [], [], 0, 0
    for c in captions:
        tok = {"text": c["text"], "fromMs": c["startMs"], "toMs": c["endMs"]}
        if c["text"].startswith(" ") and cur_to - cur_from > COMBINE_MS:
            if cur:
                pages.append(cur)
            tok["text"] = tok["text"].lstrip()
            cur, cur_from = [tok], c["startMs"]
        else:
            if not cur:
                cur_from = c["startMs"]
            cur.append(tok)
        cur_to = c["endMs"]
    if cur:
        pages.append(cur)
    return pages


_CLAUSE = re.compile(r"[.!?…:;,][\"”»)]?$")


def _ends(tok: dict) -> bool:
    return bool(_SENT_END.search(tok["text"].strip()))


def _compositions(n: int, k: int) -> list[list[int]]:
    if k == 1:
        return [[n]] if MIN_WORDS <= n <= MAX_WORDS else []
    return [[s, *r] for s in range(MIN_WORDS, MAX_WORDS + 1) for r in _compositions(n - s, k - 1)]


def _split_clause(toks: list[dict]) -> list[list[dict]]:
    n = len(toks)
    if n <= MAX_WORDS:
        return [toks]
    best = None
    k = -(-n // MAX_WORDS)
    while best is None and k <= -(-n // MIN_WORDS):
        for sizes in _compositions(n, k):
            pos, pauses = 0, 0
            for s in sizes[:-1]:
                pos += s
                pauses += toks[pos]["pause"]
            score = pauses * 10 - (max(sizes) - min(sizes))
            if best is None or score > best[0]:
                best = (score, sizes)
        k += 1
    out, pos = [], 0
    for s in best[1]:
        out.append(toks[pos:pos + s])
        pos += s
    return out


def paginate(captions: list[dict]) -> list[dict]:
    toks = [{"text": t["text"].strip(), "fromMs": t["fromMs"], "toMs": t["toMs"], "pause": i == 0}
            for p in _tiktok_pages(captions) for i, t in enumerate(p)]
    chunks, cur = [], []
    for t in toks:
        cur.append(t)
        if _CLAUSE.search(t["text"]):
            chunks += _split_clause(cur)
            cur = []
    if cur:
        chunks += _split_clause(cur)
    out: list[list[dict]] = []
    carry: list[dict] = []

    def can_join_prev(n: int) -> bool:
        return bool(out) and not _ends(out[-1][-1]) and len(out[-1]) + n <= MAX_WORDS

    for c in chunks:
        p = carry + c
        if len(p) > MAX_WORDS:
            if can_join_prev(len(carry)):
                out[-1] += carry
            else:
                out.append(carry)
            p = list(c)
        carry = []
        if len(p) == 1 and not _ends(p[0]):
            carry = p
        else:
            out.append(p)
    if carry:
        if can_join_prev(len(carry)):
            out[-1] += carry
        else:
            out.append(carry)
    return [{"text": " ".join(t["text"] for t in p), "startMs": p[0]["fromMs"],
             "endMs": p[-1]["toMs"], "tokens": p} for p in out]