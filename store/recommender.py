from collections import defaultdict, Counter

import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder

from db import get_db
import ga


W_RATING = 0.40
W_VIEWED = 0.20
W_CLICKED = 0.25
W_PURCHASED = 0.15


def _load_snapshot():
    db = get_db()
    products = db.execute(
        "SELECT product_id, name, category, price, image_url, stock FROM products"
    ).fetchall()
    product_categories = {p["product_id"]: p["category"] for p in products}
    product_index = {p["product_id"]: dict(p) for p in products}

    rating_rows = db.execute(
        "SELECT user_id, product_id, rating FROM ratings").fetchall()

    behavior_rows = db.execute(
        "SELECT user_id, product_id, event FROM behavior").fetchall()

    return product_index, product_categories, rating_rows, behavior_rows


def _build_score_matrix(rating_rows, behavior_rows):
    rating = {(r["user_id"], r["product_id"]): (r["rating"] - 1) / 4.0
              for r in rating_rows}

    flags = defaultdict(lambda: {"viewed": 0, "clicked": 0, "purchased": 0})
    for b in behavior_rows:
        ev = b["event"]
        if ev in flags[(b["user_id"], b["product_id"])]:
            flags[(b["user_id"], b["product_id"])][ev] = 1

    keys = set(rating.keys()) | set(flags.keys())
    score = {}
    for k in keys:
        f = flags.get(k, {"viewed": 0, "clicked": 0, "purchased": 0})
        score[k] = (W_RATING    * rating.get(k, 0.0)
                    + W_VIEWED    * f["viewed"]
                    + W_CLICKED   * f["clicked"]
                    + W_PURCHASED * f["purchased"])
    return score


def _build_user_purchased(behavior_rows):
    out = defaultdict(set)
    for b in behavior_rows:
        if b["event"] == "purchased":
            out[b["user_id"]].add(b["product_id"])
    return out


def _user_features(user_row, behavior_rows, rating_rows, product_categories,
                   categories, country_encoder):
    n_cats = len(categories)
    cat_idx = {c: i for i, c in enumerate(categories)}
    feats = np.zeros(3 + n_cats * 3 + 1, dtype=float)

    feats[0] = user_row["age"] or 0
    try:
        feats[1] = country_encoder.transform([user_row["location"] or "?"])[0]
    except ValueError:
        feats[1] = -1
    feats[2] = 0  # placeholder

    for r in rating_rows:
        if r["user_id"] != user_row["user_id"]:
            continue
        ci = cat_idx.get(product_categories.get(r["product_id"]))
        if ci is not None:
            feats[3 + ci] += r["rating"]
    for b in behavior_rows:
        if b["user_id"] != user_row["user_id"]:
            continue
        ci = cat_idx.get(product_categories.get(b["product_id"]))
        if ci is None:
            continue
        if b["event"] == "clicked":
            feats[3 + n_cats + ci] += 1
        elif b["event"] == "purchased":
            feats[3 + 2 * n_cats + ci] += 1
    feats[-1] = feats[3 + 2 * n_cats:3 + 3 * n_cats].sum()
    return feats


def _train_decision_tree(product_categories):
    db = get_db()
    users = db.execute(
        "SELECT user_id, age, location FROM users").fetchall()
    rating_rows = db.execute(
        "SELECT user_id, product_id, rating FROM ratings").fetchall()
    behavior_rows = db.execute(
        "SELECT user_id, product_id, event FROM behavior").fetchall()

    categories = sorted(set(product_categories.values()))
    if len(categories) < 2:
        return None, categories, None, None

    countries = sorted({(u["location"] or "?") for u in users})
    le = LabelEncoder().fit(countries)

    by_user_purchased = defaultdict(Counter)
    for b in behavior_rows:
        if b["event"] == "purchased":
            cat = product_categories.get(b["product_id"])
            if cat:
                by_user_purchased[b["user_id"]][cat] += 1

    by_user_rated = defaultdict(Counter)
    for r in rating_rows:
        cat = product_categories.get(r["product_id"])
        if cat:
            by_user_rated[r["user_id"]][cat] += r["rating"]

    X, y = [], []
    for u in users:
        uid = u["user_id"]
        if by_user_purchased[uid]:
            label = by_user_purchased[uid].most_common(1)[0][0]
        elif by_user_rated[uid]:
            label = by_user_rated[uid].most_common(1)[0][0]
        else:
            continue
        X.append(_user_features(u, behavior_rows, rating_rows,
                                product_categories, categories, le))
        y.append(label)

    if len(set(y)) < 2:
        return None, categories, le, None

    clf = DecisionTreeClassifier(max_depth=8, min_samples_leaf=5, random_state=42)
    clf.fit(np.array(X), y)
    return clf, categories, le, (behavior_rows, rating_rows)


def predict_preferred_category(user_id, product_categories,
                               clf, categories, encoder, cached_rows):
    if clf is None:
        cats = list(product_categories.values())
        return Counter(cats).most_common(1)[0][0] if cats else None
    db = get_db()
    user_row = db.execute(
        "SELECT user_id, age, location FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if user_row is None:
        return None
    behavior_rows, rating_rows = cached_rows
    feats = _user_features(user_row, behavior_rows, rating_rows,
                           product_categories, categories, encoder)
    return clf.predict(feats.reshape(1, -1))[0]


def recommend(user_id, top_n=10, ga_seed=None):
    product_index, product_categories, rating_rows, behavior_rows = _load_snapshot()
    score_matrix = _build_score_matrix(rating_rows, behavior_rows)
    user_purchased = _build_user_purchased(behavior_rows)

    clf, categories, encoder, cached = _train_decision_tree(product_categories)
    preferred = predict_preferred_category(
        user_id, product_categories, clf, categories, encoder, cached)

    in_stock = [pid for pid, p in product_index.items() if p["stock"] > 0]
    pool = in_stock if len(in_stock) >= top_n else list(product_index.keys())

    result = ga.run(
        user_id=user_id, product_pool=pool, score_matrix=score_matrix,
        product_categories=product_categories, user_purchased=user_purchased,
        preferred_category=preferred,
        length=top_n, pop_size=60, generations=40, seed=ga_seed,
    )

    out = []
    for rank, pid in enumerate(result["recommendations"], start=1):
        p = product_index.get(pid)
        if not p:
            continue
        out.append({
            "rank": rank,
            "product_id": p["product_id"], "name": p["name"], "category": p["category"],
            "price": p["price"], "image_url": p["image_url"],
            "score": score_matrix.get((user_id, pid), 0.0),
        })
    return {
        "preferred_category": preferred,
        "fitness": result["fitness"],
        "products": out,
    }
