"""KOREX motion: camino unico de produccion de KOREX desde nov 2026.

Guion JSON + voz qw_korex (con marcas por palabra) -> manifest -> composicion
Remotion `KorexMotion` (motion_graphics/src/korex/KorexMotion.jsx) -> mezcla
de voz + musica + diseno sonoro generado por codigo, con el mismo ducking que
assemble().

Reemplaza a Flow (una imagen generada por escena) y a Wan (animar la escena
0). Ninguno de los dos se borra: quedan LEGACY detras de `--korex-legacy` en
pipeline.py. Por que se cambia: Flow fallaba de forma intermitente (rondas de
korex_fill), colaba personajes ajenos y pintaba color en un canal B/N; Wan
deformaba a Tadeo pasados ~2 s. Aqui el personaje son las laminas ya
aprobadas de assets/kx_cast/ movidas por codigo: no hay nada generativo que
pueda salir mal en el render.

Datos opcionales en el guion (bloque "motion"; todo tiene un valor por
defecto automatico, el bloque solo afina):
    "motion": {
      "hero":   {"scene": 3, "text": "$35", "label": "de sobregiro", "label_top": "..."},
      "scenes": {"4": {"concept": {"type": "bars", "label": "...", "reorder": true}},
                 "7": {"keyword": "..."}}
    }
Tipos de concepto: line | bars | toggle | doc | check.

Uso directo sobre una carpeta ya producida (re-render sin volver a sintetizar):
    py korex_motion.py output/<carpeta>
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion_graphics"
FPS = 30
SR = 48000
SFX_CACHE = ROOT / "assets" / "cache" / "kx_sfx"
SFX_VOLUME = 0.4  # bus de efectos antes del ducking; ver sound_report.json


def _log(msg: str) -> None:
    print(f"[korex-motion] {msg}", flush=True)


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "")[-2500:]
        raise RuntimeError(f"fallo: {' '.join(map(str, cmd[:4]))}...\n{tail}")


# ---------------------------------------------------------------------------
# Numeros hablados -> cifra (el guion escribe "treinta y cinco dolares" porque
# el TTS lee mal los digitos; el numero heroe necesita "$35").
# ---------------------------------------------------------------------------
_UNI = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciséis": 16, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18,
    "diecinueve": 19, "veinte": 20, "veintiún": 21, "veintiun": 21,
    "veintiuno": 21, "veintidós": 22, "veintidos": 22, "veintitrés": 23,
    "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiséis": 26,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100, "ciento": 100,
    "doscientos": 200, "trescientos": 300, "cuatrocientos": 400,
    "quinientos": 500, "seiscientos": 600, "setecientos": 700,
    "ochocientos": 800, "novecientos": 900,
}


def _parse_spoken(tokens: list[str]) -> int | None:
    total, cur, seen = 0, 0, False
    for t in tokens:
        if t == "y" and seen:
            continue
        if t in _UNI:
            cur += _UNI[t]
            seen = True
        elif t == "mil" and seen:
            total += (cur or 1) * 1000
            cur = 0
        else:
            break
    return total + cur if seen else None


def detect_hero(sentence: str) -> dict | None:
    """Primera cantidad con unidad en la frase: dolares, por ciento, %."""
    low = sentence.lower()
    m = re.search(r"\$?\s?(\d[\d,.]*)\s*(d[oó]lares|%|por ciento)?", low)
    if m and m.group(1):
        unit = m.group(2) or ""
        n = m.group(1)
        return {"text": f"{n}%" if "ciento" in unit or unit == "%" else f"${n}"}
    words = re.findall(r"[a-záéíóúñü]+", low)
    for i in range(len(words)):
        if words[i] in _UNI and words[i] not in ("un", "una", "uno"):
            j = i
            while j < len(words) and (words[j] in _UNI or words[j] in ("y", "mil")):
                j += 1
            val = _parse_spoken(words[i:j])
            nxt = " ".join(words[j : j + 2])
            if val is not None and val >= 2:
                if nxt.startswith("dólares") or nxt.startswith("dolares"):
                    return {"text": f"${val:,}"}
                if nxt.startswith("por ciento"):
                    return {"text": f"{val}%"}
    return None


# ---------------------------------------------------------------------------
# Escenas: una por oracion, cortando en el arranque de la oracion siguiente.
# ---------------------------------------------------------------------------
def split_sentences(script: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", script.strip()) if s]


def sentence_starts(words: list[tuple[float, float, str]], sentences: list[str]) -> list[float]:
    """Tiempo de arranque de cada oracion. Primero por puntuacion del TTS; si
    no cuadra, por proporcion de palabras del guion (nunca a ciegas)."""
    starts = [0.0]
    for k in range(1, len(words)):
        if words[k - 1][2].rstrip("\"')»”").endswith((".", "!", "?", "…")):
            starts.append(words[k][0])
    if len(starts) == len(sentences):
        return starts
    counts = [len(s.split()) for s in sentences]
    total = sum(counts)
    starts, acc = [], 0
    for c in counts:
        idx = min(len(words) - 1, round(acc / total * len(words)))
        starts.append(words[idx][0] if acc else 0.0)
        acc += c
    _log(f"AVISO: puntuacion del TTS no cuadra ({len(sentences)} oraciones); cortes por proporcion")
    return starts


_CONCEPT_RULES = [
    (r"interruptor|apag|declinar|activad|bot[oó]n", {"type": "toggle", "off": "ACTIVADO", "on": "APAGADO"}),
    (r"firm|ley|contrato|aceptaste|dicho que s[ií]", {"type": "doc"}),
    (r"reorden|mayor a menor|orden en que|compras chiquitas|recibos", {"type": "bars", "reorder": True}),
    (r"revisa|pagos autom|lista|activos", {"type": "check"}),
    (r"baja|cae|pierde|vac[ií]e", {"type": "line", "down": True}),
]


def auto_concept(sentence: str) -> dict:
    low = sentence.lower()
    for pat, spec in _CONCEPT_RULES:
        if re.search(pat, low):
            return dict(spec)
    return {"type": "line"}


def _stage_pose(src: Path | None, pub: Path, slug: str) -> str | None:
    if not src:
        return None
    dst = pub / src.parent.name
    dst.mkdir(parents=True, exist_ok=True)
    tgt = dst / src.name
    if not tgt.exists():
        shutil.copy2(src, tgt)
    return f"kxm/{slug}/{src.parent.name}/{src.name}"


def build_manifest(
    out_dir: Path,
    data: dict,
    words: list[tuple[float, float, str]],
    audio_dur: float,
    cta_text: str | None = None,
    cta_position: str | None = None,
) -> dict:
    import kx_cast

    sentences = split_sentences(data["script"])
    n = len(sentences)
    starts = sentence_starts(words, sentences)
    total_frames = int(math.ceil(audio_dur * FPS))
    cuts = [0] + [max(1, int(round(t * FPS)) - 2) for t in starts[1:]] + [total_frames]

    slug = out_dir.name[:60]
    pub = MOTION / "public" / "kxm" / slug
    pub.mkdir(parents=True, exist_ok=True)
    poses = kx_cast.resolve_scene_cast(data, n)
    char_terms = data.get("character_terms") or []
    motion = data.get("motion") or {}
    overrides = motion.get("scenes") or {}

    twist = (data.get("twist_phrase") or "").strip()
    twist_idx = next(
        (i for i, s in enumerate(sentences) if twist and twist.lower() in s.lower()), None
    )
    hero_spec = motion.get("hero")
    hero_idx = hero_spec.get("scene") if hero_spec else None
    if hero_idx is None:
        for i, s in enumerate(sentences[1:-1], start=1):
            if i == twist_idx:
                continue
            h = detect_hero(s)
            if h:
                hero_idx, hero_spec = i, h
                break

    scenes, sidekick = [], None
    first_tadeo = next(
        (p for p in poses if p and p.parent.name == "tadeo"), None
    )
    for i in range(n):
        frm, to = cuts[i], cuts[i + 1]
        pose = _stage_pose(poses[i], pub, slug)
        if poses[i] and poses[i].parent.name == "tadeo":
            sidekick = pose
        term = char_terms[i] if i < len(char_terms) else ""
        ov = overrides.get(str(i)) or {}
        if i == 0:
            kind = "hook"
        elif i == n - 1:
            kind = "close"
        elif i == twist_idx:
            kind = "twist"
        elif i == hero_idx:
            kind = "hero"
        elif pose:
            kind = "tadeo"
        else:
            kind = "concept"
        sc = {
            "i": i,
            "kind": ov.get("kind", kind),
            "from": frm,
            "dur": max(1, to - frm),
            "text": sentences[i],
            "pose": pose,
            "beat": bool(term) and kx_cast.is_beat(term),
            "sidekick": sidekick or _stage_pose(first_tadeo, pub, slug),
        }
        if sc["kind"] in ("hook", "close") and not pose:
            sc["pose"] = sc["sidekick"]
        if sc["kind"] == "concept":
            sc["concept"] = {**auto_concept(sentences[i]), **(ov.get("concept") or {})}
        if sc["kind"] == "hero":
            sc["hero"] = {**(detect_hero(sentences[i]) or {}), **(hero_spec or {})}
        if ov.get("keyword"):
            sc["keyword"] = ov["keyword"]
        scenes.append(sc)

    # karaoke: grupos de hasta 3 palabras / 18 caracteres, sin cruzar oraciones
    wf = [
        {"s": int(round(ws * FPS)), "e": int(round(we * FPS)), "w": w.strip("\"'«»“”")}
        for ws, we, w in words
    ]
    groups, cur = [], []
    for k, w in enumerate(wf):
        cur.append(w)
        text_len = sum(len(x["w"]) + 1 for x in cur)
        end_sent = words[k][2].rstrip("\"')»”").endswith((".", "!", "?", "…", ",", ":"))
        if len(cur) >= 3 or text_len >= 18 or end_sent or k == len(wf) - 1:
            groups.append(cur)
            cur = []
    captions = []
    for gi, g in enumerate(groups):
        frm = g[0]["s"]
        to = groups[gi + 1][0]["s"] if gi + 1 < len(groups) else total_frames
        to = min(to, g[-1]["e"] + 18) if gi + 1 < len(groups) else total_frames
        captions.append({"from": frm, "to": max(frm + 1, to), "words": g})

    cta = None
    if cta_text and cta_position:
        dur = int(2.6 * FPS)
        if cta_position == "start":
            at = int(0.8 * FPS)
        elif cta_position == "end":
            at = total_frames - dur - int(1.0 * FPS)
        else:
            # a mitad del video: justo DESPUES del giro (el momento de mayor
            # receptividad); sin giro, al 50 %
            at = (
                scenes[twist_idx]["from"] + scenes[twist_idx]["dur"]
                if twist_idx is not None
                else total_frames // 2
            )
        cta = {"text": cta_text, "from": int(at), "dur": dur}

    return {
        "durationInFrames": total_frames,
        "fps": FPS,
        "hook": data.get("hook_card") or sentences[0],
        "twist": twist,
        "scenes": scenes,
        "captions": captions,
        "cta": cta,
    }


# ---------------------------------------------------------------------------
# Diseno sonoro generado por codigo (numpy, local, gratis). Cacheado en disco.
# ---------------------------------------------------------------------------
def _env(n: int, attack: float, release: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    r = np.exp(-np.maximum(t - attack, 0) / max(release, 1e-4))
    return a * r


def _lowpass_sweep(x: np.ndarray, f0: float, f1: float) -> np.ndarray:
    out = np.empty_like(x)
    y = 0.0
    n = len(x)
    for i in range(n):
        fc = f0 * (f1 / f0) ** (i / n)
        a = 1 - math.exp(-2 * math.pi * fc / SR)
        y += a * (x[i] - y)
        out[i] = y
    return out


def _synth(name: str) -> np.ndarray:
    rng = np.random.default_rng(7)
    if name == "whoosh":
        n = int(0.38 * SR)
        noise = rng.standard_normal(n)
        sig = _lowpass_sweep(noise, 300, 6000) * np.sin(np.linspace(0, math.pi, n)) ** 2
        return sig / np.max(np.abs(sig)) * 0.8
    if name == "pop":
        n = int(0.14 * SR)
        t = np.arange(n) / SR
        f = 950 * np.exp(-t * 18) + 260
        sig = np.sin(2 * math.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.04)
        sig[:60] += rng.standard_normal(60) * 0.4
        return sig / np.max(np.abs(sig)) * 0.9
    if name == "impact":
        n = int(0.7 * SR)
        t = np.arange(n) / SR
        f = 70 * np.exp(-t * 4) + 38
        body = np.sin(2 * math.pi * np.cumsum(f) / SR) * _env(n, 0.003, 0.22)
        crack = _lowpass_sweep(rng.standard_normal(n), 4000, 400) * _env(n, 0.001, 0.05)
        sig = body + crack * 0.6
        return sig / np.max(np.abs(sig))
    if name == "riser":
        n = int(0.6 * SR)
        t = np.arange(n) / SR
        f = 200 * (4 ** (t / t[-1]))
        tone = np.sin(2 * math.pi * np.cumsum(f) / SR) * 0.35
        air = _lowpass_sweep(rng.standard_normal(n), 400, 9000) * 0.6
        sig = (tone + air) * (t / t[-1]) ** 2
        return sig / np.max(np.abs(sig)) * 0.8
    raise ValueError(name)


def sfx(name: str) -> np.ndarray:
    SFX_CACHE.mkdir(parents=True, exist_ok=True)
    f = SFX_CACHE / f"{name}.npy"
    if f.exists():
        return np.load(f)
    x = _synth(name).astype(np.float32)
    np.save(f, x)
    return x


def _write_wav(path: Path, x: np.ndarray) -> None:
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def build_sfx_bus(manifest: dict, dur: float, path: Path) -> list[dict]:
    bus = np.zeros(int(dur * SR) + SR, dtype=np.float32)
    cues: list[dict] = []

    def put(name: str, t: float, gain: float) -> None:
        x = sfx(name) * gain
        i = max(0, int(t * SR))
        j = min(len(bus), i + len(x))
        bus[i:j] += x[: j - i]
        cues.append({"t": round(t, 2), "sfx": name, "gain": gain})

    scenes = manifest["scenes"]
    put("pop", 0.0, 0.5)
    for sc in scenes[1:]:
        put("whoosh", sc["from"] / FPS - 0.16, 0.45)
    for sc in scenes:
        t = sc["from"] / FPS
        # el golpe va EN EL CORTE, en el hueco antes de la primera palabra:
        # encima de la palabra tapa justo el arranque de la frase clave
        # (medido en el piloto: -4.9 dB sobre "Las reordenan")
        if sc["kind"] == "hero":
            put("impact", t - 0.15, 0.45)
        elif sc["kind"] == "twist":
            put("riser", t - 0.75, 0.3)
            put("impact", t - 0.15, 0.5)
    if manifest.get("cta"):
        put("pop", manifest["cta"]["from"] / FPS, 0.6)
    _write_wav(path, bus[: int(dur * SR)])
    return cues


# ---------------------------------------------------------------------------
# Render + mezcla
# ---------------------------------------------------------------------------
def _resolve_music(data: dict) -> Path | None:
    import pipeline as pl

    m = data.get("music")
    if m is False or data.get("music_mood") is None:
        return None
    if isinstance(m, str):
        cand = pl.MUSIC_DIR / m
        if cand.exists():
            return cand
        try:
            man = json.loads((pl.MUSIC_DIR / "manifest.json").read_text("utf-8"))
        except Exception:
            man = {}
        por_era = [
            pl.MUSIC_DIR / k
            for k, v in man.items()
            if isinstance(v, dict) and m in (v.get("era") or []) and (pl.MUSIC_DIR / k).exists()
        ]
        if por_era:
            return sorted(por_era)[0]
    return pl._pick_music(text=data.get("hook_card"))


def _read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
        return x, w.getframerate()


def _sound_report(voice: Path, sfx_ducked: Path) -> dict:
    v, sr = _read_wav(voice)
    s, _ = _read_wav(sfx_ducked)
    n = min(len(v), len(s))
    # 100 ms y solo donde la voz habla de verdad (> -30 dBFS): "tapar la voz"
    # es competir con una palabra, no sonar en el silencio previo
    win = int(0.1 * sr)
    rows = []
    for k in range(0, n - win, win):
        vr = float(np.sqrt(np.mean(v[k : k + win] ** 2)) + 1e-9)
        sr_ = float(np.sqrt(np.mean(s[k : k + win] ** 2)) + 1e-9)
        if sr_ > 1e-3 and vr > 0.03:
            rows.append(20 * math.log10(sr_ / vr))
    return {
        "windows_with_both": len(rows),
        "sfx_vs_voice_db_max": round(max(rows), 1) if rows else None,
        "sfx_vs_voice_db_median": round(float(np.median(rows)), 1) if rows else None,
        "sfx_peak_dbfs": round(20 * math.log10(float(np.max(np.abs(s))) + 1e-9), 1),
    }


def render(
    out_dir: Path,
    data: dict,
    words: list[tuple[float, float, str]],
    audio_path: Path,
    cta_text: str | None = None,
    cta_position: str | None = None,
) -> Path:
    import pipeline as pl

    t0 = time.time()
    out_dir = Path(out_dir)
    clips = out_dir / "clips"
    clips.mkdir(exist_ok=True)
    audio_dur = pl.ffprobe_duration(audio_path)
    manifest = build_manifest(out_dir, data, words, audio_dur, cta_text, cta_position)
    kinds = [s["kind"] for s in manifest["scenes"]]
    _log(f"{len(kinds)} escenas: {' '.join(kinds)} | {manifest['durationInFrames']} frames")
    (out_dir / "motion_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    props = clips / "motion_props.json"
    new_props = json.dumps({"manifest": manifest}, ensure_ascii=False)
    engine = clips / "motion_engine.mp4"
    # Si el manifest no cambio, el video tampoco: solo se rehace la mezcla
    # (ajustes de sonido sin pagar ~5 min de render)
    same = engine.exists() and props.exists() and props.read_text(encoding="utf-8") == new_props
    props.write_text(new_props, encoding="utf-8")
    npx = shutil.which("npx") or "npx"
    import os

    t_r = time.time()
    if same:
        _log("manifest sin cambios: reuso motion_engine.mp4, solo remezclo")
    else:
      _log("renderizando KorexMotion (Remotion)...")
      _run(
        [
            npx, "remotion", "render", "src/index.jsx", "KorexMotion", str(engine.resolve()),
            "--props", str(props.resolve()),
            f"--concurrency={max(2, int((os.cpu_count() or 4) * 0.75))}",
            "--muted", "--crf=18",
        ],
        cwd=MOTION,
    )
    render_s = time.time() - t_r

    sfx_wav = clips / "sfx_bus.wav"
    cues = build_sfx_bus(manifest, audio_dur, sfx_wav)
    music = _resolve_music(data)

    final = out_dir / "video.mp4"
    inputs = ["-i", str(engine), "-i", str(audio_path), "-i", str(sfx_wav)]
    fc = (
        "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,asplit=4[vmix][vt1][vt2][vstem];"
        f"[2:a]volume={SFX_VOLUME}[sfx0];"
        # el bus de efectos tambien se agacha bajo la voz (mas suave que la
        # musica: los acentos deben oirse entre palabras, nunca encima)
        "[sfx0][vt1]sidechaincompress=threshold=0.02:ratio=8:attack=5:release=200,asplit=2[sfx][sfxstem];"
    )
    labels = "[vmix][sfx]"
    if music:
        inputs += ["-i", str(music)]
        fade = min(2.5, audio_dur / 4)
        fc += (
            f"[3:a]aloop=loop=-1:size=2e9,volume={pl.MUSIC_VOLUME},"
            f"afade=t=in:st=0:d={fade:.2f},afade=t=out:st={max(audio_dur - fade, 0):.2f}:d={fade:.2f}[bg0];"
            "[bg0][vt2]sidechaincompress=threshold=0.03:ratio=8:attack=50:release=300[bg];"
        )
        labels += "[bg]"
    else:
        fc += "[vt2]anullsink;"
    nlab = labels.count("[")
    fc += (
        f"{labels}amix=inputs={nlab}:duration=first:dropout_transition=0:normalize=0,"
        "loudnorm=I=-14:TP=-1.0:LRA=11[aout]"
    )
    stem_v = clips / "stem_voice.wav"
    stem_s = clips / "stem_sfx.wav"
    _run(
        [
            "ffmpeg", "-y", *inputs, "-filter_complex", fc,
            "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(final),
            "-map", "[vstem]", "-ac", "1", str(stem_v),
            "-map", "[sfxstem]", "-ac", "1", str(stem_s),
        ]
    )
    report = _sound_report(stem_v, stem_s)
    report.update(
        {
            "cues": cues,
            "music": music.name if music else None,
            "render_seconds": round(render_s, 1),
            "motion_total_seconds": round(time.time() - t0, 1),
        }
    )
    (out_dir / "sound_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    _log(
        f"listo: {final.name} | render {render_s:.0f}s | sfx vs voz max "
        f"{report['sfx_vs_voice_db_max']} dB | musica: {report['music']}"
    )
    return final


def _main(argv: list[str]) -> int:
    """Re-render sobre una carpeta ya producida (reusa voice.mp3 + words.json)."""
    if not argv:
        print(__doc__)
        return 1
    out_dir = Path(argv[0])
    data = json.loads((out_dir / "script.json").read_text(encoding="utf-8"))
    wj = out_dir / "words.json"
    if not wj.exists():
        print("falta words.json (se escribe al producir por pipeline.py)")
        return 1
    words = [tuple(w) for w in json.loads(wj.read_text(encoding="utf-8"))]
    cta = json.loads((out_dir / "motion_manifest.json").read_text("utf-8")).get("cta") if (out_dir / "motion_manifest.json").exists() else None
    render(
        out_dir, data, words, out_dir / "voice.mp3",
        cta_text=(cta or {}).get("text"), cta_position="middle" if cta else None,
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(_main(sys.argv[1:]))
