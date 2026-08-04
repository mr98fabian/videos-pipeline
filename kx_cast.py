"""Biblioteca de POSES del reparto de KOREX — la otra mitad del pedido del 3 ago
2026 ("que el fondo y los personajes se generen por separado y se guarde un cache
de cada cosa"). Los fondos viven en kx_assets.py; los personajes, aca.

POR QUE ESTO Y NO IP-ADAPTER / LORA / REDUX (decision 4 ago 2026):
el problema a resolver era la consistencia de Tadeo entre escenas, y la respuesta
obvia era condicionar la generacion con una imagen de referencia. Se descarto:
  - FLUX Redux y FLUX.1-dev son licencia NON-COMMERCIAL, inservibles para un canal
    monetizado (mismo criterio que dejo fuera a XTTS-v2 en la voz).
  - SDXL + IP-Adapter costaba ~10GB mas de pesos y da un personaje PARECIDO en
    cada escena, no el mismo.
El motor KoreX ya compone al personaje como RECORTE sobre el set, asi que la
consistencia perfecta sale gratis reusando el mismo archivo: si la pose 'grito'
es siempre el mismo PNG, Tadeo es identico por construccion. Es como funciona la
animacion de recortes de verdad (South Park, Monty Python), no un atajo.

Consecuencia: una pose nueva se genera UNA vez en la vida y a partir de ahi todos
los videos del canal cuestan cero llamadas de imagen para el personaje.

Estructura: assets/kx_cast/<personaje>/<pose>.png (con alfa ya recortado).
El guion referencia "tadeo/grito" en character_terms; si esa pose no existe, se
genera a partir de la hoja canonica del personaje y queda cacheada.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAST_DIR = ROOT / "assets" / "kx_cast"
CHARACTERS_DIR = ROOT / "assets" / "characters"
MANIFEST = CAST_DIR / "cast.json"

# Vocabulario de poses. Un motor de recortes no necesita cientos: necesita las
# que la narracion realmente usa, y que se repitan es parte del lenguaje visual.
POSES = {
    "grito": "screaming directly at the camera, both arms up, intense eye contact, extreme close-up of the face",
    "orgulloso": "standing proud, chest out, hands on hips, smug clown-like grin",
    "confundido": "shrugging with both palms up, eyebrows raised, puzzled expression",
    "estafado": "slumped shoulders, comic teary eyes, mouth open in disbelief",
    "senalando": "pointing forward at something off-frame with one arm fully extended",
    "decidido": "fist slammed down, leaning forward, determined frown",
    "triunfo": "arms crossed, satisfied smirk, chin slightly raised",
    "codicia": "holding a stack of bills with both hands, greedy wide-eyed grin",
    "asombro": "both hands on cheeks, mouth wide open in naive amazement",
    "picaro": "winking at the camera, one eyebrow raised, sly half-smile",
}

# Estilo del reparto. Igual que SET_STYLE en kx_assets: vive en el codigo, no en
# el guion, para que el personaje no derive de un video a otro.
CAST_STYLE = (
    "Flat vector 1930s rubber-hose cartoon character (early Disney/Fleischer style), "
    "black and white with soft grey wash, thick confident ink outlines, white "
    "four-fingered gloves, simple geometric construction"
)
_CAST_RULES = (
    "FULL BODY unless the pose says close-up, centered, facing the camera, on a "
    "PLAIN SOLID WHITE background with no floor, no shadow, no props beyond the "
    "ones named, no text, no letters, no numbers. The character must be fully "
    "inside the frame with clear margin on every side."
)


def _slug(v: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", (v or "").strip().lower()).strip("_")


def _load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _canonical_sheet(character: str) -> Path | None:
    """Hoja de personaje ya existente en assets/characters/<slug>/, que es la que
    define la identidad. Se usa como referencia cuando el generador la acepta."""
    d = CHARACTERS_DIR / _slug(character).replace("_", "-")
    if not d.is_dir():
        return None
    sheets = sorted(d.glob("default_*.png")) or sorted(d.glob("*.png"))
    return sheets[0] if sheets else None


def path_for(character: str, pose: str) -> Path:
    return CAST_DIR / _slug(character) / f"{_slug(pose)}.png"


def variants(character: str, pose: str) -> list[Path]:
    """Todos los dibujos disponibles de esa pose: <pose>.png y <pose>_N.png.

    Tener varias versiones de la MISMA pose es lo que evita el efecto de figura
    congelada: el personaje sigue siendo identico (mismo modelo, mismo estilo)
    pero no es literalmente el mismo pixel dos escenas seguidas.
    """
    d = CAST_DIR / _slug(character)
    if not d.is_dir():
        return []
    p, base = _slug(pose), []
    single = d / f"{p}.png"
    if single.exists():
        base.append(single)
    base += sorted(d.glob(f"{p}_*.png"), key=lambda f: f.name)
    return base


def pick(character: str, pose: str, index: int = 0) -> Path | None:
    """Elige una variante de forma DETERMINISTA por indice de escena: el mismo
    guion produce siempre el mismo video (si fuera aleatorio, dos renders del
    mismo material no se podrian comparar en un A/B)."""
    vs = variants(character, pose)
    if not vs:
        return None
    return vs[index % len(vs)]


def get_pose(character: str, pose: str, description: str = "") -> Path | None:
    """Devuelve la pose cacheada, generandola solo la primera vez.

    El PNG se guarda con el fondo ya recortado (alfa real), porque el motor lo
    compone como sticker troquelado sobre el set y recortar en cada render seria
    pagar rembg mil veces por el mismo resultado.
    """
    character, pose = _slug(character), _slug(pose)
    if not character or not pose:
        return None
    dest = path_for(character, pose)
    if dest.exists():
        return dest

    desc = description.strip() or POSES.get(pose, "")
    if not desc:
        print(f"[kx_cast] pose '{pose}' sin descripcion y no esta en POSES")
        return None

    sys.path.insert(0, str(ROOT))
    import pipeline as pl

    sheet = _canonical_sheet(character)
    prompt = (f"A single cartoon character: {character.capitalize()}, {desc}. "
              f"{_CAST_RULES}")

    piapi = pl.os.environ.get("PIAPI_API_KEY", "")
    if piapi and sheet:
        # con referencia: mantiene la identidad ya establecida del personaje
        gen = lambda: pl._seedream_generate_image(prompt, dest, piapi,
                                                   reference_image=sheet,
                                                   style_directive=CAST_STYLE)
    elif piapi:
        gen = lambda: pl._seedream_generate_image(prompt, dest, piapi,
                                                   style_directive=CAST_STYLE)
    else:
        import comfy_client
        gen = lambda: comfy_client.generate_image(prompt, dest,
                                                   style_directive=CAST_STYLE)

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[kx_cast] generando pose '{character}/{pose}' (una sola vez en la vida)...")
    if not gen() or not dest.exists():
        print(f"[kx_cast] fallo la generacion de '{character}/{pose}'")
        return None

    # recorte a alfa real, una sola vez, sobre el archivo cacheado
    try:
        from visual_cache import plate_cutout
        cut = plate_cutout(dest)
        if cut and Path(cut).exists():
            import shutil
            shutil.copyfile(cut, dest)
    except Exception as e:
        print(f"[kx_cast] recorte omitido ({type(e).__name__}: {e})")

    man = _load_manifest()
    man.setdefault(character, {})[pose] = {"prompt": prompt, "style": CAST_STYLE}
    pl._atomic_write_json(MANIFEST, man)
    return dest


def adopt(character: str, pose: str, source: Path) -> Path | None:
    """Registra una imagen YA generada como la pose canonica del personaje.

    Sirve para sembrar la biblioteca con las placas buenas que ya existen en
    output/*/clips/ch_*.png en vez de volver a generarlas.
    """
    dest = path_for(character, pose)
    source = Path(source)
    if not source.exists():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copyfile(source, dest)
    # se recorta aca y no en cada render: el alfa es deterministico
    try:
        from visual_cache import plate_cutout
        cut = plate_cutout(dest)
        if cut and Path(cut).exists():
            shutil.copyfile(cut, dest)
    except Exception as e:
        print(f"[kx_cast] recorte omitido ({type(e).__name__}: {e})")
    man = _load_manifest()
    man.setdefault(_slug(character), {})[_slug(pose)] = {"adopted_from": str(source)}
    sys.path.insert(0, str(ROOT))
    import pipeline as pl
    pl._atomic_write_json(MANIFEST, man)
    return dest


def resolve_scene_cast(data: dict, n_scenes: int) -> list[Path | None]:
    """Traduce los character_terms del guion a poses cacheadas, una por escena.

    Formato aceptado: "tadeo/grito" (personaje/pose). Un character_term vacio
    sigue significando "esta escena NO lleva personaje", igual que en el motor.
    Cualquier otro formato devuelve None, para que el pipeline caiga al camino
    de siempre (generar la placa dentro del video) sin romperse.
    """
    terms = data.get("character_terms") or []
    out: list[Path | None] = []
    for i in range(n_scenes):
        t = (terms[i] if i < len(terms) else "") or ""
        if "/" not in t:
            out.append(None)
            continue
        char, _, pose = t.partition("/")
        # ya en biblioteca (con o sin variantes) -> gratis; si no, se genera
        out.append(pick(char, pose, i) or get_pose(char, pose))
    return out
