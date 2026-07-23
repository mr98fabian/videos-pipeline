"""Publica la pregunta polarizante del video como comentario del canal.

El diagnostico del 22 jul mostro comments ~0; cada descripcion ya trae una
pregunta A/B transparente ("NIXON or KHRUSHCHEV? Say your pick below."). Este
script la extrae y la publica como comentario de nivel superior via
youtube_api.add_comment() — el FIJARLO sigue siendo 1 clic manual en Studio
(la API no lo permite).

IMPORTANTE: correr DESPUES de que el video este publico (los programados se
publican solos a su hora; comentar un video privado falla o no sirve).

Uso:
  py post_question_comment.py output/2026-07-23-nixon-vs-khrushchev...   # busca el video_id en video_log.csv
  py post_question_comment.py --video-id CnZhQOz1a2Q --dir output/...    # explicito
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent


def extract_question(description: str) -> str | None:
    """La pregunta A/B: el parrafo que contiene '?' y 'Say your pick' (o el
    primer parrafo interrogativo como fallback)."""
    paras = [p.strip() for p in description.split("\n\n") if p.strip()]
    for p in paras:
        if "?" in p and "say your pick" in p.lower():
            return p
    for p in paras:
        if "?" in p and len(p) < 220:
            return p
    return None


def video_id_for_dir(output_dir: str) -> str | None:
    log = ROOT / "video_log.csv"
    if not log.exists():
        return None
    key = Path(output_dir).name
    for row in csv.DictReader(log.open(encoding="utf-8")):
        if row.get("output_dir", "").strip("/\\").endswith(key):
            return row.get("video_id")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output_dir", nargs="?", help="carpeta output/<...> del video")
    ap.add_argument("--video-id", default=None)
    ap.add_argument("--account", default="default")
    args = ap.parse_args()

    if not args.output_dir and not args.video_id:
        ap.print_help()
        return 1

    out_dir = Path(args.output_dir) if args.output_dir else None
    vid = args.video_id or (video_id_for_dir(args.output_dir) if args.output_dir else None)
    if not vid:
        print("ERROR: no encontre el video_id (pasa --video-id o registra el video con track_video.py)")
        return 1

    desc_file = (out_dir / "description.txt") if out_dir else None
    if not desc_file or not desc_file.exists():
        print("ERROR: no encontre description.txt para extraer la pregunta")
        return 1
    question = extract_question(desc_file.read_text(encoding="utf-8"))
    if not question:
        print("ERROR: la descripcion no tiene pregunta A/B reconocible")
        return 1

    import youtube_api
    cid = youtube_api.add_comment(vid, question, account=args.account)
    print(f"[comment] pregunta publicada ({cid}). RECORDA fijarla en Studio (1 clic).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
