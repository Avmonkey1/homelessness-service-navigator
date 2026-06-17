<?php
/**
 * Lead Scraper Configuration
 */

$config = [
    // Directory where results are stored (trailing slash required)
    'results_dir' => __DIR__ . '/results/',

    // Predefined domains for bulk scraping (host names, no scheme)
    'domains' => [
        // 'example.com',
        // 'another-site.org',
    ],

    // Maximum pages to crawl per domain
    'max_pages' => 10,

    // Milliseconds to wait between requests
    'request_delay_ms' => 500,

    // cURL timeout in seconds
    'request_timeout' => 15,

    // HTTP headers sent with every request
    'request_headers' => [
        'User-Agent: Mozilla/5.0 (compatible; LeadScraper/1.0)',
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language: en-US,en;q=0.5',
    ],
];
