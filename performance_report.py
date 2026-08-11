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
import json
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

# columnas derivadas (10 ago 2026, ANALISIS_OUTLIERS_PROPIOS.md §6): los KPI que
# el analisis de outliers propios exigio medir -- shares/1000 es LA palanca sin
# explotar del corpus (mediana de shares = 0 en 51 videos) y la retencion NO
# correlaciona con vistas (-0.127), asi que el ranking importante ya no es
# retencion sino accion social por mil vistas.
DERIVED_FIELDS = [
    "shares_per_1000_views",
    "subs_per_1000_views",
    # etiquetas del guion (regla 11) para correlacionar emocion/giro -> shares:
    # se leen del guion.json que pipeline.py guarda en cada carpeta de output
    "target_emotion",
    "twist_phrase",
]

ROOT = Path(__file__).resolve().parent


def _resolve_out_dir(value: str) -> Path:
    """Misma logica que experiments.resolve_out_dir: el log guarda solo el
    nombre de la carpeta, hay que probar con y sin 'output/' delante."""
    p = Path(value or "")
    if p.is_absolute():
        return p
    direct = ROOT / value
    if direct.exists():
        return direct
    return ROOT / "output" / value


def _enrich_row(row: dict) -> None:
    views = _num(row, "views")
    shares = _num(row, "shares")
    subs = _num(row, "subscribersGained")
    if views and views > 0:
        if shares is not None:
            row["shares_per_1000_views"] = f"{shares / views * 1000:.2f}"
        if subs is not None:
            row["subs_per_1000_views"] = f"{subs / views * 1000:.2f}"
    guion = _resolve_out_dir(row.get("output_dir", "")) / "guion.json"
    if guion.exists():
        try:
            data = json.loads(guion.read_text(encoding="utf-8"))
            row["target_emotion"] = data.get("target_emotion", "")
            row["twist_phrase"] = data.get("twist_phrase", "")
        except (OSError, json.JSONDecodeError):
            pass


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
            _enrich_row(row)
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

    # 4. shares/1000 vistas: el KPI que manda desde el analisis de outliers
    #    propios (9 ago 2026) -- cualquier video >5 shares entra a analisis
    with_shares = [
        r for r in scored if _num(r, "shares_per_1000_views") is not None
    ]
    if with_shares:
        by_shares = sorted(
            with_shares,
            key=lambda r: _num(r, "shares_per_1000_views"),
            reverse=True,
        )
        top_share = by_shares[0]
        med_shares = statistics.median(
            _num(r, "shares_per_1000_views") for r in by_shares
        )
        print(
            f"\n  shares/1000 vistas (mediana={med_shares:.2f}): "
            f"'{top_share.get('title', '')[:60]}' lidera con "
            f"{_num(top_share, 'shares_per_1000_views'):.2f} "
            f"({top_share.get('shares', '?')} shares en {top_share.get('views', '?')} vistas)"
        )
        outliers = [r for r in by_shares if (_num(r, "shares") or 0) >= 5]
        if outliers:
            print(
                f"  OUTLIERS DE SHARES (>=5): {len(outliers)} video(s) -- "
                + ", ".join(f"'{r.get('title', '')[:40]}'" for r in outliers[:5])
            )

    # 5. emocion objetivo del guion (regla 11) vs vistas/shares -- para
    #    responder 'que emocion conviene provocar' con datos propios
    with_emotion = [
        r
        for r in scored
        if r.get("target_emotion") and _num(r, "views") is not None
    ]
    if len(with_emotion) >= 3:
        by_emotion: dict[str, list[dict]] = {}
        for r in with_emotion:
            by_emotion.setdefault(r["target_emotion"], []).append(r)
        print("\n  Por emocion objetivo (vistas mediana | shares/1000 mediana):")
        for emo, group in sorted(
            by_emotion.items(), key=lambda kv: len(kv[1]), reverse=True
        ):
            med_views = statistics.median(_num(r, "views") for r in group)
            s1000 = [
                _num(r, "shares_per_1000_views")
                for r in group
                if _num(r, "shares_per_1000_views") is not None
            ]
            med_s = f"{statistics.median(s1000):.2f}" if s1000 else "n/d"
            print(f"    {emo:<10} n={len(group):<3} {med_views:>8,.0f} | {med_s}")

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
    fieldnames = (
        LOG_FIELDS
        + [m for m in METRIC_FIELDS if m not in LOG_FIELDS]
        + [d for d in DERIVED_FIELDS if d not in LOG_FIELDS]
    )
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
