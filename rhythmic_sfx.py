"""Capa de SFX ritmico (whoosh en cada corte de escena), ADITIVA al sistema
literal existente (pick_sfx_cues en pipeline.py, que solo suena cuando la
narracion describe el evento -- espada, trueno).

Por que existe separado y no reemplaza al otro: feedback previo del usuario
fue que los SFX "decorativos" puestos solo por ritmo sonaban falsos, por eso
pick_sfx_cues es literal a proposito. Este script prueba la hipotesis
contraria (estimulo constante en cada corte, estilo Kallaway/canales de
retencion alta) como capa nueva para A/B, sin tocar la logica ya validada.

Uso:
    py rhythmic_sfx.py output/<carpeta>
    py rhythmic_sfx.py output/<carpeta> --volume 0.35 --pick "Whoosh_Camera_Whoosh_01.mp3"

Lee los cortes de escena desde clips/concat.txt (la lista de segmentos que ya
arma el pipeline), pone un whoosh corto justo ANTES de cada corte (los ultimos
~120ms del clip saliente), y mezcla el resultado sobre voice.mp3 + musica ya
existentes. Escribe video_rhythmic.mp4 en la misma carpeta; no toca nada mas.
"""

from __future__ import annotations

import argparse
import random
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
SFX_DIR = ROOT / "assets" / "sfx"


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return float(out.stdout.strip())


def scene_cut_times(clips_dir: Path) -> list[float]:
    """Timestamps (segundos, acumulados) de cada corte de escena, leyendo la
    duracion real de cada seg_N.mp4 en el orden de concat.txt -- son los
    clips YA cortados a la duracion de cada oracion, asi que sus bordes SON
    los cortes de escena reales del video final."""
    concat_txt = clips_dir / "concat.txt"
    if not concat_txt.exists():
        # fallback: todos los seg_*.mp4 en orden numerico
        segs = sorted(
            clips_dir.glob("seg_*.mp4"),
            key=lambda p: (
                int(re.search(r"seg_(\d+)", p.stem).group(1))
                if re.search(r"seg_(\d+)", p.stem)
                else 0
            ),
        )
    else:
        segs = []
        for line in concat_txt.read_text(encoding="utf-8").splitlines():
            m = re.match(r"file '(.+)'", line.strip())
            if m:
                p = Path(m.group(1))
                segs.append(p if p.is_absolute() else clips_dir / p.name)
    segs = [s for s in segs if s.exists() and "holdend" not in s.stem]

    cuts, acc = [], 0.0
    for s in segs:
        acc += ffprobe_duration(s)
        cuts.append(acc)
    return cuts[:-1]  # el ultimo "corte" es el final del video, no un corte real


def pick_whoosh_pool() -> list[Path]:
    pool = sorted(SFX_DIR.glob("Whoosh_*")) + sorted(SFX_DIR.glob("*Swoosh*"))
    return list(dict.fromkeys(pool))  # sin duplicados, conserva orden


def build(out_dir: Path, volume: float, single_pick: str | None, seed: int) -> Path:
    voice = out_dir / "voice.mp3"
    if not voice.exists():
        sys.exit(f"no existe {voice}")
    clips_dir = out_dir / "clips"
    total = ffprobe_duration(voice)
    cuts = scene_cut_times(clips_dir)
    if not cuts:
        sys.exit("no se encontraron cortes de escena en clips/")

    pool = [SFX_DIR / single_pick] if single_pick else pick_whoosh_pool()
    if not pool:
        sys.exit("no hay whoosh/swoosh en assets/sfx/")

    rng = random.Random(seed)
    inputs, filters, labels = [], [], []
    for i, t in enumerate(cuts):
        f = rng.choice(pool)
        inputs += ["-i", str(f)]
        delay_ms = max(0, int((t - 0.06) * 1000))  # ~60ms antes del corte
        lbl = f"w{i}"
        filters.append(
            f"[{i + 1}:a]adelay={delay_ms}|{delay_ms},volume={volume}[{lbl}];"
        )
        labels.append(f"[{lbl}]")

    mix = (
        "".join(filters)
        + "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0[whooshes];"
    )
    # cuenta cuantas cuentas de fondo (voz + lo que ya venga en video.mp4) hay
    # que sumar -- aqui se monta sobre voice.mp3 solo, para mezclar luego con
    # el video ya armado via un segundo paso simple (mas facil de razonar que
    # meterlo todo en un solo filtro gigante)
    out_path = out_dir / "whooshes_track.mp3"
    cmd = (
        ["ffmpeg", "-y", "-v", "error", "-i", str(voice)]
        + inputs
        + [
            "-filter_complex",
            mix,
            "-map",
            "[whooshes]",
            "-t",
            f"{total:.3f}",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(out_path),
        ]
    )
    subprocess.run(cmd, check=True, timeout=600)
    print(f"{len(cuts)} whoosh colocados, pista en {out_path.name}")
    return out_path


def mux_with_video(
    out_dir: Path,
    base_video: Path,
    whooshes: Path,
    dst_name: str = "video_rhythmic.mp4",
) -> Path:
    """Mezcla la pista de whooshes sobre el audio YA existente del video base
    (voz + musica + sfx literal), sin re-decidir nada de eso -- solo suma."""
    dst = out_dir / dst_name
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(base_video),
            "-i",
            str(whooshes),
            "-filter_complex",
            "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0[a]",
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(dst),
        ],
        check=True,
        timeout=600,
    )
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("out_dir")
    ap.add_argument(
        "--video",
        default="video.mp4",
        help="video base ya armado sobre el que mezclar (default video.mp4)",
    )
    ap.add_argument(
        "--volume",
        type=float,
        default=0.35,
        help="volumen del whoosh relativo (default 0.35)",
    )
    ap.add_argument(
        "--pick",
        default=None,
        help="usar SIEMPRE este archivo de assets/sfx/ en vez de rotar al azar",
    )
    ap.add_argument(
        "--seed", type=int, default=1, help="semilla para la rotacion aleatoria"
    )
    args = ap.parse_args()

    d = Path(args.out_dir)
    if not d.is_absolute():
        d = ROOT / d
    whooshes = build(d, args.volume, args.pick, args.seed)

    base = d / args.video
    if base.exists():
        dst = mux_with_video(d, base, whooshes)
        print(f"escrito {dst.name}")
    else:
        print(f"aviso: no existe {base}, solo se genero la pista de whooshes")


if __name__ == "__main__":
    main()
