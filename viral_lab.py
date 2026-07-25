"""viral_lab.py — laboratorio de clips virales de terceros.

Sirve a dos cosas a la vez (por eso vive en este repo y no en otro):
  1. El canal de "nicho comentario": bajar un clip viral, ENTENDERLO y escribir
     encima un guion que NO narre lo que ya se ve.
  2. La investigacion de nicho (canales operadores, estructura de sus virales),
     que alimenta tambien a HiddenFacts.

Subcomandos:
  py viral_lab.py get <url> [--dir viral]
      Descarga el clip + su ficha de origen (autor, fecha, metricas, licencia
      declarada). La ficha NO es burocracia: es lo que permite dar credito y
      saber si un clip ya esta quemado por otros canales.

  py viral_lab.py read <url|carpeta> [--model M] [--whisper base] [--force]
      Lo COMPRENDE: Gemini analiza el video con timestamps (que se ve, donde
      esta el payout, riesgos), faster-whisper saca el audio original y
      PySceneDetect los cortes. Escribe analysis.json + analysis.md.

El campo que de verdad importa del analisis es `not_visible`: la informacion
que el espectador NO puede deducir mirando. Esa es la materia prima del guion,
porque narrar lo visible es el error #1 de este formato (mata la retencion: si
te cuento lo que ya ves, te vale mas ver el video en silencio).

Requiere GEMINI_API_KEY (la misma de Nano Banana) y FFmpeg en el PATH.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
DEFAULT_DIR = ROOT / "viral"

# Modelo de comprension de video. Flash sobra para esto (muestrea a 1 fps) y es
# barato; subir a un pro solo si el analisis sale pobre. Override por entorno.
VIDEO_MODEL = os.environ.get("GEMINI_VIDEO_MODEL", "gemini-3.6-flash")


def _key() -> str:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass
    k = os.getenv("GEMINI_API_KEY", "").strip()
    if not k:
        print("ERROR: falta GEMINI_API_KEY (.env o variable de entorno)")
        raise SystemExit(1)
    return k


def _run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Subprocess SIEMPRE con timeout: una corrida desatendida no puede colgarse
    para siempre en un ffmpeg atascado (misma regla que pipeline.py)."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")


def _write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------------- GET

def cmd_get(a) -> int:
    import yt_dlp

    base = Path(a.dir)
    base.mkdir(parents=True, exist_ok=True)

    # primero solo metadata: asi sabemos la carpeta destino antes de bajar nada
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as y:
        info = y.extract_info(a.url, download=False)

    slug = f"{info.get('extractor_key', 'web').lower()}-{info.get('id', 'x')}"
    out = base / slug
    video = out / "video.mp4"
    if video.exists() and not a.force:
        print(f"[get] ya estaba: {video}")
        return 0
    out.mkdir(parents=True, exist_ok=True)

    opts = {
        "quiet": True, "no_warnings": True,
        # mp4 hasta 1080p: es la fuente de un vertical, no hace falta mas
        "format": "bestvideo[height<=1920][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(out / "video.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(opts) as y:
        y.download([a.url])

    src = {
        "url": info.get("webpage_url") or a.url,
        "platform": info.get("extractor_key"),
        "id": info.get("id"),
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "uploader_url": info.get("uploader_url") or info.get("channel_url"),
        "upload_date": info.get("upload_date"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "license": info.get("license"),
        "description": (info.get("description") or "")[:1000],
        # credito listo para pegar en la descripcion del video que publiquemos:
        # el valor anadido nos cubre la politica, el credito cubre al creador
        "credit": f"Clip: {info.get('uploader') or '?'} — {info.get('webpage_url') or a.url}",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "permission": "none",  # cambiar a 'asked'/'granted' si se pide al creador
    }
    _write_json(out / "source.json", src)
    mb = video.stat().st_size / 1e6 if video.exists() else 0
    print(f"[get] {out}  ({mb:.1f} MB, {src['duration']}s, {src['view_count']} vistas)")
    print(f"[get] credito: {src['credit']}")
    return 0


# --------------------------------------------------------------------- READ

ANALYSIS_SCHEMA = """{
  "summary": "una frase: que pasa en el clip",
  "beats": [{"t": 0.0, "visible": "que se VE en ese segundo, sin interpretar"}],
  "payout": {"exists": true, "t": 0.0, "what": "el momento de resultado/satisfaccion"},
  "people_talking": false,
  "transformable": true,
  "transformable_reason": "por que si o por que no",
  "risk_flags": ["sangre|armas|petardos|peleas|menores|nsfw|marca comercial"],
  "watermark": {"present": false, "where": "esquina inferior derecha"},
  "not_visible": ["dato/contexto que el espectador NO puede deducir mirando"],
  "hook_ideas": ["primera frase posible, <15 palabras, curiosidad"],
  "best_cut": {"start": 0.0, "end": 0.0}
}"""

ANALYSIS_PROMPT = f"""Analiza este clip vertical corto para decidir si sirve como VIDEO BASE de un
short de comentario (se le pone voz en off narrando encima).

