"""Capa de acceso a la base de datos (SQLite, sin dependencias externas)."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    platform TEXT NOT NULL,
    condition TEXT NOT NULL DEFAULT 'sin_confirmar',   -- con_caratula | sin_caratula | sin_confirmar
    source TEXT NOT NULL,                              -- vinted | wallapop
    listing_url TEXT,
    listing_price REAL NOT NULL,
    currency_status TEXT NOT NULL DEFAULT 'sin_confirmar', -- eur | no_eur | sin_confirmar
    seller_location TEXT,
    cex_cash_price REAL NOT NULL,
    profit_estimate REAL NOT NULL,
    margin_pct REAL,
    status TEXT NOT NULL DEFAULT 'pendiente',           -- pendiente | comprado | descartado
    bought_price REAL,
    bought_profit REAL,
    found_at TEXT NOT NULL,
    bought_at TEXT,
    is_pack INTEGER NOT NULL DEFAULT 0,
    matched_titles TEXT,                                -- juegos detectados dentro del pack, separados por " | "
    UNIQUE(title, platform, source, listing_url)
);
CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);
CREATE INDEX IF NOT EXISTS idx_deals_profit ON deals(profit_estimate);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    platform TEXT NOT NULL,
    cex_cash_price REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(title, platform)
);
"""

# Columnas añadidas después de la primera versión: si la base de datos ya
# existía (creada antes de que existiera esta columna), hay que agregarlas
# a mano porque SQLite no las crea solo con CREATE TABLE IF NOT EXISTS.
_MIGRATIONS = [
    ("is_pack", "INTEGER NOT NULL DEFAULT 0"),
    ("matched_titles", "TEXT"),
]


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(deals)")}
        for col_name, col_def in _MIGRATIONS:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE deals ADD COLUMN {col_name} {col_def}")


def upsert_deal(deal: dict):
    """Inserta un deal nuevo o actualiza el precio/beneficio si ya existía
    (mismo título+plataforma+origen+url) y sigue pendiente."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT id, status FROM deals WHERE title=? AND platform=? AND source=? AND listing_url=?",
            (deal["title"], deal["platform"], deal["source"], deal["listing_url"]),
        )
        row = cur.fetchone()
        if row and row["status"] != "pendiente":
            return row["id"]  # no tocar deals ya comprados/descartados
        is_pack = int(deal.get("is_pack", False))
        matched_titles = deal.get("matched_titles")
        if row:
            conn.execute(
                """UPDATE deals SET listing_price=?, currency_status=?, seller_location=?,
                   cex_cash_price=?, profit_estimate=?, margin_pct=?, condition=?, found_at=?,
                   is_pack=?, matched_titles=?
                   WHERE id=?""",
                (
                    deal["listing_price"], deal["currency_status"], deal["seller_location"],
                    deal["cex_cash_price"], deal["profit_estimate"], deal["margin_pct"],
                    deal["condition"], now, is_pack, matched_titles, row["id"],
                ),
            )
            return row["id"]
        cur = conn.execute(
            """INSERT INTO deals (title, platform, condition, source, listing_url, listing_price,
               currency_status, seller_location, cex_cash_price, profit_estimate, margin_pct,
               status, found_at, is_pack, matched_titles)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?, ?)""",
            (
                deal["title"], deal["platform"], deal["condition"], deal["source"],
                deal["listing_url"], deal["listing_price"], deal["currency_status"],
                deal["seller_location"], deal["cex_cash_price"], deal["profit_estimate"],
                deal["margin_pct"], now, is_pack, matched_titles,
            ),
        )
        return cur.lastrowid


def list_deals(status=None, order_by="profit_estimate DESC"):
    query = "SELECT * FROM deals"
    params = ()
    if status:
        query += " WHERE status=?"
        params = (status,)
    query += f" ORDER BY {order_by}"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_deal(deal_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM deals WHERE id=?", (deal_id,)).fetchone()
        return dict(row) if row else None


def mark_bought(deal_id, bought_price):
    deal = get_deal(deal_id)
    if not deal:
        return None
    profit = round(deal["cex_cash_price"] - bought_price, 2)
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """UPDATE deals SET status='comprado', bought_price=?, bought_profit=?, bought_at=?
               WHERE id=?""",
            (bought_price, profit, now, deal_id),
        )
    return profit


def mark_status(deal_id, status):
    with get_conn() as conn:
        conn.execute("UPDATE deals SET status=? WHERE id=?", (status, deal_id))


def set_currency_status(deal_id, currency_status):
    with get_conn() as conn:
        conn.execute("UPDATE deals SET currency_status=? WHERE id=?", (currency_status, deal_id))
        if currency_status == "no_eur":
            conn.execute("UPDATE deals SET status='descartado' WHERE id=?", (deal_id,))


def summary():
    with get_conn() as conn:
        row = conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN status='comprado' THEN bought_profit END), 0) AS total_profit,
                 COUNT(CASE WHEN status='comprado' THEN 1 END) AS num_purchases,
                 COUNT(CASE WHEN status='pendiente' THEN 1 END) AS num_pending
               FROM deals"""
        ).fetchone()
        return dict(row)


def upsert_game(title: str, platform: str, cex_cash_price: float):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO games (title, platform, cex_cash_price, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(title, platform) DO UPDATE SET
                 cex_cash_price=excluded.cex_cash_price, updated_at=excluded.updated_at""",
            (title.strip(), platform, cex_cash_price, now),
        )


def list_games(platform=None):
    query = "SELECT * FROM games"
    params = ()
    if platform:
        query += " WHERE platform=?"
        params = (platform,)
    query += " ORDER BY platform, title"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def delete_game(game_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM games WHERE id=?", (game_id,))


def cumulative_profit_series():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT bought_at, bought_profit FROM deals WHERE status='comprado' ORDER BY bought_at ASC"
        ).fetchall()
    labels, values = [], []
    running = 0.0
    for r in rows:
        running += r["bought_profit"] or 0
        labels.append(r["bought_at"])
        values.append(round(running, 2))
    return labels, values
