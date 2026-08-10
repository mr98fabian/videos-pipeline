"""Biblioteca de clips animados de Flow, para no volver a pagarlos.

Animar cuesta ~100 creditos por clip de 8s (el 4 ago 2026 una sola tanda dejo
la cuenta en 846 -> 6), asi que un clip generado es un activo, no un archivo
temporal de una corrida. Aqui se guardan TODOS: los que se usaron y tambien los
que se descartaron por no corresponder a su escena, porque esos siguen siendo
metraje valido -- simplemente estaban en el sitio equivocado (el grafico
desplomandose salio asi y es de lo mejor que ha dado el motor).

Dos formas de reusar:

- **Automatica, por imagen.** Si un clip se genero a partir de EXACTAMENTE la
  misma imagen (mismo sha1), se reusa solo y sin gastar creditos. Es lo que
  pasa al re-montar un video: las escenas que no cambiaron no se re-animan.
- **Manual, por concepto.** `py clip_library.py --find grafico` lista lo que
  hay sobre ese tema para meterlo a mano en otro video. No es automatico a
  proposito: un clip de otra escena NO casa con la imagen de esta, y la puerta
  de calidad (korex_qa) lo marcaria como incoherente, que es justo lo que debe
  hacer.

    py clip_library.py --seed     # recoge los fx_*.mp4 que haya en output/
    py clip_library.py --list
    py clip_library.py --find flecha
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "assets" / "cache" / "flow_clips"
MANIFEST = LIB / "manifest.json"


def _load() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _save(data: dict) -> None:
    LIB.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(MANIFEST)


def _sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _duration(path: Path) -> float:
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout.strip()
        return round(float(out), 2)
    except Exception:
        return 0.0


def store(
    clip: Path, term: str = "", source_img: Path | None = None, note: str = ""
) -> str | None:
    """Archiva un clip. Devuelve su id, o None si ya estaba."""
    clip = Path(clip)
    if not clip.exists() or clip.stat().st_size == 0:
        return None
    data = _load()
    cid = _sha1(clip)[:16]
    if cid in data:
        return cid
    LIB.mkdir(parents=True, exist_ok=True)
    dst = LIB / f"{cid}.mp4"
    if not dst.exists():
        shutil.copyfile(clip, dst)
    data[cid] = {
        "file": dst.name,
        "term": term,
        "img_sha1": _sha1(Path(source_img))
        if source_img and Path(source_img).exists()
        else "",
        "dur": _duration(clip),
        "note": note,
    }
    _save(data)
    return cid


def lookup_by_image(img: Path) -> Path | None:
    """Clip generado a partir de esta MISMA imagen. Reuso seguro: sigue
    casando con la escena, asi que la puerta de calidad lo da por bueno."""
    img = Path(img)
    if not img.exists():
        return None
    h = _sha1(img)
    for cid, meta in _load().items():
        if meta.get("img_sha1") == h:
            p = LIB / meta["file"]
            if p.exists():
                return p
    return None


def find(query: str) -> list[tuple[str, dict]]:
    q = (query or "").strip().lower()
    return [
        (cid, m)
        for cid, m in _load().items()
        if not q or q in (m.get("term", "") + " " + m.get("note", "")).lower()
    ]


def seed_from_outputs() -> int:
    """Recoge los fx_*.mp4 que ya existan en output/, con el search_term de su
    escena. Sirve para no perder lo ya pagado."""
    nuevos = 0
    for folder in sorted((ROOT / "output").glob("*")):
        script = folder / "script.json"
        if not script.is_dir() and script.exists():
            try:
                terms = (
                    json.loads(script.read_text(encoding="utf-8")).get("search_terms")
                    or []
                )
            except Exception:
                terms = []
        else:
            terms = []
        for clip in sorted((folder / "clips").glob("fx_[0-9]*.mp4")):
            try:
                idx = int(clip.stem.split("_")[1])
            except ValueError:
                continue
            img = clip.parent / f"nb_{idx}.png"
            cid = store(
                clip,
                term=terms[idx] if idx < len(terms) else "",
                source_img=img if img.exists() else None,
                note=f"{folder.name} escena {idx}",
            )
            if cid:
                nuevos += 1
    return nuevos


def main() -> int:
    if "--seed" in sys.argv:
        print(f"{seed_from_outputs()} clips en la biblioteca")
    if "--find" in sys.argv:
        q = sys.argv[sys.argv.index("--find") + 1]
        rows = find(q)
    elif "--list" in sys.argv or "--seed" in sys.argv:
        rows = find("")
    else:
        print(__doc__)
        return 1
    print(f"\n{len(rows)} clip(s) en {LIB}:")
    for cid, m in rows:
        print(
            f"  {cid}  {m['dur']:>5.1f}s  {m.get('note', '')[:38]:38}  "
            f"{(m.get('term') or '(sin term)')[:70]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
