import React, { useState } from 'react';

const RiskBadge = ({ level }) => {
  const colors = {
    Low: 'bg-green-100 text-green-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    High: 'bg-red-100 text-red-800',
    Unknown: 'bg-gray-100 text-gray-800',
  };
  const defaultLevel = level in colors ? level : 'Unknown';
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[defaultLevel]}`}>
      {defaultLevel}
    </span>
  );
};

const ConfidenceBadge = ({ level }) => {
  const colors = {
    Confirmed: 'bg-green-100 text-green-800',
    Likely: 'bg-blue-100 text-blue-800',
    Possible: 'bg-yellow-100 text-yellow-800',
    Unverified: 'bg-gray-100 text-gray-800',
  };
  const defaultLevel = level in colors ? level : 'Unverified';
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[defaultLevel]}`}>
      {defaultLevel}
    </span>
  );
};

const ResultCard = ({
  title,
  meaning,
  risk,
  source,
  action,
  confidence,
  explanation,
  whyItMatters,
  doesNotProve,
  nextStep
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border rounded-lg p-4 mb-4 shadow-sm bg-white">
      <div className="flex flex-wrap gap-2 justify-between items-start mb-2">
        <h3 className="font-semibold text-lg">{title}</h3>
        <div className="flex flex-wrap gap-2">
          <ConfidenceBadge level={confidence} />
          <RiskBadge level={risk} />
        </div>
      </div>

      <p className="text-sm text-gray-600 mt-2">
        <strong>What it means:</strong> {meaning}
      </p>
      <p className="text-sm text-gray-600 mt-1">
        <strong>Source:</strong> {source}
      </p>
      <p className="text-sm text-gray-600 mt-1">
        <strong>Action:</strong> {action}
      </p>

      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="mt-3 text-blue-600 text-sm hover:underline font-medium"
        aria-expanded={isExpanded}
      >
        {isExpanded ? 'Hide Explanation' : 'Explain this'}
      </button>

      {isExpanded && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm">
          <div className="mb-2">
            <strong>What this finding means:</strong> {explanation}
          </div>
          <div className="mb-2 text-gray-700">
            <strong>Why it matters:</strong> {whyItMatters}
          </div>
          <div className="mb-2 text-gray-700">
            <strong>What it does NOT prove:</strong> {doesNotProve}
          </div>
          <div className="text-gray-700">
            <strong>What you should do next:</strong> {nextStep}
          </div>
        </div>
      )}
    </div>
  );
};

