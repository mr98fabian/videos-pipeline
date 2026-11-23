"""La puerta compartida del repo Videos (Misión 0002, equivalente a la de CoreX-SF).

    py scripts/verify.py                 # local: árbol limpio -> exit 0 sin correr nada
    py scripts/verify.py --hook          # Stop hook de Claude Code (exit 2 = no cierra el turno)
    python scripts/verify.py --ci --base origin/master   # CI: lo cambiado frente a la base

Chequeos, solo sobre lo que cambió (los guiones ya publicados no se tocan,
regla 3 de la casa, así que no se les exige retroactivamente nada):
  (a) lint_enie.py en los guiones cambiados.
  (b) formato de guion de la casa: 1 search_term por oración, character_terms
      paralelo a search_terms, twist_phrase literal entre el 25 % y el 75 %,
      exactamente un beat `*` en character_terms.
  (c) tests del repo (pytest sobre tests/), si existen.
  (d) escudo: ningún archivo que el .gitignore prohíbe aparece como añadido
      (forzado con `git add -f`). Excepción: misiones/evidencia/, cuyas hojas
      de contacto se fuerzan a propósito como evidencia de auditoría.

Caché por hash del estado del árbol (HEAD + diff + contenido de lo no
rastreado) en <git-dir>/verify_cache.json: si ese estado ya pasó, no se repite.
Exit: 0 verde · 1 rojo · 2 rojo en modo --hook (bloquea el cierre del turno).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Mismas reglas que pipeline.py (_check_giro_posicion, conteo 1:1): si cambian
# allí, cambian aquí.
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
GIRO_MIN, GIRO_MAX = 0.25, 0.75
EVIDENCE_DIR = "misiones/evidencia/"


def git(*args: str, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


# --------------------------------------------------------------- qué cambió
def _status() -> list[tuple[str, str]]:
    """[(código XY, ruta)] del árbol de trabajo, incluidos los no rastreados."""
    out = []
    for line in git("status", "--porcelain", "-z", "--untracked-files=all").split("\0"):
        if len(line) > 3:
            out.append((line[:2], line[3:]))
    return out


def changed_local() -> tuple[list[str], list[str]]:
    """(rutas cambiadas existentes, rutas añadidas) frente a HEAD."""
    changed, added = [], []
    for xy, path in _status():
        if "D" in xy or not (ROOT / path).exists():
            continue
        changed.append(path)
        if xy == "??" or "A" in xy:
            added.append(path)
    return changed, added


def changed_ci(base: str) -> tuple[list[str], list[str]]:
    mb = git("merge-base", base, "HEAD").strip()
    head = git("rev-parse", "HEAD").strip()
    if mb == head:  # push directo a la rama base: se mira el último commit
        mb = git("rev-parse", "HEAD~1", check=False).strip() or mb
    changed = [p for p in git("diff", "--name-only", "--diff-filter=AMR", mb, "HEAD").splitlines() if p]
    added = [p for p in git("diff", "--name-only", "--diff-filter=A", mb, "HEAD").splitlines() if p]
    return changed, added


def is_guion(path: str) -> bool:
    p = path.replace("\\", "/")
    return p.startswith("scripts/") and p.endswith(".json") and p.count("/") == 1


# ------------------------------------------------------- (b) formato de guion
def validate_script(data: dict) -> list[str]:
    """Fallos de formato de un guion de la casa (lista vacía = válido)."""
    fails = []
    script = data.get("script") or ""
    st = data.get("search_terms")
    ct = data.get("character_terms")
    if not isinstance(script, str) or not script.strip():
        return ["falta `script` (texto del guion)"]
    sentences = [s for s in SENT_SPLIT.split(script) if s.strip()]
    if st is not None:
        if not isinstance(st, list):
            fails.append("`search_terms` no es una lista")
        elif len(st) != len(sentences):
            fails.append(f"{len(st)} search_terms para {len(sentences)} oraciones "
                         "(regla 1:1 frase↔imagen)")
        elif any(isinstance(t, str) and t.startswith("*") for t in st):
            fails.append("beat `*` en search_terms: va en character_terms")
    if ct is not None:
        if not isinstance(ct, list):
            fails.append("`character_terms` no es una lista")
        else:
            if isinstance(st, list) and len(ct) != len(st):
                fails.append(f"{len(ct)} character_terms para {len(st)} search_terms "
                             "(viajan en paralelo)")
            beats = sum(1 for t in ct if isinstance(t, str) and t.startswith("*"))
            if beats != 1:
                fails.append(f"{beats} beats `*` en character_terms (debe haber exactamente uno)")
    twist = data.get("twist_phrase")
    if twist:
        i = script.find(twist)
        if i < 0:
            fails.append(f"twist_phrase {twist!r} no aparece literal en el guion")
        else:
            total = len(script.split())
            frac = len(script[:i].split()) / total if total else 0.0
            if not GIRO_MIN <= frac <= GIRO_MAX:
                fails.append(f"el giro cae al {frac:.0%} del guion (banda 25-75 %)")
    return fails


# --------------------------------------------------------------- chequeos
def check_guiones(paths: list[str]) -> list[str]:
    import lint_enie

    fails = []
    for p in paths:
        f = ROOT / p
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # JSON roto es un fallo, no una excepción del gate
            fails.append(f"[formato] {p}: JSON ilegible ({e})")
            continue
        if not isinstance(data, dict):
            fails.append(f"[formato] {p}: el guion no es un objeto JSON")
            continue
        fails += [f"[enie] {p}: {m}" for m in lint_enie.revisar(f)]
        fails += [f"[formato] {p}: {m}" for m in validate_script(data)]
    return fails


def check_tests() -> tuple[list[str], str]:
    if not (ROOT / "tests").is_dir():
        return [], "sin tests/"
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", timeout=600)
    tail = (r.stdout.strip().splitlines() or ["(sin salida)"])[-1]
    if r.returncode != 0:
        return [f"[tests] pytest falló: {tail}"], tail
    return [], tail


def check_escudo(added: list[str]) -> list[str]:
    cand = [p for p in added if not p.replace("\\", "/").startswith(EVIDENCE_DIR)]
    if not cand:
        return []
    # -z y bytes: en Windows el modo texto convierte \n en \r\n y git dejaba
    # de reconocer las rutas (el escudo salía verde con un token forzado).
    r = subprocess.run(["git", "check-ignore", "--no-index", "-v", "-z", "--stdin"], cwd=ROOT,
                       input="\0".join(cand).encode("utf-8"), capture_output=True, timeout=60)
    f = r.stdout.decode("utf-8").split("\0")
    fails = []
    for i in range(0, len(f) - 3, 4):  # registros: fuente, línea, patrón, ruta
        pattern, path = f[i + 2], f[i + 3]
        if pattern.startswith("!"):  # excepción explícita del .gitignore: permitido
            continue
        fails.append(f"[escudo] {path} está prohibido por .gitignore ({pattern})")
    return fails


# ------------------------------------------------------------------ caché
def _cache_path() -> Path:
    # --git-path: funciona también en worktrees, donde .git es un archivo
    return ROOT / git("rev-parse", "--git-path", "verify_cache.json").strip()


def tree_hash() -> str:
    h = hashlib.sha256(git("rev-parse", "HEAD").encode())
    h.update(git("diff", "HEAD", "--binary").encode("utf-8", "replace"))
    for xy, path in sorted(_status()):
        if xy == "??":
            h.update(path.encode())
            f = ROOT / path
            if f.is_file():
                h.update(hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def _cache_get() -> dict:
    try:
        return json.loads(_cache_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cache_put(**kv) -> None:
    try:
        _cache_path().write_text(json.dumps({**_cache_get(), **kv}), encoding="utf-8")
    except OSError:
        pass  # sin caché solo se repite el trabajo


# ------------------------------------------------------------------- main
def run(changed: list[str], added: list[str]) -> tuple[list[str], list[str]]:
    guiones = sorted(p for p in changed if is_guion(p))
    fails = check_guiones(guiones)
    tfails, ttail = check_tests()
    fails += tfails
    fails += check_escudo(added)
    info = [f"guiones revisados: {len(guiones)}", f"tests: {ttail}",
            f"archivos añadidos bajo el escudo: {len(added)}"]
    return fails, info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hook", action="store_true", help="modo Stop hook de Claude Code")
    ap.add_argument("--ci", action="store_true", help="compara contra --base en vez del árbol")
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()

    hook_input = {}
    if a.hook and not sys.stdin.isatty():
        try:
            hook_input = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            hook_input = {}

    if a.ci:
        changed, added = changed_ci(a.base)
        key = None
    else:
        changed, added = changed_local()
        if not changed:
            print("verify: árbol limpio — nada que verificar")
            return 0
        key = tree_hash()
        if not a.no_cache and _cache_get().get("pass") == key:
            print("verify: verde (caché: este estado del árbol ya pasó)")
            return 0

    fails, info = run(changed, added)
    if not fails:
        if key:
            _cache_put(**{"pass": key})
        print("verify: VERDE · " + " · ".join(info))
        return 0

    out = sys.stderr if a.hook else sys.stdout
    print(f"verify: ROJO — {len(fails)} fallo(s) · " + " · ".join(info), file=out)
    for f in fails:
        print("  - " + f, file=out)
    if a.hook:
        # Si el turno ya se bloqueó por ESTE mismo estado y nada cambió, el
        # ejecutor no pudo arreglarlo: se deja cerrar para que lo reporte en
        # vez de entrar en bucle. Cualquier cambio del árbol vuelve a bloquear.
        if hook_input.get("stop_hook_active") and _cache_get().get("blocked") == key:
            print("verify: sigue en ROJO sin cambios desde el último bloqueo — "
                  "se permite cerrar para REPORTARLO a Fabian/Mijo.", file=out)
            return 0
        _cache_put(blocked=key)
        print("Arregla los fallos (o repórtalos) antes de cerrar el turno.", file=out)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
