"""Trazador de láminas de pose de Tadeo (método «una pose = un dibujo»).

    py kx_lamina.py                 # traza las 9 láminas + pointing, mide y calibra
    py kx_lamina.py decidido grito  # solo esas
    py kx_lamina.py --debug         # además, hoja de segmentación en evidencia

Diseño: misiones/2026-11-25-diseno-trazador-laminas.md (aprobado el 25 nov 2026).
De cada lámina sale `traza_<pose>.js` con el cuerpo (una pieza), la cola y el
tapón de cuello, en unidades del rig (suelo y = 0, x = 0 en el punto medio de
los pies) y a la escala de la madre: el antifaz mide lo que mide el del rig.
La cabeza de la lámina se descarta: la pone el rig, anclada por el antifaz.

Nunca «arregla» una lámina: si no encuentra dos lóbulos de antifaz o dos pies,
la rechaza con el motivo (sección 7 del diseño).
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import cv2
    import numpy as np

    import kx_trazolib as L
except ImportError:  # pragma: no cover - CI sin OpenCV
    cv2 = np = L = None

ROOT = Path(__file__).resolve().parent
EVID = ROOT / "misiones" / "evidencia"
OUT_DIR = ROOT / "motion_graphics" / "src" / "kx" / "tadeo" / "laminas"
EVID_OUT = EVID / "0006"
POSES = ["decidido", "confundido", "orgulloso", "estafado", "grito", "explicando", "codicia", "asombro", "triunfo"]
# Las regeneradas de la misión 0006 (por un fallo concreto) sustituyen a las de la 0005.
REGENERADAS = EVID / "0006" / "regeneradas"
FUENTES = {p: (REGENERADAS / f"{p}_api.png" if (REGENERADAS / f"{p}_api.png").exists() else EVID / "0005" / f"{p}_api.png")
           for p in POSES} | {"pointing": EVID / "0004" / "pointing_api.png"}
VISTA_3_4 = {"pointing"}          # marcas que dependen de la vista: se reportan, no cuentan

ESCALA = 2                        # las láminas (896×1200) se trabajan ×2: antifaz ≈ 600-770 px, como la madre ×4
INK = 75                          # luminancia de tinta (igual que kx_trazo)
A_RIG = 379.5                     # ancho del antifaz de la madre en u del rig (622 px ×4 / 1,639 px por u)
BARBILLA_A = 0.34                 # barbilla del rig bajo el borde inferior del antifaz, en A (medida en la madre)


class Rechazo(Exception):
    """La lámina no se traza: motivo concreto, para regenerarla (sección 7)."""


@dataclass
class Lamina:
    nombre: str
    g: np.ndarray                         # gris ×ESCALA
    sil: np.ndarray = None
    ink: np.ndarray = None
    A: float = 0.0
    antifaz: dict = field(default_factory=dict)
    pies: dict = field(default_factory=dict)
    barbilla: dict = field(default_factory=dict)
    mascaras: dict = field(default_factory=dict)
    marcas: dict = field(default_factory=dict)


# ------------------------------------------------------------------ carga
def cargar(nombre: str, ruta: Path | None = None, gris: np.ndarray | None = None, escala: float = ESCALA) -> Lamina:
    if gris is None:
        gris = cv2.imread(str(ruta or FUENTES[nombre]), cv2.IMREAD_GRAYSCALE)
        if gris is None:
            raise Rechazo(f"no se puede leer {ruta or FUENTES[nombre]}")
    if escala != 1:
        gris = cv2.resize(gris, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)
    lam = Lamina(nombre, gris)
    lam.sil = silueta(gris)
    lam.ink = (gris < INK) & lam.sil
    return lam


def silueta(g: np.ndarray) -> np.ndarray:
    """Lo que el papel exterior no alcanza, rellenando desde las cuatro esquinas."""
    m = (g > 220).astype(np.uint8)
    ff = np.zeros((g.shape[0] + 2, g.shape[1] + 2), np.uint8)
    for x, y in ((0, 0), (g.shape[1] - 1, 0), (0, g.shape[0] - 1), (g.shape[1] - 1, g.shape[0] - 1)):
        if m[y, x] == 1:
            cv2.floodFill(m, ff, (x, y), 2)
    return m != 2


def madre() -> Lamina:
    """La vista frontal de la hoja madre (×4) como si fuera una lámina: prueba de identidad."""
    import kx_trazo as KT
    cb, _ = KT.frente()
    return cargar("madre", gris=cb, escala=1)


# ------------------------------------------------------------------ anclas
def regiones(lam: Lamina, min_area: int = 300):
    return L.componentes(lam.sil & ~lam.ink, min_area)


def anclar_antifaz(lam: Lamina) -> None:
    g, sil = lam.g, lam.sil
    ys = np.where(sil.any(1))[0]
    top, bot = int(ys.min()), int(ys.max())
    cand = [(m, st, c) for m, st, c in regiones(lam)
            if 70 < np.median(g[m]) < 130 and c[1] < top + 0.45 * (bot - top)]
    cand.sort(key=lambda t: -t[1][4])
    # El antifaz es un PAR: dos manchas casi a la misma altura y una junto a otra.
    # No basta con «las dos mayores»: un anillo de cola alto (asombro) también es
    # medio-oscuro y cae en la mitad de arriba. Ratio de áreas ≥ 0,15 (en 3/4 un
    # lóbulo se ve pequeño), |dy| < media altura, separación < 3 anchos.
    pares = []
    for i in range(min(len(cand), 5)):
        for j in range(i + 1, min(len(cand), 5)):
            (_, si, ci), (_, sj, cj) = cand[i], cand[j]
            ratio = min(si[4], sj[4]) / max(si[4], sj[4])
            h = (si[3] + sj[3]) / 2
            w = (si[2] + sj[2]) / 2
            if ratio < 0.15 or abs(ci[1] - cj[1]) > 0.5 * h or abs(ci[0] - cj[0]) > 3 * w:
                continue
            pares.append((abs(ci[1] - cj[1]) / h - ratio, i, j))
    if not pares:
        raise Rechazo("antifaz: no hay dos lóbulos a la misma altura")
    pares.sort()
    if len(pares) > 1 and {pares[0][1], pares[0][2]} & {pares[1][1], pares[1][2]} == set() \
            and pares[1][0] - pares[0][0] < 0.05:
        raise Rechazo("antifaz: dos pares posibles")
    lob = sorted([cand[pares[0][1]], cand[pares[0][2]]], key=lambda t: t[2][0])
    union = L.fill_holes(lob[0][0]) | L.fill_holes(lob[1][0])
    yy, xx = np.where(union)
    # eje: recta que une los dos lóbulos (la inclinación base de la cabeza)
    c0, c1 = np.array(lob[0][2]), np.array(lob[1][2])
    ang = float(np.degrees(np.arctan2(c1[1] - c0[1], c1[0] - c0[0])))
    # ancho en la dirección del eje (invariante al giro de la cabeza)
    d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
    proy = xx * d[0] + yy * d[1]
    A = float(proy.max() - proy.min())
    n = np.array([-d[1], d[0]])                       # normal hacia abajo (y crece hacia abajo)
    if n[1] < 0:
        n = -n
    centro = np.array([xx.mean(), yy.mean()])
    abajo = float(((np.stack([xx, yy], 1) - centro) @ n).max())
    lam.A = A
    lam.antifaz = {"centro": centro.tolist(), "angulo": round(ang, 2), "A_px": round(A, 2), "dir": d.tolist(),
                   "normal": n.tolist(), "borde_inf": abajo, "mask": union}


def anclar_pies(lam: Lamina) -> None:
    g, sil, A = lam.g, lam.sil, lam.A
    bot = int(np.where(sil.any(1))[0].max())
    cand = []
    for m, st, c in regiones(lam):
        if np.median(g[m]) >= 130 or st[4] < 0.05 * A * A:
            continue
        if bot - (st[1] + st[3]) > 0.15 * A:
            continue
        cand.append((m, st, c))
    cand.sort(key=lambda t: -t[1][4])
    if len(cand) < 2 or cand[1][1][4] < 0.6 * cand[0][1][4]:
        raise Rechazo("pies: no hay dos pies a ras de suelo")
    pies = sorted(cand[:2], key=lambda t: t[2][0])
    suelo = float(max(st[1] + st[3] for _, st, _ in pies)) - 1
    xm = float(np.mean([c[0] for _, _, c in pies]))
    lam.pies = {"x": xm, "suelo": suelo, "masks": [m for m, _, _ in pies],
                "largo": [largo_rect(m) / A for m, _, _ in pies]}


def largo_rect(m: np.ndarray) -> float:
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    (_, _), (w, h), _ = cv2.minAreaRect(max(cs, key=cv2.contourArea))
    return float(max(w, h))


def anclar_barbilla(lam: Lamina) -> None:
    """Línea de corte de la cabeza: la barbilla del RIG, puesta por el antifaz.

    La cara y el peto son la misma región en todas las láminas (y en la madre):
    no hay línea de tinta que separe la barbilla, así que el corte no puede ser
    topológico. La cabeza del rig es la de la madre; colocada por el antifaz,
    su barbilla cae a BARBILLA_A·A bajo el borde inferior del antifaz, en la
    normal del eje. Como diagnóstico se mide también el estrechamiento de la
    región de la cara de la lámina (`propia_A`)."""
    af = lam.antifaz
    c, n, A = np.array(af["centro"]), np.array(af["normal"]), lam.A
    p = c + n * (af["borde_inf"] + BARBILLA_A * A)
    lam.barbilla = {"punto": p.tolist(), "propia_A": estrechamiento(lam)}


def estrechamiento(lam: Lamina):
    """Primer mínimo del ancho de la región cara-peto bajo el antifaz (en A), o None."""
    af, A, g = lam.antifaz, lam.A, lam.g
    c, n = np.array(af["centro"]), np.array(af["normal"])
    base = c + n * af["borde_inf"]
    reg = None
    for m, _, _ in regiones(lam):
        q = np.round(base + n * 0.35 * A).astype(int)
        if 0 <= q[1] < g.shape[0] and 0 <= q[0] < g.shape[1] and m[q[1], q[0]]:
            reg = L.fill_holes(m)
            break
    if reg is None:
        return None
    anchos = []
    for f in np.arange(0.10, 0.70, 0.01):
        y = int(round(base[1] + f * A))
        if not 0 <= y < g.shape[0]:
            break
        fila = reg[y]
        d = np.diff(np.r_[0, fila.astype(np.int8), 0])
        a, b = np.where(d == 1)[0], np.where(d == -1)[0]
        xc = int(round(base[0] + n[0] * f * A))
        w = [b[i] - a[i] for i in range(len(a)) if a[i] <= xc < b[i]]
        anchos.append((f, w[0] / A if w else np.nan))
    v = np.array([w for _, w in anchos])
    if np.all(np.isnan(v)):
        return None
    i = int(np.nanargmin(v))
    return round(float(anchos[i][0]), 2)


# ------------------------------------------------------------------ segmentación
_PLANTILLA = {}


def _cabeza_conexa(lam: Lamina) -> np.ndarray:
    """Silueta sobre la barbilla conexa con el antifaz (se usa solo en la madre,
    donde no hay manos ni hombros por encima de la barbilla)."""
    A, n, p = lam.A, np.array(lam.antifaz["normal"]), np.array(lam.barbilla["punto"])
    arriba = lam.sil & _encima(lam.g.shape, p, n)
    r = max(2, int(round(0.022 * A)))
    abierta = cv2.erode(arriba.astype(np.uint8), L.disk(r)).astype(bool)
    cab = np.zeros_like(arriba)
    for m, _, _ in L.componentes(abierta, 50):
        if (m & lam.antifaz["mask"]).any():
            cab |= m
    return cv2.dilate(cab.astype(np.uint8), L.disk(r + 1)).astype(bool) & arriba


def _encima(shape, p, n):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return ((xx - p[0]) * n[0] + (yy - p[1]) * n[1]) < 0


def plantilla_cabeza(lam: Lamina) -> np.ndarray:
    """La cabeza de la madre (la que pone el rig) llevada a la lámina por su
    antifaz: misma escala A, mismo giro, mismo centro."""
    if "m" not in _PLANTILLA:
        md = madre()
        anclar_antifaz(md)
        anclar_barbilla(md)
        _PLANTILLA["m"] = (_cabeza_conexa(md), md.antifaz["centro"], md.antifaz["angulo"], md.A)
    cab_m, c_m, ang_m, A_m = _PLANTILLA["m"]
    af = lam.antifaz
    M = cv2.getRotationMatrix2D((float(c_m[0]), float(c_m[1])), -(af["angulo"] - ang_m), lam.A / A_m)
    M[:, 2] += np.array(af["centro"]) - np.array(c_m)
    H, W = lam.g.shape
    return cv2.warpAffine(cab_m.astype(np.uint8), M, (W, H), flags=cv2.INTER_NEAREST).astype(bool)


def cortar_cabeza(lam: Lamina) -> None:
    """Máscara de la cabeza de la lámina: sus regiones (separadas por tinta) que
    caen sobre todo dentro de la cabeza de la madre colocada por el antifaz, más
    la tinta que las rodea, por encima de la barbilla. Hombros, brazos y manos
    que suben junto a la cabeza quedan fuera porque su región cae fuera."""
    A = lam.A
    tmpl = cv2.dilate(plantilla_cabeza(lam).astype(np.uint8), L.disk(max(2, int(0.06 * A)))).astype(bool)
    lam.mascaras["plantilla"] = tmpl
    encima = _encima(lam.g.shape, np.array(lam.barbilla["punto"]), np.array(lam.antifaz["normal"]))
    cab = lam.antifaz["mask"].copy()
    # regiones ya cortadas por la barbilla: la cara y el pelo de la cabeza siguen
    # sin tinta hasta el peto y los hombros, así que sin el corte serían una sola
    for m, st, _ in L.componentes(lam.sil & ~lam.ink & encima, 40):
        if (m & tmpl).sum() >= 0.6 * st[4]:
            cab |= m
    r = max(2, int(round(0.03 * A)))
    cab = L.fill_holes(cv2.morphologyEx(cab.astype(np.uint8), cv2.MORPH_CLOSE, L.disk(r)).astype(bool))
    cab = cv2.dilate(cab.astype(np.uint8), L.disk(r)).astype(bool)
    cab &= lam.sil & tmpl & encima
    if not cab.any():
        raise Rechazo("cabeza: el antifaz no queda dentro de la silueta")
    lam.mascaras["cabeza"] = cab


def quitar_huecos(lam: Lamina) -> None:
    """Papel encerrado (entre brazo y torso): región blanca cuyo anillo, pasada su
    tinta, es todo pelaje. Sale de la silueta: es fondo, no guante."""
    g, A = lam.g, lam.A
    cab = lam.mascaras["cabeza"]
    r = max(3, int(round(0.04 * A)))
    huecos = np.zeros_like(lam.sil)
    for m, st, _ in regiones(lam, 200):
        if np.median(g[m]) <= 240 or (m & cab).any():
            continue
        anillo = cv2.dilate(m.astype(np.uint8), L.disk(r)).astype(bool) & ~m & ~lam.ink
        if not anillo.any():
            continue
        v = g[anillo]
        # papel exterior al lado: es una mano o un borde, no un hueco cerrado
        if (~lam.sil[anillo]).any() or ((v > 100) & (v < 205)).mean() < 0.6:
            continue
        huecos |= m
    lam.mascaras["huecos"] = huecos
    lam.sil = lam.sil & ~huecos


def segmentar_cola(lam: Lamina) -> None:
    """Anillos oscuros (no pies, no antifaz, bajo la barbilla) + los anillos medios
    que los separan. Debe haber ≥ 3 bandas alternas."""
    g, A = lam.g, lam.A
    cab = lam.mascaras["cabeza"]
    pies = lam.pies["masks"]
    regs = regiones(lam, 150)
    oscuras, medias = [], []
    for m, st, c in regs:
        if (m & cab).any() or any((m & p).any() for p in pies):
            continue
        med = np.median(g[m])
        if med < 130:
            oscuras.append(m)
        elif med < 200 and st[4] < 0.25 * A * A:
            medias.append(m)
    if len(oscuras) < 2:
        raise Rechazo("cola: menos de dos anillos oscuros")
    r = max(2, int(round(0.03 * A)))
    cerca = lambda a, b: (cv2.dilate(a.astype(np.uint8), L.disk(r)).astype(bool) & b).any()  # noqa: E731
    pie_d = [cv2.dilate(p.astype(np.uint8), L.disk(r)).astype(bool) for p in pies]
    anillos = list(oscuras)
    for m in medias:
        vecinos = sum(cerca(m, o) for o in oscuras)
        if vecinos >= 2 or (vecinos == 1 and not any((m & pd).any() for pd in pie_d)):
            # descarta pierna y torso: un anillo es estrecho comparado con su largo
            if L.mayor(m).sum() < 0.12 * A * A:
                anillos.append(m)
    cola = np.zeros_like(lam.sil)
    for m in anillos:
        cola |= m
    # la tinta entre anillos entra en la cola (cierre de un grosor de línea)
    cola = cv2.morphologyEx(cola.astype(np.uint8), cv2.MORPH_CLOSE, L.disk(r)).astype(bool) & lam.sil
    # la pierna puede partir la cola en dos: entra todo trozo que tenga un anillo oscuro
    trozos = [m for m, _, _ in L.componentes(cola, 50) if any((m & o).sum() > 0.5 * o.sum() for o in oscuras)]
    cola = np.zeros_like(cola)
    for m in trozos:
        cola |= m
    n_anillos = sum((m & cola).sum() > 0.5 * m.sum() for m in anillos)
    if n_anillos < 3:
        raise Rechazo(f"cola: solo {n_anillos} bandas alternas")
    lam.mascaras["cola"] = cola
    lam.marcas["cola_anillos"] = int(n_anillos)


def segmentar_guantes(lam: Lamina) -> None:
    """Regiones casi blancas (dedos, palma, puño), agrupadas a través de su tinta.
    Un guante puede pisar la cara (`grito`): cuenta si al menos un cuarto de su
    área cae fuera de la cabeza de la madre o bajo la barbilla. Así quedan fuera
    ojos, dientes y mejillas claras, que caen enteros dentro."""
    g, A = lam.g, lam.A
    ojos = cv2.dilate(lam.antifaz["mask"].astype(np.uint8), L.disk(max(2, int(0.02 * A)))).astype(bool)
    dentro = lam.mascaras["plantilla"] & _encima(g.shape, np.array(lam.barbilla["punto"]), np.array(lam.antifaz["normal"]))
    blanco = np.zeros_like(lam.sil)
    for m, st, c in regiones(lam, 40):
        if np.median(g[m]) > 238 and not (m & ojos).sum() > 0.5 * m.sum():
            blanco |= m
    r = max(2, int(round(0.03 * A)))
    grupos = L.componentes(cv2.morphologyEx(blanco.astype(np.uint8), cv2.MORPH_CLOSE, L.disk(r)), int(0.02 * A * A))
    grupos = [(m & lam.sil, st) for m, st, _ in grupos if (m & ~dentro).sum() >= 0.25 * st[4]]
    grupos.sort(key=lambda t: -t[1][4])
    lam.mascaras["guantes"] = [m for m, _ in grupos[:2]]
    # lo que el guante pisa de la cabeza vuelve al cuerpo y se pinta DELANTE de la cabeza del rig
    todos = np.zeros_like(lam.sil)
    for m in lam.mascaras["guantes"]:
        todos |= cv2.dilate(m.astype(np.uint8), L.disk(r)).astype(bool) & lam.sil
    lam.mascaras["delante"] = todos & lam.mascaras["cabeza"]
    lam.mascaras["cabeza"] = lam.mascaras["cabeza"] & ~todos


def segmentar(lam: Lamina) -> Lamina:
    anclar_antifaz(lam)
    anclar_pies(lam)
    anclar_barbilla(lam)
    cortar_cabeza(lam)
    quitar_huecos(lam)
    segmentar_cola(lam)
    segmentar_guantes(lam)
    cab, cola = lam.mascaras["cabeza"], lam.mascaras["cola"]
    cuerpo = lam.sil & ~cab & ~cola
    # restos de la cabeza de la lámina que sobresalen de la del rig (una oreja más
    # alta, un mechón): sobre la barbilla y sin unirse a nada de debajo. Brazos y
    # manos alzados sí se unen (por el brazo) y se quedan.
    enc = _encima(lam.g.shape, np.array(lam.barbilla["punto"]), np.array(lam.antifaz["normal"]))
    abajo = cv2.dilate((cuerpo & ~enc).astype(np.uint8), L.disk(2)).astype(bool)
    restos = np.zeros_like(cuerpo)
    for m, _, _ in L.componentes(cuerpo & enc, 1):
        if not (m & abajo).any():
            restos |= m
    lam.mascaras["restos_cabeza"] = restos
    lam.mascaras["cuerpo"] = cuerpo & ~restos
    return lam


# ------------------------------------------------------------------ marcas (sección 3.2)
MARCAS = ["pie", "panza", "brazo_grosor", "brazo_largo", "cola_ancho", "cola_anillos"]
SOLO_FRONTAL = {"pie", "panza"}   # dependen de la vista: en 3/4 se reportan y no cuentan


def medir_marcas(lam: Lamina) -> dict:
    A = lam.A
    mk = lam.marcas
    mk["pie"] = round(float(np.mean(lam.pies["largo"])), 4)
    pz = panza(lam)
    mk["panza"] = round(pz / A, 4) if pz is not None else None
    gros, largos = [], []
    cuerpo = lam.mascaras["cuerpo"] & ~lam.mascaras["huecos"]
    for gl in lam.mascaras["guantes"]:
        b = brazo(lam, cuerpo, gl)
        if b:
            gros.append(b[0])
            largos.append(b[1])
    mk["brazo_grosor"] = round(float(np.median(gros)) / A, 4) if gros else None
    mk["brazo_largo"] = round(float(np.median(largos)) / A, 4) if largos else None
    mk["brazo_detalle"] = [[round(g_ / A, 3), round(l_ / A, 3)] for g_, l_ in zip(gros, largos)]
    dt = cv2.distanceTransform(lam.mascaras["cola"].astype(np.uint8), cv2.DIST_L2, 5)
    mk["cola_ancho"] = round(float(2 * dt.max()) / A, 4)
    return mk


def panza(lam: Lamina) -> float:
    """Ancho máximo del peto claro bajo la barbilla (fila a fila, el tramo que contiene su eje)."""
    g, A = lam.g, lam.A
    p, n = np.array(lam.barbilla["punto"]), np.array(lam.antifaz["normal"])
    q = np.round(p + n * 0.5 * A).astype(int)
    for m, _, _ in regiones(lam):
        if m[q[1], q[0]] and np.median(g[m]) > 195:
            reg = L.fill_holes(m & ~_encima(g.shape, p, n))
            r = max(3, int(0.04 * A))
            if any((cv2.dilate(gl.astype(np.uint8), L.disk(r)).astype(bool) & reg).any() for gl in lam.mascaras["guantes"]):
                return None          # las manos tapan el peto (codicia): no medible
            ys, xs = np.where(reg)
            best = 0
            for y in range(int(p[1] + 0.1 * A), int(ys.max())):
                fila = reg[y]
                d = np.diff(np.r_[0, fila.astype(np.int8), 0])
                a, b = np.where(d == 1)[0], np.where(d == -1)[0]
                w = [b[i] - a[i] for i in range(len(a))]
                best = max(best, max(w) if w else 0)
            return float(best)
    raise Rechazo("panza: no hay peto claro bajo la barbilla")


def brazo(lam: Lamina, cuerpo: np.ndarray, guante: np.ndarray):
    """(grosor, largo) en px del tubo que sale del guante: se recorre el esqueleto
    del cuerpo desde el puño; el grosor es la mediana de 2·dt en el tramo
    0,12–0,40 A, y el brazo termina donde el tubo se ensancha 1,6 veces (el
    torso). None si no hay tubo estable (brazo pegado al cuerpo)."""
    from collections import deque

    from skimage.morphology import skeletonize
    A = lam.A
    m = cuerpo & ~guante
    dt = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
    sk = skeletonize(m)
    gd = cv2.dilate(guante.astype(np.uint8), L.disk(max(3, int(0.05 * A)))).astype(bool)
    ini = np.argwhere(sk & gd)
    if not len(ini):
        return None
    H, W = m.shape
    dist = np.full((H, W), -1.0)
    cola = deque()
    for y, x in ini:
        dist[y, x] = 0
        cola.append((y, x))
    while cola:
        y, x = cola.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                yy, xx = y + dy, x + dx
                if (dy or dx) and 0 <= yy < H and 0 <= xx < W and sk[yy, xx] and dist[yy, xx] < 0:
                    dist[yy, xx] = dist[y, x] + (1.4142 if dy and dx else 1.0)
                    if dist[yy, xx] < 1.6 * A:
                        cola.append((yy, xx))
    sel = (dist >= 0.12 * A) & (dist <= 0.40 * A)
    if sel.sum() < 0.1 * A:
        return None
    w = 2 * dt[sel]
    grosor = float(np.median(w))
    if np.percentile(w, 90) > 1.5 * np.percentile(w, 10):
        return None
    # fin del brazo: primera distancia (por tramos de 0,02 A) con tubo 1,6 veces más ancho
    largo = None
    for d0 in np.arange(0.12 * A, 1.6 * A, 0.02 * A):
        t = (dist >= d0) & (dist < d0 + 0.02 * A)
        if t.any() and np.median(2 * dt[t]) > 1.6 * grosor:
            largo = float(d0)
            break
    return (grosor, largo) if largo is not None else None


# ------------------------------------------------------------------ trazo (R1: tinta copiada)
TINTA_LUM = 60
TINTA_DIST_U = 3.7        # u (6 px de la rejilla ×4 de la madre)
BANDA_CABEZA_U = 12.0
TONO_SIGMA = 6
TONO_UMBRAL = 0.08
PAPEL = 251.0
UMBRALES_31 = {"iou_min": 0.98, "iou_duro": 0.95, "tinta_min": 0.97, "area_tinta": (0.97, 1.03),
               "tono_error_medio_max": 0.030, "tono_superficie_max": 0.05}


def cal_de(lam: Lamina) -> dict:
    """px → u: el antifaz mide A_RIG, origen en el punto medio de los pies a ras de suelo."""
    return {"xc": lam.pies["x"], "suelo": lam.pies["suelo"], "s": lam.A / A_RIG}


def tono_region(g, m) -> int:
    """Índice de TADEO_TONE del tono plano de una región (su mediana)."""
    f = (1 - float(np.median(g[m])) / PAPEL) / L.RECTA
    return int(L.cuantiza(np.array([f]))[0])


def pieza(lam: Lamina, zona: np.ndarray, cal: dict, con_tinta=True, zona_tinta=None) -> dict:
    """Relleno por tonos planos (una capa por tono: las regiones de la lámina que
    separa su propia tinta, ensanchadas por debajo de la línea) + tinta copiada
    como isolínea subpíxel, todo en u."""
    g = lam.g
    r = max(2, int(round(0.02 * lam.A)))
    capas = {}
    for m, _, _ in L.componentes(zona & ~lam.ink, 30):
        t = tono_region(g, m)
        capas.setdefault(t, np.zeros_like(zona))
        capas[t] |= m
    base_t = max(capas, key=lambda t: capas[t].sum()) if capas else 3
    rellenos = [{"tono": L.TN[base_t], "caminos": L.poly_ccomp(cal, zona, eps=0.6, suav=1.0)}]
    for t in sorted(capas, key=lambda t: -capas[t].sum()):
        if t == base_t:
            continue
        m = cv2.dilate(capas[t].astype(np.uint8), L.disk(r)).astype(bool) & zona
        rellenos.append({"tono": L.TN[t], "caminos": L.poly_ccomp(cal, m, eps=0.6, suav=1.0)})
    out = {"rellenos": rellenos}
    if con_tinta:
        out["tinta"] = L.poly_iso(cal, g, zona if zona_tinta is None else zona_tinta)
    return out


def tapon(lam: Lamina) -> np.ndarray:
    """Pelaje bajo la barbilla que cierra el cuello cuando el rig mueve la cabeza:
    la franja de la cabeza de la lámina hasta 0,15 A sobre la línea de corte, en
    las columnas donde el cuerpo sigue justo debajo. Sin tinta."""
    A, sh = lam.A, lam.g.shape
    p, n = np.array(lam.barbilla["punto"]), np.array(lam.antifaz["normal"])
    banda = ~_encima(sh, p - n * 0.15 * A, n) & _encima(sh, p + n * 3, n)
    debajo = lam.mascaras["cuerpo"] & ~_encima(sh, p, n) & _encima(sh, p + n * 0.05 * A, n)
    base = lam.mascaras["cabeza"] & banda & debajo.any(0)[None, :]
    # Bolsas: donde la cabeza de la lámina era más ancha que la del rig y un brazo
    # alzado la encierra (asombro, triunfo), quedaría papel entre mejilla, hombro y
    # brazo. Se cierran con el mismo pelaje sin tinta, detrás del cuerpo. Solo
    # dentro de lo que era cabeza de la lámina (nunca un hueco brazo-torso) y
    # pequeñas (≤ 0,02 A²): una bolsa grande sería un fallo de la lámina, no un cierre.
    cubre = (lam.mascaras["cuerpo"] | lam.mascaras["cola"] | lam.mascaras["delante"] | base
             | plantilla_cabeza(lam))
    bolsa = ~cubre & L.fill_holes(cubre)
    era_cabeza = cv2.dilate(lam.mascaras["cabeza"].astype(np.uint8), L.disk(max(2, int(0.02 * A)))).astype(bool)
    bolsas = np.zeros_like(bolsa)
    for m, st, _ in L.componentes(bolsa, 1):
        # la bolsa tiene que ser casi toda de la cabeza de la lámina (su borde cae en la tinta)
        if st[4] <= 0.02 * A * A and (m & lam.mascaras["cabeza"]).sum() >= 0.5 * st[4] and (m & ~era_cabeza).sum() == 0:
            bolsas |= m
    lam.mascaras["bolsas"] = bolsas
    return base | cv2.dilate(bolsas.astype(np.uint8), L.disk(3)).astype(bool)


_MADRE_RIG = {}


def antifaz_madre_rig() -> dict:
    """Centro del antifaz de la madre en unidades del RIG (x = 0 en la nariz, como
    traza.js) y su eje, medidos con el mismo código que en las láminas."""
    if not _MADRE_RIG:
        import kx_trazo as KT
        md = madre()
        anclar_antifaz(md)
        cal_rig = KT.calibrar(md.g, KT.silueta(md.g))
        _MADRE_RIG.update({"centro_u": L.r1(L.to_u(cal_rig, [md.antifaz["centro"]]))[0],
                           "eje": round(-md.antifaz["angulo"], 2)})
    return _MADRE_RIG


def trazar(lam: Lamina) -> dict:
    cal = cal_de(lam)
    delante = lam.mascaras["delante"]
    # las piezas de DETRÁS (cola, tapón) se ensanchan 2 px por debajo de la de delante:
    # sin solape, el borde simplificado de dos polígonos vecinos deja rendijas de 1 px
    detras = lambda m: cv2.dilate(m.astype(np.uint8), L.disk(2)).astype(bool) & (lam.sil | lam.mascaras["cabeza"])  # noqa: E731
    t = {
        "cola": pieza(lam, detras(lam.mascaras["cola"]), cal, zona_tinta=lam.mascaras["cola"]),
        "cuerpo": pieza(lam, lam.mascaras["cuerpo"] & ~delante, cal),
        "tapon": pieza(lam, detras(tapon(lam)), cal, con_tinta=False),
        "delante": pieza(lam, delante, cal) if delante.any() else None,
    }
    # Cierre sobre lo YA TRAZADO: la simplificación del polígono del cuerpo puede
    # perder una astilla en la unión con la mejilla y dejar una bolsa que en las
    # máscaras no existe. Las bolsas pequeñas junto a lo que era la cabeza de la
    # lámina entran en el tapón (pelaje sin tinta, detrás del cuerpo).
    cub = cobertura(t, cal, lam.g.shape) | plantilla_cabeza(lam)
    cerca = cv2.dilate(lam.mascaras["cabeza"].astype(np.uint8), L.disk(max(3, int(0.03 * lam.A)))).astype(bool)
    extra = np.zeros_like(cub)
    for m, st, _ in L.componentes(~cub & L.fill_holes(cub), 1):
        if st[4] <= 0.02 * lam.A ** 2 and (m & cerca).sum() >= 0.5 * st[4]:
            extra |= m
    if extra.any():
        lam.mascaras["bolsas"] = lam.mascaras.get("bolsas", np.zeros_like(extra)) | extra
        zona = detras(tapon(lam)) | cv2.dilate(extra.astype(np.uint8), L.disk(4)).astype(bool)
        t["tapon"] = pieza(lam, zona, cal, con_tinta=False)
    af = lam.antifaz
    t["anclas"] = {
        "pies": [0.0, 0.0],
        "barbilla": L.r1(L.to_u(cal, [lam.barbilla["punto"]]))[0],
        "antifaz_centro": L.r1(L.to_u(cal, [af["centro"]]))[0],
        "eje_cabeza": round(-af["angulo"], 2),
        "A_px": round(lam.A, 2),
        "escala_u_por_px": round(1 / cal["s"], 5),
        "barbilla_propia_A": lam.barbilla["propia_A"],
    }
    # Dónde va la cabeza del rig: la cabeza trazada de la madre (traza.js) está en
    # su posición neutra; se lleva su antifaz al de la lámina y se gira lo que la
    # cabeza de la lámina está ladeada respecto a la de la madre. Escala 1: la
    # normalización ya dejó el antifaz de la lámina al tamaño del de la madre.
    # caja de la figura entera (con la cabeza de la lámina, del tamaño de la del rig) en u:
    # para encajar el vector en el mismo hueco que ocupaba un PNG (KorexMotion)
    ys, xs = np.where(lam.sil)
    esq = L.to_u(cal, np.array([[xs.min(), ys.max()], [xs.max(), ys.min()]], float))
    t["caja"] = [round(float(v), 1) for v in (*esq[0], *esq[1])]
    m = antifaz_madre_rig()
    t["cabeza_rig"] = {
        "desde": m["centro_u"],
        "hacia": t["anclas"]["antifaz_centro"],
        "giro": round(t["anclas"]["eje_cabeza"] - m["eje"], 2),
    }
    t["marcas"] = {k: lam.marcas.get(k) for k in MARCAS}
    return t


# ------------------------------------------------------------------ medición 3.1 (trazo contra su lámina)
def rasterizar(t: dict, cal: dict, shape) -> np.ndarray:
    """Dibuja la traza en la rejilla de la lámina (gris, fondo papel, even-odd,
    ×4 y reducida con área = antialias) en el orden del rig: cola, tapón,
    cuerpo, delante (el tapón va detrás: nunca tapa tinta del cuerpo)."""
    H, W = shape
    sub = 4
    img = np.full((H * sub, W * sub), int(PAPEL), np.uint8)

    def poly(caminos):
        return [np.round(L.to_px(cal, np.array(c, float)) * sub).astype(np.int32) for c in caminos if len(c) >= 3]

    for clave in ("cola", "tapon", "cuerpo", "delante"):
        pz = t.get(clave)
        if not pz:
            continue
        for capa in pz["rellenos"]:
            ps = poly(capa["caminos"])
            if ps:
                cv2.fillPoly(img, ps, int(round(PAPEL * (1 - L.RECTA * L.TONOS[capa["tono"]]))))
        ps = poly(pz.get("tinta", []))
        if ps:
            cv2.fillPoly(img, ps, 17)
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)


def cobertura(t: dict, cal: dict, shape) -> np.ndarray:
    """Lo que la traza cubre (cualquier relleno o tinta), sin mirar el tono: así el
    blanco de un guante no cuenta como hueco."""
    H, W = shape
    sub = 4
    img = np.zeros((H * sub, W * sub), np.uint8)
    for clave in ("cola", "tapon", "cuerpo", "delante"):
        pz = t.get(clave)
        if not pz:
            continue
        for caminos in [c["caminos"] for c in pz["rellenos"]] + [pz.get("tinta", [])]:
            ps = [np.round(L.to_px(cal, np.array(c, float)) * sub).astype(np.int32) for c in caminos if len(c) >= 3]
            if ps:
                cv2.fillPoly(img, ps, 255)
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA) > 127


def medir_31(lam: Lamina, t: dict, render: np.ndarray | None = None) -> dict:
    """Sección 3.1 del diseño, fuera de la cabeza de la lámina y de una banda de 12 u
    a su alrededor (la cabeza la pone el rig: no se compara aquí). `render`: la
    figura ya dibujada por el rig en la rejilla de la lámina; si no, se rasteriza aquí."""
    cal = cal_de(lam)
    r = rasterizar(t, cal, lam.g.shape) if render is None else render
    s = cal["s"]
    zona = ~cv2.dilate(lam.mascaras["cabeza"].astype(np.uint8), L.disk(int(round(BANDA_CABEZA_U * s)))).astype(bool)
    # la cabeza se tapa en las dos imágenes antes de buscar el papel exterior: si no,
    # el relleno desde las esquinas entra por el cuello del trazo hasta el peto claro.
    # Los huecos entre brazo y torso cuentan igual en las dos (papel encerrado).
    cab = lam.mascaras["cabeza"] | lam.mascaras["restos_cabeza"]
    zona &= ~lam.mascaras["restos_cabeza"]
    gl, gr = lam.g.copy(), r.copy()
    gl[cab] = 0
    gr[cab] = 0
    sil_l = silueta(gl) & zona
    sil_r = silueta(gr) & zona
    iou = float((sil_l & sil_r).sum() / max(1, (sil_l | sil_r).sum()))
    il = (lam.g < TINTA_LUM) & sil_l
    ir = (r < TINTA_LUM) & sil_r
    dpx = TINTA_DIST_U * s
    dr = cv2.distanceTransform((~ir).astype(np.uint8), cv2.DIST_L2, 5)
    dl = cv2.distanceTransform((~il).astype(np.uint8), cv2.DIST_L2, 5)
    l_en_t = float(1 - (il & (dr > dpx)).sum() / max(1, il.sum()))
    t_en_l = float(1 - (ir & (dl > dpx)).sum() / max(1, ir.sum()))
    area = float(ir.sum() / max(1, il.sum()))

    def mapa(g, sil, i, papel=PAPEL):
        m = (sil & ~i).astype(float)
        num = cv2.GaussianBlur(g.astype(float) / papel * m, (0, 0), TONO_SIGMA)
        return num / np.maximum(cv2.GaussianBlur(m, (0, 0), TONO_SIGMA), 1e-6)

    reg = sil_l & sil_r & ~(il | ir)
    # la lámina, contra el papel del modelo de tonos (251); el trazo, contra el suyo:
    # 251 si lo rasteriza Python, el crema de PAPER si lo dibuja el rig (medido en el borde)
    papel_r = PAPEL if render is None else float(np.median(np.concatenate([r[0], r[-1], r[:, 0], r[:, -1]])))
    e = np.abs(mapa(lam.g, sil_l, il) - mapa(r, sil_r, ir, papel_r))
    u = UMBRALES_31
    res = {"iou": round(iou, 4), "tinta_lamina_en_trazo": round(l_en_t, 4), "tinta_trazo_en_lamina": round(t_en_l, 4),
           "area_tinta": round(area, 4), "tono_error_medio": round(float(e[reg].mean()), 4),
           "tono_superficie_mayor_008": round(float((e[reg] > TONO_UMBRAL).mean()), 4)}
    res["cumple"] = {
        "iou": res["iou"] >= u["iou_min"],
        "tinta_lamina_en_trazo": l_en_t >= u["tinta_min"],
        "tinta_trazo_en_lamina": t_en_l >= u["tinta_min"],
        "area_tinta": u["area_tinta"][0] <= area <= u["area_tinta"][1],
        "tono_error_medio": res["tono_error_medio"] <= u["tono_error_medio_max"],
        "tono_superficie": res["tono_superficie_mayor_008"] <= u["tono_superficie_max"],
    }
    lam.mascaras["_render"] = r
    return res


# ------------------------------------------------------------------ calibración (sección 4)
TOL_BASE, TOL_TOPE, TOL_FACTOR = 0.08, 0.15, 1.25
MARGEN_BUENO, EXCESO_MALO = 0.02, 0.05
ANILLOS = (5, 7)
MARCAS_CONTINUAS = ["pie", "panza", "brazo_grosor", "brazo_largo", "cola_ancho"]
# Decisión de Fabian (27 nov 2026): la 3.2 se aprueba SOLO con las marcas que la
# calibración dejó estables + los anillos. brazo_grosor, brazo_largo y cola_ancho se
# siguen midiendo y reportando, pero no deciden (dependen de la pose o no tienen referencia).
DECIDEN = ("pie", "panza")
MALO_NATURAL = ROOT / "assets" / "kx_cast" / "tadeo" / "_hojas" / "Cartoon_character_pointing_forward_202608040458.jpeg"


def desviaciones(mk: dict, ref: dict, vista_3_4=False) -> dict:
    d = {}
    for k in MARCAS_CONTINUAS:
        if vista_3_4 and k in SOLO_FRONTAL:
            continue
        if not ref.get(k):
            continue                      # sin referencia en la madre: la marca no entra
        if mk.get(k) is None:
            d[k] = None
        else:
            d[k] = round((mk[k] - ref[k]) / ref[k], 4)
    return d


def tolerancias(buenos: dict) -> dict:
    tol = {}
    for k in MARCAS_CONTINUAS:
        v = [abs(d[k]) for d in buenos.values() if d.get(k) is not None]
        tol[k] = round(min(TOL_TOPE, max(TOL_BASE, TOL_FACTOR * max(v))) if v else TOL_BASE, 4)
        tol[k + "_sin_tope"] = round(max(TOL_BASE, TOL_FACTOR * max(v)), 4) if v else None
    return tol


def veredicto(d: dict, anillos, tol: dict) -> dict:
    """Paso de una lámina: todas sus marcas dentro de tolerancia. Una marca no medible
    (None) no pasa: se lista aparte, nunca cuenta como «dentro»."""
    d = {k: v for k, v in d.items() if k in DECIDEN}
    fuera = {k: v for k, v in d.items() if v is not None and abs(v) > tol[k]}
    no_medible = [k for k, v in d.items() if v is None]
    an_ok = anillos is not None and ANILLOS[0] <= anillos <= ANILLOS[1]
    if not d:                       # 3/4: ninguna marca que decide se puede medir → no pasa
        no_medible = ["sin marcas que decidan en esta vista"]
    return {"fuera": fuera, "no_medible": no_medible, "anillos_ok": an_ok,
            "pasa": not fuera and not no_medible and an_ok}


def _pegar_cabeza(base: np.ndarray, fuente: np.ndarray, cab: np.ndarray) -> np.ndarray:
    out = base.copy()
    out[cab] = fuente[cab]
    return out


def fabricar_malos(lam: Lamina) -> dict:
    """Los malos fabricados de la sección 4, a partir de una lámina buena (gris ×ESCALA).
    Cada uno es una transformación OpenCV registrada aquí mismo."""
    g = lam.g
    H, W = g.shape
    cab = cv2.dilate(lam.mascaras["cabeza"].astype(np.uint8), L.disk(3)).astype(bool)
    c = np.array(lam.antifaz["centro"])
    papel = np.full_like(g, 251)
    malos = {}
    # 1. cabeza ×1,3 alrededor del centro del antifaz
    M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), 0, 1.3)
    gc = cv2.warpAffine(g, M, (W, H), borderValue=251)
    cc = cv2.warpAffine(cab.astype(np.uint8), M, (W, H), flags=cv2.INTER_NEAREST).astype(bool)
    malos["cabeza_x1.3"] = _pegar_cabeza(np.where(cab, papel, g), gc, cc)
    # 2. cuerpo estirado ×1,25 en horizontal, cabeza intacta en su sitio
    x0 = float(lam.pies["x"])
    M = np.float32([[1.25, 0, x0 * (1 - 1.25)], [0, 1, 0]])
    cuerpo = cv2.warpAffine(np.where(cab, papel, g), M, (W, H), borderValue=251)
    malos["cuerpo_ancho_x1.25"] = _pegar_cabeza(cuerpo, g, cab)
    # 3. cuerpo aplastado ×0,8 en vertical (desde el suelo), cabeza bajada con él
    s0 = float(lam.pies["suelo"])
    M = np.float32([[1, 0, 0], [0, 0.8, s0 * (1 - 0.8)]])
    cuerpo = cv2.warpAffine(np.where(cab, papel, g), M, (W, H), borderValue=251)
    yb = float(lam.barbilla["punto"][1])
    dy = (s0 - (s0 - yb) * 0.8) - yb
    Mh = np.float32([[1, 0, 0], [0, 1, dy]])
    gh = cv2.warpAffine(g, Mh, (W, H), borderValue=251)
    ch = cv2.warpAffine(cab.astype(np.uint8), Mh, (W, H), flags=cv2.INTER_NEAREST).astype(bool)
    malos["cuerpo_bajo_x0.8"] = _pegar_cabeza(cuerpo, gh, ch)
    # 4. brazos adelgazados: NO fabricado (ver informe). Recortar un tubo de goma
    #    redibujando su tinta exige un editor de la lámina que no existe; se declara.
    return malos


def calibrar(resultados: dict, ref: dict, lam_base: Lamina) -> dict:
    """resultados: {nombre: marcas}. Devuelve tolerancias, desviaciones y la regla de separación."""
    buenos = {n: desviaciones(resultados[n], ref) for n in POSES if n in resultados}
    vista = {"pointing": desviaciones(resultados["pointing"], ref, vista_3_4=True)} if "pointing" in resultados else {}
    tol = tolerancias(buenos | vista)
    malos = {}
    for nombre, gris in fabricar_malos(lam_base).items():
        lm = cargar(nombre, gris=gris, escala=1)
        try:
            segmentar(lm)
            medir_marcas(lm)
            malos[nombre] = {"d": desviaciones(lm.marcas, ref), "anillos": lm.marcas.get("cola_anillos")}
        except Rechazo as e:
            malos[nombre] = {"rechazo": str(e)}
    if MALO_NATURAL.exists():
        lm = cargar("malo_natural", ruta=MALO_NATURAL, escala=1)
        try:
            segmentar(lm)
            medir_marcas(lm)
            malos["natural_pointing_forward"] = {"d": desviaciones(lm.marcas, ref), "anillos": lm.marcas.get("cola_anillos")}
        except Rechazo as e:
            malos["natural_pointing_forward"] = {"rechazo": str(e)}
    sep_buenos = {}
    for n, d in (buenos | vista).items():
        d = {k: v for k, v in d.items() if k in DECIDEN}
        if not d:
            continue
        margenes = {k: round(tol[k] - abs(v), 4) for k, v in d.items() if v is not None}
        sep_buenos[n] = {"margen_min": min(margenes.values()) if margenes else None,
                         "cumple": bool(margenes) and min(margenes.values()) >= MARGEN_BUENO
                         and all(v is not None for v in d.values())}
    sep_malos = {}
    for n, m in malos.items():
        if "rechazo" in m:
            sep_malos[n] = {"rechazada_antes": m["rechazo"], "cumple": True}
            continue
        exc = {k: round(abs(v) - tol[k], 4) for k, v in m["d"].items()
               if k in DECIDEN and v is not None and abs(v) > tol[k]}
        sep_malos[n] = {"marcas_fuera": len(exc), "peor_exceso": max(exc.values()) if exc else 0.0,
                        "cumple": len(exc) >= 2 and max(exc.values()) >= EXCESO_MALO}
    regla = all(v["cumple"] for v in sep_buenos.values()) and all(v["cumple"] for v in sep_malos.values())
    return {"referencia_madre": {k: ref.get(k) for k in MARCAS}, "tolerancias": tol, "buenos": buenos, "vista_3_4": vista,
            "malos": malos, "separacion": {"buenos": sep_buenos, "malos": sep_malos, "cumple": regla}}


# ------------------------------------------------------------------ pruebas del trazador (sección 6)
def invariancia(nombre="decidido") -> dict:
    """Prueba 2: la lámina desplazada, escalada ×0,7 – ×1,4 y girada ± 3° da el mismo
    cuerpo en u (área y centroide ± 1 %) y las mismas marcas (± 1 %)."""
    g0 = cv2.imread(str(FUENTES[nombre]), cv2.IMREAD_GRAYSCALE)
    H, W = g0.shape
    pad = 300
    lienzo = np.full((H + 2 * pad, W + 2 * pad), 251, np.uint8)
    lienzo[pad:pad + H, pad:pad + W] = g0

    def medir(gris, escala):
        lam = cargar(nombre, gris=gris, escala=escala)
        segmentar(lam)
        medir_marcas(lam)
        cal = cal_de(lam)
        ys, xs = np.where(lam.mascaras["cuerpo"])
        u = L.to_u(cal, np.stack([xs, ys], 1))
        return {"area_u2": float(len(xs) / cal["s"] ** 2), "centroide_u": u.mean(0).tolist(),
                "marcas": {k: lam.marcas.get(k) for k in MARCAS_CONTINUAS}}

    base = medir(lienzo, ESCALA)
    casos = {}
    Hc, Wc = lienzo.shape
    for nom, (dx, dy, esc, ang) in {"desplazada": (120, -80, 1.0, 0), "x0.7": (0, 0, 0.7, 0), "x1.4": (0, 0, 1.4, 0),
                                     "giro+3": (0, 0, 1.0, 3), "giro-3": (0, 0, 1.0, -3)}.items():
        M = cv2.getRotationMatrix2D((Wc / 2, Hc / 2), ang, 1.0)
        M[:, 2] += (dx, dy)
        g = cv2.warpAffine(lienzo, M, (Wc, Hc), flags=cv2.INTER_CUBIC, borderValue=251)
        try:
            r = medir(g, ESCALA * esc)
        except Rechazo as e:
            casos[nom] = {"rechazo": str(e), "cumple": False}
            continue
        da = r["area_u2"] / base["area_u2"] - 1
        dc = float(np.linalg.norm(np.array(r["centroide_u"]) - np.array(base["centroide_u"])) / np.sqrt(base["area_u2"]))
        dm = {k: (round(r["marcas"][k] / base["marcas"][k] - 1, 4) if r["marcas"][k] and base["marcas"][k] else None)
              for k in MARCAS_CONTINUAS}
        ok = abs(da) <= 0.01 and dc <= 0.01 and all(v is None or abs(v) <= 0.01 for v in dm.values())
        casos[nom] = {"area": round(da, 4), "centroide": round(dc, 4), "marcas": dm, "cumple": bool(ok)}
    return {"lamina": nombre, "casos": casos, "cumple": all(c["cumple"] for c in casos.values())}


def solido(lam: Lamina, t: dict) -> dict:
    """Prueba 5: cuerpo + cola + tapón con la cabeza (silueta de la cabeza de la madre
    colocada por el antifaz, la que pone el rig) en las dos escalas extremas de
    respiración (sy 1 ± 0,012 desde el suelo): cero huecos de fondo de 4 a 399 px."""
    cal = cal_de(lam)
    res = {}
    for sy in (0.988, 1.012):
        c2 = dict(cal)
        t2 = json.loads(json.dumps(t))
        for clave in ("cola", "tapon", "cuerpo", "delante"):
            pz = t2.get(clave)
            if not pz:
                continue
            for capa in pz["rellenos"]:
                capa["caminos"] = [[[x, y * sy] for x, y in c] for c in capa["caminos"]]
            pz["tinta"] = [[[x, y * sy] for x, y in c] for c in pz.get("tinta", [])]
        cub = cobertura(t2, c2, lam.g.shape)
        cab = plantilla_cabeza(lam)
        dy = (lam.pies["suelo"] - lam.barbilla["punto"][1]) * (sy - 1)   # la cabeza sigue a la barbilla
        cab = cv2.warpAffine(cab.astype(np.uint8), np.float32([[1, 0, 0], [0, 1, -dy]]), cab.shape[::-1],
                             flags=cv2.INTER_NEAREST).astype(bool)
        cub |= cab
        hueco = ~cub & L.fill_holes(cub)                  # sin cubrir y encerrado
        tam = [int(st[4]) for _, st, _ in L.componentes(hueco, 1)]
        res[f"sy_{sy}"] = {"huecos_4_399": sum(4 <= a <= 399 for a in tam)}
    res["cumple"] = all(v["huecos_4_399"] == 0 for v in res.values() if isinstance(v, dict))
    return res


# ------------------------------------------------------------------ salida
def escribir_rig(pasan: list) -> None:
    """Sección 7: en la biblioteca del rig solo entran las láminas que pasan todo.
    Copia la traza de evidencia tal cual (misma huella) y regenera el índice."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for viejo in OUT_DIR.glob("traza_*.js"):
        if viejo.stem.removeprefix("traza_") not in pasan:
            viejo.unlink()
    for n in pasan:
        (OUT_DIR / f"traza_{n}.js").write_bytes((EVID_OUT / "trazas" / f"traza_{n}.js").read_bytes())
    imports = "".join(f'import {{ TRAZA_{n.upper()} }} from "./traza_{n}.js";\n' for n in pasan)
    tabla = ", ".join(f"{n}: TRAZA_{n.upper()}" for n in pasan)
    (OUT_DIR / "index.js").write_text(
        "// GENERADO por kx_lamina.py: las láminas de pose que pasan el trazador (misión 0006).\n"
        "// Una pose que no está aquí se dibuja con el cuerpo por piezas de siempre.\n"
        f"{imports}\nexport const LAMINAS = {{ {tabla} }};\n", encoding="utf-8", newline="\n")


