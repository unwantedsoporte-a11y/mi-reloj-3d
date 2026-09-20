"""Cliente para CEX (webuy): busca el precio que pagan EN EFECTIVO por
juegos. Abre la página de búsqueda real en un navegador (Playwright) y
captura la respuesta JSON que la propia web pide para mostrar resultados
— pedir la API directamente da 403 Forbidden, por eso se hace así.
"""
import logging
from urllib.parse import quote

from app import config
from app.services import browser
from app.services.http_utils import dig, find_first_matching_key

logger = logging.getLogger("flipgames.cex")

SEARCH_PAGE_URL = f"https://{config.CEX_COUNTRY}.webuy.com/search"
API_URL_FRAGMENTS = ["/v3/boxes"]

_EXCLUDE_WORDS = ("console", "consola", "cargador", "charger", "mando", "controller",
                  "funda", "case", "cable", "adaptador", "adapter", "docking")


def _price_from_box(box: dict):
    for key in ("cashPrice", "CashPrice", "cash_price"):
        val = box.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    val = find_first_matching_key(box, "cash")
    if isinstance(val, (int, float)) and val > 0:
        return float(val)
    return None


def _looks_like_game(box: dict) -> bool:
    name = (box.get("boxName") or box.get("boxDetail") or "").lower()
    category = (box.get("categoryFriendlyName") or "").lower()
    if not name:
        return False
    if any(word in name for word in _EXCLUDE_WORDS):
        return False
    if "game" not in category and "juego" not in category and "software" not in category:
        if any(word in category for word in ("console", "hardware", "accessor")):
            return False
    return True


def search_platform_games(platform: str, limit: int = None):
    """Devuelve una lista de dicts {title, platform, cex_cash_price} para
    una plataforma dada (p.ej. 'Nintendo Switch'), ordenados por precio en
    efectivo descendente."""
    limit = limit or config.SCAN_LIMIT_PER_PLATFORM
    page_url = f"{SEARCH_PAGE_URL}?stext={quote(platform)}"

    try:
        data = browser.fetch_api_json(page_url, API_URL_FRAGMENTS)
    except browser.BrowserNotReady as exc:
        logger.warning("CEX: %s", exc)
        return []

    if data is None:
        logger.warning("Fallo consultando CEX para %s (sin respuesta de la API)", platform)
        return []

    boxes = (
        dig(data, "response", "data", "boxes", default=None)
        or dig(data, "response", "data", "results", default=None)
        or []
    )
    games = {}
    for box in boxes:
        if not _looks_like_game(box):
            continue
        price = _price_from_box(box)
        if price is None or price < config.MIN_CEX_CASH_PRICE:
            continue
        title = (box.get("boxName") or "").strip()
        if not title:
            continue
        if title not in games or games[title]["cex_cash_price"] < price:
            games[title] = {"title": title, "platform": platform, "cex_cash_price": price}

    result = sorted(games.values(), key=lambda g: g["cex_cash_price"], reverse=True)
    return result[:limit]
