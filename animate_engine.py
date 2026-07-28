"""Anima una PLACA DE PERSONAJE (ch_<i>.png) con esqueleto real.

Cadena: placa plana -> articulaciones -> retarget de una captura BVH -> clip
con ALFA que el motor Archivo compone en vez del sticker quieto.

Las articulaciones salen del contenedor `docker_torchserve` (detector de
humanoides dibujados + estimador de pose de Meta). Si no responde -- y en una
corrida programada a las 06:00 no tiene por que estar levantado -- se caen a
proporciones de figura de pie, que funcionan PORQUE la placa fuerza la pose:
cuerpo entero, de frente, brazos a 45 grados y piernas abiertas. Sin esa
garantia las proporciones no valdrian nada.

Arrancar el contenedor:  docker start docker_torchserve
Construirlo desde cero:  ver tools/animated_drawings/repo/torchserve/ y el
                         config.oneworker.properties (default_workers_per_model=1
                         es obligatorio: por defecto levanta un worker por
                         nucleo y muere de OOM sin dejar excepcion).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
AD_ROOT = ROOT / "tools" / "animated_drawings" / "repo"
AD_PY = ROOT / "tools" / "animated_drawings" / ".venv" / "Scripts" / "python.exe"
CACHE = ROOT / "assets" / "cache" / "animated"
TORCHSERVE = "http://localhost:8080"

# Movimientos disponibles hoy. Los cuatro bailes (dab, jesse_dance, jumping,
# jumping_jacks) NO se usan: en un canal de historia leen como parodia. La
# biblioteca CMU (libre, miles de BVH) es la via para ampliar esto con andares,
# gestos de senalar y caidas.
MOTIONS = {
    "wave":   "examples/config/motion/wave_hello.yaml",
    "shamble": "examples/config/motion/zombie.yaml",
}
DEFAULT_MOTION = "wave"

# verbo narrado -> movimiento. Mismo patron de palabra completa que _ACTION_KW
# en archivo_engine.py, para que un 'shot' no dispare por 'shoulder'.
_MOTION_KW = [
    ("shamble", r"march|walk|advance|retreat|flee|escape|drag|stagger|collaps"),
    ("wave",    r"\btold\b|\bsaid\b|announc|declar|order|blame|accus|point|claim|insist"),
]


def motion_for(narration: str) -> str:
    t = (narration or "").lower()
    for name, kw in _MOTION_KW:
        if re.search(kw, t):
            return name
    return DEFAULT_MOTION


def _sha1(path: Path) -> str:
    import hashlib
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def torchserve_up() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(f"{TORCHSERVE}/ping", timeout=5) as r:
            return json.loads(r.read()).get("status") == "Healthy"
    except Exception:
        return False


# proporciones de una figura de pie recortada a su caja; solo son fiables
# porque la placa impone la pose (ver CHARACTER_PLATE en pipeline.py)
_PROPORTIONS = {
    "root": (0.50, 0.56), "hip": (0.50, 0.56), "torso": (0.50, 0.37), "neck": (0.50, 0.21),
    "right_shoulder": (0.35, 0.25), "right_elbow": (0.27, 0.40), "right_hand": (0.24, 0.55),
    "left_shoulder": (0.65, 0.25), "left_elbow": (0.73, 0.40), "left_hand": (0.77, 0.54),
    "right_hip": (0.43, 0.57), "right_knee": (0.42, 0.78), "right_foot": (0.40, 0.97),
    "left_hip": (0.57, 0.57), "left_knee": (0.58, 0.76), "left_foot": (0.60, 0.95),
}
_PARENTS = {
    "root": None, "hip": "root", "torso": "hip", "neck": "torso",
    "right_shoulder": "torso", "right_elbow": "right_shoulder", "right_hand": "right_elbow",
    "left_shoulder": "torso", "left_elbow": "left_shoulder", "left_hand": "left_elbow",
    "right_hip": "root", "right_knee": "right_hip", "right_foot": "right_knee",
    "left_hip": "root", "left_knee": "left_hip", "left_foot": "left_knee",
}


def _annotate_fallback(plate: Path, out_dir: Path) -> None:
    """char_cfg + texture + mask por proporciones, sin red."""
    import yaml
    from PIL import Image
    im = Image.open(plate).convert("RGBA")
    box = im.split()[3].getbbox() or (0, 0, *im.size)
    c = im.crop(box)
    c.thumbnail((700, 1200), Image.LANCZOS)
    w, h = c.size
    out_dir.mkdir(parents=True, exist_ok=True)
    flat = Image.alpha_composite(Image.new("RGBA", c.size, (255, 255, 255, 255)), c)
    flat.convert("RGB").save(out_dir / "texture.png")
    c.split()[3].point(lambda a: 255 if a > 40 else 0).convert("L").save(out_dir / "mask.png")
    sk = [{"loc": [int(_PROPORTIONS[n][0] * w), int(_PROPORTIONS[n][1] * h)],
           "name": n, "parent": _PARENTS[n]} for n in _PARENTS]
    yaml.safe_dump({"width": w, "height": h, "skeleton": sk},
                   open(out_dir / "char_cfg.yaml", "w"), sort_keys=False)


def _clean_frames(gif: Path, out_dir: Path, tol: int = 40) -> int:
    """Quita el fondo blanco que queda DENTRO de la silueta, fotograma a
    fotograma. Devuelve cuantos escribio.

    Por que aqui y no en la mascara (medido el 28 jul 2026): AnimatedDrawings
    segmenta una SILUETA MACIZA, asi que el hueco entre las piernas y entre los
    brazos y el torso sale relleno con el blanco de la placa. Sustituir su
    mascara por la nuestra (con esos huecos vaciados) CUELGA el render: las
    concavidades profundas rompen la triangulacion de la malla ARAP -- se probo
    y el proceso se queda mudo para siempre, sin excepcion.

    Limpiando el fotograma YA renderizado se evita tocar la malla y, mejor aun,
    el recorte SIGUE LA DEFORMACION: cuando el personaje separa las piernas, el
    hueco se abre solo. El relleno arranca del borde, asi que el pelo cano y los
    ojos (blancos pero encerrados por el trazo) no se agujerean.
    """
    import numpy as np
    from PIL import Image, ImageSequence
    from scipy import ndimage

    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for fr in ImageSequence.Iterator(Image.open(gif)):
        a = np.asarray(fr.convert("RGBA")).copy()
        rgb = a[:, :, :3].astype(np.int16)
        alpha = a[:, :, 3]
        # fondo = ya transparente O casi blanco
        bg_like = (alpha < 40) | (np.abs(rgb - 255).max(axis=2) <= tol)
        lab, k = ndimage.label(bg_like)
        if k:
            edge = np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])
            keep = np.unique(edge[edge > 0])
            if keep.size:
                a[:, :, 3] = np.where(np.isin(lab, keep), 0, alpha)
        Image.fromarray(a, "RGBA").save(out_dir / f"f{n:05d}.png")
        n += 1
    return n


def annotate(plate: Path, out_dir: Path) -> str:
    """Anota la placa. Devuelve 'torchserve' o 'proporciones' segun la via."""
    if torchserve_up():
        try:
            work = AD_ROOT / "work" / "_in"
            work.mkdir(parents=True, exist_ok=True)
            src = work / f"{out_dir.name}.png"
            # la placa lleva alfa; el detector espera una imagen plana
            from PIL import Image
            im = Image.open(plate).convert("RGBA")
            Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im) \
                 .convert("RGB").save(src)
            r = subprocess.run(
                [str(AD_PY), "examples/image_to_annotations.py", str(src), str(out_dir)],
                cwd=AD_ROOT, capture_output=True, text=True, timeout=600)
            if (out_dir / "char_cfg.yaml").exists():
                return "torchserve"
            print(f"[animate] anotacion fallo, van proporciones: {r.stderr[-200:]}")
        except Exception as e:
            print(f"[animate] anotacion fallo, van proporciones: {e}")
    _annotate_fallback(plate, out_dir)
    return "proporciones"


def animate(plate: Path, motion: str = DEFAULT_MOTION, fps: int = 30) -> Path | None:
    """Placa -> clip ProRes 4444 con alfa. Cacheado por (contenido, movimiento).

    Devuelve None si algo falla: el motor sigue con el sticker quieto, que es
    peor pero valido. Animar nunca puede tumbar un render.
    """
    plate = Path(plate)
    motion_cfg = MOTIONS.get(motion, MOTIONS[DEFAULT_MOTION])
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{_sha1(plate)}.{motion}.mov"
    if out.exists():
        return out
    if not AD_PY.exists():
        return None

    name = out.stem.replace(".", "_")
    char_dir = AD_ROOT / "work" / name
    shutil.rmtree(char_dir, ignore_errors=True)
    try:
        via = annotate(plate, char_dir)
        gif = AD_ROOT / "work" / f"{name}.gif"
        mvc = AD_ROOT / "work" / f"{name}.yaml"
        mvc.write_text(
            "scene:\n"
            "  ANIMATED_CHARACTERS:\n"
            f"    - character_cfg: work/{name}/char_cfg.yaml\n"
            f"      motion_cfg: {motion_cfg}\n"
            "      retarget_cfg: examples/config/retarget/fair1_ppf.yaml\n"
            "controller:\n"
            "  MODE: video_render\n"
            f"  OUTPUT_VIDEO_PATH: work/{name}.gif\n"
            "  OUTPUT_VIDEO_CODEC: png\n", encoding="utf-8")
        r = subprocess.run(
            [str(AD_PY), "-c",
             "from animated_drawings import render; render.start(r'work/%s.yaml')" % name],
            cwd=AD_ROOT, capture_output=True, text=True, timeout=1800)
        if not gif.exists():
            print(f"[animate] render fallo: {r.stderr[-300:]}")
            return None
        # fotogramas limpios -> ProRes 4444, el unico codec de esta instalacion
        # que conserva alfa (ver stock_effects.chromakey_to_alpha)
        frames = AD_ROOT / "work" / f"{name}_frames"
        shutil.rmtree(frames, ignore_errors=True)
        nf = _clean_frames(gif, frames)
        if not nf:
            print("[animate] no se pudieron limpiar los fotogramas")
            return None
        cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
               "-i", str(frames / "f%05d.png"),
               "-vf", "scale=720:-2,format=yuva444p10le",
               "-c:v", "prores_ks", "-profile:v", "4444", "-qscale:v", "18",
               "-pix_fmt", "yuva444p10le", "-an", str(out)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if p.returncode != 0 or not out.exists():
            print(f"[animate] conversion a alfa fallo: {p.stderr[-300:]}")
            out.unlink(missing_ok=True)
            return None
        print(f"[animate] {plate.name} -> {motion} ({via})")
        return out
    except Exception as e:
        print(f"[animate] {plate.name}: {e}")
        return None
    finally:
        shutil.rmtree(char_dir, ignore_errors=True)
        shutil.rmtree(AD_ROOT / "work" / f"{name}_frames", ignore_errors=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Anima una placa de personaje")
    ap.add_argument("plate")
    ap.add_argument("--motion", default=DEFAULT_MOTION, choices=list(MOTIONS))
    a = ap.parse_args()
    print(f"torchserve: {'arriba' if torchserve_up() else 'abajo (iran proporciones)'}")
    print(animate(Path(a.plate).resolve(), a.motion))
