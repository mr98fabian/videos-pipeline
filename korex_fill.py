"""Completa las escenas que le faltan a una carpeta de salida ya producida,
insistiendo SOLO en las que faltan.

Flow falla de forma intermitente: en una misma corrida la misma escena puede
salir a la primera o negarse tres veces seguidas. Con 3 reintentos en linea
dentro de `pipeline.py` siempre quedaban huecos, y un hueco arruina el montaje
entero (la escena cae a gradiente y el motor pierde esa imagen). En vez de
reintentar mas fuerte dentro de la corrida, esto converge por fuera: mira que
`nb_<i>.png` no existen, los pide otra vez, y repite por rondas hasta que estan
todos o se agotan las rondas.

    py korex_fill.py output/<carpeta>            # hasta 6 rondas
    py korex_fill.py output/<carpeta> --rondas 3

Despues, para rehacer el video con las escenas completas, el camino clasico
(imagenes de Flow a pantalla completa). OJO: `korex_engine.py` esta RETIRADO
para KOREX desde el 9 ago 2026 -- ese motor es la piel de HiddenFacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    argv = sys.argv[1:]
    rondas = 6
    if "--rondas" in argv:
        k = argv.index("--rondas")
        rondas = int(argv[k + 1])
        del argv[k : k + 2]
    out_dir = Path(argv[0]).resolve()
    clips = out_dir / "clips"
    data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    terms = data.get("search_terms") or []
    char_terms = data.get("character_terms") or []
    style = data.get("style") or ""

    import kx_cast
    import flow_automation as fa

    for ronda in range(1, rondas + 1):
        faltan = [i for i in range(len(terms)) if not (clips / f"nb_{i}.png").exists()]
        if not faltan:
            print(f"completo: {len(terms)}/{len(terms)} escenas")
            break
        print(f"\n--- ronda {ronda}/{rondas}: faltan {faltan} ---")
        for i in faltan:
            term = terms[i]
            raw_char = char_terms[i] if i < len(char_terms) else ""
            refs = []
            prompt = term
            if raw_char and "/" in raw_char:
                c, _, p = raw_char.partition("/")
                # solo la HOJA MADRE como referencia; la pose va en palabras.
                # Ver el comentario de identidad en pipeline.acquire_media.
                sheet = kx_cast._canonical_sheet(c)
                refs = [Path(sheet)] if sheet and Path(sheet).exists() else []
                if not refs:
                    pose_img = kx_cast.pick(c, p, i) or kx_cast.get_pose(c, p)
                    refs = [Path(pose_img)] if pose_img else []
                pose_txt = kx_cast.pose_text(p)
                if pose_txt:
                    term = f"{term}. Tadeo esta {pose_txt}"
                prompt = f"{term}. {kx_cast.CHARACTER_LOCK}"
            # SECUNDARIOS TAMBIEN AQUI (10 ago 2026). Este enganche vive en tres
            # sitios (pipeline, korex_fill y el parcheo manual) y se olvido en
            # los tres por separado: cada vez que faltaba, la Bruja del Banco
            # volvia a salir de bruja de cuento en vez de banquera.
            sec_refs, sec_lock = kx_cast.secondary_refs(term)
            if sec_refs:
                refs = list(refs) + [r for r in sec_refs if r not in refs]
                if sec_lock:
                    prompt = f"{prompt}. {sec_lock}"
            ok = fa.generate_image(
                prompt,
                clips / f"nb_{i}.png",
                "",
                reference_images=refs,
                style_directive=style,
            )
            print(f"  escena {i}: {'OK' if ok else 'falla'}")

    fa.close_session()
    faltan = [i for i in range(len(terms)) if not (clips / f"nb_{i}.png").exists()]
    if faltan:
        print(f"\nSIGUEN FALTANDO: {faltan}. Volver a correr korex_fill.")
        return 1
    print(f"\nLISTO: las {len(terms)} escenas estan en {clips}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
