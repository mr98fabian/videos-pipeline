"""Motor "Archivo Vivo" — integracion pipeline <-> Remotion (23 jul 2026).

Toma los artefactos que el pipeline YA genera (imagenes de escena nb_i.png,
voz con timestamps, guion JSON) y produce el video completo en el estilo
aprobado (ver memoria estilo-archivo-vivo) via la composicion ArchivoVideo:

  1. Recortes rembg CACHEADOS por hash (visual_cache) + regla de tratamiento
     por cobertura (sticker troquelado vs foto de archivo clavada).
  2. Captions cineticos con los timestamps REALES del TTS (adios ASS quemado).
  3. Beats visuales: sello de fecha automatico (regex sobre el guion) +
     "visual_beats" opcionales del guion JSON (censura, zoom, typewriter).
  4. Cold-open censurado (Tier 3) usando la escena de climax.
  5. Cierre de franquicia: mapa vivo + share-card + CASE #N CLOSED + SUBSCRIBE.
  6. Mux final: video del motor (con sus SFX frame-exactos) + voz + musica.

Uso standalone (regenerar un video ya producido, costo API cero):
  py archivo_engine.py output/2026-07-23-hitler-s-first-coup-collapsed-in-one-aft

Desde pipeline.py se invoca con render_from_parts() (flag --archivo).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion_graphics"
FPS = 30
COLD_FRAMES = 22  # duracion del cold-open censurado
CLOSE_TAIL = 112  # frames de cierre tras terminar la voz (~3.7s)


def _run(cmd: list[str], cwd: Path | None = None, timeout: float = 900.0) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"cmd fallo ({cmd[0]}):\n{r.stderr[-1200:]}")


def _ffprobe_dur(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, timeout=30,
    )
    return float(r.stdout.strip())


# --- timestamps por palabra: en memoria (pipeline) o desde subs.ass (standalone)
_ASS_ACTIVE = re.compile(r"\\t\(0,90[^}]*\}([^{]+)\{")
_ASS_LINE = re.compile(r"Dialogue: 0,(\d+:\d+:\d+\.\d+),")


def words_from_ass(ass_path: Path) -> list[tuple[float, str]]:
    """Reconstruye [(start_seg, palabra)] desde el karaoke del subs.ass ya
    generado (un evento por palabra, la activa lleva el tag de pop \\t(0,90...)."""
    out = []
    for line in ass_path.read_text(encoding="utf-8").splitlines():
        m = _ASS_LINE.match(line)
        if not m:
            continue
        h, mnt, s = m.group(1).split(":")
        t = int(h) * 3600 + int(mnt) * 60 + float(s)
        w = _ASS_ACTIVE.search(line)
        if w:
            word = w.group(1).strip()
            if word:
                out.append((t, word))
    return out


# verbo narrado -> tipo de accion (orden = prioridad). Regex con limites de
# palabra donde el substring colisiona (p.ej. "fleet" NO debe disparar "flee",
# "falling" NO debe disparar "fall"); prefijos sueltos para conjugaciones.
_ACTION_KW = [
    ("explosion", r"explod|explos|detonat|blast|blew up|blew apart|bombed|erupt"),
    ("impact",    r"slam|smash|struck|\bstrike\b|shrapnel|rammed|crash|hurl|\btore\b|\btorn\b"),
    ("topple",    r"collaps|toppl|crumbl|\bfell\b|knocked down|brought down"),
    ("sink",      r"\bsank\b|\bsunk\b|\bsink\b|drown|underwater|beneath the wa|went under"),
    ("shoot",     r"\bshot\b|\bshoot\b|\bfired\b|firing|gunned|execut|\bbullet|opened fire"),
    ("flee",      r"escap|\bfled\b|\bflee\b|fleeing|slipp|smuggl|sneak|\bsnuck\b|\bran\b"),
    ("rise",      r"emerg|stood up|rebuil|rose up|rising up"),
]


# Como REACCIONA el resto de la escena al verbo que actua la pieza principal
# (multi-recorte, 25 jul 2026): (tipo de reaccion, retardo en frames). El retardo
# es lo que vende la causalidad: primero pasa, DESPUES los demas lo sufren.
_REACTION = {
    "explosion": ("topple", 6),
    "impact":    ("topple", 5),
    "shoot":     ("recoil", 5),
    "lunge":     ("recoil", 5),
    "topple":    ("recoil", 6),
    "fall":      ("recoil", 6),
    "collapse":  ("recoil", 6),
    "flee":      ("lunge", 8),    # uno huye, el otro se lanza tras el
    "escape":    ("lunge", 8),
    "sink":      ("sink", 9),     # se hunden en cadena
    "rise":      ("rise", 7),
    "recoil":    ("recoil", 4),
}


def _detect_action(text: str):
    t = text.lower()
    for atype, pat in _ACTION_KW:
        if re.search(pat, t):
            return atype
    return None


_TITLE_STOP = {"how", "why", "the", "what", "when", "who", "a", "an", "this",
               "that", "his", "her", "their", "one", "man", "became", "of", "in"}


def _auto_subject(title: str):
    """Nombre propio mas prominente del titulo para buscar su foto real
    (ej. 'How Fidel Castro's...' -> 'Fidel Castro'). None si no hay uno claro."""
    words = title.replace("|", " ").replace("'s", "").split()
    run = []
    best = []
    for w in words:
        clean = re.sub(r"[^A-Za-z]", "", w)
        if clean and clean[0].isupper() and clean.lower() not in _TITLE_STOP:
            run.append(clean)
        else:
            if len(run) > len(best):
                best = run
            run = []
    if len(run) > len(best):
        best = run
    return " ".join(best) if best else None


def _fetch_real_photo(query: str, pub: Path, slug: str):
    """Descarga una foto de archivo REAL con licencia libre (Wikimedia Commons,
    mismo fetch del pipeline clasico) y la guarda como evidencia. No la recorta:
    va como foto rectangular clavada al tablero. Devuelve la ruta relativa o None."""
    import hashlib
    import io
    import re as _re
    import shutil as _sh
    import time
    import urllib.request
    import pipeline as pl
    from PIL import Image
    # cache de foto real por query -> se descarga UNA vez en la vida (evita el
    # 429 de Wikimedia en cada re-render)
    cache_dir = ROOT / "assets" / "cache" / "real"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ckey = cache_dir / (hashlib.sha1(query.encode()).hexdigest() + ".png")
    if ckey.exists():
        _sh.copyfile(ckey, pub / "real.png")
        return f"archivo/{slug}/real.png"
    # variantes: como viene, sin años/números (Wikimedia no matchea "X 1953"),
    # y solo las dos primeras palabras (nombre propio) como último recurso
    bare = _re.sub(r"\s+\d{3,4}", "", query).strip()
    variants = list(dict.fromkeys([query, bare, " ".join(bare.split()[:2])]))
    cands = []
    for v in variants:
        for _ in range(3):  # backoff ante 429 de Wikimedia
            cands = pl._wikimedia_commons_search(v, bias_portrait=True)
            if cands:
                break
            time.sleep(3)
        if cands:
            break
    # preferir dominio público / CC0 (sin obligación de atribución en el Short)
    cands.sort(key=lambda c: 0 if any(t in (c.get("license") or "").lower()
                                      for t in ("public domain", "cc0", "pd")) else 1)
    for c in cands:
        url = c.get("url")
        if not url:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HiddenFactsBot/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                im = Image.open(io.BytesIO(r.read())).convert("RGB")
            w, h = im.size
            if w < 260 or h < 260 or w / h > 2.2 or h / w > 2.2:
                continue  # descarta miniaturas y panoramicas raras
            im.thumbnail((900, 900))
            im.save(ckey)               # cache de por vida
            _sh.copyfile(ckey, pub / "real.png")
            print(f"[archivo] foto real: '{query}' <- {c.get('license', '?')} ({c.get('title', '')[:40]})")
            return f"archivo/{slug}/real.png"
        except Exception:
            continue
    return None


_DATE_PAT = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+(1[89]\d\d|20\d\d)\b", re.I)


def build_manifest(out_dir: Path, data: dict, words: list[tuple[float, str]],
                    audio_dur: float, slug: str) -> dict:
    """Arma el manifest para ArchivoVideo. words = [(start_seg, palabra)]."""
    sys.path.insert(0, str(ROOT))
    from visual_cache import cached_cutout, cutout_coverage, cutout_parts
    import pipeline as pl

    clips = out_dir / "clips"
    imgs = sorted(clips.glob("nb_*.png"), key=lambda p: int(p.stem.split("_")[1]))
    if not imgs:
        raise RuntimeError(f"no hay nb_*.png en {clips} (el motor necesita imagenes de escena)")
    n = len(imgs)

    # carpeta de assets publicos del video
    pub = MOTION / "public" / "archivo" / slug
    pub.mkdir(parents=True, exist_ok=True)

    # duraciones por escena con cortes en fin de frase (regla existente del pipeline)
    pl_words = [(t, t, w) for t, w in words]
    durations = pl._scene_boundaries(pl_words, n, audio_dur)

    cold_shift = COLD_FRAMES
    # escenas (1-based, como visual_beats) donde el recorte rembg sale lavado ->
    # forzar foto clavada sin intentar el sticker
    force_photo = {int(k) for k in data.get("force_photo", [])}
    # los primeros planos de CARA nunca se troquelan bien (cara flotante, borde
    # sucio); van como foto clavada, que es donde lucen (feedback 23 jul)
    _CLOSEUP_KW = ("close-up", "close up", "extreme close", "'s face", " a face", "portrait", "facial")
    for ti, term in enumerate(terms_all := (data.get("search_terms") or [])):
        if any(k in term.lower() for k in _CLOSEUP_KW):
            force_photo.add(ti + 1)
    scenes = []
    cursor = cold_shift
    for i, img in enumerate(imgs):
        shutil.copyfile(img, pub / f"bg_{i}.png")
        fg_rel = None
        treatment = "photo"
        parts_rel = []
        try:
            if (i + 1) in force_photo:
                raise ValueError("force_photo")
            cut = cached_cutout(img)
            if cutout_coverage(cut) > 0.17:  # v2: recortes chicos (cabezas sueltas) -> foto clavada, que es lo que el usuario ama
                shutil.copyfile(cut, pub / f"fg_{i}.png")
                fg_rel = f"archivo/{slug}/fg_{i}.png"
                treatment = "sticker"
                # MULTI-RECORTE: si la escena tiene varias figuras/objetos separados,
                # cada uno sale como sticker propio para que puedan interactuar.
                for k, pt in enumerate(cutout_parts(cut)):
                    shutil.copyfile(pt["path"], pub / f"fg_{i}_p{k}.png")
                    parts_rel.append({
                        "src": f"archivo/{slug}/fg_{i}_p{k}.png",
                        "nx": pt["nx"], "ny": pt["ny"], "nw": pt["nw"], "nh": pt["nh"],
                        "area": pt["area"],
                    })
                if parts_rel:
                    big = max(p["area"] for p in parts_rel)
                    for k, p in enumerate(parts_rel):
                        # el mas grande manda el plano cercano; los demas se alejan
                        p["depth"] = round(0.70 + 0.30 * (p["area"] / big), 3)
                        p["from"] = k * 3          # entradas escalonadas, no en bloque
                        p["dir"] = "left" if p["nx"] < 0.45 else "right" if p["nx"] > 0.55 else "bottom"
                    print(f"[archivo] escena {i}: {len(parts_rel)} piezas separadas")
        except Exception as e:
            print(f"[archivo] recorte escena {i} fallo ({e}); foto clavada")
        dur_f = max(int(round(durations[i] * FPS)), 12)
        scenes.append({
            "from": cursor, "dur": dur_f,
            "bg": f"archivo/{slug}/bg_{i}.png", "fg": fg_rel,
            "parts": parts_rel, "treatment": treatment, "beats": {},
        })
        cursor += dur_f

    # palabras -> frames globales (desplazadas por el cold-open)
    wframes = [{"t": int(round(t * FPS)) + cold_shift, "w": w} for t, w in words]

    # beat automatico: sello con la FECHA narrada, en la escena donde se narra
    mdate = _DATE_PAT.search(data.get("script", ""))
    if mdate:
        date_text = mdate.group(0).upper().replace(",", ", ").replace("  ", " ")
        script_words = data["script"].split()
        # indice aproximado de la palabra del mes en el guion
        for wi, sw in enumerate(script_words):
            if sw.lower().startswith(mdate.group(1).lower()):
                if wi < len(wframes):
                    g = wframes[wi]["t"]
                    for s in scenes:
                        if s["from"] <= g < s["from"] + s["dur"]:
                            s["beats"]["stamp"] = {"text": date_text, "at": max(g - s["from"], 4)}
                            break
                break

    # ---- DENSIDAD AUTOMATICA v2 (feedback 23 jul: escenas ralas) ----
    # 1. [RETIRADO 23 jul] stickers de biblioteca por palabra clave: chocaban con
    #    el sujeto y a veces salian de baja calidad. La marginalia de expediente +
    #    la capa de accion ya dan densidad; menos ruido, cero choques.

    # 2. numeros narrados grandes -> mini sello rojo ("150", "883", "1934" ya va en fecha)
    for wi, wd in enumerate(wframes):
        raw = wd["w"].strip(".,!?").replace(",", "")
        if raw.isdigit() and len(raw) >= 2 and not (1800 <= int(raw) <= 2099):
            g = wd["t"]
            for s_ in scenes:
                if s_["from"] <= g < s_["from"] + s_["dur"] and "numstamp" not in s_["beats"]:
                    s_["beats"]["numstamp"] = {"text": raw, "at": max(g - s_["from"], 4)}
                    break

    # 3. zoom-evidencia alternado en toda escena con aire (>55 frames)
    for si, s_ in enumerate(scenes):
        if s_["dur"] > 55 and "zoom" not in s_["beats"]:
            s_["beats"]["zoom"] = {
                "at": int(s_["dur"] * 0.42),
                "scale": 1.2 if si % 2 == 0 else 1.26,
                "x": -70 if si % 2 == 0 else 70,
                "y": 60,
            }

    # 4. ACCION: detecta el verbo narrado por escena y lo ACTUA (el recorte se
    #    transforma + FX de comic), sincronizado al frame en que se dice. Solo
    #    los tipos de impacto llevan palabra (BANG/BOOM/CRASH); el resto no.
    terms = data.get("search_terms") or []
    scene_words = {si: [] for si in range(len(scenes))}
    for wd in wframes:
        for si, s_ in enumerate(scenes):
            if s_["from"] <= wd["t"] < s_["from"] + s_["dur"]:
                scene_words[si].append(wd)
                break
    for si, s_ in enumerate(scenes):
        narr = " ".join(w["w"] for w in scene_words[si])
        # SOLO la narracion (lo que se dice); los search_terms traen terminos de
        # camara ("wide shot", "close-up") que dispararian falsos (shot->shoot)
        atype = _detect_action(narr)
        if not atype:
            continue
        at = None
        for w in scene_words[si]:  # frame local del verbo narrado
            if _detect_action(w["w"]) == atype:
                at = max(w["t"] - s_["from"], 4)
                break
        if at is None:
            at = max(int(s_["dur"] * 0.4), 6)
        s_["beats"]["action"] = {"type": atype, "at": at, "dur": 16}
        # INTERACCION entre piezas: la mas grande ACTUA el verbo, las demas
        # REACCIONAN unos frames despues (causa -> efecto legible en pantalla).
        for k, p in enumerate(s_.get("parts") or []):
            if k == 0:
                p["action"] = {"type": atype, "at": at, "dur": 16}
            else:
                rtype, lag = _REACTION.get(atype, ("recoil", 5))
                # sentido: el que esta a la izquierda del que actua sale despedido
                # hacia la izquierda (y viceversa) -> se lee empuje, no derrumbe
                away = -1 if p["nx"] < (s_["parts"][0]["nx"] - 0.02) else 1
                p["action"] = {"type": rtype, "at": at + lag + (k - 1) * 2,
                                "dur": 16, "away": away, "amp": 0.7}

    # 5. FOTO REAL de archivo (Wikimedia libre) clavada como EVIDENCIA en 1-2
    #    escenas clave -> momento "esto paso de verdad" (feedback 24 jul).
    rp = data.get("real_photo")
    if rp is None:
        subj = _auto_subject(data.get("title", ""))
        if subj:
            rp = {"query": subj}
    if rp and rp.get("query"):
        try:
            real_rel = _fetch_real_photo(rp["query"], pub, slug)
            if real_rel:
                mid = max(len(scenes) - 2, 1)
                targets = rp.get("scenes") or [1, mid]
                yr = rp.get("year") or (mdate.group(2) if mdate else "")
                for si in targets:
                    if 0 <= si < len(scenes):
                        scenes[si]["beats"]["evidence"] = {"src": real_rel, "at": 8, "year": yr}
        except Exception as e:
            print(f"[archivo] foto real no disponible: {e}")

    # beats del guion (autor manda): visual_beats = {"<scene_idx>": {...}}
    for k, beat in (data.get("visual_beats") or {}).items():
        idx = int(k)
        if 0 <= idx < len(scenes):
            scenes[idx]["beats"].update(beat)

    voice_end = cold_shift + int(round(audio_dur * FPS))
    close_from = voice_end + 4
    # sin gap por redondeo: la ultima escena cubre hasta el cierre
    if scenes:
        scenes[-1]["dur"] = close_from - scenes[-1]["from"]

    # serie y numero de caso desde el titulo "... | WWII Secrets"
    title = data.get("title", "")
    series = title.split("|")[-1].strip() if "|" in title else "HIDDEN FACTS"
    share = data.get("share_card") or {}
    # numero de caso ALEATORIZADO (feedback 23 jul: "CASE #1" en cada video se ve
    # falso). Determinista desde el hash del tema -> mismo video = mismo numero,
    # pero variado entre videos, sensacion de "archivo de mil casos". Override
    # explicito con case_no en el JSON.
    case_no = int(data["case_no"]) if str(data.get("case_no", "")).isdigit() and int(data.get("case_no", 1)) > 1 \
        else 12 + (zlib.crc32(slug.encode()) % 460)

    def _word_safe(text: str, limit: int = 58) -> str:
        text = text.strip()
        if len(text) <= limit:
            return text
        cut = text[:limit].rsplit(" ", 1)[0]
        return cut.rstrip(".,;: ")

    return {
        "durationInFrames": close_from + CLOSE_TAIL,
        "coldOpen": {"src": f"archivo/{slug}/bg_{n - 1}.png", "label": "CLASSIFIED",
                      "tag": "IN 60 SECONDS...", "frames": COLD_FRAMES},
        "scenes": scenes,
        "words": wframes,
        "caseBase": case_no,
        "close": {
            "from": close_from, "series": series,
            "caseNo": case_no,
            "share1": share.get("line1", _word_safe(
                (data.get("hook_card") or title.split("|")[0]).split(".")[0] + ".")),
            "share2": share.get("line2", "True story."),
        },
    }


def render_from_parts(out_dir: Path, data: dict, words: list[tuple[float, str]],
                       audio_path: Path) -> Path:
    """Renderiza el video Archivo Vivo completo y muxea voz + musica."""
    sys.path.insert(0, str(ROOT))
    import pipeline as pl

    out_dir = Path(out_dir)
    slug = out_dir.name[-40:].strip("-")
    audio_dur = _ffprobe_dur(audio_path)
    manifest = build_manifest(out_dir, data, words, audio_dur, slug)

    props = out_dir / "clips" / "archivo_manifest.json"
    props.parent.mkdir(exist_ok=True)
    props.write_text(json.dumps({"manifest": manifest}, ensure_ascii=False), encoding="utf-8")
    print(f"[archivo] manifest: {len(manifest['scenes'])} escenas, "
          f"{len(manifest['words'])} palabras, {manifest['durationInFrames']} frames")

    engine_mp4 = out_dir / "clips" / "archivo_engine.mp4"
    npx = shutil.which("npx") or "npx"
    print("[archivo] renderizando composicion (esto tarda unos minutos)...")
    _run([npx, "remotion", "render", "src/index.jsx", "ArchivoVideo",
          str(engine_mp4.resolve()), "--props", str(props.resolve())], cwd=MOTION)

    # mux: motor (video + sfx del motor) + voz desplazada por el cold-open + musica
    cold_ms = int(COLD_FRAMES / FPS * 1000)
    music = pl._pick_music()
    final = out_dir / "video.mp4"
    inputs = ["-i", str(engine_mp4), "-i", str(audio_path)]
    fc = f"[1:a]adelay={cold_ms}|{cold_ms}[voice];"
    if music:
        # DUCKING (fix 23 jul): la musica baja cuando habla la voz, igual que en
        # assemble() clasico (sidechaincompress con los mismos parametros probados)
        inputs += ["-i", str(music)]
        fc += ("[voice]asplit=2[vmix][vtrig];"
               "[2:a]aloop=loop=-1:size=2e9,volume=0.06[bg0];"
               "[bg0][vtrig]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[bg];")
        labels, ninputs = "[0:a][vmix][bg]", 3
    else:
        fc += "[voice]anull[vmix];"
        labels, ninputs = "[0:a][vmix]", 2
    fc += f"{labels}amix=inputs={ninputs}:normalize=0:duration=first[a]"
    _run(["ffmpeg", "-y", *inputs, "-filter_complex", fc,
          "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
          str(final)])
    print(f"[archivo] LISTO: {final}")
    return final


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    out_dir = Path(sys.argv[1])
    data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    words = words_from_ass(out_dir / "subs.ass")
    if not words:
        print("ERROR: no pude reconstruir timestamps desde subs.ass")
        return 1
    print(f"[archivo] {len(words)} palabras reconstruidas del ASS")
    render_from_parts(out_dir, data, words, out_dir / "voice.mp3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
