"""Cliente para CEX (webuy): busca el precio que pagan EN EFECTIVO por juegos.

Usa el endpoint JSON que utiliza la propia web de CEX para su buscador
(no es una API pública documentada). Si CEX cambia su API, ajusta
BASE_URL / el parseo de `_price_from_box` — se han dejado varias formas de
extraer el precio para ser lo más resistente posible a cambios de nombre
de campo.
"""
import logging

from app import config
from app.services.http_utils import get_session, polite_sleep, dig, find_first_matching_key

logger = logging.getLogger("flipgames.cex")

BASE_URL = f"https://wss2.cex.{config.CEX_COUNTRY}.webuy.io/v3/boxes"

# CEX usa "Nintendo Switch", "Nintendo DS", "Nintendo 3DS" en el nombre de
# categoría/título; con esto filtramos accesorios/consolas y nos quedamos
# solo con juegos.
_EXCLUDE_WORDS = ("console", "consola", "cargador", "charger", "mando", "controller",
                  "funda", "case", "cable", "adaptador", "adapter", "docking")


def _price_from_box(box: dict):
    """Precio en efectivo ('cash') que CEX pagaría por el artículo."""
    for key in ("cashPrice", "CashPrice", "cash_price"):
        val = box.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    # Red de seguridad: busca cualquier campo cuyo nombre contenga "cash"
    val = find_first_matching_key(box, "cash")
    if isinstance(val, (int, float)) and val > 0:
        return float(val)
    return None


def _looks_like_game(box: dict, platform: str) -> bool:
    name = (box.get("boxName") or box.get("boxDetail") or "").lower()
    category = (box.get("categoryFriendlyName") or "").lower()
    if not name:
        return False
    if any(word in name for word in _EXCLUDE_WORDS):
        return False
    if "game" not in category and "juego" not in category and "software" not in category:
        # Si la categoría no lo deja claro, exigimos al menos que no parezca hardware
        if any(word in category for word in ("console", "hardware", "accessor")):
            return False
    return True


def _ensure_session_cookies(session):
    """CEX bloquea con 403 las peticiones que no parecen venir de un
    navegador real. Visitamos su web una vez para conseguir cookies de
    sesión antes de llamar a la API."""
    if session.cookies.get("_abck") or session.cookies.get("bm_sz"):
        return
    try:
        session.get(config.CEX_SITE_URL, timeout=config.REQUEST_TIMEOUT)
    except Exception as exc:
        logger.warning("No se pudo obtener cookies de CEX: %s", exc)


def search_platform_games(platform: str, limit: int = None):
    """Devuelve una lista de dicts {title, cex_cash_price, box_id} para una
    plataforma dada (p.ej. 'Nintendo Switch'), ordenados por precio en
    efectivo descendente."""
    limit = limit or config.SCAN_LIMIT_PER_PLATFORM
    session = get_session()
    _ensure_session_cookies(session)
    games = {}
    page_size = 50
    try:
        resp = session.get(
            BASE_URL,
            params={
                "q": platform,
                "firstRecord": 1,
                "pageSize": page_size,
                "sortBy": "cashPrice",
                "sortOrder": "desc",
                "inStock": 1,
            },
            headers={
                "Referer": config.CEX_SITE_URL,
                "Origin": config.CEX_SITE_URL.rstrip("/"),
            },
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Fallo consultando CEX para %s: %s", platform, exc)
        return []

    boxes = (
        dig(data, "response", "data", "boxes", default=None)
        or dig(data, "response", "data", "results", default=None)
        or []
    )
    for box in boxes:
        if not _looks_like_game(box, platform):
            continue
        price = _price_from_box(box)
        if price is None or price < config.MIN_CEX_CASH_PRICE:
            continue
        title = (box.get("boxName") or "").strip()
        if not title:
            continue
        # nos quedamos con el precio más alto si el título se repite
        # (ediciones distintas con el mismo nombre "limpio")
        if title not in games or games[title]["cex_cash_price"] < price:
            games[title] = {
                "title": title,
                "platform": platform,
                "cex_cash_price": price,
                "box_id": box.get("boxId"),
            }

    result = sorted(games.values(), key=lambda g: g["cex_cash_price"], reverse=True)
    polite_sleep()
    return result[:limit]
