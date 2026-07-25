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


def _load_env() -> None:
    """Carga .env una vez al arrancar. Sin esto el SDK de Anthropic no encuentra
    la clave y revienta con un TypeError poco claro."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass


def _key() -> str:
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
    # Instagram no devuelve duracion ni vistas por yt-dlp: la duracion la sacamos
    # del fichero, y las vistas hay que traerlas del radar (vidiq xoutliers)
    if not src["duration"] and video.exists():
        src["duration"] = round(_duration(video), 1)
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
        # Whisper ALUCINA sobre pistas de solo musica (devuelve cosas como
        # "gracias por ver el video" en un idioma random). Si apenas hay voz
        # respecto a la duracion del clip, es musica: mejor nada que un texto
        # inventado, que ademas contaminaria el analisis del guion.
        speech = sum(s.end - s.start for s in segs)
        dur = _duration(video)
        if speech < 1.5 or (dur and speech / dur < 0.12):
            return {"text": "", "note": "sin voz (pista de musica)"}
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


def _duration(video: Path) -> float:
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "csv=p=0", str(video)], timeout=60)
    try:
        return float((r.stdout or "0").strip() or 0)
    except ValueError:
        return 0.0


def _frames_at(video: Path, times: list[float], width: int = 512) -> list[tuple[float, Path]]:
    """Extrae un fotograma en cada instante pedido."""
    out = []
    tmp = video.parent / "_frames"
    tmp.mkdir(exist_ok=True)
    for i, t in enumerate(times):
        f = tmp / f"f{i:02d}.jpg"
        _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video),
              "-frames:v", "1", "-vf", f"scale={width}:-1", "-q:v", "4", str(f)], timeout=90)
        if f.exists():
            out.append((round(t, 2), f))
    return out


def _drop_frames(frames: list[tuple[float, Path]]) -> None:
    for _, f in frames:
        f.unlink(missing_ok=True)
    if frames:
        try:
            frames[0][1].parent.rmdir()
        except OSError:
            pass


def _frames(video: Path, n: int = 12) -> list[tuple[float, Path]]:
    """Muestrea n fotogramas repartidos por el clip. Es el plan B cuando Gemini
    no esta disponible: Claude no ingiere video, pero con una tira de fotogramas
    + la transcripcion + los cortes reconstruye lo esencial."""
    dur = _duration(video)
    if dur <= 0:
        return []
    return _frames_at(video, [dur * (i + 0.5) / n for i in range(n)])


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
    _drop_frames(frames)
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


# --------------------------------------------------------------------- FIND

# Nicho del canal de comentario: fitness/gimnasio en ingles (decision 25 jul
# 2026). Editar aqui si cambia; cada consulta cuesta ~5 creditos de vidIQ.
NICHE_QUERIES = [
    "gym strength challenge heavy lift",
    "fitness challenge fail vs success",
    "strongman feat of strength",
]
AUDIENCE = "Culture/Region: US/Western Europe; Global: true"

# senales de que el clip NO se puede transformar: alguien hablando a camara.
# El formato necesita gente HACIENDO algo, la voz en off la ponemos nosotros.
_TALKING = ("talking head", "voiceover", "voice-over", "speaking to camera",
            "dialogue", "narration", "interview", "storytime", "podcast")
_RISKY = ("blood", "fight", "firework", "gun", "weapon", "injury", "knockout")


def _num(s: str) -> float:
    """'1.1M' -> 1100000.0 ; '5.2K' -> 5200.0"""
    s = s.strip().upper().replace(",", "")
    mult = {"K": 1e3, "M": 1e6, "B": 1e9}.get(s[-1:], 1)
    try:
        return float(s[:-1]) * mult if mult > 1 else float(s)
    except ValueError:
        return 0.0


def _parse_outliers(md: str) -> list[dict]:
    """El endpoint de outliers cross-plataforma devuelve MARKDOWN, no JSON (por
    eso no se puede usar call_json). Se parsea por bloques: cada candidato
    empieza en una linea '**@handle** — "caption"'."""
    import re
    platform = "instagram"
    items, cur = [], None
    for raw in md.splitlines():
        ln = raw.rstrip()
        if ln.startswith("## "):
            platform = ln[3:].strip().lower()
            continue
        m = re.match(r'\*\*@([\w.\-]+)\*\*\s*—\s*"?(.*)', ln)
        if m:
            if cur:
                items.append(cur)
            cur = {"platform": platform, "handle": m.group(1),
                   "caption": m.group(2).strip('"'), "fields": {}}
            continue
        if cur is None:
            continue
        m = re.search(r"([\d.,]+[KMB]?)\s+views\s*\((\d+(?:\.\d+)?)x their median of ([\d.,]+[KMB]?)\)"
                      r"(?:\s*·\s*([\d.,]+[KMB]?)\s+followers)?", ln)
        if m:
            cur.update(views=_num(m.group(1)), multiplier=float(m.group(2)),
                       median=_num(m.group(3)), followers=_num(m.group(4) or "0"))
            continue
        m = re.match(r"\s*(reel|tiktok|post|video|short):\s*([\w\-]+)", ln)
        if m:
            cur["kind"], cur["vid"] = m.group(1), m.group(2)
            continue
        m = re.match(r"\s*\*\*(\w+)\*\*:\s*(.*)", ln)
        if m and m.group(2).strip():
            cur["fields"][m.group(1)] = m.group(2).strip()
            continue
        m = re.match(r"\s+(\w+):\s*(.+)", ln)
        if m:
            cur["fields"][m.group(1)] = m.group(2).strip()
    if cur:
        items.append(cur)
    return [i for i in items if i.get("vid")]


def _url_of(it: dict) -> str:
    if it["platform"].startswith("tiktok"):
        return f"https://www.tiktok.com/@{it['handle']}/video/{it['vid']}"
    return f"https://www.instagram.com/reel/{it['vid']}/"


def _judge(it: dict) -> tuple[float, list[str]]:
    """Puntua y marca descartes. El multiplicador sobre la mediana DEL PROPIO
    creador es la mejor senal: significa que el video se disparo solo, no que el
    creador tenga audiencia. Un 200x de una cuenta de 7K vale mas que 1M vistas
    de una cuenta de 2M."""
    blob = " ".join([it.get("caption", ""), *it.get("fields", {}).values()]).lower()
    flags = []
    if any(w in blob for w in _TALKING):
        flags.append("habla-a-camara")
    if any(w in blob for w in _RISKY):
        flags.append("riesgo-normas")
    if "music only" not in blob and "audio_mix" in it.get("fields", {}):
        flags.append("audio-con-voz")
    score = it.get("multiplier", 0)
    if it.get("views", 0) >= 1e6:
        score *= 1.15  # volumen ya probado, no solo anomalia estadistica
    if flags:
        score *= 0.25
    return round(score, 1), flags


def cmd_find(a) -> int:
    import vidiq_tools as v

    queries = a.query or NICHE_QUERIES
    print(f"[find] {len(queries)} consultas (~{len(queries) * 5} creditos vidIQ)")
    seen, rows = set(), []
    for q in queries:
        try:
            md = v.call("vidiq_instagram_tiktok_outlier_search", {
                "query": q, "audienceQuery": AUDIENCE,
                "resultsPerPlatform": a.limit, "collapseByCreator": True})
        except Exception as e:
            print(f"[find] fallo '{q}': {e}")
            continue
        for it in _parse_outliers(md):
            if it["vid"] in seen:
                continue
            seen.add(it["vid"])
            it["url"] = _url_of(it)
            it["query"] = q
            it["score"], it["flags"] = _judge(it)
            # ya descargado en una corrida anterior -> no volver a proponerlo
            it["done"] = (Path(a.dir) / f"{it['platform'].split()[0]}-{it['vid']}").exists()
            rows.append(it)

    rows.sort(key=lambda r: -r["score"])
    Path(a.dir).mkdir(parents=True, exist_ok=True)
    _write_json(Path(a.dir) / "queue.json", rows)

    print(f"\n{'score':>6} {'xmed':>6} {'vistas':>9}  {'plataforma':10} candidato")
    for r in rows[:a.top]:
        mark = "·" if r["done"] else " "
        note = (" [" + ",".join(r["flags"]) + "]") if r["flags"] else ""
        concept = (r["fields"].get("reel_concept") or r["caption"])[:64].replace("\n", " ")
        print(f"{r['score']:>6} {r.get('multiplier', 0):>5}x {int(r.get('views', 0)):>9} "
              f"{r['platform'][:10]:10}{mark} @{r['handle'][:18]}{note}\n"
              f"        {concept}\n        {r['url']}")
    good = [r for r in rows if not r["flags"] and not r["done"]]
    print(f"\n[find] {len(rows)} candidatos, {len(good)} limpios sin procesar "
          f"-> {Path(a.dir) / 'queue.json'}")
    if good:
        print(f"[find] siguiente: py viral_lab.py read \"{good[0]['url']}\"")
    return 0


# -------------------------------------------------------------------- SCRIPT

WPS = 2.8  # palabras por segundo de una voz IA en ingles a ritmo natural

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "hook": {"type": "string", "description": "primera frase, <15 palabras, 0-3s"},
        "script": {"type": "string", "description": "guion completo para TTS, sin markdown"},
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"t": {"type": "number"}, "text": {"type": "string"}},
                "required": ["t", "text"], "additionalProperties": False,
            },
            "description": "cada frase con el segundo del CLIP en que debe sonar",
        },
        "invented": {"type": "array", "items": {"type": "string"},
                      "description": "todo lo que no se puede verificar del clip"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "pinned_comment": {"type": "string"},
    },
    "required": ["hook", "script", "lines", "invented", "title", "description",
                  "tags", "pinned_comment"],
    "additionalProperties": False,
}


def cmd_script(a) -> int:
    """Guion de voz en off a partir del analisis del clip.

    La regla que manda: NO narrar lo que se ve. El analisis ya separo las dos
    cosas -- `beats` es lo visible (prohibido) y `not_visible` es la materia
    prima (obligatorio). Sin esa separacion el guion sale describiendo la imagen,
    que es el error #1 del formato y lo que hunde la retencion."""
    import anthropic

    target = Path(a.target)
    aj = target / "analysis.json"
    if not aj.exists():
        print(f"ERROR: falta {aj} — corre primero: py viral_lab.py read {target}")
        return 2
    d = json.loads(aj.read_text(encoding="utf-8"))
    an, src = d["analysis"], d.get("source", {})
    if not an.get("transformable"):
        print(f"[script] OJO: el analisis descarto este clip ({an.get('transformable_reason', '')})")

    cut = an.get("best_cut") or {}
    clip_len = (cut.get("end") or src.get("duration") or 20) - (cut.get("start") or 0)
    seconds = a.seconds or max(round(clip_len), 22)
    words = int(seconds * WPS)
    payout = an.get("payout") or {}

    visible = "\n".join(f"- {b.get('t')}s: {b.get('visible')}" for b in an.get("beats", []))
    raw = "\n".join(f"- {x}" for x in an.get("not_visible", []))
    bait = ("\n- Mete UN error factual pequeno y facil de detectar (un numero, un lugar) "
            "para provocar correcciones en comentarios; listalo en `invented`."
            if a.bait else "")

    prompt = f"""Escribe la voz en off de un YouTube Short en INGLES sobre este clip.

CLIP: {an.get('summary', '')}
Duracion util: {clip_len:.1f}s (recorte {cut.get('start')}s a {cut.get('end')}s)
Payout (el momento de resultado) en {payout.get('t')}s: {payout.get('what')}

LO QUE SE VE — PROHIBIDO NARRAR ESTO:
{visible}

MATERIA PRIMA — de aqui sale el guion (lo que el espectador NO puede saber mirando):
{raw}

REGLAS DURAS:
- Nunca describas lo que la imagen ya muestra. Si el espectador puede verlo, no
  se dice. El valor de la voz es aportar lo que la imagen NO cuenta.
- HOOK en la primera frase (menos de 15 palabras): curiosidad que obligue a
  quedarse. No reveles el payout en el hook.
- Cuerpo: contexto, cifras, motivo, consecuencia — informacion que no se ve.
- Si el guion pasa de 28s, mete UN rehook a mitad con un conector ("but",
  "though", "here is the thing") que reencuadre lo anterior.
- El PAYOUT va al FINAL y cae justo cuando ocurre en el clip ({payout.get('t')}s).
  Despues del payout NO va nada explicativo: ni datos, ni contexto, ni resumen.
  Como mucho una frase corta y seca, o una pregunta.
- {words} palabras aproximadamente ({seconds}s de narracion).
- Texto plano para una voz IA: sin markdown, sin emojis, sin acotaciones.
- Lo que no puedas verificar del clip, inventalo plausible, pero listalo TODO en
  `invented` para poder revisarlo antes de publicar.{bait}

`lines`: reparte las frases con el segundo del CLIP en que deben sonar.
`pinned_comment`: un comentario del canal para fijar, que invite a responder algo
trivial (asi el video sigue corriendo mientras escriben). Ni insultante ni falso.
`title`: menos de 90 caracteres, curiosidad, sin clickbait mentiroso.
`tags`: 6-8, especificos."""

    print(f"[script] escribiendo ~{words} palabras para {seconds}s...")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=os.environ.get("VIRAL_CLAUDE_MODEL", "claude-opus-4-8"),
        max_tokens=4000, thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": SCRIPT_SCHEMA}},
        messages=[{"role": "user", "content": prompt}])
    txt = next((b.text for b in resp.content if b.type == "text"), None)
    if not txt:
        print("ERROR: Claude no devolvio texto")
        return 2
    sc = json.loads(txt)
    sc["source_credit"] = src.get("credit", "")
    sc["cut"] = cut
    sc["target_seconds"] = seconds
    _write_json(target / "script.json", sc)

    n = len(sc["script"].split())
    md = [f"# Guion — {sc['title']}", "", f"**{n} palabras ≈ {n / WPS:.1f}s**  ·  "
          f"recorte {cut.get('start')}s → {cut.get('end')}s", "",
          "## Narracion", ""]
    for ln in sc["lines"]:
        md.append(f"- `{ln['t']}s` {ln['text']}")
    md += ["", "## Texto seguido (TTS)", "", sc["script"], "",
           "## Comentario para fijar", "", sc["pinned_comment"], "",
           "## Inventado (revisar antes de publicar)", ""]
    md += [f"- {x}" for x in sc.get("invented", [])]
    md += ["", "## Publicacion", "", f"**Titulo**: {sc['title']}", "",
           sc["description"], "", f"`{', '.join(sc['tags'])}`", "",
           f"**Credito**: {sc['source_credit']}"]
    (target / "script.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[script] {n} palabras ({n / WPS:.1f}s) — {target / 'script.md'}")
    if sc.get("invented"):
        print(f"[script] {len(sc['invented'])} datos inventados: revisalos antes de publicar")
    return 0


