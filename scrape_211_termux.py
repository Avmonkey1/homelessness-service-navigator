#!/usr/bin/env python3
"""
211 Colorado homeless services scraper — copy-paste ready for Termux.

Install deps:
    pip install requests beautifulsoup4

Run:
    python3 scrape_211_termux.py
    python3 scrape_211_termux.py --location "Denver, CO" --terms "shelter" "food"
    python3 scrape_211_termux.py --output my_results.csv
"""

import argparse
import csv
import json
import re
import sys
import time

# ── dependency check ─────────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    sys.exit("Missing requests — run:  pip install requests")

try:
    from bs4 import BeautifulSoup
    try:
        import lxml
        _PARSER = 'lxml'
    except ImportError:
        _PARSER = 'html.parser'
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False
    print("Tip: pip install beautifulsoup4  (needed for HTML fallback parsing)")

# ── config ────────────────────────────────────────────────────────────────────
BASE_URL = "https://search.211colorado.org"
SEARCH_PATH = "/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.6367.82 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL + "/",
    "Connection": "keep-alive",
}

DEFAULT_TERMS = [
    "homeless shelter",
    "emergency shelter",
    "transitional housing",
    "food bank",
    "mental health",
    "substance abuse treatment",
    "employment services",
    "medical services",
]

DEFAULT_LOCATIONS = [
    "Denver, CO",
    "Colorado Springs, CO",
    "Aurora, CO",
    "Boulder, CO",
    "Fort Collins, CO",
    "Pueblo, CO",
    "Lakewood, CO",
    "Thornton, CO",
]

# ── helpers ───────────────────────────────────────────────────────────────────

def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    # warm-up visit to get session cookies
    try:
        s.get(BASE_URL, timeout=15)
    except requests.RequestException:
        pass
    return s


def fetch_page(session, term, location, page):
    params = {
        "terms": term,
        "location": location,
        "service_area": "colorado",
        "page": page,
    }
    try:
        r = session.get(BASE_URL + SEARCH_PATH, params=params, timeout=30)
        print(f"    HTTP {r.status_code}  ({len(r.content)} bytes)")
        if r.status_code == 200:
            return r
        if r.status_code == 403:
            print("    403 — site is blocking this request. Try --delay 5 or run again later.")
        return None
    except requests.RequestException as exc:
        print(f"    Request error: {exc}")
        return None


def parse_response(r):
    """Try JSON first, fall back to HTML."""
    content_type = r.headers.get("Content-Type", "")

    # ── JSON API path ──
    if "json" in content_type:
        try:
            return _parse_json(r.json())
        except Exception as exc:
            print(f"    JSON parse error: {exc}")
            return []

    # ── Try JSON anyway (some servers don't set the right Content-Type) ──
    try:
        data = r.json()
        orgs = _parse_json(data)
        if orgs:
            return orgs
    except Exception:
        pass

    # ── HTML path ──
    return _parse_html(r.text)


def _parse_json(data):
    """Extract orgs from common iCarol / Open Referral JSON shapes."""
    orgs = []
    records = (
        data.get("records") or
        data.get("results") or
        data.get("data") or
        data.get("agencies") or
        data.get("organizations") or
        (data if isinstance(data, list) else [])
    )
    for rec in records:
        name = (
            rec.get("name") or rec.get("AgencyName") or
            rec.get("agency_name") or rec.get("title") or ""
        )
        phone = (
            rec.get("phone") or rec.get("PublicPhone") or
            rec.get("phone_number") or ""
        )
        street = (
            rec.get("address") or rec.get("PhysicalAddress") or
            rec.get("address1") or rec.get("street_address") or ""
        )
        city  = rec.get("city") or rec.get("City") or ""
        state = rec.get("state") or rec.get("State") or "CO"
        zipcode = rec.get("zip") or rec.get("postal_code") or rec.get("Zip") or ""
        url   = rec.get("url") or rec.get("website") or rec.get("Website") or ""

        services_raw = rec.get("services") or rec.get("Services") or []
        if isinstance(services_raw, list):
            services = "; ".join(str(s) for s in services_raw)
        else:
            services = str(services_raw)

        description = rec.get("description") or rec.get("Description") or ""

        if name:
            orgs.append({
                "name": name.strip(),
                "phone": str(phone).strip(),
                "street": str(street).strip(),
                "city": str(city).strip(),
                "state": str(state).strip(),
                "zip": str(zipcode).strip(),
                "url": str(url).strip(),
                "services": services,
                "description": description[:300] if description else "",
            })
    return orgs


