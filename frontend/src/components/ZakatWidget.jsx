import { Moon } from 'lucide-react';

export default function ZakatWidget({ zakatData }) {
  const {
    zakat_due = false,
    zakat_amount_usd = 0,
    days_to_hawl = 0,
    hawl_met = false,
    above_nisab = false,
    total_wealth_usd = 0,
    nisab_usd = 6800,
  } = zakatData || {};

  const progress = hawl_met ? 100 : Math.max(0, Math.min(100, ((354 - days_to_hawl) / 354) * 100));

  return (
    <div className="p-4 rounded-xl bg-bg-card border border-border-main">
      <div className="flex items-center gap-2 mb-3">
        <Moon size={18} className="text-brand-gold" />
        <h3 className="font-heading text-sm font-semibold text-text-primary">Zakat Calculator</h3>
      </div>

      {zakat_due ? (
        <div className="p-3 rounded-lg bg-brand-gold/10 border border-brand-gold/30 mb-3">
          <p className="text-brand-gold font-mono text-lg font-bold">${zakat_amount_usd.toFixed(2)}</p>
          <p className="text-xs text-text-muted mt-1">Zakat due — 2.5% of zakatable wealth</p>
        </div>
      ) : (
        <div className="mb-3">
          {!above_nisab ? (
            <p className="text-xs text-text-muted">
              Portfolio below nisab (${nisab_usd.toLocaleString()}). No Zakat obligation.
            </p>
          ) : (
            <p className="text-xs text-text-muted">
              Hawl not met. {days_to_hawl} days remaining until lunar year completion.
            </p>
          )}
        </div>
      )}

      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-text-muted">Wealth</span>
          <span className="font-mono text-text-primary">${total_wealth_usd.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">Nisab</span>
          <span className="font-mono text-text-primary">${nisab_usd.toLocaleString()}</span>
        </div>
        <div>
          <div className="flex justify-between mb-1">
            <span className="text-text-muted">Hawl Progress</span>
            <span className="font-mono text-text-primary">{Math.round(progress)}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-bg-hover overflow-hidden">
            <div
              className="h-full rounded-full bg-brand-gold transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      <p className="text-[10px] text-text-muted mt-3 italic">
        For educational purposes only. Consult a qualified scholar for your personal Zakat obligation.
      </p>
    </div>
  );
}