# ---------------------------------------------------------------------- EDIT

# cajas de desenfoque por posicion declarada de la marca de agua, en el lienzo
# ya normalizado a 1080x1920 (x, y, w, h)
_WM_BOXES = {
    "superior derecha": (620, 60, 420, 190),
    "superior izquierda": (40, 60, 420, 190),
    "inferior derecha": (620, 1660, 420, 200),
    "inferior izquierda": (40, 1660, 420, 200),
    "superior": (240, 60, 600, 190),
    "inferior": (240, 1660, 600, 200),
}
# zooms por frase: "cada frase = un cambio de perspectiva" es la regla del
# formato; sin esto el espectador ve el mismo plano 20s y se va
_ZOOMS = [1.0, 1.10, 1.04, 1.13, 1.06, 1.16, 1.02, 1.09]
MAX_SLOWDOWN = 2.2  # mas alla se ve a camara lenta obvia


def _letterbox(clip: Path, start: float, dur: float) -> str | None:
    """Detecta franjas negras del clip original. Muchos reels traen un video
    horizontal pegado en un lienzo vertical con barras: si no se quitan, el
    short final desperdicia media pantalla en negro."""
    r = _run(["ffmpeg", "-v", "info", "-ss", f"{start:.2f}", "-t", f"{min(dur, 4):.2f}",
              "-i", str(clip), "-vf", "cropdetect=24:2:0", "-f", "null", "-"], timeout=180)
    import re
    hits = re.findall(r"crop=(\d+:\d+:\d+:\d+)", (r.stderr or ""))
    if not hits:
        return None
    crop = hits[-1]
    w, h, _, _ = (int(x) for x in crop.split(":"))
    if w < 16 or h < 16:
        return None
    return crop


