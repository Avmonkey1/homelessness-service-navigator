<?php
/**
 * Core scraping logic
 */

require_once __DIR__ . '/config.php';

class LeadScraper {

    private array $leads = [];
    private array $errors = [];

    public function run(array $sources): array {
        foreach ($sources as $url) {
            $this->scrapeSource($url);
            usleep(REQUEST_DELAY_MS * 1000);
        }
        return $this->leads;
    }

    private function scrapeSource(string $url): void {
        $html = $this->fetch($url);
        if ($html === false) {
            $this->errors[] = "Failed to fetch: $url";
            return;
        }

        $extracted = $this->extractLeads($html, $url);
        foreach ($extracted as $lead) {
            $this->leads[] = $lead;
            if (count($this->leads) >= MAX_LEADS_PER_RUN) {
                break 2;
            }
        }
    }

    private function fetch(string $url): string|false {
        global $REQUEST_HEADERS;

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT        => REQUEST_TIMEOUT_SEC,
            CURLOPT_HTTPHEADER     => $REQUEST_HEADERS,
            CURLOPT_SSL_VERIFYPEER => true,
        ]);

        $html = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        return ($html !== false && $httpCode === 200) ? $html : false;
    }

    private function extractLeads(string $html, string $sourceUrl): array {
        $leads = [];
        $dom = new DOMDocument();
        libxml_use_internal_errors(true);
        $dom->loadHTML($html);
        libxml_clear_errors();

        $xpath = new DOMXPath($dom);

        // Extract email addresses via regex on raw HTML
        preg_match_all(
            '/[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/',
            $html,
            $emailMatches
        );

        // Extract phone numbers (basic North American pattern)
        preg_match_all(
            '/(\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}/',
            $html,
            $phoneMatches
        );

        // Extract page title as a fallback name
        $titleNodes = $xpath->query('//title');
        $pageName = $titleNodes->length ? trim($titleNodes->item(0)->textContent) : '';

        $emails  = array_unique($emailMatches[0]);
        $phones  = array_unique($phoneMatches[0]);

        // Build one lead per unique email found
        foreach ($emails as $i => $email) {
            $leads[] = [
                'name'       => $pageName,
                'email'      => $email,
                'phone'      => $phones[$i] ?? '',
                'website'    => $sourceUrl,
                'address'    => '',
                'category'   => '',
                'source_url' => $sourceUrl,
                'scraped_at' => date('c'),
            ];
        }

        return $leads;
    }

    public function getErrors(): array {
        return $this->errors;
    }

    public function saveLeads(): bool {
        $existing = [];
        if (file_exists(LEADS_FILE)) {
            $content  = file_get_contents(LEADS_FILE);
            $existing = json_decode($content, true) ?? [];
        }

        $merged = array_merge($existing, $this->leads);
        return file_put_contents(
            LEADS_FILE,
            json_encode($merged, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
        ) !== false;
    }
}
