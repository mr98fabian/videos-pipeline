"""Motor visual de KOREX — canal de finanzas satiricas (Tadeo el mapache).

POR QUE EXISTE APARTE DE archivo_engine.py (3 ago 2026):
"Archivo Vivo" es la piel de HiddenFacts -- expediente de misterio con polaroid
"REAL", sello "EXHIBIT B", numero de caso y anotaciones rojas de detective. Esa
piel se aplicaba a CUALQUIER video que pasara por --archivo, asi que el primer
video de Tadeo salio siendo un mapache comico dentro de un expediente policial.
El rechazo del usuario ("horrible, no me gusta la edicion") no era un problema de
tecnica de edicion: era el disfraz equivocado.

REGLAS DE ESTA PLANTILLA (investigadas el 3 ago 2026 sobre Cuphead, Kurzgesagt y
los cortos de Duolingo/Titmouse -- ver skill `explainer-parallax`):

 1. UN SET FIJO, no un fondo nuevo por escena. Lo que separa una pieza artistica
    intencional de "imagenes de IA cosidas" es que el mundo sea el MISMO y la
    profundidad venga de capas con parallax. Por eso este motor USA SOLO las
    placas de personaje (ch_*.png) sobre un escenario dibujado en la composicion,
    y descarta las imagenes de escena completas salvo para los INSERT.
 2. PALETA CERRADA de 3 tonos + un acento por villano. El grade se aplica al
    video entero, para que cada imagen generada no traiga su propio balance.
 3. CAPTIONS ancladas siempre en la misma zona, resaltado en el acento vigente.
 4. CORTES DUROS (iris / barrido de tinta / flash) sobre golpe de foley.
 5. MOVIMIENTO: push-in lento + squash-stretch del personaje sobre las silabas.

Uso standalone (regenerar un video ya producido, costo API cero):
  py korex_engine.py output/2026-08-03-como-sobrevivirias-a-una-tarjeta-de-cred

Desde pipeline.py se invoca con render_from_parts() (flag --korex).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion_graphics"
FPS = 30

# Acentos por personaje. El manifest lleva la CLAVE, no el color: el color vive
# en la composicion (KX_ACCENTS) para que la paleta no pueda divergir entre el
# lado Python y el lado React.
_ACCENT_BY_CHAR = {
    "bruja": "witch",
    "witch": "witch",
    "banco": "witch",
    "millonario": "tycoon",
    "tycoon": "tycoon",
}


def _accent_for(term: str) -> str:
    t = (term or "").lower()
    for k, v in _ACCENT_BY_CHAR.items():
        if k in t:
            return v
    return "neutral"


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 3600) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True, timeout=timeout)


def _ffprobe_dur(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True, timeout=60).stdout.strip()
    return float(out)


def build_manifest(out_dir: Path, data: dict, words: list[tuple[float, str]],
                    audio_dur: float, slug: str) -> dict:
    """Arma el manifest para la composicion KorexVideo.

    words = [(inicio_seg, palabra)]. A diferencia de Archivo Vivo, aqui NO se
    decide "sticker vs foto clavada" por cobertura: el personaje SIEMPRE va
    troquelado sobre el set fijo, y la imagen de escena completa solo se usa
    cuando la escena no tiene personaje (los INSERT infograficos).
    """
    sys.path.insert(0, str(ROOT))
    from visual_cache import cached_cutout, cutout_coverage, plate_cutout
    import pipeline as pl

    clips = out_dir / "clips"
    imgs = sorted(clips.glob("nb_*.png"), key=lambda p: int(p.stem.split("_")[1]))
    if not imgs:
        raise RuntimeError(f"no hay nb_*.png en {clips} (el motor necesita imagenes de escena)")
    n = len(imgs)

    pub = MOTION / "public" / "korex" / slug
    pub.mkdir(parents=True, exist_ok=True)

    pl_words = [(t, t, w) for t, w in words]
    durations = pl._scene_boundaries(pl_words, n, audio_dur)

    terms = data.get("search_terms") or []
    char_terms = data.get("character_terms") or []

    # Fondos reusables: se generan una vez en la vida y se comparten entre videos
    # (ver kx_assets.py). Sin set_terms en el guion, todas las escenas van con el
    # set dibujado en SVG de siempre.
    import kx_assets
    scene_sets = kx_assets.resolve_scene_sets(data, n)
    set_rel_by_name: dict[str, str] = {}

    # Poses del reparto, cacheadas de por vida (ver kx_cast.py)
    import kx_cast
    cast_poses = kx_cast.resolve_scene_cast(data, n)

    scenes = []
    cursor = 0
    for i, img in enumerate(imgs):
        dur_f = int(round(durations[i] * FPS))
        term = terms[i] if i < len(terms) else ""
        char_term = char_terms[i] if i < len(char_terms) else ""

        fg_rel, bg_rel = None, None

        # 1) BIBLIOTECA DE POSES (kx_cast): si el guion pide "tadeo/grito", se
        # reusa el mismo PNG de siempre. Es lo unico que garantiza que el
        # personaje sea IDENTICO entre escenas y entre videos -- las placas
        # generadas por escena daban un mapache distinto cada vez (contact sheet
        # del 4 ago 2026: pardo, gris, crema y tostado en el mismo video).
        cast_plate = cast_poses[i] if i < len(cast_poses) else None
        if cast_plate and cast_plate.exists():
            shutil.copyfile(cast_plate, pub / f"fg_{i}.png")
            fg_rel = f"korex/{slug}/fg_{i}.png"

        # 2) si no hay pose en biblioteca, el camino de siempre: recortar la
        # placa generada dentro de este video
        plate = clips / f"ch_{i}.png"
        if not fg_rel and plate.exists():
            # el personaje SIEMPRE troquelado: contra el fondo blanco de la placa
            # el vaciado por color acierta donde rembg deja pegotes macizos
            try:
                cut = plate_cutout(plate) or cached_cutout(plate)
                if cutout_coverage(cut) > 0.05:
                    shutil.copyfile(cut, pub / f"fg_{i}.png")
                    fg_rel = f"korex/{slug}/fg_{i}.png"
            except Exception as e:
                print(f"[korex] escena {i}: recorte fallo ({e}); va la imagen entera")

        if not fg_rel:
            # sin personaje (INSERT infografico, o el recorte fallo): la imagen
            # va como LAMINA con margen sobre el set, nunca a sangre -- a sangre
            # rompe el mundo fijo, que es justo la regla 1.
            shutil.copyfile(img, pub / f"bg_{i}.png")
            bg_rel = f"korex/{slug}/bg_{i}.png"

        # el escenario se copia UNA vez por video aunque lo usen varias escenas
        set_path = scene_sets[i] if i < len(scene_sets) else None
        set_rel = None
        if set_path and set_path.exists():
            if set_path.name not in set_rel_by_name:
                shutil.copyfile(set_path, pub / f"set_{set_path.name}")
                set_rel_by_name[set_path.name] = f"korex/{slug}/set_{set_path.name}"
            set_rel = set_rel_by_name[set_path.name]

        scenes.append({
            "from": cursor,
            "dur": dur_f,
            "fg": fg_rel,
            "bg": bg_rel,
            "set": set_rel,
            "accent": _accent_for(f"{term} {char_term}"),
            # alterna el encuadre del personaje para que dos escenas seguidas no
            # sean la misma pose mirando al mismo lado
            "flip": bool(i % 3 == 2),
        })
        cursor += dur_f

    wframes = [{"t": int(round(t * FPS)), "w": w} for t, w in words]

    # las primeras palabras (la promesa) se pintan enteras desde el frame 0:
    # la decision de quedarse se toma antes del segundo 1 y una palabra suelta
    # no es una promesa que se pueda leer.
    opener_words = min(7, max(0, len(wframes) - 1))

    return {
        "durationInFrames": cursor,
        "scenes": scenes,
        "words": wframes,
        "openerWords": opener_words,
        "hook": (data.get("hook_card")
                 or " ".join(data.get("script", "").split()[:8])).strip(),
    }


def render_from_parts(out_dir: Path, data: dict, words: list[tuple[float, str]],
                       audio_path: Path) -> Path:
    """Renderiza el video KoreX completo y muxea voz + musica."""
    sys.path.insert(0, str(ROOT))
    import pipeline as pl

    out_dir = Path(out_dir)
    slug = out_dir.name[-40:].strip("-")
    audio_dur = _ffprobe_dur(audio_path)
    manifest = build_manifest(out_dir, data, words, audio_dur, slug)

    props = out_dir / "clips" / "korex_manifest.json"
    props.parent.mkdir(exist_ok=True)
    props.write_text(json.dumps({"manifest": manifest}, ensure_ascii=False), encoding="utf-8")
    print(f"[korex] manifest: {len(manifest['scenes'])} escenas, "
          f"{len(manifest['words'])} palabras, {manifest['durationInFrames']} frames")

    engine_mp4 = out_dir / "clips" / "korex_engine.mp4"
    npx = shutil.which("npx") or "npx"
    print("[korex] renderizando composicion (esto tarda unos minutos)...")
    _run([npx, "remotion", "render", "src/index.jsx", "KorexVideo",
          str(engine_mp4.resolve()), "--props", str(props.resolve())], cwd=MOTION)

    music = pl._pick_music()
    final = out_dir / "video.mp4"
    inputs = ["-i", str(engine_mp4), "-i", str(audio_path)]
    fc = "[1:a]anull[voice];"
    if music:
        inputs += ["-i", str(music)]
        fc += ("[voice]asplit=2[vmix][vtrig];"
               "[2:a]aloop=loop=-1:size=2e9,volume=0.06[bg0];"
               "[bg0][vtrig]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[bg];")
        labels, ninputs = "[0:a][vmix][bg]", 3
    else:
        fc += "[voice]anull[vmix];"
        labels, ninputs = "[0:a][vmix]", 2
    fc += f"{labels}amix=inputs={ninputs}:normalize=0:duration=first[a]"
    _run(["ffmpeg", "-y", *inputs, "-filter_complex", fc,
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
          str(final)])
    print(f"[korex] LISTO: {final}")
    return final


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    out_dir = Path(sys.argv[1])
    data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT))
    from archivo_engine import words_from_ass
    import pipeline as pl
    words = words_from_ass(out_dir / "subs.ass")
    if not words:
        print("ERROR: no pude reconstruir timestamps desde subs.ass")
        return 1
    voice = out_dir / "voice.mp3"

    # cero aire muerto (investigacion "edicion dopaminica" 3 ago 2026): edge-tts
    # deja ~0.4s de pausa por oracion, y medido en un video real de este motor
    # eso era 21.5% del total -- silencio que en Shorts es retencion regalada
    # (el factor de reparto es tiempo absoluto visto). A diferencia de
    # pipeline.py, korex_engine no tenia esto ni siquiera como flag opt-in.
    # Se recorta ANTES de armar el manifest para que escenas y frames ya salgan
    # sobre el eje apretado. Es idempotente: si ya se corrio antes, los huecos
    # que quedan (0.10s) estan por debajo del umbral de deteccion (0.20s) y no
    # se vuelven a tocar.
    pl_words = [(t, t, w) for t, w in words]
    voice, pl_words = pl.trim_silence_inplace(voice, pl_words)
    words = [(s, w) for s, _e, w in pl_words]

    render_from_parts(out_dir, data, words, voice)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
