<?php
/**
 * Lead Scraper Dashboard
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/scraper.php';

$message = '';
$leads   = [];
$errors  = [];

// Load existing leads from storage
if (file_exists(LEADS_FILE)) {
    $content = file_get_contents(LEADS_FILE);
    $leads   = json_decode($content, true) ?? [];
}

// Handle run-scraper action
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'run') {
    global $SCRAPER_SOURCES;

    if (empty($SCRAPER_SOURCES)) {
        $message = 'No source URLs configured. Add them to config.php first.';
    } else {
        $scraper = new LeadScraper();
        $newLeads = $scraper->run($SCRAPER_SOURCES);
        $errors   = $scraper->getErrors();

        if ($scraper->saveLeads()) {
            $content = file_get_contents(LEADS_FILE);
            $leads   = json_decode($content, true) ?? [];
            $message = 'Scrape complete. Found ' . count($newLeads) . ' new lead(s).';
        } else {
            $message = 'Scrape ran but failed to save results.';
        }
    }
}

// Handle clear action
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'clear') {
    file_put_contents(LEADS_FILE, '[]');
    $leads   = [];
    $message = 'All leads cleared.';
}

// Handle export-CSV action
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'export') {
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="leads_' . date('Ymd_His') . '.csv"');
    $out = fopen('php://output', 'w');
    fputcsv($out, ['Name', 'Email', 'Phone', 'Website', 'Address', 'Category', 'Source URL', 'Scraped At']);
    foreach ($leads as $lead) {
        fputcsv($out, [
            $lead['name']       ?? '',
            $lead['email']      ?? '',
            $lead['phone']      ?? '',
            $lead['website']    ?? '',
            $lead['address']    ?? '',
            $lead['category']   ?? '',
            $lead['source_url'] ?? '',
            $lead['scraped_at'] ?? '',
        ]);
    }
    fclose($out);
    exit;
}

// Render results template
require __DIR__ . '/templates/results.php';
?>

<!-- Dashboard controls (appended below the results template) -->
<hr>
<section style="margin:2rem 0;font-family:sans-serif;">
    <h2>Controls</h2>

    <?php if ($message): ?>
    <p style="background:#e8f5e9;border:1px solid #a5d6a7;padding:.75rem 1rem;border-radius:4px;margin-bottom:1rem;">
        <?= htmlspecialchars($message) ?>
    </p>
    <?php endif; ?>

    <form method="post" style="display:inline-block;margin-right:.5rem;">
        <input type="hidden" name="action" value="run">
        <button type="submit">Run Scraper</button>
    </form>

    <form method="post" style="display:inline-block;margin-right:.5rem;"
          onsubmit="return confirm('Export all leads as CSV?');">
        <input type="hidden" name="action" value="export">
        <button type="submit">Export CSV</button>
    </form>

    <form method="post" style="display:inline-block;"
          onsubmit="return confirm('Clear all stored leads? This cannot be undone.');">
        <input type="hidden" name="action" value="clear">
        <button type="submit" style="color:#c62828;">Clear All Leads</button>
    </form>
</section>
