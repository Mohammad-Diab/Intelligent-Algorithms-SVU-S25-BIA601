import os
import sys
import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "store"))

import db as store_db

DATA_DIR = os.path.join(ROOT, "data")
DEFAULT_STOCK = 50
PW_METHOD = "pbkdf2:sha256:1000"


FIRST_NAMES = [
    "Ahmed", "Mohammed", "Ali", "Omar", "Khalid", "Hassan", "Hussein",
    "Mahmoud", "Youssef", "Ibrahim", "Bashar", "Rami", "Tariq", "Karim",
    "Samir", "Nabil", "Ziad", "Adel", "Fadi", "Marwan",
    "Fatima", "Layla", "Zainab", "Mariam", "Aisha", "Khadija", "Sara",
    "Nour", "Hala", "Rana", "Lina", "Dalia", "Reem", "Salma", "Maya",
    "Yara", "Hiba", "Amina", "Lubna", "Ghada",
]

LAST_NAMES = [
    "Al-Hassan", "Al-Khouri", "Al-Mansour", "Al-Saleh", "Haddad", "Najjar",
    "Sayegh", "Rahman", "Diab", "Khalil", "Younes", "Awad", "Saadi",
    "Tabbara", "Faraj", "Maalouf", "Shami", "Hariri", "Sabbagh",
    "Hamdan", "Zein", "Bakri", "Daher", "Sulaiman", "Tannous", "Karam",
]


PRODUCT_NAMES = {
    "Toys": [
        "Wooden Train Set", "RC Race Car", "Plush Teddy Bear", "Rubik's Cube Pro",
        "Building Blocks Kit", "Action Figure", "Board Game Classic", "Mini Drone",
        "Puzzle 1000pc", "Doll House", "Toy Robot", "Magic Kit",
    ],
    "Home Appliances": [
        "Coffee Maker Deluxe", "Vacuum Cleaner X1", "Air Fryer Pro", "Blender Plus",
        "4-Slice Toaster", "Microwave 25L", "Steam Iron", "Electric Kettle",
        "Rice Cooker", "Stand Mixer", "Slow Cooker", "Dishwasher Compact",
    ],
    "Electronics": [
        "Bluetooth Speaker", "Wireless Earbuds", "Smart Watch", "USB-C Hub",
        "Power Bank 20000mAh", "4K Webcam", "Mechanical Keyboard", "Gaming Mouse",
        "27-inch Monitor", "External SSD 1TB", "WiFi Router", "Smart Plug",
    ],
    "Books": [
        "Mystery Novel", "Cookbook Volume 1", "History of the Levant",
        "Self-Help Guide", "Sci-Fi Anthology", "Programming Manual",
        "Poetry Collection", "Hardcover Biography", "Travel Guide",
        "Children's Storybook", "Photography Album", "Philosophy Reader",
    ],
    "Clothes": [
        "Cotton T-Shirt", "Slim-Fit Jeans", "Wool Sweater", "Linen Shirt",
        "Hooded Sweatshirt", "Summer Dress", "Leather Jacket", "Polo Shirt",
        "Cargo Shorts", "Pleated Skirt", "Trench Coat", "Knit Cardigan",
    ],
    "Sports": [
        "Yoga Mat Pro", "Adjustable Dumbbells", "Football Premium", "Tennis Racket",
        "Cycling Helmet", "Running Shoes", "Resistance Band Set", "Jump Rope Speed",
        "Boxing Gloves", "Swim Goggles", "Hiking Backpack", "Foam Roller",
    ],
    "Perfumes": [
        "Oud Royal", "Rose Garden EDP", "Sandalwood Mist", "Jasmine Bloom",
        "Amber Nights", "Citrus Breeze", "Vanilla Musk", "Ocean Spray Cologne",
        "Patchouli Classic", "Cedar Wood Eau", "Lavender Fields", "Saffron Velvet",
    ],
}


def _user_full_name(uid):
    first = FIRST_NAMES[(uid - 1) % len(FIRST_NAMES)]
    last  = LAST_NAMES[((uid - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]
    return f"{first} {last} #{uid}"


def _product_name(category, pid):
    pool = PRODUCT_NAMES.get(category, [f"{category} Premium"])
    base = pool[(pid - 1) % len(pool)]
    return f"{base} #{pid}"


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
            f"{username}@example.com",
            generate_password_hash(username, method=PW_METHOD),
            _user_full_name(uid),
            int(r.age),
            str(r.country),
        ))
    conn.executemany(
        "INSERT INTO users(id, username, email, password_hash, full_name, age, location) "
        "VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


def seed_products(conn):
    df = pd.read_excel(os.path.join(DATA_DIR, "products.xlsx"))
    rows = []
    for r in df.itertuples():
        pid = int(r.product_id)
        cat = str(r.category)
        name = _product_name(cat, pid)
        rows.append((
            pid,
            name,
            cat,
            float(r.price),
            f"https://picsum.photos/seed/p{pid}/400/300",
            f"{name} — a quality {cat.lower()} product.",
            DEFAULT_STOCK,
        ))
    conn.executemany(
        "INSERT INTO products(id, name, category, price, image_url, description, stock) "
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
        conn.commit()
    finally:
        conn.close()
    print(f"Seeded: users={nu} products={np_} ratings={nr} behavior_events={nb}")
    print("Login: username == password (e.g. user1 / user1, user42 / user42)")


if __name__ == "__main__":
    main()
