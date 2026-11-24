"""Aprender de un outlier evergreen sin copiarle una sola frase.

Que hace: coge un video ajeno que funciono, saca su transcripcion con vidIQ y
devuelve **solo su esqueleto** -- donde promete, donde gira, cuantos bucles abre
y cuales deja sin pagar, con que unidad cuenta las cosas y a que ritmo habla.
Nunca devuelve su texto.

Por que existe: la estructura no es de nadie y es donde esta el valor -- el orden
de los golpes, la posicion del giro, el tipo de gancho. El texto y las imagenes
si son de alguien: reescribir un guion frase por frase para otro nicho es obra
derivada, y en YouTube ademas hay un segundo filtro aparte del legal (la politica
de contenido reutilizado, que es la que bloquea monetizacion). Esta herramienta
existe para poder hacer lo primero sin rozar lo segundo.

**La garantia es mecanica, no una promesa en el prompt.** Pedirle al modelo "no
cites" no es una garantia: es una intencion. Por eso, despues de generar, cada
campo de texto de la salida se compara contra la transcripcion y se **borra** si
comparte una racha de MAX_RACHA palabras seguidas. Un prompt se puede ignorar;
un filtro que corre sobre la salida, no.

Uso:
    py esqueleto.py <video_id> [<video_id> ...]
    py esqueleto.py dQw4w9WgXcQ --guarda        # ademas escribe esqueletos/<id>.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

MAX_RACHA = 6          # palabras seguidas compartidas que ya se consideran cita
DESTINO = ROOT / "esqueletos"

# Palabras que nunca son "la unidad" de un video aunque se repitan mucho.
VACIAS = set(
    """de la que el en y a los se del las un por con no una su para es al lo como
    mas o pero sus le ha me si sin sobre este ya entre cuando todo esta ser son dos
    tambien fue habia era muy hasta desde nos durante todos uno les ni contra otros
    ese eso ante ellos esto mi antes algunos unos yo otro otras otra tanto esa
    estos nada muchos cual sea poco ella estar haber estas estaba estamos algunas
    algo nosotros mis tu te ti tus ellas nosotras mio mia hay ver bien vamos ahora
    aqui porque solo cada asi entonces you the and to of that is it for this in we
    """.split()
)

FUNCIONES = [
    "gancho", "promesa", "contexto", "mecanismo", "ejemplo", "objecion",
    "giro", "prueba", "herramienta", "recapitulacion", "cta", "cierre",
]

ESQUEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["beats", "bucles", "unidad", "promesa_pct", "giro_pct",
                 "cierre_deja_abierto", "por_que_funciono"],
    "properties": {
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["pct", "funcion", "nota"],
                "properties": {
                    "pct": {"type": "integer"},
                    "funcion": {"type": "string", "enum": FUNCIONES},
                    # 'nota' describe la FUNCION, no el contenido: "presenta un
                    # segundo caso identico para comparar", no de que va la escena.
                    "nota": {"type": "string"},
                },
            },
        },
        "bucles": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["abre_pct", "paga_pct", "tipo"],
                "properties": {
                    "abre_pct": {"type": "integer"},
                    # -1 = nunca lo paga (deuda abierta al final, que es deseable)
                    "paga_pct": {"type": "integer"},
                    "tipo": {"type": "string",
                             "enum": ["identidad", "conocimiento", "resultado"]},
                },
            },
        },
        "unidad": {"type": "string"},
        "promesa_pct": {"type": "integer"},
        "giro_pct": {"type": "integer"},
        "cierre_deja_abierto": {"type": "boolean"},
        "por_que_funciono": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}

PROMPT = """Eres analista de estructura narrativa. Te doy la transcripcion de un
video que funciono muy bien. Tu trabajo NO es resumirlo ni contarme de que va.

Tu trabajo es devolver su ESQUELETO: en que porcentaje del video hace cada cosa,
que bucles abre y donde los paga, y con que unidad mide las cosas.

REGLAS DURAS:
- Prohibido citar. Prohibido parafrasear el contenido. Prohibido nombrar el tema
  concreto, los personajes, las marcas o los datos del video.
- Cada 'nota' describe la FUNCION del beat, no lo que dice. Bien: "presenta un
  segundo caso identico para comparar". Mal: "habla de dos vecinos y un carro".
- 'unidad' es la cosa contable con la que mide (por ejemplo "veces por semana",
  "kilos", "intentos"), no el tema.
- 'por_que_funciono' son mecanismos trasladables a CUALQUIER nicho, no
  observaciones sobre este tema.

Tipos de bucle: identidad (el espectador se pregunta si va de el), conocimiento
(el autor sabe algo que el espectador no), resultado (paso algo y falta el
desenlace). paga_pct = -1 si nunca lo paga.

Devuelve entre 8 y 16 beats y entre 3 y 5 mecanismos.

