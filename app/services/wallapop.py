"""Cliente para Wallapop: busca anuncios de un juego y extrae precio/moneda/
ubicación. Usa el endpoint JSON interno de búsqueda de Wallapop (no es una
API pública documentada, puede cambiar).
"""
import logging

from app import config
from app.services.http_utils import get_session, polite_sleep, dig

logger = logging.getLogger("flipgames.wallapop")

SEARCH_URL = "https://api.wallapop.com/api/v3/general/search"


def search(query: str, limit: int = None):
    limit = limit or config.LISTINGS_PER_GAME
    session = get_session()

    try:
        resp = session.get(
            SEARCH_URL,
            params={
                "keywords": query,
                "latitude": config.WALLAPOP_LAT,
                "longitude": config.WALLAPOP_LON,
                "order_by": "price_low_to_high",
            },
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Fallo consultando Wallapop para %r: %s", query, exc)
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

    polite_sleep()
    return results
