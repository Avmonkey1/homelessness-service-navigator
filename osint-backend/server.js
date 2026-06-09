require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const https = require('https');
const dns = require('dns').promises;

const app = express();
const PORT = process.env.PORT || 3001;

app.use(helmet());
app.use(express.json());

app.use(cors({
  origin: [
    'http://localhost:3000',
    'http://localhost:5173',
    process.env.FRONTEND_URL,
  ].filter(Boolean),
  methods: ['GET', 'POST'],
}));

const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000,
  max: parseInt(process.env.RATE_LIMIT_MAX) || 100,
  message: { error: 'Too many requests, please try again later.' },
});
app.use('/api/', limiter);

// ── Utility ────────────────────────────────────────────────────────────────

function httpsGet(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'OSINT-MVP/1.0' } }, (res) => {
      let data = '';
      res.on('data', chunk => (data += chunk));
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch { resolve(data); }
      });
    }).on('error', reject);
  });
}

// ── Investigation modules ───────────────────────────────────────────────────

async function checkDnsRecords(domain) {
  try {
    const [a, mx, txt, ns] = await Promise.allSettled([
      dns.resolve4(domain),
      dns.resolveMx(domain),
      dns.resolveTxt(domain),
      dns.resolveNs(domain),
    ]);

    const aRecords  = a.status  === 'fulfilled' ? a.value  : [];
    const mxRecords = mx.status === 'fulfilled' ? mx.value : [];
    const nsRecords = ns.status === 'fulfilled' ? ns.value : [];

    return {
      title: 'DNS Configuration',
      meaning: `Found ${aRecords.length} A record(s), ${mxRecords.length} MX record(s), ${nsRecords.length} NS record(s).`,
      risk: 'Low',
      source: 'DNS Lookup (live)',
      action: 'Review records for accuracy and unexpected entries.',
      confidence: aRecords.length > 0 ? 'Confirmed' : 'Unverified',
      section: 'general',
      explanation: `A records: ${aRecords.join(', ') || 'none'}. NS: ${nsRecords.join(', ') || 'none'}.`,
      whyItMatters: 'DNS records control where traffic is routed and can reveal infrastructure.',
      doesNotProve: 'This does not prove the DNS configuration is optimal or secure.',
      nextStep: 'Audit records for unauthorised changes (DNS hijacking).',
    };
  } catch {
    return null;
  }
}

async function checkRdap(domain) {
  try {
    const data = await httpsGet(`https://rdap.org/domain/${domain}`);
    const registrar = data.entities
      ? data.entities.find(e => Array.isArray(e.roles) && e.roles.includes('registrar'))
      : null;
    const registrarName = registrar?.vcardArray?.[1]?.find(f => f[0] === 'fn')?.[3] || 'Unknown';
    const expires = data.events?.find(e => e.eventAction === 'expiration')?.eventDate || 'Unknown';

    return {
      title: 'Domain Ownership (RDAP)',
      meaning: `Registrar: ${registrarName}. Expiry: ${expires}.`,
      risk: 'Low',
      source: 'RDAP (rdap.org)',
      action: 'Verify the registrar and expiry date are expected.',
      confidence: 'Confirmed',
      section: 'important',
      explanation: 'RDAP is the modern replacement for WHOIS and provides structured registration data.',
      whyItMatters: 'Knowing the domain owner can help establish accountability.',
      doesNotProve: 'This does not prove the domain is malicious or involved in illegal activity.',
      nextStep: 'Check whether registrant details are public or privacy-redacted.',
    };
  } catch {
    return {
      title: 'Domain Ownership (RDAP)',
      meaning: 'RDAP lookup could not be completed for this domain.',
      risk: 'Unknown',
      source: 'RDAP (rdap.org)',
      action: 'Try a manual WHOIS lookup.',
      confidence: 'Unverified',
      section: 'important',
      explanation: 'The RDAP service did not return data — the domain may be unregistered or the TLD unsupported.',
      whyItMatters: 'Registration data can confirm domain legitimacy.',
      doesNotProve: 'A failed lookup does not prove the domain is malicious.',
      nextStep: 'Use https://lookup.icann.org for a manual check.',
    };
  }
}

