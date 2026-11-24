"""Biblioteca del rig de Tadeo (Misión 0001, Fase 2, criterios 1 y 3).

La hoja de poses dibuja exactamente lo que exporta poses.js; los miembros
respetan 0,75×-1,35×; y una mano que rebasa ×1,25 (ACENTO) con el personaje
a ×1,12 (beat) sigue dentro de la zona segura.
"""
import json
import math
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import kx_tadeo  # noqa: E402

LIB = kx_tadeo.cargar_biblioteca()
CELDAS = json.loads((kx_tadeo.EVID / "hoja_celdas.json").read_text(encoding="utf-8"))
SAFE = (48, 288, 888, 1248)


def test_biblioteca_al_dia_con_poses_js():
    if not shutil.which("node"):
        pytest.skip("sin node: no se puede re-exportar poses.js")
    fresca = kx_tadeo.node_eval('import { bibliotecaJSON } from "./kx/tadeo/poses.js";'
                                "process.stdout.write(JSON.stringify(bibliotecaJSON()));")
    assert fresca == LIB, "biblioteca.json desactualizada: corre `py kx_tadeo.py --export`"


def test_tamano_de_la_biblioteca():
    assert len(LIB["poses"]) == 14
    assert len(LIB["expresiones"]) == 10
    assert len(LIB["miradas"]) == 4


def test_hoja_cubre_toda_la_biblioteca():
    assert CELDAS["poses"] == LIB["poses"]
    assert CELDAS["siluetas"] == LIB["poses"]
    assert CELDAS["expresiones"] == LIB["expresiones"]
    assert CELDAS["miradas"] == LIB["miradas"]
    rejilla = {(c["expr"], c["mirada"]) for c in CELDAS["cabezas"]}
    assert len(CELDAS["cabezas"]) == 40
    assert rejilla == {(e, m) for e in LIB["expresiones"] for m in LIB["miradas"]}
    assert (kx_tadeo.EVID / "hoja_de_poses.png").exists()


def test_defaults_validos():
    d = LIB["definiciones"]
    for pid, p in d["POSES"].items():
        assert p["expr"] in LIB["expresiones"], pid
        assert p["mirada"] in LIB["miradas"], pid
        for lado in ("brazoI", "brazoD"):
            assert p[lado]["guante"] in LIB["guantes"], (pid, lado)
            cmax = LIB["rig"]["brazo"]["curvaMax"]
            assert -cmax <= p[lado]["curva"] <= cmax, (pid, lado)
            assert p[lado]["capa"] in ("delante", "detras"), (pid, lado)


def _bezier_len(p0, p1, p2, n=400):
    pts = [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


@pytest.mark.parametrize("pose", LIB["poses"])
def test_largos_de_miembro(pose):
    rig = LIB["rig"]
    m = LIB["medidas"][pose]
    for lado, b in m["brazos"].items():
        r = _bezier_len(b["hombro"], b["control"], b["mano"]) / rig["brazo"]["largo"]
        assert rig["brazo"]["min"] <= r <= rig["brazo"]["max"], f"{pose} brazo {lado}: {r:.2f}×"
    for lado, pts in m["piernas"].items():
        r = _bezier_len(*pts) / rig["pierna"]["largo"]
        assert rig["brazo"]["min"] <= r <= rig["brazo"]["max"], f"{pose} pierna {lado}: {r:.2f}×"


@pytest.mark.parametrize("pose", LIB["poses"])
def test_manos_acento_caben_en_zona_segura(pose):
    """Mano rebasando ×1,25 desde el hombro + radio del guante, con el
    personaje a ×1,12 (beat), en la posición por defecto."""
    rig = LIB["rig"]
    s = rig["pantalla"]["alto"] / rig["alto"] * rig["beatEscala"]
    X, Y = rig["pantalla"]["x"], rig["pantalla"]["y"]
    for lado, b in LIB["medidas"][pose]["brazos"].items():
        hx, hy = b["hombro"]
        mx, my = b["mano"]
        ox, oy = hx + (mx - hx) * rig["acentoRebase"], hy + (my - hy) * rig["acentoRebase"]
        r = rig["guante"]["radio"]
        x0, x1 = X + (ox - r) * s, X + (ox + r) * s
        y0, y1 = Y - (oy + r) * s, Y - (oy - r) * s
        assert SAFE[0] <= x0 and x1 <= SAFE[2] and SAFE[1] <= y0 and y1 <= SAFE[3], \
            f"{pose} mano {lado} sale de la zona segura: x {x0:.0f}-{x1:.0f}, y {y0:.0f}-{y1:.0f}"


@pytest.mark.parametrize("pose", LIB["poses"])
def test_caja_dentro_de_zona_segura(pose):
    c = kx_tadeo.caja_px(pose, LIB, LIB["rig"]["beatEscala"])
    assert SAFE[0] <= c["x"] and c["x"] + c["w"] <= SAFE[2], (pose, c)
    assert SAFE[1] <= c["y"] and c["y"] + c["h"] <= SAFE[3], (pose, c)


def test_sin_deuda_ni_hex_en_tadeo():
    """Criterio 3: nada en tadeo/ importa DEBT ni escribe un color propio."""
    for f in kx_tadeo.TADEO.glob("*.js*"):
        if f.suffix == ".json":
            continue
        txt = f.read_text(encoding="utf-8")
        assert "DEBT" not in txt, f.name
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", txt), f"hex en {f.name}"


def test_termino_fuera_de_biblioteca_falla():
    assert kx_tadeo.pose_de_termino("*tadeo/estafado", LIB) == "estafado"
    assert kx_tadeo.pose_de_termino("tadeo/grito", LIB) == "grito"
    with pytest.raises(KeyError):
        kx_tadeo.pose_de_termino("tadeo/bailando", LIB)
    with pytest.raises(KeyError):
        kx_tadeo.pose_de_termino("skick/grito", LIB)
