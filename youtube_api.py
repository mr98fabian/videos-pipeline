"""Integracion con YouTube Data API v3 (subida) y YouTube Analytics API (metricas).

Requiere client_secret.json (OAuth Desktop app, ver README) en la raiz del proyecto.
La primera vez que se use cualquier funcion de este modulo se abre el navegador para
autorizar; el token queda cacheado en token.json y se reusa/renueva despues.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Windows con tarea programada suele heredar stdout en cp1252; un titulo/comentario
# con emoji o caracter fuera de ese charset lanza UnicodeEncodeError al imprimir.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
CLIENT_SECRET_PATH = ROOT / "client_secret.json"


def _parse_yt_time(s: str) -> datetime:
    """Parsea un timestamp de la API de YouTube ('...Z') a datetime aware UTC.
    Unifica las 3 copias sueltas de '.replace(\"Z\",\"+00:00\")'."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _yt_execute(request, tries: int = 3, delay: float = 5.0):
    """Ejecuta un request de googleapiclient con reintento/backoff ante errores
    transitorios (429 cuota, 500/503 del lado de Google) -- antes cualquier
    .execute() propagaba el HttpError crudo en el primer fallo, incluso cuando
    reintentar unos segundos despues suele resolverlo solo."""
    last_exc: Exception | None = None
    for attempt in range(1, tries + 1):
        try:
            return request.execute()
        except HttpError as e:
            status = getattr(e, "status_code", None) or getattr(e.resp, "status", None)
            transient = status in (403, 429, 500, 503)
            last_exc = e
            if not transient or attempt == tries:
                raise
            print(f"[retry] YouTube API {status} (intento {attempt}/{tries}), "
                  f"reintento en {delay:.0f}s...")
            time.sleep(delay)
    raise last_exc

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # publicar comentarios
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def _token_path(account: str = "default") -> Path:
    """Cada canal (HiddenFacts, ImPixxel, ...) tiene su propio token, porque la
    cuenta de Google [cuenta de Google del proyecto, ver .env local] administra varios canales/marca y
    cada autorizacion de YouTube API queda atada al canal elegido durante el
    consentimiento de Google, no a la cuenta en si."""
    name = "token.json" if account == "default" else f"token_{account}.json"
    return ROOT / name


