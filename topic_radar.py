"""Radar de temas para HiddenFacts: antes de producir un video, cruza las
EFEMERIDES del dia (Wikipedia "On this day", API gratis sin auth) con los
criterios ya validados del canal (villano nombrable, tema del nicho, aniversario
redondo, evitar saturados) y devuelve una SHORTLIST rankeada de temas con
ventaja de "timeliness" -- en vez de elegir a dedo de topics.txt.

Para Shorts el feed manda sobre la busqueda (96.7% del trafico de HiddenFacts es
feed), asi que el objetivo NO es SEO de keywords sino RESONANCIA + FRESCURA: un
hecho historico con un engano/secreto que ademas cae en su aniversario esta
semana. La senal viral mas fuerte sigue siendo los OUTLIERS de vidIQ; este radar
deja un slot para enchufarlos (--outliers), pero no depende de ellos.

Uso:
  py topic_radar.py                      # hoy + 7 dias, top 15
  py topic_radar.py --days 14 --top 25
  py topic_radar.py --date 08-15         # una fecha puntual MM-DD
  py topic_radar.py --append-topics      # vuelca el top a topics.txt
  py topic_radar.py --outliers vidiq.txt # sube el score de temas que matcheen
                                          # un outlier real (una linea por titulo)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
CUR_YEAR = 2026  # se ajusta abajo con la fecha real si esta disponible

# Temas del nicho -> keywords que los delatan en el texto del evento. Un evento
# que no matchea NINGUN tema se descarta (no es del canal).
NICHE_THEMES: dict[str, tuple[str, ...]] = {
    "espionaje": ("spy", "espionage", "intelligence", "cia", "kgb", "mi6", "mi5",
                   "gestapo", "agent", "defector", "codebreak", "cipher", "enigma",
                   "cryptolog", "double agent", "counterintelligence", "mossad"),
    "wwii": ("nazi", "hitler", "wehrmacht", "world war ii", "wwii", "d-day",
              "resistance", "sabotage", "commando", "occupation", "holocaust",
              "partisan", "gestapo", "waffen", "reich", "auschwitz", "blitz"),
    "guerra_fria": ("soviet", "stalin", "cold war", "nuclear", "atomic", "manhattan project",
                     "cuban missile", "berlin wall", "kgb", "defect", "iron curtain",
                     "mkultra", "u-2", "bay of pigs"),
    "cons_fraude": ("hoax", "con man", "con artist", "fraud", "scam", "forgery",
                     "counterfeit", "impostor", "swindle", "ponzi", "embezzle", "fake"),
    "misterio": ("mystery", "disappear", "vanished", "unsolved", "unexplained",
                  "cover-up", "coverup", "conspiracy", "classified", "declassified",
                  "secret", "hidden", "mysterious"),
    "heroes_ocultos": ("rescued", "saved", "smuggled", "secretly", "medal of honor",
                        "hid ", "sheltered", "forged papers", "underground railroad"),
    "asesinato_golpe": ("assassinat", "coup", "plot to kill", "conspir", "overthrow",
                         "regicide", "poison"),
}

# Antagonista famoso nombrable en el titulo = la senal validada mas fuerte del
# canal (ver memoria titulo-antagonista-famoso). Presencia -> bonus grande.
NAMEABLE_ANTAGONISTS = (
    "hitler", "stalin", "mussolini", "hirohito", "mao", "castro", "franco",
    "kgb", "cia", "gestapo", "the ss", "waffen-ss", "nazi", "mafia", "cosa nostra",
    "hoover", "beria", "himmler", "goebbels", "napoleon", "lenin", "trotsky",
    "pol pot", "idi amin", "pinochet", "the stasi", "the cartel", "escobar",
)

# Temas sobre-explotados en el nicho -> penalizacion (ver criterio-guiones).
SATURATED = (
    "bermuda triangle", "flight 19", "area 51", "roswell", "loch ness",
    "jack the ripper", "amelia earhart", "d.b. cooper", "titanic",
)


def _fetch_onthisday(month: int, day: int) -> list[dict]:
    """Eventos + 'selected' (curados) de Wikipedia On this day para MM/DD."""
    out: list[dict] = []
    for kind in ("selected", "events"):
        url = (f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/"
               f"{kind}/{month:02d}/{day:02d}")
        req = urllib.request.Request(url, headers={"User-Agent": "HiddenFactsRadar/1.0 (topic research)"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"[radar] aviso: fallo {kind} {month:02d}/{day:02d}: {e}", file=sys.stderr)
            continue
        for ev in data.get(kind, []) or data.get("events", []):
            out.append({"year": ev.get("year"), "text": ev.get("text", ""), "kind": kind})
    # dedup por texto
    seen, uniq = set(), []
    for ev in out:
        key = ev["text"][:80]
        if key not in seen:
            seen.add(key)
            uniq.append(ev)
    return uniq


# Acronimos/palabras cortas ambiguas: se exigen como PALABRA COMPLETA (\b...\b),
# si no "cia" matchea dentro de "official/comercial/Valencia" (bug real 22 jul).
# El resto usa solo limite inicial (\bterm) para permitir plurales/derivados
# ("secret" -> "secrets", "assassinat" -> "assassination").
_EXACT = {"cia", "kgb", "mi6", "mi5", "ss", "u-2", "mao", "spy"}


def _matches(low: str, terms) -> list[str]:
    hits = []
    for t in terms:
        pat = r"\b" + re.escape(t) + (r"\b" if t in _EXACT else "")
        if re.search(pat, low):
            hits.append(t)
    return hits


def _themes_of(text: str) -> list[str]:
    low = text.lower()
    return [name for name, kws in NICHE_THEMES.items() if _matches(low, kws)]


def _antagonist_in(text: str) -> str | None:
    low = text.lower()
    hits = _matches(low, NAMEABLE_ANTAGONISTS)
    return hits[0] if hits else None


def _anniversary_bonus(year: int | None, on_year: int) -> tuple[int, int]:
    """(bonus, edad). Aniversarios redondos = mas 'timeliness'. 80/75/50/100
    pesan mas (WWII/guerra fria caen justo en esa ventana en 2026)."""
    if not year:
        return 0, 0
    age = on_year - int(year)
    if age <= 0:
        return 0, age
    if age in (50, 75, 80, 100, 25):
        return 3, age
    if age in (40, 60, 70, 90, 125, 150):
        return 2, age
    if age % 10 == 0:
        return 1, age
    return 0, age


def _hook_angle(text: str, antagonist: str | None) -> str:
    """Plantilla de angulo (no el guion final -- eso lo escribe /canal guion)."""
    if antagonist:
        return f"Nombrar a {antagonist.title()} en el titulo; secreto/engaño detras del hecho."
    return "Enmarcar como secreto/engaño oculto detras del hecho; buscar el villano nombrable."


def score_event(ev: dict, on_year: int, outlier_terms: list[str]) -> dict | None:
    text = ev["text"]
    themes = _themes_of(text)
    if not themes:
        return None  # fuera del nicho
    low = text.lower()
    if any(s in low for s in SATURATED):
        sat_pen = -5
    else:
        sat_pen = 0
    antagonist = _antagonist_in(text)
    anni_bonus, age = _anniversary_bonus(ev.get("year"), on_year)
    outlier_hit = any(t and t in low for t in outlier_terms)

    score = (
        min(len(themes), 3) * 2        # fuerza/variedad de tema (cap 3)
        + (4 if antagonist else 0)     # villano nombrable (senal #1)
        + anni_bonus                    # aniversario redondo
        + (3 if outlier_hit else 0)    # matchea un outlier real de vidIQ
        + sat_pen                       # saturacion
    )
    return {
        "score": score, "year": ev.get("year"), "age": age, "text": text,
        "themes": themes, "antagonist": antagonist, "anni_bonus": anni_bonus,
        "outlier_hit": outlier_hit, "angle": _hook_angle(text, antagonist),
    }


def run(days: int, top: int, start: date, outlier_terms: list[str]) -> list[dict]:
    on_year = start.year
    cands: list[dict] = []
    for i in range(days):
        if i:
            time.sleep(0.5)  # cortesia con la API de Wikipedia (evita 429 en rafaga)
        d = start + timedelta(days=i)
        for ev in _fetch_onthisday(d.month, d.day):
            sc = score_event(ev, on_year, outlier_terms)
            if sc:
                sc["date"] = d.isoformat()
                cands.append(sc)
    cands.sort(key=lambda c: (c["score"], c["age"]), reverse=True)
    return cands[:top]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7, help="ventana desde hoy (default 7)")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--date", default=None, help="fecha puntual MM-DD (ignora --days)")
    ap.add_argument("--outliers", default=None,
                     help="archivo con titulos de outliers de vidIQ (1 por linea) "
                          "para subir el score de temas que matcheen; 'auto' los "
                          "trae en vivo via vidiq_tools (YouTube + TikTok/IG, ~25 cr)")
    ap.add_argument("--append-topics", action="store_true",
                     help="agrega el top al final de topics.txt (temas nuevos, sin duplicar)")
    args = ap.parse_args()

    outlier_terms: list[str] = []
    if args.outliers == "auto":
        # fetch en vivo (YouTube + TikTok/IG); si vidIQ falla, el radar sigue sin la capa
        try:
            import subprocess
            r = subprocess.run(
                [sys.executable, str(Path(__file__).parent / "vidiq_tools.py"),
                 "radar-terms", "--cross-platform"],
                capture_output=True, text=True, encoding="utf-8", timeout=180)
            titles = [ln for ln in (r.stdout or "").splitlines() if ln and not ln.startswith("#")]
            outlier_terms = [w.strip().lower() for t in titles for w in t.split()
                             if len(w.strip()) >= 4]
            print(f"[radar] outliers en vivo: {len(titles)} titulos ({len(outlier_terms)} terminos)")
        except Exception as e:
            print(f"[radar] aviso: outliers auto fallo ({e}), sigo sin capa de outliers")
    elif args.outliers:
        p = Path(args.outliers)
        if p.exists():
            outlier_terms = [w.strip().lower() for w in p.read_text(encoding="utf-8").split()
                             if len(w.strip()) >= 4]
            print(f"[radar] {len(outlier_terms)} terminos de outliers cargados de {p.name}")
        else:
            print(f"[radar] aviso: no existe {p}, sigo sin capa de outliers")

    if args.date:
        mm, dd = args.date.split("-")
        start = date(CUR_YEAR, int(mm), int(dd))
        days = 1
    else:
        start = date.today()
        days = args.days

    results = run(days, args.top, start, outlier_terms)
    if not results:
        print("[radar] sin candidatos del nicho en esa ventana (raro; revisa la API)")
        return 1

    print(f"\n=== RADAR DE TEMAS — {start.isoformat()} (+{days-1}d) — top {len(results)} ===\n")
    for i, c in enumerate(results, 1):
        anni = f" · {c['age']}º aniversario" if c["anni_bonus"] else ""
        vil = f" · villano: {c['antagonist'].title()}" if c["antagonist"] else ""
        out = " · [OUTLIER]" if c["outlier_hit"] else ""
        print(f"{i:2d}. [score {c['score']}] {c['year']} — {', '.join(c['themes'])}{anni}{vil}{out}")
        print(f"    {c['text']}")
        print(f"    -> {c['angle']}\n")

    if args.append_topics:
        tp = ROOT / "topics.txt"
        existing = tp.read_text(encoding="utf-8") if tp.exists() else ""
        added = 0
        with tp.open("a", encoding="utf-8") as f:
            for c in results:
                line = c["text"].split(".")[0].strip()[:90]
                if line and line not in existing:
                    f.write(f"\n{line}")
                    added += 1
        print(f"[radar] {added} temas nuevos agregados a topics.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
