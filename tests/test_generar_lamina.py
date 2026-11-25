"""Misión 0004: el script de láminas falla limpio y nunca deja salir una llave.

Sin red: la API se sustituye por un doble. Las llaves de estas pruebas son
INVENTADAS; la real (si hay .env) solo se usa para comprobar que no aparece en
ningún archivo commiteado, y no se imprime nunca.
"""
import base64
import io
import json
import re
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generar_lamina as G  # noqa: E402

FALSA = "AQ.FALSA-llave-de-prueba-0123456789abcdefghijkl"
FORMA_AIZA = "AIza" + "x" * 35          # forma antigua, inventada
FORMA_AQ = "AQ." + "y" * 40             # forma nueva, inventada


def _ref(tmp_path):
    p = tmp_path / "ref.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\nfalso")
    return p


def _run(tmp_path, argv, entorno, capsys):
    rc = G.main(["--salida", str(tmp_path / "out"), "--referencia", str(_ref(tmp_path)), *argv],
                entorno=entorno, raiz=tmp_path)
    cap = capsys.readouterr()
    return rc, cap.out + cap.err


def test_sin_llave_falla_limpio(tmp_path, capsys):
    rc, salida = _run(tmp_path, ["--pose", "pointing"], {}, capsys)
    assert rc == 2
    assert "GEMINI_API_KEY" in salida and ".env" in salida
    assert "Traceback" not in salida
    assert not (tmp_path / "out" / "pointing_api.png").exists()


def test_llave_invalida_falla_limpio_sin_eco(tmp_path, monkeypatch, capsys):
    def rechaza(req, timeout=0):
        cuerpo = json.dumps({"error": {"code": 400, "message": f"API key not valid ({FALSA}). Please pass a valid API key."}})
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, io.BytesIO(cuerpo.encode()))
    monkeypatch.setattr(G.urllib.request, "urlopen", rechaza)
    rc, salida = _run(tmp_path, ["--pose", "pointing"], {"GEMINI_API_KEY": FALSA}, capsys)
    assert rc == 2
    assert "rechazó la llave" in salida
    assert FALSA not in salida and "FALSA-llave" not in salida
    assert "Traceback" not in salida


def test_error_de_red_no_filtra_la_llave(tmp_path, monkeypatch, capsys):
    def cae(req, timeout=0):
        raise urllib.error.URLError(f"fallo de conexión con clave {FALSA}")
    monkeypatch.setattr(G.urllib.request, "urlopen", cae)
    rc, salida = _run(tmp_path, ["--pose", "pointing"], {"GEMINI_API_KEY": FALSA}, capsys)
    assert rc == 2 and FALSA not in salida


def test_llave_en_env_del_repo(tmp_path):
    (tmp_path / ".env").write_text(f"OTRA=1\nGEMINI_API_KEY={FALSA}\n", encoding="utf-8")
    assert G.leer_llave(tmp_path, {}) == FALSA
    assert G.leer_llave(tmp_path / "otro", {}) is None


def test_tope_de_diez_imagenes(tmp_path, monkeypatch, capsys):
    llamadas = []
    monkeypatch.setattr(G, "llamar_api", lambda *a, **k: llamadas.append(1) or {})
    rc, salida = _run(tmp_path, ["--pose", "pointing", "--n", "11"], {"GEMINI_API_KEY": FALSA}, capsys)
    assert rc == 2 and "--lote" in salida and not llamadas


def test_exito_guarda_imagen_y_costo_sin_llave(tmp_path, monkeypatch, capsys):
    png = b"\x89PNG\r\n\x1a\nimagen-generada"
    resp = {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(png).decode()}}]}}],
            "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 1290,
                              "candidatesTokensDetails": [{"modality": "IMAGE", "tokenCount": 1290}]}}
    visto = {}

    def falso(modelo, cuerpo, llave, timeout=0):
        visto.update(modelo=modelo, cuerpo=cuerpo)
        return resp
    monkeypatch.setattr(G, "llamar_api", falso)
    rc, salida = _run(tmp_path, ["--pose", "pointing"], {"GEMINI_API_KEY": FALSA}, capsys)
    assert rc == 0, salida
    assert (tmp_path / "out" / "pointing_api.png").read_bytes() == png
    log = (tmp_path / "out" / "costos.csv").read_text(encoding="utf-8")
    assert "pointing_api.png" in log and "tokens" in log
    assert FALSA not in salida and FALSA not in log
    assert visto["modelo"] == G.MODELO
    partes = visto["cuerpo"]["contents"][0]["parts"]
    assert partes[1]["inlineData"]["mimeType"] == "image/png"   # la referencia va dentro
    esperado = (1000 * 1.50 + 1290 * 30.0) / 1e6
    assert abs(G.costo_usd(G.MODELO, resp["usageMetadata"])[0] - esperado) < 1e-6


def test_respuesta_sin_imagen_falla_limpio():
    with pytest.raises(G.ErrorLimpio):
        G.extraer_imagen({"candidates": [{"finishReason": "SAFETY", "content": {"parts": [{"text": "no"}]}}]})


def test_redactar_tapa_formas_de_llave():
    assert FORMA_AIZA not in G.redactar(f"clave {FORMA_AIZA} fin")
    assert FORMA_AQ not in G.redactar(f"clave {FORMA_AQ} fin")


def _archivos_commiteados():
    try:
        r = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    return [ROOT / f for f in r.stdout.splitlines() if (ROOT / f).is_file()]


def test_ninguna_llave_en_archivos_commiteados():
    """Ni la de .env (si existe, solo local) ni nada con forma de llave de Google."""
    forma = re.compile(r"(AIza[0-9A-Za-z_\-]{30,}|AQ\.Ab[0-9A-Za-z_\-]{20,})")
    real = G.leer_llave(ROOT, {})
    en_suelto = []
    for f in _archivos_commiteados():
        if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".mp4", ".mp3", ".wav", ".gif", ".ico", ".pdf", ".woff2", ".ttf"}:
            continue
        try:
            txt = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if forma.search(txt) or (real and real in txt):
            en_suelto.append(str(f.relative_to(ROOT)))
    assert not en_suelto, f"llave en: {en_suelto}"


def test_env_sigue_ignorado_por_git():
    r = subprocess.run(["git", "check-ignore", ".env"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, ".env debe estar en .gitignore"
