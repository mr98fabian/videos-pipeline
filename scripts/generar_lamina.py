"""Genera láminas de pose de Tadeo con la API oficial de Gemini (Nano Banana).

    py scripts/generar_lamina.py --pose pointing
    py scripts/generar_lamina.py --pose pointing --n 3
    py scripts/generar_lamina.py --pose pointing --n 12 --lote     # más de 10 solo con --lote

Misión 0004. La hoja madre (assets/kx_cast/tadeo/_hojas/model_sheet.png) va como
imagen de referencia y la lámina se guarda en misiones/evidencia/0004/<pose>_api.png.
Ningún píxel generado llega al vídeo sin trazarse antes con kx_trazo.py.

La llave NUNCA se imprime ni se escribe: se lee de GEMINI_API_KEY (entorno o
.env en la raíz del repo, ya ignorado por git) y todo texto que sale del script
—mensajes, errores de la API, log— pasa por `redactar()`.

Costo: cada llamada añade una fila a misiones/evidencia/0004/costos.csv con los
tokens que devuelve la API (usageMetadata) y su costo estimado en USD.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
REFERENCIA = ROOT / "assets" / "kx_cast" / "tadeo" / "_hojas" / "model_sheet.png"
SALIDA = ROOT / "misiones" / "evidencia" / "0004"
LOG = SALIDA / "costos.csv"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

# ID verificado el 25 nov 2026 contra la doc oficial (aistudio.google.com/docs/models)
# y contra la propia API (GET /v1beta/models con la llave de Fabian: lo lista con
# generateContent). La doc lo recomienda para proyectos nuevos de la familia
# Nano Banana. Alternativa estable: gemini-3.1-flash-image (Nano Banana 2).
MODELO = "gemini-nano-banana-2.1"

# USD por 1M de tokens y por imagen de 1K según la página de precios (tier de pago,
# 25 nov 2026; cifras leídas de un resumen de la doc: revisar si cambia el precio).
PRECIOS = {
    "gemini-nano-banana-2.1": {"entrada": 1.50, "salida_imagen": 30.00, "salida_texto": 30.00, "imagen_1k": 0.0336},
    "gemini-3.1-flash-image": {"entrada": 0.50, "salida_imagen": 60.00, "salida_texto": 3.00, "imagen_1k": 0.067},
    "gemini-3.1-flash-lite-image": {"entrada": 0.25, "salida_imagen": 30.00, "salida_texto": 1.50, "imagen_1k": 0.0336},
    "gemini-2.5-flash-image": {"entrada": 0.30, "salida_imagen": 30.00, "salida_texto": 2.50, "imagen_1k": 0.039},
    "gemini-3-pro-image": {"entrada": 2.00, "salida_imagen": 120.00, "salida_texto": 12.00, "imagen_1k": 0.134},
}
TOPE_POR_EJECUCION = 10

ESTILO = (
    "The attached image is the MODEL SHEET of the character 'Tadeo', a cartoon raccoon. "
    "Draw ONE new full-body pose of exactly this character on a plain white background. "
    "Keep his design identical to the model sheet: same head shape and proportions, same mask, "
    "same large round eyes with the white highlight, same small black nose, same chest tuft, "
    "same white gloves, same dark feet, same striped tail. "
    "Style: 1930s rubber-hose cartoon, clean black ink outline of uniform weight, flat grayscale "
    "fills (no color, no gradients, no hatching, no shadows on the floor), pure white background. "
    "Output a single character illustration only: no text, no labels, no panels, no other poses, "
    "no expression sheets, no turnaround."
)

POSES = {
    "pointing": (
        "Pose 'pointing': he stands in a confident wide stance, body turned three-quarters, "
        "his LEFT arm (viewer's left) stretched out straight to the side and pointing with the index "
        "finger extended and the other fingers curled, his other hand resting on his hip, "
        "head turned toward the pointing direction, a slight smirk."
    ),
}


# ------------------------------------------------------------------ llave
class ErrorLimpio(Exception):
    """Fallo esperado: se imprime el mensaje (ya sin llaves) y se sale con código 2."""


def leer_llave(raiz: Path, entorno: dict) -> str | None:
    k = (entorno.get("GEMINI_API_KEY") or "").strip()
    if k:
        return k
    env = raiz / ".env"
    if env.is_file():
        for linea in env.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(?:export\s+)?GEMINI_API_KEY\s*=\s*(.*)", linea)
            if m:
                return m.group(1).strip().strip("'\"") or None
    return None


# formas conocidas de llave de Google (AIza…, AQ.…): se tapan aunque no sean la actual
PATRON_LLAVE = re.compile(r"(AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-]{20,})")


def redactar(texto: str, llave: str | None = None) -> str:
    texto = str(texto)
    if llave:
        texto = texto.replace(llave, "***")
    return PATRON_LLAVE.sub("***", texto)


# ------------------------------------------------------------------ API
def construir_cuerpo(prompt: str, ref_png: bytes, mime: str = "image/png") -> dict:
    return {
        "contents": [{"parts": [
            {"text": prompt},
            {"inlineData": {"mimeType": mime, "data": base64.b64encode(ref_png).decode("ascii")}},
        ]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }


def llamar_api(modelo: str, cuerpo: dict, llave: str, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        ENDPOINT.format(modelo=modelo), data=json.dumps(cuerpo).encode("utf-8"), method="POST",
        headers={"x-goog-api-key": llave, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            detalle = json.loads(e.read().decode("utf-8", "replace")).get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001 - cuerpo no JSON
            detalle = ""
        if e.code in (400, 401, 403) and re.search(r"api key|API_KEY|permission|credential", detalle, re.I):
            raise ErrorLimpio(f"la API rechazó la llave (HTTP {e.code}). Revisa GEMINI_API_KEY en .env "
                              "y que el proyecto tenga facturación activada.") from None
        raise ErrorLimpio(f"la API respondió HTTP {e.code}: {redactar(detalle or e.reason, llave)[:900]}") from None
    except urllib.error.URLError as e:
        raise ErrorLimpio(f"no se pudo conectar con la API: {redactar(e.reason, llave)}") from None


def extraer_imagen(resp: dict) -> bytes:
    for cand in resp.get("candidates", []):
        for parte in cand.get("content", {}).get("parts", []):
            blob = parte.get("inlineData") or parte.get("inline_data")
            if blob and blob.get("data"):
                return base64.b64decode(blob["data"])
    motivo = ""
    cands = resp.get("candidates") or [{}]
    if cands[0].get("finishReason"):
        motivo = f" (finishReason: {cands[0]['finishReason']})"
    fb = resp.get("promptFeedback", {}).get("blockReason")
    if fb:
        motivo += f" (bloqueada: {fb})"
    raise ErrorLimpio("la respuesta no trae imagen" + motivo)


def costo_usd(modelo: str, uso: dict) -> tuple[float, str]:
    """(USD, método). Con tokens por modalidad si la API los da; si no, precio plano de 1K."""
    p = PRECIOS.get(modelo)
    if not p:
        return 0.0, "modelo sin precio en PRECIOS"
    ent = uso.get("promptTokenCount")
    det = uso.get("candidatesTokensDetails") or []
    if ent is not None and det:
        img = sum(d.get("tokenCount", 0) for d in det if str(d.get("modality", "")).upper() == "IMAGE")
        txt = sum(d.get("tokenCount", 0) for d in det if str(d.get("modality", "")).upper() == "TEXT")
        usd = ent * p["entrada"] / 1e6 + img * p["salida_imagen"] / 1e6 + txt * p["salida_texto"] / 1e6
        return round(usd, 5), "tokens"
    return p["imagen_1k"], "precio plano 1K"


def anotar_costo(log: Path, fila: dict) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not log.exists()
    with log.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fila))
        if nuevo:
            w.writeheader()
        w.writerow(fila)


# ------------------------------------------------------------------ principal
def main(argv: list[str] | None = None, entorno: dict | None = None, raiz: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pose", required=True, help=f"una de: {', '.join(POSES)}")
    ap.add_argument("--n", type=int, default=1, help="imágenes a generar (máx. 10 por ejecución)")
    ap.add_argument("--lote", action="store_true", help="permite más de 10 imágenes en una ejecución")
    ap.add_argument("--modelo", default=MODELO)
    ap.add_argument("--referencia", type=Path, default=raiz / REFERENCIA.relative_to(ROOT))
    ap.add_argument("--salida", type=Path, default=raiz / SALIDA.relative_to(ROOT))
    ap.add_argument("--extra", default="", help="texto que se añade al prompt de la pose")
    a = ap.parse_args(argv)
    entorno = os.environ if entorno is None else entorno
    llave = None
    try:
        if a.pose not in POSES:
            raise ErrorLimpio(f"pose desconocida «{a.pose}». Poses definidas: {', '.join(POSES)}")
        if a.n < 1:
            raise ErrorLimpio("--n debe ser al menos 1")
        if a.n > TOPE_POR_EJECUCION and not a.lote:
            raise ErrorLimpio(f"se niega a generar {a.n} imágenes en una ejecución (tope {TOPE_POR_EJECUCION}, "
                              "contra gasto accidental). Si es a propósito, añade --lote.")
        llave = leer_llave(raiz, entorno)
        if not llave:
            raise ErrorLimpio("falta GEMINI_API_KEY. Ponla en el archivo .env de la raíz del repo "
                              "(una línea: GEMINI_API_KEY=tu_llave) o en la variable de entorno. "
                              "Se crea en aistudio.google.com con facturación activada.")
        if not a.referencia.is_file():
            raise ErrorLimpio(f"no encuentro la imagen de referencia: {a.referencia}")
        ref = a.referencia.read_bytes()
        prompt = f"{ESTILO}\n\n{POSES[a.pose]}" + (f"\n\n{a.extra}" if a.extra else "")
        cuerpo = construir_cuerpo(prompt, ref, "image/png" if a.referencia.suffix.lower() == ".png" else "image/jpeg")
        a.salida.mkdir(parents=True, exist_ok=True)
        total = 0.0
        for i in range(a.n):
            resp = llamar_api(a.modelo, cuerpo, llave)
            img = extraer_imagen(resp)
            nombre = f"{a.pose}_api.png" if a.n == 1 else f"{a.pose}_api_{i + 1}.png"
            destino = a.salida / nombre
            destino.write_bytes(img)
            uso = resp.get("usageMetadata", {})
            usd, metodo = costo_usd(a.modelo, uso)
            total += usd
            anotar_costo(a.salida / LOG.name, {
                "fecha": dt.datetime.now().isoformat(timespec="seconds"), "modelo": a.modelo, "pose": a.pose,
                "archivo": nombre, "tokens_entrada": uso.get("promptTokenCount", ""),
                "tokens_salida": uso.get("candidatesTokenCount", ""), "costo_usd": usd, "metodo": metodo})
            print(f"[{i + 1}/{a.n}] {destino}  ·  {usd:.4f} USD ({metodo})")
        print(f"modelo {a.modelo} · total {total:.4f} USD · log: {a.salida / LOG.name}")
        return 0
    except ErrorLimpio as e:
        print(f"ERROR: {redactar(e, llave)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
