from flask import Flask, render_template, g

import os
import sqlite3
import sys

import db
import auth
import products
import reviews
import cart
import recommender
import playground


def _ensure_seeded(app):
    db.init_db()
    conn = sqlite3.connect(db.DB_PATH)
    try:
        n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()
    if n > 0:
        return
    seed_dir = os.path.join(os.path.dirname(__file__), "..", "seed")
    sys.path.insert(0, seed_dir)
    import excel_to_sqlite
    excel_to_sqlite.main()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me")
    db.init_app(app)
    _ensure_seeded(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(products.bp)
    app.register_blueprint(reviews.bp)
    app.register_blueprint(cart.bp)
    app.register_blueprint(playground.bp)
    app.before_request(auth.load_logged_in_user)
    app.before_request(auth.require_login_globally)

    @app.route("/")
    def home():
        recs = None
        trending = []
        if g.user:
            try:
                recs = recommender.recommend(g.user["user_id"], top_n=10, ga_seed=42)
            except Exception:
                recs = None
            trending = db.get_db().execute(
                "SELECT p.product_id, p.name, p.category, p.price, p.image_url, "
                "       COUNT(b.id) AS purchases "
                "FROM products p "
                "JOIN behavior b ON b.product_id = p.product_id AND b.event = 'purchased' "
                "GROUP BY p.product_id "
                "ORDER BY purchases DESC, p.product_id "
                "LIMIT 4"
            ).fetchall()
        return render_template("home.html", recs=recs, trending=trending)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
