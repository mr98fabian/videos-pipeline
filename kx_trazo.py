"""Traza a Tadeo SOBRE la hoja madre (Misión 0001, Fase 2, iteración de parecido).

    py kx_trazo.py            # escribe motion_graphics/src/kx/tadeo/traza.js
    py kx_trazo.py --debug    # además, una superposición de piezas en misiones/evidencia/0001-fase2/

No dibuja con primitivas: segmenta la vista frontal de
assets/kx_cast/tadeo/_hojas/model_sheet.png (reescalada ×4) en piezas separadas
por la propia tinta del dibujo, el tono y unos pocos cortes (bases de oreja,
coronilla, barbilla y axilas). Cada contorno pasa a ser un camino en unidades
del rig (alto 1000 u, suelo en y = 0, eje x = 0 en la nariz).
Brazos y piernas no se trazan como forma: de la banda que dejan entre sus
dos líneas de tinta salen la línea central y el grosor del tubo rubber hose.
Las caras de expresión (fila inferior de la hoja) se trazan igual (bocas).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
HOJA = ROOT / "assets" / "kx_cast" / "tadeo" / "_hojas" / "model_sheet.png"
OUT = ROOT / "motion_graphics" / "src" / "kx" / "tadeo" / "traza.js"
EVID = ROOT / "misiones" / "evidencia" / "0001-fase2"

F = 4                      # factor de reescalado para trazar con curvas suaves
FRENTE = (55, 60, 385, 485)  # recorte de la vista frontal en la hoja (x0, y0, x1, y1)
INK = 75                   # luminancia de tinta
HALF_INK = 6               # media línea de tinta en px ×4: el camino va por el centro del trazo


# ------------------------------------------------------------------ carga
def hoja_gris() -> np.ndarray:
    """Hoja en gris sin las líneas guía horizontales del model sheet."""
    g = cv2.cvtColor(cv2.imread(str(HOJA)), cv2.COLOR_BGR2GRAY).astype(np.int16)
    for d in (3, 4):
        up, dn = np.roll(g, d, 0), np.roll(g, -d, 0)
        g[(g < 225) & (g > 120) & (up > 228) & (dn > 228)] = 240
    return g.astype(np.uint8)


def silueta(c: np.ndarray) -> np.ndarray:
    """Todo lo que el papel exterior no alcanza (relleno desde la esquina)."""
    m = (c > 220).astype(np.uint8)
    ff = np.zeros((c.shape[0] + 2, c.shape[1] + 2), np.uint8)
    cv2.floodFill(m, ff, (0, 0), 2)
    return m != 2


def frente() -> tuple[np.ndarray, np.ndarray]:
    g = hoja_gris()
    x0, y0, x1, y1 = FRENTE
    cb = cv2.resize(g[y0:y1, x0:x1], None, fx=F, fy=F, interpolation=cv2.INTER_CUBIC)
    return cb, silueta(cb)


def calibrar(cb: np.ndarray, sil: np.ndarray) -> dict:
    ys = np.where(sil.any(axis=1))[0]
    top, suelo = int(ys.min()), int(ys.max())
    # eje: centro de la nariz (la mancha de tinta mayor bajo los ojos, al centro)
    band = (cb < INK).astype(np.uint8)
    band[: int(top + 0.25 * (suelo - top))] = 0
    band[int(top + 0.33 * (suelo - top)):] = 0
    n, lab, st, cen = cv2.connectedComponentsWithStats(band, 8)
    mid = cb.shape[1] / 2
    best = min((i for i in range(1, n) if st[i, 4] > 1500), key=lambda i: abs(cen[i][0] - mid))
    return {"top": top, "suelo": suelo, "xc": float(cen[best][0]), "s": (suelo - top) / 1000.0}


# ------------------------------------------------------------------ util
def to_u(cal, pts):
    pts = np.asarray(pts, float)
    return np.stack([(pts[:, 0] - cal["xc"]) / cal["s"], (cal["suelo"] - pts[:, 1]) / cal["s"]], 1)


def to_px(cal, pts):
    pts = np.asarray(pts, float)
    return np.stack([pts[:, 0] * cal["s"] + cal["xc"], cal["suelo"] - pts[:, 1] * cal["s"]], 1)


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def fill_holes(m: np.ndarray) -> np.ndarray:
    m = m.astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m)
    cv2.drawContours(out, cs, -1, 1, -1)
    return out.astype(bool)


def contornos(m: np.ndarray, min_area=60, eps=1.0, suav=2.0):
    """Contornos exteriores suavizados y simplificados (px)."""
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        if cv2.contourArea(c) < min_area:
            continue
        p = c[:, 0, :].astype(float)
        if suav and len(p) > 12:
            k = int(3 * suav) | 1
            pad = np.concatenate([p[-k:], p, p[:k]])
            w = np.exp(-0.5 * (np.arange(-k, k + 1) / suav) ** 2)
            w /= w.sum()
            p = np.stack([np.convolve(pad[:, i], w, "same")[k:-k] for i in range(2)], 1)
        a = cv2.approxPolyDP(p.astype(np.float32).reshape(-1, 1, 2), eps, True)[:, 0, :]
        if len(a) >= 3:
            out.append(a)
    return out


def r1(a):
    return [[round(float(x), 1), round(float(y), 1)] for x, y in a]


def poly_u(cal, m, **kw):
    return [r1(to_u(cal, c)) for c in contornos(m, **kw)]


def mayor(m: np.ndarray) -> np.ndarray:
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    if n <= 1:
        return m.astype(bool)
    i = 1 + int(np.argmax(st[1:, 4]))
    return lab == i


def componentes(m, min_area=1):
    n, lab, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    return [(lab == i, st[i], cen[i]) for i in range(1, n) if st[i, 4] >= min_area]


def lado_de_recta(shape, a, b):
    """>0 a la izquierda de a→b (en coordenadas de imagen)."""
    yy, xx = np.mgrid[0: shape[0], 0: shape[1]]
    return (b[0] - a[0]) * (yy - a[1]) - (b[1] - a[1]) * (xx - a[0])


def trazo_sin_cortes(cal, m, cortes: np.ndarray, **kw):
    """Contorno de `m` en tramos abiertos que evitan los bordes de corte
    (ahí la pieza continúa en otra capa: no lleva línea)."""
    out = []
    for c in contornos(m, eps=0.8, **kw):
        ok = [not cortes[int(min(max(y, 0), cortes.shape[0] - 1)), int(min(max(x, 0), cortes.shape[1] - 1))] for x, y in c]
        if all(ok):
            out.append(r1(to_u(cal, np.vstack([c, c[:1]]))))
            continue
        i0 = ok.index(False)
        rot = list(range(i0, len(c))) + list(range(i0))
        run = []
        for i in rot + [rot[0]]:
            if ok[i]:
                run.append(c[i])
            elif len(run) >= 2:
                out.append(r1(to_u(cal, np.array(run))))
                run = []
            else:
                run = []
        if len(run) >= 2:
            out.append(r1(to_u(cal, np.array(run))))
    return out


def separar_nariz(m: np.ndarray):
    """La nariz es la única mancha GRUESA de la tinta del hocico: una apertura
    morfológica la separa del surco y la boca, que son líneas finas."""
    gruesa = mayor(cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, disk(11)).astype(bool))
    nariz = m & cv2.dilate(gruesa.astype(np.uint8), disk(4)).astype(bool)
    return fill_holes(nariz), m & ~nariz


# ------------------------------------------------------------------ miembros
def runs_tinta(row: np.ndarray, x_from: int, step: int, limit: int):
    """Tramos de tinta recorriendo la fila desde x_from (step ±1)."""
    out, x, en = [], x_from, False
    while 0 <= x < len(row) and len(out) < limit:
        t = row[x] < 95
        if t and not en:
            ini = x
        if not t and en:
            out.append((min(ini, x - step), max(ini, x - step)))
        en = t
        x += step
    return out


def banda_miembro(cb, sil, ys, desde_fuera=True, izquierda=True):
    """Centro y ancho exterior (de borde exterior de tinta a borde exterior) por fila."""
    pts = []
    for y in ys:
        row = cb[y]
        xs = np.where(sil[y])[0]
        if not len(xs):
            continue
        x_from = int(xs.min()) if izquierda else int(xs.max())
        r = runs_tinta(row, x_from, 1 if izquierda else -1, 2)
        if len(r) < 2:
            continue
        a, b = r[0], r[1]
        outer = a[0] if izquierda else a[1]
        inner = b[1] if izquierda else b[0]
        w = abs(inner - outer)
        if 40 < w < 220:
            pts.append((y, (outer + inner) / 2, w))
    return np.array(pts, float)


def ajustar_bezier(P: np.ndarray):
    """Bézier cuadrática por mínimos cuadrados con extremos fijos (parámetro por cuerda)."""
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = d / d[-1]
    p0, p2 = P[0], P[-1]
    b = 2 * (1 - t) * t
    rhs = P - ((1 - t) ** 2)[:, None] * p0 - (t ** 2)[:, None] * p2
    p1 = (b[:, None] * rhs).sum(0) / (b ** 2).sum()
    return p0, p1, p2


def bez(p0, p1, p2, t):
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2


# ------------------------------------------------------------------ principal
def trazar(debug=False) -> dict:
    cb, sil = frente()
    cal = calibrar(cb, sil)
    xc = cal["xc"]
    H, W = cb.shape
    yy, xx = np.mgrid[0:H, 0:W]
    ink = cb < INK
    ux = lambda u: xc + u * cal["s"]  # noqa: E731
    uy = lambda u: cal["suelo"] - u * cal["s"]  # noqa: E731
    T = {"escala": {"px_por_u": cal["s"], "xc_px": xc, "suelo_px": cal["suelo"], "top_px": cal["top"], "F": F,
                    "recorte": FRENTE}}

    # ---- componentes libres de tinta (piezas cerradas por el propio dibujo)
    libre = sil & ~ink
    comps = componentes(libre, 300)

    def comp_en(px, py):
        for m, st, cen in comps:
            if m[int(py), int(px)]:
                return m
        return None

    # ---- guantes: zonas blancas grandes en la mitad baja
    guantes = {}
    for m, st, cen in comps:
        x, y, w, h, a = st
        if a > 25000 and y > 0.55 * H and np.median(cb[m]) > 235 and h > 250:
            guantes["I" if cen[0] < xc else "D"] = fill_holes(m)
    assert set(guantes) == {"I", "D"}, "no encuentro los dos guantes"
    gl_top = min(int(np.where(g.any(1))[0].min()) for g in guantes.values())

    # ---- brazos: banda entre la línea exterior y la interior
    ys_b = range(int(gl_top - 270), int(gl_top - 12), 3)
    brazos = {}
    for lado in ("I", "D"):
        b = banda_miembro(cb, sil, ys_b, izquierda=(lado == "I"))
        P = np.stack([b[:, 1], b[:, 0]], 1)
        p0, p1, p2 = ajustar_bezier(P)
        # prolonga el hombro bajo la cabeza (oculto) siguiendo la tangente inicial
        tan0 = (p0 - p1) / np.linalg.norm(p0 - p1)
        p0x = p0 + tan0 * 70
        # la muñeca entra en el puño del guante
        tan2 = (p2 - p1) / np.linalg.norm(p2 - p1)
        p2x = p2 + tan2 * 26
        w_out = float(np.median(b[:, 2]))
        P0, P1, P2 = to_u(cal, [p0x, p1, p2x])
        brazos[lado] = {"P0": r1([P0])[0], "P1": r1([P1])[0], "P2": r1([P2])[0],
                        "grosor": round(w_out / cal["s"] - 2 * 7, 1)}
    T["brazos"] = brazos

    # ---- guantes en coordenadas locales: origen en la muñeca, +x por la tangente final
    T["guantes"] = {}
    for lado, gm in guantes.items():
        br = brazos[lado]
        P1, P2 = np.array(br["P1"]), np.array(br["P2"])
        ang = np.arctan2(P2[1] - P1[1], P2[0] - P1[0])
        rot = np.array([[np.cos(-ang), -np.sin(-ang)], [np.sin(-ang), np.cos(-ang)]])
        loc = lambda pts: r1((to_u(cal, pts) - P2) @ rot.T)  # noqa: E731
        forma = cv2.dilate(gm.astype(np.uint8), disk(HALF_INK)).astype(bool)
        lineas = []
        for m, st, cen in componentes(ink & cv2.erode(gm.astype(np.uint8), disk(8)).astype(bool), 40):
            lineas += [loc(c) for c in contornos(m, min_area=30, eps=0.7, suav=1.2)]
        T["guantes"][lado] = {"forma": [loc(c) for c in contornos(forma)], "lineas": lineas,
                              "angulo_neutro": round(float(np.degrees(ang)), 2)}

    # ---- piernas (la izquierda se mide, la derecha es su espejo: a la derecha está la cola)
    pies = {}
    for m, st, cen in comps:
        x, y, w, h, a = st
        if a > 20000 and y > 0.85 * H and np.median(cb[m]) < 130:
            pies["I" if cen[0] < xc else "D"] = fill_holes(m)
    assert set(pies) == {"I", "D"}, "no encuentro los dos pies"
    pie_top = min(int(np.where(p.any(1))[0].min()) for p in pies.values())
    gl_bot = int(np.where(guantes["I"].any(1))[0].max())
    ys_p = range(max(int(pie_top - 200), gl_bot + 15), int(pie_top - 15), 3)
    bp = banda_miembro(cb, sil, ys_p, izquierda=True)
    P = np.stack([bp[:, 1], bp[:, 0]], 1)
    p0, p1, p2 = ajustar_bezier(P)
    tan0 = (p0 - p1) / np.linalg.norm(p0 - p1)
    p0x = p0 + tan0 * 60
    p2x = p2 + (p2 - p1) / np.linalg.norm(p2 - p1) * 30
    P0, P1, P2 = to_u(cal, [p0x, p1, p2x])
    grosor_p = round(float(np.median(bp[:, 2])) / cal["s"] - 14, 1)
    T["pierna"] = {"P0": r1([P0])[0], "P1": r1([P1])[0], "P2": r1([P2])[0], "grosor": grosor_p}
    T["pies"] = {}
    for lado, pm in pies.items():
        tob = np.array(P2) * ([1, 1] if lado == "I" else [-1, 1])
        forma = cv2.dilate(pm.astype(np.uint8), disk(HALF_INK)).astype(bool)
        lineas = []
        for m, st, cen in componentes(ink & cv2.erode(pm.astype(np.uint8), disk(6)).astype(bool), 40):
            lineas += [r1(to_u(cal, c) - tob) for c in contornos(m, min_area=30, eps=0.7, suav=1.2)]
        T["pies"][lado] = {"forma": [r1(to_u(cal, c) - tob) for c in contornos(forma)], "lineas": lineas}

    # ---- cola: las franjas que asoman a la derecha y entre las piernas
    cola_c = []
    for m, st, cen in comps:
        x, y, w, h, a = st
        if cen[0] > xc - 60 and cen[1] > 0.66 * H and cen[1] < 0.9 * H and a > 2000:
            if any((m & g).any() for g in guantes.values()) or any((m & p).any() for p in pies.values()):
                continue
            if np.median(cb[m]) > 240:   # hueco de papel encerrado
                continue
            cola_c.append(m)
    cola = np.zeros((H, W), bool)
    for m in cola_c:
        cola |= m
    cola_full = cv2.morphologyEx(cola.astype(np.uint8), cv2.MORPH_CLOSE, disk(60)).astype(bool)
    cola_full = fill_holes(cv2.dilate(cola_full.astype(np.uint8), disk(HALF_INK + 2)))
    bandas = [m for m in cola_c if np.median(cb[m]) < 125]
    cola_base_px = (xc - 40, float(np.where(cola_full.any(1))[0].min()) + 160)
    base_u = to_u(cal, [cola_base_px])[0]
    T["cola"] = {"base": r1([base_u])[0], "forma": poly_u(cal, cola_full),
                 "bandas": [p for m in bandas for p in poly_u(cal, cv2.dilate(m.astype(np.uint8), disk(3)).astype(bool))]}

    # ---- cabeza: la silueta sobre la barbilla
    menton = 655.0 / (F * 0 + 1)  # px ×4 medidos sobre la hoja (barbilla en los lados)
    yb = np.where(np.abs(xx - xc) < 210, menton + 28 * (1 - ((xx - xc) / 210.0) ** 2), menton)
    cabeza = sil & (yy < yb)
    cabeza = mayor(cv2.morphologyEx(cabeza.astype(np.uint8), cv2.MORPH_OPEN, disk(4)).astype(bool))
    # orejas: más allá de la recta de su base (medida en la hoja); la recta se espeja en xc
    bases = {"I": ((325.0, 250.0), (455.0, 150.0))}
    bases["D"] = ((2 * xc - 455.0, 150.0), (2 * xc - 325.0, 250.0))
    T["orejas"] = {}
    cortes = np.zeros((H, W), bool)
    craneo = cabeza.copy()
    for lado, (a, b) in bases.items():
        s = lado_de_recta((H, W), a, b)
        # la oreja es el lado PEQUEÑO de la recta (el otro es el cráneo entero)
        sup = (yy < 330) & (np.abs(xx - (a[0] + b[0]) / 2) < 220)
        lado_pos = (cabeza & sup & (s > 0)).sum() < (cabeza & sup & (s < 0)).sum()
        oreja = cabeza & sup & ((s > 0) if lado_pos else (s < 0))
        # se mete 30 px bajo el cráneo (capa de atrás) para no dejar costura al girar
        oreja_ext = cabeza & cv2.dilate(oreja.astype(np.uint8), disk(30)).astype(bool)
        craneo &= ~oreja
        corte = cv2.dilate(oreja.astype(np.uint8), disk(5)).astype(bool) & craneo
        cortes |= corte
        interior = oreja & (cb > 175) & ~ink
        interior = mayor(cv2.morphologyEx(interior.astype(np.uint8), cv2.MORPH_OPEN, disk(3)).astype(bool))
        piv = to_u(cal, [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)])[0]
        T["orejas"][lado] = {"forma": poly_u(cal, cv2.erode(oreja_ext.astype(np.uint8), disk(HALF_INK)).astype(bool)),
                             "interior": poly_u(cal, interior), "pivote": r1([piv])[0]}
    # mechón de la coronilla
    mech = craneo & (yy < 120) & (np.abs(xx - xc) < 115)
    mech_ext = craneo & (yy < 150) & (np.abs(xx - xc) < 115)
    craneo &= ~mech
    cortes |= cv2.dilate(mech.astype(np.uint8), disk(5)).astype(bool) & craneo
    T["mechon"] = {"forma": poly_u(cal, cv2.erode(mech_ext.astype(np.uint8), disk(HALF_INK)).astype(bool)),
                   "pivote": r1(to_u(cal, [(xc, 125)]))[0]}
    # la barbilla es un corte artificial (en la hoja la cara se funde con el pecho): sin línea
    cortes |= (yy > yb - 16) & (np.abs(xx - xc) < 215)
    cr = cv2.erode(craneo.astype(np.uint8), disk(HALF_INK)).astype(bool)
    T["craneo"] = {"forma": poly_u(cal, cr), "trazo": trazo_sin_cortes(cal, cr, cortes)}
    chin_u = to_u(cal, [(xc, menton + 28)])[0]
    T["menton"] = r1([chin_u])[0]

    # ---- cara: antifaz, ojos, pupilas, cejas, nariz, boca, crema
    head_in = cv2.erode(cabeza.astype(np.uint8), disk(14)).astype(bool)
    oscuros = [(m, st, cen) for m, st, cen in comps if (m & head_in).sum() > 0.9 * m.sum()
               and st[4] > 5000 and 70 < np.median(cb[m]) < 125]
    lobulos = sorted(oscuros, key=lambda t: -t[1][4])[:2]
    T["antifaz"] = {}
    T["ojos"] = {}
    for m, st, cen in lobulos:
        lado = "I" if cen[0] < xc else "D"
        lob = fill_holes(m)
        T["antifaz"][lado] = poly_u(cal, cv2.dilate(lob.astype(np.uint8), disk(HALF_INK - 1)).astype(bool))
        blanco = [(mm, s2, c2) for mm, s2, c2 in comps if (mm & lob).sum() > 0.9 * mm.sum() and np.median(cb[mm]) > 235]
        mm = fill_holes(max(blanco, key=lambda t: t[1][4])[0])
        x, y, w, h = cv2.boundingRect(mm.astype(np.uint8))
        pup = mayor(ink & cv2.erode(mm.astype(np.uint8), disk(6)).astype(bool))
        px_, py_, pw, ph = cv2.boundingRect(pup.astype(np.uint8))
        c_ojo = to_u(cal, [(x + w / 2, y + h / 2)])[0]
        c_pup = to_u(cal, [(px_ + pw / 2, py_ + ph / 2)])[0]
        T["ojos"][lado] = {"forma": poly_u(cal, cv2.dilate(mm.astype(np.uint8), disk(3)).astype(bool)),
                           "centro": r1([c_ojo])[0], "rx": round(w / 2 / cal["s"], 1), "ry": round(h / 2 / cal["s"], 1),
                           "pupila": {"centro": r1([c_pup])[0], "rx": round(pw / 2 / cal["s"], 1), "ry": round(ph / 2 / cal["s"], 1)}}
    # crema de la cara (sin los blancos de los ojos)
    blancos = np.zeros((H, W), bool)
    for m, st, cen in lobulos:
        blancos |= fill_holes(m)
    lob_cy = float(np.mean([cen[1] for _, _, cen in lobulos]))
    crema = cabeza & (cb > 195) & ~blancos & ~ink & (yy > lob_cy)
    crema = cv2.morphologyEx(crema.astype(np.uint8), cv2.MORPH_OPEN, disk(4)).astype(bool)
    crema = cv2.morphologyEx(crema.astype(np.uint8), cv2.MORPH_CLOSE, disk(9)).astype(bool)
    crema_c = [m for m, st, cen in componentes(crema, 2500)]
    T["crema_cara"] = [p for m in crema_c for p in poly_u(cal, fill_holes(m), suav=3)]
    # tintas interiores de la cabeza: cejas, nariz, boca, detalles de pelo
    tintas = componentes(ink & head_in & ~blancos, 120)
    ojo_y = np.mean([to_px(cal, [T["ojos"][l]["centro"]])[0][1] for l in "ID"])
    nariz = boca = None
    cejas, bocas, detalles = {}, [], []
    for m, st, cen in tintas:
        x, y, w, h, a = st
        if abs(cen[0] - xc) < 60 and ojo_y + 60 < cen[1] < ojo_y + 190 and a > 1500 and nariz is None:
            nariz = fill_holes(m)
        elif cen[1] < ojo_y - 60 and w > 90 and a > 900:
            lado = "I" if cen[0] < xc else "D"
            if lado not in cejas or a > cejas[lado][1]:
                cejas[lado] = (m, a, cen, w)
        elif cen[1] > ojo_y + 120 and abs(cen[0] - xc) < 260:
            bocas.append(m)
        else:
            detalles.append(m)
    assert nariz is not None, "no encuentro la nariz"
    nariz, resto = separar_nariz(nariz)
    if resto.sum() > 200:
        bocas += [mm for mm, _, _ in componentes(resto, 60)]
    brillo = [mm for mm, st, cen in comps if (mm & nariz).sum() > 0.9 * mm.sum() and np.median(cb[mm]) > 200]
    T["nariz"] = {"forma": poly_u(cal, nariz, suav=1.5), "brillo": [p for m in brillo for p in poly_u(cal, m, suav=1.5)]}
    bocas = [m for m in bocas if not (m & nariz).any()]
    T["boca_sonrisa"] = [p for m in bocas for p in poly_u(cal, m, eps=0.6, suav=1.2)]
    T["cejas"] = {}
    for lado, (m, a, cen, w) in cejas.items():
        T["cejas"][lado] = {"forma": poly_u(cal, m, eps=0.6, suav=1.2), "centro": r1(to_u(cal, [cen]))[0],
                            "largo": round(w / cal["s"], 1)}
    T["detalles_cabeza"] = [p for m in detalles for p in poly_u(cal, m, eps=0.6, suav=1.2)]

    # ---- torso y panza
    tz = sil.copy()
    tz[yy < menton - 40] = False
    tz[yy > uy(0) - 0] = tz[yy > uy(0)]
    for g in guantes.values():
        tz &= ~cv2.dilate(g.astype(np.uint8), disk(10)).astype(bool)
    tz &= ~cv2.dilate(cola.astype(np.uint8), disk(8)).astype(bool)
    for m, st, cen in comps:  # huecos de papel encerrados (entre brazo, torso y cola)
        if st[4] > 3000 and np.median(cb[m]) > 245 and not any((m & g).any() for g in guantes.values())                 and cen[1] > menton + 60:
            tz &= ~cv2.dilate(m.astype(np.uint8), disk(HALF_INK + 2)).astype(bool)
    for lado, br in brazos.items():
        p0, p1, p2 = (to_px(cal, [br[k]])[0] for k in ("P0", "P1", "P2"))
        half = (br["grosor"] / 2 + 7) * cal["s"]
        arm = np.zeros((H, W), np.uint8)
        pts = np.array([bez(p0, p1, p2, t) for t in np.linspace(0, 1, 60)], np.int32)
        cv2.polylines(arm, [pts], False, 1, int(2 * half - 8))
        tz &= ~arm.astype(bool)
    pp = {k: to_px(cal, [T["pierna"][k]])[0] for k in ("P0", "P1", "P2")}
    hip_y = pp["P0"][1] + 40
    entrepierna = float(np.median([np.where(sil[:, int(xc + dx)])[0].max() for dx in (-10, 0, 10)]))
    tz[yy > hip_y + 30] = False
    tz = mayor(cv2.morphologyEx(tz.astype(np.uint8), cv2.MORPH_OPEN, disk(6)).astype(bool))
    torso = cv2.erode(tz.astype(np.uint8), disk(HALF_INK)).astype(bool)
    T["torso"] = {"forma": poly_u(cal, torso, suav=3)}
    panza = tz & (cb > 195) & ~ink & (yy > menton + 30)
    panza = mayor(cv2.morphologyEx(panza.astype(np.uint8), cv2.MORPH_OPEN, disk(5)).astype(bool))
    panza = fill_holes(cv2.dilate(panza.astype(np.uint8), disk(HALF_INK)))
    # la panza no tiene línea arriba: su crema continúa la de la cara
    T["panza"] = {"forma": poly_u(cal, panza, suav=3),
                  "trazo": trazo_sin_cortes(cal, panza, yy < menton + 75, suav=3)}
    tinta_torso = componentes(ink & cv2.erode(panza.astype(np.uint8), disk(10)).astype(bool), 80)
    T["detalles_torso"] = [p for m, st, cen in tinta_torso for p in poly_u(cal, m, eps=0.6, suav=1.2)]
    T["torso_base_y"] = round(float(to_u(cal, [(xc, hip_y + 30)])[0][1]), 1)

    # ---- silueta de referencia (para el solape) y marcas
    T["_ref"] = {"area_px": int(sil.sum())}
    if debug:
        EVID.mkdir(parents=True, exist_ok=True)
        vis = cv2.cvtColor(cb, cv2.COLOR_GRAY2BGR)
        rng = np.random.default_rng(3)
        for m in [cabeza, tz, panza, cola_full, *guantes.values(), *pies.values(), crema]:
            col = rng.integers(40, 255, 3)
            vis[m] = (0.55 * vis[m] + 0.45 * col).astype(np.uint8)
        cv2.imwrite(str(EVID / "_traza_debug.png"), cv2.resize(vis, None, fx=0.5, fy=0.5))
    return T



# ------------------------------------------------------------------ expresiones
EXPR_HOJA = ["sonrisa", "asombro", "triste", "decidido", "guino", "risa"]  # fila inferior, izq→der
CERRADOS = {"guino": "D", "risa": "ID"}  # ojos dibujados cerrados en la hoja madre


def _lobulos(cb, sil):
    """Los dos lóbulos del antifaz de una cabeza (px), de izquierda a derecha."""
    ink = cb < INK
    H = cb.shape[0]
    osc = sorted([(m, st, cen) for m, st, cen in componentes(sil & ~ink, 200)
                  if 70 < np.median(cb[m]) < 125 and cen[1] < 0.62 * H], key=lambda t: -t[1][4])[:2]
    osc = sorted(osc, key=lambda t: t[2][0])
    return [fill_holes(m) for m, _, _ in osc], [np.array(cen) for _, _, cen in osc]


def _ancho_en(sil, y):
    xs = np.where(sil[int(y)])[0]
    return float(xs.min()), float(xs.max())


def trazar_expresiones(T: dict) -> dict:
    g = hoja_gris()
    banda = g[530:730]
    sil_b = silueta(banda)
    heads = sorted([st for m, st, cen in componentes(sil_b, 8000)], key=lambda st: st[0])
    assert len(heads) == 6, f"esperaba 6 cabezas en la fila inferior, hay {len(heads)}"
    # cabeza frontal (u): altura de los lóbulos y ancho del cráneo a esa altura
    lob_y_u = float(np.mean([np.vstack(T["antifaz"][l]).mean(0)[1] for l in "ID"]))
    cr = np.vstack([np.array(p) for p in T["craneo"]["forma"]])
    fila = cr[np.abs(cr[:, 1] - lob_y_u) < 25]
    f_x0, f_x1 = float(fila[:, 0].min()), float(fila[:, 0].max())
    nb = np.vstack([np.array(p) for p in T["nariz"]["forma"]])
    out = {}
    for nombre, st in zip(EXPR_HOJA, heads):
        x, y, w, h, _ = st
        x0, y0 = max(0, x - 6), 530 + max(0, y - 6)
        crop = g[y0: 530 + y + h + 6, x0: x + w + 6]
        cb = cv2.resize(crop, None, fx=F, fy=F, interpolation=cv2.INTER_CUBIC)
        sil = silueta(cb)
        ink = cb < INK
        lob, lc = _lobulos(cb, sil)
        ly = float(np.mean([c[1] for c in lc]))
        e_x0, e_x1 = _ancho_en(sil, ly)
        k = (f_x1 - f_x0) / (e_x1 - e_x0)
        cx_e, cx_f = (e_x0 + e_x1) / 2, (f_x0 + f_x1) / 2

        def to_u2(pts, k=k, cx_e=cx_e, ly=ly):
            pts = np.asarray(pts, float)
            return np.stack([cx_f + (pts[:, 0] - cx_e) * k, lob_y_u - (pts[:, 1] - ly) * k], 1)

        def to_px2(pts, k=k, cx_e=cx_e, ly=ly):
            pts = np.asarray(pts, float)
            return np.stack([cx_e + (pts[:, 0] - cx_f) / k, ly - (pts[:, 1] - lob_y_u) / k], 1)

        def polys(m, **kw):
            return [r1(to_u2(c)) for c in contornos(m, **kw)]
        # la nariz es la del frente: se borra de esta cara por su posición
        q = to_px2([[nb[:, 0].min() - 6, nb[:, 1].max() + 6], [nb[:, 0].max() + 6, nb[:, 1].min() - 4]])
        nm = np.zeros_like(ink)
        nm[int(q[0][1]):int(q[1][1]), int(q[0][0]):int(q[1][0])] = True
        ncen = ((q[0][0] + q[1][0]) / 2, (q[0][1] + q[1][1]) / 2)
        nst = (0, 0, 0, q[1][1] - q[0][1])
        # si la nariz es una mancha suelta, se usa la mancha (más exacta que la caja)
        for m, s2, cen in componentes(ink, 400):
            if m[int(ncen[1]), int(ncen[0])] or (m & nm).sum() > 0.5 * m.sum():
                solo, _ = separar_nariz(m)
                if solo.sum() > 800:
                    nm = cv2.dilate(solo.astype(np.uint8), disk(3)).astype(bool)
                    ys_n = np.where(solo.any(1))[0]
                    nst = (0, 0, 0, ys_n.max() - q[0][1])
                break
        ink = ink & ~nm
        interior = cv2.erode(sil.astype(np.uint8), disk(14)).astype(bool)
        nariz_y = ncen[1] + nst[3] / 2
        lb = np.zeros_like(ink)
        for l in lob:
            lb |= l
        ys_l, xs_l = np.where(lb)
        lx0, lx1, ly0, ly1 = xs_l.min(), xs_l.max(), ys_l.min(), ys_l.max()
        lh, lw = ly1 - ly0, lx1 - lx0
        yy2, xx2 = np.mgrid[0:ink.shape[0], 0:ink.shape[1]]
        cerca_lob = cv2.dilate(lb.astype(np.uint8), disk(9)).astype(bool)
        zona_boca = (yy2 > nariz_y + 4) & (xx2 > lx0 + 0.08 * lw) & (xx2 < lx1 - 0.08 * lw)
        boca_px = ink & interior & zona_boca & ~cerca_lob
        boca = componentes(boca_px, 150)
        if boca:  # fuera los restos sueltos (pelo de la mejilla): solo lo que pesa
            amax = max(s2[4] for _, s2, _ in boca)
            boca = [m for m, s2, cen in boca if s2[4] >= 0.2 * amax]
        pecas = [m for m, s2, cen in componentes(ink & interior & zona_boca & ~cerca_lob, 30) if s2[4] < 150]
        zona_ceja = (yy2 > ly0 - 0.75 * lh) & (yy2 < ly0 + 0.25 * lh) & (xx2 > lx0 - 0.05 * lw) & (xx2 < lx1 + 0.05 * lw)
        ceja_px = ink & interior & zona_ceja & ~cerca_lob
        cejas = {}
        for m, s2, cen in componentes(ceja_px, 300):
            if s2[2] < 0.12 * lw:
                continue
            lado = "I" if cen[0] < (lx0 + lx1) / 2 else "D"
            if lado not in cejas or s2[4] > cejas[lado][1][4]:
                cejas[lado] = (m, s2)
        cerrado = {}
        for l, lado in zip(lob, "ID"):
            if lado in CERRADOS.get(nombre, ""):
                arco = ink & cv2.erode(l.astype(np.uint8), disk(2)).astype(bool)
                cerrado[lado] = [p for m, _, _ in componentes(arco, 150) for p in polys(m, suav=1.2, eps=0.7)]
        # zonas cerradas de la boca (dientes, lengua, interior)
        boca_rell = []
        if boca:
            u = np.zeros_like(ink)
            for m in boca:
                u |= m
            hull = fill_holes(cv2.dilate(u.astype(np.uint8), disk(2)))
            for m, s2, cen in componentes(hull & ~ink, 80):
                med = float(np.median(cb[m]))
                tono = "T_WHITE" if med > 225 else ("T_CREAM" if med > 195 else ("T_FUR" if med > 120 else "T_MASK"))
                if (m & ~hull).any():
                    continue
                boca_rell.append({"tono": tono, "forma": polys(m, suav=1.2)})
        ce = {}
        for lado, (m, s2) in cejas.items():
            ys, xs = np.where(m)
            iz, de = np.argmin(xs), np.argmax(xs)
            pa = to_u2([[xs[iz], ys[iz]], [xs[de], ys[de]]])
            inner, outer = (pa[1], pa[0]) if lado == "I" else (pa[0], pa[1])
            ce[lado] = {"interior": r1([inner])[0], "exterior": r1([outer])[0], "forma": polys(m, suav=1.2, eps=0.6)}
        out[nombre] = {"boca": [p for m in boca for p in polys(m, suav=1.2, eps=0.6)], "boca_relleno": boca_rell,
                       "cejas": ce, "cerrado": cerrado,
                       "pecas": [p for m in pecas for p in polys(m, suav=1.0, eps=0.6)], "escala": round(float(k), 4)}
    return out

def escribir(T: dict) -> None:
    body = json.dumps(T, separators=(",", ":"))
    OUT.write_text("// GENERADO por kx_trazo.py a partir de assets/kx_cast/tadeo/_hojas/model_sheet.png.\n"
                   "// No editar a mano: se regenera trazando la hoja madre. Unidades del rig (y hacia arriba).\n"
                   f"export const TRAZA = {body};\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    T = trazar(a.debug)
    T["expresiones"] = trazar_expresiones(T)
    escribir(T)
    print(f"traza.js: {OUT.stat().st_size // 1024} KB · px/u {T['escala']['px_por_u']:.3f} · "
          f"brazo I {T['brazos']['I']} · pierna {T['pierna']} · mentón {T['menton']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
