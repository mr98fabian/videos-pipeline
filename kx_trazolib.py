"""Funciones de apoyo para trazar dibujos de Tadeo (compartidas por kx_trazo y kx_lamina).

Sin nada de la hoja madre: contornos, componentes, isolíneas de tinta, tonos y
conversión px <-> unidades del rig. `cal` es {"xc", "suelo", "s"}: eje x en px,
suelo en px y px por unidad del rig.
"""
from __future__ import annotations

import cv2
import numpy as np

def silueta(c: np.ndarray) -> np.ndarray:
    """Todo lo que el papel exterior no alcanza (relleno desde la esquina)."""
    m = (c > 220).astype(np.uint8)
    ff = np.zeros((c.shape[0] + 2, c.shape[1] + 2), np.uint8)
    cv2.floodFill(m, ff, (0, 0), 2)
    return m != 2



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
TONOS = {"T_WHITE": 0.0, "T_CREAM": 0.09, "T_MEDIO": 0.25, "T_FUR": 0.39, "T_FUR_SOMBRA": 0.47, "T_MASK": 0.64, "T_OSCURO": 0.69}
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
HALO_NIVEL = 170.0
BORDE_AA = 0.6       # u: la silueta de la madre (luminancia 220) va ~1 px por fuera de su tinta   # iteración 3: el borde suave de la madre (segunda tinta, T_FUR_SOMBRA)


def poly_iso(cal, cb, zona, dens=False, eps=0.5, min_area=6, excluir=None, nivel=None):
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
    for c in find_contours(f, ISO_TINTA if nivel is None else nivel):
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