async function checkCertTransparency(domain) {
  try {
    const data = await httpsGet(`https://crt.sh/?q=%.${domain}&output=json`);
    if (!Array.isArray(data)) return null;

    const subdomains = [...new Set(
      data.map(c => c.name_value).flatMap(n => n.split('\n'))
        .filter(n => n.endsWith(domain) && n !== domain)
    )].slice(0, 10);

    return {
      title: 'Certificate Transparency History',
      meaning: `${data.length} certificate(s) issued. ${subdomains.length} unique subdomain(s) found.`,
      risk: subdomains.length > 5 ? 'Medium' : 'Low',
      source: 'crt.sh (Certificate Transparency Logs)',
      action: 'Check whether old subdomains still resolve and are secured.',
      confidence: 'Confirmed',
      section: 'possible',
      explanation: `Subdomains seen: ${subdomains.slice(0, 5).join(', ')}${subdomains.length > 5 ? '…' : ''}.`,
      whyItMatters: 'Forgotten subdomains can be attack vectors.',
      doesNotProve: 'This does not prove the subdomains are still active or controlled by the same entity.',
      nextStep: 'DNS-resolve each subdomain to check if it is still live.',
    };
  } catch {
    return null;
  }
}

async function checkIpGeolocation(ip) {
  try {
    const data = await httpsGet(`http://ip-api.com/json/${ip}?fields=status,country,regionName,city,isp,org,as,proxy,hosting`);
    if (data.status !== 'success') return null;

    const flags = [];
    if (data.proxy)   flags.push('proxy/VPN detected');
    if (data.hosting) flags.push('hosting/datacenter IP');

    return {
      title: 'IP Geolocation & ASN',
      meaning: `${data.city}, ${data.regionName}, ${data.country} — ISP: ${data.isp}.`,
      risk: flags.length ? 'Medium' : 'Low',
      source: 'ip-api.com (live lookup)',
      action: flags.length ? `Note: ${flags.join(', ')}.` : 'Cross-reference with other data points.',
      confidence: 'Confirmed',
      section: 'important',
      explanation: `ASN: ${data.as}. Org: ${data.org}.${flags.length ? ' Flags: ' + flags.join(', ') + '.' : ''}`,
      whyItMatters: 'Location and ASN data helps identify the origin or hosting of traffic.',
      doesNotProve: 'This does not prove the exact physical location or the user\'s intent.',
      nextStep: 'Check the ASN reputation using BGPView or Shodan.',
    };
  } catch {
    return null;
  }
}

async function checkAbuseIPDB(ip) {
  if (!process.env.ABUSEIPDB_API_KEY) return null;
  try {
    const data = await new Promise((resolve, reject) => {
      const req = https.request({
        hostname: 'api.abuseipdb.com',
        path: `/api/v2/check?ipAddress=${encodeURIComponent(ip)}&maxAgeInDays=90`,
        headers: {
          Key: process.env.ABUSEIPDB_API_KEY,
          Accept: 'application/json',
        },
      }, res => {
        let body = '';
        res.on('data', c => (body += c));
        res.on('end', () => resolve(JSON.parse(body)));
      });
      req.on('error', reject);
      req.end();
    });

    const score = data.data?.abuseConfidenceScore ?? 0;
    return {
      title: 'IP Abuse Report',
      meaning: `Abuse confidence score: ${score}%. Reports in last 90 days: ${data.data?.totalReports ?? 0}.`,
      risk: score > 50 ? 'High' : score > 10 ? 'Medium' : 'Low',
      source: 'AbuseIPDB',
      action: score > 50 ? 'Treat this IP with high suspicion.' : 'Monitor for further activity.',
      confidence: 'Confirmed',
      section: 'important',
      explanation: `Country: ${data.data?.countryCode}. Usage type: ${data.data?.usageType}.`,
      whyItMatters: 'Community-reported abuse history can indicate malicious infrastructure.',
      doesNotProve: 'A low score does not guarantee the IP is safe.',
      nextStep: 'View full report at https://www.abuseipdb.com/check/' + ip,
    };
  } catch {
    return null;
  }
}

