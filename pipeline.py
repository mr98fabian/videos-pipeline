"""Faceless Shorts pipeline: tema -> video vertical listo para subir.

Etapas:
  1. SCRIPT    Claude API (guion + search terms + titulo + descripcion)
  2. AUDIO     edge-tts (mp3 + timestamps por palabra, gratis)
  3. MEDIA     Pexels API (clips verticales) o gradientes generados (fallback)
  4. SUBS      ASS word-level estilo Hormozi, quemados en el video
  5. ASSEMBLY  FFmpeg puro: 1080x1920 @ 30fps, CRF 21, AAC 192k

Uso:
  py pipeline.py "the 50/30/20 budget rule"
  py pipeline.py --script-file sample_script.json      (sin Claude API)
  py pipeline.py "topic" --no-pexels                   (fondos de gradiente)
  py pipeline.py --ideas                               (genera 5 temas nuevos)

Claves (archivo .env o variables de entorno):
  ANTHROPIC_API_KEY   requerida salvo que uses --script-file
  PEXELS_API_KEY      opcional; sin ella se usan fondos de gradiente
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path

import requests

import sticker_library

# Windows con tarea programada suele heredar stdout en cp1252; un titulo con
# emoji o caracter fuera de ese charset lanza UnicodeEncodeError y tumba la
# corrida DESPUES de haber gastado creditos de TTS/imagenes/musica (visto
# repetidas veces esta sesion). Forzar UTF-8 lo elimina de raiz.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).parent
OUTPUT_ROOT = ROOT / "output"
LOG_DIR = ROOT / "logs"
USED_TOPICS_FILE = ROOT / "used_topics.json"

MODEL = "claude-opus-4-8"
DEFAULT_VOICE = "en-US-AndrewNeural"
# Estilo visual FIJO del canal (27 jul 2026). Bug real: SCRIPT_SCHEMA nunca
# tuvo un campo "style", asi que data.get("style") dependia de que Claude lo
# inventara por su cuenta -- salio vacio en un video real y las imagenes
# perdieron el sepia Nickelodeon. Segun CLAUDE.md esto NUNCA debe variar por
# video, asi que ahora es una constante de codigo, no algo que el modelo decide.
HIDDENFACTS_STYLE = (
    "1990s Nickelodeon rubber-hose cartoon style, exaggerated comic-book "
    "expressions with big unsettling eyes, thick wobbly hand-drawn black "
    "outlines, snappy low-frame animation feel. Color palette: sepia, dusty "
    "burnt yellow, aged parchment, dark brown shadows instead of pure black. "
    "Heavy vintage film grain and scratched-film texture overlaid, retro "
    "documentary aesthetic, slightly distorted, high contrast, hand-drawn "
    "sketch look. No bright saturated colors. Only human characters, never "
    "humanoid animals."
)
# ============================================================================
# PLACAS SEPARADAS (28 jul 2026) — personaje y fondo se generan como DOS
# imagenes distintas por escena, no una sola.
#
# Por que: todo lo que el motor hace despues consiste en SEPARAR cosas que la
# imagen trae juntas, y cada solape en la imagen es una separacion que ya no se
# puede hacer. Tres fallos medidos que salen del mismo sitio:
#   - 3 de 10 escenas del ultimo render dieron "recorte fallo" y cayeron a foto
#     clavada: BiRefNet no separa al sujeto de un fondo cargado.
#   - cutout_parts() necesita figuras que no se toquen para partirlas.
#   - el esqueleto (AnimatedDrawings) no encuentra la articulacion si el brazo
#     esta pegado al torso; el miembro se anima como parte del tronco.
# Contra fondo blanco plano y pose en A, los tres funcionan.
#
# Pose en A y no en T: la T se lee como maniqui si un fotograma la muestra sin
# animar, y el retargeter maneja las dos igual de bien.
# ============================================================================
CHARACTER_PLATE = (
    "Full body from head to feet, entire figure inside the frame with margin, "
    "nothing cropped. Relaxed A-pose: arms hanging away from the torso at about "
    "45 degrees, hands clearly separated from the body, legs apart in a wide "
    "stance with a clear visible gap of background between the two feet, feet "
    "never touching each other. "
    "No limb touching or overlapping another limb or the torso. Facing the "
    "viewer, centered, standing upright. Plain flat pure white background, "
    "no floor, no shadow, no ground line, no props, no scenery, no other "
    "characters. One single character only."
)
BACKGROUND_PLATE = (
    "Empty scene with NO people, NO characters, NO figures anywhere. "
    "Environment only."
)
# El estilo del canal pide grano de pelicula, textura rayada y sombras: sobre
# la placa eso es basura que hay que recortar despues. El motor YA pone el
# grano, el papel y la sombra troquelada (DIE_CUT) por encima.
# Medido en la placa del general (28 jul 2026): el modelo pinto una sombra
# casi negra (43,11,9) entre los faldones. No es un fallo del recorte -- el
# hueco entre las piernas venia relleno de negro en el PNG original, y ningun
# recorte por color lo puede quitar sin comerse las botas.
PLATE_STYLE = (
    "1990s Nickelodeon rubber-hose cartoon style, exaggerated comic-book "
    "expressions with big unsettling eyes, thick wobbly hand-drawn black "
    "outlines. Color palette: sepia, dusty burnt yellow, aged parchment, dark "
    "brown. CLEAN FLAT LINE ART: flat solid fills, no film grain, no scratches, "
    "no paper texture, no vignette, no gradient, no cast shadow, no shadow "
    "under the feet, no ground line, no floor. The space between the arms and "
    "the body and between the legs must be pure background color, never filled "
    "with shadow or dark shapes. Only human characters, never humanoid animals."
)
# sustantivos de persona con los que se deriva la placa de personaje cuando el
# guion es escrito a mano y no trae 'character_terms'
_PERSON_RE = re.compile(
    r"\b(?:a|an|one|two|three|the|several|)\s*(?:[a-z-]+\s+){0,3}?"
    r"(man|men|woman|women|person|people|soldier|soldiers|officer|officers|"
    r"general|generals|detective|detectives|guard|guards|worker|workers|"
    r"handyman|policeman|policemen|prisoner|prisoners|spy|spies|king|queen|"
    r"boy|girl|scientist|sailor|sailors|tourist|tourists|crowd)\b",
    re.I,
)


# notas de encuadre que el guion arrastra y que no pintan nada en ninguna placa
_CAMERA_RE = re.compile(
    r",\s*(?:full figures?(?: apart)?|half figures?|close ?ups?|standing apart"
    r"|full figures? apart)\b.*$", re.I)
# el participio (-ing) parte la frase: delante queda QUIEN, detras DONDE
_GERUND_RE = re.compile(
    # el (?:\w+\s+)? admite un adverbio entre el gerundio y la preposicion:
    # "sitting ALONE in a plain quiet room" no matcheaba y la escena acababa
    # con un prompt contradictorio (la persona + "escena vacia sin gente"),
    # que el modelo resuelve dibujando a la persona igual (28 jul 2026)
    r"\b(\w+ing)\s+(?:\w+\s+)?(?:inside|into|in front of|at|on|in|under|near|behind|"
    r"outside|across|through|over|beside|down|along)\s+(.+)$", re.I)


def _plate_terms(term: str, char_term: str | None) -> tuple[str, str | None]:
    """(prompt de fondo, prompt de personaje o None) para una escena.

    Con `character_terms` del guion se respeta tal cual: es lo que Claude
    escribio ya separado. Sin el (guiones a mano) se parte el search_term por
    el participio -- delante esta QUIEN y detras DONDE:
      "a man in workman overalls hiding inside a dark storage closet"
        -> personaje "a man in workman overalls" / fondo "a dark storage closet"
    Partir mal es peor que no partir: un fondo que sigue pidiendo gente mas un
    "NO people" pegado detras es un prompt que se contradice, y el modelo hace
    lo que le da la gana.
    """
    clean = _CAMERA_RE.sub("", (term or "").strip()).strip(" ,")
    has_person = bool(_PERSON_RE.search(clean))
    if not has_person and not char_term:
        return term, None            # escena sin personaje: una sola placa

    place = None
    g = _GERUND_RE.search(clean)
    if g:
        cand = g.group(2).split(" with ")[0].strip(" ,.")
        # si el "sitio" sigue nombrando gente ("across from two policemen"),
        # el corte esta mal: un fondo que pide personas y a la vez dice
        # "NO people" es un prompt que se contradice
        if cand and not _PERSON_RE.search(cand):
            place = cand

    if char_term:
        if place:
            return f"{place}, {BACKGROUND_PLATE}", char_term
        # NO se pudo aislar el sitio. Pegar "escena vacia sin gente" detras de
        # un termino que sigue nombrando a una persona es un prompt que se
        # contradice, y el modelo lo resuelve dibujando a la persona igual: el
        # fondo acababa con una copia del personaje que se veia como una sombra
        # gigante detras de la tarjeta. Mejor una sola imagen compuesta.
        if has_person:
            return term, None
        return f"{clean}, {BACKGROUND_PLATE}", char_term
    if not place:
        # hay persona pero no se puede separar el sitio -> no se parte: mejor
        # una placa correcta que dos mal cortadas
        return term, None
    return f"{place}, {BACKGROUND_PLATE}", clean[:g.start()].strip(" ,")


DEFAULT_RATE = "+8%"
DEFAULT_CLIPS = 10  # ~4-5s/escena en un Short de 45s. Antes 5 (~9s/escena) -- muy
                    # por debajo del benchmark de retencion de 2-4s por corte
                    # (ver RETENCION_PSICOLOGIA.md secc. 4). Subir aun mas si el
                    # guion tiene muchos beats cortos.
WIDTH, HEIGHT, FPS = 1080, 1920, 30

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "script": {
            "type": "string",
            "description": "Voiceover text, word-for-word, 355-375 words, no markdown. "
                            "*** HARD RULE: NOTHING EXPLANATORY AFTER THE PAYOFF *** The payoff is "
                            "the sentence that delivers what the hook promised (the twist, the "
                            "result, the reveal). The moment it lands, the story is OVER for the "
                            "viewer -- any further background, dates, aftermath or 'and that is why "
                            "...' sentence is dead weight and they leave right there, taking the "
                            "last seconds of retention with them. After the payoff you may write "
                            "ONLY: (a) at most one short dry acid remark, if it hits HARDER than the "
                            "payoff itself, (b) the share trigger, (c) the closing question. Never a "
                            "new fact, never a recap, never extra context. If a detail matters, it "
                            "belongs BEFORE the payoff, not after it. "
                            "*** HARD RULE: THE SCRIPT MUST LOOP *** The last sentence has to close using the SAME KEY WORDS as the hook, so that when the Short restarts the viewer does not perceive a cut and watches it again. Measured on this channel (26 jul 2026): the only video with a real loop holds a 3.76 -> 2.89 audience ratio (watched ~3 times through, -23% across the whole video), while videos closing with a summary sentence ('and so...', 'that is how...') fall to 0.95 and 0.08. A summary tells the viewer it is over; a loop hides the seam. Example that works: hook 'almost nobody today remembers why' -> close 'then quietly vanished from the pages of history'. NEVER close with a recap or a moral. "
                            "*** PLANTILLA UNICA DEL CANAL: replicar Black Tom *** Es el unico video con re-watch real (3,76 -> 2,89) y de el se copian TRES cosas, no solo el loop: (1) el ancla es un ICONO FAMOSO que el espectador reconoce al instante y puede ver hoy (la Estatua de la Libertad), no un personaje historico que hay que presentar; (2) la consecuencia SIGUE VISIBLE HOY -- la antorcha lleva cerrada desde entonces -- asi que el espectador puede comprobarlo el mismo ('ever since', 'to this day', 'still closed'); (3) el loop lexico y visual. Si el tema no tiene un icono reconocible con una huella visible hoy, el guion no alcanza este patron: buscar otro angulo del mismo hecho hasta encontrarlo.",
        },
        "search_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "8-12 concrete, visual queries (objects/scenes, not concepts). "
                            "More, shorter scenes beat fewer long ones -- retention research shows "
                            "high-performing Shorts cut every 2-4 seconds, not every 8-9. "
                            "CUT-OUT FRIENDLY (the engine isolates the subject as a die-cut sticker): "
                            "each MIDDLE term should show ONE clear subject as a FULL or HALF figure "
                            "with a clean silhouette, doing one readable action, on an uncluttered "
                            "background -- e.g. 'a soldier crouching in a trench, full figure' NOT "
                            "'a soldier's face in extreme close-up'. Extreme face close-ups isolate "
                            "as ugly floating heads. The ONLY exception is the FIRST (and its echo, "
                            "the last) term: a single intense face close-up there is encouraged for "
                            "the thumbnail scroll-stop -- the engine renders those as a clean taped "
                            "photo, not a cut-out. "
                            "*** THE LAST TERM MUST CHAIN INTO THE FIRST *** Not merely resemble it: the closing image has to be a frame the first image could cut back to without a visible seam (same place, same light, same framing, later moment). That visual loop is half of the re-watch effect measured on this channel. Example: opens on a night explosion in the harbor, closes on the same harbor still smoldering. "
                            "MULTI-SUBJECT: in 3-4 of the middle terms, ask for TWO or THREE figures "
                            "(or a figure plus a key object) STANDING CLEARLY APART, not touching and "
                            "not overlapping -- e.g. 'two officers standing apart facing each other "
                            "across an empty room, full figures'. The engine cuts each one out "
                            "separately and makes them ACT on each other (one shoves, the other "
                            "topples), which only works if they do not overlap in the image.",
        },
        "character_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "PARALLEL to search_terms, exactly the same length. For a scene "
                            "whose subject is a PERSON, put the character alone here: who they "
                            "are and what they wear, nothing else -- 'a museum handyman in "
                            "workman overalls', 'an elderly Prussian general in dress uniform'. "
                            "No place, no action, no props, no other characters: the engine adds "
                            "the pose and the plain background, and the ACTION comes from the "
                            "skeleton animation, not from the drawing. For a scene with no person "
                            "(an empty room, a document, a railway track) put an EMPTY STRING. "
                            "The character is drawn on its own plate and composited over the "
                            "background plate, so anything that touches the figure in the image "
                            "can never be separated again.",
        },
        "title": {"type": "string", "description": "YouTube Shorts title, <90 chars, curiosity-driven"},
        "description": {"type": "string", "description": "YouTube description with 3-5 hashtags at the end"},
        "music_mood": {
            "type": "string",
            "description": "Short text prompt (English) describing instrumental background music matching "
                            "this script's tone, for an AI music generator. E.g. 'upbeat quirky ukulele pop, "
                            "playful and light' or 'tense minimal synth, building suspense'. No vocals.",
        },
        "hook_card": {
            "type": "string",
            "description": "A ~6-10 word on-screen premise card shown for the first 2.2s (high-contrast "
                            "text over the video, separate from narration/subtitles). States the video's "
                            "premise as a curiosity gap -- withholds the resolution the script itself "
                            "reveals. E.g. 'A king survived a gun built to kill him.' Never restates the "
                            "hook sentence word-for-word; it should read like a caption someone would pause "
                            "on, not a subtitle.",
        },
        "hook_punch": {
            "type": "string",
            "description": "EXACTLY 3-5 words, no more. The visual hook: rendered huge and bold at the "
                            "top of the card, above hook_card. Kallaway (reviewed 30 jul 2026) argues the "
                            "visual hook is far more powerful than the spoken one because people read "
                            "faster than they hear -- a full-sentence card is read too slowly to land in "
                            "the window that decides the swipe. This is the 3-5 words the viewer absorbs "
                            "in one glance, BEFORE reading anything else. Make it concrete and loaded, not "
                            "a topic label: 'HE INVOICED HIS SISTER' not 'FAMILY DRAMA'; 'THE TORCH NEVER "
                            "REOPENED' not 'STATUE OF LIBERTY'. No final period. It may be uppercase.",
        },
    },
    "required": ["script", "search_terms", "character_terms", "title", "description",
                 "music_mood", "hook_card", "hook_punch"],
    "additionalProperties": False,
}

# NOTA (28 jul 2026): el canal de finanzas personales que este prompt describia
# esta en pausa -- se retoma en el futuro, no ahora. Guardado abajo en
# FINANCE_SCRIPT_PROMPT_CONTEXT para no perder el trabajo. Foco actual: SOLO
# HiddenFacts (historia oculta/engaños/espionaje).
FINANCE_SCRIPT_PROMPT_CONTEXT = """\
Context: personal-finance channel for a US/English-speaking audience.
Voice: second person throughout ("you", "your paycheck", "your bank account") — never
"we" or "I". This is proven to retain viewers better than third-person narration.
Angle templates:
- "Why can't you ___?" — explains a universal money frustration through a real rule or bias
- "You never noticed that ___" — reveals a hidden mechanic in something the viewer does weekly
- "The ___ effect" — names a real, citable phenomenon and mirrors it onto the viewer's habits
- "What if your ___ is ___?" — a provocative reframe grounded in a concrete number or rule
"""

SCRIPT_PROMPT = """\
Create a viral YouTube Short script about: {topic}

Context: HiddenFacts channel — hidden history, hoaxes, and espionage for a US/English-
speaking audience. Assume 50% of viewers watch on mute (subtitles are burned in). Target
90 seconds of spoken content. MEDIDO 31 jul 2026 sobre 4 videos reales (no estimado):
edge-tts a +8% con --trim-silence entrega 4,07 palabras/segundo, asi que 355-375 palabras
= ~90s finales. Sin --trim-silence el mismo guion sale ~11% mas largo. Los 175s salen de
medir los 50 videos mas recientes de Reddit Gossipz: TODOS entre 163s y 179s, mediana 176s.

Role: you are a scriptwriter whose Shorts consistently retain viewers past the 3-second mark.

Voice: third person, narrating real events — never "we" or "I", and never second-person
finance-style address ("your paycheck"). The viewer is watching history unfold, not being
lectured about their own life.

APPROVED EXCEPTION — IMMERSIVE ANGLE (28 jul 2026). If the topic has ONE real, named,
verifiable person whose situation can be handed to the viewer without inventing anything,
write the WHOLE script in second person and put the viewer inside it: "you eat first,
every day, and you do not know if today is the day". The point is that the stakes land in
the viewer's own body instead of a stranger's — a third-person witness feels nothing.
This does NOT replace the Black Tom template, it combines with it: still a famous anchor,
still a consequence visible today, still the loop.
Use it ONLY when the person is real and documented (Hitler's food taster, yes; "a soldier",
no). If the event has no single clear protagonist, use standard third person. Never invent
a person or a sensation to force this angle.

Rhythm (follow this cadence, it is not optional): short sentence. Short sentence. One
longer sentence that adds depth or nuance. Short sentence. A question, roughly every
4-6 sentences, to keep the viewer mentally engaged.

Tone — THE VOICE IS A CYNICAL ARCHIVIST: a jaded investigator who has read too many
files and narrates history with dry contempt, like a friend telling you the most insane
true story they found on Wikipedia at 4 a.m. Deadpan, acidic, never impressed. This voice
is the channel's brand; funny/absurd gets SHARED, which is what grows the channel:
- ACIDIC SATIRE THAT PUNCHES UP. Aim the acid at POWER — dictators' egos, government
  cover-ups, corporate greed, propaganda, pompous officialdom. Black humor at the expense
  of the powerful and the absurd is fair game and it is what gets shared. NEVER punch down:
  victims of the events are always protected, never the joke.
- The humor comes from the ABSURDITY of the TRUE fact, delivered deadpan — never jokes,
  puns, or breaking the documentary voice. A short, dry punch-line tag at the end of a
  sentence is the tool ("...in exchange for soda.", "Marketing."). The narration is TTS
  and flat, so the wit must live in the WORDING (irony, understatement, juxtaposition).
