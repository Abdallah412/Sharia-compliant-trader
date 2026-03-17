import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, TrendingUp, TrendingDown, Minus, Newspaper, Scale, Calculator, ShieldCheck } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import ComplianceBadge from './ComplianceBadge';
import EMAChart from './EMAChart';

function SignalBadge({ signal }) {
  const config = {
    BUY: 'bg-gain/20 text-gain border-gain/30',
    SELL: 'bg-loss/20 text-loss border-loss/30',
    HOLD: 'bg-brand-gold/20 text-brand-gold border-brand-gold/30',
  };
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold border ${config[signal] || config.HOLD}`}>
      {signal === 'BUY' && <TrendingUp size={14} />}
      {signal === 'SELL' && <TrendingDown size={14} />}
      {signal === 'HOLD' && <Minus size={14} />}
      {signal || 'HOLD'}
    </span>
  );
}

function SectionHeading({ icon: Icon, children }) {
  return (
    <h3 className="flex items-center gap-2 text-text-primary font-semibold text-sm uppercase tracking-wider mb-3">
      <Icon size={16} className="text-brand-teal" />
      {children}
    </h3>
  );
}

export default function StockDetailDrawer({ ticker, onClose }) {
  const { data: compliance, loading: complianceLoading } = useApi(
    `/api/compliance/${ticker}`,
    { enabled: !!ticker }
  );
  const { data: priceData, loading: priceLoading } = useApi(
    `/api/price/${ticker}`,
    { enabled: !!ticker }
  );

  // Close on Escape key
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const sheikh = compliance?.sheikh || compliance?.sheikh_analysis || {};
  const finance = compliance?.finance || compliance?.finance_signal || {};
  const tax = compliance?.tax || compliance?.tax_impact || {};
  const news = compliance?.news || compliance?.recent_news || [];
  const complianceStatus = compliance?.status || compliance?.compliance_status || 'N/A';

  return (
    <AnimatePresence>
      {ticker && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/50 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.aside
            className="fixed top-0 right-0 z-40 w-[480px] h-full bg-bg-card border-l border-border-main overflow-y-auto"
            initial={{ x: 480 }}
            animate={{ x: 0 }}
            exit={{ x: 480 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          >
            <div className="p-6 space-y-6">
              {/* Header */}
              <div className="flex items-center justify-between">
                <h2 className="font-display text-xl text-brand-gold">{ticker}</h2>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Compliance Badge */}
              <div>
                <ComplianceBadge status={complianceStatus} size="lg" />
              </div>

              {/* EMA Chart */}
              <div className="bg-bg-elevated rounded-lg p-4 border border-border-main">
                <EMAChart ticker={ticker} height={240} />
              </div>

              {/* Loading state */}
              {complianceLoading && (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-bg-elevated rounded w-1/3 mb-2" />
                      <div className="h-3 bg-bg-elevated rounded w-full mb-1" />
                      <div className="h-3 bg-bg-elevated rounded w-2/3" />
                    </div>
                  ))}
                </div>
              )}

              {/* Sheikh Analysis */}
              {!complianceLoading && (
                <section>
                  <SectionHeading icon={ShieldCheck}>Sheikh Analysis</SectionHeading>
                  <div className="bg-bg-elevated rounded-lg p-4 border border-border-main space-y-2">
                    <p className="text-text-primary font-medium">
                      Verdict:{' '}
                      <span className={
                        sheikh.verdict === 'HALAL' ? 'text-halal' :
                        sheikh.verdict === 'HARAM' ? 'text-haram' :
                        'text-doubtful'
                      }>
                        {sheikh.verdict || 'Pending'}
                      </span>
                    </p>
                    <p className="text-text-muted text-sm leading-relaxed">
                      {sheikh.reasoning || sheikh.explanation || 'No analysis available.'}
                    </p>
                  </div>
                </section>
              )}

              {/* Finance Signal */}
              {!complianceLoading && (
                <section>
                  <SectionHeading icon={TrendingUp}>Finance Signal</SectionHeading>
                  <div className="bg-bg-elevated rounded-lg p-4 border border-border-main space-y-3">
                    <div className="flex items-center gap-3">
                      <SignalBadge signal={finance.action || finance.signal} />
                      {finance.confidence != null && (
                        <span className="text-text-muted text-sm">
                          Confidence: <span className="text-text-primary font-mono">{(finance.confidence * 100).toFixed(0)}%</span>
                        </span>
                      )}
                    </div>
                    {(finance.expected_return_min != null || finance.expected_return_max != null) && (
                      <p className="text-text-muted text-sm">
                        Expected return:{' '}
                        <span className="text-text-primary font-mono">
                          {finance.expected_return_min != null ? `${(finance.expected_return_min * 100).toFixed(1)}%` : '—'}
                          {' to '}
                          {finance.expected_return_max != null ? `${(finance.expected_return_max * 100).toFixed(1)}%` : '—'}
                        </span>
                      </p>
                    )}
                  </div>
                </section>
              )}

              {/* Tax Impact */}
              {!complianceLoading && (
                <section>
                  <SectionHeading icon={Calculator}>Tax Impact</SectionHeading>
                  <div className="bg-bg-elevated rounded-lg p-4 border border-border-main space-y-2">
                    {tax.holding_period && (
                      <p className="text-text-muted text-sm">
                        Holding period: <span className="text-text-primary">{tax.holding_period}</span>
                      </p>
                    )}
                    {tax.estimated_tax != null && (
                      <p className="text-text-muted text-sm">
                        Est. tax: <span className="text-text-primary font-mono">${Number(tax.estimated_tax).toLocaleString()}</span>
                      </p>
                    )}
                    {tax.recommendation && (
                      <p className="text-text-muted text-sm">
                        Recommendation: <span className="text-text-primary">{tax.recommendation}</span>
                      </p>
                    )}
                    {!tax.holding_period && !tax.estimated_tax && !tax.recommendation && (
                      <p className="text-text-muted text-sm">No tax data available.</p>
                    )}
                  </div>
                </section>
              )}

              {/* Recent News */}
              {!complianceLoading && (
                <section>
                  <SectionHeading icon={Newspaper}>Recent News</SectionHeading>
                  <div className="space-y-2">
                    {(Array.isArray(news) ? news.slice(0, 3) : []).map((item, i) => (
                      <div key={i} className="bg-bg-elevated rounded-lg p-3 border border-border-main">
                        <p className="text-text-primary text-sm font-medium leading-snug">
                          {item.headline || item.title}
                        </p>
                        {item.sentiment != null && (
                          <span className={`inline-block mt-1.5 text-xs font-mono px-2 py-0.5 rounded ${
                            item.sentiment > 0 ? 'bg-gain/10 text-gain' :
                            item.sentiment < 0 ? 'bg-loss/10 text-loss' :
                            'bg-bg-hover text-text-muted'
                          }`}>
                            Sentiment: {typeof item.sentiment === 'number' ? item.sentiment.toFixed(2) : item.sentiment}
                          </span>
                        )}
                      </div>
                    ))}
                    {(!Array.isArray(news) || news.length === 0) && (
                      <p className="text-text-muted text-sm">No recent news available.</p>
                    )}
                  </div>
                </section>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2 pb-4">
                <div className="relative group flex-1">
                  <button
                    disabled
                    className="w-full px-4 py-2.5 rounded-lg border border-gain text-gain font-semibold opacity-50 cursor-not-allowed"
                  >
                    Buy More
                  </button>
                  <span className="absolute -top-8 left-1/2 -translate-x-1/2 bg-bg-elevated text-text-muted text-xs px-2 py-1 rounded border border-border-main opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    Coming soon
                  </span>
                </div>
                <div className="relative group flex-1">
                  <button
                    disabled
                    className="w-full px-4 py-2.5 rounded-lg border border-loss text-loss font-semibold opacity-50 cursor-not-allowed"
                  >
                    Sell
                  </button>
                  <span className="absolute -top-8 left-1/2 -translate-x-1/2 bg-bg-elevated text-text-muted text-xs px-2 py-1 rounded border border-border-main opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                    Coming soon
                  </span>
                </div>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
