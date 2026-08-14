"""Montaje del formato LARGO de KOREX: imagenes fijas cortadas contra la voz.

Por que existe aparte de `pipeline.assemble()`: el largo no comparte casi nada
con el Short. Aqui no hay subtitulos quemados (los referentes del formato --
Zenn0009, ecomonos -- no los usan y a 9 minutos el karaoke cansa), no hay bucle
final, y el corte no lo manda la escena sino la FRASE: el guion trae 104 cortes
sobre 52 imagenes, o sea que casi toda imagen aguanta dos frases y cambia de
encuadre en medio.

El sincronismo no se estima por palabras/segundo: se mide. `_align_words` corre
whisper sobre la voz ya sintetizada y devuelve los tiempos reales pegados al
texto del guion, asi que cada corte cae donde de verdad empieza su frase. Con
8m47s de narracion, un desfase de decimas por frase acumula minutos al final.

Uso:
    py korex_largo.py output/<carpeta> [--guion scripts/<x>.json] [--solo 3]
"""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

W, H, FPS = 1920, 1080, 30
CRF_SEG, CRF_FINAL = 18, 20
# Mismos numeros que el Short (pipeline.MUSIC_VOLUME y el loudnorm previo de la
# voz): la relacion musica/voz no puede depender del formato ni del motor de TTS.
MUSIC_VOLUME = 0.05
# Solo dominio publico: el canal no da creditos a nadie (decision 12 ago 2026).
MUSICA_CC0 = ("Frogs Legs Rag.mp3", "Maple Leaf Rag.mp3",
              "Barroom Ballet.mp3", "Vintage Party.mp3")


def run(cmd: list[str], timeout: int = 900) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{cmd[0]} fallo:\n{(p.stderr or '')[-1500:]}")


def duracion(path: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, timeout=60)
    return float((p.stdout or "0").strip())


def palabras(voz: Path, guion: str) -> list[tuple[float, float, str]]:
    """Tiempos por palabra, cacheados: whisper sobre 9 minutos no es gratis y el
    montaje se repite (un corte mal, un cambio de musica)."""
    cache = voz.with_suffix(".words.json")
    if cache.exists():
        return [tuple(x) for x in json.loads(cache.read_text("utf-8"))]
    from pipeline import _align_words

    ws = _align_words(voz, guion, "es")
    cache.write_text(json.dumps(ws, ensure_ascii=False), "utf-8")
    return ws


def cortes(sb: list[dict], ws: list[tuple[float, float, str]],
           total: float) -> list[tuple[float, float, int]]:
    """Reparte los 104 cortes sobre la linea de tiempo real de la voz.

    Se cuenta por PALABRAS acumuladas, no por caracteres: el guion que se
    sintetizo y el que trae el storyboard son el mismo texto partido en frases,
    asi que la palabra n-esima de uno es la n-esima del otro. Es un ancla
    exacta, no una proporcion.
    """
    import re

    fuera: list[tuple[float, float, int]] = []
    i = 0
    for k, c in enumerate(sb):
        n = len([w for w in re.findall(r"\S+", c["narra"]) if w.strip()])
        ini = ws[min(i, len(ws) - 1)][0]
        i += n
        fin = ws[min(i, len(ws) - 1)][0] if k < len(sb) - 1 else total
        # Un corte por debajo de medio segundo es un parpadeo: se absorbe en el
        # anterior en vez de meter un flash que el ojo lee como error de montaje.
        if fuera and fin - ini < 0.5:
            fuera[-1] = (fuera[-1][0], fin, fuera[-1][2])
            continue
        fuera.append((ini, fin, c["img"]))
    return fuera


def _kenburns(idx: int, frames: int) -> str:
    """Deriva lento, alternando dentro/fuera. Sin esto la imagen fija delata que
    es una imagen fija; con mas de esto, a 9 minutos, marea."""
    if idx % 2 == 0:
        z = f"min(1.0+(0.07/{frames})*on,1.07)"
    else:
        z = f"max(1.07-(0.07/{frames})*on,1.0)"
    if idx % 4 == 1:      # cada cuatro, ademas, un paneo horizontal corto
        x = f"(iw-iw/zoom)/2+(iw*0.03/{frames})*on"
    elif idx % 4 == 3:
        x = f"(iw-iw/zoom)/2-(iw*0.03/{frames})*on"
    else:
        x = "(iw-iw/zoom)/2"
    return (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
            f"crop={W * 2}:{H * 2},"
            f"zoompan=z='{z}':d={frames}:x='{x}':y='(ih-ih/zoom)/2':"
            f"s={W}x{H}:fps={FPS},setsar=1,format=yuv420p")


def render_corte(args) -> Path:
    idx, ini, fin, img, dst = args
    if dst.exists() and duracion(dst) > 0:
        return dst
    frames = max(int(round((fin - ini) * FPS)), 2)
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(img),
         "-vf", _kenburns(idx, frames), "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "medium", "-crf", str(CRF_SEG),
         "-pix_fmt", "yuv420p", "-r", str(FPS), str(dst)])
    return dst


