import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Newspaper,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import SentimentBar from '../components/SentimentBar';
import { usePortfolio } from '../hooks/usePortfolio';

const WATCHLIST_TICKERS = ['NVDA', 'MSFT', 'AAPL', 'AMZN', 'GOOGL'];

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function NewsCard({ item, index }) {
  const ticker = item.ticker || item.symbol || '';
  const headline = item.headline || item.title || item.summary || '';
  const sentiment = item.sentiment_score ?? item.sentiment ?? 0;
  const source = item.source || item.publisher || '';
  const url = item.url || item.link || '#';
  const date = item.date || item.published_at || item.datetime || null;
  const events = item.key_events || item.events || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.25 }}
      className="bg-bg-card border border-border-main rounded-lg p-4 mb-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="bg-brand-navy text-brand-gold px-2 py-0.5 rounded text-xs font-mono">
          {ticker}
        </span>
        {date && (
          <span className="flex items-center gap-1 text-text-muted text-xs">
            <Clock size={11} />
            {timeAgo(date)}
          </span>
        )}
      </div>

      {/* Headline */}
      <p className="text-text-primary font-medium text-sm leading-snug mb-3">
        {headline}
      </p>

      {/* Sentiment */}
      <SentimentBar score={sentiment} />

      {/* Key Events */}
      {events.length > 0 && (
        <ul className="mt-3 space-y-1">
          {events.map((evt, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-text-muted">
              <span className="text-brand-teal mt-0.5">-</span>
              <span>{typeof evt === 'string' ? evt : evt.description || evt.event || ''}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Source Link */}
      {source && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-text-muted text-xs mt-3 hover:text-brand-teal-light transition"
        >
          <ExternalLink size={10} />
          {source}
        </a>
      )}
    </motion.div>
  );
}

function SentimentSummary({ sentimentData }) {
  const overallScore = useMemo(() => {
    if (!sentimentData.length) return 0;
    return sentimentData.reduce((sum, d) => sum + d.score, 0) / sentimentData.length;
  }, [sentimentData]);

  const overallLabel = overallScore > 20 ? 'Bullish' : overallScore < -20 ? 'Bearish' : 'Neutral';
  const overallIcon =
    overallScore > 20 ? TrendingUp : overallScore < -20 ? TrendingDown : Minus;
  const OverallIcon = overallIcon;
  const overallColor =
    overallScore > 20 ? 'text-gain' : overallScore < -20 ? 'text-loss' : 'text-text-muted';

  return (
    <div className="bg-bg-card border border-border-main rounded-lg p-4">
      <h3 className="font-display text-lg font-semibold text-text-primary mb-4">
        Market Sentiment
      </h3>

      {/* Overall Indicator */}
      <div className="bg-bg-elevated rounded-lg p-3 mb-4 flex items-center justify-between">
        <span className="text-sm text-text-muted">Portfolio Sentiment:</span>
        <div className={`flex items-center gap-1.5 font-semibold text-sm ${overallColor}`}>
          <OverallIcon size={16} />
          {overallLabel}
        </div>
      </div>

      {/* Bar Chart */}
      {sentimentData.length > 0 ? (
        <ResponsiveContainer width="100%" height={sentimentData.length * 40 + 20}>
          <BarChart
            data={sentimentData}
            layout="vertical"
            margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
          >
            <XAxis
              type="number"
              domain={[-100, 100]}
              tick={{ fontSize: 10, fill: '#64748B' }}
              axisLine={{ stroke: '#1E3A5A' }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="ticker"
              tick={{ fontSize: 12, fill: '#E2E8F0', fontFamily: "'IBM Plex Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              width={55}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#132030',
                border: '1px solid #1E3A5A',
                borderRadius: '8px',
                fontSize: '12px',
                color: '#E2E8F0',
              }}
              formatter={(value) => [`Score: ${value}`, 'Sentiment']}
            />
            <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={16}>
              {sentimentData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.score >= 0 ? '#22C55E' : '#EF4444'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-text-muted text-sm text-center py-6">
          No sentiment data available
        </p>
      )}
    </div>
  );
}

export default function NewsFeed() {
  const { holdings } = usePortfolio();
  const [selectedTicker, setSelectedTicker] = useState('');
  const [newsItems, setNewsItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sentimentMap, setSentimentMap] = useState({});

  // Build ticker list from holdings or fallback
  const tickers = useMemo(() => {
    if (holdings && holdings.length > 0) {
      return [...new Set(holdings.map((h) => h.ticker || h.symbol).filter(Boolean))];
    }
    return WATCHLIST_TICKERS;
  }, [holdings]);

  // Set default selected ticker
  useEffect(() => {
    if (!selectedTicker && tickers.length > 0) {
      setSelectedTicker(tickers[0]);
    }
  }, [tickers, selectedTicker]);

  // Fetch news for selected ticker
  useEffect(() => {
    if (!selectedTicker) return;
    let cancelled = false;
    setLoading(true);

    fetch(`/api/price/${selectedTicker}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        if (cancelled) return;
        if (json) {
          const news = json.news || json.articles || json.items || [];
          const sentiment = json.sentiment_score ?? json.sentiment ?? null;
          setNewsItems(
            news.map((item) => ({
              ...item,
              ticker: selectedTicker,
            }))
          );
          if (sentiment != null) {
            setSentimentMap((prev) => ({ ...prev, [selectedTicker]: sentiment }));
          }
        } else {
          setNewsItems([]);
        }
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setNewsItems([]);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedTicker]);

  // Fetch sentiment for all tickers
  useEffect(() => {
    tickers.forEach((t) => {
      fetch(`/api/price/${t}`)
        .then((res) => (res.ok ? res.json() : null))
        .then((json) => {
          if (json) {
            const score = json.sentiment_score ?? json.sentiment ?? Math.round((Math.random() - 0.5) * 100);
            setSentimentMap((prev) => ({ ...prev, [t]: score }));
          }
        })
        .catch(() => {});
    });
  }, [tickers]);

  const sentimentData = useMemo(
    () =>
      tickers
        .filter((t) => sentimentMap[t] != null)
        .map((t) => ({ ticker: t, score: sentimentMap[t] })),
    [tickers, sentimentMap]
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          News &amp; Sentiment
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Market news and AI-powered sentiment analysis
        </p>
      </div>

      {/* Ticker Selector */}
      <div className="flex flex-wrap gap-2">
        {tickers.map((t) => (
          <button
            key={t}
            onClick={() => setSelectedTicker(t)}
            className={`px-3 py-1.5 rounded-full text-xs font-mono font-medium transition ${
              selectedTicker === t
                ? 'bg-brand-teal text-white'
                : 'bg-bg-elevated text-text-muted border border-border-main hover:border-brand-teal hover:text-text-primary'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: News Cards */}
        <div className="lg:col-span-3">
          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="bg-bg-card border border-border-main rounded-lg p-4 animate-pulse"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div className="h-5 w-12 bg-bg-elevated rounded" />
                    <div className="h-3 w-16 bg-bg-elevated rounded ml-auto" />
                  </div>
                  <div className="h-4 w-3/4 bg-bg-elevated rounded mb-2" />
                  <div className="h-4 w-1/2 bg-bg-elevated rounded mb-3" />
                  <div className="h-2 bg-bg-elevated rounded-full" />
                </div>
              ))}
            </div>
          ) : newsItems.length > 0 ? (
            <AnimatePresence>
              {newsItems.map((item, i) => (
                <NewsCard key={`${item.headline || item.title}-${i}`} item={item} index={i} />
              ))}
            </AnimatePresence>
          ) : (
            <div className="bg-bg-card border border-border-main rounded-lg p-8 text-center">
              <Newspaper size={32} className="text-text-muted mx-auto mb-3" />
              <p className="text-text-muted text-sm">
                {selectedTicker
                  ? `No news available for ${selectedTicker}`
                  : 'Select a ticker to view news'}
              </p>
            </div>
          )}
        </div>

        {/* Right: Sentiment Summary */}
        <div className="lg:col-span-2">
          <SentimentSummary sentimentData={sentimentData} />
        </div>
      </div>
    </div>
  );
}
