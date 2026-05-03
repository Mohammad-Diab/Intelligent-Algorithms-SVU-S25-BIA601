from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g

from db import get_db, log_event
from auth import login_required


bp = Blueprint("cart", __name__, url_prefix="/cart")


def _cart_rows(user_id):
    return get_db().execute(
        "SELECT p.id, p.name, p.image_url, p.price, p.stock, c.qty, "
        "       (p.price * c.qty) AS line_total "
        "FROM cart_items c JOIN products p ON p.id = c.product_id "
        "WHERE c.user_id = ? ORDER BY p.name",
        (user_id,),
    ).fetchall()


@bp.route("/")
@login_required
def view_cart():
    items = _cart_rows(g.user["id"])
    total = sum(r["line_total"] for r in items)
    return render_template("cart/index.html", items=items, total=total)


@bp.route("/add/<int:product_id>", methods=["POST"])
@login_required
def add(product_id):
    db = get_db()
    p = db.execute("SELECT id, stock FROM products WHERE id = ?", (product_id,)).fetchone()
    if p is None:
        abort(404)
    try:
        qty = max(1, int(request.form.get("qty", "1")))
    except ValueError:
        qty = 1

    existing = db.execute(
        "SELECT qty FROM cart_items WHERE user_id = ? AND product_id = ?",
        (g.user["id"], product_id)).fetchone()
    new_qty = (existing["qty"] if existing else 0) + qty

    if new_qty > p["stock"]:
        new_qty = p["stock"]
        flash(f"المتوفر في المخزون فقط {p['stock']} — تم تعديل الكمية.", "error")

    if new_qty <= 0:
        flash("نفد المخزون.", "error")
        return redirect(request.referrer or url_for("products.detail", product_id=product_id))

    db.execute(
        "INSERT INTO cart_items(user_id, product_id, qty) VALUES (?,?,?) "
        "ON CONFLICT(user_id, product_id) DO UPDATE SET qty = excluded.qty",
        (g.user["id"], product_id, new_qty))
    db.commit()
    log_event(g.user["id"], product_id, "added_to_cart")
    flash("تمت الإضافة إلى العربة.", "success")
    return redirect(request.referrer or url_for("cart.view_cart"))


@bp.route("/update/<int:product_id>", methods=["POST"])
@login_required
def update(product_id):
    try:
        qty = int(request.form.get("qty", "0"))
    except ValueError:
        qty = 0
    db = get_db()
    if qty <= 0:
        db.execute("DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
                   (g.user["id"], product_id))
    else:
        stock = db.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()
        if stock is None:
            abort(404)
        if qty > stock["stock"]:
            qty = stock["stock"]
            flash(f"تم تعديل الكمية إلى الحد المتوفر ({stock['stock']}).", "error")
        db.execute(
            "INSERT INTO cart_items(user_id, product_id, qty) VALUES (?,?,?) "
            "ON CONFLICT(user_id, product_id) DO UPDATE SET qty = excluded.qty",
            (g.user["id"], product_id, qty))
    db.commit()
    return redirect(url_for("cart.view_cart"))


@bp.route("/remove/<int:product_id>", methods=["POST"])
@login_required
def remove(product_id):
    db = get_db()
    db.execute("DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
               (g.user["id"], product_id))
    db.commit()
    flash("تم حذف العنصر.", "success")
    return redirect(url_for("cart.view_cart"))


@bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    db = get_db()
    items = _cart_rows(g.user["id"])
    if not items:
        flash("عربتك فارغة.", "error")
        return redirect(url_for("cart.view_cart"))

    for r in items:
        if r["qty"] > r["stock"]:
            flash(f"'{r['name']}' المتوفر منه فقط {r['stock']} في المخزون.", "error")
            return redirect(url_for("cart.view_cart"))

    total = sum(r["line_total"] for r in items)
    cur = db.execute(
        "INSERT INTO orders(user_id, total) VALUES (?,?)", (g.user["id"], total))
    order_id = cur.lastrowid

    for r in items:
        db.execute(
            "INSERT INTO order_items(order_id, product_id, qty, price) VALUES (?,?,?,?)",
            (order_id, r["id"], r["qty"], r["price"]))
        db.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (r["qty"], r["id"]))
        for _ in range(r["qty"]):
            db.execute(
                "INSERT INTO behavior(user_id, product_id, event) VALUES (?,?,'purchased')",
                (g.user["id"], r["id"]))

    db.execute("DELETE FROM cart_items WHERE user_id = ?", (g.user["id"],))
    db.commit()

    return redirect(url_for("cart.order_confirmation", order_id=order_id))


@bp.route("/order/<int:order_id>")
@login_required
def order_confirmation(order_id):
    db = get_db()
    order = db.execute(
        "SELECT id, total, created_at FROM orders WHERE id = ? AND user_id = ?",
        (order_id, g.user["id"])).fetchone()
    if order is None:
        abort(404)
    items = db.execute(
        "SELECT p.name, oi.qty, oi.price, (oi.qty * oi.price) AS line_total "
        "FROM order_items oi JOIN products p ON p.id = oi.product_id "
        "WHERE oi.order_id = ?", (order_id,)).fetchall()
    return render_template("cart/order.html", order=order, items=items)
