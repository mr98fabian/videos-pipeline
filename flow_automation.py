"""Automatiza Google Flow (labs.google/fx/tools/flow) via Playwright para
generar imagenes gratis (modelo Nano Banana 2) en vez de pagar la API de
Gemini/PiAPI. Reemplaza la extension de Chrome 'Zappy Flow' (tercero no
verificado, zapiwala.ai) con automatizacion propia sobre la misma pagina --
mismo resultado, sin darle acceso de extension a la cuenta de Google.

Selectores verificados a mano el 20 jul 2026 navegando labs.google/fx/tools/flow
con una cuenta real (locale es-419). La UI de Flow es una SPA con clases CSS
hasheadas (styled-components) que cambian entre builds, por eso los selectores
usan el TEXTO visible de los botones (estable) en vez de clases. Si Google
cambia el idioma/texto de la UI, esto se rompe -- correr con FLOW_DEBUG=1 para
ver la ventana real y el error exacto.

Setup una sola vez:
    playwright install chromium
    python flow_automation.py --login
Abre Chrome con un perfil dedicado (.flow_profile/); logueate en Google ahi
manualmente. La sesion queda cacheada, igual que token.json para YouTube API.

Un proyecto de Flow = un video: se crea una vez por corrida de pipeline.py y
se reusa para todas las escenas (mismo patron que hace un humano a mano),
evita reabrir/reconfigurar aspecto y modelo en cada imagen.

Dos capacidades sobre las que se apoya KOREX (Tadeo consistente escena a
escena):
  - `references=[...]` en generate(): sube imagenes al input file oculto que
    Flow tiene siempre montado (`input[type=file][accept=image/*][multiple]`),
    o sea imagen->imagen. Es lo que replica al personaje y el fondo.
  - `mode="video"` / `animate()`: la misma caja de prompt con la pestana Video
    del panel de configuracion, con la imagen de la escena como referencia =
    imagen->video, una escena a la vez.

El resultado NO se baja por el dialogo de descarga: cada tile expone la URL
directa `labs.google/fx/api/trpc/media.getMediaUrlRedirect?name=<uuid>`, que se
pide con las cookies de la misma sesion. Mucho menos fragil que clickear.

Selectores REVALIDADOS contra el DOM real el 4 ago 2026 (`--inspect`). Lo que
cambio respecto de la version del 20 jul, y que la tenia rota:
  - la caja de prompt no es un <textarea> con placeholder sino un
    `div[role=textbox]`; `get_by_placeholder` no encontraba nada;
  - los botones llevan el nombre de la ligadura de Material Symbols pegado al
    texto visible ('crop_9_16\\n9:16', 'arrow_forward\\nCrear'), asi que se
    buscan por subcadena y no por texto exacto;
  - el chip de modelo abre un panel con pestanas Imagen/Video, 5 aspectos y
    x1..x4, todos con role=tab.
Correr `python flow_automation.py --inspect` cuando Google cambie el build:
vuelca botones/inputs/menus reales a .flow_inspect/.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

FLOW_PROFILE_DIR = Path(__file__).parent / ".flow_profile"
FLOW_URL = "https://labs.google/fx/tools/flow"
DEBUG = bool(os.getenv("FLOW_DEBUG"))
MODEL_NAME = "Nano Banana 2"

# MODELO DE VIDEO: 'Veo 3.1 - Lite' cuesta 10 creditos por generacion, 'Fast'
# 20 y 'Quality' 100 (plan Pro = 1.000/mes). Hasta el 4 ago 2026 el codigo no
# fijaba ninguno y Flow generaba con el default: la cuenta paso de 846 a 6
# creditos en una tarde. Con Lite las mismas doce escenas cuestan 120.
VIDEO_MODEL_NAME = os.getenv("FLOW_VIDEO_MODEL", "Veo 3.1 - Lite")

# Submodo de video. 'Fotogramas' = frames-to-video: tu imagen es el PRIMER
# fotograma y el modelo la anima, con duraciones de 4/6/8s. 'Ingredientes'
# compone una escena NUEVA a partir de referencias y solo hace 8s -- es lo que
# estaba activo por defecto, y por eso salian planos que no eran la escena.
VIDEO_SUBMODE = "Fotogramas"
VIDEO_DURATIONS = (4, 6, 8, 10)

# --- selectores verificados (ver docstring) ---------------------------------
# La UI corre en es-419. Todo lo que se busca por texto usa subcadena porque el
# texto real trae la ligadura del icono delante ('add_2\nCrear').
SEL_PROMPT = "div[role=textbox]"
SEL_SUBMIT = "button:has-text('arrow_forward')"
# El chip que abre el panel de configuracion muestra modelo + aspecto + salidas
# ('🍌 Nano Banana 2\ncrop_16_9\nx2'). El emoji depende del modelo por defecto
# del proyecto (uno nuevo puede abrir en Veo, sin banana), asi que se busca
# primero por la ligadura del icono de aspecto, que esta siempre.
SEL_CONFIG_CHIP_CANDIDATES = (
    "button:has-text('crop_')",
    "button:has-text('🍌')",
)
SEL_FILE_INPUT = "input[type=file][accept='image/*']"
SEL_TILE = "div[role=button]"
MEDIA_URL_PREFIX = "https://labs.google/fx/api/trpc/media.getMediaUrlRedirect"

# Espera minima entre dos envios.
#
# ERA 60s Y NO HACIA FALTA (medido el 3 ago 2026). El valor venia de la corrida
# del 4 ago, donde encadenar sin pausa daba "No se pudo generar" alternando
# (escena 1 OK, 2 fallaba, 4 OK, 5 fallaba) y se leyo como limite de ritmo/cuota.
# No lo era: ese mensaje es TRANSITORIO -- aparece mientras Nano Banana trabaja y
# despues la imagen lo reemplaza -- y `_submit_and_wait` lo tomaba por un fallo
# (ver el comentario de REFUSAL_GRACE_S). Sin pausa, la peticion siguiente pillaba
# el tile transitorio de la anterior; con pausa le daba tiempo a desaparecer. La
# pausa curaba el sintoma de un bug de deteccion, no un limite de Google.
#
# Medicion controlada (misma sesion, mismos 4 prompts por condicion):
#     cooldown  0s -> 4/4 OK, 11s por imagen
#     cooldown 15s -> 4/4 OK, 13s por imagen
#     cooldown 30s -> 4/4 OK, 24s por imagen
# El exito no depende de la pausa; el tiempo, si. Se deja en 5s y no en 0 porque
# la prueba fue de 4 imagenes seguidas, no de una tanda larga, y un colchon
# minimo cuesta nada frente al riesgo (no medido) de que Google limite a volumen
# alto. Subirlo con FLOW_COOLDOWN si algun dia se ve rate-limiting de verdad.
COOLDOWN_S = float(os.getenv("FLOW_COOLDOWN", "5"))
_last_submit = 0.0

# Margen tras ver un aviso "No se pudo generar" antes de darlo por definitivo.
# El tile de error aparece MIENTRAS Nano Banana 2 sigue trabajando y luego la
# imagen buena lo reemplaza; abortar al verlo descartaba generaciones correctas
# (medido el 3 ago 2026: tres pruebas seguidas visibles en Flow y las tres
# reportadas como rechazo). 0 = comportamiento viejo (abortar al instante).
REFUSAL_GRACE_S = float(os.getenv("FLOW_REFUSAL_GRACE", "75"))


def is_logged_in() -> bool:
    return FLOW_PROFILE_DIR.exists() and any(FLOW_PROFILE_DIR.iterdir())


# Google bloquea el login ("este navegador puede no ser seguro") en el Chromium
# empaquetado de Playwright. Con el Chrome real instalado (channel="chrome") y
# sin la bandera de automatizacion, el login pasa. El perfil sigue siendo
# .flow_profile/, aparte del perfil personal de Chrome.
_STEALTH_ARGS = ["--disable-blink-features=AutomationControlled"]


def _launch_ctx(p, *, headless: bool, extra_args: list[str] | None = None):
    args = _STEALTH_ARGS + (extra_args or [])
    for channel in ("chrome", None):
        try:
            return p.chromium.launch_persistent_context(
                str(FLOW_PROFILE_DIR),
                headless=headless,
                channel=channel,
                args=args,
            )
        except Exception as e:
            _log(f"no se pudo abrir con channel={channel}: {e}")
    raise RuntimeError("no hay navegador disponible para Playwright")


def _login() -> None:
    from playwright.sync_api import sync_playwright

    FLOW_PROFILE_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch_ctx(p, headless=False, extra_args=["--start-maximized"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(FLOW_URL)
        print("Inicia sesion en Google en la ventana abierta.")
        print(
            "Cuando veas el dashboard de Flow (proyectos), volve aca y "
            "presiona Enter para guardar la sesion."
        )
        input()
        ctx.close()
    print(f"Sesion guardada en {FLOW_PROFILE_DIR}")


def _log(msg: str) -> None:
    if DEBUG:
        print(f"[flow] {msg}")


_REF_CACHE = Path(__file__).parent / "assets" / "cache" / "flow_refs"


def _flatten_alpha(path: Path) -> Path:
    """Aplana el canal alfa sobre blanco antes de subir la referencia.

    MEDIDO el 4 ago 2026, no es precaucion: Flow contesta 'No se pudo generar'
    cuando la UNICA referencia es un PNG con transparencia. Misma escena, misma
    pose, unica variable el alfa -> RGBA falla, la misma imagen aplanada pasa.
    Las 33 laminas de assets/kx_cast/tadeo/ estan recortadas, asi que fallaban
    casi siempre; solo colaban cuando ademas iba una referencia opaca al lado, y
    eso hacia que el fallo pareciera aleatorio (o de cuota, o de politicas).
    """
    try:
        from PIL import Image

        with Image.open(path) as im:
            if im.mode not in ("RGBA", "LA", "PA") and "transparency" not in im.info:
                return path
            im = im.convert("RGBA")
            import hashlib

            key = hashlib.sha1(path.read_bytes()).hexdigest()[:16]
            _REF_CACHE.mkdir(parents=True, exist_ok=True)
            dst = _REF_CACHE / f"{path.stem}_{key}.png"
            if not dst.exists():
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[3])
                bg.save(dst)
            return dst
    except Exception as e:
        _log(f"no pude aplanar {path.name} ({e}); va tal cual")
    return path


def _match_extension(path: Path, mime: str) -> None:
    """Flow devuelve JPEG aunque el pipeline pida un .png. Guardar bytes JPEG
    en un archivo .png funciona con PIL/ffmpeg (miran el contenido) pero rompe
    cualquier consumidor que confie en la extension, asi que se reencoda."""
    if not path.suffix.lower() in (".png",) or "jpeg" not in mime:
        return
    try:
        from PIL import Image

        with Image.open(path) as im:
            im.convert("RGB").save(path, "PNG")
    except Exception as e:
        _log(f"no pude reencodar a PNG ({e}); queda JPEG dentro de {path.name}")


# Devuelve las URLs de media presentes en la grilla, en orden del DOM. Es la
# huella con la que se detecta "apareci&oacute; algo nuevo": comparar contra el
# conjunto previo es fiable aunque Flow reordene o inserte placeholders, cosa
# que esperar a que desaparezca un "NN%" no era.
_JS_MEDIA_URLS = r"""
() => [...document.querySelectorAll('img, video, source')]
  .map(m => ({tag: m.tagName.toLowerCase(),
              url: m.currentSrc || m.src || m.getAttribute('src') || ''}))
  .filter(m => m.url.includes('media.getMediaUrlRedirect'))
