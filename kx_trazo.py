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


# ------------------------------------------------------------------ iteración 2 (R1-R3)
# Tonos medidos en la madre (fracción de INK sobre PAPER, I2-2 punto 5). Deben
# coincidir con TADEO_TONE de tokens.js (lo vigila tests/test_tadeo_parecido.py).
TONOS = {"T_WHITE": 0.0, "T_CREAM": 0.09, "T_MEDIO": 0.25, "T_FUR": 0.39, "T_FUR_SOMBRA": 0.47, "T_MASK": 0.64}
TN = list(TONOS)
TV = np.array(list(TONOS.values()))
RECTA = 1 - 17 / 241.1          # luminancia de INK sobre la de PAPER: tone(f) ≈ papel·(1 − RECTA·f)
SOMBRA_AREA_MIN = 1500          # px² de la rejilla ×4 (I2-2 punto 6)
SOMBRAS_MAX = 14
SEG_MAX = 6.0                   # u: densificado antes de deformar (R3)


def fraccion_tono(cb, sil, ink, sigma) -> np.ndarray:
    """Fracción de INK de cada píxel con la tinta rellenada por sus vecinos y suavizada a σ."""
    papel = float(np.median(cb[~sil]))
    m = (sil & ~ink).astype(float)
    q = cv2.GaussianBlur(cb.astype(float) * m, (0, 0), sigma) / np.maximum(cv2.GaussianBlur(m, (0, 0), sigma), 1e-6)
    return (1 - q / papel) / RECTA


def cuantiza(frac) -> np.ndarray:
    return np.argmin(np.abs(np.asarray(frac)[..., None] - TV), -1)


def chaikin(p, n=2):
    for _ in range(n):
        q = np.roll(p, -1, 0)
        p = np.stack([0.75 * p + 0.25 * q, 0.25 * p + 0.75 * q], 1).reshape(-1, 2)
    return p


def suave_mask(m, shape, eps=1.5, agujeros=True):
    """Máscara → contorno ε 1,5 + 2 pasadas de Chaikin → máscara (formas planas de
    borde limpio). Los agujeros (p. ej. la panza dentro de su banda) se respetan."""
    if agujeros:
        llena = fill_holes(m)
        hueco = llena & ~m
        out = suave_mask(llena, shape, eps, False)
        if hueco.sum() > 200:
            out &= ~suave_mask(cv2.morphologyEx(hueco.astype(np.uint8), cv2.MORPH_OPEN, disk(2)).astype(bool), shape, eps, False)
        return out
    out = np.zeros(shape, np.uint8)
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs:
        a = cv2.approxPolyDP(c.astype(np.float32), eps, True)[:, 0, :]
        if len(a) >= 3:
            cv2.fillPoly(out, [np.round(chaikin(a.astype(float)) * 8).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=3)
    return out.astype(bool)


def densifica(p, seg=SEG_MAX):
    p = np.asarray(p, float)
    out = []
    for a, b in zip(p, np.roll(p, -1, 0)):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / seg)))
        out += [a + (b - a) * k / n for k in range(n)]
    return np.array(out)


def poly_ccomp(cal, m, eps=0.6, suav=1.0, dens=False, min_area=12):
    """Contornos CON agujeros (para fill-rule evenodd), en u."""
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        if abs(cv2.contourArea(c)) < min_area:
            continue
        p = c[:, 0, :].astype(float)
        if suav and len(p) > 12:
            k = int(3 * suav) | 1
            pad = np.concatenate([p[-k:], p, p[:k]])
            w = np.exp(-0.5 * (np.arange(-k, k + 1) / suav) ** 2)
            w /= w.sum()
            p = np.stack([np.convolve(pad[:, i], w, "same")[k:-k] for i in range(2)], 1)
        a = cv2.approxPolyDP(p.astype(np.float32).reshape(-1, 1, 2), eps, True)[:, 0, :]
        if len(a) < 3:
            continue
        u = to_u(cal, a)
        out.append(r1(densifica(u) if dens else u))
    return out


ISO_TINTA = 66.0


def poly_iso(cal, cb, zona, dens=False, eps=0.5, min_area=6, excluir=None):
    """Tinta R1: isolínea subpíxel de luminancia = 60 dentro de `zona` (con
    agujeros, para evenodd). Así el área de tinta es la de la madre, no la de
    un contorno de píxeles que pierde medio píxel por lado."""
    from skimage.measure import find_contours
    if not zona.any():
        return []
    ys, xs = np.where(zona)
    y0, y1, x0, x1 = max(ys.min() - 3, 0), ys.max() + 4, max(xs.min() - 3, 0), xs.max() + 4
    # la zona se ensancha 3 px (lo mismo que el relleno): en un corte, el relleno de
    # la pieza de encima nunca tapa un tramo de línea que su propia tinta no repinte
    dentro = cv2.dilate(zona.astype(np.uint8), disk(3)).astype(bool)
    if excluir is not None:      # tinta de otra pieza que se mueve aparte (cejas, boca…): ni un píxel
        dentro &= ~excluir
    f = np.where(dentro, cb.astype(float), 255.0)[y0:y1, x0:x1]
    f = np.pad(f, 1, constant_values=255.0)
    out = []
    # nivel de la isolínea: 60 es la tinta medida; el polígono se dibuja un poco
    # más ancho (ISO_TINTA) para que, con el antialias del render, el umbral 60
    # vuelva a caer donde cae en la madre (calibrado con el área de tinta)
    for c in find_contours(f, ISO_TINTA):
        p = np.stack([c[:, 1] + x0 - 1, c[:, 0] + y0 - 1], 1)
        if len(p) < 4 or abs(cv2.contourArea(p.astype(np.float32))) < min_area:
            continue
        a = cv2.approxPolyDP(p.astype(np.float32).reshape(-1, 1, 2), eps, True)[:, 0, :]
        if len(a) >= 3:
            u = to_u(cal, a)
            out.append(r1(densifica(u) if dens else u))
    return out


