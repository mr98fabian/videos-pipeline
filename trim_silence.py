"""Recorta los silencios de la narracion y REMAPEA los subtitulos al nuevo tiempo.

Por que existe: edge-tts deja una pausa natural de ~0.4s entre oraciones. Medido
30 jul 2026 en un guion de 16 oraciones, eso son 9.58s de 68.68s -- el 13.9% del
video es aire muerto, y en Shorts el tiempo absoluto visto es el factor de reparto
principal, asi que ese 14% es retencion regalada.

El detalle que hace esto no trivial: si solo se recorta el audio, los subtitulos
quedan desfasados y crecen a medida que avanza el video (cada silencio eliminado
suma desfase). Por eso aqui se recorta y se remapea con LA MISMA lista de
intervalos, no con dos pasadas independientes.

No deja los silencios en cero: se conserva un hueco minimo (--keep, 0.10s por
defecto) porque a cero las palabras se pisan y suena atropellado, peor que el
original.

Uso:
    py trim_silence.py output/<carpeta>
    py trim_silence.py output/<carpeta> --keep 0.08 --noise -35 --min-silence 0.20
    py trim_silence.py output/<carpeta> --dry-run     # solo medir, no escribir

Escribe voice_tight.mp3 y subs_tight.ass en la misma carpeta; no toca los
originales.
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


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True, timeout=60)
    return float(out.stdout.strip())


def detect_silences(audio: Path, noise_db: float, min_silence: float) -> list[tuple[float, float]]:
    """Lista de (inicio, fin) de cada silencio, via el filtro silencedetect."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(audio),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"],
        capture_output=True, text=True, timeout=300)
    log = proc.stderr
    starts = [float(m) for m in re.findall(r"silence_start:\s*([0-9.]+)", log)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([0-9.]+)", log)]
    # si el audio termina en silencio, silencedetect abre un start sin su end
    if len(starts) == len(ends) + 1:
        ends.append(ffprobe_duration(audio))
    return list(zip(starts, ends))


def removal_intervals(silences: list[tuple[float, float]], keep: float) -> list[tuple[float, float]]:
    """Trozos a ELIMINAR: de cada silencio se quita todo menos `keep` segundos."""
    out = []
    for s, e in silences:
        if (e - s) > keep:
            out.append((s + keep, e))
    return out


def keep_segments(removals: list[tuple[float, float]], total: float) -> list[tuple[float, float]]:
    """Complemento de los intervalos eliminados: lo que se conserva."""
    segs, cursor = [], 0.0
    for s, e in removals:
        if s > cursor:
            segs.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < total:
        segs.append((cursor, total))
    return segs


def remap(t: float, removals: list[tuple[float, float]]) -> float:
    """Traduce un instante del audio ORIGINAL al audio recortado.

    Resta todo el tiempo eliminado que quede por delante de `t`. Un instante
    que cae DENTRO de un trozo eliminado se colapsa al inicio de ese trozo.
    """
    shift = 0.0
    for s, e in removals:
        if t <= s:
            break
        shift += min(t, e) - s
    return max(0.0, t - shift)


def build_audio(src: Path, dst: Path, segs: list[tuple[float, float]]) -> None:
    """Reconstruye el audio concatenando solo los tramos conservados.

    Se usa atrim+concat explicito en vez de `silenceremove` porque este script
    necesita saber EXACTAMENTE que se quito para remapear los subtitulos con la
    misma lista; silenceremove no reporta los intervalos que decidio cortar.
    """
    parts = "".join(
        f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS[a{i}];"
        for i, (s, e) in enumerate(segs))
    joins = "".join(f"[a{i}]" for i in range(len(segs)))
    fc = f"{parts}{joins}concat=n={len(segs)}:v=0:a=1[out]"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src),
         "-filter_complex", fc, "-map", "[out]",
         "-c:a", "libmp3lame", "-q:a", "2", str(dst)],
        check=True, timeout=600)


