"""Motor de navegador (Playwright) para saltarse los bloqueos anti-bots de
CEX, Vinted y Wallapop: en vez de pedir su API directamente (que es lo que
bloquean con 403/404), abrimos la página de búsqueda real en un navegador
de verdad y capturamos la respuesta JSON que la propia web pide por dentro
al cargar los resultados. Al ser un navegador real (ejecuta JavaScript,
tiene cookies, etc.) tiene más posibilidades de colar, aunque sigue sin
haber garantía: algunas protecciones también detectan navegadores
automatizados.

Requiere, además de `pip install -r requirements.txt`, descargar el
navegador una sola vez:
    playwright install chromium
"""
import atexit
import logging
import threading

from app import config

logger = logging.getLogger("flipgames.browser")

_lock = threading.Lock()
_playwright = None
_browser = None


class BrowserNotReady(Exception):
    pass


def _ensure_browser():
    global _playwright, _browser
    if _browser is not None:
        return _browser
    with _lock:
        if _browser is not None:
            return _browser
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserNotReady(
                "Falta el paquete 'playwright'. Ejecuta: pip install -r requirements.txt"
            ) from exc
        try:
            _playwright = sync_playwright().start()
            _browser = _playwright.chromium.launch(headless=True)
        except Exception as exc:
            raise BrowserNotReady(
                "No se pudo arrancar el navegador de Playwright. Ejecuta una vez: "
                "playwright install chromium — y vuelve a intentarlo. "
                f"Detalle: {exc}"
            ) from exc
    return _browser


def fetch_api_json(page_url: str, url_contains, timeout_ms: int = None):
    """Abre `page_url` en un navegador real y devuelve el JSON de la primera
    respuesta cuya URL contenga alguno de los fragmentos de `url_contains`
    (str o lista de str) — esa es la llamada interna que hace la propia web
    al cargar los resultados de búsqueda. Devuelve None si no llega a
    tiempo, la web bloquea la carga, o cualquier otro fallo."""
    fragments = [url_contains] if isinstance(url_contains, str) else list(url_contains)
    timeout_ms = timeout_ms or config.BROWSER_TIMEOUT_MS
    browser = _ensure_browser()
    context = browser.new_context(user_agent=config.USER_AGENT, locale="es-ES")
    page = context.new_page()
    try:
        with page.expect_response(
            lambda r: any(f in r.url for f in fragments) and r.status == 200,
            timeout=timeout_ms,
        ) as resp_info:
            page.goto(page_url, timeout=timeout_ms, wait_until="domcontentloaded")
        return resp_info.value.json()
    except Exception as exc:
        logger.warning("No se pudo capturar respuesta (%s) en %s: %s", fragments, page_url, exc)
        return None
    finally:
        context.close()


def shutdown():
    global _playwright, _browser
    if _browser:
        try:
            _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright:
        try:
            _playwright.stop()
        except Exception:
            pass
        _playwright = None


atexit.register(shutdown)
