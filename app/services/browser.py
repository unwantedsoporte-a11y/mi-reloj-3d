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

Nota técnica: la API "sync" de Playwright solo puede usarse desde el
mismo hilo (thread) en el que se arrancó — si se llama desde hilos
distintos (como puede pasar con el servidor de desarrollo de Flask)
revienta con "greenlet.error: Cannot switch to a different thread". Por
eso aquí todas las operaciones del navegador se ejecutan siempre dentro
de un único hilo dedicado, usando un ThreadPoolExecutor de un solo
worker: pase lo que pase en Flask, Playwright siempre ve el mismo hilo.
"""
import atexit
import logging
from concurrent.futures import ThreadPoolExecutor

from app import config

logger = logging.getLogger("flipgames.browser")

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="playwright")
_playwright = None
_browser = None


class BrowserNotReady(Exception):
    pass


def _reset_playwright_state():
    global _playwright, _browser
    if _playwright is not None:
        try:
            _playwright.stop()
        except Exception:
            pass
    _playwright = None
    _browser = None


def _ensure_browser():
    """Se ejecuta SIEMPRE dentro del hilo dedicado del executor."""
    global _playwright, _browser
    if _browser is not None:
        return _browser
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserNotReady(
            "Falta el paquete 'playwright'. Ejecuta: pip install -r requirements.txt"
        ) from exc

    # Primero intenta con la configuración normal (visible u oculto según
    # BROWSER_HEADLESS); si falla (p.ej. no hay pantalla disponible), se
    # limpia el estado y se reintenta una vez en modo oculto como red de
    # seguridad, en vez de dejar todo roto para las siguientes búsquedas.
    attempts = [config.BROWSER_HEADLESS]
    if not config.BROWSER_HEADLESS:
        attempts.append(True)

    last_error = None
    for headless in attempts:
        try:
            _playwright = sync_playwright().start()
            _browser = _playwright.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            return _browser
        except Exception as exc:
            last_error = exc
            _reset_playwright_state()

    raise BrowserNotReady(
        "No se pudo arrancar el navegador de Playwright. Ejecuta una vez: "
        "playwright install chromium — y vuelve a intentarlo. "
        f"Detalle: {last_error}"
    ) from last_error


_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
"""


def _new_context(browser):
    context = browser.new_context(
        user_agent=config.USER_AGENT,
        locale="es-ES",
        viewport={"width": 1366, "height": 850},
    )
    context.add_init_script(_STEALTH_SCRIPT)
    return context


def _fetch_in_browser_thread(page_url: str, fragments: list, timeout_ms: int):
    browser = _ensure_browser()
    context = _new_context(browser)
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


# Varias formas de encontrar la caja de búsqueda, se prueban en orden hasta
# que una encuentre algo (las webs no siempre marcan su buscador igual).
_SEARCH_BOX_LOCATORS = [
    lambda page: page.get_by_role("searchbox"),
    lambda page: page.get_by_role("combobox"),
    lambda page: page.locator('input[type="search"]'),
    lambda page: page.locator('input[name*="search" i]'),
    lambda page: page.locator('input[placeholder*="buscar" i]'),
]


def _search_in_browser_thread(base_url: str, query: str, fragments: list, timeout_ms: int):
    """Carga `base_url`, escribe `query` en el buscador de la propia página
    y pulsa Enter — igual que haría una persona — en vez de ir directo a la
    URL de resultados. Algunas webs solo hacen la llamada JSON que nos
    interesa cuando buscas así (si vas directo a la URL de resultados, a
    veces mandan la página ya montada de fábrica, sin esa llamada aparte)."""
    browser = _ensure_browser()
    context = _new_context(browser)
    page = context.new_page()
    try:
        page.goto(base_url, timeout=timeout_ms, wait_until="domcontentloaded")

        search_box = None
        for locator_fn in _SEARCH_BOX_LOCATORS:
            try:
                candidate = locator_fn(page)
                if candidate.count() > 0:
                    search_box = candidate.first
                    break
            except Exception:
                continue

        if search_box is None:
            logger.warning("No se encontró la caja de búsqueda en %s", base_url)
            return None

        with page.expect_response(
            lambda r: any(f in r.url for f in fragments) and r.status == 200,
            timeout=timeout_ms,
        ) as resp_info:
            search_box.click()
            search_box.fill(query)
            search_box.press("Enter")
        return resp_info.value.json()
    except Exception as exc:
        logger.warning("No se pudo capturar respuesta (%s) buscando %r en %s: %s", fragments, query, base_url, exc)
        return None
    finally:
        context.close()


def fetch_api_json(page_url: str, url_contains, timeout_ms: int = None):
    """Abre `page_url` en un navegador real y devuelve el JSON de la primera
    respuesta cuya URL contenga alguno de los fragmentos de `url_contains`
    (str o lista de str) — esa es la llamada interna que hace la propia web
    al cargar los resultados de búsqueda. Devuelve None si no llega a
    tiempo, la web bloquea la carga, o cualquier otro fallo."""
    fragments = [url_contains] if isinstance(url_contains, str) else list(url_contains)
    timeout_ms = timeout_ms or config.BROWSER_TIMEOUT_MS
    future = _executor.submit(_fetch_in_browser_thread, page_url, fragments, timeout_ms)
    return future.result(timeout=(timeout_ms / 1000) + 20)


def search_via_typing(base_url: str, query: str, url_contains, timeout_ms: int = None):
    """Como `fetch_api_json`, pero simulando escribir `query` en el buscador
    de `base_url` y pulsar Enter, en vez de navegar directo a una URL de
    resultados. Devuelve None si no encuentra la caja de búsqueda, no llega
    a tiempo, o cualquier otro fallo."""
    fragments = [url_contains] if isinstance(url_contains, str) else list(url_contains)
    timeout_ms = timeout_ms or config.BROWSER_TIMEOUT_MS
    future = _executor.submit(_search_in_browser_thread, base_url, query, fragments, timeout_ms)
    return future.result(timeout=(timeout_ms / 1000) + 20)


def _shutdown_in_browser_thread():
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


def shutdown():
    try:
        _executor.submit(_shutdown_in_browser_thread).result(timeout=10)
    except Exception:
        pass
    _executor.shutdown(wait=False)


atexit.register(shutdown)
