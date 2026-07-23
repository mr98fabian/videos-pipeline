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


def cached_cutout(src: Path) -> Path:
    """Recorte rembg de `src`, cacheado por hash del contenido. La primera vez
    corre rembg (lento); despues es una copia instantanea. Devuelve la ruta del
    PNG recortado dentro del cache."""
    src = Path(src)
    key = _sha1(src)
    out = CUTOUTS_DIR / f"{key}.png"
    if out.exists():
        return out
    from rembg import remove  # import perezoso: solo paga el arranque si hace falta
    out.write_bytes(remove(src.read_bytes()))
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
