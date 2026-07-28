# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A faceless YouTube Shorts pipeline: topic in, vertical video (1080x1920@30fps, subtitles burned in) out, with automated upload/tracking. Runs three channels from one codebase:

- **HiddenFacts** (`--account default`, English): historical secrets/hoaxes/espionage, sepia 1990s-Nickelodeon-toon style. Primary/active channel — nearly all work goes here.
- **ImPixxel** (`--account impixxel`, Spanish/LATAM): League of Legends gaming content + "Skick" meme character. Currently paused (see project memory) — do not proactively propose ImPixxel work unless asked.
- **Comment/viral channel** (`viral_lab.py`, separate flow): commentary over third-party viral clips (fitness, English-learning). Does not use `pipeline.py` at all.

## Commands

```powershell
py -m pip install -r requirements.txt      # deps (Python 3.10+, needs FFmpeg on PATH)
```

Generate a video:
```powershell
py pipeline.py "topic in english or spanish"          # full run via Claude API
py pipeline.py --script-file scripts/<name>.json      # pre-written script, skips Claude
py pipeline.py --auto                                 # picks next unused topic from topics.txt, used for scheduled/unattended runs
py pipeline.py --ideas                                # generate 5 new topic ideas, no video
```
Common flags: `--nanobanana` (Gemini image gen, needs `GEMINI_API_KEY`), `--seedream` (PiAPI/ByteDance image gen, better multi-reference character consistency, needs `PIAPI_API_KEY`), `--flow` (free Google Flow automation via `flow_automation.py`, falls back to `--nanobanana`), `--archivo` (render with the Remotion "Archivo Vivo" engine instead of the classic FFmpeg assembly — requires generated scene images), `--no-pexels`, `--no-sfx`, `--no-motion`, `--watermark ""`, `--hook-max`/`--no-hook-max` (first-2-seconds hook bundle, on by default).

Pre-production (pick *what* to make before making it):
```powershell
py topic_radar.py --days 14 --top 25        # rank topics by ephemeris + channel criteria
py vidiq_tools.py balance                   # free; every other subcommand costs ~5 credits
py vidiq_tools.py radar-terms > vidiq.txt   # outlier titles, one per line
py topic_radar.py --outliers vidiq.txt      # boost topics matching a real outlier
```

Upload + track (always in this order after a video is generated):
```powershell
py youtube_api.py upload output/<folder>/video.mp4 --title "..." --description "..." --tags "..." --privacy unlisted --account default
py track_video.py output/<folder> <video_id> --keyword-score X --title-score Y --outlier-ref "..."
```
`--account` selects the channel/OAuth token (`default` = HiddenFacts, `impixxel` = ImPixxel) across every `youtube_api.py` subcommand (`upload`, `update`, `report`, `top`, `retention`, `search-terms`, `video-metrics`, `comment`). Uploads default to `unlisted`; the user promotes to public manually after reviewing. Uploads under 58s are blocked by default (`min_duration` guardrail in `upload_video`) unless the format is an intentional short one (ultrashort/silent-card/readcard), in which case pass `min_duration=None` when calling the function directly — there is no CLI flag for it.

After a video goes public, `py post_question_comment.py output/<folder>` posts the description's A/B question as a channel comment (pinning it is still a manual click in Studio). Running it on a private/scheduled video does nothing useful.

Analyze performance:
```powershell
py performance_report.py                      # all accounts in video_log.csv
py performance_report.py --account impixxel   # one channel
```

One-time sticker library setup (shared across channels):
```powershell
py sticker_library.py --list          # see catalog / what's missing
py sticker_library.py --generate      # generate missing ones (Nano Banana)
```

Double-click `generar_video.bat` runs `--auto` and logs to `logs/run_<date>.log` / `logs/fail_<date>.log` (failed topics are NOT marked used, so a rerun retries the same topic).

There is no automated test suite, linter, or build step — validation is `py -c "import ast; ast.parse(open('pipeline.py',encoding='utf-8').read())"` for syntax and manual smoke runs (e.g. `pipeline.py --no-pexels --no-sfx`) end to end.

## Architecture