def _get_credentials(account: str = "default") -> Credentials:
    token_path = _token_path(account)
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_PATH.exists():
                raise SystemExit(
                    f"Falta {CLIENT_SECRET_PATH}. Descargalo desde Google Cloud Console "
                    "(Credenciales > ID de cliente OAuth > Descargar JSON)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def get_youtube_client(account: str = "default"):
    return build("youtube", "v3", credentials=_get_credentials(account))


def get_analytics_client(account: str = "default"):
    return build("youtubeAnalytics", "v2", credentials=_get_credentials(account))


MIN_PUBLISH_GAP_MINUTES = 3 * 60  # 3h. Historial de cambios (19 jul 2026):
# 1) El 18 jul se subieron 12 videos en un dia (35min de separacion) y 5 de esos 12
#    cayeron en 0-view jail real (2-5 vistas) -- se leyo como "la rafaga mata las vistas"
#    y el gap subio a 20h.
# 2) Pero revisando el MISMO lote con mas cuidado: los otros 2 videos de esa tanda
#    (_2b0cUyn4OY y xz362sxj_sA), tambien 35min entre si, MISMO dia, rompieron 1K
#    (1495 y 1226 vistas) -- contradice que la rafaga por si sola sea la causa
#    determinista. Con n=12 es mas probable que sea varianza normal de muestra chica
#    (formato ultra-corto de 6-8s, primeras pruebas de ese formato) que un efecto de
#    espaciado. 20h era mas conservador de lo que los datos sostienen.
# 3) Bajado a 3h: suficiente para no repetir el patron extremo de "12 en 35min" (que
#    de todas formas fallo en su mayoria), pero permite probar varios formatos nuevos
#    por dia (ver FORMATOS_A_PROBAR.md) en vez de 1 solo -- prioridad actual. Sirve
#    ademas para mapear el gap exacto real entre publicaciones con datos limpios en
#    vez de asumirlo.
# MAX_PUBLIC_PER_DAY (cap fijo de 3/dia) RETIRADO el 17 jul 2026: probamos deliberadamente
# un 4to video de HiddenFacts (09:30 UTC, dentro de la franja buena) y funciono normal
# (574 vistas) -- el cap nunca fue real, estaba confundido con la franja horaria (ver
# GOOD_WINDOW_* abajo). Los primeros datos (7/14, 7/15) coincidian con "primeros 3 del dia"
# Y "dentro de la franja" al mismo tiempo, sin que hubieramos separado las dos variables.
GOOD_WINDOW_START_HOUR = 1   # UTC -- franja donde HiddenFacts arranca fuerte (~1000+ vistas)
GOOD_WINDOW_END_HOUR = 13    # UTC -- fuera de este rango, arranque lento (recuperable en 24-48h)
# Mejor hora MEDIDA con los propios datos del canal (26 jul 2026, periodo sano
# previo al derrumbe): mediana de vistas por hora de publicacion. 05:00-07:00 es
# el unico bloque de tres horas seguidas por encima de 1.190; 20:00 da 158.
BEST_HOUR = 6

# ===================== METRICAS QUE MANDAN (Shorts 2026) =====================
# Investigado 26 jul 2026. Hardcodeado para no volver a salirnos de lo que el
# algoritmo premia de verdad:
#   - El WATCH TIME sustituyo al swipe rate como factor principal: pesa el tiempo
#     ABSOLUTO visto, no solo el porcentaje.
#   - Los Shorts de MENOS DE 15s se hundieron en alcance en 2026: no superan el
#     umbral de tiempo absoluto ni con 100% de retencion. Por eso los ultracortos
#     de este canal daban vistas pero CERO suscriptores.
#   - Punto dulce 30-45s. Retencion >70% dispara reparto amplio, >75% triplica la
#     probabilidad de llegar a audiencias nuevas.
#   - Swipe-away en los 3 primeros segundos: <25% sano, >40% gancho roto.
SHORTS_HARD_MIN = 15.0    # por debajo, YouTube directamente no reparte
SHORTS_SWEET_MIN = 30.0   # por debajo del punto dulce: aviso
SHORTS_SWEET_MAX = 45.0
RETENTION_WIDE_DISTRIBUTION = 0.70  # el umbral que dispara reparto amplio


def _effective_publish_times(youtube) -> list[datetime]:
    """publishedAt de videos ya publicos + publishAt de videos programados
    (privados con fecha futura), para chequear espaciado real de aparicion
    publica, no solo fecha de subida.

    Usa search().list(order="date") en vez de playlistItems() de la playlist
    de uploads: playlistItems() no garantiza orden por fecha y con maxResults=50
    en un canal con >50 videos historicos puede devolver los mas VIEJOS y
    omitir los ultimos subidos -- justo los que este chequeo necesita ver
    (bug real detectado: Yasuo/Darius/Ping9 no aparecian en la lista)."""
    resp = _yt_execute(youtube.search().list(part="id", forMine=True, type="video",
                                              order="date", maxResults=50))
    ids = [it["id"]["videoId"] for it in resp.get("items", []) if "videoId" in it.get("id", {})]
    if not ids:
        return []
    resp = _yt_execute(youtube.videos().list(part="snippet,status", id=",".join(ids)))
    times = []
    for it in resp.get("items", []):
        status = it.get("status", {})
        snippet = it.get("snippet", {})
        if status.get("privacyStatus") == "public" and snippet.get("publishedAt"):
            times.append(_parse_yt_time(snippet["publishedAt"]))
        elif status.get("publishAt"):
            times.append(_parse_yt_time(status["publishAt"]))
    return times


def _check_publish_spacing(youtube, target_time: datetime) -> None:
    """Bloquea la subida si otro video (ya publico o programado) queda a menos
    de MIN_PUBLISH_GAP_MINUTES del horario objetivo -- ver memoria
    espaciado-publicacion-shorts: publicar seguido aplasta las vistas a un
    digito, confirmado con datos reales del canal."""
    for t in _effective_publish_times(youtube):
        gap = abs((target_time - t).total_seconds()) / 60
        if gap < MIN_PUBLISH_GAP_MINUTES:
            raise SystemExit(
                f"BLOQUEADO: hay otro video publicandose a las {t.isoformat()} "
                f"({gap:.0f} min de diferencia con el horario pedido). "
                f"Minimo {MIN_PUBLISH_GAP_MINUTES} min de espaciado (ver memoria "
                "espaciado-publicacion-shorts -- publicar seguido aplasta las "
                "vistas). Usa --publish-at con otro horario, o sube como "
                "'unlisted'/'private' y programa despues."
            )


def _check_publish_window(target_time: datetime) -> None:
    """AVISO (no bloqueo) si target_time cae fuera de la franja horaria buena
    (GOOD_WINDOW_START_HOUR-GOOD_WINDOW_END_HOUR UTC). No es un bloqueo duro
    porque la evidencia es una correlacion fuerte, no una regla determinista
    (algunos videos fuera de franja igual arrancan bien) -- ver memoria
    espaciado-publicacion-shorts."""
    hour = target_time.hour
    if hour != BEST_HOUR:
        print(f"[aviso] la mejor hora medida del canal es {BEST_HOUR:02d}:00 UTC "
              f"(mediana ~1.234 vistas); 20:00 UTC da ~158. Estas publicando a las "
              f"{hour:02d}:00.")
    if not (GOOD_WINDOW_START_HOUR <= hour < GOOD_WINDOW_END_HOUR):
        print(f"[aviso] {target_time.isoformat()} cae fuera de la franja buena "
              f"({GOOD_WINDOW_START_HOUR:02d}:00-{GOOD_WINDOW_END_HOUR:02d}:00 UTC) -- "
              "arranque probablemente mas lento (ver memoria espaciado-publicacion-shorts). "
              "No es un bloqueo, solo una advertencia.")


def _check_duplicate_title(youtube, title: str) -> None:
    """Bloquea subir un video cuyo titulo YA existe en el canal.

    Nace de un caso real (jul 2026): el mismo short acabo subido CUATRO veces y
    otros tres por duplicado, repartiendo entre copias las vistas de lo que mas
    traccion tenia. Es un error silencioso -- YouTube deja subirlo sin avisar --
    asi que el control tiene que estar aqui."""
    norm = " ".join(title.lower().split())
    try:
        ch = _yt_execute(youtube.channels().list(part="contentDetails", mine=True))
        up = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        ids, tok = [], None
        while True:
            r = _yt_execute(youtube.playlistItems().list(
                part="contentDetails", playlistId=up, maxResults=50, pageToken=tok))
            ids += [i["contentDetails"]["videoId"] for i in r["items"]]
            tok = r.get("nextPageToken")
            if not tok:
                break
        ids = list(dict.fromkeys(ids))
        for i in range(0, len(ids), 50):
            d = _yt_execute(youtube.videos().list(part="snippet", id=",".join(ids[i:i + 50])))
            for v in d["items"]:
                if " ".join(v["snippet"]["title"].lower().split()) == norm:
                    raise SystemExit(
                        f"ERROR: ya existe un video con ese titulo en el canal "
                        f"(https://youtu.be/{v['id']}). Subirlo otra vez parte las "
                        f"vistas entre copias. Cambia el titulo o borra/oculta el otro.")
    except SystemExit:
        raise
    except Exception as e:  # una comprobacion no debe impedir una subida legitima
        print(f"[aviso] no pude comprobar duplicados ({e})")


def next_available_slot(youtube, after: datetime | None = None) -> datetime:
    """Calcula el proximo horario que cumple espaciado (MIN_PUBLISH_GAP_MINUTES)
    -- para que un video generado nunca se quede sin programar por chocar con
    el guardrail: en vez de solo bloquear, esta funcion dice exactamente cuando
    SI se puede subir. Ya no aplica cap diario (ver nota arriba)."""
    if after is None:
        after = datetime.now(timezone.utc)
    existing = _effective_publish_times(youtube)
    candidate = after
    for _ in range(1000):  # tope de seguridad, nunca deberia iterar tanto
        conflict = next((t for t in existing
                          if abs((candidate - t).total_seconds()) / 60 < MIN_PUBLISH_GAP_MINUTES),
                         None)
        if conflict is None:
            return candidate
        candidate = conflict + timedelta(minutes=MIN_PUBLISH_GAP_MINUTES)
    raise RuntimeError("no se encontro horario disponible")


def _video_duration_seconds(video_path: str | Path) -> float | None:
    """Duracion real del archivo via ffprobe, o None si ffprobe no esta
    disponible/falla (nunca bloquea la subida por un problema de tooling,
    solo por una duracion realmente corta)."""
    import subprocess
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
            capture_output=True, text=True, check=True, timeout=30,
        ).stdout.strip()
        return float(out)
    except Exception:
        return None


