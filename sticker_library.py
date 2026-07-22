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

# bug real (22 jul 2026): esta faltando cargar el .env -- os.getenv leia solo
# variables de entorno del proceso, nunca las del archivo .env (a diferencia
# de pipeline.py, que si llama a load_dotenv()). Con GEMINI_API_KEY solo en
# .env, --generate fallaba de entrada con "falta GEMINI_API_KEY" aunque
# estuviera bien configurada.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

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

    # ---- gethiddenfacts: espionaje / Guerra Fria / WWII / misterio historico ----
    # (vocabulario sacado de scripts/*.json reales: agent_garbo, mkultra_secret,
    # operation_cicero, markov_umbrella, etc. -- pedido usuario 22 jul 2026)
    {"id": "spy", "triggers": ("spy", "espia", "secret agent", "agente secreto"),
     "prompt": "a shadowy trench-coat figure icon wearing a fedora hat and dark sunglasses",
     "category": "hiddenfacts"},
    {"id": "double_agent", "triggers": ("double agent", "agente doble", "mole", "topo"),
     "prompt": "a two-faced mask icon split in half showing two different expressions",
     "category": "hiddenfacts"},
    {"id": "informant", "triggers": ("informant", "informante", "chivato", "tipster"),
     "prompt": "a whispering mouth icon next to an ear with a small speech bubble",
     "category": "hiddenfacts"},
    {"id": "handler", "triggers": ("handler", "contacto", "case officer", "manejador"),
     "prompt": "a hand icon pulling invisible strings like a puppeteer",
     "category": "hiddenfacts"},
    {"id": "dead_drop", "triggers": ("dead drop", "buzon muerto", "escondite secreto"),
     "prompt": "a hollow tree stump icon with a rolled note hidden inside",
     "category": "hiddenfacts"},
    {"id": "secret_police", "triggers": ("secret police", "policia secreta", "gestapo", "stasi"),
     "prompt": "a dark trench-coat silhouette icon standing under a single spotlight",
     "category": "hiddenfacts"},
    {"id": "classified_stamp", "triggers": ("classified", "clasificado", "top secret", "alto secreto"),
     "prompt": "a red TOP SECRET rubber stamp icon over a paper folder",
     "category": "hiddenfacts"},
    {"id": "hidden_camera", "triggers": ("hidden camera", "camara oculta", "spy camera"),
     "prompt": "a tiny vintage spy camera icon peeking from behind a curtain fold",
     "category": "hiddenfacts"},
    {"id": "microfilm", "triggers": ("microfilm", "microfilme"),
     "prompt": "a small film reel icon glowing under a magnifying lens",
     "category": "hiddenfacts"},
    {"id": "poison", "triggers": ("poison", "poisoned", "veneno", "envenenado"),
     "prompt": "a small vintage glass vial icon with a skull label and a single drop falling",
     "category": "hiddenfacts"},
    {"id": "embassy", "triggers": ("embassy", "embajada"),
     "prompt": "a grand embassy building icon with a flagpole on the roof",
     "category": "hiddenfacts"},
    {"id": "briefcase", "triggers": ("briefcase", "maletin"),
     "prompt": "a locked leather briefcase icon with a glowing keyhole",
     "category": "hiddenfacts"},
    {"id": "cover_up", "triggers": ("cover up", "encubrimiento", "taparon"),
     "prompt": "a large black marker icon redacting lines of text on a document",
     "category": "hiddenfacts"},
    {"id": "conspiracy", "triggers": ("conspiracy", "conspiracion", "complot"),
     "prompt": "a corkboard icon with photos connected by red string",
     "category": "hiddenfacts"},
    {"id": "newspaper_headline", "triggers": ("newspaper", "headline", "periodico", "titular"),
     "prompt": "a folded vintage newspaper icon with a bold black headline banner",
     "category": "hiddenfacts"},
    {"id": "morse_code", "triggers": ("morse code", "codigo morse"),
     "prompt": "a row of glowing dots and dashes icon like a telegraph signal",
     "category": "hiddenfacts"},
    {"id": "cipher", "triggers": ("cipher", "cifrado", "codigo secreto"),
     "prompt": "a scrambled letter grid icon with one glowing highlighted symbol",
     "category": "hiddenfacts"},
    {"id": "enigma_machine", "triggers": ("enigma", "maquina enigma"),
     "prompt": "a vintage mechanical cipher machine icon with round dial keys",
     "category": "hiddenfacts"},
    {"id": "codebreaker", "triggers": ("codebreaker", "descifrador", "decodificador"),
     "prompt": "a magnifying glass icon hovering over scrambled code symbols",
     "category": "hiddenfacts"},
    {"id": "typewriter", "triggers": ("typewriter", "maquina de escribir"),
     "prompt": "a vintage black typewriter icon with a sheet of paper rolled in",
     "category": "hiddenfacts"},
    {"id": "prisoner", "triggers": ("prisoner", "prisionero", "preso"),
     "prompt": "a striped prison uniform icon with a small ball and chain",
     "category": "hiddenfacts"},
    {"id": "prison_cell", "triggers": ("prison cell", "celda", "carcel"),
     "prompt": "a jail cell icon with thick metal bars and a small barred window",
     "category": "hiddenfacts"},
    {"id": "escape", "triggers": ("escape", "fuga", "escaparon"),
     "prompt": "a sawed-through prison bar icon with a rope ladder hanging out",
     "category": "hiddenfacts"},
    {"id": "capture", "triggers": ("capture", "captured", "captura", "capturado"),
     "prompt": "a glowing net icon closing over a running silhouette",
     "category": "hiddenfacts"},
    {"id": "execution", "triggers": ("execution", "ejecucion", "fusilamiento"),
     "prompt": "a blindfold icon draped over a solemn wooden post",
     "category": "hiddenfacts"},
    {"id": "firing_squad", "triggers": ("firing squad", "peloton de fusilamiento"),
     "prompt": "a row of vintage rifles standing at attention icon",
     "category": "hiddenfacts"},
    {"id": "assassination", "triggers": ("assassination", "asesinato", "magnicidio"),
     "prompt": "a red crosshair icon over a shadowy walking silhouette",
     "category": "hiddenfacts"},
    {"id": "evidence", "triggers": ("evidence", "evidencia", "pruebas"),
     "prompt": "an evidence bag icon sealed with a red tag and label",
     "category": "hiddenfacts"},
    {"id": "autopsy", "triggers": ("autopsy", "autopsia"),
     "prompt": "a clipboard icon with a body outline diagram and a small scalpel",
     "category": "hiddenfacts"},
    {"id": "forensics", "triggers": ("forensics", "forense"),
     "prompt": "a magnifying glass icon hovering over a fingerprint",
     "category": "hiddenfacts"},
    {"id": "witness", "triggers": ("witness", "testigo"),
     "prompt": "a wide-open eye icon peeking through a slightly open door",
     "category": "hiddenfacts"},
    {"id": "testimony", "triggers": ("testimony", "testimonio", "declaracion"),
     "prompt": "a raised hand icon swearing an oath over a small book",
     "category": "hiddenfacts"},
    {"id": "confession", "triggers": ("confession", "confesion"),
     "prompt": "a signed paper icon with a fountain pen and a red thumbprint",
     "category": "hiddenfacts"},
    {"id": "trial", "triggers": ("trial", "juicio", "court martial", "corte marcial"),
     "prompt": "a wooden judge's gavel icon striking a sound block",
     "category": "hiddenfacts"},
    {"id": "sentence", "triggers": ("sentence", "sentencia", "condena"),
     "prompt": "a court document icon stamped GUILTY in bold red letters",
     "category": "hiddenfacts"},
    {"id": "handcuffs", "triggers": ("handcuffs", "esposas"),
     "prompt": "a pair of shiny metal handcuffs icon linked together",
     "category": "hiddenfacts"},
    {"id": "interrogation", "triggers": ("interrogation", "interrogatorio"),
     "prompt": "a single bright desk lamp icon shining onto an empty chair",
     "category": "hiddenfacts"},
    {"id": "torture", "triggers": ("torture", "tortura"),
     "prompt": "a dim dungeon chain icon hanging from a stone wall",
     "category": "hiddenfacts"},
    {"id": "submarine", "triggers": ("submarine", "submarino"),
     "prompt": "a cartoon submarine icon with a periscope raised through waves",
     "category": "hiddenfacts"},
    {"id": "train", "triggers": ("train", "tren"),
     "prompt": "a vintage steam train icon puffing smoke on a track",
     "category": "hiddenfacts"},
    {"id": "tunnel", "triggers": ("tunnel", "tunel"),
     "prompt": "a dark tunnel entrance icon with a single light at the end",
     "category": "hiddenfacts"},
    {"id": "bunker", "triggers": ("bunker", "refugio subterraneo"),
     "prompt": "a concrete bunker icon with a thick steel door and a small vent",
     "category": "hiddenfacts"},
    {"id": "concentration_camp", "triggers": ("concentration camp", "campo de concentracion"),
     "prompt": "a barbed wire fence icon stretched between two wooden posts",
     "category": "hiddenfacts"},
    {"id": "resistance", "triggers": ("resistance", "resistencia", "movimiento de resistencia"),
     "prompt": "a raised fist icon holding a small torn flag",
     "category": "hiddenfacts"},
    {"id": "sabotage", "triggers": ("sabotage", "sabotaje"),
     "prompt": "a wrench icon jammed into spinning gears with sparks",
     "category": "hiddenfacts"},
    {"id": "parachute", "triggers": ("parachute", "paracaidas"),
     "prompt": "an open parachute icon with a tiny falling silhouette below",
     "category": "hiddenfacts"},
    {"id": "disguise", "triggers": ("disguise", "disfraz", "disfrazado"),
     "prompt": "a fake mustache and glasses icon on a small stick",
     "category": "hiddenfacts"},
    {"id": "defector", "triggers": ("defector", "desertor"),
     "prompt": "a running silhouette icon crossing a broken dividing wall",
     "category": "hiddenfacts"},
    {"id": "sleeper_agent", "triggers": ("sleeper agent", "agente durmiente"),
     "prompt": "a sleeping silhouette icon with a glowing open eye inside the head",
     "category": "hiddenfacts"},
    {"id": "surveillance", "triggers": ("surveillance", "vigilancia"),
     "prompt": "a pair of vintage binoculars icon with a glowing lens",
     "category": "hiddenfacts"},
    {"id": "wiretap", "triggers": ("wiretap", "escucha telefonica", "intervenido"),
     "prompt": "a rotary telephone icon with a small clip and wire attached",
     "category": "hiddenfacts"},
    {"id": "tail_someone", "triggers": ("followed", "tailed", "lo siguen", "seguimiento"),
     "prompt": "two overlapping footprint trails icon, one close behind the other",
     "category": "hiddenfacts"},
    {"id": "safehouse", "triggers": ("safehouse", "casa segura"),
     "prompt": "a plain small house icon with a glowing single window at night",
     "category": "hiddenfacts"},
    {"id": "vault", "triggers": ("vault", "boveda", "caja fuerte"),
     "prompt": "a heavy round bank vault door icon with a large dial lock",
     "category": "hiddenfacts"},
    {"id": "archive", "triggers": ("archive", "archivo"),
     "prompt": "a tall shelf of dusty filing boxes icon",
     "category": "hiddenfacts"},
    {"id": "forgery", "triggers": ("forgery", "falsificacion", "falsificar"),
     "prompt": "a fountain pen icon forging a signature with a small red flag",
     "category": "hiddenfacts"},
    {"id": "counterfeit_money", "triggers": ("counterfeit money", "dinero falso", "billetes falsos"),
     "prompt": "a stack of banknotes icon with a bold red FAKE stamp",
     "category": "hiddenfacts"},
    {"id": "passport", "triggers": ("passport", "pasaporte"),
     "prompt": "an open passport booklet icon with a stamped visa page",
     "category": "hiddenfacts"},
    {"id": "smuggling", "triggers": ("smuggling", "contrabando"),
     "prompt": "a wooden crate icon with a false bottom slightly open",
     "category": "hiddenfacts"},
    {"id": "disappearance", "triggers": ("disappeared", "vanished", "desaparecio", "desaparicion"),
     "prompt": "a fading dotted-outline silhouette icon",
     "category": "hiddenfacts"},
    {"id": "grave", "triggers": ("grave", "tumba"),
     "prompt": "a simple stone grave marker icon under a bare tree",
     "category": "hiddenfacts"},
    {"id": "skeleton", "triggers": ("skeleton", "bones", "esqueleto", "huesos"),
     "prompt": "a small cartoon skeleton hand icon holding a bone",
     "category": "hiddenfacts"},
    {"id": "kidnapping", "triggers": ("kidnap", "kidnapped", "secuestro", "secuestrado"),
     "prompt": "a hand reaching through a car window icon grabbing a small figure",
     "category": "hiddenfacts"},
    {"id": "hostage", "triggers": ("hostage", "rehen"),
     "prompt": "a tied rope knot icon around a small chair silhouette",
     "category": "hiddenfacts"},
    {"id": "blackmail", "triggers": ("blackmail", "chantaje"),
     "prompt": "a sealed envelope icon with a red exclamation mark and a photo peeking out",
     "category": "hiddenfacts"},
    {"id": "bribe", "triggers": ("bribe", "soborno"),
     "prompt": "a hand icon slipping cash under a table to another hand",
     "category": "hiddenfacts"},
    {"id": "ransom", "triggers": ("ransom", "rescate"),
     "prompt": "a cut-out letter ransom note icon with mismatched fonts",
     "category": "hiddenfacts"},
    {"id": "war_map", "triggers": ("war map", "mapa de guerra"),
     "prompt": "a vintage war map icon with red arrows and pins marking positions",
     "category": "hiddenfacts"},
    {"id": "battlefield", "triggers": ("battlefield", "campo de batalla"),
     "prompt": "a cracked helmet icon resting on a rifle stuck in the ground",
     "category": "hiddenfacts"},
    {"id": "trench", "triggers": ("trench", "trinchera"),
     "prompt": "a muddy zigzag trench icon with sandbags stacked on the edge",
     "category": "hiddenfacts"},
    {"id": "landmine", "triggers": ("landmine", "mina terrestre"),
     "prompt": "a round buried landmine icon with a small warning triangle above",
     "category": "hiddenfacts"},
    {"id": "grenade", "triggers": ("grenade", "granada"),
     "prompt": "a classic pineapple hand grenade icon with the pin half pulled",
     "category": "hiddenfacts"},
    {"id": "warship", "triggers": ("warship", "buque de guerra"),
     "prompt": "a gray battleship icon with cannons and smoke stacks",
     "category": "hiddenfacts"},
    {"id": "shipwreck", "triggers": ("shipwreck", "wreck", "naufragio"),
     "prompt": "a broken ship hull icon tilted on the ocean floor with bubbles",
     "category": "hiddenfacts"},
    {"id": "jungle_expedition", "triggers": ("jungle", "selva", "expedicion"),
     "prompt": "a machete icon cutting through thick jungle vines",
     "category": "hiddenfacts"},
    {"id": "lost_expedition", "triggers": ("lost expedition", "expedicion perdida", "explorer"),
     "prompt": "a torn vintage map icon with a compass resting on top",
     "category": "hiddenfacts"},
    {"id": "island_hideout", "triggers": ("island", "isla remota", "escondite"),
     "prompt": "a small remote palm tree island icon with a hidden cave entrance",
     "category": "hiddenfacts"},
    {"id": "propaganda_poster", "triggers": ("propaganda",),
     "prompt": "a bold vintage propaganda poster icon with a pointing hand and rays",
     "category": "hiddenfacts"},
    {"id": "compass", "triggers": ("compass", "brujula"),
     "prompt": "a brass compass icon with the needle spinning",
     "category": "hiddenfacts"},
    {"id": "old_photograph", "triggers": ("old photograph", "foto antigua", "fotografia"),
     "prompt": "a sepia-toned photograph icon with a torn corner",
     "category": "hiddenfacts"},
    {"id": "secret_meeting", "triggers": ("secret meeting", "reunion secreta"),
     "prompt": "a small round table icon with shadowy figures leaning in under one lamp",
     "category": "hiddenfacts"},
    {"id": "shredder", "triggers": ("shredded", "shredder", "destructora de papel", "triturar"),
     "prompt": "a paper shredder icon with thin strips of paper coming out",
     "category": "hiddenfacts"},
    {"id": "burned_documents", "triggers": ("burned documents", "documentos quemados", "quemar documentos"),
     "prompt": "a small bonfire icon burning a stack of papers with rising embers",
     "category": "hiddenfacts"},
    {"id": "one_way_mirror", "triggers": ("one way mirror", "espejo espia"),
     "prompt": "a rectangular mirror icon with a shadowy eye watching from behind it",
     "category": "hiddenfacts"},
    {"id": "test_subject", "triggers": ("test subject", "sujeto de prueba"),
     "prompt": "a clipboard icon with a small human silhouette and a syringe beside it",
     "category": "hiddenfacts"},
    {"id": "secret_experiment", "triggers": ("secret experiment", "experimento secreto"),
     "prompt": "a glowing beaker icon bubbling behind a restricted-access door",
     "category": "hiddenfacts"},
    {"id": "secret_scientist", "triggers": ("scientist", "cientifico", "researcher", "investigador"),
     "prompt": "a lab coat and glasses icon beside a glowing test tube",
     "category": "hiddenfacts"},
    {"id": "courtroom_gavel", "triggers": ("gavel", "martillo de juez"),
     "prompt": "a wooden judge gavel icon mid-strike with motion lines",
     "category": "hiddenfacts"},
    {"id": "secret_diary", "triggers": ("secret diary", "diario secreto", "journal"),
     "prompt": "a small locked leather diary icon with a tiny brass key",
     "category": "hiddenfacts"},
    {"id": "wanted_poster", "triggers": ("wanted poster", "se busca"),
     "prompt": "a vintage WANTED poster icon with a torn edge and bold letters",
     "category": "hiddenfacts"},
    {"id": "fingerprint", "triggers": ("fingerprint", "huella dactilar"),
     "prompt": "a glowing fingerprint icon highlighted under a magnifying glass",
     "category": "hiddenfacts"},
    {"id": "blueprint_plans", "triggers": ("blueprint", "planos secretos"),
     "prompt": "a rolled blue blueprint icon with white technical line drawings",
     "category": "hiddenfacts"},
    {"id": "code_name", "triggers": ("code name", "nombre en clave", "alias"),
     "prompt": "a folder tab icon with a redacted black bar over a name",
     "category": "hiddenfacts"},
    {"id": "back_alley_meeting", "triggers": ("back alley", "callejon oscuro"),
     "prompt": "a narrow shadowy alley icon with a single flickering street lamp",
     "category": "hiddenfacts"},
    {"id": "border_crossing", "triggers": ("border", "frontera", "cruzar la frontera"),
     "prompt": "a striped border checkpoint gate icon with a small guard booth",
     "category": "hiddenfacts"},
    {"id": "refugee_flight", "triggers": ("refugee", "refugiado", "huida"),
     "prompt": "a small suitcase icon beside a silhouette walking away at dusk",
     "category": "hiddenfacts"},
    {"id": "spy_ring", "triggers": ("spy ring", "red de espias"),
     "prompt": "several shadowy figure icons connected by dotted lines like a network",
     "category": "hiddenfacts"},
    {"id": "cold_war_standoff", "triggers": ("cold war", "guerra fria"),
     "prompt": "two glowing red and blue chess king pieces facing off icon",
     "category": "hiddenfacts"},
    {"id": "declassified", "triggers": ("declassified", "desclasificado"),
     "prompt": "a red DECLASSIFIED stamp icon over a faded document",
     "category": "hiddenfacts"},
    {"id": "final_reveal", "triggers": ("revealed", "finalmente revelado", "reveal"),
     "prompt": "a curtain icon pulling back to reveal a glowing spotlight",
     "category": "hiddenfacts"},
]


