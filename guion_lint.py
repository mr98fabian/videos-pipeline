"""Mide la redundancia DENTRO de un guion, antes de producirlo.

POR QUE (13 ago 2026): Fabian, sobre el largo de "Dos sueldos": *"me gusto pero
me parece que repite una y otra vez lo mismo"*. Y era medible --  en 1.273
palabras: "casa" 23 veces, "rebusca/rebuscas" 24, "mano" 11, y la frase "la casa
de tus papas" cinco veces enteras.

El diagnostico no es el vocabulario, es la estructura: el guion re-enuncia la
TESIS en vez de avanzar el argumento. En un Short de 60 s repetir ancla; en 9
minutos, aburre y se nota como relleno.

Ya existia `_check_antislop_similarity` en pipeline.py, pero compara un guion
con el ANTERIOR. Esto mira dentro de uno solo.

    py guion_lint.py scripts/korex-dos-sueldos.json
"""

from __future__ import annotations

import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Umbral DE TRABAJO, no medido contra rendimiento: ninguna palabra de contenido
# deberia pasar del 0,8% del guion. Con 1.273 palabras eso son 10 usos; "casa"
# iba por 24. Si algun dia hay datos de retencion que lo contradigan, mandan
# ellos.
#
# EL SUELO DE 5 NO ES OPCIONAL: en un Short de 190 palabras el 0,8% es UNA
# palabra, asi que nombrar al personaje tres veces saldria marcado. En textos
# cortos repetir el ancla es correcto --es lo que hace que el espectador sepa de
# quien va--; la redundancia solo empieza a molestar cuando hay minutos por
# delante. Sin este suelo el lint contradecia a la plantilla del canal.
TOPE_PALABRA_PCT = 0.8
SUELO_REPETICIONES = 5
TOPE_BIGRAMA = 3          # una frase de dos palabras repetida 3+ veces canta
SOLAPE_TESIS = 0.6        # frases que repiten la de apertura
MIN_CONTENIDO_ECO = 4     # una frase de dos palabras no "repite la tesis"

# El nombre del personaje no es redundancia, es identidad: se repite a proposito.
NOMBRES = {"tadeo", "korex", "bruja", "skick"}

_STOP = set(
    "el la los las un una unos unas de del a al y o u que en es son era eran se "
    "su sus lo le les por para con no ni mas pero si te tu ti me mi ya cuando "
    "como donde eso esa ese esta este esto hay muy sin sobre entre desde hasta "
    "ser estar tiene tienen hace hacen va van vas ir the of and".split()
)


def _norm(w: str) -> str:
    w = "".join(c for c in unicodedata.normalize("NFD", w.lower())
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


def _contenido(texto: str) -> list[str]:
    return [w for w in (_norm(x) for x in texto.split())
            if w and w not in _STOP and len(w) > 3]


def analizar(guion: str) -> dict:
    palabras = guion.split()
    cont = _contenido(guion)
    total = max(len(palabras), 1)
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", guion) if f.strip()]

    veces = collections.Counter(cont)
    # singular y plural son la misma idea repetida ("rebusca"/"rebuscas")
    familias: dict[str, int] = collections.Counter()
    for w, n in veces.items():
        familias[w[:-1] if w.endswith("s") and len(w) > 4 else w] += n

    limite = max(SUELO_REPETICIONES, total * TOPE_PALABRA_PCT / 100)
    abusadas = [(w, n, 100 * n / total) for w, n in familias.most_common()
                if n > limite and w not in NOMBRES]
    bigramas = [(" ".join(k), v) for k, v in
                collections.Counter(zip(cont, cont[1:])).most_common()
                if v >= TOPE_BIGRAMA]

    # frases que vuelven a decir la tesis (la de apertura). LA ULTIMA NO CUENTA:
    # el guion DEBE cerrar sobre las palabras del gancho para que el bucle no
    # tenga costura (regla del canal, medida: 3,76 -> 2,89 de retencion en el
    # unico video con bucle, frente a 0,08 en los que cierran con resumen). Sin
    # esta excepcion el lint pedia romper justo lo que mejor funciona.
    base = set(_contenido(frases[0])) if frases else set()
    ecos = []
    for f in frases[1:-1]:
        s = set(_contenido(f))
        if len(s) >= MIN_CONTENIDO_ECO and base and \
                len(s & base) / len(s) >= SOLAPE_TESIS:
            ecos.append(f)
    return {"palabras": total, "frases": len(frases), "abusadas": abusadas,
            "bigramas": bigramas, "ecos": ecos}


def informe(r: dict) -> bool:
    print(f"{r['palabras']} palabras, {r['frases']} frases\n")
    ok = True
    if r["abusadas"]:
        ok = False
        print("palabras repetidas de mas:")
        for w, n, pct in r["abusadas"][:10]:
            print(f"  {w:<16} {n:>3} veces  ({pct:.1f}%)")
    else:
        print("ninguna palabra pasa del tope")
    if r["bigramas"]:
        ok = False
        print(f"\nfrases hechas repetidas {TOPE_BIGRAMA}+ veces:")
        for b, n in r["bigramas"][:10]:
            print(f"  '{b}'  x{n}")
    if r["ecos"]:
        ok = False
        print(f"\n{len(r['ecos'])} frases repiten la tesis de apertura:")
        for f in r["ecos"][:6]:
            print(f"  - {f[:78]}")
    if ok:
        print("\nsin redundancia detectada")
    else:
        print("\nCada frase tiene que anadir algo que no se dijo antes. La tesis "
              "se enuncia al principio y se cierra al final; en medio se avanza.")
    return ok


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    d = json.loads(Path(sys.argv[1]).read_text("utf-8"))
    return 0 if informe(analizar(d["script"])) else 2


if __name__ == "__main__":
    sys.exit(main())
