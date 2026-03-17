import { ArrowUpRight, ArrowDownRight, Pause, Clock } from 'lucide-react';

const ACTION_CONFIG = {
  BUY: { icon: ArrowUpRight, color: 'text-gain', bg: 'bg-gain/10', label: 'BUY' },
  SELL: { icon: ArrowDownRight, color: 'text-loss', bg: 'bg-loss/10', label: 'SELL' },
  HOLD: { icon: Pause, color: 'text-brand-gold', bg: 'bg-brand-gold/10', label: 'HOLD' },
};

function formatTime(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  if (isNaN(d)) return ts;
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function AgentDecisionCard({ decision, compact = false }) {
  const action = (decision.action || decision.side || 'HOLD').toUpperCase();
  const config = ACTION_CONFIG[action] || ACTION_CONFIG.HOLD;
  const ActionIcon = config.icon;

  if (compact) {
    return (
      <div className="flex items-center gap-3 px-3 py-2 bg-bg-elevated/50 rounded-lg border border-border-main/50 hover:border-border-light transition-colors">
        <div className={`flex-shrink-0 w-7 h-7 rounded-md flex items-center justify-center ${config.bg}`}>
          <ActionIcon size={14} className={config.color} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-bold text-text-primary">
              {decision.ticker || '--'}
            </span>
            <span className={`text-xs font-semibold ${config.color}`}>
              {config.label}
            </span>
            {decision.qty && (
              <span className="text-xs text-text-muted">
                x{decision.qty}
              </span>
            )}
          </div>
          {decision.reason && (
            <p className="text-xs text-text-muted truncate mt-0.5">
              {decision.reason}
            </p>
          )}
        </div>
        <div className="flex-shrink-0 flex items-center gap-1 text-text-dim text-xs">
          <Clock size={10} />
          <span>{formatTime(decision.timestamp || decision.created_at)}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-bg-card border border-border-main rounded-lg p-4">
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center ${config.bg}`}>
          <ActionIcon size={18} className={config.color} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-base font-bold text-text-primary">
              {decision.ticker || '--'}
            </span>
            <span className={`text-sm font-semibold ${config.color}`}>
              {config.label}
            </span>
            {decision.qty && (
              <span className="text-sm text-text-muted">x{decision.qty}</span>
            )}
          </div>
          {decision.reason && (
            <p className="text-sm text-text-muted leading-relaxed">
              {decision.reason}
            </p>
          )}
          <p className="text-xs text-text-dim mt-2 flex items-center gap-1">
            <Clock size={11} />
            {formatTime(decision.timestamp || decision.created_at)}
          </p>
        </div>
      </div>
    </div>
  );
}
