from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

W_RATING = 0.40
W_VIEWED = 0.20
W_CLICKED = 0.25
W_PURCHASED = 0.15


def load_raw():
    users = pd.read_csv(DATA_DIR / "users.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    ratings = pd.read_csv(DATA_DIR / "ratings.csv")
    behavior = pd.read_csv(DATA_DIR / "behavior_15500.csv")
    return users, products, ratings, behavior


def clean(users, products, ratings, behavior):
    users = users.drop_duplicates(subset=["user_id"]).reset_index(drop=True)
    products = products.drop_duplicates(subset=["product_id"]).reset_index(drop=True)

    ratings = ratings.dropna(subset=["user_id", "product_id", "rating"])
    ratings = ratings.drop_duplicates(subset=["user_id", "product_id"], keep="last")
    ratings["rating"] = ratings["rating"].clip(1, 5).astype(int)

    behavior = behavior.fillna(0)
    behavior = behavior.drop_duplicates(subset=["user_id", "product_id"], keep="last")
    for col in ["viewed", "clicked", "purchased"]:
        behavior[col] = (behavior[col].astype(int) > 0).astype(int)

    return users, products, ratings, behavior


def build_score_matrix(ratings, behavior):
    r = ratings.copy()
    r["rating_norm"] = (r["rating"] - 1) / 4.0

    merged = pd.merge(
        behavior, r[["user_id", "product_id", "rating_norm"]],
        on=["user_id", "product_id"], how="outer",
    ).fillna(0)

    merged["score"] = (
        W_RATING * merged["rating_norm"]
        + W_VIEWED * merged["viewed"]
        + W_CLICKED * merged["clicked"]
        + W_PURCHASED * merged["purchased"]
    )

    score_matrix = {
        (int(row.user_id), int(row.product_id)): float(row.score)
        for row in merged.itertuples(index=False)
    }
    return score_matrix, merged


def load_all():
    users, products, ratings, behavior = clean(*load_raw())
    score_matrix, merged = build_score_matrix(ratings, behavior)

    product_categories = dict(zip(products["product_id"].astype(int),
                                  products["category"].astype(str)))

    purchased = behavior[behavior["purchased"] == 1]
    user_purchased = (
        purchased.groupby("user_id")["product_id"]
        .apply(lambda s: set(int(x) for x in s))
        .to_dict()
    )

    return {
        "users": users,
        "products": products,
        "ratings": ratings,
        "behavior": behavior,
        "score_matrix": score_matrix,
        "product_categories": product_categories,
        "user_purchased": user_purchased,
        "merged": merged,
    }


if __name__ == "__main__":
    data = load_all()
    print(f"users:        {len(data['users'])}")
    print(f"products:     {len(data['products'])}")
    print(f"ratings:      {len(data['ratings'])}")
    print(f"behavior:     {len(data['behavior'])}")
    print(f"score pairs:  {len(data['score_matrix'])}")
    print(f"categories:   {sorted(set(data['product_categories'].values()))}")
    sample = list(data["score_matrix"].items())[:5]
    print("sample scores:")
    for k, v in sample:
        print(f"  {k} -> {v:.3f}")
