"""Actualiza giros_ganadores.md y hipotesis.json con datos REALES de YouTube.

Existe porque un registro de "lo que funciona" mantenido a mano se queda
desactualizado -- y porque ya paso una vez hoy que un video (storage-headstone)
se publico sin que quedara registrado en la conversacion.

    py actualizar_giros.py              # lista estado de los 5 videos trackeados
    py actualizar_giros.py --escribir   # ademas reescribe la tabla en giros_ganadores.md

No inventa nada: si la API todavia no tiene la curva, queda "sin datos aun".
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import youtube_api as Y  # noqa: E402

# video_id -> (nombre interno, duracion de referencia usada solo para verificar
# identidad, estructuras de giro de giros_ganadores.md)
TRACKEADOS = {
    "UsfXWdu8Hwo": ("the-visitor-log", "G1"),
    "RtpFVz0OCx0": ("family-group-chat", "G1, G4, G5, G6"),
    "JKWewZot6As": ("storage-unit-headstone", "G1, G2, G3, G6"),
    "2FUAvwi5_xI": ("christening-announcement", "G1, G2, G3, G5, G6"),
}
# wedding-photos-father: sin video_id, no publicado todavia

# Ventana critica de PLAN_SEGUNDO_6.md: si la caida ahi baja de 45 a <20 puntos,
# el arreglo de montaje (corte de plano + premio 5-10s) funciono.
VENTANA = (5.5, 10.0)
EXITO_MAX_CAIDA = 20.0


def curva(an, vid, dur):
    r = an.reports().query(
        ids="channel==MINE", startDate="2026-07-01", endDate="2026-08-05",
        metrics="views,engagedViews,averageViewPercentage", filters=f"video=={vid}",
    ).execute()
    resumen = r.get("rows", [[0, 0, 0]])[0]
    c = an.reports().query(
        ids="channel==MINE", startDate="2026-07-01", endDate="2026-08-05",
        metrics="audienceWatchRatio", dimensions="elapsedVideoTimeRatio",
        filters=f"video=={vid}", sort="elapsedVideoTimeRatio",
    ).execute()
    puntos = [(t * dur, w * 100) for t, w in c.get("rows", [])]
    return resumen, puntos


def en(puntos, s):
    if not puntos:
        return None
    return min(puntos, key=lambda p: abs(p[0] - s))[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--escribir", action="store_true")
    args = ap.parse_args()

    yt = Y.get_youtube_client("mindcheckpoint")
    an = Y.get_analytics_client("mindcheckpoint")
    ids = list(TRACKEADOS)
    meta = {v["id"]: v for v in yt.videos().list(
        part="snippet,contentDetails,status", id=",".join(ids)).execute()["items"]}

    filas = {}
    print(f"{'video':<28} {'estado':<10} {'vistas':>7} {'%visto':>7} {'caida 5,5-10s':>14}")
    for vid, (nombre, estructuras) in TRACKEADOS.items():
        m = meta.get(vid)
        if not m:
            filas[nombre] = "no encontrado en el canal"
            continue
        priv = m["status"]["privacyStatus"]
        dur_s = int(re.match(r"PT(?:(\d+)M)?(?:(\d+)S)?", m["contentDetails"]["duration"])
                    .group(1) or 0) * 60 + int(re.match(r"PT(?:(\d+)M)?(?:(\d+)S)?",
                    m["contentDetails"]["duration"]).group(2) or 0)
        if priv != "public":
            print(f"{nombre:<28} {priv:<10} {'—':>7} {'—':>7} {'—':>14}")
            filas[nombre] = f"{priv}, sin datos publicos"
            continue

        resumen, puntos = curva(an, vid, dur_s)
        v = resumen[0]
        if not v:
            print(f"{nombre:<28} {'public':<10} {'—':>7}   Analytics aun no procesa esto")
            filas[nombre] = "publico, Analytics sin procesar aun"
            continue

        avp = resumen[2]
        a, b = en(puntos, VENTANA[0]), en(puntos, VENTANA[1])
        caida_txt = "sin curva"
        if a is not None and b is not None:
            caida = a - b
            veredicto = "OK (<20)" if caida < EXITO_MAX_CAIDA else "SIGUE ROTA"
            caida_txt = f"{caida:+.1f}pts {veredicto}"
            filas[nombre] = (f"publicado, {int(v)} vistas, {avp:.1f}% visto, "
                             f"caida 5,5-10s: {caida:.1f}pts ({veredicto})")
        else:
            filas[nombre] = f"publicado, {int(v)} vistas, {avp:.1f}% visto, sin curva por segundo"
        print(f"{nombre:<28} {'public':<10} {int(v):>7} {avp:>6.1f}% {caida_txt:>14}")

    filas.setdefault("wedding-photos-father", "sin publicar")

    if not args.escribir:
        print("\n(solo lectura -- pasa --escribir para volcar esto a giros_ganadores.md)")
        return

    orden = ["christening-announcement", "family-group-chat", "storage-unit-headstone",
             "wedding-photos-father", "the-visitor-log"]
    estructuras_por_nombre = {n: e for _id, (n, e) in TRACKEADOS.items()}
    estructuras_por_nombre["wedding-photos-father"] = "G1, G2, G6"

    filas_md = ["| Vídeo | Estructura(s) | Estado |", "|---|---|---|"]
    for n in orden:
        filas_md.append(f"| `{n}` | {estructuras_por_nombre.get(n, '?')} | {filas.get(n, 'sin dato')} |")
    tabla_nueva = "\n".join(filas_md)

    p = ROOT / "giros_ganadores.md"
    texto = p.read_text(encoding="utf-8")
    patron = re.compile(r"\| Vídeo \| Estructura\(s\) \| Estado \|\n\|---\|---\|---\|\n"
                        r"(?:\|.*\|\n?)*", re.MULTILINE)
    if not patron.search(texto):
        print("\nAVISO: no encontre la tabla en giros_ganadores.md, no se escribio nada.")
        return
    texto = patron.sub(tabla_nueva + "\n", texto)
    p.write_text(texto, encoding="utf-8")
    print("\ngiros_ganadores.md actualizado con datos reales.")


if __name__ == "__main__":
    main()
