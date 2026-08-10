"""Puerta de calidad de un video KOREX: comprueba los artefactos y arma una
hoja de contacto para revisarlos de un vistazo.

Existe por una razon concreta, medida el 4 ago 2026: **todos** los fallos de
ese dia fueron silenciosos. El generador devolvia OK y el archivo era valido,
pero el contenido estaba mal -- la escena 0 salio de la cache con un mapache de
otra corrida, un `generate()` devolvio la propia imagen de referencia, y varios
clips "animados" eran texto->video sin ninguna relacion con la escena (un senor
fotorrealista, un magnate en 3D). Ninguno dio error. Revisar 24 archivos a mano
falla; revisar una sola imagen, no.

    py korex_qa.py output/<carpeta>          # comprueba + hoja de contacto
    py korex_qa.py output/<carpeta> --sheet  # solo la hoja

Sale con codigo != 0 si hay algun fallo duro, para poder encadenarlo antes de
montar.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

THUMB_W = 240  # ancho de cada miniatura en la hoja de contacto
CLIP_TOL = 26.0  # diferencia media (0-255) admitida entre clip e imagen
REF_TOL = 2.0  # por debajo de esto la "escena" ES la referencia


def _thumb_array(path: Path, size=(64, 64)):
    from PIL import Image
    import numpy as np

    with Image.open(path) as im:
        return np.asarray(im.convert("L").resize(size), dtype=float)


def _first_frame(clip: Path, dst: Path, at: str = "0.1") -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", at, "-i", str(clip), "-frames:v", "1", str(dst)],
            check=True,
            timeout=120,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return dst.exists()
    except Exception:
        return False


def check(out_dir: Path) -> list[str]:
    """Devuelve la lista de fallos duros. Vacia = se puede montar."""
    import kx_cast
    import numpy as np

    clips = out_dir / "clips"
    data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    terms = data.get("search_terms") or []
    char_terms = data.get("character_terms") or []
    fallos: list[str] = []

    for i, term in enumerate(terms):
        img = clips / f"nb_{i}.png"
        if not img.exists():
            fallos.append(f"escena {i}: falta la imagen (nb_{i}.png)")
            continue

        # 1) la imagen no puede SER la lamina de referencia: pasaba cuando Flow
        #    devolvia el propio ingrediente recien subido como si fuera el
        #    resultado
        raw_char = char_terms[i] if i < len(char_terms) else ""
        if raw_char and "/" in raw_char:
            c, _, p = raw_char.partition("/")
            pose = kx_cast.pick(c, p, i) or kx_cast.get_pose(c, p)
            if pose and Path(pose).exists():
                try:
                    a, b = _thumb_array(img), _thumb_array(Path(pose))
                    if float(np.abs(a - b).mean()) < REF_TOL:
                        fallos.append(
                            f"escena {i}: la imagen ES la lamina de referencia "
                            f"({Path(pose).name}), no una escena"
                        )
                except Exception:
                    pass
            elif not pose:
                fallos.append(
                    f"escena {i}: la pose '{raw_char}' no resuelve a ninguna lamina"
                )

        # 1b) formato vertical: una escena en 16:9 se cuela y al recortarla a
        #     1080x1920 se pierde media composicion
        try:
            from PIL import Image

            with Image.open(img) as im:
                if im.width >= im.height:
                    fallos.append(
                        f"escena {i}: la imagen es horizontal "
                        f"({im.width}x{im.height}), y el canal es 9:16"
                    )
        except Exception:
            pass

        # 2) el canal es blanco y negro: una escena con color se cuela sola y
        #    rompe la unidad visual (la 8 salio en marron el 4 ago)
        try:
            from PIL import Image

            with Image.open(img) as im:
                sat = np.asarray(im.convert("HSV"), dtype=float)[:, :, 1].mean()
            # Flow devuelve casi siempre un tinte papel/crema (saturacion ~20)
            # que el montaje neutraliza con hue=s=0; lo que hay que cazar aqui
            # es el color de verdad, como la escena 8 en marron (44).
            if sat > 35:
                fallos.append(
                    f"escena {i}: la imagen tiene color "
                    f"(saturacion media {sat:.0f}), y el canal es B/N"
                )
        except Exception:
            pass

        # 3) dos escenas distintas no pueden ser la misma imagen: pasaba cuando
        #    Flow devolvia el resultado de otra escena (la 10 repetia la 6)
        for j in range(i):
            otra = clips / f"nb_{j}.png"
            if not otra.exists():
                continue
            try:
                d = float(np.abs(_thumb_array(img) - _thumb_array(otra)).mean())
            except Exception:
                continue
            # las escenas 0 y ultima SON la misma a proposito (eco del bucle)
            if d < 6.0 and not (j == 0 and i == len(terms) - 1):
                fallos.append(
                    f"escena {i}: es practicamente la misma imagen que la escena {j}"
                )

        # 4) el clip animado tiene que arrancar en su propia imagen
        fx = clips / f"fx_{i}.mp4"
        if fx.exists():
            tmp = clips / f"_qa_{i}.png"
            if _first_frame(fx, tmp):
                try:
                    d = float(np.abs(_thumb_array(tmp) - _thumb_array(img)).mean())
                    if d > CLIP_TOL:
                        fallos.append(
                            f"escena {i}: el clip animado no es esta escena "
                            f"(diferencia {d:.0f} > {CLIP_TOL:.0f})"
                        )
                except Exception:
                    pass
                tmp.unlink(missing_ok=True)

    return fallos


def contact_sheet(out_dir: Path) -> Path | None:
    """Una sola imagen con las escenas arriba y el primer fotograma de su clip
    debajo. Si una columna no casa verticalmente, ese clip esta mal."""
    from PIL import Image, ImageDraw

    clips = out_dir / "clips"
    data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    n = len(data.get("search_terms") or [])
    imgs = [clips / f"nb_{i}.png" for i in range(n)]
    if not any(p.exists() for p in imgs):
        return None

    cols = 6
    rows = (n + cols - 1) // cols
    with Image.open(next(p for p in imgs if p.exists())) as probe:
        ar = probe.height / probe.width
    tw, th = THUMB_W, int(THUMB_W * ar)
    pad, label = 8, 22
    cell_h = th * 2 + label + pad
    sheet = Image.new(
        "RGB", (cols * (tw + pad) + pad, rows * (cell_h + pad) + pad), (24, 24, 24)
    )
    draw = ImageDraw.Draw(sheet)

    for i in range(n):
        cx = pad + (i % cols) * (tw + pad)
        cy = pad + (i // cols) * (cell_h + pad)
        draw.text((cx + 2, cy + 4), f"escena {i}", fill=(235, 235, 235))
        img = clips / f"nb_{i}.png"
        if img.exists():
            with Image.open(img) as im:
                sheet.paste(im.convert("RGB").resize((tw, th)), (cx, cy + label))
        else:
            draw.rectangle(
                [cx, cy + label, cx + tw, cy + label + th], fill=(90, 20, 20)
            )
            draw.text((cx + 8, cy + label + th // 2), "FALTA", fill=(255, 200, 200))

        fx = clips / f"fx_{i}.mp4"
        y2 = cy + label + th
        if fx.exists():
            tmp = clips / f"_sheet_{i}.png"
            if _first_frame(fx, tmp):
                with Image.open(tmp) as im:
                    sheet.paste(im.convert("RGB").resize((tw, th)), (cx, y2))
                tmp.unlink(missing_ok=True)
        else:
            draw.rectangle([cx, y2, cx + tw, y2 + th], fill=(60, 50, 20))
            draw.text((cx + 8, y2 + th // 2), "sin animar", fill=(235, 220, 150))

    dst = out_dir / "qa_contactsheet.png"
    sheet.save(dst)
    return dst


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    out_dir = Path(sys.argv[1]).resolve()
    sheet = contact_sheet(out_dir)
    if sheet:
        print(f"hoja de contacto: {sheet}")
    if "--sheet" in sys.argv:
        return 0

    fallos = check(out_dir)
    if fallos:
        print(f"\n{len(fallos)} FALLO(S):")
        for f in fallos:
            print("  -", f)
        return 1
    print("\nsin fallos duros: imagenes completas y clips coherentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
