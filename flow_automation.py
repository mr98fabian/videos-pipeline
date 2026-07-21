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

No soporta imagenes de referencia (consistencia de personaje entre escenas) --
Flow en este flujo es solo texto->imagen. pipeline.py salta directo a Nano
Banana API cuando el guion necesita reference_image/reference_images/
style_directive, y cae a Nano Banana API si Flow falla por cualquier motivo.
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


def is_logged_in() -> bool:
    return FLOW_PROFILE_DIR.exists() and any(FLOW_PROFILE_DIR.iterdir())


def _login() -> None:
    from playwright.sync_api import sync_playwright

    FLOW_PROFILE_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(FLOW_PROFILE_DIR), headless=False, args=["--start-maximized"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(FLOW_URL)
        print("Inicia sesion en Google en la ventana abierta.")
        print("Cuando veas el dashboard de Flow (proyectos), volve aca y "
              "presiona Enter para guardar la sesion.")
        input()
        ctx.close()
    print(f"Sesion guardada en {FLOW_PROFILE_DIR}")


def _log(msg: str) -> None:
    if DEBUG:
        print(f"[flow] {msg}")


class FlowSession:
    """Un proyecto de Flow abierto, reusado para todas las escenas de un
    video. Uso:
        with FlowSession(aspect_ratio="9:16") as flow:
            for prompt, path in scenes:
                ok = flow.generate(prompt, path)
    """

    def __init__(self, aspect_ratio: str = "9:16", headless: bool | None = None):
        self.aspect_ratio = aspect_ratio
        self.headless = (not DEBUG) if headless is None else headless
        self._pw = None
        self._ctx = None
        self._page = None

    def __enter__(self) -> "FlowSession":
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(
            str(FLOW_PROFILE_DIR), headless=self.headless,
            args=[] if self.headless else ["--start-minimized"],
        )
        self._page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        self._open_new_project()
        self._configure_once()
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self._ctx:
                self._ctx.close()
        finally:
            if self._pw:
                self._pw.stop()

    def _open_new_project(self) -> None:
        page = self._page
        page.goto(FLOW_URL, timeout=30_000)
        page.wait_for_load_state("networkidle", timeout=20_000)
        # tile "+ Proyecto nuevo" en el dashboard de proyectos
        page.get_by_text("Proyecto nuevo", exact=False).first.click(timeout=15_000)
        page.wait_for_selector("text=¿Qué quieres crear?", timeout=15_000)

    def _configure_once(self) -> None:
        page = self._page
        # chip de modelo/config, abajo a la derecha de la caja de prompt --
        # muestra el modelo actual con emoji de banana (default "Nano Banana Pro")
        page.locator("button", has_text="🍌").last.click(timeout=10_000)

        # modo Imagen (Flow arranca a veces en modo Video)
        page.get_by_text("Imagen", exact=True).first.click(timeout=10_000)

        # aspect ratio exacto, ej "9:16" o "16:9"
        page.get_by_text(self.aspect_ratio, exact=True).first.click(timeout=10_000)

        # cantidad de salidas por prompt -> 1x (una imagen por escena)
        page.get_by_text("1x", exact=True).first.click(timeout=5_000)

        # dropdown de modelo -> Nano Banana 2
        page.locator("button", has_text="🍌").last.click(timeout=10_000)
        page.get_by_text(MODEL_NAME, exact=True).first.click(timeout=10_000)

        # cierra el panel de configuracion clickeando la caja de prompt
        page.get_by_placeholder("¿Qué quieres crear?", exact=False).click(timeout=5_000)

    def generate(self, prompt: str, path: Path, timeout_s: int = 90) -> bool:
        page = self._page
        try:
            box = page.get_by_placeholder("¿Qué quieres crear?", exact=False)
            box.click(timeout=10_000)
            box.fill(prompt)
            page.locator("button", has_text="arrow_forward").first.click(timeout=10_000)

            # espera a que desaparezca el indicador de progreso "NN%"
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                if not page.get_by_text("%", exact=False).count():
                    break
                page.wait_for_timeout(1000)
            else:
                _log(f"timeout esperando generacion de '{prompt[:50]}...'")
                return False

            # la imagen mas nueva siempre aparece primera (arriba a la
            # izquierda de la grilla) -- click para abrir el detalle
            page.wait_for_timeout(500)
            first_thumb = page.locator("img").first
            first_thumb.click(timeout=10_000)

            with page.expect_download(timeout=20_000) as dl_info:
                page.locator("button", has_text="Descargar").first.click(timeout=10_000)
            dl_info.value.save_as(str(path))

            # vuelve al lienzo del proyecto (flecha "Atras")
            page.locator("button", has_text="Atrás").first.click(timeout=10_000)
            page.wait_for_selector("text=¿Qué quieres crear?", timeout=10_000)

            return path.exists() and path.stat().st_size > 0
        except Exception as e:
            _log(f"fallo generando '{prompt[:50]}...': {e}")
            return False


def flow_generate_image(prompt: str, path: Path, aspect_ratio: str = "9:16",
                         timeout_s: int = 90) -> bool:
    """Atajo para una sola imagen (abre y cierra sesion de Flow). Para varias
    escenas de un mismo video, usar FlowSession directamente y reusar el
    proyecto -- mucho mas rapido que reabrir Flow por cada imagen."""
    if not is_logged_in():
        _log("sin sesion guardada, correr: python flow_automation.py --login")
        return False
    try:
        with FlowSession(aspect_ratio=aspect_ratio) as flow:
            return flow.generate(prompt, path, timeout_s=timeout_s)
    except Exception as e:
        _log(f"fallo de sesion: {e}")
        return False


if __name__ == "__main__":
    if "--login" in sys.argv:
        _login()
    else:
        print("Uso: python flow_automation.py --login")
