"""Cliente para CEX (webuy): busca el precio que pagan EN EFECTIVO por
juegos. CEX usa Algolia como buscador y expone una clave pública de solo
búsqueda en el propio HTML de su web (pensada para usarse desde el
navegador de cualquier visitante, así que no es ningún secreto): con eso
podemos consultar directamente su índice sin necesitar un navegador
automatizado, mucho más rápido y fiable que abrir la página cada vez.

Si algún día CEX cambia de proveedor de búsqueda o rota la clave, esto
dejará de funcionar (fallará de forma controlada, sin romper la app).
Para volver a sacar los datos: abre es.webuy.com, F12 -> pestaña Network
-> filtra por "algolia" -> busca algo -> mira la petición "queries" (URL,
x-algolia-api-key, x-algolia-application-id e indexName del payload).
"""
import logging
from urllib.parse import quote

import requests

from app import config
from app.services.http_utils import dig

logger = logging.getLogger("flipgames.cex")

ALGOLIA_URL = "https://search.webuy.io/1/indexes/*/queries"
ALGOLIA_APP_ID = "LNNFEEWZVA"
ALGOLIA_API_KEY = "bf79f2b6699e60a18ae330a1248b452c"
ALGOLIA_INDEX = f"prod_cex_{config.CEX_COUNTRY}"
REQUEST_TIMEOUT = 15

_EXCLUDE_WORDS = ("console", "consola", "cargador", "charger", "mando", "controller",
                  "funda", "case", "cable", "adaptador", "adapter", "docking",
                  "joy-con", "joy con", "joycon")


def _looks_like_game(hit: dict) -> bool:
    name = (hit.get("boxName") or "").lower()
    category = (hit.get("categoryFriendlyName") or hit.get("categoryName") or "").lower()
    if not name:
        return False
    # la categoría de CEX para juegos siempre incluye la palabra "juegos"
    # (ej. "Switch Juegos", "3DS Juegos"); si no la tiene, casi seguro es
    # un accesorio (mando, cargador, funda...) y no un juego.
    if "juego" not in category and "game" not in category:
        return False
    if any(word in name for word in _EXCLUDE_WORDS):
        return False
    return True


def search_platform_games(platform: str, limit: int = None):
    """Devuelve una lista de dicts {title, platform, cex_cash_price} para
    una plataforma dada (p.ej. 'Nintendo Switch'), ordenados por precio en
    efectivo descendente."""
    limit = limit or config.SCAN_LIMIT_PER_PLATFORM
    payload = {
        "requests": [{
            "indexName": ALGOLIA_INDEX,
            "params": f"query={quote(platform)}&hitsPerPage=100&page=0",
        }]
    }

    try:
        resp = requests.post(
            ALGOLIA_URL,
            params={
                "x-algolia-agent": "Algolia for JavaScript (5.21.1); Search (5.21.1); Browser",
                "x-algolia-api-key": ALGOLIA_API_KEY,
                "x-algolia-application-id": ALGOLIA_APP_ID,
            },
            json=payload,
            headers={
                "Referer": f"https://{config.CEX_COUNTRY}.webuy.com/",
                "Origin": f"https://{config.CEX_COUNTRY}.webuy.com",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Fallo consultando CEX (Algolia) para %s: %s", platform, exc)
        return []

    hits = dig(data, "results", 0, "hits", default=[]) or []
    games = {}
    for hit in hits:
        if not _looks_like_game(hit):
            continue
        price = hit.get("cashPriceCalculated")
        if not isinstance(price, (int, float)) or price < config.MIN_CEX_CASH_PRICE:
            continue
        title = (hit.get("boxName") or "").strip()
        if not title:
            continue
        if title not in games or games[title]["cex_cash_price"] < price:
            games[title] = {"title": title, "platform": platform, "cex_cash_price": float(price)}

    result = sorted(games.values(), key=lambda g: g["cex_cash_price"], reverse=True)
    return result[:limit]
