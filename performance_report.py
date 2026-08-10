"""Cruza video_log.csv (topic/estilo/duracion/keyword_score de cada video, ya
guardado por track_video.py al subir) con las metricas REALES de YouTube
Analytics (vistas, retencion, likes...) y exporta un solo CSV para estudiar
que funciono -- pedido usuario 22 jul 2026, a raiz de un video que mostraba
como bajar un excel asi desde YouTube Studio a mano (Analytics > Overview >
Ver mas > modo avanzado > Descargar). Esto hace lo mismo pero automatico via
API, para todos los videos ya subidos y sin tocar Studio.

Uso:
  py performance_report.py                       # todas las cuentas conocidas en el log
  py performance_report.py --account impixxel     # solo esa cuenta
  py performance_report.py --out reporte.csv

El CSV resultante se puede abrir en Excel/Sheets y ordenar exactamente igual
que en el video (por vistas, por duracion promedio vista, etc.) -- ademas el
script imprime un resumen con esa misma comparacion ya hecha (top vs bottom
por retencion, duracion del video vs performance, y si keyword_score/
title_score de la fase de research predicen algo real).
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

from track_video import LOG_PATH, FIELDS as LOG_FIELDS
import youtube_api

OUT_PATH = Path(__file__).resolve().parent / "performance_report.csv"

# columnas que vienen de la Analytics API (video_metrics_batch) -- se suman a
# las de video_log.csv en el CSV final. impressions/impressionsClickThroughRate
# pueden faltar si la cuenta/rango no las tiene disponibles.
METRIC_FIELDS = [
    "views",
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
    "likes",
    "comments",
    "subscribersGained",
    "shares",
    "impressions",
    "impressionsClickThroughRate",
]


def load_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_report(only_account: str | None = None) -> list[dict]:
    rows = load_log()
    if only_account:
        rows = [r for r in rows if (r.get("account") or "default") == only_account]

    by_account: dict[str, list[dict]] = {}
    for r in rows:
        acc = (
            r.get("account") or "default"
        )  # filas viejas (antes de sumar la columna 'account')
        by_account.setdefault(acc, []).append(r)

    combined = []
    for account, acc_rows in by_account.items():
        video_ids = [r["video_id"] for r in acc_rows if r.get("video_id")]
        print(f"[report] pidiendo metricas de {len(video_ids)} videos ({account})...")
        try:
            metrics = youtube_api.video_metrics_batch(video_ids, account=account)
        except Exception as e:
            print(
                f"[report] fallo al pedir metricas para '{account}': {e} -- se omite esa cuenta"
            )
            continue
        for r in acc_rows:
            m = metrics.get(r["video_id"], {})
            row = {k: r.get(k, "") for k in LOG_FIELDS}
            row["account"] = account
            for mf in METRIC_FIELDS:
                row[mf] = m.get(mf, "")
            combined.append(row)
    return combined


def _num(row: dict, field: str) -> float | None:
    v = row.get(field, "")
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def print_insights(rows: list[dict]) -> None:
    scored = [r for r in rows if _num(r, "views") is not None]
    if len(scored) < 4:
        print(
            "\n[insights] muy pocos videos con datos todavia para sacar conclusiones (minimo ~4)"
        )
        return

    print(f"\n[insights] {len(scored)} videos con metricas de {len(rows)} en el log\n")

    # 0. el video que mas minutos de visualizacion acumulo (metrica clave para
    #    watch time / requisitos de monetizacion, distinta de "mas vistas")
    with_minutes = [r for r in scored if _num(r, "estimatedMinutesWatched") is not None]
    if with_minutes:
        best = max(with_minutes, key=lambda r: _num(r, "estimatedMinutesWatched"))
        print(
            f"  Mas minutos de visualizacion: '{best.get('title', '')[:60]}' "
            f"({best.get('video_id')}) -> {_num(best, 'estimatedMinutesWatched'):,.0f} min, "
            f"{_num(best, 'views'):,.0f} vistas, {best.get('youtube_url', '')}"
        )

    # 1. retencion (averageViewPercentage) alta vs baja -- misma comparacion
    #    que el video de referencia (top 26 vs bottom 26 por avg view duration)
    with_pct = [r for r in scored if _num(r, "averageViewPercentage") is not None]
    if with_pct:
        n = max(
            1, len(with_pct) // 4
        )  # cuartil en vez de "26 fijo" (ese numero era para 5500 videos)
        by_pct = sorted(
            with_pct, key=lambda r: _num(r, "averageViewPercentage"), reverse=True
        )
        top = by_pct[:n]
        bottom = by_pct[-n:]
        top_views = statistics.mean(_num(r, "views") for r in top)
        bottom_views = statistics.mean(_num(r, "views") for r in bottom)
        print(
            f"  Retencion alta (top {n}, avg %view={statistics.mean(_num(r, 'averageViewPercentage') for r in top):.0f}%) "
            f"-> {top_views:,.0f} vistas promedio"
        )
        print(
            f"  Retencion baja (bottom {n}, avg %view={statistics.mean(_num(r, 'averageViewPercentage') for r in bottom):.0f}%) "
            f"-> {bottom_views:,.0f} vistas promedio"
        )

    # 2. duracion del video vs performance
    with_dur = [r for r in scored if _num(r, "duration_sec") is not None]
    if len(with_dur) >= 4:
        by_dur = sorted(with_dur, key=lambda r: _num(r, "duration_sec"))
        half = len(by_dur) // 2
        short_avg = statistics.mean(_num(r, "views") for r in by_dur[:half])
        long_avg = statistics.mean(_num(r, "views") for r in by_dur[half:])
        short_dur = statistics.mean(_num(r, "duration_sec") for r in by_dur[:half])
        long_dur = statistics.mean(_num(r, "duration_sec") for r in by_dur[half:])
        print(
            f"\n  Videos mas cortos (avg {short_dur:.0f}s) -> {short_avg:,.0f} vistas promedio"
        )
        print(
            f"  Videos mas largos  (avg {long_dur:.0f}s) -> {long_avg:,.0f} vistas promedio"
        )

    # 3. el research previo (vidIQ keyword_score/title_score) predice algo real?
    for score_field in ("keyword_score", "title_score"):
        with_score = [r for r in scored if _num(r, score_field) is not None]
        if len(with_score) >= 4:
            by_score = sorted(
                with_score, key=lambda r: _num(r, score_field), reverse=True
            )
            half = len(by_score) // 2
            high_avg = statistics.mean(_num(r, "views") for r in by_score[:half])
            low_avg = statistics.mean(_num(r, "views") for r in by_score[half:])
            print(f"\n  {score_field} alto -> {high_avg:,.0f} vistas promedio")
            print(f"  {score_field} bajo -> {low_avg:,.0f} vistas promedio")

    if not any(r.get("impressions") for r in scored):
        print(
            "\n  (impressions/CTR no disponibles via API para esta cuenta -- para ver el "
            "equivalente a 'viewed vs swiped away' de Shorts hay que revisarlo a mano en "
            "YouTube Studio > Analytics > Alcance)"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--account",
        default=None,
        help="limita a una cuenta (default/impixxel/...); sin esto usa todas las del log",
    )
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    rows = build_report(only_account=args.account)
    if not rows:
        print(
            "[report] video_log.csv vacio o sin videos de esa cuenta -- nada que reportar"
        )
        return 1

    out_path = Path(args.out)
    fieldnames = LOG_FIELDS + [m for m in METRIC_FIELDS if m not in LOG_FIELDS]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(
        f"[report] {len(rows)} filas -> {out_path} (abrilo en Excel/Sheets para ordenar/filtrar)"
    )

    print_insights(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
