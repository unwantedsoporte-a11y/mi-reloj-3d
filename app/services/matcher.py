"""Clasifica anuncios (con/sin carátula) y calcula el beneficio frente al
precio que paga CEX en efectivo."""
from typing import Optional

from app import config

_CON_CARATULA_WORDS = (
    "completo", "con caja", "con funda", "con estuche", "caja y manual",
    "cib", "boxed", "case included", "con carátula", "con caratula",
)
_SIN_CARATULA_WORDS = (
    "solo cartucho", "solo el cartucho", "suelto", "sin caja", "sin funda",
    "sin estuche", "cartucho solo", "loose", "cart only", "cartridge only",
    "sin carátula", "sin caratula",
)


def classify_condition(text: str) -> str:
    text = (text or "").lower()
    if any(w in text for w in _CON_CARATULA_WORDS):
        return "con_caratula"
    if any(w in text for w in _SIN_CARATULA_WORDS):
        return "sin_caratula"
    return "sin_confirmar"


def build_deal(game: dict, listing: dict) -> Optional[dict]:
    """Combina un juego (con su precio en efectivo de CEX) con un anuncio de
    marketplace, y calcula el beneficio estimado. Devuelve None si no es
    rentable (por debajo del umbral configurado)."""
    price = listing["listing_price"]
    if price <= 0:
        return None
    profit = round(game["cex_cash_price"] - price, 2)
    if profit < config.MIN_PROFIT_EUR:
        return None
    margin_pct = round((profit / price) * 100, 1) if price else None

    return {
        "title": game["title"],
        "platform": game["platform"],
        "condition": classify_condition(listing.get("raw_description") or listing["title"]),
        "source": listing["source"],
        "listing_url": listing["listing_url"],
        "listing_price": price,
        "currency_status": listing["currency_status"],
        "seller_location": listing.get("seller_location"),
        "cex_cash_price": game["cex_cash_price"],
        "profit_estimate": profit,
        "margin_pct": margin_pct,
    }
