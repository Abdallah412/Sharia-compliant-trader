import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, ChevronDown, ChevronUp, BookOpen, AlertTriangle } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import ComplianceBadge from '../components/ComplianceBadge';

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.25 } },
};

const STATUS_ORDER = { HARAM: 0, DOUBTFUL: 1, HALAL: 2 };
const PIE_COLORS = { HALAL: '#22C55E', DOUBTFUL: '#D97706', HARAM: '#DC2626' };

async function fetchJSON(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function RatioBar({ value, max = 100, thresholds = [33, 66] }) {
  const pct = Math.min((value / max) * 100, 100);
  let color = 'bg-gain';
  if (value > thresholds[1]) color = 'bg-loss';
  else if (value > thresholds[0]) color = 'bg-doubtful';

  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-bg-elevated rounded-full overflow-hidden border border-border-main">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-text-muted">{value?.toFixed(1)}%</span>
    </div>
  );
}

function CustomPieLabel({ viewBox, total }) {
  const { cx, cy } = viewBox;
  return (
    <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central">
      <tspan x={cx} dy="-0.4em" className="fill-text-primary text-2xl font-bold font-mono">
        {total}
      </tspan>
      <tspan x={cx} dy="1.4em" className="fill-text-muted text-xs">
        Holdings
      </tspan>
    </text>
  );
}