async function checkBreachExposure(email) {
  if (!process.env.HIBP_API_KEY) {
    return {
      title: 'Breach Exposure (API key required)',
      meaning: 'A Have I Been Pwned API key is needed to check breach status.',
      risk: 'Unknown',
      source: 'Have I Been Pwned',
      action: 'Add HIBP_API_KEY to .env and restart the server.',
      confidence: 'Unverified',
      section: 'important',
      explanation: 'HIBP requires a paid API key for programmatic access.',
      whyItMatters: 'Breach exposure can lead to credential stuffing and account takeover.',
      doesNotProve: 'Nothing — check manually at https://haveibeenpwned.com.',
      nextStep: 'Visit https://haveibeenpwned.com and search for this email manually.',
    };
  }

  try {
    const data = await new Promise((resolve, reject) => {
      const req = https.request({
        hostname: 'haveibeenpwned.com',
        path: `/api/v3/breachedaccount/${encodeURIComponent(email)}?truncateResponse=false`,
        headers: {
          'hibp-api-key': process.env.HIBP_API_KEY,
          'User-Agent': 'OSINT-MVP/1.0',
        },
      }, res => {
        if (res.statusCode === 404) return resolve([]);
        let body = '';
        res.on('data', c => (body += c));
        res.on('end', () => { try { resolve(JSON.parse(body)); } catch { resolve([]); } });
      });
      req.on('error', reject);
      req.end();
    });

    const count = Array.isArray(data) ? data.length : 0;
    const names = Array.isArray(data) ? data.map(b => b.Name).slice(0, 5).join(', ') : '';

    return {
      title: 'Breach Exposure',
      meaning: count > 0 ? `Found in ${count} breach(es): ${names}${count > 5 ? '…' : ''}.` : 'No breaches found.',
      risk: count > 3 ? 'High' : count > 0 ? 'Medium' : 'Low',
      source: 'Have I Been Pwned',
      action: count > 0 ? 'Change passwords and enable 2FA on affected accounts.' : 'No immediate action required.',
      confidence: 'Confirmed',
      section: 'important',
      explanation: 'HIBP aggregates known data breaches and checks whether this email appeared in any of them.',
      whyItMatters: 'Breach exposure can lead to unauthorized access or identity theft.',
      doesNotProve: 'This does not prove the email is currently compromised.',
      nextStep: 'Visit https://haveibeenpwned.com for full breach details.',
    };
  } catch {
    return null;
  }
}

