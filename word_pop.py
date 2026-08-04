"""Capa de "pop" en cada palabra resaltada del karaoke, ADITIVA (no reemplaza
nada). Requiere SUB_CHUNK_WORDS=1 en pipeline.py (30 jul 2026) para que cada
evento del .ass sea una sola palabra -- con eso el inicio de cada evento ES el
onset de la palabra.

No hay un sonido de "pop" real en assets/sfx/, asi que se genera uno sintetico
con ffmpeg (tono corto con envolvente rapida) en vez de forzar un clic que no
encaje. Se cachea una vez en assets/sfx/_synth_pop.wav.

Uso:
    py word_pop.py output/<carpeta>
    py word_pop.py output/<carpeta> --volume 0.25 --video video_final.mp4
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
SFX_DIR = ROOT / "assets" / "sfx"
POP_PATH = SFX_DIR / "_synth_pop.wav"


def ensure_pop_asset(force: bool = False) -> Path:
    """Genera el pop sintetico una sola vez: ruido blanco filtrado en agudos,
    ~18ms, no un tono puro.

    La primera version usaba un seno de 900Hz -- sonaba bien un pop aislado,
    pero con ~4 palabras/seg repitiendo la MISMA frecuencia el oido deja de
    percibir clics discretos y lo escucha como un pitido sostenido (reportado
    30 jul 2026: 'pin pin pin' de fondo). El ruido filtrado no tiene una
    frecuencia fija que se pueda encadenar en un tono, asi que aunque se repita
    rapido sigue leyendose como una serie de clics."""
    if POP_PATH.exists() and not force:
        return POP_PATH
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "anoisesrc=color=white:duration=0.018:amplitude=1.0",
        "-af", "highpass=f=3000,afade=t=out:st=0.004:d=0.014,volume=2.2",
        "-ar", "44100", str(POP_PATH),
    ], check=True, timeout=30)
    return POP_PATH


_TS = re.compile(r"^(\d):(\d{2}):(\d{2}\.\d{2})$")


def _parse_ts(ts: str) -> float:
    m = _TS.match(ts.strip())
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


_ASS_TAG = re.compile(r"\{[^}]*\}")


def word_events(ass_path: Path) -> list[tuple[float, str]]:
    """(onset, palabra_limpia) por evento de dialogo -- valido si
    SUB_CHUNK_WORDS=1 (cada evento = una palabra). Con chunks de mas de 1
    palabra esto marcaria el inicio del BLOQUE, no de cada palabra."""
    out = []
    for line in ass_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            t = _parse_ts(parts[1])
            word = _ASS_TAG.sub("", parts[9]).replace("\\N", " ").strip()
            out.append((t, word))
    return out


def word_onsets(ass_path: Path) -> list[float]:
    """Todos los onsets, sin filtrar (compatibilidad)."""
    return [t for t, _ in word_events(ass_path)]


def keyword_onsets(ass_path: Path, keywords: list[str]) -> list[float]:
    """Onsets SOLO de las palabras cuyo texto (sin puntuacion) coincide con
    alguna de `keywords` (comparacion insensible a mayusculas). Pedido
    explicito del usuario 30 jul 2026: poner un pop en cada palabra sonaba a
    pitido sostenido, y ademas es mas ruido del que hace falta -- solo las
    palabras con carga emocional real deben tener acento sonoro."""
    kws = {k.strip().upper() for k in keywords if k.strip()}
    out = []
    for t, word in word_events(ass_path):
        clean = re.sub(r"[^\w]", "", word).upper()
        if clean in kws:
            out.append(t)
    return out


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True, timeout=60)
    return float(out.stdout.strip())


def build_pop_track(onsets: list[float], total: float, volume: float, out_path: Path) -> None:
    pop = ensure_pop_asset()
    if not onsets:
        sys.exit("no hay onsets de palabra (subs.ass vacio o sin eventos)")
    filters, labels = [], []
    for i, t in enumerate(onsets):
        ms = max(0, int(t * 1000))
        lbl = f"p{i}"
        filters.append(f"[0:a]adelay={ms}|{ms},volume={volume}[{lbl}];")
        labels.append(f"[{lbl}]")
    mix = "".join(filters) + "".join(labels) + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0[out]"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-stream_loop", str(len(onsets) - 1), "-i", str(pop),
        "-filter_complex", mix, "-map", "[out]", "-t", f"{total:.3f}",
        "-c:a", "libmp3lame", "-q:a", "2", str(out_path),
    ], check=True, timeout=600)
    print(f"{len(onsets)} pops colocados -> {out_path.name}")


def mux(base_video: Path, pop_track: Path, dst: Path) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(base_video), "-i", str(pop_track),
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(dst),
    ], check=True, timeout=600)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir")
    ap.add_argument("--ass", default="subs.ass", help="archivo .ass a usar (default subs.ass)")
    ap.add_argument("--video", default="video.mp4", help="video base sobre el que mezclar")
    ap.add_argument("--volume", type=float, default=0.25)
    ap.add_argument("--out-name", default="video_with_pop.mp4")
    ap.add_argument("--keywords", default=None,
                    help="lista separada por comas de palabras clave del guion "
                         "(ej. 'FUNERAL,MONEY,ALIVE,PREGNANT'). Sin esto, pop en "
                         "CADA palabra -- eso fue lo que sono a pitido sostenido "
                         "(reportado 30 jul 2026), usar --keywords para evitarlo.")
    args = ap.parse_args()

    d = Path(args.out_dir)
    if not d.is_absolute():
        d = ROOT / d
    ass = d / args.ass
    if not ass.exists():
        sys.exit(f"no existe {ass}")

    if args.keywords:
        onsets = keyword_onsets(ass, args.keywords.split(","))
        if not onsets:
            sys.exit(f"ninguna de estas palabras aparece en {ass.name}: {args.keywords}")
    else:
        onsets = word_onsets(ass)
    total = ffprobe_duration(d / "voice.mp3") if (d / "voice.mp3").exists() else max(onsets) + 1
    pop_track = d / "pop_track.mp3"
    build_pop_track(onsets, total, args.volume, pop_track)

    base = d / args.video
    if base.exists():
        dst = d / args.out_name
        mux(base, pop_track, dst)
        print(f"escrito {dst.name}")


if __name__ == "__main__":
    main()