def upload_video(video_path: str | Path, title: str, description: str,
                  tags: list[str] | None = None, category_id: str = "27",
                  privacy_status: str = "unlisted", account: str = "default",
                  publish_at: str | None = None, default_language: str | None = None,
                  min_duration: float | None = 58.0) -> str:
    """Sube un video. privacy_status: 'private' | 'unlisted' | 'public'.
    publish_at: timestamp ISO 8601 UTC (ej. '2026-07-16T23:00:00Z') para publicacion
    programada -- YouTube exige privacyStatus='private' cuando se usa publishAt;
    el video se hace publico solo el mismo automaticamente a esa hora.
    account: 'default' (HiddenFacts) o 'impixxel' (u otro canal ya autorizado
    con --account, ver _token_path). Devuelve el video_id.
    default_language: idioma del video/audio (ej. 'en', 'es-US'). Si se omite,
    se infiere del account ('default'->'en', 'impixxel'->'es') -- bug real (20
    jul 2026): el default de idioma del CANAL HiddenFacts en Studio estaba en
    'es-US' pese a ser 100% ingles, y como el video nunca mandaba defaultLanguage
    explicito, cada subida heredaba ese default incorrecto silenciosamente.
    Fijarlo aca por video evita depender de la configuracion del canal en Studio.
    min_duration: bloquea la subida si el video final mide MENOS que esto en
    segundos (default 58s, la regla dura del canal). Bug real (22 jul 2026):
    12 videos con guiones de ~15 palabras (en vez de ~150) se generaron y
    publicaron con 5-7s de duracion real -- nada verificaba el VIDEO FINAL
    antes de subir, solo `_check_pacing()` avisaba sobre el guion antes de
    generar el TTS. Pasar min_duration=None o 0 para formatos cortos
    legitimos (ultrashort/silent_card_mode/readcard), nunca por default."""
    if min_duration:
        dur = _video_duration_seconds(video_path)
        if dur is not None and dur < min_duration:
            raise ValueError(
                f"Video de {dur:.1f}s, por debajo del minimo de {min_duration:.0f}s -- "
                f"subida BLOQUEADA (bug real 22 jul 2026: guiones truncados generaron "
                f"12 videos de 5-7s que se publicaron sin que nada los detectara). "
                f"Si este video es un formato corto INTENCIONAL (ultrashort/silent_card/"
                f"readcard), volve a llamar con min_duration=None."
            )
    # SUELO ABSOLUTO, sin escape posible ni con min_duration=None ni --allow-short.
    # En 2026 los Shorts por debajo de 15s dejaron de repartirse: no superan el
    # umbral de tiempo absoluto ni con retencion del 100%. Los ultracortos de este
    # canal lo confirman -- 1.400 vistas y CERO suscriptores cada uno.
    _dur = _video_duration_seconds(video_path)
    if _dur is not None and _dur < SHORTS_HARD_MIN:
        raise ValueError(
            f"Video de {_dur:.1f}s: por debajo de {SHORTS_HARD_MIN:.0f}s YouTube ya no "
            f"reparte Shorts (2026). Subirlo es quemar el hueco del dia. Alarga el guion "
            f"o descarta el clip."
        )
    if _dur is not None and _dur < SHORTS_SWEET_MIN:
        print(f"[aviso] {_dur:.1f}s esta por debajo del punto dulce "
              f"({SHORTS_SWEET_MIN:.0f}-{SHORTS_SWEET_MAX:.0f}s). Reparte, pero con menos "
              f"alcance que un video del doble de largo con la misma retencion.")
    if default_language is None:
        default_language = "es" if account == "impixxel" else "en"
    youtube = get_youtube_client(account)
    _check_duplicate_title(youtube, title)
    if publish_at or privacy_status == "public":
        target = (datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
                  if publish_at else datetime.now(timezone.utc))
        _check_publish_spacing(youtube, target)
        _check_publish_window(target)
    video_status = {"privacyStatus": "private" if publish_at else privacy_status,
                     "selfDeclaredMadeForKids": False}
    if publish_at:
        video_status["publishAt"] = publish_at
    # si se olvida --tags, no dejar el video sin NINGUNA tag (bug real: 8 videos
    # de esta sesion se subieron con tags=[] al llamar upload sin --tags -- sin
    # tags YouTube tiene menos senal textual para clasificarlo). Fallback base
    # minimo, no sustituye tags especificas del tema pero evita el peor caso.
    effective_tags = tags if tags else ["hiddenfacts", "history", "shorts", "truestory"]
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": effective_tags,
            "categoryId": category_id,  # 27 = Education
            "defaultLanguage": default_language,
            "defaultAudioLanguage": default_language,
        },
        "status": video_status,
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    upload_retries = 0
    while response is None:
        try:
            progress, response = request.next_chunk()
        except HttpError as e:
            status = getattr(e, "status_code", None) or getattr(e.resp, "status", None)
            upload_retries += 1
            if status not in (403, 429, 500, 503) or upload_retries > 3:
                raise
            print(f"[retry] upload chunk fallo ({status}), reintento {upload_retries}/3...")
            time.sleep(5)
            continue
        if progress:
            print(f"[upload] {int(progress.progress() * 100)}%")
    video_id = response["id"]
    if publish_at:
        print(f"[upload] listo: https://youtube.com/watch?v={video_id} "
              f"(programado para {publish_at}, privado hasta entonces)")
    else:
        print(f"[upload] listo: https://youtube.com/watch?v={video_id} (privacy={privacy_status})")
    return video_id


