from flask import Blueprint, request, redirect, url_for, flash, abort, g

from db import get_db
from auth import login_required


bp = Blueprint("reviews", __name__, url_prefix="/reviews")


def _ensure_product(product_id):
    row = get_db().execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        abort(404)


@bp.route("/<int:product_id>/rating", methods=["POST"])
@login_required
def submit_rating(product_id):
    _ensure_product(product_id)
    try:
        rating = int(request.form.get("rating", ""))
    except ValueError:
        rating = 0
    if rating < 1 or rating > 5:
        flash("Rating must be between 1 and 5.", "error")
        return redirect(url_for("products.detail", product_id=product_id))

    db = get_db()
    db.execute(
        "INSERT INTO ratings(user_id, product_id, rating) VALUES (?,?,?) "
        "ON CONFLICT(user_id, product_id) DO UPDATE SET rating = excluded.rating, "
        "created_at = datetime('now')",
        (g.user["id"], product_id, rating))
    db.commit()
    flash("Rating saved.", "success")
    return redirect(url_for("products.detail", product_id=product_id))


@bp.route("/<int:product_id>/comment", methods=["POST"])
@login_required
def submit_review(product_id):
    _ensure_product(product_id)
    comment = (request.form.get("comment") or "").strip()
    if not comment:
        flash("Review cannot be empty.", "error")
        return redirect(url_for("products.detail", product_id=product_id))
    if len(comment) > 1000:
        comment = comment[:1000]

    db = get_db()
    db.execute(
        "INSERT INTO reviews(user_id, product_id, comment) VALUES (?,?,?)",
        (g.user["id"], product_id, comment))
    db.commit()
    flash("Review posted.", "success")
    return redirect(url_for("products.detail", product_id=product_id))
