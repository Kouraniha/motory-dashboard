"""
Motory Price Scraper — GitHub Actions version
Scrapes Syarah.com for latest car prices using Playwright (handles JS rendering).
Updates src/prices.json with fresh prices.

Usage: python src/scrape_prices.py
"""

import json
import os
import re
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES_JSON = os.path.join(REPO_ROOT, "src", "prices.json")

# ─── Load current prices ──────────────────────────────────────────────────────
with open(PRICES_JSON) as f:
    data = json.load(f)

cars        = data["cars"]
syarah_urls = data.get("syarah_urls", {})
today       = datetime.now().strftime("%Y-%m-%d")

print(f"Scraping Syarah prices — {today}")
print(f"Cars to scrape: {len(syarah_urls)}\n")

# ─── Price extraction helper ──────────────────────────────────────────────────
PRICE_JS = """
() => {
    // Collect all numeric tokens that look like SAR prices (10,000 – 1,000,000)
    const all = [];
    document.querySelectorAll('*').forEach(el => {
        if (el.children.length > 0) return;   // leaf nodes only
        const t = el.textContent.trim();
        // Match patterns like "62,675" or "62675"
        const m = t.match(/^(\\d{1,3}(?:,\\d{3})+|\\d{5,7})$/);
        if (m) {
            const n = parseInt(m[1].replace(/,/g,''));
            if (n >= 15000 && n <= 1000000) all.push(n);
        }
    });
    return all.length ? Math.min(...all) : null;
}
"""

def scrape_syarah(page, model, url):
    """Return the lowest SAR price found on a Syarah model page, or None."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=35000)
        # Give React/Next.js time to hydrate
        page.wait_for_timeout(4000)
        price = page.evaluate(PRICE_JS)
        if price:
            print(f"  ✅  {model:30s}  {price:>8,} SAR")
        else:
            print(f"  ⚠️   {model:30s}  price not found — keeping current")
        return price
    except PWTimeout:
        print(f"  ⏱️   {model:30s}  timeout — keeping current")
        return None
    except Exception as e:
        print(f"  ❌  {model:30s}  error: {e}")
        return None

# ─── Build model → car index map ──────────────────────────────────────────────
model_index = {car["model"].replace("*","").strip(): i for i, car in enumerate(cars)}

# ─── Scrape ───────────────────────────────────────────────────────────────────
updated = 0
failed  = 0

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx     = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="ar-SA",
        extra_http_headers={"Accept-Language": "ar-SA,ar;q=0.9,en;q=0.8"},
    )
    page = ctx.new_page()

    for model, url in syarah_urls.items():
        clean = model.replace("*","").strip()
        idx   = model_index.get(clean)
        if idx is None:
            print(f"  ⚠️   {model} — not found in cars list, skipping")
            continue

        price = scrape_syarah(page, model, url)

        if price and price > 0:
            cars[idx]["sy"] = price
            # Update da (DriveArabia reference) if it was same as sy before
            if cars[idx].get("da") == cars[idx].get("sy") or cars[idx].get("da") is None:
                cars[idx]["da"] = price
            updated += 1
        else:
            failed += 1

    browser.close()

# ─── Save updated prices ──────────────────────────────────────────────────────
data["last_updated"] = today
data["cars"]         = cars

with open(PRICES_JSON, "w") as f:
    json.dump(data, f, indent=2)

print(f"\n{'─'*50}")
print(f"Scraping complete:  {updated} updated,  {failed} unchanged")
print(f"Saved: {PRICES_JSON}")

if failed > len(syarah_urls) * 0.5:
    print("\n⚠️  More than 50% of scrapes failed — check Syarah site structure")
    sys.exit(1)   # Fail the workflow so we get a notification
