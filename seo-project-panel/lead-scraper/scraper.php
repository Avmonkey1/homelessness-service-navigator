<?php
/**
 * Core scraping logic.
 *
 * Public API: scrape_domain(string $domain, array $config): array
 * Returns: ['emails' => [], 'phones' => [], 'contact_forms' => [], 'urls_scraped' => []]
 */

function scrape_domain(string $domain, array $config): array {
    $results = [
        'emails'        => [],
        'phones'        => [],
        'contact_forms' => [],
        'urls_scraped'  => [],
    ];

    $baseUrl   = 'https://' . $domain;
    $visited   = [];
    $queue     = [$baseUrl];
    $maxPages  = $config['max_pages'] ?? 10;

    while (!empty($queue) && count($visited) < $maxPages) {
        $url = array_shift($queue);

        if (isset($visited[$url])) {
            continue;
        }
        $visited[$url] = true;

        $html = _fetch_url($url, $config);
        if ($html === false) {
            continue;
        }

        $results['urls_scraped'][] = $url;

        // Extract contacts from this page
        _extract_emails($html, $results['emails']);
        _extract_phones($html, $results['phones']);
        _extract_contact_forms($html, $url, $domain, $results['contact_forms']);

        // Discover internal links to crawl next
        $links = _extract_internal_links($html, $url, $domain);
        foreach ($links as $link) {
            if (!isset($visited[$link]) && !in_array($link, $queue, true)) {
                $queue[] = $link;
            }
        }

        if ($config['request_delay_ms'] > 0) {
            usleep($config['request_delay_ms'] * 1000);
        }
    }

    // Deduplicate
    $results['emails']        = array_values(array_unique($results['emails']));
    $results['phones']        = array_values(array_unique($results['phones']));
    $results['contact_forms'] = array_values(array_unique($results['contact_forms']));

    return $results;
}

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

function _fetch_url(string $url, array $config): string|false {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT        => $config['request_timeout'] ?? 15,
        CURLOPT_HTTPHEADER     => $config['request_headers'] ?? [],
        CURLOPT_SSL_VERIFYPEER => true,
    ]);

    $html     = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    return ($html !== false && $httpCode === 200) ? $html : false;
}

function _extract_emails(string $html, array &$emails): void {
    preg_match_all(
        '/[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/',
        $html,
        $matches
    );
    foreach ($matches[0] as $email) {
        $emails[] = strtolower($email);
    }
}

function _extract_phones(string $html, array &$phones): void {
    // North American + international formats
    preg_match_all(
        '/(\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}/',
        $html,
        $matches
    );
    foreach ($matches[0] as $phone) {
        $phones[] = trim($phone);
    }
}

function _extract_contact_forms(string $html, string $pageUrl, string $domain, array &$forms): void {
    $dom = new DOMDocument();
    libxml_use_internal_errors(true);
    $dom->loadHTML($html);
    libxml_clear_errors();

    $xpath = new DOMXPath($dom);

    // Pages whose URL or title suggests a contact form
    $contactPatterns = ['contact', 'get-in-touch', 'reach-us', 'enquiry', 'inquiry'];
    foreach ($contactPatterns as $pattern) {
        if (stripos($pageUrl, $pattern) !== false) {
            $forms[] = $pageUrl;
            return;
        }
    }

    // Pages that contain a <form> with action or method
    $formNodes = $xpath->query('//form[@action or @method]');
    if ($formNodes->length > 0) {
        $forms[] = $pageUrl;
    }
}

function _extract_internal_links(string $html, string $currentUrl, string $domain): array {
    $dom = new DOMDocument();
    libxml_use_internal_errors(true);
    $dom->loadHTML($html);
    libxml_clear_errors();

    $xpath = new DOMXPath($dom);
    $links = [];

    foreach ($xpath->query('//a[@href]') as $node) {
        $href = $node->getAttribute('href');

        // Resolve relative URLs
        if (str_starts_with($href, '/')) {
            $href = 'https://' . $domain . $href;
        } elseif (!str_starts_with($href, 'http')) {
            continue; // skip mailto:, javascript:, anchors, etc.
        }

        // Keep only same-domain links
        $parsed = parse_url($href);
        if (($parsed['host'] ?? '') === $domain) {
            // Strip fragment
            $href = strtok($href, '#');
            if ($href) {
                $links[] = $href;
            }
        }
    }

    return $links;
}