_TS = re.compile(r"^(\d):(\d{2}):(\d{2}\.\d{2})$")


def _parse_ts(ts: str) -> float:
    m = _TS.match(ts.strip())
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def _fmt_ts(t: float) -> str:
    h = int(t // 3600)
    mi = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{mi:02d}:{s:05.2f}"


def remap_ass(src: Path, dst: Path, removals: list[tuple[float, float]],
              offset: float) -> int:
    """Reescribe los tiempos del .ass al eje del audio recortado.

    `offset` se resta ANTES de remapear: pipeline.py genera los subs con
    offset_ms=1000 cuando el guion trae hook_card, y ese segundo no existe en
    voice.mp3, asi que hay que quitarlo o todo el remapeo sale corrido.
    """
    lines, n = [], 0
    for line in src.read_text(encoding="utf-8").splitlines():
        if line.startswith("Dialogue:"):
            parts = line.split(",")
            for idx in (1, 2):
                t = max(0.0, _parse_ts(parts[idx]) - offset)
                parts[idx] = _fmt_ts(remap(t, removals))
            # un evento que quedo con duracion 0 tras el colapso se estira un
            # minimo para que libass no lo descarte
            if _parse_ts(parts[2]) <= _parse_ts(parts[1]):
                parts[2] = _fmt_ts(_parse_ts(parts[1]) + 0.05)
            line = ",".join(parts)
            n += 1
        lines.append(line)
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir", help="carpeta de output del video")
    ap.add_argument("--keep", type=float, default=0.10,
                    help="hueco a conservar en cada silencio, en segundos (default 0.10). "
                         "A 0 las palabras se pisan y suena peor que el original.")
    ap.add_argument("--noise", type=float, default=-35,
                    help="umbral de silencio en dB (default -35)")
    ap.add_argument("--min-silence", type=float, default=0.20,
                    help="duracion minima para considerarlo silencio (default 0.20s)")
    ap.add_argument("--subs-offset", type=float, default=1.0,
                    help="segundos de offset que el .ass trae de mas respecto a la voz "
                         "(pipeline usa 1.0 cuando hay hook_card; 0 si no)")
    ap.add_argument("--dry-run", action="store_true", help="solo medir, no escribir")
    args = ap.parse_args()

    d = Path(args.out_dir)
    if not d.is_absolute():
        d = Path(__file__).resolve().parent / d
    voice = d / "voice.mp3"
    ass = d / "subs.ass"
    if not voice.exists():
        sys.exit(f"no existe {voice}")

    total = ffprobe_duration(voice)
    sils = detect_silences(voice, args.noise, args.min_silence)
    rem = removal_intervals(sils, args.keep)
    cut = sum(e - s for s, e in rem)

    print(f"voz original      {total:.2f}s")
    print(f"silencios         {len(sils)} (>={args.min_silence}s, {args.noise}dB)")
    print(f"se recorta        {cut:.2f}s  ({cut / total * 100:.1f}% del total)")
    print(f"voz resultante    {total - cut:.2f}s   (hueco conservado: {args.keep}s)")

    if args.dry_run:
        print("\n--dry-run: no se escribio nada")
        return
    if not rem:
        print("\nno hay nada que recortar")
        return

    segs = keep_segments(rem, total)
    out_voice = d / "voice_tight.mp3"
    build_audio(voice, out_voice, segs)
    real = ffprobe_duration(out_voice)
    print(f"\nescrito {out_voice.name}  ({real:.2f}s real)")

    if ass.exists():
        out_ass = d / "subs_tight.ass"
        n = remap_ass(ass, out_ass, rem, args.subs_offset)
        print(f"escrito {out_ass.name}  ({n} eventos remapeados)")
    else:
        print(f"aviso: no existe {ass.name}, no se remapearon subtitulos")


if __name__ == "__main__":
    main()
