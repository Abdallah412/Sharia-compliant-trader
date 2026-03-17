import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, DollarSign, Droplets, X } from 'lucide-react';

const TYPE_CONFIG = {
  tax_large_gain: {
    bg: 'bg-brand-gold/10 border-brand-gold/30',
    text: 'text-brand-gold',
    Icon: DollarSign,
  },
  near_longterm: {
    bg: 'bg-doubtful/10 border-doubtful/30',
    text: 'text-doubtful',
    Icon: AlertTriangle,
  },
  purification: {
    bg: 'bg-brand-teal/10 border-brand-teal/30',
    text: 'text-brand-teal-light',
    Icon: Droplets,
  },
};

export default function TaxWarningBanner({ warnings }) {
  const [dismissed, setDismissed] = useState(new Set());

  if (!warnings || warnings.length === 0) return null;

  const visible = warnings.filter((_, i) => !dismissed.has(i));
  if (visible.length === 0) return null;

  const dismiss = (idx) => {
    setDismissed((prev) => new Set([...prev, idx]));
  };

  return (
    <div className="sticky top-0 z-10 space-y-1">
      <AnimatePresence>
        {warnings.map((w, i) => {
          if (dismissed.has(i)) return null;

          const config = TYPE_CONFIG[w.type] || TYPE_CONFIG.tax_large_gain;
          const { bg, text, Icon } = config;

          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, height: 0, y: -8 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0, y: -8 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border ${bg}`}
            >
              <Icon size={16} className={text} />
              <span className={`flex-1 text-sm ${text}`}>
                {w.ticker && (
                  <span className="font-mono font-bold mr-1.5">{w.ticker}</span>
                )}
                {w.message}
              </span>
              {w.action && (
                <span className="text-xs text-text-muted font-medium">{w.action}</span>
              )}
              <button
                onClick={() => dismiss(i)}
                className="text-text-dim hover:text-text-muted transition-colors p-0.5"
                aria-label="Dismiss warning"
              >
                <X size={14} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
