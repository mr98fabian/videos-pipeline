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
import re
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
    ap.add_argument("--max-chars", type=int, default=280,
                    help="tamano de trozo; Chatterbox trunca en silencio "
                         "por encima de ~40s de audio por generacion")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--lang", default="en",
                    help="en usa el modelo ingles; cualquier otro (es, pt, fr...) "
                         "carga el multilingue")
    a = ap.parse_args()

    import torch
    import torchaudio as ta

    device = a.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[chatterbox] device={device} lang={a.lang}", file=sys.stderr)

    text = Path(a.text_file).read_text(encoding="utf-8").strip()
    kw = {"exaggeration": a.exaggeration, "cfg_weight": a.cfg}
    if a.ref:
        kw["audio_prompt_path"] = a.ref

    if a.lang == "en":
        # el modelo ingles dedicado suena algo mejor que el multilingue en ingles
        from chatterbox.tts import ChatterboxTTS
        model = ChatterboxTTS.from_pretrained(device=device)
    else:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    if a.lang != "en":
        kw["language_id"] = a.lang

    # Chatterbox TRUNCA en silencio por encima de ~40s de audio. Medido el
    # 1 ago 2026: un guion de 330 palabras (~77s) salio como 40s sin ningun
    # error. Por eso se trocea por frases y se concatena.
    trozos, actual = [], ""
    for frase in re.split(r"(?<=[.!?])\s+", text):
        if len(actual) + len(frase) + 1 > a.max_chars and actual:
            trozos.append(actual.strip())
            actual = frase
        else:
            actual = f"{actual} {frase}".strip()
    if actual:
        trozos.append(actual)
    print(f"[chatterbox] {len(trozos)} trozos", file=sys.stderr)

    partes, ancla = [], a.ref
    for i, trozo in enumerate(trozos):
        k = dict(kw)
        if ancla:
            # Sin referencia, cada generacion elige una voz distinta y el
            # troceado sonaria a varios narradores. El primer trozo fija la
            # identidad y ancla a todos los demas.
            k["audio_prompt_path"] = ancla
        w = model.generate(trozo, **k)
        partes.append(w)
        if i == 0 and not ancla:
            ancla = str(Path(a.out).with_name("_ancla.wav"))
            ta.save(ancla, w, model.sr)
        print(f"[chatterbox]   {i+1}/{len(trozos)} "
              f"({w.shape[-1]/model.sr:.1f}s)", file=sys.stderr)

    sil = torch.zeros(1, int(model.sr * 0.18))   # respiracion entre trozos
    wav = torch.cat([t for p in partes for t in (p, sil)][:-1], dim=-1)
    ta.save(a.out, wav, model.sr)
    anc = Path(a.out).with_name("_ancla.wav")
    if anc.exists() and not a.ref:
        anc.unlink()
    print(f"[chatterbox] {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
