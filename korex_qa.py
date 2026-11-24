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
        raw_char = kx_cast.strip_beat(char_terms[i] if i < len(char_terms) else "")
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


def avisos(out_dir: Path) -> list[str]:
    """Avisos NO bloqueantes (no impiden montar). Hoy solo el beat del
    storyboard: ver LATIDO_DEL_STORYBOARD.md. Un guion sin beat marcado no es
    un error de produccion, es que la escena que importa no se distinguio de
    las demas al escribir character_terms."""
    import kx_cast

    data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    char_terms = data.get("character_terms") or []
    beats = [i for i, t in enumerate(char_terms) if kx_cast.is_beat(t or "")]
    out = []
    if not beats:
        out.append(
            "sin beat marcado: ninguna escena lleva '*' en character_terms "
            "(ver LATIDO_DEL_STORYBOARD.md)"
        )
    elif len(beats) > 1:
        out.append(f"mas de un beat marcado: escenas {beats} (deberia ser una sola)")
    return out


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


# ---------------------------------------------------------------------------
# MODO MOTION (nov 2026): el artefacto ya no son imagenes por escena sino un
# video renderizado por korex_motion.py. Se verifica el VIDEO final, no lo que
# devolvio el render: pureza B/N, personaje moviendose en cada escena,
# subtitulos atados a las marcas del TTS, duracion, numero heroe y mezcla.
# ---------------------------------------------------------------------------
def _ffprobe(path: Path, entry: str, stream: str | None = None) -> str:
    cmd = ["ffprobe", "-v", "error"]
    if stream:
        cmd += ["-select_streams", stream]
    cmd += ["-show_entries", entry, "-of", "default=nw=1:nk=1", str(path)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def _grab(video: Path, t: float, dst: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{max(t, 0):.3f}", "-i", str(video), "-frames:v", "1",
         "-vf", "scale=540:960", "-update", "1", str(dst)],
        capture_output=True,
    )
    return dst


