"""Sintetiza voz con Qwen3-TTS VoiceDesign (Alibaba, licencia Apache 2.0).

POR QUE ESTE Y NO OTRO (3 ago 2026): es el unico motor local del proyecto que
acepta una DESCRIPCION EN TEXTO de como debe sonar la voz (`--instruct`), no
solo que voz usar. Para KOREX eso es la diferencia entre un narrador plano y el
tono burlon y sarcastico que pide el canal: edge-tts no tiene control de tono
(solo velocidad y pitch) y Chatterbox solo tiene una perilla de intensidad
(`exaggeration`), que sube el enfasis pero no cambia la ACTITUD.

Frente a los otros dos motores embebidos:
  - edge-tts: instantaneo y gratis, pero voz de lector; sin control de actitud.
  - Kokoro:   local y rapido, misma limitacion.
  - Chatterbox: mas humano, sin timestamps, minutos en CPU.
  - Qwen3-TTS: control por descripcion + 10 idiomas (espanol incluido).

Igual que Chatterbox, NO devuelve timestamps de palabra: quien lo llame debe
alinear el wav con whisper (`viral_lab._align_words` ya lo hace).

Uso:
  uv run synth.py --text-file guion.txt --out voz.wav \
      --instruct "Narrador masculino latino, tono burlon y sarcastico, como
                  quien se rie del protagonista mientras lo explica"
"""
import argparse
import re
import sys
from pathlib import Path

MODEL_VOICEDESIGN = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
MODEL_CUSTOMVOICE = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

# ============================================================================
# VOZ OFICIAL DE KOREX -- elegida por Fabian el 3 ago 2026 tras un casting de
# 21 muestras (variante "mex4_locutor_mx"). NO cambiar sin que lo pida.
#
# Como se llego aqui, por si hay que reconstruirla:
#   - el CARACTER sale de la mezcla de sus dos referencias de ElevenLabs
#     ("Leonidas, spartan warrior" + "Johnny, mocking sarcastic and rich"):
#     el peso grave del guerrero con la burla rica y aterciopelada;
#   - el ACENTO hubo que forzarlo. Pedir "espanol neutro" a secas devolvia
#     castellano peninsular una y otra vez. Solo se corrigio nombrando MEXICO
#     y PROHIBIENDO por su nombre los rasgos ibericos (ceceo, 'vosotros',
#     entonacion madrilena). Si se reescribe esta cadena, mantener esa parte.
# ============================================================================
KOREX_VOICE = (
    "Voz masculina adulta, timbre rico y aterciopelado, grave y calida, "
    "de hombre poderoso y seguro de si mismo. Tono mordaz y burlon, "
    "ironia elegante de quien se sabe superior, nunca grita. "
    "Acento MEXICANO de locutor profesional de radio de Mexico, "
    "diccion impecable y neutra para toda Latinoamerica. NUNCA acento "
    "de Espana, sin ceceo ni entonacion peninsular."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--instruct", default=KOREX_VOICE,
        help="descripcion EN TEXTO de como debe sonar la voz -- es la razon "
             "de existir de este motor. Por defecto, la voz oficial de KOREX")
    ap.add_argument("--language", default="Spanish",
                    help="Chinese/English/Japanese/Korean/German/French/"
                         "Russian/Portuguese/Spanish/Italian")
    ap.add_argument("--speaker", default="",
                    help="si se pasa, usa el modelo CustomVoice con esa voz "
                         "predefinida en vez de disenar una nueva")
    ap.add_argument("--max-chars", type=int, default=280,
                    help="tamano de trozo; los modelos TTS truncan en silencio "
                         "las generaciones largas (medido en Chatterbox: un "
                         "guion de 77s salia como 40s SIN ningun error)")
    ap.add_argument("--device", default="auto")
    a = ap.parse_args()

    import torch
    import numpy as np
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel

    device = a.device
    if device == "auto":
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    # bfloat16 solo tiene sentido en GPU; en CPU se cae o va lentisimo
    dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
    model_id = MODEL_CUSTOMVOICE if a.speaker else MODEL_VOICEDESIGN
    print(f"[qwen-tts] device={device} modelo={model_id}", file=sys.stderr)

    kw = {"device_map": device, "dtype": dtype}
    try:
        # flash_attention_2 baja el uso de VRAM, pero su rueda casi nunca
        # compila en Windows: se intenta y se sigue sin el si no esta.
        model = Qwen3TTSModel.from_pretrained(
            model_id, attn_implementation="flash_attention_2", **kw)
    except Exception as e:
        print(f"[qwen-tts] sin flash-attn ({type(e).__name__}); sigo igual",
              file=sys.stderr)
        model = Qwen3TTSModel.from_pretrained(model_id, **kw)

    text = Path(a.text_file).read_text(encoding="utf-8").strip()

    # TROCEADO POR FRASE, igual que en Chatterbox y por el mismo motivo: una
    # generacion larga se corta sola y el fallo es SILENCIOSO (el wav es valido,
    # solo que le falta el final). Cortar por frase evita ademas que un corte
    # caiga a mitad de palabra.
    trozos, actual = [], ""
    for frase in re.split(r"(?<=[.!?])\s+", text):
        if len(actual) + len(frase) + 1 > a.max_chars and actual:
            trozos.append(actual.strip())
            actual = frase
        else:
            actual = f"{actual} {frase}".strip()
    if actual:
        trozos.append(actual)
    print(f"[qwen-tts] {len(trozos)} trozos", file=sys.stderr)

    partes, sr = [], None
    for i, trozo in enumerate(trozos):
        if a.speaker:
            wavs, sr = model.generate_custom_voice(
                text=trozo, language=a.language, speaker=a.speaker,
                instruct=a.instruct)
        else:
            # MISMO `instruct` EN TODOS LOS TROZOS: es lo que fija la identidad
            # de la voz. Variarlo entre trozos suena a varios narradores, el
            # mismo problema que Chatterbox resuelve con su wav de ancla.
            wavs, sr = model.generate_voice_design(
                text=trozo, language=a.language, instruct=a.instruct)
        w = np.asarray(wavs[0])
        partes.append(w)
        print(f"[qwen-tts]   {i+1}/{len(trozos)} ({len(w)/sr:.1f}s)",
              file=sys.stderr)

    sil = np.zeros(int(sr * 0.18), dtype=partes[0].dtype)  # respiracion
    wav = np.concatenate([x for p in partes for x in (p, sil)][:-1])
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), wav, sr)
    print(f"[qwen-tts] {out} ({len(wav)/sr:.1f}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
