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


# AMBIENTE POR DEFECTO (27 jul 2026). La deteccion por palabra clave solo
# acertaba 1 de 17 frases en un guion real: casi todo el video quedaba sin
# footage. Estas tres categorias son atmosfericas -- no representan nada
# concreto, asi que valen para CUALQUIER escena y aportan movimiento continuo,
# que es lo que retiene. Van a opacidad baja (AMBIENT_OPACITY): a 0,85 tapan
# el recorte y ensucian el papel.
# Solo humo y niebla: son las dos categorias con cobertura real medida (59-75%
# y 44%). El polvo del catalogo se queda en 1,9% -- correcto para el efecto en
# si, pero como textura de fondo no se ve, y el pedido era que cada escena
# tuviera movimiento visible.
AMBIENT = ("smoke", "fog")
AMBIENT_OPACITY = 0.45
MATCH_OPACITY = 0.85


def ambient_effect(index: int) -> str:
    """Categoria atmosferica para una escena sin match literal. Rota por indice
    para que dos escenas seguidas no lleven exactamente la misma textura."""
    return AMBIENT[index % len(AMBIENT)]


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
    import urllib.parse as _uparse
    q = _uparse.quote(EFFECTS[category]["query"])
    url = f"https://pixabay.com/api/videos/?key={key}&q={q}&per_page={count * 2}"
    # Pixabay bloquea el User-Agent por defecto de urllib con 403
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
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
        vreq = urllib.request.Request(vid["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(vreq, timeout=60) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        got.append(dest)
    return got


def _pix_fmt(path: Path) -> str:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def is_greenscreen(src: Path, min_ratio: float = 0.25) -> bool:
    """True si el clip ES realmente greenscreen. La query de Pixabay
    ("fire green screen") devuelve tambien footage normal sin fondo verde:
    esos NO se pueden cachear, porque al componerlos se ve el clip entero
    en vez del efecto recortado. Mide el area verde de un fotograma del
    medio con el mismo umbral que usa el chromakey."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "probe.png"
        # el frame 0 suele ser negro/fundido: se muestrea al 40% del clip
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(src),
             "-vf", "select=eq(n\\,25),scale=160:-1", "-frames:v", "1", str(png)],
            capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not png.exists():
            return False
        from PIL import Image
        im = Image.open(png).convert("RGB")
        px = list(im.getdata())
        green = sum(1 for (r_, g_, b_) in px if g_ > 90 and g_ > r_ * 1.5 and g_ > b_ * 1.5)
        return (green / max(len(px), 1)) >= min_ratio


# Duracion util de un efecto: se recorta a esto para no cargar 30s de clip por
# una escena de 6s. ProRes es pesado por segundo, no por resolucion.
FX_SECONDS = 6
FX_WIDTH = 1080

# ELEMENTO CLARO SOBRE PAPEL CLARO (27 jul 2026). Humo, polvo, niebla, lluvia
# y nieve son BLANCOS (luminancia medida ~175/255). El motor los componia con
# screen/lighten sobre las tarjetas de papel casi blanco del tablero, y
# max(claro, claro) = claro: invisibles. Se invierte el RGB conservando el
# alpha (filtro `negate`, que por defecto NO toca el canal alfa) y se componen
# con multiply -> se leen como sombra/humo sucio sobre el papel, que ademas es
# el lenguaje sepia del canal. Es el mismo error que las transiciones v1.
DARK_ON_PAPER = ("smoke", "dust", "fog", "rain", "snow")

# BANDA de cobertura valida, no un minimo. El fallo de la primera version fue
# tratar esto como "cuanto mas mejor":
#   - cobertura ~0%   -> similarity demasiado alta, el chromakey borro el clip
#                        entero (le paso a polvo, lluvia y niebla a 0.30)
#   - cobertura ~100% -> similarity demasiado baja, el verde SIGUE ahi y lo que
#                        se compone es el rectangulo entero (lluvia y nieve
#                        pasaron el filtro asi, con el fondo verde intacto)
# Una lluvia real son rayas finas: 1-3% de cobertura es CORRECTO, no un fallo.
MIN_COVERAGE = 0.004
MAX_COVERAGE = 0.80
# Ascendente: mas similarity = mas verde eliminado. Se sube hasta que el fondo
# se va PERO el elemento sobrevive, y se para en el primero que cae en banda.
_SIMILARITIES = (0.10, 0.14, 0.18, 0.22, 0.26, 0.32)


def alpha_coverage(mov: Path) -> float:
    """Fraccion del fotograma con alpha util, medida como el MAXIMO de tres
    fotogramas: en un solo frame un efecto intermitente (rayo, chispa) puede
    salir vacio y parecer un keyeo roto. Es la unica forma de saber si el
    chromakey dejo algo -- FFmpeg no da error cuando borra el clip entero."""
    import tempfile
    from PIL import Image
    best = 0.0
    with tempfile.TemporaryDirectory() as td:
        for n in (10, 40, 80):
            png = Path(td) / f"a{n}.png"
            r = subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", str(mov),
                 "-vf", f"select=eq(n\\,{n}),scale=200:-1", "-frames:v", "1", str(png)],
                capture_output=True, text=True, timeout=120)
            if r.returncode != 0 or not png.exists():
                continue
            px = list(Image.open(png).convert("RGBA").getdata())
            best = max(best, sum(1 for p in px if p[3] > 40) / max(len(px), 1))
    return best


def chromakey_to_alpha(src: Path, color: str = "0x00FF00",
                       similarity: float | None = None) -> Path:
    """Quita el verde con FFmpeg y guarda un .mov ProRes 4444 con ALPHA REAL,
    reusable en cualquier composicion. Se hace UNA vez por clip y se cachea.

    POR QUE ProRes y no WebM (27 jul 2026): en este build de FFmpeg (8.0.1
    gyan) tanto libvpx-vp9 como libvpx anuncian yuva420p entre sus formatos
    pero escriben yuv420p SIN error -- ni -auto-alt-ref 0 ni el metadato
    alpha_mode lo evitan. Los 30 clips de la biblioteca quedaron sin canal
    alfa y el motor compuso el rectangulo verde crudo sobre cada escena.
    ProRes 4444 es el unico codec de esta instalacion que conserva el alfa;
    a 6s / 1080 de ancho sale ~5 MB por clip, ~130 MB la biblioteca entera.
    El pix_fmt se VERIFICA despues de codificar: confiar en el flag es
    exactamente lo que fallo."""
    dst = src.with_name(src.stem.replace("raw_", "alpha_") + ".mov")
    if dst.exists() and _pix_fmt(dst).startswith("yuva"):
        cov = alpha_coverage(dst)
        if MIN_COVERAGE <= cov <= MAX_COVERAGE:
            return dst
    # el RGB se invierte ANTES de convertir a yuva: `negate` sin un formato con
    # alpha explicito puede negociar uno sin canal alfa y devolverlo opaco
    # hue=s=0 despues del negate: invertir un humo BLANCO da azul, y el azul
    # rompe la paleta sepia del canal (visible en el render del 27 jul).
    # Desaturado queda gris neutro, y multiply sobre el papel crema lo tine
    # solo con el color del papel -- que es justo el look de archivo.
    negate = ",format=rgba,negate,hue=s=0" if src.parent.name in DARK_ON_PAPER else ""
    cands = _SIMILARITIES if similarity is None else (similarity,) + _SIMILARITIES
    last = "sin candidatos"
    for sim in cands:
        cmd = [
            "ffmpeg", "-y", "-t", str(FX_SECONDS), "-i", str(src),
            "-vf", (f"scale={FX_WIDTH}:-2,chromakey={color}:{sim}:0.12,"
                    f"despill{negate},format=yuva444p10le"),
            "-c:v", "prores_ks", "-profile:v", "4444", "-qscale:v", "18",
            "-pix_fmt", "yuva444p10le", "-an", str(dst),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            last = f"ffmpeg fallo: {r.stderr[-300:]}"
            continue
        got = _pix_fmt(dst)
        if not got.startswith("yuva"):
            last = f"perdio el alpha (pix_fmt={got})"
            continue
        cov = alpha_coverage(dst)
        if cov > MAX_COVERAGE:
            last = f"el verde sigue ahi (cobertura {cov * 100:.0f}% con similarity {sim})"
            continue          # subir similarity: falta quitar fondo
        if cov < MIN_COVERAGE:
            last = f"clip borrado por el key (cobertura {cov * 100:.1f}% con similarity {sim})"
            break             # ya se paso: subir mas solo borra mas
        return dst
    dst.unlink(missing_ok=True)
    raise RuntimeError(f"{src.parent.name}/{src.name}: {last}")


def pick_effect_clip(category: str) -> Path | None:
    """Un clip ya listo (alpha) de una categoria, o None si la biblioteca esta
    vacia para esa categoria (sin API key o sin haberla poblado aun)."""
    import random
    out_dir = EFFECTS_DIR / category
    clips = sorted(out_dir.glob("alpha_*.mov"))
    return random.choice(clips) if clips else None
