<?php
/**
 * Lead Scraper Configuration
 */

define('SCRAPER_VERSION', '1.0.0');
define('RESULTS_DIR', __DIR__ . '/results');
define('LEADS_FILE', RESULTS_DIR . '/leads.json');

// Scraper settings
define('MAX_LEADS_PER_RUN', 100);
define('REQUEST_DELAY_MS', 500);       // delay between requests in milliseconds
define('REQUEST_TIMEOUT_SEC', 15);

// Target sources (add URLs or search queries to scrape)
$SCRAPER_SOURCES = [
    // 'https://example.com/directory',
];

// Fields to extract per lead
$LEAD_FIELDS = [
    'name',
    'email',
    'phone',
    'website',
    'address',
    'category',
    'source_url',
    'scraped_at',
];

// HTTP headers for requests
$REQUEST_HEADERS = [
    'User-Agent: Mozilla/5.0 (compatible; LeadScraper/' . SCRAPER_VERSION . ')',
    'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language: en-US,en;q=0.5',
];
