import { motion } from 'framer-motion';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function KPICard({ title, value, change, changePct, positive, icon: Icon, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: 'easeOut' }}
      className="bg-bg-card border border-border-main rounded-lg p-5 relative group
                 hover:border-border-light hover:-translate-y-px transition-all duration-200"
    >
      {/* Icon in top-right */}
      {Icon && (
        <div className="absolute top-4 right-4 text-text-dim">
          <Icon size={20} />
        </div>
      )}

      {/* Title */}
      <p className="text-text-muted text-sm uppercase tracking-wider mb-2">{title}</p>

      {/* Value */}
      <p className="font-mono text-2xl font-bold text-text-primary">{value}</p>

      {/* Change line */}
      {(change !== undefined || changePct !== undefined) && (
        <div className={`flex items-center gap-1 mt-2 text-sm font-mono ${positive ? 'text-gain' : 'text-loss'}`}>
          {positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
          {change !== undefined && (
            <span>{positive ? '+' : ''}{change}</span>
          )}
          {changePct !== undefined && (
            <span className="text-xs opacity-80">
              ({positive ? '+' : ''}{changePct}%)
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}
