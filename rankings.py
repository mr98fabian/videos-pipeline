"""Genera un Short de "Top N" a partir de clips reales de YouTube (via yt-dlp,
busqueda integrada, sin API key ni cuenta -- Reddit bloquea sin OAuth, X/Twitter
no tiene API gratis, TikTok no tiene busqueda confiable sin scraping fragil).

Narracion: SOLO el titulo del ranking (una linea, al inicio) -- no hay guion por
clip, cada clip habla por si mismo con su numero de puesto + credito.

Uso:
  py rankings.py "robo de baron" --title "Top 5 robos de baron mas clutch" --n 5

Etica/legal: los clips son de otros creadores. Se acredita el canal de origen
en pantalla (esquina) y en la descripcion final -- no es opcional, hacerlo es
lo correcto y ademas reduce (no elimina) el riesgo de reclamo de copyright.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

from pipeline import (
    ROOT,
    OUTPUT_ROOT,
    WIDTH,
    HEIGHT,
    FPS,
    log,
    run,
    ffprobe_duration,
    generate_audio,
    generate_subtitles,
    _list_sfx,
    slugify,
)

CLIP_TRIM_SECONDS = (
    7.0  # cuanto se usa de cada clip (el final suele tener el highlight)
)
MAX_CANDIDATES = 20


def search_clips(query: str, n: int, max_duration: int = 110) -> list[dict]:
    """Busca en YouTube (sin API key) y devuelve los N clips mas vistos que
    cumplen el limite de duracion -- proxy simple de 'impacto/calidad'."""
    log("rankings", f"Buscando '{query}' en YouTube...")
    proc = subprocess.run(
        [
            "py",
            "-m",
            "yt_dlp",
            f"ytsearch{MAX_CANDIDATES}:{query}",
            "--dump-json",
            "--no-warnings",
            "--flat-playlist",
            "--match-filter",
            f"duration < {max_duration} & duration > 10",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    candidates = []
    for line in proc.stdout.splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not d.get("id"):
            continue
        candidates.append(
            {
                "id": d["id"],
                "url": d.get("webpage_url")
                or f"https://www.youtube.com/watch?v={d['id']}",
                "title": d.get("title", "").strip(),
                "channel": d.get("channel") or d.get("uploader") or "canal desconocido",
                "channel_url": d.get("channel_url") or d.get("uploader_url") or "",
                "view_count": d.get("view_count") or 0,
                "duration": d.get("duration") or 0,
            }
        )
    candidates.sort(key=lambda c: c["view_count"], reverse=True)
    # dedupe por canal para no repetir el mismo uploader varias veces en el top
    seen_channels = set()
    picked = []
    for c in candidates:
        if c["channel"] in seen_channels:
            continue
        seen_channels.add(c["channel"])
        picked.append(c)
        if len(picked) >= n:
            break
    log(
        "rankings", f"{len(picked)} clips seleccionados de {len(candidates)} candidatos"
    )
    return picked


def download_clip(clip: dict, out_path: Path) -> bool:
    proc = subprocess.run(
        [
            "py",
            "-m",
            "yt_dlp",
            clip["url"],
            "-f",
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o",
            str(out_path),
            "--no-warnings",
            "--merge-output-format",
            "mp4",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    ok = out_path.exists() and out_path.stat().st_size > 10_000
    if not ok:
        log("rankings", f"fallo descarga: {clip['title'][:50]} -- {proc.stderr[-300:]}")
    return ok


def _prep_ranked_clip(
    raw_path: Path, out_path: Path, rank: int, credit: str, sfx_path: Path | None
) -> None:
    """Recorta el final del clip (donde suele estar el highlight), lo pasa a
    vertical 9:16, y le quema el numero de puesto gigante + credito discreto."""
    dur = ffprobe_duration(raw_path)
    trim = min(CLIP_TRIM_SECONDS, dur)
    start = max(dur - trim, 0)

    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1,"
        f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='TOP {rank}':"
        f"fontcolor=0xFFD400:fontsize=170:borderw=14:bordercolor=black:"
        f"x=(w-text_w)/2:y=90,"
        f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='{credit}':"
        f"fontcolor=white@0.8:fontsize=30:borderw=3:bordercolor=black@0.6:"
        f"x=30:y=h-70"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.2f}",
        "-i",
        str(raw_path),
        "-t",
        f"{trim:.2f}",
        "-vf",
        vf,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "21",
        "-pix_fmt",
        "yuv420p",
        str(out_path),
    ]
    run(cmd)


def assemble_ranking(
    clips_meta: list[dict], clip_paths: list[Path], title: str, out_dir: Path
) -> Path:
    # 1. narracion: solo el titulo
    audio_path, words = generate_audio(title, "em_alex", "+0%", out_dir)
    ass_path = generate_subtitles(words, out_dir)
    narration_dur = ffprobe_duration(audio_path)

    # 2. concatenar clips ya preparados (numerados, verticales, sin audio propio)
    # concat_list y los .mp4 deben estar en el MISMO directorio (rutas relativas
    # del protocolo concat se resuelven contra el cwd del proceso, no el archivo)
    prep_dir = clip_paths[0].parent
    concat_list = prep_dir / "clips_concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.name}'\n" for p in clip_paths), encoding="utf-8"
    )
    concat_path = out_dir / "clips_concat.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list.name,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            str(concat_path),
        ],
        cwd=prep_dir,
    )

    # 3. musica de fondo: biblioteca local. La generacion con Lyria se elimino
    # junto con el resto de Gemini el 3 ago 2026.
    from pipeline import _pick_music

    music = _pick_music()

    # 4. SFX de transicion en cada corte entre clips
    sfx_files = _list_sfx()
    cut_times = []
    t = narration_dur  # el primer clip empieza cuando termina la narracion (o se solapa un poco)
    for i in range(len(clip_paths)):
        cut_times.append(t)
        t += ffprobe_duration(clip_paths[i])

    video_total_dur = ffprobe_duration(concat_path)

    final = out_dir / "video.mp4"
    inputs = ["-i", str(concat_path)]
    # narracion se reproduce ANTES de que arranquen los clips (intro con la
    # imagen congelada del primer clip de fondo) -- mas simple: la superponemos
    # a los primeros segundos del concat, se solapa con el TOP 5 en pantalla.
    inputs += ["-i", str(audio_path)]
    next_idx = 2
    music_idx = None
    if music:
        inputs += ["-i", str(music)]
        music_idx = next_idx
        next_idx += 1
    sfx_idxs = []
    for i, ct in enumerate(cut_times):
        if not sfx_files:
            break
        sfx_path = sfx_files[i % len(sfx_files)]
        inputs += ["-i", str(sfx_path)]
        sfx_idxs.append((next_idx, ct))
        next_idx += 1

    # narracion se rellena con silencio hasta el largo total del video, asi
    # amix duration=first (con [narr] primero) siempre da la duracion correcta
    # sin importar si hay musica/sfx o no -- ver nota mas abajo sobre por que
    # NO usar duration=longest con un loop infinito (cuelga ffmpeg).
    audio_filters = f"[1:a]apad=whole_dur={video_total_dur:.3f},atrim=0:{video_total_dur:.3f}[narr];"
    labels = ["[narr]"]
    if music:
        # aloop=-1 es infinito; SIEMPRE recortarlo con atrim a la duracion real
        # del video -- combinar loop infinito + amix duration=longest cuelga
        # ffmpeg (se puso a procesar el stream infinito sin parar, +20min sin
        # terminar). Con duration=first (narr=corta) tambien cortaba mal el
        # video. Fix: todo finito de antemano, amix duration=first sobre
        # streams ya acotados al largo real.
        audio_filters += (
            f"[{music_idx}:a]aloop=loop=-1:size=2e9,atrim=0:{video_total_dur:.3f},"
            f"volume=0.05[bg];"
        )
        labels.append("[bg]")
    for k, (idx, ct) in enumerate(sfx_idxs):
        ms = int(ct * 1000)
        audio_filters += f"[{idx}:a]adelay={ms}|{ms},volume=0.35[sfx{k}];"
        labels.append(f"[sfx{k}]")
    audio_filters += (
        f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:"
        "dropout_transition=0:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
    )

    video_filter = f"[0:v]ass={ass_path.name}[v];"

    run(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            video_filter + audio_filters,
            "-map",
            "[v]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-shortest",
            final.name,
        ],
        cwd=out_dir,
    )
    return final


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "query", help="Tema de busqueda en YouTube (ej. 'robo de baron clutch')"
    )
    ap.add_argument(
        "--title", required=True, help="Titulo del ranking, se narra al inicio"
    )
    ap.add_argument("--n", type=int, default=5)
    args = ap.parse_args()

    out_dir = OUTPUT_ROOT / f"{date.today().isoformat()}-ranking-{slugify(args.title)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    prep_dir = out_dir / "prep"
    prep_dir.mkdir(exist_ok=True)

    clips_meta = search_clips(args.query, args.n)
    if len(clips_meta) < 2:
        log("rankings", "muy pocos clips encontrados, prueba otra busqueda")
        return 1

    clip_paths = []
    credits = []
    # orden: el mas visto (mas "impactante") va AL FINAL como cierre del top
    # (formato conteo regresivo clasico: TOP 5 -> TOP 1)
    ordered = list(reversed(clips_meta))
    for i, clip in enumerate(ordered):
        rank = len(ordered) - i
        raw_path = raw_dir / f"{i}.mp4"
        if not download_clip(clip, raw_path):
            continue
        prep_path = prep_dir / f"{i}.mp4"
        credit = f"via {clip['channel']}"
        _prep_ranked_clip(raw_path, prep_path, rank, credit, None)
        clip_paths.append(prep_path)
        credits.append(f"#{rank} — {clip['title']} — {clip['channel']} — {clip['url']}")

    if len(clip_paths) < 2:
        log("rankings", "muy pocas descargas exitosas, aborta")
        return 1

    final = assemble_ranking(clips_meta, clip_paths, args.title, out_dir)

    (out_dir / "title.txt").write_text(args.title, encoding="utf-8")
    desc = (
        f"{args.title}\n\n"
        "Creditos de los clips usados:\n"
        + "\n".join(credits)
        + "\n\n#leagueoflegends #shorts #ranking #lol"
    )
    (out_dir / "description.txt").write_text(desc, encoding="utf-8")

    log("done", f"Video listo: {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