def update_video(video_id: str, title: str | None = None, description: str | None = None,
                  tags: list[str] | None = None, account: str = "default") -> None:
    """Actualiza titulo/descripcion/tags de un video ya subido (ej. tras afinar
    con vidIQ despues de la subida)."""
    youtube = get_youtube_client(account)
    resp = _yt_execute(youtube.videos().list(part="snippet", id=video_id))
    items = resp.get("items", [])
    if not items:
        raise SystemExit(f"No se encontro el video {video_id} (id invalido o sin permisos)")
    current = items[0]["snippet"]
    if title is not None:
        current["title"] = title[:100]
    if description is not None:
        current["description"] = description
    if tags is not None:
        current["tags"] = tags
    _yt_execute(youtube.videos().update(part="snippet", body={"id": video_id, "snippet": current}))
    print(f"[update] listo: https://youtube.com/watch?v={video_id}")


def create_playlist(title: str, description: str = "", privacy_status: str = "public",
                     account: str = "default") -> str:
    """Crea una playlist vacia y devuelve su playlist_id."""
    youtube = get_youtube_client(account)
    body = {
        "snippet": {"title": title[:150], "description": description},
        "status": {"privacyStatus": privacy_status},
    }
    resp = _yt_execute(youtube.playlists().insert(part="snippet,status", body=body))
    print(f"[playlist] creada: {title} ({resp['id']})")
    return resp["id"]


