import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ShieldCheck, TrendingUp, Calculator, Clock } from 'lucide-react';

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function PendingTradeModal({ trade, onApprove, onReject, onClose }) {
  const [remaining, setRemaining] = useState(30 * 60); // 30 minutes in seconds

  useEffect(() => {
    if (!trade) return;

    // Calculate remaining from trade.expires_at if provided
    if (trade.expires_at) {
      const diff = Math.max(0, Math.floor((new Date(trade.expires_at) - Date.now()) / 1000));
      setRemaining(diff);
    } else {
      setRemaining(30 * 60);
    }

    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 0) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [trade]);

  const isExpired = remaining <= 0;
  const isUrgent = remaining <= 120; // under 2 minutes

  if (!trade) return null;

  const sheikh = trade.sheikh || trade.sheikh_summary || {};
  const finance = trade.finance || trade.finance_summary || {};
  const accountant = trade.accountant || trade.accountant_summary || {};
  const totalValue = trade.quantity && trade.estimated_price
    ? (trade.quantity * trade.estimated_price).toFixed(2)
    : null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 bg-black/70 flex justify-center overflow-y-auto"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="bg-bg-card border border-border-main rounded-xl max-w-lg w-full mx-auto p-6 mt-20 mb-10 h-fit"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="font-display text-xl text-text-primary">Trade Approval Required</h2>
              <p className="text-brand-gold font-display text-lg mt-1">{trade.ticker || trade.symbol}</p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          {/* Agent Reasoning */}
          <div className="space-y-3 mb-6">
            <div className="bg-bg-elevated rounded-lg p-3 border border-border-main">
              <div className="flex items-center gap-2 mb-1.5">
                <ShieldCheck size={14} className="text-brand-teal" />
                <span className="text-text-primary text-sm font-semibold">Sheikh Review</span>
              </div>
              <p className="text-text-muted text-sm leading-relaxed">
                {sheikh.summary || sheikh.reasoning || 'No sheikh analysis provided.'}
              </p>
            </div>

            <div className="bg-bg-elevated rounded-lg p-3 border border-border-main">
              <div className="flex items-center gap-2 mb-1.5">
                <TrendingUp size={14} className="text-brand-teal" />
                <span className="text-text-primary text-sm font-semibold">Finance Analysis</span>
              </div>
              <p className="text-text-muted text-sm leading-relaxed">
                {finance.summary || finance.reasoning || 'No finance analysis provided.'}
              </p>
            </div>

            <div className="bg-bg-elevated rounded-lg p-3 border border-border-main">
              <div className="flex items-center gap-2 mb-1.5">
                <Calculator size={14} className="text-brand-teal" />
                <span className="text-text-primary text-sm font-semibold">Accountant Review</span>
              </div>
              <p className="text-text-muted text-sm leading-relaxed">
                {accountant.summary || accountant.reasoning || 'No accountant analysis provided.'}
              </p>
            </div>
          </div>

          {/* Trade Details */}
          <div className="bg-bg-elevated rounded-lg p-4 border border-border-main mb-6">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-text-muted">Action</span>
                <p className={`font-semibold ${
                  trade.action === 'BUY' ? 'text-gain' :
                  trade.action === 'SELL' ? 'text-loss' :
                  'text-text-primary'
                }`}>
                  {trade.action || 'N/A'}
                </p>
              </div>
              <div>
                <span className="text-text-muted">Quantity</span>
                <p className="text-text-primary font-mono font-semibold">{trade.quantity || 'N/A'}</p>
              </div>
              <div>
                <span className="text-text-muted">Est. Price</span>
                <p className="text-text-primary font-mono font-semibold">
                  {trade.estimated_price != null ? `$${Number(trade.estimated_price).toFixed(2)}` : 'N/A'}
                </p>
              </div>
              <div>
                <span className="text-text-muted">Total Value</span>
                <p className="text-text-primary font-mono font-semibold">
                  {totalValue != null ? `$${Number(totalValue).toLocaleString()}` : 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Countdown */}
          <div className={`flex items-center justify-center gap-2 mb-6 text-sm ${
            isExpired ? 'text-loss' : isUrgent ? 'text-loss animate-pulse' : 'text-text-muted'
          }`}>
            <Clock size={16} />
            <span>
              {isExpired ? 'Trade expired' : `Expires in ${formatTime(remaining)}`}
            </span>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              onClick={() => onApprove(trade)}
              disabled={isExpired}
              className="flex-1 bg-gain hover:bg-gain-muted disabled:opacity-40 disabled:cursor-not-allowed text-white px-8 py-3 rounded-lg font-bold text-lg transition-colors"
            >
              Approve
            </button>
            <button
              onClick={() => onReject(trade)}
              disabled={isExpired}
              className="flex-1 bg-loss hover:bg-loss-muted disabled:opacity-40 disabled:cursor-not-allowed text-white px-8 py-3 rounded-lg font-bold text-lg transition-colors"
            >
              Reject
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
