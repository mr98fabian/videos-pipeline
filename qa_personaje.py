"""Puerta de calidad de las imagenes generadas: que Tadeo sea Tadeo.

POR QUE EXISTE (12 ago 2026): revisar 52 imagenes a ojo, de una en una y a
tamaño pequeño, no funciona. Se colaron un Tadeo con chaqueta, dos con otra
cara, unos gatos negros en vez de mapaches y una tanda entera en 9:16 cuando el
video es 16:9. Todo eso se vio DESPUES de generar las 52.

Esto separa las dos mitades del problema:

  1. Lo que se puede comprobar SOLO (formato, color, lamina colada, imagen
     duplicada). Es instantaneo y no necesita ojo.
  2. Lo que hay que MIRAR (que el personaje sea el personaje). Para eso genera
     hojas de revision a tamaño util --340 px, no 175--, porque a tamaño de
     sello una mano de mas o un hocico distinto son invisibles.

Uso:
    py qa_personaje.py <carpeta> --aspecto 16:9      # comprueba y arma hojas
    py qa_personaje.py <carpeta> --rehacer 9,14,20   # marca para regenerar
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent
POR_HOJA = 6          # 6 por hoja: 3x2 a 340 px entra en pantalla y se ve
ANCHO_REVISION = 340


def _imagenes(carpeta: Path) -> list[Path]:
    ims = sorted(carpeta.glob("img_*.png"), key=lambda p: int(p.stem.split("_")[1]))
    return ims or sorted(carpeta.glob("nb_*.png"),
                         key=lambda p: int(p.stem.split("_")[1]))


def comprobar(carpeta: Path, aspecto: str = "16:9") -> dict[str, list[str]]:
    """Los cuatro fallos que NO hacen falta ojos para detectar."""
    from PIL import Image

    ancho, alto = (int(x) for x in aspecto.split(":"))
    objetivo = ancho / alto
    fallos: dict[str, list[str]] = {"formato": [], "color": [], "lamina": [], "repetida": []}
    firmas: dict[tuple, str] = {}
    for p in _imagenes(carpeta):
        im = Image.open(p).convert("RGB")
        if abs(im.size[0] / im.size[1] - objetivo) > 0.02:
            fallos["formato"].append(f"{p.stem} ({im.size[0]}x{im.size[1]})")
        chico = im.resize((32, 32))
        px = list(chico.getdata())
        sat = sum(max(c) - min(c) for c in px) / len(px)
        if sat > 25:            # el canal es B/N; por debajo es la textura de papel
            fallos["color"].append(f"{p.stem} (sat {sat:.0f})")
        borde = [chico.getpixel((x, y)) for x in range(32) for y in range(32)
                 if x < 2 or x > 29 or y < 2 or y > 29]
        if sum(sum(c) / 3 for c in borde) / len(borde) > 245:
            fallos["lamina"].append(p.stem)   # fondo blanco = se colo una lamina
        firma = tuple(sum(c) // 24 for c in px)
        if firma in firmas:
            fallos["repetida"].append(f"{p.stem} = {firmas[firma]}")
        firmas[firma] = p.stem
    return fallos


def hojas(carpeta: Path, salida: Path | None = None) -> list[Path]:
    """Hojas de revision a tamaño util, numeradas, para mirar de verdad."""
    from PIL import Image, ImageDraw

    salida = salida or carpeta
    ims = _imagenes(carpeta)
    hechas = []
    for lote in range((len(ims) + POR_HOJA - 1) // POR_HOJA):
        trozo = ims[lote * POR_HOJA:(lote + 1) * POR_HOJA]
        alto = int(ANCHO_REVISION * 9 / 16)
        hoja = Image.new("RGB", (ANCHO_REVISION * 3, (alto + 20) * 2), "white")
        d = ImageDraw.Draw(hoja)
        for k, p in enumerate(trozo):
            im = Image.open(p).convert("RGB")
            im.thumbnail((ANCHO_REVISION, alto))
            x, y = (k % 3) * ANCHO_REVISION, (k // 3) * (alto + 20)
            hoja.paste(im, (x, y))
            d.text((x + 4, y + im.size[1] + 4), p.stem, fill="black")
        dest = salida / f"_revision_{lote}.png"
        hoja.save(dest)
        hechas.append(dest)
    return hechas


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    carpeta = Path(argv[0])
    aspecto = argv[argv.index("--aspecto") + 1] if "--aspecto" in argv else "16:9"

    if "--rehacer" in argv:
        nums = [int(x) for x in argv[argv.index("--rehacer") + 1].split(",")]
        for n in nums:
            for patron in (f"img_{n:02d}.png", f"nb_{n}.png"):
                f = carpeta / patron
                if f.exists():
                    f.unlink()
                    print(f"borrada {f.name} -> la volvera a pedir el generador")
        return 0

    f = comprobar(carpeta, aspecto)
    total = len(_imagenes(carpeta))
    print(f"{total} imagenes en {carpeta}\n")
    for k, v in f.items():
        print(f"  {k:9}: {', '.join(v) if v else 'ok'}")
    malas = sorted({x.split()[0].split('_')[1].lstrip('0') or '0'
                    for lista in f.values() for x in lista})
    print(f"\nautomatico -> rehacer: {','.join(malas) if malas else 'ninguna'}")
    print("\nhojas de revision (mirar UNA A UNA, el personaje no lo juzga el script):")
    for h in hojas(carpeta):
        print("   ", h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
