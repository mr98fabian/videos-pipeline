"""LEGACY (nov 2026): KOREX ya no anima con Wan; el movimiento lo pone
korex_motion.py (Remotion). Codigo intacto, sin uso salvo --korex-legacy.

Anima las escenas de un video ya producido con Wan 2.2 EN LOCAL (WanGP).

Es el reemplazo del imagen->video de Flow, que esta apagado desde el 3 ago 2026
por caro (~100 creditos por clip) y por fallar de forma intermitente. Aqui el
clip no cuesta creditos: cuesta minutos de GPU propia, asi que un fallo se
reintenta sin pagar nada y se puede animar el video entero, no solo la escena 1.

Lo que NO cambia: las imagenes las sigue generando Flow. Wan solo pone el
movimiento partiendo de la imagen ya aprobada, que es lo que mantiene a Tadeo
identico entre escenas -- la consistencia la aporta el fotograma de partida, no
el modelo de video.

    py wan_animate.py output/<carpeta>                  # anima lo que falte
    py wan_animate.py output/<carpeta> --dry-run        # valida sin generar
    py wan_animate.py output/<carpeta> --escenas 0,3,7  # solo esas
    py wan_animate.py output/<carpeta> --res 480x832    # mas rapido, peor

Escribe `clips/fx_<i>.mp4`, que es EXACTAMENTE lo que consume korex_animate.py.
O sea, el montaje posterior no cambia ni una linea:

    py wan_animate.py output/<carpeta>
    py korex_animate.py output/<carpeta> --animar-todo

Cada clip se cachea: si esto se corta a la mitad, al relanzarlo solo genera lo
que falta. Y cada clip se verifica contra su imagen con la misma comprobacion
que Flow (`clip_matches_source`): un mp4 valido que anima OTRA escena es un
fallo silencioso, y en imagen->video local tambien puede pasar si el mapeo de
salidas se desordena.

Requiere WanGP instalado en WAN_DIR (ver INSTALACION_WAN.md). La primera corrida
descarga el modelo (~30 GB, una sola vez).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
WAN_DIR = ROOT.parent / "Wan2GP"
WAN_PY = WAN_DIR / ".venv" / "Scripts" / "python.exe"

# Lightning v2: 4 pasos en vez de 20. En una 4080 portatil de 12 GB esa es la
# diferencia entre viable y no viable; la version base del modelo esta pensada
# para tarjetas de escritorio con 24 GB.
MODEL = "i2v_2_2_Enhanced_Lightning_v2"
STEPS = 4
RES = "720x1280"
# DURACION RECORTADA (24 ago 2026). Medido sobre el mismo clip, diferencia
# contra la imagen de origen a lo largo del tiempo: 0.6s=18 / 1.2s=39 /
# 2.0s=50 / 2.5s=53 / 3.0s=60. korex_animate.clip_keeps_identity rechaza por
# encima de 55 -- a los 5s de siempre (81 frames) el personaje ya iba en 61 y
# se quedaba ahi (orejas de Tadeo estiradas hasta parecer conejo). 32 frames
# (~2s) deja margen real bajo el umbral y sigue siendo movimiento de verdad,
# no solo el primer fotograma. korex_animate clona el ultimo frame (ya
# validado) para el resto de la duracion de la escena.
FRAMES = 32  # ~2s a 16fps


def model_defaults(model=MODEL):
    """Los defaults del modelo (guidance, flow_shift, fases), sin los que sale ruido.

    NO es opcional y no es cosmetico. El modo headless de WanGP usa TAL CUAL el
    JSON que se le pasa: no mezcla los defaults del modelo como hace la web. Sin
    `guidance_scale: 1` y las dos fases, Lightning corre con una guidance
    generica de 5 en 4 pasos y devuelve ruido de color -- un mp4 valido, de la
    duracion correcta, con el fotograma 0 identico a la imagen y todo lo demas
    basura. Medido el 15 ago 2026: diff 57-66 con los defaults perdidos, 21-34
    con ellos puestos.
    """
    f = WAN_DIR / "defaults" / f"{model}.json"
    if not f.exists():
        return {}
    d = json.loads(f.read_text(encoding="utf-8"))
    # "model" es metadatos y "prompt" es el ejemplo del autor: los dos estorban
    return {
        k: v
        for k, v in d.items()
        if k not in ("model", "prompt") and not isinstance(v, (dict, list))
    }


def build_queue(imgs, terms, res, frames, steps, motion_hint):
    """Una tarea por escena, en orden. El orden es el contrato del mapeo."""
    base = model_defaults()
    tasks = []
    for img in imgs:
        idx = int(img.stem.split("_")[1])
        term = terms[idx] if idx < len(terms) else ""
        prompt = f"{term}. {motion_hint}" if term else motion_hint
        task = dict(base)
        task.update(
            {
                "model_type": MODEL,
                "prompt": prompt,
                "image_start": str(img).replace("\\", "/"),
                "resolution": res,
                "video_length": frames,
                "num_inference_steps": steps,
                "seed": 42 + idx,
            }
        )
        tasks.append(task)
    return tasks


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    argv = sys.argv[1:]

    def _opt(flag, default):
        if flag in argv:
            k = argv.index(flag)
            v = argv[k + 1]
            del argv[k : k + 2]
            return v
        return default

    dry = "--dry-run" in argv
    if dry:
        argv.remove("--dry-run")
    res = _opt("--res", RES)
    frames = int(_opt("--frames", FRAMES))
    steps = int(_opt("--pasos", STEPS))
    solo = _opt("--escenas", "")

    out_dir = Path(argv[0]).resolve()
    clips = out_dir / "clips"
    if not clips.is_dir():
        print(f"ERROR: no existe {clips}")
        return 1
    if not WAN_PY.exists():
        print(f"ERROR: WanGP no instalado en {WAN_DIR} (ver INSTALACION_WAN.md)")
        return 1

    import korex_animate as ka

    imgs = ka.scene_images(clips)
    if not imgs:
        print(f"ERROR: no hay escenas nb_*.png en {clips}")
        return 1

    data = {}
    script_json = out_dir / "script.json"
    if script_json.exists():
        data = json.loads(script_json.read_text(encoding="utf-8"))
    terms = data.get("search_terms") or []

    pedidas = None
    if solo:
        pedidas = {int(x) for x in solo.replace(" ", "").split(",") if x != ""}

    faltan = []
    for img in imgs:
        idx = int(img.stem.split("_")[1])
        if pedidas is not None and idx not in pedidas:
            continue
        if (clips / f"fx_{idx}.mp4").exists():
            continue
        faltan.append(img)

    if not faltan:
        print("nada que animar: todas las escenas ya tienen su fx_<i>.mp4")
        return 0

    print(f"{len(faltan)}/{len(imgs)} escenas por animar | {MODEL} "
          f"| {res} | {frames}f | {steps} pasos")

    raw = clips / "wan_raw"
    raw.mkdir(exist_ok=True)
    previos = {p.name for p in raw.glob("*.mp4")}

    queue = build_queue(faltan, terms, res, frames, steps, ka.MOTION_HINT)
    qfile = clips / "wan_queue.json"
    qfile.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"cola: {qfile}")

    cmd = [
        str(WAN_PY), "wgp.py",
        "--process", str(qfile),
        "--output-dir", str(raw),
        "--verbose", "1",
    ]
    if dry:
        cmd.append("--dry-run")

    # sin timeout corto a proposito: la primera corrida descarga ~30 GB de
    # modelo y cada clip tarda minutos. 6h cubre un video entero.
    subprocess.run(cmd, cwd=str(WAN_DIR), timeout=6 * 3600)

    if dry:
        print("dry-run: no se genero nada")
        return 0

    # El mapeo salida->escena va por orden de creacion, que es el orden de la
    # cola. Si se desordena, clip_matches_source lo caza: un clip que no
    # empieza en su propia imagen no se acepta.
    nuevos = sorted(
        [p for p in raw.glob("*.mp4") if p.name not in previos],
        key=lambda p: p.stat().st_mtime,
    )
    if len(nuevos) != len(faltan):
        print(f"AVISO: {len(nuevos)} clips para {len(faltan)} escenas pedidas")

    ok = 0
    for img, clip in zip(faltan, nuevos):
        idx = int(img.stem.split("_")[1])
        fx = clips / f"fx_{idx}.mp4"
        shutil.copyfile(clip, fx)
        if not ka.clip_matches_source(fx, img):
            fx.unlink(missing_ok=True)
            print(f"  {img.name}: DESCARTADO (el clip no es esta escena)")
        elif not ka.clip_keeps_identity(fx, img):
            # BUG del 24 ago 2026: Wan sostiene la escena pero no el diseno del
            # personaje -- las orejas de Tadeo se estiran hasta parecer de
            # conejo a mitad de clip. El primer fotograma es identico (por eso
            # clip_matches_source pasa) pero el ultimo ya no es el mismo
            # personaje. Se descarta el clip animado y la escena cae al
            # camino de siempre (imagen estatica + Ken Burns), que nunca
            # deforma a Tadeo.
            fx.unlink(missing_ok=True)
            print(f"  {img.name}: DESCARTADO (Tadeo se deformo durante el clip)")
        else:
            ok += 1
            print(f"  {img.name}: OK -> {fx.name}")

    print(f"\n{ok}/{len(faltan)} clips validos")
    print(f"montar con:  py korex_animate.py {out_dir} --animar-todo")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
