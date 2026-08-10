"""Suite vidIQ por HTTP directo (sin depender del MCP de la sesion).

El MCP de vidIQ a veces exige re-auth OAuth y sus tools no cargan; este cliente
habla JSON-RPC directo con https://mcp.vidiq.com/mcp usando la API key, asi que
funciona en cualquier sesion (incluidos runs programados). La key se lee de la
variable de entorno VIDIQ_API_KEY o del archivo vidiq_key.txt (gitignored).

Subcomandos (cada llamada gasta ~5 creditos; `balance` es gratis):
  py vidiq_tools.py balance
  py vidiq_tools.py outliers "stalin"                # outliers de YouTube por keyword
  py vidiq_tools.py xoutliers "wwii secret"          # outliers de TikTok+Instagram
  py vidiq_tools.py watch <url-short>                # desglose escena por escena
  py vidiq_tools.py transcript <video_id> [...]      # transcripciones (patrones de guion)
  py vidiq_tools.py similar <video_id>               # hermanos exitosos de un hit
  py vidiq_tools.py comments <video_id|@handle>      # minar comentarios (demanda de temas)
  py vidiq_tools.py radar-terms                      # titulos de outliers del nicho, 1/linea
                                                     #   (formato que consume topic_radar --outliers)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
URL = "https://mcp.vidiq.com/mcp"

# queries fijas del nicho HiddenFacts para el radar (ampliar con cuidado: 5 cr c/u)
NICHE_QUERIES = ["history secret", "wwii story", "declassified"]
XPLATFORM_AUDIENCE = "Culture/Region: US/Western Europe; Global: true"

_sid = None
_next_id = [1]


def _key() -> str:
    k = os.environ.get("VIDIQ_API_KEY")
    if k:
        return k.strip()
    f = ROOT / "vidiq_key.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    print("ERROR: falta VIDIQ_API_KEY (o vidiq_key.txt en la raiz del repo)")
    raise SystemExit(1)


def _post(payload: dict):
    global _sid
    h = {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if _sid:
        h["Mcp-Session-Id"] = _sid
    req = urllib.request.Request(URL, json.dumps(payload).encode(), h)
    with urllib.request.urlopen(req, timeout=120) as r:
        _sid = r.headers.get("Mcp-Session-Id", _sid)
        body = r.read().decode("utf-8", "replace")
    datas = [ln[5:].strip() for ln in body.splitlines() if ln.startswith("data:")]
    return (
        json.loads(datas[-1]) if datas else (json.loads(body) if body.strip() else None)
    )


def _rpc(method: str, params: dict | None = None, notify: bool = False):
    p = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if not notify:
        p["id"] = _next_id[0]
        _next_id[0] += 1
    return _post(p)


def _init():
    _rpc(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "vidiq-tools", "version": "1.0"},
        },
    )
    _rpc("notifications/initialized", notify=True)


def call(name: str, args: dict) -> str:
    """Llama un tool y devuelve el texto crudo de la respuesta."""
    _init()
    r = _rpc("tools/call", {"name": name, "arguments": args})
    if "error" in r:
        raise RuntimeError(f"vidIQ {name}: {r['error'].get('message', r['error'])}")
    return "\n".join(c.get("text", "") for c in r["result"].get("content", []))


def call_json(name: str, args: dict):
    return json.loads(call(name, args))


# ---------------------------------------------------------------- subcomandos


def cmd_balance(_a) -> int:
    d = call_json("vidiq_balance", {})
    print(
        f"creditos: {d.get('totalCredits')} (renovables {d.get('renewableCredits')}, "
        f"extra {d.get('addOnCredits')}; renuevan {d.get('renewableResetsAt', '?')[:10]})"
    )
    return 0


def cmd_outliers(a) -> int:
    d = call_json(
        "vidiq_outliers",
        {
            "keyword": a.query,
            "contentType": "short",
            "publishedWithin": "threeMonths",
            "limit": a.limit,
        },
    )
    for v in d.get("videos", d.get("results", [])):
        if isinstance(v, dict):
            print(
                f"x{v.get('breakoutScore', '?'):>6} | {v.get('viewCount', '?'):>9} vistas | "
                f"{v.get('vph', '?'):>5} vph | {str(v.get('channelTitle', ''))[:20]:20} | "
                f"{str(v.get('videoTitle', ''))[:60]}"
            )
    return 0


def cmd_xoutliers(a) -> int:
    d = call_json(
        "vidiq_instagram_tiktok_outlier_search",
        {
            "query": a.query,
            "audienceQuery": XPLATFORM_AUDIENCE,
            "resultsPerPlatform": a.limit,
            "collapseByCreator": True,
        },
    )
    for plat in ("tiktok", "instagram"):
        for v in d.get(plat, d.get(f"{plat}Results", [])) or []:
            if isinstance(v, dict):
                cap = str(v.get("caption", v.get("description", "")))[:80].replace(
                    "\n", " "
                )
                print(
                    f"[{plat}] {v.get('outlierScore', '?')} | {v.get('views', v.get('playCount', '?'))} vistas | {cap}"
                )
    return 0


def cmd_title_patterns(a) -> int:
    """Busca Shorts con outlier score cercano a 100x en el nicho, junta sus
    titulos, y le pide a Claude que extraiga el PATRON (estructura, promesa,
    palabras que se repiten) -- no para copiar el titulo, para replicar la
    formula. Ver memoria titulo-antagonista-famoso / criterio-guiones-post-analisis-28d
    para lo ya validado; esto es la version automatizada de ese analisis."""
    import anthropic

    queries = a.query or NICHE_QUERIES
    seen, hits = set(), []
    for q in queries:
        try:
            d = call_json(
                "vidiq_outliers",
                {
                    "keyword": q,
                    "contentType": "short",
                    "publishedWithin": "threeMonths",
                    "limit": 15,
                },
            )
        except Exception as e:
            print(f"[title-patterns] fallo '{q}': {e}", file=sys.stderr)
            continue
        for v in d.get("videos", d.get("results", [])):
            if not isinstance(v, dict):
                continue
            t = (v.get("videoTitle") or "").strip()
            score = v.get("breakoutScore") or 0
            if t and t.lower() not in seen and score >= a.min_score:
                seen.add(t.lower())
                hits.append((score, t))
    hits.sort(reverse=True)
    top = hits[: a.top]
    if not top:
        print(
            f"[title-patterns] nada por encima de x{a.min_score}. Baja --min-score o prueba otras queries."
        )
        return 1

    print(f"[title-patterns] {len(top)} titulos (x{top[-1][0]}-x{top[0][0]}):")
    for score, t in top:
        print(f"  x{score:>4} | {t}")

    titles_block = "\n".join(f"- ({s}x) {t}" for s, t in top)
    prompt = (
        "Estos son titulos de YouTube Shorts con outlier score cercano a 100x "
        "(muy por encima de la mediana de su propio canal) en el nicho de "
        f"'{a.niche}'.\n\n{titles_block}\n\n"
        "Analiza SOLO la estructura, no el contenido especifico: que patrones de "
        "titulo se repiten, que tipo de promesa usan (resultado, curiosidad, "
        "antagonista nombrado, cifra, pregunta), que estructura gramatical "
        "domina, y que palabras de gancho aparecen mas. Termina con 3 formulas "
        "de titulo reutilizables (con placeholders tipo [ANTAGONISTA], [CIFRA], "
        "[CONSECUENCIA]) que se puedan aplicar a un titulo NUEVO de este nicho, "
        "sin copiar ningun titulo de la lista."
    )
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    txt = next((b.text for b in resp.content if b.type == "text"), "")
    print("\n" + txt)
    return 0


def cmd_watch(a) -> int:
    print(call("vidiq_watch_shortform_content", {"url": a.url}))
    return 0


def cmd_transcript(a) -> int:
    for vid in a.video_ids:
        try:
            d = call_json("vidiq_video_transcript", {"videoId": vid})
            txt = d.get("transcript", d) if isinstance(d, dict) else d
            print(f"=== {vid}\n{txt}\n")
        except Exception as e:  # un video sin captions no debe tumbar el batch
            print(f"=== {vid}\nERROR: {e}\n")
    return 0


def cmd_similar(a) -> int:
    d = call_json(
        "vidiq_similar_videos",
        {
            "videoId": a.video_id,
            "contentType": "short",
            "excludeSeedChannel": True,
            "limit": a.limit,
        },
    )
    for v in d.get("videos", d.get("results", [])):
        if isinstance(v, dict):
            print(
                f"{v.get('viewCount', '?'):>9} vistas | {str(v.get('channelTitle', ''))[:20]:20} | "
                f"{str(v.get('videoTitle', ''))[:60]}"
            )
    return 0


def cmd_comments(a) -> int:
    key = "channelId" if a.target.startswith(("@", "UC")) else "videoId"
    d = call_json(
        "vidiq_video_comments",
        {key: a.target, "order": "relevance", "maxResult": a.limit},
    )
    for c in d.get("comments", d.get("threads", [])):
        if isinstance(c, dict):
            txt = str(c.get("text", c.get("topLevelComment", "")))[:110].replace(
                "\n", " "
            )
            print(f"{c.get('likeCount', 0):>5} likes | {txt}")
    return 0


def cmd_radar_terms(a) -> int:
    """Titulos de outliers del nicho (YouTube + TikTok/IG), uno por linea.
    Es el formato que consume `topic_radar.py --outliers <archivo>`."""
    seen = set()
    for q in NICHE_QUERIES:
        try:
            d = call_json(
                "vidiq_outliers",
                {
                    "keyword": q,
                    "contentType": "short",
                    "publishedWithin": "threeMonths",
                    "limit": 10,
                },
            )
            for v in d.get("videos", d.get("results", [])):
                t = (v.get("videoTitle") or "").strip() if isinstance(v, dict) else ""
                if t and t.lower() not in seen:
                    seen.add(t.lower())
                    print(t)
        except Exception as e:
            print(f"# [radar-terms] fallo '{q}': {e}", file=sys.stderr)
    if a.cross_platform:
        for q in NICHE_QUERIES[:2]:  # limitar gasto
            try:
                md = call(
                    "vidiq_instagram_tiktok_outlier_search",
                    {
                        "query": q,
                        "audienceQuery": XPLATFORM_AUDIENCE,
                        "resultsPerPlatform": 5,
                        "collapseByCreator": True,
                    },
                )
                # markdown: lineas `**@handle** — "caption"`
                import re as _re

                for cap in _re.findall(r'\*\*@[\w.]+\*\* — "([^"]+)"', md):
                    line = cap.strip()[:120]
                    if line and line.lower() not in seen:
                        seen.add(line.lower())
                        print(line)
            except Exception as e:
                print(f"# [radar-terms] fallo x-platform '{q}': {e}", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("balance")
    p = sub.add_parser("outliers")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=15)
    p = sub.add_parser("xoutliers")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=8)
    p = sub.add_parser("watch")
    p.add_argument("url")
    p = sub.add_parser("transcript")
    p.add_argument("video_ids", nargs="+")
    p = sub.add_parser("similar")
    p.add_argument("video_id")
    p.add_argument("--limit", type=int, default=12)
    p = sub.add_parser("comments")
    p.add_argument("target")
    p.add_argument("--limit", type=int, default=25)
    p = sub.add_parser("radar-terms")
    p.add_argument("--cross-platform", action="store_true")
    p = sub.add_parser(
        "title-patterns",
        help="titulos x100 del nicho -> Claude extrae la formula reutilizable",
    )
    p.add_argument("query", nargs="*", help="keywords (por defecto NICHE_QUERIES)")
    p.add_argument("--niche", default="historia oculta / WWII / espionaje")
    p.add_argument(
        "--min-score",
        type=float,
        default=40.0,
        help="outlier score minimo para entrar al analisis",
    )
    p.add_argument("--top", type=int, default=20)
    a = ap.parse_args()
    return {
        "balance": cmd_balance,
        "outliers": cmd_outliers,
        "xoutliers": cmd_xoutliers,
        "watch": cmd_watch,
        "transcript": cmd_transcript,
        "similar": cmd_similar,
        "comments": cmd_comments,
        "radar-terms": cmd_radar_terms,
        "title-patterns": cmd_title_patterns,
    }[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