- When a pompous official euphemism appears AND it fits naturally (don't force it), puncture
  it with the blunt translation ("'strategic redeployment' — they ran."). Occasional, not
  every video.
- SCALE IT INVERSELY TO GRAVITY. Light topics (odd deals, naming quirks, con artists,
  bureaucratic absurdity, pointless traditions) → full acid. Grave topics (genocide,
  executions, massacres, war dead) → NO jokes; the acid, if any, points ONLY at the
  perpetrator, never the victims, and mostly you pull back to bitter irony and restraint.
  The `music_mood` you pick signals which end you are on.

Instructions:
1. Open with a hook in the first sentence: a curiosity gap, a bold claim, or a surprising
   number. The first 1-2 seconds decide whether the viewer swipes away (this is the single
   biggest drop-off point in short-form video) — the opening must never be a slow warm-up.
2. Deliver value with the "slippery slide": second-best point first, best point early.
3. Add 1-2 mini re-hooks ("but here's the part nobody mentions...", "and then it got worse")
   roughly every 15 seconds — this exploits the Zeigarnik effect (the brain fixates on
   unresolved information) to prevent mid-video drop-off, not just at the very start.
4. Close with a line that repeats the EXACT key word or phrase from the opening hook
   (not just the same theme — the literal word), reframed by what the viewer now knows.
   Example: hook "Hitler's own men didn't recognize him" -> closer "...and by the end,
   even Hitler's own men didn't recognize HIM." The literal repetition is what makes the
   final-to-first splice read as a real loop instead of "a new video starting" — this
   drives rewatches (>100% watched), the strongest retention signal Shorts rewards.
5. NEVER speak a call-to-action ("subscribe", "follow for more", "let me know below") inside
   the script. Announcing the video is ending causes a hard drop-off right at that line
   (viewers mentally close out before the real ending) — the CTA belongs ONLY in the
   description, never in spoken audio.
6. Write the script as a sequence of short, punchy visual beats (one clear image/moment
   per sentence or two) rather than long flowing paragraphs — each beat should map to a
   distinct scene change every 2-4 seconds of spoken audio, matching how high-retention
   Shorts are cut. Avoid any beat that would need more than ~4 seconds of the same visual.
   The FIRST search_term must literally depict the subject of the first spoken sentence —
   any mismatch between the first words heard and the first image shown reads as
   incongruence before the viewer consciously processes it, and the thumb is already
   swiping by then.
7. search_terms MUST have exactly one entry per sentence of the script, in order, same
   count as the number of sentences (count periods/!/?). This is a hard rule: the video
   assembly cuts to a new image at each sentence boundary, so a mismatched count forces a
   cut mid-sentence, which reads as the image and the voice telling two different things
   at once. If you want a bookend/loop visual (last image echoes the first), repeat the
   first search_term as an EXTRA sentence's worth at the end and add one more short closing
   sentence to the script to match it -- never add an extra search_term without an extra
   sentence to anchor it.
8. hook_card: write it as a separate curiosity-gap caption, not a copy of the first spoken
   sentence. It should promise the shape of the story without giving the twist away, so a
   viewer who only reads the card (sound off, 2 seconds) still feels compelled to keep
   watching.
9. *** OPEN WITH A FLAT UNRESOLVED FACT, NOT A QUESTION *** (rewritten 1 ago 2026, from
   the oral-narrative masters: Garcia Marquez, Chekhov, "Cronica de una muerte anunciada".)
   The script, the title and the hook_card must all open with a DECLARATIVE statement of
   something that cannot be true, or should not be, stated in the flattest possible tone --
   and they must NOT explain it. Do not open with "Why".
   The old rule locked the first word to "Why". It is retired because a question ASKS the
   viewer to become curious; a contradiction stated as plain fact leaves them uncomfortable
   until it resolves, which is stronger and does not sound like a quiz channel. Garcia
   Marquez never asks a question. He states two things that cannot both be true and lets
   the reader do the asking.
   Required shape -- three parts, all inside the first sentence:
     (a) the impossible fact, said flatly, no adjectives, no build-up;
     (b) ONE concrete verifiable detail carried inside it (a number, a date, a proper noun,
         an object). This is the "prime": curiosity is an information gap and a gap needs
         something on BOTH sides. Without a concrete detail there is nothing to feel
         deprived of yet, and the line reads as vague mood instead of a gap;
     (c) a SECOND TIME folded in -- the future consequence, or how long it went on, or when
         it was found out. The opening of "Cien anos de soledad" holds three moments in one
         sentence and two of them are unexplained; that is the whole engine.
   Weak (old style): "Why did my grandmother write her recipes wrong?"
   Weak (self-resolving): "My grandmother wrote every recipe wrong because she was losing
   her memory." <- the subordinate clause answers it in second 3 and the video is over.
   Strong: "My grandmother wrote every recipe wrong on purpose, and we did not find out
   until we spread all thirty-one cards on her kitchen table after the funeral."
   *** NEVER RESOLVE THE HOOK IN THE HOOK. *** Any "because...", "since...", "so that..."
   attached to the opening fact kills the video. If the first sentence contains its own
   answer, the viewer owes you nothing from second 3 on -- which is exactly where measured
   drop-off happens. Cut the clause and let it hang.
   *** ANNOUNCING THE ENDING IS ALLOWED AND OFTEN BETTER. *** "Cronica de una muerte
   anunciada" tells you in line one who dies. Curiosity about HOW survives 90 seconds;
   curiosity about WHAT is spent in ten. Giving away the outcome and making the mechanism
   the question is a legitimate, stronger opening -- not a spoiler.
9b. *** THE 3-BEAT HOOK: the first 3 sentences must turn the viewer around ***
   (Kallaway hook framework, 428k-sub channel whose own numbers verify it, reviewed
   30 jul 2026.) The mental model: the viewer is driving past at 70mph. Sentence 1 makes
   them slow down, sentence 2 makes them stop, sentence 3 makes them turn around. Our old
   rule only handled sentence 1 -- the "Why" question -- and then went straight into
   chronological setup, which loses the turn-around. Structure the opening as exactly three
   beats, in this order:
   (a) CONTEXT LEAN -- the "Why" question itself (rule 9). It states the topic plainly so
       the right viewer self-selects IN, and carries the concrete prime so they lean in.
       Do NOT try to be mysterious about the subject; be mysterious about the OUTCOME.
   (b) SCROLL-STOP INTERJECTION -- ONE short sentence that must open with a contrast word:
       "But", "Except", "Yet", "Although". Its only job is to stun: it contradicts what the
       viewer just assumed from (a). Example shape: "But the will was not the part that
       destroyed her." This is a setup line, not the payoff.
   (c) CONTRARIAN SNAPBACK -- one sentence that sends the story in the OPPOSITE direction
       from the lean in (a), still on topic. The bigger the reversal, the stronger the hook:
       "Because the person who lost everything that day was the one holding the envelope."
   Only AFTER these three beats does the chronological setup begin.
   *** STACCATO OPENING *** Beats (b) and (c) must be SHORT -- under 12 words each. Short
   sentences force maximum clarity and raise value-per-word exactly where attention is most
   expensive. Sentences may grow to medium and long only after the third beat.
   *** SPEED TO VALUE *** Do not save every concrete detail for the ending. Land one real,
   specific piece of the story (a number, a dated fact, a quoted line) within the first ~4
   seconds of narration -- inside or immediately after the 3-beat hook. Burying all payoff
   at the end assumes the viewer stays; frontloading earns the stay. This does NOT weaken
   the loop rule: the FINAL twist still stays hidden, only the first hit of value moves up.
9e. *** NO TODO ES VENGANZA: EL REGISTRO CALIDO GANA MAS *** (medido 31 jul 2026.)
   En el top 10 de Reddit Gossipz, los tres videos mas vistos NO son de venganza,
   son de REVERSION EMOCIONAL -- alguien injustamente no reconocido que por fin
   recibe reconocimiento:
     1.66M "I called my stepdad by his first name for 17 years. Last Tuesday I called him dad..."
     974k  "I was born blind. I got my vision back the day I married him."
     919k  "I told my father that my stepdad is more of a man than he will ever be."
   El pago no es un castigo al villano, es un reconocimiento que llega tarde y
   revienta a alguien que aguanto en silencio durante anos. Es MAS compartible que
   la venganza porque el espectador lo manda a alguien que quiere, no para burlarse.
   Regla practica: alterna registros. Si los ultimos dos guiones fueron de traicion
   y castigo, el siguiente debe ser de reconocimiento tardio. Un canal que solo hace
   venganza se siente de una sola nota y satura rapido.
   Detalle de ejecucion que hace creible el registro calido: DETALLE CONCRETO Y
   ESPECIFICO, no adjetivos. Ellos no dicen "era un buen padrastro", dicen "trajo
   una cana de pescar", "engancho su propia camisa", "encontre las entradas en el
   cajon de su caja de herramientas, mismo partido, dos asientos, sin escanear".
9d. *** THE TITLE IS THE FIRST LINE OF THE SCRIPT, VERBATIM *** (medido 31 jul 2026
   sobre los 50 videos mas recientes de Reddit Gossipz, el lider del formato.)
   El titulo NO es una pregunta separada del guion: es literalmente la primera
   frase hablada, copiada tal cual, cortada a media idea con "...". El espectador
   lee el titulo, empieza el audio, y la voz dice exactamente lo que acaba de leer
   -- cero friccion entre ambos.
   Patron medido en su top 10: 7/10 arrancan en PRIMERA PERSONA ("I..." / "My..."),
   2/10 abren con una CITA TEXTUAL de dialogo, y CERO empiezan con "Why".
   Ejemplos reales suyos (1,6M y 1,6M de vistas):
     "I called my stepdad by his first name for 17 years. Last Tuesday I called him dad..."
     'During dinner, my mom slid a ring box across the table and said, "Your uncle picked it himself."'
   *** ESTO ANULA la parte de la regla 9 que obligaba al TITULO a empezar con "Why" ***
   para el canal de historias. La regla 9 la pidio el usuario el 30 jul; la evidencia
   del 31 jul muestra que el lider del formato hace lo contrario y el titulo es su
   palanca principal. La curiosidad se genera TRUNCANDO la frase, no preguntando.
   El guion hablado puede seguir cualquiera de las dos formas -- lo que importa es
   que titulo y primera linea sean el mismo texto.
9c. *** THE BODY OF THE SCRIPT, NOT JUST THE HOOK *** (Kallaway storytelling +
   Trey Parker/Matt Stone, reviewed 31 jul 2026.) Rule 9b fixes the first three
   sentences; these three fix everything after them.
   (a) BUT / THEREFORE, NEVER "AND THEN". Between any two beats the word that fits
       must be "but" or "therefore" -- never "and then". "And then" piles detail on
       detail and the viewer drifts; "but/therefore" opens a conflict that has to be
       closed. Aim for the MAJORITY of sentences after the hook to chain with
       but / so / because / therefore / yet. Do not force it to 100% -- that reads
       robotic -- but "I did this. I did that. Then this happened." is the failure
       mode to avoid.
   (b) VARY SENTENCE LENGTH ON PURPOSE. Alternate short, medium and long sentences.
       A page where every sentence is the same length reads as monotonous even when
       the content is good (Gary Provost). Note: our own channel data does NOT yet
       confirm this one -- the best-retaining video so far has the LOWEST variance --
       so treat it as a soft preference, not a hard rule.
   (c) HEAD-FAKE BEFORE THE PAYOFF. Peak dopamine lands just BEFORE the answer, not
       at the answer. So: give enough detail that the viewer starts guessing the
       resolution, let them get close, then swerve once to a different answer than
       the one they were building toward -- and only then deliver the real payoff.
       One swerve, not three. Without it the story is a straight line from question
       to answer and the middle goes flat, which is exactly where viewers leave.
9f. *** ONE PAYOFF AT THE END IS A FAILED SCRIPT: BUILD A LADDER *** (1 ago 2026, from
   the transcript of a 1.6M-view Short on a 5,320-subscriber channel -- the closest
   verified comparable this channel has.)
   Two structural requirements, both mandatory.
   (a) COLD OPEN ON THE CONSEQUENCE, THEN REWIND. The first sentence states the END
       STATE -- what it cost, who stopped speaking to whom, what was sent -- and the
       rest of the script explains how it got there. Same engine as "Cronica de una
       muerte anunciada" in rule 9: the outcome is free, the mechanism is the debt.
       This guarantees every viewer who watches three seconds receives a promise, and
       it stacks a SECOND open loop (what was in the file / what did they do) on top
       of the first, so closing one does not release the viewer.
   (b) A PAYOFF LADDER AT IRREGULAR INTERVALS. A payoff is any moment the viewer is
       rewarded for still being there: a number that lands, a lie exposed, someone
       who was wrong being shown to be wrong, a document produced. Requirements:
         - at least FOUR payoffs across the script, and the biggest one last;
         - never more than ~20 seconds (~85 spoken words) with none. Measured on the
           first version of the visitor-log script, seconds 8 to 37 contained only
           setup -- room number, window, filing procedure -- and that is exactly the
           band where this channel's retention already collapses;
         - space them UNEVENLY. A regular beat lets the brain predict when the next
           reward is due, and a predictable gap is a safe moment to leave. Irregular
           reward schedules are the single most under-used retention lever available
           here, and they cost nothing but ordering.
       Declare them in the script JSON as `payoffs`: a list of short verbatim phrases
       from the script, in order. `_check_payoff_spacing` reads that list and warns on
       count, on gaps, and on a rhythm that is too regular.
   Corollary: the counter overlay (`counter_overlay.py`) should FILL LATE, near the
   final payoff, not at the halfway mark. Goal-gradient: motivation to keep watching
   rises as a visible goal gets close, so a bar that completes at 45% spends the whole
   second half giving nothing back.
9h. *** LA APUESTA ES COTIDIANA, NO MORTAL *** (2 ago 2026, a peticion de Fabian
   tras detectar que cinco guiones seguidos tenian una muerte o una perdida grave.)
   El drama sale de que algo PEQUENO escale, no de que alguien se muera. Matar a un
   personaje es el atajo barato: sube la temperatura sin que el guion se la gane.
   La prueba que lo zanja: el comparable verificado de 1,6M vistas (`kmiZss057XE`,
   canal de 5.320 subs) no tiene ni un muerto. Va de la compra del supermercado --
   los padres llaman parasito al hijo y luego se gastan 2.500 dolares al mes porque
   no saben comprar. Es mezquino, es cotidiano, y viaja por eso: todo el mundo ha
   sentido que su familia no le valora por dinero. Nadie ha enterrado a cinco
   parientes.
   Reglas:
   - Por defecto la historia NO lleva muerte, funeral, enfermedad terminal ni
     perdida gestacional. Si el giro solo funciona con un muerto, el giro es flojo.
   - Territorio bueno: dinero que no se devuelve, credito robado en el trabajo,
     el vecino, el grupo de padres del colegio, quien nunca paga su parte, la
     invitada de blanco. Bajo riesgo, alta identificacion.
   - Tres costes de abusar de la muerte, en orden: monotonia (quien ve dos ya sabe
     como va el tercero), techo de audiencia (la gente entra a Shorts a
     entretenerse) e idoneidad para anunciantes.
   - Excepcion: una muerte cada varios videos esta bien. Lo que rompe el canal es
     la racha, no el caso suelto. Por eso `_check_apuesta_cotidiana` mira los
     guiones ANTERIORES, no solo este.
10. The FIRST search_term (and its Wan/hero framing) must show the FAMOUS ICON ITSELF in a
    recognizable, unmistakable framing -- not a contextual establishing shot (a hallway, a
    document, a crowd) that requires explanation before it reads. A viewer's brain either
    recognizes a face/icon within about 100ms or it doesn't register in time to matter --
    an unfamiliar establishing shot burns that entire window for nothing. If the topic's
    icon cannot be shown instantly recognizable in frame one, it fails rule 9 of the Black
    Tom template above (find a different angle) rather than opening on a vague shot.

*** PLANTILLA UNICA DEL CANAL: replicar Black Tom *** Es el unico video con re-watch real
(3,76 -> 2,89) y de el se copian TRES cosas, no solo el loop: (1) el ancla es un ICONO
FAMOSO que el espectador reconoce al instante y puede ver hoy (la Estatua de la Libertad),
no un personaje historico que hay que presentar; (2) la consecuencia SIGUE VISIBLE HOY --
la antorcha lleva cerrada desde entonces -- asi que el espectador puede comprobarlo el
mismo ('ever since', 'to this day', 'still closed'); (3) el loop lexico y visual. Si el
tema no tiene un icono reconocible con una huella visible hoy, buscar otro angulo del
mismo hecho hasta encontrarlo -- no escribir el guion sin el.

Constraints:
- 355-375 words (NO menos: 160 palabras dan ~40s y el objetivo son 90s).
  Conversational, spoken English. Fragments are fine.
- Actionable and specific: real numbers, real rules, real examples.
- NO markdown, NO emojis, NO "in this video", NO headers. Ready to voice as-is.
- TWO PLATES PER SCENE. A scene with a person is drawn as two separate images:
  the BACKGROUND (search_terms[i], the place with nobody in it) and the CHARACTER
  (character_terms[i], the person alone). Write them so neither needs the other:
  the background must read as a finished empty scene, and the character must read
  as a standing figure with no context. Everything the engine does afterwards --
  cutting the figure out, splitting two figures apart, rigging a skeleton -- is
  separating things, and anything drawn touching cannot be separated later.
  Put the ACTION in the script, not in character_terms: the movement comes from
  the skeleton, so 'a handyman in workman overalls' is right and 'a handyman
  climbing out of a closet' is wrong.
- search_terms must be things a stock-footage site can match visually:
  "soldier reading a telegram by candlelight" yes, "the weight of betrayal" no. One
  term per scene, in the order the scenes should appear.
- description: open with a 1-2 sentence hook mirroring the script's tone, one sentence
  teasing the reframe, then 3-5 hashtags on their own line at the end.
"""

IDEAS_PROMPT = """\
Generate 5 viral YouTube Shorts topic ideas for HiddenFacts (US/English audience) — hidden
history, hoaxes, and espionage. Each idea must fit the Black Tom template: a famous icon
the viewer recognizes instantly, whose consequence is still visible today. If an idea has
no such anchor, find a different angle on the same event instead of proposing it without one.

Each idea must be a short, curiosity-driven title phrased as an unresolved question (see
title/hook_card rule in SCRIPT_PROMPT), under 70 characters, specific enough to script in
355-375 words (one clear event, not a broad theme).
Avoid topics already in this list: {existing_topics}
"""

IDEAS_SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 5,
            "description": "5 short, specific, curiosity-driven video topic titles",
        }
    },
    "required": ["ideas"],
    "additionalProperties": False,
}


def log(stage: str, msg: str) -> None:
    print(f"[{stage}] {msg}", flush=True)


def run(cmd: list[str], cwd: Path | None = None, timeout: float = 600.0) -> None:
    """timeout=600s por defecto: un ffmpeg colgado (input corrupto, stream_loop
    infinito) no debe bloquear una corrida desatendida (tarea programada) para
    siempre -- antes no habia limite y el proceso podia quedar colgado indefinidamente."""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Comando colgado >{timeout:.0f}s ({cmd[0]}), abortado: {' '.join(cmd[:4])}...") from e
    if result.returncode != 0:
        raise RuntimeError(f"Comando fallo ({cmd[0]}):\n{result.stderr[-2000:]}")


def ffprobe_duration(path: Path, timeout: float = 30.0) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True, timeout=timeout,
    )
    return float(out.stdout.strip())


def ffprobe_resolution(path: Path, timeout: float = 30.0) -> tuple[int, int] | None:
    """(ancho, alto) reales del stream de video, o None si no se puede leer."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=p=0:s=x", str(path)],
            capture_output=True, text=True, check=True, timeout=timeout,
        )
        w, h = out.stdout.strip().split("x")[:2]
        return int(w), int(h)
    except Exception:
        return None


def _atomic_write_json(path: Path, data) -> None:
    """Escribe a un .tmp y luego renombra (os.replace es atomico en el mismo
    filesystem) -- evita que dos procesos escribiendo el mismo manifest.json
    (ej. tarea programada solapada con una corrida manual) se pisen a mitad
    de escritura y corrompan used_topics.json / manifest de personajes /
    gemini_usage.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path, default):
    """Carga JSON con guarda contra archivo corrupto/inexistente -- unifica
    las ~4 variantes de 'leer dict o default' que habia sueltas por el archivo."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


_DRAWTEXT_SPECIAL = str.maketrans({
    "\\": "\\\\", "'": "’", ":": "\\:", ",": "\\,", "%": "\\%",
})


def _drawtext_escape(text: str) -> str:
    """Escapa texto para usarlo dentro de un filtro drawtext de ffmpeg.
    Sin esto, una coma parte el filtergraph completo (cada ',' separa
    filtros en -filter_complex) y '%{...}' dispara expansion de expresiones
    de drawtext (vector de inyeccion real) -- visto al agregar el CTA de
    texto en pantalla, que puede traer titulos/frases con puntuacion normal."""
    return text.translate(_DRAWTEXT_SPECIAL)


def _wrap_caption(text: str, width_chars: int = 26) -> str:
    """Envuelve el parrafo de caption estatico en lineas cortas para que quepa
    en el ancho del frame vertical -- drawtext no auto-envuelve texto."""
    import textwrap
    return "\n".join(textwrap.wrap(text, width=width_chars))


def with_retries(fn, *args, attempts: int = 3, delay: float = 10.0, **kwargs):
    """Reintenta llamadas de red (Claude, edge-tts) para que fallos transitorios
    no arruinen una corrida desatendida (tarea programada)."""
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            log("retry", f"{fn.__name__} intento {attempt}/{attempts} fallo: {e}")
            if attempt < attempts:
                time.sleep(delay)
    raise last_exc


# ------------------------------------------------------------- AUTO TOPICS

def _load_used_topics() -> set[str]:
    return set(_load_json(USED_TOPICS_FILE, []))


def _mark_topic_used(topic: str) -> None:
    used = _load_used_topics()
    used.add(topic)
    _atomic_write_json(USED_TOPICS_FILE, sorted(used))


