"""Datos de ejemplo para probar el panel sin depender de red externa.

Útil para comprobar que la interfaz funciona (tabla, botones, gráfica)
mientras ajustas los clientes reales de CEX/Vinted/Wallapop, o si
estás en un entorno sin salida a internet."""
from app import db
from app.services.matcher import build_deal, build_pack_deal

_SAMPLE = [
    # (juego, plataforma, precio_cex_efectivo, [(origen, precio, moneda_ok, ubicacion, descripcion), ...])
    ("The Legend of Zelda: Tears of the Kingdom", "Nintendo Switch", 38.0, [
        ("vinted", 19.0, "eur", "Madrid", "Cartucho suelto, sin caja"),
        ("wallapop", 22.5, "eur", "Barcelona", "Completo con caja y manual"),
    ]),
    ("Mario Kart 8 Deluxe", "Nintendo Switch", 35.0, [
        ("vinted", 24.0, "eur", "Valencia", "Solo cartucho"),
        ("wallapop", 26.0, None, None, "Como nuevo"),
    ]),
    ("Animal Crossing: New Horizons", "Nintendo Switch", 28.0, [
        ("vinted", 15.0, "eur", "Sevilla", "Con caja y funda"),
    ]),
    ("Pokémon Omega Ruby", "Nintendo 3DS", 22.0, [
        ("wallapop", 8.0, "eur", "Bilbao", "Cartucho suelto"),
        ("vinted", 9.5, None, None, "Sin caja"),
    ]),
    ("Mario Kart 7", "Nintendo 3DS", 14.0, [
        ("vinted", 6.0, "eur", "Zaragoza", "Completo"),
    ]),
    ("New Super Mario Bros", "Nintendo DS", 16.0, [
        ("wallapop", 5.0, "eur", "Malaga", "Solo cartucho, funciona perfecto"),
    ]),
]

# Ejemplo de anuncio "lote" que junta varios juegos de los de arriba
_SAMPLE_PACK = {
    "source": "wallapop",
    "title": "Lote juegos Nintendo Switch",
    "listing_price": 30.0,
    "currency_status": "eur",
    "seller_location": "Madrid",
    "listing_url": "https://example.com/wallapop/lote-switch",
    "raw_description": (
        "Vendo pack de varios juegos: The Legend of Zelda: Tears of the Kingdom, "
        "Mario Kart 8 Deluxe y Animal Crossing: New Horizons. Todo en buen estado."
    ),
}


def seed():
    total = 0
    all_games_by_platform = {}
    for title, platform, cex_price, listings in _SAMPLE:
        game = {"title": title, "platform": platform, "cex_cash_price": cex_price}
        all_games_by_platform.setdefault(platform, []).append(game)
        for source, price, currency, location, desc in listings:
            listing = {
                "source": source,
                "title": title,
                "listing_price": price,
                "currency_status": currency or "sin_confirmar",
                "seller_location": location,
                "listing_url": f"https://example.com/{source}/{title.replace(' ', '-').lower()}",
                "raw_description": desc,
            }
            deal = build_deal(game, listing)
            if deal:
                db.upsert_deal(deal)
                total += 1

    switch_games = all_games_by_platform.get("Nintendo Switch", [])
    matched = [g for g in switch_games if g["title"] in _SAMPLE_PACK["raw_description"]]
    pack_deal = build_pack_deal(matched, _SAMPLE_PACK, "Nintendo Switch")
    if pack_deal:
        db.upsert_deal(pack_deal)
        total += 1

    return total
