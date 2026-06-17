#!/usr/bin/env python3
"""Debug script — paste into Termux, run it, share the output."""

import sys
try:
    import requests
except ImportError:
    sys.exit("pip install requests")

URL = "https://search.211colorado.org/search"
PARAMS = {
    "terms": "homeless shelter",
    "location": "Denver, CO",
    "service_area": "colorado",
    "page": 1,
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.6367.82 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://search.211colorado.org/",
}

s = requests.Session()
s.headers.update(HEADERS)

# 1. Hit homepage first to get cookies
print("Step 1: homepage...")
try:
    home = s.get("https://search.211colorado.org", timeout=15)
    print(f"  Status : {home.status_code}")
    print(f"  Cookies: {dict(s.cookies)}")
except Exception as e:
    print(f"  Error  : {e}")

# 2. Search request
print("\nStep 2: search request...")
try:
    r = s.get(URL, params=PARAMS, timeout=30)
    print(f"  Status      : {r.status_code}")
    print(f"  Content-Type: {r.headers.get('Content-Type', 'unknown')}")
    print(f"  Body size   : {len(r.content)} bytes")
    print(f"  URL called  : {r.url}")

    # Show first 2000 chars of body
    body = r.text[:2000]
    print(f"\n--- First 2000 chars of response ---\n{body}\n---")

    # Try JSON
    try:
        data = r.json()
        print(f"\nJSON keys at root: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    print(f"  '{k}' is a list of {len(v)} items")
                    if v:
                        print(f"    First item keys: {list(v[0].keys()) if isinstance(v[0], dict) else type(v[0])}")
                else:
                    print(f"  '{k}': {str(v)[:100]}")
        elif isinstance(data, list):
            print(f"Root is list of {len(data)} items")
            if data:
                print(f"  First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
    except Exception:
        print("\nNot JSON — is HTML/other")
        # Check for React SPA shell
        if '<div id="root"' in r.text or '<div id="app"' in r.text:
            print("*** React SPA detected — content is client-side rendered ***")
            print("*** Need Selenium or a headless browser to get data ***")
        # Check for iCarol patterns
        for pattern in ['icarol', 'resource-item', 'listing-item', 'result-item', 'agency']:
            if pattern.lower() in r.text.lower():
                print(f"Found HTML pattern: '{pattern}'")

except Exception as e:
    print(f"  Error: {e}")
