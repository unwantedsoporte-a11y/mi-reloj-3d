import logging

from flask import Flask, jsonify, render_template, request

from app import db
from app.services import demo
from app.services.scanner import run_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
db.init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/historial")
def historial():
    return render_template("historial.html")


@app.route("/games")
def games_page():
    return render_template("games.html")


@app.route("/api/games")
def api_games():
    return jsonify(db.list_games())


@app.route("/api/games", methods=["POST"])
def api_games_add():
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get("title") or "").strip()
    platform = (body.get("platform") or "").strip()
    try:
        price = float(body.get("cex_cash_price"))
    except (TypeError, ValueError):
        return jsonify({"error": "cex_cash_price inválido"}), 400
    if not title or not platform:
        return jsonify({"error": "Falta title o platform"}), 400
    if price <= 0:
        return jsonify({"error": "El precio debe ser mayor que 0"}), 400
    db.upsert_game(title, platform, price)
    return jsonify({"ok": True})


@app.route("/games/<int:game_id>/delete", methods=["POST"])
def api_games_delete(game_id):
    db.delete_game(game_id)
    return jsonify({"ok": True})


@app.route("/api/deals")
def api_deals():
    status = request.args.get("status", "pendiente")
    if status == "todos":
        status = None
    deals = db.list_deals(status=status)
    return jsonify(deals)


@app.route("/api/summary")
def api_summary():
    return jsonify(db.summary())


@app.route("/api/chart")
def api_chart():
    labels, values = db.cumulative_profit_series()
    return jsonify({"labels": labels, "cumulative_profit": values})


@app.route("/scan", methods=["POST"])
def scan():
    stats = run_scan()
    return jsonify(stats)


@app.route("/scan/demo", methods=["POST"])
def scan_demo():
    """Carga datos de ejemplo (sin tocar la red) para probar el panel."""
    total = demo.seed()
    return jsonify({"deals_found": total})


@app.route("/deals/<int:deal_id>/buy", methods=["POST"])
def buy_deal(deal_id):
    body = request.get_json(force=True, silent=True) or {}
    try:
        price = float(body.get("buy_price"))
    except (TypeError, ValueError):
        return jsonify({"error": "buy_price inválido"}), 400
    profit = db.mark_bought(deal_id, price)
    if profit is None:
        return jsonify({"error": "deal no encontrado"}), 404
    return jsonify({"ok": True, "profit": profit})


@app.route("/deals/<int:deal_id>/discard", methods=["POST"])
def discard_deal(deal_id):
    db.mark_status(deal_id, "descartado")
    return jsonify({"ok": True})


@app.route("/deals/<int:deal_id>/verify", methods=["POST"])
def verify_deal(deal_id):
    body = request.get_json(force=True, silent=True) or {}
    currency_status = body.get("currency_status")
    if currency_status not in ("eur", "no_eur"):
        return jsonify({"error": "currency_status debe ser 'eur' o 'no_eur'"}), 400
    db.set_currency_status(deal_id, currency_status)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
