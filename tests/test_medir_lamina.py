"""Misión 0005: las comprobaciones automáticas de láminas distinguen una buena de una mala."""
import sys
from pathlib import Path

import pytest

# La CI solo tiene pytest: sin cv2/numpy estas pruebas se saltan (se corren en local).
cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import medir_lamina as M  # noqa: E402


def _lamina(tmp_path, nombre, tono=(120, 120, 120), caja=(200, 250, 700, 1000)):
    img = np.full((1200, 896, 3), 255, np.uint8)
    x0, y0, x1, y1 = caja
    cv2.rectangle(img, (x0, y0), (x1, y1), tono, -1)
    p = tmp_path / nombre
    cv2.imwrite(str(p), img)
    return p


def test_lamina_buena_pasa(tmp_path):
    assert M.medir(_lamina(tmp_path, "ok.png"))["fallos"] == []


def test_color_falla(tmp_path):
    r = M.medir(_lamina(tmp_path, "color.png", tono=(120, 150, 190)))
    assert any("color" in f for f in r["fallos"])


def test_figura_pegada_al_borde_falla(tmp_path):
    r = M.medir(_lamina(tmp_path, "borde.png", caja=(0, 250, 700, 1000)))
    assert any("borde" in f for f in r["fallos"])


def test_dos_figuras_fallan(tmp_path):
    p = _lamina(tmp_path, "dos.png")
    img = cv2.imread(str(p))
    cv2.rectangle(img, (20, 20), (160, 160), (90, 90, 90), -1)
    cv2.imwrite(str(p), img)
    assert any("figuras" in f for f in M.medir(p)["fallos"])


def test_fondo_gris_falla(tmp_path):
    img = np.full((1200, 896, 3), 200, np.uint8)
    cv2.rectangle(img, (200, 250), (700, 1000), (60, 60, 60), -1)
    p = tmp_path / "fondo.png"
    cv2.imwrite(str(p), img)
    assert any("fondo" in f for f in M.medir(p)["fallos"])
