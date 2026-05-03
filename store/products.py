from flask import Blueprint, render_template, request, abort

from db import get_db


bp = Blueprint("products", __name__, url_prefix="/products")

PAGE_SIZE = 24


@bp.route("/")
def list_products():
    db = get_db()
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    page = max(1, int(request.args.get("page", "1") or 1))

    where, params = [], []
    if q:
        where.append("(name LIKE ? OR description LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if category:
        where.append("category = ?")
        params.append(category)
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.execute(f"SELECT COUNT(*) FROM products {clause}", params).fetchone()[0]
    offset = (page - 1) * PAGE_SIZE
    products = db.execute(
        f"SELECT id, name, category, price, image_url FROM products "
        f"{clause} ORDER BY id LIMIT ? OFFSET ?",
        params + [PAGE_SIZE, offset],
    ).fetchall()
    categories = [r["category"] for r in db.execute(
        "SELECT DISTINCT category FROM products ORDER BY category").fetchall()]

    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return render_template(
        "products/list.html",
        products=products, categories=categories,
        q=q, category=category, page=page, pages=pages, total=total,
    )


@bp.route("/<int:product_id>")
def detail(product_id):
    db = get_db()
    p = db.execute(
        "SELECT id, name, category, price, image_url, description, stock "
        "FROM products WHERE id = ?", (product_id,)).fetchone()
    if p is None:
        abort(404)

    rating_row = db.execute(
        "SELECT AVG(rating) AS avg, COUNT(*) AS n FROM ratings WHERE product_id = ?",
        (product_id,)).fetchone()
    avg_rating = float(rating_row["avg"]) if rating_row["avg"] is not None else None
    rating_count = rating_row["n"]

    reviews = db.execute(
        "SELECT r.comment, r.created_at, u.username "
        "FROM reviews r JOIN users u ON u.id = r.user_id "
        "WHERE r.product_id = ? ORDER BY r.created_at DESC LIMIT 50",
        (product_id,)).fetchall()

    user_rating = None
    from flask import g
    if g.user:
        row = db.execute(
            "SELECT rating FROM ratings WHERE user_id = ? AND product_id = ?",
            (g.user["id"], product_id)).fetchone()
        if row:
            user_rating = row["rating"]

    return render_template(
        "products/detail.html",
        product=p, avg_rating=avg_rating, rating_count=rating_count,
        reviews=reviews, user_rating=user_rating,
    )
