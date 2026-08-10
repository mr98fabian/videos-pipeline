"""Contador HUD sobre el video: sube solo, marcando progreso sin narrarlo.

La idea (1 ago 2026): el espectador ve avanzar un numero mientras la historia
avanza. Da sensacion de acumulacion y de "esto va a algun sitio" sin gastar ni
una palabra del guion, y da un motivo concreto para no hacer scroll: quiere ver
en que numero termina.

Los puntos de control se dan en segundos reales del video ya montado, sacados de
los timestamps del .ass, para que el numero cambie donde la narracion lo pide.

    py counter_overlay.py video.mp4 --keys 3.0=1,47.9=39,57.5=40 --total 40 \
        --label HOUSE --out video_counter.mp4

Entre dos claves interpola lineal y trunca, asi que sube de uno en uno. Despues
de la ultima clave se queda fijo y cambia de color: ese es el numero final, el
que el espectador estaba esperando.
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Monoespaciada: los digitos no bailan al cambiar de numero. La ruta necesita
# comillas Y los dos puntos escapados a la vez; con solo una de las dos cosas
# ffmpeg corta el valor de la opcion en "C:" y falla el filtergraph entero.
FONT = "C\\:/Windows/Fonts/consolab.ttf"
ACCENT = "0xFFE24A"  # amarillo del canal, solo para el valor final


def parse_keys(raw: str) -> list[tuple[float, int]]:
    keys = []
    for part in raw.split(","):
        t, v = part.split("=")
        keys.append((float(t), int(v)))
    keys.sort(key=lambda k: k[0])
    if len(keys) < 2:
        raise SystemExit("--keys necesita al menos dos puntos (ej. 3.0=1,50=40)")
    return keys


def build_expr(keys: list[tuple[float, int]]) -> str:
    """Expresion ffmpeg: rampa lineal truncada entre claves, plana despues."""
    expr = str(keys[-1][1])
    for (t0, v0), (t1, v1) in reversed(list(zip(keys, keys[1:]))):
        ramp = f"floor({v0}+({v1}-{v0})*(t-{t0})/({t1}-{t0}))"
        expr = f"if(lt(t\\,{t1})\\,{ramp}\\,{expr})"
    return expr


def draw(text_expr: str, color: str, enable: str, y: int, size: int) -> str:
    return (
        f"drawtext=fontfile='{FONT}':text='{text_expr}'"
        f":fontcolor={color}:fontsize={size}"
        f":borderw=6:bordercolor=black@0.9"
        f":box=1:boxcolor=black@0.42:boxborderw=22"
        f":x=(w-text_w)/2:y={y}:enable='{enable}'"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument(
        "--keys", required=True, help="t=valor,t=valor,... en segundos del video final"
    )
    ap.add_argument("--total", type=int, required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out")
    ap.add_argument("--y", type=int, default=210)
    ap.add_argument("--size", type=int, default=58)
    args = ap.parse_args()

    src = Path(args.video)
    out = Path(args.out) if args.out else src.with_name(src.stem + "_counter.mp4")
    keys = parse_keys(args.keys)
    digits = len(str(args.total))
    prefix = f"{args.label} " if args.label else ""

    climbing = f"{prefix}%{{eif\\:{build_expr(keys)}\\:d\\:{digits}}}/{args.total}"
    final = f"{prefix}{keys[-1][1]:0{digits}d}/{args.total}"
    t_first, t_last = keys[0][0], keys[-1][0]

    vf = ",".join(
        [
            draw(
                climbing, "white", f"between(t,{t_first},{t_last})", args.y, args.size
            ),
            draw(final, ACCENT, f"gte(t,{t_last})", args.y, args.size),
        ]
    )

    # sin -stats: el progreso de ffmpeg son cientos de lineas por render y no
    # aporta nada cuando esto lo lanza un agente. Con -v error, si falla, el
    # error sigue saliendo.
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(src),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(out),
    ]
    subprocess.run(cmd, check=True, timeout=1800)
    print(f"listo -> {out}")


if __name__ == "__main__":
    main()
