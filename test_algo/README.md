# test_algo — GA Recommender Sandbox

Standalone genetic-algorithm recommender that reads directly from `../data/*.xlsx`. Kept as an isolated reference / experimentation harness while the production app moves into `store/` with SQLite + Decision Tree + GA.

## Run

```bash
cd test_algo
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000.

## Files
- `app.py` — Flask API + UI
- `data_loader.py` — Excel loader + composite score
- `genetic_algorithm.py` — GA engine (chromosome, fitness, OX crossover, swap mutation, tournament + elitism)
- `static/` — single-page UI

The full project (store + DT + GA hybrid) lives in [../store/](../store/).
