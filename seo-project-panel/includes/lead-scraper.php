<?php
/**
 * Lead Scraper helper functions — integrates with the broader SEO project panel.
 */

/**
 * Return all stored leads, optionally filtered by category or keyword.
 */
function get_leads(string $category = '', string $keyword = ''): array {
    $file = __DIR__ . '/../lead-scraper/results/leads.json';
    if (!file_exists($file)) {
        return [];
    }

    $leads = json_decode(file_get_contents($file), true) ?? [];

    if ($category !== '') {
        $leads = array_filter($leads, fn($l) => ($l['category'] ?? '') === $category);
    }

    if ($keyword !== '') {
        $kw    = strtolower($keyword);
        $leads = array_filter($leads, function ($l) use ($kw) {
            return str_contains(strtolower($l['name']    ?? ''), $kw)
                || str_contains(strtolower($l['email']   ?? ''), $kw)
                || str_contains(strtolower($l['website'] ?? ''), $kw);
        });
    }

    return array_values($leads);
}

/**
 * Return the total count of stored leads.
 */
function count_leads(): int {
    return count(get_leads());
}

/**
 * Append a single lead array to the persistent store.
 * Returns true on success.
 */
function save_lead(array $lead): bool {
    $file    = __DIR__ . '/../lead-scraper/results/leads.json';
    $existing = file_exists($file) ? (json_decode(file_get_contents($file), true) ?? []) : [];

    $lead['scraped_at'] = $lead['scraped_at'] ?? date('c');
    $existing[]         = $lead;

    return file_put_contents(
        $file,
        json_encode($existing, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
    ) !== false;
}

/**
 * Delete leads that match a given email address.
 * Returns the number of leads removed.
 */
function delete_lead_by_email(string $email): int {
    $file   = __DIR__ . '/../lead-scraper/results/leads.json';
    $leads  = file_exists($file) ? (json_decode(file_get_contents($file), true) ?? []) : [];
    $before = count($leads);

    $leads  = array_values(array_filter($leads, fn($l) => ($l['email'] ?? '') !== $email));
    file_put_contents($file, json_encode($leads, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

    return $before - count($leads);
}
