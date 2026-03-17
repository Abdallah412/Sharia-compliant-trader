import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  DollarSign,
  Receipt,
  Percent,
  TrendingUp,
  Moon,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Coins,
} from 'lucide-react';
import KPICard from '../components/KPICard';
import { formatCurrency, formatPct } from '../utils/formatCurrency';
import Disclaimer from '../components/Disclaimer';

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.25 } },
};

async function fetchJSON(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function DaysToSaveCell({ holding }) {
  const { long_term, days_held, est_tax_now, est_tax_if_wait } = holding;
  const daysToLongTerm = 366 - days_held;
  const saving = est_tax_now - est_tax_if_wait;

  if (long_term) {
    return (
      <span className="text-gain flex items-center gap-1">
        <CheckCircle2 size={14} />
        Long-term rate
      </span>
    );
  }

  if (daysToLongTerm <= 30) {
    return (
      <span className="text-doubtful flex items-center gap-1">
        <AlertTriangle size={14} />
        Hold {daysToLongTerm} more days, save {formatCurrency(saving)}
      </span>
    );
  }

  return <span className="text-text-primary font-mono">{daysToLongTerm} days</span>;
}

export default function TaxCenter() {
  const [taxData, setTaxData] = useState(null);
  const [harvestConfirm, setHarvestConfirm] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const data = await fetchJSON('/api/tax');
      if (data) setTaxData(data);
      setLoading(false);
    })();
  }, []);

  const summary = taxData?.summary ?? {};
  const holdings = taxData?.holdings ?? [];
  const losses = taxData?.losses ?? [];
  const zakat = taxData?.zakat ?? {};

  // Zakat progress: days elapsed out of 354 lunar year days
  const lunarYearDays = 354;
  const zakatDaysElapsed = zakat.days_elapsed ?? 0;
  const zakatProgress = Math.min((zakatDaysElapsed / lunarYearDays) * 100, 100);

  const handleHarvest = (ticker) => {
    if (harvestConfirm === ticker) {
      // Confirmed — send request
      fetch(`/api/tax/harvest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker }),
      });
      setHarvestConfirm(null);
    } else {
      setHarvestConfirm(ticker);
    }
  };

  if (loading) {
    return (
      <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit"
        className="min-h-screen bg-bg-base p-6 flex items-center justify-center">
        <p className="text-text-muted">Loading tax data...</p>
      </motion.div>
    );
  }

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit"
      className="min-h-screen bg-bg-base p-6 space-y-6 max-w-7xl mx-auto">

      {/* Header KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="YTD Realized Gains"
          value={formatCurrency(summary.ytd_realized_gains)}
          icon={TrendingUp}
          delay={0}
        />
        <KPICard
          title="Est. Tax Liability"
          value={formatCurrency(summary.est_tax_liability)}
          icon={Receipt}
          delay={0.1}
        />
        <KPICard
          title="Effective Rate"
          value={formatPct(summary.effective_rate, false)}
          icon={Percent}
          delay={0.2}
        />
        <KPICard
          title="Net After-Tax Gain"
          value={formatCurrency(summary.net_after_tax_gain)}
          icon={DollarSign}
          delay={0.3}
          positive={summary.net_after_tax_gain > 0}
        />
      </div>

      {/* Panel 1 — Holdings Tax Status */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35, duration: 0.4 }}
        className="bg-bg-card rounded-lg p-4"
      >
        <h2 className="text-text-primary text-lg font-semibold mb-4 flex items-center gap-2">
          <Calendar size={20} className="text-brand-teal" />
          Holdings Tax Status
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-text-muted text-xs uppercase tracking-wider border-b border-border-main">
                <th className="text-left py-3 px-2">Ticker</th>
                <th className="text-left py-3 px-2">Purchase Date</th>
                <th className="text-right py-3 px-2">Days Held</th>
                <th className="text-center py-3 px-2">Long-Term?</th>
                <th className="text-right py-3 px-2">Est. Tax Now</th>
                <th className="text-right py-3 px-2">Est. Tax if Wait</th>
                <th className="text-left py-3 px-2">Days to Save</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h) => (
                <tr key={h.ticker} className="border-b border-border-main/50 hover:bg-bg-elevated/50 transition-colors">
                  <td className="py-3 px-2 font-mono font-semibold text-text-primary">{h.ticker}</td>
                  <td className="py-3 px-2 font-mono text-text-muted">{h.purchase_date}</td>
                  <td className="py-3 px-2 font-mono text-right text-text-primary">{h.days_held}</td>
                  <td className="py-3 px-2 text-center">
                    {h.long_term ? (
                      <span className="text-gain">Yes</span>
                    ) : (
                      <span className="text-text-muted">No</span>
                    )}
                  </td>
                  <td className="py-3 px-2 font-mono text-right text-text-primary">{formatCurrency(h.est_tax_now)}</td>
                  <td className="py-3 px-2 font-mono text-right text-text-primary">{formatCurrency(h.est_tax_if_wait)}</td>
                  <td className="py-3 px-2">
                    <DaysToSaveCell holding={h} />
                  </td>
                </tr>
              ))}
              {holdings.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-text-muted">No holdings data available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Panel 2 — Tax Loss Harvesting */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.4 }}
        className="bg-bg-card rounded-lg p-4"
      >
        <h2 className="text-text-primary text-lg font-semibold mb-4 flex items-center gap-2">
          <Receipt size={20} className="text-loss" />
          Tax Loss Harvesting
        </h2>
        {losses.length === 0 ? (
          <p className="text-text-muted py-6 text-center">
            No tax loss harvesting opportunities. All positions are profitable.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-muted text-xs uppercase tracking-wider border-b border-border-main">
                  <th className="text-left py-3 px-2">Ticker</th>
                  <th className="text-right py-3 px-2">Current Loss</th>
                  <th className="text-right py-3 px-2">Potential Tax Offset</th>
                  <th className="text-right py-3 px-2">Net Saving</th>
                  <th className="text-right py-3 px-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {losses.map((l) => (
                  <tr key={l.ticker} className="border-b border-border-main/50 hover:bg-bg-elevated/50 transition-colors">
                    <td className="py-3 px-2 font-mono font-semibold text-text-primary">{l.ticker}</td>
                    <td className="py-3 px-2 font-mono text-right text-loss">{formatCurrency(l.current_loss)}</td>
                    <td className="py-3 px-2 font-mono text-right text-text-primary">{formatCurrency(l.potential_tax_offset)}</td>
                    <td className="py-3 px-2 font-mono text-right text-gain">{formatCurrency(l.net_saving)}</td>
                    <td className="py-3 px-2 text-right">
                      <button
                        onClick={() => handleHarvest(l.ticker)}
                        className={`px-3 py-1.5 rounded border text-sm font-medium transition-colors ${
                          harvestConfirm === l.ticker
                            ? 'bg-loss text-white border-loss'
                            : 'border-loss text-loss hover:bg-loss/10'
                        }`}
                      >
                        {harvestConfirm === l.ticker ? 'Confirm Harvest' : 'Harvest Loss'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>

      {/* Panel 3 — Zakat Calculator */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.55, duration: 0.4 }}
        className="bg-bg-card rounded-lg p-4"
      >
        <div className="flex items-center gap-3 mb-6">
          <Moon size={24} className="text-brand-gold" />
          <h2 className="font-display text-lg font-semibold text-brand-gold uppercase tracking-wider">
            Zakat Calculator
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {/* Portfolio Value */}
          <div className="bg-bg-elevated rounded-lg p-4 border border-border-main">
            <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Portfolio Value</p>
            <p className="font-mono text-xl font-bold text-text-primary">
              {formatCurrency(zakat.portfolio_value)}
            </p>
          </div>

          {/* Nisab Threshold */}
          <div className="bg-bg-elevated rounded-lg p-4 border border-border-main">
            <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Nisab Threshold (85g Gold)</p>
            <p className="font-mono text-xl font-bold text-text-primary">
              {formatCurrency(zakat.nisab_threshold)}
            </p>
          </div>

          {/* Status */}
          <div className="bg-bg-elevated rounded-lg p-4 border border-border-main">
            <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Status</p>
            <p className={`text-xl font-bold ${
              zakat.above_nisab ? 'text-brand-gold' : 'text-gain'
            }`}>
              {zakat.above_nisab ? 'Above Nisab' : 'Below Nisab'}
            </p>
          </div>
        </div>

        {/* Zakat Due */}
        {zakat.above_nisab && (
          <div className="bg-bg-elevated rounded-lg p-4 border border-brand-gold/30 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Zakat Due (2.5%)</p>
                <p className="font-mono text-2xl font-bold text-brand-gold">
                  {formatCurrency(zakat.zakat_due)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Lunar Year Anniversary</p>
                <p className="font-mono text-text-primary">{zakat.lunar_anniversary ?? 'N/A'}</p>
              </div>
            </div>
          </div>
        )}

        {/* Purification Section */}
        {(zakat.purification_amount != null && zakat.purification_amount > 0) && (
          <div className="bg-bg-elevated rounded-lg p-4 border border-border-main mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Coins size={18} className="text-brand-gold" />
              <p className="text-text-muted text-sm font-semibold uppercase tracking-wider">Dividend Purification</p>
            </div>
            <p className="text-text-primary text-sm mb-1">
              Amount to donate for purification of non-compliant dividend income:
            </p>
            <p className="font-mono text-lg font-bold text-brand-gold">
              {formatCurrency(zakat.purification_amount)}
            </p>
          </div>
        )}

        {/* Progress Bar — Lunar Year */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-text-muted text-xs uppercase tracking-wider">Lunar Year Progress</p>
            <p className="font-mono text-sm text-text-muted">
              {zakatDaysElapsed} / {lunarYearDays} days
            </p>
          </div>
          <div className="w-full h-3 bg-bg-elevated rounded-full overflow-hidden border border-border-main">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${zakatProgress}%` }}
              transition={{ duration: 1, ease: 'easeOut', delay: 0.6 }}
              className="h-full bg-brand-gold rounded-full"
            />
          </div>
        </div>
      </motion.div>
      <Disclaimer />
    </motion.div>
  );
}
