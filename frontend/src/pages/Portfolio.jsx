import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  X,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Banknote,
  PiggyBank,
  ShoppingCart,
} from 'lucide-react';

import KPICard from '../components/KPICard';
import HoldingsTable from '../components/HoldingsTable';
import EMAChart from '../components/EMAChart';
import ComplianceBadge from '../components/ComplianceBadge';
import AllocatorPanel from '../components/AllocatorPanel';
import { usePortfolio } from '../hooks/usePortfolio';
import { useApi } from '../hooks/useApi';
import { formatCurrency, formatPct, pnlColor } from '../utils/formatCurrency';
import Disclaimer from '../components/Disclaimer';

// ── Page transition ──────────────────────────────────────────────────
const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.45, ease: 'easeOut' } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.2 } },
};

// ── Drawer animation ─────────────────────────────────────────────────
const drawerVariants = {
  hidden: { x: '100%', opacity: 0 },
  visible: { x: 0, opacity: 1, transition: { type: 'spring', damping: 26, stiffness: 260 } },
  exit: { x: '100%', opacity: 0, transition: { duration: 0.2 } },
};

// ── Teal shades for pie chart segments ───────────────────────────────
const TEAL_SHADES = [
  '#0D7377',
  '#14A085',
  '#0B5E61',
  '#18B89B',
  '#097A7E',
  '#1CC4A6',
  '#064E52',
  '#20D0B0',
  '#0A6669',
  '#25DCBA',
  '#C9A84C',
  '#B8963F',
  '#A78432',
];

// ── Custom pie chart center label ────────────────────────────────────
function CenterLabel({ viewBox, value }) {
  const { cx, cy } = viewBox;
  return (
    <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central">
      <tspan x={cx} dy="-8" className="fill-text-muted" fontSize="12">
        Total Value
      </tspan>
      <tspan x={cx} dy="22" className="fill-text-primary" fontSize="18" fontWeight="bold">
        {formatCurrency(value)}
      </tspan>
    </text>
  );
}

