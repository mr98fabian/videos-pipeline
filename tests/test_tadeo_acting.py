"""Reglas de acting de Tadeo (Misión 0001, Fase 2, criterio 4), medidas sobre
las funciones puras de acting.js — las mismas que dibuja Tadeo.jsx — sin render.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import kx_tadeo  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="sin node")

LINEA = kx_tadeo.LINEA
DUR = kx_tadeo.DURACION

SCRIPT = """
import * as A from "./kx/tadeo/acting.js";
import { POSES } from "./kx/tadeo/poses.js";
const LINEA = %(linea)s, DUR = %(dur)d;
const out = {};

// 1. orden de arranque: primer frame con progreso > 0 por capa (t0 = 100)
const t0 = 100;
out.arranque = {};
for (const c of A.CAPAS) {
  let f = t0 - 5;
  while (A.estado({ desde: "neutro", hacia: "triunfo", t0, frame: f, miradaHacia: "der", conIdle: false, agenda: [] }).progreso[c] <= 0) f++;
  out.arranque[c] = f - t0;
}

// 2. parpadeo
out.curva = Array.from({ length: 61 }, (_, i) => A.curvaParpadeo(i / 10));
out.parpadeo = A.PARPADEO;
out.agenda = A.agendaLinea(LINEA, DUR, 3);
out.agendaRisa = A.agendaParpadeo({ exprInicial: "sonrisa", cambios: [{ t0: 60, expr: "risa" }], duracion: 400, semilla: 1 });
out.agendaGrito = A.agendaParpadeo({ exprInicial: "sonrisa", cambios: [{ t0: 60, expr: "grito" }], duracion: 400, semilla: 1 });

// 5. squash en todo frame: la línea de prueba y cada transición entre poses
out.squash = [];
const ids = Object.keys(POSES);
for (let f = 0; f < DUR; f++) {
  const e = A.estadoLinea(LINEA, f, { semilla: 3, duracion: DUR });
  out.squash.push([e.torso.sx * e.torso.sy, e.cabeza.sx * e.cabeza.sy, e.torso.sy]);
}
for (let i = 0; i < ids.length; i++) for (const beat of [false, true]) {
  const hacia = ids[(i + 1) %% ids.length];
  for (let f = 0; f < 90; f++) {
    const e = A.estado({ desde: ids[i], hacia, t0: 10, frame: f, beat, semilla: i });
    out.squash.push([e.torso.sx * e.torso.sy, e.cabeza.sx * e.cabeza.sy, e.torso.sy]);
  }
}

// 4. holds: estado sin idle ni parpadeo, cuadro a cuadro
const plano = (e) => [e.torso.inclina, e.torso.sy, e.cabeza.inclina, e.cabeza.gira, e.cabeza.dy,
  ...e.brazoI.mano, e.brazoI.curva, ...e.brazoD.mano, e.brazoD.curva, e.cola.rizo, e.cola.alza,
  e.orejas.i, e.orejas.d, e.mirada.x, e.mirada.y, e.mechon];
out.holdSerie = [];
for (let f = 0; f < DUR; f++) out.holdSerie.push(plano(A.estadoLinea(LINEA, f, { conIdle: false, duracion: DUR, agenda: [] })));
out.validaOk = A.validarLinea(LINEA);
try { A.validarLinea([{ pose: "neutro", t0: 0 }, { pose: "grito", t0: 30 }, { pose: "triunfo", t0: 45 }]); out.rechaza = false; }
catch (err) { out.rechaza = String(err.message); }
out.asentamiento = A.asentamiento();
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def M():
    return kx_tadeo.node_eval(SCRIPT % {"linea": json.dumps(LINEA), "dur": DUR}, timeout=120)


def test_la_mirada_lidera(M):
    a = M["arranque"]
    assert a["pupilas"] < a["cabeza"] < a["torso"] < a["brazos"] < a["cola"], a
    assert a["pupilas"] <= a["cara"] < a["cabeza"]
    assert a["orejas"] < a["cola"] < a["mechon"]


def test_parpadeo_42_58(M):
    p = M["parpadeo"]
    assert p["dur"] == 6
    assert abs(p["cierre"] / p["dur"] - 0.42) < 0.005
    assert abs(p["apertura"] / p["dur"] - 0.58) < 0.005
    c = M["curva"]  # muestras cada 0,1 frame
    pico = max(range(len(c)), key=c.__getitem__)
    assert pico == 25 and c[25] == pytest.approx(1)
    assert c[0] == 0 and c[60] == 0
    assert c[12] < 0.5           # cierre ease-in: lento al principio
    assert c[25 + 17] < 0.5      # apertura ease-out: rápida al principio
    assert all(x <= y for x, y in zip(c[:26], c[1:26]))
    assert all(x >= y for x, y in zip(c[25:], c[26:]))


def test_parpadeo_en_cada_cambio_y_separado(M):
    ag = M["agenda"]
    for c in LINEA[1:]:
        assert any(abs(s + 2.5 - (c["t0"] + 1)) < 1e-9 for s in ag), f"sin parpadeo en el cambio de t0={c['t0']}"
    assert all(b - a >= 20 for a, b in zip(ag, ag[1:])), ag
    assert any(s > 0 and all(abs(s - (c["t0"] - 1.5)) > 1e-9 for c in LINEA) for s in ag), "sin parpadeo de reposo"


def test_nunca_parpadea_en_risa_ni_al_empezar_grito(M):
    assert all(s + 6 < 61 for s in M["agendaRisa"]), M["agendaRisa"]
    assert all(not (59 <= s <= 69) for s in M["agendaGrito"]), M["agendaGrito"]


def test_squash_conserva_volumen(M):
    for torso, cabeza, sy in M["squash"]:
        assert abs(torso - 1) <= 0.001 and abs(cabeza - 1) <= 0.001
        assert 0.85 <= sy <= 1.15


def test_holds_de_10_frames(M):
    assert M["validaOk"] is True
    assert M["rechaza"] and "hold" in M["rechaza"]
    serie = M["holdSerie"]
    quieto = [max(abs(a - b) for a, b in zip(serie[f], serie[f + 1])) < 1e-3 for f in range(len(serie) - 1)]
    for c in LINEA[1:]:
        racha = 0
        for f in range(c["t0"] - 1, -1, -1):
            if not quieto[f]:
                break
            racha += 1
        assert racha >= 10, f"hold de {racha} frames antes de {c['pose']} (t0={c['t0']})"