def pick_next_topic() -> str:
    """Elige el siguiente tema no usado de topics.txt. Si se agotaron, genera 5 mas
    con Claude y los agrega al archivo. Nunca repite un tema ya producido."""
    topics_path = ROOT / "topics.txt"
    used = _load_used_topics()
    lines = [
        line.strip() for line in topics_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ] if topics_path.exists() else []

    remaining = [t for t in lines if t not in used]
    if remaining:
        return remaining[0]

    log("auto", "topics.txt agotado; generando 5 ideas nuevas con Claude...")
    ideas = with_retries(generate_ideas, lines)
    with topics_path.open("a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(ideas) + "\n")
    log("auto", f"5 ideas nuevas agregadas a topics.txt")
    return ideas[0]


# ---------------------------------------------------------------- 1. SCRIPT

def _claude_json_call(max_tokens: int, schema: dict, prompt: str) -> dict:
    """Helper compartido para llamadas a Claude con salida json_schema --
    unifica el patron repetido 3 veces (generate_script, generate_ideas,
    pick_sfx_cues) y corrige un bug real: si la respuesta solo trae un bloque
    'thinking' (presupuesto de pensamiento agotado), next(...) sin default
    lanza StopIteration cruda en vez de un error legible."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise RuntimeError("Claude no devolvio bloque de texto (solo thinking?) -- "
                            "revisar max_tokens/presupuesto de pensamiento")
    return json.loads(text)


def generate_script(topic: str) -> dict:
    log("script", f"Generando guion con {MODEL}...")
    # 2000 se quedaba corto (27 jul 2026): el prompt crecio mucho hoy (loop,
    # plantilla Black Tom, reglas de hook) y el presupuesto de thinking
    # adaptativo se comia todo el budget antes de escribir el bloque de texto
    data = with_retries(_claude_json_call, 4000, SCRIPT_SCHEMA, SCRIPT_PROMPT.format(topic=topic))
    log("script", f"{len(data['script'].split())} palabras, {len(data['search_terms'])} search terms")
    return data


def generate_ideas(existing_topics: list[str]) -> list[str]:
    log("ideas", f"Generando 5 ideas con {MODEL}...")
    prompt = IDEAS_PROMPT.format(existing_topics=", ".join(existing_topics) or "none")
    data = with_retries(_claude_json_call, 1000, IDEAS_SCHEMA, prompt)
    return data["ideas"]


# ----------------------------------------------------------------- 2. AUDIO

async def _tts(script: str, voice: str, rate: str, mp3_path: Path) -> list[tuple[float, float, str]]:
    import edge_tts

    words: list[tuple[float, float, str]] = []
    communicate = edge_tts.Communicate(script, voice, rate=rate, boundary="WordBoundary")
    with open(mp3_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000
                end = (chunk["offset"] + chunk["duration"]) / 10_000_000
                words.append((start, end, chunk["text"]))
    return words


def trim_silence_inplace(audio_path: Path, words: list[tuple[float, float, str]],
                         keep: float = 0.10, noise: float = -35.0,
                         min_silence: float = 0.20):
    """Recorta los silencios de la voz y remapea los timestamps de palabra.

    edge-tts deja ~0.4s entre oraciones; medido 30 jul 2026 eso era el 13,9% de
    un guion de 16 oraciones. En Shorts manda el tiempo absoluto visto, asi que
    ese aire es retencion regalada.

    Devuelve (audio_path, words) ya en el eje recortado. El original se guarda
    como voice_raw.mp3 y voice.mp3 pasa a ser la version apretada, para que
    nada aguas abajo tenga que enterarse del cambio.

    No lleva los silencios a cero (keep=0.10 por defecto): a cero las palabras
    se pisan y suena atropellado, peor que el original.
    """
    try:
        import trim_silence as tsm
    except Exception as e:
        log("audio", f"AVISO: no se pudo importar trim_silence ({e}), sigo sin recortar")
        return audio_path, words

    try:
        total = ffprobe_duration(audio_path)
        sils = tsm.detect_silences(audio_path, noise, min_silence)
        rem = tsm.removal_intervals(sils, keep)
        if not rem:
            log("audio", "sin silencios que recortar")
            return audio_path, words

        segs = tsm.keep_segments(rem, total)
        tmp = audio_path.with_name("voice_tight.mp3")
        tsm.build_audio(audio_path, tmp, segs)

        raw = audio_path.with_name("voice_raw.mp3")
        audio_path.replace(raw)
        tmp.replace(audio_path)

        new_words = [(tsm.remap(s, rem), tsm.remap(e, rem), w) for s, e, w in words]
        cut = sum(e - s for s, e in rem)
        log("audio", f"silencios recortados: -{cut:.2f}s ({cut / total * 100:.1f}%), "
                     f"{total:.1f}s -> {total - cut:.1f}s (original en voice_raw.mp3)")
        return audio_path, new_words
    except Exception as e:
        log("audio", f"AVISO: fallo el recorte de silencios ({type(e).__name__}: {e}), "
                     f"sigo con la voz original")
        return audio_path, words


KOKORO_DIR = ROOT / "tools" / "kokoro_tts"
# Prefijos de voz Kokoro -> si --voice empieza con uno de estos, se usa Kokoro
# (voz local, mas natural, gratis e ilimitada) en vez de edge-tts.
KOKORO_VOICE_PREFIXES = ("em_", "ef_", "am_", "af_", "bm_", "bf_")


def _kokoro_tts(script: str, voice: str, wav_path: Path, speed: float = 1.0) -> list[tuple[float, float, str]]:
    """Corre tools/kokoro_tts/synth.py en su propio venv (Python 3.12; Kokoro
    no compila aun en 3.14). Timestamps de palabra son una ESTIMACION por
    longitud de caracter, no timing acustico real -- ver synth.py."""
    text_file = wav_path.with_suffix(".txt")
    words_file = wav_path.with_suffix(".words.json")
    text_file.write_text(script, encoding="utf-8")
    run([
        "uv", "run", "--directory", str(KOKORO_DIR), "synth.py",
        "--text-file", str(text_file), "--voice", voice,
        "--out", str(wav_path), "--words-out", str(words_file),
        "--speed", str(speed),
    ])
    words_raw = json.loads(words_file.read_text(encoding="utf-8"))
    return [(float(s), float(e), w) for s, e, w in words_raw]


CHATTERBOX_DIR = ROOT / "tools" / "chatterbox_tts"
# Prefijo de voz Chatterbox: --voice cb_es / cb_en. Hasta el 3 ago 2026 el
# pipeline SOLO sabia enrutar a Kokoro o edge-tts, asi que todo guion en espanol
# caia en edge-tts (es-US-AlonsoNeural) y sonaba a lector de Windows: Chatterbox
# existia en tools/ pero unicamente viral_lab.py lo llamaba.
CHATTERBOX_VOICE_PREFIXES = ("cb_",)
# Timbre de referencia. Sin --ref, Chatterbox usa su voz por defecto, que en
# espanol sale ambigua y aguda: el canal necesita narrador masculino de
# documental. Chatterbox toma del --ref SOLO EL TIMBRE (y con el, el acento); la
# prosodia la genera el. Dos hallazgos de la sesion del 3 ago 2026, ambos de oido:
#  - Clonar una muestra de edge-tts a exaggeration 0.3 seguia sonando a robot;
#    con exaggeration 0.45 + cfg 0.3 pasa a sonar humano. El problema eran los
#    parametros, no el origen sintetico de la muestra.
#  - Las voces en espanol de Kokoro (em_*) son de Espana y el acento viaja con el
#    timbre, asi que la muestra tiene que ser LATAM. Se eligio base mexicana:
#    es el "espanol neutro" del doblaje, el que no suena de ningun pais concreto.
# assets/voice_refs/<lang>.wav manda si existe; si no, se sintetiza y se cachea.
CHATTERBOX_REF_DIR = ROOT / "assets" / "voice_refs"
_REF_SEED_VOICE = {"es": "es-MX-JorgeNeural", "en": "en-US-AndrewNeural"}
# Frase larga y en tono neutro: la referencia define el timbre, asi que no debe
# llevar carga emocional ni signos de exclamacion.
_REF_SEED_TEXT = {
    "es": "En noviembre de aquel año, los documentos del archivo revelaron una "
          "operación que nadie había registrado. Las cifras estaban ahí, firmadas, "
          "y durante años ninguna autoridad quiso revisarlas con atención.",
    "en": "In November of that year, the archive documents revealed an operation "
          "no one had recorded. The figures were there, signed, and for years no "
          "authority cared to examine them closely.",
}


def _chatterbox_ref(lang: str) -> Path | None:
    """Devuelve (creandola si hace falta) la muestra de timbre para ese idioma.

    Un wav propio en assets/voice_refs/<lang>.wav tiene prioridad: si el usuario
    deja ahi una grabacion real, se clona esa en vez de la sintetica.
    """
    CHATTERBOX_REF_DIR.mkdir(parents=True, exist_ok=True)
    ref = CHATTERBOX_REF_DIR / f"{lang}.wav"
    if ref.exists():
        return ref
    seed_voice = _REF_SEED_VOICE.get(lang)
    if not seed_voice:
        return None
    mp3 = ref.with_suffix(".mp3")
    try:
        log("audio", f"Creando muestra de timbre masculino ({seed_voice})...")
        asyncio.run(_tts(_REF_SEED_TEXT[lang], seed_voice, "-5%", mp3))
        run(["ffmpeg", "-y", "-i", str(mp3), "-ar", "24000", "-ac", "1", str(ref)])
        mp3.unlink(missing_ok=True)
        return ref
    except Exception as e:
        log("audio", f"AVISO: sin muestra de timbre ({type(e).__name__}: {e}), "
                     f"Chatterbox usara su voz por defecto")
        return None


def _align_words(audio: Path, script: str = "",
                 lang: str = "") -> list[tuple[float, float, str]]:
    """Timestamps REALES por palabra sobre el audio ya sintetizado.

    Chatterbox no devuelve tiempos (ver tools/chatterbox_tts/synth.py) y los de
    Kokoro son una estimacion por longitud de caracter. Todo lo que va sincronizado
    -- subtitulos karaoke, SFX, cortes de escena, el motor KoreX -- necesita timing
    acustico, asi que se reconoce el propio audio con whisper.
    """
    from faster_whisper import WhisperModel
    try:
        import torch
        cuda = torch.cuda.is_available()
    except Exception:
        cuda = False
    device, compute = ("cuda", "float16") if cuda else ("cpu", "int8")
    m = WhisperModel("base", device=device, compute_type=compute)
    segs, _ = m.transcribe(str(audio), word_timestamps=True, language=lang or None)
    heard = [(float(w.start), float(w.end), w.word.strip())
             for s in segs for w in (s.words or []) if w.word.strip()]
    return _snap_to_script(heard, script) if script else heard


def _norm_word(w: str) -> str:
    """Forma comparable: minusculas, sin puntuacion y sin tildes/dieresis."""
    import unicodedata
    w = "".join(c for c in unicodedata.normalize("NFD", w.lower())
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", w)


def _snap_to_script(heard: list[tuple[float, float, str]],
                    script: str) -> list[tuple[float, float, str]]:
    """Devuelve las palabras DEL GUION con los tiempos que midio whisper.

    Whisper transcribe lo que oye, no lo que escribimos: donde entiende mal, el
    subtitulo quemado muestra una palabra distinta a la narrada y parece que el
    TTS "cambio el guion" (reportado por el usuario 3 ago 2026). El audio manda
    para el TIMING, el guion manda para el TEXTO.

    Se alinean ambas secuencias con difflib; a cada palabra del guion sin
    contraparte reconocida se le reparte el hueco temporal de sus vecinas, asi
    que nunca se pierde ni se reordena una palabra del guion.
    """
    import difflib
    target = [w for w in re.findall(r"\S+", script) if _norm_word(w)]
    if not target or not heard:
        return heard
    sm = difflib.SequenceMatcher(
        a=[_norm_word(w) for _, _, w in heard],
        b=[_norm_word(w) for w in target], autojunk=False)
    times: list[tuple[float, float] | None] = [None] * len(target)
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            times[j + k] = (heard[i + k][0], heard[i + k][1])
    # Rellena los no emparejados repartiendo el hueco entre anclas conocidas.
    first = next((t for t in times if t), (heard[0][0], heard[0][1]))
    last = next((t for t in reversed(times) if t), (heard[-1][0], heard[-1][1]))
    idx = 0
    while idx < len(times):
        if times[idx] is not None:
            idx += 1
            continue
        end = idx
        while end < len(times) and times[end] is None:
            end += 1
        lo = times[idx - 1][1] if idx > 0 else first[0]
        hi = times[end][0] if end < len(times) else last[1]
        step = max((hi - lo) / (end - idx), 0.06)
        for k in range(idx, end):
            times[k] = (lo + step * (k - idx), lo + step * (k - idx + 1))
        idx = end
    return [(t[0], t[1], w) for t, w in zip(times, target)]


def _chatterbox_tts(script: str, voice: str, wav_path: Path,
                    exaggeration: float = 0.45,
                    cfg: float = 0.3) -> list[tuple[float, float, str]]:
    """Corre tools/chatterbox_tts/synth.py en su propio venv (arrastra torch).

    Cacheado por hash de texto+parametros en assets/cache/voices/: sintetizar es
    lo mas lento del pipeline, y re-renderizar un video no debe volver a pagarlo.
    """
    lang = voice.split("_", 1)[1] if "_" in voice else "es"
    ref = str(_chatterbox_ref(lang).resolve()) if _chatterbox_ref(lang) else ""
    key = hashlib.sha1(f"{script}|{ref}|{exaggeration}|{cfg}|{lang}".encode()).hexdigest()[:16]
    cache = ROOT / "assets" / "cache" / "voices"
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / f"{key}.wav"
    if cached.exists():
        log("audio", "voz Chatterbox desde cache")
        shutil.copyfile(cached, wav_path)
    else:
        text_file = wav_path.with_suffix(".txt")
        text_file.write_text(script, encoding="utf-8")
        cmd = ["uv", "run", "--directory", str(CHATTERBOX_DIR), "synth.py",
               "--text-file", str(text_file.resolve()), "--out", str(wav_path.resolve()),
               "--exaggeration", str(exaggeration), "--cfg", str(cfg),
               "--lang", lang]
        if ref:
            cmd += ["--ref", ref]
        log("audio", f"Sintetizando voz con Chatterbox (lang={lang}"
                     f"{', ref clonada' if ref else ''})...")
        run(cmd, timeout=1800)
        text_file.unlink(missing_ok=True)
        if not wav_path.exists():
            raise RuntimeError("Chatterbox no genero el wav")
        shutil.copyfile(wav_path, cached)
    return _align_words(wav_path, script=script, lang=lang)


# Velocidad real de edge-tts a +8%, MEDIDA sobre 4 videos generados el 30 jul
# 2026 (no estimada): 3,65 wps sin recortar, 4,07 wps con --trim-silence. Las
# constantes anteriores (2,3-2,7) venian de otra configuracion y hacian que el
# aviso de pacing saltara en TODOS los guiones aunque estuvieran bien.
# El rango se centra en 4,07 (ritmo CON --trim-silence, que es como generamos
# ahora). Sin recorte el mismo guion sale ~11% mas largo.
WPS_MIN, WPS_MAX = 3.9, 4.3

# Duracion objetivo. 60s -> 90s -> 175s el 31 jul 2026.
# Los 175s NO son una estimacion: se midieron los 50 videos mas recientes de
# Reddit Gossipz (196k subs, 416M vistas, mediana de 233k vistas por video) y
# TODOS caen entre 163s y 179s, mediana 176s. Ni uno solo corto. Estan pegados
# al techo de 3 minutos de Shorts, no al "punto dulce 30-45s" -- ese numero se
# midio para HiddenFacts, que es otro formato.
# TOPE FIJADO POR EL USUARIO 31 jul 2026: 90s maximo, aunque el lider use 175s.
# A nuestro ritmo medido (4,07 wps con --trim-silence) => ~366 palabras.
# Nota: ellos hablan a 5,78 wps, bastante mas rapido, asi que su guion de 175s
# tiene ~1000 palabras. No copiar su conteo de palabras, copiar la DURACION.
TARGET_SECONDS = 90.0


def _check_pacing(script: str, target_seconds: float = TARGET_SECONDS) -> None:
    """Avisa ANTES de gastar creditos de TTS/imagen si la densidad de
    palabras-por-segundo del guion cae fuera de [WPS_MIN, WPS_MAX]. No bloquea,
    solo informa (igual que el resto de logs del pipeline) -- ver
    RETENTION_CHECKLIST.md."""
    word_count = len(script.split())
    wps = word_count / target_seconds
    if wps < WPS_MIN:
        target_words = round(WPS_MIN * target_seconds)
        log("pacing", f"AVISO: {word_count} palabras / {target_seconds:.0f}s = "
                       f"{wps:.2f} wps (lento, riesgo de curva 'Hump'). "
                       f"Considera subir a ~{target_words} palabras.")
    elif wps > WPS_MAX:
        target_words = round(WPS_MAX * target_seconds)
        log("pacing", f"AVISO: {word_count} palabras / {target_seconds:.0f}s = "
                       f"{wps:.2f} wps (denso, se pierden palabras en mute). "
                       f"Considera bajar a ~{target_words} palabras.")
    else:
        log("pacing", f"{word_count} palabras / {target_seconds:.0f}s = {wps:.2f} wps (OK)")


def _starts_with_why(text: str) -> bool:
    """True si el texto arranca literalmente con 'Why' / 'Por que' (con o sin
    tilde, con o sin '¿' de apertura)."""
    t = (text or "").strip().lstrip("¿\"'“”‘’-— ").lower()
    return t.startswith("why") or t.startswith("por que") or t.startswith("por qué")


def _check_open_hook(script: str, title: str, hook_card: str,
                     formato: str = "") -> None:
    """La primera frase debe AFIRMAR un hecho imposible y dejarlo sin resolver
    (regla 9 reescrita el 1 ago 2026; antes obligaba a abrir con "Why").

    Dos avisos distintos:
      - abre con pregunta -> el modelo viejo, mas debil: la pregunta PIDE al
        espectador que se interese en vez de dejarlo incomodo.
      - la frase se auto-resuelve -> una subordinada causal ("because...",
        "so that...") contesta el misterio en el segundo 3 y a partir de ahi
        no le debemos nada al espectador. Es exactamente donde la retencion
        medida se cae.

    Vive aqui y no solo en el prompt porque los guiones escritos a mano entran
    por --script-file y NO pasan por Claude: sin este aviso la regla no se
    aplicaria justo en el camino que mas usamos.
    """
    for etiqueta, texto in (("guion", script), ("titulo", title), ("hook_card", hook_card)):
        if texto and _starts_with_why(texto):
            log("lint", f"AVISO: el {etiqueta} abre con pregunta 'Why/Por que'. "
                        f"La regla 9 pide un hecho imposible AFIRMADO en seco "
                        f"(Garcia Marquez nunca pregunta).")

    primera = next((x.strip() for x in re.split(r"(?<=[.!?])\s+", script or "") if x.strip()), "")
    if primera and _RESUELVE_HOOK.search(primera):
        log("lint", "AVISO: la 1a frase contiene su propia respuesta "
                    "(because/since/so that/porque). Corta la subordinada y "
                    "dejala colgando -- regla 9, 'never resolve the hook in the hook'.")
    tiene_cifra = re.search(r"\d", primera)
    tiene_nombre = re.search(r"\s[A-Z][a-z]+", primera)
    tiene_numero = any(w.strip(".,;:-").upper() in _AUTO_RED
                       for w in re.split(r"[\s-]+", primera))
    if formato == "chisme":
        # Excepcion pedida por Fabian el 1 ago 2026 y respaldada por el unico
        # dato real que hay: el ganador de 1,6M tambien abre con marco, no con
        # hecho. El chisme hablado empieza por la REACCION del que cuenta y el
        # oyente se inclina para averiguar que la provoco; un hecho en seco es
        # periodismo, no chisme. La intencion de la regla 9 se conserva -- el
        # hueco sigue necesitando su prime -- solo se mueve de sitio: en vez de
        # exigirlo en la 1a frase, se admite en los primeros ~3 segundos.
        ventana = " ".join(script.split()[:int(3 * WPS_SPOKEN)])
        if not (re.search(r"\d", ventana) or re.search(r"\s[A-Z][a-z]+", ventana)
                or any(w.strip(".,;:-").upper() in _AUTO_RED
                       for w in re.split(r"[\s-]+", ventana))):
            log("lint", "AVISO: formato chisme, pero en los primeros 3 segundos "
                        "no hay ningun dato concreto. El marco emocional abre la "
                        "puerta; sin dato detras no hay hueco que llenar.")
        return

    if primera and not (tiene_cifra or tiene_nombre or tiene_numero):
        log("lint", "AVISO: la 1a frase no lleva ningun dato concreto dentro "
                    "(cifra, fecha o nombre propio). Sin ese 'prime' no hay hueco "
                    "de informacion que llenar, solo ambiente -- regla 9.")


# Subordinadas que resuelven el gancho dentro del propio gancho.
_RESUELVE_HOOK = re.compile(
    r"\b(because|so that|which is why|porque|ya que|"
    r"puesto que|de modo que)\b", re.I)


# Palabras por segundo reales de edge-tts a +8% tras recortar silencios, medidas
# sobre los tres guiones de agosto: ~4.3. Se usa para traducir posiciones del
# texto a segundos aproximados sin tener que sintetizar el audio.
WPS_SPOKEN = 4.3
PAYOFF_MAX_GAP_S = 20.0
PAYOFF_MIN_COUNT = 4


# Frases de preambulo disfrazadas de narracion. Medido 1 ago 2026 en
# -79EJI_BSsE: "My name doesn't matter, but my story does" ocupa el segundo
# 4,0-5,8 y la retencion se desploma desde el 5,5 (104,9% -> 59,4% en 4,6s).
# Segundo y medio de desfase = lo que tarda alguien en decidir y deslizar.
_RELLENO = [
    r"my name (does\s*n.?t|doesn't) matter", r"this is my story", r"here'?s my story",
    r"let me tell you", r"i'?ll tell you", r"it all started", r"where do i (even )?begin",
    r"buckle up", r"bear with me", r"a bit of context", r"some background",
    r"mi nombre no importa", r"esta es mi historia", r"dejame contarte",
    r"todo empezo cuando", r"para que entiendas", r"os cuento",
]
_RELLENO_RE = [re.compile(p, re.I) for p in _RELLENO]
VENTANA_CRITICA = (5.0, 10.0)


_MUERTE = re.compile(
    r"\b(died|death|dead|funeral|buried|grave|headstone|cemetery|"
    r"terminal|miscarriage|stillborn|passed away|murio|muerte|"
    r"entierro|lapida|cementerio)\b|no heartbeat", re.I)


def _check_apuesta_cotidiana(script: str, script_path=None) -> None:
    """Regla 9h: avisa de la RACHA de historias con muerte, no del caso suelto.

    Una muerte cada varios videos esta bien. Lo que rompe el canal es encadenar
    -- medido el 2 ago 2026: cinco guiones seguidos con funeral o perdida, y el
    comparable de 1,6M no tiene ninguna.
    """
    aqui = bool(_MUERTE.search(script or ""))
    if not aqui:
        return
    carpeta = Path(script_path).parent if script_path else Path("scripts")
    if not carpeta.is_dir():
        log("lint", "AVISO: este guion se apoya en una muerte (regla 9h).")
        return
    otros = sorted(carpeta.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:6]
    con = sum(1 for f in otros
              if f.name != Path(script_path or "").name
              and _MUERTE.search(f.read_text(encoding="utf-8", errors="ignore")))
    if con >= 2:
        log("lint", f"AVISO: este guion se apoya en una muerte, y {con} de los "
                    f"ultimos guiones tambien. Es una racha, no un caso suelto -- "
                    f"regla 9h. El comparable de 1,6M no tiene ni un muerto.")


def _check_relleno_inicial(script: str) -> None:
    """Ninguna frase de los primeros 10s puede existir sin aportar un hecho.

    Regla 9g. El relleno no aburre: rompe la confianza. El espectador acaba de
    aceptar una promesa y la siguiente frase no le da nada, asi que concluye
    que el resto tampoco. Por eso la caida es tan vertical y no gradual.
    """
    t = 0.0
    for frase in [x.strip() for x in re.split(r"(?<=[.!?])\s+", script or "") if x.strip()]:
        dur = len(frase.split()) / WPS_SPOKEN
        if t > 12.0:
            break
        for rx in _RELLENO_RE:
            if rx.search(frase):
                log("lint", f"AVISO: relleno en el segundo {t:.1f} -> {frase!r}. "
                            f"Ninguna frase de los primeros 10s puede existir sin "
                            f"aportar un hecho nuevo (regla 9g).")
                break
        t += dur


def _check_ventana_critica(script: str, payoffs: list[str] | None) -> None:
    """Tiene que haber un premio entre el segundo 5 y el 10 (regla 9g).

    Es la ventana donde la retencion medida se desangra: -45,5 puntos en 4,6s.
    La regla 9f reparte premios pero no fija ninguno AQUI, y por eso el
    visitor-log salio con premios en el 3,2 y el 20,1 -- el hueco justo encima.
    """
    if not payoffs:
        return
    a, b = VENTANA_CRITICA
    for frase in payoffs:
        i = script.lower().find(frase.lower())
        if i < 0:
            continue
        t = len(script[:i].split()) / WPS_SPOKEN
        if a <= t <= b:
            return
    log("lint", f"AVISO: ningun premio entre el segundo {a:.0f} y el {b:.0f}. "
                f"Es la ventana donde la retencion medida cae 45 puntos en 4,6s "
                f"-- regla 9g, premio obligatorio ahi.")


def _check_payoff_spacing(script: str, payoffs: list[str] | None) -> None:
    """Verifica la escalera de premios de la regla 9f.

    Un premio es cualquier momento en que el espectador cobra por seguir ahi.
    Tres avisos: pocos premios, un hueco largo sin ninguno, y un ritmo
    demasiado regular (si el cerebro puede predecir cuando llega el siguiente,
    el hueco previsible es un momento seguro para irse).

    Vive aqui y no solo en el prompt porque los guiones a mano entran por
    --script-file y no pasan por Claude.
    """
    if not payoffs:
        log("lint", "AVISO: el guion no declara `payoffs`. Sin la escalera de la "
                    "regla 9f no hay forma de saber si hay 30s seguidos sin premio.")
        return

    palabras = script.split()
    total_s = len(palabras) / WPS_SPOKEN
    pos = []
    for frase in payoffs:
        i = script.lower().find(frase.lower())
        if i < 0:
            log("lint", f"AVISO: el payoff {frase!r} no aparece literal en el guion.")
            continue
        pos.append(len(script[:i].split()) / WPS_SPOKEN)
    if not pos:
        return
    pos.sort()

    if len(pos) < PAYOFF_MIN_COUNT:
        log("lint", f"AVISO: solo {len(pos)} premios declarados (minimo "
                    f"{PAYOFF_MIN_COUNT}, regla 9f). Un unico pago al final solo "
                    f"lo cobra quien llega al final.")

    huecos = [pos[0]] + [b - a for a, b in zip(pos, pos[1:])] + [total_s - pos[-1]]
    peor = max(huecos)
    if peor > PAYOFF_MAX_GAP_S:
        i = huecos.index(peor)
        desde = 0.0 if i == 0 else pos[i - 1]
        log("lint", f"AVISO: {peor:.0f}s sin ningun premio (del segundo {desde:.0f} "
                    f"al {desde + peor:.0f}). Maximo {PAYOFF_MAX_GAP_S:.0f}s, regla 9f.")

    internos = huecos[1:-1]
    if len(internos) >= 3:
        media = sum(internos) / len(internos)
        desv = (sum((x - media) ** 2 for x in internos) / len(internos)) ** 0.5
        if media and desv / media < 0.25:
            log("lint", f"AVISO: los premios llegan a intervalos casi iguales "
                        f"(~{media:.0f}s, desviacion {desv:.1f}s). Un ritmo predecible "
                        f"le dice al espectador cuando puede irse -- regla 9f pide "
                        f"espaciado irregular.")


_CONTRAST_OPENERS = ("but", "except", "yet", "although", "however",
                     "pero", "salvo", "aunque", "sin embargo")


def _check_hook_beats(script: str) -> None:
    """Verifica el gancho de 3 tiempos de la regla 9b (framework Kallaway).

    Beat 1 = el hecho imposible afirmado (regla 9, _check_open_hook), beat 2 = frase
    corta que arranca con palabra de contraste, beat 3 = giro contrario.
    Solo avisa; igual que el resto del lint, nunca bloquea. Vive aqui y no
    solo en el prompt porque los guiones a mano entran por --script-file y no
    pasan por Claude.
    """
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script or "") if s.strip()]
    if len(sents) < 3:
        log("lint", "AVISO: el guion tiene menos de 3 oraciones, no se puede "
                    "verificar el gancho de 3 tiempos (regla 9b).")
        return

    beat2 = sents[1]
    first_word = re.sub(r"[^\w]", "", beat2.split()[0]).lower() if beat2.split() else ""
    if first_word not in _CONTRAST_OPENERS:
        log("lint", f"AVISO: la 2a oracion no abre con palabra de contraste "
                    f"(But/Except/Yet/Although); abre con {first_word!r}. Es el "
                    f"'scroll-stop' de la regla 9b, sin el no hay freno tras el gancho.")

    for i, beat in ((2, sents[1]), (3, sents[2])):
        n = len(beat.split())
        if n > 12:
            log("lint", f"AVISO: la oracion {i} del gancho tiene {n} palabras (max 12) "
                        f"-- la apertura debe ser staccato, regla 9b.")


_CONNECTIVES = ("but", "therefore", "so", "because", "yet", "except", "although",
                "however", "pero", "asi que", "porque", "aunque", "sin embargo")


def _check_but_therefore(script: str) -> None:
    """Avisa si el guion encadena escenas con 'and then' en vez de 'but/therefore'.

    Regla de Trey Parker / Matt Stone (South Park), citada por Kallaway y
    revisada 31 jul 2026: entre dos beats debe caber 'pero' o 'por lo tanto',
    nunca 'y entonces'. 'Y entonces' apila detalles y el espectador se cae;
    'pero/por lo tanto' abre un conflicto que hay que cerrar.

    *** RECALIBRADO 31 jul 2026, LA EVIDENCIA LO CONTRADICE EN PARTE ***
    Al medir el video #1 de Reddit Gossipz (1,66M vistas, lider del formato)
    dio 0/27 conectores = 0%. Reprobaria este lint entero y aun asi es el video
    mas visto del nicho. El consejo de Parker/Stone viene de comedia narrativa
    larga (South Park) y NO parece transferir a este formato, que es una
    acumulacion de vinetas cortas, no una cadena causal.
    Por eso el umbral baja de 0,30 a 0,12: sigue avisando del caso patologico
    (un guion sin ningun conector) pero ya no penaliza el patron que de hecho
    usa el lider. Si al medir 3-5 competidores mas sigue dando ~0%, este check
    hay que borrarlo, no seguir bajandole el umbral.
    """
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script or "") if s.strip()]
    if len(sents) < 4:
        return
    body = sents[1:]  # la primera es el gancho, no encadena con nada
    hits = sum(1 for s in body
               if s.split() and s.split()[0].strip(",.").lower() in _CONNECTIVES)
    ratio = hits / len(body)
    if ratio < 0.12:
        log("lint", f"AVISO (suave): {hits}/{len(body)} oraciones encadenan con "
                    f"but/therefore/so/because ({ratio:.0%}). Referencia: el lider "
                    f"del formato esta en 0%, asi que esto NO es urgente -- solo "
                    f"revisa que la historia no sea una lista plana de sucesos.")


def _check_sentence_rhythm(script: str) -> None:
    """Avisa si todas las oraciones miden casi lo mismo (ritmo monotono).

    Principio de Gary Provost citado por Kallaway: alternar frases cortas,
    medias y largas crea musica; frases todas iguales aburren.

    *** RECALIBRADO 31 jul 2026: AYER DIJE QUE NO HABIA EVIDENCIA, AHORA SI LA HAY ***
    Se implemento con umbral 3,5 y una nota diciendo que nuestros datos lo
    contradecian (black_tom, el de mejor retencion, tenia la MENOR variacion:
    3,7). Al medir al lider del formato el resultado se invierte: Reddit Gossipz
    #1 (1,66M vistas) tiene desviacion 6,1, con frases de 2 a 24 palabras. Sus
    frases de dos palabras ("Same game.", "Never scanned.") son justo el recurso
    que rompe la monotonia.
    Nuestros guiones de historias estaban entre 3,7 y 4,8, todos por debajo del
    lider, asi que el umbral sube de 3,5 a 5,0. black_tom sigue siendo la
    excepcion pero es de OTRO canal y otro formato (documental historico, no
    historia personal en primera persona).
    """
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script or "") if s.strip()]
    if len(sents) < 6:
        return
    lens = [len(s.split()) for s in sents]
    mean = sum(lens) / len(lens)
    var = sum((x - mean) ** 2 for x in lens) / len(lens)
    stdev = var ** 0.5
    if stdev < 5.0:
        log("lint", f"AVISO: las oraciones miden casi todas lo mismo "
                    f"(media {mean:.0f} palabras, desviacion {stdev:.1f}; el lider "
                    f"del formato esta en 6,1 con frases de 2 a 24 palabras). "
                    f"Mete frases de 2-4 palabras entre las largas para romper la "
                    f"monotonia (ver regla 9c).")


def _check_script_lint(script: str, title: str, voice: str,
                       search_terms: list[str] | None = None) -> None:
    """Avisos rapidos y baratos (nunca bloquean) sobre reglas ya validadas
    con datos reales esta temporada, para no depender de acordarse a mano:
    (1) palabras con ñ en guiones de voz en espanol -- el TTS las pronuncia
    mal (ver memoria voz-espanol-impixxel); (2) titulo sin nombre propio
    reconocible -- proxy barato de la regla 'antagonista/institucion famosa
    en el titulo' (ver memoria titulo-antagonista-famoso), que correlaciono
    con 1000+ vistas en HiddenFacts; (3) primer search_term sin cara/close-up
    -- el area fusiforme facial reconoce rostros en 50-200ms, es el freno de
    scroll mas rapido; abrir con una escena amplia desperdicia esa palanca (ver
    RETENTION_CHECKLIST.md, gancho visual)."""
    if voice.startswith("es-") and "ñ" in script.lower():
        log("lint", "AVISO: el guion tiene 'ñ' con voz en espanol -- el TTS suele "
                     "pronunciarla mal, considera un sinonimo (ver memoria "
                     "voz-espanol-impixxel).")
    # heuristica barata: alguna palabra que empiece en mayuscula despues de la
    # primera palabra del titulo (nombre propio/institucion), sin serlo TODAS
    # las palabras (titulo en Title Case no cuenta como señal)
    words = title.split()
    if len(words) > 1:
        capitalized = sum(1 for w in words[1:] if w[:1].isupper())
        if capitalized == 0:
            log("lint", "AVISO: el titulo no parece nombrar a nadie/nada propio "
                        "(antagonista, institucion, figura famosa) -- esa señal "
                        "correlaciono con 1000+ vistas en HiddenFacts, considera "
                        "agregarla si el hecho real lo permite (ver memoria "
                        "titulo-antagonista-famoso).")
    if search_terms:
        first = search_terms[0].lower()
        if not any(w in first for w in ("face", "close-up", "close up", "eyes",
                                        "portrait", "staring", "expression")):
            log("lint", "AVISO: el primer search_term no parece un primer plano de "
                        "un rostro -- una cara con contacto visual frena el scroll "
                        "en 50-200ms (gancho visual, ver RETENTION_CHECKLIST.md). "
                        "Considera abrir con un close-up de cara intensa.")
        sentence_count = len([s for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()])
        if len(search_terms) != sentence_count:
            log("lint", f"AVISO: {len(search_terms)} search_terms mas {sentence_count} "
                        "oraciones en el guion -- el corte de escena solo puede caer en "
                        "fin de oracion, un conteo distinto fuerza al menos un corte a "
                        "mitad de frase (imagen y voz desincronizadas, ver investigacion "
                        "de sync narracion/imagen). Igualalos o agrega una oracion de "
                        "cierre extra si el ultimo search_term es un eco/loop visual.")


def _rate_to_kokoro_speed(rate: str) -> float:
    """Reusa el mismo --rate de edge-tts ('+8%', '-15%') como velocidad para
    Kokoro, asi no hace falta un flag nuevo: '+0%' o vacio = 1.0 normal."""
    try:
        pct = float(rate.strip().replace("%", ""))
        return max(0.5, min(2.0, 1.0 + pct / 100))
    except (ValueError, AttributeError):
        return 1.0


def generate_audio(script: str, voice: str, rate: str, out_dir: Path) -> tuple[Path, list]:
    if voice.startswith(CHATTERBOX_VOICE_PREFIXES):
        wav_path = out_dir / "voice.wav"
        words = _chatterbox_tts(script, voice, wav_path)
        mp3_path = out_dir / "voice.mp3"
        run(["ffmpeg", "-y", "-i", str(wav_path), "-ar", "44100", str(mp3_path)])
    elif voice.startswith(KOKORO_VOICE_PREFIXES):
        wav_path = out_dir / "voice.wav"
        speed = _rate_to_kokoro_speed(rate)
        log("audio", f"Sintetizando voz con Kokoro (local, voz {voice}, speed {speed})...")
        words = _kokoro_tts(script, voice, wav_path, speed=speed)
        # convertir a mp3 para que el resto del pipeline (assemble, etc) sea igual
        mp3_path = out_dir / "voice.mp3"
        run(["ffmpeg", "-y", "-i", str(wav_path), "-ar", "44100", str(mp3_path)])
    else:
        mp3_path = out_dir / "voice.mp3"
        log("audio", f"Sintetizando voz ({voice}, rate {rate})...")
        words = asyncio.run(_tts(script, voice, rate, mp3_path))

    if not words:
        raise RuntimeError("TTS no devolvio timestamps de palabras")

    # Recorta el silencio de la COLA para que el autoloop del Short empalme
    # apretado (final->inicio) y dispare re-watches (>100% de reproduccion, la
    # senal mas fuerte en Shorts). Solo afecta despues de la ultima palabra, asi
    # que no desincroniza los subtitulos (sus timestamps caen antes del silencio).
    trimmed = out_dir / "voice_trim.mp3"
    try:
        run(["ffmpeg", "-y", "-i", str(mp3_path), "-af",
             "areverse,silenceremove=start_periods=1:start_silence=0.1:"
             "start_threshold=-45dB,areverse", str(trimmed)])
        trimmed.replace(mp3_path)
    except Exception as e:
        log("audio", f"trim de silencio final omitido: {e}")

    # Recorta el silencio de ARRANQUE (28 jul 2026, investigacion de atencion):
    # edge-tts deja 100-300ms de silencio antes de la primera palabra. La
    # ventana de orientacion visual/auditiva es de ~100ms -- ese silencio
    # regala la ventana entera antes de que suene nada. Se recorta el audio Y
    # se restan los ms recortados a CADA timestamp de palabra, para que subs y
    # medios sigan sincronizados.
    lead_trimmed = out_dir / "voice_lead.mp3"
    try:
        run(["ffmpeg", "-y", "-i", str(mp3_path), "-af",
             "silenceremove=start_periods=1:start_silence=0.1:start_threshold=-45dB",
             str(lead_trimmed)])
        cut = ffprobe_duration(mp3_path) - ffprobe_duration(lead_trimmed)
        if 0 < cut < 1.0:  # guarda de sanidad: nunca recortar mas de 1s
            words = [(max(t - cut, 0.0), max(t2 - cut, 0.0), w) for t, t2, w in words]
            lead_trimmed.replace(mp3_path)
        else:
            lead_trimmed.unlink(missing_ok=True)
    except Exception as e:
        log("audio", f"trim de silencio inicial omitido: {e}")

    dur = ffprobe_duration(mp3_path)
    log("audio", f"{dur:.1f}s de audio, {len(words)} palabras")
    if dur > 58:
        log("audio", "AVISO: el audio supera 58s; el Short puede exceder 60s")
    return mp3_path, words


# ------------------------------------------------------------ 3. SUBTITLES

def _ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int(seconds % 3600 // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


SUB_LINE_CHARS = 14  # max chars por linea a fontsize 96 sin acercarse a los bordes
# Cuantas palabras se muestran juntas por bloque de karaoke (una resaltada, el
# resto en blanco). 1 = una palabra a la vez en pantalla, pedido explicito del
# usuario 30 jul 2026 sobre un checklist de edicion tipo Hormozi.
SUB_CHUNK_WORDS = 1
# Volumen lineal de la musica de fondo antes del sidechain-duck contra la voz.
# 0.09 ~= -20.9dB, dentro del rango -18/-22dB pedido explicitamente 30 jul
# 2026 (antes 0.06 ~= -24.4dB, mas bajo de lo pedido).
MUSIC_VOLUME = 0.09


def _split_index(tokens: list[str]) -> int:
    """Indice de token donde insertar el salto \\N para 2 lineas balanceadas;
    len(tokens) (sin salto, una sola linea) si todo cabe en SUB_LINE_CHARS.
    WrapStyle 2 no auto-envuelve, por eso el corte es explicito (feedback del
    usuario: los bloques largos se salian de pantalla)."""
    if len(" ".join(tokens)) <= SUB_LINE_CHARS or len(tokens) < 2:
        return len(tokens)
    best_i, best_diff = 1, float("inf")
    for i in range(1, len(tokens)):
        diff = abs(len(" ".join(tokens[:i])) - len(" ".join(tokens[i:])))
        if diff < best_diff:
            best_i, best_diff = i, diff
    return best_i


# Colores ASS (formato BBGGRR): palabra activa amarilla, resto blanco.
# La activa ademas hace un "pop" de escala: sube a 113% en 90ms y se sostiene
# mientras se pronuncia. El movimiento sobre la palabra hablada fija mas la
# mirada que solo el cambio de color -- clave con ~50% viendo en mute y para
# no-nativos (tecnica estandar de captions estilo TikTok). El reset devuelve las
# demas palabras a blanco y escala 100 para que el efecto no se arrastre.
_CAP_ACTIVE = r"{\c&H00FFFF&\fscx100\fscy100\t(0,90,\fscx113\fscy113)}"
_CAP_WHITE = r"{\c&HFFFFFF&\fscx100\fscy100}"

# Rojo para las palabras que cargan el dato (1 ago 2026). Con SUB_CHUNK_WORDS=1
# la palabra activa es la unica en pantalla, asi que el amarillo pasaba a ser el
# 100% del texto y dejaba de significar nada: si todo resalta, nada resalta.
# El rojo se reserva a las palabras de `caption_keywords`: verbos de accion y la
# palabra que gira la frase ("rebuilt", "typed", "unfinished"), no sustantivos de
# relleno. Objetivo ~5% del guion; pintar 40 palabras convierte el rojo en el
# nuevo amarillo y se pierde otra vez la jerarquia.
_CAP_RED = r"{\c&H2222DD&\fscx100\fscy100\t(0,90,\fscx118\fscy118)}"
_CAP_RED_IDLE = r"{\c&H2222DD&\fscx100\fscy100}"


# Cifras: van en rojo aunque el guion no las declare. Son las palabras que
# cargan el dato en casi todo guion del canal ("forty times", "eleven days") y
# asi el resalte funciona tambien en los guiones que genera Claude, donde no hay
# lista de keywords escrita a mano.
# ONE/TWO/THREE quedan FUERA a proposito: en ingles son relleno gramatical
# ("one of us", "not one", "thirty one") mucho mas que dato. Medido en el guion
# de las recetas, solas subian el resaltado del 7,7% al 10,6% sin aportar nada.
_AUTO_RED = {
    "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
    "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN",
    "EIGHTEEN", "NINETEEN", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY",
    "SEVENTY", "EIGHTY", "NINETY", "MILLION",
}


def _is_red(token: str, red_tokens: set[str]) -> bool:
    key = token.strip(".,;:!?\"'()-")
    return bool(key) and (key in red_tokens or key in _AUTO_RED or key.isdigit())


def _keyword_tokens(keywords: list[str] | None) -> set[str]:
    """Palabras sueltas en mayusculas y sin puntuacion, como salen en el .ass."""
    tokens: set[str] = set()
    for kw in keywords or []:
        for part in re.findall(r"[A-Za-z0-9']+", kw.upper()):
            tokens.add(part)
    return tokens


def generate_subtitles(words: list[tuple[float, float, str]], out_dir: Path,
                       lead_ms: int = 0, offset_ms: int = 0,
                       keywords: list[str] | None = None) -> Path:
    # Karaoke palabra-por-palabra: agrupa en bloques cortos (max 3 palabras / 18
    # chars, texto-como-imagen: lectura instantanea sin "leer" gramaticalmente)
    # para conservar contexto de 2 lineas, pero emite UN evento por palabra con
    # la activa resaltada en amarillo -- fija la mirada (clave con ~50% viendo
    # en mute) y sube la retencion en Shorts.
    if lead_ms:
        # adelanta el texto respecto al audio (test: el ojo "lee" el gancho antes
        # de que se oiga, aunque la mayoria vea en mute) -- no afecta el audio.
        lead = lead_ms / 1000
        words = [(max(ws - lead, 0.0), max(we - lead, 0.0), w) for ws, we, w in words]
    if offset_ms:
        # atrasa TODOS los subtitulos por igual -- usado por el modo card 'read':
        # se antepone un segmento de ~2.2s (frame congelado + premise card) antes
        # de que arranque la narracion, asi que los timestamps de las palabras
        # (que salen del audio de voz) hay que correrlos ese mismo tiempo para
        # que sigan sincronizados con la voz ya desplazada.
        off = offset_ms / 1000
        words = [(ws + off, we + off, w) for ws, we, w in words]

    red_tokens = _keyword_tokens(keywords)
    chunks: list[list[tuple[float, float, str]]] = []
    buf: list[tuple[float, float, str]] = []
    for w in words:
        buf.append(w)
        if len(buf) >= SUB_CHUNK_WORDS or len(" ".join(x[2] for x in buf)) >= 18:
            chunks.append(buf)
            buf = []
    if buf:
        chunks.append(buf)

    events = []
    for ci, chunk in enumerate(chunks):
        # fin de display del bloque: hasta el inicio del siguiente (anti-parpadeo)
        chunk_end = chunk[-1][1]
        if ci + 1 < len(chunks):
            chunk_end = max(chunk_end, chunks[ci + 1][0][0])
        tokens = [x[2].upper().replace("\\", "").replace("{", "").replace("}", "")
                  for x in chunk]
        split = _split_index(tokens)
        for wi, (ws, _we, _w) in enumerate(chunk):
            start = ws
            end = chunk[wi + 1][0] if wi + 1 < len(chunk) else chunk_end
            if end <= start:
                end = start + 0.05
            parts = []
            for j, t in enumerate(tokens):
                red = _is_red(t, red_tokens)
                if j == wi:
                    lead_tag = _CAP_RED if red else _CAP_ACTIVE
                    parts.append(f"{lead_tag}{t}{_CAP_WHITE}")
                elif red:
                    # la keyword se queda roja aunque no sea la activa: es lo que
                    # rompe el bloque monocolor cuando hay varias palabras a la vez
                    parts.append(f"{_CAP_RED_IDLE}{t}{_CAP_WHITE}")
                else:
                    parts.append(t)
            line1 = " ".join(parts[:split])
            line2 = " ".join(parts[split:])
            text = line1 + ("\\N" + line2 if line2 else "")
            events.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Cap,,0,0,0,,{text}")

    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Arial Black,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,2,60,60,960,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"

    ass_path = out_dir / "subs.ass"
    ass_path.write_text(ass, encoding="utf-8")
    log("subs", f"{len(events)} eventos karaoke ({len(chunks)} bloques)")
    return ass_path


# ---------------------------------------------------------------- 4. MEDIA

GRADIENTS = [
    ("0x0f2027", "0x2c5364"), ("0x1a2a6c", "0x3a6073"), ("0x232526", "0x414345"),
    ("0x141e30", "0x243b55"), ("0x2c3e50", "0x4ca1af"), ("0x000428", "0x004e92"),
]


def _gradient_clip(index: int, duration: float, path: Path) -> None:
    c0, c1 = GRADIENTS[index % len(GRADIENTS)]
    run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"gradients=s={WIDTH}x{HEIGHT}:d={duration:.2f}:c0={c0}:c1={c1}:speed=0.03:r={FPS}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        str(path),
    ])


# Palabras que aparecen en casi todo search_term ("close up hands ...") y
# matchearian con cualquier clip: no aportan senal para medir relevancia.
_PEXELS_STOPWORDS = {
    "the", "and", "with", "for", "from", "into", "onto", "over", "out",
    "close", "shot", "view", "video", "footage", "clip", "scene",
    "slowly", "slow", "detail", "person", "people", "someone",
}


def _pexels_relevance(term: str, video: dict) -> float:
    """Fraccion de palabras significativas del termino presentes en los metadatos
    del clip (slug de la URL + tags).

    Pexels NUNCA falla por una query sin sentido: siempre devuelve algo. Medido
    29 jul 2026, 'xzqvblorptronic nonexistent gibberish 9999' descargo un render
    3D abstracto y la funcion devolvia True como si hubiera acertado -- ese es el
    mecanismo real detras de "los clips no pegan con la historia". Esto no
    bloquea nada (el pipeline debe seguir fallando suave), solo hace visible en
    el log que el clip probablemente no corresponde al termino.
    """
    words = {w for w in re.findall(r"[a-z]+", term.lower())
             if len(w) > 2 and w not in _PEXELS_STOPWORDS}
    if not words:
        return 1.0  # nada verificable: no penalizar
    haystack = (video.get("url") or "").lower()
    haystack += " " + " ".join(str(t).lower() for t in (video.get("tags") or []))
    return sum(1 for w in words if w in haystack) / len(words)


def _apply_entry_zoom(path: Path) -> None:
    """Zoom-in rapido en el primer ~20% de frames de un clip de VIDEO (no
    imagen estatica). Misma curva que hook=True en _static_image_clip
    (+0.15 de zoom comprimido en el primer 20%, luego se asienta), pero
    aplicado sobre un clip ya grabado -- los de Pexels nunca pasan por
    zoompan porque _static_image_clip solo corre para imagenes generadas por
    IA. Sobrescribe el archivo in place; si falla, deja el clip como estaba
    (nunca bloquea el render por un efecto cosmetico)."""
    try:
        dur = ffprobe_duration(path)
    except Exception:
        return
    frames = max(int(round(dur * FPS)), 1)
    rush = max(int(frames * 0.2), 1)
    # OJO con zoompan sobre VIDEO: 'd' es cuantos frames de SALIDA genera por
    # cada frame de ENTRADA. En _static_image_clip la entrada es '-loop 1' con
    # UNA imagen, asi que d=frames da exactamente esa cantidad. Aqui la entrada
    # ya son N frames, asi que d debe ser 1 o el clip se multiplica por N
    # (probado 30 jul 2026: un clip de 35s no terminaba de renderizar nunca).
    # Con d=1 el contador 'on' avanza de a un frame, asi que sirve igual que en
    # el caso de imagen ('n' NO existe como variable en zoompan).
    zexpr = f"if(lt(on,{rush}),1.0+(0.15/{rush})*on,1.15)"
    tmp = path.with_name(path.stem + "_zoom" + path.suffix)
    try:
        run([
            "ffmpeg", "-y", "-i", str(path),
            # el fps= va ANTES de zoompan: los clips de Pexels vienen a 25fps y
            # zoompan solo DECLARA la tasa sin remuestrear, asi que sin esto un
            # clip de 4s salia de 3.33s (100 frames reproducidos a 30fps).
            "-vf", (f"fps={FPS},"
                    f"scale={WIDTH * 2}:{HEIGHT * 2}:force_original_aspect_ratio=increase,"
                    f"crop={WIDTH * 2}:{HEIGHT * 2},"
                    f"zoompan=z='{zexpr}':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1"),
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
            str(tmp),
        ])
        tmp.replace(path)
    except Exception as e:
        log("media", f"AVISO: zoom de entrada de escena 1 fallo ({type(e).__name__}: {e}), sigo sin el")
        tmp.unlink(missing_ok=True)


def _pexels_download(term: str, path: Path, api_key: str) -> bool:
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": term, "per_page": 5, "orientation": "portrait", "size": "medium"},
            headers={"Authorization": api_key},
            timeout=30,
        )
        r.raise_for_status()
        for video in r.json().get("videos", []):
            if video.get("duration", 0) < 4:
                continue
            files = [f for f in video.get("video_files", [])
                     if f.get("height", 0) >= 1280 and f.get("width", 0) <= f.get("height", 0)]
            if not files:
                continue
            best = min(files, key=lambda f: abs(f["height"] - HEIGHT))
            if _pexels_relevance(term, video) == 0:
                log("media", f"AVISO: el clip de Pexels para '{term}' no coincide con "
                             f"ninguna palabra del termino ({video.get('url', '?')}) -- "
                             f"revisa visualmente, puede ser metraje aleatorio")
            with requests.get(best["link"], stream=True, timeout=120) as dl:
                dl.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in dl.iter_content(1 << 16):
                        f.write(chunk)
            # Los metadatos de Pexels mienten: medido 29 jul 2026, el archivo
            # '7299471-hd_1080_1920_30fps.mp4' (width/height declarados 1080x1920,
            # y hasta el nombre lo dice) trae un stream real de 720x1280. Por eso
            # esto se comprueba sobre el archivo ya descargado, no sobre el JSON.
            real = ffprobe_resolution(path)
            if real and real[0] < WIDTH:
                log("media", f"AVISO: el clip para '{term}' es {real[0]}x{real[1]} real "
                             f"(Pexels declaraba {best.get('width')}x{best.get('height')}), "
                             f"por debajo de {WIDTH}x{HEIGHT} -- se reescalara hacia "
                             f"arriba y perdera nitidez")
            return True
    except Exception as e:
        log("media", f"Pexels fallo para '{term}': {e}")
    return False


# Neutral a proposito: NO fuerza "photo-realistic" porque eso arruina estilos
# especificos (ej. splash art de videojuegos). Cada prompt define su propio estilo.
# Guardrails de composicion: el personaje quedaba "lanzado"/descentrado en escenas
# de accion; esto fuerza encuadre estable sin perder la pose que pida la escena.
NANOBANANA_STYLE_SUFFIX = (
    ", vertical 9:16 portrait composition, character centered in frame and fully "
    "visible, stable and grounded pose appropriate to the scene (not falling, not "
    "tilted at a weird angle, not cropped at the edges), no text, no watermark, no logos"
    ", anatomically correct: exactly two arms and two hands per human figure, five "
    "fingers per hand, no extra or missing limbs, no distorted or merged body parts, "
    "no nonsensical objects"
    ", if a human figure's face is visible, eyes looking slightly toward the lower-"
    "center of frame (where captions appear), with rim light separating the subject "
    "silhouette from the background"
)

SKICK_REFERENCE = ROOT / "assets" / "skick" / "skick_reference.png"
LOL_CHAMPIONS_DIR = ROOT / "assets" / "lol_db" / "champions"


def _champion_references(term: str) -> list[Path]:
    """Detecta nombres de campeones de LoL mencionados en la escena y devuelve
    sus splash oficiales como referencia de fidelidad (mismo mecanismo que
    SKICK_REFERENCE, pero soporta VARIOS personajes en una misma escena --
    necesario para historias de lore con mas de un protagonista, ej. Yasuo
    y Yone en el mismo duelo)."""
    if not LOL_CHAMPIONS_DIR.exists():
        return []
    refs = []
    term_lower = term.lower()
    for splash in LOL_CHAMPIONS_DIR.glob("*_splash.jpg"):
        champ_id = splash.stem.replace("_splash", "")
        # \b no basta con ids que empiezan/terminan en caracter no-alfanumerico
        # (ninguno aqui), pero evita matches parciales dentro de otra palabra
        # (ej. "vi" dentro de "victorious", "sion" dentro de "vision", "nami"
        # dentro de "dynamic" -- visto en produccion, genero hojas de personaje
        # de sobra para campeones que no aparecian en el guion).
        if re.search(rf"\b{re.escape(champ_id.lower())}\b", term_lower):
            refs.append(splash)
    return refs


ROBLOX_SHEETS_DIR = ROOT / "assets" / "lol_db" / "roblox_sheets"


def _champion_id(splash: Path) -> str:
    return splash.stem.replace("_splash", "")


def _character_sheet_prompt(champ_id: str, style_directive: str) -> str:
    return (
        f"A Roblox game character reference sheet for a custom avatar based on "
        f"{champ_id.title()} from League of Legends. Show the SAME avatar three "
        "times side by side on a plain neutral gray background: front view, "
        "3/4 view, and side view, all in a neutral standing pose with arms "
        "relaxed. This is a character turnaround sheet, not a scene -- no "
        "background environment, no props, no action. "
        f"MANDATORY ART STYLE: {style_directive}. Blocky cylinder/box limbs, "
        "simple flat face, voxel proportions, cel-shaded Roblox game aesthetic "
        "applied identically to all three views. Keep the character's identity "
        "(hair, face markings, outfit colors, weapon, silhouette) clearly "
        "recognizable from the reference image but fully rebuilt in Roblox "
        "blocks -- ignore the reference image's painted art style completely. "
        "Vertical 9:16, no text, no labels."
    )


CHARACTERS_DIR = ROOT / "assets" / "characters"
CHARACTERS_MANIFEST = CHARACTERS_DIR / "manifest.json"
# palabras que marcan una FASE distinta del mismo personaje (ej. Viego rey vs
# Viego fantasma) -- si ninguna aparece en la escena, se usa la fase "default"
PHASE_KEYWORDS = ["ghost", "spectral", "skeletal", "phantom", "undead", "ruined",
                  "child", "young", "prisoner", "warden", "possessed", "corrupted"]

_CHARACTER_PATTERN = re.compile(r"^([A-Za-zÀ-ÿ][\w' -]*?) character:", re.IGNORECASE)


def _detect_named_character(term: str) -> tuple[str, str] | None:
    """Detecta el patron '<Nombre> character: ...' al inicio de un search_term
    (convencion ya usada para Skick, generalizada a cualquier personaje
    recurrente -- campeones de lore, figuras historicas de HiddenFacts,
    secundarios de sketches). Devuelve (nombre, fase) o None si no aplica.
    La fase es la primera palabra de PHASE_KEYWORDS que aparece en el texto,
    o 'default' si el personaje aparece en su forma base."""
    m = _CHARACTER_PATTERN.match(term.strip())
    if not m:
        return None
    name = m.group(1).strip()
    term_lower = term.lower()
    phase = next((kw for kw in PHASE_KEYWORDS if kw in term_lower), "default")
    return name, phase


def _character_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _load_characters_manifest() -> dict:
    return _load_json(CHARACTERS_MANIFEST, {})


def _save_characters_manifest(data: dict) -> None:
    _atomic_write_json(CHARACTERS_MANIFEST, data)


def _get_named_character_sheet(name: str, phase: str, style_directive: str,
                                api_key: str, seed_term: str, api_key_style_id: str = "") -> Path | None:
    """Hoja de personaje PERSISTENTE (entre videos, no solo dentro de una
    corrida) para cualquier personaje recurrente -- marca personal reconocible
    en ambos canales. Primera vez que aparece un personaje/fase: se genera y
    se guarda en assets/characters/<slug>/<fase>_<estilo>.png + se registra en
    manifest.json. Veces siguientes (mismo video u otro futuro): se reusa tal
    cual, igual que ya pasa con los campeones de LoL (ver _get_character_sheet)."""
    slug = _character_slug(name)
    char_dir = CHARACTERS_DIR / slug
    char_dir.mkdir(parents=True, exist_ok=True)
    style_key = re.sub(r"[^a-z0-9]+", "-", style_directive.lower())[:40]
    sheet_path = char_dir / f"{phase}_{style_key}.png"

    manifest = _load_characters_manifest()
    entry = manifest.setdefault(slug, {"name": name, "phases": {}})

    if sheet_path.exists():
        log("media", f"personaje '{name}' fase '{phase}': reusando de base de datos")
        return sheet_path

    # Skick ya tenia una referencia fija de antes de esta base de datos
    # generica (assets/skick/skick_reference.png) -- sembrar la fase default
    # con esa imagen en vez de generar una nueva, para no crear una segunda
    # version distinta del personaje ya establecido
    if slug == "skick" and phase == "default" and SKICK_REFERENCE.exists():
        import shutil
        shutil.copyfile(SKICK_REFERENCE, sheet_path)
        entry["phases"][f"{phase}_{style_key}"] = sheet_path.name
        manifest[slug] = entry
        _save_characters_manifest(manifest)
        log("media", f"personaje 'Skick' fase 'default': sembrado desde la referencia original")
        return sheet_path

    # si ya existe la fase "default" de este personaje, la usamos como
    # referencia de identidad para que la fase nueva (ej. fantasma) mantenga
    # la misma cara/silueta reconocible en vez de reinventar al personaje
    default_key = f"default_{style_key}"
    seed_ref = None
    if phase != "default" and default_key in entry["phases"]:
        candidate = char_dir / f"{entry['phases'][default_key]}"
        if candidate.exists():
            seed_ref = candidate

    log("media", f"generando hoja de personaje NUEVA para '{name}' fase '{phase}' "
                  "(se guarda para siempre, se reusa en todos los videos futuros)...")
    prompt = (
        f"A character reference sheet/turnaround for '{name}', shown three times "
        "side by side on a plain neutral background: front view, 3/4 view, and "
        "side view, same pose, arms relaxed, no action, no props, no environment. "
        f"MANDATORY ART STYLE: {style_directive}. "
        f"Character description/context: {seed_term}. "
        "Keep the identity (face, outfit, colors, silhouette) clearly consistent "
        "across the three views. Vertical 9:16, no text, no labels."
    )
    ok = _seedream_generate_image(prompt, sheet_path, api_key, reference_image=seed_ref, attempts=3)
    if not ok:
        return None
    entry["phases"][f"{phase}_{style_key}"] = sheet_path.name
    manifest[slug] = entry
    _save_characters_manifest(manifest)
    return sheet_path


def _get_character_sheet(splash: Path, style_directive: str, api_key: str) -> Path | None:
    """Genera (o reutiliza) una 'hoja de personaje' Roblox: el mismo avatar en 3
    poses fijas sobre fondo neutro, generada UNA vez por campeon+estilo y cacheada
    en disco. Usarla como referencia (en vez del splash pintado original) mantiene
    consistente el diseño del personaje entre escenas y evita que el modelo copie
    el estilo pintado del splash en escenas atmosfericas (ver memoria
    estilo-roblox-nanobanana, escrita cuando el generador era Nano Banana)."""
    ROBLOX_SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    champ_id = _champion_id(splash)
    cache_key = re.sub(r"[^a-z0-9]+", "-", style_directive.lower())[:40]
    sheet_path = ROBLOX_SHEETS_DIR / f"{champ_id}_{cache_key}.png"
    if sheet_path.exists():
        log("media", f"hoja de personaje '{champ_id}': reusando cache")
        return sheet_path

    log("media", f"generando hoja de personaje para '{champ_id}' (una vez, se reusa en todas las escenas)...")
    prompt = _character_sheet_prompt(champ_id, style_directive)
    ok = _seedream_generate_image(prompt, sheet_path, api_key, reference_image=splash, attempts=3)
    return sheet_path if ok else None




def _piapi_upload_temp(image_path: Path, api_key: str) -> str:
    """Sube un archivo local al endpoint efimero de PiAPI (se borra solo a las 24h)
    y devuelve una URL publica -- Seedream (via PiAPI) solo acepta image_urls, no
    base64 directo."""
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    r = requests.post(
        "https://upload.theapi.app/api/ephemeral_resource",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={"file_name": image_path.name, "file_data": b64},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("data", {}).get("url") or data["url"]


def _seedream_generate_image(prompt: str, path: Path, api_key: str,
                              reference_image: Path | None = None,
                              reference_images: list[Path] | None = None,
                              style_directive: str | None = None,
                              attempts: int = 2) -> bool:
    """Generador de imagenes del pipeline: Seedream (ByteDance) via PiAPI -- mejor
    consistencia de personaje multi-referencia segun benchmarks (ver
    investigacion 19 jul 2026). Es el UNICO generador de imagenes del pipeline
    desde el 3 ago 2026 (ver nota de la eliminacion de Gemini arriba). image_urls debe ser URL publica,
    por eso cada referencia se sube primero al endpoint efimero de PiAPI."""
    all_refs = ([reference_image] if reference_image else []) + (reference_images or [])
    all_refs = [r for r in all_refs if r]
    full_prompt = prompt + NANOBANANA_STYLE_SUFFIX
    if style_directive:
        full_prompt = (f"CRITICAL: apply this exact art style to the ENTIRE frame, "
                        f"overriding any style in the reference images: {style_directive}. "
                        f"{full_prompt}")

    for attempt in range(attempts):
        try:
            image_urls = [_piapi_upload_temp(ref, api_key) for ref in all_refs]
            payload = {
                "model": "seedream",
                "task_type": "seedream-5-lite",
                "input": {
                    "prompt": full_prompt,
                    "aspect_ratio": "9:16",
                    "output_format": "png",
                },
            }
            if image_urls:
                payload["input"]["image_urls"] = image_urls
            r = requests.post(
                "https://api.piapi.ai/api/v1/task",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                json=payload, timeout=60,
            )
            r.raise_for_status()
            task_id = r.json()["data"]["task_id"]

            for _ in range(60):  # hasta 2 min de polling (2s por intento)
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
                    path.write_bytes(img_resp.content)
                    return True
                if status in ("failed", "error"):
                    raise RuntimeError(task.get("error", "tarea fallo sin detalle"))
            raise RuntimeError("timeout esperando la tarea de Seedream")
        except Exception as e:
            if attempt < attempts - 1:
                log("media", f"Seedream fallo (intento {attempt + 1}), reintento en 5s: {e}")
                time.sleep(5)
            else:
                log("media", f"Seedream fallo para '{prompt[:60]}...': {e}")
    return False


def _static_image_clip(image_path: Path, duration: float, path: Path, zoom_in: bool = True,
                        punch: bool = False, hook: bool = False, static: bool = False,
                        hook_strong: bool = False, move: int = 0) -> None:
    """Convierte una imagen fija en un clip con efecto Ken Burns (zoom lento, gratis).
    move: indice de escena -- rota entre 6 movimientos distintos (zoom-in/out
    centrado + 4 paneos direccionales) para que dos escenas seguidas nunca se
    sientan clonadas. Antes solo alternaba zoom-in/zoom-out, ambos centrados, y
    todas las escenas se percibian iguales (feedback visual 22 jul 2026). El
    parametro zoom_in quedo obsoleto (lo reemplaza 'move'); se mantiene por
    compatibilidad de firma pero ya no se usa en el modo normal.
    punch=True: quieto los primeros ~60% y zoom rapido "golpe" el resto -- usar
    en la escena del remate/giro comico para dar un acento visual.
    hook=True: golpe de entrada -- zoom-in rapido en el primer ~20% y luego se
    asienta, para ganar la decision de swipe del primer segundo en la escena 1
    (la palanca #1 de retencion en Shorts).
    hook_strong=True: version mas agresiva del golpe de entrada (bajo --hook-max)
    -- +0.25 de zoom comprimido en el primer ~12% de frames; mas movimiento en el
    frame 0, que es lo que el sistema reticular detecta antes que el contenido.
    static=True: sin ningun movimiento (modo caption -- la imagen ya comparte
    el frame con texto fijo, el zoom se sentia inconsistente con esa quietud)."""
    frames = max(int(round(duration * FPS)), 1)
    # x/y por defecto: ventana de recorte centrada (comportamiento clasico).
    # Los paneos la desplazan; usan zoom FIJO porque con zoom bajo (~1.0) no hay
    # "slack" para moverse sin mostrar borde negro -- a z=1.12 el rango valido de
    # x/y es [0, 0.107*iw] con centro en 0.054*iw, asi que un offset de +/-0.04*iw
    # se queda siempre dentro del recorte.
    xexpr = "iw/2-(iw/zoom/2)"
    yexpr = "ih/2-(ih/zoom/2)"
    if static:
        zexpr = "1.0"
    elif hook and hook_strong:
        rush = max(int(frames * 0.12), 1)
        zexpr = f"if(lt(on,{rush}),1.0+(0.25/{rush})*on,1.25)"
    elif hook:
        rush = max(int(frames * 0.2), 1)
        zexpr = f"if(lt(on,{rush}),1.0+(0.15/{rush})*on,1.15)"
    elif punch:
        hold = max(int(frames * 0.6), 1)
        zexpr = f"if(lt(on,{hold}),1.0,min(1.0+0.045*(on-{hold}),1.35))"
    else:
        # progreso lineal -1 -> +1 a lo largo del clip, para los paneos
        prog = f"((2*on/{frames})-1)"
        variant = move % 6
        if variant == 0:      # zoom-in centrado
            zexpr = "min(zoom+0.0015,1.18)"
        elif variant == 1:    # zoom-out centrado
            zexpr = "if(eq(on,1),1.18,max(zoom-0.0015,1.0))"
        elif variant == 2:    # paneo izquierda -> derecha (zoom fijo)
            zexpr = "1.12"
            xexpr = f"iw/2-(iw/zoom/2)+(iw*0.04)*{prog}"
        elif variant == 3:    # paneo derecha -> izquierda
            zexpr = "1.12"
            xexpr = f"iw/2-(iw/zoom/2)-(iw*0.04)*{prog}"
        elif variant == 4:    # paneo arriba -> abajo (zoom fijo)
            zexpr = "1.12"
            yexpr = f"ih/2-(ih/zoom/2)+(ih*0.04)*{prog}"
        else:                 # paneo abajo -> arriba
            zexpr = "1.12"
            yexpr = f"ih/2-(ih/zoom/2)-(ih*0.04)*{prog}"
    vf = (
        f"scale={WIDTH * 2}:{HEIGHT * 2}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='{zexpr}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}:"
        f"x='{xexpr}':y='{yexpr}',setsar=1"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-t", f"{duration:.2f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        str(path),
    ])


def _scene_boundaries(words: list[tuple[float, float, str]], n_clips: int,
                       audio_dur: float) -> list[float]:
    """Duracion de cada escena de modo que los cortes caigan en FIN DE FRASE
    (palabra terminada en ./!/?) en vez de en puntos equidistantes -- antes la
    imagen cambiaba a mitad de frase y se percibia como desfase voz/imagen
    (feedback del usuario). Para cada corte ideal (i*dur/n) se elige el fin de
    frase mas cercano; si una frase abarca varios cortes se cae al fin de
    palabra mas cercano para no dejar escenas vacias."""
    sentence_ends = [w[1] for w in words if w[2].rstrip('"\')').endswith((".", "!", "?", "…"))]
    word_ends = [w[1] for w in words]
    cuts: list[float] = []
    prev = 0.0
    for i in range(1, n_clips):
        ideal = audio_dur * i / n_clips
        # candidatos posteriores al corte anterior Y anteriores al final del
        # audio (margen 0.5s en ambos lados) -- sin el limite superior, la
        # ULTIMA palabra del guion (que tambien termina en '.') se colaba como
        # candidato y un corte interno terminaba clavado en audio_dur, dejando
        # escenas de duracion 0 al final (visto en produccion con guiones
        # cortos / pocas frases).
        cands = [t for t in sentence_ends if prev + 0.5 < t < audio_dur - 0.5] or \
                [t for t in word_ends if prev + 0.5 < t < audio_dur - 0.5]
        if cands:
            cut = min(cands, key=lambda t: abs(t - ideal))
        else:
            # sin mas palabras/frases disponibles (guion corto, muchas escenas):
            # repartir el tiempo restante en partes iguales para las escenas
            # que faltan, garantizando avance monotono (visto en produccion:
            # el fallback anterior podia devolver un corte ANTERIOR a 'prev'
            # y generar una duracion negativa de escena)
            remaining_clips = n_clips - i + 1
            cut = prev + (audio_dur - prev) / remaining_clips
        cuts.append(cut)
        prev = cut
    bounds = [0.0] + cuts + [audio_dur]
    return [bounds[i + 1] - bounds[i] for i in range(n_clips)]


def acquire_media(search_terms: list[str], n_clips: int, durations: list[float],
                  out_dir: Path, media_source: str,
                  punch_index: int | None = None, style: str | None = None,
                  static: bool = False, hook_strong: bool = False,
                  wan_hero_path: Path | None = None,
                  character_terms: list[str] | None = None) -> list[Path]:
    """media_source: 'seedream' | 'pexels' | 'gradient'. Siempre cae a gradiente si falla.
    punch_index: escena que recibe el zoom "golpe" (quieta y luego zoom rapido) para
    acentuar el remate/giro comico -- por defecto la penultima escena (ver
    RETENCION_PSICOLOGIA.md, feedback "falta energia visual").
    style: estilo de arte obligatorio para TODAS las escenas (campo "style" del
    guion JSON) -- ej. 'Roblox blocky voxel avatars and environments'."""
    if punch_index is None:
        punch_index = max(n_clips - 2, 0)
    clips_dir = out_dir / "clips"
    clips_dir.mkdir(exist_ok=True)
    pexels_key = os.getenv("PEXELS_API_KEY", "")
    piapi_key = os.getenv("PIAPI_API_KEY", "")
    clips: list[Path] = []


    terms = (search_terms * ((n_clips // max(len(search_terms), 1)) + 1))[:n_clips]
    # character_terms viaja en paralelo a search_terms y se recicla igual, para
    # que escena i y personaje i sigan emparejados tras el recorte a n_clips
    _ct = list(character_terms or [])
    char_terms = ((_ct * ((n_clips // max(len(_ct), 1)) + 1))[:n_clips]) if _ct else []

    # Con estilo (ej. Roblox) generamos primero una hoja de personaje por cada
    # campeon mencionado en CUALQUIER escena, una sola vez, y la reusamos como
    # referencia en todas las escenas -- evita que el diseño del personaje
    # varie entre escenas y que el modelo copie el estilo pintado del splash
    # (ver memoria estilo-roblox-nanobanana, escrita cuando el generador era Nano Banana).
    sheet_cache: dict[str, Path] = {}
    named_char_cache: dict[tuple[str, str], Path] = {}
    if media_source in ("seedream", "comfy") and (piapi_key or media_source == "comfy") and style:
        all_splashes = {s for t in search_terms for s in _champion_references(t)}
        for splash in all_splashes:
            sheet = _get_character_sheet(splash, style, piapi_key)
            if sheet:
                sheet_cache[_champion_id(splash)] = sheet

        # base de datos de personajes recurrentes (marca personal, ver
        # convencion '<Nombre> character: ...' generalizada de Skick) --
        # persistente entre videos via assets/characters/manifest.json
        for t in search_terms:
            detected = _detect_named_character(t)
            if detected:
                name, phase = detected
                if (name, phase) not in named_char_cache:
                    sheet = _get_named_character_sheet(name, phase, style, piapi_key, seed_term=t)
                    if sheet:
                        named_char_cache[(name, phase)] = sheet

    return _acquire_clips_loop(terms, n_clips, durations, clips_dir, media_source,
                                punch_index, style, static, hook_strong,
                                wan_hero_path, piapi_key, pexels_key,
                                sheet_cache, named_char_cache, char_terms=char_terms)


def _acquire_clips_loop(terms, n_clips, durations, clips_dir, media_source,
                         punch_index, style, static, hook_strong,
                         wan_hero_path, piapi_key, pexels_key,
                         sheet_cache, named_char_cache, char_terms=None) -> list[Path]:
    clips: list[Path] = []
    char_terms = list(char_terms or [])
    for i, term in enumerate(terms):
        raw = clips_dir / f"raw_{i}.mp4"
        got = False

        if i == 0 and wan_hero_path is not None:
            # hero local (Wan 2.2 via ComfyUI, gratis): solo la escena 0, para
            # maxima retencion (ver plan de gancho + ComfyUI local).
            run(["ffmpeg", "-y", "-i", str(wan_hero_path),
                 "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                        f"crop={WIDTH}:{HEIGHT},setsar=1",
                 "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                 "-pix_fmt", "yuv420p", str(raw)])
            got = True
            log("media", f"clip 1/{n_clips}: hero local Wan 2.2 OK")

        if not got and (media_source == "comfy" or (media_source == "seedream" and piapi_key)):
            img_path = clips_dir / f"nb_{i}.png"
            detected = _detect_named_character(term)
            if detected and detected in named_char_cache:
                char_ref = named_char_cache[detected]
            elif "skick" in term.lower():
                char_ref = SKICK_REFERENCE  # fallback si el guion no usa 'Skick character:'
            else:
                char_ref = None
            raw_champ_refs = _champion_references(term)
            if sheet_cache:
                champ_refs = [sheet_cache.get(_champion_id(s), s) for s in raw_champ_refs]
            else:
                champ_refs = raw_champ_refs
            # DOS PLACAS: el fondo se pide vacio y el personaje aparte, en pose
            # de A sobre blanco. La escena 0 queda fuera a proposito -- es un
            # primer plano de cara que el motor clava como foto, no troquela.
            # Un character_term VACIO es una orden, no un hueco (28 jul 2026).
            # Si el guion trae la lista, "" significa "esta escena NO lleva
            # personaje" y se respeta. Antes caia al derivador por regex, que
            # sacaba una figura igualmente: la escena de cierre del bucle salio
            # como sticker recortado en vez de la misma foto de la escena 1, y
            # el empalme final->inicio dejo de existir.
            explicit = i < len(char_terms)
            raw_char = (char_terms[i] if explicit else None) or None
            if i == 0:
                bg_term, plate_term = term, None
            elif explicit and not raw_char:
                bg_term, plate_term = term, None
            else:
                bg_term, plate_term = _plate_terms(term, raw_char)
            gen_term = bg_term
            if i == 0:
                # pattern interrupt (segundo 0-1): encuadre inesperado que rompe lo
                # "familiar" del feed antes de que el pulgar decida seguir scrolleando
                gen_term += (", unexpected framing: extreme low angle or dramatically "
                             "disproportionate scale between subject and surroundings")
            elif i % 2 == 1:
                # movimiento organico (humo/polvo/tela) alternado con el Ken Burns
                # mecanico -- el ojo sigue mucho mas el movimiento fluido/organico
                # que el zoom rigido (percepcion de movimiento biologico)
                gen_term += (", include drifting smoke, dust, mist, or fabric/hair "
                             "moving gently in the scene")
            # Dos generadores desde el 3 ago 2026: Seedream (PiAPI, de pago) y
            # ComfyUI local (gratis, sin limite, ver comfy_client.py). No hay
            # respaldo cruzado automatico: si el elegido falla, la escena cae al
            # gradiente, y con todas en gradiente el motor Archivo/KoreX se queda
            # sin nb_*.png y no puede renderizar.
            if media_source == "comfy":
                import comfy_client
                gen_fn, gen_key = comfy_client.generate_image, ""
            else:
                gen_fn, gen_key = _seedream_generate_image, piapi_key
            # CACHE DE ESCENAS GENERICAS: una escena sin nombres propios ni fechas
            # sirve igual en cualquier video -> se genera una vez y se reusa (cero
            # llamada de imagen). Las escenas con personaje de referencia quedan
            # fuera: dependen del sheet, no son intercambiables.
            gen_ok = False
            cache_hit = None
            if not char_ref and not champ_refs:
                try:
                    from visual_cache import scene_cache_lookup, scene_cache_store
                    cache_hit = scene_cache_lookup(gen_term, style)
                except Exception:
                    cache_hit = None
            if cache_hit:
                shutil.copyfile(cache_hit, img_path)
                gen_ok = True
                log("media", f"clip {i + 1}/{n_clips}: escena cacheada (sin coste de API)")
            else:
                gen_ok = gen_fn(gen_term, img_path, gen_key, reference_image=char_ref,
                                reference_images=champ_refs, style_directive=style)
                if gen_ok and not char_ref and not champ_refs:
                    try:
                        scene_cache_store(gen_term, style, img_path)
                    except Exception:
                        pass
            # PLACA DE PERSONAJE: imagen aparte, misma escena. El motor la
            # troquela contra blanco (donde BiRefNet no falla) y la compone
            # sobre la placa de fondo. Si falla, la escena sigue siendo valida:
            # queda el fondo vacio como foto clavada, nunca bloquea el render.
            if gen_ok and plate_term:
                ch_path = clips_dir / f"ch_{i}.png"
                # PLATE_STYLE prohibe "animales antropomorficos" para que el
                # fondo/multitud de HiddenFacts nunca derive en un animal por
                # accidente. Con char_ref (personaje con hoja de referencia
                # propia, ej. Tadeo el mapache) ese texto contradice la imagen
                # de referencia y el modelo empieza a titubear entre las dos --
                # se retira solo en ese caso, nunca para figuras sin referencia.
                plate_style = (PLATE_STYLE.replace(
                    " Only human characters, never humanoid animals.", "")
                    if char_ref else PLATE_STYLE)
                ch_prompt = f"{plate_term}. {CHARACTER_PLATE}"
                ch_hit = None
                try:
                    from visual_cache import scene_cache_lookup, scene_cache_store
                    ch_hit = scene_cache_lookup(ch_prompt, PLATE_STYLE)
                except Exception:
                    ch_hit = None
                if ch_hit:
                    shutil.copyfile(ch_hit, ch_path)
                    log("media", f"clip {i + 1}/{n_clips}: personaje cacheado '{plate_term[:40]}'")
                else:
                    ch_ok = gen_fn(ch_prompt, ch_path, gen_key, reference_image=char_ref,
                                   reference_images=champ_refs, style_directive=plate_style)
                    if not ch_ok and alt_key:
                        ch_ok = alt_fn(ch_prompt, ch_path, alt_key, reference_image=char_ref,
                                       reference_images=champ_refs, style_directive=plate_style)
                    if ch_ok:
                        log("media", f"clip {i + 1}/{n_clips}: placa personaje '{plate_term[:40]}'")
                        if not char_ref and not champ_refs:
                            try:
                                scene_cache_store(ch_prompt, PLATE_STYLE, ch_path)
                            except Exception:
                                pass
                    else:
                        ch_path.unlink(missing_ok=True)
                        log("media", f"clip {i + 1}/{n_clips}: placa personaje fallo, solo fondo")
            if gen_ok:
                if not got:
                    _static_image_clip(img_path, durations[i] + 1.0, raw, move=i,
                                        punch=(i == punch_index), hook=(i == 0), static=static,
                                        hook_strong=hook_strong)
                    got = True
                    log("media", f"clip {i + 1}/{n_clips}: {media_source} '{term}'")
        elif media_source == "pexels" and pexels_key:
            got = _pexels_download(term, raw, pexels_key)
            if got:
                log("media", f"clip {i + 1}/{n_clips}: Pexels '{term}'")
                if i == 0:
                    # Los clips de Pexels nunca pasan por _static_image_clip (esa
                    # funcion solo corre para imagenes generadas por IA), asi que
                    # el zoom de entrada de la escena 1 -- la palanca #1 de
                    # retencion en Shorts -- nunca se aplicaba en el camino que
                    # de verdad usamos. Detectado 30 jul 2026 auditando un
                    # checklist externo.
                    _apply_entry_zoom(raw)

        if not got:
            log("media", f"clip {i + 1}/{n_clips}: gradiente (fallback)")
            _gradient_clip(i, durations[i] + 1.0, raw)
        clips.append(raw)
    return clips


SFX_DIR = ROOT / "assets" / "sfx"

# Capa OPCIONAL (--sticker-sfx) de sonido de ENTRADA de sticker: un swish de
# papel suave en el frame exacto en que el sticker hace pop. NO es SFX diegetico
# (no describe un evento de la narracion) -- es el "sonido del collage armandose",
# motivado por la estetica de recortes de papel que ya usan los stickers
# (tarjeta beige + borde de tinta + flecha dibujada a mano). Reglas para que no
# se sienta "puesto por ponerlo": UN solo sonido consistente (firma del canal),
# volumen bajo bajo la narracion, y se OMITE entero si el tono del video es
# sombrio. Capa separada de pick_sfx_cues (que sigue siendo 100% diegetico).
STICKER_SFX_DEFAULT = "Paper___book_ManualTurnPage_AP1.1244.mp3"  # swish de papel, 0.58s
STICKER_SFX_VOLUME = 0.16
_SOMBER_TONE_WORDS = ("sad", "tragic", "mournful", "grief", "sorrow", "solemn",
                       "melancholy", "funeral", "elegy", "lament", "somber", "sombre",
                       "requiem", "heartbreaking")


def _list_sfx() -> list[Path]:
    if not SFX_DIR.exists():
        return []
    return [p for p in SFX_DIR.iterdir()
            if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")]


def _load_sfx_manifest() -> dict:
    """assets/sfx/manifest.json: descripcion de que suena en cada archivo y
    que conceptos del guion lo justifican. Sin manifest, dict vacio."""
    path = SFX_DIR / "manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("sfx", {})
    except Exception:
        return {}


def pick_sfx_cues(words: list[tuple[float, float, str]],
                   tone: str | None = None,
                   script: str | None = None,
                   search_terms: list[str] | None = None) -> list[tuple[float, Path, str]]:
    """Usa Claude para colocar SFX SOLO donde la narracion describe literalmente
    el evento sonoro (espada, trueno, golpe...) -- feedback del usuario: los
    efectos 'decorativos' parecen puestos por ponerlos. Cada cue debe citar la
    palabra disparadora (trigger_word, validada contra la palabra real del
    guion). Recibe el guion completo con puntuacion, el manifest de que suena
    en cada archivo, y los search_terms (que se VE en cada escena). Max 4 cues;
    0 es una respuesta valida. Sin API key o sin efectos, lista vacia."""
    sfx_files = _list_sfx()
    if not sfx_files or not os.getenv("ANTHROPIC_API_KEY"):
        return []

    schema = {
        "type": "object",
        "properties": {
            "cues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "word_index": {"type": "integer"},
                        "sfx_file": {"type": "string"},
                        "trigger_word": {"type": "string",
                                          "description": "la palabra EXACTA del guion (en word_index o adyacente) que describe el evento sonoro"},
                    },
                    "required": ["word_index", "sfx_file", "trigger_word"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["cues"],
        "additionalProperties": False,
    }
    word_list = [w[2] for w in words]
    manifest = _load_sfx_manifest()
    catalog = {f.name: manifest.get(f.name, {"suena_como": f.stem}) for f in sfx_files}
    tone_line = f"\nTono/musica de este video: {tone!r}\n" if tone else ""
    script_line = f"\nGuion completo (con puntuacion):\n{script}\n" if script else ""
    scenes_line = (f"\nQue se VE en pantalla en cada escena (en orden):\n"
                   f"{json.dumps(search_terms, ensure_ascii=False)}\n") if search_terms else ""
    prompt = (
        "Eres editor de sonido para Shorts de gaming. Tu regla es de DISENO DE "
        "SONIDO DIEGETICO: un efecto solo puede sonar si la narracion en ese punto "
        "DESCRIBE LITERALMENTE el evento que produce ese sonido (se menciona una "
        "espada -> puede sonar una espada; se menciona un golpe/caida -> impacto; "
        "trueno/tormenta -> trueno). NUNCA coloques un efecto 'para dar energia' o "
        "'de ambientacion' si la palabra narrada en ese momento no describe el "
        "evento: eso se percibe como puesto por ponerlo, y es exactamente lo que "
        "hay que evitar.\n\n"
        "Para cada cue devuelve trigger_word: la palabra EXACTA del guion (la de "
        "word_index o una inmediatamente adyacente) que describe el evento sonoro. "
        "Si no puedes citar una palabra concreta que lo justifique, NO pongas el cue.\n\n"
        "Ademas: (1) el efecto debe cuadrar con el tono del momento (nada comico/"
        "cartoon en un momento triste o dramatico, nada dramatico en un gag); "
        "(2) el efecto tambien debe ser coherente con lo que se VE en la escena "
        "activa en ese momento; (3) maximo 4 cues y minimo 4 palabras de distancia "
        "entre cues; (4) devolver 0 cues es una respuesta correcta si el guion no "
        "narra eventos sonoros.\n"
        f"{tone_line}{script_line}{scenes_line}\n"
        f"Palabras con su indice 0-based (usa el indice de la palabra exacta donde "
        f"debe sonar): {json.dumps(word_list, ensure_ascii=False)}\n\n"
        f"Catalogo de efectos (nombre EXACTO de archivo -> que suena y cuando usarlo): "
        f"{json.dumps(catalog, ensure_ascii=False)}"
    )
    # max_tokens generoso: con thinking adaptive a veces el presupuesto se
    # consume pensando y no deja espacio para el bloque de texto final --
    # _claude_json_call ya convierte eso en un RuntimeError legible en vez
    # de la StopIteration silenciosa que habia antes.
    try:
        data = with_retries(_claude_json_call, 4000, schema, prompt, attempts=2, delay=3.0)
    except Exception as e:
        log("sfx", f"Seleccion de SFX fallo: {type(e).__name__}: {e}")
        return []

    def _norm(w: str) -> str:
        return re.sub(r"[^\wáéíóúñü]", "", w.lower())

    name_to_path = {f.name: f for f in sfx_files}
    cues = []
    for cue in data.get("cues", []):
        idx = cue.get("word_index", -1)
        fname = cue.get("sfx_file", "")
        trigger = cue.get("trigger_word", "")
        if not (0 <= idx < len(words) and fname in name_to_path):
            continue
        # el trigger_word debe ser una palabra REAL del guion en word_index o
        # inmediatamente adyacente -- descarta cues decorativos inventados
        window = [_norm(words[j][2]) for j in range(max(0, idx - 1), min(len(words), idx + 2))]
        if _norm(trigger) not in window:
            log("sfx", f"cue descartado: '{trigger}' no esta junto a la palabra {idx} "
                        f"('{words[idx][2]}')")
            continue
        cues.append((words[idx][0], name_to_path[fname], trigger))
        log("sfx", f"  {words[idx][0]:6.2f}s  {fname}  <- '{trigger}'")
    cues.sort(key=lambda c: c[0])
    cues = cues[:4]  # tope duro (la API no soporta maxItems en el schema)
    log("sfx", f"{len(cues)} efectos de sonido colocados (regla: solo eventos narrados)")
    return cues


# ------------------------------------------------------------- 5. ASSEMBLY

def assemble(clips: list[Path], audio: Path, ass_path: Path, out_dir: Path,
             music_mood: str | None = None,
             sfx_cues: list[tuple[float, Path]] | None = None,
             durations: list[float] | None = None,
             watermark: str | None = "ImPixxel",
             cta_text: str | None = None,
             cta_position: str | None = None,
             intro_stinger: bool = False,
             split_first_clip: bool = False,
             caption_header: str | None = None,
             caption_text: str | None = None,
             caption_keywords: list[str] | None = None,
             hook_card: str | None = None,
             hook_card_mode: str = "overlay",
             hook_punch: bool = False) -> Path:
    """durations: duracion por escena (de _scene_boundaries, cortes en fin de
    frase). Sin ella, reparto uniforme (comportamiento anterior).
    hook_card: premisa en pantalla (~2.2s, alto contraste, curiosity gap) al
    inicio. hook_card_mode: 'overlay' (se superpone mientras ya narra desde t=0)
    o 'read' (beat de lectura primero: frame congelado 2.2s con solo musica/
    stinger, la narracion arranca despues). En modo 'read' el audio de voz debe
    llegar YA desplazado card_dur (la voz se retrasa con adelay aca) y los subs
    tambien (se generan con offset_ms en main). card_dur fijo = 2.2s."""
    HOOK_CARD_DUR = 2.2
    LOOP_DUR = 0.4  # seg -- duracion del crossfade final hacia el frame de apertura
    OVERLAY_VOICE_DELAY = 1.0  # seg -- feedback 20 jul 2026: dar tiempo de leer el
    # card antes de que arranque la narracion, incluso en modo 'overlay' (video ya
    # corriendo). Se logra sosteniendo el ULTIMO frame +1s al final (no se pierde
    # nada de narracion) y retrasando la voz 1s, no los 2.2s completos del modo 'read'.
    read_mode = bool(hook_card) and hook_card_mode == "read"
    overlay_delay_mode = bool(hook_card) and hook_card_mode != "read"
    audio_dur = ffprobe_duration(audio)
    if durations is None:
        durations = [audio_dur / len(clips)] * len(clips)

    if split_first_clip and durations[0] > 1.0:
        # parte la escena 1 en dos mitades del mismo clip -- un corte extra en
        # el primer segundo simula "mas camaras"/ritmo, sin generar media nueva
        # (test: el corte en si es una senal de "esto se mueve rapido").
        half = durations[0] / 2
        clips = [clips[0], clips[0], *clips[1:]]
        durations = [half, half, *durations[1:]]

    norm_paths = []

    for i, clip in enumerate(clips):
        norm = out_dir / "clips" / f"seg_{i}.mp4"
        seg = durations[i]
        clip_dur = ffprobe_duration(clip)
        loop_args = ["-stream_loop", "-1"] if clip_dur < seg else []
        run([
            "ffmpeg", "-y", *loop_args, "-i", str(clip), "-t", f"{seg:.3f}",
            "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                   f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", str(norm),
        ])
        norm_paths.append(norm)

    loop_frame = None
    if hook_punch:
        # loop visual real (investigacion 19-20 jul 2026, canal vidIQ): el ultimo
        # frame del video debe parecerse al primero para que un rewatch/loop se
        # sienta continuo en vez de "arranca un video nuevo" -- YouTube cuenta el
        # loop como señal fuerte de engagement. Se captura el primer frame ORIGINAL
        # (antes del wipe/flash de entrada) para usarlo como destino del loop al
        # final, sin importar que efectos de entrada se apliquen despues.
        loop_frame = out_dir / "clips" / "loop_frame.png"
        run(["ffmpeg", "-y", "-i", str(norm_paths[0]), "-vframes", "1", str(loop_frame)])

    if read_mode:
        # beat de lectura primero: congelar el primer frame del clip 0 durante
        # HOOK_CARD_DUR y anteponerlo. La narracion (voz) se retrasa ese mismo
        # tiempo en el filtro de audio; los subs ya llegan con offset_ms desde
        # main. El premise card se dibuja encima de este segmento (0-2.2s).
        first_frame = out_dir / "clips" / "hookcard_frame.png"
        run(["ffmpeg", "-y", "-i", str(norm_paths[0]), "-vframes", "1",
             str(first_frame)])
        freeze = out_dir / "clips" / "seg_hookcard.mp4"
        _static_image_clip(first_frame, HOOK_CARD_DUR, freeze, static=True)
        norm_paths = [freeze, *norm_paths]

    if overlay_delay_mode:
        # sostiene el ultimo frame +1s al final para compensar el retraso de voz
        # (asi no se corta el ultimo segundo de narracion) -- ver OVERLAY_VOICE_DELAY.
        last_frame = out_dir / "clips" / "hookcard_last_frame.png"
        run(["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(norm_paths[-1]),
             "-vframes", "1", str(last_frame)])
        hold = out_dir / "clips" / "seg_holdend.mp4"
        _static_image_clip(last_frame, OVERLAY_VOICE_DELAY, hold, static=True)
        norm_paths = [*norm_paths, hold]

    if hook_punch:
        # transicion de entrada agresiva (bajo --hook-max): wipe circular muy
        # rapido (~0.3s) desde blanco hacia el primer clip, en vez del corte
        # seco de siempre. Es una anomalia de movimiento adicional en el
        # frame 0 -- el ojo la registra antes de evaluar el contenido, mismo
        # principio que el flash pero con mas "sensacion de impacto".
        entry_clip = norm_paths[0]
        punch_dur = 0.3
        wiped = out_dir / "clips" / "seg_punch_wipe.mp4"
        run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=white:s={WIDTH}x{HEIGHT}:d={punch_dur}:r={FPS}",
            "-i", str(entry_clip),
            "-filter_complex",
            f"[1:v]trim=0:{punch_dur},setpts=PTS-STARTPTS,fps={FPS}[headv];"
            f"[0:v][headv]xfade=transition=circleopen:duration={punch_dur}:offset=0[wv]",
            "-map", "[wv]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", str(wiped),
        ])
        rest = out_dir / "clips" / "seg_punch_rest.mp4"
        run([
            "ffmpeg", "-y", "-i", str(entry_clip), "-ss", f"{punch_dur:.3f}",
            # NUNCA "-c copy" aca -- el clip fuente (libx264 veryfast, GOP largo)
            # suele no tener keyframe en 0.3s, y el copy silenciosamente produce
            # un archivo casi vacio que trunca el concat entero (bug real, visto
            # 20 jul 2026: video final de 23.6s en vez de ~39s). Reencodear.
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", str(rest),
        ])
        norm_paths = [wiped, rest, *norm_paths[1:]]

    if loop_frame is not None:
        # crossfade final hacia el frame de apertura -- el ultimo medio segundo
        # del video se funde con la misma imagen/encuadre con la que arranca,
        # asi al repetirse (loop de YouTube) no se percibe un corte, se siente
        # continuo. Duracion corta para no robarle tiempo a la narracion real.
        loop_dur = LOOP_DUR
        loop_still = out_dir / "clips" / "seg_loop_still.mp4"
        _static_image_clip(loop_frame, loop_dur, loop_still, static=True)
        last_clip = norm_paths[-1]
        looped = out_dir / "clips" / "seg_loop_xfade.mp4"
        last_dur = ffprobe_duration(last_clip)
        xfade_offset = max(last_dur - loop_dur, 0)
        run([
            "ffmpeg", "-y", "-i", str(last_clip), "-i", str(loop_still),
            "-filter_complex",
            f"[0:v]fps={FPS}[v0];[1:v]fps={FPS}[v1];"
            f"[v0][v1]xfade=transition=fade:duration={loop_dur}:offset={xfade_offset:.3f}[v]",
            "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", str(looped),
        ])
        norm_paths = [*norm_paths[:-1], looped]

    concat_list = out_dir / "clips" / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.name}'\n" for p in norm_paths), encoding="utf-8"
    )
    concat_path = out_dir / "clips" / "concat.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list.name,
         "-c", "copy", concat_path.name], cwd=out_dir / "clips")

    # cwd = out_dir con rutas relativas: evita escapar rutas de Windows en el filtro ass
    final = out_dir / "video.mp4"
    sfx_cues = sfx_cues or []

    stinger_path = None
    if intro_stinger:
        # gancho auditivo en el frame 0, independiente de trigger_word (que
        # nunca dispara nada antes de que se diga la primera palabra) -- test
        # de si un whoosh/riser generico al inicio baja el swipe inmediato.
        candidates = [p for p in SFX_DIR.iterdir()
                      if p.suffix.lower() in (".mp3", ".wav")
                      and re.search(r"whoosh|riser|swoosh", p.name, re.I)] if SFX_DIR.exists() else []
        if candidates:
            import random
            stinger_path = random.choice(candidates)

    # La musica generada (Lyria) se elimino con el resto de Gemini el 3 ago 2026:
    # queda solo la biblioteca local de assets/music.
    music = None
    # music_mood=None explicito (no "sin music_mood en el guion", eso no pasa --
    # es requerido por el schema) significa "sin musica a proposito" (modo
    # silent_card_mode: el video se sube mudo de musica para agregar despues a
    # mano un audio trending del nicho en el editor de Shorts de Studio, ver
    # memoria musica-trending-videos-solo-lectura). No caer al fallback de
    # libreria local en ese caso.
    if not music and music_mood is not None:
        music = _pick_music()

    watermark_filter = (
        f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='{_drawtext_escape(watermark)}'"
        ":fontcolor=white@0.55:fontsize=34:borderw=2:bordercolor=black@0.4"
        ":x=w-text_w-28:y=110,"
    ) if watermark else ""

    cta_filter = ""
    if cta_text and cta_position:
        # CTA como texto en pantalla, NUNCA narrado -- test de posicion
        # (inicio/medio/final) sin arriesgar el "Cliff" de retencion del CTA
        # hablado (ver RETENTION_CHECKLIST.md). 3s de aparicion con fade.
        cta_dur = 3.0
        if cta_position == "start":
            cta_start = 0.5
        elif cta_position == "end":
            cta_start = max(audio_dur - cta_dur - 0.5, 0)
        else:  # "middle"
            cta_start = max(audio_dur / 2 - cta_dur / 2, 0)
        cta_end = cta_start + cta_dur
        safe_text = _drawtext_escape(cta_text)
        cta_filter = (
            f"drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='{safe_text}'"
            ":fontcolor=white:fontsize=44:borderw=3:bordercolor=black@0.6"
            ":x=(w-text_w)/2:y=h-320"
            f":alpha='if(lt(t,{cta_start}),0,if(lt(t,{cta_start+0.3}),(t-{cta_start})/0.3,"
            f"if(lt(t,{cta_end-0.3}),1,if(lt(t,{cta_end}),({cta_end}-t)/0.3,0))))'"
            f":enable='between(t,{cta_start},{cta_end})',"
        )

    # premise card: texto de alto contraste ~2.2s al inicio (curiosity gap "solo
    # para leer"). Scrim negro semitransparente sobre el video para maximo
    # contraste + texto grande centrado. Se dibuja en AMBOS modos (overlay/read);
    # en read el frame de abajo esta congelado, en overlay ya corre el video.
    # el TEXTO del card va como eventos ASS (no drawtext): drawtext expande
    # '%{...}' incluso desde textfile, asi que un '100%' en el card rompe la
    # linea. ASS no tiene ese problema y ademas da fade/posicion mas limpios.
    # El scrim oscuro si es un filtro (drawbox), dibujado ANTES del ass para
    # que el texto quede por encima.
    # pattern interrupt: flash blanco de ~2 frames en t=0 (bajo --hook-max) --
    # el sistema reticular activador prioriza anomalias de brillo/contraste
    # sobre contenido "normal", frena el scroll antes de que el ojo evalue
    # la escena en si. Se dibuja ANTES del scrim/ass para quedar debajo del
    # texto del hook_card si coexisten.
    hook_punch_filter = ""
    if hook_punch:
        flash_end = round(2 / FPS, 3)
        hook_punch_filter = (
            f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.9:t=fill"
            f":enable='between(t,0,{flash_end})',"
        )

    hook_card_filter = ""
    if hook_card:
        card_clean = hook_card.replace("\\", "").replace("{", "(").replace("}", ")")
        card_lines = _wrap_caption(card_clean, width_chars=22).split("\n")
        c_gap = 78
        # anclado cerca del TOP (no centrado verticalmente) -- el estilo 'Cap' de
        # los subtitulos karaoke usa MarginV alto (ver Style: Cap en generate_subtitles),
        # lo que los deja cayendo en la franja media/baja del frame. Si el card se
        # centra verticalmente, cae en la MISMA franja y ambos textos se solapan
        # (bug real detectado 19 jul 2026, ver captura de pantalla del usuario).
        c_y0 = 220
        cx = WIDTH // 2
        # scrim SOLO detras del bloque de texto (no el frame completo, feedback
        # del usuario 20 jul 2026 -- el oscurecido total se sentia como "filtro
        # blanco y negro" sobre toda la imagen). Caja centrada en X, ajustada a
        # la altura real del texto con padding.
        box_pad_y = 30
        box_w = min(int(WIDTH * 0.9), 900)
        box_h = len(card_lines) * c_gap + box_pad_y * 2
        box_x = (WIDTH - box_w) // 2
        box_y = c_y0 - c_gap // 2 - box_pad_y
        hook_card_filter = (
            f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:color=black@0.75:t=fill"
            ":enable='between(t,0,2.2)',"
        )
        # revelado progresivo linea por linea (no todo junto) -- investigacion
        # 20 jul 2026: el "hook card hipnotico" tira de la vista siguiendo un
        # ritmo de lectura en vez de dejar escanear todo de una, y la animacion
        # elaborada rinde PEOR que un fade simple, asi que el efecto es solo
        # stagger de tiempo, no de movimiento. Los numeros/datos concretos se
        # resaltan en amarillo sobre texto blanco (mismo patron que caption
        # mode) -- la especificidad es lo que separa un hook fuerte de uno
        # generico segun la misma investigacion.
        line_stagger_s = 0.28
        card_events = []
        for i, line in enumerate(card_lines):
            y = c_y0 + i * c_gap
            start_s = i * line_stagger_s
            line_colored = re.sub(r"\d+", lambda m: f"{{\\c&H4AD2FF&}}{m.group(0)}{{\\c&HFFFFFF&}}", line)
            card_events.append(
                f"Dialogue: 0,{_ass_time(start_s)},0:00:02.20,Cap,,0,0,0,,"
                f"{{\\an5\\pos({cx},{y})\\fs60\\c&HFFFFFF&\\fad(250,200)}}{line_colored}"
            )
        with ass_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(card_events) + "\n")

    if caption_text:
        # modo caption estatico: la imagen ocupa solo la parte inferior del
        # frame, el titulo+parrafo quedan fijos arriba (nunca desaparecen,
        # a diferencia del karaoke) -- el narrador solo lee el titulo corto,
        # el parrafo es puro texto para leer al propio ritmo (evita el "loop
        # mecanico por no dar tiempo a leer" que se vio en el lote ultra-corto
        # de subtitulos karaoke). Se inyecta como Dialogue extra en el MISMO
        # .ass del karaoke (en vez de drawtext) porque ASS soporta color por
        # palabra via {\c&Hbbggrr&} inline -- drawtext es un solo color por
        # llamada, no alcanzaba para resaltar keywords en rojo dentro de la
        # linea.
        def _ass_clean(s: str) -> str:
            return s.replace("\\", "").replace("{", "(").replace("}", ")")

        # feedback 20 jul 2026: letras mas grandes Y que se extiendan mas a lo
        # lateral (antes quedaban en una columna angosta con mucho margen a los
        # costados). width_chars mas alto = lineas mas largas = usa mas ancho
        # del cuadro con el mismo tamano de fuente.
        header_lines = _wrap_caption(_ass_clean(caption_header or ""), width_chars=18).split("\n")

        # bug real (20 jul 2026): al envolver el parrafo, una keyword de varias
        # palabras (ej. "cryptic message") podia terminar partida entre dos
        # lineas -- el regex de resaltado corre POR LINEA, asi que la mitad
        # partida ya no matcheaba y la keyword se quedaba sin marcar en rojo.
        # Fix: unir los espacios internos de cada keyword con un word-joiner
        # invisible (U+2060) ANTES de envolver, para que textwrap la trate
        # como una sola palabra indivisible; se separa recien al pintar rojo.
        body_text = _ass_clean(caption_text)
        JOINER = "⁠"
        joined_keywords = []
        for kw in (caption_keywords or []):
            kw_clean = _ass_clean(kw)
            joined = kw_clean.replace(" ", JOINER)
            body_text = re.sub(re.escape(kw_clean), joined, body_text, flags=re.IGNORECASE)
            joined_keywords.append(joined)

        body_lines = _wrap_caption(body_text, width_chars=38).split("\n")

        RED, WHITE = r"{\c&H0000FF&}", r"{\c&HFFFFFF&}"
        for joined in joined_keywords:
            pattern = re.compile(re.escape(joined), re.IGNORECASE)
            body_lines = [
                pattern.sub(lambda m: f"{RED}{m.group(0).replace(JOINER, ' ')}{WHITE}", line)
                for line in body_lines
            ]

        img_h = int(HEIGHT * 0.62)
        img_y = HEIGHT - img_h

        # feedback 20 jul 2026: el bloque se veia chico y pegado arriba, con
        # mucho negro vacio debajo -- ahora usa fuente grande por defecto y se
        # centra verticalmente en TODA la franja negra disponible (con margen
        # chico), en vez de anclarse fijo cerca del tope. Si no entra ni asi,
        # se encoge fuente/interlineado proporcionalmente (header y body
        # juntos, misma escala) en vez de desbordar sobre la imagen.
        # tamanos medidos con Pillow (arialbd.ttf) contra el ancho real del
        # frame (20 jul 2026) en vez de a ojo: con margen lateral ~5% (972px
        # utiles de 1080), header cabe hasta fs=92 y body hasta width_chars=38
        # a fs=48 sin desbordar horizontalmente en los 3 guiones de prueba.
        margin = 54
        header_size, header_gap = 92, 118
        body_size, body_gap = 48, 62
        block_gap = 50  # separacion entre el header y el body

        total_h = len(header_lines) * header_gap + block_gap + len(body_lines) * body_gap
        available_h = img_y - margin * 2
        if total_h > available_h and available_h > 0:
            scale = available_h / total_h
            header_size = max(int(header_size * scale), 28)
            header_gap = max(int(header_gap * scale), 34)
            body_size = max(int(body_size * scale), 22)
            body_gap = max(int(body_gap * scale), 28)
            block_gap = max(int(block_gap * scale), 20)
            total_h = len(header_lines) * header_gap + block_gap + len(body_lines) * body_gap

        start_y = margin + max((available_h - total_h) / 2, 0)
        header_y0 = int(start_y + header_gap / 2)
        body_y0 = header_y0 + len(header_lines) * header_gap + block_gap

        cx = WIDTH // 2
        caption_events = []
        for i, line in enumerate(header_lines):
            y = header_y0 + i * header_gap
            caption_events.append(
                f"Dialogue: 0,0:00:00.00,0:59:59.00,Cap,,0,0,0,,"
                f"{{\\an5\\pos({cx},{y})\\fs{header_size}\\c&H4AD2FF&}}{line}"
            )
        for i, line in enumerate(body_lines):
            y = body_y0 + i * body_gap
            caption_events.append(
                f"Dialogue: 0,0:00:00.00,0:59:59.00,Cap,,0,0,0,,"
                f"{{\\an5\\pos({cx},{y})\\fs{body_size}\\c&HFFFFFF&}}{line}"
            )
        with ass_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(caption_events) + "\n")

        video_filter = (
            f"color=c=black:s={WIDTH}x{HEIGHT}:d=1[bgbase];"
            f"[0:v]scale={WIDTH}:{img_h}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{img_h}[imgbox];"
            f"[bgbase][imgbox]overlay=0:{img_y}[withimg];"
            f"[withimg]{hook_punch_filter}{hook_card_filter}ass={ass_path.name},"
            f"{watermark_filter}{cta_filter}null[v];"
        )
    else:
        video_filter = (
            f"[0:v]{hook_punch_filter}{hook_card_filter}ass={ass_path.name},"
            f"{watermark_filter}{cta_filter}null[v];"
        )

    # inputs: 0=video concat, 1=voz, [2=musica], luego un input por cada sfx
    inputs = ["-i", str(Path("clips") / "concat.mp4"), "-i", audio.name]
    next_idx = 2
    music_idx = None
    if music:
        inputs += ["-i", str(music)]
        music_idx = next_idx
        next_idx += 1
    sfx_idxs = []
    for _, sfx_path in sfx_cues:
        inputs += ["-i", str(sfx_path)]
        sfx_idxs.append(next_idx)
        next_idx += 1

    stinger_idx = None
    if stinger_path:
        inputs += ["-i", str(stinger_path)]
        stinger_idx = next_idx
        next_idx += 1

    # modo card 'read': la narracion arranca despues del beat de lectura, asi que
    # la voz (y los sfx atados a palabras) se retrasan card_ms; la musica y el
    # stinger arrancan en 0 (suenan durante el card). total_dur incluye el card
    # para que el fade-out de la musica caiga al final real, no 2.2s antes.
    voice_delay_s = HOOK_CARD_DUR if read_mode else (OVERLAY_VOICE_DELAY if overlay_delay_mode else 0.0)
    card_ms = int(voice_delay_s * 1000)
    total_dur = audio_dur + voice_delay_s + (LOOP_DUR if hook_punch else 0.0)

    audio_labels = []
    audio_filters = ""
    if card_ms:
        audio_filters += f"[1:a]adelay={card_ms}|{card_ms}[voicesrc];"
        voice_lbl = "[voicesrc]"
    else:
        voice_lbl = "[1:a]"
    if music:
        fade_dur = min(2.5, total_dur / 4)
        fade_out_start = max(total_dur - fade_dur, 0)
        audio_filters += (
            f"{voice_lbl}asplit=2[voice_mix][voice_trigger];"
            f"[{music_idx}:a]aloop=loop=-1:size=2e9,volume={MUSIC_VOLUME},"
            f"afade=t=in:st=0:d={fade_dur:.2f},"
            f"afade=t=out:st={fade_out_start:.2f}:d={fade_dur:.2f}[bg];"
            "[bg][voice_trigger]sidechaincompress="
            "threshold=0.03:ratio=8:attack=20:release=400[bg_ducked];"
        )
        audio_labels += ["[voice_mix]", "[bg_ducked]"]
    else:
        audio_filters += f"{voice_lbl}anull[voice_mix];"
        audio_labels += ["[voice_mix]"]

    for k, ((ts, _), idx) in enumerate(zip(sfx_cues, sfx_idxs)):
        ms = int(ts * 1000) + card_ms
        audio_filters += f"[{idx}:a]adelay={ms}|{ms},volume=0.2[sfx{k}];"
        audio_labels.append(f"[sfx{k}]")

    if stinger_idx is not None:
        audio_filters += f"[{stinger_idx}:a]atrim=0:0.6,volume=0.42[stinger];"
        audio_labels.append("[stinger]")

    # el mix termina en audio_dur+voice_delay_s -- si hay loop visual al final
    # (hook_punch), el video queda LOOP_DUR mas largo que eso, y sin este padding
    # "-shortest" cortaria justo ese segmento de loop antes de que se vea (bug
    # real detectado 20 jul 2026: el ultimo frame mostraba una escena del medio,
    # no el loop, porque el audio mas corto truncaba el video).
    pad_filter = f",apad=pad_dur={LOOP_DUR}" if hook_punch else ""
    audio_filters += (
        f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:"
        "duration=first:dropout_transition=0:normalize=0,"
        f"loudnorm=I=-14:TP=-1.5:LRA=11{pad_filter}[aout]"
    )

    label = "musica + " if music else ""
    label += f"{len(sfx_cues)} sfx" if sfx_cues else "sin sfx"
    log("assembly", f"Render final (subtitulos + voz + {label})...")
    run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", video_filter + audio_filters,
        "-map", "[v]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-shortest", final.name,
    ], cwd=out_dir)
    return final


MUSIC_DIR = ROOT / "assets" / "music"


def _pick_music() -> Path | None:
    """Elige una pista al azar de assets/music/ (mp3/m4a/wav/ogg). None si esta vacia."""
    if not MUSIC_DIR.exists():
        return None
    tracks = [p for p in MUSIC_DIR.iterdir()
              if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg", ".flac")]
    if not tracks:
        return None
    import random
    return random.choice(tracks)


# ------------------------------------------------------------- MOTION GRAPHICS

MOTION_DIR = ROOT / "motion_graphics"

# mapeo palabra disparadora (trigger_word de pick_sfx_cues) -> emoji. Heuristica
# por categoria de sonido/concepto, no traduccion literal -- alcanza con que el
# icono refuerce visualmente lo mismo que ya dice el SFX (ver HISTORIAL_MEJORAS.md
# 21 jul 2026, patron "icono+SFX por cada beat" de los videos de referencia).
_EMOJI_CATEGORIES: list[tuple[tuple[str, ...], str]] = [
    (("radio", "transmission", "signal", "broadcast"), "\U0001F4FB"),
    (("shot", "gun", "gunfire", "rifle", "pistol"), "\U0001F4A5"),
    (("sword", "blade", "knife"), "\U0001F5E1"),
    (("explosion", "bomb", "blast"), "\U0001F4A3"),
    (("fire", "burn", "burned", "flame"), "\U0001F525"),
    (("water", "lake", "river", "flood", "drown"), "\U0001F30A"),
    (("money", "cash", "gold", "banknote", "currency", "counterfeit"), "\U0001F4B0"),
    (("key", "lock", "unlock", "locked"), "\U0001F513"),
    (("letter", "paper", "document", "telegram", "note"), "\U0001F4C4"),
    (("phone", "call", "telephone"), "\U0000260E"),
    (("bell", "alarm", "siren"), "\U0001F514"),
    (("clock", "time", "minutes", "hours"), "\U000023F0"),
    (("plates", "engraving", "printing", "press"), "\U0001F5A8"),
    (("glider", "plane", "aircraft", "flight"), "\U00002708"),
    (("kidnap", "kidnapped", "captured", "capture"), "\U0001F6A8"),
    (("dead", "died", "death", "killed"), "\U0001F480"),
    (("never", "found", "unsolved", "mystery"), "\U00002753"),
    (("cigar", "smoke"), "\U0001F6AC"),
]


def _word_to_emoji(word: str) -> str:
    w = re.sub(r"[^a-z]", "", word.lower())
    for keys, emoji in _EMOJI_CATEGORIES:
        if any(k in w for k in keys):
            return emoji
    return "\U00002757"  # exclamacion generica de fallback


# categoria -> query de foto real generica para Wikimedia. Paralelo a
# _EMOJI_CATEGORIES: mismo set de palabras disparadoras, pero acá el valor es
# una BUSQUEDA (no un emoji). El sticker intenta primero foto real recortada
# y cae a emoji solo si no hay resultado libre de un solo sujeto (pedido
# usuario 21 jul 2026: "foto real para todo lo que se pueda").
_PHOTO_QUERY_CATEGORIES: list[tuple[tuple[str, ...], str]] = [
    (("radio", "transmission", "signal", "broadcast"), "vintage military radio"),
    (("shot", "gun", "gunfire", "rifle", "pistol"), "WWII rifle"),
    (("sword", "blade", "knife"), "antique military sword"),
    (("explosion", "bomb", "blast"), "explosion black and white photo"),
    (("fire", "burn", "burned", "flame"), "fire vintage photo"),
    (("water", "lake", "river", "flood", "drown"), None),  # paisaje generico, mejor emoji
    (("money", "cash", "gold", "banknote", "currency", "counterfeit"), "banknote 1940s"),
    (("key", "lock", "unlock", "locked"), "antique lock"),
    (("letter", "paper", "document", "telegram", "note"), "declassified document"),
    (("phone", "call", "telephone"), "vintage telephone"),
    (("bell", "alarm", "siren"), "air raid siren"),
    (("clock", "time", "minutes", "hours"), "antique pocket watch"),
    (("plates", "engraving", "printing", "press"), "vintage printing press"),
    (("glider", "plane", "aircraft", "flight"), "WWII military aircraft"),
    (("kidnap", "kidnapped", "captured", "capture"), None),
    (("dead", "died", "death", "killed"), None),
    (("never", "found", "unsolved", "mystery"), None),
    (("cigar", "smoke"), "cigar vintage photo"),
    (("flag", "banner"), "military flag"),
    (("medal", "award", "decoration"), "military medal"),
    (("uniform", "soldier", "officer"), "WWII soldier uniform"),
    (("tank", "armor", "armored"), "WWII tank"),
    (("ship", "submarine", "boat", "vessel"), "WWII ship"),
]


def _scene_hint(text: str) -> tuple[str, str, str | None]:
    """Escanea el texto de una escena (search_term del guion) y devuelve
    (trigger_word_para_mostrar, emoji_fallback, photo_query|None). Reemplaza
    el matching anterior que solo miraba una palabra suelta (trigger_word de
    SFX) -- ahora cada ESCENA completa se analiza para elegir un sticker
    (1 por escena, ver HISTORIAL_MEJORAS.md 21 jul 2026)."""
    w = re.sub(r"[^a-z ]", "", text.lower())
    for i, (keys, emoji) in enumerate(_EMOJI_CATEGORIES):
        if any(k in w for k in keys):
            display = next((k for k in keys if k in w), keys[0])
            photo_q = _PHOTO_QUERY_CATEGORIES[i][1]
            return display.upper(), emoji, photo_q
    return "", "\U00002757", None


def _photo_sticker(query: str, clips_dir: Path, tag: str) -> str | None:
    """Intenta armar un sticker de FOTO REAL recortada para un objeto/lugar
    generico (no una persona) -- misma fuente (Wikimedia Commons, licencia
    libre) y mismo pipeline de recorte que add_real_photo_collage, pero mas
    chico y sin sesgo 'portrait' (un rifle o una bandera no son retratos).
    Devuelve el nombre de archivo relativo dentro de motion_graphics/public/
    o None si no hay candidato libre de un solo sujeto."""
    candidates = _wikimedia_commons_search(query, bias_portrait=False)
    if not candidates:
        return None
    import urllib.request
    fname = f"scene_sticker_{tag}.png"
    out_path = MOTION_DIR / "public" / fname
    for i, cand in enumerate(candidates[:6]):
        raw_path = clips_dir / f"scene_raw_{tag}_{i}.jpg"
        req = urllib.request.Request(cand["url"], headers={"User-Agent": "HiddenFactsBot/1.0 (contact@example.com)"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_path.write_bytes(resp.read())
        except Exception:
            continue
        if _cutout_and_halftone(raw_path, out_path) == "ok":
            return fname
    return None


def add_scene_stickers(video_path: Path, search_terms: list[str], durations: list[float],
                        out_dir: Path, words: list[tuple[float, float, str]] | None = None,
                        sticker_sfx: bool = False, tone: str | None = None,
                        sticker_sfx_file: str | None = None) -> Path:
    """Sticker por cada palabra clave REALMENTE narrada (words, con timestamp
    real de TTS) usando la libreria pre-generada de sticker_library.py --
    pedido usuario 22 jul 2026: 'asegurate de usarlo en cada palabra clave
    que se diga', no solo 1 por escena. Las escenas que no tienen ninguna
    keyword narrada caen al esquema viejo (foto real recortada de Wikimedia,
    y si no hay candidato, emoji -- ver HISTORIAL_MEJORAS.md 21 jul 2026) para
    no perder densidad visual. Si Remotion/Node no esta disponible o falla,
    devuelve el video sin tocar."""
    if not (MOTION_DIR / "node_modules").exists():
        log("motion", "motion_graphics/node_modules no existe, salteando (correr npm install)")
        return video_path

    clips_dir = out_dir / "clips"
    video_dur = ffprobe_duration(video_path)
    fps = FPS

    library_cues = sticker_library.prepare_render_cues(words, MOTION_DIR / "public") if words else []
    log("motion", f"{len(library_cues)} stickers de la libreria (keywords narradas)")

    cues = list(library_cues)
    t = 0.0
    for i, (term, dur) in enumerate(zip(search_terms, durations)):
        scene_start, scene_end = t, t + dur
        mid = t + dur / 2
        t += dur
        # ya hay un sticker de la libreria narrado en esta escena -- no
        # duplicar con el fallback generico (1 sticker visible a la vez)
        if any(scene_start <= c["time"] < scene_end for c in library_cues):
            continue
        keyword, emoji, photo_query = _scene_hint(term)
        photo = _photo_sticker(photo_query, clips_dir, str(i)) if photo_query else None
        cues.append({"time": mid, "keyword": keyword, "emoji": emoji, "photo": photo})
        if photo:
            log("motion", f"escena {i+1}: foto real ({photo_query})")
        else:
            log("motion", f"escena {i+1}: emoji fallback ({keyword or '?'})")
    cues.sort(key=lambda c: c["time"])

    props = {"cues": cues, "durationInFrames": max(int(round(video_dur * fps)), 1), "fps": fps,
              "width": WIDTH, "height": HEIGHT}
    props_path = clips_dir / "motion_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    # bug real (21 jul 2026): vp8/yuva420p NO preserva canal alpha de forma
    # confiable en este render (ya lo vimos antes con el prototipo manual) --
    # el resultado sale con fondo negro opaco en vez de transparente. ProRes
    # 4444 + yuva444p10le si preserva el alpha real, confirmado con ffprobe
    # en esa prueba. Usar siempre ProRes aca, nunca vp8/webm.
    overlay_path = clips_dir / "motion_overlay.mov"
    # en Windows "npx" es npx.cmd -- subprocess.run(shell=False, default de
    # run()) no lo resuelve y tira WinError 2. shutil.which encuentra el
    # ejecutable real sin necesitar shell=True para todo el resto de run().
    npx_bin = shutil.which("npx") or "npx"
    try:
        run([
            npx_bin, "remotion", "render",
            "--image-format=png", "--pixel-format=yuva444p10le",
            "--codec=prores", "--prores-profile=4444",
            "--props", str(props_path.resolve()),
            "src/index.jsx", "AutoOverlay", str(overlay_path.resolve()),
        ], cwd=str(MOTION_DIR))
    except Exception as e:
        log("motion", f"Render de Remotion fallo, se sigue sin motion graphics: {e}")
        return video_path

    # el resto del pipeline (subida, QA, este mismo main()) asume que el
    # resultado final siempre vive en out_dir/video.mp4 -- se compone a un
    # archivo temporal y se reemplaza in-place, nunca se cambia el nombre.
    # capa opcional de sonido de entrada de sticker (swish de papel en cada pop).
    # Se omite si: el flag esta apagado, no hay cues, no existe el archivo, o el
    # tono del video es sombrio (respeta la misma logica de tono que pick_sfx_cues).
    sfx_path = SFX_DIR / (sticker_sfx_file or STICKER_SFX_DEFAULT)
    somber = bool(tone) and any(w in tone.lower() for w in _SOMBER_TONE_WORDS)
    sfx_cue_times = [c["time"] for c in cues]
    use_sticker_sfx = bool(sticker_sfx and sfx_cue_times and sfx_path.exists() and not somber)
    if sticker_sfx and somber:
        log("motion", "sticker-sfx omitido: tono sombrio")
    elif sticker_sfx and not sfx_path.exists():
        log("motion", f"sticker-sfx omitido: no existe {sfx_path.name}")

    composited = clips_dir / "video_with_motion.mp4"
    try:
        if use_sticker_sfx:
            # un input del sonido por cada pop, retrasado a su tiempo y a volumen
            # bajo; se suma (amix normalize=0) sobre el audio original sin pisarlo.
            inputs = ["-i", str(video_path), "-i", str(overlay_path)]
            fc = "[1:v]format=yuva420p[ov];[0:v][ov]overlay=0:0[v];"
            labels = "[0:a]"
            for k, t in enumerate(sfx_cue_times):
                inputs += ["-i", str(sfx_path)]
                ms = int(round(t * 1000))
                fc += f"[{2 + k}:a]adelay={ms}|{ms},volume={STICKER_SFX_VOLUME}[ssf{k}];"
                labels += f"[ssf{k}]"
            fc += f"{labels}amix=inputs={1 + len(sfx_cue_times)}:normalize=0:duration=first[a]"
            run([
                "ffmpeg", "-y", *inputs,
                "-filter_complex", fc,
                "-map", "[v]", "-map", "[a]",
                "-c:a", "aac", "-b:a", "192k",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                str(composited),
            ])
        else:
            run([
                "ffmpeg", "-y", "-i", str(video_path), "-i", str(overlay_path),
                "-filter_complex",
                "[1:v]format=yuva420p[ov];[0:v][ov]overlay=0:0[v]",
                "-map", "[v]", "-map", "0:a", "-c:a", "copy",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                str(composited),
            ])
    except Exception as e:
        log("motion", f"Composicion ffmpeg fallo, se sigue sin motion graphics: {e}")
        return video_path

    shutil.copyfile(composited, video_path)
    log("motion", f"{len(cues)} stickers agregados (1 por escena)")
    return video_path


# -------------------------------------------------------------- REAL PHOTO COLLAGE

def _wikimedia_commons_search(term: str, bias_portrait: bool = True) -> list[dict]:
    """Busca fotos de dominio publico/CC en Wikimedia Commons para `term`.
    Devuelve una LISTA de candidatos {"url","license","title","artist"}
    (jpg/png con licencia libre), no solo el primero -- add_real_photo_collage
    los prueba en orden y descarta los que no son un retrato de una sola
    persona (ver _is_single_subject), en vez de quedarse con el primer
    resultado aunque sea una foto grupal (bug real detectado 21 jul 2026:
    "Fidel Castro" trajo una foto con Cristina Kirchner). Nunca usa
    buscadores de imagenes tipo Google/Apify -- esos devuelven resultados con
    copyright real, mal encaje para un canal monetizado (riesgo de Content
    ID/strike). Wikimedia/NARA/LoC tienen API propia con licencia explicita
    por archivo (ver HISTORIAL_MEJORAS.md 21 jul 2026)."""
    import urllib.request, urllib.parse
    # se refuerza la query con "portrait" (si no la trae ya) para sesgar la
    # busqueda hacia fotos de una sola persona desde el vamos -- no reemplaza
    # la heuristica de abajo, solo mejora el orden de los candidatos.
    term_q = term
    if bias_portrait and "portrait" not in term.lower():
        term_q = f"{term} portrait"
    q = urllib.parse.quote(term_q)
    url = (f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
           f"&gsrsearch={q}&gsrnamespace=6&gsrlimit=12&prop=imageinfo"
           f"&iiprop=url|extmetadata|mime|size&format=json")
    req = urllib.request.Request(url, headers={"User-Agent": "HiddenFactsBot/1.0 (contact@example.com)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except Exception as e:
        log("collage", f"Busqueda Wikimedia fallo: {e}")
        return []
    candidates = []
    for p in data.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        if "image/jpeg" not in mime and "image/png" not in mime:
            continue
        w, h = ii.get("width", 0), ii.get("height", 0)
        if w < 200 or h < 200:
            continue
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", ""))
        candidates.append({"url": ii.get("url"), "license": lic,
                            "title": p.get("title", ""), "artist": artist})
    return candidates


def _is_single_subject(alpha_channel) -> bool:
    """Heuristica anti-foto-grupal: cuenta blobs grandes en el canal alpha del
    recorte (rembg). Una foto grupal casi siempre produce >1 blob grande
    (personas separadas) o un blob unico demasiado ancho respecto a su alto
    (dos cuerpos pegados). Se usa para descartar candidatos sin intervencion
    manual -- el usuario pidio automatizacion 100%, sin curar terminos de
    busqueda a mano (ver HISTORIAL_MEJORAS.md 21 jul 2026)."""
    import numpy as np
    from skimage import measure
    mask = np.array(alpha_channel) > 40
    if mask.sum() < 500:
        return False
    labeled = measure.label(mask)
    props = measure.regionprops(labeled)
    if not props:
        return False
    total_area = mask.sum()
    big_blobs = [r for r in props if r.area > total_area * 0.08]
    if len(big_blobs) > 1:
        return False
    main = max(props, key=lambda r: r.area)
    y0, x0, y1, x1 = main.bbox
    bbox_w, bbox_h = (x1 - x0), (y1 - y0)
    if bbox_w == 0 or bbox_h == 0:
        return False
    # un retrato/cuerpo de una persona es mas alto que ancho; > 1.35 de ancho
    # relativo a alto es tipico de dos personas paradas una al lado de la otra.
    if bbox_w / bbox_h > 1.35:
        return False
    return True


def _cutout_and_halftone(image_path: Path, out_path: Path) -> str:
    """Recorta el sujeto (rembg, sin API de pago) y aplica look 'foto de
    archivo recortada de periodico' (halftone B/N) preservando el alpha del
    recorte. Devuelve "ok", "no_rembg" o "multi_subject" (nunca lanza) --
    add_real_photo_collage usa el resultado para decidir si probar el
    siguiente candidato de la busqueda."""
    try:
        from rembg import remove
    except ImportError:
        log("collage", "rembg no instalado (py -m pip install rembg onnxruntime), salteando collage")
        return "no_rembg"
    from PIL import Image, ImageOps
    im = Image.open(image_path)
    cutout = remove(im)
    alpha = cutout.split()[3]
    if not _is_single_subject(alpha):
        return "multi_subject"
    rgb = cutout.convert("RGB")
    gray = ImageOps.autocontrast(rgb.convert("L"), cutoff=2)
    small = gray.resize((max(gray.width // 4, 1), max(gray.height // 4, 1)), Image.BILINEAR)
    dotted = small.resize(gray.size, Image.NEAREST)
    halftone = Image.blend(gray, dotted, 0.35)
    out = Image.merge("RGBA", (halftone, halftone, halftone, alpha))
    out.save(out_path)
    return "ok"


def add_real_photo_collage(video_path: Path, collage_subject: str, out_dir: Path,
                            collage_time: float | None = None) -> Path:
    """Inserta una escena de collage con FOTO REAL recortada (estilo 'recorte
    de periodico', pedido por el usuario 21 jul 2026) en un unico momento del
    video (default: ~66% de la duracion, el beat de 'reveal'). Fuente: solo
    Wikimedia Commons con licencia libre explicita -- nunca scraping de
    imagenes con copyright. Si falla cualquier paso (sin resultado, sin
    rembg, sin Remotion), devuelve el video sin tocar."""
    if not (MOTION_DIR / "node_modules").exists():
        log("collage", "motion_graphics/node_modules no existe, salteando (correr npm install)")
        return video_path

    candidates = _wikimedia_commons_search(collage_subject)
    if not candidates:
        log("collage", f"Sin resultado libre en Wikimedia para '{collage_subject}', salteando")
        return video_path

    import urllib.request
    clips_dir = out_dir / "clips"
    photo_path = MOTION_DIR / "public" / "collage_photo.png"
    hit = None
    no_rembg = False
    # prueba candidatos en orden hasta encontrar UNO de una sola persona --
    # nunca se conforma con el primer resultado aunque sea foto grupal (esto
    # es lo que reemplaza la curacion manual del termino de busqueda: el
    # usuario pidio automatizacion 100%, ver HISTORIAL_MEJORAS.md 21 jul 2026).
    for i, cand in enumerate(candidates):
        raw_path = clips_dir / f"collage_raw_{i}.jpg"
        req = urllib.request.Request(cand["url"], headers={"User-Agent": "HiddenFactsBot/1.0 (contact@example.com)"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw_path.write_bytes(resp.read())
        except Exception as e:
            log("collage", f"Descarga fallo para candidato {i} ({cand['title']}): {e}")
            continue
        status = _cutout_and_halftone(raw_path, photo_path)
        if status == "no_rembg":
            no_rembg = True
            break
        if status == "ok":
            hit = cand
            log("collage", f"Candidato {i+1}/{len(candidates)} aceptado: {cand['title']}")
            break
        log("collage", f"Candidato {i+1}/{len(candidates)} descartado (foto grupal/multi-sujeto): {cand['title']}")

    if no_rembg:
        return video_path
    if hit is None:
        log("collage", f"Ningun candidato de '{collage_subject}' paso el filtro de sujeto unico, salteando")
        return video_path

    # credito de atribucion: CC-BY/CC-BY-SA lo exigen -- se guarda para agregar
    # a la descripcion del video, nunca se omite silenciosamente.
    credit_path = out_dir / "collage_credit.txt"
    credit_path.write_text(
        f"Foto: {hit['title']} ({hit['license']}), autor: {hit.get('artist') or 'desconocido'}, "
        f"via Wikimedia Commons — {hit['url']}",
        encoding="utf-8")

    video_dur = ffprobe_duration(video_path)
    scene_dur = 2.4
    t0 = collage_time if collage_time is not None else max(video_dur * 0.66 - scene_dur / 2, 0)
    t0 = min(t0, max(video_dur - scene_dur, 0))

    props = {"photo": "collage_photo.png", "clipping": None, "stampText": "DECLASSIFIED",
              "durationInFrames": int(round(scene_dur * FPS)), "fps": FPS, "width": WIDTH, "height": HEIGHT}
    props_path = clips_dir / "collage_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    overlay_path = clips_dir / "collage_overlay.mov"
    npx_bin = shutil.which("npx") or "npx"
    try:
        run([
            npx_bin, "remotion", "render",
            "--image-format=png", "--pixel-format=yuva444p10le",
            "--codec=prores", "--prores-profile=4444",
            "--props", str(props_path.resolve()),
            "src/index.jsx", "RealCollage", str(overlay_path.resolve()),
        ], cwd=str(MOTION_DIR))
    except Exception as e:
        log("collage", f"Render de Remotion fallo, se sigue sin collage: {e}")
        return video_path

    composited = clips_dir / "video_with_collage.mp4"
    try:
        run([
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(overlay_path),
            "-filter_complex",
            # el overlay .mov arranca SU PROPIO timeline en t=0 (dura solo
            # scene_dur); sin el setpts, al llegar t0 en el video principal el
            # stream corto ya esta agotado (EOF) y el collage nunca aparece --
            # bug real detectado 21 jul 2026 en QA visual. setpts+t0 corre el
            # overlay para que sus frames coincidan con el instante correcto.
            f"[1:v]format=yuva420p,setpts=PTS+{t0}/TB[ov];"
            f"[0:v][ov]overlay=0:0:enable='between(t,{t0},{t0 + scene_dur})'[v]",
            "-map", "[v]", "-map", "0:a", "-c:a", "copy",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            str(composited),
        ])
    except Exception as e:
        log("collage", f"Composicion ffmpeg fallo, se sigue sin collage: {e}")
        return video_path

    shutil.copyfile(composited, video_path)
    log("collage", f"Collage de foto real insertado en t={t0:.1f}s ({hit['title']}, {hit['license']})")
    return video_path


def add_real_photo_collages(video_path: Path, subjects: list[dict], out_dir: Path) -> Path:
    """Version multi-sujeto de add_real_photo_collage -- el guion puede listar
    varias fotos reales ({"subject": ..., "time": opcional}) en vez de una
    sola (pedido usuario 21 jul 2026: 'mas stickers/fotos completas'). Si un
    item no trae "time", se reparte automaticamente y en orden a lo largo del
    video (excluyendo el primer/ultimo 12% para no pisar el hook ni el
    cierre), dejando 2.4s de margen entre cada uno para que no se superpongan."""
    if not subjects:
        return video_path
    video_dur = ffprobe_duration(video_path)
    scene_dur = 2.4
    explicit = [s for s in subjects if s.get("time") is not None]
    auto = [s for s in subjects if s.get("time") is None]
    if auto:
        lo, hi = video_dur * 0.12, video_dur * 0.88
        span = max(hi - lo, 0)
        n = len(auto)
        for i, s in enumerate(auto):
            frac = (i + 1) / (n + 1)
            s["_auto_time"] = lo + span * frac

    ordered = sorted(subjects, key=lambda s: s.get("time", s.get("_auto_time", 0)))
    for s in ordered:
        t = s.get("time", s.get("_auto_time"))
        video_path = add_real_photo_collage(video_path, s["subject"], out_dir, collage_time=t)
    return video_path


# ------------------------------------------------------------------- MAIN

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "short"


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un YouTube Short desde un tema")
    parser.add_argument("topic", nargs="?", help="Tema del video (en ingles o espanol)")
    parser.add_argument("--script-file", help="JSON con script/search_terms/title/description (omite Claude)")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--trim-silence", dest="trim_silence", action="store_true",
                        help="recorta las pausas de la narracion antes de calcular escenas "
                             "y subtitulos (edge-tts deja ~0.4s por oracion; medido 13,9%% "
                             "del video). Guarda el original en voice_raw.mp3")
    parser.add_argument("--trim-keep", dest="trim_keep", type=float, default=0.10,
                        help="hueco a conservar en cada silencio (default 0.10s). A 0 las "
                             "palabras se pisan y suena peor que el original")
    parser.add_argument("--rate", default=DEFAULT_RATE)
    parser.add_argument("--clips", type=int, default=None,
                        help=f"escenas del video. Por defecto, UNA POR search_term "
                             f"(regla 1:1 frase<->imagen); {DEFAULT_CLIPS} si el guion no trae.")
    parser.add_argument("--no-pexels", action="store_true", help="Usa gradientes en vez de Pexels")
    parser.add_argument("--no-sfx", action="store_true",
                        help="No coloca efectos de sonido automaticos (requiere ANTHROPIC_API_KEY "
                             "y archivos en assets/sfx/)")
    parser.add_argument("--no-motion", action="store_true",
                        help="Desactiva los graficos de movimiento automaticos (icono+texto "
                             "kinetico via Remotion) que se agregan por cada sfx_cue detectado.")
    parser.add_argument("--no-collage", action="store_true",
                        help="Desactiva la escena de collage con foto real recortada aunque el "
                             "guion tenga 'collage_subject'.")
    parser.add_argument("--sticker-sfx", action="store_true",
                        help="Capa opcional (opt-in, para A/B): un swish de papel suave en el "
                             "frame en que cada sticker hace pop -- el 'sonido del collage "
                             "armandose', motivado por la estetica de recortes. Volumen bajo, "
                             "se omite entero si el music_mood del video es sombrio. NO toca "
                             "pick_sfx_cues (que sigue siendo puramente diegetico).")
    parser.add_argument("--sticker-sfx-file", default=None, metavar="NOMBRE",
                        help="Nombre de archivo dentro de assets/sfx/ para reemplazar el swish "
                             f"de papel por defecto ({STICKER_SFX_DEFAULT}). Para probar de oido "
                             "otro sonido sin tocar el codigo.")
    parser.add_argument("--comfy", action="store_true",
                        help="Genera las imagenes en LOCAL con ComfyUI + FLUX.1-schnell "
                             "(gratis, sin limite de cuota, licencia Apache-2.0 apta para uso "
                             "comercial). No soporta imagen de referencia, asi que NO da "
                             "consistencia de personaje -- ver comfy_client.py.")
    parser.add_argument("--seedream", action="store_true",
                        help="Usa imagenes estaticas generadas con Seedream (ByteDance, via PiAPI) "
                             "en vez de Pexels/gradiente. Es el unico generador de imagenes del "
                             "repo desde el 3 ago 2026. Requiere PIAPI_API_KEY.")
    parser.add_argument("--wan-hero", type=Path, default=None, metavar="PATH",
                        help="Usa un video ya animado localmente (Wan 2.2 via ComfyUI, gratis) "
                             "como escena 0 en vez de generarla; el resto sigue estatico.")
    parser.add_argument("--watermark", default="",
                        help="Texto de marca de agua (esquina superior derecha). Vacio por "
                             "defecto -- especifica explicitamente '--watermark ImPixxel' para "
                             "ese canal (antes el default era 'ImPixxel' fijo y se colaba por "
                             "error en videos de HiddenFacts, ver bug 19 jul 2026).")
    parser.add_argument("--cta-text", default=None,
                        help="Texto de CTA en pantalla (nunca narrado, evita el 'Cliff' de "
                             "retencion del CTA hablado). Requiere --cta-position.")
    parser.add_argument("--cta-position", choices=["start", "middle", "end"], default=None,
                        help="Donde aparece --cta-text: 'start' (~0.5s), 'middle' (mitad del "
                             "video), o 'end' (ultimos ~3.5s). Test de posicion del CTA.")
    parser.add_argument("--punch-index", type=int, default=None, metavar="N",
                        help="Escena (0-indexed) que recibe el zoom 'golpe' para acentuar el "
                             "remate/giro comico. Por defecto la penultima escena.")
    parser.add_argument("--intro-stinger", action="store_true",
                        help="Agrega un whoosh/riser generico en el frame 0 (gancho auditivo "
                             "independiente de la narracion). Test de primeros 2 segundos.")
    parser.add_argument("--subs-lead-ms", type=int, default=0, metavar="MS",
                        help="Adelanta el texto de los subtitulos MS milisegundos respecto al "
                             "audio (no afecta el audio). Test de primeros 2 segundos.")
    parser.add_argument("--split-first-clip", action="store_true",
                        help="Corta la escena 1 en dos mitades (mismo clip) para agregar un "
                             "corte extra de ritmo en el primer segundo. Test de primeros 2 segundos.")
    parser.add_argument("--hook-max", dest="hook_max", action="store_true", default=True,
                        help="Bundle de gancho de los primeros 2s: activa golpe auditivo en "
                             "frame 0 (stinger), texto adelantado 150ms, zoom de entrada fuerte, "
                             "wipe circular de entrada, y el premise card si el guion trae "
                             "'hook_card'. Default ON desde el 19 jul 2026 (paso de test A/B a "
                             "estandar de produccion). Usa --no-hook-max para desactivarlo.")
    parser.add_argument("--no-hook-max", dest="hook_max", action="store_false",
                        help="Desactiva --hook-max (vuelve al comportamiento clasico sin bundle de gancho).")
    parser.add_argument("--hook-card-mode", choices=["overlay", "read"], default="overlay",
                        help="Modo del premise card (campo 'hook_card' del guion): 'overlay' "
                             "(se superpone mientras ya narra) o 'read' (frame congelado 2.2s, "
                             "solo musica/stinger, la narracion arranca despues).")
    parser.add_argument("--archivo", action="store_true",
                        help="Renderiza con el motor visual 'Archivo Vivo' (Remotion, "
                             "collage documental punchy) en vez del ensamblado FFmpeg "
                             "clasico. Requiere imagenes de escena (--seedream/--comfy). "
                             "Ver archivo_engine.py.")
    parser.add_argument("--korex", action="store_true",
                        help="Renderiza con el motor visual de KOREX (Remotion): set fijo "
                             "con parallax, paleta cerrada de 3 tonos + acento por villano, "
                             "personaje troquelado con squash-stretch. Es la piel del canal "
                             "de finanzas satiricas (Tadeo), NO el expediente de HiddenFacts. "
                             "Requiere imagenes de escena (--seedream). Ver korex_engine.py.")
    parser.add_argument("--ideas", action="store_true",
                        help="Genera 5 ideas de tema nuevas (usando topics.txt como referencia) y termina")
    parser.add_argument("--auto", action="store_true",
                        help="Modo automatico: toma el siguiente tema no usado de topics.txt "
                             "(genera mas si se agotan) y corre el pipeline completo. "
                             "Pensado para tareas programadas sin supervision.")
    args = parser.parse_args()

    if args.ideas:
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("ERROR: falta ANTHROPIC_API_KEY. Copia .env.example a .env")
            return 1
        topics_path = ROOT / "topics.txt"
        existing = [
            line.strip() for line in topics_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ] if topics_path.exists() else []
        ideas = generate_ideas(existing)
        print("\nIdeas generadas:")
        for i, idea in enumerate(ideas, 1):
            print(f"  {i}. {idea}")
        print(f"\nAgregalas a topics.txt o corre: py pipeline.py \"{ideas[0]}\"")
        return 0

    if args.script_file:
        data = json.loads(Path(args.script_file).read_text(encoding="utf-8"))
        topic = args.topic or data.get("title", "short")
    elif args.auto:
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("ERROR: falta ANTHROPIC_API_KEY. Copia .env.example a .env")
            return 1
        topic = pick_next_topic()
        log("auto", f"Tema elegido: {topic}")
        try:
            data = with_retries(generate_script, topic)
        except Exception:
            _log_auto_failure(topic)
            return 1
    elif args.topic:
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("ERROR: falta ANTHROPIC_API_KEY (o usa --script-file). Copia .env.example a .env")
            return 1
        topic = args.topic
        data = generate_script(topic)
    else:
        parser.print_help()
        return 1

    if args.seedream and not os.getenv("PIAPI_API_KEY"):
        print("ERROR: falta PIAPI_API_KEY en .env. Registrate en https://piapi.ai y anda a "
              "Workspace > Settings > API Keys.")
        return 1

    base_slug = f"{date.today().isoformat()}-{slugify(topic)}"
    out_dir = OUTPUT_ROOT / base_slug
    # si la carpeta ya existe (o se crea al mismo tiempo por otra corrida en
    # paralelo), es una corrida DISTINTA con el mismo titulo el mismo dia (ej.
    # mismo guion re-generado con --cta-position distinto) -- usar un sufijo
    # incremental en vez de pisar voice.mp3/clips/video.mp4 de la otra corrida.
    # mkdir(exist_ok=False) es atomico a nivel de SO: si dos procesos compiten
    # por el mismo out_dir, solo uno gana la carpeta base y el otro reintenta
    # con el siguiente sufijo (bug real: dos corridas lanzadas en paralelo
    # esta sesion pasaron el chequeo "existe video.mp4" ANTES de que ninguna
    # hubiera escrito el archivo, y terminaron pisandose los inputs a mitad
    # de render).
    suffix = 2
    while True:
        try:
            out_dir.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            out_dir = OUTPUT_ROOT / f"{base_slug}-{suffix}"
            suffix += 1
    _atomic_write_json(out_dir / "script.json", data)

    # SEEDREAM ES EL UNICO GENERADOR (3 ago 2026). Gemini/Nano Banana, Veo, Lyria
    # y la automatizacion de Flow se eliminaron del repo por pedido del usuario;
    # antes Nano Banana ya habia quedado como respaldo al agotarse sus creditos.
    media_source = ("comfy" if args.comfy else
                    "seedream" if args.seedream else
                    ("gradient" if args.no_pexels else "pexels"))

    # --hook-max: bundle de palancas del gancho de los primeros 2s (opt-in, para
    # A/B). Fuerza stinger + texto adelantado + zoom fuerte; el premise card se
    # activa aparte segun 'hook_card' del guion. Sin el flag, nada cambia.
    hook_card = data.get("hook_card")
    card_duration = data.get("card_duration")
    silent_card_mode = bool(card_duration) and not data.get("script")
    # silent_card_mode: el usuario pidio explicitamente CERO efectos (sin wipe de
    # entrada, sin stinger, sin zoom) -- que se vea practicamente como una imagen
    # fija (feedback 20 jul 2026). El bundle --hook-max no aplica aca.
    intro_stinger = (args.intro_stinger or args.hook_max) and not silent_card_mode
    hook_strong = args.hook_max and not silent_card_mode
    subs_lead = args.subs_lead_ms or (150 if args.hook_max else 0)
    # offset de subs: 2.2s en modo 'read' (narracion arranca tras el card), 1s en
    # 'overlay' (nuevo, feedback 20 jul 2026 -- dar tiempo de leer antes de narrar)
    card_read = bool(hook_card) and args.hook_card_mode == "read"
    subs_offset = 2200 if card_read else (1000 if hook_card else 0)

    # card_duration + sin 'script': modo "solo lectura", sin narrador -- un card
    # de texto denso (mas largo de lo que la narracion permitiria a ritmo de
    # habla) se queda fijo TODA la duracion; el video es corto (tipico 7s) y
    # apuesta a que el viewer no termine de leer en un solo pase y deje que
    # YouTube lo repita solo (loop nativo) para terminar de leer -- pedido
    # 20 jul 2026 tras ver que el ultrashort narrado limita el texto a ~18-20
    # palabras por el ritmo de habla (2.3-2.6 palabras/seg).

    try:
        if silent_card_mode:
            words = []
            audio_path = out_dir / "voice.mp3"
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                 "-t", f"{card_duration:.2f}", "-q:a", "9", "-acodec", "libmp3lame",
                 str(audio_path)])
            ass_path = generate_subtitles(words, out_dir, lead_ms=0, offset_ms=0,
                                          keywords=data.get("caption_keywords"))
            audio_dur = float(card_duration)
            durations = [audio_dur]
            n_clips = 1
        else:
            _check_pacing(data["script"])
            _check_script_lint(data["script"], data.get("title", ""), args.voice,
                               search_terms=data.get("search_terms"))
            _check_open_hook(data["script"], data.get("title", ""),
                               data.get("hook_card", "") or "")
            _check_hook_beats(data["script"])
            _check_payoff_spacing(data["script"], data.get("payoffs"))
            _check_relleno_inicial(data["script"])
            _check_ventana_critica(data["script"], data.get("payoffs"))
            _check_but_therefore(data["script"])
            _check_sentence_rhythm(data["script"])
            audio_path, words = with_retries(generate_audio, data["script"], args.voice, args.rate, out_dir)
            # El recorte va AQUI, entre la voz y todo lo demas: los subtitulos y
            # las duraciones de escena se calculan despues, asi que ambos salen
            # ya sobre el eje recortado. Hacerlo al final (sobre el video ya
            # armado) desincroniza las imagenes hasta 7s -- medido 30 jul 2026.
            if args.trim_silence:
                audio_path, words = trim_silence_inplace(
                    audio_path, words, keep=args.trim_keep)
            ass_path = generate_subtitles(words, out_dir, lead_ms=subs_lead, offset_ms=subs_offset,
                                          keywords=data.get("caption_keywords"))

            audio_dur = ffprobe_duration(audio_path)
            # UNA ESCENA POR search_term (28 jul 2026). Antes se fijaba a
            # DEFAULT_CLIPS=10 y los terminos sobrantes se DESCARTABAN en
            # silencio: un guion de 13 frases perdia las 3 ultimas imagenes,
            # que son justo el pago (la consecuencia visible hoy) y el eco de
            # apertura que cierra el loop. El prompt exige 1:1 frase<->termino,
            # asi que truncar aqui rompe una regla dura del canal.
            n_clips = args.clips or len(data.get("search_terms") or []) or DEFAULT_CLIPS
            durations = _scene_boundaries(words, n_clips, audio_dur)
            if card_duration:
                # script presente PERO se pidio una duracion fija de card (caso
                # hibrido, poco comun) -- fuerza la duracion total en vez de la
                # derivada de la narracion.
                audio_dur = float(card_duration)
                durations = [audio_dur]

        clips = acquire_media(data["search_terms"], n_clips, durations,
                              out_dir, media_source=media_source,
                              punch_index=args.punch_index, style=data.get("style") or HIDDENFACTS_STYLE,
                              static=bool(data.get("caption_text")) or silent_card_mode,
                              character_terms=data.get("character_terms"),
                              hook_strong=hook_strong,
                              wan_hero_path=args.wan_hero)

        if args.korex and not silent_card_mode:
            # Motor KOREX (3 ago 2026): piel propia del canal de finanzas
            # satiricas. NO reusa Archivo Vivo porque ese es el expediente de
            # HiddenFacts (polaroid REAL / EXHIBIT B / N. de caso) y sobre un
            # mapache comico se lee absurdo. Ver korex_engine.py.
            import korex_engine
            final = korex_engine.render_from_parts(
                out_dir, data, [(ws, w) for ws, _we, w in words], audio_path)
        elif args.archivo and not silent_card_mode:
            # Motor "Archivo Vivo" (23 jul 2026): la composicion Remotion
            # manifest-driven reemplaza ensamblado FFmpeg + ASS + stickers +
            # collage (ver archivo_engine.py y memoria estilo-archivo-vivo)
            import archivo_engine
            final = archivo_engine.render_from_parts(
                out_dir, data, [(ws, w) for ws, _we, w in words], audio_path)
        else:
            sfx_cues_full = ([] if (args.no_sfx or silent_card_mode) else
                        pick_sfx_cues(words, tone=data.get("music_mood"),
                                      script=data.get("script"),
                                      search_terms=data.get("search_terms")))
            sfx_cues = [(t, p) for t, p, _ in sfx_cues_full]
            # silent_card_mode (sin narrador, card de texto largo): NO generar musica
            # propia -- estos videos se pensaron para reemplazar la musica con un
            # audio trending del nicho, agregado a mano en el editor de Shorts de
            # Studio (ver memoria musica-trending-videos-solo-lectura).
            final = assemble(clips, audio_path, ass_path, out_dir,
                              music_mood=(None if silent_card_mode else data.get("music_mood")),
                              sfx_cues=sfx_cues,
                              durations=durations, watermark=args.watermark or None,
                              cta_text=args.cta_text, cta_position=args.cta_position,
                              intro_stinger=intro_stinger,
                              split_first_clip=args.split_first_clip,
                              caption_header=data.get("caption_header"),
                              caption_text=data.get("caption_text"),
                              caption_keywords=data.get("caption_keywords"),
                              hook_card=hook_card, hook_card_mode=args.hook_card_mode,
                              hook_punch=hook_strong)

            # stickers automaticos (21 jul 2026): UNO por escena (search_term), no
            # atado a sfx_cues -- mas denso, y cada uno intenta foto real recortada
            # antes de caer a emoji (ver HISTORIAL_MEJORAS.md). No aplica al modo
            # silent_card_mode (sin escenas narradas) ni si el usuario paso --no-motion.
            if not silent_card_mode and not args.no_motion:
                final = add_scene_stickers(final, data["search_terms"], durations, out_dir, words=words,
                                           sticker_sfx=args.sticker_sfx, tone=data.get("music_mood"),
                                           sticker_sfx_file=args.sticker_sfx_file)

            # collage de foto real (21 jul 2026): campo del guion 'collage_subjects'
            # (lista de {"subject", "time" opcional}) o el viejo 'collage_subject'
            # singular (compatibilidad) -- ver add_real_photo_collages().
            collage_subjects = data.get("collage_subjects")
            if collage_subjects is None and data.get("collage_subject"):
                collage_subjects = [{"subject": data["collage_subject"], "time": data.get("collage_time")}]
            if collage_subjects and not args.no_collage and not silent_card_mode:
                final = add_real_photo_collages(final, collage_subjects, out_dir)
    except Exception:
        if args.auto:
            _log_auto_failure(topic)
        raise

    (out_dir / "title.txt").write_text(data["title"], encoding="utf-8")
    (out_dir / "description.txt").write_text(data["description"], encoding="utf-8")

    if args.auto:
        _mark_topic_used(topic)

    log("done", f"Video listo: {final}")
    log("done", f"Titulo: {data['title']}")
    return 0


def _log_auto_failure(topic: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"fail_{date.today().isoformat()}.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().isoformat()}] Tema: {topic}\n")
        f.write(traceback.format_exc())
    log("auto", f"FALLO registrado en {log_path} (el tema NO se marca como usado; se reintentara)")


if __name__ == "__main__":
    sys.exit(main())