"""

# Que etiqueta tiene que traer el resultado segun el modo. Sin esto, animate()
# se quedaba con la imagen de referencia que la propia subida acaba de meter en
# la grilla y guardaba un JPEG dentro de un .mp4.
_WANT_TAGS = {"image": ("img",), "video": ("video", "source")}
_WANT_MIME = {"image": "image/", "video": "video/"}


class FlowSession:
    """Un proyecto de Flow abierto, reusado para todas las escenas de un
    video. Uso:

        with FlowSession(aspect_ratio="9:16") as flow:
            flow.generate("Tadeo mira la bolsa", Path("s1.png"),
                          references=[Path("assets/kx_cast/tadeo/codicia_1.png")])
            flow.animate(Path("s1.png"), "camara acercandose lento",
                         Path("s1.mp4"))
    """

    def __init__(
        self,
        aspect_ratio: str = "9:16",
        mode: str = "image",
        # x4 POR DEFECTO EN IMAGEN (3 ago 2026). Nano Banana 2 es gratis e
        # ilimitado en el plan Pro, y una tirada es estocastica: el mismo prompt
        # da resultados muy desiguales. Pedir 4 salidas cuesta lo mismo en
        # tiempo y multiplica por 4 las opciones para quedarse con la buena --
        # que es como se puebla la biblioteca de poses de kx_cast, donde cada
        # pose se genera UNA vez en la vida.
        # OJO: en modo VIDEO esto se fuerza a 1 dentro de _configure(); ahi cada
        # salida SI cuesta creditos (~100 por clip) y x4 vaciaria la cuota.
        count: int = 4,
        model: str | None = None,
        project_url: str | None = None,
        headless: bool | None = None,
        duration_s: int | None = None,
    ):
        self.aspect_ratio = aspect_ratio
        self.mode = mode
        self.count = count
        self.model = model
        # duracion del clip; pagar 8s para una escena de 5 es tirar creditos
        self.duration_s = duration_s
        self.project_url = project_url
        # headless NO es el default: Flow es una SPA pesada y el modo headless
        # dispara con mas frecuencia el muro de "navegador no compatible".
        self.headless = (not DEBUG) if headless is None else headless
        self._pw = None
        self._ctx = None
        self._page = None
        self._refs: list[Path] = []
        self._ref_hashes: set[str] = set()
        # ultimo motivo por el que Flow se nego, para que quien llame pueda
        # distinguir "reintentar sirve" de "este prompt no va a pasar nunca"
        self.last_refusal: str = ""

    # -- ciclo de vida -------------------------------------------------------

    def __enter__(self) -> "FlowSession":
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._ctx = _launch_ctx(
            self._pw,
            headless=self.headless,
            extra_args=[] if self.headless else ["--start-maximized"],
        )
        self._page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        self._page.set_default_timeout(20_000)
        self._open_project()
        self._configure(mode=self.mode)
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self._ctx:
                self._ctx.close()
        finally:
            if self._pw:
                self._pw.stop()

    def _open_project(self) -> None:
        page = self._page
        if self.project_url:
            page.goto(self.project_url, timeout=60_000)
        else:
            page.goto(FLOW_URL, timeout=60_000)
            try:
                page.wait_for_load_state("networkidle", timeout=25_000)
            except Exception:
                pass
            page.get_by_text("Proyecto nuevo", exact=False).first.click(timeout=20_000)
        page.wait_for_selector(SEL_PROMPT, timeout=30_000)
        page.wait_for_timeout(2500)
        self.project_url = page.url

    # -- configuracion -------------------------------------------------------

    def _tab(self, needle: str):
        """Pestana del panel de configuracion. El texto real trae la ligadura
        del icono pegada ('crop_9_16\\n9:16'), por eso subcadena y no exacto."""
        return self._page.locator("button[role=tab]", has_text=needle)

    def _config_chip(self, wait_s: int = 30):
        page = self._page
        deadline = time.monotonic() + wait_s
        while time.monotonic() < deadline:
            for sel in SEL_CONFIG_CHIP_CANDIDATES:
                loc = page.locator(sel)
                if loc.count():
                    return loc.last
            page.wait_for_timeout(1000)
        raise RuntimeError(
            "no encontre el chip de configuracion; correr --inspect, Flow "
            "cambio el build"
        )

    def _configure(self, mode: str | None = None) -> None:
        page = self._page
        mode = mode or self.mode or "image"
        self._config_chip().click(timeout=15_000)
        page.wait_for_timeout(1200)

        self._tab("Video" if mode == "video" else "Imagen").first.click(timeout=10_000)
        page.wait_for_timeout(1200)

        if mode == "video":
            # submodo: Fotogramas (imagen como primer frame) en vez de
            # Ingredientes (recompone la escena). Ver comentario en VIDEO_SUBMODE.
            sub = self._tab(VIDEO_SUBMODE)
            if sub.count():
                sub.first.click(timeout=10_000)
                page.wait_for_timeout(800)
            else:
                _log(f"no encontre el submodo '{VIDEO_SUBMODE}'")
            if self.duration_s:
                d = self._tab(f"{self.duration_s}s")
                if d.count():
                    d.first.click(timeout=10_000)
                    page.wait_for_timeout(500)

        # en video cada salida cuesta creditos de verdad: x4 seria pagar cuatro
        # clips para usar uno. El x4 es solo para imagen (ver comentario en count)
        n_out = self.count if mode == "image" else 1
        for needle, click in ((self.aspect_ratio, True), (f"x{n_out}", True)):
            loc = self._tab(needle)
            if click and loc.count():
                loc.first.click(timeout=10_000)
                page.wait_for_timeout(500)
            elif click:
                _log(f"no encontre la pestana '{needle}' en modo {mode}")

        # El dropdown de modelo solo se toca si se pidio uno explicito: Flow ya
        # viene en Nano Banana 2, y en modo Video la lista es otra (Veo). Ojo:
        # hay que buscar la opcion DENTRO del [role=menu] abierto -- el propio
        # boton del dropdown tambien contiene el nombre del modelo, y clickearlo
        # otra vez deja el menu abierto tapando toda la caja de prompt.
        want_model = self.model if mode == "image" else VIDEO_MODEL_NAME
        if want_model:
            try:
                # en modo imagen el chip lleva el emoji; en video lleva el
                # nombre del modelo, asi que se busca el ultimo desplegable
                # del panel abierto
                drop = page.locator("button:has-text('arrow_drop_down')")
                if mode == "image":
                    drop = drop.filter(has_text="🍌")
                drop.last.click(timeout=6000)
                page.wait_for_timeout(1200)
                # las opciones del desplegable son botones con la ligadura
                # 'volume_up' delante ('volume_up\nVeo 3.1 - Lite'); buscar por
                # [role=menu] resuelve al propio boton que lo abre y da timeout
                page.locator("button").filter(has_text=want_model).last.click(
                    timeout=6000
                )
                page.wait_for_timeout(1000)
            except Exception as e:
                _log(f"no pude fijar el modelo '{want_model}': {e}")

        self._close_popovers()
        self.mode = mode

    def _close_popovers(self) -> None:
        """Los paneles de Flow son poppers de Radix: mientras uno queda abierto
        intercepta TODOS los clicks, incluido el de la caja de prompt. Un solo
        Escape no basta cuando hay panel + dropdown encimados."""
        page = self._page
        for _ in range(6):
            if not page.locator("div[data-radix-popper-content-wrapper]").count():
                return
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
        try:  # ultimo recurso: click en una zona muerta del encabezado
            page.mouse.click(620, 8)
            page.wait_for_timeout(500)
        except Exception:
            pass

    def set_mode(self, mode: str) -> None:
        """Cambia entre imagen y video sin reabrir el proyecto."""
        if mode != self.mode:
            self._configure(mode=mode)

    def _reset_prompt(self, mode: str) -> None:
        """Recarga el proyecto para dejar la caja de prompt limpia.

        MEDIDO el 4 ago 2026: sin esto, TODA generacion fallaba la primera vez y
        salia al reintentar. Los ingredientes de la escena anterior se quedan
        enganchados, asi que la escena N+1 se enviaba con 4 referencias (2
        suyas y 2 ajenas) y Flow contestaba 'No se pudo generar'; el fallo
        limpiaba el estado y por eso el reintento funcionaba. Recargar cuesta
        unos segundos y quita la clase entera de fallo.
        """
        page = self._page
        page.goto(self.project_url, timeout=60_000)
        page.wait_for_selector(SEL_PROMPT, timeout=30_000)
        page.wait_for_timeout(3000)
        self.mode = None  # la recarga tambien resetea el panel de configuracion
        self._configure(mode=mode)

    # -- generacion ----------------------------------------------------------

    # Solo el aviso EXACTO del tile fallido. La primera version de este regex
    # llevaba tambien 'error', 'blocked' y 'violates', y disparaba con el blob
    # JSON de Next.js que Flow incrusta en la propia pagina: contaba rechazos
    # inexistentes y tumbo una corrida entera (12/12 a gradiente) por un fallo
    # que nunca ocurrio. Cualquier termino generico que se anada aqui vuelve a
    # romperlo.
    _REFUSAL_RE = r"^(no se pudo generar|couldn'?t generate|no se pudo crear)"

    def _refusals(self) -> list[str]:
        """Avisos de rechazo visibles, buscados SOLO dentro de los tiles de la
        grilla. Se devuelve la lista y no un booleano porque los tiles fallidos
        se quedan ahi: lo que importa es si aparecio uno NUEVO tras enviar, no
        si existe alguno."""
        try:
            return (
                self._page.evaluate(
                    "(args) => {"
                    " const [sel, re] = args;"
                    " const rx = new RegExp(re, 'i'); const out = [];"
                    " for (const tile of document.querySelectorAll(sel)) {"
                    "   for (const e of tile.querySelectorAll('*')) {"
                    "     if (e.children.length) continue;"
                    "     const t = (e.innerText || '').trim();"
                    "     if (t && t.length < 120 && rx.test(t)) { out.push(t); break; }"
                    "   }"
                    " } return out; }",
                    [SEL_TILE, self._REFUSAL_RE],
                )
                or []
            )
        except Exception:
            return []

    def _media(self) -> list[dict]:
        try:
            return self._page.evaluate(_JS_MEDIA_URLS)
        except Exception:
            return []

    def _looks_like_reference(self, path: Path) -> bool:
        """Al enviar el prompt, Flow guarda tambien la imagen de referencia en
        la grilla del proyecto, con una URL igual de nueva que la del
        resultado. Sin este control, generate() devolvia la propia referencia
        recien subida y parecia que habia funcionado."""
        if not self._refs:
            return False
        try:
            data = path.read_bytes()
        except Exception:
            return False
        import hashlib

        if hashlib.sha1(data).hexdigest() in self._ref_hashes:
            return True
        try:  # re-encodada por Flow: comparar pixeles, no bytes
            from PIL import Image, ImageChops, ImageStat

            with Image.open(path) as got:
                got = got.convert("RGB")
                for ref in self._refs:
                    with Image.open(ref) as r:
                        r = r.convert("RGB")
                        if r.size != got.size:
                            continue
                        diff = ImageChops.difference(r, got)
                        if max(ImageStat.Stat(diff).mean) < 2.0:
                            return True
        except Exception as e:
            _log(f"no pude comparar con la referencia: {e}")
        return False

    def _attach_frame(self, image: Path, last: Path | None = None) -> None:
        """Submodo Fotogramas: la imagen va en la ranura de PRIMER fotograma.

        Aqui no existe el selector de ingredientes (`add_2`): hay dos ranuras
        con su propio input de archivo -- la primera es el fotograma inicial y
        la segunda el final. Basta con soltar el archivo en el input; no hay
        que enganchar nada a la instruccion, que es lo que complicaba el modo
        Ingredientes.
        """
        import hashlib

        page = self._page
        img = _flatten_alpha(Path(image).resolve())
        self._refs = [img]
        self._ref_hashes = {hashlib.sha1(img.read_bytes()).hexdigest()}

        # Sobre la caja de prompt aparecen dos ranuras, 'Iniciar' y 'Fin'. Hay
        # que ABRIR la ranura y elegir el asset en el selector; soltar el
        # archivo en el input oculto no la rellena.
        submit = page.locator(SEL_SUBMIT).first
        # la ranura no es un <button> ni lleva role: es un div con el texto
        abierto = False
        for loc in (
            page.get_by_text("Iniciar", exact=True),
            page.locator("button:has-text('Iniciar')"),
            page.locator("[role=button]:has-text('Iniciar')"),
        ):
            if loc.count():
                loc.first.click(timeout=10_000)
                abierto = True
                break
        if not abierto:
            raise RuntimeError("no encontre la ranura 'Iniciar' del primer fotograma")
        page.wait_for_timeout(2500)

        page.locator(SEL_FILE_INPUT).first.set_input_files(str(img), timeout=60_000)
        page.wait_for_timeout(6000)

        # la subida deja el asset repetido en la lista; el ULTIMO es el recien
        # subido, y es el que corresponde a esta escena
        opts = page.locator("[role=option]").filter(has_text=img.name)
        try:
            if opts.count():
                o = opts.last
                if o.get_attribute("aria-selected") != "true":
                    o.click(timeout=8000)
                    page.wait_for_timeout(1500)
        except Exception as e:
            _log(f"no pude seleccionar {img.name}: {e}")

        add = page.locator("button:has-text('Agregar a la instrucción')")
        if add.count():
            for _ in range(20):
                if add.first.is_enabled():
                    break
                page.wait_for_timeout(500)
            add.first.click(timeout=10_000)
            page.wait_for_timeout(3000)

        # OJO con la senal de exito: 'Crear' NO se habilita por tener el
        # fotograma puesto, sino cuando ademas hay texto en el prompt. Usarlo
        # aqui daba un falso "no se cargo" con la miniatura ya en la ranura.
        # La comprobacion real es que la ranura tenga imagen.
        page.wait_for_timeout(2500)
        self._close_popovers()
        try:
            puesto = page.evaluate(
                "() => !!document.querySelector('form img, [class*=frame] img')"
                " || [...document.querySelectorAll('img')].some(i =>"
                "   i.getBoundingClientRect().top > window.innerHeight * 0.7)"
            )
            if not puesto:
                _log("aviso: no veo miniatura en la ranura del primer fotograma")
        except Exception:
            pass

    def _attach(self, references: list[Path]) -> None:
        """Engancha imagenes al prompt como INGREDIENTES.

        Son dos pasos distintos y confundirlos costo dos vueltas: el input file
        oculto solo sube el archivo a la biblioteca del proyecto -- el modelo
        no lo mira. Para que cuente como referencia hay que abrir el selector
        ('+ Crear'), elegir el asset y pulsar 'Agregar a la instruccion'. Con
        la version anterior el video salia de texto puro: un mapache
        fotorrealista en un bosque, nada que ver con Tadeo.
        """
        import hashlib

        page = self._page
        files = [_flatten_alpha(Path(r).resolve()) for r in references]
        for f in files:
            if not f.exists():
                raise FileNotFoundError(f)
        self._refs = files
        self._ref_hashes = {hashlib.sha1(f.read_bytes()).hexdigest() for f in files}

        # 1) subir a la biblioteca del proyecto
        page.locator(SEL_FILE_INPUT).first.set_input_files(
            [str(f) for f in files], timeout=60_000
        )
        stable, last = 0, -1
        for _ in range(40):
            page.wait_for_timeout(1000)
            now = len(self._media())
            stable = stable + 1 if now == last else 0
            last = now
            if stable >= 3:
                break

        # 2) enganchar cada una a la instruccion
        for f in files:
            self._close_popovers()
            page.locator("button:has-text('add_2')").first.click(timeout=15_000)
            page.wait_for_timeout(2500)
            opt = page.locator("[role=option]").filter(has_text=f.name).first
            # el selector abre con el asset recien subido ya marcado
            # (aria-selected=true) y volver a clickearlo no es accionable: se
            # queda esperando y tira timeout. Solo se clickea si hace falta.
            if opt.get_attribute("aria-selected") != "true":
                # la lista es virtualizada (react-virtuoso): mientras se
                # recicla, el contenedor tapa la fila y el click normal se
                # queda reintentando hasta agotar el timeout. force=True
                # dispara igual sobre la fila ya resuelta.
                try:
                    opt.scroll_into_view_if_needed(timeout=5000)
                    opt.click(timeout=8000)
                except Exception:
                    opt.click(timeout=8000, force=True)
                page.wait_for_timeout(1200)
            # segun el estado del proyecto el click ya engancha y cierra el
            # dialogo; solo si sigue abierto hay que confirmar con el boton
            add = page.locator("button:has-text('Agregar a la instrucción')")
            if add.count():
                btn = add.first
                for _ in range(20):
                    if btn.is_enabled():
                        break
                    page.wait_for_timeout(500)
                if btn.is_enabled():
                    btn.click(timeout=15_000)
            page.wait_for_timeout(2500)
        self._close_popovers()

    def _download(self, url: str, path: Path, want_mime: str) -> bool:
        """Baja el media por la URL directa del tile con las cookies de la
        sesion. Verifica el Content-Type: Flow sirve el poster JPEG de un video
        por una URL casi identica, y sin este control termina un .mp4 con una
        imagen adentro."""
        resp = self._ctx.request.get(url, timeout=180_000)
        if not resp.ok:
            _log(f"descarga {resp.status} en {url[:80]}")
            return False
        mime = (resp.headers.get("content-type") or "").lower()
        if want_mime and not mime.startswith(want_mime):
            _log(f"content-type {mime!r}, esperaba {want_mime!r}")
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.body())
        _match_extension(path, mime)
        return path.exists() and path.stat().st_size > 0

    def _submit_and_wait(self, prompt: str, path: Path, timeout_s: int) -> bool:
        page = self._page
        self._close_popovers()
        want_tags = _WANT_TAGS[self.mode]
        want_mime = _WANT_MIME[self.mode]
        # la huella se toma DESPUES de adjuntar: subir una referencia mete esa
        # misma imagen en la grilla y si no, cuenta como "resultado nuevo"
        before = {m["url"] for m in self._media()}
        refusals_before = len(self._refusals())
        refusal_at: float | None = None  # cuando se vio el primer aviso de rechazo

        box = page.locator(SEL_PROMPT).first
        box.click(timeout=10_000)
        box.fill(prompt)
        page.wait_for_timeout(600)

        submit = page.locator(SEL_SUBMIT).first
        # el boton arranca deshabilitado; con prompt (o referencia) se habilita
        for _ in range(20):
            if submit.is_enabled():
                break
            page.wait_for_timeout(500)

        global _last_submit
        wait = COOLDOWN_S - (time.monotonic() - _last_submit)
        if _last_submit and wait > 0:
            _log(f"enfriando {wait:.0f}s antes de enviar")
            page.wait_for_timeout(int(wait * 1000))
        _last_submit = time.monotonic()

        submit.click(timeout=15_000)

        deadline = time.monotonic() + timeout_s
        tried: set[str] = set()
        while time.monotonic() < deadline:
            page.wait_for_timeout(3000)
            # EL MEDIA MANDA SOBRE EL MENSAJE DE RECHAZO (3 ago 2026). Antes se
            # miraba el rechazo PRIMERO y se abortaba, y eso daba falsos
            # negativos medidos: Flow generaba la imagen perfectamente y aun asi
            # devolviamos False porque en la grilla habia aparecido un tile
            # "No se pudo generar" (de un intento anterior o transitorio). Si
            # hay imagen nueva descargable, la corrida es un exito, diga lo que
            # diga la grilla.
            fresh = [
                m["url"]
                for m in self._media()
                if m["url"] not in before
                and m["tag"] in want_tags
                and m["url"] not in tried
            ]
            for url in fresh:
                tried.add(url)
                if not self._download(url, path, want_mime):
                    continue
                if self.mode == "image" and self._looks_like_reference(path):
                    _log("descartado: era la referencia recien subida")
                    path.unlink(missing_ok=True)
                    continue
                return True
            # Una negativa por politicas y un timeout se ven identicos desde el
            # codigo: en los dos casos no aparece media nueva. Sin esta lectura
            # del mensaje real, el pipeline reintenta 3 veces algo que Flow no
            # va a generar nunca, y encima lo reporta como "timeout".
            now = self._refusals()
            if len(now) > refusals_before:
                # EL RECHAZO ES UNA SEÑAL DEBIL, NO UNA SENTENCIA (3 ago 2026).
                # Medido: el tile "No se pudo generar" aparece mientras Nano
                # Banana 2 sigue trabajando y despues lo REEMPLAZA la imagen
                # buena. Abortar al verlo daba falsos negativos con la imagen
                # ya generada en el proyecto (tres pruebas seguidas: gato y dos
                # mapaches, todas visibles en Flow, todas reportadas como
                # rechazo). Asi que se anota y se sigue esperando un rato mas;
                # solo si en ese margen no aparece media se da por rechazado.
                if refusal_at is None:
                    refusal_at = time.monotonic()
                    self.last_refusal = now[-1]
                    _log(
                        f"aviso de rechazo ('{self.last_refusal}'); "
                        f"sigo esperando {REFUSAL_GRACE_S:.0f}s por si es transitorio"
                    )
                elif time.monotonic() - refusal_at > REFUSAL_GRACE_S:
                    _log(f"Flow rechazo el prompt: {self.last_refusal}")
                    return False
        _log(f"timeout ({timeout_s}s) esperando '{prompt[:50]}...'")
        return False

    def generate(
        self,
        prompt: str,
        path: Path,
        references: list[Path] | None = None,
        timeout_s: int = 300,
    ) -> bool:
        """Texto->imagen, o imagen->imagen si se pasan `references` (es lo que
        replica a Tadeo y el fondo entre escenas)."""
        try:
            # OJO: aqui hubo un _reset_prompt() que recargaba el proyecto antes
            # de cada escena, con la teoria de que los ingredientes se
            # arrastraban. Medido el 4 ago 2026: empeoro de 9/12 a 0/12. La
            # pagina recien recargada es justo el estado que FALLA.
            self.set_mode("image")
            self._refs, self._ref_hashes = [], set()
            if references:
                self._attach(list(references))
            return self._submit_and_wait(prompt, Path(path), timeout_s)
        except Exception as e:
            _log(f"fallo generando '{prompt[:50]}...': {e}")
            return False

    def animate(
        self,
        image: Path,
        prompt: str,
        path: Path,
        timeout_s: int = 420,
        duration_s: int | None = None,
    ) -> bool:
        """Imagen->video por frames-to-video: la imagen es el PRIMER fotograma.
        Timeout alto porque un clip de Veo tarda minutos, no segundos."""
        try:
            if duration_s:
                # se redondea hacia arriba a una duracion que Flow ofrezca
                self.duration_s = min(
                    (d for d in VIDEO_DURATIONS if d >= duration_s),
                    default=max(VIDEO_DURATIONS),
                )
                self.mode = None  # forzar reconfiguracion con la nueva duracion
            self.set_mode("video")
            self._refs, self._ref_hashes = [], set()
            if VIDEO_SUBMODE == "Fotogramas":
                self._attach_frame(Path(image))
            else:
                self._attach([Path(image)])
            return self._submit_and_wait(prompt, Path(path), timeout_s)
        except Exception as e:
            _log(f"fallo animando '{Path(image).name}': {e}")
            return False


# --- adaptador para pipeline.py ---------------------------------------------
# Misma firma que comfy_client.generate_image / _seedream_generate_image, para
# que el bucle de escenas no sepa quien genera. La sesion es UNA sola para toda
# la corrida: abrir un Chrome por escena costaria ~15s de arranque cada vez.
_SHARED: FlowSession | None = None


class _Worker:
    """Hilo propio para todo lo que toque Playwright.

    La API sincrona de Playwright se niega a arrancar si en ese hilo hay un
    bucle de asyncio corriendo ('Playwright Sync API inside the asyncio loop').
    `pipeline.py` usa asyncio para el TTS y clientes de API, asi que llamar a
    Flow desde el hilo principal fallaba en las 12 escenas de una corrida --
    pero funcionaba desde `korex_fill.py`, que no toca asyncio. En vez de cazar
    quien deja el bucle vivo, todo el navegador vive aqui: un hilo dedicado no
    tiene bucle y ademas conserva la sesion, que debe usarse siempre desde el
    mismo hilo que la creo.
    """

    def __init__(self):
        import queue
        import threading

        self._q: "queue.Queue" = queue.Queue()
        self._threading = threading
        self._t = threading.Thread(
            target=self._loop, daemon=True, name="flow-playwright"
        )
        self._t.start()

    def _loop(self) -> None:
        while True:
            item = self._q.get()
            if item is None:
                return
            fn, box = item
            try:
                box["r"] = fn()
            except BaseException as e:  # se re-lanza en el hilo que llamo
                box["e"] = e
            finally:
                box["ev"].set()

    def call(self, fn):
        box = {"ev": self._threading.Event()}
        self._q.put((fn, box))
        box["ev"].wait()
        if "e" in box:
            raise box["e"]
        return box.get("r")


_WORKER: _Worker | None = None


def _worker() -> _Worker:
    global _WORKER
    if _WORKER is None:
        _WORKER = _Worker()
    return _WORKER


def _shared_session(aspect_ratio: str = "9:16") -> FlowSession:
    global _SHARED
    if _SHARED is None:
        import atexit

        s = FlowSession(aspect_ratio=aspect_ratio)
        s.__enter__()
        _SHARED = s
        atexit.register(close_session)
    return _SHARED


def close_session() -> None:
    # cerrar TAMBIEN desde el hilo del navegador: los objetos de Playwright solo
    # se pueden tocar desde el hilo que los creo
    def _job():
        global _SHARED
        if _SHARED is not None:
            try:
                _SHARED.__exit__(None, None, None)
            finally:
                _SHARED = None

    try:
        _worker().call(_job)
    except Exception as e:
        _log(f"no pude cerrar la sesion: {e}")


def generate_image(
    prompt: str,
    path: Path,
    key: str = "",
    reference_image: Path | None = None,
    reference_images: list[Path] | None = None,
    style_directive: str | None = None,
    aspect_ratio: str = "9:16",
    timeout_s: int = 300,
) -> bool:
    """Genera una escena en Flow. `reference_image`/`reference_images` son las
    laminas del personaje (assets/kx_cast/tadeo/...) y del set: van como
    ingredientes del prompt, que es lo unico que replica a Tadeo identico entre
    escenas."""
    refs: list[Path] = []
    if reference_image:
        refs.append(Path(reference_image))
    refs += [Path(r) for r in (reference_images or [])]
    refs = [r for r in refs if r.exists()]
    full = f"{prompt}. {style_directive}" if style_directive else prompt

    def _job() -> bool:
        s = _shared_session(aspect_ratio)
        ok = s.generate(full, Path(path), references=refs or None, timeout_s=timeout_s)
        if not ok and s.last_refusal:
            print(f"[flow] RECHAZO por contenido, no timeout: {s.last_refusal}")
            s.last_refusal = ""
        return ok

    try:
        return _worker().call(_job)
    except Exception as e:
        _log(f"generate_image fallo: {e}")
        return False


def animate_image(
    image: Path,
    prompt: str,
    path: Path,
    aspect_ratio: str = "9:16",
    duration_s: int | None = None,
) -> bool:
    """Anima una escena ya generada. `duration_s` = segundos que dura la escena
    en el montaje: pedir 4s para una escena de 4s cuesta lo mismo que 8s en
    creditos pero acaba antes y no hay que congelar el ultimo fotograma."""
    try:
        return _worker().call(
            lambda: _shared_session(aspect_ratio).animate(
                Path(image), prompt, Path(path), duration_s=duration_s
            )
        )
    except Exception as e:
        _log(f"animate_image fallo: {e}")
        return False


def flow_generate_image(
    prompt: str,
    path: Path,
    aspect_ratio: str = "9:16",
    references: list[Path] | None = None,
    timeout_s: int = 180,
) -> bool:
    """Atajo para una sola imagen (abre y cierra sesion de Flow). Para varias
    escenas de un mismo video, usar FlowSession directamente y reusar el
    proyecto -- mucho mas rapido que reabrir Flow por cada imagen."""
    if not is_logged_in():
        _log("sin sesion guardada, correr: python flow_automation.py --login")
        return False
    try:
        with FlowSession(aspect_ratio=aspect_ratio) as flow:
            return flow.generate(
                prompt, path, references=references, timeout_s=timeout_s
            )
    except Exception as e:
        _log(f"fallo de sesion: {e}")
        return False


_JS_DUMP = r"""
() => {
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.opacity !== '0';
  };
  const txt = (el) => (el.innerText || el.textContent || '').trim().slice(0, 120);
  const desc = (el) => {
    const r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(), text: txt(el),
      aria: el.getAttribute('aria-label'), title: el.getAttribute('title'),
      role: el.getAttribute('role'), type: el.getAttribute('type'),
      placeholder: el.getAttribute('placeholder'), accept: el.getAttribute('accept'),
      multiple: el.hasAttribute('multiple'),
      disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true',
      testid: el.getAttribute('data-testid') || el.getAttribute('data-test-id'),
      box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
    };
  };
  const pick = (sel, onlyVisible = true) =>
    [...document.querySelectorAll(sel)].filter(e => !onlyVisible || vis(e)).map(desc);
  return {
    url: location.href, title: document.title, lang: document.documentElement.lang,
    buttons: pick('button'),
    inputs: pick('input, textarea, [contenteditable="true"]', false),
    fileInputs: pick('input[type=file]', false),
    roleButtons: pick('[role=button]'),
    menuitems: pick('[role=menuitem], [role=menuitemradio], [role=option], [role=tab], [role=radio], [role=switch]'),
    comboboxes: pick('[role=combobox], select'),
    dialogs: pick('[role=dialog], [role=menu], [role=listbox]'),
    links: pick('a[href]').slice(0, 50),
  };
}
"""

_INSPECT_DIR = Path(__file__).parent / ".flow_inspect"


def _dump(page, label: str) -> dict:
    """Vuelca el DOM real de Flow. La UI es una SPA con clases hasheadas, asi
    que lo unico estable es texto visible / aria-label / placeholder: hay que
    revalidar los selectores contra esta salida cada vez que Google cambia el
    build."""
    import json

    page.wait_for_timeout(1500)
    data = page.evaluate(_JS_DUMP)
    _INSPECT_DIR.mkdir(exist_ok=True)
    (_INSPECT_DIR / f"dom_{label}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    try:
        page.screenshot(path=str(_INSPECT_DIR / f"shot_{label}.png"))
    except Exception:
        pass
    print(f"\n===== {label} :: {data['url']} =====")
    print(f"lang={data['lang']} title={data['title']}")
    for key in (
        "buttons",
        "roleButtons",
        "inputs",
        "fileInputs",
        "menuitems",
        "comboboxes",
        "dialogs",
    ):
        items = data.get(key) or []
        if not items:
            continue
        print(f"-- {key} ({len(items)}) --")
        for it in items[:60]:
            bits = [f"<{it['tag']}>"]
            if it["text"]:
                bits.append(repr(it["text"]))
            for k in (
                "aria",
                "title",
                "placeholder",
                "accept",
                "testid",
                "type",
                "role",
            ):
                if it.get(k):
                    bits.append(f"{k}={it[k]!r}")
            if it["multiple"]:
                bits.append("MULTIPLE")
            if it["disabled"]:
                bits.append("DISABLED")
            bits.append(f"@{it['box']}")
            print("   " + " ".join(bits))
    return data


def _inspect() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = _launch_ctx(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(20_000)
        page.goto(FLOW_URL, timeout=60_000)
        try:
            page.wait_for_load_state("networkidle", timeout=25_000)
        except Exception:
            pass
        page.wait_for_timeout(4000)
        _dump(page, "dashboard")

        entered = False
        cards = page.locator("a[href*='/project/']")
        if cards.count():
            cards.first.click()
            entered = True
        else:
            for label in ("Proyecto nuevo", "New project", "Nuevo proyecto"):
                loc = page.get_by_text(label, exact=False)
                if loc.count():
                    loc.first.click()
                    entered = True
                    break
        if not entered:
            print("[warn] no encontre como entrar a un proyecto")
            ctx.close()
            return

        page.wait_for_timeout(8000)
        _dump(page, "project")

        # cada panel se abre, se vuelca y se cierra con Escape
        panels = [
            ("mediamenu", "button:has-text('Agregar archivo multimedia')"),
            ("createmenu", "button:has-text('add_2')"),
            ("modelpanel", "button:has-text('Nano Banana')"),
            ("personajes", "button:has-text('Personajes')"),
        ]
        for label, sel in panels:
            try:
                loc = page.locator(sel)
                if not loc.count():
                    print(f"[warn] no existe {label}: {sel}")
                    continue
                loc.first.click()
                page.wait_for_timeout(2500)
                _dump(page, label)
                page.keyboard.press("Escape")
                page.wait_for_timeout(800)
            except Exception as e:
                _log(f"no pude abrir {label}: {e}")

        # como se baja el resultado: URL directa del tile vs dialogo de descarga
        page.goto(page.url.split("/characters")[0], timeout=30_000)
        page.wait_for_timeout(5000)
        tiles = page.evaluate(r"""
          () => [...document.querySelectorAll('div[role=button]')].slice(0, 3).map(t => ({
            box: (b => [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)])(t.getBoundingClientRect()),
            media: [...t.querySelectorAll('img, video, source')].map(m => ({
              tag: m.tagName.toLowerCase(),
              src: (m.currentSrc || m.src || m.getAttribute('src') || '').slice(0, 220),
              poster: m.getAttribute('poster'),
            })),
            html: t.outerHTML.slice(0, 700),
          }))
        """)
        print("\n===== tiles =====")
        for i, t in enumerate(tiles):
            print(f"[{i}] box={t['box']}")
            for m in t["media"]:
                print(f"    <{m['tag']}> src={m['src']}")
                if m["poster"]:
                    print(f"        poster={m['poster'][:160]}")
        if tiles:
            b = tiles[0]["box"]
            page.mouse.move(b[0] + b[2] // 2, b[1] + b[3] // 2)
            page.wait_for_timeout(1500)
            _dump(page, "tilehover")
            page.mouse.click(b[0] + b[2] // 2, b[1] + b[3] // 2)
            page.wait_for_timeout(3500)
            _dump(page, "tiledetail")
        ctx.close()
    print(f"\nOK -- JSON y capturas en {_INSPECT_DIR}")


def _crear_personaje(nombre: str, descripcion: str, refs: list[Path]) -> bool:
    """Da de alta un Personaje nativo de Flow a partir de laminas propias.

    Un Personaje empaqueta referencias + rasgos en una entidad reutilizable que
    luego se elige en cualquier prompt, y es mas fiable que adjuntar la lamina
    a mano en cada escena. Lo que decide la consistencia es la calidad de la
    referencia: nitida, bien iluminada, sujeto centrado y fondo limpio -- por
    eso se aplanan y se manda la mejor pose, no todas.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = _launch_ctx(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(25_000)
        try:
            page.goto(FLOW_URL, timeout=60_000)
            page.wait_for_timeout(7000)
            cards = page.locator("a[href*='/project/']")
            if cards.count():
                cards.first.click()
            else:
                page.get_by_text("Proyecto nuevo", exact=False).first.click()
            page.wait_for_selector(SEL_PROMPT, timeout=30_000)
            page.wait_for_timeout(4000)

            page.locator("button:has-text('Personajes')").first.click()
            page.wait_for_timeout(4000)

            files = [str(_flatten_alpha(Path(r).resolve())) for r in refs]
            page.locator(SEL_FILE_INPUT).first.set_input_files(files, timeout=60_000)
            page.wait_for_timeout(8000)

            box = page.locator("div[role=textbox]").last
            box.click(timeout=15_000)
            box.fill(descripcion)
            page.wait_for_timeout(1000)

            submit = page.locator(SEL_SUBMIT).first
            for _ in range(20):
                if submit.is_enabled():
                    break
                page.wait_for_timeout(500)
            submit.click(timeout=15_000)
            print(f"'{nombre}' enviado a Personajes; esperando...")
            page.wait_for_timeout(60_000)

            # La ficha del personaje tiene campos PROPIOS, distintos de la caja
            # de prompt: un input 'Nombre del personaje' y un textarea de
            # personalidad que el agente de Flow usa para construir escenas.
            # Sin rellenarlos queda como "Personaje sin titulo".
            try:
                page.locator("input[placeholder='Nombre del personaje']").first.fill(
                    nombre
                )
                page.wait_for_timeout(500)
                page.locator("textarea[placeholder*='actúa']").first.fill(descripcion)
                page.wait_for_timeout(500)
                page.locator("button:has-text('Listo')").first.click(timeout=10_000)
                page.wait_for_timeout(3000)
            except Exception as e:
                _log(f"no pude rellenar nombre/personalidad: {e}")
            _dump(page, "personaje_creado")
            print(f"revisa {_INSPECT_DIR / 'shot_personaje_creado.png'}")
            return True
        except Exception as e:
            _log(f"fallo creando el personaje: {e}")
            try:
                _dump(page, "personaje_error")
            except Exception:
                pass
            return False
        finally:
            ctx.close()


def _probe() -> None:
    """Sondea COMO se engancha una imagen al prompt. El input file oculto la
    sube a la biblioteca del proyecto pero no la usa como ingrediente: el video
    salio de texto puro, ignorando la referencia. Vuelca el menu de un tile y
    el dialogo del boton '+'."""
    from playwright.sync_api import sync_playwright

    ref = Path(__file__).parent / "assets" / "kx_cast" / "tadeo" / "codicia_1.png"
    with sync_playwright() as p:
        ctx = _launch_ctx(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(20_000)
        page.goto(FLOW_URL, timeout=60_000)
        page.wait_for_timeout(6000)
        page.locator("a[href*='/project/']").first.click()
        page.wait_for_selector(SEL_PROMPT, timeout=30_000)
        page.wait_for_timeout(6000)

        # 1) menu contextual de un tile: buscamos "Animar"/"Crear video"
        tile = page.locator(SEL_TILE).first
        try:
            tile.hover()
            page.wait_for_timeout(1200)
            tile.locator("button:has-text('more_vert')").first.click()
            page.wait_for_timeout(1500)
            _dump(page, "tilemenu")
            page.keyboard.press("Escape")
            page.wait_for_timeout(800)
        except Exception as e:
            _log(f"tilemenu: {e}")

        # 2) dialogo de ingredientes: subir y "Agregar a la instruccion"
        try:
            page.locator("button:has-text('add_2')").first.click()
            page.wait_for_timeout(2000)
            _dump(page, "ingredients")
            with page.expect_file_chooser(timeout=15_000) as fc:
                page.locator("button:has-text('Cargar medios')").first.click()
            fc.value.set_files(str(ref))
            page.wait_for_timeout(9000)
            _dump(page, "ingredients_uploaded")
        except Exception as e:
            _log(f"ingredientes: {e}")

        ctx.close()
    print(f"\nOK -- volcados en {_INSPECT_DIR}")


def _errors() -> None:
    """Abre el proyecto mas reciente y busca por que fallo una generacion. Una
    negativa por politicas y un timeout se ven IGUAL desde el codigo (en los dos
    casos no aparece media nueva), asi que hay que leer el mensaje real de la
    UI."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = _launch_ctx(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(20_000)
        page.goto(FLOW_URL, timeout=60_000)
        page.wait_for_timeout(6000)
        page.locator("a[href*='/project/']").first.click()
        page.wait_for_selector(SEL_PROMPT, timeout=30_000)
        page.wait_for_timeout(7000)

        texts = page.evaluate(
            r"""
          () => [...document.querySelectorAll('body *')]
            .filter(e => e.children.length === 0)
            .map(e => (e.innerText || '').trim())
            .filter(t => t && /no se pudo|pol[ií]tic|no cumple|infring|bloque|
                            unable|violat|not allowed|error/i.test(t))
        """.replace("\n", " ")
        )
        print("=== textos de error visibles ===")
        for t in dict.fromkeys(texts):
            print("  ", t[:200])

        # el tile fallido: abrirlo suele mostrar el motivo completo
        bad = page.locator("div[role=button]").filter(has_text="No se pudo")
        print(f"tiles fallidos: {bad.count()}")
        if bad.count():
            bad.first.click()
            page.wait_for_timeout(3000)
            _dump(page, "error_tile")
            print(page.locator("body").inner_text()[:1500])
        ctx.close()


def _smoke() -> None:
    """Prueba real de las dos capacidades nuevas, contra Flow de verdad:
    imagen con referencia de Tadeo, y despues animacion de esa misma imagen."""
    out = _INSPECT_DIR
    out.mkdir(exist_ok=True)
    ref = Path(__file__).parent / "assets" / "kx_cast" / "tadeo" / "codicia_1.png"
    if not ref.exists():
        print(f"falta la referencia {ref}")
        return
    img, vid = out / "smoke_ref.png", out / "smoke_video.mp4"

    with FlowSession(aspect_ratio="9:16", headless=False) as flow:
        print(f"proyecto: {flow.project_url}")
        ok_img = flow.generate(
            "El mismo mapache de la imagen de referencia, identico en estilo y "
            "diseno, de pie frente a un tablero de bolsa con las flechas en "
            "rojo. Dibujo animado en blanco y negro, estilo caricatura vintage.",
            img,
            references=[ref],
        )
        print(f"imagen con referencia: {'OK' if ok_img else 'FALLO'} -> {img}")

        if ok_img:
            ok_vid = flow.animate(
                img,
                "Camara acercandose muy lento al mapache. Movimiento sutil, "
                "sin cortes.",
                vid,
            )
            print(f"animacion: {'OK' if ok_vid else 'FALLO'} -> {vid}")


if __name__ == "__main__":
    if "--login" in sys.argv:
        _login()
    elif "--inspect" in sys.argv:
        _inspect()
    elif "--smoke" in sys.argv:
        _smoke()
    elif "--probe" in sys.argv:
        _probe()
    elif "--errors" in sys.argv:
        _errors()
    elif "--personaje" in sys.argv:
        import kx_cast

        refs = [
            p
            for p in (
                kx_cast._canonical_sheet("tadeo"),
                kx_cast.pick("tadeo", "triunfo", 0),
                kx_cast.pick("tadeo", "explicando", 0),
            )
            if p and Path(p).exists()
        ]
        _crear_personaje(
            "Tadeo",
            "Tadeo: mapache de dibujo animado 'rubber hose' de los anos 30, "
            "blanco y negro con grises neutros, contorno de tinta grueso, ojos "
            "grandes y redondos, antifaz oscuro, hocico redondeado, pecho "
            "crema, cola anillada y guantes blancos de cuatro dedos. "
            "Personaje comico, ingenuo y confiado.",
            refs,
        )
    else:
        print(
            "Uso: python flow_automation.py [--login | --inspect | --probe | --smoke]"
        )
