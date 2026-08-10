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
import json
import os
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
    a = a.filter(ImageFilter.MinFilter(3))  # erosion 1px: quita la franja fantasma
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


# ============================================================================
# RECORTE DE PLACA (28 jul 2026) — para las imagenes ch_<i>.png, que vienen con
# el personaje solo sobre fondo plano.
#
# rembg/BiRefNet devuelve una SILUETA MACIZA: el contorno exterior sale limpio
# pero los huecos interiores no se vacian. En la placa del general, el espacio
# entre las piernas y bajo los faldones quedaba relleno con un pegote de fondo.
# Eso es lo que se leia como "raro", no el borde.
#
# Contra fondo plano no hace falta una red: el fondo es la region conectada a
# los BORDES del lienzo. Se rellena desde el borde y se corta ahi. Y esa es la
# razon exacta de la pose en A: con brazos y piernas separados, el hueco toca
# el borde y se vacia solo. Con los brazos pegados al cuerpo queda encerrado y
# ni esto lo salva.
#
# OJO, medido y NO teorico (28 jul 2026): con las botas casi juntas el hueco
# ENTRE LAS PIERNAS queda encerrado por el abrigo arriba y las botas abajo, no
# toca ningun borde, y se quedaba relleno de blanco. Por eso la placa pide
# postura abierta con hueco visible entre los pies. Vaciar cualquier region
# interior del color de fondo NO es una alternativa: el pelo cano y los ojos
# son blancos y saldrian agujereados.
# ============================================================================
PLATE_TOL = 34  # distancia al color de fondo que sigue contando como fondo
PLATE_MIN_BG = 0.20  # menos fondo que esto = la imagen no es una placa
PLATE_MAX_BG = 0.96  # mas que esto = se comio al personaje