Five-stage pipeline, all orchestrated from `main()` in [pipeline.py](pipeline.py):

1. **SCRIPT** — Claude API (`MODEL = claude-opus-4-8`) generates `script`, `search_terms` (one per sentence — hard 1:1 rule), `title`, `description`, `music_mood`, `hook_card` via a JSON schema tool call (`_claude_json_call`). Skipped with `--script-file` (used for hand-written videos in `scripts/*.json`).
2. **AUDIO** — `edge-tts` (or Kokoro TTS in `tools/kokoro_tts/`) synthesizes voice + word-level timestamps.
3. **MEDIA** — one image/clip per scene, selected by `media_source`: `pexels` (default, stock footage) → `gradient` (`--no-pexels` fallback, no API key needed) → `nanobanana` (Gemini image gen) → `seedream` (PiAPI/ByteDance, better character consistency) → `flow` (free Google Flow browser automation, falls back to nanobanana). Named-character scenes (LoL champions, Skick) reuse a cached multi-pose "character sheet" instead of the raw splash art for style consistency (see `_get_character_sheet`/`_get_named_character_sheet`).
4. **SUBS** — word-level `.ass` subtitles (Hormozi-style), burned in.
5. **ASSEMBLY** — two mutually exclusive renderers:
   - *Classic (default)* — pure FFmpeg (`assemble()`): 1080x1920 CRF 21 / AAC 192k, plus optional SFX cues (`pick_sfx_cues`, matched to `music_mood` so tone never clashes), scene stickers (`add_scene_stickers`), real-photo collages (`add_real_photo_collages`), CTA text, watermark, and the `--hook-max` first-2-seconds bundle (stinger + advanced subs + zoom + wipe + premise card).
   - *"Archivo Vivo" (`--archivo`)* — [archivo_engine.py](archivo_engine.py) hands the already-produced artifacts (scene images, TTS timestamps, script JSON) to the Remotion composition `ArchivoVideo`, which renders kinetic captions from the real TTS timestamps (no burned ASS), coverage-based cutout-vs-pinned-photo treatment, date stamps, optional `visual_beats` from the script JSON, and the franchise closer; FFmpeg only muxes voice + music at the end.

Output lands in `output/<date>-<slug>/`: `video.mp4`, `title.txt`, `description.txt`, `script.json` (auditable), plus intermediates (`voice.mp3`, `subs.ass`, `clips/`). Folder collisions (same topic same day) get an incremental `-2`/`-3` suffix rather than overwriting — `mkdir(exist_ok=False)` is the atomicity guard for concurrent scheduled+manual runs.

State files at repo root (all gitignored, treated as runtime data not code): `used_topics.json` (never repeat a topic in `--auto`), `gemini_usage.json` (cost tracking), `video_log.csv` (every upload, written by `track_video.py`, consumed by `performance_report.py`), `token.json`/`token_impixxel.json` (per-channel OAuth), `vidiq_key.txt`.

`motion_graphics/` is a separate Remotion (React) project — `npm install` inside that directory, not part of the Python dependency chain. It hosts both the older standalone overlays (`MotionOverlay.jsx`, `RealCollage.jsx`, `Proof*.jsx`) and `src/archivo/` (the full Archivo Vivo engine, `components.jsx` + `ArchivoVideo.jsx`), which `archivo_engine.py` drives via `npx remotion render`.

