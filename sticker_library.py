"""Libreria de stickers generados UNA sola vez con IA y reutilizados en todos
los videos (pedido usuario 22 jul 2026: no regenerar/pagar el mismo concepto
en cada corrida, tener un catalogo fijo de ~100 stickers listos en disco).

Cubre los dos canales que corren hoy en este repo: finanzas personales (temas
en ingles, topics.txt) y gamer/Skick (guiones en espanol, guion_gamer_latam_*.
json), mas un set generico de reacciones/tiempo/documental que ya usaba
pipeline.py via _EMOJI_CATEGORIES.

Uso:
    py sticker_library.py --list                 # ver que falta generar
    py sticker_library.py --generate              # generar los que faltan
    py sticker_library.py --generate --force      # regenerar todo
    py sticker_library.py --generate --only money,lag,smurf

Requiere GEMINI_API_KEY en .env (gratis en https://aistudio.google.com/apikey)
y opcionalmente rembg (`py -m pip install rembg onnxruntime`) para recortar el
fondo -- sin rembg se guarda el PNG con el fondo solido que devuelve el modelo.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import unicodedata
from pathlib import Path

import requests

ROOT = Path(__file__).parent
STICKERS_DIR = ROOT / "assets" / "stickers"
MANIFEST_PATH = STICKERS_DIR / "manifest.json"

NANOBANANA_MODEL = "gemini-2.5-flash-image"

# Estilo unico para las 100 -- coherencia visual entre stickers es lo que hace
# que se vean "de la misma libreria" en vez de un colage random. Fondo solido
# blanco (no transparente): los modelos de imagen no devuelven alpha real, asi
# que se pide un fondo facil de recortar despues con rembg.
STICKER_STYLE_SUFFIX = (
    ", flat 2D vector sticker icon, thick bold black outline, bold saturated "
    "flat colors, subtle drop shadow, simple clean shapes, single object "
    "centered and filling most of the frame, plain solid white background, "
    "no text, no watermark, no logos, no gradients, no realistic textures, "
    "mobile game HUD icon aesthetic"
)

# (id, triggers ES+EN en minuscula, prompt corto del icono, categoria)
STICKER_LIBRARY: list[dict] = [
    # ---- finanzas / general (canal en ingles, topics.txt) ----
    {"id": "money", "triggers": ("money", "cash", "dinero", "efectivo", "plata"),
     "prompt": "a thick stack of colorful banknotes fanned out with a glowing dollar sign above it",
     "category": "finanzas"},
    {"id": "piggy_bank", "triggers": ("piggy bank", "alcancia", "savings", "ahorro", "ahorros"),
     "prompt": "a cute pink piggy bank with a coin slot and a shiny gold coin dropping into it",
     "category": "finanzas"},
    {"id": "debt", "triggers": ("debt", "deuda", "owe", "credit card debt"),
     "prompt": "a red credit card snapped in half with warning cracks around it",
     "category": "finanzas"},
    {"id": "bank", "triggers": ("bank", "banco", "banking"),
     "prompt": "a classic bank building icon with tall pillars and a dollar sign on the front",
     "category": "finanzas"},
    {"id": "budget", "triggers": ("budget", "presupuesto", "budgeting"),
     "prompt": "a notepad icon with a small pie chart and a pencil ticking a checkbox",
     "category": "finanzas"},
    {"id": "salary", "triggers": ("salary", "paycheck", "sueldo", "salario", "income", "ingreso"),
     "prompt": "an envelope bursting open with coins and a glowing dollar sign",
     "category": "finanzas"},
    {"id": "rent", "triggers": ("rent", "alquiler", "renta"),
     "prompt": "a small house icon with a dollar sign and a key hanging from the door",
     "category": "finanzas"},
    {"id": "coffee", "triggers": ("coffee", "cafe", "latte"),
     "prompt": "a to-go coffee cup icon with steam swirls and a small dollar sign on the sleeve",
     "category": "finanzas"},
    {"id": "house", "triggers": ("house", "casa", "home", "mortgage", "hipoteca"),
     "prompt": "a cute cartoon house icon with a red heart-shaped welcome mat",
     "category": "finanzas"},
    {"id": "car", "triggers": ("car", "auto", "coche", "carro"),
     "prompt": "a shiny cartoon car icon with sparkle highlights",
     "category": "finanzas"},
    {"id": "loan", "triggers": ("loan", "prestamo", "credito"),
     "prompt": "a handshake icon over a small stack of coins",
     "category": "finanzas"},
    {"id": "interest_rate", "triggers": ("interest", "interes", "tasa", "apr"),
     "prompt": "a glowing percentage sign with a small upward arrow beside it",
     "category": "finanzas"},
    {"id": "tax", "triggers": ("tax", "taxes", "impuesto", "impuestos"),
     "prompt": "a government building icon stamping a document with a red seal",
     "category": "finanzas"},
    {"id": "wallet", "triggers": ("wallet", "billetera", "cartera"),
     "prompt": "an open brown leather wallet stuffed with cash and cards",
     "category": "finanzas"},
    {"id": "calculator", "triggers": ("calculator", "calculadora"),
     "prompt": "a cartoon calculator icon with a big glowing green checkmark on the screen",
     "category": "finanzas"},
    {"id": "chart_up", "triggers": ("profit", "growth", "ganancia", "crecimiento", "gain"),
     "prompt": "a bold green upward-trending bar chart icon with an arrow",
     "category": "finanzas"},
    {"id": "chart_down", "triggers": ("loss", "perdida", "crash", "drop"),
     "prompt": "a bold red downward-trending bar chart icon with an arrow",
     "category": "finanzas"},
    {"id": "coins", "triggers": ("coins", "monedas", "change", "suelto"),
     "prompt": "a pile of shiny gold coins stacked unevenly",
     "category": "finanzas"},
    {"id": "gold", "triggers": ("gold", "oro"),
     "prompt": "a shiny gold bar icon with a sparkle highlight",
     "category": "finanzas"},
    {"id": "invoice", "triggers": ("invoice", "bill", "factura", "cuenta"),
     "prompt": "a paper invoice icon with a red OVERDUE stamp",
     "category": "finanzas"},
    {"id": "discount", "triggers": ("discount", "descuento", "sale", "oferta"),
     "prompt": "a red price tag icon with a bold percent symbol",
     "category": "finanzas"},
    {"id": "emergency_fund", "triggers": ("emergency fund", "fondo de emergencia"),
     "prompt": "a glass jar full of coins with a red cross bandage on it",
     "category": "finanzas"},
    {"id": "investment", "triggers": ("invest", "investing", "inversion", "stock", "accion"),
     "prompt": "an upward arrow made of stacked gold coins",
     "category": "finanzas"},
    {"id": "crypto", "triggers": ("crypto", "bitcoin", "cripto"),
     "prompt": "a glowing bitcoin coin icon with circuit-board lines",
     "category": "finanzas"},
    {"id": "lottery", "triggers": ("lottery", "loteria", "jackpot"),
     "prompt": "a golden lottery ticket icon with a shining star",
     "category": "finanzas"},
    {"id": "subscription", "triggers": ("subscription", "suscripcion", "membership"),
     "prompt": "a phone screen icon with a recurring circular arrow and a dollar sign",
     "category": "finanzas"},
    {"id": "checking_account", "triggers": ("checking account", "cuenta bancaria", "account"),
     "prompt": "a bank card icon hovering above a smartphone screen",
     "category": "finanzas"},
    {"id": "shopping", "triggers": ("shopping", "compras", "impulse buy"),
     "prompt": "a shopping bag icon overflowing with items and a small warning triangle",
     "category": "finanzas"},

    # ---- gamer / Skick (canal en espanol, guion_gamer_latam_*.json) ----
    {"id": "level_up", "triggers": ("level up", "subio de nivel", "sube de nivel", "lvl up", "nivel"),
     "prompt": "a glowing golden up arrow bursting out of a video game level badge",
     "category": "gamer"},
    {"id": "level_down", "triggers": ("nivel bajo", "low level", "noob level"),
     "prompt": "a cracked dim video game level badge with a downward arrow",
     "category": "gamer"},
    {"id": "smurf", "triggers": ("smurf", "cuenta nueva", "twink"),
     "prompt": "a suspicious video game profile icon wearing a disguise mask",
     "category": "gamer"},
    {"id": "lag", "triggers": ("lag", "lagueando", "delay"),
     "prompt": "a spinning loading wheel icon with jagged glitch lightning lines",
     "category": "gamer"},
    {"id": "ping", "triggers": ("ping", "latencia"),
     "prompt": "a signal bars icon with a bold red X over it",
     "category": "gamer"},
    {"id": "nerf", "triggers": ("nerf", "nerfeado", "nerfearon"),
     "prompt": "a video game sword icon broken in half with a downward arrow",
     "category": "gamer"},
    {"id": "buff", "triggers": ("buff", "buffeado", "buffearon"),
     "prompt": "a glowing video game shield icon with an upward arrow",
     "category": "gamer"},
    {"id": "ban", "triggers": ("ban", "baneado", "banned", "baneo"),
     "prompt": "a red hammer icon stamping a game controller with a ban symbol",
     "category": "gamer"},
    {"id": "report", "triggers": ("report", "reportado", "reporte"),
     "prompt": "a red flag icon with an exclamation mark over a game profile card",
     "category": "gamer"},
    {"id": "camper", "triggers": ("camper", "campeando", "camping"),
     "prompt": "a cartoon bush icon with two sneaky eyes peeking out",
     "category": "gamer"},
    {"id": "afk", "triggers": ("afk", "ausente"),
     "prompt": "a game character icon frozen with sleepy zzz symbols above it",
     "category": "gamer"},
    {"id": "one_more_game", "triggers": ("one more game", "una mas", "otra partida"),
     "prompt": "a glowing rematch button icon with a circular replay arrow",
     "category": "gamer"},
    {"id": "whale", "triggers": ("whale", "ballena", "pay to win", "p2w"),
     "prompt": "a cartoon whale icon wearing a tiny crown made of coins",
     "category": "gamer"},
    {"id": "skin", "triggers": ("skin", "skin nueva", "outfit"),
     "prompt": "a glowing treasure chest icon with a shiny costume peeking out",
     "category": "gamer"},
    {"id": "loot_box", "triggers": ("loot box", "caja", "gacha"),
     "prompt": "a glowing golden loot chest icon bursting with sparkles",
     "category": "gamer"},
    {"id": "rage_quit", "triggers": ("rage quit", "se salio", "tilt", "tilteado"),
     "prompt": "an angry red game controller icon with steam coming out of it",
     "category": "gamer"},
    {"id": "gg_easy", "triggers": ("gg", "gg ez", "easy win"),
     "prompt": "a glowing trophy icon with GG-style star checkmarks around it",
     "category": "gamer"},
    {"id": "victory", "triggers": ("victory", "gano", "gane", "win", "victoria"),
     "prompt": "a golden trophy icon with confetti bursting around it",
     "category": "gamer"},
    {"id": "defeat", "triggers": ("defeat", "perdio", "perdi", "derrota", "lose"),
     "prompt": "a cracked shield icon with a downward red arrow",
     "category": "gamer"},
    {"id": "health_bar", "triggers": ("health", "vida", "hp"),
     "prompt": "a red heart-shaped health bar icon half empty",
     "category": "gamer"},
    {"id": "mana_bar", "triggers": ("mana", "energia"),
     "prompt": "a blue glowing energy orb icon",
     "category": "gamer"},
    {"id": "boss", "triggers": ("boss", "jefe final", "jefe"),
     "prompt": "a menacing video game boss skull icon with glowing red eyes",
     "category": "gamer"},
    {"id": "noob", "triggers": ("noob", "novato"),
     "prompt": "a confused green rookie game character icon with a question mark",
     "category": "gamer"},
    {"id": "pro_player", "triggers": ("pro", "profesional", "sweaty", "sweat"),
     "prompt": "a golden star badge icon with a controller silhouette",
     "category": "gamer"},
    {"id": "ranked", "triggers": ("ranked", "elo", "rango"),
     "prompt": "a tiered medal badge icon shifting from bronze to diamond",
     "category": "gamer"},
    {"id": "matchmaking", "triggers": ("matchmaking", "buscando partida"),
     "prompt": "a magnifying glass icon scanning over game character silhouettes",
     "category": "gamer"},
    {"id": "teammate", "triggers": ("teammate", "companero", "duo"),
     "prompt": "two game controller icons doing a fist bump",
     "category": "gamer"},
    {"id": "enemy", "triggers": ("enemy", "enemigo", "rival"),
     "prompt": "a red glowing crosshair target icon over a silhouette",
     "category": "gamer"},
    {"id": "respawn", "triggers": ("respawn", "reaparecer"),
     "prompt": "a glowing circular portal icon with an upward arrow",
     "category": "gamer"},
    {"id": "cooldown", "triggers": ("cooldown", "enfriamiento"),
     "prompt": "a clock icon overlaid on a glowing ability button",
     "category": "gamer"},
    {"id": "ultimate", "triggers": ("ultimate", "definitiva", "ulti"),
     "prompt": "an exploding starburst icon around a glowing ability symbol",
     "category": "gamer"},
    {"id": "combo", "triggers": ("combo", "racha"),
     "prompt": "a chained lightning bolt icon with a multiplier burst effect",
     "category": "gamer"},
    {"id": "new_account", "triggers": ("cuenta nueva", "fresh account"),
     "prompt": "a blank game profile card icon with a plus sign",
     "category": "gamer"},
    {"id": "hacker", "triggers": ("hacker", "cheater", "tramposo", "hackeando"),
     "prompt": "a shady game character icon wearing a dark hood with glitchy red eyes",
     "category": "gamer"},

    # ---- reacciones / emociones (hooks genericos) ----
    {"id": "shock", "triggers": ("shocking", "increible", "wow", "no puedo creer"),
     "prompt": "a cartoon face icon with wide eyes and jaw dropped in shock",
     "category": "emocion"},
    {"id": "mind_blown", "triggers": ("mind blown", "mente volada"),
     "prompt": "a cartoon head icon exploding into colorful stars and sparks",
     "category": "emocion"},
    {"id": "laughing", "triggers": ("laughing", "jajaja", "funny", "gracioso"),
     "prompt": "a cartoon crying-laughing face icon with tears of joy",
     "category": "emocion"},
    {"id": "crying", "triggers": ("crying", "llorando", "sad", "triste"),
     "prompt": "a cartoon face icon with big blue tears streaming down",
     "category": "emocion"},
    {"id": "angry", "triggers": ("angry", "enojado", "furioso", "rage"),
     "prompt": "a cartoon red face icon with steam coming out of the ears",
     "category": "emocion"},
    {"id": "confused", "triggers": ("confused", "confundido", "que"),
     "prompt": "a cartoon face icon with a big question mark and a raised eyebrow",
     "category": "emocion"},
    {"id": "thinking", "triggers": ("thinking", "pensando"),
     "prompt": "a cartoon face icon with a hand on chin and a lightbulb above",
     "category": "emocion"},
    {"id": "secret", "triggers": ("secret", "secreto"),
     "prompt": "a glowing padlock icon over a folded note with a shush finger",
     "category": "emocion"},
    {"id": "warning", "triggers": ("warning", "cuidado", "atencion"),
     "prompt": "a bold yellow and black warning triangle icon with an exclamation mark",
     "category": "emocion"},
    {"id": "danger", "triggers": ("danger", "peligro"),
     "prompt": "a bold red skull and crossbones danger icon",
     "category": "emocion"},
    {"id": "trophy", "triggers": ("trophy", "campeon", "champion"),
     "prompt": "a glowing golden trophy icon with a star on top",
     "category": "emocion"},
    {"id": "checkmark", "triggers": ("correct", "right", "correcto"),
     "prompt": "a bold green circle icon with a thick white checkmark",
     "category": "emocion"},
    {"id": "wrong_x", "triggers": ("wrong", "incorrecto", "error"),
     "prompt": "a bold red circle icon with a thick white X mark",
     "category": "emocion"},
    {"id": "fail", "triggers": ("fail", "fallo", "epic fail"),
     "prompt": "a red stamp icon reading FAIL in bold cracked letters",
     "category": "emocion"},
    {"id": "success", "triggers": ("success", "exito", "lograste"),
     "prompt": "a golden starburst icon with a glowing checkmark at the center",
     "category": "emocion"},
    {"id": "exclamation", "triggers": ("importante", "atento", "alert"),
     "prompt": "a bold orange exclamation mark icon inside a speech bubble",
     "category": "emocion"},

    # ---- tiempo / urgencia ----
    {"id": "clock", "triggers": ("time", "tiempo", "minutos", "hora", "horas"),
     "prompt": "a vintage alarm clock icon with the hands spinning fast",
     "category": "tiempo"},
    {"id": "calendar", "triggers": ("calendar", "calendario", "fecha"),
     "prompt": "a desk calendar icon with a red circled date",
     "category": "tiempo"},
    {"id": "deadline", "triggers": ("deadline", "plazo", "limite"),
     "prompt": "an hourglass icon with red sand almost run out",
     "category": "tiempo"},
    {"id": "alarm", "triggers": ("alarm", "alarma"),
     "prompt": "a ringing bell alarm icon with sound wave lines",
     "category": "tiempo"},
    {"id": "countdown", "triggers": ("countdown", "cuenta regresiva"),
     "prompt": "a glowing digital countdown timer icon showing 3-2-1",
     "category": "tiempo"},

    # ---- documental / misterio / peligro (compatibilidad con _EMOJI_CATEGORIES) ----
    {"id": "radio", "triggers": ("radio", "transmission", "signal", "broadcast"),
     "prompt": "a vintage military radio icon with an antenna and sound waves",
     "category": "documental"},
    {"id": "gun", "triggers": ("shot", "gun", "gunfire", "rifle", "pistol", "disparo", "arma"),
     "prompt": "a cartoon pistol icon with a small muzzle flash",
     "category": "documental"},
    {"id": "sword", "triggers": ("sword", "blade", "knife", "espada"),
     "prompt": "a shiny sword icon with a glowing blade edge",
     "category": "documental"},
    {"id": "explosion", "triggers": ("explosion", "bomb", "blast"),
     "prompt": "a bold cartoon explosion burst icon in orange and yellow",
     "category": "documental"},
    {"id": "fire", "triggers": ("fire", "burn", "burned", "flame", "fuego"),
     "prompt": "a bold cartoon flame icon in orange and red",
     "category": "documental"},
    {"id": "water", "triggers": ("water", "flood", "agua"),
     "prompt": "a bold blue water droplet icon with ripples",
     "category": "documental"},
    {"id": "key_lock", "triggers": ("key", "lock", "unlock", "llave", "candado"),
     "prompt": "a golden key icon next to an open padlock",
     "category": "documental"},
    {"id": "letter_document", "triggers": ("letter", "document", "telegram", "note", "documento", "carta"),
     "prompt": "a folded paper letter icon with a red wax seal",
     "category": "documental"},
    {"id": "phone_call", "triggers": ("phone", "call", "telefono", "llamada"),
     "prompt": "a retro red telephone icon with sound wave lines",
     "category": "documental"},
    {"id": "bell", "triggers": ("bell", "siren", "campana"),
     "prompt": "a golden bell icon mid-ring with motion lines",
     "category": "documental"},
    {"id": "plane", "triggers": ("plane", "aircraft", "flight", "avion"),
     "prompt": "a small cartoon airplane icon banking through clouds",
     "category": "documental"},
    {"id": "ship", "triggers": ("ship", "boat", "barco", "vessel"),
     "prompt": "a cartoon ship icon sailing over blue waves",
     "category": "documental"},
    {"id": "tank", "triggers": ("tank", "armored", "tanque"),
     "prompt": "a cartoon military tank icon with a raised cannon",
     "category": "documental"},
    {"id": "medal", "triggers": ("medal", "award", "medalla"),
     "prompt": "a shiny gold medal icon hanging from a red ribbon",
     "category": "documental"},
    {"id": "flag", "triggers": ("flag", "banner", "bandera"),
     "prompt": "a waving flag icon on a pole",
     "category": "documental"},
    {"id": "mystery", "triggers": ("mystery", "unsolved", "misterio"),
     "prompt": "a bold glowing question mark icon with a magnifying glass",
     "category": "documental"},
    {"id": "death", "triggers": ("dead", "death", "killed", "muerte"),
     "prompt": "a stylized skull icon with crossbones, flat cartoon style",
     "category": "documental"},
]


# --------------------------------------------------------------- matching

def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", text).strip()


_TRIGGER_INDEX: dict[str, str] | None = None


def _build_trigger_index() -> dict[str, str]:
    global _TRIGGER_INDEX
    if _TRIGGER_INDEX is None:
        idx: dict[str, str] = {}
        for concept in STICKER_LIBRARY:
            for trig in concept["triggers"]:
                idx[_normalize(trig)] = concept["id"]
        _TRIGGER_INDEX = idx
    return _TRIGGER_INDEX


def match_sticker(word: str) -> str | None:
    """Matchea una sola palabra (o frase corta) contra el catalogo. Solo match
    exacto (normalizado) -- evita falsos positivos tipo 'car' matcheando
    dentro de 'cardio'."""
    return _build_trigger_index().get(_normalize(word))


# --------------------------------------------------------------- manifest

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def get_sticker_path(sticker_id: str) -> Path | None:
    manifest = load_manifest()
    entry = manifest.get(sticker_id)
    if not entry:
        return None
    path = STICKERS_DIR / entry["file"]
    return path if path.exists() else None


# --------------------------------------------------------------- cues para el pipeline

def find_keyword_cues(words: list[tuple[float, float, str]], min_gap: float = 1.8,
                       max_cues: int = 40) -> list[tuple[float, str, str]]:
    """Escanea las palabras REALMENTE narradas (con timestamp real de TTS, no
    el texto de search_terms) y devuelve (tiempo, sticker_id, palabra) por
    cada keyword detectada -- 1 sticker por CADA vez que se dice la palabra,
    no 1 por escena. min_gap evita 2 stickers pegados si dos triggers caen
    muy cerca en el guion."""
    manifest = load_manifest()
    cues: list[tuple[float, str, str]] = []
    last_t = -min_gap
    for start, _end, word in words:
        sid = match_sticker(word)
        if not sid or sid not in manifest:
            continue
        if start - last_t < min_gap:
            continue
        cues.append((start, sid, word))
        last_t = start
        if len(cues) >= max_cues:
            break
    return cues


def prepare_render_cues(words: list[tuple[float, float, str]], public_dir: Path,
                         min_gap: float = 1.8, max_cues: int = 40) -> list[dict]:
    """Igual que find_keyword_cues pero ya en el formato que espera
    AutoOverlay.jsx ({"time","keyword","emoji","photo"}) y copiando el PNG de
    cada sticker matcheado a public_dir (Remotion carga imagenes desde ahi)."""
    import shutil
    manifest = load_manifest()
    public_dir.mkdir(parents=True, exist_ok=True)
    cues = []
    for start, sid, word in find_keyword_cues(words, min_gap=min_gap, max_cues=max_cues):
        entry = manifest[sid]
        src = STICKERS_DIR / entry["file"]
        if not src.exists():
            continue
        dst_name = f"sticker_{sid}.png"
        dst = public_dir / dst_name
        if not dst.exists():
            shutil.copyfile(src, dst)
        cues.append({"time": start, "keyword": word.upper(), "emoji": "", "photo": dst_name})
    return cues


# --------------------------------------------------------------- generacion

def _generate_icon_image(prompt: str, api_key: str, attempts: int = 3) -> bytes | None:
    full_prompt = prompt + STICKER_STYLE_SUFFIX
    for attempt in range(attempts):
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{NANOBANANA_MODEL}:generateContent",
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"imageConfig": {"aspectRatio": "1:1"}},
                },
                timeout=60,
            )
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inlineData" in part:
                    return base64.b64decode(part["inlineData"]["data"])
            raise RuntimeError("respuesta sin imagen")
        except Exception as e:
            if attempt < attempts - 1:
                print(f"  intento {attempt + 1} fallo, reintento en 5s: {e}")
                time.sleep(5)
            else:
                print(f"  FALLO definitivo: {e}")
    return None


def _remove_background(raw_bytes: bytes) -> bytes:
    from rembg import remove
    return remove(raw_bytes)


def generate_library(force: bool = False, only: list[str] | None = None,
                      delay: float = 4.0) -> None:
    STICKERS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: falta GEMINI_API_KEY en .env (gratis en https://aistudio.google.com/apikey)")
        return

    try:
        import rembg  # noqa: F401
        has_rembg = True
    except ImportError:
        has_rembg = False
        print("AVISO: rembg no instalado (py -m pip install rembg onnxruntime) -- "
              "los PNG quedaran con fondo blanco solido en vez de transparente")

    todo = [c for c in STICKER_LIBRARY if (only is None or c["id"] in only)]
    pending = [c for c in todo if force or c["id"] not in manifest
               or not (STICKERS_DIR / manifest.get(c["id"], {}).get("file", "")).exists()]
    print(f"{len(pending)}/{len(todo)} stickers a generar "
          f"({len(todo) - len(pending)} ya existen, usa --force para regenerar)")

    for i, concept in enumerate(pending, 1):
        print(f"[{i}/{len(pending)}] {concept['id']} ...")
        raw = _generate_icon_image(concept["prompt"], api_key)
        if raw is None:
            continue
        data = _remove_background(raw) if has_rembg else raw
        fname = f"{concept['id']}.png"
        (STICKERS_DIR / fname).write_bytes(data)
        manifest[concept["id"]] = {
            "file": fname,
            "triggers": list(concept["triggers"]),
            "category": concept["category"],
            "prompt": concept["prompt"],
        }
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if i < len(pending):
            time.sleep(delay)

    print(f"Listo: {len(manifest)}/{len(STICKER_LIBRARY)} stickers en {STICKERS_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera/gestiona la libreria de stickers reutilizable")
    parser.add_argument("--generate", action="store_true", help="genera los stickers faltantes")
    parser.add_argument("--force", action="store_true", help="regenera aunque ya existan")
    parser.add_argument("--only", help="ids separados por coma, ej: money,lag,smurf")
    parser.add_argument("--list", action="store_true", help="muestra estado del catalogo")
    args = parser.parse_args()

    if args.list or not args.generate:
        manifest = load_manifest()
        for c in STICKER_LIBRARY:
            done = c["id"] in manifest and (STICKERS_DIR / manifest[c["id"]]["file"]).exists()
            status = "OK   " if done else "falta"
            print(f"  [{status}] {c['id']:20} ({c['category']:10}) {', '.join(c['triggers'][:4])}")
        done_n = sum(1 for c in STICKER_LIBRARY
                     if c["id"] in manifest and (STICKERS_DIR / manifest[c["id"]]["file"]).exists())
        print(f"\n{done_n}/{len(STICKER_LIBRARY)} generados")
        if not args.generate:
            print("(corre con --generate para generar los que faltan)")
        return

    only = args.only.split(",") if args.only else None
    generate_library(force=args.force, only=only)


if __name__ == "__main__":
    main()