def poly_ext(cal, m, dens=False, eps=0.8, suav=1.0, min_area=60):
    out = []
    for c in contornos(m, min_area=min_area, eps=eps, suav=suav):
        u = to_u(cal, c)
        out.append(r1(densifica(u) if dens else u))
    return sorted(out, key=lambda p: -abs(cv2.contourArea(np.array(p, np.float32))))


class Espina:
    """Espina en px muestreada por longitud de arco; (σ, d) de cualquier punto
    (σ en px desde el inicio, prolongada recta por los extremos)."""

    def __init__(self, pts):
        self.p = np.asarray(pts, float)
        seg = np.linalg.norm(np.diff(self.p, axis=0), axis=1)
        self.cum = np.r_[0, np.cumsum(seg)]
        t = np.gradient(self.p, axis=0)
        self.t = t / np.linalg.norm(t, axis=1)[:, None]
        from scipy.spatial import cKDTree
        self.kd = cKDTree(self.p)

    @classmethod
    def bezier(cls, P, n=400):
        P = [np.asarray(q, float) for q in P]
        t = np.linspace(0, 1, n)[:, None]
        if len(P) == 3:
            pts = (1 - t) ** 2 * P[0] + 2 * (1 - t) * t * P[1] + t ** 2 * P[2]
        else:
            pts = (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]
        return cls(pts)

    def sd(self, X):
        X = np.asarray(X, float)
        _, i = self.kd.query(X)
        r = X - self.p[i]
        tn = self.t[i]
        along = (r * tn).sum(1)
        d = tn[:, 0] * r[:, 1] - tn[:, 1] * r[:, 0]
        return self.cum[i] + along * ((i == 0) | (i == len(self.p) - 1)), d

    def punto(self, sig, d):
        sig = np.asarray(sig, float)
        L = self.cum[-1]
        sc = np.clip(sig, 0, L)
        x = np.interp(sc, self.cum, self.p[:, 0])
        y = np.interp(sc, self.cum, self.p[:, 1])
        tx = np.interp(sc, self.cum, self.t[:, 0])
        ty = np.interp(sc, self.cum, self.t[:, 1])
        ex = sig - sc
        x, y = x + tx * ex, y + ty * ex
        return np.stack([x - ty * d, y + tx * d], 1)


def banda_sd(esp, shape, mask):
    ys, xs = np.where(mask)
    s, d = esp.sd(np.stack([xs, ys], 1))
    S = np.full(shape, np.nan)
    D = np.full(shape, np.nan)
    S[ys, xs], D[ys, xs] = s, d
    return S, D


def extension(esp, region, ink, sig0, largo, shape, sentido=-1):
    """Prolonga el relleno y los tramos de tinta del perfil en σ0 un `largo`
    (px) por la tangente (R3, puntos 1 y 3): oculto bajo la pieza de encima."""
    ys, xs = np.where(region)
    s, d = esp.sd(np.stack([xs, ys], 1))
    sel = (s > sig0 + 3) & (s < sig0 + 18)
    if sel.sum() < 20:
        return np.zeros(shape, bool), np.zeros(shape, bool)
    dd, yy_, xx_ = d[sel], ys[sel], xs[sel]
    d0, d1 = np.percentile(dd, 1), np.percentile(dd, 99)
    bins = np.arange(np.floor(d0), np.ceil(d1) + 1)
    es_t = ink[yy_, xx_]
    tramos, en = [], False
    for b in bins:
        k = (dd >= b) & (dd < b + 1)
        t = k.sum() > 0 and es_t[k].mean() > 0.5
        if t and not en:
            ini = b
        if not t and en:
            tramos.append((ini, b))
        en = t
    if en:
        tramos.append((ini, bins[-1] + 1))
    sig = np.linspace(sig0 + 10, sig0 + sentido * largo, 24)

    def poly(a, b):
        return np.round(np.vstack([esp.punto(sig, np.full_like(sig, a)), esp.punto(sig[::-1], np.full_like(sig, b))]) * 8).astype(np.int32)
    fill = np.zeros(shape, np.uint8)
    cv2.fillPoly(fill, [poly(d0, d1)], 1, shift=3)
    tin = np.zeros(shape, np.uint8)
    for a, b in tramos:
        if b - a >= 3:
            cv2.fillPoly(tin, [poly(a, b)], 1, shift=3)
    return fill.astype(bool), tin.astype(bool)


def camino_esqueleto(m, inicio):
    """Camino más largo del esqueleto de `m` desde el extremo más cercano a `inicio` (px)."""
    from collections import deque

    from skimage.morphology import skeletonize
    sk = skeletonize(m)
    pts = set(zip(*np.where(sk)))
    vec = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
    deg = {p: sum((p[0] + a, p[1] + b) in pts for a, b in vec) for p in pts}
    ext = [p for p, g in deg.items() if g == 1] or list(pts)
    s0 = min(ext, key=lambda p: (p[1] - inicio[0]) ** 2 + (p[0] - inicio[1]) ** 2)

    def bfs(s):
        par, dist, q = {s: None}, {s: 0}, deque([s])
        while q:
            p = q.popleft()
            for a, b in vec:
                n = (p[0] + a, p[1] + b)
                if n in pts and n not in par:
                    par[n], dist[n] = p, dist[p] + 1
                    q.append(n)
        return par, dist
    par, dist = bfs(s0)
    fin = max(dist, key=dist.get)
    out = []
    while fin is not None:
        out.append((fin[1], fin[0]))
        fin = par[fin]
    return np.array(out[::-1], float)


def ajustar_cubica(P):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = (d / d[-1])[:, None]
    p0, p3 = P[0], P[-1]
    b1, b2 = 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2
    rhs = P - (1 - t) ** 3 * p0 - t ** 3 * p3
    A = np.hstack([b1, b2])
    sol = np.linalg.lstsq(A, rhs, rcond=None)[0]
    return p0, sol[0], sol[1], p3