# --------------------------------------------------------------- matching

def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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

_MAX_TRIGGER_WORDS = 3  # el trigger mas largo del catalogo ("cruzar la frontera") tiene 3 palabras


def find_keyword_cues(words: list[tuple[float, float, str]], min_gap: float = 1.8,
                       max_cues: int = 40) -> list[tuple[float, str, str]]:
    """Escanea las palabras REALMENTE narradas (con timestamp real de TTS, no
    el texto de search_terms) y devuelve (tiempo, sticker_id, frase) por cada
    keyword detectada -- 1 sticker por CADA vez que se dice, no 1 por escena.
    Varios triggers del catalogo son frases de 2-3 palabras ("war map",
    "secret police", "one more game"), y `words` viene tokenizado palabra por
    palabra -- por eso en cada posicion se prueba la ventana mas larga posible
    (3, 2, 1 palabras) antes de avanzar, en vez de comparar solo la palabra
    suelta (bug real: una frase de 2+ palabras nunca hubiera matcheado).
    min_gap evita 2 stickers pegados si dos triggers caen muy cerca."""
    manifest = load_manifest()
    cues: list[tuple[float, str, str]] = []
    last_t = -min_gap
    n = len(words)
    i = 0
    while i < n and len(cues) < max_cues:
        sid = None
        span = 1
        for L in range(min(_MAX_TRIGGER_WORDS, n - i), 0, -1):
            phrase = " ".join(w[2] for w in words[i:i + L])
            candidate = match_sticker(phrase)
            if candidate and candidate in manifest:
                sid, span = candidate, L
                break
        if sid:
            start = words[i][0]
            if start - last_t >= min_gap:
                cues.append((start, sid, " ".join(w[2] for w in words[i:i + span])))
                last_t = start
            i += span
        else:
            i += 1
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

