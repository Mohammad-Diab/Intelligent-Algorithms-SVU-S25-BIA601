from flask import Blueprint, render_template, request

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
