"""Parecido MEDIBLE entre el rig de Tadeo y la hoja madre (Misión 0001, Fase 2).

    py kx_parecido.py      # render del neutro en la rejilla de la hoja, solape, marcas y paneles

Renderiza el neutro del rig (composición KxTadeoMolde) en la MISMA rejilla de
píxeles que la vista frontal de la hoja madre reescalada ×4 (misma escala y
mismo anclaje: pies en el suelo de la hoja, eje en la nariz) y mide con UN solo
código las dos imágenes:
  solape     IoU de las siluetas (todo lo que el papel exterior no alcanza)
  marcas     ancho/alto de cabeza, alto y ancho de oreja, distancia entre ojos,
             ancho del antifaz, del hocico y de la panza
  tinta      (iteración 2) tinta = luminancia < 60 dentro de la silueta:
             la de la madre presente en el rig a ≤ 6 px y viceversa, área rig/madre
  grosor     p10/p50/p90 del contorno y de las líneas interiores, en u
             (grosor local 2·dt + 1 por píxel de tinta; interior = a más de 10 u del papel)
  tono       luminancia / papel sin tinta, suavizada σ = 6 px: error medio y
             % de superficie con error > 0,08
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
IOU_MIN = 0.98
MARCA_TOL = 0.03
# La barra de «perfecta» (I2-3). No se aflojan: si no se alcanzan, se reporta.
BARRA = {"tinta_madre_en_rig_min": 0.97, "tinta_rig_en_madre_min": 0.97, "area_tinta": (0.97, 1.03),
         "grosor_interior_p50": (4.6, 5.6), "tono_error_medio_max": 0.030, "tono_superficie_max": 0.05}
TINTA_LUM = 60
TINTA_DIST = 6
TONO_SIGMA = 6
TONO_UMBRAL = 0.08
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


def tinta(g, sil):
    return (g < TINTA_LUM) & sil


def medir_tinta(im, ir):
    dr = cv2.distanceTransform((~ir).astype(np.uint8), cv2.DIST_L2, 5)
    dm = cv2.distanceTransform((~im).astype(np.uint8), cv2.DIST_L2, 5)
    falta = im & (dr > TINTA_DIST)
    sobra = ir & (dm > TINTA_DIST)
    return {"madre_en_rig": float(1 - falta.sum() / im.sum()), "rig_en_madre": float(1 - sobra.sum() / ir.sum()),
            "area": float(ir.sum() / im.sum())}, falta, sobra


def grosores(i, sil, s):
    """Grosor local de cada píxel de tinta (el de su esqueleto más cercano,
    2·dt + 1), ponderado por área; solo líneas (< 14 u: fuera nariz y pupilas).
    Interior = a más de 10 u del papel exterior; contorno = el resto."""
    from skimage.morphology import skeletonize
    dt = cv2.distanceTransform(i.astype(np.uint8), cv2.DIST_L2, 5)
    sk = skeletonize(i)
    _, lab = cv2.distanceTransformWithLabels((~sk).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.where(sk)
    val = np.zeros(lab.max() + 1)
    val[lab[ys, xs]] = 2 * dt[ys, xs] + 1
    w = val[lab[i]] / s
    papel = cv2.distanceTransform(sil.astype(np.uint8), cv2.DIST_L2, 5)[i]
    lin = w < 14
    pc = lambda v: [round(float(x), 2) for x in np.percentile(v, [10, 50, 90])]  # noqa: E731
    return {"interior": pc(w[(papel > 10 * s) & lin]), "contorno": pc(w[(papel <= 10 * s) & lin])}


def mapa_tono(g, sil, i):
    papel = float(np.median(g[~sil]))
    m = (sil & ~i).astype(float)
    num = cv2.GaussianBlur(g.astype(float) / papel * m, (0, 0), TONO_SIGMA)
    return num / np.maximum(cv2.GaussianBlur(m, (0, 0), TONO_SIGMA), 1e-6)


def medir_tono(gm, sm, im, gr, sr, ir):
    reg = sm & sr & ~(im | ir)
    e = np.abs(mapa_tono(gm, sm, im) - mapa_tono(gr, sr, ir))
    e[~reg] = 0
    return {"error_medio": float(e[reg].mean()), "superficie_mayor_008": float((e[reg] > TONO_UMBRAL).mean())}, e, reg


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


def panel_residuo(madre, falta, sobra, e, reg, res):
    """Mapa de tinta que falta (azul) / sobra (rojo) y de error tonal > 0,08 (ámbar)."""
    from PIL import Image, ImageDraw
    v = cv2.cvtColor((0.35 * madre + 0.65 * 255).astype(np.uint8), cv2.COLOR_GRAY2RGB)
    v[reg & (e > TONO_UMBRAL)] = (250, 200, 90)
    v[cv2.dilate(falta.astype(np.uint8), KT.disk(2)).astype(bool)] = (0, 90, 255)
    v[cv2.dilate(sobra.astype(np.uint8), KT.disk(2)).astype(bool)] = (230, 30, 30)
    im = Image.fromarray(v)
    d = ImageDraw.Draw(im)
    t = res["tinta"]
    d.text((20, 10), f"tinta que falta (azul) {100 * (1 - t['madre_en_rig']):.1f} %  ·  sobra (rojo) {100 * (1 - t['rig_en_madre']):.1f} %",
           fill=(17, 17, 17), font=_font(34))
    d.text((20, 56), f"error tonal > 0,08 (ámbar) {100 * res['tono']['superficie_mayor_008']:.1f} %", fill=(17, 17, 17), font=_font(34))
    im.save(EVID / "parecido_residuo.png")
    filas = filas_barra(res)
    im = Image.new("RGB", (1500, 120 + 64 * len(filas)), (244, 241, 234))
    d = ImageDraw.Draw(im)
    f, fb = _font(32), _font(36)
    for x, h in ((30, "medida (I2-3)"), (700, "umbral"), (980, "rig")):
        d.text((x, 30), h, fill=(17, 17, 17), font=fb)
    for i, (k, umb, val, ok) in enumerate(filas):
        y = 104 + 64 * i
        for x, t_ in ((30, k), (700, umb), (980, val), (1250, "OK" if ok else "NO")):
            d.text((x, y), t_, fill=(17, 17, 17), font=f)
    im.save(EVID / "parecido_barra.png")


def filas_barra(res):
    t, g, o = res["tinta"], res["grosor"], res["tono"]
    b = BARRA
    peor = max(abs(m["desviacion"]) for m in res["marcas"].values())
    gi = g["rig"]["interior"][1]
    return [
        ("IoU de silueta", f"≥ {IOU_MIN}", f"{res['iou']:.4f}", res["iou"] >= IOU_MIN),
        ("7 marcas (peor)", "±3 %", f"{100 * peor:.2f} %", peor <= MARCA_TOL),
        ("tinta madre en rig", "≥ 97 %", f"{100 * t['madre_en_rig']:.1f} %", t["madre_en_rig"] >= b["tinta_madre_en_rig_min"]),
        ("tinta rig en madre", "≥ 97 %", f"{100 * t['rig_en_madre']:.1f} %", t["rig_en_madre"] >= b["tinta_rig_en_madre_min"]),
        ("área tinta rig/madre", "0,97–1,03", f"{t['area']:.3f}", b["area_tinta"][0] <= t["area"] <= b["area_tinta"][1]),
        ("grosor interior p50", "4,6–5,6 u", f"{gi:.2f} u", b["grosor_interior_p50"][0] <= gi <= b["grosor_interior_p50"][1]),
        ("error tonal medio", "≤ 0,030", f"{o['error_medio']:.4f}", o["error_medio"] <= b["tono_error_medio_max"]),
        ("superficie error > 0,08", "≤ 5 %", f"{100 * o['superficie_mayor_008']:.1f} %", o["superficie_mayor_008"] <= b["tono_superficie_max"]),
    ]


def medir(render=True) -> dict:
    madre, sil_m = KT.frente()
    cal = KT.calibrar(madre, sil_m)
    rig = render_rig(cal, madre.shape) if render else cv2.cvtColor(cv2.imread(str(EVID / "rig_neutro.png")), cv2.COLOR_BGR2GRAY)
    sil_r = KT.silueta(rig)
    mm, mr = marcas(madre, sil_m, cal["xc"]), marcas(rig, sil_r, cal["xc"])
    res = {"huella": huella(), "iou": round(iou(sil_m, sil_r), 4), "iou_min": IOU_MIN, "tolerancia_marcas": MARCA_TOL,
           "marcas": {k: {"madre": round(mm[k], 4), "rig": round(mr[k], 4),
                          "desviacion": round((mr[k] - mm[k]) / mm[k], 4)} for k in mm}}
    im, ir = tinta(madre, sil_m), tinta(rig, sil_r)
    t, falta, sobra = medir_tinta(im, ir)
    res["tinta"] = {k: round(v, 4) for k, v in t.items()}
    res["grosor"] = {"madre": grosores(im, sil_m, cal["s"]), "rig": grosores(ir, sil_r, cal["s"])}
    o, e, reg = medir_tono(madre, sil_m, im, rig, sil_r, ir)
    res["tono"] = {k: round(v, 4) for k, v in o.items()}
    res["barra"] = BARRA
    res["cumple"] = {k: bool(ok) for k, _, _, ok in filas_barra(res)}
    paneles(madre, rig, sil_m, sil_r, res)
    panel_residuo(madre, falta, sobra, e, reg, res)
    (EVID / "parecido.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return res


def main() -> int:
    res = medir(render="--sin-render" not in sys.argv)
    print(f"IoU {res['iou']:.4f} (mín {IOU_MIN})")
    fuera = []
    for k, m in res["marcas"].items():
        ok = abs(m["desviacion"]) <= MARCA_TOL
        fuera += [] if ok else [k]
        print(f"  {k:18s} madre {m['madre']:9.3f}  rig {m['rig']:9.3f}  {m['desviacion'] * 100:+6.2f} %  {'OK' if ok else 'FUERA'}")
    for k, umb, val, ok_ in filas_barra(res)[2:]:
        print(f"  {k:24s} {val:>10s}  (umbral {umb})  {'OK' if ok_ else 'NO'}")
    print(f"  grosor madre {res['grosor']['madre']}  rig {res['grosor']['rig']}")
    ok = all(res["cumple"].values())
    print("OK" if ok else "FALLA")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
