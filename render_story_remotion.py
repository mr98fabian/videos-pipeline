"""Renderiza un video del formato "historia sobre gameplay" 100% en Remotion.

Reemplaza el `-filter_complex` de FFmpeg escrito a mano video a video: el zoom
de entrada, los subtitulos, la hook card, el contador y los golpes dramaticos
pasan a ser la composicion `StoryVideo` (motion_graphics/src/archivo/StoryVideo.jsx),
con `spring()` en vez de rampas lineales.

Lo unico que Remotion NO hace aqui es cortar el gameplay en tramos (eso sigue
siendo un video ya pre-concatenado que se le pasa como fondo) -- el resto
(subtitulos, hook card, contador, beats, voz, musica con ducking) vive entero
dentro de la composicion, incluido el audio.

    py render_story_remotion.py output/2026-08-01-wedding-photos

Necesita en esa carpeta: script.json (con `counter` y `beats_s`, ver
storage-unit-headstone.json o wedding-photos-father.json como ejemplo),
voice.mp3, gameplay.mp4, hookcard.png.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion_graphics"
PUBLIC = MOTION / "public" / "story"
FPS = 30

sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")


def ffprobe_dur(p: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nk=1:nw=1",
            str(p),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return float(r.stdout.strip())


def align_words(voice_mp3: Path) -> list[tuple[float, float, str]]:
    """Timestamps reales por palabra alineando el audio ya sintetizado con
    whisper -- lo mismo que hace viral_lab._align_words, reusado aqui para no
    depender de que el word-list original siga vivo en memoria."""
    from faster_whisper import WhisperModel

    m = WhisperModel("base", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(voice_mp3), word_timestamps=True)
    out = []
    for s in segs:
        for w in s.words or []:
            out.append((float(w.start), float(w.end), w.word.strip()))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out_dir")
    ap.add_argument(
        "--out", help="nombre del mp4 final (por defecto video_remotion.mp4)"
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    slug = out_dir.name

    for campo in ("counter", "beats_s"):
        if campo not in data:
            print(
                f"AVISO: script.json no tiene '{campo}'. Ver wedding-photos-father.json "
                f"como ejemplo de como declararlo. Sigo sin el."
            )

    voice = out_dir / "voice.mp3"
    gameplay = out_dir / "gameplay.mp4"
    hookcard = out_dir / "hookcard.png"
    music_src = ROOT / data.get("musica", "") if data.get("musica") else None

    dur_s = ffprobe_dur(voice)
    dur_frames = int(dur_s * FPS) + 15  # colchon corto para el fade de salida

    print("alineando palabras con whisper (unos segundos)...")
    palabras = align_words(voice)
    words_js = [{"t": round(s * FPS), "w": w} for s, _e, w in palabras]

    # --- copia los assets al public/ de Remotion, unico sitio de donde
    # staticFile() puede leer, siguiendo el mismo patron que archivo_engine.py
    dst = PUBLIC / slug
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(gameplay, dst / "gameplay.mp4")
    shutil.copyfile(hookcard, dst / "hookcard.png")
    shutil.copyfile(voice, dst / "voice.mp3")
    if music_src and music_src.exists():
        shutil.copyfile(music_src, dst / "music.mp3")

    counter = None
    if data.get("counter"):
        c = data["counter"]
        counter = {
            "label": c["label"],
            "total": c["total"],
            "keys": [[round(t * FPS), v] for t, v in c["keys_s"]],
        }
    beats = [
        {"frame": round(b["t"] * FPS), "dur": round(b.get("dur", 0.5) * FPS)}
        for b in data.get("beats_s", [])
    ]

    props = {
        "gameplaySrc": f"story/{slug}/gameplay.mp4",
        "voiceSrc": f"story/{slug}/voice.mp3",
        "musicSrc": f"story/{slug}/music.mp3"
        if (music_src and music_src.exists())
        else None,
        "words": words_js,
        "redWords": data.get("caption_keywords", []),
        "hookCardSrc": f"story/{slug}/hookcard.png",
        "hook": data.get("hook_card", ""),
        "counter": counter,
        "beats": beats,
        "musicVolume": 0.09,
        "durationInFrames": dur_frames,
    }
    props_path = out_dir / "remotion_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    print(
        f"props: {len(words_js)} palabras, {len(beats)} beats, "
        f"contador={'si' if counter else 'no'}, duracion {dur_frames} frames"
    )

    final = out_dir / (args.out or "video_remotion.mp4")
    npx = shutil.which("npx") or "npx"
    print("renderizando en Remotion (esto tarda unos minutos)...")
    subprocess.run(
        [
            npx,
            "remotion",
            "render",
            "src/index.jsx",
            "StoryVideo",
            str(final.resolve()),
            "--props",
            str(props_path.resolve()),
        ],
        cwd=MOTION,
        check=True,
        timeout=1800,
    )
    print(f"\nlisto -> {final}")


if __name__ == "__main__":
    main()
