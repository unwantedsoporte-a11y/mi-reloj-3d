"""Datos de ejemplo para probar el panel sin depender de red externa.

Útil para comprobar que la interfaz funciona (tabla, botones, gráfica)
mientras ajustas los clientes reales de CEX/Vinted/Wallapop, o si
estás en un entorno sin salida a internet."""
from app import db
from app.services.matcher import build_deal

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


def seed():
    total = 0
    for title, platform, cex_price, listings in _SAMPLE:
        game = {"title": title, "platform": platform, "cex_cash_price": cex_price}
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
    return total
