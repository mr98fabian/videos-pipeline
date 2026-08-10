"""Caza palabras que perdieron su enie y se volvieron OTRA palabra.

Origen: para esquivar un fallo de pronunciacion del TTS se escribian los
guiones sin enie, y eso convierte 'año' en 'ano' -- que el sintetizador lee tal
cual y suena mucho peor que el error que se queria evitar. La regla correcta no
es quitar la enie: es **reescribir la frase** para no necesitarla, o dejarla y
comprobar de oido.

    py lint_enie.py scripts/korex-ponzi.json
    py lint_enie.py            # revisa todos los scripts/*.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent

# solo palabras que SIN enie siguen siendo una palabra valida distinta: son las
# unicas que el TTS puede leer mal sin que nadie lo note leyendo el guion
TRAMPAS = {
    "ano": "año",
    "anos": "años",
    "nino": "niño",
    "nina": "niña",
    "ninos": "niños",
    "ninas": "niñas",
    "senor": "señor",
    "senora": "señora",
    "senal": "señal",
    "senales": "señales",
    "sena": "seña",
    "senas": "señas",
    "manana": "mañana",
    "pequeno": "pequeño",
    "pequena": "pequeña",
    "engano": "engaño",
    "enganos": "engaños",
    "dueno": "dueño",
    "duenos": "dueños",
    "sueno": "sueño",
    "suenos": "sueños",
    "empeno": "empeño",
    "empenos": "empeños",
    "diseno": "diseño",
    "companero": "compañero",
    "compania": "compañía",
    "montana": "montaña",
    "cana": "caña",
    "canon": "cañón",
    "bano": "baño",
    "punos": "puños",
    "extrano": "extraño",
    "extrana": "extraña",
    "danos": "daños",
    "espanol": "español",
    "espanola": "española",
    "manas": "mañas",
}


def trampas_en_texto(texto: str) -> list[str]:
    """Palabras del texto a las que les falta la enie (en minusculas, sin
    repetir y en orden de aparicion).

    Existe aparte de `revisar()` para que `pipeline.py` pueda avisar sobre un
    guion que todavia esta en memoria, sin tener que haberlo escrito a disco:
    el aviso sirve ANTES de gastar el TTS, no despues.
    """
    vistas, out = set(), []
    for w in re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñÜü]+", texto or ""):
        wl = w.lower()
        if wl in TRAMPAS and wl not in vistas:
            vistas.add(wl)
            out.append(wl)
    return out


def revisar(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    texto = data.get("script") or ""
    return [
        f"'{w}' deberia ser '{TRAMPAS[w]}' -- el TTS lo lee literal"
        for w in trampas_en_texto(texto)
    ]


def main() -> int:
    archivos = [Path(a) for a in sys.argv[1:] if not a.startswith("-")] or sorted(
        (ROOT / "scripts").glob("*.json")
    )
    total = 0
    for f in archivos:
        try:
            fallos = revisar(f)
        except Exception as e:
            print(f"{f.name}: no pude leerlo ({e})")
            continue
        if fallos:
            total += len(fallos)
            print(f"\n{f.name}:")
            for x in fallos:
                print("  -", x)
    if not total:
        print("sin palabras mutiladas por quitar la enie")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
