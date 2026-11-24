"""Parecido MEDIBLE entre el rig de Tadeo y la hoja madre (Misión 0001, Fase 2).

    py kx_parecido.py      # render del neutro en la rejilla de la hoja, solape, marcas y paneles

Renderiza el neutro del rig (composición KxTadeoMolde) en la MISMA rejilla de
píxeles que la vista frontal de la hoja madre reescalada ×4 (misma escala y
mismo anclaje: pies en el suelo de la hoja, eje en la nariz) y mide con UN solo
código las dos imágenes:
  solape     IoU de las siluetas (todo lo que el papel exterior no alcanza)
  marcas     ancho/alto de cabeza, alto y ancho de oreja, distancia entre ojos,
             ancho del antifaz, del hocico y de la panza
Salida en misiones/evidencia/0001-fase2/: parecido.json, rig_neutro.png,
parecido_lado_a_lado.png, parecido_solape.png, parecido_marcas.png.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# cv2/numpy solo hacen falta para medir; el test de la CI (solo pytest) usa
# huella() y los umbrales sin importarlos.
try:
    import cv2
    import numpy as np

    import kx_trazo as KT
except ImportError:  # pragma: no cover - entorno de CI
    cv2 = np = KT = None

ROOT = Path(__file__).resolve().parent
MG = ROOT / "motion_graphics"
EVID = ROOT / "misiones" / "evidencia" / "0001-fase2"
IOU_MIN = 0.95
MARCA_TOL = 0.03
# Lo que el resultado depende de: si cambia, parecido.json está viejo.
ENTRADAS = ["motion_graphics/src/kx/tadeo/partes.jsx", "motion_graphics/src/kx/tadeo/poses.js",
            "motion_graphics/src/kx/tadeo/traza.js", "motion_graphics/src/kx/tadeo/acting.js",
            "motion_graphics/src/kx/tokens.js", "kx_trazo.py", "kx_parecido.py"]


def huella() -> str:
    h = hashlib.sha256()
    for rel in ENTRADAS:
        h.update(rel.encode())
        h.update((ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


# ------------------------------------------------------------------ medir
def _runs(row: np.ndarray):
    """[(x0, x1)] tramos True de una fila."""
    d = np.diff(np.r_[0, row.astype(np.int8), 0])
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0] - 1))


def marcas(g: np.ndarray, sil: np.ndarray, xc: float) -> dict:
    """Las mismas mediciones para la hoja y para el rig (px)."""
    H, W = g.shape
    ink = g < KT.INK
    comps = KT.componentes(sil & ~ink, 300)
    top = int(np.where(sil.any(1))[0].min())
    # lóbulos del antifaz: las dos zonas oscuras mayores en el tercio alto
    lob = sorted([(m, st, cen) for m, st, cen in comps if 70 < np.median(g[m]) < 125 and cen[1] < 0.45 * H],
                 key=lambda t: -t[1][4])[:2]
    lob = sorted(lob, key=lambda t: t[2][0])
    lm = [KT.fill_holes(m) for m, _, _ in lob]
    ys, xs = np.where(lm[0] | lm[1])
    l_y0, l_y1 = ys.min(), ys.max()
    ojos = []
    for l in lm:
        bl = [(m, st, cen) for m, st, cen in comps if (m & l).sum() > 0.9 * m.sum() and np.median(g[m]) > 225]
        m = KT.fill_holes(max(bl, key=lambda t: t[1][4])[0])
        yy, xx = np.where(m)
        ojos.append((xx.mean(), yy.mean()))
    # nariz y barbilla por la columna del eje
    col = ink[:, int(round(xc))]
    runs = [r for r in _runs(col) if r[0] > l_y1]
    nariz_y1 = runs[0][1]
    barbilla = max(r[1] for r in runs if r[0] < nariz_y1 + 0.16 * H)
    # cabeza: ancho máximo entre los ojos y la barbilla; alto de la punta de oreja a la barbilla
    ancho_cab = max(sil[y].sum() if len(_runs(sil[y])) == 1 else max(b - a + 1 for a, b in _runs(sil[y]))
                    for y in range(int(np.mean([o[1] for o in ojos])), barbilla - 20))
    alto_cab = barbilla - top
    # oreja izquierda: de la punta a donde se funde con el cráneo (el hueco
    # entre oreja y coronilla, de más de 40 px, desaparece)
    punta = mezcla = None
    vistas_dos = False
    for y in range(top, l_y0):
        r = [t for t in _runs(sil[y]) if t[0] < xc]
        if r and punta is None:
            punta = y
        if punta is None:
            continue
        hueco = len(r) >= 2 and any(r[i + 1][0] - r[i][1] > 40 for i in range(len(r) - 1))
        if hueco:
            vistas_dos = True
        elif vistas_dos:
            mezcla = y
            break
    alto_oreja = mezcla - punta
    y_med = int(punta + 0.6 * alto_oreja)
    r = [t for t in _runs(sil[y_med]) if t[0] < xc]
    ancho_oreja = r[0][1] - r[0][0] + 1
    # hocico: el tramo crema que cruza el eje entre la sonrisa y la barbilla
    crema = (g > 195) & sil
    cerca = [r for r in runs if r[0] < nariz_y1 + 0.16 * H]
    y_h = int((cerca[-2][1] + cerca[-1][0]) / 2)
    tr = [t for t in _runs(crema[y_h]) if t[0] <= xc <= t[1]]
    ancho_hocico = (tr[0][1] - tr[0][0] + 1) if tr else 0
    # panza: tramo crema más ancho que contiene el eje, del pecho a la cadera
    ancho_panza = 0
    for y in range(barbilla + int(0.06 * H), barbilla + int(0.40 * H)):
        tr = [t for t in _runs(crema[y]) if t[0] <= xc <= t[1]]
        if tr:
            ancho_panza = max(ancho_panza, tr[0][1] - tr[0][0] + 1)
    return {
        "cabeza_ancho_alto": ancho_cab / alto_cab,
        "oreja_alto": float(alto_oreja),
        "oreja_ancho": float(ancho_oreja),
        "ojos_distancia": float(abs(ojos[1][0] - ojos[0][0])),
        "antifaz_ancho": float(xs.max() - xs.min()),
        "hocico_ancho": float(ancho_hocico),
        "panza_ancho": float(ancho_panza),
    }


def iou(a: np.ndarray, b: np.ndarray) -> float:
    return float((a & b).sum() / (a | b).sum())


# ------------------------------------------------------------------ render
def render_rig(cal: dict, shape) -> np.ndarray:
    H, W = shape
    out = EVID / "rig_neutro.png"
    props = EVID / "_molde_props.json"
    props.write_text(json.dumps({"xc": cal["xc"], "suelo": cal["suelo"], "s": cal["s"], "w": W, "h": H}), encoding="utf-8")
    try:
        subprocess.run(["npx", "remotion", "still", "src/index.jsx", "KxTadeoMolde", str(out),
                        f"--props={props}", "--log=error"], cwd=MG, check=True, shell=True, timeout=600)
    finally:
        props.unlink(missing_ok=True)
    return cv2.cvtColor(cv2.imread(str(out)), cv2.COLOR_BGR2GRAY)


# ------------------------------------------------------------------ paneles
def _font(size):
    from PIL import ImageFont
    for f in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def paneles(madre, rig, sil_m, sil_r, res):
    from PIL import Image, ImageDraw

    EVID.mkdir(parents=True, exist_ok=True)
    lado = np.hstack([madre, np.full((madre.shape[0], 40), 255, np.uint8), rig])
    im = Image.fromarray(lado).convert("RGB")
    d = ImageDraw.Draw(im)
    d.text((20, 10), "hoja madre", fill=(17, 17, 17), font=_font(44))
    d.text((madre.shape[1] + 60, 10), "rig (neutro)", fill=(17, 17, 17), font=_font(44))
    im.save(EVID / "parecido_lado_a_lado.png")
    # solape: el rig al 50 % sobre la madre + borde de cada silueta
    mix = (0.5 * madre.astype(float) + 0.5 * rig.astype(float)).astype(np.uint8)
    v = cv2.cvtColor(mix, cv2.COLOR_GRAY2RGB)
    for m, col in ((sil_m, (0, 120, 255)), (sil_r, (230, 40, 40))):
        e = m & ~cv2.erode(m.astype(np.uint8), KT.disk(3)).astype(bool)
        v[e] = col
    im = Image.fromarray(v)
    d = ImageDraw.Draw(im)
    d.text((20, 10), f"solape IoU = {res['iou']:.4f}  (azul: madre · rojo: rig)", fill=(17, 17, 17), font=_font(40))
    im.save(EVID / "parecido_solape.png")
    # tabla de marcas
    filas = list(res["marcas"].items())
    im = Image.new("RGB", (1500, 120 + 70 * len(filas)), (244, 241, 234))
    d = ImageDraw.Draw(im)
    f, fb = _font(34), _font(38)
    d.text((30, 30), "marca", fill=(17, 17, 17), font=fb)
    for x, t in ((560, "madre"), (820, "rig"), (1060, "desviación")):
        d.text((x, 30), t, fill=(17, 17, 17), font=fb)
    for i, (k, m) in enumerate(filas):
        y = 110 + 70 * i
        ok = abs(m["desviacion"]) <= MARCA_TOL
        d.text((30, y), k, fill=(17, 17, 17), font=f)
        d.text((560, y), f"{m['madre']:.3f}", fill=(17, 17, 17), font=f)
        d.text((820, y), f"{m['rig']:.3f}", fill=(17, 17, 17), font=f)
        d.text((1060, y), f"{m['desviacion'] * 100:+.2f} %  {'OK' if ok else 'FUERA'}", fill=(17, 17, 17), font=f)
    im.save(EVID / "parecido_marcas.png")


def medir() -> dict:
    madre, sil_m = KT.frente()
    cal = KT.calibrar(madre, sil_m)
    rig = render_rig(cal, madre.shape)
    sil_r = KT.silueta(rig)
    mm, mr = marcas(madre, sil_m, cal["xc"]), marcas(rig, sil_r, cal["xc"])
    res = {"huella": huella(), "iou": round(iou(sil_m, sil_r), 4), "iou_min": IOU_MIN, "tolerancia_marcas": MARCA_TOL,
           "marcas": {k: {"madre": round(mm[k], 4), "rig": round(mr[k], 4),
                          "desviacion": round((mr[k] - mm[k]) / mm[k], 4)} for k in mm}}
    paneles(madre, rig, sil_m, sil_r, res)
    (EVID / "parecido.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return res


def main() -> int:
    res = medir()
    print(f"IoU {res['iou']:.4f} (mín {IOU_MIN})")
    fuera = []
    for k, m in res["marcas"].items():
        ok = abs(m["desviacion"]) <= MARCA_TOL
        fuera += [] if ok else [k]
        print(f"  {k:18s} madre {m['madre']:9.3f}  rig {m['rig']:9.3f}  {m['desviacion'] * 100:+6.2f} %  {'OK' if ok else 'FUERA'}")
    ok = res["iou"] >= IOU_MIN and not fuera
    print("OK" if ok else "FALLA")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
