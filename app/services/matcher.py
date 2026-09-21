"""Clasifica anuncios (con/sin carátula), detecta lotes/packs de varios
juegos en un mismo anuncio, y calcula el beneficio frente al precio que
paga CEX en efectivo."""
import re
import unicodedata
from typing import List, Optional

from app import config

# Palabras que sugieren que un anuncio es un lote de varios juegos, no uno solo
PACK_WORDS = ("lote", "pack", "varios juegos", "bundle", "juegos sueltos", "x juegos")

_CON_CARATULA_WORDS = (
    "completo", "con caja", "con funda", "con estuche", "caja y manual",
    "cib", "boxed", "case included", "con carátula", "con caratula",
)
_SIN_CARATULA_WORDS = (
    "solo cartucho", "solo el cartucho", "suelto", "sin caja", "sin funda",
    "sin estuche", "cartucho solo", "loose", "cart only", "cartridge only",
    "sin carátula", "sin caratula",
)

# Anuncios que venden SOLO la caja/manual, sin el cartucho — no es un juego
# de verdad (no hay nada que revender a CEX), así que se descartan del todo
# más abajo en build_deal/build_pack_deal. Solo cuentan si NO se menciona
# también el cartucho en el mismo texto (para no descartar por error un
# anuncio "completo: caja + manual + cartucho").
_BOX_ONLY_WORDS = (
    "sin cartucho", "sin el cartucho", "sin juego", "sin el juego",
    "solo caja", "solo la caja", "solo manual", "solo el manual",
    "caja vacia", "caja vacía", "caja+manual", "caja + manual", "caja y manual",
    "solo caratula", "solo carátula",
)
_CARTRIDGE_MENTIONED_WORDS = ("cartucho", "completo", "cib", "juego incluido")

# Importaciones de otras regiones: CEX paga por versiones PAL/España, no por
# imports (y en 3DS/Switch ni siquiera funcionarían por el bloqueo regional).
_IMPORT_WORDS_RE = re.compile(
    r"\b(jpn|jap|japones|japonés|japon|japan|ntsc-?j|ntsc-?u|usa import|us version|import)\b",
    re.IGNORECASE,
)


def classify_condition(text: str) -> str:
    text = (text or "").lower()
    if any(w in text for w in _CON_CARATULA_WORDS):
        return "con_caratula"
    if any(w in text for w in _SIN_CARATULA_WORDS):
        return "sin_caratula"
    return "sin_confirmar"


def is_box_only(text: str) -> bool:
    """True si el anuncio vende solo la caja/manual sin el cartucho (no hay
    juego de verdad que revender)."""
    norm = (text or "").lower()
    if any(w in norm for w in _CARTRIDGE_MENTIONED_WORDS):
        return False
    return any(w in norm for w in _BOX_ONLY_WORDS)


def is_import(text: str) -> bool:
    """True si el anuncio parece ser una versión importada (JPN/USA...) en
    vez de la versión PAL/España que compraría CEX."""
    return bool(_IMPORT_WORDS_RE.search(text or ""))


def build_deal(game: dict, listing: dict) -> Optional[dict]:
    """Combina un juego (con su precio en efectivo de CEX) con un anuncio de
    marketplace, y calcula el beneficio estimado. Devuelve None si no es
    rentable (por debajo del umbral configurado)."""
    price = listing["listing_price"]
    if price <= 0:
        return None
    text = listing.get("raw_description") or listing["title"]
    if is_box_only(text) or is_import(text):
        return None
    profit = round(game["cex_cash_price"] - price, 2)
    if profit < config.MIN_PROFIT_EUR:
        return None
    margin_pct = round((profit / price) * 100, 1) if price else None

    return {
        "title": game["title"],
        "platform": game["platform"],
        "condition": classify_condition(text),
        "source": listing["source"],
        "listing_url": listing["listing_url"],
        "listing_price": price,
        "currency_status": listing["currency_status"],
        "seller_location": listing.get("seller_location"),
        "cex_cash_price": game["cex_cash_price"],
        "profit_estimate": profit,
        "margin_pct": margin_pct,
        "is_pack": False,
        "matched_titles": None,
    }


def _normalize(text: str) -> str:
    text = (text or "").lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9 ]", " ", text)


def looks_like_pack(text: str) -> bool:
    norm = _normalize(text)
    return any(w in norm for w in PACK_WORDS)


def find_matching_games(text: str, games: List[dict]) -> List[dict]:
    """Busca, dentro del texto de un anuncio, qué juegos (de los ya
    consultados en CEX para esa plataforma) parecen estar mencionados.
    Es un matching por texto, best-effort: puede dar falsos positivos o
    negativos, así que siempre hay que revisar el anuncio a mano antes de
    comprar un pack."""
    norm_text = _normalize(text)
    matches = []
    seen_titles = set()
    for game in games:
        norm_title = _normalize(game["title"])
        # títulos muy cortos dan demasiados falsos positivos
        if len(norm_title) < 6:
            continue
        if norm_title in norm_text and game["title"] not in seen_titles:
            matches.append(game)
            seen_titles.add(game["title"])
    return matches


def build_pack_deal(matched_games: List[dict], listing: dict, platform: str) -> Optional[dict]:
    """Combina varios juegos detectados dentro de un mismo anuncio (lote/pack)
    y calcula el beneficio total frente a la suma de lo que pagaría CEX por
    cada uno por separado."""
    price = listing["listing_price"]
    if price <= 0 or len(matched_games) < config.PACK_MIN_GAMES:
        return None
    text = listing.get("raw_description") or listing["title"]
    if is_box_only(text) or is_import(text):
        return None
    total_cex = sum(g["cex_cash_price"] for g in matched_games)
    profit = round(total_cex - price, 2)
    if profit < config.MIN_PROFIT_EUR:
        return None
    margin_pct = round((profit / price) * 100, 1) if price else None
    titles = [g["title"] for g in matched_games]

    return {
        "title": f"Pack ({len(titles)} juegos): " + ", ".join(titles[:4]) + (
            "…" if len(titles) > 4 else ""
        ),
        "platform": platform,
        "condition": classify_condition(text),
        "source": listing["source"],
        "listing_url": listing["listing_url"],
        "listing_price": price,
        "currency_status": listing["currency_status"],
        "seller_location": listing.get("seller_location"),
        "cex_cash_price": round(total_cex, 2),
        "profit_estimate": profit,
        "margin_pct": margin_pct,
        "is_pack": True,
        "matched_titles": " | ".join(titles),
    }
