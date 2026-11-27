"""Trazador de láminas de pose de Tadeo (misión 0006, diseño del 25 nov 2026).

En la CI (solo pytest, sin OpenCV) se comprueba lo commiteado: que
misiones/evidencia/0006/informe.json corresponde al código actual del trazador
(huella), que cada traza candidata es la que dice el informe (SHA-1) y sale de la
lámina que dice (SHA-1 de la fuente), que los umbrales de la sección 3.1 no se
han aflojado y que ninguna lámina «pasa» sin haberse medido.
Con OpenCV, además, se vuelve a segmentar una lámina y se miden sus anclas.
Se regenera con `py kx_lamina.py`.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import kx_lamina as K  # noqa: E402

INF = json.loads((K.EVID_OUT / "informe.json").read_text(encoding="utf-8"))
LAMINAS = [*K.POSES, "pointing"]


def _sha1(p: Path) -> str:
    return hashlib.sha1(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]


def test_informe_al_dia_con_el_trazador():
    assert INF["huella_codigo"] == K.huella_codigo(), "informe.json es de otro trazador: corre `py kx_lamina.py`"


@pytest.mark.parametrize("nombre", LAMINAS)
def test_traza_y_fuente_son_las_del_informe(nombre):
    m = INF["medidas"][nombre]
    assert "rechazo" not in m, m.get("rechazo")
    assert _sha1(ROOT / m["traza"]["archivo"]) == m["traza"]["sha1"], "la traza cambió sin regenerar el informe"
    assert _sha1(K.FUENTES[nombre]) == m["fuente_sha1"], "la lámina cambió: hay que volver a trazarla"


def test_umbrales_31_no_se_aflojan():
    u = INF["umbrales_31"]
    assert u["iou_min"] >= 0.98 and u["tinta_min"] >= 0.97
    assert u["area_tinta"] == [0.97, 1.03]
    assert u["tono_error_medio_max"] <= 0.030 and u["tono_superficie_max"] <= 0.05


@pytest.mark.parametrize("nombre", LAMINAS)
def test_trazo_copia_su_lamina(nombre):
    """Silueta y tinta (la parte del 3.1 que el trazador controla) en todas."""
    t = INF["medidas"][nombre]["traza_31"]
    assert t["iou"] >= 0.98
    assert t["tinta_lamina_en_trazo"] >= 0.97 and t["tinta_trazo_en_lamina"] >= 0.97
    assert 0.97 <= t["area_tinta"] <= 1.03


def test_nadie_pasa_sin_medirse():
    for n, v in INF["por_lamina"].items():
        if v.get("pasa"):
            assert v["pasa_31"] and v["pasa_32"] and v["solido"] and not v["no_medible"], n


def test_malos_fabricados_existen_y_estan_medidos():
    """Los malos de la sección 4 se fabrican y se miden siempre. Si se detectan o no es
    un dato del informe (con solo pie y panza, el cuerpo aplastado ×0,8 NO se detecta)."""
    malos = INF["calibracion"]["separacion"]["malos"]
    assert {"cabeza_x1.3", "cuerpo_ancho_x1.25", "cuerpo_bajo_x0.8"} <= set(malos)
    for n, v in malos.items():
        assert "cumple" in v and ("rechazada_antes" in v or "marcas_fuera" in v), n


def test_solo_deciden_pie_y_panza():
    """Decisión de Fabian del 27 nov 2026: las marcas de brazo y cola informan, no deciden."""
    assert K.DECIDEN == ("pie", "panza")
    for n, v in INF["por_lamina"].items():
        assert set(v.get("marcas_fuera", {})) <= {"pie", "panza"}, n


def test_en_el_rig_estan_exactamente_las_que_pasan():
    """Sección 7: en laminas/ solo entran las que pasan todo, copia exacta de su traza de evidencia."""
    carpeta = ROOT / "motion_graphics" / "src" / "kx" / "tadeo" / "laminas"
    pasan = {n for n in K.POSES if INF["por_lamina"][n].get("pasa")}
    en_rig = {p.stem.removeprefix("traza_") for p in carpeta.glob("traza_*.js")}
    assert en_rig == pasan
    indice = (carpeta / "index.js").read_text(encoding="utf-8")
    for n in pasan:
        assert _sha1(carpeta / f"traza_{n}.js") == INF["medidas"][n]["traza"]["sha1"], n
        assert f"{n}: TRAZA_{n.upper()}" in indice, n


RIG = json.loads((K.EVID_OUT / "rig.json").read_text(encoding="utf-8"))


def test_rig_medido_con_el_trazador_actual():
    assert RIG["huella_codigo"] == K.huella_codigo(), "rig.json es de otro trazador: corre `py kx_lamina.py --rig`"
    assert set(RIG["poses"]) == {n for n in K.POSES if INF["por_lamina"][n].get("pasa")}


@pytest.mark.parametrize("pose", sorted(RIG["poses"]))
def test_el_rig_dibuja_la_lamina(pose):
    """El render REAL del rig (Remotion) copia el cuerpo de su lámina y pone la cabeza donde se calculó."""
    r = RIG["poses"][pose]
    assert all(r["traza_31_rig"]["cumple"].values()), r["traza_31_rig"]
    assert K.anclaje_ok(r), r


def test_anclas_de_decidido():
    pytest.importorskip("cv2")
    lam = K.segmentar(K.cargar("decidido"))
    assert abs(lam.A - INF["medidas"]["decidido"]["anclas"]["A_px"]) < 0.5
    assert len(lam.pies["masks"]) == 2
    assert lam.marcas["cola_anillos"] == INF["medidas"]["decidido"]["marcas"]["cola_anillos"]


def test_rechaza_una_lamina_sin_antifaz():
    cv2 = pytest.importorskip("cv2")
    import numpy as np
    g = np.full((600, 450), 251, np.uint8)
    cv2.circle(g, (225, 300), 120, 150, -1)
    cv2.circle(g, (225, 300), 120, 20, 6)
    with pytest.raises(K.Rechazo, match="antifaz"):
        K.segmentar(K.cargar("vacia", gris=g, escala=1))
