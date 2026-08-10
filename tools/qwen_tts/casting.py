"""Genera VARIAS voces distintas de la misma frase para elegir de oido.

Existe porque comparar voces llamando a synth.py una vez por variante recarga
el modelo cada vez (~40s de mas por prueba). Aqui se carga UNA vez y se generan
todas seguidas.

    uv run python casting.py --text-file frase.txt --out-dir ./casting
"""
import argparse
import sys
from pathlib import Path

MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"

# Cada entrada es un ANGULO distinto de "burlon y sarcastico", no variaciones
# de lo mismo: el matiz que separa a un locutor guason de un narrador deadpan
# cambia por completo como cae el chiste del guion.
VOCES = {
    "01_deportivo": (
        "Hombre latino, locutor deportivo guason y energico, se rie del "
        "protagonista como quien narra una jugada ridicula, ritmo rapido, "
        "sube el tono en los remates"),
    "02_deadpan": (
        "Hombre latino, narrador de documental serio que suelta las burlas "
        "sin cambiar el gesto, humor seco y deadpan, ritmo pausado y grave, "
        "ironia contenida sin reirse nunca"),
    "03_cinico": (
        "Hombre latino joven, comediante de stand-up cinico y desencantado, "
        "tono burlon y cansado, como quien ya vio esta estupidez mil veces, "
        "pausas de comediante antes del remate"),
    "04_cizanero": (
        "Hombre latino, amigo cizanero que se rie por lo bajo mientras te "
        "cuenta que la cagaste, tono complice y burlon, casi susurrado, "
        "risita contenida entre frases"),
    "05_feriante": (
        "Hombre latino, presentador de feria exagerado y teatral, tono de "
        "vendedor de circo que se burla del publico, muy expresivo, "
        "alarga las vocales en los remates"),
    "06_condescendiente": (
        "Hombre latino, tono condescendiente y paternalista, explica como si "
        "hablara con alguien muy tonto, sarcasmo elegante y calmado, "
        "sonrisa audible en la voz"),
}


# VARIANTES DEL ANGULO "CINICO" (el elegido), todas MASCULINAS.
# Decir "hombre latino joven" no basta: VoiceDesign disena una voz nueva en cada
# generacion y con una pista de genero debil devuelve timbres ambiguos o
# femeninos. Hay que cargar la descripcion de rasgos fisicos del aparato vocal
# (grave, pecho, barba, treintañero), no solo la etiqueta "hombre".
VOCES_CINICO = {
    "c1_grave_seco": (
        "Voz de HOMBRE adulto, masculina y grave, registro de barítono con "
        "cuerpo y resonancia de pecho. Comediante cínico y desencantado, "
        "humor seco, ritmo pausado, pausas antes del remate. Espanol NEUTRO "
        "de doblaje latinoamericano, sin acento regional marcado, sin sesear "
        "ni cecear a la espanola. Nada agudo, nada juvenil, nada femenino"),
    "c2_treintanero": (
        "Voz de HOMBRE de unos treinta y cinco anios, masculina, timbre medio "
        "grave y algo rasposo. Tono cínico y cansado de quien ya vio esta "
        "estupidez mil veces, ironía tranquila. Espanol NEUTRO de doblaje latinoamericano, sin acento regional marcado, sin sesear ni cecear a la espanola"),
    "c3_barbudo_bajo": (
        "Voz masculina GRAVE y profunda de hombre grande, pecho amplio, "
        "casi bajo. Sarcasmo tranquilo y burlón, habla despacio y seguro, "
        "se ríe por lo bajo. Espanol NEUTRO de doblaje latinoamericano, sin acento regional marcado, sin sesear ni cecear a la espanola. Registro claramente varonil"),
    "c4_fumador": (
        "Voz de HOMBRE maduro, masculina, ronca y rasposa de fumador, "
        "grave. Cinismo amargo y divertido, ironía mordaz, ritmo lento y "
        "arrastrado. Espanol NEUTRO de doblaje latinoamericano, sin acento regional marcado, sin sesear ni cecear a la espanola"),
    "c5_locutor_cinico": (
        "Voz masculina de locutor de radio nocturna, HOMBRE adulto, grave y "
        "aterciopelada, con autoridad. Tono cínico y burlón bajo una "
        "aparente calma profesional. Espanol NEUTRO de doblaje latinoamericano, sin acento regional marcado, sin sesear ni cecear a la espanola"),
    "c6_joven_afilado": (
        "Voz de HOMBRE joven adulto, masculina y clara pero de registro bajo, "
        "nada aguda. Sarcasmo afilado y rápido, remates cortantes, "
        "sonrisa audible de superioridad. Espanol NEUTRO de doblaje latinoamericano, sin acento regional marcado, sin sesear ni cecear a la espanola"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--language", default="Spanish")
    ap.add_argument("--set", dest="conjunto", default="registros",
                    choices=["registros", "cinico"],
                    help="'registros' = 6 angulos distintos de sarcasmo; "
                         "'cinico' = variantes masculinas del angulo cinico")
    a = ap.parse_args()

    import torch
    import numpy as np
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
    print(f"[casting] device={device}", file=sys.stderr)
    model = Qwen3TTSModel.from_pretrained(MODEL, device_map=device, dtype=dtype)

    text = Path(a.text_file).read_text(encoding="utf-8").strip()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    conjunto = VOCES_CINICO if a.conjunto == "cinico" else VOCES
    for nombre, instruct in conjunto.items():
        wavs, sr = model.generate_voice_design(
            text=text, language=a.language, instruct=instruct)
        dest = out_dir / f"{nombre}.wav"
        sf.write(str(dest), np.asarray(wavs[0]), sr)
        print(f"[casting] {dest.name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
