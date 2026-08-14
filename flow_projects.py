"""Un proyecto de Google Flow por CANAL (uno por guion fuera de KOREX).

Por que existe (3 ago 2026): `FlowSession._open_project()` pulsa "Proyecto
nuevo" siempre que no se le pasa una URL, asi que cada corrida creaba uno --
y una corrida no es un video: entre `pipeline.py`, `korex_fill.py` y
`korex_animate.py` un mismo guion abre Flow tres o cuatro veces, mas los
reintentos. De ahi que la cuenta acabara llena de proyectos sueltos, cada uno
con dos o tres imagenes.

Aqui se guarda `slug del guion -> URL del proyecto` en `flow_projects.json`, de
modo que **todas** las corridas del mismo guion caen en el mismo proyecto y un
guion nuevo estrena el suyo. Efecto secundario util: los ingredientes y el
personaje ya subidos siguen ahi, o sea menos subidas repetidas.

Uso:

    import flow_projects
    flow_projects.use_project("korex-tadeo-tarjeta")   # antes de tocar Flow
    ...                                               # pipeline / fill / animate
    flow_projects.forget("korex-tadeo-tarjeta")        # si se quiere empezar limpio

NOTA DE IMPLEMENTACION: ya NO hay monkeypatch. Este modulo solo elige la clave
de proyecto y `flow_automation._open_project` hace el resto (fijar, reabrir y
recrear si el proyecto fijado no existe).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "flow_projects.json"

_current: str | None = None


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:60]


def _load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    """Escritura atomica: pipeline.py y korex_animate.py pueden correr a la vez
    y una escritura a medias dejaria el mapa ilegible (mismo motivo que
    `_atomic_write_json` en pipeline.py)."""
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE)


def url_for(script: str) -> str | None:
    """URL del proyecto de Flow de este guion, o None si aun no tiene."""
    return _load().get(_slugify(script))


def remember(script: str, url: str) -> None:
    if not url or "/project/" not in url:
        return
    data = _load()
    slug = _slugify(script)
    if data.get(slug) == url:
        return
    data[slug] = url
    _save(data)
    print(f"[flow] proyecto de '{slug}': {url}")


def forget(script: str) -> None:
    """Olvida el proyecto de este guion: la proxima corrida estrena uno.

    No borra nada en Flow -- eso se hace a mano desde la web, a proposito: un
    borrado masivo automatizado es irreversible y se llevaria por delante
    imagenes y clips que ya costaron creditos.
    """
    data = _load()
    if data.pop(_slugify(script), None) is not None:
        _save(data)


def use_project(script: str, *pistas: str) -> None:
    """Ata todas las sesiones de Flow de este proceso a un proyecto conocido.

    UN PROYECTO POR CANAL EN KOREX (14 ago 2026). Antes era uno por guion, y
    tenia sentido: evitaba llenar la cuenta de proyectos con dos imagenes cada
    uno. Pero con el build nuevo de Flow los PERSONAJES viven DENTRO de un
    proyecto y el selector solo lista el actual: con un proyecto por guion, el
    Tadeo registrado no vuelve a estar al alcance nunca. Un solo proyecto de
    canal cumple las dos cosas -- no hay spam de proyectos y el personaje
    siempre esta ahi. Los guiones que no son de KOREX conservan el reparto por
    guion.

    SE ACABO EL MONKEYPATCH. Lo habia porque `flow_automation.py` lo estaba
    reescribiendo la otra sesion y no se queria pisar; esa migracion ya
    aterrizo. Y el parche costo caro: su `_shared_session` se quedo con la
    firma vieja (sin `count`), asi que en cuanto el pipeline empezo a pasar
    `count` TODA generacion lanzaba TypeError y caia al gradiente. Medido el 14
    ago: 24 de 24 escenas en gradiente, sin un solo error visible en el log
    porque `generate_image` se traga la excepcion.
    """
    global _current
    import flow_automation as fa

    _current = _slugify(script)
    # LAS PISTAS IMPORTAN: el titulo del guion de KOREX no dice "korex" por
    # ningun lado ("Isaac Newton perdio su fortuna..."), asi que detectar el
    # canal por el titulo falla siempre. El nombre del archivo si lo dice.
    todo = " ".join(_slugify(x) for x in (script, *pistas) if x)
    clave = "korex" if "korex" in todo else _current
    fa.FLOW_PROJECT_KEY = clave
    known = _load().get(clave)
    print(
        f"[flow] guion '{_current}' -> proyecto '{clave}': "
        + ("reusando el existente" if known else "estrenara uno nuevo")
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        for k, v in _load().items():
            print(f"{k}\n  {v}")
    elif len(sys.argv) > 2 and sys.argv[1] == "--forget":
        forget(sys.argv[2])
        print(f"olvidado: {sys.argv[2]}")
    else:
        print(__doc__)
