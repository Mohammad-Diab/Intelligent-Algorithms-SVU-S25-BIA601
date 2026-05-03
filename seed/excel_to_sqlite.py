import os
import sys
import sqlite3
import random
from urllib.parse import quote
import pandas as pd
from werkzeug.security import generate_password_hash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "store"))

import db as store_db

DATA_DIR = os.path.join(ROOT, "data")
DEFAULT_STOCK = 50
PW_METHOD = "pbkdf2:sha256:1000"


# Per-category Arabic name + English keyword used for the image search.
# (name_ar, image_keyword)
CATEGORY_AR = {
    "Toys": "ألعاب",
    "Home Appliances": "أجهزة منزلية",
    "Electronics": "إلكترونيات",
    "Books": "كتب",
    "Clothes": "ملابس",
    "Sports": "رياضة",
    "Perfumes": "عطور",
}

CATEGORY_SLUG = {
    "Toys": "toys",
    "Home Appliances": "home-appliances",
    "Electronics": "electronics",
    "Books": "books",
    "Clothes": "clothes",
    "Sports": "sports",
    "Perfumes": "perfumes",
}

REVIEW_TEMPLATES = {
    5: [
        "منتج ممتاز جداً، أنصح به بشدة!",
        "جودة رائعة، وصل في الوقت المحدد.",
        "تجاوز توقعاتي، يستحق كل قرش.",
        "من أفضل المنتجات التي اشتريتها.",
        "خدمة وسرعة وجودة عالية.",
        "قيمة استثنائية مقابل السعر.",
    ],
    4: [
        "جيد جداً وقيمة مقابل المال.",
        "راضٍ عن الشراء، ينقصه القليل.",
        "جودة جيدة، التغليف ممكن أن يكون أفضل.",
        "أنصح به للمبتدئين.",
        "تجربة إيجابية بشكل عام.",
    ],
    3: [
        "متوسط، يفي بالغرض.",
        "ليس سيئاً ولكن ليس مميزاً.",
        "السعر مناسب للجودة.",
        "بحاجة لتحسينات بسيطة.",
    ],
    2: [
        "لم يعجبني كثيراً، توقعت أفضل.",
        "الجودة دون المتوقع.",
        "لن أعيد شراءه.",
    ],
    1: [
        "غير راضٍ نهائياً.",
        "مضيعة للمال، لا أنصح به.",
        "وصل بحالة سيئة.",
    ],
    "purchased_only": [
        "وصل بسرعة وبحالة جيدة.",
        "تم الشراء، التغليف محترم.",
        "أحتاج وقتاً أطول لتقييمه.",
    ],
}


def _user_full_name(uid):
    return f"مستخدم {uid}"


def _product_info(category_en, pid):
    """Build the product display name. Prefers data/product_images.csv;
    falls back to '<Arabic category> #<id>' if a row is missing."""
    csv_name = (_load_product_overrides().get(pid, {}).get("name_ar") or "").strip()
    if csv_name:
        return f"#{pid} {csv_name}"
    return f"#{pid} {CATEGORY_AR.get(category_en, category_en)}"


_PRODUCT_OVERRIDES = None


def _load_product_overrides():
    """Load per-product overrides from data/product_images.csv:
       { pid: {"name_ar": ..., "image_url": ...} }
    URLs in the CSV are expected to be the final resolved CDN URLs.
    Run seed/resolve_image_urls.py after replacing the CSV to re-resolve."""
    global _PRODUCT_OVERRIDES
    if _PRODUCT_OVERRIDES is not None:
        return _PRODUCT_OVERRIDES

    out = {}
    csv_path = os.path.join(DATA_DIR, "product_images.csv")
    if os.path.exists(csv_path):
        import csv
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    pid = int(row["id"])
                except (KeyError, ValueError):
                    continue
                name_ar = (row.get("name") or "").strip()
                url = (row.get("image_url") or "").strip().replace("/800/600/", "/400/300/")
                out[pid] = {"name_ar": name_ar, "image_url": url}

    _PRODUCT_OVERRIDES = out
    return out


def _image_url(category_en, pid):
    """Return the product image URL. Prefers data/product_images.csv;
    falls back to local category SVG (5 per category, picked by pid % 5)."""
    url = _load_product_overrides().get(pid, {}).get("image_url")
    if url:
        return url
    slug = CATEGORY_SLUG.get(category_en, "toys")
    return f"/static/img/products/{slug}/{pid % 5}.svg"