def add_video_to_playlist(playlist_id: str, video_id: str, account: str = "default") -> None:
    youtube = get_youtube_client(account)
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    _yt_execute(youtube.playlistItems().insert(part="snippet", body=body))


def get_channel_id(account: str = "default") -> str:
    youtube = get_youtube_client(account)
    resp = _yt_execute(youtube.channels().list(part="id", mine=True))
    items = resp.get("items", [])
    if not items:
        raise SystemExit(f"Cuenta '{account}' sin canal asociado (revisar autorizacion)")
    return items[0]["id"]


def channel_report(start_date: str, end_date: str, channel_id: str | None = None,
                    account: str = "default") -> dict:
    """Metricas agregadas del canal entre dos fechas YYYY-MM-DD:
    views, estimatedMinutesWatched, averageViewDuration, subscribersGained,
    likes, comments, shares."""
    analytics = get_analytics_client(account)
    cid = channel_id or get_channel_id(account)
    resp = _yt_execute(analytics.reports().query(
        ids=f"channel=={cid}",
        startDate=start_date,
        endDate=end_date,
        metrics="views,estimatedMinutesWatched,averageViewDuration,"
                "subscribersGained,likes,comments,shares",
    ))
    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    row = resp.get("rows", [[0] * len(headers)])[0]
    return dict(zip(headers, row))


def top_videos(start_date: str, end_date: str, max_results: int = 10,
                channel_id: str | None = None, account: str = "default") -> list[dict]:
    """Videos ordenados por views en el rango de fechas, con retencion promedio."""
    analytics = get_analytics_client(account)
    cid = channel_id or get_channel_id(account)
    resp = _yt_execute(analytics.reports().query(
        ids=f"channel=={cid}",
        startDate=start_date,
        endDate=end_date,
        metrics="views,averageViewDuration,averageViewPercentage,likes,subscribersGained",
        dimensions="video",
        sort="-views",
        maxResults=max_results,
    ))
    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    return [dict(zip(headers, row)) for row in resp.get("rows", [])]


