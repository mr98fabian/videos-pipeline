"""Hook machine: deriva la rubrica de ganchos DE LOS DATOS, no de mis prejuicios.

Idea robada del workflow 5 de Kallaway (1 ago 2026), pero montada sobre vidIQ en
vez de Sandcastles, que es un segundo servicio de pago haciendo lo mismo.

El problema real que resuelve: las reglas 9, 9b, 9c y 9f del `SCRIPT_PROMPT`
salieron de que yo leyera UNA transcripcion. Suenan bien y pueden estar mal.
Esta herramienta mide los primeros segundos de N ganadores reales y saca la
distribucion, asi que puede **desmentir** esas reglas en vez de confirmarlas.
Si 18 de 20 ganadores abren con pregunta, la regla 9 esta mal y se cambia.

Tres etapas, cada una guarda en disco para no repetir llamadas caras:

    py hook_machine.py collect --canal @StoryModeOn --n 20 --min-views 300000
    py hook_machine.py rubric
    py hook_machine.py score "On a Sunday in March I sent the same file to forty people"

`collect` cuesta 5 creditos de vidIQ por video (outliers 5 + una transcripcion
por video). Comprueba el saldo ANTES y se niega a empezar si no llega, para no
gastar la mitad y quedarse a medias.
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import vidiq_tools as V  # noqa: E402
import pipeline as P  # noqa: E402

CORPUS = ROOT / "assets" / "hook_corpus.json"
COSTE_POR_LLAMADA = 5
HOOK_PALABRAS = 45   # ~10s de narracion: la ventana donde se decide el scroll


# ---------------------------------------------------------------- medidas
# Cada medida devuelve un bool o un numero. Son deliberadamente mecanicas:
# el valor esta en la DISTRIBUCION sobre muchos ganadores, no en el juicio
# sobre uno. Varias corresponden 1:1 con una regla del SCRIPT_PROMPT, para
# que el informe diga si esa regla la cumplen los que ganan o no.

_NUM = re.compile(r"\b\d+\b|\b(one|two|three|four|five|six|seven|eight|nine|ten|"
                  r"eleven|twelve|twenty|thirty|forty|fifty|hundred|thousand)\b", re.I)
_DIALOGO = re.compile(r'["“]|\bsaid\b|\bscreamed\b|\btold me\b', re.I)
_TIEMPO = re.compile(r"\b(years?|months?|weeks?|days?|hours?|minutes?|later|"
                     r"before|since|ago|until)\b", re.I)
_ACCION = re.compile(r"\b(slapped|threw|shattered|walked|stood|grabbed|slammed|"
                     r"hit|pushed|dropped|screamed|ran)\b", re.I)


def primera_frase(texto: str) -> str:
    partes = [s.strip() for s in re.split(r"(?<=[.!?])\s+", texto) if s.strip()]
    return partes[0] if partes else texto


def medir(hook: str) -> dict:
    p1 = primera_frase(hook)
    frases = [s for s in re.split(r"(?<=[.!?])\s+", hook) if s.strip()]
    return {
        "abre_con_pregunta": bool(P._starts_with_why(p1)) or p1.rstrip().endswith("?"),
        "se_autoresuelve": bool(P._RESUELVE_HOOK.search(p1)),
        "lleva_cifra": bool(_NUM.search(p1)),
        "lleva_dialogo": bool(_DIALOGO.search(hook)),
        "lleva_2o_tiempo": bool(_TIEMPO.search(p1)),
        # sobre TODO el gancho, no solo la 1a frase: en el ganador de 1,6M la
        # accion fisica ("slapped a cereal bowl out of my hands") esta en la
        # segunda, y medirla solo en la primera la daba por ausente.
        "abre_en_accion": bool(_ACCION.search(hook)),
        "palabras_frase_1": len(p1.split()),
        "frases_en_10s": len(frases),
        "cifras_en_10s": len(_NUM.findall(hook)),
    }


# ---------------------------------------------------------------- etapas

def cmd_collect(a) -> int:
    saldo = V.call_json("vidiq_balance", {}).get("totalCredits", 0)
    hacen_falta = COSTE_POR_LLAMADA * (a.n + 1)
    print(f"saldo {saldo} creditos | esta recogida cuesta ~{hacen_falta}")
    if saldo < hacen_falta:
        print(f"ABORTADO: faltan {hacen_falta - saldo}. No empiezo para no gastar "
              f"la mitad y quedarme a medias. Los renovables entran el 15 ago.")
        return 1

    args = {"contentType": "short", "limit": a.n, "minViews": a.min_views,
            "publishedWithin": "sixMonths"}
    if a.canal:
        args["channelIds"] = [a.canal]
    if a.keyword:
        args["keyword"] = a.keyword
    videos = V.call_json("vidiq_outliers", args).get("videos", [])
    print(f"{len(videos)} videos candidatos")

    corpus = json.loads(CORPUS.read_text(encoding="utf-8")) if CORPUS.exists() else []
    vistos = {c["videoId"] for c in corpus}
    nuevos = 0
    for v in videos:
        if v["videoId"] in vistos:
            continue
        try:
            t = V.call_json("vidiq_video_transcript", {"videoId": v["videoId"]})
            texto = (t.get("transcription") or "").strip()
        except Exception as e:
            print(f"  {v['videoId']}: sin transcripcion ({e})")
            continue
        if len(texto.split()) < HOOK_PALABRAS:
            continue
        corpus.append({
            "videoId": v["videoId"], "titulo": v.get("videoTitle"),
            "canal": v.get("channelTitle"), "subs": v.get("subscriberCount"),
            "vistas": v.get("viewCount"), "outlier": v.get("breakoutScore"),
            "duracion_s": v.get("videoDuration"),
            "hook": " ".join(texto.split()[:HOOK_PALABRAS]),
        })
        nuevos += 1
        print(f"  + {v.get('channelTitle')} | {v.get('viewCount'):,} vistas")

    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    CORPUS.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{nuevos} ganchos nuevos, {len(corpus)} en total -> {CORPUS}")
    return 0


def cmd_rubric(_a) -> int:
    if not CORPUS.exists():
        print("no hay corpus todavia: corre `collect` primero")
        return 1
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    if len(corpus) < 5:
        print(f"solo {len(corpus)} ganchos. Por debajo de ~15 la distribucion no "
              f"dice nada; sigue recogiendo antes de sacar conclusiones.")
    medidas = [medir(c["hook"]) for c in corpus]
    n = len(medidas)

    print(f"\nRUBRICA DERIVADA DE {n} GANADORES REALES")
    print(f"(mediana de vistas: {statistics.median(c['vistas'] for c in corpus):,.0f})\n")

    reglas = {
        "abre_con_pregunta": "regla 9 dice NO. Si aqui sale alto, la regla 9 esta mal",
        "se_autoresuelve": "regla 9 dice NO (nada de 'because' en la 1a frase)",
        "lleva_cifra": "regla 9 dice SI (el 'prime' del hueco de informacion)",
        "lleva_2o_tiempo": "regla 9 dice SI (pliegue temporal)",
        "lleva_dialogo": "sin regla propia todavia",
        "abre_en_accion": "sin regla propia todavia",
    }
    for k, nota in reglas.items():
        pct = sum(m[k] for m in medidas) / n
        marca = "###" if pct >= 0.7 else ("---" if pct <= 0.3 else "   ")
        print(f"  {marca} {k:<20} {pct:5.0%}   {nota}")

    print()
    for k in ("palabras_frase_1", "frases_en_10s", "cifras_en_10s"):
        vals = [m[k] for m in medidas]
        print(f"      {k:<20} mediana {statistics.median(vals):5.1f}   "
              f"rango {min(vals)}-{max(vals)}")

    print("\n  ### = lo hacen 7 de cada 10 o mas -> es regla\n"
          "  --- = lo hacen 3 de cada 10 o menos -> es antipatron\n"
          "  (en medio = no discrimina, no lo conviertas en regla)")
    return 0


def cmd_score(a) -> int:
    if not CORPUS.exists():
        print("no hay corpus: sin rubrica derivada no puedo puntuar nada.")
        return 1
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    medidas = [medir(c["hook"]) for c in corpus]
    n = len(medidas)
    mio = medir(a.hook)

    print(f"\nTU GANCHO vs {n} ganadores\n")
    puntos = total = 0
    for k in ("abre_con_pregunta", "se_autoresuelve", "lleva_cifra",
              "lleva_2o_tiempo", "lleva_dialogo", "abre_en_accion"):
        pct = sum(m[k] for m in medidas) / n
        if 0.3 < pct < 0.7:
            print(f"      {k:<20} {pct:5.0%} en los ganadores -- no discrimina, ignorado")
            continue
        quieren = pct >= 0.7
        ok = mio[k] == quieren
        total += 1
        puntos += ok
        print(f"  {'OK ' if ok else 'NO '} {k:<20} ganadores {pct:5.0%} | tu {mio[k]}")

    mediana = statistics.median(m["palabras_frase_1"] for m in medidas)
    print(f"\n      1a frase: {mio['palabras_frase_1']} palabras "
          f"(mediana de los ganadores {mediana:.0f})")
    print(f"\n  {puntos}/{total} criterios que SI discriminan")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="baja ganchos de ganadores (CUESTA CREDITOS)")
    c.add_argument("--canal", help="@handle o UC... para un solo canal")
    c.add_argument("--keyword", help="busqueda por tema si no hay canal")
    c.add_argument("--n", type=int, default=20)
    c.add_argument("--min-views", type=int, default=300000)
    c.set_defaults(fn=cmd_collect)

    r = sub.add_parser("rubric", help="saca la distribucion del corpus (gratis)")
    r.set_defaults(fn=cmd_rubric)

    s = sub.add_parser("score", help="puntua un gancho contra el corpus (gratis)")
    s.add_argument("hook")
    s.set_defaults(fn=cmd_score)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
