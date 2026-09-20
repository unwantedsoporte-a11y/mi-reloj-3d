"""Orquesta el escaneo: para cada plataforma, busca automáticamente los
juegos con mejor precio en efectivo en CEX (navegador automatizado) y los
combina con los que hayas guardado a mano en "Mis juegos". Para cada uno,
busca anuncios en Vinted y Wallapop (también con navegador automatizado),
calcula el beneficio y guarda las oportunidades rentables. También busca
packs/lotes de varios juegos en un mismo anuncio."""
import logging

from app import config, db
from app.services import cex, vinted, wallapop
from app.services.matcher import build_deal, build_pack_deal, find_matching_games, looks_like_pack

logger = logging.getLogger("flipgames.scanner")


def _fetch_listings(query, stats):
    listings = []
    for fetcher, name in ((vinted.search, "vinted"), (wallapop.search, "wallapop")):
        try:
            listings += fetcher(query)
        except Exception as exc:
            logger.exception("Error buscando en %s para %r", name, query)
            stats["errors"].append(f"{name}/{query}: {exc}")
    return listings


def _scan_packs(platform, games, stats):
    """Busca anuncios de lotes/packs de varios juegos y comprueba si, sumando
    lo que pagaría CEX por cada juego detectado dentro del anuncio, sale
    rentable frente al precio del lote."""
    if not games:
        return
    for term in config.PACK_SEARCH_TERMS:
        query = f"{term} {platform}"
        listings = _fetch_listings(query, stats)
        for listing in listings[: config.PACK_LISTINGS_PER_QUERY]:
            stats["listings_checked"] += 1
            text = f"{listing['title']} {listing.get('raw_description') or ''}"
            if not looks_like_pack(text):
                continue
            matched = find_matching_games(text, games)
            if len(matched) < config.PACK_MIN_GAMES:
                continue
            deal = build_pack_deal(matched, listing, platform)
            if deal is None:
                continue
            db.upsert_deal(deal)
            stats["deals_found"] += 1
            stats["packs_found"] += 1


def _collect_games(platforms):
    """Junta los juegos encontrados automáticamente en CEX con los que el
    usuario haya guardado a mano en 'Mis juegos', sin repetir títulos."""
    games_by_platform = {}
    errors = []

    for platform in platforms:
        try:
            games_by_platform[platform] = list(cex.search_platform_games(platform))
        except Exception as exc:
            logger.exception("Error buscando en CEX para %s", platform)
            errors.append(f"CEX/{platform}: {exc}")
            games_by_platform[platform] = []

    for game in db.list_games():
        games_by_platform.setdefault(game["platform"], []).append(game)

    for platform, games in games_by_platform.items():
        seen = set()
        unique_games = []
        for g in games:
            key = g["title"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            unique_games.append(g)
        games_by_platform[platform] = unique_games

    return games_by_platform, errors


def run_scan(platforms=None):
    platforms = platforms or config.PLATFORMS
    stats = {"games_checked": 0, "listings_checked": 0, "deals_found": 0, "packs_found": 0, "errors": []}

    games_by_platform, errors = _collect_games(platforms)
    stats["errors"].extend(errors)

    if not any(games_by_platform.values()):
        stats["errors"].append(
            "No se encontró ningún juego (ni en CEX automático ni en 'Mis juegos'). "
            "Añade alguno a mano en 'Mis juegos' o revisa los errores de arriba."
        )
        return stats

    for platform, games in games_by_platform.items():
        for game in games:
            stats["games_checked"] += 1
            query = f"{game['title']} {platform}"
            listings = _fetch_listings(query, stats)

            for listing in listings:
                stats["listings_checked"] += 1
                deal = build_deal(game, listing)
                if deal is None:
                    continue
                db.upsert_deal(deal)
                stats["deals_found"] += 1

        _scan_packs(platform, games, stats)

    return stats
