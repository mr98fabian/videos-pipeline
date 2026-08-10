"""Flecha que senala lo que la narracion esta nombrando en ese instante.

De donde sale: analisis del short de TLOU2 que le funciono a un conocido de
Fabian (1 ago 2026). En el segundo 1,5, justo cuando la voz dice "genericos",
aparece una flecha ROJA diagonal apuntando al enemigo del fondo -- un enemigo
pequeno, facil de perder entre la vegetacion. Sin la flecha, la frase y la
imagen van por separado; con ella, el ojo mira exactamente lo que la voz nombra.

Tres cosas que hacen que funcione y que este script conserva:
  1. Cae DENTRO de la ventana que decide el swipe (segundo 1-3), no despues.
  2. Es el unico color saturado del cuadro. El resto del video es la paleta
     verde/gris apagada del juego, asi que el ojo la agarra al instante. Por eso
     el rojo por defecto: si el fondo ya tiene rojo, cambialo con --color.
  3. Dura poco (~1,2s). Es un puntero, no un adorno permanente.

Detalle de implementacion: la flecha se dibuja a 4x y se reduce, porque a
tamano final los bordes diagonales salen dentados.

Uso:
    py arrow_pointer.py video.mp4 --at 1.5 --to 720,430
    py arrow_pointer.py video.mp4 --at 1.5 --to 720,430 --from-dir bottom-left --dur 1.2
    py arrow_pointer.py video.mp4 --at 1.5 --to 720,430 --color "#FF3B30" --out con_flecha.mp4
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
SS = 4  # supersampling: se dibuja a 4x y se reduce, si no los bordes salen dentados

# de donde VIENE la flecha, en grados (0 = apunta a la derecha)
DIRS = {
    "bottom-left": 45,  # la del video de referencia: sube hacia la derecha
    "bottom-right": 135,
    "top-left": -45,
    "top-right": -135,
    "bottom": 90,
    "top": -90,
    "left": 0,
    "right": 180,
}


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def make_arrow(length: int, angle_deg: float, color: str, width: int) -> Image.Image:
    """Flecha apuntando al ORIGEN (0,0) de la imagen, viniendo desde `angle_deg`.

    El punto de la punta queda en el centro del lienzo para poder posicionarla
    directamente sobre el objetivo con un overlay simple.
    """
    pad = length + 40
    size = pad * 2
    img = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rgb = _hex(color)

    cx = cy = size * SS // 2  # punta = centro
    a = math.radians(angle_deg)
    tail_x = cx + int(math.cos(a) * length * SS)
    tail_y = cy + int(math.sin(a) * length * SS)

    # cuerpo
    d.line([(tail_x, tail_y), (cx, cy)], fill=rgb + (255,), width=width * SS)

    # cabeza: triangulo isosceles centrado en la punta
    head = int(length * 0.34) * SS
    spread = math.radians(26)
    p1 = (cx + int(math.cos(a - spread) * head), cy + int(math.sin(a - spread) * head))
    p2 = (cx + int(math.cos(a + spread) * head), cy + int(math.sin(a + spread) * head))
    d.polygon([(cx, cy), p1, p2], fill=rgb + (255,))

    return img.resize((size, size), Image.LANCZOS)


def ffprobe_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("video")
    ap.add_argument(
        "--at",
        type=float,
        required=True,
        help="segundo en que aparece (el del video de referencia: 1.5)",
    )
    ap.add_argument("--dur", type=float, default=1.2, help="cuanto dura en pantalla")
    ap.add_argument(
        "--to", required=True, help="a que punto apunta, en pixeles del video: 'x,y'"
    )
    ap.add_argument(
        "--from-dir",
        default="bottom-left",
        choices=sorted(DIRS),
        help="desde donde entra la flecha (default bottom-left, como la de referencia)",
    )
    ap.add_argument("--length", type=int, default=170, help="largo en px")
    ap.add_argument("--width", type=int, default=13, help="grosor del cuerpo en px")
    ap.add_argument(
        "--color",
        default="#E8352B",
        help="color; rojo por defecto porque debe ser el unico saturado del cuadro",
    )
    ap.add_argument(
        "--fade", type=float, default=0.15, help="fundido de entrada/salida"
    )
    ap.add_argument(
        "--out", default=None, help="nombre de salida (default <video>_flecha.mp4)"
    )
    args = ap.parse_args()

    src = Path(args.video)
    if not src.is_absolute():
        src = ROOT / src
    if not src.exists():
        sys.exit(f"no existe {src}")

    try:
        tx, ty = (int(v) for v in args.to.split(","))
    except Exception:
        sys.exit("--to debe ser 'x,y' en pixeles, ej: --to 720,430")

    vw, vh = ffprobe_size(src)
    if not (0 <= tx <= vw and 0 <= ty <= vh):
        sys.exit(f"el objetivo {tx},{ty} cae fuera del video ({vw}x{vh})")

    arrow = make_arrow(args.length, DIRS[args.from_dir], args.color, args.width)
    png = ROOT / "tmp_local_review" / "_arrow.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    arrow.save(png)

    # la punta esta en el centro del PNG, asi que se resta la mitad al posicionar
    ox, oy = tx - arrow.width // 2, ty - arrow.height // 2
    end = args.at + args.dur
    fo = max(end - args.fade, args.at)

    dst = Path(args.out) if args.out else src.with_name(src.stem + "_flecha.mp4")
    if not dst.is_absolute():
        dst = ROOT / dst

    fc = (
        f"[1:v]format=rgba,fade=t=in:st={args.at}:d={args.fade}:alpha=1,"
        f"fade=t=out:st={fo}:d={args.fade}:alpha=1[a];"
        f"[0:v][a]overlay={ox}:{oy}:enable='between(t,{args.at},{end})',setsar=1[v]"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(src),
            "-loop",
            "1",
            "-i",
            str(png),
            "-filter_complex",
            fc,
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-crf",
            "21",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-shortest",
            str(dst),
        ],
        check=True,
        timeout=900,
    )

    print(f"flecha {args.color} desde {args.from_dir} -> ({tx},{ty})")
    print(f"visible {args.at:.2f}s - {end:.2f}s")
    print(f"escrito {dst}")


if __name__ == "__main__":
    main()
