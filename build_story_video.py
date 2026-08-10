"""Voz + subtitulos para el formato "historia sobre gameplay a pantalla completa".

No usa la etapa MEDIA de pipeline.py: en este formato no hay imagenes de escena,
el fondo entero es un gameplay CC-BY. Solo hace falta
TTS -> recorte de silencios -> pausas dramaticas -> .ass con keywords en rojo.

    py build_story_video.py scripts/the-visitor-log.json output/2026-08-01-visitor-log \\
        --pausa "My aunt had signed in twice=0.6" --pausa "She did not stand up=0.7"

Imprime al final los segundos exactos de cada pausa, que son los que hay que
meter en el `enable=` de la desaturacion y en los `adelay` de los golpes graves
del comando de composicion (ver ESTADO_SESION.md).
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import pipeline as P  # noqa: E402


def find_word_start(words, frase: str) -> float | None:
    """Instante de la primera palabra de `frase` en la lista de timestamps."""
    limpiar = lambda w: w.lower().strip(".,;:!?\"'")  # noqa: E731
    objetivo = [limpiar(w) for w in frase.split()]
    limpio = [(s, limpiar(w)) for s, _e, w in words]
    for i in range(len(limpio) - len(objetivo) + 1):
        if [w for _s, w in limpio[i : i + len(objetivo)]] == objetivo:
            return limpio[i][0]
    return None


def insertar_pausas(voice_path: Path, words, cortes):
    """Mete silencio real en el audio y desplaza los timestamps posteriores.

    Va DESPUES de trim_silence_inplace a proposito: el recorte se comeria estas
    pausas. Son los unicos silencios del guion donde el silencio es informacion
    y no aire de TTS, asi que se ponen a mano y donde toca.
    """
    filtros, partes, prev = [], [], 0.0
    for idx, (t, dur) in enumerate(cortes):
        filtros.append(f"[0:a]atrim=start={prev}:end={t},asetpts=PTS-STARTPTS[a{idx}]")
        filtros.append(f"anullsrc=r=24000:cl=mono,atrim=duration={dur}[s{idx}]")
        partes += [f"[a{idx}]", f"[s{idx}]"]
        prev = t
    n = len(cortes)
    filtros.append(f"[0:a]atrim=start={prev},asetpts=PTS-STARTPTS[a{n}]")
    partes.append(f"[a{n}]")
    filtros.append("".join(partes) + f"concat=n={len(partes)}:v=0:a=1[out]")

    tmp = voice_path.with_name("voice_paused.mp3")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(voice_path),
            "-filter_complex",
            ";".join(filtros),
            "-map",
            "[out]",
            "-ar",
            "24000",
            str(tmp),
        ],
        check=True,
        timeout=300,
    )
    tmp.replace(voice_path)

    def shift(t: float) -> float:
        return t + sum(d for c, d in cortes if c <= t)

    return [(shift(s), shift(e), w) for s, e, w in words]


def voz_chatterbox(
    script: str,
    out: Path,
    exaggeration: float,
    ref: str = "",
    cfg: float = 0.5,
    cadena: str = "",
):
    """Voz con Chatterbox + timestamps REALES por alineacion con Whisper.

    Chatterbox suena mucho mas humano que edge-tts y admite control de
    exageracion, pero NO devuelve tiempos por palabra, y todo lo aguas abajo
    (karaoke, keywords en rojo, pausas, desaturacion, golpes) depende de ellos.
    La salida es reconocer el propio audio ya sintetizado: el timing acustico
    de verdad, no una estimacion por longitud de caracter.

    Contrapartida que hay que vigilar: el texto de los subtitulos pasa a ser lo
    que Whisper OYE, no lo que se escribio. Si transcribe mal una palabra, sale
    mal en pantalla. Por eso se compara contra el guion y se avisa.
    """
    import sys as _sys

    _sys.path.insert(0, str(ROOT))
    import viral_lab as V

    import hashlib

    key = hashlib.sha1(f"{script}|{ref}|{exaggeration}|{cfg}|en".encode()).hexdigest()[
        :16
    ]
    cache = ROOT / "assets" / "cache" / "voices" / f"{key}.wav"
    wav = out / "voice_chatterbox.wav"
    if cache.exists():
        shutil.copyfile(cache, wav)
        print("  voz Chatterbox desde cache")
    else:
        txt = out / "_t.txt"
        txt.write_text(script, encoding="utf-8")
        cmd = [
            "uv",
            "run",
            "--directory",
            str(ROOT / "tools" / "chatterbox_tts"),
            "synth.py",
            "--text-file",
            str(txt.resolve()),
            "--out",
            str(wav.resolve()),
            "--exaggeration",
            str(exaggeration),
            "--cfg",
            str(cfg),
            "--lang",
            "en",
        ]
        if ref:
            cmd += ["--ref", str((ROOT / ref).resolve())]
        subprocess.run(cmd, check=True, timeout=3600)
        txt.unlink(missing_ok=True)
        cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(wav, cache)
    mp3 = out / "voice.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-ar", "44100", str(mp3)],
        check=True,
        timeout=600,
    )
    words = V._align_words(mp3)
    if not words:
        raise RuntimeError("Whisper no devolvio ninguna palabra alineada")

    limpiar = lambda t: re.sub(r"[^a-z0-9']+", " ", t.lower()).split()  # noqa: E731
    esperadas, oidas = limpiar(script), limpiar(" ".join(w for _s, _e, w in words))
    faltan = len(esperadas) - len(oidas)
    if abs(faltan) > max(3, len(esperadas) * 0.03):
        print(
            f"  AVISO: el guion tiene {len(esperadas)} palabras y Whisper oyo "
            f"{len(oidas)}. Los subtitulos muestran lo OIDO, asi que revisa el "
            f".ass antes de renderizar."
        )
    return mp3, words


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("script_json")
    ap.add_argument("out_dir")
    ap.add_argument(
        "--pausa",
        action="append",
        default=[],
        help='"frase literal del guion=segundos", repetible',
    )
    ap.add_argument("--tts", choices=["edge", "chatterbox"], default="edge")
    ap.add_argument(
        "--exaggeration",
        type=float,
        default=0.62,
        help="solo con --tts chatterbox; <0.5 lee plano, >0.7 sobreactua",
    )
    ap.add_argument("--ref", default="", help="wav de referencia para clonar voz")
    ap.add_argument("--voice", default=P.DEFAULT_VOICE)
    ap.add_argument("--rate", default="+8%")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(args.script_json).read_text(encoding="utf-8"))

    P._check_open_hook(
        data["script"],
        data.get("title", ""),
        data.get("hook_card", ""),
        data.get("formato", ""),
    )
    P._check_payoff_spacing(data["script"], data.get("payoffs"))
    P._check_relleno_inicial(data["script"])
    P._check_ventana_critica(data["script"], data.get("payoffs"))
    P._check_apuesta_cotidiana(data["script"], args.script_json)

    if args.tts == "chatterbox":
        ex = (data.get("voz") or {}).get("exaggeration", args.exaggeration)
        v = data.get("voz") or {}
        voice, words = voz_chatterbox(
            data["script"],
            out,
            ex,
            args.ref or v.get("ref", ""),
            v.get("cfg", 0.5),
            v.get("cadena", ""),
        )
    else:
        voice, words = P.generate_audio(data["script"], args.voice, args.rate, out)
    voice, words = P.trim_silence_inplace(voice, words)

    cortes = []
    for spec in args.pausa:
        frase, _, dur = spec.rpartition("=")
        t = find_word_start(words, frase)
        if t is None:
            print(f"  AVISO: no encontre {frase!r} en el guion, sin pausa")
            continue
        cortes.append((t, float(dur)))
    cortes.sort()
    if cortes:
        words = insertar_pausas(voice, words, cortes)

    total = P.ffprobe_duration(voice)
    ass = P.generate_subtitles(words, out, keywords=data.get("caption_keywords"))
    rojas = len(re.findall(re.escape(P._CAP_RED), ass.read_text(encoding="utf-8")))

    (out / "script.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "title.txt").write_text(data["title"], encoding="utf-8")

    print(
        f"\nvoz {total:.2f}s | {rojas}/{len(words)} palabras en rojo "
        f"({rojas / len(words) * 100:.1f}%, objetivo ~5%)"
    )
    desp = 0.0
    print("silencios ya desplazados (para el enable= y los adelay=):")
    for t, dur in cortes:
        ini = t + desp
        print(f"  between(t,{ini:.2f},{ini + dur:.2f})   adelay={int(ini * 1000)}")
        desp += dur


if __name__ == "__main__":
    main()
