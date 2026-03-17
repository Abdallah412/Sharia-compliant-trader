import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Moon,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  BookOpen,
  Plus,
} from 'lucide-react';
import ComplianceBadge from '../components/ComplianceBadge';
import Disclaimer from '../components/Disclaimer';

const SCREEN_NAMES = [
  'Business Activity Screening',
  'Interest Income Ratio',
  'Debt-to-Market-Cap Ratio',
  'Liquid Assets Ratio',
  'Receivables Ratio',
];

const STATUS_ICON = {
  PASS: { Icon: CheckCircle2, color: 'text-gain' },
  FAIL: { Icon: XCircle, color: 'text-loss' },
  REVIEW: { Icon: AlertTriangle, color: 'text-doubtful' },
};

function getRatioBarColor(ratio) {
  if (ratio <= 20) return 'bg-gain';
  if (ratio <= 28) return 'bg-doubtful';
  return 'bg-loss';
}

function RatioBar({ ratio }) {
  const pct = Math.min(ratio, 40);
  const barWidth = (pct / 40) * 100;
  const thresholdPos = (30 / 40) * 100;

  return (
    <div className="relative mt-2 mb-1">
      <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${getRatioBarColor(ratio)}`}
          initial={{ width: 0 }}
          animate={{ width: `${barWidth}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
      {/* Threshold line at 30% */}
      <div
        className="absolute top-0 h-2 w-0.5 bg-text-primary/50"
        style={{ left: `${thresholdPos}%` }}
      />
      <div className="flex justify-between mt-1">
        <span className="text-[10px] text-text-muted font-mono">{ratio.toFixed(1)}%</span>
        <span className="text-[10px] text-text-muted font-mono">Threshold: 30%</span>
      </div>
    </div>
  );
}

function ScreenResult({ screen, index, isRatioScreen }) {
  const statusConfig = STATUS_ICON[screen.status] || STATUS_ICON.REVIEW;
  const { Icon, color } = statusConfig;

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.15, duration: 0.3, ease: 'easeOut' }}
      className="border-b border-border-main/50 py-4 last:border-b-0"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p className="text-text-muted uppercase text-xs tracking-wider font-semibold mb-1">
            {screen.name}
          </p>
          <p className="text-text-primary text-sm">{screen.description}</p>
          {isRatioScreen && screen.ratio != null && (
            <RatioBar ratio={screen.ratio} />
          )}
        </div>
        <div className={`flex items-center gap-1.5 shrink-0 ${color}`}>
          <Icon size={18} />
          <span className="text-xs font-semibold uppercase">{screen.status}</span>
        </div>
      </div>
    </motion.div>
  );
}

function PulsingMoon() {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
      >
        <Moon size={40} className="text-brand-gold" />
      </motion.div>
      <p className="text-text-muted text-sm">Running Shariah compliance screen...</p>
    </div>
  );
}

export default function Screener() {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [addedToWatchlist, setAddedToWatchlist] = useState(false);

  const runScreen = useCallback(async () => {
    if (!ticker.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    setAddedToWatchlist(false);

    try {
      const res = await fetch(`/api/compliance/${ticker.trim().toUpperCase()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setResult(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') runScreen();
  };

  const handleAddToWatchlist = async () => {
    if (!result) return;
    try {
      await fetch('/api/watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: result.ticker || ticker.toUpperCase() }),
      });
      setAddedToWatchlist(true);
    } catch {
      // silently fail
    }
  };

  // Normalize result data
  const screens = result?.screens || result?.results || [];
  const normalizedScreens = screens.map((s, i) => ({
    name: s.name || SCREEN_NAMES[i] || `Screen ${i + 1}`,
    status: (s.status || s.result || 'REVIEW').toUpperCase(),
    description: s.description || s.detail || s.reason || '',
    ratio: s.ratio ?? s.value ?? null,
  }));

  const complianceStatus = result?.status || result?.overall_status || result?.compliance_status || null;
  const companyName = result?.company_name || result?.name || '';
  const resultTicker = result?.ticker || result?.symbol || ticker.toUpperCase();
  const scholarlyNotes = result?.scholarly_notes || result?.notes || result?.scholarly_opinion || null;
  const source = result?.source || result?.data_source || null;
  const lastChecked = result?.last_checked || result?.updated_at || result?.date || null;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Shariah Compliance Screener
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Screen stocks against AAOIFI Shariah standards
        </p>
      </div>

      {/* Search Bar */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            onKeyDown={handleKeyDown}
            placeholder="Enter ticker symbol (e.g., NVDA)"
            className="w-full bg-bg-elevated border border-border-main rounded-lg pl-10 pr-4 py-2.5 text-text-primary font-mono text-sm placeholder:text-text-muted/60 focus:outline-none focus:border-brand-teal transition"
          />
        </div>
        <button
          onClick={runScreen}
          disabled={!ticker.trim() || loading}
          className="bg-brand-teal hover:bg-brand-teal-light text-white font-semibold px-5 py-2.5 rounded-lg transition disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
        >
          Run Shariah Screen
        </button>
      </div>

      {/* Loading State */}
      {loading && <PulsingMoon />}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-loss/10 border border-loss/30 rounded-lg p-4 text-loss text-sm">
          Failed to fetch compliance data: {error}
        </div>
      )}

      {/* Results */}
      <AnimatePresence>
        {result && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.3 }}
            className="bg-bg-card border border-border-main rounded-lg p-6"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-display font-bold text-text-primary">
                  {resultTicker}
                </h2>
                {companyName && (
                  <span className="text-text-muted text-sm">{companyName}</span>
                )}
              </div>
              <ComplianceBadge status={complianceStatus} size="lg" />
            </div>

            {/* Screen Results */}
            <div className="divide-y divide-border-main/50">
              {normalizedScreens.map((screen, i) => (
                <ScreenResult
                  key={i}
                  screen={screen}
                  index={i}
                  isRatioScreen={i === 2 || i === 3}
                />
              ))}
            </div>

            {/* If no screens returned, show overall status */}
            {normalizedScreens.length === 0 && (
              <p className="text-text-muted text-sm py-4">
                No detailed screen results available. Overall status: {complianceStatus || 'N/A'}
              </p>
            )}

            {/* Scholarly Notes */}
            {scholarlyNotes && (
              <div className="bg-bg-elevated rounded-lg p-3 mt-5">
                <div className="flex items-center gap-2 mb-2">
                  <BookOpen size={14} className="text-brand-gold" />
                  <span className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                    Scholarly Notes
                  </span>
                </div>
                <p className="text-text-muted text-sm leading-relaxed">
                  {scholarlyNotes}
                </p>
              </div>
            )}

            {/* Source + Date + Add to Watchlist */}
            <div className="flex items-center justify-between mt-5 pt-4 border-t border-border-main/50">
              <div className="text-text-muted text-xs space-y-0.5">
                {source && <p>Source: {source}</p>}
                {lastChecked && <p>Last checked: {lastChecked}</p>}
              </div>
              <button
                onClick={handleAddToWatchlist}
                disabled={addedToWatchlist}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg border text-sm font-medium transition ${
                  addedToWatchlist
                    ? 'border-gain/30 text-gain cursor-default'
                    : 'border-border-main text-text-primary hover:border-brand-teal hover:text-brand-teal-light'
                }`}
              >
                {addedToWatchlist ? (
                  <>
                    <CheckCircle2 size={14} />
                    Added
                  </>
                ) : (
                  <>
                    <Plus size={14} />
                    Add to Watchlist
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <Disclaimer />
    </div>
  );
}
