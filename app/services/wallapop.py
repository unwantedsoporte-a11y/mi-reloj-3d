"""Cliente para Wallapop: abre la página de búsqueda real en un navegador
(Playwright) y captura la respuesta JSON que la propia web pide para
mostrar los resultados. Wallapop bloquea (403) las peticiones directas a
su API sin pasar por un navegador real, por eso se hace así."""
import logging
from urllib.parse import quote

from app import config
from app.services import browser
from app.services.http_utils import dig

logger = logging.getLogger("flipgames.wallapop")

SEARCH_PAGE_URL = "https://es.wallapop.com/search"
API_URL_FRAGMENTS = ["/api/v3/general/search", "/api/v3/search"]


def search(query: str, limit: int = None):
    limit = limit or config.LISTINGS_PER_GAME
    page_url = (
        f"{SEARCH_PAGE_URL}?keywords={quote(query)}"
        f"&latitude={config.WALLAPOP_LAT}&longitude={config.WALLAPOP_LON}"
    )

    try:
        data = browser.fetch_api_json(page_url, API_URL_FRAGMENTS)
    except browser.BrowserNotReady as exc:
        logger.warning("Wallapop: %s", exc)
        return []

    if data is None:
        logger.warning("Fallo consultando Wallapop para %r (sin respuesta de la API)", query)
        return []

    items = (
        dig(data, "search_objects", default=None)
        or dig(data, "data", "section", "payload", "items", default=None)
        or []
    )
    results = []
    for item in items[:limit]:
        price = dig(item, "price", default=None)
        currency = dig(item, "currency", default=None)
        if isinstance(price, dict):
            currency = currency or price.get("currency")
            price = price.get("amount") or price.get("cash_amount")
        if price is None:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue

        currency_status = "eur" if currency == "EUR" else ("sin_confirmar" if not currency else "no_eur")
        item_id = item.get("id") or item.get("item_id")
        web_slug = item.get("web_slug")
        url = f"https://es.wallapop.com/item/{web_slug}" if web_slug else (
            f"https://es.wallapop.com/item/{item_id}" if item_id else None
        )
        location = dig(item, "location", "city", default=None) or dig(item, "location", "postal_code", default=None)

        results.append({
            "source": "wallapop",
            "title": item.get("title") or query,
            "listing_price": price,
            "currency_status": currency_status,
            "seller_location": location,
            "listing_url": url,
            "raw_description": (item.get("title") or "") + " " + (item.get("description") or ""),
        })

    return results
