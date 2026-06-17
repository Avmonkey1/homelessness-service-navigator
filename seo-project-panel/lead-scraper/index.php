<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/scraper.php';

// Ensure results directory exists
if (!is_dir($config['results_dir'])) {
    mkdir($config['results_dir'], 0755, true);
}

// Load existing leads
$leads_file = $config['results_dir'] . 'leads.json';
$all_leads = file_exists($leads_file) ? json_decode(file_get_contents($leads_file), true) : [];

// Handle form submission
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['scrape_domain'])) {
    $domain = trim($_POST['domain']);
    if (!empty($domain)) {
        // Add http:// if missing
        if (strpos($domain, 'http') !== 0) {
            $domain = 'https://' . $domain;
        }
        $parsed = parse_url($domain);
        $domain_name = $parsed['host'] ?? $domain;

        // Scrape the domain
        $leads = scrape_domain($domain_name, $config);

        // Save results
        $all_leads[$domain_name] = $leads;
        file_put_contents($leads_file, json_encode($all_leads, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));

        // Redirect to avoid form resubmission
        header("Location: " . $_SERVER['PHP_SELF']);
        exit;
    }
}

// Handle bulk scrape
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['bulk_scrape'])) {
    foreach ($config['domains'] as $domain) {
        if (!isset($all_leads[$domain])) {
            $leads = scrape_domain($domain, $config);
            $all_leads[$domain] = $leads;
        }
    }
    file_put_contents($leads_file, json_encode($all_leads, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
    header("Location: " . $_SERVER['PHP_SELF']);
    exit;
}

// Handle clear results
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['clear_results'])) {
    file_put_contents($leads_file, json_encode([], JSON_PRETTY_PRINT));
    header("Location: " . $_SERVER['PHP_SELF']);
    exit;
}

// Function to escape output
function e($string) {
    return htmlspecialchars($string, ENT_QUOTES, 'UTF-8');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lead Scraper</title>
    <style>
        :root {
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-card: #0f3460;
            --text-primary: #eaeaea;
            --text-secondary: #a0a0a0;
            --accent: #e94560;
            --success: #4ecca3;
            --warning: #ffc107;
            --danger: #ff4757;
            --border: #2a2a4a;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            padding: 20px;
            margin: 0;
        }
        header {
            text-align: center;
            margin-bottom: 30px;
        }
        h1 {
            color: var(--accent);
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: var(--bg-card);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        form {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"], input[type="url"] {
            flex: 1;
            padding: 10px;
            border: 1px solid var(--border);
            border-radius: 4px;
            background: var(--bg-secondary);
            color: var(--text-primary);
        }
        button, .btn {
            padding: 10px 20px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
        }
        button:hover, .btn:hover {
            background: #ff6b6b;
        }
        .btn-danger {
            background: var(--danger);
        }
        .btn-danger:hover {
            background: #ff3347;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        th {
            background: var(--bg-secondary);
        }
        tr:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        .leads-list {
            margin-top: 20px;
        }
        .leads-list h3 {
            margin-bottom: 10px;
        }
        .leads-list ul {
            list-style: none;
            padding: 0;
        }
        .leads-list li {
            padding: 5px 0;
            border-bottom: 1px solid var(--border);
        }
        .domain-results {
            margin-bottom: 30px;
        }
        .domain-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .domain-header h2 {
            margin: 0;
            color: var(--accent);
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat {
            background: var(--bg-secondary);
            padding: 10px 15px;
            border-radius: 4px;
        }
        .stat strong {
            color: var(--accent);
        }
    </style>
</head>
<body>
    <header>
        <h1>Lead Scraper</h1>
        <p>Scrape emails, phone numbers, and contact forms from websites</p>
    </header>

    <div class="container">
        <div class="card">
            <h2>Scrape a Domain</h2>
            <form method="post">
                <input type="url" name="domain" placeholder="https://example.com" required>
                <button type="submit" name="scrape_domain">Scrape</button>
            </form>

            <form method="post">
                <button type="submit" name="bulk_scrape" class="btn">Bulk Scrape Predefined Domains</button>
                <button type="submit" name="clear_results" class="btn btn-danger" onclick="return confirm('Are you sure?')">Clear All Results</button>
            </form>
        </div>

        <?php if (!empty($all_leads)): ?>
            <div class="card">
                <div class="stats">
                    <div class="stat">
                        <strong>Domains Scraped:</strong> <?php echo count($all_leads); ?>
                    </div>
                    <div class="stat">
                        <strong>Total Emails:</strong>
                        <?php
                        $total_emails = 0;
                        foreach ($all_leads as $domain => $leads) {
                            $total_emails += count($leads['emails']);
                        }
                        echo $total_emails;
                        ?>
                    </div>
                    <div class="stat">
                        <strong>Total Phones:</strong>
                        <?php
                        $total_phones = 0;
                        foreach ($all_leads as $domain => $leads) {
                            $total_phones += count($leads['phones']);
                        }
                        echo $total_phones;
                        ?>
                    </div>
                </div>

                <?php foreach ($all_leads as $domain => $leads): ?>
                    <div class="domain-results">
                        <div class="domain-header">
                            <h2><?php echo e($domain); ?></h2>
                            <span>Scraped <?php echo count($leads['urls_scraped']); ?> pages</span>
                        </div>

                        <div class="leads-list">
                            <h3>Emails (<?php echo count($leads['emails']); ?>)</h3>
                            <?php if (!empty($leads['emails'])): ?>
                                <ul>
                                    <?php foreach ($leads['emails'] as $email): ?>
                                        <li><a href="mailto:<?php echo e($email); ?>"><?php echo e($email); ?></a></li>
                                    <?php endforeach; ?>
                                </ul>
                            <?php else: ?>
                                <p>No emails found.</p>
                            <?php endif; ?>
                        </div>

                        <div class="leads-list">
                            <h3>Phone Numbers (<?php echo count($leads['phones']); ?>)</h3>
                            <?php if (!empty($leads['phones'])): ?>
                                <ul>
                                    <?php foreach ($leads['phones'] as $phone): ?>
                                        <li><a href="tel:<?php echo e(preg_replace('/[^0-9+]/', '', $phone)); ?>"><?php echo e($phone); ?></a></li>
                                    <?php endforeach; ?>
                                </ul>
                            <?php else: ?>
                                <p>No phone numbers found.</p>
                            <?php endif; ?>
                        </div>

                        <div class="leads-list">
                            <h3>Contact Forms (<?php echo count($leads['contact_forms']); ?>)</h3>
                            <?php if (!empty($leads['contact_forms'])): ?>
                                <ul>
                                    <?php foreach ($leads['contact_forms'] as $form): ?>
                                        <li><a href="<?php echo e($form); ?>" target="_blank"><?php echo e($form); ?></a></li>
                                    <?php endforeach; ?>
                                </ul>
                            <?php else: ?>
                                <p>No contact forms found.</p>
                            <?php endif; ?>
                        </div>
                    </div>
                <?php endforeach; ?>
            </div>
        <?php else: ?>
            <div class="card">
                <p>No leads scraped yet. Enter a domain and click "Scrape" to begin.</p>
            </div>
        <?php endif; ?>
    </div>
</body>
</html>