def _generate_icon_image_gemini(prompt: str, api_key: str, attempts: int = 3) -> bytes | None:
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


def _generate_icon_image_seedream(prompt: str, api_key: str, attempts: int = 3) -> bytes | None:
    """Alternativa via Seedream (ByteDance) por PiAPI -- mismo patron que
    _seedream_generate_image() en pipeline.py. Bug real (22 jul 2026): la
    cuota gratuita de GEMINI_API_KEY para imagenes se agoto (0/200 stickers
    generados, todo 429) mientras PIAPI_API_KEY seguia con cupo -- esta
    funcion es el fallback que usa esa cuota en vez de quedar bloqueado."""
    full_prompt = prompt + STICKER_STYLE_SUFFIX
    for attempt in range(attempts):
        try:
            r = requests.post(
                "https://api.piapi.ai/api/v1/task",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                json={
                    "model": "seedream",
                    "task_type": "seedream-5-lite",
                    "input": {"prompt": full_prompt, "aspect_ratio": "1:1", "output_format": "png"},
                },
                timeout=60,
            )
            r.raise_for_status()
            task_id = r.json()["data"]["task_id"]
            for _ in range(60):
                time.sleep(2)
                poll = requests.get(f"https://api.piapi.ai/api/v1/task/{task_id}",
                                     headers={"X-API-Key": api_key}, timeout=30)
                poll.raise_for_status()
                task = poll.json()["data"]
                status = task.get("status", "").lower()
                if status in ("completed", "success"):
                    output = task.get("output", {})
                    img_url = (output.get("image_urls") or output.get("images") or [None])[0]
                    if not img_url:
                        raise RuntimeError("tarea completa sin imagen de salida")
                    img_resp = requests.get(img_url, timeout=60)
                    img_resp.raise_for_status()
                    return img_resp.content
                if status in ("failed", "error"):
                    raise RuntimeError(task.get("error", "tarea fallo sin detalle"))
            raise RuntimeError("timeout esperando la tarea de Seedream")
        except Exception as e:
            if attempt < attempts - 1:
                print(f"  intento {attempt + 1} fallo, reintento en 5s: {e}")
                time.sleep(5)
            else:
                print(f"  FALLO definitivo: {e}")
    return None


