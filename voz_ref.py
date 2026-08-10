"""Prueba una muestra de voz de referencia y la deja instalada si convence.

Chatterbox no inventa la interpretacion: la copia del clip de
`assets/voice_refs/<lang>.wav`. Con la muestra que habia (generada con
edge-tts) el techo era una lectura plana -- se estaba clonando la prosodia de
otro TTS. Cambiar esa muestra es la palanca real sobre el "suena sin vida"; los
parametros de exageracion son el ultimo 20%.

    py voz_ref.py probar <audio> --desde 1:23 --dur 20
    py voz_ref.py instalar <audio> --desde 1:23 --dur 20

`probar` corta el fragmento, sintetiza una frase de prueba y deja los dos
archivos en .flow_inspect/ para compararlos de oido. `instalar` ademas lo copia
a assets/voice_refs/es.wav y **borra la cache de voces**, porque si no los
guiones ya sintetizados siguen saliendo con la voz vieja.

Que buscar en el fragmento (importa mas que el locutor):
  - 15-20s, UNA sola voz, sin musica ni efectos, sin saturar;
  - un pasaje con rango: que suba y baje, no descripcion plana. La energia que
    copia el modelo es la del fragmento, no la del libro entero;
  - consonantes limpias; si el audio esta comprimido o lejano, sale turbio.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / ".flow_inspect"
FRASE = (
    "Confiaste tu plata a la firma mas grande del pais. "
    "Y un lunes, sin avisar, ya no existia."
)


def _arg(flag: str, default=None):
    if flag in sys.argv:
        return sys.argv[sys.argv.index(flag) + 1]
    return default


def cortar(src: Path, desde: str, dur: str, dst: Path) -> None:
    # mono 24k: es lo que espera Chatterbox y evita que el remuestreo se coma
    # los agudos, que es justo donde vive la dic­cion
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            desde,
            "-i",
            str(src),
            "-t",
            dur,
            "-ac",
            "1",
            "-ar",
            "24000",
            str(dst),
        ],
        check=True,
        timeout=300,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in ("probar", "instalar"):
        print(__doc__)
        return 1
    modo, src = sys.argv[1], Path(sys.argv[2]).resolve()
    if not src.exists():
        print(f"no existe {src}")
        return 1
    OUT.mkdir(exist_ok=True)
    frag = OUT / "ref_candidata.wav"
    cortar(src, _arg("--desde", "0"), _arg("--dur", "20"), frag)
    print(f"fragmento: {frag}")

    sys.path.insert(0, str(ROOT))
    import pipeline as pl

    destino = pl.CHATTERBOX_REF_DIR / "es.wav"
    backup = None
    if destino.exists():
        backup = destino.with_suffix(".wav.bak")
        shutil.copyfile(destino, backup)
    pl.CHATTERBOX_REF_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(frag, destino)

    # la cache esta indexada por (texto, ref, params): al cambiar la ref la
    # clave cambia sola, pero se limpia igual para no acumular
    prueba = OUT / "voz_prueba.wav"
    try:
        pl._chatterbox_tts(
            FRASE,
            "cb_es",
            prueba,
            exaggeration=float(_arg("--exag", 0.7)),
            cfg=float(_arg("--cfg", 0.25)),
        )
        print(f"prueba sintetizada: {prueba}")
    except Exception as e:
        print(f"fallo la sintesis: {e}")
        if backup:
            shutil.copyfile(backup, destino)
        return 1

    if modo == "probar" and backup:
        shutil.copyfile(backup, destino)
        print("(muestra anterior restaurada; usa 'instalar' si te convence)")
    elif modo == "instalar":
        cache = ROOT / "assets" / "cache" / "voices"
        if cache.exists():
            shutil.rmtree(cache, ignore_errors=True)
        print(f"instalada como {destino} y cache de voces limpiada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