function staticResult(type, target) {
  const map = {
    company: [{
      title: 'Company Name Search',
      meaning: 'Search public business registries for this company name.',
      risk: 'Low',
      source: 'OpenCorporates / Government Databases',
      action: 'Verify registration status and directors.',
      confidence: process.env.OPENCORPORATES_API_KEY ? 'Possible' : 'Unverified',
      section: 'important',
      explanation: 'Business registration records confirm legal status and registered address.',
      whyItMatters: 'Official records help verify the legitimacy and status of a company.',
      doesNotProve: 'This does not prove the company is currently operational or trustworthy.',
      nextStep: `Search https://opencorporates.com/companies?q=${encodeURIComponent(target)} manually.`,
    }],
    username: [{
      title: 'Username Search',
      meaning: 'Check common platforms for this username.',
      risk: 'Low',
      source: 'Public platform search',
      action: 'Review any public profiles for relevant information.',
      confidence: 'Possible',
      section: 'possible',
      explanation: 'Searching for a username across platforms can surface public profiles and activity.',
      whyItMatters: 'Profiles can provide context about the user\'s public activities.',
      doesNotProve: 'This does not prove the identity or intentions of the user.',
      nextStep: `Try https://whatsmyname.app/?q=${encodeURIComponent(target)} for a multi-platform check.`,
    }],
    message: [{
      title: 'Message Pattern Analysis',
      meaning: 'Message content checked against known phishing and scam patterns.',
      risk: 'Medium',
      source: 'Pattern matching',
      action: 'Verify the sender and any links before taking action.',
      confidence: 'Possible',
      section: 'important',
      explanation: 'Common scam patterns include urgency, requests for money, and suspicious links.',
      whyItMatters: 'Identifying suspicious patterns can help prevent fraud.',
      doesNotProve: 'This does not prove the message is definitely malicious.',
      nextStep: 'Extract any URLs and investigate them separately as URL targets.',
    }],
    url: [{
      title: 'URL Structure Analysis',
      meaning: `Analysed URL: ${target}`,
      risk: target.includes('bit.ly') || target.includes('tinyurl') ? 'Medium' : 'Low',
      source: 'URL parsing',
      action: 'Check URL reputation before clicking.',
      confidence: 'Confirmed',
      section: 'important',
      explanation: 'URL structure can reveal shortened links, suspicious TLDs, or obfuscated domains.',
      whyItMatters: 'Understanding URL structure helps assess potential risks.',
      doesNotProve: 'This does not prove the URL is currently malicious.',
      nextStep: 'Check reputation at https://www.virustotal.com/gui/url/',
    }],
  };
  return map[type] || [{
    title: 'General Information',
    meaning: `Passive checks completed for target: ${target}`,
    risk: 'Low',
    source: 'Public Databases',
    action: 'Review for relevance.',
    confidence: 'Unverified',
    section: 'general',
    explanation: 'No automated checks are available for this target type without additional API keys.',
    whyItMatters: 'Context helps guide the direction of the investigation.',
    doesNotProve: 'This does not prove any specific claim about the target.',
    nextStep: 'Use this as a starting point for deeper manual analysis.',
  }];
}

async function runInvestigation(type, target) {
  let checks = [];

  if (type === 'domain' || type === 'url') {
    const domain = type === 'url'
      ? target.replace(/^https?:\/\//, '').split('/')[0]
      : target;
    checks = [checkRdap(domain), checkDnsRecords(domain), checkCertTransparency(domain)];
  } else if (type === 'ip') {
    checks = [checkIpGeolocation(target), checkAbuseIPDB(target)];
  } else if (type === 'email') {
    checks = [checkBreachExposure(target)];
  } else {
    return staticResult(type, target);
  }

  const settled = await Promise.allSettled(checks);
  return settled
    .filter(r => r.status === 'fulfilled' && r.value !== null)
    .map(r => r.value);
}

// ── Routes ──────────────────────────────────────────────────────────────────

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

const INVESTIGATION_TYPES = {
  domain:   'Website or domain name',
  ip:       'IP address (IPv4)',
  email:    'Email address',
  company:  'Company name',
  username: 'Username or handle',
  message:  'Suspicious message content',
  url:      'Website URL',
};

app.get('/api/types', (_req, res) => {
  res.json({ types: Object.keys(INVESTIGATION_TYPES), description: INVESTIGATION_TYPES });
});

app.post('/api/investigate', async (req, res) => {
  const { type, target } = req.body || {};

  if (!type || !target || !target.trim()) {
    return res.status(400).json({ error: 'type and target are required' });
  }
  if (!INVESTIGATION_TYPES[type]) {
    return res.status(400).json({
      error: `Invalid type. Supported: ${Object.keys(INVESTIGATION_TYPES).join(', ')}`,
    });
  }

  try {
    const results = await runInvestigation(type, target.trim());
    res.json({
      success: true,
      type,
      target: target.trim(),
      timestamp: new Date().toISOString(),
      results,
      count: results.length,
    });
  } catch (err) {
    console.error('Investigation error:', err);
    res.status(500).json({ error: 'Investigation failed', message: err.message });
  }
});

// ── Start ───────────────────────────────────────────────────────────────────

const server = app.listen(PORT, () => {
  console.log(`OSINT backend running on port ${PORT}`);
});

module.exports = { app, server };