def plate_cutout(src: Path, tol: int = PLATE_TOL) -> Path | None:
    """Recorta una placa de personaje vaciando el fondo conectado al borde.
    Devuelve None si el resultado no es creible (la imagen no era una placa, o
    el color del personaje se fundio con el fondo y el relleno se lo comio),
    para que el llamante caiga a rembg."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage

    src = Path(src)
    out = CUTOUTS_DIR / f"{_sha1(src)}.plate{tol}.png"
    if out.exists():
        return out

    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    # color de fondo = mediana de las cuatro esquinas (robusto a una esquina sucia)
    corners = np.array([a[0, 0], a[0, -1], a[-1, 0], a[-1, -1]], dtype=np.int16)
    bg = np.median(corners, axis=0)
    near = np.abs(a - bg).max(axis=2) <= tol

    lab, n = ndimage.label(near)
    if n == 0:
        return None
    # etiquetas presentes en cualquier borde -> fondo real; una region interior
    # del mismo color (el pelo blanco del general) NO toca el borde y se queda
    edge = np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])
    keep = np.unique(edge[edge > 0])
    if keep.size == 0:
        return None
    bg_mask = np.isin(lab, keep)

    frac = float(bg_mask.mean())
    if not (PLATE_MIN_BG <= frac <= PLATE_MAX_BG):
        return None

    alpha = np.where(bg_mask, 0, 255).astype(np.uint8)
    # 1px de erosion + suavizado: deja el borde del trazo sin halo del fondo
    alpha = ndimage.grey_erosion(alpha, size=(3, 3))
    alpha = ndimage.gaussian_filter(alpha, sigma=0.6)

    rgba = np.dstack([np.asarray(im), alpha])
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(out)
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


# ============================================================================
# MULTI-RECORTE (pedido usuario 25 jul 2026, "ruta A"): BiRefNet devuelve TODO
# el primer plano en un solo PNG -> personajes y objetos se mueven como una
# plancha y no pueden interactuar. Aqui se parte ese alfa en COMPONENTES CONEXAS
# (cada figura/objeto separado = su propio sticker), conservando donde estaba
# cada uno para que el motor los recoloque y los haga actuar entre si.
# Coste extra: ~0 (opera sobre el recorte ya cacheado) y el resultado se cachea.
# ============================================================================

PART_WORK = 220  # resolucion de trabajo del etiquetado (rapido y estable)
PART_MIN_AREA = 0.010  # <1% del lienzo = mota/ruido, no un sujeto
PART_MAX = 5  # tope pedido por el usuario (2..5 stickers por escena)
PART_DOMINANT = 0.88  # si una pieza se lleva casi todo, no hay nada que separar


def _components(mask: list[bool], w: int, h: int) -> list[int]:
    """Etiquetado de componentes conexas (8-vecinos, dos pasadas + union-find).
    Sin scipy a proposito: la mascara viene reducida a ~220px, con python puro
    sobra y el motor no gana una dependencia nueva."""
    parent = [0]

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    lab = [0] * (w * h)
    nxt = 1
    for y in range(h):
        base = y * w
        for x in range(w):
            i = base + x
            if not mask[i]:
                continue
            nb = []
            for dx, dy in ((-1, 0), (-1, -1), (0, -1), (1, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    v = lab[ny * w + nx]
                    if v:
                        nb.append(v)
            if nb:
                lab[i] = min(nb)
                for o in nb:
                    union(lab[i], o)
            else:
                parent.append(nxt)
                lab[i] = nxt
                nxt += 1
    return [find(v) if v else 0 for v in lab]


def _seeds_by_erosion(base, w: int, h: int) -> list[int] | None:
    """Encuentra SEMILLAS de figura erosionando la mascara hasta que las piezas
    se despegan. Necesario porque BiRefNet devuelve un unico blob: dos marineros
    de pie sobre la misma cubierta salen unidos por el suelo (medido 25 jul 2026:
    3 marineros = 1 componente cruda, 3 componentes al erosionar 2 pasos).
    Devuelve la etiqueta por pixel de las semillas, o None si no hay division."""
    from PIL import ImageFilter

    m = base
    for r in range(1, 7):
        m = m.filter(ImageFilter.MinFilter(3))
        mask = [v > 40 for v in m.tobytes()]
        if sum(mask) < 200:
            return None  # se comio todo: era una sola figura fina
        lab = _components(mask, w, h)
        areas: dict[int, int] = {}
        for v in lab:
            if v:
                areas[v] = areas.get(v, 0) + 1
        big = sorted((a for a in areas.values()), reverse=True)
        if len(big) >= 2 and big[1] >= 0.25 * big[0]:
            # 2+ nucleos comparables: es una escena con varios sujetos, no una
            # figura a la que se le desprendio una mano
            drop = {k for k, a in areas.items() if a < 0.25 * big[0]}
            return [0 if v in drop else v for v in lab]
    return None


def _watershed(seeds: list[int], mask: list[bool], w: int, h: int) -> list[int]:
    """Devuelve cada pixel de la mascara a su semilla mas cercana (BFS multi-
    fuente): recupera la figura COMPLETA que la erosion habia adelgazado."""
    from collections import deque

    lab = list(seeds)
    q = deque(i for i, v in enumerate(lab) if v)
    while q:
        i = q.popleft()
        v = lab[i]
        x, y = i % w, i // w
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                j = ny * w + nx
                if mask[j] and not lab[j]:
                    lab[j] = v
                    q.append(j)
    return lab


def cutout_parts(cutout_path: Path, max_parts: int = PART_MAX) -> list[dict]:
    """Parte un recorte en sus figuras/objetos separados.

    Devuelve [] cuando no hay nada que separar (una sola figura, o una domina el
    encuadre) -> el motor sigue con el recorte entero de siempre. Si hay 2+, cada
    dict trae el PNG de esa pieza y su geometria NORMALIZADA en la imagen fuente
    (nx/ny = centro 0..1, nw/nh = tamano 0..1, area = fraccion opaca), que es lo
    que permite recolocarlos respetando la composicion original.
    Cacheado junto al recorte: se calcula una vez por imagen."""
    from PIL import Image, ImageFilter

    cutout_path = Path(cutout_path)
    side = cutout_path.name  # ya incluye hash+modelo
    meta_f = CUTOUTS_DIR / f"{side[:-4]}.parts.json"
    if meta_f.exists():
        try:
            cached = json.loads(meta_f.read_text(encoding="utf-8"))
            if all(Path(p["path"]).exists() for p in cached):
                return cached
        except Exception:
            pass  # meta corrupta -> recalcular

    im = Image.open(cutout_path).convert("RGBA")
    W, H = im.size
    small = im.getchannel("A").resize((PART_WORK, PART_WORK), Image.BILINEAR)
    # cierre suave: sutura huecos finos (un brazo, un fusil cruzado) para que una
    # misma figura no se parta en dos piezas
    small = small.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    px = list(small.getdata())
    mask = [v > 40 for v in px]
    total = sum(mask)
    if total < 200:
        meta_f.write_text("[]", encoding="utf-8")
        return []

    lab = _components(mask, PART_WORK, PART_WORK)
    if len({v for v in lab if v}) < 2:
        # un solo blob: puede ser una figura sola (correcto) o varias pegadas por
        # el suelo -> erosionar hasta despegarlas y devolverles su carne
        seeds = _seeds_by_erosion(small, PART_WORK, PART_WORK)
        if seeds is None:
            meta_f.write_text("[]", encoding="utf-8")
            return []
        lab = _watershed(seeds, mask, PART_WORK, PART_WORK)

    stats: dict[int, list] = {}
    for i, r in enumerate(lab):
        if not r:
            continue
        x, y = i % PART_WORK, i // PART_WORK
        s = stats.get(r)
        if s is None:
            stats[r] = [1, x, y, x, y]  # area, x0, y0, x1, y1
        else:
            s[0] += 1
            if x < s[1]:
                s[1] = x
            if y < s[2]:
                s[2] = y
            if x > s[3]:
                s[3] = x
            if y > s[4]:
                s[4] = y

    canvas = PART_WORK * PART_WORK
    keep = [(r, s) for r, s in stats.items() if s[0] / canvas >= PART_MIN_AREA]
    keep.sort(key=lambda rs: -rs[1][0])
    keep = keep[:max_parts]
    if len(keep) < 2 or keep[0][1][0] / (total or 1) > PART_DOMINANT:
        meta_f.write_text("[]", encoding="utf-8")
        return []  # nada que separar: el recorte entero sigue siendo lo correcto

    out = []
    for k, (root, s) in enumerate(keep):
        # mascara solo-de-esta-pieza, dilatada 1px en pequeno (~5px reales) para
        # no comerse el antialias del borde, y subida a resolucion completa
        band = bytes(255 if lab[i] == root else 0 for i in range(canvas))
        m = Image.frombytes("L", (PART_WORK, PART_WORK), band)
        m = m.filter(ImageFilter.MaxFilter(3)).resize((W, H), Image.BILINEAR)
        piece = im.copy()
        a = piece.getchannel("A")
        piece.putalpha(
            Image.frombytes(
                "L",
                (W, H),
                bytes((av * mv) // 255 for av, mv in zip(a.tobytes(), m.tobytes())),
            )
        )
        box = piece.getchannel("A").getbbox()
        if not box:
            continue
        piece = piece.crop(box)
        pf = CUTOUTS_DIR / f"{side[:-4]}.p{k}.png"
        piece.save(pf)
        x0, y0, x1, y1 = box
        out.append(
            {
                "path": str(pf),
                "nx": ((x0 + x1) / 2) / W,
                "ny": ((y0 + y1) / 2) / H,
                "nw": (x1 - x0) / W,
                "nh": (y1 - y0) / H,
                "area": s[0] / canvas,
            }
        )
    if len(out) < 2:
        out = []
    meta_f.write_text(json.dumps(out), encoding="utf-8")
    return out


# ============================================================================
# CACHE DE ESCENAS GENERICAS (pedido usuario 25 jul 2026): una escena sin
# nombres propios ni fechas ("sailors scrubbing a steel deck, vintage
# documentary style") sirve igual en cualquier video del canal -> se genera UNA
# vez y se reusa, ahorrando llamada de imagen (y su coste) en cada repeticion.
# Las escenas ESPECIFICAS (Stalin, Bikini Atoll, 1946) nunca entran al cache:
# reusarlas seria mentir visualmente.
# ============================================================================

SCENES_DIR = CACHE_DIR / "scenes"
SCENES_DIR.mkdir(parents=True, exist_ok=True)
SCENES_INDEX = SCENES_DIR / "index.json"

import re as _re

_SPECIFIC = _re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")  # anos = escena datada


def scene_is_generic(term: str) -> bool:
    """True si el termino no ancla a una persona/lugar/fecha concreta. Heuristica
    barata: los search_terms del pipeline van en minusculas, asi que una mayuscula
    a mitad de frase es un nombre propio."""
    t = term.strip()
    if not t or _SPECIFIC.search(t):
        return False
    return not any(w[:1].isupper() for w in t.split()[1:])


def _scene_key(term: str, style: str = "") -> str:
    norm = " ".join(_re.sub(r"[^a-z0-9 ]+", " ", term.lower()).split())
    return hashlib.sha1(f"{norm}||{(style or '').strip()[:400]}".encode()).hexdigest()


def _scene_index() -> dict:
    if SCENES_INDEX.exists():
        try:
            return json.loads(SCENES_INDEX.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _scene_index_write(idx: dict) -> None:
    tmp = SCENES_INDEX.with_suffix(".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, SCENES_INDEX)


def scene_cache_lookup(term: str, style: str = "") -> Path | None:
    """Imagen ya generada para una escena generica equivalente, o None."""
    if not scene_is_generic(term):
        return None
    key = _scene_key(term, style)
    f = SCENES_DIR / f"{key}.png"
    if not f.exists():
        return None
    idx = _scene_index()
    if key in idx:  # contador de reusos: cuanto ahorra el cache, auditable
        idx[key]["uses"] = idx[key].get("uses", 0) + 1
        _scene_index_write(idx)
    return f


def scene_cache_store(term: str, style: str, img: Path) -> None:
    """Guarda una escena generica recien generada. Falla en silencio: el cache
    nunca debe tumbar un render."""
    try:
        if not scene_is_generic(term):
            return
        key = _scene_key(term, style)
        f = SCENES_DIR / f"{key}.png"
        if f.exists():
            return
        import shutil as _sh

        _sh.copyfile(img, f)
        idx = _scene_index()
        idx[key] = {"term": term[:200], "file": f.name, "uses": 0}
        _scene_index_write(idx)
    except Exception:
        pass
