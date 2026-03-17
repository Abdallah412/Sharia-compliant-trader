import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Check, Moon } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

const plans = [
  {
    name: 'Free',
    subtitle: 'Screener',
    price: '$0',
    period: 'forever',
    features: [
      'Shariah screener (5/day)',
      'Sheikh AI verdict',
      '3-stock watchlist',
      'Basic news feed',
      'Mobile app access',
    ],
    cta: 'Get Started',
    ctaLink: '/register',
    highlight: false,
  },
  {
    name: 'Pro',
    subtitle: 'Analyst',
    price: '$19',
    period: '/month',
    annual: '$169/year (save 26%)',
    features: [
      'Everything in Free',
      'All 4 AI agents',
      'Connect Schwab brokerage',
      'Automated trading bot',
      'Tax engine + Zakat calculator',
      '50-stock watchlist',
      'Push + Telegram alerts',
      'PDF reports',
      'Priority support',
    ],
    cta: 'Start Pro',
    ctaLink: '/register',
    highlight: true,
    planId: 'pro_monthly',
  },
  {
    name: 'Managed',
    subtitle: 'Autopilot',
    price: '$79',
    period: '/month',
    annual: '$749/year (save 21%)',
    trial: '30-day free trial',
    features: [
      'Everything in Pro',
      'Human trader reviews',
      'Weekly 15-min call',
      'Dedicated analyst DM',
      'Monthly report PDF',
      'Tax PDF for CPA',
      'VIP onboarding call',
    ],
    cta: 'Start Free Trial',
    ctaLink: '/register',
    highlight: false,
    planId: 'managed_monthly',
  },
];

export default function Pricing() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-bg-base text-text-primary">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-border-main max-w-7xl mx-auto">
        <Link to="/" className="flex items-center gap-2">
          <Moon className="text-brand-gold" size={24} />
          <span className="text-lg font-bold">Halal Trader</span>
        </Link>
        {user ? (
          <Link to="/" className="text-sm text-text-muted hover:text-text-primary">Dashboard</Link>
        ) : (
          <Link to="/login" className="text-sm text-text-muted hover:text-text-primary">Login</Link>
        )}
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h1 className="text-3xl md:text-4xl font-bold mb-3">Choose Your Plan</h1>
          <p className="text-text-muted">Start free. Upgrade when you're ready for automated halal trading.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`p-6 rounded-xl border ${
                plan.highlight
                  ? 'bg-bg-card border-brand-teal ring-1 ring-brand-teal/30'
                  : 'bg-bg-card border-border-main'
              }`}
            >
              {plan.highlight && (
                <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-brand-teal/20 text-brand-teal-light mb-3">
                  Most Popular
                </span>
              )}
              {plan.trial && (
                <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-brand-gold/20 text-brand-gold mb-3">
                  {plan.trial}
                </span>
              )}
              <h2 className="text-xl font-bold">{plan.name}</h2>
              <p className="text-xs text-text-muted mb-3">{plan.subtitle}</p>
              <div className="mb-1">
                <span className="text-3xl font-bold">{plan.price}</span>
                <span className="text-sm text-text-muted">{plan.period}</span>
              </div>
              {plan.annual && <p className="text-xs text-brand-teal-light mb-4">{plan.annual}</p>}
              {!plan.annual && <div className="mb-4" />}

              <ul className="space-y-2 mb-6">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-text-muted">
                    <Check size={14} className="text-halal mt-0.5 shrink-0" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              <Link
                to={plan.ctaLink}
                className={`block text-center py-2.5 rounded-lg font-semibold text-sm transition ${
                  plan.highlight
                    ? 'bg-brand-teal text-white hover:bg-brand-teal-light'
                    : 'bg-bg-elevated text-text-primary border border-border-light hover:bg-bg-hover'
                }`}
              >
                {plan.cta}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
