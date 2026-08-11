"""Digest mensual datos -> prompt (ROADMAP.md §2.7, implementado 10 ago 2026).

La ventaja compuesta del proyecto: cerrar el ciclo datos reales -> guion. Nadie
mas en el nicho lo hace sistematicamente. Este script es el artefacto del loop:
lee performance_report.csv (que ya cruza video_log + Analytics + guion.json con
los KPI de la regla 11) y produce FEEDBACK_DIGEST.md, el resumen que se pega en
la revision mensual de SCRIPT_PROMPT / reglas de guion.

Uso:
  py performance_report.py        # primero: refresca el CSV (necesita token Analytics)
  py feedback_digest.py           # despues: genera FEEDBACK_DIGEST.md

Si el token de Analytics esta caducado, correr una vez cualquier comando de
youtube_api (ej. py track_video.py --help NO basta: hay que llamar la API --
py performance_report.py mismo sirve) y el navegador se abre solo para
re-autorizar (InstalledAppFlow.run_local_server, ver youtube_api.py:95-98).
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "performance_report.csv"
OUT = ROOT / "FEEDBACK_DIGEST.md"


def _num(v: str) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _median(nums: list[float]) -> float | None:
    return statistics.median(nums) if nums else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", default=str(REPORT))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument(
        "--min-views",
        type=int,
        default=50,
        help="ignora videos con menos vistas (ruido de no-distribuidos)",
    )
    args = ap.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"[digest] no existe {report_path} -- corre primero: py performance_report.py")
        return 1

    with report_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    rows = [r for r in rows if (_num(r.get("views", "")) or 0) >= args.min_views]
    if len(rows) < 4:
        print(f"[digest] solo {len(rows)} videos con >= {args.min_views} vistas; minimo 4")
        return 1

    L: list[str] = []
    L.append(f"# Feedback digest datos -> prompt — {datetime.now(tz=timezone.utc).date().isoformat()}")
    L.append("")
    L.append(f"Corpus: {len(rows)} videos con >= {args.min_views} vistas. "
             "Generado por `feedback_digest.py` sobre `performance_report.csv`. "
             "Regla del corpus: nuestros datos medidos ganan sobre benchmarks externos.")
    L.append("")

    # 1. outliers de shares (la palanca #1 del corpus)
    with_s = [r for r in rows if _num(r.get("shares_per_1000_views", "")) is not None]
    if with_s:
        top = sorted(with_s, key=lambda r: _num(r["shares_per_1000_views"]), reverse=True)[:5]
        med = _median([_num(r["shares_per_1000_views"]) for r in with_s])
        L.append(f"## 1. Shares/1000 vistas (mediana del corpus: {med:.2f})")
        L.append("")
        L.append("| Video | Vistas | Shares | Shares/1000 | Emocion |")
        L.append("|---|---|---|---|---|")
        for r in top:
            L.append(
                f"| {r.get('title', '')[:50]} | {r.get('views')} | {r.get('shares')} "
                f"| {_num(r['shares_per_1000_views']):.2f} | {r.get('target_emotion') or '—'} |"
            )
        L.append("")
        L.append("**Accion:** cualquier video >2x la mediana entra a analisis de "
                 "outliers (`ANALISIS_OUTLIERS_PROPIOS.md`): extraer que lo hizo "
                 "compartible y convertirlo en regla del prompt.")
        L.append("")

    # 2. emocion -> rendimiento
    with_e = [r for r in rows if r.get("target_emotion")]
    if len(with_e) >= 3:
        by_emo: dict[str, list[dict]] = {}
        for r in with_e:
            by_emo.setdefault(r["target_emotion"], []).append(r)
        L.append("## 2. Emocion objetivo -> rendimiento")
        L.append("")
        L.append("| Emocion | n | Vistas mediana | Shares/1000 mediana | Subs/1000 mediana |")
        L.append("|---|---|---|---|---|")
        for emo, g in sorted(by_emo.items(), key=lambda kv: len(kv[1]), reverse=True):
            mv = _median([_num(r["views"]) for r in g if _num(r.get("views")) is not None])
            ms = _median([_num(r["shares_per_1000_views"]) for r in g if _num(r.get("shares_per_1000_views", "")) is not None])
            mu = _median([_num(r["subs_per_1000_views"]) for r in g if _num(r.get("subs_per_1000_views", "")) is not None])
            fmt = lambda x: f"{x:.2f}" if x is not None else "n/d"
            L.append(f"| {emo} | {len(g)} | {mv:,.0f} | {fmt(ms)} | {fmt(mu)} |")
        L.append("")
        best = max(by_emo.items(), key=lambda kv: _median([_num(r["views"]) for r in kv[1] if _num(r.get("views")) is not None]) or 0)
        L.append(f"**Accion:** priorizar `{best[0]}` como `target_emotion` por "
                 "defecto hasta que otro la supere con n>=3.")
        L.append("")

    # 3. bandas de palabras (replica del analisis de outliers, se actualiza solo)
    with_w = [r for r in rows if _num(r.get("word_count", "")) is not None]
    if len(with_w) >= 4:
        bands = {"ultra (<25)": (0, 25), "corto (25-80)": (25, 80),
                 "medio (80-120)": (80, 120), "largo (120+)": (120, 10**9)}
        L.append("## 3. Palabras del guion -> rendimiento")
        L.append("")
        L.append("| Banda | n | Vistas mediana | Shares/1000 mediana |")
        L.append("|---|---|---|---|")
        for name, (lo, hi) in bands.items():
            g = [r for r in with_w if lo <= _num(r["word_count"]) < hi]
            if not g:
                continue
            mv = _median([_num(r["views"]) for r in g if _num(r.get("views")) is not None])
            ms = _median([_num(r["shares_per_1000_views"]) for r in g if _num(r.get("shares_per_1000_views", "")) is not None])
            L.append(f"| {name} | {len(g)} | {mv:,.0f} | {f'{ms:.2f}' if ms is not None else 'n/d'} |")
        L.append("")
        L.append("**Accion:** comparar contra el sweet spot medido (80-120 "
                 "palabras, `ANALISIS_OUTLIERS_PROPIOS.md` §1); si la banda "
                 "ganadora cambio, ajustar el largo objetivo del prompt.")
        L.append("")

    # 4. pendientes del loop
    L.append("## 4. Pendientes del loop")
    L.append("")
    L.append("- Retencion segmentada 0-6s y 6-10%: la Analytics API no entrega "
             "curvas por segundo; bajar el CSV de retencion de YouTube Studio "
             "(Analytics > Contenido > video > Retencion) para los outliers y "
             "guardarlo como `retencion_<video_id>.json` en la carpeta de output.")
    L.append("- Revisar este digest el primer lunes del mes y tocar SOLO una "
             "regla del prompt a la vez (si se cambian dos, la atribucion se "
             "pierde -- ver `experiments.py`).")

    out_path = Path(args.out)
    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[digest] {len(rows)} videos -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
