"""Registro central de videos generados y subidos: une carpeta de output,
video_id de YouTube y los parametros clave del guion (topic, style, music_mood)
en video_log.csv, para poder cruzar despues contra youtube_api.py top/report.

Tambien registra opcionalmente las senales de vidIQ usadas en la fase de
research (keyword_score, title_score, outlier_reference) para poder evaluar
despues si el research previo se correlaciona con el rendimiento real."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "video_log.csv"
FIELDS = ["logged_at", "output_dir", "video_id", "youtube_url", "title",
          "style_summary", "music_mood", "word_count", "duration_sec", "privacy",
          "keyword_score", "title_score", "outlier_reference"]


def _style_summary(style: str | None) -> str:
    if not style:
        return ""
    return style[:60] + ("..." if len(style) > 60 else "")


def _video_duration(video_path: Path) -> str:
    """Duracion del video.mp4 en segundos (str, 1 decimal) via ffprobe; ''
    si falla. Permite correlacionar despues duracion vs retencion real."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return f"{float(out):.1f}"
    except Exception:
        return ""


def _migrate_if_needed() -> None:
    """Si el CSV existente tiene un header mas viejo (menos columnas), lo
    reescribe con el header actual, dejando en blanco las columnas nuevas
    para las filas que ya existian."""
    if not LOG_PATH.exists():
        return
    with LOG_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if rows and list(rows[0].keys()) == FIELDS:
        return
    with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})


def log_video(output_dir: str | Path, video_id: str, privacy: str = "unlisted",
              keyword_score: float | None = None, title_score: float | None = None,
              outlier_reference: str | None = None) -> None:
    out_dir = Path(output_dir)
    script_data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    title = (out_dir / "title.txt").read_text(encoding="utf-8").strip()

    _migrate_if_needed()

    row = {
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "output_dir": out_dir.name,
        "video_id": video_id,
        "youtube_url": f"https://youtube.com/watch?v={video_id}",
        "title": title,
        "style_summary": _style_summary(script_data.get("style")),
        "music_mood": script_data.get("music_mood", ""),
        "word_count": len(script_data.get("script", "").split()),
        "duration_sec": _video_duration(out_dir / "video.mp4"),
        "privacy": privacy,
        "keyword_score": keyword_score if keyword_score is not None else "",
        "title_score": title_score if title_score is not None else "",
        "outlier_reference": outlier_reference or "",
    }

    is_new = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
    print(f"[track] agregado a {LOG_PATH.name}: {row['youtube_url']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    parser.add_argument("video_id")
    parser.add_argument("--privacy", default="unlisted")
    parser.add_argument("--keyword-score", type=float, default=None)
    parser.add_argument("--title-score", type=float, default=None)
    parser.add_argument("--outlier-ref", default=None)
    args = parser.parse_args()
    log_video(args.output_dir, args.video_id, args.privacy,
              keyword_score=args.keyword_score, title_score=args.title_score,
              outlier_reference=args.outlier_ref)
