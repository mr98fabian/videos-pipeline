"""Mineria semanal de temas con demanda real (ROADMAP.md §1.2, implementado 10 ago 2026).

El por que: los temas con demanda probada superan a los inventados, y las
preguntas de Reddit son dolor real -- gente que YA esta buscando la respuesta.
El video ganador de KoreX ("Como salir de deudas y dejar de pelar cable") salio
de exactamente ese patron: busqueda evergreen + slang local.

Que hace:
  1. Baja los posts top/hot de subreddits de finanzas personales (JSON publico
     de Reddit, sin API key -- solo User-Agent).
  2. Mina el AUTOCOMPLETADO de YouTube (suggestqueries.google.com) desde semillas
     de dolor financiero -- las frases que la gente YA esta escribiendo en el
     buscador de YouTube. Es la fuente mas alineada con la formula ganadora del
     video de pelar cable: busqueda evergreen + lenguaje de la calle.
  3. Filtra los que parecen PREGUNTA o dolor concreto (son los angulos con
     intencion de busqueda, no noticias).
  4. Descarta los que ya estan en topics.txt / used_topics.json / corridas
     anteriores de este script.
  5. Escribe los candidatos nuevos en topics_mined.txt (NO toca topics.txt
     directo: la seleccion final sigue siendo manual, ver ROADMAP §1.2).
     Con --to-topics los anexa a topics.txt para que --auto los tome solo.

Uso:
  py mine_topics.py                 # mina y escribe topics_mined.txt
  py mine_topics.py --to-topics     # ademas anexa los nuevos a topics.txt
  py mine_topics.py --limit 30      # posts por subreddit/sort (default 25)
  py mine_topics.py --no-reddit     # solo autocompletado (si Reddit 403-ea la red)

Nota Trends: Google Trends quedo fuera a proposito -- pytrends no es dependencia
del proyecto y su API no oficial rompe seguido; si se quiere, correrlo aparte y
pegar los resultados en topics.txt a mano.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
TOPICS_FILE = ROOT / "topics.txt"
USED_TOPICS_FILE = ROOT / "used_topics.json"
MINED_FILE = ROOT / "topics_mined.txt"

# mezcla EN/ES a proposito: KoreX es en español pero el dolor de
# r/personalfinance y r/povertyfinance se traduce 1:1 a LATAM; los subs en
# español dan el slang local que hizo ganar al video de pelar cable.
SUBREDDITS = [
    "personalfinance",
    "povertyfinance",
    "MexicoFinanciero",
    "ChileFinancial",
]

# Reddit 403-ea UAs obvias de bot; hace falta un UA de navegador realista
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
}

# un post "sirve de tema" si es pregunta/dolor, no noticia ni discusion meta
_QUESTION_HINTS = (
    "?",
    "how do",
    "how to",
    "how can",
    "why is",
    "why does",
    "what happens",
    "should i",
    "is it worth",
    "como ",
    "cómo ",
    "por que ",
    "por qué ",
    "que pasa",
    "qué pasa",
    "conviene",
    "vale la pena",
)
_SKIP_HINTS = (
    "[meta]",
    "weekly",
    "megathread",
    "discussion thread",
    "rant wednesday",
    "wiki",
)


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_posts(sub: str, limit: int) -> list[dict]:
    """Top del mes + hot actual de un subreddit; devuelve posts crudos."""
    posts = []
    for sort in (f"top.json?t=month&limit={limit}", f"hot.json?limit={limit}"):
        url = f"https://www.reddit.com/r/{sub}/{sort}"
        try:
            data = _fetch(url)
            posts.extend(data.get("data", {}).get("children", []))
        except (OSError, ValueError) as e:
            print(f"[mine] fallo {url}: {e} -- sigo con los demas")
        time.sleep(1.5)  # cortesia con el rate limit del JSON publico
    return posts


# semillas de dolor financiero para el autocompletado de YouTube -- la gente
# escribe estas frases TAL CUAL en el buscador, y cada sugerencia es un titulo
# con intencion de busqueda probada. Mezcla ES/EN como el canal.
SUGGEST_SEEDS = [
    "como salir de deudas",
    "como ahorrar",
    "como sobrevivir la quincena",
    "que pasa si no pago",
    "tarjeta de credito",
    "como salir del",
    "prestar plata",
    "cuanto debo ahorrar",
    "how to get out of debt",
    "living paycheck to paycheck",
    "credit card minimum payment",
    "what happens if you dont pay",
]


def fetch_suggestions(seeds: list[str]) -> list[str]:
    """Autocompletado de YouTube por semilla (JSONP publico de Google). Cada
    sugerencia es una frase que la gente escribe de verdad en el buscador."""
    suggestions = []
    for seed in seeds:
        url = (
            "https://suggestqueries.google.com/complete/search"
            f"?client=firefox&ds=yt&q={urllib.parse.quote(seed)}"
        )
        try:
            data = _fetch(url)
            suggestions.extend(s for s in data[1] if isinstance(s, str))
        except (OSError, ValueError) as e:
            print(f"[mine] fallo autocompletado '{seed}': {e} -- sigo con las demas")
        time.sleep(0.4)
    return suggestions


def is_topic_worthy(title: str) -> bool:
    t = title.lower()
    if any(s in t for s in _SKIP_HINTS):
        return False
    return any(h in t for h in _QUESTION_HINTS)


def normalize(title: str) -> str:
    return re.sub(r"[^a-z0-9áéíóúñü]+", " ", title.lower()).strip()


def already_known(norm_title: str, known: set[str]) -> bool:
    """Dedup difuso barato: si >=70% de las palabras ya aparecen en un tema
    conocido, se considera repetido (los titulos de Reddit no llegan listos
    para ser guion, asi que la comparacion exacta no sirve)."""
    words = set(norm_title.split())
    if not words:
        return True
    for k in known:
        kws = set(k.split())
        if not kws:
            continue
        overlap = len(words & kws) / len(words | kws)
        if overlap >= 0.7:
            return True
    return False


def load_known() -> set[str]:
    known = set()
    for path in (TOPICS_FILE, MINED_FILE):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    known.add(normalize(line))
    if USED_TOPICS_FILE.exists():
        try:
            used = json.loads(USED_TOPICS_FILE.read_text(encoding="utf-8"))
            for t in used if isinstance(used, list) else used.keys():
                known.add(normalize(str(t)))
        except json.JSONDecodeError:
            pass
    return known


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=25, help="posts por subreddit/sort")
    ap.add_argument(
        "--to-topics",
        action="store_true",
        help="anexa los candidatos nuevos a topics.txt (ademas de topics_mined.txt)",
    )
    ap.add_argument(
        "--no-reddit",
        dest="reddit",
        action="store_false",
        default=True,
        help="salta Reddit y mina solo el autocompletado de YouTube (util si "
        "Reddit 403-ea la red actual, verificado 10 ago 2026 desde esta maquina)",
    )
    args = ap.parse_args()

    known = load_known()
    candidates: list[tuple[str, int, str]] = []  # (titulo, score, fuente)
    if args.reddit:
        for sub in SUBREDDITS:
            for child in fetch_posts(sub, args.limit):
                data = child.get("data", {})
                title = (data.get("title") or "").strip()
                if not title or not is_topic_worthy(title):
                    continue
                if already_known(normalize(title), known):
                    continue
                candidates.append((title, int(data.get("score", 0)), f"r/{sub}"))

    for sug in fetch_suggestions(SUGGEST_SEEDS):
        if already_known(normalize(sug), known):
            continue
        # las sugerencias ya vienen filtradas por intencion de busqueda real;
        # score sintetico para que compitan con Reddit en el orden
        candidates.append((sug, 50, "yt-autocomplete"))

    # orden por score descendente: el dolor mas votado primero
    candidates.sort(key=lambda c: c[1], reverse=True)

    if not candidates:
        print("[mine] sin candidatos nuevos (todo ya estaba minado o en topics.txt)")
        return 0

    header = (
        f"# minados {time.strftime('%Y-%m-%d')} (Reddit + autocompletado YouTube) "
        "-- revisar y pasar los buenos a topics.txt (o correr con --to-topics)\n"
    )
    lines = [f"{title}  # {src} score={score}\n" for title, score, src in candidates]
    with MINED_FILE.open("a", encoding="utf-8") as f:
        f.write(header)
        f.writelines(lines)

    print(f"[mine] {len(candidates)} candidatos nuevos -> {MINED_FILE}")
    for title, score, src in candidates[:10]:
        print(f"  [{score:>5}] {src:<18} {title[:90]}")

    if args.to_topics:
        with TOPICS_FILE.open("a", encoding="utf-8") as f:
            for title, _score, _sub in candidates:
                f.write(f"{title}\n")
        print(f"[mine] anexados tambien a {TOPICS_FILE} (--auto los tomara)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
