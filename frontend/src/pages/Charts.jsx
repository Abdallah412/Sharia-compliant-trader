import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  Search,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  BarChart3,
} from 'lucide-react';
import {
  ComposedChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import SentimentBar from '../components/SentimentBar';
import { usePortfolio } from '../hooks/usePortfolio';
import { formatCurrency } from '../utils/formatCurrency';
import Disclaimer from '../components/Disclaimer';

const FALLBACK_TICKERS = ['NVDA', 'MSFT', 'AAPL', 'AMZN', 'GOOGL'];
const TIME_RANGES = ['1W', '1M', '3M', '6M', '1Y'];
const RANGE_DAYS = { '1W': 5, '1M': 21, '3M': 63, '6M': 126, '1Y': 252 };

function SkeletonChart() {
  return (
    <div className="bg-bg-card border border-border-main rounded-lg p-4 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-5 w-32 bg-bg-elevated rounded" />
        <div className="h-5 w-24 bg-bg-elevated rounded" />
      </div>
      <div className="h-[400px] bg-bg-elevated/50 rounded-lg flex items-end px-4 pb-4 gap-1">
        {[...Array(30)].map((_, i) => (
          <div
            key={i}
            className="flex-1 bg-bg-elevated rounded-t"
            style={{ height: `${20 + Math.random() * 70}%` }}
          />
        ))}
      </div>
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="bg-bg-elevated border border-border-main rounded-lg p-3 shadow-xl font-mono text-xs">
      <p className="text-text-muted mb-2">{label}</p>
      <div className="space-y-1">
        {data.open != null && (
          <div className="flex justify-between gap-4">
            <span className="text-text-muted">O</span>
            <span className="text-text-primary">{formatCurrency(data.open)}</span>
          </div>
        )}
        {data.high != null && (
          <div className="flex justify-between gap-4">
            <span className="text-text-muted">H</span>
            <span className="text-text-primary">{formatCurrency(data.high)}</span>
          </div>
        )}
        {data.low != null && (
          <div className="flex justify-between gap-4">
            <span className="text-text-muted">L</span>
            <span className="text-text-primary">{formatCurrency(data.low)}</span>
          </div>
        )}
        <div className="flex justify-between gap-4">
          <span className="text-text-muted">C</span>
          <span className="text-text-primary">{formatCurrency(data.close)}</span>
        </div>
        {data.volume != null && (
          <div className="flex justify-between gap-4">
            <span className="text-text-muted">Vol</span>
            <span className="text-text-primary">
              {(data.volume / 1e6).toFixed(2)}M
            </span>
          </div>
        )}
        {data.ema20 != null && (
          <div className="flex justify-between gap-4">
            <span className="text-brand-teal-light">EMA20</span>
            <span className="text-brand-teal-light">{formatCurrency(data.ema20)}</span>
          </div>
        )}
        {data.ema50 != null && (
          <div className="flex justify-between gap-4">
            <span className="text-brand-gold">EMA50</span>
            <span className="text-brand-gold">{formatCurrency(data.ema50)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function SignalPanel({ data, sentimentScore }) {
  const latest = data[data.length - 1];
  if (!latest) return null;

  const ema20 = latest.ema20;
  const ema50 = latest.ema50;
  const hasCrossover = ema20 != null && ema50 != null;

  let signal = 'HOLD';
  let signalColor = 'text-text-muted';
  let signalBg = 'bg-bg-elevated';
  let SignalIcon = ArrowRight;

  if (hasCrossover) {
    if (ema20 > ema50) {
      signal = 'BUY SIGNAL ACTIVE';
      signalColor = 'text-gain';
      signalBg = 'bg-gain/10';
      SignalIcon = TrendingUp;
    } else if (ema20 < ema50) {
      signal = 'SELL SIGNAL ACTIVE';
      signalColor = 'text-loss';
      signalBg = 'bg-loss/10';
      SignalIcon = TrendingDown;
    }
  }

  // Calculate a simple confidence based on EMA distance
  let confidence = 50;
  if (hasCrossover && ema50 > 0) {
    const dist = Math.abs(ema20 - ema50) / ema50;
    confidence = Math.min(95, Math.round(50 + dist * 500));
  }

  const crossoverStatus = hasCrossover
    ? ema20 > ema50
      ? 'EMA20 above EMA50 (Bullish)'
      : ema20 < ema50
        ? 'EMA20 below EMA50 (Bearish)'
        : 'EMAs converging'
    : 'Insufficient data';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="bg-bg-card border border-border-main rounded-lg p-4"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Signal */}
        <div className={`${signalBg} rounded-lg p-3`}>
          <p className="text-text-muted text-xs uppercase tracking-wider mb-1">
            Current Signal
          </p>
          <div className={`flex items-center gap-2 ${signalColor} font-semibold`}>
            <SignalIcon size={18} />
            <span className="text-sm">{signal}</span>
          </div>
        </div>

        {/* EMA Values */}
        <div className="bg-bg-elevated rounded-lg p-3">
          <p className="text-text-muted text-xs uppercase tracking-wider mb-1">
            EMA Values
          </p>
          <div className="space-y-1 font-mono text-sm">
            <div className="flex justify-between">
              <span className="text-brand-teal-light">EMA20</span>
              <span className="text-text-primary">
                {ema20 != null ? formatCurrency(ema20) : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-brand-gold">EMA50</span>
              <span className="text-text-primary">
                {ema50 != null ? formatCurrency(ema50) : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Crossover + Confidence */}
        <div className="bg-bg-elevated rounded-lg p-3">
          <p className="text-text-muted text-xs uppercase tracking-wider mb-1">
            Crossover Status
          </p>
          <p className="text-text-primary text-sm">{crossoverStatus}</p>
          <div className="mt-2 flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-bg-hover rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-brand-teal transition-all duration-500"
                style={{ width: `${confidence}%` }}
              />
            </div>
            <span className="text-xs font-mono text-text-muted">{confidence}%</span>
          </div>
        </div>

        {/* Sentiment */}
        <div className="bg-bg-elevated rounded-lg p-3">
          <p className="text-text-muted text-xs uppercase tracking-wider mb-2">
            News Sentiment
          </p>
          <SentimentBar score={sentimentScore} />
        </div>
      </div>
    </motion.div>
  );
}

export default function Charts() {
  const { holdings } = usePortfolio();
  const [selectedTicker, setSelectedTicker] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [timeRange, setTimeRange] = useState('3M');
  const [rawData, setRawData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sentimentScore, setSentimentScore] = useState(0);

  const tickers = useMemo(() => {
    if (holdings && holdings.length > 0) {
      return [...new Set(holdings.map((h) => h.ticker || h.symbol).filter(Boolean))];
    }
    return FALLBACK_TICKERS;
  }, [holdings]);

  useEffect(() => {
    if (!selectedTicker && tickers.length > 0) {
      setSelectedTicker(tickers[0]);
    }
  }, [tickers, selectedTicker]);

  // Fetch price data
  useEffect(() => {
    if (!selectedTicker) return;
    let cancelled = false;
    setLoading(true);

    fetch(`/api/price/${selectedTicker}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        if (cancelled) return;
        if (json) {
          const prices = Array.isArray(json) ? json : json.prices || json.data || [];
          setRawData(
            prices.map((p) => ({
              date: p.date || p.timestamp || '',
              open: p.open != null ? Number(p.open) : null,
              high: p.high != null ? Number(p.high) : null,
              low: p.low != null ? Number(p.low) : null,
              close: Number(p.close || p.price || 0),
              volume: p.volume != null ? Number(p.volume) : null,
              ema20: p.ema20 != null ? Number(p.ema20) : null,
              ema50: p.ema50 != null ? Number(p.ema50) : null,
            }))
          );
          const score = json.sentiment_score ?? json.sentiment ?? 0;
          setSentimentScore(score);
        } else {
          setRawData([]);
        }
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setRawData([]);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedTicker]);

  // Filter data by time range
  const chartData = useMemo(() => {
    const days = RANGE_DAYS[timeRange] || 63;
    return rawData.slice(-days);
  }, [rawData, timeRange]);

  const priceMin = useMemo(() => {
    if (!chartData.length) return 0;
    const vals = chartData.map((d) => d.low ?? d.close).filter(Boolean);
    return Math.floor(Math.min(...vals) * 0.98);
  }, [chartData]);

  const priceMax = useMemo(() => {
    if (!chartData.length) return 100;
    const vals = chartData.map((d) => d.high ?? d.close).filter(Boolean);
    return Math.ceil(Math.max(...vals) * 1.02);
  }, [chartData]);

  const volumeMax = useMemo(() => {
    if (!chartData.length) return 1;
    return Math.max(...chartData.map((d) => d.volume || 0));
  }, [chartData]);

  const handleSearch = () => {
    if (searchInput.trim()) {
      setSelectedTicker(searchInput.trim().toUpperCase());
      setSearchInput('');
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Stock Charts
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Technical analysis with EMA crossover signals
        </p>
      </div>

      {/* Ticker Selector */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search Input */}
        <div className="relative flex-shrink-0 w-full sm:w-64">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search ticker..."
            className="w-full bg-bg-elevated border border-border-main rounded-lg pl-9 pr-4 py-2 text-text-primary font-mono text-sm placeholder:text-text-muted/60 focus:outline-none focus:border-brand-teal transition"
          />
        </div>

        {/* Watchlist Quick Select */}
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
      </div>

      {/* Main Chart */}
      {loading ? (
        <SkeletonChart />
      ) : chartData.length > 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="bg-bg-card border border-border-main rounded-lg p-4"
        >
          {/* Chart Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <BarChart3 size={18} className="text-brand-teal" />
              <h2 className="text-lg font-display font-semibold text-text-primary">
                {selectedTicker}
              </h2>
              {chartData.length > 0 && (
                <span className="text-text-muted text-sm font-mono">
                  {formatCurrency(chartData[chartData.length - 1]?.close)}
                </span>
              )}
            </div>

            {/* Time Range Buttons */}
            <div className="flex bg-bg-elevated rounded-lg p-0.5">
              {TIME_RANGES.map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
                    timeRange === range
                      ? 'bg-brand-teal text-white'
                      : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  {range}
                </button>
              ))}
            </div>
          </div>

          {/* Chart */}
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart
              data={chartData}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="tealGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0D7377" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#0D7377" stopOpacity={0.02} />
                </linearGradient>
              </defs>

              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: '#334155' }}
                axisLine={{ stroke: '#1E3A5A' }}
                tickLine={false}
                tickFormatter={(v) => {
                  const d = new Date(v);
                  return isNaN(d) ? v : `${d.getMonth() + 1}/${d.getDate()}`;
                }}
                interval="preserveStartEnd"
              />
              <YAxis
                yAxisId="price"
                domain={[priceMin, priceMax]}
                tick={{ fontSize: 10, fill: '#334155' }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `$${v}`}
                width={55}
                orientation="right"
              />
              <YAxis
                yAxisId="volume"
                domain={[0, volumeMax * 5]}
                hide
              />

              <Tooltip content={<CustomTooltip />} />

              {/* Volume Bars */}
              <Bar
                yAxisId="volume"
                dataKey="volume"
                fill="#1A2C40"
                opacity={0.5}
                barSize={3}
              />

              {/* Close Price Area */}
              <Area
                yAxisId="price"
                type="monotone"
                dataKey="close"
                stroke="#0D7377"
                strokeWidth={2}
                fill="url(#tealGradient)"
                dot={false}
                activeDot={{ r: 3, fill: '#0D7377', stroke: '#E2E8F0', strokeWidth: 1 }}
              />

              {/* EMA20 - dashed teal-light */}
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="ema20"
                stroke="#14A085"
                strokeWidth={1.5}
                strokeDasharray="5 3"
                dot={false}
                connectNulls
              />

              {/* EMA50 - solid gold */}
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="ema50"
                stroke="#C9A84C"
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>

          {/* Legend */}
          <div className="flex items-center justify-center gap-6 mt-3 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-4 h-0.5 bg-brand-teal rounded" />
              <span className="text-text-muted">Close</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className="inline-block w-4 h-0.5 rounded"
                style={{
                  background: '#14A085',
                  backgroundImage: 'repeating-linear-gradient(90deg, #14A085 0, #14A085 3px, transparent 3px, transparent 5px)',
                }}
              />
              <span className="text-text-muted">EMA20</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-4 h-0.5 bg-brand-gold rounded" />
              <span className="text-text-muted">EMA50</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 bg-bg-hover rounded-sm opacity-50" />
              <span className="text-text-muted">Volume</span>
            </div>
          </div>
        </motion.div>
      ) : (
        <div className="bg-bg-card border border-border-main rounded-lg p-12 text-center">
          <BarChart3 size={40} className="text-text-muted mx-auto mb-3" />
          <p className="text-text-muted text-sm">
            {selectedTicker
              ? `No chart data available for ${selectedTicker}`
              : 'Select a ticker to view chart'}
          </p>
        </div>
      )}

      {/* Signal Panel */}
      {chartData.length > 0 && !loading && (
        <SignalPanel data={chartData} sentimentScore={sentimentScore} />
      )}
      <Disclaimer />
    </div>
  );
}