### Key modules
- [pipeline.py](pipeline.py) — everything above; the one large file (~2950 lines, functions occasionally >100 lines — accepted tradeoff, see `MEJORAS_CODIGO.md` #18).
- [archivo_engine.py](archivo_engine.py) + [visual_cache.py](visual_cache.py) — the Archivo Vivo bridge, and the derived-asset cache (rembg cutouts keyed by file SHA-1, country maps, textures) so a re-render costs zero API calls and zero re-segmentation. It runs standalone on an already-produced folder: `py archivo_engine.py output/<folder>`.
- [youtube_api.py](youtube_api.py) — upload/update/analytics via YouTube Data + Analytics API v3. Retries transient errors (429/500/503) via `_yt_execute`; hard-fails on real usage errors (400/404) with a readable message instead of a raw traceback. Publish-time guardrails: `_check_publish_spacing` (min 30 min between public videos), `_check_publish_window` (advisory good-posting-window warning, HiddenFacts-only signal — ImPixxel's timing data is contaminated by paid ads) and `_check_duplicate_title`.
- [viral_lab.py](viral_lab.py) — the commentary-channel flow, an independent 6-step CLI: `find` (ranked niche candidates) → `get` (download + provenance sheet, quality gate on source resolution/bitrate) → `read` (Gemini video analysis + faster-whisper + PySceneDetect → `analysis.json`) → `script` → `edit` (Chatterbox voice `am_michael` by default) → `qa`. The load-bearing field of the analysis is `not_visible`: narrating what the viewer can already see is the format's #1 retention killer.
- [topic_radar.py](topic_radar.py) — crosses Wikipedia "On this day" ephemerides with the channel's validated criteria (nameable villain, niche theme, round anniversary, penalize saturated topics) into a ranked shortlist. For Shorts the feed dominates (~96.7% of HiddenFacts traffic), so the target is resonance + freshness, not keyword SEO.
- [vidiq_tools.py](vidiq_tools.py) — direct JSON-RPC client for `mcp.vidiq.com/mcp` using the API key, so outliers/transcripts/comments work even when the session's vidIQ MCP fails to load or in unattended runs.
- [sticker_library.py](sticker_library.py) — generates/matches the shared sticker catalog (`assets/stickers/`) keyed by narration keyword, reused by `pipeline.py`'s scene-sticker step.
- [track_video.py](track_video.py) / [performance_report.py](performance_report.py) — logging and cross-referencing production metadata (style, keyword/title research scores) against real YouTube Analytics.
- [flow_automation.py](flow_automation.py) — Playwright browser automation for free image gen via Google Flow (session persisted after `--login`).
- [rankings.py](rankings.py) — separate "Top N" format built from third-party YouTube clips via yt-dlp; imports helpers straight from `pipeline.py`. On-screen + description credit to the source channel is non-optional.
- `tools/kokoro_tts/`, `tools/chatterbox_tts/` — embedded TTS engines with their own `uv` environments; not installed by `requirements.txt`.
- `scripts/*.json` — one file per hand-written video (`script`, `search_terms`, `title`, `description`, `music_mood`, `style`). HiddenFacts scripts always reuse the same fixed sepia/Nickelodeon `style` string unless a change is explicitly requested.

### Script rules encoded in the prompt (do not soften them)
`SCRIPT_PROMPT` in `pipeline.py` carries hard rules derived from measured channel data, not style preferences. Before rewording that prompt, know why each exists:
- **The script must loop.** The last sentence closes on the hook's key words so a restart has no perceptible seam. Measured 26 jul 2026: the only looped video holds a 3.76 → 2.89 audience ratio; videos closing with a summary ("and so…", "that is how…") drop to 0.95 and 0.08.
- **The last `search_term` must chain into the first** — same place/light/framing, a later moment, so the visual loop matches the lexical one.
- **Black Tom template.** Anchor on a famous icon the viewer recognizes instantly and whose consequence is still visible today ("still closed", "to this day"). If a topic has no such anchor, find another angle on the same event rather than shipping without one.
- **No cold-open.** `COLD_FRAMES = 0` in `archivo_engine.py` — the 0.73s CLASSIFIED card was removed because the stay/scroll decision happens before second 1. Set it >0 to restore.
- **No closer either.** `CLOSE_TAIL = 0` — the CASE #N / share-card / SUBSCRIBE tail ran ~3.7s *after* the last spoken word, announcing "it's over" exactly where the loop must be invisible. The video now hard-cuts on the final word so the restart splices into frame 0. The closing `<Sequence>` in `ArchivoVideo.jsx` only mounts if the manifest actually has a tail.
- **190-200 words, 60-65s.** edge-tts at +8% speaks ~3.15 wps. The prompt used to say "110-130 words / 40-50s", which silently produced 40s videos and contradicted the channel's 60s minimum — fixed 27 jul 2026 in all three places the prompt mentioned it.
- **The visual style is a code constant, not a model output.** `HIDDENFACTS_STYLE` in `pipeline.py`. `SCRIPT_SCHEMA` never had a `style` property (`additionalProperties: False` blocked it), so `data.get("style")` was dead code and one real video shipped with no sepia/Nickelodeon at all. The style never varies per video, so it must not depend on the model generating it.
- **`generate_script` needs `max_tokens=4000`.** The prompt grew a lot (loop, Black Tom, hook rules); at 2000 the adaptive thinking budget consumed everything before Claude emitted the text block, and all three retries failed every time.

### Shorts 2026 metrics hardcoded in the pipeline (not preferences — distribution thresholds)
Researched 26 jul 2026 and pinned in code so nothing drifts back:
- **Watch time replaced swipe rate as the primary ranking factor**: absolute seconds watched matter more than percentage.
- **Shorts under 15s collapsed in reach** — they cannot clear the absolute watch-time bar even at 100% retention. `SHORTS_HARD_MIN = 15.0` in `youtube_api.py` blocks the upload with no escape (not even `--allow-short`); `viral_lab.MIN_SECONDS = 20` discards the clip *before* producing. This is why this channel's ultrashorts got ~1,400 views and **zero** subscribers each.
- **Sweet spot 30-45s** (`SHORTS_SWEET_MIN/MAX`), retention >70% triggers wide distribution and >75% triples reach to new audiences, first-3s swipe-away <25% healthy / >40% broken hook.
- **`BEST_HOUR = 6` UTC**, measured from this channel's own healthy period: median ~1,234 views at 05:00-07:00 vs ~158 at 20:00.
- **`_check_duplicate_title` blocks re-uploading a title already on the channel.** A real incident: the Coca-Cola short ended up uploaded four times and three other videos twice, splitting the views of the channel's best-performing content across copies. YouTube allows it silently, so the guard has to live here.

### The opening 2 seconds (Archivo Vivo)
Measured "stayed to watch" was 43.9%, far below the 60% where distribution collapses (70-90% is the good band). Three changes, all in the engine:
- **Frame 0 must move** — a static frame is a scroll target. Scene 1 opens tight (×1.34) and pushes out over ~0.5s, so there is motion from the very first frame regardless of the image.
- **The full promise is written at frame 0** — `HookText` paints the hook card above the subject for ~1.5s. The karaoke caption builds word by word and has said nothing yet by the time the viewer has already decided. Two things cost an iteration each: no scale pop (it made the text invisible on the one frame that decides) and use the first *complete sentence* (truncating at 8 words left "…on a spy", promising without delivering).
- **Nothing before the voice** — no intro card, no logo, no music-only lead-in.

### Archivo Vivo visual layer (27 jul 2026)
- **6 rotating cut transitions** cycling by scene index (light sweep L→R, film burn, sweep R→L, vertical paper wipe, dry impact flash, dark ink wipe). One repeated transition across 10 scenes reads as a mechanical tic. All are ~16 frames — hard cuts, never slow dissolves. None use `screen` blend: the engine's cards are near-white paper and white-on-white is invisible (that was the v1 bug).
- **Background boil** — a fast 1-2px jitter layered on top of the existing slow drift, simulating hand-drawn frame-to-frame wobble. A "still" background reads as digital and dead even with camera parallax.
- **No projected shadow.** It was added and removed the same day: duplicating/skewing the cutout under the feet produced a dirty smudge over the light paper card. `DIE_CUT` already carries the correct hard shadow — the channel's language is a cut-out sticker on paper, not a 3D figure.
- **Stock greenscreen effects** (`stock_effects.py`): 10 categories (fire/water/smoke/explosion/rain/lightning/snow/sparks/fog/dust) fetched once from the Pixabay API (free, commercial use, no attribution), chroma-keyed to real alpha with FFmpeg and cached for life in `assets/cache/effects/`. `archivo_engine` maps the narration of each scene to a category with the same word-boundary regex pattern as `_ACTION_KW` and composites real footage instead of only the drawn FX — screen blend for fire/sparks, lighten for water/smoke. Fails silently with no library, never blocks a render. Note: Pixabay 403s urllib's default User-Agent.

### Validated external references — faceless long-form (28 jul 2026, research only, nothing shipped)
Every number below was verified with vidIQ, not taken from the source video (`a1zBbJ1A22k`, which is an academy sales funnel and inflates earnings ~5x — it claims ">$5,000/mo" for a channel vidIQ estimates at $1,052).
- **`@behindthethroneofficial` — the closest thing to HiddenFacts in long-form.** 13.1k subs, 13 videos, 40-45 min each, one video at 290k views, +182% views / +42% subs in 30 days. Its title formula *is* the Black Tom template written long: famous anchor + one concrete brutal consequence — "Lincoln's First Lady — Locked in an Asylum by Her Own Son". Stock images, faceless, zero Shorts.
- **`@thedarkhorizonyt`** (natural disasters, 35.6k subs, 24 videos, ~16 min, 265k avg views) — same production floor, shorter format.
- **The "money" line is the highest-RPM extension of this channel's existing formula**, but only told as narrative. Economy-as-explainer is a graveyard: `@theforgottenfortunes` 33 videos → 915 total views, `@wheninhistorycreations` 32 videos → 1.3k avg. Narrative money-history grows: `@truthfinance0.1` 18 videos → 261k avg, +31% in 30d. Viable topics are the ones that already fit Black Tom (Enron, the 1929 crash, Madoff, Weimar hyperinflation, Bre-X): famous icon, nameable villain, consequence still visible today — and they land in the finance advertiser pool.
- **What this implies for the code:** none of these channels needs the Archivo Vivo engine. The classic FFmpeg path (Pexels + TTS + Ken Burns) already covers ~90% of that production style; what's missing is a 5,000-word script mode and an image cadence for 30-40 min, not a new renderer. No long-form decision has been taken — do not assume it, and do not scale the Shorts pipeline to long-form unprompted.

### Cross-cutting conventions worth knowing before editing
- `sys.stdout.reconfigure(encoding="utf-8")` is forced at the top of every entry-point script — Windows Task Scheduler otherwise inherits cp1252 and a title/comment with an emoji crashes the run *after* API credits are already spent.
- JSON state (`used_topics.json`, character-sheet manifest, `gemini_usage.json`) is written via `_atomic_write_json` (tmp file + `os.replace`) because scheduled runs and manual runs can race.
- `run()` (subprocess) and `ffprobe_duration()` always pass a `timeout=` — an unattended scheduled run must never hang forever on a stuck ffmpeg/ffprobe.
- Any FFmpeg concat segment must be re-encoded, never `-c copy`, unless a keyframe is guaranteed at the cut — that exact bug silently truncated four finished videos to 23.6s.
- `drawtext` inputs (watermark, CTA text) go through `_drawtext_escape()` — unescaped `, : % {}` breaks the ffmpeg filtergraph or allows expression injection.
- External API calls (Pexels, Nano Banana, Veo, Lyria) fail soft to a known fallback by design (broad `except Exception` is intentional there, not an oversight).
- Per-channel config (voices, style defaults, watermark, publish window) is still hardcoded inline rather than factored into a `config.py` — accepted for now.
- Never regenerate an already-uploaded video to apply a new rule, even while it is still private; improvements start with the next script.

### The documentation corpus
~20 Spanish `.md` files at the root hold the channel strategy, not code docs. The ones that actually get consulted:
- `HISTORIAL_MEJORAS.md` — the chronological research → change → where-it-shipped → hypothesis log. **Append an entry here whenever a change affects the output of a video.**
- `RETENTION_CHECKLIST.md` + `EDICION_GUIONES.md` — script/editing rules; `FORMATOS_A_PROBAR.md` — the numbered backlog of formats to test.
- `PROGRESO_CANAL.md` / `MEJORAS_CANAL.md` — channel state and pending levers; `MEJORAS_CODIGO.md` — known code debt with numbered items.
- `GUIONES_SKICK.md`, `FORMATOS_IMPIXXEL.md`, `IMPIXXEL_HOOK_GUIDE.md`, `HUMOR_GAMER.md` — ImPixxel-only (paused channel).
