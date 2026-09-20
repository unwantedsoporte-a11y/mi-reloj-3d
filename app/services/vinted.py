"""Cliente para Vinted: abre la página de búsqueda real en un navegador
(Playwright) y captura la respuesta JSON que la propia web pide para
mostrar los resultados. Vinted bloquea (404) las peticiones directas a su
API sin pasar por un navegador real, por eso se hace así."""
import logging
from urllib.parse import quote

from app import config
from app.services import browser
from app.services.http_utils import dig

logger = logging.getLogger("flipgames.vinted")

SEARCH_PAGE_URL = "https://www.vinted.es/catalog"
API_URL_FRAGMENTS = ["/api/v2/catalog/items"]


def search(query: str, limit: int = None):
    limit = limit or config.LISTINGS_PER_GAME
    page_url = f"{SEARCH_PAGE_URL}?search_text={quote(query)}&order=price_low_to_high"

    try:
        data = browser.fetch_api_json(page_url, API_URL_FRAGMENTS)
    except browser.BrowserNotReady as exc:
        logger.warning("Vinted: %s", exc)
        return []

    if data is None:
        logger.warning("Fallo consultando Vinted para %r (sin respuesta de la API)", query)
        return []

    items = dig(data, "items", default=[]) or []
    results = []
    for item in items[:limit]:
        price = dig(item, "price", "amount", default=None)
        currency = dig(item, "price", "currency_code", default=None)
        if price is None:
            price = dig(item, "total_item_price", "amount", default=None) or item.get("price")
            currency = currency or dig(item, "total_item_price", "currency_code", default=None)
        if price is None:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue

        currency_status = "eur" if currency == "EUR" else ("sin_confirmar" if not currency else "no_eur")
        item_id = item.get("id")
        url = item.get("url") or (f"https://www.vinted.es/items/{item_id}" if item_id else None)

        results.append({
            "source": "vinted",
            "title": item.get("title") or query,
            "listing_price": price,
            "currency_status": currency_status,
            "seller_location": item.get("city") or dig(item, "user", "city", default=None),
            "listing_url": url,
            "raw_description": item.get("title") or "",
        })

    return results
