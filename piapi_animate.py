"""Anima una escena ya generada: imagen -> video 5s con Seedance 2 via PiAPI.

POR QUE ESTO Y NO FLOW (12 ago 2026): la animacion de Flow va por navegador y
ese camino nos costo tandas enteras -- la sesion se atasca a mitad, el cupo
diario del modelo solo se ve en una captura, y los tiles sobrantes se cuelan en
la escena siguiente. Esto es una API: falla con un codigo, no con una imagen
equivocada que parece buena.

LA CONSISTENCIA DEL PERSONAJE NO ES PROBLEMA AQUI, y conviene entender por que:
en imagen->video el PRIMER FRAME ES la imagen ya aprobada, asi que el modelo no
redibuja a Tadeo, lo mueve. Todo el trabajo de identidad (hoja madre, bloque de
identidad, revision a 340px) ya paso aguas arriba. Ademas Seedance acepta DOS
extremos (`mode: first_last_frames`): pasando la escena N como primer frame y la
N+1 como ultimo, la deriva de los 5 segundos queda encajonada por los dos lados
y el clip se convierte en la transicion entre dos planos ya validados.

Clave: PIAPI_API_KEY en el entorno, o piapi_key.txt en la raiz (gitignored).

Uso:
    py piapi_animate.py output/<carpeta> 0            # anima la escena 0
    py piapi_animate.py output/<carpeta> 0 --hasta 1  # escena 0 -> 1 (dos extremos)
    py piapi_animate.py output/<carpeta> 0 --segundos 5 --resolucion 720p
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

API = "https://api.piapi.ai/api/v1/task"
# VARIANTE BARATA POR DEFECTO (12 ago 2026, ver INVESTIGACION_COSTE_ANIMACION.md).
# El primer clip se genero con `seedance-2`, el buque insignia, y costo ~$2 por
# 5s: estabamos pagando el modelo tope para hacer un empuje de camara sobre un
# dibujo quieto. `seedance-2-mini` cuesta $0,084/s a 720p frente a $0,20/s --58%
# menos-- y el modo de dos extremos esta en TODAS las variantes, asi que no se
# pierde nada de la receta. Se cambia con --modelo si algun plano lo pide.
MODELO = "seedance-2-mini"
# 720p y no 1080p a proposito: la tarifa oficial se dispara en 1080p y el canal
# ya publica escalando desde 768x1376, asi que no se gana nitidez real.
RESOLUCION = "720p"


def _api_key() -> str:
    import os

    k = os.environ.get("PIAPI_API_KEY", "").strip()
    if k:
        return k
    f = ROOT / "piapi_key.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    raise SystemExit(
        "Falta la clave de PiAPI: exporta PIAPI_API_KEY o crea piapi_key.txt "
        "en la raiz del repo (esta gitignorado)."
    )


def animar(
    imagen: Path,
    movimiento: str,
    destino: Path,
    ultima: Path | None = None,
    segundos: int = 5,
    resolucion: str = RESOLUCION,
    modelo: str = MODELO,
    timeout_s: int = 900,
) -> bool:
    """Crea el clip y lo baja. Devuelve False sin lanzar: una escena sin animar
    no debe tumbar el montaje, igual que en el resto del pipeline."""
    import pipeline as pl

    key = _api_key()
    urls = [pl._piapi_upload_temp(imagen, key)]
    if ultima and Path(ultima).exists():
        urls.append(pl._piapi_upload_temp(Path(ultima), key))

    payload = {
        "model": "seedance",
        "task_type": modelo,
        "input": {
            "prompt": movimiento,
            "mode": "first_last_frames",
            "image_urls": urls,
            "duration": int(segundos),
            "aspect_ratio": "9:16",
            "resolution": resolucion,
        },
    }
    r = requests.post(
        API,
        headers={"X-API-Key": key, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if r.status_code >= 400:
        print(f"[piapi] {r.status_code}: {r.text[:300]}")
        return False
    task_id = r.json()["data"]["task_id"]
    print(
        f"[piapi] tarea {task_id} ({modelo}, {len(urls)} extremo(s), "
        f"{segundos}s, {resolucion})"
    )

    limite = time.monotonic() + timeout_s
    while time.monotonic() < limite:
        time.sleep(10)
        g = requests.get(f"{API}/{task_id}", headers={"X-API-Key": key}, timeout=60)
        if g.status_code >= 400:
            print(f"[piapi] poll {g.status_code}: {g.text[:200]}")
            continue
        data = g.json().get("data") or {}
        estado = (data.get("status") or "").lower()
        if estado in ("completed", "success"):
            url = (data.get("output") or {}).get("video")
            if not url:
                print(f"[piapi] completado SIN video: {json.dumps(data)[:300]}")
                return False
            destino.parent.mkdir(parents=True, exist_ok=True)
            with requests.get(url, stream=True, timeout=300) as v:
                v.raise_for_status()
                with open(destino, "wb") as fh:
                    for trozo in v.iter_content(1 << 16):
                        fh.write(trozo)
            print(f"[piapi] LISTO: {destino}")
            return True
        if estado in ("failed", "error"):
            print(f"[piapi] fallo: {json.dumps(data.get('error') or data)[:300]}")
            return False
        print(f"[piapi] {estado or 'pendiente'}...")
    print(f"[piapi] timeout tras {timeout_s}s")
    return False


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) < 2:
        print(__doc__)
        return 1
    out_dir = Path(argv[0])
    i = int(argv[1])
    hasta = None
    segundos, resolucion, modelo = 5, RESOLUCION, MODELO
    if "--hasta" in argv:
        hasta = int(argv[argv.index("--hasta") + 1])
    if "--segundos" in argv:
        segundos = int(argv[argv.index("--segundos") + 1])
    if "--resolucion" in argv:
        resolucion = argv[argv.index("--resolucion") + 1]
    if "--modelo" in argv:
        modelo = argv[argv.index("--modelo") + 1]

    data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    movimientos = data.get("motion_terms") or []
    if i >= len(movimientos):
        return print(f"el guion no trae motion_terms para la escena {i}") or 1
    clips = out_dir / "clips"
    ok = animar(
        clips / f"nb_{i}.png",
        movimientos[i],
        clips / f"fx_{i}.mp4",
        ultima=(clips / f"nb_{hasta}.png") if hasta is not None else None,
        segundos=segundos,
        resolucion=resolucion,
        modelo=modelo,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