def huella_archivo(p: Path) -> str:
    return hashlib.sha1(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]


def escribir_traza(nombre: str, t: dict, carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    fuente = FUENTES.get(nombre)
    t = dict(t)
    if fuente:
        t["fuente"] = {"archivo": fuente.relative_to(ROOT).as_posix(), "sha1": huella_archivo(fuente)}
    ruta = carpeta / f"traza_{nombre}.js"
    cuerpo = json.dumps(t, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    ruta.write_text("// GENERADO por kx_lamina.py a partir de la lámina de pose. No editar a mano.\n"
                    "// Unidades del rig: suelo y = 0, x = 0 en el punto medio de los pies, antifaz = 379,5 u.\n"
                    f"export const TRAZA_{nombre.upper()} = {cuerpo};\n", encoding="utf-8", newline="\n")
    return ruta


# ------------------------------------------------------------------ evidencia
def _guardar(ruta: Path, img: np.ndarray, ancho_max: int = 2400) -> None:
    if img.shape[1] > ancho_max:
        f = ancho_max / img.shape[1]
        img = cv2.resize(img, (ancho_max, int(img.shape[0] * f)), interpolation=cv2.INTER_AREA)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(ruta), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])


def hoja_segmentacion(lams: list, motivos: dict, ruta: Path) -> None:
    """Una sola imagen: cada lámina con cabeza (rojo), cola (azul), guantes
    (verde), pies (naranja) y la línea de barbilla."""
    celdas = []
    for lam in lams:
        v = cv2.cvtColor(lam.g, cv2.COLOR_GRAY2RGB).astype(float)
        if lam.nombre in motivos:
            pass
        else:
            for clave, col in (("cabeza", (230, 40, 40)), ("cola", (40, 90, 240)), ("huecos", (250, 220, 0))):
                m = lam.mascaras.get(clave)
                if m is not None:
                    v[m] = 0.55 * v[m] + 0.45 * np.array(col)
            for m in lam.mascaras.get("guantes", []):
                v[m] = 0.5 * v[m] + 0.5 * np.array((40, 200, 60))
            for m in lam.pies.get("masks", []):
                v[m] = 0.5 * v[m] + 0.5 * np.array((250, 150, 20))
        v = v.astype(np.uint8)
        if lam.barbilla:
            p, d = np.array(lam.barbilla["punto"]), np.array(lam.antifaz["dir"])
            a, b = (p - d * lam.A).astype(int), (p + d * lam.A).astype(int)
            cv2.line(v, tuple(int(t) for t in a), tuple(int(t) for t in b), (200, 0, 200), max(2, int(lam.A / 120)))
        alto = 700
        v = cv2.resize(v, (int(v.shape[1] * alto / v.shape[0]), alto), interpolation=cv2.INTER_AREA)
        txt = lam.nombre + ("  RECHAZO: " + motivos[lam.nombre] if lam.nombre in motivos else "")
        cv2.putText(v, txt, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 0, 30), 2, cv2.LINE_AA)
        celdas.append(v)
    filas, ancho = [], 6
    for i in range(0, len(celdas), ancho):
        fila = celdas[i:i + ancho]
        w = sum(c.shape[1] for c in fila)
        fila += [np.full((700, max(0, celdas[0].shape[1] * ancho - w) or 1, 3), 255, np.uint8)]
        filas.append(np.hstack(fila))
    W = max(f.shape[1] for f in filas)
    filas = [np.hstack([f, np.full((700, W - f.shape[1], 3), 255, np.uint8)]) if f.shape[1] < W else f for f in filas]
    _guardar(ruta, cv2.cvtColor(np.vstack(filas), cv2.COLOR_RGB2BGR))