def _wipe(conn):
    for t in ["order_items", "orders", "cart_items", "reviews",
              "behavior", "ratings", "products", "users"]:
        conn.execute(f"DELETE FROM {t}")
        conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{t}'")


def seed_users(conn):
    df = pd.read_excel(os.path.join(DATA_DIR, "users.xlsx"))
    rows = []
    for r in df.itertuples():
        uid = int(r.user_id)
        username = f"user{uid}"
        rows.append((
            uid,
            username,
            generate_password_hash(username, method=PW_METHOD),
            _user_full_name(uid),
            int(r.age),
            str(r.country),
        ))
    conn.executemany(
        "INSERT INTO users(user_id, username, password_hash, full_name, age, location) "
        "VALUES (?,?,?,?,?,?)", rows)
    return len(rows)


def seed_products(conn):
    df = pd.read_excel(os.path.join(DATA_DIR, "products.xlsx"))
    rows = []
    for r in df.itertuples():
        pid = int(r.product_id)
        cat_en = str(r.category)
        cat_ar = CATEGORY_AR.get(cat_en, cat_en)
        name_ar = _product_info(cat_en, pid)
        rows.append((
            pid,
            name_ar,
            cat_ar,
            float(r.price),
            _image_url(cat_en, pid),
            f"{name_ar} — منتج {cat_ar} عالي الجودة.",
            DEFAULT_STOCK,
        ))
    conn.executemany(
        "INSERT INTO products(product_id, name, category, price, image_url, description, stock) "
        "VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


def seed_ratings(conn):
    df = pd.read_excel(os.path.join(DATA_DIR, "ratings.xlsx"))
    df = df.drop_duplicates(subset=["user_id", "product_id"], keep="last")
    rows = [(int(r.user_id), int(r.product_id), int(r.rating))
            for r in df.itertuples()]
    conn.executemany(
        "INSERT INTO ratings(user_id, product_id, rating) VALUES (?,?,?)", rows)
    return len(rows)


def seed_behavior(conn):
    df = pd.read_excel(os.path.join(DATA_DIR, "behavior_15500.xlsx"))
    rows = []
    for r in df.itertuples():
        uid, pid = int(r.user_id), int(r.product_id)
        if int(r.viewed):    rows.append((uid, pid, "viewed"))
        if int(r.clicked):   rows.append((uid, pid, "clicked"))
        if int(r.purchased): rows.append((uid, pid, "purchased"))
    conn.executemany(
        "INSERT INTO behavior(user_id, product_id, event) VALUES (?,?,?)", rows)
    return len(rows)


def seed_reviews(conn):
    rng = random.Random(42)
    rated = conn.execute(
        "SELECT user_id, product_id, rating FROM ratings ORDER BY user_id, product_id"
    ).fetchall()
    purchased = conn.execute(
        "SELECT DISTINCT b.user_id, b.product_id FROM behavior b "
        "WHERE b.event='purchased' "
        "AND NOT EXISTS (SELECT 1 FROM ratings r "
        "                WHERE r.user_id=b.user_id AND r.product_id=b.product_id) "
        "LIMIT 1500"
    ).fetchall()

    rows = []
    for uid, pid, rating in rated:
        if rng.random() < 0.55:
            tpl = REVIEW_TEMPLATES.get(int(rating), REVIEW_TEMPLATES["purchased_only"])
            rows.append((uid, pid, rng.choice(tpl)))
    for uid, pid in purchased:
        if rng.random() < 0.30:
            rows.append((uid, pid, rng.choice(REVIEW_TEMPLATES["purchased_only"])))

    conn.executemany(
        "INSERT INTO reviews(user_id, product_id, comment) VALUES (?,?,?)", rows)
    return len(rows)


def main():
    store_db.init_db()
    conn = sqlite3.connect(store_db.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _wipe(conn)
        nu = seed_users(conn)
        np_ = seed_products(conn)
        nr = seed_ratings(conn)
        nb = seed_behavior(conn)
        nrev = seed_reviews(conn)
        conn.commit()
    finally:
        conn.close()
    print(f"Seeded: users={nu} products={np_} ratings={nr} "
          f"behavior_events={nb} reviews={nrev}")
    print("Login: username == password (e.g. user1 / user1, user42 / user42)")


if __name__ == "__main__":
    main()
