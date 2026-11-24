"""Crea las playlists de KOREX y reparte el catalogo entero dentro.

Por que existe: una playlist **posiciona en busqueda por si misma** y encadena
reproduccion, que es el punto 2 del metodo de Romuald (ver ESCUELA_ROMUALD.md).
El canal no tenia ninguna, y `track_video.py` avisaba en cada subida de que el
video "no matcheo ninguna playlist".

El titulo de cada playlist ES una keyword medida con vidIQ, no un nombre bonito:
por eso "Como salir de deudas sin ganar mas dinero" y no "Deudas". El primer
video de cada lista es el que mas vistas tiene, porque es el que la sostiene.

    py organizar_playlists.py --dry-run     # que haria, sin tocar nada
    py organizar_playlists.py               # crea y reparte

Idempotente: si ya existe una playlist con ese titulo la reusa, y no vuelve a
anadir un video que ya este dentro.
"""

from __future__ import annotations

import sys

sys.stdout.reconfigure(encoding="utf-8")

ACCOUNT = "korex"

# playlist -> (descripcion, [fragmentos de titulo, en el orden de reproduccion])
# El orden importa: primero el ancla (mas vistas), luego de mas concreto a mas
# general. Los fragmentos se comparan en minusculas y sin acentos.
PLAYLISTS: dict[str, tuple[str, list[str]]] = {
    "💸 Cómo salir de deudas sin ganar más dinero": (
        "Todo lo que hay que entender para salir de deudas cuando el sueldo no "
        "sube: por dónde empezar, qué pasa si dejas de pagar, y por qué el pago "
        "mínimo está diseñado para que nunca termines. Explicado desde cero con "
        "Tadeo el mapache. Canal KoreX.",
        [
            "salir de deudas y dejar de",       # el ancla: 9.682 vistas
            "como se sale de deudas sin ganar",
            "que pasa si dejas de pagar la tarjeta",
            "solo pagas el minimo",
            "esclavo favorito de tu banco",
            "error matematico que te mantiene pobre",
        ],
    ),
    "🪙 Cómo ahorrar dinero si ganas poco": (
        "A dónde se va el dinero cuando no compras nada grande, cuánto guardar "
        "de verdad y por qué ahorrar mientras debes puede costarte dinero. "
        "Explicado desde cero con Tadeo el mapache. Canal KoreX.",
        [
            "a donde se va tu quincena",
            "tu quincena no se va en la renta",
            "cuanto tengo que ahorrar",
            "interes compuesto no te va a salvar",
            "secreto de los lacras",
        ],
    ),
    "🦝 Pelando cable: la serie": (
        "La serie de KoreX sobre el dinero de todos los días, capítulo a "
        "capítulo. Tadeo el mapache aprende a fuerza de equivocarse.",
        [
            "solo pagas el minimo",
            "cuando te piden plata prestada",
        ],
    ),
    "📜 Historias de dinero que parecen mentira": (
        "Burbujas, bonos de trescientos años y fortunas perdidas por mirar al "
        "vecino. Historia del dinero contada en un minuto con Tadeo el mapache. "
        "Canal KoreX.",
        [
            "papel de 1648",
            "flor costar mas que una casa",
            "newton perdio su fortuna",
            "hombre mas rico de babilonia",
        ],
    ),
}


def _norm(s: str) -> str:
    tabla = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")
    return s.translate(tabla).lower()


def main() -> int:
    dry = "--dry-run" in sys.argv
    import youtube_api as y

    yt = y.get_youtube_client(ACCOUNT)

    # catalogo entero del canal (subidas), con su titulo
    subidas = y._yt_execute(
        yt.channels().list(part="contentDetails", mine=True)
    )["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    videos: list[tuple[str, str]] = []
    page = None
    while True:
        r = y._yt_execute(
            yt.playlistItems().list(
                part="snippet", playlistId=subidas, maxResults=50, pageToken=page
            )
        )
        for it in r.get("items", []):
            videos.append(
                (it["snippet"]["resourceId"]["videoId"], it["snippet"]["title"])
            )
        page = r.get("nextPageToken")
        if not page:
            break
    print(f"catalogo: {len(videos)} videos")

    # playlists que ya existen, para no duplicarlas
    existentes: dict[str, str] = {}
    page = None
    while True:
        r = y._yt_execute(
            yt.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=page)
        )
        for it in r.get("items", []):
            existentes[it["snippet"]["title"]] = it["id"]
        page = r.get("nextPageToken")
        if not page:
            break

    for titulo, (desc, fragmentos) in PLAYLISTS.items():
        pid = existentes.get(titulo)
        recien_creada = False
        print(f"\n== {titulo}")
        if pid:
            print(f"   (ya existia: {pid})")
        elif dry:
            print("   [dry-run] se crearia")
            pid = None
        else:
            pid = y.create_playlist(titulo, desc, "public", account=ACCOUNT)
            recien_creada = True

        # Que videos ya estan dentro, para no repetirlos. Una playlist RECIEN
        # creada esta vacia por definicion y ademas tarda unos segundos en ser
        # consultable: preguntar por sus items devuelve 404 y tumbaba el script
        # justo despues de crearla.
        dentro: set[str] = set()
        if pid and not recien_creada:
            page = None
            while True:
                r = y._yt_execute(
                    yt.playlistItems().list(
                        part="snippet", playlistId=pid, maxResults=50, pageToken=page
                    )
                )
                for it in r.get("items", []):
                    dentro.add(it["snippet"]["resourceId"]["videoId"])
                page = r.get("nextPageToken")
                if not page:
                    break

        for frag in fragmentos:
            f = _norm(frag)
            match = next((v for v in videos if f in _norm(v[1])), None)
            if not match:
                print(f"   SIN ENCONTRAR: '{frag}'")
                continue
            vid, vtit = match
            if vid in dentro:
                print(f"   ya estaba: {vtit[:52]}")
                continue
            if dry:
                print(f"   [dry-run] anadiria: {vtit[:52]}")
                continue
            y.add_video_to_playlist(pid, vid, account=ACCOUNT)
            print(f"   anadido:   {vtit[:52]}")

    print("\nListo." if not dry else "\nDry-run: no se toco nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