def _parse_html(html):
    if not _HAS_BS4:
        print("    (Install beautifulsoup4 to parse HTML responses)")
        return []

    soup = BeautifulSoup(html, _PARSER)
    orgs = []

    containers = (
        soup.select(".result-item") or
        soup.select(".search-result") or
        soup.select(".listing-item") or
        soup.select(".resource-card") or
        soup.select("article.result") or
        soup.select("[class*='result-item']") or
        soup.select("[class*='listing']")
    )

    for c in containers:
        name_el = (
            c.select_one("h2.name, h3.name, .agency-name, .result-title") or
            c.select_one("h2, h3") or
            c.select_one(".name, .title")
        )
        name = name_el.get_text(strip=True) if name_el else ""

        phone_el = c.select_one(".phone, [class*='phone'], [data-type='phone']")
        if not phone_el:
            m = re.search(r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}', c.get_text())
            phone = m.group().strip() if m else ""
        else:
            phone = phone_el.get_text(strip=True)

        addr_el = c.select_one(".address, [class*='address'], .location")
        address = addr_el.get_text(separator=" ", strip=True) if addr_el else ""

        zip_m = re.search(r'\b(\d{5})\b', address)
        zipcode = zip_m.group(1) if zip_m else ""

        link_el = c.select_one("a[href]")
        url = link_el["href"] if link_el else ""

        if name:
            orgs.append({
                "name": name, "phone": phone, "street": address,
                "city": "", "state": "CO", "zip": zipcode,
                "url": url, "services": "", "description": "",
            })
    return orgs


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrape 211 Colorado homeless services")
    parser.add_argument("--terms", nargs="+", default=DEFAULT_TERMS,
                        help="Search terms")
    parser.add_argument("--location", nargs="+", default=DEFAULT_LOCATIONS,
                        help="City/location strings")
    parser.add_argument("--output", default="211colorado_services.csv",
                        help="Output CSV filename (default: 211colorado_services.csv)")
    parser.add_argument("--delay", type=float, default=2.5,
                        help="Seconds between requests (default: 2.5)")
    parser.add_argument("--max-pages", type=int, default=5,
                        help="Max pages per search (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print results without saving")
    args = parser.parse_args()

    locations = args.location if isinstance(args.location, list) else [args.location]
    terms = args.terms

    print(f"Target  : {BASE_URL}")
    print(f"Locations: {len(locations)}  |  Terms: {len(terms)}  |  Max pages: {args.max_pages}")
    print(f"Output  : {'[dry-run]' if args.dry_run else args.output}\n")

    session = make_session()
    all_orgs = []
    seen = set()

    for location in locations:
        for term in terms:
            print(f"[{term}] @ {location}")
            for page in range(1, args.max_pages + 1):
                r = fetch_page(session, term, location, page)
                if r is None:
                    break

                orgs = parse_response(r)
                print(f"    → {len(orgs)} records on page {page}")

                if not orgs:
                    break

                added = 0
                for org in orgs:
                    key = (org["name"].lower().strip(), org["street"].lower().strip())
                    if key not in seen and org["name"]:
                        seen.add(key)
                        all_orgs.append(org)
                        added += 1

                print(f"    → {added} new unique orgs (total so far: {len(all_orgs)})")
                time.sleep(args.delay)

    print(f"\n{'='*50}")
    print(f"Total unique organizations found: {len(all_orgs)}")

    if not all_orgs:
        print("\nNo results. Possible reasons:")
        print("  • Site returned 403 (try --delay 5 and run again)")
        print("  • Search terms returned no matches")
        print("  • Response format changed (check HTTP status above)")
        return

    if args.dry_run:
        for org in all_orgs[:10]:
            print(f"\n  {org['name']}")
            print(f"    {org['street']} {org['city']}, {org['state']} {org['zip']}")
            print(f"    Phone: {org['phone']}")
            print(f"    URL  : {org['url']}")
        if len(all_orgs) > 10:
            print(f"\n  ... and {len(all_orgs) - 10} more")
        return

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_orgs[0].keys())
        writer.writeheader()
        writer.writerows(all_orgs)

    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
