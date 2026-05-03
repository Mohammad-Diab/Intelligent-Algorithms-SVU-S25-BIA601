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

    _CAT_SLUG = {
        "ألعاب": "toys", "أجهزة منزلية": "home-appliances",
        "إلكترونيات": "electronics", "كتب": "books",
        "ملابس": "clothes", "رياضة": "sports", "عطور": "perfumes",
    }

    @app.template_filter("product_fallback")
    def product_fallback(p):
        cat = p["category"] if hasattr(p, "keys") and "category" in p.keys() else None
        pid = p["product_id"] if hasattr(p, "keys") and "product_id" in p.keys() else 0
        slug = _CAT_SLUG.get(cat, "toys")
        return f"/static/img/products/{slug}/{pid % 5}.svg"

    @app.context_processor
    def inject_cart_count():
        if g.get("user"):
            row = db.get_db().execute(
                "SELECT COALESCE(SUM(qty), 0) FROM cart_items WHERE user_id = ?",
                (g.user["user_id"],),
            ).fetchone()
            return {"cart_count": int(row[0] or 0)}
        return {"cart_count": 0}

    @app.route("/dashboard")
    @auth.login_required
    def dashboard():
        d = db.get_db()
        stats = {
            "revenue": d.execute(
                "SELECT COALESCE(SUM(p.price), 0) FROM products p "
                "JOIN behavior b ON b.product_id=p.product_id WHERE b.event='purchased'"
            ).fetchone()[0],
            "active_users": d.execute(
                "SELECT COUNT(DISTINCT user_id) FROM behavior"
            ).fetchone()[0],
            "top_category": (d.execute(
                "SELECT p.category FROM products p "
                "JOIN behavior b ON b.product_id=p.product_id AND b.event='purchased' "
                "GROUP BY p.category ORDER BY COUNT(*) DESC LIMIT 1"
            ).fetchone() or [None])[0] or "—",
            "clicks": d.execute("SELECT COUNT(*) FROM behavior WHERE event='clicked'").fetchone()[0],
            "purchases": d.execute("SELECT COUNT(*) FROM behavior WHERE event='purchased'").fetchone()[0],
        }
        stats["conversion"] = round(stats["purchases"] / stats["clicks"] * 100, 2) if stats["clicks"] else 0
        # Run GA briefly to get a fitness history for the chart
        try:
            r = recommender.recommend(g.user["user_id"], top_n=10, ga_seed=42)
        except Exception:
            r = None
        return render_template("dashboard.html", stats=stats, recs=r,
                               ga_pop=60, ga_gens=40, ga_mutation=0.05)

    @app.route("/analytics")
    @auth.login_required
    def analytics():
        d = db.get_db()
        views = d.execute("SELECT COUNT(*) FROM behavior WHERE event='viewed'").fetchone()[0]
        clicks = d.execute("SELECT COUNT(*) FROM behavior WHERE event='clicked'").fetchone()[0]
        purchases = d.execute("SELECT COUNT(*) FROM behavior WHERE event='purchased'").fetchone()[0]
        ctr = round(clicks / views * 100, 2) if views else 0
        conv = round(purchases / clicks * 100, 2) if clicks else 0
        # Real avg order value if any orders exist
        aov_row = d.execute("SELECT AVG(total) FROM orders").fetchone()
        aov = float(aov_row[0]) if aov_row[0] else 0.0
        # Real category distribution (purchased counts)
        cat_rows = d.execute(
            "SELECT p.category, COUNT(*) AS n FROM products p "
            "JOIN behavior b ON b.product_id=p.product_id AND b.event='purchased' "
            "GROUP BY p.category ORDER BY n DESC"
        ).fetchall()
        return render_template("analytics.html",
                               views=views, clicks=clicks, purchases=purchases,
                               ctr=ctr, conv=conv, aov=aov,
                               categories=[(r["category"], r["n"]) for r in cat_rows])

    @app.route("/profile")
    @auth.login_required
    def profile():
        from collections import defaultdict
        recs = recommender.recommend(g.user["user_id"], top_n=6, ga_seed=42)
        # Real interest analysis: weighted per-category from user's ratings + behavior
        rows = db.get_db().execute(
            "SELECT p.category, "
            "       COALESCE(SUM(CASE WHEN b.event='clicked'   THEN 1 ELSE 0 END), 0) AS clicks, "
            "       COALESCE(SUM(CASE WHEN b.event='purchased' THEN 1 ELSE 0 END), 0) AS purchases, "
            "       COALESCE((SELECT SUM(rating) FROM ratings r "
            "                 JOIN products p2 ON p2.product_id=r.product_id "
            "                 WHERE r.user_id=? AND p2.category=p.category), 0) AS rating_sum "
            "FROM products p "
            "LEFT JOIN behavior b ON b.product_id=p.product_id AND b.user_id=? "
            "GROUP BY p.category",
            (g.user["user_id"], g.user["user_id"]),
        ).fetchall()
        scores = {r["category"]: float(r["rating_sum"] or 0) * 1.0
                  + float(r["clicks"] or 0) * 0.5
                  + float(r["purchases"] or 0) * 2.0
                  for r in rows}
        total = sum(scores.values()) or 1
        interests = sorted(
            ((cat, round(score / total * 100, 1)) for cat, score in scores.items()),
            key=lambda x: x[1], reverse=True
        )
        # Match score: scale fitness — chromosome length 6 with possible bonuses ≈ 1-2 per item
        match_score = min(99, max(20, round(recs["fitness"] / 6 * 50)))
        return render_template(
            "profile.html",
            recs=recs, interests=interests, match_score=match_score,
            ga_pop=60, ga_gens=40, ga_mutation=0.05,
        )

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
