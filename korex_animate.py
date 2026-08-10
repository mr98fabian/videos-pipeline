"""Remonta un video KOREX ya producido: voz, musica con ducking y subtitulos.

**La animacion imagen->video de Flow esta APAGADA por defecto** (3 ago 2026).
El flujo vigente es: imagenes con Flow -> se descargan -> el movimiento lo pone
el motor (Ken Burns / parallax), que es gratis, instantaneo y no falla. Animar
en Flow cuesta ~100 creditos por clip, tarda minutos por escena y falla de
forma intermitente. Con `--animar` se vuelve a activar.

Existe aparte de `pipeline.py --flow-animate` por una razon concreta: el motor
KOREX (Remotion) consume `clips/nb_*.png`, o sea imagenes, y no sabe montar
video. Este script toma la salida ya generada y la vuelve a montar por FFmpeg,
sin regenerar ni una sola imagen ni volver a sintetizar la voz.

    py korex_animate.py output/<carpeta>
    py korex_animate.py output/<carpeta> --voice cb_es   # resintetiza la voz
    py korex_animate.py output/<carpeta> --animar        # anima en Flow (caro)

Cada clip se cachea en `clips/fx_<i>.mp4`: si el script se corta a la mitad, al
relanzarlo solo anima lo que falta. Animar es lo caro (minutos por escena), no
el montaje.

Con `--voice` se vuelve a sintetizar la narracion y **se recalculan los tiempos**:
subtitulos nuevos y duracion nueva de cada escena. Los clips de Flow no se
re-animan (duran 8s, mas que cualquier escena), solo se recortan distinto. Existe
porque una corrida sin `--voice cb_es` cae en el edge-tts ingles por defecto
(`en-US-AndrewNeural`) y lee un guion en espanol: suena a lector de Windows.

La musica sale de assets/music/ con el mismo mezclado que korex_engine: volumen
0.09 y `sidechaincompress` contra la voz (attack 50ms / release 300ms), o sea la
musica se aparta sola cuando Tadeo habla en vez de taparlo.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

FPS = 30
WIDTH, HEIGHT = 1080, 1920
ROOT = Path(__file__).resolve().parent

# CAMARA BLOQUEADA (3 ago 2026). Antes pedia "slow, controlled camera move" y
# era justo el error: en imagen->video el modelo deforma y hace morphing CUANDO
# tiene libertad para mover la camara -- el warp entra por ahi. Si la camara se
# clava y el movimiento sale SOLO del contenido (gesto del personaje, tela,
# polvo, luz), el resultado se lee estable y hecho a mano en vez de "IA".
MOTION_HINT = (
    "LOCKED CAMERA: absolutely no zoom, no pan, no push-in, no drift, "
    "no camera movement of any kind. The frame stays perfectly still. "
    "All motion comes from inside the scene only: subtle character "
    "movement and small secondary motion (fabric, dust, hair, shifting "
    "light). The character stays exactly on model, same design, same "
    "style. No morphing, no cuts, no new text appearing."
)


def run(cmd: list[str], timeout: int = 1800) -> None:
    subprocess.run(
        cmd,
        check=True,
        timeout=timeout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def clip_matches_source(clip: Path, img: Path, tol: float = 26.0) -> bool:
    """¿El clip animado ES esta escena, o Flow se inventó otra cosa?

    Verificación imprescindible, no paranoia: en imagen->video Flow ignora a
    veces la referencia y genera desde el texto (salieron un señor
    fotorrealista en una casa de empeño y un magnate en 3D, ninguno de este
    vídeo), y otras veces devuelve el clip de OTRA escena. Los dos fallos son
    silenciosos: el mp4 es válido y dura lo que toca.

    Como Flow arranca el vídeo en la imagen de partida, el primer fotograma de
    un clip legítimo se parece mucho a la imagen; uno inventado, nada. Se
    comparan en 64x64 en gris, que aguanta el reencuadre y el grano pero no
    que cambie la escena entera.
    """
    frame = clip.with_suffix(".chk.png")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                "0.1",
                "-i",
                str(clip),
                "-frames:v",
                "1",
                str(frame),
            ],
            check=True,
            timeout=120,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        from PIL import Image
        import numpy as np

        def thumb(p):
            with Image.open(p) as im:
                return np.asarray(im.convert("L").resize((64, 64)), dtype=float)

        diff = float(np.abs(thumb(frame) - thumb(img)).mean())
        return diff <= tol
    except Exception as e:
        print(f"    (no pude comparar {clip.name}: {e})")
        return True  # ante la duda no se descarta un clip que puede ser bueno
    finally:
        frame.unlink(missing_ok=True)


def scene_images(clips: Path) -> list[Path]:
    """Mismo orden que usa korex_engine.build_manifest, para que la escena i del
    manifest y la imagen i sean la misma. Ojo: la numeracion puede tener huecos
    (una escena que no se genero), asi que se ordena por el numero real."""
    return sorted(clips.glob("nb_*.png"), key=lambda p: int(p.stem.split("_")[1]))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    argv = sys.argv[1:]
    new_voice = None
    if "--voice" in argv:
        k = argv.index("--voice")
        new_voice = argv[k + 1]
        del argv[k : k + 2]

    # Emocion de la narracion. Chatterbox saca la prosodia del clip de
    # referencia; con exaggeration bajo lee plano, "sin vida". Se exponen para
    # poder comparar de oido, que es la unica forma de calibrar esto.
    def _num(flag, default):
        nonlocal argv
        if flag in argv:
            k = argv.index(flag)
            v = float(argv[k + 1])
            del argv[k : k + 2]
            return v
        return default

    exag = _num("--exag", None)
    cfg = _num("--cfg", None)
    margin_v = int(_num("--margin", 380))
    out_dir = Path(argv[0]).resolve()
    clips = out_dir / "clips"
    manifest_path = clips / "korex_manifest.json"
    voice = out_dir / "voice.mp3"
    subs = out_dir / "subs.ass"
    for p in (manifest_path, voice):
        if not p.exists():
            print(f"falta {p}")
            return 1

    man = json.loads(manifest_path.read_text(encoding="utf-8"))
    man = man.get("manifest", man)
    scenes = man["scenes"]
    imgs = scene_images(clips)

    data = {}
    script_json = out_dir / "script.json"
    if script_json.exists():
        data = json.loads(script_json.read_text(encoding="utf-8"))
    terms = data.get("search_terms") or []

    # Mismo proyecto de Flow que uso pipeline.py para este guion: animar es otra
    # corrida, no otro video (ver flow_projects.py). Se ata por el titulo porque
    # aqui no llega el nombre del --script-file.
    try:
        import flow_projects

        flow_projects.use_project(data.get("title") or out_dir.name)
    except Exception as e:
        print(f"[flow] no pude atar el proyecto (no critico): {e}")

    # PUERTA DURA: montar con escenas faltantes es peor que no montar. La corrida
    # del 4 ago perdio nb_2 y el video salio con 11 de 12 sin que se notara hasta
    # verlo. Se aborta salvo que se pida explicitamente seguir.
    have = {int(p.stem.split("_")[1]) for p in imgs}
    missing = [i for i in range(len(terms)) if i not in have] if terms else []
    if missing and "--allow-missing" not in argv:
        print(
            f"ABORTADO: faltan las imagenes de las escenas {missing} "
            f"({len(imgs)} de {len(terms)}). Regenerarlas y volver a correr, "
            f"o pasar --allow-missing si de verdad quieres montarlo asi."
        )
        return 1
    if len(imgs) != len(scenes):
        print(
            f"aviso: {len(imgs)} imagenes vs {len(scenes)} escenas en el "
            f"manifest; se usa el minimo"
        )
    n = min(len(imgs), len(scenes))

    sys.path.insert(0, str(ROOT))
    import pipeline as pl
    import flow_automation
    import clip_library

    durations = [s["dur"] / FPS for s in scenes]
    words_for_sfx: list = []
    if new_voice:
        print(f"resintetizando voz con {new_voice}...")
        voice, words = pl.generate_audio(
            data["script"], new_voice, "+8%", out_dir, exaggeration=exag, cfg=cfg
        )
        # margin_v bajo: con Tadeo en cuadro el subtitulo centrado le tapa la
        # cara, y la cara es donde esta la actuacion
        subs = pl.generate_subtitles(
            words, out_dir, margin_v=margin_v, keywords=data.get("caption_keywords")
        )
        # los tiempos cambian con la voz: hay que repartir las escenas otra vez
        # o la imagen deja de caer sobre la frase que la nombra
        durations = pl._scene_boundaries(words, n, pl.ffprobe_duration(voice))
        words_for_sfx = words
        print(f"voz {pl.ffprobe_duration(voice):.1f}s, {len(words)} palabras")

    # IMAGEN->VIDEO DESACTIVADO POR DEFECTO (3 ago 2026, decision del usuario:
    # "deten los videos animados, por ahora solo hacemos las imagenes con flow
    # y le colocamos movimiento con zoom"). El movimiento lo pone el motor
    # (Ken Burns / parallax del motor KOREX), que es gratis, instantaneo y no
    # falla; animar en Flow cuesta ~100 creditos por clip, tarda minutos por
    # escena y falla de forma intermitente. Se reactiva con `--animar`.
    #
    # ANIMAR POR RONDAS (cuando se pide): con un solo intento por escena
    # quedaban 7 de 12 estaticas -- Flow falla intermitentemente, y una escena
    # quieta entre animadas se nota mas que si estuvieran todas quietas. Se
    # insiste solo en las que faltan, igual que korex_fill con las imagenes.
    rondas = 5 if "--animar" in argv else 0

    # SOLO SE ANIMA LA PRIMERA ESCENA (decision del 4 ago 2026). Un clip de
    # Flow cuesta ~100 creditos: doce escenas son la cuota de un mes por video,
    # y aun asi fallan a mitad. El movimiento rinde donde se decide quedarse --
    # el frame 0 -- y el resto lo cubre el Ken Burns, que es gratis y no falla.
    solo_primera = "--animar-todo" not in argv
    for ronda in range(1, rondas + 1):
        faltan = [
            i
            for i in range(n)
            if not (clips / f"fx_{int(imgs[i].stem.split('_')[1])}.mp4").exists()
            and not (solo_primera and i > 0)
        ]
        if not faltan:
            break
        print(f"\n--- animacion, ronda {ronda}/{rondas}: faltan {len(faltan)} ---")
        for i in faltan:
            img = imgs[i]
            idx = int(img.stem.split("_")[1])
            term = terms[idx] if idx < len(terms) else ""
            prompt = f"{term}. {MOTION_HINT}" if term else MOTION_HINT
            fx = clips / f"fx_{idx}.mp4"

            # 1) ¿ya pagamos este clip? Un clip generado a partir de ESTA misma
            # imagen sirve tal cual y cuesta cero creditos (~100 por clip de
            # 8s: una tanda de 12 vacia la cuenta). Ver clip_library.
            reuso = clip_library.lookup_by_image(img)
            if reuso:
                shutil.copyfile(reuso, fx)
                print(
                    f"  {img.name}: reusado de la biblioteca (0 creditos)", flush=True
                )
                continue

            print(f"  animando {img.name} ({durations[i]:.1f}s)...", flush=True)
            ok = flow_automation.animate_image(
                img, prompt, fx, duration_s=int(durations[i]) + 1
            )
            if ok and not clip_matches_source(fx, img):
                # NO se borra: el clip es metraje valido, solo esta en la
                # escena equivocada. Se archiva para poder reusarlo a mano.
                clip_library.store(
                    fx, term=term, note=f"descartado: no casaba con {img.name}"
                )
                fx.unlink(missing_ok=True)
                ok = False
                print(
                    f"  {img.name}: DESCARTADO (no es esta escena; guardado "
                    f"en la biblioteca)",
                    flush=True,
                )
            else:
                if ok:
                    clip_library.store(fx, term=term, source_img=img)
                print(f"  {img.name}: {'OK' if ok else 'falla'}", flush=True)

    estaticas = [
        int(imgs[i].stem.split("_")[1])
        for i in range(n)
        if not (clips / f"fx_{int(imgs[i].stem.split('_')[1])}.mp4").exists()
    ]
    if estaticas:
        print(f"AVISO: quedan estaticas las escenas {estaticas}")

    # hoja de contacto ANTES de montar: escenas arriba, primer fotograma de su
    # clip debajo. Si una columna no casa verticalmente, ese clip esta mal.
    try:
        import korex_qa

        sheet = korex_qa.contact_sheet(out_dir)
        if sheet:
            print(f"hoja de contacto: {sheet}")
        for f in korex_qa.check(out_dir):
            print(f"  QA: {f}")
    except Exception as e:
        print(f"aviso: QA omitido ({e})")

    parts: list[Path] = []
    for i in range(n):
        img = imgs[i]
        idx = int(img.stem.split("_")[1])
        dur_s = durations[i]
        fx = clips / f"fx_{idx}.mp4"
        seg = clips / f"seg_{idx}.mp4"
        if fx.exists():
            # tpad clona el ultimo frame por si el clip de Flow (8s) se queda
            # corto para la escena; el trim posterior lo deja en su duracion
            src, vf = (
                fx,
                (
                    f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                    f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},"
                    f"tpad=stop_mode=clone:stop_duration=3"
                ),
            )
            cmd = ["ffmpeg", "-y", "-i", str(src), "-t", f"{dur_s:.3f}", "-vf", vf]
            cmd += [
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "21",
                "-pix_fmt",
                "yuv420p",
                str(seg),
            ]
            run(cmd)
        else:
            # Sin clip de Flow: Ken Burns, NO un fotograma congelado. Se reusa
            # `_static_image_clip` de pipeline.py, que rota entre 6 movimientos
            # distintos segun el indice para que dos escenas seguidas no se
            # sientan clonadas, y da el "golpe" de zoom en el remate.
            pl._static_image_clip(
                img, dur_s, seg, move=i, punch=(i == n - 2), hook=(i == 0)
            )
        parts.append(seg)

    # concat SIEMPRE reencodeando: con -c copy y sin keyframe en el corte, el
    # video sale truncado (ese bug ya se pago una vez, ver HISTORIAL 20 jul)
    lst = clips / "fx_concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    joined = clips / "fx_joined.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            str(joined),
        ]
    )

    final = out_dir / "video_animado.mp4"
    music = pl._pick_music()

    # SFX: solo donde la narracion NOMBRA el evento sonoro, y con el tono del
    # video (music_mood) para que un efecto comico no caiga en una frase grave.
    # Devolver 0 cues es una respuesta valida, no un fallo.
    cues = []
    if words_for_sfx:
        try:
            cues = pl.pick_sfx_cues(
                words_for_sfx,
                tone=data.get("music_mood"),
                script=data.get("script"),
                search_terms=terms,
            )
        except Exception as e:
            print(f"aviso: SFX omitidos ({e})")

    # Mezcla identica a korex_engine.render_from_parts: la musica va a 0.09
    # (pedido explicito del usuario 30 jul 2026: rango -18/-22dB) y ademas pasa
    # por sidechaincompress disparado por la propia voz, asi que se aparta sola
    # en cada frase en vez de competir con ella. attack 50ms / release 300ms:
    # fila "contenido rapido" de la tabla de ducking (SOUND_DESIGN_RETENCION.md,
    # 9 ago 2026) -- la musica vuelve rapido entre frases staccato.
    inputs = ["-i", str(joined), "-i", str(voice)]
    fc = "[1:a]anull[voice];"
    mix_labels, nmix = [], 0
    if music:
        inputs += ["-i", str(music)]
        fc += (
            "[voice]asplit=2[vmix][vtrig];"
            "[2:a]aloop=loop=-1:size=2e9,volume=0.09[bg0];"
            "[bg0][vtrig]sidechaincompress=threshold=0.03:ratio=8:"
            "attack=50:release=300[bg];"
        )
        mix_labels, nmix = ["[vmix]", "[bg]"], 2
        print(f"musica: {music.name}")
    else:
        fc += "[voice]anull[vmix];"
        mix_labels, nmix = ["[vmix]"], 1
        print("aviso: assets/music/ vacio, va sin musica")

    for k, (t, sfx_path, trigger) in enumerate(cues):
        idx_in = len(inputs) // 2
        inputs += ["-i", str(sfx_path)]
        ms = max(int(t * 1000), 0)
        fc += f"[{idx_in}:a]adelay={ms}|{ms},volume=0.45[sfx{k}];"
        mix_labels.append(f"[sfx{k}]")
        nmix += 1
        print(f"sfx @{t:.1f}s '{trigger}' -> {Path(sfx_path).name}")

    fc += (
        f"{''.join(mix_labels)}amix=inputs={nmix}:normalize=0:"
        # loudnorm -14 LUFS / -1.0 dBTP (estandar de plataformas,
        # SOUND_DESIGN_RETENCION.md) antes del limiter de seguridad.
        f"duration=first,loudnorm=I=-14:TP=-1.0:LRA=11,alimiter[a]"
    )
    # Blanco y negro DURO. El prompt pide gris neutro pero Flow devuelve casi
    # siempre un tono crema/papel, asi que se garantiza aqui. Va ANTES de los
    # subtitulos: si se desatura despues, se lleva por delante el amarillo de
    # la palabra activa y el rojo de las keywords, que son jerarquia de lectura.
    if subs.exists():
        fc = f"[0:v]hue=s=0,subtitles='{subs.as_posix().replace(':', r'\:')}'[v];" + fc
        vmap = "[v]"
    else:
        fc = "[0:v]hue=s=0[v];" + fc
        vmap = "[v]"
    run(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            fc,
            "-map",
            vmap,
            "-map",
            "[a]",
            "-shortest",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-aspect",
            "9:16",
            str(final),
        ]
    )

    flow_automation.close_session()
    print(f"LISTO: {final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
