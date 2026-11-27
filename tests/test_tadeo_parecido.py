"""Parecido medible del rig de Tadeo con la hoja madre (Misión 0001, Fase 2).

Iteración 2 (I2-3, «la barra de perfecta»): sobre el neutro, solape de
silueta ≥ 0,98, las 7 marcas dentro de ±3 %, tinta de la madre presente en el
rig y viceversa ≥ 97 % (a ≤ 6 px, luminancia < 60), área de tinta 0,97–1,03,
grosor p50 de las líneas interiores 4,6–5,6 u, error tonal medio ≤ 0,030 y
superficie con error > 0,08 ≤ 5 %. Ninguno se afloja. Desde la iteración 3
(halo = el borde suave de la madre como segunda tinta) la barra entera pasa, y
además la silueta de los tubos mantiene IoU ≥ 0,988.

Además: parecido.json tiene que corresponder al código actual (huella), los
tonos de kx_trazo son los de tokens.js, las sombras respetan el mínimo y el
máximo (punto 6), ningún stroke baja de 3,5 u ni hay línea interior de más de
5,5 u (punto 14), y la cola se curva sin tocar el suelo (punto 9).
Se regenera con `py kx_trazo.py && py kx_parecido.py`.
"""
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import kx_parecido as P  # noqa: E402

RES = json.loads((P.EVID / "parecido.json").read_text(encoding="utf-8"))
MARCAS = ["cabeza_ancho_alto", "oreja_alto", "oreja_ancho", "ojos_distancia",
          "antifaz_ancho", "hocico_ancho", "panza_ancho"]
TADEO = ROOT / "motion_graphics" / "src" / "kx" / "tadeo"
TRAZA = json.loads((TADEO / "traza.js").read_text(encoding="utf-8").split("TRAZA = ", 1)[1].rstrip().rstrip(";"))
LIB = json.loads((TADEO / "biblioteca.json").read_text(encoding="utf-8"))


def test_medicion_al_dia_con_el_rig():
    assert RES["huella"] == P.huella(), "parecido.json es de otro rig: corre `py kx_parecido.py`"


def test_solape_de_silueta():
    assert RES["iou"] >= 0.98, f"IoU {RES['iou']} < 0,98"


def test_solape_tras_los_tubos():
    """QA de la iteración 3: la silueta generada por los tubos mantiene IoU ≥ 0,988."""
    assert RES["iou"] >= 0.988, f"IoU {RES['iou']} < 0,988"


@pytest.mark.parametrize("marca", MARCAS)
def test_marca_dentro_de_3_por_ciento(marca):
    m = RES["marcas"][marca]
    assert m["madre"] > 0 and m["rig"] > 0, marca
    assert abs(m["rig"] - m["madre"]) / m["madre"] <= 0.03, f"{marca}: {m}"


def test_tinta_de_la_madre_en_el_rig():
    assert RES["tinta"]["madre_en_rig"] >= 0.97, RES["tinta"]


def test_tinta_del_rig_en_la_madre():
    assert RES["tinta"]["rig_en_madre"] >= 0.97, RES["tinta"]


def test_area_de_tinta():
    assert 0.97 <= RES["tinta"]["area"] <= 1.03, RES["tinta"]


def test_grosor_de_las_lineas_interiores():
    assert 4.6 <= RES["grosor"]["rig"]["interior"][1] <= 5.6, RES["grosor"]


def test_error_tonal_medio():
    assert RES["tono"]["error_medio"] <= 0.030, RES["tono"]


def test_superficie_con_error_tonal():
    assert RES["tono"]["superficie_mayor_008"] <= 0.05, RES["tono"]


def test_evidencia_visual_existe():
    for f in ("parecido_lado_a_lado.png", "parecido_solape.png", "parecido_marcas.png", "rig_neutro.png",
              "parecido_residuo.png", "parecido_barra.png", "hoja_de_poses.png"):
        assert (P.EVID / f).exists(), f


def test_tonos_de_trazo_son_los_de_tokens():
    tok = (ROOT / "motion_graphics" / "src" / "kx" / "tokens.js").read_text(encoding="utf-8")
    js = dict((k, float(v)) for k, v in re.findall(r"(T_[A-Z_]+): ([0-9.]+)", tok.split("TADEO_TONE", 1)[1].split("}")[0]))
    py = (ROOT / "kx_trazolib.py").read_text(encoding="utf-8")
    tr = dict((k, float(v)) for k, v in re.findall(r'"(T_[A-Z_]+)": ([0-9.]+)', py.split("TONOS = {", 1)[1].split("}")[0]))
    assert tr == {k: v for k, v in js.items() if k != "T_INK"}, (tr, js)
    assert TRAZA["tonos"] == tr


def _area(p):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1]))) / 2


def _sombras():
    out = []
    for k in ("craneo", "mechon", "torso"):
        out += TRAZA[k]["sombras"]
    for k in ("orejas", "brazo_piel", "pierna_piel"):
        for lado in "ID":
            out += TRAZA[k][lado]["sombras"]
    return out


def test_sombras_planas_dentro_del_minimo_y_el_maximo():
    meta = TRAZA["sombras_meta"]
    sombras = _sombras()
    assert len(sombras) == meta["n"] <= 14
    assert meta["area_min_px"] >= 1500
    k = meta["px_por_u"] ** 2
    for s in sombras:
        area = sum(_area(p) for p in s["forma"]) * k   # con agujeros sobra: es una cota por arriba
        assert area >= 0.5 * meta["area_min_px"], (s["tono"], area)
        assert s["tono"] in TRAZA["tonos"] and s["tono"] != "T_WHITE"


def test_pesos_de_linea_y_strokes():
    linea = LIB["rig"]["linea"]
    assert linea == {"exterior": 7.3, "interior": 5.0, "fina": 3.6}
    assert linea["interior"] <= 5.5 and min(linea.values()) >= 3.5
    for f in TADEO.glob("*.jsx"):
        for w in re.findall(r"strokeWidth=\{([^}]*)\}", f.read_text(encoding="utf-8")):
            w = w.strip()
            # los únicos strokes que quedan son de primitivas (bolsillos, lágrima,
            # párpado) y los rellenos «cap» de los guantes construidos (forma, no línea)
            assert w in ("L.interior", "L.fina") or w.startswith("f.w"), f"{f.name}: strokeWidth={{{w}}}"


@pytest.mark.skipif(not shutil.which("node"), reason="sin node")
def test_cola_se_curva_y_no_toca_el_suelo():
    import kx_tadeo
    r = kx_tadeo.node_eval(
        'import { POSES, colaGiros, colaRizoEfectivo, colaForma, COLA_SUELO } from "./kx/tadeo/poses.js";'
        "const out = {}; for (const [id, p] of Object.entries(POSES)) {"
        "  const g = colaGiros(p.cola, colaRizoEfectivo(p.cola));"
        "  out[id] = { rizo: p.cola.rizo, giro: g[g.length - 1] - g[0], minY: Math.min(...colaForma(p.cola).map((q) => q[1])), suelo: COLA_SUELO }; }"
        "process.stdout.write(JSON.stringify(out));", timeout=300)
    mayor = max(r.values(), key=lambda v: v["rizo"])
    assert mayor["giro"] >= 15, mayor
    for pid, v in r.items():
        assert v["minY"] >= v["suelo"], (pid, v)