def cabeza_rig_pixeles(lam: Lamina):
    """La cabeza de la madre (gris y máscara) colocada por el antifaz: aproximación
    en píxeles de la cabeza del rig, solo para la hoja de contacto y la prueba 5."""
    md = madre()
    anclar_antifaz(md)
    cab_m, c_m, ang_m, A_m = _PLANTILLA["m"]
    af = lam.antifaz
    M = cv2.getRotationMatrix2D((float(c_m[0]), float(c_m[1])), -(af["angulo"] - ang_m), lam.A / A_m)
    M[:, 2] += np.array(af["centro"]) - np.array(c_m)
    H, W = lam.g.shape
    g = cv2.warpAffine(md.g, M, (W, H), flags=cv2.INTER_AREA, borderValue=251)
    m = cv2.warpAffine(cab_m.astype(np.uint8), M, (W, H), flags=cv2.INTER_NEAREST).astype(bool)
    return g, m


def hoja_contacto(filas: list, ruta: Path) -> None:
    """Por lámina: la lámina | su trazo con la cabeza de la madre puesta por el antifaz."""
    celdas = []
    for nombre, lam, ok in filas:
        r = lam.mascaras["_render"].copy()
        gh, mh = cabeza_rig_pixeles(lam)
        r[mh] = gh[mh]
        if lam.mascaras["delante"].any():            # las manos que pisan la cara, delante
            r[lam.mascaras["delante"]] = lam.mascaras["_render"][lam.mascaras["delante"]]
        par = np.hstack([lam.g, np.full((lam.g.shape[0], 20), 255, np.uint8), r])
        alto = 640
        par = cv2.resize(par, (int(par.shape[1] * alto / par.shape[0]), alto), interpolation=cv2.INTER_AREA)
        par = cv2.cvtColor(par, cv2.COLOR_GRAY2BGR)
        cv2.putText(par, f"{nombre}  {ok}", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 0, 180), 2, cv2.LINE_AA)
        celdas.append(par)
    W = max(c.shape[1] for c in celdas)
    celdas = [np.hstack([c, np.full((c.shape[0], W - c.shape[1], 3), 255, np.uint8)]) for c in celdas]
    filas_img = []
    for i in range(0, len(celdas), 4):
        f = celdas[i:i + 4]
        f += [np.full_like(celdas[0], 255)] * (4 - len(f))
        filas_img.append(np.hstack(f))
    _guardar(ruta, np.vstack(filas_img))


