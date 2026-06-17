"""
Django management command to scrape 211 directory for DC-area homeless services.

Usage:
    python manage.py scrape_211
    python manage.py scrape_211 --base-url https://dc.211.org --delay 3
    python manage.py scrape_211 --zip-codes 20001 20002 20003 --dry-run
    python manage.py scrape_211 --search-terms "shelter" "food" "housing"
"""

import logging
import re
import time
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

try:
    import lxml  # noqa: F401
    _BS4_PARSER = 'lxml'
except ImportError:
    _BS4_PARSER = 'html.parser'

from navigator.models import OrganizationInfo

logger = logging.getLogger(__name__)

# Maps 211/AIRS taxonomy terms to the project's internal service names.
CATEGORY_MAP = {
    'accessibility': 'ACCESSIBILITY_SERVICES',
    'accessible': 'ACCESSIBILITY_SERVICES',
    'adult literacy': 'ADULT_LITERACY',
    'literacy': 'ADULT_LITERACY',
    'art therapy': 'ART_THERAPY',
    'assessment': 'ASSESSMENT',
    'intake': 'ASSESSMENT',
    'borrow': 'BORROW_MATERIALS',
    'lending library': 'BORROW_MATERIALS',
    'case management': 'CASE_MANAGEMENT',
    'case manager': 'CASE_MANAGEMENT',
    'child care': 'CHILD_CARE',
    'childcare': 'CHILD_CARE',
    'daycare': 'CHILD_CARE',
    'clothing': 'CLOTHING',
    'clothes': 'CLOTHING',
    'computer': 'COMPUTERS',
    'internet access': 'COMPUTERS',
    'dental': 'DENTAL_SERVICES',
    'documentation': 'DOCUMENTATION_ASSISTANCE',
    'id assistance': 'DOCUMENTATION_ASSISTANCE',
    'vital records': 'DOCUMENTATION_ASSISTANCE',
    'domestic violence': 'DOMESTIC_VIOLENCE_SERVICES',
    'dv services': 'DOMESTIC_VIOLENCE_SERVICES',
    'food pantry': 'FOOD_GROCERIES',
    'groceries': 'FOOD_GROCERIES',
    'food bank': 'FOOD_GROCERIES',
    'food assistance': 'FOOD_GROCERIES',
    'food': 'FOOD_GROCERIES',
    'support groups': 'GROUPS',
    'groups': 'GROUPS',
    'haircut': 'HAIRCUTS',
    'barber': 'HAIRCUTS',
    'harm reduction': 'HARM_REDUCTION',
    'needle exchange': 'HARM_REDUCTION',
    'hiv testing': 'HIV_TESTING',
    'std testing': 'HIV_TESTING',
    'housing': 'HOUSING',
    'shelter': 'HOUSING',
    'emergency shelter': 'HOUSING',
    'transitional housing': 'HOUSING',
    'housing navigation': 'HOUSING_NAVIGATION',
    'housing assistance': 'HOUSING_NAVIGATION',
    'housing search': 'HOUSING_NAVIGATION',
    'tax': 'INCOME_TAX_HELP',
    'vita': 'INCOME_TAX_HELP',
    'laundry': 'LAUNDRY',
    'legal': 'LEGAL_SERVICES',
    'lgbtq': 'LGBTQ_FOCUSED',
    'transgender': 'LGBTQ_FOCUSED',
    'library card': 'LIBRARY_CARD',
    'mail': 'MAIL',
    'mailing address': 'MAIL',
    'meals': 'MEALS',
    'hot meals': 'MEALS',
    'soup kitchen': 'MEALS',
    'meal program': 'MEALS',
    'medical benefits': 'MEDICAL_BENEFITS',
    'medicaid': 'MEDICAL_BENEFITS',
    'medical': 'MEDICAL_SERVICES',
    'health care': 'MEDICAL_SERVICES',
    'clinic': 'MEDICAL_SERVICES',
    'mental health': 'MENTAL_HEALTH',
    'behavioral health': 'MENTAL_HEALTH',
    'counseling': 'MENTAL_HEALTH',
    'therapy': 'MENTAL_HEALTH',
    'ministry': 'MINISTRY',
    'faith': 'MINISTRY',
    'chapel': 'MINISTRY',
    'phone': 'PHONE',
    'voicemail': 'PHONE',
    'restroom': 'PUBLIC_RESTROOMS',
    'bathroom': 'PUBLIC_RESTROOMS',
    'refreshment': 'REFRESHMENTS',
    'snack': 'REFRESHMENTS',
    'coffee': 'REFRESHMENTS',
    'shower': 'SHOWERS',
    'hygiene': 'SHOWERS',
    'snap': 'SNAP_FOOD_STAMPS',
    'food stamps': 'SNAP_FOOD_STAMPS',
    'ebt': 'SNAP_FOOD_STAMPS',
    'storage': 'STORAGE',
    'baggage': 'STORAGE',
    'substance abuse': 'SUBSTANCE_ABUSE_TREATMENT',
    'substance use': 'SUBSTANCE_ABUSE_TREATMENT',
    'addiction': 'SUBSTANCE_ABUSE_TREATMENT',
    'recovery': 'SUBSTANCE_ABUSE_TREATMENT',
    'detox': 'SUBSTANCE_ABUSE_TREATMENT',
    'employment': 'SUPPORTED_EMPLOYMENT',
    'job placement': 'SUPPORTED_EMPLOYMENT',
    'work readiness': 'SUPPORTED_EMPLOYMENT',
    'tanf': 'TANF_FINANCIAL_ASSISTANCE',
    'financial assistance': 'TANF_FINANCIAL_ASSISTANCE',
    'emergency assistance': 'TANF_FINANCIAL_ASSISTANCE',
    'transportation': 'TRANSPORTATION',
    'bus pass': 'TRANSPORTATION',
    'vocational': 'VOCATIONAL_TRAINING',
    'job training': 'VOCATIONAL_TRAINING',
    'skills training': 'VOCATIONAL_TRAINING',
}

