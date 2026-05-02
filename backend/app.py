from flask import Flask, jsonify, send_from_directory, abort, request
from pathlib import Path

from data_loader import load_all
from genetic_algorithm import run_ga

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")

print("Loading data...")
DATA = load_all()
PRODUCT_POOL = list(DATA["product_categories"].keys())
print(f"Loaded {len(DATA['users'])} users, {len(DATA['products'])} products, "
      f"{len(DATA['score_matrix'])} score pairs.")

CACHE = {}

DEFAULTS = {"pop_size": 80, "generations": 120, "mutation_rate": 0.05}


def get_recommendations(user_id, params, limit=10):
    cache_key = (user_id, params["pop_size"], params["generations"],
                 round(params["mutation_rate"], 4))
    if cache_key in CACHE:
        return CACHE[cache_key]

    result = run_ga(
        user_id=user_id,
        product_pool=PRODUCT_POOL,
        score_matrix=DATA["score_matrix"],
        product_categories=DATA["product_categories"],
        user_purchased=DATA["user_purchased"],
        chromosome_length=limit,
        pop_size=params["pop_size"],
        generations=params["generations"],
        mutation_rate=params["mutation_rate"],
        seed=user_id,
    )

    products = []
    for pid in result["recommendations"]:
        prod_row = DATA["products"][DATA["products"]["product_id"] == pid].iloc[0]
        products.append({
            "product_id": int(pid),
            "category": str(prod_row["category"]),
            "price": float(prod_row["price"]),
            "score": round(DATA["score_matrix"].get((user_id, pid), 0.0), 3),
        })

    payload = {
        "user_id": user_id,
        "fitness": round(result["fitness"], 3),
        "params": params,
        "history": result["history"],
        "recommendations": products,
    }
    CACHE[cache_key] = payload
    return payload


def parse_params():
    def clamp(v, lo, hi):
        return max(lo, min(hi, v))
    try:
        pop = clamp(int(request.args.get("pop_size", DEFAULTS["pop_size"])), 20, 300)
        gens = clamp(int(request.args.get("generations", DEFAULTS["generations"])), 10, 500)
        mut = clamp(float(request.args.get("mutation_rate", DEFAULTS["mutation_rate"])), 0.0, 0.5)
    except (TypeError, ValueError):
        abort(400, description="invalid parameters")
    return {"pop_size": pop, "generations": gens, "mutation_rate": mut}


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "users": len(DATA["users"]),
                    "products": len(DATA["products"]),
                    "cached": len(CACHE)})


@app.route("/api/users")
def list_users():
    df = DATA["users"]
    return jsonify([
        {"user_id": int(r.user_id), "age": int(r.age), "country": str(r.country)}
        for r in df.itertuples(index=False)
    ])


@app.route("/api/products")
def list_products():
    df = DATA["products"]
    return jsonify([
        {"product_id": int(r.product_id),
         "category": str(r.category),
         "price": float(r.price)}
        for r in df.itertuples(index=False)
    ])


@app.route("/api/recommend/<int:user_id>")
def recommend(user_id):
    if user_id not in set(DATA["users"]["user_id"].astype(int)):
        abort(404, description=f"user_id {user_id} not found")
    return jsonify(get_recommendations(user_id, parse_params()))


@app.route("/api/defaults")
def defaults():
    return jsonify(DEFAULTS)


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
