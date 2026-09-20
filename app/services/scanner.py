"""Orquesta el escaneo completo: para cada plataforma, pide a CEX los juegos
con mejor precio en efectivo, busca anuncios en Vinted y Wallapop, calcula
el beneficio y guarda las oportunidades rentables en la base de datos."""
import logging

from app import config, db
from app.services import cex, vinted, wallapop
from app.services.matcher import build_deal

logger = logging.getLogger("flipgames.scanner")


def run_scan(platforms=None):
    platforms = platforms or config.PLATFORMS
    stats = {"games_checked": 0, "listings_checked": 0, "deals_found": 0, "errors": []}

    for platform in platforms:
        try:
            games = cex.search_platform_games(platform)
        except Exception as exc:
            logger.exception("Error buscando en CEX para %s", platform)
            stats["errors"].append(f"CEX/{platform}: {exc}")
            continue

        for game in games:
            stats["games_checked"] += 1
            query = f"{game['title']} {platform}"
            listings = []
            for fetcher, name in ((vinted.search, "vinted"), (wallapop.search, "wallapop")):
                try:
                    listings += fetcher(query)
                except Exception as exc:
                    logger.exception("Error buscando en %s para %r", name, query)
                    stats["errors"].append(f"{name}/{query}: {exc}")

            for listing in listings:
                stats["listings_checked"] += 1
                deal = build_deal(game, listing)
                if deal is None:
                    continue
                db.upsert_deal(deal)
                stats["deals_found"] += 1

    return stats