# Orden importa: primer match gana. Palabras en minuscula, buscadas como
# substring del titulo+descripcion en minuscula -- clasificacion best-effort,
# no perfecta (ver track_video.py log_video para el fallback si no matchea
# ninguna).
PLAYLIST_KEYWORDS: dict[str, list[str]] = {
    "PLRizVB4PvxnQ": [  # Space Race Secrets
        "space", "nasa", "soviet space", "laika", "moon landing", "apollo", "cosmonaut",
    ],
    "PLTV_oX18Ko_k": [  # WWII Secrets & Spies
        "nazi", "hitler", "wwii", "world war ii", "d-day", "codebreak", "bletchley",
        "rommel", "commando", "turing", "ghost army", "gestapo",
    ],
    "PLT5eTA5TAYM0": [  # Cold War Secrets
        "cold war", "soviet", "cia", "kgb", "stalin", "mkultra", "manhattan project",
        "mafia", "northwoods", "cuba", "atomic", "nuclear",
    ],
    "PLeyjdSceljwo": [  # Silenced Truths & Hidden Heroes
        "rejected", "sexis", "radium", "poisoning its workers", "just an actress",
        "freed", "her own freedom",
    ],
    "PLWJd-A6OnC_A": [  # American Heroes & Hidden Genius
        "american soldier", "medal of honor", "american inventor", "american teenager",
        "a company tried to steal", "farm boy",
    ],
    "PLKfjliWPUzKI": [  # Legendary Cons & Unsolved Mysteries
        "con man", "hoax", "scam", "scandal", "mystery", "secret recipe",
        "vikings", "myth", "fraud", "sold an entire country", "didn't exist",
        "invented a scandal", "exposed him",
    ],
}


def classify_playlist(title: str, description: str = "") -> str | None:
    """Devuelve el playlist_id que matchea (primer hit por orden de
    PLAYLIST_KEYWORDS), o None si ninguna palabra clave aparece."""
    text = f"{title} {description}".lower()
    for playlist_id, keywords in PLAYLIST_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return playlist_id
    return None


def auto_add_to_playlist(video_id: str, title: str, description: str = "",
                          account: str = "default") -> str | None:
    """Clasifica por keywords y agrega el video a la playlist que matchea.
    Devuelve el playlist_id usado, o None si no matcheo ninguna (queda para
    asignacion manual)."""
    playlist_id = classify_playlist(title, description)
    if playlist_id is None:
        print(f"[playlist] AVISO: '{title[:50]}...' no matcheo ninguna playlist -- asignar manual")
        return None
    add_video_to_playlist(playlist_id, video_id, account=account)
    print(f"[playlist] agregado a {playlist_id}")
    return playlist_id


def video_metrics_batch(video_ids: list[str], start_date: str = "2015-01-01",
                         end_date: str | None = None, account: str = "default") -> dict[str, dict]:
    """Metricas por video para una lista puntual de video_ids (a diferencia de
    top_videos, que trae el ranking de TODO el canal) -- pensado para cruzar
    contra video_log.csv en performance_report.py: cada video ya tiene su
    topic/estilo/keyword_score guardado, esto le suma como le fue de verdad.
    Devuelve {video_id: {metric: valor}}; video sin datos (muy nuevo, sin
    vistas) simplemente no aparece en el dict.

    Tambien intenta impressions/impressionsClickThroughRate (aproximacion mas
    cercana a 'viewed vs swiped away' de Shorts que expone la API publica --
    Studio muestra VVSA pero esa metrica puntual NO esta documentada en la
    Analytics API; si el pedido falla se sigue sin esas 2 columnas en vez de
    frenar todo el reporte)."""
    from datetime import date
    if not video_ids:
        return {}
    analytics = get_analytics_client(account)
    cid = get_channel_id(account)
    end = end_date or date.today().isoformat()
    base_metrics = ("views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
                     "likes,comments,subscribersGained,shares")

    out: dict[str, dict] = {}
    batch_size = 200  # limite prudente para el valor de filters=video==... (no documentado con precision)
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i + batch_size]
        try:
            resp = _yt_execute(analytics.reports().query(
                ids=f"channel=={cid}", startDate=start_date, endDate=end,
                metrics=base_metrics + ",impressions,impressionsClickThroughRate",
                dimensions="video", filters=f"video=={','.join(batch)}", maxResults=len(batch),
            ))
        except HttpError as e:
            print(f"[metrics] impressions no disponible para esta cuenta/rango ({e}), sigo sin esa columna")
            resp = _yt_execute(analytics.reports().query(
                ids=f"channel=={cid}", startDate=start_date, endDate=end,
                metrics=base_metrics, dimensions="video",
                filters=f"video=={','.join(batch)}", maxResults=len(batch),
            ))
        headers = [h["name"] for h in resp.get("columnHeaders", [])]
        for row in resp.get("rows", []):
            data = dict(zip(headers, row))
            out[data["video"]] = data
    return out