const Onboarding = ({ onSelect }) => {
  const [selected, setSelected] = useState(null);
  const options = [
    { label: "Website or domain", value: "domain" },
    { label: "IP address", value: "ip" },
    { label: "Email address", value: "email" },
    { label: "Company name", value: "company" },
    { label: "Username", value: "username" },
    { label: "Suspicious message", value: "message" },
    { label: "Website URL", value: "url" },
  ];

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4 text-center">What are you investigating?</h1>
      <p className="text-gray-600 mb-6 text-center">
        Select the type of target you want to investigate.
      </p>

      <p className="text-xs text-gray-500 mb-6 text-center bg-gray-100 p-3 rounded-lg">
        <strong>Ethical Use Notice:</strong> This tool only uses passive, public, permission-based checks.
        It does not attack, scan, exploit, bypass access controls, or access private systems.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {options.map((option) => (
          <button
            type="button"
            key={option.value}
            onClick={() => {
              setSelected(option.value);
              onSelect(option.value);
            }}
            className={`p-4 border rounded-lg hover:bg-gray-50 transition-colors ${
              selected === option.value ? "bg-blue-50 border-blue-300" : ""
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
};

const Dashboard = ({ results, investigationType, target, onBack }) => {
  const labelMap = {
    domain: "Website or domain",
    ip: "IP address",
    email: "Email address",
    company: "Company name",
    username: "Username",
    message: "Suspicious message",
    url: "Website URL"
  };

  const importantResults = results.filter(r => r.section === "important");
  const possibleResults = results.filter(r => r.section === "possible");
  const generalResults = results.filter(r => r.section === "general");

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Investigation Dashboard</h1>
        <button
          type="button"
          onClick={onBack}
          className="text-gray-600 text-sm hover:underline"
        >
          &larr; Change investigation type
        </button>
      </div>

      <div className="mb-4 p-3 bg-gray-100 rounded-lg text-sm">
        <strong>Target:</strong> {target} (<strong>Type:</strong> {labelMap[investigationType] || investigationType})
      </div>

      <div className="mb-6 p-4 bg-white rounded-lg shadow-sm">
        <h2 className="text-lg font-semibold mb-2">Summary</h2>
        <p className="text-gray-600">
          We found {results.length} relevant items for your investigation.
        </p>
      </div>

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Important Findings</h2>
        {importantResults.length > 0 ? (
          <div className="space-y-4">
            {importantResults.map((result, index) => (
              <ResultCard key={index} {...result} />
            ))}
          </div>
        ) : (
          <div className="p-4 bg-gray-50 rounded-lg text-sm text-gray-500">
            No high-priority findings in this mock report.
          </div>
        )}
      </div>

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Possible Connections</h2>
        {possibleResults.length > 0 ? (
          <div className="space-y-4">
            {possibleResults.map((result, index) => (
              <ResultCard key={index} {...result} />
            ))}
          </div>
        ) : (
          <div className="p-4 bg-gray-50 rounded-lg text-sm text-gray-500">
            No possible connections found in this mock report.
          </div>
        )}
      </div>

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">All Results</h2>
        <div className="space-y-4">
          {results.map((result, index) => (
            <ResultCard key={index} {...result} />
          ))}
        </div>
      </div>

      {generalResults.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">General Information</h2>
          <div className="space-y-4">
            {generalResults.map((result, index) => (
              <ResultCard key={index} {...result} />
            ))}
          </div>
        </div>
      )}

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">What We Cannot Confirm</h2>
        <div className="p-4 bg-yellow-50 rounded-lg text-sm text-yellow-800">
          <p>
            Some findings may require additional verification.
            Always cross-check with multiple sources before drawing conclusions.
          </p>
        </div>
      </div>

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Recommended Next Steps</h2>
        <div className="p-4 bg-blue-50 rounded-lg text-sm">
          <ul className="list-disc pl-5">
            <li>Review all findings for accuracy.</li>
            <li>Verify high-risk items independently.</li>
            <li>Check for false positives or outdated data.</li>
          </ul>
        </div>
      </div>

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Source List</h2>
        <div className="p-4 bg-gray-50 rounded-lg text-sm">
          <p>
            Data is sourced from public records, open databases, and third-party APIs.
            No private or proprietary systems are accessed.
          </p>
        </div>
      </div>

      <div className="flex space-x-4">
        <button type="button" className="border rounded-lg p-2 px-4 hover:bg-gray-50 transition-colors">
          Export Report
        </button>
        <button type="button" className="border rounded-lg p-2 px-4 hover:bg-gray-50 transition-colors">
          Show Graph View
        </button>
      </div>
    </div>
  );
};

const BACKEND_URL = process.env.REACT_APP_OSINT_API_URL || 'http://localhost:3001';

const OSINTApp = () => {
  const [investigationType, setInvestigationType] = useState(null);
  const [target, setTarget] = useState('');
  const [hasStarted, setHasStarted] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState([]);

  const labelMap = {
    domain: "Website or domain",
    ip: "IP address",
    email: "Email address",
    company: "Company name",
    username: "Username",
    message: "Suspicious message",
    url: "Website URL"
  };

  const validateTarget = (type, value) => {
    if (!value.trim()) return 'Please enter a target.';

    switch (type) {
      case 'domain':
      case 'url':
        if (!/^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$/.test(value)) {
          return 'Please enter a valid domain (e.g., example.com).';
        }
        break;
      case 'email':
        if (!value.includes('@')) {
          return 'Please enter a valid email address (e.g., user@example.com).';
        }
        break;
      case 'ip':
        if (!/^(\d{1,3}\.){3}\d{1,3}$/.test(value)) {
          return 'Please enter a valid IPv4 address (e.g., 192.168.1.1).';
        }
        break;
      default:
        break;
    }
    return '';
  };

  const handleSelect = (type) => {
    setInvestigationType(type);
    setTarget('');
    setHasStarted(false);
    setError('');
    setResults([]);
  };

  const handleBack = () => {
    setInvestigationType(null);
    setTarget('');
    setHasStarted(false);
    setError('');
    setResults([]);
  };

  const handleStartInvestigation = async () => {
    const validationError = validateTarget(investigationType, target);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${BACKEND_URL}/api/investigate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: investigationType, target: target.trim() }),
      });
      const data = await response.json();
      if (data.success) {
        setResults(data.results);
        setHasStarted(true);
      } else {
        setError(data.error || 'Investigation failed.');
      }
    } catch {
      setError('Could not reach the backend server. Is it running on port 3001?');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTargetChange = (e) => {
    setTarget(e.target.value);
    setError('');
  };

  const isValid = !validateTarget(investigationType, target);

  return (
    <div className="min-h-screen bg-gray-50">
      {!investigationType ? (
        <Onboarding onSelect={handleSelect} />
      ) : !hasStarted ? (
        <div className="p-4 max-w-2xl mx-auto">
          <button
            type="button"
            onClick={handleBack}
            className="mb-4 text-gray-600 text-sm hover:underline"
          >
            &larr; Back
          </button>

          <h1 className="text-2xl font-bold mb-4">Investigating: {labelMap[investigationType] || investigationType}</h1>
          <p className="text-gray-600 mb-4">
            Enter the target you want to investigate:
          </p>

          <input
            type="text"
            placeholder={
              investigationType === 'domain' || investigationType === 'url' ? 'example.com' :
              investigationType === 'ip' ? '192.168.1.1' :
              investigationType === 'email' ? 'user@example.com' :
              'Enter target'
            }
            value={target}
            onChange={handleTargetChange}
            className="w-full p-3 border rounded-lg mb-2"
          />
          {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

          <button
            type="button"
            onClick={handleStartInvestigation}
            disabled={!isValid || isLoading}
            className={`w-full p-3 rounded-lg transition-colors font-medium ${
              isValid && !isLoading
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {isLoading ? 'Running checks…' : 'Start Passive Check'}
          </button>

          <p className="text-xs text-gray-500 mt-4 text-center">
            <strong>Ethical Use Notice:</strong> This tool only uses passive, public, permission-based checks.
            It does not attack, scan, exploit, bypass access controls, or access private systems.
          </p>
        </div>
      ) : (
        <Dashboard
          results={results}
          investigationType={investigationType}
          target={target}
          onBack={handleBack}
        />
      )}
    </div>
  );
};

export default OSINTApp;