# DC zip codes covering all 8 wards.
CO_LOCATIONS = [
    'Denver, CO',
    'Colorado Springs, CO',
    'Aurora, CO',
    'Boulder, CO',
    'Fort Collins, CO',
    'Pueblo, CO',
    'Lakewood, CO',
    'Thornton, CO',
]

# Search terms targeting homeless-relevant services.
SEARCH_TERMS = [
    'homeless shelter',
    'emergency shelter',
    'transitional housing',
    'food bank',
    'mental health',
    'substance abuse treatment',
    'employment services',
    'medical services',
]


class Command(BaseCommand):
    help = 'Scrape 211 directory for homeless services and load into database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-url',
            default='https://search.211colorado.org',
            help='Base URL of the 211 site (default: https://search.211colorado.org)',
        )
        parser.add_argument(
            '--locations',
            nargs='+',
            default=CO_LOCATIONS,
            help='City/location strings to search (default: major Colorado cities)',
        )
        parser.add_argument(
            '--search-terms',
            nargs='+',
            default=SEARCH_TERMS,
            help='Search terms to query (default: common homeless service terms)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Seconds between requests to be respectful (default: 2.0)',
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=5,
            help='Max pages per search query (default: 5)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print results without saving to database',
        )
        parser.add_argument(
            '--state',
            default='CO',
            help='Default state for parsed organizations (default: CO)',
        )
        parser.add_argument(
            '--city',
            default='DENVER',
            help='Default city for parsed organizations (default: DENVER)',
        )

    def handle(self, *args, **options):
        self.base_url = options['base_url'].rstrip('/')
        self.delay = options['delay']
        self.max_pages = options['max_pages']
        self.dry_run = options['dry_run']
        self.default_state = options['state'].upper()
        self.default_city = options['city'].upper()

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) '
                'Gecko/20100101 Firefox/115.0'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })

        seen_keys = set()
        saved = 0
        updated = 0
        skipped = 0

        locations = options['locations']
        search_terms = options['search_terms']

        self.stdout.write(
            f'Scraping {self.base_url} | '
            f'{len(locations)} location(s) × {len(search_terms)} search term(s)'
        )

        for zip_code in locations:
            for term in search_terms:
                orgs = self._scrape_search(term, zip_code)
                for org in orgs:
                    dedup_key = (org['name'].lower(), org['street'].lower())
                    if dedup_key in seen_keys:
                        continue
                    seen_keys.add(dedup_key)

                    if self.dry_run:
                        self.stdout.write(self._format_org(org))
                    else:
                        result = self._save_org(org)
                        if result == 'created':
                            saved += 1
                        elif result == 'updated':
                            updated += 1
                        else:
                            skipped += 1

                time.sleep(self.delay)

        if self.dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'Dry run complete — found {len(seen_keys)} unique organizations'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Done: {saved} created, {updated} updated, {skipped} skipped'
            ))

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    def _scrape_search(self, term, zip_code):
        """Scrape all pages for a single (term, zip_code) combination."""
        results = []
        for page in range(1, self.max_pages + 1):
            url = self._search_url(term, zip_code, page)
            html = self._fetch(url)
            if html is None:
                break

            soup = BeautifulSoup(html, _BS4_PARSER)
            page_results = self._parse_page(soup)
            if not page_results:
                break

            results.extend(page_results)

            if not self._has_next_page(soup):
                break

            time.sleep(self.delay)

        return results

    def _fetch(self, url):
        """Fetch a URL and return HTML text, or None on failure."""
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            logger.warning('Request failed for %s: %s', url, exc)
            self.stderr.write(f'  [skip] {url} — {exc}')
            return None

    def _search_url(self, term, location, page=1):
        # search.211colorado.org uses: terms=, location=, service_area=, page=
        params = {
            'terms': term,
            'location': location,
            'service_area': 'colorado',
            'page': page,
        }
        return f'{self.base_url}/search?{urlencode(params)}'

    # ------------------------------------------------------------------
    # HTML parsing  (multi-selector strategy for iCarol / generic 211 sites)
    # ------------------------------------------------------------------

    def _parse_page(self, soup):
        """Return a list of raw org dicts from a search results page."""
        containers = self._find_result_containers(soup)
        return [org for org in (self._parse_container(c) for c in containers) if org]

    def _find_result_containers(self, soup):
        """Try common CSS selectors used by iCarol and other 211 platforms."""
        strategies = [
            # iCarol (dc.211.org)
            '.result-item',
            '.search-result',
            '.agency-result',
            # findhelp / Aunt Bertha
            '[data-testid="result-item"]',
            '.listing-item',
            # Generic
            'article.result',
            '.resource-result',
            '.service-listing',
            '.provider-card',
        ]
        for selector in strategies:
            containers = soup.select(selector)
            if containers:
                return containers
        return []

    def _parse_container(self, el):
        """Extract a single organization dict from a result container element."""
        org = {
            'name': self._extract_name(el),
            'url': self._extract_url(el),
            'phone_number': self._extract_phone(el),
            'street': '',
            'city': self.default_city,
            'state': self.default_state,
            'zipcode': None,
            'services': self._extract_services(el),
        }

        addr = self._extract_address(el)
        if addr:
            self._populate_address_fields(addr, org)

        # Drop records with no name or no street — not useful.
        if not org['name'] or not org['street']:
            return None

        return org

    def _extract_name(self, el):
        name_el = (
            el.select_one('h2.result-name') or
            el.select_one('h2.agency-name') or
            el.select_one('.result-title') or
            el.select_one('.listing-name') or
            el.select_one('.provider-name') or
            el.select_one('h2') or
            el.select_one('h3') or
            el.select_one('.name')
        )
        return name_el.get_text(strip=True) if name_el else ''

    def _extract_url(self, el):
        link = el.select_one('a.result-link, a.agency-link, a[href*="/detail"], h2 a, h3 a, a[href]')
        if not link:
            return ''
        href = link.get('href', '')
        if href.startswith('http'):
            return href
        return urljoin(self.base_url, href)

    def _extract_phone(self, el):
        phone_el = (
            el.select_one('.phone') or
            el.select_one('.result-phone') or
            el.select_one('[data-type="phone"]') or
            el.select_one('[class*="phone"]')
        )
        raw = phone_el.get_text(strip=True) if phone_el else ''

        # Fall back: scan all text for a phone pattern.
        if not raw:
            text = el.get_text(' ', strip=True)
            m = re.search(r'(\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4})', text)
            raw = m.group(1) if m else ''

        return raw or None

    def _extract_address(self, el):
        addr_el = (
            el.select_one('.address') or
            el.select_one('.result-address') or
            el.select_one('[data-type="address"]') or
            el.select_one('.location') or
            el.select_one('[class*="address"]')
        )
        return addr_el.get_text(separator=' ', strip=True) if addr_el else ''

    def _extract_services(self, el):
        tag_els = (
            el.select('.service-tag') or
            el.select('.category-tag') or
            el.select('.tag') or
            el.select('.service') or
            el.select('[class*="service-tag"]') or
            el.select('[class*="category"]')
        )
        services = []
        for tag in tag_els:
            mapped = self._map_category(tag.get_text(strip=True))
            if mapped and mapped not in services:
                services.append(mapped)
        return services

    def _map_category(self, text):
        """Map a free-text 211 category to an internal service name."""
        lower = text.lower().strip()
        if lower in CATEGORY_MAP:
            return CATEGORY_MAP[lower]
        for key, value in CATEGORY_MAP.items():
            if key in lower:
                return value
        return None

    def _populate_address_fields(self, addr_text, org):
        """Parse a raw address string and write into the org dict."""
        # Zip code
        zip_m = re.search(r'\b(\d{5})(?:-\d{4})?\b', addr_text)
        if zip_m:
            org['zipcode'] = int(zip_m.group(1))

        # State abbreviation
        state_m = re.search(r'\b(DC|MD|VA|WV)\b', addr_text, re.IGNORECASE)
        if state_m:
            org['state'] = state_m.group(1).upper()

        # Street / city split on comma
        parts = [p.strip() for p in addr_text.split(',')]
        if len(parts) >= 2:
            org['street'] = parts[0]
            city_m = re.match(r'^([A-Za-z .]+)', parts[1])
            if city_m:
                org['city'] = city_m.group(1).strip().upper()
        elif parts:
            org['street'] = parts[0]

    def _has_next_page(self, soup):
        return bool(
            soup.select_one('a[rel="next"]') or
            soup.select_one('.pagination .next:not(.disabled)') or
            soup.select_one('a.next-page') or
            soup.select_one('[aria-label="Next page"]') or
            soup.select_one('.pager-next a')
        )

    # ------------------------------------------------------------------
    # Database persistence
    # ------------------------------------------------------------------

    def _save_org(self, org):
        """
        Upsert an organization.
        Returns 'created', 'updated', or 'skipped'.
        """
        try:
            obj, created = OrganizationInfo.objects.get_or_create(
                name=org['name'],
                street=org['street'],
                defaults={
                    'url': org.get('url', ''),
                    'phone_number': org.get('phone_number'),
                    'city': org.get('city', self.default_city),
                    'state': org.get('state', self.default_state),
                    'zipcode': org.get('zipcode'),
                    'services': org.get('services', []),
                },
            )
            if created:
                return 'created'

            # Merge any new service tags discovered in this pass.
            new_services = set(org.get('services', []))
            existing_services = set(obj.services or [])
            merged = existing_services | new_services
            if merged != existing_services:
                obj.services = list(merged)
                obj.save(update_fields=['services'])
                return 'updated'

            return 'skipped'
        except Exception as exc:  # noqa: BLE001
            logger.error('Failed to save org "%s": %s', org.get('name'), exc)
            self.stderr.write(f'  [error] {org.get("name")}: {exc}')
            return 'skipped'

    # ------------------------------------------------------------------
    # Dry-run formatting
    # ------------------------------------------------------------------

    def _format_org(self, org):
        return (
            f'\n--- {org["name"]}\n'
            f'  Address : {org["street"]}, {org["city"]}, {org["state"]} {org["zipcode"]}\n'
            f'  Phone   : {org["phone_number"]}\n'
            f'  URL     : {org["url"]}\n'
            f'  Services: {", ".join(org["services"]) or "(none mapped)"}'
        )
