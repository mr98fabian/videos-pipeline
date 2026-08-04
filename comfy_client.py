"""Generador de imagenes LOCAL via ComfyUI — pedido usuario 3 ago 2026, tras
quedarse sin ninguna via de generar imagenes: Gemini se elimino del repo por
pedido suyo y la cuenta de PiAPI/Seedream devolvio "insufficient credits".

POR QUE ESTE MODELO (FLUX.1-schnell, no dev):
schnell es Apache-2.0 y permite uso COMERCIAL; FLUX.1-dev rinde algo mejor pero
su licencia es non-commercial, inservible para un canal monetizado -- el mismo
criterio que dejo fuera a XTTS-v2 para la voz. Ademas schnell resuelve en 4 pasos
sin CFG, asi que una imagen tarda segundos en una 4080 en vez de minutos.

QUE NO RESUELVE (leer antes de asumir paridad con Seedream):
schnell solo hace texto->imagen. NO acepta imagen de referencia, asi que NO da
consistencia de personaje: las placas de Tadeo van a derivar entre escenas. Para
eso hace falta ademas FLUX Redux o un IP-Adapter, que no estan cableados. Sirve
YA para fondos/escenarios (kx_assets) y para escenas sin personaje.

ComfyUI se arranca solo la primera vez que se pide una imagen y queda vivo para
el resto de la corrida: levantarlo cuesta ~30-60s de carga de modelo y pagarlo
una vez por escena seria absurdo.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMFY_DIR = ROOT / "tools" / "comfyui"
HOST = os.environ.get("COMFY_HOST", "127.0.0.1")
PORT = int(os.environ.get("COMFY_PORT", "8188"))
BASE = f"http://{HOST}:{PORT}"

# Nombres de archivo dentro de tools/comfyui/models/. Se pueden sobreescribir por
# entorno para probar otro modelo sin tocar el codigo.
UNET = os.environ.get("COMFY_UNET", "flux1-schnell-Q4_K_S.gguf")
CLIP_L = os.environ.get("COMFY_CLIP_L", "clip_l.safetensors")
T5 = os.environ.get("COMFY_T5", "t5xxl_fp8_e4m3fn.safetensors")
VAE = os.environ.get("COMFY_VAE", "ae.safetensors")
STEPS = int(os.environ.get("COMFY_STEPS", "4"))  # schnell esta destilado a 4

_PROC: subprocess.Popen | None = None


def _up() -> bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex((HOST, PORT)) == 0


def ensure_server(timeout: float = 180.0) -> bool:
    """Arranca ComfyUI si no esta corriendo. Idempotente."""
    global _PROC
    if _up():
        return True
    main_py = COMFY_DIR / "main.py"
    if not main_py.exists():
        print(f"[comfy] no existe {main_py}")
        return False
    print("[comfy] arrancando ComfyUI local (la primera imagen tarda mas)...")
    _PROC = subprocess.Popen(
        ["uv", "run", "--directory", str(COMFY_DIR), "main.py",
         "--port", str(PORT), "--listen", HOST],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _up():
            print("[comfy] servidor listo")
            return True
        if _PROC.poll() is not None:
            print("[comfy] el proceso murio al arrancar")
            return False
        time.sleep(2)
    print("[comfy] timeout esperando el servidor")
    return False


def shutdown() -> None:
    global _PROC
    if _PROC is not None and _PROC.poll() is None:
        _PROC.terminate()
    _PROC = None


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as r:
        return json.loads(r.read())


def _workflow(prompt: str, width: int, height: int, seed: int) -> dict:
    """Grafo en formato API de ComfyUI. schnell no usa CFG (va en 1.0) ni prompt
    negativo -- por eso el nodo negativo existe pero va vacio: el sampler exige
    la conexion igual."""
    return {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": UNET}},
        "2": {"class_type": "DualCLIPLoader",
              "inputs": {"clip_name1": T5, "clip_name2": CLIP_L,
                         "type": "flux", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode",
              "inputs": {"text": "", "clip": ["2", 0]}},
        "6": {"class_type": "EmptyLatentImage",
              "inputs": {"width": width, "height": height, "batch_size": 1}},
        "7": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": STEPS, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple",
                         "denoise": 1.0, "model": ["1", 0],
                         "positive": ["4", 0], "negative": ["5", 0],
                         "latent_image": ["6", 0]}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"filename_prefix": "pipe", "images": ["8", 0]}},
    }


def generate_image(prompt: str, path: Path, api_key: str = "",
                   reference_image: Path | None = None,
                   reference_images: list[Path] | None = None,
                   style_directive: str | None = None,
                   attempts: int = 2) -> bool:
    """Misma firma que _seedream_generate_image() para poder intercambiarlos.

    api_key se ignora (es local). Las referencias tambien se ignoran: schnell no
    las soporta -- se avisa una vez por llamada para que no pase desapercibido
    que esa escena perdio la consistencia de personaje.
    """
    if reference_image or reference_images:
        print("[comfy] AVISO: FLUX schnell ignora las imagenes de referencia; "
              "esta escena no tendra consistencia de personaje")
    if not ensure_server():
        return False

    full = f"{style_directive}. {prompt}" if style_directive else prompt
    # 9:16 en multiplos de 16, que es lo que exige el VAE
    width, height = 768, 1360

    for attempt in range(attempts):
        try:
            seed = int.from_bytes(os.urandom(4), "big")
            res = _post("/prompt", {"prompt": _workflow(full, width, height, seed)})
            pid = res["prompt_id"]
            deadline = time.time() + 300
            while time.time() < deadline:
                time.sleep(2)
                hist = _get(f"/history/{pid}")
                if pid not in hist:
                    continue
                outs = hist[pid].get("outputs", {})
                imgs = (outs.get("9") or {}).get("images") or []
                if not imgs:
                    raise RuntimeError("el grafo termino sin imagen")
                im = imgs[0]
                q = urllib.parse.urlencode(
                    {"filename": im["filename"], "subfolder": im.get("subfolder", ""),
                     "type": im.get("type", "output")})
                with urllib.request.urlopen(f"{BASE}/view?{q}", timeout=120) as r:
                    path.write_bytes(r.read())
                return True
            raise RuntimeError("timeout esperando la imagen")
        except Exception as e:
            if attempt < attempts - 1:
                print(f"[comfy] fallo (intento {attempt + 1}), reintento: {e}")
                time.sleep(3)
            else:
                print(f"[comfy] fallo para '{prompt[:60]}...': {e}")
    return False


if __name__ == "__main__":
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "comfy_test.png")
    ok = generate_image(sys.argv[1] if len(sys.argv) > 1 else "a plain wooden table", out)
    print("OK" if ok else "FALLO", out)
