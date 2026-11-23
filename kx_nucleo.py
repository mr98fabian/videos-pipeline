"""Fase 1 de la Misión 0001: render de prueba del núcleo KoreX + evidencia.

    py kx_nucleo.py [carpeta_con_voz] [--seconds 14.9]

Toma un tramo real de la voz qw_korex (por defecto, el piloto del sobregiro),
lo renderiza con la composición KxNucleo (solo Remotion: ni Flow ni Wan) y
corre las comprobaciones de kx_gate sobre el MP4 resultante.
Salida: output/<fecha>-kx-nucleo/{video.mp4, props.json, gate.json, contactsheet.png}
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import kx_captions
import kx_gate

ROOT = Path(__file__).resolve().parent
MG = ROOT / "motion_graphics"
PILOT = ROOT / "output" / "2026-11-21-el-banco-no-te-bloque-la-compra-por-erro"
POSE = ROOT / "assets" / "kx_cast" / "tadeo" / "asombro.png"
CHAR_BOX = {"x": 48, "y": 400, "w": 420, "h": 560}
FPS = 30


def js_paginate(captions: list[dict], out: Path) -> list[dict]:
    """Ejecuta la paginate() real de src/kx/paginate.js en Node (paridad)."""
    bundle = out / "_paginate.cjs"
    subprocess.run(["npx", "esbuild", "src/kx/paginate.js", "--bundle", "--platform=node", "--format=cjs",
                    f"--outfile={bundle}", "--log-level=error"], cwd=MG, check=True, shell=True, timeout=120)
    js = ("const {paginate}=require(process.argv[1]);let s='';process.stdin.on('data',d=>s+=d)"
          ".on('end',()=>process.stdout.write(JSON.stringify(paginate(JSON.parse(s)))))")
    r = subprocess.run(["node", "-e", js, str(bundle)], input=json.dumps(captions), capture_output=True,
                       text=True, encoding="utf-8", check=True, timeout=60)
    bundle.unlink()
    return json.loads(r.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=str(PILOT))
    ap.add_argument("--seconds", type=float, default=14.9)
    a = ap.parse_args()
    src = Path(a.src)
    voice = next(p for p in (src / "voice.wav", src / "voice.mp3") if p.exists())

    out = ROOT / "output" / f"{dt.date.today():%Y-%m-%d}-kx-nucleo"
    out.mkdir(parents=True, exist_ok=True)
    pub = MG / "public" / "kxm" / "nucleo"  # ignorado por git
    pub.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(voice), "-t", f"{a.seconds}",
                    "-ar", "48000", str(pub / "voice.wav")], check=True, timeout=120)
    shutil.copy2(POSE, pub / "tadeo.png")

    captions, source = kx_captions.get_captions(src, until_s=a.seconds)
    hero = next((c for c in captions if kx_gate._norm(c["text"]) == "treinta"), captions[-1])
    props = {"voice": "kxm/nucleo/voice.wav", "pose": "kxm/nucleo/tadeo.png", "captions": captions,
             "heroMs": hero["startMs"], "charBox": CHAR_BOX, "durationInFrames": round(a.seconds * FPS)}
    (out / "props.json").write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    t0 = time.time()
    subprocess.run(["npx", "remotion", "render", "src/index.jsx", "KxNucleo", str(out / "video.mp4"),
                    f"--props={out / 'props.json'}", "--crf=18", "--log=error"],
                   cwd=MG, check=True, shell=True, timeout=1200)
    render_s = round(time.time() - t0, 1)

    video = out / "video.mp4"
    still_frame = round(hero["startMs"] / 1000 * FPS) + 30  # héroe en pantalla: el frame con más rojo
    subprocess.run(["npx", "remotion", "still", "src/index.jsx", "KxNucleo", str(out / "still_hero.png"),
                    f"--props={out / 'props.json'}", f"--frame={still_frame}", "--log=error"],
                   cwd=MG, check=True, shell=True, timeout=600)
    pages = kx_captions.paginate(captions)
    js_pages = js_paginate(captions, out)
    report = {"timing_source": source, "render_seconds": render_s, "pages": len(pages),
              "words_per_page": [len(p["tokens"]) for p in pages]}
    fails = []
    if [p["text"] for p in js_pages] != [p["text"] for p in pages]:
        fails.append("paginación JS (pantalla) ≠ Python (QA)")
    report["parity_js_python"] = [p["text"] for p in js_pages] == [p["text"] for p in pages]
    for name, fn in (("palette_still", lambda: kx_gate.check_palette_image(out / "still_hero.png", [CHAR_BOX])),
                     ("palette", lambda: kx_gate.check_palette(video, [CHAR_BOX])),
                     ("safe_zone", lambda: kx_gate.check_safe_zone(video)),
                     ("whisper", lambda: kx_gate.check_whisper(video, pages))):
        f, info = fn()
        fails += f
        report[name] = info
    report["fails"] = fails
    kx_gate.contact_sheet(video, out / "contactsheet.png")
    kx_gate.save_report(out / "gate.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "whisper"}, ensure_ascii=False, indent=1))
    print("whisper:", {k: v for k, v in report["whisper"].items() if k != "pages"})
    for p in report["whisper"]["pages"]:
        print(f"  {p['confirmed']:.0%}  {p['ms']}  {p['page']}")
    print("OK" if not fails else "FALLA")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
