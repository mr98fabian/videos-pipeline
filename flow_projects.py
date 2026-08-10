"""Un proyecto de Google Flow POR GUION (no por corrida).

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

NOTA DE IMPLEMENTACION: engancha con un monkeypatch sobre
`flow_automation._shared_session` en vez de editar ese archivo, a proposito --
`flow_automation.py` lo esta reescribiendo la otra sesion de Claude (1000+
lineas sin commitear) y tocarlo ahora pisaria su trabajo. Cuando esa migracion
aterrice, esto se puede plegar dentro de `_shared_session` sin cambiar la API.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "flow_projects.json"

_patched = False
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


def use_project(script: str) -> None:
    """Ata todas las sesiones de Flow de este proceso al proyecto del guion.

    Si el guion ya tiene proyecto, se reabre; si no, Flow crea uno y se apunta
    aqui para las corridas siguientes.
    """
    global _patched, _current
    import flow_automation as fa

    _current = _slugify(script)

    if not _patched:
        original = fa._shared_session

        def _shared_session(aspect_ratio: str = "9:16"):
            if fa._SHARED is None and _current:
                url = _load().get(_current)
                s = fa.FlowSession(aspect_ratio=aspect_ratio, project_url=url)
                s.__enter__()
                fa._SHARED = s
                import atexit

                atexit.register(fa.close_session)
                # tras abrir, project_url ya trae la URL real del proyecto
                remember(_current, s.project_url or "")
                return s
            return original(aspect_ratio)

        fa._shared_session = _shared_session
        _patched = True

    known = _load().get(_current)
    print(
        f"[flow] guion '{_current}': "
        + (f"reusando proyecto existente" if known else "estrenara proyecto nuevo")
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
