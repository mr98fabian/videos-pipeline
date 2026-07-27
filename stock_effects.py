"""Biblioteca de efectos stock en greenscreen (fuego, agua, humo, etc.) para
compositar detras/delante de los recortes troquelados del motor Archivo Vivo.

Referencia (26 jul 2026): video "Vox-style explainer" que compone stock real de
greenscreen (oceano, fuego) detras de cutouts recortados, en vez de generar el
efecto con IA -- el resultado se ve mucho mas real porque ES footage real.

Flujo:
  1. fetch_effect(categoria) descarga UNA vez de Pixabay (API oficial, requiere
     PIXABAY_API_KEY, gratis, sin atribucion, uso comercial permitido) y cachea
     en assets/cache/effects/<categoria>/.
  2. chromakey_to_alpha() quita el verde con FFmpeg y deja un webm con alpha real.
  3. detect_effect(narracion) mapea el verbo narrado a una categoria, mismo
     patron que _ACTION_KW en archivo_engine.py, para que el motor pueda meter
     un efecto por escena SIN que el guion lo pida a mano -- el pedido es que
     haya animacion en cada escena para sostener la atencion.

NO incluye descargas: sin PIXABAY_API_KEY no hay biblioteca. Bajar clips a mano
de un sitio y automatizar el scraping del boton de descarga rompe los terminos
de la mayoria de estos bancos (Videezy/Vecteezy no tienen API publica gratis).
Pixabay si la tiene, por eso es la fuente elegida.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EFFECTS_DIR = ROOT / "assets" / "cache" / "effects"
EFFECTS_DIR.mkdir(parents=True, exist_ok=True)

# Categorias del catalogo, con las queries de busqueda en Pixabay y el patron
# de deteccion automatica sobre la narracion (mismo estilo que _ACTION_KW).
# Elegidas para el nicho de HiddenFacts (WWII/espionaje/historia): fuego,
# explosion y humo ya los cubre la capa de accion existente con FX dibujado;
# esto los reemplaza por footage REAL cuando hay clip cacheado.
EFFECTS = {
    "fire":      {"query": "fire green screen", "kw": r"burn|fire|flame|ablaze|torch"},
    "water":     {"query": "ocean waves green screen", "kw": r"\bsea\b|ocean|harbor|wave|flood|drown|underwater"},
    "smoke":     {"query": "smoke green screen", "kw": r"\bsmoke\b|smoulder|smoke-filled|haze"},
    "explosion": {"query": "explosion green screen", "kw": r"explod|explos|detonat|blast|erupt"},
    "rain":      {"query": "rain green screen", "kw": r"\brain\b|storm|downpour|thunderstorm"},
    "lightning": {"query": "lightning green screen", "kw": r"lightning|thunderbolt|struck by lightning"},
    "snow":      {"query": "snow falling green screen", "kw": r"\bsnow\b|blizzard|frost|freezing"},
    "sparks":    {"query": "sparks green screen", "kw": r"\bspark|ember|gunfire flash|muzzle flash"},
    "fog":       {"query": "fog mist green screen", "kw": r"\bfog\b|\bmist\b|foggy"},
    "dust":      {"query": "dust storm green screen", "kw": r"\bdust\b|sandstorm|debris cloud"},
}


def detect_effect(narration: str) -> str | None:
    """Verbo/sustantivo narrado -> categoria de efecto, o None. Mismo patron que
    _detect_action en archivo_engine.py: la deteccion es SOLO sobre lo que se
    dice, nunca sobre los search_terms (que traen ruido de encuadre)."""
    t = narration.lower()
    for cat, spec in EFFECTS.items():
        if re.search(spec["kw"], t):
            return cat
    return None


def _pixabay_key() -> str:
    k = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not k:
        raise RuntimeError(
            "falta PIXABAY_API_KEY -- registro gratis en pixabay.com/api/docs/ "
            "(uso comercial permitido, sin atribucion). Sin esto no se puede "
            "poblar la biblioteca: los bancos alternativos (Videezy/Vecteezy) "
            "no tienen API publica y automatizar su boton de descarga rompe "
            "sus terminos de uso."
        )
    return k


def fetch_effect(category: str, count: int = 3) -> list[Path]:
    """Descarga hasta `count` clips greenscreen de una categoria y los cachea
    de por vida. Idempotente: si ya hay clips cacheados, no vuelve a pedir."""
    import json
    import urllib.request

    if category not in EFFECTS:
        raise ValueError(f"categoria desconocida: {category} (opciones: {list(EFFECTS)})")
    out_dir = EFFECTS_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(out_dir.glob("raw_*.mp4"))
    if len(existing) >= count:
        return existing[:count]

    key = _pixabay_key()
    q = urllib.parse.quote(EFFECTS[category]["query"])
    url = f"https://pixabay.com/api/videos/?key={key}&q={q}&per_page={count * 2}"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    hits = data.get("hits", [])[:count]
    got = []
    for i, hit in enumerate(hits):
        # 'large' suele venir sin fondo verde recortado; pedimos el mayor
        # tamano disponible, luego el chromakey lo procesa igual
        vid = hit.get("videos", {}).get("large") or hit.get("videos", {}).get("medium")
        if not vid:
            continue
        dest = out_dir / f"raw_{i}.mp4"
        urllib.request.urlretrieve(vid["url"], dest)
        got.append(dest)
    return got


def chromakey_to_alpha(src: Path, color: str = "0x00FF00", similarity: float = 0.22) -> Path:
    """Quita el verde con FFmpeg y guarda un webm (VP9+alpha) reusable en
    cualquier composicion. Se hace UNA vez por clip fuente y se cachea junto a
    el; el codec con alpha real permite superponerlo sin recortes duros."""
    dst = src.with_name(src.stem.replace("raw_", "alpha_") + ".webm")
    if dst.exists():
        return dst
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf", f"chromakey={color}:{similarity}:0.08,format=yuva420p",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-an",
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"chromakey fallo en {src.name}: {r.stderr[-400:]}")
    return dst


def pick_effect_clip(category: str) -> Path | None:
    """Un clip ya listo (alpha) de una categoria, o None si la biblioteca esta
    vacia para esa categoria (sin API key o sin haberla poblado aun)."""
    import random
    out_dir = EFFECTS_DIR / category
    clips = sorted(out_dir.glob("alpha_*.webm"))
    return random.choice(clips) if clips else None