def _wm_box(where: str):
    w = (where or "").lower()
    for k, box in _WM_BOXES.items():
        if all(t in w for t in k.split()):
            return box
    return None


def cmd_edit(a) -> int:
    """Ensambla el short final: voz + clip estirado al largo de la narracion +
    zoom por frase + subtitulos quemados + musica con ducking."""
    import asyncio

    sys.path.insert(0, str(ROOT))
    import pipeline as pl

    target = Path(a.target)
    sj, aj = target / "script.json", target / "analysis.json"
    if not sj.exists():
        print(f"ERROR: falta {sj} — corre antes: py viral_lab.py script {target}")
        return 2
    sc = json.loads(sj.read_text(encoding="utf-8"))
    an = json.loads(aj.read_text(encoding="utf-8"))["analysis"] if aj.exists() else {}
    clip = target / "video.mp4"

    # ---- 1. VOZ. Se sintetiza de una pieza: edge-tts no deja huecos entre
    # frases, asi que no hay silencios que cortar despues (el error #1 del
    # formato se evita de origen en vez de arreglarlo en la edicion).
    voice = target / "voice.mp3"
    words = asyncio.run(pl._tts(sc["script"], a.voice, a.rate, voice))
    adur = _duration(voice)
    print(f"[edit] voz: {adur:.1f}s, {len(words)} palabras")

    # ---- 2. BASE: recorte, marca de agua tapada, estirado al largo de la voz
    cut = sc.get("cut") or {}
    s0 = float(cut.get("start") or 0)
    s1 = float(cut.get("end") or _duration(clip))
    cut_len = max(s1 - s0, 0.5)
    ratio = min(max(adur / cut_len, 1.0), MAX_SLOWDOWN)
    lb = None if a.no_crop else _letterbox(clip, s0, cut_len)
    if lb:
        print(f"[edit] franjas negras recortadas: crop={lb}")
    chain = (f"[0:v]trim=start={s0}:end={s1},setpts=(PTS-STARTPTS)*{ratio:.4f},"
             + (f"crop={lb}," if lb else "")
             + f"scale=1080:1920:force_original_aspect_ratio=increase,"
               f"crop=1080:1920,fps=30")
    box = _wm_box(((an.get("watermark") or {}).get("where") or "")) \
        if (an.get("watermark") or {}).get("present") else None
    if box:
        x, y, w, h = box
        chain += (f",split[a][b];[b]crop={w}:{h}:{x}:{y},boxblur=22[bl];"
                  f"[a][bl]overlay={x}:{y}[v]")
        print(f"[edit] tapando marca de agua en {x},{y}")
    else:
        chain += "[v]"
    base = target / "base.mp4"
    r = _run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-filter_complex", chain,
              "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast",
              "-crf", "20", "-pix_fmt", "yuv420p", str(base)], timeout=600)
    if r.returncode != 0:
        print(f"ERROR base: {r.stderr[-500:]}")
        return 2
    print(f"[edit] base: {_duration(base):.1f}s (clip x{ratio:.2f})")

    # ---- 3. ZOOM POR FRASE. Los cortes se reparten segun el peso en palabras de
    # cada frase, que es la mejor aproximacion a cuando suena cada una.
    lines = sc.get("lines") or [{"text": sc["script"]}]
    counts = [max(len(l["text"].split()), 1) for l in lines]
    total = sum(counts)
    bounds, acc = [], 0.0
    for c in counts:
        d = adur * c / total
        bounds.append((acc, acc + d))
        acc += d
    parts, labels = [], []
    for i, (b0, b1) in enumerate(bounds):
        z = _ZOOMS[i % len(_ZOOMS)]
        cw, ch = int(1080 / z) // 2 * 2, int(1920 / z) // 2 * 2
        parts.append(f"[0:v]trim=start={b0:.3f}:end={b1:.3f},setpts=PTS-STARTPTS,"
                     f"crop={cw}:{ch}:{(1080 - cw) // 2}:{(1920 - ch) // 2},"
                     f"scale=1080:1920[s{i}]")
        labels.append(f"[s{i}]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(parts)}:v=1:a=0[vz]"

    # subtitulos palabra a palabra del pipeline (mismo estilo que el canal madre)
    ass = pl.generate_subtitles(words, target)
    ass_esc = str(ass.resolve()).replace("\\", "/").replace(":", "\\:")
    fc += f";[vz]subtitles='{ass_esc}'[vout]"

    # ---- 4. AUDIO: voz + musica con ducking (mismos parametros probados)
    music = pl._pick_music() if not a.no_music else None
    inputs = ["-stream_loop", "-1", "-i", str(base), "-i", str(voice)]
    if music:
        inputs += ["-i", str(music)]
        fc += (";[1:a]asplit=2[vmix][vtrig];"
               "[2:a]aloop=loop=-1:size=2e9,volume=0.14[bg0];"
               "[bg0][vtrig]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[bg];"
               "[vmix][bg]amix=inputs=2:normalize=0:duration=first[aout]")
    else:
        fc += ";[1:a]anull[aout]"

    out = target / "short.mp4"
    r = _run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc,
              "-map", "[vout]", "-map", "[aout]", "-t", f"{adur:.3f}",
              "-c:v", "libx264", "-preset", "medium", "-crf", "21",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(out)],
             timeout=900)
    if r.returncode != 0:
        print(f"ERROR montaje: {r.stderr[-800:]}")
        return 2
    base.unlink(missing_ok=True)
    print(f"[edit] LISTO: {out} ({_duration(out):.1f}s)")
    print(f"[edit] credito obligatorio en la descripcion: {sc.get('source_credit', '')}")
    print(f"[edit] revisa antes de publicar: py viral_lab.py qa {out}")
    return 0


