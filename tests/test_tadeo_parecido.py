"""Parecido medible del rig de Tadeo con la hoja madre (Misión 0001, Fase 2).

Falla si el solape de silueta del neutro baja de 0,95 o si alguna marca se
desvía más de ±3 %; y también si parecido.json no corresponde al código
actual (huella de partes.jsx, poses.js, traza.js… distinta): la medición
vieja no vale como evidencia de un rig nuevo. Se regenera con
`py kx_trazo.py && py kx_parecido.py`.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import kx_parecido as P  # noqa: E402

RES = json.loads((P.EVID / "parecido.json").read_text(encoding="utf-8"))
MARCAS = ["cabeza_ancho_alto", "oreja_alto", "oreja_ancho", "ojos_distancia",
          "antifaz_ancho", "hocico_ancho", "panza_ancho"]


def test_medicion_al_dia_con_el_rig():
    assert RES["huella"] == P.huella(), "parecido.json es de otro rig: corre `py kx_parecido.py`"


def test_solape_de_silueta():
    assert RES["iou"] >= 0.95, f"IoU {RES['iou']} < 0,95"


@pytest.mark.parametrize("marca", MARCAS)
def test_marca_dentro_de_3_por_ciento(marca):
    m = RES["marcas"][marca]
    assert m["madre"] > 0 and m["rig"] > 0, marca
    assert abs(m["rig"] - m["madre"]) / m["madre"] <= 0.03, f"{marca}: {m}"


def test_evidencia_visual_existe():
    for f in ("parecido_lado_a_lado.png", "parecido_solape.png", "parecido_marcas.png", "rig_neutro.png"):
        assert (P.EVID / f).exists(), f
