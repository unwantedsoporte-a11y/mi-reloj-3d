"""Configuración de la app. Ajusta estos valores a tu gusto."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "flipgames.db")

# Plataformas que se buscan en CEX / Vinted / Wallapop
PLATFORMS = ["Nintendo Switch", "Nintendo 3DS", "Nintendo DS"]

# Cuántos juegos por plataforma se consultan en cada escaneo (para no tardar
# una eternidad ni martillear las webs a lo bestia)
SCAN_LIMIT_PER_PLATFORM = int(os.environ.get("SCAN_LIMIT_PER_PLATFORM", 25))

# Cuántos anuncios de Vinted/Wallapop se miran por cada juego
LISTINGS_PER_GAME = int(os.environ.get("LISTINGS_PER_GAME", 5))

# Beneficio mínimo (€) para que un "deal" se guarde como oportunidad
MIN_PROFIT_EUR = float(os.environ.get("MIN_PROFIT_EUR", 2.0))

# --- Packs / lotes de varios juegos en un mismo anuncio ---
PACK_SEARCH_TERMS = ["lote juegos", "pack juegos", "varios juegos"]
PACK_LISTINGS_PER_QUERY = int(os.environ.get("PACK_LISTINGS_PER_QUERY", 10))
PACK_MIN_GAMES = int(os.environ.get("PACK_MIN_GAMES", 2))

# País de CEX a consultar (afecta a la web y a los precios). "es" = España.
CEX_COUNTRY = os.environ.get("CEX_COUNTRY", "es")
CEX_SITE_URL = f"https://{CEX_COUNTRY}.webuy.com/"

# Precio mínimo que debe pagar CEX en efectivo para que nos molestemos en mirarlo
MIN_CEX_CASH_PRICE = float(os.environ.get("MIN_CEX_CASH_PRICE", 3.0))

# Ubicación por defecto para Wallapop (Madrid). Cámbiala por la tuya si quieres
# resultados de envío/ubicación más cercanos.
WALLAPOP_LAT = float(os.environ.get("WALLAPOP_LAT", 40.4168))
WALLAPOP_LON = float(os.environ.get("WALLAPOP_LON", -3.7038))

# Pausa (segundos) entre peticiones a marketplaces para no ser agresivos
REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", 0.8))

# Cabecera User-Agent usada en las peticiones
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

REQUEST_TIMEOUT = 15
