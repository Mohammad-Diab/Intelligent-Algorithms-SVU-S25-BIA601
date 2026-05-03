"""Resolve LoremFlickr redirect URLs in data/product_images.csv to their final
Flickr CDN URLs IN PLACE. Run once after replacing the CSV with a fresh catalog
that has redirect-style URLs.

After this finishes, the CSV's image_url column contains the final resolved
URLs (sized 400x300, no redirect hop). The seed reads the CSV directly.

Usage:
    python seed/resolve_image_urls.py

Skips rows whose URL is already resolved (cache/resized/...).
"""
import csv
import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
CSV_PATH = os.path.join(DATA_DIR, "product_images.csv")

TIMEOUT = 15
WORKERS = 8


def downsize(url):
    return url.replace("/800/600/", "/400/300/")


def needs_resolve(url):
    return "/cache/resized/" not in url


def resolve(url):
    """Follow redirects, return the final URL after the chain."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.geturl()
    except urllib.error.HTTPError as e:
        return e.url
    except Exception:
        return None


def main():
    if not os.path.exists(CSV_PATH):
        print(f"missing {CSV_PATH}")
        sys.exit(1)

    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("empty CSV")
        return
    fieldnames = list(rows[0].keys())

    # Downsize first so resolve hits the smaller variant
    pending = []
    for i, row in enumerate(rows):
        url = downsize(row.get("image_url", "").strip())
        row["image_url"] = url
        if needs_resolve(url):
            pending.append(i)

    if not pending:
        print(f"All {len(rows)} URLs already resolved.")
        # still write back (in case of size normalization)
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader() or None
            csv.DictWriter(f, fieldnames=fieldnames).writerows(rows)
        return

    print(f"Resolving {len(pending)} URLs ({WORKERS} workers)...")
    start = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(resolve, rows[i]["image_url"]): i for i in pending}
        for fut in as_completed(futs):
            i = futs[fut]
            final = fut.result()
            if final:
                rows[i]["image_url"] = final
            done += 1
            if done % 25 == 0 or done == len(pending):
                print(f"  {done}/{len(pending)}  ({time.time()-start:.1f}s)")

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nUpdated {len(rows)} rows in {CSV_PATH}")


if __name__ == "__main__":
    main()