# ----------------------------------------------------------------------- QA

QA_PROMPT = """Eres el control de calidad de un canal de Shorts de historia. Te paso un
fotograma por escena de un video ya renderizado, en orden, con su timestamp, y
debajo el guion narrado completo.

Revisa CADA fotograma y marca SOLO problemas reales, sin inventar ninguno:

1. `humanoid_animal`: aparece un animal antropomorfo (animal con ropa, de pie,
   con manos, actuando como persona). Es una violacion DURA del estilo del canal:
   solo personajes humanos. Un animal real y normal (un caballo, un perro a cuatro
   patas) NO cuenta.
2. `mismatch`: la imagen no corresponde a nada de lo que narra el guion en ese
   momento (el generador de imagenes a veces devuelve algo ajeno sin dar error).
3. `text_problem`: hay texto renderizado cortado, ilegible, superpuesto o mal
   escrito (ignora los subtitulos grandes en el centro-abajo, esos son correctos).
4. `broken_cutout`: un recorte roto — cabeza flotante sin cuerpo, miembro cortado,
   figura con halo o borde sucio.
5. `other`: cualquier otra cosa que impediria publicarlo.

Responde SOLO JSON:
{"frames": [{"t": 0.0, "sees": "una frase de que se ve",
             "problems": ["humanoid_animal"], "detail": "explicacion corta"}],
 "verdict": "publicable" | "revisar" | "bloqueado",
 "summary": "una frase"}
Si un fotograma esta bien, deja `problems` vacio."""


