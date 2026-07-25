"""Sintetiza voz con Chatterbox (Resemble AI, licencia MIT).

Por que este y no otro: en estudios de escucha a ciegas su voz gana a ElevenLabs
en la mayoria de comparaciones, corre local y gratis, y la licencia MIT si
permite uso comercial -- a diferencia de XTTS-v2, que es no comercial y por eso
no sirve para un canal monetizado.

Frente a Kokoro suena bastante mas humano (prosodia, respiraciones, variacion de
entonacion) a cambio de tardar mas: en CPU son minutos por narracion, en GPU
segundos. El resultado se cachea por hash del texto+voz para no repetir.

NO devuelve timestamps de palabra: quien lo llame debe alinear el wav resultante
con whisper (viral_lab._align_words ya lo hace). Es mas fiable que cualquier
estimacion, porque mide el audio real.

Uso:
  uv run synth.py --text-file guion.txt --out voz.wav
  uv run synth.py --text-file guion.txt --out voz.wav --ref muestra_de_tu_voz.wav
"""
import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", default="", help="wav de referencia para clonar una voz")
    ap.add_argument("--exaggeration", type=float, default=0.5,
                    help="0.3 = sobrio/documental, 0.7+ = enfatico")
    ap.add_argument("--cfg", type=float, default=0.5,
                    help="mas bajo = ritmo mas lento y pausado")
    ap.add_argument("--device", default="auto")
    a = ap.parse_args()

    import torch
    import torchaudio as ta
    from chatterbox.tts import ChatterboxTTS

    device = a.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[chatterbox] device={device}", file=sys.stderr)

    text = Path(a.text_file).read_text(encoding="utf-8").strip()
    model = ChatterboxTTS.from_pretrained(device=device)
    kw = {"exaggeration": a.exaggeration, "cfg_weight": a.cfg}
    if a.ref:
        kw["audio_prompt_path"] = a.ref
    wav = model.generate(text, **kw)
    ta.save(a.out, wav, model.sr)
    print(f"[chatterbox] {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