def check_motion(out_dir: Path) -> tuple[list[str], list[str], Path | None]:
    import numpy as np
    from PIL import Image, ImageDraw

    fallos: list[str] = []
    info: list[str] = []
    man = json.loads((out_dir / "motion_manifest.json").read_text(encoding="utf-8"))
    video = out_dir / "video.mp4"
    if not video.exists():
        return [f"falta {video.name}"], info, None
    fps = man.get("fps", 30)
    vdur = float(_ffprobe(video, "format=duration") or 0)
    adur = float(_ffprobe(video, "stream=duration", "a:0") or 0)
    info.append(f"duracion {vdur:.1f}s (audio {adur:.1f}s)")
    if vdur < 58:
        fallos.append(f"duracion {vdur:.1f}s < 58s")
    if not adur:
        fallos.append("el video no tiene pista de audio")
    elif abs(vdur - adur) > 0.2:
        fallos.append(f"audio y video desfasados en largo ({vdur:.2f} vs {adur:.2f})")

    # subtitulos == marcas del TTS (mismo dato, se comprueba que no se movio)
    wj = out_dir / "words.json"
    if wj.exists():
        words = json.loads(wj.read_text(encoding="utf-8"))
        cap = [w for g in man.get("captions", []) for w in g["words"]]
        if len(cap) != len(words):
            fallos.append(f"subtitulos: {len(cap)} palabras vs {len(words)} del TTS")
        else:
            drift = max(abs(c["s"] - round(w[0] * fps)) for c, w in zip(cap, words))
            info.append(f"subtitulos: {len(cap)} palabras, desvio max {drift} frame(s) vs TTS")
            if drift > 1:
                fallos.append(f"subtitulos desincronizados ({drift} frames)")
    else:
        fallos.append("falta words.json (no se puede verificar sincronia)")

    clips = out_dir / "clips"
    qa = clips / "qa_motion"
    qa.mkdir(parents=True, exist_ok=True)
    tiles = []
    max_sat = 0.0
    for sc in man["scenes"]:
        if not (sc.get("pose") or sc.get("sidekick")):
            fallos.append(f"escena {sc['i']} ({sc['kind']}): sin personaje en cuadro")
        a_t = (sc["from"] + sc["dur"] * 0.5) / fps
        a = _grab(video, a_t, qa / f"s{sc['i']:02d}_a.png")
        b = _grab(video, a_t + 6 / fps, qa / f"s{sc['i']:02d}_b.png")
        A = np.asarray(Image.open(a).convert("L"), dtype=np.float32)
        B = np.asarray(Image.open(b).convert("L"), dtype=np.float32)
        motion = float(np.mean(np.abs(A - B)))
        if motion < 0.6:
            fallos.append(f"escena {sc['i']} ({sc['kind']}): casi sin movimiento ({motion:.2f})")
        tiles.append((a, f"{sc['i']} {sc['kind']} {a_t:.1f}s mov {motion:.1f}"))
        if sc["kind"] in ("hero", "twist"):
            e_t = (sc["from"] + 14) / fps
            tiles.append((_grab(video, e_t, qa / f"s{sc['i']:02d}_e.png"), f"{sc['kind']} +14f"))
    if man.get("cta"):
        c_t = (man["cta"]["from"] + 20) / fps
        tiles.append((_grab(video, c_t, qa / "cta.png"), f"CTA {c_t:.1f}s"))
    tiles.append((_grab(video, vdur - 0.05, qa / "last.png"), "ultimo frame"))
    tiles.insert(1, (_grab(video, 0.0, qa / "first.png"), "frame 0"))

    for path, _ in tiles:
        hsv = np.asarray(Image.open(path).convert("HSV"), dtype=np.float32)
        sat = float(np.percentile(hsv[..., 1], 99.9))
        max_sat = max(max_sat, sat)
    info.append(f"saturacion p99.9 maxima {max_sat:.1f}/255")
    if max_sat > 14:
        fallos.append(f"hay color en cuadro (saturacion {max_sat:.1f})")

    # bucle: el ultimo frame debe parecerse al primero
    f0 = np.asarray(Image.open(qa / "first.png").convert("L"), dtype=np.float32)
    fl = np.asarray(Image.open(qa / "last.png").convert("L"), dtype=np.float32)
    loop = float(np.mean(np.abs(f0 - fl)))
    info.append(f"bucle: diferencia frame0 vs ultimo {loop:.1f}")
    if loop > 25:
        fallos.append(f"el cierre no empalma con el frame 0 ({loop:.1f})")

    hero = [s for s in man["scenes"] if s["kind"] == "hero"]
    if not hero:
        fallos.append("no hay escena de numero heroe")
    elif len(str(hero[0].get("hero", {}).get("text", ""))) > 7:
        fallos.append("numero heroe demasiado largo para leerse en un telefono")

    rep = out_dir / "sound_report.json"
    if rep.exists():
        r = json.loads(rep.read_text(encoding="utf-8"))
        info.append(
            f"sonido: {len(r.get('cues', []))} efectos, sfx vs voz max "
            f"{r.get('sfx_vs_voice_db_max')} dB (mediana {r.get('sfx_vs_voice_db_median')})"
        )
        if not r.get("cues"):
            fallos.append("sin diseno sonoro")
        if (r.get("sfx_vs_voice_db_max") or -99) > -6:
            fallos.append("los efectos llegan a tapar la voz (> -6 dB)")
    else:
        fallos.append("falta sound_report.json")

    cols = 6
    tw, th, lab = 270, 480, 34
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + lab)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for k, (path, text) in enumerate(tiles):
        x, y = (k % cols) * tw, (k // cols) * (th + lab)
        sheet.paste(Image.open(path).convert("RGB").resize((tw, th)), (x, y + lab))
        d.text((x + 6, y + 8), text, fill=(235, 235, 235))
    out = out_dir / "qa_contactsheet.png"
    sheet.save(out)
    return fallos, info, out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    out_dir = Path(sys.argv[1]).resolve()
    if (out_dir / "motion_manifest.json").exists():
        fallos, info, sheet = check_motion(out_dir)
        if sheet:
            print(f"hoja de contacto: {sheet}")
        for i in info:
            print(f"  {i}")
        if fallos:
            print(f"\n{len(fallos)} FALLO(S):")
            for f in fallos:
                print("  -", f)
            return 1
        print("\nsin fallos duros (motion): B/N, personaje vivo, subs, duracion, sonido")
        return 0
    sheet = contact_sheet(out_dir)
    if sheet:
        print(f"hoja de contacto: {sheet}")
    if "--sheet" in sys.argv:
        return 0

    for a in avisos(out_dir):
        print(f"  AVISO: {a}")

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