def cama_musical(tmp: Path) -> Path | None:
    """Encadena las cuatro pistas CC0 en vez de repetir una: a nueve minutos, un
    ragtime en bucle de 3 minutos se oye tres veces y canta."""
    pistas = [ROOT / "assets" / "music" / n for n in MUSICA_CC0]
    pistas = [p for p in pistas if p.exists()]
    if not pistas:
        return None
    lista = tmp / "musica.txt"
    lista.write_text("".join(f"file '{p.resolve().as_posix()}'\n"
                             for p in pistas), "utf-8")
    dst = tmp / "cama.m4a"
    if not dst.exists():
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
             "-c:a", "aac", "-b:a", "192k", str(dst)])
    return dst


def montar(carpeta: Path, guion_path: Path, solo: int = 0) -> Path:
    d = json.loads(guion_path.read_text("utf-8"))
    voz = carpeta / "voice.mp3"
    sb = d["storyboard"]
    total = duracion(voz)
    ws = palabras(voz, d["script"])
    plan = cortes(sb, ws, total)
    if solo:
        plan = plan[:solo]
    imgs = carpeta / "storyboard"
    faltan = sorted({i for _, _, i in plan
                     if not (imgs / f"img_{i:02d}.png").exists()})
    if faltan:
        # ABORTAR, NO MONTAR CON HUECOS: la leccion de korex_animate. Un video
        # con una escena repetida en lugar de la que falta pasa desapercibido
        # en el render y salta en YouTube.
        raise SystemExit(f"faltan imagenes: {faltan}")

    tmp = carpeta / "cortes"
    tmp.mkdir(exist_ok=True)
    tareas = [(k, ini, fin, imgs / f"img_{i:02d}.png", tmp / f"c_{k:03d}.mp4")
              for k, (ini, fin, i) in enumerate(plan)]
    print(f"{len(tareas)} cortes sobre {total:.1f}s de voz", flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        for k, _ in enumerate(ex.map(render_corte, tareas), 1):
            if k % 10 == 0:
                print(f"  {k}/{len(tareas)} cortes", flush=True)

    lista = tmp / "lista.txt"
    # RUTAS ABSOLUTAS: el demuxer concat resuelve cada 'file' RELATIVO A LA
    # CARPETA DE LA LISTA, no al directorio de trabajo, asi que una ruta
    # relativa acaba duplicando el prefijo ('.../cortes/output/.../c_000.mp4').
    lista.write_text("".join(f"file '{t[4].resolve().as_posix()}'\n"
                             for t in tareas), "utf-8")
    mudo = carpeta / "video_mudo.mp4"
    # Reencodear el concat SIEMPRE (regla del proyecto): con -c copy, un corte
    # sin keyframe en su primer frame trunca el resultado sin avisar.
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
         "-c:v", "libx264", "-preset", "medium", "-crf", str(CRF_FINAL),
         "-pix_fmt", "yuv420p", "-r", str(FPS), str(mudo)], timeout=3600)

    cama = cama_musical(tmp)
    dst = carpeta / "video.mp4"
    cmd = ["ffmpeg", "-y", "-i", str(mudo), "-i", str(voz)]
    if cama:
        cmd += ["-stream_loop", "-1", "-i", str(cama)]
        af = (
            # La voz se ancla a -16 LUFS ANTES de mezclar; si no, el loudnorm
            # final sube la mezcla entera para compensar una voz baja y lo que
            # de verdad sube es la musica (medido con Qwen el 9 ago 2026).
            "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,asplit=2[voz][trig];"
            f"[2:a]volume={MUSIC_VOLUME},afade=t=in:st=0:d=2,"
            f"afade=t=out:st={max(total - 4, 0):.2f}:d=4[bg];"
            "[bg][trig]sidechaincompress=threshold=0.03:ratio=6:attack=50:"
            "release=300[duck];"
            "[voz][duck]amix=inputs=2:duration=first:normalize=0,"
            # 48 kHz estereo explicito: la voz de Qwen sale mono a 96 kHz y el
            # grafo la arrastraba tal cual hasta el archivo final. YouTube lo
            # reencoda igual, pero un master mono a 96k no es lo que se sube.
            "loudnorm=I=-14:TP=-1.0:LRA=11,"
            "aformat=sample_rates=48000:channel_layouts=stereo[aout]"
        )
        cmd += ["-filter_complex", af, "-map", "0:v", "-map", "[aout]"]
    else:
        cmd += ["-filter_complex",
                "[1:a]loudnorm=I=-14:TP=-1.0:LRA=11,"
                "aformat=sample_rates=48000:channel_layouts=stereo[aout]",
                "-map", "0:v", "-map", "[aout]"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(dst)]
    run(cmd, timeout=1800)
    print(f"\n{dst}  ({duracion(dst):.1f}s)", flush=True)
    return dst


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    carpeta = Path(argv[0])
    guion = Path(argv[argv.index("--guion") + 1]) if "--guion" in argv else \
        ROOT / "scripts" / "korex-dos-sueldos.json"
    solo = int(argv[argv.index("--solo") + 1]) if "--solo" in argv else 0
    montar(carpeta, guion, solo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