export default function Compliance() {
  const [holdings, setHoldings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedRow, setExpandedRow] = useState(null);
  const [rescreenDays, setRescreenDays] = useState(null);

  useEffect(() => {
    (async () => {
      const data = await fetchJSON('/api/holdings');
      if (data) {
        const list = Array.isArray(data) ? data : data.holdings || [];
        setHoldings(list);
      }
      const status = await fetchJSON('/api/status');
      if (status?.rescreen_days != null) {
        setRescreenDays(status.rescreen_days);
      }
      setLoading(false);
    })();
  }, []);

  // Sort by compliance risk
  const sortedHoldings = [...holdings].sort((a, b) => {
    const aKey = (a.halal_status || a.compliance_status || '').toUpperCase();
    const bKey = (b.halal_status || b.compliance_status || '').toUpperCase();
    return (STATUS_ORDER[aKey] ?? 3) - (STATUS_ORDER[bKey] ?? 3);
  });

  // Counts
  const counts = { HALAL: 0, DOUBTFUL: 0, HARAM: 0 };
  holdings.forEach((h) => {
    const status = (h.halal_status || h.compliance_status || '').toUpperCase();
    if (status === 'HALAL' || status === 'COMPLIANT') counts.HALAL++;
    else if (status === 'DOUBTFUL' || status === 'REVIEW') counts.DOUBTFUL++;
    else if (status === 'HARAM' || status === 'NON_COMPLIANT') counts.HARAM++;
  });
  const total = holdings.length;

  const pieData = [
    { name: 'HALAL', value: counts.HALAL },
    { name: 'DOUBTFUL', value: counts.DOUBTFUL },
    { name: 'HARAM', value: counts.HARAM },
  ].filter((d) => d.value > 0);

  // Collect all scholarly notes
  const allNotes = sortedHoldings
    .filter((h) => h.scholarly_notes && h.scholarly_notes.length > 0)
    .flatMap((h) =>
      (Array.isArray(h.scholarly_notes) ? h.scholarly_notes : [h.scholarly_notes]).map((note) => ({
        ticker: h.ticker,
        status: (h.halal_status || h.compliance_status || '').toUpperCase(),
        note: typeof note === 'string' ? note : note.text || note.note || '',
        madhab: typeof note === 'object' ? note.madhab : null,
        severity: typeof note === 'object' ? note.severity : null,
      }))
    );

  // Rescreen progress
  const rescreenTotal = 90; // quarterly = ~90 days
  const rescreenProgress = rescreenDays != null
    ? Math.min(((rescreenTotal - rescreenDays) / rescreenTotal) * 100, 100)
    : 0;

  if (loading) {
    return (
      <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit"
        className="min-h-screen bg-bg-base p-6 flex items-center justify-center">
        <p className="text-text-muted">Loading compliance data...</p>
      </motion.div>
    );
  }

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit"
      className="min-h-screen bg-bg-base p-6 space-y-6 max-w-7xl mx-auto">

      {/* Header */}
      <div className="flex items-center gap-3">
        <Shield size={28} className="text-brand-teal" />
        <h1 className="font-display text-2xl font-bold text-text-primary">Shariah Compliance Status</h1>
      </div>

      {/* Top Section — Compliance Summary */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.4 }}
        className="bg-bg-card rounded-lg p-6 border border-border-main"
      >
        <div className="flex flex-col md:flex-row items-center gap-8">
          {/* Pie Chart */}
          <div className="w-56 h-56 flex-shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={2}
                  strokeWidth={0}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={PIE_COLORS[entry.name]} />
                  ))}
                </Pie>
                {/* Center label */}
                <Pie
                  data={[{ value: 1 }]}
                  dataKey="value"
                  cx="50%"
                  cy="50%"
                  innerRadius={0}
                  outerRadius={0}
                  fill="none"
                  label={({ viewBox }) => <CustomPieLabel viewBox={viewBox} total={total} />}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Summary Stats */}
          <div className="flex-1 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-halal" />
              <span className="text-text-primary">
                <span className="font-mono font-bold">{counts.HALAL}</span> of{' '}
                <span className="font-mono font-bold">{total}</span> holdings are{' '}
                <span className="text-halal font-semibold">HALAL</span>
              </span>
            </div>
            {counts.DOUBTFUL > 0 && (
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-doubtful" />
                <span className="text-text-primary">
                  <span className="font-mono font-bold">{counts.DOUBTFUL}</span> holdings are{' '}
                  <span className="text-doubtful font-semibold">DOUBTFUL</span>
                </span>
              </div>
            )}
            {counts.HARAM > 0 && (
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-haram" />
                <span className="text-text-primary">
                  <span className="font-mono font-bold">{counts.HARAM}</span> holdings are{' '}
                  <span className="text-haram font-semibold">HARAM</span>
                </span>
              </div>
            )}

            {/* Quarterly re-screen */}
            {rescreenDays != null && (
              <div className="mt-4 pt-4 border-t border-border-main">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-text-muted text-sm">Quarterly re-screen in {rescreenDays} days</span>
                  <span className="font-mono text-xs text-text-muted">
                    {Math.round(rescreenProgress)}%
                  </span>
                </div>
                <div className="w-full h-2 bg-bg-elevated rounded-full overflow-hidden border border-border-main">
                  <div
                    className="h-full bg-brand-teal rounded-full transition-all duration-500"
                    style={{ width: `${rescreenProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Middle — Holdings Compliance Table */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.4 }}
        className="bg-bg-card rounded-lg p-4 border border-border-main"
      >
        <h2 className="text-text-primary text-lg font-semibold mb-4">Holdings Compliance</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-text-muted text-xs uppercase tracking-wider border-b border-border-main">
                <th className="text-left py-3 px-2">Ticker</th>
                <th className="text-left py-3 px-2">Name</th>
                <th className="text-left py-3 px-2">Sector</th>
                <th className="text-center py-3 px-2">Halal Status</th>
                <th className="text-center py-3 px-2">Debt Ratio</th>
                <th className="text-center py-3 px-2">Cash Ratio</th>
                <th className="text-right py-3 px-2">Purification %</th>
                <th className="text-left py-3 px-2">Notes</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {sortedHoldings.map((h) => {
                const status = (h.halal_status || h.compliance_status || '').toUpperCase();
                const isHaram = status === 'HARAM' || status === 'NON_COMPLIANT';
                const isExpanded = expandedRow === h.ticker;
                const notes = h.scholarly_notes
                  ? Array.isArray(h.scholarly_notes) ? h.scholarly_notes : [h.scholarly_notes]
                  : [];
                const hasNotes = notes.length > 0;

                return (
                  <motion.tr
                    key={h.ticker}
                    layout
                    className={`border-b border-border-main/50 transition-colors cursor-pointer ${
                      isHaram ? 'bg-haram/10' : 'hover:bg-bg-elevated/50'
                    }`}
                    onClick={() => setExpandedRow(isExpanded ? null : h.ticker)}
                  >
                    <td className="py-3 px-2 font-mono font-semibold text-text-primary">{h.ticker}</td>
                    <td className="py-3 px-2 text-text-primary">{h.name || h.ticker}</td>
                    <td className="py-3 px-2 text-text-muted">{h.sector || '—'}</td>
                    <td className="py-3 px-2 text-center">
                      <ComplianceBadge status={status} size="sm" />
                    </td>
                    <td className="py-3 px-2">
                      <RatioBar value={h.debt_ratio ?? 0} />
                    </td>
                    <td className="py-3 px-2">
                      <RatioBar value={h.cash_ratio ?? 0} />
                    </td>
                    <td className="py-3 px-2 font-mono text-right text-text-primary">
                      {h.purification_pct != null ? `${h.purification_pct.toFixed(2)}%` : '—'}
                    </td>
                    <td className="py-3 px-2 text-text-muted text-xs max-w-[200px] truncate">
                      {hasNotes
                        ? typeof notes[0] === 'string'
                          ? notes[0]
                          : notes[0].text || notes[0].note || ''
                        : '—'}
                    </td>
                    <td className="py-3 px-2 text-text-muted">
                      {hasNotes && (isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                    </td>
                  </motion.tr>
                );
              })}

              {/* Expanded row detail — rendered separately to avoid nesting issues */}
              {sortedHoldings.map((h) => {
                const isExpanded = expandedRow === h.ticker;
                const notes = h.scholarly_notes
                  ? Array.isArray(h.scholarly_notes) ? h.scholarly_notes : [h.scholarly_notes]
                  : [];
                if (!isExpanded || notes.length === 0) return null;

                return (
                  <tr key={`${h.ticker}-expanded`}>
                    <td colSpan={9} className="p-0">
                      <AnimatePresence>
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.25 }}
                          className="bg-bg-elevated border-l-4 border-brand-teal px-4 py-3 overflow-hidden"
                        >
                          <p className="text-text-muted text-xs uppercase tracking-wider mb-2">
                            Sheikh Agent Notes
                          </p>
                          {notes.map((note, i) => (
                            <p key={i} className="text-text-primary text-sm mb-1">
                              {typeof note === 'string' ? note : note.text || note.note || JSON.stringify(note)}
                            </p>
                          ))}
                        </motion.div>
                      </AnimatePresence>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Bottom — Sheikh Agent Notes Panel */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.4 }}
        className="bg-bg-card rounded-lg p-4 border border-border-main"
      >
        <div className="flex items-center gap-2 mb-4">
          <BookOpen size={20} className="text-brand-teal" />
          <h2 className="text-text-primary text-lg font-semibold">Sheikh Agent Notes</h2>
        </div>

        {allNotes.length === 0 ? (
          <p className="text-text-muted py-4 text-center">
            All holdings are free of scholarly concerns.
          </p>
        ) : (
          <div className="max-h-96 overflow-y-auto space-y-3 pr-2">
            {allNotes.map((item, i) => {
              const severityColor =
                item.severity === 'high' || item.status === 'HARAM'
                  ? 'border-l-loss'
                  : item.severity === 'medium' || item.status === 'DOUBTFUL'
                    ? 'border-l-doubtful'
                    : 'border-l-brand-teal';

              return (
                <div
                  key={i}
                  className={`bg-bg-elevated rounded-lg p-3 border border-border-main border-l-4 ${severityColor}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-semibold bg-bg-card px-2 py-0.5 rounded text-text-primary border border-border-main">
                      {item.ticker}
                    </span>
                    {item.madhab && (
                      <span className="text-xs bg-brand-teal/20 text-brand-teal px-2 py-0.5 rounded">
                        {item.madhab}
                      </span>
                    )}
                    {item.severity && (
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        item.severity === 'high'
                          ? 'bg-loss/20 text-loss'
                          : item.severity === 'medium'
                            ? 'bg-doubtful/20 text-doubtful'
                            : 'bg-gain/20 text-gain'
                      }`}>
                        {item.severity}
                      </span>
                    )}
                  </div>
                  <p className="text-text-primary text-sm">{item.note}</p>
                </div>
              );
            })}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