TRANSCRIPCION:
{txt}
"""


def _norm(t: str) -> list[str]:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", t)


def _rachas(palabras: list[str], n: int) -> set[tuple]:
    return {tuple(palabras[i:i + n]) for i in range(len(palabras) - n + 1)}


def limpiar_citas(dato, fuente_rachas: set[tuple]) -> tuple[object, int]:
    """Borra recursivamente cualquier cadena que comparta MAX_RACHA palabras
    seguidas con la transcripcion. Devuelve (dato_limpio, n_borradas)."""
    borradas = 0
    if isinstance(dato, dict):
        out = {}
        for k, v in dato.items():
            out[k], n = limpiar_citas(v, fuente_rachas)
            borradas += n
        return out, borradas
    if isinstance(dato, list):
        out = []
        for v in dato:
            v2, n = limpiar_citas(v, fuente_rachas)
            out.append(v2)
            borradas += n
        return out, borradas
    if isinstance(dato, str):
        pal = _norm(dato)
        if len(pal) >= MAX_RACHA and _rachas(pal, MAX_RACHA) & fuente_rachas:
            return "[CITA ELIMINADA]", 1
        return dato, 0
    return dato, 0


def metricas(txt: str) -> dict:
    """Lo que se puede medir sin gastar un token de modelo."""
    pal = _norm(txt)
    frases = [f for f in re.split(r"[.!?]+", txt) if f.strip()]
    largos = [len(_norm(f)) for f in frases] or [0]
    conteo = Counter(p for p in pal if p not in VACIAS and len(p) > 3)
    return {
        "palabras": len(pal),
        "frases": len(frases),
        "palabras_por_frase": round(sum(largos) / len(largos), 1),
        "preguntas": txt.count("?"),
        "cifras": len(re.findall(r"\b\d[\d.,]*\b", txt)),
        "repetidas": conteo.most_common(6),
    }


def analiza(vid: str, guarda: bool) -> None:
    import vidiq_tools

    d = vidiq_tools.call_json("vidiq_video_transcript", {"videoId": vid})
    txt = (d.get("transcription") or d.get("transcript") or "") if isinstance(d, dict) else d
    if not isinstance(txt, str) or len(txt) < 400:
        print(f"=== {vid}: sin transcripcion util")
        return

    m = metricas(txt)
    import pipeline

    bruto = pipeline._claude_json_call(3000, ESQUEMA, PROMPT.format(txt=txt[:60000]))
    limpio, borradas = limpiar_citas(bruto, _rachas(_norm(txt), MAX_RACHA))

    print(f"\n=== {vid}")
    print(f"  {m['palabras']} palabras · {m['palabras_por_frase']} por frase · "
          f"{m['preguntas']} preguntas · {m['cifras']} cifras")
    print(f"  unidad con la que mide: {limpio['unidad']}")
    print(f"  promesa al {limpio['promesa_pct']}% · giro al {limpio['giro_pct']}% · "
          f"deja algo abierto al final: {'si' if limpio['cierre_deja_abierto'] else 'NO'}")
    print("  palabras propias mas repetidas: "
          + ", ".join(f"{p} x{n}" for p, n in m["repetidas"]))

    print("\n  MAPA DE GOLPES")
    for b in sorted(limpio["beats"], key=lambda x: x["pct"]):
        print(f"    {b['pct']:>3}%  {b['funcion']:<14} {b['nota']}")

    print("\n  BUCLES")
    for c in sorted(limpio["bucles"], key=lambda x: x["abre_pct"]):
        paga = "NUNCA (deuda abierta)" if c["paga_pct"] < 0 else f"{c['paga_pct']}%"
        # un bucle que abre y paga dentro del mismo tramo no crea tension entre
        # bloques; el que cruza una costura es el que produce el repunte
        cruza = "" if c["paga_pct"] < 0 else (
            "  <- cruza costura" if c["paga_pct"] - c["abre_pct"] > 12 else "")
        print(f"    abre {c['abre_pct']:>3}%  paga {paga:<22} [{c['tipo']}]{cruza}")

    print("\n  MECANISMOS TRASLADABLES")
    for r in limpio["por_que_funciono"]:
        print(f"    - {r}")

    if borradas:
        print(f"\n  [filtro] {borradas} campo(s) borrados por compartir "
              f"{MAX_RACHA}+ palabras seguidas con el original")

    if guarda:
        DESTINO.mkdir(exist_ok=True)
        (DESTINO / f"{vid}.json").write_text(
            json.dumps({"video_id": vid, "metricas": m, "esqueleto": limpio},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  guardado en esqueletos/{vid}.json")


def main() -> int:
    ap = argparse.ArgumentParser(description="Esqueleto de un outlier, sin su texto.")
    ap.add_argument("video_ids", nargs="+")
    ap.add_argument("--guarda", action="store_true")
    a = ap.parse_args()
    for vid in a.video_ids:
        try:
            analiza(vid, a.guarda)
        except Exception as e:
            print(f"=== {vid}: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
