from collections import defaultdict
from flask import Blueprint, render_template, jsonify, abort, request

from db import get_db
from auth import login_required
import ga


bp = Blueprint("playground", __name__, url_prefix="/playground")

DEFAULTS = {"pop_size": 80, "generations": 120, "mutation_rate": 0.05}

W_RATING, W_VIEWED, W_CLICKED, W_PURCHASED = 0.40, 0.20, 0.25, 0.15


def _build_data():
    db = get_db()
    users = db.execute(
        "SELECT user_id, age, location FROM users ORDER BY user_id").fetchall()
    products = db.execute(
        "SELECT product_id, name, category, price FROM products ORDER BY product_id").fetchall()
    rating_rows = db.execute(
        "SELECT user_id, product_id, rating FROM ratings").fetchall()
    behavior_rows = db.execute(
        "SELECT user_id, product_id, event FROM behavior").fetchall()

    product_categories = {p["product_id"]: p["category"] for p in products}

    rating = {(r["user_id"], r["product_id"]): (r["rating"] - 1) / 4.0
              for r in rating_rows}

    flags = defaultdict(lambda: {"viewed": 0, "clicked": 0, "purchased": 0})
    for b in behavior_rows:
        ev = b["event"]
        if ev in flags[(b["user_id"], b["product_id"])]:
            flags[(b["user_id"], b["product_id"])][ev] = 1

    keys = set(rating.keys()) | set(flags.keys())
    score_matrix = {}
    for k in keys:
        f = flags.get(k, {"viewed": 0, "clicked": 0, "purchased": 0})
        score_matrix[k] = (W_RATING    * rating.get(k, 0.0)
                           + W_VIEWED    * f["viewed"]
                           + W_CLICKED   * f["clicked"]
                           + W_PURCHASED * f["purchased"])

    user_purchased = defaultdict(set)
    for b in behavior_rows:
        if b["event"] == "purchased":
            user_purchased[b["user_id"]].add(b["product_id"])

    return {
        "users": users,
        "products": products,
        "product_categories": product_categories,
        "score_matrix": score_matrix,
        "user_purchased": user_purchased,
    }


def _parse_params():
    def check(name, v, lo, hi):
        if v < lo or v > hi:
            abort(400, description=f"{name}={v} out of range [{lo}, {hi}]")
        return v
    try:
        pop = check("pop_size", int(request.args.get("pop_size", DEFAULTS["pop_size"])), 20, 300)
        gens = check("generations", int(request.args.get("generations", DEFAULTS["generations"])), 10, 500)
        mut = check("mutation_rate", float(request.args.get("mutation_rate", DEFAULTS["mutation_rate"])), 0.0, 0.5)
    except (TypeError, ValueError):
        abort(400, description="invalid parameters")
    return {"pop_size": pop, "generations": gens, "mutation_rate": mut}


@bp.route("/")
@login_required
def index():
    return render_template("playground/index.html")


@bp.route("/api/users")
@login_required
def list_users():
    rows = get_db().execute(
        "SELECT user_id, age, location FROM users ORDER BY user_id").fetchall()
    return jsonify([
        {"user_id": r["user_id"], "age": r["age"] or 0,
         "country": r["location"] or ""}
        for r in rows
    ])


@bp.route("/api/defaults")
@login_required
def defaults():
    return jsonify(DEFAULTS)


@bp.route("/api/recommend/<int:user_id>")
@login_required
def recommend(user_id):
    data = _build_data()
    if not any(u["user_id"] == user_id for u in data["users"]):
        abort(404, description=f"user_id {user_id} not found")
    params = _parse_params()
    pool = list(data["product_categories"].keys())

    result = ga.run(
        user_id=user_id,
        product_pool=pool,
        score_matrix=data["score_matrix"],
        product_categories=data["product_categories"],
        user_purchased=data["user_purchased"],
        preferred_category=None,
        length=10,
        pop_size=params["pop_size"],
        generations=params["generations"],
        mutation_rate=params["mutation_rate"],
        seed=user_id,
    )

    products_idx = {p["product_id"]: p for p in data["products"]}
    recs = []
    for pid in result["recommendations"]:
        p = products_idx.get(pid)
        if not p:
            continue
        recs.append({
            "product_id": p["product_id"],
            "name": p["name"],
            "category": p["category"],
            "price": float(p["price"]),
            "score": round(data["score_matrix"].get((user_id, pid), 0.0), 3),
        })

    return jsonify({
        "user_id": user_id,
        "fitness": round(result["fitness"], 3),
        "params": params,
        "history": result["history"],
        "recommendations": recs,
    })
