#!/usr/bin/env python3
"""
scrape_prices.py  —  Scrape latest SAR prices from Syarah.com
Runs as part of the GitHub Actions daily-update workflow.
Falls back to existing prices gracefully if Syarah is unreachable.
"""

import json, sys, os, re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES_FILE = os.path.join(REPO_ROOT, "src", "prices.json")

PRICE_JS = """
() => {
    const all = [];
    document.querySelectorAll('*').forEach(el => {
        if (el.children.length > 0) return;
        const t = el.textContent.trim();
        const m = t.match(/^(\d{1,3}(?:,\d{3})+|\d{5,7})$/);
        if (m) {
            const n = parseInt(m[1].replace(/,/g,''));
            if (n >= 15000 && n <= 1000000) all.push(n);
        }
    });
    return all.length ? Math.min(...all) : null;
}
"""

def scrape_price(page, url, retries=2):
    """Try to scrape a price from a Syarah URL, with retries."""
    for attempt in range(retries + 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            # Wait for React to render content
            page.wait_for_timeout(8000)
            price = page.evaluate(PRICE_JS)
            if price:
                return price
            # Extra wait and retry
            if attempt < retries:
                page.wait_for_timeout(4000)
        except PWTimeout:
            if attempt < retries:
                continue
        except Exception as e:
            print(f"    Error on attempt {attempt+1}: {e}")
            if attempt < retries:
                continue
    return None


def main():
    with open(PRICES_FILE, "r", encoding="utf-8") as f:
        cars = json.load(f)

    print(f"Scraping Syarah prices — {datetime.utcnow().strftime('%Y-%m-%d')}")
    print(f"Cars to scrape: {len(cars)}\n")

    updated = 0
    failed = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--lang=ar-SA",
            ]
        )
        context = browser.new_context(
            locale="ar-SA",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        for car in cars:
            url = car.get("syarah_url", "")
            if not url:
                failed += 1
                print(f"⚠️  {car['model']} — no URL defined, skipping")
                continue

            price = scrape_price(page, url)
            if price:
                old = car.get("syarah_price")
                car["syarah_price"] = price
                car["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d")
                updated += 1
                change = ""
                if old and old != price:
                    diff = price - old
                    change = f"  (was {old:,}, Δ {'+' if diff>0 else ''}{diff:,})"
                print(f"✅  {car['model']}: SAR {price:,}{change}")
            else:
                failed += 1
                print(f"⚠️  {car['model']} price not found — keeping current")

        browser.close()

    print(f"\n{'─'*50}")
    print(f"Scraping complete: {updated} updated, {len(cars)-updated} unchanged")

    with open(PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(cars, f, ensure_ascii=False, indent=2)
    print(f"Saved: {PRICES_FILE}")

    # Warn but do NOT fail the workflow — rebuild still runs with existing prices
    fail_rate = failed / len(cars) if cars else 0
    if fail_rate > 0.5:
        print(f"\n⚠️  Warning: {failed}/{len(cars)} scrapes failed ({fail_rate:.0%})")
        print("   Dashboard will rebuild with existing prices.")
    # Always exit 0 so the rebuild step runs
    sys.exit(0)


if __name__ == "__main__":
    main()