Reglas del formato, tenlas en cuenta al juzgar:
- Sirve si tiene PAYOUT: un resultado, una curiosidad que se resuelve al final.
  Un clip donde todos logran algo, o donde nadie lo logra, no sirve.
- Sirve si hay gente HACIENDO algo. Si son personas hablando a camara, no sirve.
- NO sirve si hay sangre, peleas, petardos, armas: tumban el video por normas.

Lo mas importante que tienes que producir es `not_visible`: cosas que un
espectador NO puede saber solo mirando (contexto, motivo, consecuencia, quien es
alguien, que pasa despues). Es la materia prima del guion, porque narrar lo que
ya se ve mata la retencion. Da 5-8 elementos, concretos, no genericos.

En `beats` describe lo que se VE cada 1-2 segundos, con timestamp real, sin
interpretar ni adornar.

Responde SOLO JSON valido con esta forma exacta:
{ANALYSIS_SCHEMA}"""


def _transcribe(video: Path, model_size: str) -> dict:
    """Audio original del clip (a veces trae dialogo que da contexto util).
    Falla suave: un clip sin voz o sin pista de audio no debe tumbar el analisis."""
    wav = video.with_name("audio.wav")
    try:
        r = _run(["ffmpeg", "-y", "-v", "error", "-i", str(video),
                  "-vn", "-ac", "1", "-ar", "16000", str(wav)], timeout=180)
        if r.returncode != 0 or not wav.exists():
            return {"text": "", "note": "sin pista de audio"}
        from faster_whisper import WhisperModel
        m = WhisperModel(model_size, device="cpu", compute_type="int8")
        segs, info = m.transcribe(str(wav), vad_filter=True)
        segs = list(segs)
        return {
            "language": info.language,
            "text": " ".join(s.text.strip() for s in segs).strip(),
            "segments": [{"t": round(s.start, 2), "text": s.text.strip()} for s in segs],
        }
    except Exception as e:
        return {"text": "", "note": f"transcripcion fallida: {e}"}
    finally:
        wav.unlink(missing_ok=True)


def _scenes(video: Path) -> list[float]:
    """Cortes del clip original. Opcional: si PySceneDetect no esta instalado se
    omite y no pasa nada (Gemini ya da los beats)."""
    try:
        from scenedetect import detect, ContentDetector
        return [round(s.get_seconds(), 2) for s, _ in detect(str(video), ContentDetector())]
    except ImportError:
        return []
    except Exception as e:
        print(f"[read] deteccion de escenas omitida: {e}")
        return []


def _gemini_read(video: Path, model: str) -> dict:
    """Comprension del video con Gemini (File API + 1 fps de muestreo)."""
    from google import genai

    client = genai.Client(api_key=_key())
    print(f"[read] subiendo {video.name} a la File API...")
    f = client.files.upload(file=str(video))
    for _ in range(60):  # el fichero tiene que estar ACTIVE antes de usarlo
        state = getattr(f.state, "name", str(f.state))
        if state == "ACTIVE":
            break
        if state == "FAILED":
            raise RuntimeError("Gemini no pudo procesar el video")
        time.sleep(3)
        f = client.files.get(name=f.name)
    print(f"[read] analizando con {model}...")
    resp = client.models.generate_content(
        model=model, contents=[f, ANALYSIS_PROMPT],
        config={"response_mime_type": "application/json"})
    txt = (resp.text or "").strip()
    try:
        client.files.delete(name=f.name)  # no dejar basura en la cuota
    except Exception:
        pass
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    return json.loads(txt)


def _frames(video: Path, n: int = 12) -> list[tuple[float, Path]]:
    """Muestrea n fotogramas repartidos por el clip. Es el plan B cuando Gemini
    no esta disponible: Claude no ingiere video, pero con una tira de fotogramas
    + la transcripcion + los cortes reconstruye lo esencial."""
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "csv=p=0", str(video)], timeout=60)
    dur = float((r.stdout or "0").strip() or 0)
    if dur <= 0:
        return []
    out = []
    tmp = video.parent / "_frames"
    tmp.mkdir(exist_ok=True)
    for i in range(n):
        t = dur * (i + 0.5) / n
        f = tmp / f"f{i:02d}.jpg"
        _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video),
              "-frames:v", "1", "-vf", "scale=512:-1", "-q:v", "4", str(f)], timeout=90)
        if f.exists():
            out.append((round(t, 2), f))
    return out


def _claude_read(video: Path, tr: dict, scenes: list[float]) -> dict:
    """Comprension por fotogramas con Claude. Menos fino que Gemini para el
    movimiento, pero suficiente para el veredicto (payout, riesgos, que NO se ve)
    y no depende de la cuota de Gemini."""
    import base64
    import anthropic

    frames = _frames(video)
    if not frames:
        raise RuntimeError("no pude extraer fotogramas del clip")
    print(f"[read] analizando {len(frames)} fotogramas con Claude...")
    content = []
    for t, f in frames:
        content.append({"type": "text", "text": f"--- t={t}s"})
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": "image/jpeg",
            "data": base64.b64encode(f.read_bytes()).decode()}})
    extra = ""
    if tr.get("text"):
        extra += f"\n\nAudio original transcrito: {tr['text'][:1500]}"
    if scenes:
        extra += f"\n\nCortes detectados en: {', '.join(str(s) for s in scenes[:40])}"
    content.append({"type": "text", "text": ANALYSIS_PROMPT +
                    "\n\nSolo tienes fotogramas muestreados, no el video completo: "
                    "infiere el movimiento entre ellos y di en `beats` lo que se ve "
                    "en cada fotograma con su timestamp." + extra})

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=os.environ.get("VIRAL_CLAUDE_MODEL", "claude-opus-4-8"),
        max_tokens=4000, thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": content}])
    txt = next((b.text for b in resp.content if b.type == "text"), None)
    for _, f in frames:
        f.unlink(missing_ok=True)
    (video.parent / "_frames").rmdir()
    if not txt:
        raise RuntimeError("Claude no devolvio texto")
    txt = txt.strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    return json.loads(txt[txt.find("{"):txt.rfind("}") + 1])


def _markdown(src: dict, an: dict, tr: dict, scenes: list[float]) -> str:
    L = [f"# {src.get('title') or src.get('id')}", ""]
    L.append(f"**Origen**: {src.get('credit')}")
    L.append(f"**Metricas**: {src.get('view_count')} vistas · {src.get('like_count')} likes "
             f"· {src.get('comment_count')} comentarios · {src.get('duration')}s")
    L.append("")
    L.append(f"> {an.get('summary', '')}")
    L.append("")
    p = an.get("payout") or {}
    ok = "SI" if an.get("transformable") else "NO"
    L.append(f"## Veredicto: {ok} sirve como video base")
    L.append(f"- {an.get('transformable_reason', '')}")
    L.append(f"- Payout: {'si, en ' + str(p.get('t')) + 's — ' + str(p.get('what')) if p.get('exists') else 'NO HAY'}")
    L.append(f"- Gente hablando: {'si (mala senal)' if an.get('people_talking') else 'no'}")
    if an.get("risk_flags"):
        L.append(f"- **Riesgos**: {', '.join(an['risk_flags'])}")
    w = an.get("watermark") or {}
    if w.get("present"):
        L.append(f"- Marca de agua: {w.get('where')} (hay que taparla)")
    bc = an.get("best_cut") or {}
    if bc.get("end"):
        L.append(f"- Mejor recorte: {bc.get('start')}s → {bc.get('end')}s")
    L.append("")
    L.append("## Materia prima del guion (lo que NO se ve)")
    for x in an.get("not_visible", []):
        L.append(f"- {x}")
    L.append("")
    L.append("## Ideas de hook")
    for x in an.get("hook_ideas", []):
        L.append(f"- {x}")
    L.append("")
    L.append("## Lo que se ve (no narrar esto)")
    for b in an.get("beats", []):
        L.append(f"- `{b.get('t')}s` {b.get('visible')}")
    if tr.get("text"):
        L.append("")
        L.append(f"## Audio original ({tr.get('language', '?')})")
        L.append(tr["text"][:2000])
    if scenes:
        L.append("")
        L.append(f"## Cortes del original ({len(scenes)})")
        L.append(", ".join(f"{s}s" for s in scenes))
    return "\n".join(L) + "\n"


def cmd_read(a) -> int:
    target = Path(a.target)
    if not target.exists():  # se acepta una url directa: baja y sigue
        print("[read] no es una carpeta, descargando primero...")
        g = argparse.Namespace(url=a.target, dir=a.dir, force=False)
        if cmd_get(g) != 0:
            return 1
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as y:
            info = y.extract_info(a.target, download=False)
        target = Path(a.dir) / f"{info.get('extractor_key', 'web').lower()}-{info.get('id', 'x')}"

    video = target / "video.mp4"
    if not video.exists():
        print(f"ERROR: no hay video.mp4 en {target}")
        return 1
    out_json = target / "analysis.json"
    if out_json.exists() and not a.force:
        print(f"[read] ya analizado: {out_json} (usa --force para rehacer)")
        return 0

    src = json.loads((target / "source.json").read_text(encoding="utf-8")) \
        if (target / "source.json").exists() else {}
    # el audio y los cortes van primero: alimentan al motor de fotogramas si toca
    tr = _transcribe(video, a.whisper)
    scenes = _scenes(video)

    engine = a.engine
    an = None
    if engine in ("auto", "gemini"):
        try:
            an = _gemini_read(video, a.model)
            engine = "gemini"
        except Exception as e:
            if a.engine == "gemini":
                raise
            # cuota agotada / modelo caido -> no bloquear el analisis, hay plan B
            print(f"[read] Gemini no disponible ({str(e)[:90]}); paso a fotogramas + Claude")
            an = None
    if an is None:
        an = _claude_read(video, tr, scenes)
        engine = "claude-frames"
    an["_engine"] = engine

    _write_json(out_json, {"source": src, "analysis": an, "transcript": tr, "scenes": scenes})
    (target / "analysis.md").write_text(_markdown(src, an, tr, scenes), encoding="utf-8")
    verdict = "SIRVE" if an.get("transformable") else "DESCARTAR"
    print(f"[read] {verdict} — {an.get('summary', '')[:80]}")
    print(f"[read] {target / 'analysis.md'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Laboratorio de clips virales de terceros")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("get", help="descarga un clip + su ficha de origen")
    g.add_argument("url")
    g.add_argument("--dir", default=str(DEFAULT_DIR))
    g.add_argument("--force", action="store_true")
    g.set_defaults(func=cmd_get)

    r = sub.add_parser("read", help="analiza un clip (Gemini + whisper + escenas)")
    r.add_argument("target", help="carpeta de viral/ o una url directa")
    r.add_argument("--dir", default=str(DEFAULT_DIR))
    r.add_argument("--model", default=VIDEO_MODEL)
    r.add_argument("--engine", choices=["auto", "gemini", "claude"], default="auto",
                    help="auto = Gemini (video real) y si no hay cuota cae a "
                         "fotogramas + Claude")
    r.add_argument("--whisper", default="base", help="tamano del modelo faster-whisper")
    r.add_argument("--force", action="store_true")
    r.set_defaults(func=cmd_read)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
