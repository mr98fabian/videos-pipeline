"""Voz + las 52 laminas del formato LARGO de KOREX, listas para `korex_largo.py`.

Existe porque el largo no pasa por `pipeline.main()`: alli una imagen equivale a
una frase, y aqui una imagen aguanta dos frases y viene descrita en el bloque
`imagenes` del guion, no en `search_terms`. Hasta ahora este paso se hacia a
mano y no quedaba escrito en ningun sitio.

Dos cosas son deliberadas:

* **Converge por rondas insistiendo solo en lo que falta.** Flow falla de forma
  intermitente y sin patron -- misma peticion, una vez sale y otra dice "no se
  pudo generar". Un intento por lamina deja huecos; reintentar mas fuerte dentro
  de la misma corrida, tampoco basta (ver korex_fill.py).
* **La identidad de Tadeo viaja igual que en el Short**: hoja madre como
  ingrediente de referencia + CHARACTER_LOCK literal, palabra por palabra. Si
  se reescribe aqui, la marca diverge entre formatos.

Uso:
    py korex_largo_imagenes.py output/<carpeta> --guion scripts/<x>.json
    py korex_largo_imagenes.py output/<carpeta> --guion scripts/<x>.json --solo-voz
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

ASPECTO = "16:9"          # el largo es apaisado; el Short es 9:16
RONDAS = 4
PREFIJO_TADEO = "Tadeo character:"


def _log(etapa: str, msg: str) -> None:
    print(f"[{etapa}] {msg}", flush=True)


def voz(carpeta: Path, guion: dict, voice: str = "qw_korex") -> Path:
    """Sintetiza la narracion completa. Cacheada por hash aguas abajo, asi que
    volver a lanzar el script no vuelve a pagar el TTS."""
    mp3 = carpeta / "voice.mp3"
    if mp3.exists():
        _log("voz", f"ya estaba: {mp3.name}")
        return mp3
    import pipeline

    wav = carpeta / "voice.wav"
    _log("voz", f"sintetizando {len(guion['script'].split())} palabras con {voice}...")
    pipeline._qwen_tts(guion["script"], voice, wav)
    pipeline.run(["ffmpeg", "-y", "-i", str(wav), "-ar", "44100", str(mp3)])
    _log("voz", f"listo: {mp3.name}")
    return mp3


def _prompt(texto: str, estilo: str) -> tuple[str, list[Path]]:
    """Monta el prompt de una lamina con las mismas piezas que usa el Short."""
    import kx_cast

    refs: list[Path] = []
    term = texto.strip()
    if term.startswith(PREFIJO_TADEO):
        term = term[len(PREFIJO_TADEO):].strip()
        hoja = kx_cast._canonical_sheet("tadeo")
        if hoja and Path(hoja).exists():
            refs.append(Path(hoja))
            term = f"{term}. {kx_cast.CHARACTER_LOCK}"
    # secundarios con hoja madre propia (la Bruja del Banco y demas)
    sec_refs, sec_lock = kx_cast.secondary_refs(term)
    if sec_refs:
        refs.extend(sec_refs)
        if sec_lock:
            term = f"{term}. {sec_lock}"
    # figuras historicas: sin hoja, la identidad viaja entera en palabras
    hist = kx_cast.historical_lock(term)
    if hist:
        term = f"{term}. {hist}"
    return f"{term}. {estilo}. {kx_cast.SIN_TEXTO}", refs


def laminas(carpeta: Path, guion: dict) -> None:
    import flow_automation

    destino = carpeta / "storyboard"
    destino.mkdir(parents=True, exist_ok=True)
    estilo = guion["style"]
    total = len(guion["imagenes"])

    for ronda in range(1, RONDAS + 1):
        pendientes = [im for im in guion["imagenes"]
                      if not (destino / f"img_{im['i']:02d}.png").exists()]
        if not pendientes:
            break
        _log("flow", f"ronda {ronda}/{RONDAS}: faltan {len(pendientes)} de {total}")
        for im in pendientes:
            salida = destino / f"img_{im['i']:02d}.png"
            prompt, refs = _prompt(im["imagen"], estilo)
            _log("flow", f"img_{im['i']:02d} <- {im['imagen'][:70]}")
            try:
                flow_automation.generate_image(
                    prompt, salida,
                    reference_images=refs or None,
                    aspect_ratio=ASPECTO,
                )
            except Exception as e:                      # Flow falla soft a proposito
                _log("flow", f"img_{im['i']:02d}: {type(e).__name__}: {e}")

    faltan = sorted(im["i"] for im in guion["imagenes"]
                    if not (destino / f"img_{im['i']:02d}.png").exists())
    if faltan:
        # No es un aviso: `korex_largo` aborta igualmente, y montar con huecos
        # es justo el fallo silencioso que costo cuatro videos en agosto.
        raise SystemExit(f"[flow] siguen faltando tras {RONDAS} rondas: {faltan}")
    _log("flow", f"{total}/{total} laminas listas en {destino}")


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    carpeta = Path(argv[0])
    carpeta.mkdir(parents=True, exist_ok=True)
    guion_path = Path(argv[argv.index("--guion") + 1])
    guion = json.loads(guion_path.read_text("utf-8"))

    voz(carpeta, guion)
    if "--solo-voz" not in argv:
        laminas(carpeta, guion)
    print(f"\nAhora: py korex_largo.py {carpeta} --guion {guion_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
