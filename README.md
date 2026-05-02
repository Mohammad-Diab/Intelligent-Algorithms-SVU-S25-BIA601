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
backend/
  app.py                  — Flask API + GA engine entry point
  data_loader.py          — loads Excel files, computes composite scores
  genetic_algorithm.py    — GA: chromosome, fitness, crossover, mutation
  requirements.txt
  static/
    index.html            — single-page UI
    style.css
    app.js
data/
  users.xlsx
  products.xlsx
  ratings.xlsx
  behavior_15500.xlsx
plan.md                   — project plan
report.md                 — technical report (Arabic)
mysol.md                  — final report draft
```

## Usage

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000` in a browser.

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