def search_terms(start_date: str, end_date: str, video_id: str | None = None,
                  max_results: int = 15, account: str = "default") -> list[list]:
    """Terminos de busqueda de YouTube que generaron vistas (canal completo, o
    de UN video si se pasa video_id). No existe metrica de impresiones/CTR en
    la Analytics API publica (confirmado con error 400 'Unknown identifier'),
    pero insightTrafficSourceDetail filtrado a YT_SEARCH si funciona -- es la
    misma tabla que Studio muestra en Alcance > Terminos de busqueda."""
    analytics = get_analytics_client(account)
    cid = get_channel_id(account)
    filters = "insightTrafficSourceType==YT_SEARCH"
    if video_id:
        filters += f";video=={video_id}"
    resp = _yt_execute(analytics.reports().query(
        ids=f"channel=={cid}", startDate=start_date, endDate=end_date,
        metrics="views", dimensions="insightTrafficSourceDetail",
        filters=filters, sort="-views", maxResults=max_results,
    ))
    return resp.get("rows", [])


def retention_curve(video_id: str, start_date: str = "2020-01-01",
                     end_date: str | None = None, account: str = "default") -> dict:
    """Curva de retencion de audiencia de UN video: para cada punto del video
    (elapsedVideoTimeRatio 0..1) devuelve audienceWatchRatio (>1 = re-watch de
    ese tramo). Detecta la caida mas fuerte y el punto donde cruza 0.6, mapeado
    a segundos aprox (usar la duracion real del video para interpretar). Requiere
    watch-time suficiente: en videos nuevos/pocas vistas devuelve {'rows': []}.
    """
    from datetime import date
    analytics = get_analytics_client(account)
    cid = get_channel_id(account)
    resp = _yt_execute(analytics.reports().query(
        ids=f"channel=={cid}",
        startDate=start_date,
        endDate=end_date or date.today().isoformat(),
        metrics="audienceWatchRatio,relativeRetentionPerformance",
        dimensions="elapsedVideoTimeRatio",
        filters=f"video=={video_id}",
    ))
    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    rows = [dict(zip(headers, r)) for r in resp.get("rows", [])]
    if not rows:
        return {"rows": [], "note": "sin datos de retencion (video nuevo o pocas vistas)"}

    ratios = [(r["elapsedVideoTimeRatio"], r["audienceWatchRatio"]) for r in rows]
    ratios.sort(key=lambda x: x[0])
    # caida mas pronunciada entre puntos consecutivos
    biggest_drop = {"at_ratio": None, "drop": 0.0}
    for (r0, w0), (r1, w1) in zip(ratios, ratios[1:]):
        d = w0 - w1
        if d > biggest_drop["drop"]:
            biggest_drop = {"at_ratio": r1, "drop": round(d, 3)}
    # primer punto donde la retencion cae por debajo de 0.6
    below_60 = next((r for r, w in ratios if w < 0.6), None)
    return {
        "rows": rows,
        "biggest_drop": biggest_drop,
        "first_below_0.6": below_60,
        "hint": "multiplica los ratios por la duracion del video (seg) para el "
                "timestamp; el beat/frase del guion en ese segundo es el que hay "
                "que reescribir o acortar.",
    }


