"""Fase 2 de la Misión 0001: rig vectorial de Tadeo — prueba, gate y hoja de poses.

    py kx_tadeo.py                # export + composición de prueba (13 s) + gate + hoja de poses
    py kx_tadeo.py --export       # solo regenera motion_graphics/src/kx/tadeo/biblioteca.json
    py kx_tadeo.py --solo-hoja    # export + hoja de poses, sin vídeo

La biblioteca y las reglas de acting viven en JS (motion_graphics/src/kx/tadeo/);
este script las ejecuta en Node tal cual (sin bundler) para exportarlas y para
que los tests midan las mismas funciones que dibuja Remotion.
Evidencia: misiones/evidencia/0001-fase2/{hoja_de_poses.png, hoja_celdas.json,
gate.json, contactsheet.png, still.png}; vídeo en output/<fecha>-kx-tadeo/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
MG = ROOT / "motion_graphics"
KX = MG / "src" / "kx"
TADEO = KX / "tadeo"
BIBLIOTECA = TADEO / "biblioteca.json"
EVID = ROOT / "misiones" / "evidencia" / "0001-fase2"
HOJA_MADRE = ROOT / "assets" / "kx_cast" / "tadeo" / "_hojas" / "model_sheet.png"
FPS = 30
DURACION = 13 * FPS

# Composición de prueba: idle de 3 s, tres cambios con spring y un beat.
LINEA = [
    {"pose": "neutro", "t0": 0},
    {"pose": "explicando", "t0": 90},
    {"pose": "confundido", "t0": 170},
    {"pose": "decidido", "t0": 250, "beat": True},
]


# ------------------------------------------------------------------ Node
def node_eval(code: str, timeout: int = 60):
    """Ejecuta `code` (ESM) con acceso a ./kx/tokens.js y ./kx/tadeo/*.js y
    devuelve el JSON que imprima. Copia a un temporal con package.json
    type=module para no depender de bundler ni de node_modules."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node no está en el PATH")
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        (t / "kx" / "tadeo").mkdir(parents=True)
        shutil.copy2(KX / "tokens.js", t / "kx" / "tokens.js")
        for f in TADEO.glob("*.js"):
            shutil.copy2(f, t / "kx" / "tadeo" / f.name)
        (t / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        (t / "run.js").write_text(code, encoding="utf-8")
        r = subprocess.run([node, str(t / "run.js")], capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(f"node falló:\n{r.stderr}")
        return json.loads(r.stdout)


def exportar_biblioteca() -> dict:
    lib = node_eval('import { bibliotecaJSON } from "./kx/tadeo/poses.js";'
                    "process.stdout.write(JSON.stringify(bibliotecaJSON()));")
    BIBLIOTECA.write_text(json.dumps(lib, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return lib


def cargar_biblioteca() -> dict:
    return json.loads(BIBLIOTECA.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ guion
def pose_de_termino(term: str, lib: dict | None = None) -> str:
    """'*tadeo/estafado' -> 'estafado'. Un término fuera de la biblioteca
    hace fallar el constructor (A8): nunca cae a `neutro` en silencio."""
    import kx_cast

    lib = lib or cargar_biblioteca()
    t = kx_cast.strip_beat(term or "").strip()
    personaje, _, pose = t.partition("/")
    if personaje != "tadeo" or pose not in lib["poses"]:
        raise KeyError(f"character_term fuera de la biblioteca de Tadeo: {term!r}")
    return pose


# ------------------------------------------------------------------ caja
def caja_px(pose: str, lib: dict, escala: float = 1.0) -> dict:
    """Igual que tadeoBox() de poses.js (el gate y las plantillas la usan)."""
    x0, y0, x1, y1 = lib["medidas"][pose]["caja_u"]
    p = lib["rig"]["pantalla"]
    s = p["alto"] / lib["rig"]["alto"] * escala
    import math
    return {"x": math.floor(p["x"] + x0 * s), "y": math.floor(p["y"] - y1 * s),
            "w": math.ceil((x1 - x0) * s), "h": math.ceil((y1 - y0) * s)}


def caja_union(cajas: list[dict]) -> dict:
    x0 = min(c["x"] for c in cajas)
    y0 = min(c["y"] for c in cajas)
    x1 = max(c["x"] + c["w"] for c in cajas)
    y1 = max(c["y"] + c["h"] for c in cajas)
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


# ------------------------------------------------------------------ hoja
def celdas_hoja(lib: dict) -> dict:
    """Lo que la hoja de poses dibuja: cada elemento de la biblioteca una vez."""
    return {
        "poses": list(lib["poses"]),
        "siluetas": list(lib["poses"]),
        "expresiones": list(lib["expresiones"]),
        "miradas": list(lib["miradas"]),
        "cabezas": [{"expr": e, "mirada": m} for m in lib["miradas"] for e in lib["expresiones"]],
        "comparacion": ["orgulloso", "codicia"],
    }


def render_hoja(lib: dict) -> Path:
    pub = MG / "public" / "kxm" / "tadeo"  # ignorado por git
    pub.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HOJA_MADRE, pub / "model_sheet.png")
    celdas = celdas_hoja(lib)
    EVID.mkdir(parents=True, exist_ok=True)
    (EVID / "hoja_celdas.json").write_text(json.dumps(celdas, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    props = EVID / "_hoja_props.json"
    props.write_text(json.dumps({"celdas": celdas, "hojaMadre": "kxm/tadeo/model_sheet.png"}), encoding="utf-8")
    out = EVID / "hoja_de_poses.png"
    try:
        subprocess.run(["npx", "remotion", "still", "src/index.jsx", "KxTadeoHoja", str(out),
                        f"--props={props}", "--log=error"], cwd=MG, check=True, shell=True, timeout=600)
    finally:
        props.unlink(missing_ok=True)
    return out


# ------------------------------------------------------------------ gate
def check_nunca_congelado(video: Path, caja: dict) -> tuple[list[str], dict]:
    """A6.9: dos frames consecutivos de la caja del personaje siempre difieren."""
    import numpy as np

    import kx_gate

    W, H = kx_gate.W, kx_gate.H
    cmd = ["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    prev, n, iguales, minimo = None, 0, 0, 1e9
    x0, y0, x1, y1 = caja["x"], caja["y"], caja["x"] + caja["w"], caja["y"] + caja["h"]
    try:
        while True:
            buf = p.stdout.read(W * H)
            if len(buf) < W * H:
                break
            f = np.frombuffer(buf, np.uint8).reshape(H, W)[y0:y1, x0:x1].astype(np.int16)
            if prev is not None:
                d = float(np.abs(f - prev).mean())
                minimo = min(minimo, d)
                if d < 0.01:
                    iguales += 1
            prev, n = f, n + 1
    finally:
        p.stdout.close()
        p.wait(timeout=60)
    fails = [f"Tadeo congelado en {iguales} pares de frames consecutivos"] if iguales else []
    return fails, {"frames": n, "pares_identicos": iguales, "dif_media_minima": round(minimo, 4)}


def render_prueba(lib: dict) -> dict:
    import kx_gate

    node_eval('import { validarLinea } from "./kx/tadeo/acting.js";'
              f"validarLinea({json.dumps(LINEA)}); process.stdout.write('true');")
    out = ROOT / "output" / f"{dt.date.today():%Y-%m-%d}-kx-tadeo"
    out.mkdir(parents=True, exist_ok=True)
    props = {"linea": LINEA, "durationInFrames": DURACION}
    (out / "props.json").write_text(json.dumps(props), encoding="utf-8")
    video = out / "video.mp4"
    subprocess.run(["npx", "remotion", "render", "src/index.jsx", "KxTadeo", str(video),
                    f"--props={out / 'props.json'}", "--crf=18", "--log=error"],
                   cwd=MG, check=True, shell=True, timeout=1200)
    still_frame = LINEA[-1]["t0"] + 60  # el beat asentado: la pose más grande
    still = EVID / "still.png"
    subprocess.run(["npx", "remotion", "still", "src/index.jsx", "KxTadeo", str(still),
                    f"--props={out / 'props.json'}", f"--frame={still_frame}", "--log=error"],
                   cwd=MG, check=True, shell=True, timeout=600)

    cajas = [caja_px(c["pose"], lib, lib["rig"]["beatEscala"] if c.get("beat") else 1.0) for c in LINEA]
    caja = caja_union(cajas)
    report = {"linea": LINEA, "char_box": caja, "duracion_s": DURACION / FPS}
    fails = []
    for name, fn in (("palette_still", lambda: kx_gate.check_palette_image(still, [caja])),
                     ("palette", lambda: kx_gate.check_palette(video, [caja])),
                     ("safe_zone", lambda: kx_gate.check_safe_zone(video)),
                     ("nunca_congelado", lambda: check_nunca_congelado(video, caja))):
        f, info = fn()
        fails += f
        report[name] = info
    report["fails"] = fails
    kx_gate.contact_sheet(video, EVID / "contactsheet.png")
    kx_gate.save_report(EVID / "gate.json", report)
    shutil.copy2(video, out / "video.mp4") if video.parent != out else None
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--solo-hoja", action="store_true")
    a = ap.parse_args()
    lib = exportar_biblioteca()
    print(f"biblioteca: {len(lib['poses'])} poses · {len(lib['expresiones'])} expresiones · {len(lib['miradas'])} miradas")
    if a.export:
        return 0
    print("hoja:", render_hoja(lib))
    if a.solo_hoja:
        return 0
    report = render_prueba(lib)
    print(json.dumps({k: v for k, v in report.items() if k != "linea"}, ensure_ascii=False, indent=1))
    print("OK" if not report["fails"] else "FALLA")
    return 1 if report["fails"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
