import os
import sys
import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "store"))

import db as store_db

DATA_DIR = os.path.join(ROOT, "data")
DEFAULT_PASSWORD = "password"
DEFAULT_STOCK = 50


def _wipe(conn):
    for t in ["order_items", "orders", "cart_items", "reviews",
              "behavior", "ratings", "products", "users"]:
        conn.execute(f"DELETE FROM {t}")
        conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{t}'")


def seed_users(conn):
    df = pd.read_excel(os.path.join(DATA_DIR, "users.xlsx"))
    pw = generate_password_hash(DEFAULT_PASSWORD)
    rows = [
        (int(r.user_id),
         f"user{int(r.user_id)}",
         f"user{int(r.user_id)}@example.com",
         pw,
         f"User {int(r.user_id)}",
         int(r.age),
         str(r.country))
        for r in df.itertuples()
    ]
    conn.executemany(
        "INSERT INTO users(id, username, email, password_hash, full_name, age, location) "
        "VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


def seed_products(conn):
    df = pd.read_excel(os.path.join(DATA_DIR, "products.xlsx"))
    rows = [
        (int(r.product_id),
         f"{r.category} Item #{int(r.product_id)}",
         str(r.category),
         float(r.price),
         f"https://picsum.photos/seed/p{int(r.product_id)}/400/300",
         f"A quality {str(r.category).lower()} product (#{int(r.product_id)}).",
         DEFAULT_STOCK)
        for r in df.itertuples()
    ]
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
    print(f"Default login password for every user: {DEFAULT_PASSWORD!r}")


if __name__ == "__main__":
    main()
