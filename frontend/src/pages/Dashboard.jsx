import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { DollarSign, TrendingUp, Percent, Wallet, Activity } from 'lucide-react';
import { useState } from 'react';

import KPICard from '../components/KPICard';
import HoldingsTable from '../components/HoldingsTable';
import AgentDecisionCard from '../components/AgentDecisionCard';
import { usePortfolio } from '../hooks/usePortfolio';
import { formatCurrency, formatPct, pnlColor } from '../utils/formatCurrency';

// ── Page transition wrapper ──────────────────────────────────────────
const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.45, ease: 'easeOut' } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.2 } },
};

// ── Chart tooltip ────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-bg-elevated border border-border-main rounded-lg px-3 py-2 shadow-lg">
      <p className="text-text-muted text-xs mb-1">{label}</p>
      <p className="font-mono text-sm text-brand-teal">
        {formatCurrency(payload[0].value)}
      </p>
    </div>
  );
}

// ── Time range filter ────────────────────────────────────────────────
const TIME_RANGES = ['7D', '30D', '90D', 'ALL'];

function filterByRange(data, range) {
  if (!data || data.length === 0) return [];
  if (range === 'ALL') return data;

  const days = range === '7D' ? 7 : range === '30D' ? 30 : 90;
  return data.slice(-days);
}

// ── Generate sample chart data (used when API provides none) ─────────
function generateChartData(portfolio) {
  if (!portfolio) return [];
  const baseValue = portfolio.total_value || 10000;
  const points = [];
  const now = new Date();
  for (let i = 89; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const drift = (90 - i) * 0.001;
    const noise = (Math.random() - 0.48) * 0.015;
    const value = baseValue * (1 + drift + noise * (90 - i));
    points.push({
      date: `${d.getMonth() + 1}/${d.getDate()}`,
      value: Math.round(value * 100) / 100,
    });
  }
  return points;
}

// ═════════════════════════════════════════════════════════════════════
// Dashboard Page
// ═════════════════════════════════════════════════════════════════════
export default function Dashboard() {
  const { portfolio, holdings, decisions, loading } = usePortfolio();
  const [timeRange, setTimeRange] = useState('30D');

  // KPI values
  const totalValue = portfolio?.total_value ?? 0;
  const dayPnl = portfolio?.day_pnl ?? 0;
  const dayPnlPct = portfolio?.day_pnl_pct ?? 0;
  const totalReturnPct = portfolio?.total_return_pct ?? 0;
  const cash = portfolio?.cash ?? 0;

  // Chart data
  const chartData = useMemo(() => {
    const raw = portfolio?.history || portfolio?.chart || [];
    const data = raw.length > 0 ? raw : generateChartData(portfolio);
    return filterByRange(data, timeRange);
  }, [portfolio, timeRange]);

  // Top 5 holdings
  const topHoldings = useMemo(() => {
    return [...(holdings || [])]
      .sort((a, b) => (b.value || 0) - (a.value || 0))
      .slice(0, 5);
  }, [holdings]);

  // Last 10 decisions
  const recentDecisions = useMemo(() => {
    return (decisions || []).slice(0, 10);
  }, [decisions]);

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
      className="space-y-6"
    >
      {/* ── Row 1: KPI Cards ─────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Portfolio Value"
          value={formatCurrency(totalValue)}
          icon={DollarSign}
          delay={0}
        />
        <KPICard
          title="Today's P&L"
          value={formatCurrency(dayPnl)}
          change={formatCurrency(dayPnl)}
          changePct={dayPnlPct.toFixed(2)}
          positive={dayPnl >= 0}
          icon={TrendingUp}
          delay={0.1}
        />
        <KPICard
          title="Total Return"
          value={formatPct(totalReturnPct)}
          positive={totalReturnPct >= 0}
          icon={Percent}
          delay={0.2}
        />
        <KPICard
          title="Cash Available"
          value={formatCurrency(cash)}
          icon={Wallet}
          delay={0.3}
        />
      </div>

      {/* ── Row 2: Chart + Agent Feed ────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Portfolio Performance Chart */}
        <div className="lg:col-span-3 bg-bg-card border border-border-main rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-lg text-text-primary">
              Portfolio Performance
            </h2>

            {/* Time range toggle pills */}
            <div className="flex bg-bg-elevated rounded-lg p-0.5">
              {TIME_RANGES.map((r) => (
                <button
                  key={r}
                  onClick={() => setTimeRange(r)}
                  className={`px-3 py-1 text-xs font-mono rounded-md transition-colors ${
                    timeRange === r
                      ? 'bg-brand-teal text-white'
                      : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="dashTealGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0D7377" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#0D7377" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#334155', fontSize: 11 }}
                  minTickGap={40}
                />
                <YAxis
                  domain={['auto', 'auto']}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#334155', fontSize: 11 }}
                  width={58}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#0D7377"
                  strokeWidth={2}
                  fill="url(#dashTealGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[260px] text-text-dim text-sm">
              No chart data available
            </div>
          )}
        </div>

        {/* Agent Activity Feed */}
        <div className="lg:col-span-2 bg-bg-card border border-border-main rounded-lg p-4 flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={18} className="text-brand-teal" />
            <h2 className="font-display text-lg text-text-primary">
              Agent Activity
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto max-h-[280px] space-y-2 scrollbar-thin">
            {recentDecisions.length === 0 ? (
              <div className="flex items-center justify-center h-full text-text-dim text-sm py-12">
                No agent activity yet. Bot will run at market open.
              </div>
            ) : (
              recentDecisions.map((d, i) => (
                <AgentDecisionCard key={d.id || i} decision={d} compact />
              ))
            )}
          </div>
        </div>
      </div>

      {/* ── Row 3: Holdings Table (compact) ──────────────────────── */}
      <div>
        <HoldingsTable
          holdings={topHoldings}
          onSelectTicker={() => {}}
        />
        {holdings && holdings.length > 5 && (
          <div className="mt-3 text-right">
            <Link
              to="/portfolio"
              className="text-brand-teal hover:text-brand-teal-light text-sm font-mono transition-colors"
            >
              View All Holdings &rarr;
            </Link>
          </div>
        )}
      </div>
    </motion.div>
  );
}
