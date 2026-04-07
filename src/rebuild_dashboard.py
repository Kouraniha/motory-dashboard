"""
Motory Dashboard Rebuild Script — GitHub Actions version
- Reads src/prices.json with today's scraped prices
- Updates src/Motory_Dashboard.html with new prices and date
- Re-encrypts into index.html via src/build_dashboard.js

Usage: python src/rebuild_dashboard.py
"""

import json
import re
import subprocess
import os
from datetime import datetime

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR       = os.path.join(REPO_ROOT, "src")
PRICES_JSON   = os.path.join(SRC_DIR, "prices.json")
DASHBOARD_SRC = os.path.join(SRC_DIR, "Motory_Dashboard.html")
BUILD_JS      = os.path.join(SRC_DIR, "build_dashboard.js")
OUTPUT_HTML   = os.path.join(REPO_ROOT, "index.html")

print(f"Dashboard source: {DASHBOARD_SRC}")
print(f"Prices file:      {PRICES_JSON}")
print(f"Output:           {OUTPUT_HTML}")

# ─── Load prices ──────────────────────────────────────────────────────────────
with open(PRICES_JSON) as f:
    price_data = json.load(f)

cars    = price_data["cars"]
today   = datetime.now().strftime("%B %d, %Y")
today_iso = datetime.now().strftime("%Y-%m-%d")

print(f"\nUpdating dashboard for: {today}")
print(f"Cars to update: {len(cars)}")

# ─── Load dashboard HTML ───────────────────────────────────────────────────────
with open(DASHBOARD_SRC, encoding="utf-8") as f:
    html = f.read()

# ─── Update date badge ────────────────────────────────────────────────────────
html = re.sub(
    r'(<div class="date-badge">Data as of: )([^<]+)(</div>)',
    rf'\g<1>{today}\3',
    html
)
print(f"Date updated to: {today}")

# ─── Update car prices in JavaScript array ────────────────────────────────────
changes = 0
for car in cars:
    model   = car["model"]
    variant = car["variant"]
    seg     = car["seg"]

    ms_val = str(car["ms"]) if car["ms"] is not None else "null"
    sy_val = str(car["sy"]) if car["sy"] is not None else "null"
    ym_val = str(car["ym"]) if car["ym"] is not None else "null"
    ha_val = str(car["ha"]) if car["ha"] is not None else "null"
    da_val = str(car["da"]) if car["da"] is not None else "null"
    cs_val = str(car.get("da", car["sy"])) if car.get("da") or car.get("sy") else "null"

    model_clean = model.replace("*","").strip()
    model_esc   = re.escape(model_clean)
    variant_esc = re.escape(variant)
    seg_esc     = re.escape(seg)

    pattern = (
        r'\{seg:"' + seg_esc + r'",\s*model:"' + model_esc + r'\*?",\s*variant:"' + variant_esc + r'",\s*'
        r'ms:[^,]+,\s*sy:[^,]+,\s*ym:[^,]+,\s*ha:[^,]+,\s*da:[^,]+,\s*cs:[^}]+\}'
    )

    replacement = (
        f'{{seg:"{seg}", model:"{model}", variant:"{variant}", '
        f'ms:{ms_val}, sy:{sy_val}, ym:{ym_val}, ha:{ha_val}, da:{da_val}, cs:{cs_val}}}'
    )

    new_html, n = re.subn(pattern, replacement, html)
    if n > 0:
        html = new_html
        changes += 1
    else:
        print(f"  WARNING: Could not match entry for {model} / {variant}")

print(f"Updated {changes}/{len(cars)} car entries")

# ─── Write updated dashboard source ──────────────────────────────────────────
with open(DASHBOARD_SRC, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Dashboard HTML updated: {DASHBOARD_SRC}")

# ─── Update last_updated in prices.json ──────────────────────────────────────
price_data["last_updated"] = today_iso
with open(PRICES_JSON, "w") as f:
    json.dump(price_data, f, indent=2)

# ─── Re-encrypt with Node.js ──────────────────────────────────────────────────
print("\nRe-encrypting dashboard...")
result = subprocess.run(
    ["node", BUILD_JS],
    capture_output=True, text=True,
    cwd=REPO_ROOT
)
if result.returncode == 0:
    size = os.path.getsize(OUTPUT_HTML)
    print(f"✅  Encrypted index.html: {size:,} bytes")
    print(result.stdout.strip())
else:
    print(f"❌  Encryption failed:\n{result.stderr}")
    exit(1)

print(f"\n✅  Rebuild complete → {OUTPUT_HTML}")