def _generate_icon_image(prompt: str, gemini_key: str, piapi_key: str = "", attempts: int = 3) -> bytes | None:
    """Prueba Seedream/PiAPI primero si hay key (cupo disponible el 22 jul
    2026 mientras Gemini estaba agotado), cae a Gemini/Nano Banana si no."""
    if piapi_key:
        result = _generate_icon_image_seedream(prompt, piapi_key, attempts=attempts)
        if result is not None:
            return result
        print("  Seedream sin resultado, probando Gemini/Nano Banana...")
    return _generate_icon_image_gemini(prompt, gemini_key, attempts=attempts)


def _remove_background(raw_bytes: bytes) -> bytes:
    from rembg import remove
    return remove(raw_bytes)


def generate_library(force: bool = False, only: list[str] | None = None,
                      delay: float = 4.0) -> None:
    STICKERS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    api_key = os.getenv("GEMINI_API_KEY", "")
    piapi_key = os.getenv("PIAPI_API_KEY", "")
    if not api_key and not piapi_key:
        print("ERROR: falta GEMINI_API_KEY o PIAPI_API_KEY en .env "
              "(Gemini gratis en https://aistudio.google.com/apikey)")
        return
    if piapi_key:
        print("Usando Seedream/PiAPI primero (cupo disponible), Gemini como respaldo.")

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
        raw = _generate_icon_image(concept["prompt"], api_key, piapi_key)
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
