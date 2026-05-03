"""Generate 5 themed SVG images per category and write them to
store/static/img/products/<slug>/<n>.svg. Run once after editing the
CATEGORIES table. The Arabic category labels in store.db map to slugs
via CATEGORY_SLUG."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "store", "static", "img", "products")


CATEGORIES = {
    "books": {
        "label_ar": "كتب",
        "emojis":   ["📚", "📖", "📕", "📗", "📘"],
        "colors":   [("#5b3a29","#a47148"), ("#2e3d59","#5a7ca8"),
                     ("#6b3024","#a25048"), ("#284734","#4d8b6a"),
                     ("#3a3055","#6b5a91")],
    },
    "clothes": {
        "label_ar": "ملابس",
        "emojis":   ["👕", "👗", "👖", "🧥", "👔"],
        "colors":   [("#1f3a5f","#3870a8"), ("#5a1e3f","#a04575"),
                     ("#3d2a55","#7355a8"), ("#1f4a3d","#3e8a72"),
                     ("#5a3a1e","#a87138")],
    },
    "electronics": {
        "label_ar": "إلكترونيات",
        "emojis":   ["🎧", "📱", "💻", "⌚", "🎮"],
        "colors":   [("#0e2a3f","#2570a8"), ("#1a1a3a","#4a4ab8"),
                     ("#0a3030","#1f7878"), ("#1a2030","#3a4f80"),
                     ("#2a0e3f","#7028a8")],
    },
    "home-appliances": {
        "label_ar": "أجهزة منزلية",
        "emojis":   ["☕", "🍳", "🧺", "🍚", "🧊"],
        "colors":   [("#5a2e1e","#a8553a"), ("#5a4019","#c08a3a"),
                     ("#3a4a1e","#7a9838"), ("#5f3520","#b56838"),
                     ("#1e4a5a","#3e8aa8")],
    },
    "perfumes": {
        "label_ar": "عطور",
        "emojis":   ["🌹", "🌸", "💐", "🪷", "🌺"],
        "colors":   [("#5a1e3a","#a8487a"), ("#5a3a4a","#c07ea0"),
                     ("#451e5a","#8e58b0"), ("#5a2a2a","#b86060"),
                     ("#3a1e5a","#7050a8")],
    },
    "sports": {
        "label_ar": "رياضة",
        "emojis":   ["⚽", "🏀", "🎾", "🏈", "🥊"],
        "colors":   [("#1f4a2a","#3e9054"), ("#5a3a1e","#c08038"),
                     ("#1e3a5a","#3870a8"), ("#5a1e1e","#b03838"),
                     ("#3a3a1e","#909048")],
    },
    "toys": {
        "label_ar": "ألعاب",
        "emojis":   ["🧸", "🎲", "🚂", "🪀", "🎯"],
        "colors":   [("#5a2e1e","#d68838"), ("#1f4a5a","#48a8c0"),
                     ("#5a1e3a","#c04880"), ("#1e5a3a","#48b078"),
                     ("#3a1e5a","#8048b8")],
    },
}


SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="400" height="300" fill="url(#g)"/>
  <text x="200" y="180" text-anchor="middle"
        font-family="Apple Color Emoji,Segoe UI Emoji,Noto Color Emoji,Twemoji,sans-serif"
        font-size="140">{emoji}</text>
  <text x="200" y="260" text-anchor="middle"
        font-family="Tahoma,Arial,sans-serif" font-size="22"
        fill="rgba(255,255,255,0.85)" font-weight="700">{label}</text>
</svg>
"""


def main():
    total = 0
    for slug, meta in CATEGORIES.items():
        cat_dir = os.path.join(OUT_DIR, slug)
        os.makedirs(cat_dir, exist_ok=True)
        for i in range(5):
            c1, c2 = meta["colors"][i]
            svg = SVG_TEMPLATE.format(
                c1=c1, c2=c2,
                emoji=meta["emojis"][i],
                label=meta["label_ar"],
            )
            path = os.path.join(cat_dir, f"{i}.svg")
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg)
            total += 1
    print(f"Wrote {total} SVGs to {OUT_DIR}")


if __name__ == "__main__":
    main()