def regla_5(ruta: Path) -> dict:
    """Sección 5 de la especificación (figura única, fondo blanco, margen, sin color),
    con el mismo código que scripts/medir_lamina.py: una lámina no pasa sin ella."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import medir_lamina as ML
    m = ML.medir(ruta)
    return {"fallos": m["fallos"], "color_pct": m["color_pct"], "margen": m["margen"], "cumple": not m["fallos"]}


def procesar(nombres: list, debug=False) -> dict:
    """Traza, mide (3.1, 3.2, sólido) y calibra. Escribe las trazas CANDIDATAS en
    misiones/evidencia/0006/trazas/: ninguna entra en el rig hasta que pase todo."""
    lams, motivos, res = [], {}, {}
    for nom in nombres:
        lam = madre() if nom == "madre" else cargar(nom)
        try:
            segmentar(lam)
            medir_marcas(lam)
            t = trazar(lam)
            res[nom] = {"marcas": {k: lam.marcas.get(k) for k in MARCAS}, "anclas": t["anclas"],
                        "traza_31": medir_31(lam, t), "solido": solido(lam, t)}
            if nom != "madre":
                res[nom]["spec5"] = regla_5(FUENTES[nom])
                ruta = escribir_traza(nom, t, EVID_OUT / "trazas")
                res[nom]["traza"] = {"archivo": ruta.relative_to(ROOT).as_posix(), "sha1": huella_archivo(ruta)}
                res[nom]["fuente_sha1"] = huella_archivo(FUENTES[nom])
        except Rechazo as e:
            motivos[nom] = str(e)
            res[nom] = {"rechazo": str(e)}
        lams.append(lam)
    if debug:
        hoja_segmentacion(lams, motivos, EVID_OUT / "segmentacion.png")
    return {"res": res, "lams": {l_.nombre: l_ for l_ in lams}, "motivos": motivos}


def informe(todo: dict) -> dict:
    res, lams = todo["res"], todo["lams"]
    ref = dict(res["madre"]["marcas"])
    # De frente, la cola de la madre queda tapada por su guante derecho: mide 0,22 A
    # contra 0,36-0,47 en las láminas. No es una referencia: la marca queda fuera.
    ref["cola_ancho"] = None
    cal = calibrar({n: r["marcas"] for n, r in res.items() if "marcas" in r and n != "madre"}, ref, lams["decidido"])
    tol = cal["tolerancias"]
    por_lamina = {}
    for n in [*POSES, "pointing"]:
        r = res.get(n, {})
        if "rechazo" in r:
            por_lamina[n] = {"pasa": False, "motivo": r["rechazo"]}
            continue
        d = desviaciones(r["marcas"], ref, vista_3_4=n in VISTA_3_4)
        v = veredicto(d, r["marcas"].get("cola_anillos"), tol)
        c31 = r["traza_31"]["cumple"]
        por_lamina[n] = {"pasa_31": all(c31.values()), "fallos_31": [k for k, ok in c31.items() if not ok],
                         "pasa_32": v["pasa"], "marcas_fuera": v["fuera"], "no_medible": v["no_medible"],
                         "anillos_ok": v["anillos_ok"], "solido": r["solido"]["cumple"],
                         "spec5": r["spec5"]["fallos"],
                         "pasa": all(c31.values()) and v["pasa"] and r["solido"]["cumple"] and r["spec5"]["cumple"],
                         "marcas_informativas": {k: x for k, x in d.items() if k not in DECIDEN}}
    return {"huella_codigo": huella_codigo(), "umbrales_31": UMBRALES_31, "calibracion": cal,
            "por_lamina": por_lamina, "medidas": res}


CODIGO = ["kx_lamina.py", "kx_trazolib.py"]


def huella_codigo() -> str:
    """Si cambia el trazador, informe.json y las trazas están viejos (lo vigila el test de la CI)."""
    h = hashlib.sha1()
    for rel in CODIGO:
        h.update(rel.encode())
        h.update((ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def render_rig(pose: str, lam: Lamina) -> np.ndarray:
    """La pose dibujada por el rig real (Remotion, KxTadeoLaminaMolde) en la rejilla de su lámina."""
    import subprocess
    cal = cal_de(lam)
    H, W = lam.g.shape
    out = EVID_OUT / "rig" / f"rig_{pose}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    props = EVID_OUT / "rig" / f"_props_{pose}.json"
    props.write_text(json.dumps({"pose": pose, "xc": cal["xc"], "suelo": cal["suelo"], "s": cal["s"], "w": W, "h": H}),
                     encoding="utf-8")
    try:
        subprocess.run(["npx", "remotion", "still", "src/index.jsx", "KxTadeoLaminaMolde", str(out), f"--props={props}",
                        "--log=error"], cwd=ROOT / "motion_graphics", check=True, shell=True, timeout=600)
    finally:
        props.unlink(missing_ok=True)
    return cv2.cvtColor(cv2.imread(str(out)), cv2.COLOR_BGR2GRAY)


def anclaje_ok(r: dict) -> bool:
    """La cabeza del rig cae donde se calculó: antifaz a ≤ 1 % de A, misma escala ± 1 %, giro ± 0,5°."""
    return (r["antifaz_desvio_A"] <= 0.01 and abs(r["antifaz_A_rig_sobre_lamina"] - 1) <= 0.01
            and abs(r["antifaz_giro_rig_menos_lamina"]) <= 0.5)


def medir_rig() -> dict:
    """Las poses de laminas/index.js renderizadas por el rig: la 3.1 sobre el render
    real (cuerpo) y la cabeza del rig contra la de la madre colocada por el antifaz
    (IoU de silueta: comprueba que el anclaje del JSX es el que calculó Python)."""
    import re
    idx = (OUT_DIR / "index.js").read_text(encoding="utf-8")
    poses = re.findall(r"import \{ TRAZA_\w+ \} from \"\./traza_(\w+)\.js\"", idx)
    res, celdas = {}, []
    for pose in poses:
        lam = segmentar(cargar(pose))
        medir_marcas(lam)
        t = trazar(lam)
        r = render_rig(pose, lam)
        m31 = medir_31(lam, t, render=r)
        # cabeza: silueta del render dentro de la zona de la cabeza vs la cabeza de la madre puesta por el antifaz
        _, mh = cabeza_rig_pixeles(lam)
        zona = cv2.dilate(mh.astype(np.uint8), L.disk(int(0.08 * lam.A))).astype(bool)
        sil_r = silueta(r) & zona & ~lam.mascaras["cuerpo"] & ~lam.mascaras["delante"]
        cab_iou = float((sil_r & mh).sum() / max(1, (sil_r | mh).sum()))
        # el anclaje: el antifaz que dibuja el rig contra el que se calculó (en A)
        ar = cargar(pose, gris=r, escala=1)
        anclar_antifaz(ar)
        desvio = float(np.linalg.norm(np.array(ar.antifaz["centro"]) - np.array(lam.antifaz["centro"])) / lam.A)
        res[pose] = {"traza_31_rig": m31, "cabeza_iou": round(cab_iou, 4), "antifaz_desvio_A": round(desvio, 4),
                     "antifaz_A_rig_sobre_lamina": round(ar.A / lam.A, 4),
                     "antifaz_giro_rig_menos_lamina": round(ar.antifaz["angulo"] - lam.antifaz["angulo"], 2)}
        celdas.append(np.hstack([lam.g, np.full((lam.g.shape[0], 20), 255, np.uint8), r]))
        print(f"{pose:11s} rig: IoU {m31['iou']:.4f} tinta {m31['tinta_lamina_en_trazo']:.3f}/{m31['tinta_trazo_en_lamina']:.3f} "
              f"tono {m31['tono_error_medio']:.4f}/{100 * m31['tono_superficie_mayor_008']:.1f}% · cabeza IoU {cab_iou:.4f} · "
              f"antifaz desvío {desvio:.4f} A, escala {ar.A / lam.A:.4f}, giro {ar.antifaz['angulo'] - lam.antifaz['angulo']:+.2f}° · "
              f"{'OK' if anclaje_ok(res[pose]) and all(m31['cumple'].values()) else 'NO'}")
    if celdas:
        alto = 600
        celdas = [cv2.resize(c, (int(c.shape[1] * alto / c.shape[0]), alto), interpolation=cv2.INTER_AREA) for c in celdas]
        filas = [np.hstack(celdas[i:i + 3] + [np.full_like(celdas[0], 255)] * (3 - len(celdas[i:i + 3])))
                 for i in range(0, len(celdas), 3)]
        _guardar(EVID_OUT / "rig_contacto.png", np.vstack(filas))
    (EVID_OUT / "rig.json").write_text(json.dumps({"huella_codigo": huella_codigo(), "poses": res}, ensure_ascii=False,
                                                  indent=1) + "\n", encoding="utf-8")
    return res


def main(argv=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if "--invariancia" in argv:
        r = invariancia()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        (EVID_OUT / "invariancia.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return 0 if r["cumple"] else 1
    if "--rig" in argv:
        r = medir_rig()
        return 0 if all(all(v["traza_31_rig"]["cumple"].values()) and anclaje_ok(v) for v in r.values()) else 1
    if "--determinismo" in argv:
        a = procesar(["madre", "grito"])["res"]["grito"]["traza"]["sha1"]
        b = procesar(["madre", "grito"])["res"]["grito"]["traza"]["sha1"]
        print("traza_grito.js", a, b, "IDÉNTICAS" if a == b else "DISTINTAS")
        return 0 if a == b else 1
    pedidas = [a for a in argv if not a.startswith("--")]
    nombres = ["madre", *(pedidas or [*POSES, "pointing"])]
    if not pedidas:
        nombres = ["madre", *POSES, "pointing"]
    todo = procesar(nombres, debug="--debug" in argv)
    for n, r in todo["res"].items():
        if "rechazo" in r:
            print(f"{n:11s} RECHAZO: {r['rechazo']}")
            continue
        t = r["traza_31"]
        print(f"{n:11s} 3.1 IoU {t['iou']:.4f} tinta {t['tinta_lamina_en_trazo']:.3f}/{t['tinta_trazo_en_lamina']:.3f} "
              f"área {t['area_tinta']:.3f} tono {t['tono_error_medio']:.4f}/{100 * t['tono_superficie_mayor_008']:.1f}% "
              f"sólido {'OK' if r['solido']['cumple'] else 'NO'} · marcas {r['marcas']}")
    if pedidas:
        return 0
    inf = informe(todo)
    EVID_OUT.mkdir(parents=True, exist_ok=True)
    (EVID_OUT / "informe.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    pasan = [n for n in POSES if inf["por_lamina"][n].get("pasa")]
    escribir_rig(pasan)
    print("en el rig:", ", ".join(pasan))
    filas = [(n, todo["lams"][n], "PASA" if inf["por_lamina"][n].get("pasa") else "NO PASA")
             for n in [*POSES, "pointing"] if "rechazo" not in todo["res"][n]]
    hoja_contacto(filas, EVID_OUT / "contacto_trazos.png")
    cal = inf["calibracion"]
    print("tolerancias", cal["tolerancias"])
    print("separación", json.dumps(cal["separacion"], ensure_ascii=False))
    for n, v in inf["por_lamina"].items():
        print(f"  {n:11s} {'PASA' if v.get('pasa') else 'NO'}  {json.dumps({k: v[k] for k in v if k != 'solido'}, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
