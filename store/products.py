from flask import Blueprint, render_template, request, abort, g

from db import get_db, log_event
import recommender


bp = Blueprint("products", __name__, url_prefix="/products")


CATEGORY_SLUGS = {
    "ألعاب": "toys",
    "أجهزة منزلية": "home-appliances",
    "إلكترونيات": "electronics",
    "كتب": "books",
    "ملابس": "clothes",
    "رياضة": "sports",
    "عطور": "perfumes",
}
SLUG_TO_CATEGORY = {v: k for k, v in CATEGORY_SLUGS.items()}


@bp.route("/")
def list_products():
    db = get_db()
    slug = request.args.get("category", "").strip()
    category_ar = SLUG_TO_CATEGORY.get(slug, "")

    if category_ar:
        clause, params = "WHERE p.category = ?", [category_ar]
    else:
        clause, params = "", []

    products = db.execute(
        f"SELECT p.product_id, p.name, p.category, p.price, p.image_url, "
        f"       COALESCE((SELECT ROUND(AVG(rating),2) FROM ratings r WHERE r.product_id = p.product_id), 0) AS avg_rating "
        f"FROM products p {clause} ORDER BY p.product_id",
        params,
    ).fetchall()

    categories = [r["category"] for r in db.execute(
        "SELECT DISTINCT category FROM products ORDER BY category").fetchall()]
    category_pills = [(c, CATEGORY_SLUGS.get(c, c)) for c in categories]

    overall_max_price = int(db.execute(
        "SELECT COALESCE(MAX(price), 2000) FROM products").fetchone()[0])

    cat_recs = None
    if category_ar and request.args.get("recommend") == "1" and g.user:
        try:
            cat_recs = recommender.recommend(
                g.user["user_id"], top_n=6, ga_seed=42, only_category=category_ar)
        except Exception:
            cat_recs = None

    return render_template(
        "products/list.html",
        products=products, category_pills=category_pills,
        slug=slug, category_ar=category_ar, total=len(products),
        overall_max_price=overall_max_price,
        cat_recs=cat_recs,
    )


@bp.route("/<int:product_id>")
def detail(product_id):
    db = get_db()
    p = db.execute(
        "SELECT product_id, name, category, price, image_url, description, stock "
        "FROM products WHERE product_id = ?", (product_id,)).fetchone()
    if p is None:
        abort(404)

    if g.user:
        log_event(g.user["user_id"], product_id, "viewed")
        log_event(g.user["user_id"], product_id, "clicked")

    rating_row = db.execute(
        "SELECT AVG(rating) AS avg, COUNT(*) AS n FROM ratings WHERE product_id = ?",
        (product_id,)).fetchone()
    avg_rating = float(rating_row["avg"]) if rating_row["avg"] is not None else None
    rating_count = rating_row["n"]

    reviews = db.execute(
        "SELECT r.comment, r.created_at, u.full_name AS author "
        "FROM reviews r JOIN users u ON u.user_id = r.user_id "
        "WHERE r.product_id = ? ORDER BY r.created_at DESC LIMIT 50",
        (product_id,)).fetchall()

    user_rating = None
    if g.user:
        row = db.execute(
            "SELECT rating FROM ratings WHERE user_id = ? AND product_id = ?",
            (g.user["user_id"], product_id)).fetchone()
        if row:
            user_rating = row["rating"]

    return render_template(
        "products/detail.html",
        product=p, avg_rating=avg_rating, rating_count=rating_count,
        reviews=reviews, user_rating=user_rating,
    )
