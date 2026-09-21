"""Cliente para Vinted: abre la página de búsqueda real en un navegador
(Playwright) y captura la respuesta JSON que la propia web pide para
mostrar los resultados (api.vinted.es/svc-catalogue/items). Vinted
bloquea las peticiones directas sin pasar por un navegador real, por eso
se hace así.

Nota sobre monedas: cada vendedor pone el precio en la moneda que quiera,
no depende de buscar desde España — por eso NO se descartan aquí los
anuncios que no estén en EUR, se marcan con currency_status='no_eur' o
'sin_confirmar' para que el usuario decida en el panel."""
import logging

from app import config
from app.services import browser
from app.services.http_utils import dig

logger = logging.getLogger("flipgames.vinted")

HOME_URL = "https://www.vinted.es/"
API_URL_FRAGMENTS = ["/svc-catalogue/items"]


def search(query: str, limit: int = None):
    limit = limit or config.LISTINGS_PER_GAME

    try:
        data = browser.search_via_typing(HOME_URL, query, API_URL_FRAGMENTS)
    except browser.BrowserNotReady as exc:
        logger.warning("Vinted: %s", exc)
        return []

    if data is None:
        logger.warning("Fallo consultando Vinted para %r (sin respuesta de la API)", query)
        return []

    items = dig(data, "items", default=[]) or []
    results = []
    for item in items[:limit]:
        # total_item_price = precio + protección al comprador (lo que se paga
        # de verdad); si no viene, usamos el precio base del artículo.
        price = dig(item, "total_item_price", "amount", default=None)
        currency = dig(item, "total_item_price", "currency_code", default=None)
        if price is None:
            price = dig(item, "price", "amount", default=None)
            currency = currency or dig(item, "price", "currency_code", default=None)
        if price is None:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue

        currency_status = "eur" if currency == "EUR" else ("sin_confirmar" if not currency else "no_eur")
        item_id = item.get("id")
        url_path = item.get("url")
        if url_path:
            url = url_path if url_path.startswith("http") else f"https://www.vinted.es{url_path}"
        else:
            url = f"https://www.vinted.es/items/{item_id}" if item_id else None

        title = item.get("title") or dig(item, "item_box", "first_line", default=None) or query

        results.append({
            "source": "vinted",
            "title": title,
            "listing_price": price,
            "currency_status": currency_status,
            "seller_location": item.get("city") or dig(item, "user", "city", default=None),
            "listing_url": url,
            "raw_description": title,
        })

    return results
