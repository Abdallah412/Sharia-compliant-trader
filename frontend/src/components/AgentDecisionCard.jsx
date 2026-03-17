import { useState } from 'react';
import { motion } from 'framer-motion';
import { Clock, Gavel, TrendingUp, Calculator, CheckCircle2 } from 'lucide-react';
import ComplianceBadge from './ComplianceBadge';

const ACTION_STYLES = {
  BUY: 'bg-gain/10 text-gain border-gain/30',
  SELL: 'bg-loss/10 text-loss border-loss/30',
  HOLD: 'bg-doubtful/10 text-doubtful border-doubtful/30',
};

function ActionBadge({ action }) {
  const key = (action || '').toUpperCase();
  const style = ACTION_STYLES[key] || 'bg-bg-elevated text-text-muted border-border-main';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${style}`}>
      {action || 'N/A'}
    </span>
  );
}

export default function AgentDecisionCard({ decision }) {
  const [approved, setApproved] = useState(null);

  if (!decision) return null;

  const {
    ticker,
    timestamp,
    sheikh_verdict,
    halal_status,
    finance_signal,
    confidence,
    tax_verdict,
    tax_recommendation,
    final_action,
    requires_approval,
  } = decision;

  return (
    <motion.div
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="bg-bg-card border border-border-main rounded-lg p-4"
    >
      {/* Header: ticker + timestamp */}
      <div className="flex items-center justify-between mb-3">
        <span className="font-mono font-bold text-brand-gold text-lg">{ticker}</span>
        {timestamp && (
          <span className="text-text-dim text-xs flex items-center gap-1">
            <Clock size={12} />
            {new Date(timestamp).toLocaleString()}
          </span>
        )}
      </div>

      {/* Sheikh verdict */}
      <div className="flex items-center gap-2 mb-2">
        <Gavel size={14} className="text-text-muted" />
        <span className="text-text-muted text-sm">Sheikh Verdict:</span>
        <ComplianceBadge status={halal_status || sheikh_verdict} size="sm" />
      </div>

      {/* Finance signal */}
      <div className="flex items-center gap-2 mb-2">
        <TrendingUp size={14} className="text-text-muted" />
        <span className="text-text-muted text-sm">Signal:</span>
        <ActionBadge action={finance_signal} />
        {confidence !== undefined && (
          <span className="font-mono text-xs text-text-muted">
            {confidence}% confidence
          </span>
        )}
      </div>

      {/* Tax verdict */}
      {(tax_verdict || tax_recommendation) && (
        <div className="flex items-center gap-2 mb-2">
          <Calculator size={14} className="text-text-muted" />
          <span className="text-text-muted text-sm">Tax:</span>
          <span className="text-text-primary text-sm">
            {tax_recommendation || tax_verdict}
          </span>
        </div>
      )}

      {/* Final decision */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border-main">
        <CheckCircle2 size={14} className="text-text-muted" />
        <span className="text-text-muted text-sm font-medium">Final Decision:</span>
        <ActionBadge action={final_action} />
      </div>

      {/* Approval buttons */}
      {requires_approval && approved === null && (
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => setApproved(true)}
            className="flex-1 py-1.5 rounded text-sm font-semibold bg-gain/10 text-gain
                       border border-gain/30 hover:bg-gain/20 transition-colors"
          >
            Approve
          </button>
          <button
            onClick={() => setApproved(false)}
            className="flex-1 py-1.5 rounded text-sm font-semibold bg-loss/10 text-loss
                       border border-loss/30 hover:bg-loss/20 transition-colors"
          >
            Reject
          </button>
        </div>
      )}

      {approved !== null && (
        <div className={`mt-3 text-sm font-medium ${approved ? 'text-gain' : 'text-loss'}`}>
          {approved ? 'Approved' : 'Rejected'}
        </div>
      )}
    </motion.div>
  );
}
