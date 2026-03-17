import { motion } from 'framer-motion';
import { Briefcase } from 'lucide-react';
import ComplianceBadge from './ComplianceBadge';

const ROW_VARIANT = {
  hidden: { opacity: 0, y: 6 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.05, duration: 0.3, ease: 'easeOut' },
  }),
};

function formatMoney(val) {
  return Number(val || 0).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function DaysHeldCell({ daysHeld }) {
  if (daysHeld == null) return <span className="text-text-dim">--</span>;

  const daysToLongTerm = 365 - daysHeld;
  if (daysToLongTerm > 0 && daysToLongTerm <= 30) {
    return (
      <span className="text-doubtful font-medium">
        {daysHeld}d
        <span className="block text-xs opacity-80">
          Hold {daysToLongTerm} more
        </span>
      </span>
    );
  }

  return <span>{daysHeld}</span>;
}

export default function HoldingsTable({ holdings, selectedTicker, onSelectTicker }) {
  if (!holdings || holdings.length === 0) {
    return (
      <div className="bg-bg-card border border-border-main rounded-lg p-8 flex flex-col items-center justify-center text-center">
        <Briefcase size={40} className="text-text-dim mb-3" />
        <p className="text-text-muted text-sm">
          No holdings yet. The bot will start buying soon.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-bg-card border border-border-main rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-[1]">
            <tr className="bg-bg-elevated text-text-muted text-xs uppercase tracking-wider">
              <th className="px-4 py-3 text-left font-semibold">Ticker</th>
              <th className="px-4 py-3 text-left font-semibold hidden sm:table-cell">Name</th>
              <th className="px-4 py-3 text-right font-semibold">Shares</th>
              <th className="px-4 py-3 text-right font-semibold">Price</th>
              <th className="px-4 py-3 text-right font-semibold hidden md:table-cell">Value</th>
              <th className="px-4 py-3 text-right font-semibold">Day P&L</th>
              <th className="px-4 py-3 text-right font-semibold hidden lg:table-cell">Total P&L</th>
              <th className="px-4 py-3 text-right font-semibold hidden lg:table-cell">Days</th>
              <th className="px-4 py-3 text-center font-semibold">Halal</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-main">
            {holdings.map((h, i) => {
              const isSelected = selectedTicker === h.ticker;
              const dayPnl = h.day_pnl ?? h.pnl ?? 0;
              const totalPnl = h.total_pnl ?? h.pnl ?? 0;

              return (
                <motion.tr
                  key={h.ticker}
                  custom={i}
                  initial="hidden"
                  animate="visible"
                  variants={ROW_VARIANT}
                  onClick={() => onSelectTicker?.(h.ticker)}
                  className={`cursor-pointer transition-colors hover:bg-bg-hover ${
                    isSelected
                      ? 'bg-bg-elevated border-l-2 border-brand-teal'
                      : 'border-l-2 border-transparent'
                  }`}
                >
                  <td className="px-4 py-3 font-mono font-bold text-text-primary hover:text-brand-gold transition-colors">
                    {h.ticker}
                  </td>
                  <td className="px-4 py-3 text-text-muted hidden sm:table-cell truncate max-w-[160px]">
                    {h.name || '--'}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">{h.shares}</td>
                  <td className="px-4 py-3 text-right font-mono">
                    ${formatMoney(h.price)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono hidden md:table-cell">
                    ${formatMoney(h.value)}
                  </td>
                  <td className={`px-4 py-3 text-right font-mono font-medium ${
                    dayPnl >= 0 ? 'text-gain' : 'text-loss'
                  }`}>
                    {dayPnl >= 0 ? '+' : ''}${formatMoney(dayPnl)}
                  </td>
                  <td className={`px-4 py-3 text-right font-mono font-medium hidden lg:table-cell ${
                    totalPnl >= 0 ? 'text-gain' : 'text-loss'
                  }`}>
                    {totalPnl >= 0 ? '+' : ''}${formatMoney(totalPnl)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-text-muted hidden lg:table-cell">
                    <DaysHeldCell daysHeld={h.days_held} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <ComplianceBadge status={h.halal_status} size="sm" />
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
