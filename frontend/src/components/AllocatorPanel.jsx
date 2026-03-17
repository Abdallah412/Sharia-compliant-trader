import { useState } from 'react';

const RISK_PROFILES = {
  conservative: '60% ETFs, 30% Stocks, 10% Cash',
  moderate: '40% ETFs, 50% Stocks, 10% Cash',
  aggressive: '20% ETFs, 70% Stocks, 10% Cash',
};

export default function AllocatorPanel() {
  const [amount, setAmount] = useState('');
  const [riskProfile, setRiskProfile] = useState('moderate');
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState(null);

  const handleAllocate = async () => {
    const numAmount = parseFloat(amount);
    if (!numAmount || numAmount <= 0) {
      setError('Please enter a valid dollar amount');
      return;
    }
    setLoading(true);
    setError(null);
    setPlan(null);

    try {
      const params = new URLSearchParams({
        amount: numAmount.toString(),
        risk_profile: riskProfile,
        use_ai: 'true',
      });
      const res = await fetch(`/api/allocate?${params}`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Allocation failed');
      }
      const data = await res.json();
      setPlan(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-xl font-bold text-navy mb-4">Portfolio Allocator</h2>
      <p className="text-gray-600 text-sm mb-4">
        Enter a dollar amount to get a Shariah-compliant allocation recommendation.
      </p>

      <div className="flex flex-wrap gap-4 items-end mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Investment Amount ($)
          </label>
          <input
            type="number"
            min="0"
            step="100"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="500"
            className="border border-gray-300 rounded px-3 py-2 w-40 focus:outline-none focus:ring-2 focus:ring-halal"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Risk Profile
          </label>
          <select
            value={riskProfile}
            onChange={(e) => setRiskProfile(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-halal"
          >
            {Object.entries(RISK_PROFILES).map(([key, desc]) => (
              <option key={key} value={key}>
                {key.charAt(0).toUpperCase() + key.slice(1)} — {desc}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleAllocate}
          disabled={loading}
          className="bg-halal text-white px-6 py-2 rounded font-semibold hover:bg-green-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Analyzing...' : 'Get Recommendation'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {plan && (
        <div className="mt-4">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="bg-gray-50 rounded p-3 text-center">
              <div className="text-xs text-gray-500">Total Amount</div>
              <div className="text-lg font-bold">${plan.total_amount?.toLocaleString()}</div>
            </div>
            <div className="bg-green-50 rounded p-3 text-center">
              <div className="text-xs text-gray-500">Invested</div>
              <div className="text-lg font-bold text-halal">
                ${plan.invested_amount?.toLocaleString()}
              </div>
            </div>
            <div className="bg-blue-50 rounded p-3 text-center">
              <div className="text-xs text-gray-500">Cash Reserve</div>
              <div className="text-lg font-bold text-blue-700">
                ${plan.cash_reserve?.toLocaleString()}
              </div>
            </div>
            <div className="bg-gray-50 rounded p-3 text-center">
              <div className="text-xs text-gray-500">Est. Dividend Yield</div>
              <div className="text-lg font-bold">
                {plan.expected_dividend_yield?.toFixed(2)}%
              </div>
            </div>
          </div>

          {/* Allocations Table */}
          {plan.allocations?.length > 0 && (
            <div className="overflow-x-auto mb-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-navy text-white">
                    <th className="px-3 py-2 text-left">Ticker</th>
                    <th className="px-3 py-2 text-left">Name</th>
                    <th className="px-3 py-2 text-left">Sector</th>
                    <th className="px-3 py-2 text-right">Shares</th>
                    <th className="px-3 py-2 text-right">Price</th>
                    <th className="px-3 py-2 text-right">Total</th>
                    <th className="px-3 py-2 text-right">%</th>
                    <th className="px-3 py-2 text-left">Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.allocations.map((a, i) => (
                    <tr key={i} className="border-b hover:bg-gray-50">
                      <td className="px-3 py-2 font-semibold">{a.ticker}</td>
                      <td className="px-3 py-2 text-gray-600 truncate max-w-[150px]">
                        {a.company_name}
                      </td>
                      <td className="px-3 py-2 text-gray-500">{a.sector}</td>
                      <td className="px-3 py-2 text-right">{a.shares}</td>
                      <td className="px-3 py-2 text-right">
                        ${a.price_per_share?.toFixed(2)}
                      </td>
                      <td className="px-3 py-2 text-right font-medium">
                        ${a.total_cost?.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-right">{a.portfolio_pct}%</td>
                      <td className="px-3 py-2 text-gray-500 text-xs">
                        {a.rationale}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Sector Breakdown */}
          {plan.sector_breakdown && Object.keys(plan.sector_breakdown).length > 0 && (
            <div className="mb-4">
              <h3 className="font-semibold text-sm mb-2">Sector Breakdown</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(plan.sector_breakdown)
                  .sort((a, b) => b[1] - a[1])
                  .map(([sector, pct]) => (
                    <span
                      key={sector}
                      className="bg-gray-100 rounded-full px-3 py-1 text-xs"
                    >
                      {sector}: {pct}%
                    </span>
                  ))}
              </div>
            </div>
          )}

          {/* Strategy Summary */}
          {plan.strategy_summary && (
            <div className="bg-green-50 border border-green-200 rounded p-3 mb-4 text-sm">
              <strong>Strategy:</strong> {plan.strategy_summary}
            </div>
          )}

          {/* Warnings */}
          {plan.warnings?.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded p-3 text-sm">
              <strong>Warnings:</strong>
              <ul className="list-disc list-inside mt-1">
                {plan.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
