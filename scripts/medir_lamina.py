"""Comprobaciones AUTOMÁTICAS de una lámina de pose de Tadeo (misión 0005).

    py scripts/medir_lamina.py misiones/evidencia/0005/*_api.png

Implementa los puntos de la sección 5 de misiones/2026-11-25-especificacion-9-laminas.md que se pueden
medir en el píxel: (1) una sola figura sobre fondo blanco, (2/3) margen libre alrededor, (4) sin color.
NO mide el solape de trazado ni las marcas de proporción de la sección 2: eso necesita el trazador de
láminas de pose, que todavía no existe (kx_trazo.py solo traza la vista frontal de la hoja madre).
Salida: tabla por lámina y JSON en misiones/evidencia/0005/medidas.json. Sale con 1 si alguna falla.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
UMBRAL = {
    "fondo_min": 245,         # luminancia mínima del borde de la imagen (blanco puro)
    "margen_min": 0.015,      # fracción del lado entre la figura y el borde: nada recortado (regla 3 de la spec)
    "croma_max": 10,          # canal más alto − más bajo: por encima ya no es gris
    "color_max": 0.004,       # fracción de la figura con croma > croma_max
    "componentes_max": 1,     # figuras separadas (tras cerrar huecos de 7 px)
}


def medir(ruta: Path) -> dict:
    img = cv2.imread(str(ruta), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"no puedo leer {ruta}")
    h, w = img.shape[:2]
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    figura = gris < 235
    borde = np.concatenate([gris[0], gris[-1], gris[:, 0], gris[:, -1]])
    cerrada = cv2.morphologyEx(figura.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, _, st, _ = cv2.connectedComponentsWithStats(cerrada, 8)
    grandes = [i for i in range(1, n) if st[i, 4] > 0.01 * h * w]
    ys, xs = np.where(figura)
    caja = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    margen = min(caja[0] / w, caja[1] / h, 1 - caja[2] / w, 1 - caja[3] / h)
    croma = img.max(axis=2).astype(int) - img.min(axis=2).astype(int)
    color = float((croma[figura] > UMBRAL["croma_max"]).mean())
    fallos = []
    if borde.min() < UMBRAL["fondo_min"]:
        fallos.append("fondo no blanco")
    if len(grandes) > UMBRAL["componentes_max"]:
        fallos.append(f"{len(grandes)} figuras o restos sueltos")
    if margen < UMBRAL["margen_min"]:
        fallos.append("figura pegada al borde")
    if color > UMBRAL["color_max"]:
        fallos.append(f"color ({100 * color:.1f} % de la figura)")
    return {"archivo": ruta.name, "tam": [w, h], "fondo_min": int(borde.min()), "figuras": len(grandes),
            "margen": round(margen, 3), "color_pct": round(100 * color, 2), "caja": caja, "fallos": fallos}


def main(argv: list[str]) -> int:
    rutas = [Path(a) for a in argv] or sorted((ROOT / "misiones" / "evidencia" / "0005").glob("*_api.png"))
    res = [medir(r) for r in rutas]
    for r in res:
        print(f"{r['archivo']:22s} {r['tam'][0]}x{r['tam'][1]}  fondo {r['fondo_min']:3d}  figuras {r['figuras']}  "
              f"margen {r['margen']:.3f}  color {r['color_pct']:5.2f} %  {'OK' if not r['fallos'] else 'FALLA: ' + '; '.join(r['fallos'])}")
    destino = (rutas[0].parent if rutas else ROOT) / "medidas.json"
    destino.write_text(json.dumps({"umbral": UMBRAL, "laminas": res}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if any(r["fallos"] for r in res) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