def _dhash(path: Path) -> int:
    """Hash perceptual 8x8 para detectar escenas repetidas (el error de 'repetir
    el mismo clip', que en nuestro motor aparece como el eco de apertura)."""
    from PIL import Image
    im = Image.open(path).convert("L").resize((9, 8), Image.LANCZOS)
    px = im.tobytes()
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | int(px[y * 9 + x] > px[y * 9 + x + 1])
    return bits


def cmd_qa(a) -> int:
    """Revision automatica ANTES de publicar. Nace de un bug real y no resuelto:
    el generador de imagenes devuelve a veces contenido incorrecto sin marcar
    error, y se detectaba a ojo (o no se detectaba: un mapache con gabardina
    llego a publicarse en la ultima escena de un video)."""
    target = Path(a.target)
    video = target if target.suffix == ".mp4" else target / "video.mp4"
    if not video.exists():
        print(f"ERROR: no encuentro {video}")
        return 2

    # guion + limites de escena reales si es una carpeta de output del pipeline
    script, times = "", []
    sj = video.parent / "script.json"
    if sj.exists():
        d = json.loads(sj.read_text(encoding="utf-8"))
        script = d.get("script", "")
    mf = video.parent / "clips" / "archivo_manifest.json"
    if mf.exists():
        m = json.loads(mf.read_text(encoding="utf-8"))["manifest"]
        # centro de cada escena: el fotograma mas representativo de esa imagen
        times = [round((s["from"] + s["dur"] / 2) / 30, 2) for s in m["scenes"]]
    if not times:
        dur = _duration(video)
        n = a.frames or 12
        times = [round(dur * (i + 0.5) / n, 2) for i in range(n)]

    frames = _frames_at(video, times, width=640)
    if not frames:
        print("ERROR: no pude extraer fotogramas")
        return 2

    # 1) repeticiones: gratis y local, no gasta tokens
    hashes = [(t, _dhash(f)) for t, f in frames]
    dupes = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            dist = bin(hashes[i][1] ^ hashes[j][1]).count("1")
            if dist <= 6:  # <=6 bits de 64 = practicamente la misma imagen
                dupes.append((hashes[i][0], hashes[j][0], dist))

    # 2) contenido: un fotograma por escena a Claude
    import base64
    import anthropic

    content = []
    for t, f in frames:
        content.append({"type": "text", "text": f"--- t={t}s"})
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": "image/jpeg",
            "data": base64.b64encode(f.read_bytes()).decode()}})
    content.append({"type": "text", "text": QA_PROMPT +
                    (f"\n\nGUION NARRADO:\n{script}" if script else "")})
    print(f"[qa] revisando {len(frames)} escenas...")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=os.environ.get("VIRAL_CLAUDE_MODEL", "claude-opus-4-8"),
        max_tokens=4000, thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": content}])
    txt = next((b.text for b in resp.content if b.type == "text"), "")
    _drop_frames(frames)
    if txt.strip().startswith("```"):
        txt = txt.split("```")[1].lstrip("json")
    try:
        rep = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
    except Exception as e:
        print(f"ERROR: no pude leer el informe ({e})")
        return 2

    bad = [f for f in rep.get("frames", []) if f.get("problems")]
    lines = [f"# QA — {video.parent.name}", "", f"**{rep.get('summary', '')}**", ""]
    if dupes:
        lines.append("## Escenas repetidas")
        for t1, t2, d in dupes:
            lines.append(f"- `{t1}s` y `{t2}s` son casi la misma imagen (distancia {d})")
        lines.append("")
    lines.append("## Problemas de contenido" if bad else "## Sin problemas de contenido")
    for f in bad:
        lines.append(f"- `{f.get('t')}s` **{', '.join(f.get('problems', []))}** — "
                     f"{f.get('detail', '')} (se ve: {f.get('sees', '')})")
    (video.parent / "qa.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    hard = [f for f in bad if "humanoid_animal" in f.get("problems", [])
            or "mismatch" in f.get("problems", [])]
    for t1, t2, d in dupes:
        print(f"[qa] REPETIDA: {t1}s ~ {t2}s")
    for f in bad:
        print(f"[qa] {f.get('t')}s {','.join(f.get('problems', []))}: {f.get('detail', '')[:80]}")
    print(f"[qa] veredicto: {rep.get('verdict')} — {video.parent / 'qa.md'}")
    return 1 if hard else 0  # codigo 1 = no publicar sin mirarlo


