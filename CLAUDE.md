# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A faceless YouTube Shorts pipeline: topic in, vertical video (1080x1920@30fps, subtitles burned in) out, with automated upload/tracking. Runs two channels from one codebase:

- **HiddenFacts** (`--account default`, English): historical secrets/hoaxes/espionage, sepia 1990s-Nickelodeon-toon style. Primary/active channel.
- **ImPixxel** (`--account impixxel`, Spanish/LATAM): League of Legends gaming content + "Skick" meme character. Currently paused (see project memory) — do not proactively propose ImPixxel work unless asked.

## Commands

```powershell
py -m pip install -r requirements.txt      # deps (Python 3.10+, needs FFmpeg on PATH)
```

Generate a video:
```powershell
py pipeline.py "topic in english or spanish"          # full run via Claude API
py pipeline.py --script-file scripts/<name>.json      # pre-written script, skips Claude
py pipeline.py --auto                                 # picks next unused topic from topics.txt, used for scheduled/unattended runs
py pipeline.py --ideas                                 # generate 5 new topic ideas, no video
```
Common flags: `--nanobanana` (Gemini image gen, needs `GEMINI_API_KEY`), `--seedream` (PiAPI/ByteDance image gen, better multi-reference character consistency, needs `PIAPI_API_KEY`), `--flow` (free Google Flow automation via `flow_automation.py`, falls back to `--nanobanana`), `--no-pexels`, `--no-sfx`, `--no-motion`, `--watermark ""`, `--hook-max`/`--no-hook-max` (first-2-seconds hook bundle, on by default).

Upload + track (always in this order after a video is generated):
```powershell
py youtube_api.py upload output/<folder>/video.mp4 --title "..." --description "..." --tags "..." --privacy unlisted --account default
py track_video.py output/<folder> <video_id> --keyword-score X --title-score Y --outlier-ref "..."
```
`--account` selects the channel/OAuth token (`default` = HiddenFacts, `impixxel` = ImPixxel) across every `youtube_api.py` subcommand (`upload`, `update`, `report`, `top`, `retention`, `search-terms`, `video-metrics`, `comment`). Uploads default to `unlisted`; the user promotes to public manually after reviewing. Uploads under 58s are blocked by default (`min_duration` guardrail in `upload_video`) unless the format is an intentional short one (ultrashort/silent-card/readcard), in which case pass `min_duration=None` when calling the function directly — there is no CLI flag for it.

Analyze performance:
```powershell
py performance_report.py                     # all accounts in video_log.csv
py performance_report.py --account impixxel   # one channel
```

One-time sticker library setup (shared across both channels):
```powershell
py sticker_library.py --list          # see catalog / what's missing
py sticker_library.py --generate      # generate missing ones (Nano Banana)
```

Double-click `generar_video.bat` runs `--auto` and logs to `logs/run_<date>.log` / `logs/fail_<date>.log` (failed topics are NOT marked used, so a rerun retries the same topic).

There is no automated test suite, linter, or build step — validation is `py -c "import ast; ast.parse(...)"` for syntax and manual smoke runs (e.g. `pipeline.py --no-pexels --no-sfx`) end to end.

## Architecture

Five-stage pipeline, all orchestrated from `main()` in [pipeline.py](pipeline.py):

1. **SCRIPT** — Claude API (`MODEL = claude-opus-4-8`) generates `script`, `search_terms` (one per sentence — hard 1:1 rule), `title`, `description`, `music_mood`, `hook_card` via a JSON schema tool call (`_claude_json_call`). Skipped with `--script-file` (used for hand-written videos in `scripts/*.json`).
2. **AUDIO** — `edge-tts` (or Kokoro TTS in `tools/kokoro_tts/`) synthesizes voice + word-level timestamps.
3. **MEDIA** — one image/clip per scene, selected by `media_source`: `pexels` (default, stock footage) → `gradient` (`--no-pexels` fallback, no API key needed) → `nanobanana` (Gemini image gen) → `seedream` (PiAPI/ByteDance, better character consistency) → `flow` (free Google Flow browser automation, falls back to nanobanana). Named-character scenes (LoL champions, Skick) reuse a cached multi-pose "character sheet" instead of the raw splash art for style consistency (see `_get_character_sheet`/`_get_named_character_sheet`).
4. **SUBS** — word-level `.ass` subtitles (Hormozi-style), burned in.
5. **ASSEMBLY** — pure FFmpeg (`assemble()`, ~137 lines): 1080x1920 CRF 21 / AAC 192k, plus optional SFX cues (`pick_sfx_cues`, matched to `music_mood` so tone never clashes), scene stickers (`add_scene_stickers`, one per `search_term` from `assets/stickers/` or a real-photo cutout fallback), real-photo collages (`add_real_photo_collages`), CTA text, watermark, and the `--hook-max` first-2-seconds bundle (stinger + advanced subs + zoom + wipe + premise card).

