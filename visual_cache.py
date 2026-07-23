"""Cache de assets visuales derivados para el motor "Archivo Vivo" — pedido
usuario 23 jul 2026: no recalcular/regenerar lo que ya se hizo una vez.

Que se cachea y por que:
  - RECORTES rembg (assets/cache/cutouts/<sha1>.png): rembg tarda segundos por
    imagen y el resultado es deterministico -> clave = hash del archivo fuente.
    Un recorte se calcula UNA vez en la vida, aunque el video se re-renderice
    cien veces.
  - MAPAS por pais (assets/cache/maps/): el scrap de mapa de un pais es el
    mismo en todos los videos -> se genera/descarga una vez y se reusa.
  - TEXTURAS (assets/cache/textures/): pergamino, cinta, grano — estaticas.

Los stickers ya tienen su propio cache (assets/stickers/, 112 generados) y las
hojas de personaje tambien (ver _get_character_sheet en pipeline.py). Este
modulo completa el resto.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "assets" / "cache"
CUTOUTS_DIR = CACHE_DIR / "cutouts"
MAPS_DIR = CACHE_DIR / "maps"
TEXTURES_DIR = CACHE_DIR / "textures"

for d in (CUTOUTS_DIR, MAPS_DIR, TEXTURES_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# Modelo de segmentacion. BiRefNet (SOTA 2024) recorta bordes limpios y captura
# el cuerpo completo -> menos "cabezas flotantes" y sin el halo amarillo de u2net
# (comparado con datos reales 23 jul 2026). CPU-only tarda ~30-60s/imagen, pero el
# recorte se cachea de por vida, asi que solo se paga una vez. Override: REMBG_MODEL.
import os

REMBG_MODEL = os.environ.get("REMBG_MODEL", "birefnet-general")
_SESSIONS: dict = {}


def _session(model: str):
    """Sesion rembg reusada (crearla es caro; una por modelo por proceso)."""
    if model not in _SESSIONS:
        from rembg import new_session
        _SESSIONS[model] = new_session(model)
    return _SESSIONS[model]


def _clean_alpha(png_bytes: bytes) -> bytes:
    """Limpia el borde del recorte: erosiona 1px el canal alfa (mata el halo de
    pixeles semitransparentes claros) y lo suaviza levemente para anti-alias.
    Es lo que hace que el troquelado blanco del motor se asiente limpio."""
    import io
    from PIL import Image, ImageFilter
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    a = im.getchannel("A")
    a = a.filter(ImageFilter.MinFilter(3))       # erosion 1px: quita la franja fantasma
    a = a.filter(ImageFilter.GaussianBlur(0.6))  # anti-alias suave del nuevo borde
    im.putalpha(a)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def cached_cutout(src: Path, model: str | None = None) -> Path:
    """Recorte rembg de `src`, cacheado por (hash del contenido + modelo). La
    primera vez corre rembg (lento) y limpia el alfa; despues es copia instantanea.
    El modelo entra en la clave para que cambiarlo regenere sin pisar lo viejo."""
    src = Path(src)
    model = model or REMBG_MODEL
    key = _sha1(src)
    out = CUTOUTS_DIR / f"{key}.{model}.png"
    if out.exists():
        return out
    from rembg import remove  # import perezoso: solo paga el arranque si hace falta
    raw = remove(src.read_bytes(), session=_session(model))
    try:
        raw = _clean_alpha(raw)
    except Exception:
        pass  # si PIL falla por lo que sea, mejor el recorte crudo que ningun recorte
    out.write_bytes(raw)
    return out


COVERAGE_THRESHOLD = 0.08  # medido 23 jul 2026: cara valida=0.16, grupo roto=0.02


def cutout_coverage(cutout_path: Path) -> float:
    """Fraccion (0..1) de pixeles no-transparentes del recorte. Decide el
    tratamiento de escena del motor visual: cobertura > COVERAGE_THRESHOLD =
    recorte utilizable -> sticker troquelado; por debajo = rembg fallo (plano
    ancho/grupo) -> la escena entra como foto de archivo clavada. Umbral
    calibrado con datos reales del proof (23 jul 2026)."""
    from PIL import Image
    im = Image.open(cutout_path).convert("RGBA")
    alpha = im.getchannel("A").tobytes()
    # muestreo cada 4 bytes: suficiente para la decision, 4x mas rapido
    sample = alpha[::4]
    opaque = sum(1 for a in sample if a > 40)
    return opaque / (len(sample) or 1)