def main() -> int:
    ap = argparse.ArgumentParser(description="Laboratorio de clips virales de terceros")
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("find", help="busca virales del nicho y los rankea")
    f.add_argument("query", nargs="*", help="consultas (por defecto NICHE_QUERIES)")
    f.add_argument("--dir", default=str(DEFAULT_DIR))
    f.add_argument("--limit", type=int, default=8, help="resultados por plataforma")
    f.add_argument("--top", type=int, default=10, help="cuantos mostrar")
    f.set_defaults(func=cmd_find)

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

    s = sub.add_parser("script", help="guion de voz en off desde el analisis")
    s.add_argument("target", help="carpeta de viral/ ya analizada")
    s.add_argument("--seconds", type=int, default=0, help="duracion objetivo")
    s.add_argument("--bait", action="store_true",
                    help="mete un error factual pequeno a proposito para provocar "
                         "correcciones en comentarios (sube interaccion, baja credibilidad)")
    s.set_defaults(func=cmd_script)

    e = sub.add_parser("edit", help="monta el short final (voz + clip + subs + musica)")
    e.add_argument("target", help="carpeta de viral/ con script.json")
    e.add_argument("--voice", default="en-US-AndrewNeural")
    e.add_argument("--rate", default="+8%")
    e.add_argument("--no-music", action="store_true")
    e.add_argument("--no-crop", action="store_true",
                    help="no recortar las franjas negras del clip original")
    e.set_defaults(func=cmd_edit)

    q = sub.add_parser("qa", help="revision automatica de un video antes de publicar")
    q.add_argument("target", help="carpeta output/<video> o un .mp4")
    q.add_argument("--frames", type=int, default=0,
                    help="fotogramas si no hay manifest (por defecto 12)")
    q.set_defaults(func=cmd_qa)

    a = ap.parse_args()
    _load_env()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
