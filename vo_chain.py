"""Cadena de locucion: convierte una salida cruda de TTS en voz de narrador.

Escrito el 1 ago 2026. La observacion que lo motiva: Chatterbox ya suena humano,
pero sigue sonando a TTS. La diferencia con un locutor profesional casi nunca
esta en la garganta, esta en lo que pasa DESPUES del microfono:

  1. Efecto de proximidad -- hablar pegado a un cardioide sube los graves. Es lo
     que hace que una voz suene "grande" y cercana en vez de plana. Se imita con
     un shelf bajo, no con un boost de graves a lo bruto (eso embarra).
  2. Compresion fuerte -- es el ingrediente que mas se nota y el que nadie
     aplica. En locucion la palabra floja y la fuerte llegan igual de presentes;
     sin comprimir, el TTS baja de volumen a mitad de frase y el oido lo lee
     como "grabacion casera".
  3. De-esser -- las eses de los modelos neuronales pican, sobre todo en
     auriculares. Aqui se hace con un shelf negativo estrecho, que es una
     aproximacion; un de-esser real es dinamico.
  4. Presencia en 3-4 kHz -- es la banda de la inteligibilidad. El 90% de los
     Shorts se ven en el altavoz de un movil, que no da graves: si la voz no
     tiene presencia ahi, se pierde debajo de la musica.
  5. loudnorm a -14 LUFS -- el objetivo de YouTube. Sin esto, o YouTube te baja
     el volumen al normalizar, o vas mas bajo que el resto del feed, que es
     peor: el espectador percibe un video flojo antes de entender por que.

    py vo_chain.py voice.mp3                       # sobrescribe, guarda voice_pre.mp3
    py vo_chain.py voice.mp3 --out narrada.mp3 --preset intimo

Presets: `narrador` (por defecto, seco y presente), `intimo` (mas cuerpo y mas
compresion, para historias en primera persona), `crudo` (solo loudnorm, para
comparar A/B y comprobar que la cadena aporta algo).
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PRESETS = {
    # (shelf graves dB, presencia dB, ratio compresor, umbral compresor)
    "narrador": (2.5, 3.0, 4.0, 0.05),
    "intimo":   (4.0, 2.5, 6.0, 0.035),
    "crudo":    (0.0, 0.0, 1.0, 1.0),
}


def sample_rate(p: Path) -> int:
    """El sample rate REAL del archivo. `asetrate` lo necesita exacto: con un
    valor supuesto, en vez de bajar el tono lo SUBE y ademas cambia la duracion.
    Bug real del 1 ago 2026 -- se asumio 44100 sobre un fichero de 24 kHz y la
    voz salio mas aguda y a la mitad de largo."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                        "-show_entries", "stream=sample_rate", "-of",
                        "default=nk=1:nw=1", str(p)],
                       capture_output=True, text=True, timeout=60)
    return int(r.stdout.strip() or 44100)


def cadena(preset: str, semitonos: float = 0.0, sr: int = 44100) -> str:
    graves, presencia, ratio, umbral = PRESETS[preset]
    f = []
    if semitonos:
        # Baja tono Y formantes a la vez. Es lo correcto: una voz masculina no
        # es solo mas grave, es un tracto vocal mas largo, y eso mueve tambien
        # las resonancias. Un pitch-shift que conserva formantes suena a efecto
        # ("voz de pozo"); este suena a otra persona.
        # Por encima de ~4 semitonos empieza a arrastrar y se nota el proceso.
        r = 2 ** (-semitonos / 12)
        f += [f"asetrate={int(sr * r)}", f"aresample={sr}",
              f"atempo={1/r:.6f}"]               # devuelve la duracion original
    f.append("highpass=f=80")                    # fuera rumble y pops
    if graves:
        f.append(f"equalizer=f=160:t=q:w=0.9:g={graves}")     # proximidad
    if preset != "crudo":
        f.append("equalizer=f=300:t=q:w=1.2:g=-2")            # quita el barro
        f.append(f"equalizer=f=3500:t=q:w=1.4:g={presencia}") # inteligibilidad
        f.append("equalizer=f=7200:t=q:w=2.0:g=-3")           # de-ess aproximado
        f.append(f"acompressor=threshold={umbral}:ratio={ratio}:"
                 f"attack=5:release=120:makeup=2")
    f.append("loudnorm=I=-14:TP=-1.5:LRA=11")    # objetivo de YouTube
    return ",".join(f)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio")
    ap.add_argument("--out", help="por defecto sobrescribe, guardando el crudo como *_pre")
    ap.add_argument("--preset", choices=list(PRESETS), default="narrador")
    ap.add_argument("--grave", type=float, default=0.0,
                    help="semitonos a bajar tono Y formantes; 2-3 masculiniza, "
                         ">4 empieza a sonar procesado")
    a = ap.parse_args()

    src = Path(a.audio)
    if a.out:
        dst, crudo = Path(a.out), src
    else:
        crudo = src.with_name(f"{src.stem}_pre{src.suffix}")
        if not crudo.exists():
            shutil.copyfile(src, crudo)
        dst = src

    tmp = dst.with_name(f"_tmp_{dst.name}")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(crudo),
                    "-af", cadena(a.preset, a.grave, sample_rate(crudo)), "-ar", "44100", "-b:a", "192k",
                    str(tmp)], check=True, timeout=900)
    tmp.replace(dst)
    extra = f" -{a.grave:g} semitonos" if a.grave else ""
    print(f"{a.preset}{extra}: {crudo.name} -> {dst.name}")


if __name__ == "__main__":
    main()
