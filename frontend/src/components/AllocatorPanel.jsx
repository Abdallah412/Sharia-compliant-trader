import { useState } from 'react';
import { Loader2 } from 'lucide-react';

const RISK_PROFILES = ['conservative', 'moderate', 'aggressive'];

function SummaryCard({ label, value, accent }) {
  return (
    <div className="bg-bg-elevated border border-border-main rounded-lg p-3 text-center">
      <div className="text-xs text-text-muted uppercase tracking-wider mb-1">{label}</div>
      <div className={`font-mono text-lg font-bold ${accent || 'text-text-primary'}`}>
        {value}
      </div>
    </div>
  );
}

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
    <div className="bg-bg-card border border-border-main rounded-lg p-6">
      <h2 className="font-display text-xl font-bold text-text-primary mb-1">
        Portfolio Allocator
      </h2>
      <p className="text-text-muted text-sm mb-5">
        Enter a dollar amount to get a Shariah-compliant allocation recommendation.
      </p>

      {/* Input row */}
      <div className="flex flex-wrap gap-4 items-end mb-5">
        <div>
          <label className="block text-sm text-text-muted mb-1.5">
            Investment Amount ($)
          </label>
          <input
            type="number"
            min="0"
            step="100"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="500"
            className="bg-bg-elevated border border-border-main rounded-lg px-3 py-2 w-40
                       text-text-primary font-mono placeholder:text-text-dim
                       focus:outline-none focus:border-brand-teal transition-colors"
          />
        </div>

        {/* Risk profile toggle group */}
        <div>
          <label className="block text-sm text-text-muted mb-1.5">
            Risk Profile
          </label>
          <div className="inline-flex rounded-lg border border-border-main overflow-hidden">
            {RISK_PROFILES.map((profile) => (
              <button
                key={profile}
                onClick={() => setRiskProfile(profile)}
                className={`px-3 py-2 text-sm font-medium capitalize transition-colors ${
                  riskProfile === profile
                    ? 'bg-brand-teal text-white'
                    : 'bg-bg-elevated text-text-muted hover:text-text-primary'
                }`}
              >
                {profile}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleAllocate}
          disabled={loading}
          className="bg-brand-teal hover:bg-brand-teal-light text-white px-6 py-2 rounded-lg
                     font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <Loader2 size={16} className="animate-spin" />
              Analyzing...
            </span>
          ) : (
            'Get Recommendation'
          )}
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center gap-3 py-8 text-text-muted">
          <Loader2 size={20} className="animate-spin text-brand-teal" />
          <span className="text-sm">Analyzing halal universe...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-loss/10 border border-loss/30 rounded-lg p-3 mb-4 text-loss text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {plan && !loading && (
        <div className="mt-4 space-y-4">
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <SummaryCard
              label="Total Amount"
              value={`$${plan.total_amount?.toLocaleString()}`}
            />
            <SummaryCard
              label="Invested"
              value={`$${plan.invested_amount?.toLocaleString()}`}
              accent="text-gain"
            />
            <SummaryCard
              label="Cash Reserve"
              value={`$${plan.cash_reserve?.toLocaleString()}`}
              accent="text-brand-teal-light"
            />
            <SummaryCard
              label="Est. Yield"
              value={`${plan.expected_dividend_yield?.toFixed(2)}%`}
            />
          </div>

          {/* Allocations table */}
          {plan.allocations?.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-border-main">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-bg-elevated text-text-muted text-xs uppercase tracking-wider">
                    <th className="px-3 py-2.5 text-left font-semibold">Ticker</th>
                    <th className="px-3 py-2.5 text-left font-semibold">Name</th>
                    <th className="px-3 py-2.5 text-left font-semibold">Sector</th>
                    <th className="px-3 py-2.5 text-right font-semibold">Shares</th>
                    <th className="px-3 py-2.5 text-right font-semibold">Price</th>
                    <th className="px-3 py-2.5 text-right font-semibold">Total</th>
                    <th className="px-3 py-2.5 text-right font-semibold">%</th>
                    <th className="px-3 py-2.5 text-left font-semibold">Rationale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-main">
                  {plan.allocations.map((a, i) => (
                    <tr key={i} className="hover:bg-bg-hover transition-colors">
                      <td className="px-3 py-2.5 font-mono font-bold text-brand-gold">
                        {a.ticker}
                      </td>
                      <td className="px-3 py-2.5 text-text-muted truncate max-w-[150px]">
                        {a.company_name}
                      </td>
                      <td className="px-3 py-2.5 text-text-dim">{a.sector}</td>
                      <td className="px-3 py-2.5 text-right font-mono">{a.shares}</td>
                      <td className="px-3 py-2.5 text-right font-mono">
                        ${a.price_per_share?.toFixed(2)}
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono font-medium text-text-primary">
                        ${a.total_cost?.toLocaleString()}
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono">{a.portfolio_pct}%</td>
                      <td className="px-3 py-2.5 text-text-dim text-xs max-w-[200px]">
                        {a.rationale}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Sector breakdown pills */}
          {plan.sector_breakdown && Object.keys(plan.sector_breakdown).length > 0 && (
            <div>
              <h3 className="text-text-muted text-xs uppercase tracking-wider font-semibold mb-2">
                Sector Breakdown
              </h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(plan.sector_breakdown)
                  .sort((a, b) => b[1] - a[1])
                  .map(([sector, pct]) => (
                    <span
                      key={sector}
                      className="bg-bg-elevated border border-border-main rounded-full px-3 py-1
                                 text-xs text-text-muted font-mono"
                    >
                      {sector}: <span className="text-text-primary">{pct}%</span>
                    </span>
                  ))}
              </div>
            </div>
          )}

          {/* Strategy */}
          {plan.strategy_summary && (
            <div className="bg-brand-teal/10 border border-brand-teal/30 rounded-lg p-3 text-sm text-brand-teal-light">
              <strong>Strategy:</strong> {plan.strategy_summary}
            </div>
          )}

          {/* Warnings */}
          {plan.warnings?.length > 0 && (
            <div className="bg-doubtful/10 border border-doubtful/30 rounded-lg p-3 text-sm text-doubtful">
              <strong>Warnings:</strong>
              <ul className="list-disc list-inside mt-1 space-y-0.5">
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
