<?php
/**
 * Lead Scraper helper functions — integrates with the broader SEO project panel.
 *
 * Data format on disk: { "domain.com": { emails: [], phones: [], contact_forms: [], urls_scraped: [] }, ... }
 */

function _leads_file(): string {
    return __DIR__ . '/../lead-scraper/results/leads.json';
}

function _load_all_leads(): array {
    $file = _leads_file();
    return file_exists($file) ? (json_decode(file_get_contents($file), true) ?? []) : [];
}

function _save_all_leads(array $data): bool {
    return file_put_contents(
        _leads_file(),
        json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)
    ) !== false;
}

/**
 * Return scraped data for a single domain, or null if not yet scraped.
 */
function get_leads_for_domain(string $domain): ?array {
    $all = _load_all_leads();
    return $all[$domain] ?? null;
}

/**
 * Return all scraped domains and their data.
 */
function get_all_leads(): array {
    return _load_all_leads();
}

/**
 * Count total unique emails across all scraped domains.
 */
function count_total_emails(): int {
    $total = 0;
    foreach (_load_all_leads() as $data) {
        $total += count($data['emails'] ?? []);
    }
    return $total;
}

/**
 * Count total unique phone numbers across all scraped domains.
 */
function count_total_phones(): int {
    $total = 0;
    foreach (_load_all_leads() as $data) {
        $total += count($data['phones'] ?? []);
    }
    return $total;
}

/**
 * Persist scrape results for a domain (overwrites existing entry).
 */
function save_domain_leads(string $domain, array $leads): bool {
    $all          = _load_all_leads();
    $all[$domain] = $leads;
    return _save_all_leads($all);
}

/**
 * Remove a domain's data from the store. Returns true if the domain existed.
 */
function delete_domain_leads(string $domain): bool {
    $all = _load_all_leads();
    if (!isset($all[$domain])) {
        return false;
    }
    unset($all[$domain]);
    return _save_all_leads($all);
}