Output lands in `output/<date>-<slug>/`: `video.mp4`, `title.txt`, `description.txt`, `script.json` (auditable), plus intermediates (`voice.mp3`, `subs.ass`, `clips/`). Folder collisions (same topic same day) get an incremental `-2`/`-3` suffix rather than overwriting — `mkdir(exist_ok=False)` is the atomicity guard for concurrent scheduled+manual runs.

State files at repo root (all gitignored, treated as runtime data not code): `used_topics.json` (never repeat a topic in `--auto`), `gemini_usage.json` (cost tracking), `video_log.csv` (every upload, written by `track_video.py`, consumed by `performance_report.py`), `token.json`/`token_impixxel.json` (per-channel OAuth).

`motion_graphics/` is a separate Remotion (React) project used to render kinetic-text/icon overlays that FFmpeg then composites in — `npm install` inside that directory, `npm run render`, not part of the Python dependency chain.

### Key modules
- [pipeline.py](pipeline.py) — everything above; the one large file (~2800 lines, functions occasionally >100 lines — accepted tradeoff, see `MEJORAS_CODIGO.md` #18).
- [youtube_api.py](youtube_api.py) — upload/update/analytics via YouTube Data + Analytics API v3. Retries transient errors (429/500/503) via `_yt_execute`; hard-fails on real usage errors (400/404) with a readable message instead of a raw traceback. Publish-time guardrails: `_check_publish_spacing` (min 30 min between public videos) and `_check_publish_window` (advisory 01:00–13:00 UTC good-posting-window warning, HiddenFacts-only signal — ImPixxel's timing data is contaminated by paid ads).
- [sticker_library.py](sticker_library.py) — generates/matches the shared 200-sticker catalog (`assets/stickers/`) keyed by narration keyword, reused by `pipeline.py`'s scene-sticker step.
- [track_video.py](track_video.py) / [performance_report.py](performance_report.py) — logging and cross-referencing production metadata (style, keyword/title research scores) against real YouTube Analytics.
- [flow_automation.py](flow_automation.py) — Playwright-driven browser automation for free image gen via Google Flow (session persisted after `--login`).
- `scripts/*.json` — one file per hand-written video (`script`, `search_terms`, `title`, `description`, `music_mood`, `style`). HiddenFacts scripts always reuse the same fixed sepia/Nickelodeon `style` string unless a change is explicitly requested.

### Cross-cutting conventions worth knowing before editing
- `sys.stdout.reconfigure(encoding="utf-8")` is forced at the top of every entry-point script — Windows Task Scheduler otherwise inherits cp1252 and a title/comment with an emoji crashes the run *after* API credits are already spent.
- JSON state (`used_topics.json`, character-sheet manifest, `gemini_usage.json`) is written via `_atomic_write_json` (tmp file + `os.replace`) because scheduled runs and manual runs can race.
- `run()` (subprocess) and `ffprobe_duration()` always pass a `timeout=` — an unattended scheduled run must never hang forever on a stuck ffmpeg/ffprobe.
- `drawtext` inputs (watermark, CTA text) go through `_drawtext_escape()` — unescaped `, : % {}` breaks the ffmpeg filtergraph or allows expression injection.
- External API calls (Pexels, Nano Banana, Veo, Lyria) fail soft to a known fallback by design (broad `except Exception` is intentional there, not an oversight).
- Per-channel config (voices, style defaults, watermark, publish window) is still hardcoded inline rather than factored into a `config.py` — accepted until a 3rd channel exists.
