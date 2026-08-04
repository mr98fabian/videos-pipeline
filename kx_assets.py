"""Biblioteca de FONDOS reusables del canal KoreX — pedido usuario 3 ago 2026:
"que el fondo y los personajes se generen por separado y se guarde un cache de
cada cosa para no generarlo dos veces".

POR QUE UN CACHE POR CLAVE Y NO POR HASH DE ARCHIVO:
visual_cache.py cachea assets DERIVADOS (recorte rembg de una imagen que ya
existe) y por eso puede usar el sha1 del archivo fuente. Aca el asset todavia no
existe: lo que se cachea es una GENERACION. La clave tiene que ser semantica
("bolsa", "fabrica_textil") para que dos videos distintos que mencionen la bolsa
compartan literalmente el mismo escenario -- que es justo lo que hace que el
canal se lea como un mundo y no como imagenes sueltas de IA (regla 1 de
korex_engine.py).

Consecuencia buscada: el set de un video nuevo cuesta 0 llamadas de API salvo
que introduzca un escenario que nunca se uso.

Los fondos van SIN personaje y SIN texto: el personaje se compone encima como
placa troquelada (ch_*.png), separado, tal cual se pidio.

Uso desde un guion: cada escena declara una clave en "set_terms". Las claves
libres se generan la primera vez y quedan en assets/kx_sets/.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SETS_DIR = ROOT / "assets" / "kx_sets"
MANIFEST = SETS_DIR / "sets.json"

# Estilo del escenario. Se fija aca y no en el guion por la misma razon que
# HIDDENFACTS_STYLE vive en pipeline.py: si el estilo lo decide el guion, deriva
# entre videos y el mundo deja de ser el mismo.
SET_STYLE = (
    "Flat vector 1930s rubber-hose cartoon background art (early Disney/Fleischer "
    "style), black and white with soft grey wash and vintage film grain, thick "
    "confident ink outlines, simple geometric shapes, gentle vignette"
)
_SET_RULES = (
    "EMPTY STAGE: absolutely no characters, no people, no animals, no text, no "
    "letters, no numbers, no logos anywhere in the image. Composition must leave "
    "the CENTER and LOWER-CENTER of the frame clear and uncluttered, because a "
    "character will be composited on top of it later. Vertical 9:16 framing, "
    "the floor line sits around three quarters down the frame."
)

# Escenarios de arranque del canal. No es una lista cerrada: una clave nueva en
# un guion se genera y se suma sola.
BUILTIN_SETS = {
    "cuarto": "a plain modest room with a bare wooden table and a single hanging lamp",
    "bolsa": "a stock exchange trading floor with tall quote boards and ticker screens far in the background",
    "oficina_prestigio": "an elegant executive office with framed diplomas and award plaques on the wall",
    "banco": "a dim old bank interior with tall shelves of ledger books and a marble counter",
    "empeno": "a pawn shop counter with a barred window and shelves of assorted objects behind it",
    "fabrica_textil": "an old textile mill interior with looms and stacked rolls of cloth",
    "calendario": "a cramped office wall with a paper wall calendar and stacks of invoices on a desk",
    "casa": "a simple living room with a couch, a small table and a window",
}


def _slug(key: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", (key or "").strip().lower()).strip("_")


def _load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def path_for(key: str) -> Path:
    return SETS_DIR / f"{_slug(key)}.png"


def get_set(key: str, description: str = "") -> Path | None:
    """Devuelve el fondo de esa clave, generandolo solo la primera vez.

    description: que se ve en el escenario. Solo hace falta para una clave nueva;
    para las de BUILTIN_SETS se ignora. Devuelve None si no hay forma de
    generarlo (sin API key), para que el motor caiga al set dibujado en SVG.
    """
    key = _slug(key)
    if not key:
        return None
    dest = path_for(key)
    if dest.exists():
        return dest

    desc = description.strip() or BUILTIN_SETS.get(key, "")
    if not desc:
        print(f"[kx_assets] set '{key}' sin descripcion y no esta en BUILTIN_SETS")
        return None

    sys.path.insert(0, str(ROOT))
    import pipeline as pl

    # Los escenarios son el mejor caso para el generador LOCAL: van sin personaje,
    # asi que no sufren la falta de consistencia de FLUX schnell (ver comfy_client).
    api_key = pl.os.environ.get("PIAPI_API_KEY", "")
    if api_key:
        gen = lambda pr, ds: pl._seedream_generate_image(pr, ds, api_key, style_directive=SET_STYLE)
    else:
        import comfy_client
        gen = lambda pr, ds: comfy_client.generate_image(pr, ds, style_directive=SET_STYLE)

    SETS_DIR.mkdir(parents=True, exist_ok=True)
    prompt = f"{desc}. {_SET_RULES}"
    print(f"[kx_assets] generando set '{key}' (una sola vez en la vida)...")
    ok = gen(prompt, dest)
    if not ok or not dest.exists():
        print(f"[kx_assets] fallo la generacion del set '{key}'")
        return None

    man = _load_manifest()
    man[key] = {"prompt": prompt, "style": SET_STYLE}
    pl._atomic_write_json(MANIFEST, man)
    return dest


def resolve_scene_sets(data: dict, n_scenes: int) -> list[Path | None]:
    """Traduce los set_terms del guion a fondos cacheados, uno por escena.

    Un guion sin set_terms devuelve None en todas: el motor sigue usando su set
    dibujado, asi que los guiones viejos no se rompen.
    """
    terms = data.get("set_terms") or []
    if not terms:
        return [None] * n_scenes
    out: list[Path | None] = []
    seen: dict[str, Path | None] = {}
    for i in range(n_scenes):
        key = _slug(terms[i]) if i < len(terms) else ""
        if key not in seen:
            seen[key] = get_set(key) if key else None
        out.append(seen[key])
    return out
