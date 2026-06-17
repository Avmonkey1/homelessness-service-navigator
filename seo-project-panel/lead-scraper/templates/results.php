<?php
// Expects $leads (array) and $errors (array) to be set by the caller
$leads  = $leads  ?? [];
$errors = $errors ?? [];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lead Scraper — Results</title>
    <style>
        body { font-family: sans-serif; margin: 2rem; color: #222; }
        h1   { margin-bottom: 1rem; }
        .stats { margin-bottom: 1.5rem; color: #555; }
        .errors { background: #ffeaea; border: 1px solid #f99; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; }
        table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #ddd; }
        th { background: #f4f4f4; font-weight: 600; }
        tr:hover td { background: #fafafa; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Scraped Leads</h1>

    <div class="stats">
        Total leads: <strong><?= count($leads) ?></strong>
        &nbsp;|&nbsp;
        Scraped: <strong><?= htmlspecialchars(date('Y-m-d H:i:s')) ?></strong>
    </div>

    <?php if (!empty($errors)): ?>
    <div class="errors">
        <strong>Errors encountered:</strong>
        <ul>
            <?php foreach ($errors as $err): ?>
            <li><?= htmlspecialchars($err) ?></li>
            <?php endforeach; ?>
        </ul>
    </div>
    <?php endif; ?>

    <?php if (empty($leads)): ?>
    <p>No leads found yet. Add source URLs in <code>config.php</code> and run the scraper.</p>
    <?php else: ?>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Website</th>
                <th>Category</th>
                <th>Scraped At</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($leads as $i => $lead): ?>
            <tr>
                <td><?= $i + 1 ?></td>
                <td><?= htmlspecialchars($lead['name'] ?? '') ?></td>
                <td>
                    <?php if (!empty($lead['email'])): ?>
                    <a href="mailto:<?= htmlspecialchars($lead['email']) ?>">
                        <?= htmlspecialchars($lead['email']) ?>
                    </a>
                    <?php endif; ?>
                </td>
                <td><?= htmlspecialchars($lead['phone'] ?? '') ?></td>
                <td>
                    <?php if (!empty($lead['website'])): ?>
                    <a href="<?= htmlspecialchars($lead['website']) ?>" target="_blank" rel="noopener">
                        <?= htmlspecialchars($lead['website']) ?>
                    </a>
                    <?php endif; ?>
                </td>
                <td><?= htmlspecialchars($lead['category'] ?? '') ?></td>
                <td><?= htmlspecialchars($lead['scraped_at'] ?? '') ?></td>
            </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
    <?php endif; ?>
</body>
</html>