def piezas_r1(cb, sil, cal, ink_t, comps, guantes, pies, cola_c, cola_full, cabeza, orejas, orejas_ext,
              mech, mech_ext, lobulos, nariz, brillo, bocas, cejas, T, debug=False) -> dict:
    """Piezas de la iteración 2: cada una con su relleno (tono base medido), sus
    sombras planas y la TINTA de la madre en su zona (R1), sin trazo en los
    cortes (R2). Brazos, piernas y cola se guardan en u del neutro: el render
    las deforma por la espina (R3)."""
    H, W = cb.shape
    s = cal["s"]
    yy, xx = np.mgrid[0:H, 0:W]
    ink = cb < 60                                # la misma tinta que mide kx_parecido
    D = lambda r: disk(int(r))  # noqa: E731
    dil = lambda m, r: cv2.dilate(m.astype(np.uint8), D(r)).astype(bool)  # noqa: E731
    ero = lambda m, r: cv2.erode(m.astype(np.uint8), D(r)).astype(bool)  # noqa: E731
    frac = fraccion_tono(cb, sil, ink, 10)
    Q = cuantiza(frac)
    out = {"tonos": TONOS}

    # ---- huecos de papel encerrados (no son de nadie)
    huecos = np.zeros((H, W), bool)
    for m, st, cen in componentes(sil & ~ink, 300):
        if st[4] > 3000 and np.median(cb[m]) > 245 and not any((m & g).any() for g in guantes.values()):
            huecos |= m
    libre = sil & ~ink & ~huecos
    lab = np.zeros((H, W), np.int16)
    PRIO = ["cola", "piernaI", "piernaD", "pieI", "pieD", "torso", "brazoI", "brazoD",
            "orejaI", "orejaD", "mechon", "craneo", "guanteI", "guanteD"]
    ID = {k: i + 1 for i, k in enumerate(PRIO)}

    # guantes: palma + puño enrollado (el blanco pegado encima de la palma)
    puno = {}
    for lado, g in guantes.items():
        cand = [m for m, st, cen in componentes(libre & ~g, 800)
                if np.median(cb[m]) > 225 and (m & dil(g, 22)).any() and cen[1] < np.where(g)[0].mean()]
        p = np.zeros((H, W), bool)
        for m in cand:
            p |= m
        puno[lado] = p
        # palma, puño y las yemas que las rayas de los dedos separan de la palma
        yemas = libre & cv2.dilate((g | p).astype(np.uint8), disk(24)).astype(bool) & (cb > 215)
        # y todo lo libre que encierra su contorno (los grises del antialias de las rayas)
        zona_g = fill_holes(cv2.dilate((g | p | yemas).astype(np.uint8), disk(5)).astype(bool))
        lab[libre & (g | p | yemas | zona_g)] = ID["guante" + lado]
    for lado, p in pies.items():
        zona_p = fill_holes(cv2.dilate(p.astype(np.uint8), disk(5)).astype(bool))   # con los grises de sus rayas
        lab[libre & (p | zona_p) & (lab == 0)] = ID["pie" + lado]
    cola_l = np.zeros((H, W), bool)
    for m in cola_c:
        cola_l |= m
    lab[libre & cola_l & (lab == 0)] = ID["cola"]
    for m, st, cen in componentes(libre & (lab == 0), 200):   # anillos que cola_c no recogió
        if (m & cola_full).sum() >= 0.5 * st[4] and cen[1] > 0.6 * H:
            lab[m] = ID["cola"]
    for lado in "ID":
        lab[libre & orejas[lado] & (lab == 0)] = ID["oreja" + lado]
    lab[libre & mech & (lab == 0)] = ID["mechon"]
    lab[libre & cabeza & (lab == 0)] = ID["craneo"]

    # brazos: la banda de su espina; una componente que sea casi toda brazo entra entera
    esp_b, esp_p = {}, {}
    for lado in "ID":
        b = T["brazos"][lado]
        esp_b[lado] = Espina.bezier(to_px(cal, [b["P0"], b["P1"], b["P2"]]))
        hw = (b["grosor"] / 2 + 7) * s
        S_, D_ = banda_sd(esp_b[lado], (H, W), libre & (lab == 0) & (np.abs(xx - np.mean(esp_b[lado].p[:, 0])) < 260))
        S0 = np.nan_to_num(S_, nan=-1e9)
        # la banda acaba en la muñeca (la espina ya entra 26 px en el puño) y en el hombro
        banda = (np.abs(np.nan_to_num(D_, nan=1e9)) <= hw - 2) & (S0 > -90) & (S0 < esp_b[lado].cum[-1])
        for m, st, cen in componentes(libre & (lab == 0), 50):
            f = (m & banda).sum() / st[4]
            if f >= 0.6:
                lab[m] = ID["brazo" + lado]
            elif f > 0.02:
                lab[m & banda] = ID["brazo" + lado]
    # piernas: bajo el corte de cadera (perpendicular a su espina), la banda de cada una
    pi = T["pierna"]
    cortes_p = {}
    for lado in "ID":
        k = 1 if lado == "I" else -1
        P = [[pi[q][0] * k, pi[q][1]] for q in ("P0", "P1", "P2")]
        esp_p[lado] = Espina.bezier(to_px(cal, P))
        hw = (pi["grosor"] / 2 + 7) * s
        cortes_p[lado] = 60.0          # la espina trazada se prolongó 60 px sobre la cadera medida
        S_, D_ = banda_sd(esp_p[lado], (H, W), libre & (lab == 0) & ((xx < cal["xc"]) if lado == "I" else (xx >= cal["xc"])))
        S0 = np.nan_to_num(S_, nan=-1e9)
        sel = (S0 >= cortes_p[lado]) & (np.abs(np.nan_to_num(D_, nan=1e9)) <= 1.25 * hw)
        # lo que queda más allá del tobillo es del pie (si no, al doblar la pierna
        # se estira fuera de su espina y asoma bajo el pie)
        fin = esp_p[lado].cum[-1]
        techo_pie = int(np.where(pies[lado].any(1))[0].min())
        al_pie = sel & ((S0 > fin) | (yy > techo_pie + 6))
        lab[al_pie] = ID["pie" + lado]
        lab[sel & ~al_pie] = ID["pierna" + lado]
    lab[libre & (lab == 0) & cola_full & (yy > 0.6 * H)] = ID["cola"]   # anillos pegados al pelaje de la pierna
    # bajo la cadera, a la derecha y fuera de la pierna, solo queda cola
    for m, st, cen in componentes(libre & (lab == 0), 50):
        if cen[0] > cal["xc"] + 60 and cen[1] > 0.72 * H and st[4] < 40000 and not (m & dil(pies["I"] | pies["D"], 6)).any():
            lab[m] = ID["cola"]
    lab[libre & (lab == 0)] = ID["torso"]
    # por debajo del empeine no hay cola: es el pie (la cola se apoya detrás de él)
    for lado in "ID":
        techo = int(np.where(pies[lado].any(1))[0].min())
        lado_m = (xx < cal["xc"]) if lado == "I" else (xx >= cal["xc"])
        lab[(lab == ID["cola"]) & (yy > techo) & lado_m] = ID["pie" + lado]
    # el torso es UNA pieza: sus islas sueltas son de la pieza con la que más lindan
    # (islas medidas a través de la tinta: la panza y su anillo de pelo son la misma pieza)
    torso_l = lab == ID["torso"]
    grupos = componentes(dil(torso_l, 8), 1)
    principal = max(grupos, key=lambda t: (t[0] & torso_l).sum())[0]
    for g_, st, cen in grupos:
        m = g_ & torso_l
        if g_ is principal or not m.any():
            continue
        borde = lab[dil(m, 3) & ~m]
        borde = borde[(borde > 0) & (borde != ID["torso"])]
        if len(borde):
            lab[m] = np.bincount(borde).argmax()

    # ---- cada píxel de tinta va a la pieza libre más cercana; si dos empatan (a 4 px:
    # una línea compartida), a la de MÁS prioridad, la que se dibuja encima
    lab_t = np.zeros((H, W), np.int16)
    dist = {k: cv2.distanceTransform((lab != ID[k]).astype(np.uint8), cv2.DIST_L2, 5) for k in PRIO}
    dmin = np.minimum.reduce([dist[k] for k in PRIO])
    for nombre in PRIO:
        z = ink & sil & (dist[nombre] <= dmin + 4) & (dist[nombre] <= 16)
        lab_t[z] = ID[nombre]
    resto = ink & sil & (lab_t == 0)
    if resto.any():
        _, near = cv2.distanceTransformWithLabels((lab == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        ys0, xs0 = np.where(lab > 0)
        val = np.zeros(near.max() + 1, np.int16)
        val[near[ys0, xs0]] = lab[ys0, xs0]
        lab_t[resto] = val[near[resto]]
    # un miembro solo lleva la tinta de su banda: lo que quede lejos de su espina
    # (y saldría volando al doblarlo) es del torso
    for nombre, esp, hw in [("brazo" + l, esp_b[l], (T["brazos"][l]["grosor"] / 2 + 7) * s) for l in "ID"] +                            [("pierna" + l, esp_p[l], (T["pierna"]["grosor"] / 2 + 7) * s) for l in "ID"]:
        ys_, xs_ = np.where(lab_t == ID[nombre])
        if len(ys_):
            _, d_ = esp.sd(np.stack([xs_, ys_], 1))
            lejos = np.abs(d_) > hw + 14
            if lejos.any():   # a la pieza vecina más cercana que no sea este miembro
                otros = (lab > 0) & (lab != ID[nombre])
                _, near = cv2.distanceTransformWithLabels((~otros).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
                yo, xo = np.where(otros)
                val = np.zeros(near.max() + 1, np.int16)
                val[near[yo, xo]] = lab[yo, xo]
                lab_t[ys_[lejos], xs_[lejos]] = val[near[ys_[lejos], xs_[lejos]]]
    region = {k: (lab == ID[k]) | (lab_t == ID[k]) for k in PRIO}
    if debug:
        print("etiquetas:", {k: (int((lab == ID[k]).sum()), int((lab_t == ID[k]).sum())) for k in PRIO})
    tinta = {k: lab_t == ID[k] for k in PRIO}

    # ---- base tonal por píxel (para saber qué es sombra) y piezas de tono propio
    B = np.full((H, W), TN.index("T_FUR"))
    for k in ("guanteI", "guanteD"):
        B[region[k]] = TN.index("T_WHITE")
    for k in ("pieI", "pieD"):
        B[region[k]] = TN.index("T_MASK")
    # crema de la cara y panza: el mismo corte de la iteración 1 (luminancia 195 de la
    # madre) pero sobre la madre suavizada, así el borde es limpio y no dentado
    claro = frac < (1 - 195 / float(np.median(cb[~sil]))) / RECTA
    lob_m = np.zeros((H, W), bool)
    blancos, pupilas = {}, {}
    for m, st, cen in lobulos:
        lado = "I" if cen[0] < cal["xc"] else "D"
        lob = fill_holes(m)
        lob_m |= lob
        bl = [(mm, s2) for mm, s2, c2 in comps if (mm & lob).sum() > 0.9 * mm.sum() and np.median(cb[mm]) > 235]
        blancos[lado] = fill_holes(max(bl, key=lambda t: t[1][4])[0])
        pupilas[lado] = mayor(ink & ero(blancos[lado], 6))
    ojos_m = blancos["I"] | blancos["D"]
    B[dil(lob_m, 6)] = TN.index("T_MASK")
    B[ojos_m] = TN.index("T_WHITE")
    lob_cy = float(np.mean([cen[1] for _, _, cen in lobulos]))
    crema = claro & region["craneo"] & (yy > lob_cy) & ~dil(lob_m, 4)
    crema = suave_mask(cv2.morphologyEx(crema.astype(np.uint8), cv2.MORPH_OPEN, D(4)).astype(bool), (H, W))
    crema = fill_holes(crema) & ~lob_m
    crema_c = [m for m, st, cen in componentes(crema, 2500)]
    crema = np.zeros((H, W), bool)
    for m in crema_c:
        crema |= m
    B[crema] = TN.index("T_CREAM")
    panza = mayor(claro & region["torso"])
    panza = suave_mask(cv2.morphologyEx(panza.astype(np.uint8), cv2.MORPH_OPEN, D(5)).astype(bool), (H, W)) & dil(region["torso"], 2)
    B[panza] = TN.index("T_CREAM")

    # cola: cada anillo (componente libre) con la mediana de su tono en la madre
    anillos = []
    f2 = fraccion_tono(cb, sil, ink, 2)
    for m, st, cen in componentes(libre & (lab == ID["cola"]), 200):
        t = int(cuantiza(np.median(f2[m])))
        anillos.append((m, TN[t]))
        B[m] = t

    # ---- sombras: lo que la madre suavizada (σ 10) cuantiza distinto de la base
    # fuera: dentro del antifaz y los ojos, y el halo que el suavizado σ 10 saca de
    # guantes y pies (si no, el torso hereda un «guante fantasma» blanco)
    sin_sombra = dil(lob_m, 8) | dil(ojos_m, 4) | region["cola"] | dil(nariz, 6) \
        | dil(region["guanteI"] | region["guanteD"] | region["pieI"] | region["pieD"], 30)
    for m in bocas:
        sin_sombra |= dil(m, 6)
    cand = []
    for pieza in ("craneo", "orejaI", "orejaD", "mechon", "torso", "brazoI", "brazoD", "piernaI", "piernaD"):
        for ti in range(1, len(TN)):          # T_WHITE no es sombra: solo guantes, ojos y dientes
            m = (Q == ti) & (B != ti) & region[pieza] & ~sin_sombra
            if ti <= TN.index("T_MEDIO"):
                m &= ~crema & ~panza     # dentro de la crema solo entran sombras de verdad (más oscuras)
            for c, st, cen in componentes(m, SOMBRA_AREA_MIN):
                cand.append((int(st[4]), pieza, TN[ti], c))
    cand.sort(key=lambda t: -t[0])
    elegidas = cand[:SOMBRAS_MAX]
    area_min = max(SOMBRA_AREA_MIN, elegidas[-1][0]) if len(cand) > SOMBRAS_MAX else SOMBRA_AREA_MIN
    sombras = {k: [] for k in PRIO}
    sombra_vis = np.zeros((H, W), np.int16) - 1
    for a, pieza, tono, c in elegidas:
        sm = suave_mask(c, (H, W)) & dil(region[pieza], 2)
        polys = poly_ccomp(cal, sm, eps=0.8, dens=pieza.startswith(("brazo", "pierna", "craneo")), min_area=200)
        if polys:
            sombras[pieza].append({"tono": tono, "forma": polys})
            sombra_vis[sm] = TN.index(tono)
    out["sombras_meta"] = {"area_min_px": int(area_min), "n": sum(len(v) for v in sombras.values()), "max": SOMBRAS_MAX,
                           "candidatas": len(cand), "px_por_u": s}

    def relleno(k, extra=None):
        m = dil(region[k], 3) & ero(sil, 2)   # el borde del relleno queda bajo la tinta del contorno
        if extra is not None:
            m |= extra
        return fill_holes(m) & ~huecos if not k.startswith(("brazo", "pierna", "cola")) else (m & ~huecos)

    # ---- cabeza: cráneo, orejas, mechón, cara
    pup_all = pupilas["I"] | pupilas["D"]
    anillo = {l: ink & dil(blancos[l], 14) & ~dil(pupilas[l], 2) & ~ero(blancos[l], 6) for l in "ID"}
    anillo_all = anillo["I"] | anillo["D"]
    antifaz_t = ink & dil(lob_m, 12) & ~anillo_all & ~pup_all
    cejas_m = np.zeros((H, W), bool)
    for lado, (m, a, cen, w) in cejas.items():
        cejas_m |= m
    # la sonrisa (más el surco) va aparte; la raya de la barbilla es tinta del cráneo (baja con la mandíbula)
    bocas = sorted(bocas, key=lambda m: -m.sum())
    sonr = bocas[0]
    bot = np.where(sonr.any(1))[0].max()
    barbilla = [m for m in bocas[1:] if np.where(m.any(1))[0].min() > bot - 4]
    boca_m = np.zeros((H, W), bool)
    for m in bocas:
        if not any(m is b for b in barbilla):
            boca_m |= m
    cara_t = antifaz_t | anillo_all | pup_all | dil(cejas_m, 1) | dil(nariz, 3) | dil(boca_m, 1)
    out["craneo"] = {"forma": poly_ext(cal, relleno("craneo"), dens=True),
                     "tinta": poly_iso(cal, cb, tinta["craneo"] & ~cara_t, dens=True, excluir=cara_t),
                     "sombras": sombras["craneo"]}
    out["crema_cara"] = [p for m in crema_c for p in poly_ext(cal, m, dens=True)]
    for lado in "ID":
        r = relleno("oreja" + lado, orejas_ext[lado])
        out.setdefault("orejas", {})[lado] = {
            "forma": poly_ext(cal, r), "tinta": poly_iso(cal, cb, tinta["oreja" + lado] & ~cara_t),
            "sombras": sombras["oreja" + lado], "pivote": T["orejas"][lado]["pivote"]}
    out["mechon"] = {"forma": poly_ext(cal, relleno("mechon", mech_ext)), "tinta": poly_iso(cal, cb, tinta["mechon"]),
                     "sombras": sombras["mechon"], "pivote": T["mechon"]["pivote"]}
    out["antifaz_tinta"] = {l: poly_iso(cal, cb, antifaz_t & (xx < cal["xc"] if l == "I" else xx >= cal["xc"])) for l in "ID"}
    ojos = {}
    for l in "ID":
        o = dict(T["ojos"][l])
        ys_, xs_ = np.where(pupilas[l])
        o["tinta"] = poly_iso(cal, cb, anillo[l])
        o["pupila"] = dict(o["pupila"], tinta=poly_iso(cal, cb, pupilas[l]),
                           centro=r1(to_u(cal, [(xs_.mean(), ys_.mean())]))[0])
        ojos[l] = o
    out["ojos"] = ojos
    out["boca_sonrisa"] = poly_iso(cal, cb, boca_m)
    # la línea de la sonrisa frontal (para abrir la boca dentro de la cara, punto 10)
    cols = np.where(sonr.any(0))[0]
    xs_s = np.linspace(cols.min() + 2, cols.max() - 2, 41)
    ys_s = [float(np.mean(np.where(sonr[:, int(round(x))])[0])) for x in xs_s]
    lin = to_u(cal, np.stack([xs_s, ys_s], 1))
    out["sonrisa_linea"] = r1(lin)
    ys_b, xs_b = np.where(sonr)
    out["sonrisa_centro"] = r1(to_u(cal, [((xs_b.min() + xs_b.max()) / 2, (ys_b.min() + ys_b.max()) / 2)]))[0]

    # ---- torso
    # la línea que el torso comparte con cada brazo (el borde interior del brazo) es
    # también el borde del torso: se copia en los dos, así al apartar el brazo el
    # torso no queda sin contorno (en el neutro el brazo la tapa: no cambia nada)
    compartida = (tinta["brazoI"] | tinta["brazoD"]) & dil(lab == ID["torso"], 14)
    out["torso"] = {"forma": poly_ext(cal, relleno("torso")), "tinta": poly_iso(cal, cb, tinta["torso"] | compartida),
                    "sombras": sombras["torso"]}
    out["panza"] = {"forma": poly_ext(cal, panza)}

    # ---- brazos y piernas (R3): relleno, tinta y sombras en u del neutro, con su prolongación oculta
    for lado in "ID":
        k = "brazo" + lado
        S_, _ = banda_sd(esp_b[lado], (H, W), lab == ID[k])
        sig0 = float(np.nanpercentile(S_, 1))
        f_ext, t_ext = extension(esp_b[lado], region[k], ink, sig0, 40 * s, (H, W))
        bajo = dil(region["craneo"] | region[k], 3)           # el brazo va delante del torso: solo bajo la cabeza
        f_ext, t_ext = f_ext & bajo, t_ext & bajo
        # la prolongación va APARTE («raiz»): se pinta detrás del torso, el brazo delante
        rel = relleno(k)
        out.setdefault("brazo_piel", {})[lado] = {
            "forma": poly_ext(cal, rel, dens=True), "tinta": poly_iso(cal, cb, tinta[k], dens=True),
            "sombras": sombras[k], "sigma_hombro": round(sig0 / s, 1),
            "raiz": {"forma": poly_ext(cal, f_ext | (rel & dil(f_ext, 6)), dens=True),
                     "tinta": poly_iso(cal, np.where(t_ext, 0, cb), t_ext | (tinta[k] & dil(t_ext, 6)), dens=True), "sombras": []}}
        k = "pierna" + lado
        f_ext, t_ext = extension(esp_p[lado], region[k], ink, cortes_p[lado], 60 * s, (H, W))
        bajo = dil(region["torso"] | region[k], 3)            # la pierna va detrás del torso: solo bajo él
        f_ext, t_ext = f_ext & bajo, t_ext & bajo
        out.setdefault("pierna_piel", {})[lado] = {
            "forma": poly_ext(cal, relleno(k, f_ext), dens=True), "tinta": poly_iso(cal, np.where(t_ext, 0, cb), tinta[k] | t_ext, dens=True),
            "sombras": sombras[k]}

    # ---- pies y guantes (rígidos, en sus coordenadas locales)
    out["pies"] = {}
    for lado in "ID":
        tob = np.array(T["pierna"]["P2"]) * ([1, 1] if lado == "I" else [-1, 1])
        loc = lambda polys, tob=tob: [r1(np.array(p) - tob) for p in polys]  # noqa: E731
        out["pies"][lado] = {"forma": loc(poly_ext(cal, relleno("pie" + lado))), "tinta": loc(poly_iso(cal, cb, tinta["pie" + lado]))}
    out["guantes"] = {}
    for lado in "ID":
        br = T["brazos"][lado]
        P1, P2 = np.array(br["P1"]), np.array(br["P2"])
        ang = np.arctan2(P2[1] - P1[1], P2[0] - P1[0])
        rot = np.array([[np.cos(-ang), -np.sin(-ang)], [np.sin(-ang), np.cos(-ang)]])
        loc = lambda polys: [r1((np.array(p) - P2) @ rot.T) for p in polys]  # noqa: E731
        k = "guante" + lado
        pz = dil(puno[lado], 12) & region[k]
        out["guantes"][lado] = {"forma": loc(poly_ext(cal, relleno(k))), "tinta": loc(poly_iso(cal, cb, tinta[k])),
                                "puno": {"forma": loc(poly_ext(cal, dil(pz, 2) & dil(region[k], 2))),
                                         "tinta": loc(poly_iso(cal, cb, tinta[k] & pz))},
                                "angulo_neutro": round(float(np.degrees(ang)), 2)}

    # ---- cola: anillos con su tono, tinta copiada y una espina para curvarla (punto 9)
    base_px = to_px(cal, [T["cola"]["base"]])[0]
    # la cola sigue por detrás de la pierna derecha: se une solo bajo piernas y torso (no se ve)
    tapado = region["piernaI"] | region["piernaD"] | region["torso"]
    puente = fill_holes(cola_full | (cv2.morphologyEx(cola_full.astype(np.uint8), cv2.MORPH_CLOSE, D(85)).astype(bool) & tapado))
    cam = camino_esqueleto(puente, base_px)
    b0, b1, b2, b3 = ajustar_cubica(cam)
    # el relleno oculto es solo un TUBO del ancho de la cola a lo largo de su espina
    # (si se rellenara todo lo tapado, asomaría bajo piernas y torso al moverlos)
    from skimage.morphology import skeletonize
    vis_c = fill_holes(region["cola"])
    dt_c = cv2.distanceTransform(vis_c.astype(np.uint8), cv2.DIST_L2, 5)
    r_c = float(np.percentile(dt_c[skeletonize(vis_c)], 90))
    t_ = np.linspace(0, 1, 80)[:, None]
    bz = (1 - t_) ** 3 * b0 + 3 * (1 - t_) ** 2 * t_ * b1 + 3 * (1 - t_) * t_ ** 2 * b2 + t_ ** 3 * b3
    eje = np.vstack([base_px, bz])
    tubo = np.zeros((H, W), np.uint8)
    cv2.polylines(tubo, [np.round(eje).astype(np.int32)], False, 1, int(2 * r_c))
    # también lo que guantes y brazos tapan de la cola (al apartarlos no queda hueco)
    tras_mano = region["guanteI"] | region["guanteD"] | region["brazoI"] | region["brazoD"]
    tubo = tubo.astype(bool) & (tapado | tras_mano)
    ys_c, xs_c = np.where(region["cola"] & (xx > cal["xc"] + 100))
    casco = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(casco, cv2.convexHull(np.stack([xs_c, ys_c], 1).astype(np.int32)), 1)
    tubo &= yy < cal["suelo"] - 12 * s        # lo oculto no baja al suelo (regla de los 6 u de la cola)
    casco_m = casco.astype(bool) & tras_mano & sil & ~vis_c
    tubo |= casco_m
    # el borde de lo que la mano tapaba lleva contorno (se ve solo al apartar la mano)
    borde_casco = (dil(casco.astype(bool), 0) & ~ero(casco.astype(bool), 11)) & tras_mano & sil
    tubo |= cv2.morphologyEx(cola_full.astype(np.uint8), cv2.MORPH_CLOSE, D(40)).astype(bool) & tras_mano & dil(region["cola"], 60)
    out["cola"] = {"base": T["cola"]["base"], "forma": poly_ext(cal, relleno("cola", tubo), dens=True),
                   "tinta": poly_iso(cal, np.where(borde_casco, 0, cb), tinta["cola"] | borde_casco, dens=True),
                   "anillos": [{"tono": t, "forma": poly_ext(cal, dil(m, 3) & dil(region["cola"], 2), dens=True)} for m, t in anillos],
                   "espina": r1(to_u(cal, [b0, b1, b2, b3]))}

    if debug:
        EVID.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(5)
        pal = rng.integers(60, 255, (len(PRIO) + 1, 3))
        vis = cv2.cvtColor(cb, cv2.COLOR_GRAY2BGR).astype(float)
        col = pal[np.maximum(lab, lab_t)]
        msk = (lab > 0) | (lab_t > 0)
        vis[msk] = 0.5 * vis[msk] + 0.5 * col[msk]
        vis[sombra_vis >= 0] = (0.5 * vis[sombra_vis >= 0] + [0, 0, 120])
        cv2.imwrite(str(EVID / "_piezas_debug.png"), cv2.resize(vis.astype(np.uint8), None, fx=0.5, fy=0.5))
    return out


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
    orejas_px, orejas_ext_px = {}, {}
    for lado, (a, b) in bases.items():
        s = lado_de_recta((H, W), a, b)
        # la oreja es el lado PEQUEÑO de la recta (el otro es el cráneo entero)
        sup = (yy < 330) & (np.abs(xx - (a[0] + b[0]) / 2) < 220)
        lado_pos = (cabeza & sup & (s > 0)).sum() < (cabeza & sup & (s < 0)).sum()
        oreja = cabeza & sup & ((s > 0) if lado_pos else (s < 0))
        # se mete 30 px bajo el cráneo (capa de atrás) para no dejar costura al girar
        oreja_ext = cabeza & cv2.dilate(oreja.astype(np.uint8), disk(30)).astype(bool)
        craneo &= ~oreja
        orejas_px[lado], orejas_ext_px[lado] = oreja, oreja_ext
        corte =cv2.dilate(oreja.astype(np.uint8), disk(5)).astype(bool) & craneo
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

    # ---- iteración 2: tinta COPIADA, cortes sin trazo, tonos medidos (R1-R3)
    orejas_m = {lado: m for lado, m in orejas_px.items()}
    T.update(piezas_r1(cb, sil, cal, ink, comps, guantes, pies, cola_c, cola_full, cabeza, orejas_m, orejas_ext_px,
                       mech, mech_ext, lobulos, nariz, brillo, bocas, cejas, T, debug))
    for k in ("detalles_cabeza", "detalles_torso"):
        T.pop(k, None)

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


CEJAS_TRAZADAS = ("triste", "decidido")   # la de sonrisa es la de la vista frontal (la ley del neutro)
CEJA_PUNTOS = 24


def _cejas_cabeza(cb, sil, ink, lob, to_u2):
    """Punto 11: la tinta entre el borde alto del blanco del ojo y el mechón, sin la
    tinta fina del contorno (apertura de disco 5 px); la componente mayor por lado."""
    lb = lob[0] | lob[1]
    ys_l, xs_l = np.where(lb)
    lx0, lx1, lw = xs_l.min(), xs_l.max(), xs_l.max() - xs_l.min()
    ly0, ly1 = ys_l.min(), ys_l.max()
    caja_l = np.zeros_like(lb)
    caja_l[ly0:ly1, lx0:lx1] = True
    cerca = cv2.dilate(lb.astype(np.uint8), disk(15)).astype(bool)
    blancos = sorted([(st[4], m) for m, st, cen in componentes(sil & ~ink & (cb > 225), 1000)
                      if st[0] >= lx0 - 15 and st[0] + st[2] <= lx1 + 15 and st[1] >= ly0 - 15 and st[3] > 0.3 * (ly1 - ly0) and st[2] < 0.45 * lw], key=lambda t: -t[0])[:2]
    y_ojo = int(min(np.where(m.any(1))[0].min() for _, m in blancos))
    y_top = int(np.where(sil.any(1))[0].min())
    y_mech = y_top + int(0.12 * (y_ojo - y_top))
    yy, xx = np.mgrid[0:cb.shape[0], 0:cb.shape[1]]
    y_mech = max(y_mech, y_ojo - int(0.6 * (ly1 - ly0)))   # sobre el ojo, por debajo del mechón
    zona = (yy > y_mech) & (yy < y_ojo) & (xx > lx0 + 0.04 * lw) & (xx < lx1 - 0.04 * lw)
    # fuera el anillo del ojo (la tinta pegada al blanco), que también es gruesa
    anillo = np.zeros_like(lb)
    for _, m in blancos:
        anillo |= cv2.dilate(m.astype(np.uint8), disk(18)).astype(bool)
    gruesa = cv2.morphologyEx((ink & zona & ~anillo).astype(np.uint8), cv2.MORPH_OPEN, disk(5)).astype(bool)
    out = {}
    ojos_x = sorted([(np.where(m.any(0))[0].min(), np.where(m.any(0))[0].max()) for _, m in blancos])
    for lado, (ox0, ox1) in zip("ID", ojos_x):
        ow = ox1 - ox0
        columna = (xx > ox0 - 0.35 * ow) & (xx < ox1 + 0.35 * ow)   # sobre SU ojo
        m = mayor(gruesa & columna)
        if m.sum() < 200:
            continue
        cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
        out[lado] = to_u2(c)
    return out


def ceja_24(p, lado):
    """Contorno de ceja (u) → 24 puntos por longitud de arco, empezando en el
    extremo exterior y siempre en sentido antihorario (para poder mezclar)."""
    p = np.asarray(p, float)
    a = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    if a < 0:
        p = p[::-1]
    i0 = int(np.argmin(p[:, 0])) if lado == "I" else int(np.argmax(p[:, 0]))
    p = np.roll(p, -i0, 0)
    q = np.vstack([p, p[:1]])
    cum = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
    t = np.linspace(0, cum[-1], CEJA_PUNTOS, endpoint=False)
    return np.stack([np.interp(t, cum, q[:, 0]), np.interp(t, cum, q[:, 1])], 1)


def _area(p):
    p = np.asarray(p, float)
    return abs(0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]))


def cejas_mezcla(T: dict, cejas_tr: dict) -> dict:
    out, control = {}, {}
    for lado in "ID":
        base = ceja_24(max(T["cejas"][lado]["forma"], key=_area), lado)
        out[lado] = {"base": r1(base)}
        for nombre in CEJAS_TRAZADAS:
            c = ceja_24(cejas_tr[nombre][lado], lado)
            k = _area(c) / _area(base)
            control[f"{nombre}_{lado}"] = round(float(k), 3)
            assert 0.5 <= k <= 1.8, f"ceja {nombre} {lado}: área ×{k:.2f} fuera de 0,5-1,8 (corregir en traza_manual.js)"
            out[lado][nombre] = r1(c)
    out["area_relativa"] = control
    return out


def boca_o(T: dict, o_tr: dict) -> dict:
    """Punto 13: la «o» de asombro centrada en el eje, 6 u bajo el centro de la
    sonrisa frontal, y simétrica (media de la forma trazada y su espejo)."""
    k = 4.0
    todo = np.vstack([np.asarray(q, float) for q in o_tr["o"]])
    c = (todo.min(0) + todo.max(0)) / 2
    span = float(np.abs(todo - c).max()) + 10
    n = int(2 * span * k) + 1

    def ras(polys):
        m = np.zeros((n, n), np.float32)
        for q in polys:
            cv2.fillPoly(m, [np.round(((np.asarray(q, float) - c) + span) * k * 8).astype(np.int32)], 1.0, shift=3)
        return m
    m = ras(o_tr["o"])
    cx = (np.arange(n)[None, :] * m).sum() / m.sum()
    dx = int(round(2 * cx - (n - 1)))

    def sim(mm):
        return (((mm + np.roll(cv2.flip(mm, 1), dx, 1)) / 2) >= 0.5).astype(np.uint8)

    def polys(mm):
        cs, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        return [cv2.approxPolyDP(q.astype(np.float32), 0.8, True)[:, 0, :] / k - span + c for q in cs if cv2.contourArea(q) > 20]
    o = polys(sim(m))
    le = polys(sim(ras(o_tr["lengua"]))) if o_tr["lengua"] else []
    allp = np.vstack(o)
    cen = np.array([(allp[:, 0].min() + allp[:, 0].max()) / 2, (allp[:, 1].min() + allp[:, 1].max()) / 2])
    obj = np.array([0.0, float(T["sonrisa_centro"][1]) - 6])
    return {"tinta": [r1(q - cen + obj) for q in o], "lengua": [r1(q - cen + obj) for q in le], "lengua_tono": o_tr["lengua_tono"]}


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
    cejas_tr = {}
    o_tr = None
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
        if nombre == "asombro":
            # la «o»: el hueco cerrado de la tinta de la boca (interior) más su anillo
            u = ink & interior & zona_boca & ~cerca_lob
            hueco = fill_holes(u) & ~u
            hs = componentes(hueco, 300)
            if hs:
                inte = max(hs, key=lambda t: t[1][4])[0]
                anillo = cv2.dilate(inte.astype(np.uint8), disk(10)).astype(bool) & ink
                o_m = fill_holes(inte | anillo)
                lengua = inte & (cb > 110)
                o_tr = {"o": [r1(to_u2(c)) for c in contornos(o_m, eps=0.6, suav=1.2)],
                        "lengua": [r1(to_u2(c)) for c in contornos(lengua, min_area=80, eps=0.6, suav=1.2)],
                        "lengua_tono": TN[int(cuantiza(np.median(fraccion_tono(cb, sil, ink, 2)[lengua])))] if lengua.sum() > 80 else "T_MASK"}
        if nombre in CEJAS_TRAZADAS:
            cejas_tr[nombre] = _cejas_cabeza(cb, sil, ink, lob, to_u2)
        out[nombre] = {"boca": [p for m in boca for p in polys(m, suav=1.2, eps=0.6)], "boca_relleno": boca_rell,
                       "cejas": ce, "cerrado": cerrado,
                       "pecas": [p for m in pecas for p in polys(m, suav=1.0, eps=0.6)], "escala": round(float(k), 4)}
    T["cejas_mezcla"] = cejas_mezcla(T, cejas_tr)
    T["boca_o"] = boca_o(T, o_tr)
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
