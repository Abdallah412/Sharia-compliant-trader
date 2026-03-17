import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';

export default function UpgradePrompt({ feature = 'this feature', requiredTier = 'Pro' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="p-4 rounded-full bg-bg-elevated mb-4">
        <Lock className="text-text-muted" size={32} />
      </div>
      <h2 className="text-lg font-bold text-text-primary mb-2">Upgrade to {requiredTier}</h2>
      <p className="text-sm text-text-muted mb-6 max-w-md">
        {feature} requires a {requiredTier} subscription. Upgrade to unlock automated trading,
        AI analysis, tax optimization, and more.
      </p>
      <Link
        to="/pricing"
        className="px-6 py-2.5 rounded-lg bg-brand-teal text-white font-semibold text-sm hover:bg-brand-teal-light transition"
      >
        View Plans
      </Link>
    </div>
  );
}
