# متجر لاختبار نظام توصية المنتجات بالخوارزميات الجينية
### Test Store for the Product Recommendation System with Genetic Algorithms (Decision Tree + GA Hybrid)

A working e-commerce store whose "Recommended for you" engine combines a **Decision Tree** (predicts each user's preferred category) with a **Genetic Algorithm** (optimizes the recommendation list) — built for BIA601 · SVU · Spring 2025.

---

## Contents

- Online store: register/login, browse products, search & filter, product details, ratings (1–5), reviews, cart, checkout
- Behavior tracking: every view / click / cart-add / purchase is logged so the recommender learns from live activity
- Decision Tree predicts each user's preferred category from their behavior history
- Genetic Algorithm optimizes the recommendation list using composite ratings + behavior + DT bias + diversity
- Standalone GA sandbox in [test_algo/](test_algo/) (Excel-backed, used during R&D)

## Tech Stack

- **Backend:** Python + Flask (modular blueprints)
- **DB:** SQLite (8 tables, seeded from the provided Excel datasets)
- **ML:** scikit-learn (Decision Tree) + custom Genetic Algorithm (NumPy)
- **Frontend:** Server-rendered Jinja2 templates + plain CSS
- **Hosting:** Render

## File Structure

```
store/                    — online store + DT+GA recommender (SQLite)
  app.py                  — Flask entry / app factory
  db.py                   — SQLite schema + connection + log_event helper
  auth.py                 — register / login / logout (werkzeug hashing)
  products.py             — list, search, filter, detail (logs `clicked`)
  reviews.py              — ratings (1–5, upsert) + comments
  cart.py                 — add / update / remove / checkout (logs `added_to_cart`, `purchased`)
  recommender.py          — SQLite snapshot + composite score + Decision Tree
  ga.py                   — pure-Python Genetic Algorithm (OX, swap, tournament, elitism)
  templates/              — Jinja2 (base, auth/, products/, cart/, home)
  static/style.css
  requirements.txt
seed/
  excel_to_sqlite.py      — one-shot import from data/*.xlsx → store.db
test_algo/                — standalone GA prototype (Excel-backed sandbox)
data/                     — source Excel datasets (users, products, ratings, behavior)
OnlineStore/              — original C# store (reference; gitignored)
plan.md, tasks.md, report.md
```

## Usage

```bash
cd store
pip install -r requirements.txt
python ../seed/excel_to_sqlite.py    # one-time: import Excel data → store.db
python app.py
```

Then open `http://localhost:5000` in a browser. Seeded accounts are `user1` … `user1000` and the password equals the username (`user1` / `user1`, `user42` / `user42`, etc.).

To run the standalone GA sandbox instead, see [test_algo/README.md](test_algo/README.md).

## Live Demo

- **Hosted store:** https://bia601-recommender.onrender.com
- **GA-only sandbox:** same site, `/sandbox` route (also reachable from the topbar link "النموذج التجريبي")
- **3-minute demo video:** _[paste link after recording]_

> Hosted on Render free tier — first request after idle may take ~30s to wake up.

## Scientific Reference

Customer behavioural content recommendation system using decision tree and genetic algorithm for online shopping websites (2024).
DOI: 10.31893/multiscience.2025003 · https://malque.pub/ojs/index.php/msj/article/view/3865

## Developer

Mohammad Diab

## Contributors

- Sami Alkhouja
- [Add remaining team members]

## License

See [LICENSE](LICENSE) file.

> This is a personal academic project. If you're a student, use it to learn from — not to submit.
