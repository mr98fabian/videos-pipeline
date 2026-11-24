"""Comprobaciones del artefacto KoreX (base del gate Día 0 de la Fase 7).

Todas miran el MP4 renderizado, no lo que el generador dice que hizo:
  check_palette     barrido de color: solo INK/PAPER/DEBT y sus mezclas,
                    DEBT ≤8 % por frame, cero color en las cajas de personaje.
  check_safe_zone   nada oscuro (texto/trazo) fuera de la caja 840×960.
  check_whisper     transcribe el clip renderizado y confirma el texto de
                    cada página del karaoke y su ventana de tiempo.
  contact_sheet     hoja de contacto con la zona segura dibujada.
"""
from __future__ import annotations

import difflib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

import numpy as np

# Mismos valores que motion_graphics/src/kx/tokens.js
INK, PAPER, DEBT = (17, 17, 17), (244, 241, 234), (200, 16, 46)
DEBT_MAX = 0.08
SAFE = (48, 288, 888, 1248)  # x0, y0, x1, y1
W, H = 1080, 1920
OFF_TOL = 14.0     # más lejos que esto de la recta INK→PAPER = píxel con color
CHAR_MAX = 0.0005  # tolerancia de color en caja de personaje (sangrado 4:2:0)


def _frames(video: Path, fps: float, scale: int = 2):
    """Itera (t, frame RGB uint8) a `fps`, reducido 1/scale con vecino más
    cercano (no promedia: no inventa mezclas de color)."""
    w, h = W // scale, H // scale
    cmd = ["ffmpeg", "-v", "error", "-i", str(video), "-vf",
           f"fps={fps},scale={w}:{h}:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n, size = 0, w * h * 3
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            yield n / fps, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            n += 1
    finally:
        p.stdout.close()
        p.wait(timeout=60)


def _seg_dist(px: np.ndarray, a, b) -> np.ndarray:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((px - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(px - (a + t[:, None] * ab), axis=1)


def _hue_deg(px: np.ndarray) -> np.ndarray:
    r, g, b = (px[:, i] / 255 for i in range(3))
    mx, mn = np.max(px, axis=1) / 255, np.min(px, axis=1) / 255
    d = np.where(mx - mn == 0, 1e-9, mx - mn)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4))
    return h * 60


_DEBT_HUE = float(_hue_deg(np.array([DEBT], float))[0])
# El códec hace "ringing" en los bordes duros: píxeles un poco más negros que
# INK o más claros que PAPER. Eso no es otro color; se tolera extendiendo la
# recta neutra un 6 % por cada extremo.
_INK_X = tuple(np.clip(np.array(INK) - 0.06 * (np.array(PAPER) - np.array(INK)), 0, 255))
_PAPER_X = tuple(np.clip(np.array(PAPER) + 0.06 * (np.array(PAPER) - np.array(INK)), 0, 255))


def classify(px: np.ndarray, tol: float = OFF_TOL, hue_tol: float = 30.0):
    """→ (neutral, debt, off) como máscaras booleanas.
    neutral: sobre la recta INK→PAPER (mezclas, grano, antialias).
    debt: con color y de tono rojo deuda (incluye rosas y granates que el
          submuestreo 4:2:0 del H.264 crea en los bordes del rojo).
    off: con color de cualquier otro tono → fuera de paleta."""
    chroma = _seg_dist(px, _INK_X, _PAPER_X) > tol
    dh = np.abs(((_hue_deg(px) - _DEBT_HUE) + 180) % 360 - 180)
    debt = chroma & (dh <= hue_tol)
    return ~chroma, debt, chroma & ~debt


def _palette_frame(img: np.ndarray, char_boxes, scale: int, tol: float):
    _, debt, off = (m.reshape(img.shape[:2]) for m in classify(img.reshape(-1, 3).astype(float), tol))
    cpx = carea = 0
    for b in char_boxes:
        x0, y0, x1, y1 = (int(v) // scale for v in (b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]))
        cpx += int((debt[y0:y1, x0:x1] | off[y0:y1, x0:x1]).sum())
        carea += (x1 - x0) * (y1 - y0)
    return float(off.mean()), float(debt.mean()), cpx, carea


def _palette_verdict(off, debt, char_frac, where=""):
    fails = []
    if off > 0.0005:
        fails.append(f"color fuera de paleta: {off:.3%} de los píxeles{where}")
    if debt > DEBT_MAX:
        fails.append(f"rojo deuda {debt:.2%} > {DEBT_MAX:.0%}{where}")
    if char_frac > CHAR_MAX:
        fails.append(f"color dentro de la caja del personaje: {char_frac:.3%}")
    return fails


def check_palette(video: Path, char_boxes: list[dict], fps: float = 6) -> tuple[list[str], dict]:
    """Barrido del MP4 codificado (lo que verá YouTube)."""
    worst_off = worst_debt = 0.0
    worst_t, cpx, carea, frames = 0.0, 0, 0, 0
    for t, img in _frames(video, fps):
        off, debt, c, a = _palette_frame(img, char_boxes, 2, OFF_TOL)
        if off > worst_off:
            worst_off, worst_t = off, t
        worst_debt = max(worst_debt, debt)
        cpx, carea, frames = cpx + c, carea + a, frames + 1
    char_frac = cpx / max(carea, 1)
    return (_palette_verdict(worst_off, worst_debt, char_frac, f" (peor frame t={worst_t:.1f}s)"),
            {"frames": frames, "off_palette_max": round(worst_off, 6), "debt_max": round(worst_debt, 4),
             "char_color_fraction": round(char_frac, 6)})


def check_palette_image(png: Path, char_boxes: list[dict], tol: float = 6.0) -> tuple[list[str], dict]:
    """Barrido de un frame sin pérdida (remotion still): la verdad del diseño,
    sin artefactos del códec, con tolerancia estrecha."""
    from PIL import Image

    img = np.asarray(Image.open(png).convert("RGB"))
    off, debt, c, a = _palette_frame(img, char_boxes, 1, tol)
    return (_palette_verdict(off, debt, c / max(a, 1), f" ({png.name})"),
            {"off_palette": round(off, 6), "debt": round(debt, 4), "char_color_fraction": round(c / max(a, 1), 6)})


def check_safe_zone(video: Path, fps: float = 6, dark: int = 120) -> tuple[list[str], dict]:
    x0, y0, x1, y1 = (v // 2 for v in SAFE)
    worst = 0.0
    for _, img in _frames(video, fps):
        lum = img.mean(axis=2)
        mask = np.ones(lum.shape, bool)
        mask[y0:y1, x0:x1] = False
        worst = max(worst, float((lum[mask] < dark).mean()))
    fails = [f"texto/trazo fuera de la zona segura: {worst:.3%}"] if worst > 0.0005 else []
    return fails, {"dark_outside_safe_max": round(worst, 6)}


def _norm(w: str) -> str:
    w = unicodedata.normalize("NFKD", w.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9$]", "", w)


def check_whisper(video: Path, pages: list[dict], model_size: str = "small",
                  min_page: float = 0.75, window_ms: int = 250) -> tuple[list[str], dict]:
    """Transcribe el MP4 renderizado (el clip exacto, no la voz bruta)."""
    from kx_captions import from_whisper

    ref = [(pi, tok) for pi, p in enumerate(pages) for tok in p["tokens"]]
    rw = [_norm(tok["text"]) for _, tok in ref]
    vocab = set(rw)
    heard = []  # Whisper parte compuestos ("sobre giro"): se reúnen si así existen en el guion
    for c in from_whisper(video, model_size):
        prev = heard[-1] if heard else None
        if prev and _norm(prev["text"]) not in vocab and _norm(prev["text"] + c["text"]) in vocab:
            heard[-1] = {**prev, "text": prev["text"].strip() + c["text"].strip(), "endMs": c["endMs"]}
        else:
            heard.append(c)
    hw = [_norm(c["text"]) for c in heard]
    sm = difflib.SequenceMatcher(a=rw, b=hw, autojunk=False)
    match = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            match[blk.a + k] = blk.b + k
    fails, per_page, drifts = [], [], []
    for pi, p in enumerate(pages):
        idx = [i for i, (q, _) in enumerate(ref) if q == pi]
        ok = 0
        for i in idx:
            j = match.get(i)
            if j is None:
                continue
            mid = (heard[j]["startMs"] + heard[j]["endMs"]) / 2
            if p["startMs"] - window_ms <= mid <= p["endMs"] + window_ms:
                ok += 1
                drifts.append(abs(heard[j]["startMs"] - ref[i][1]["fromMs"]))
        frac = ok / max(len(idx), 1)
        per_page.append({"page": p["text"], "ms": [p["startMs"], p["endMs"]], "confirmed": round(frac, 2)})
        if frac < min_page:
            fails.append(f"página no confirmada por Whisper ({frac:.0%}): «{p['text']}»")
    d = np.array(drifts) if drifts else np.array([0])
    return fails, {"heard": " ".join(c["text"].strip() for c in heard), "pages": per_page,
                   "word_drift_ms_median": int(np.median(d)), "word_drift_ms_p90": int(np.percentile(d, 90))}


def contact_sheet(video: Path, dst: Path, n: int = 12, cols: int = 6, thumb_w: int = 270) -> Path:
    from PIL import Image, ImageDraw

    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "csv=p=0", str(video)], capture_output=True, text=True, timeout=60).stdout)
    th = thumb_w * H // W
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (th + 28)), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    s = thumb_w / W
    for i in range(n):
        t = dur * (i + 0.5) / n
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                              "-vf", f"scale={thumb_w}:{th}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, timeout=60).stdout
        im = Image.frombytes("RGB", (thumb_w, th), raw)
        x, y = (i % cols) * thumb_w, (i // cols) * (th + 28)
        sheet.paste(im, (x, y))
        draw.rectangle([x + SAFE[0] * s, y + SAFE[1] * s, x + SAFE[2] * s, y + SAFE[3] * s], outline=(0, 200, 255))
        draw.text((x + 6, y + th + 6), f"t={t:.1f}s", fill=(230, 230, 230))
    sheet.save(dst)
    return dst


def save_report(path: Path, report: dict) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
