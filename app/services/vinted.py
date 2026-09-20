"""Cliente para Vinted: busca anuncios de un juego y extrae precio/moneda/
ubicación. Usa el endpoint JSON interno del buscador de Vinted (no es una
API pública documentada, puede cambiar).
"""
import logging

from app import config
from app.services.http_utils import get_session, polite_sleep, dig

logger = logging.getLogger("flipgames.vinted")

HOME_URL = "https://www.vinted.es/"
SEARCH_URL = "https://www.vinted.es/api/v2/catalog/items"


def _ensure_session_cookies(session):
    """Vinted exige cookies de sesión (anti-bot) antes de aceptar llamadas
    a la API; las conseguimos visitando la home una vez."""
    if session.cookies.get("_vinted_fr_session"):
        return
    try:
        session.get(HOME_URL, timeout=config.REQUEST_TIMEOUT)
    except Exception as exc:
        logger.warning("No se pudo obtener cookies de Vinted: %s", exc)


def search(query: str, limit: int = None):
    limit = limit or config.LISTINGS_PER_GAME
    session = get_session()
    _ensure_session_cookies(session)

    try:
        resp = session.get(
            SEARCH_URL,
            params={
                "search_text": query,
                "order": "price_low_to_high",
                "per_page": limit,
                "currency": "EUR",
            },
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Fallo consultando Vinted para %r: %s", query, exc)
        return []

    items = dig(data, "items", default=[]) or []
    results = []
    for item in items[:limit]:
        price = dig(item, "price", "amount", default=None)
        currency = dig(item, "price", "currency_code", default=None)
        if price is None:
            # algunas versiones de la API devuelven "total_item_price" o "price" plano
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

    polite_sleep()
    return results
