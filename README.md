# الخوارزميات الذكية — نظام توصية المنتجات
### Intelligent Algorithms — E-Commerce Recommender (Genetic Algorithm)

A web application that improves product recommendations in an e-commerce store using a **Genetic Algorithm** — built for BIA601 · SVU · Spring 2025.

---

## Contents

- Genetic Algorithm engine for personalized product recommendations
- Composite scoring combining explicit ratings and implicit behavior (view / click / purchase)
- Diversity-aware fitness function with category balancing
- Order Crossover (OX) and Swap Mutation operators
- Tournament selection with elitism
- Web UI to select a user and view their recommended products

## Tech Stack

- **Backend:** Python + Flask (single-file API)
- **GA engine:** Custom implementation in pure Python + NumPy
- **Data:** pandas reading Excel files directly (no database)
- **Frontend:** HTML + CSS + JavaScript (no framework, no build step)
- **Hosting:** Render (backend) / static UI served by Flask

## File Structure

```
test_algo/                — standalone GA prototype (Excel-backed)
  app.py
  data_loader.py
  genetic_algorithm.py
  requirements.txt
  static/
store/                    — full online store + DT+GA recommender (SQLite) [in progress]
data/                     — source Excel datasets
  users.xlsx
  products.xlsx
  ratings.xlsx
  behavior_15500.xlsx
OnlineStore/              — original C# store (reference, being ported to Python)
plan.md                   — project plan
tasks.md                  — task checklist
report.md                 — technical report (Arabic)
```

## Usage

```bash
cd test_algo
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000` in a browser.

## Live Demo

https://bia601-recommender.onrender.com

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
