"""Arma el panel inferior del split cortando el gameplay cada 8-12s.

Por que: un solo clip continuo durante 40s deja de estimular -- el checklist de
edicion pedido 30 jul 2026 exige cambiar de toma cada 8-12s para mantener el
ojo activo. Esto toma UNA fuente larga (los CC-BY de assets/gameplay/) y saca
tramos de duracion aleatoria dentro de ese rango desde puntos MUY separados
entre si, para que dos tramos consecutivos no parezcan el mismo sitio.

Uso:
    py gameplay_segment.py --duration 41.3 --out tmp/gp.mp4
    py gameplay_segment.py --duration 41.3 --out tmp/gp.mp4 --source minecraft
"""

from __future__ import annotations

import argparse
import random
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
GAMEPLAY_DIR = ROOT / "assets" / "gameplay"


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True, timeout=60)
    return float(out.stdout.strip())


def pick_source(hint: str | None) -> Path:
    vids = sorted(GAMEPLAY_DIR.glob("*.mp4"))
    if not vids:
        sys.exit(f"no hay .mp4 en {GAMEPLAY_DIR} (ver ATRIBUCION.md)")
    if hint:
        for v in vids:
            if hint.lower() in v.name.lower():
                return v
        sys.exit(f"ninguna fuente coincide con {hint!r}; hay: {[v.name for v in vids]}")
    return vids[0]


def build(source: Path, total: float, out: Path, seed: int,
          lo: float, hi: float) -> list[float]:
    src_dur = ffprobe_duration(source)
    rng = random.Random(seed)

    # duraciones de cada tramo hasta cubrir `total`
    lengths, acc = [], 0.0
    while acc < total:
        d = rng.uniform(lo, hi)
        d = min(d, total - acc)
        # un resto corto no puede ser su propio tramo: un corte de 1-2s se lee
        # como parpadeo, no como cambio de toma. Se lo suma al tramo anterior
        # (que como mucho queda un poco por encima de max-cut, inofensivo).
        if d < lo / 2:
            if lengths:
                lengths[-1] += d
            acc = total
            break
        lengths.append(d)
        acc += d

    # puntos de inicio bien separados: se divide la fuente en tantas franjas
    # como tramos y se toma uno al azar DENTRO de cada franja, asi dos tramos
    # seguidos nunca salen del mismo minuto del video
    band = (src_dur - hi) / max(len(lengths), 1)
    tmp_dir = out.parent / "_gp_parts"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, d in enumerate(lengths):
        lo_b = band * i
        hi_b = max(lo_b + 1.0, band * (i + 1))
        start = rng.uniform(lo_b, hi_b)
        p = tmp_dir / f"gp_{i:02d}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{d:.2f}",
            "-i", str(source), "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", str(p),
        ], check=True, timeout=600)
        parts.append(p)

    listing = tmp_dir / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    # re-encode en el concat, nunca -c copy: sin keyframe garantizado en el corte
    # el concat trunca el video (bug real ya documentado en este repo)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
        "-i", str(listing), "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-t", f"{total:.3f}", str(out),
    ], check=True, timeout=900)

    for p in parts:
        p.unlink(missing_ok=True)
    listing.unlink(missing_ok=True)
    tmp_dir.rmdir()
    return lengths


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--duration", type=float, required=True, help="duracion total a cubrir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", default=None, help="filtro por nombre (ej. 'minecraft', 'subway')")
    ap.add_argument("--min-cut", type=float, default=8.0)
    ap.add_argument("--max-cut", type=float, default=12.0)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    src = pick_source(args.source)
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)

    lengths = build(src, args.duration, out, args.seed, args.min_cut, args.max_cut)
    real = ffprobe_duration(out)
    print(f"fuente : {src.name}")
    print(f"tramos : {len(lengths)} -> {', '.join(f'{d:.1f}s' for d in lengths)}")
    print(f"salida : {out.name} ({real:.2f}s)")


if __name__ == "__main__":
    main()
