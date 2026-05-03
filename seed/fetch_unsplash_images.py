"""Populate seed/image_cache.json with Unsplash URLs keyed by product-variant
keyword. Run ONCE locally with your free Unsplash access key.

Usage:
    set UNSPLASH_ACCESS_KEY=your_key_here          # Windows / PowerShell
    export UNSPLASH_ACCESS_KEY=your_key_here       # bash
    python seed/fetch_unsplash_images.py

Free-tier limit is 50 req/hour; this script makes ~84 requests (one per
unique keyword) and prints a warning if you get rate-limited so you can
re-run later to fill the gaps.

Get a key at: https://unsplash.com/developers (free, 30s signup).
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(__file__))

from excel_to_sqlite import PRODUCT_VARIANTS, CATEGORY_AR

CACHE_PATH = os.path.join(os.path.dirname(__file__), "image_cache.json")
ENDPOINT = "https://api.unsplash.com/search/photos"


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def fetch(keyword, key):
    qs = urllib.parse.urlencode({
        "query": keyword,
        "per_page": 1,
        "orientation": "landscape",
        "content_filter": "high",
    })
    url = f"{ENDPOINT}?{qs}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Client-ID {key}",
        "Accept-Version": "v1",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    results = data.get("results", [])
    if not results:
        return None
    return results[0]["urls"].get("small") or results[0]["urls"].get("regular")


def main():
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        print("ERROR: set UNSPLASH_ACCESS_KEY first.")
        sys.exit(1)

    cache = load_cache()
    keywords = []
    for cat, variants in PRODUCT_VARIANTS.items():
        for _, kw in variants:
            if kw not in keywords:
                keywords.append(kw)

    fetched = skipped = failed = 0
    for kw in keywords:
        if kw in cache and cache[kw]:
            skipped += 1
            continue
        try:
            url = fetch(kw, key)
            if url:
                cache[kw] = url
                fetched += 1
                print(f"  ✓ {kw:32s} → {url[:60]}…")
            else:
                cache[kw] = None
                failed += 1
                print(f"  · {kw:32s} (no result)")
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"  ! {kw}: rate-limited — saving partial cache and stopping")
                break
            print(f"  ! {kw}: HTTP {e.code}")
            failed += 1
        except Exception as e:
            print(f"  ! {kw}: {e}")
            failed += 1
        save_cache(cache)
        time.sleep(0.4)        # gentle pacing

    print(f"\nDone. fetched={fetched} skipped={skipped} failed={failed} "
          f"total_cached={sum(1 for v in cache.values() if v)} / {len(keywords)}")


if __name__ == "__main__":
    main()