// ── Pie chart tooltip ────────────────────────────────────────────────
function PieTooltipContent({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-bg-elevated border border-border-main rounded-lg px-3 py-2 shadow-lg">
      <p className="font-mono text-sm font-bold text-text-primary">{d.name}</p>
      <p className="text-text-muted text-xs mt-0.5">
        {formatCurrency(d.value)} ({d.payload.pct}%)
      </p>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════
// Portfolio Page
// ═════════════════════════════════════════════════════════════════════
export default function Portfolio() {
  const { portfolio, holdings, loading } = usePortfolio();
  const [selectedTicker, setSelectedTicker] = useState(null);

  // Compute allocation data for pie chart
  const allocationData = useMemo(() => {
    if (!holdings || holdings.length === 0) return [];
    const totalHoldingValue = holdings.reduce((s, h) => s + (h.value || 0), 0);
    return holdings
      .filter((h) => (h.value || 0) > 0)
      .sort((a, b) => (b.value || 0) - (a.value || 0))
      .map((h) => ({
        name: h.ticker,
        value: h.value || 0,
        pct: totalHoldingValue > 0
          ? ((h.value / totalHoldingValue) * 100).toFixed(1)
          : '0.0',
      }));
  }, [holdings]);

  // Portfolio stats
  const totalValue = portfolio?.total_value ?? 0;
  const invested = portfolio?.invested ?? portfolio?.cost_basis ?? 0;
  const cash = portfolio?.cash ?? 0;
  const unrealizedPnl = portfolio?.unrealized_pnl ?? (totalValue - invested - cash);

  // Selected holding data
  const selectedHolding = useMemo(() => {
    if (!selectedTicker || !holdings) return null;
    return holdings.find((h) => h.ticker === selectedTicker) || null;
  }, [selectedTicker, holdings]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-brand-teal border-t-transparent" />
      </div>
    );
  }

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="relative"
    >
      <div className={`space-y-6 transition-all duration-300 ${selectedTicker ? 'mr-[25rem]' : ''}`}>
        {/* ── Top: Pie Chart + Summary Stats ──────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Pie Chart (60%) */}
          <div className="lg:col-span-3 bg-bg-card border border-border-main rounded-lg p-4">
            <h2 className="font-display text-lg text-text-primary mb-4">
              Portfolio Allocation
            </h2>
            {allocationData.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <PieChart>
                  <Pie
                    data={allocationData}
                    cx="50%"
                    cy="45%"
                    innerRadius={80}
                    outerRadius={120}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  >
                    {allocationData.map((_, i) => (
                      <Cell
                        key={i}
                        fill={TEAL_SHADES[i % TEAL_SHADES.length]}
                      />
                    ))}
                    <CenterLabel value={totalValue} />
                  </Pie>
                  <Tooltip content={<PieTooltipContent />} />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    formatter={(value) => (
                      <span className="text-text-muted text-xs font-mono">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[320px] text-text-dim text-sm">
                No holdings to display
              </div>
            )}
          </div>

          {/* Summary Stats (40%) */}
          <div className="lg:col-span-2 flex flex-col gap-3">
            <StatRow
              label="Total Value"
              value={formatCurrency(totalValue)}
              icon={DollarSign}
              color="text-text-primary"
            />
            <StatRow
              label="Invested"
              value={formatCurrency(invested)}
              icon={PiggyBank}
              color="text-text-primary"
            />
            <StatRow
              label="Cash"
              value={formatCurrency(cash)}
              icon={Banknote}
              color="text-brand-gold"
            />
            <StatRow
              label="Unrealized P&L"
              value={formatCurrency(unrealizedPnl)}
              icon={unrealizedPnl >= 0 ? TrendingUp : TrendingDown}
              color={unrealizedPnl >= 0 ? 'text-gain' : 'text-loss'}
              sub={
                invested > 0
                  ? formatPct((unrealizedPnl / invested) * 100)
                  : undefined
              }
            />
          </div>
        </div>

        {/* ── Middle: Full Holdings Table ─────────────────────────── */}
        <div>
          <HoldingsTable
            holdings={holdings}
            selectedTicker={selectedTicker}
            onSelectTicker={setSelectedTicker}
          />
        </div>

        {/* ── Bottom: Allocator Panel ────────────────────────────── */}
        <AllocatorPanel />
      </div>

      {/* ── Right Drawer: Stock Detail ───────────────────────────── */}
      <AnimatePresence>
        {selectedTicker && (
          <motion.div
            key="stock-drawer"
            variants={drawerVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed top-0 right-0 h-full w-96 bg-bg-card border-l border-border-main
                       shadow-2xl z-40 overflow-y-auto"
          >
            {/* Close button */}
            <div className="sticky top-0 bg-bg-card/95 backdrop-blur-sm border-b border-border-main px-4 py-3 flex items-center justify-between z-10">
              <h3 className="font-display text-lg text-text-primary">
                {selectedTicker}
              </h3>
              <button
                onClick={() => setSelectedTicker(null)}
                className="text-text-muted hover:text-text-primary transition-colors p-1 rounded-md hover:bg-bg-hover"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-4 space-y-5">
              {/* EMA Chart */}
              <div>
                <h4 className="text-sm text-text-muted mb-2 uppercase tracking-wider">
                  Price Chart
                </h4>
                <EMAChart ticker={selectedTicker} height={240} />
              </div>

              {/* Compliance Info */}
              {selectedHolding && (
                <div>
                  <h4 className="text-sm text-text-muted mb-2 uppercase tracking-wider">
                    Compliance
                  </h4>
                  <div className="bg-bg-elevated rounded-lg p-3 flex items-center justify-between">
                    <span className="text-text-primary text-sm">Status</span>
                    <ComplianceBadge
                      status={selectedHolding.halal_status}
                      size="md"
                    />
                  </div>
                </div>
              )}

              {/* Holding details */}
              {selectedHolding && (
                <div>
                  <h4 className="text-sm text-text-muted mb-2 uppercase tracking-wider">
                    Position
                  </h4>
                  <div className="bg-bg-elevated rounded-lg p-3 space-y-2">
                    <DetailRow label="Shares" value={selectedHolding.shares} />
                    <DetailRow label="Avg Price" value={`$${Number(selectedHolding.avg_cost || selectedHolding.price || 0).toFixed(2)}`} />
                    <DetailRow label="Current" value={`$${Number(selectedHolding.price || 0).toFixed(2)}`} />
                    <DetailRow label="Value" value={formatCurrency(selectedHolding.value || 0)} />
                    <DetailRow
                      label="P&L"
                      value={formatCurrency(selectedHolding.pnl || 0)}
                      valueClass={pnlColor(selectedHolding.pnl || 0)}
                    />
                  </div>
                </div>
              )}

              {/* Buy / Sell buttons */}
              <div className="flex gap-3">
                <button className="flex-1 flex items-center justify-center gap-2 bg-gain/15 text-gain border border-gain/30
                                   rounded-lg py-2.5 font-mono text-sm font-semibold
                                   hover:bg-gain/25 transition-colors">
                  <ShoppingCart size={16} />
                  Buy
                </button>
                <button className="flex-1 flex items-center justify-center gap-2 bg-loss/15 text-loss border border-loss/30
                                   rounded-lg py-2.5 font-mono text-sm font-semibold
                                   hover:bg-loss/25 transition-colors">
                  <TrendingDown size={16} />
                  Sell
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <Disclaimer />
    </motion.div>
  );
}

// ── Stat Row (for portfolio summary panel) ───────────────────────────
function StatRow({ label, value, icon: Icon, color, sub }) {
  return (
    <div className="bg-bg-card border border-border-main rounded-lg px-4 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="text-text-dim">
          <Icon size={18} />
        </div>
        <span className="text-text-muted text-sm">{label}</span>
      </div>
      <div className="text-right">
        <span className={`font-mono text-base font-bold ${color}`}>{value}</span>
        {sub && (
          <span className={`block text-xs font-mono ${color} opacity-75`}>{sub}</span>
        )}
      </div>
    </div>
  );
}

// ── Detail Row (for stock drawer) ────────────────────────────────────
function DetailRow({ label, value, valueClass = 'text-text-primary' }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-text-muted">{label}</span>
      <span className={`font-mono font-semibold ${valueClass}`}>{value}</span>
    </div>
  );
}
