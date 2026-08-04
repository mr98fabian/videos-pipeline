"""Atribucion de cambios: que variante de guion/formato rinde mejor de verdad.

El problema que resuelve: cada vez que cambiamos una regla (gancho "Why", los 3
tiempos de Kallaway, split con gameplay) el video siguiente sale distinto, pero
no habia forma de saber DESPUES cual de esos cambios movio la aguja. Esto lo
cruza contra las metricas reales de YouTube.

Decision de diseno: las variantes se DETECTAN solas leyendo el script.json y la
carpeta de output de cada video ya registrado en video_log.csv. No hay que
etiquetar nada a mano ni acordarse de pasar un flag -- lo que se midio es lo que
el archivo realmente contiene, no lo que creiamos haber hecho.

Uso:
    py experiments.py                      # tabla por variante (todas las cuentas)
    py experiments.py --account default    # una cuenta
    py experiments.py --min-videos 3       # solo variantes con N+ videos
    py experiments.py --videos             # listado por video, no agregado

Sin conexion a la API (o sin videos subidos) igual imprime que variantes existen
y cuantos videos tiene cada una, marcando que faltan metricas.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "video_log.csv"

_CONTRAST_OPENERS = ("but", "except", "yet", "although", "however",
                     "pero", "salvo", "aunque", "sin embargo")


def resolve_out_dir(value: str) -> Path:
    """Ubica la carpeta del video a partir de lo guardado en el CSV.

    track_video.py guarda solo el NOMBRE de la carpeta (ej.
    '2026-07-23-how-fidel-...'), no la ruta con 'output/' delante, asi que hay
    que probar las dos formas o todo sale como '(sin script.json)'.
    """
    p = Path(value)
    if p.is_absolute():
        return p
    direct = ROOT / value
    if direct.exists():
        return direct
    return ROOT / "output" / value


# --------------------------------------------------------------- deteccion

def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def _starts_with_why(text: str) -> bool:
    t = (text or "").strip().lstrip("¿\"'“”‘’-— ").lower()
    return t.startswith("why") or t.startswith("por que") or t.startswith("por qué")


def detect_features(out_dir: Path) -> dict:
    """Deriva las variantes de UN video desde sus artefactos en disco.

    Devuelve dict con claves booleanas/valores cortos. Si falta script.json
    (video viejo, carpeta borrada) devuelve features vacias en vez de fallar:
    el CSV tiene 98 filas historicas y no todas conservan la carpeta.
    """
    f: dict = {"artifacts": False}
    script_path = out_dir / "script.json"
    if not script_path.exists():
        return f

    try:
        data = json.loads(script_path.read_text(encoding="utf-8"))
    except Exception:
        return f

    f["artifacts"] = True
    script = data.get("script") or ""
    sents = _sentences(script)

    # gancho: pregunta "Why" al inicio (regla 9)
    f["hook_why"] = _starts_with_why(script)

    # gancho de 3 tiempos (regla 9b): 2a oracion abre con contraste y
    # las oraciones 2 y 3 son staccato (<=12 palabras)
    beat2_contrast = False
    staccato = False
    if len(sents) >= 3:
        w = sents[1].split()
        if w:
            first = re.sub(r"[^\w]", "", w[0]).lower()
            beat2_contrast = first in _CONTRAST_OPENERS
        staccato = len(sents[1].split()) <= 12 and len(sents[2].split()) <= 12
    f["hook_3beat"] = bool(beat2_contrast and staccato)

    f["word_count"] = len(script.split())
    f["n_scenes"] = len(data.get("search_terms") or [])

    # formato de render: si existe algun video_split_* la version publicada
    # fue el split con gameplay
    f["split"] = any(out_dir.glob("video_split*.mp4"))

    return f


def variant_label(f: dict) -> str:
    """Etiqueta legible y estable de la combinacion de variantes."""
    if not f.get("artifacts"):
        return "(sin script.json)"
    parts = []
    parts.append("hook:3beat" if f.get("hook_3beat")
                 else ("hook:why" if f.get("hook_why") else "hook:libre"))
    parts.append("split" if f.get("split") else "single")
    return " + ".join(parts)


# --------------------------------------------------------------- metricas

METRIC_KEYS = ("views", "averageViewDuration", "averageViewPercentage",
               "subscribersGained", "shares", "likes", "comments")


def load_rows(account: str | None) -> list[dict]:
    if not LOG_PATH.exists():
        sys.exit(f"no existe {LOG_PATH} -- todavia no hay videos registrados "
                 f"(se escribe con track_video.py tras cada subida)")
    with LOG_PATH.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if account:
        rows = [r for r in rows if (r.get("account") or "default") == account]
    return rows


def fetch_metrics(rows: list[dict], account: str) -> dict[str, dict]:
    ids = [r["video_id"] for r in rows if r.get("video_id")]
    if not ids:
        return {}
    try:
        import youtube_api
        return youtube_api.video_metrics_batch(ids, account=account)
    except Exception as e:
        print(f"[metrics] no se pudieron traer metricas reales ({type(e).__name__}: {e})")
        print("[metrics] sigo mostrando solo el conteo de videos por variante\n")
        return {}


# --------------------------------------------------------------- salida

def _fmt(v, nd=1):
    if v is None:
        return "-"
    return f"{v:,.{nd}f}" if isinstance(v, float) else f"{v:,}"


def print_by_variant(rows: list[dict], metrics: dict[str, dict], min_videos: int) -> None:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        out_dir = resolve_out_dir(r["output_dir"])
        f = detect_features(out_dir)
        label = variant_label(f)
        m = metrics.get(r.get("video_id") or "", {})
        groups.setdefault(label, []).append({"row": r, "f": f, "m": m})

    print(f"{'variante':<26} {'vids':>5} {'con datos':>10} {'vistas med':>12} "
          f"{'seg vistos':>11} {'% visto':>9} {'subs':>6} {'shares':>7}")
    print("-" * 92)

    def sort_key(item):
        entries = item[1]
        vals = [e["m"].get("views") for e in entries if e["m"].get("views") is not None]
        return -(statistics.median(vals) if vals else -1)

    for label, entries in sorted(groups.items(), key=sort_key):
        if len(entries) < min_videos:
            continue
        withdata = [e for e in entries if e["m"]]

        def med(key, nd=1):
            vals = [e["m"].get(key) for e in withdata if e["m"].get(key) is not None]
            return statistics.median(vals) if vals else None

        print(f"{label:<26} {len(entries):>5} {len(withdata):>10} "
              f"{_fmt(med('views'), 0):>12} {_fmt(med('averageViewDuration'), 0):>11} "
              f"{_fmt(med('averageViewPercentage')):>9} "
              f"{_fmt(med('subscribersGained'), 0):>6} {_fmt(med('shares'), 0):>7}")

    print()
    print("Medianas, no promedios: con pocos videos un solo viral distorsiona el promedio.")
    n_nodata = sum(1 for e in (x for v in groups.values() for x in v) if not e["m"])
    if n_nodata:
        print(f"{n_nodata} video(s) sin metricas todavia (recien subidos o privados): "
              f"no cuentan en las medianas.")


def print_by_video(rows: list[dict], metrics: dict[str, dict]) -> None:
    print(f"{'fecha':<11} {'variante':<26} {'vistas':>8} {'seg':>5} {'%':>6}  titulo")
    print("-" * 100)
    for r in rows:
        out_dir = resolve_out_dir(r["output_dir"])
        f = detect_features(out_dir)
        m = metrics.get(r.get("video_id") or "", {})
        print(f"{(r.get('logged_at') or '')[:10]:<11} {variant_label(f):<26} "
              f"{_fmt(m.get('views'), 0):>8} {_fmt(m.get('averageViewDuration'), 0):>5} "
              f"{_fmt(m.get('averageViewPercentage')):>6}  {(r.get('title') or '')[:44]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", default=None,
                    help="filtra por cuenta (default / impixxel). Sin esto, todas.")
    ap.add_argument("--min-videos", type=int, default=1,
                    help="oculta variantes con menos de N videos (default 1)")
    ap.add_argument("--videos", action="store_true",
                    help="listado por video en vez de agregado por variante")
    ap.add_argument("--no-api", action="store_true",
                    help="no llamar a YouTube Analytics (solo conteo por variante)")
    args = ap.parse_args()

    rows = load_rows(args.account)
    if not rows:
        sys.exit("no hay filas para esa cuenta en video_log.csv")

    metrics = {} if args.no_api else fetch_metrics(rows, args.account or "default")

    print(f"\n{len(rows)} video(s) en video_log.csv"
          f"{f' (cuenta {args.account})' if args.account else ''}\n")

    if args.videos:
        print_by_video(rows, metrics)
    else:
        print_by_variant(rows, metrics, args.min_videos)


if __name__ == "__main__":
    main()
