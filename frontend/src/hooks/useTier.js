import { useAuth } from './useAuth';

const TIER_FEATURES = {
  free: new Set(['screener', 'basic_news', 'watchlist_3']),
  pro: new Set([
    'screener', 'basic_news', 'watchlist_3',
    'full_pipeline', 'schwab_connect', 'trading_bot', 'tax_engine',
    'zakat', 'watchlist_50', 'push_notifications', 'telegram_alerts',
    'pdf_reports', 'priority_support',
  ]),
  managed: new Set([
    'screener', 'basic_news', 'watchlist_3',
    'full_pipeline', 'schwab_connect', 'trading_bot', 'tax_engine',
    'zakat', 'watchlist_50', 'push_notifications', 'telegram_alerts',
    'pdf_reports', 'priority_support',
    'human_review', 'weekly_call', 'dedicated_dm',
    'monthly_report', 'tax_pdf', 'vip_onboarding',
  ]),
};

export function useTier() {
  const { user } = useAuth();
  const tier = user?.tier || 'free';

  const hasFeature = (feature) => {
    return TIER_FEATURES[tier]?.has(feature) || false;
  };

  const isPro = tier === 'pro' || tier === 'managed';
  const isManaged = tier === 'managed';
  const isFree = tier === 'free';

  return { tier, hasFeature, isPro, isManaged, isFree };
}