def add_comment(video_id: str, text: str, account: str = "default") -> str:
    """Publica un comentario de nivel superior como el canal (engagement bait
    temprano). Devuelve el comment_id. NOTA: la Data API no permite FIJAR el
    comentario -- el pin queda como paso manual de 1 clic en Studio."""
    youtube = get_youtube_client(account)
    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {"snippet": {"textOriginal": text}},
        }
    }
    resp = _yt_execute(youtube.commentThreads().insert(part="snippet", body=body))
    cid = resp["id"]
    print(f"[comment] publicado en {video_id} ({cid}) -- fijalo manual en Studio")
    return cid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YouTube upload / analytics",
        epilog="Si un video_id empieza con '-', antepone '--' antes: "
               "py youtube_api.py update -- -abc123 --title '...'")
    parser.add_argument("--account", default="default",
                         help="'default' = HiddenFacts, 'impixxel' = canal ImPixxel "
                              "(usa su propio token_<account>.json)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_upload = sub.add_parser("upload")
    p_upload.add_argument("video_path")
    p_upload.add_argument("--title", required=True)
    p_upload.add_argument("--description", default="")
    p_upload.add_argument("--tags", default="")
    p_upload.add_argument("--privacy", default="unlisted",
                           choices=["private", "unlisted", "public"])
    p_upload.add_argument("--publish-at", default=None,
                           help="ISO 8601 UTC ej. 2026-07-16T23:00:00Z -- programa la "
                                "publicacion; el video queda privado hasta esa hora")
    p_upload.add_argument("--allow-short", action="store_true",
                           help="Desactiva el bloqueo de duracion minima (58s) -- usar SOLO "
                                "para formatos cortos intencionales (ultrashort/silent_card/"
                                "readcard), nunca por defecto.")

    p_update = sub.add_parser("update")
    p_update.add_argument("video_id")
    p_update.add_argument("--title", default=None)
    p_update.add_argument("--description", default=None)
    p_update.add_argument("--tags", default=None)

    p_report = sub.add_parser("report")
    p_report.add_argument("--start", required=True, help="YYYY-MM-DD")
    p_report.add_argument("--end", required=True, help="YYYY-MM-DD")

    p_top = sub.add_parser("top")
    p_top.add_argument("--start", required=True, help="YYYY-MM-DD")
    p_top.add_argument("--end", required=True, help="YYYY-MM-DD")
    p_top.add_argument("--n", type=int, default=10)

    p_ret = sub.add_parser("retention")
    p_ret.add_argument("video_id")

    p_st = sub.add_parser("search-terms")
    p_st.add_argument("--start", required=True, help="YYYY-MM-DD")
    p_st.add_argument("--end", required=True, help="YYYY-MM-DD")
    p_st.add_argument("--video-id", default=None,
                       help="Limita a un video; sin esto es el canal completo")
    p_st.add_argument("--n", type=int, default=15)

    p_vm = sub.add_parser("video-metrics")
    p_vm.add_argument("video_ids", help="separados por coma, ej: abc123,def456")
    p_vm.add_argument("--start", default="2015-01-01")
    p_vm.add_argument("--end", default=None)

    p_com = sub.add_parser("comment")
    p_com.add_argument("video_id")
    p_com.add_argument("--text", required=True)

    args = parser.parse_args()

    if args.cmd == "upload":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        upload_video(args.video_path, args.title, args.description, tags,
                      privacy_status=args.privacy, account=args.account,
                      publish_at=args.publish_at,
                      min_duration=None if args.allow_short else 58.0)
    elif args.cmd == "update":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags is not None else None
        update_video(args.video_id, args.title, args.description, tags, account=args.account)
    elif args.cmd == "report":
        print(json.dumps(channel_report(args.start, args.end, account=args.account),
                          indent=2, ensure_ascii=False))
    elif args.cmd == "top":
        print(json.dumps(top_videos(args.start, args.end, args.n, account=args.account),
                          indent=2, ensure_ascii=False))
    elif args.cmd == "retention":
        print(json.dumps(retention_curve(args.video_id, account=args.account),
                          indent=2, ensure_ascii=False))
    elif args.cmd == "search-terms":
        print(json.dumps(search_terms(args.start, args.end, video_id=args.video_id,
                                       max_results=args.n, account=args.account),
                          indent=2, ensure_ascii=False))
    elif args.cmd == "video-metrics":
        ids = [v.strip() for v in args.video_ids.split(",") if v.strip()]
        print(json.dumps(video_metrics_batch(ids, args.start, args.end, account=args.account),
                          indent=2, ensure_ascii=False))
    elif args.cmd == "comment":
        add_comment(args.video_id, args.text, account=args.account)
