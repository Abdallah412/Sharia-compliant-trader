import { useState, useEffect } from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { BarChart3 } from 'lucide-react';

const TEAL = '#0D7377';
const TEAL_LIGHT = '#14A085';
const GOLD = '#C9A84C';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-bg-elevated border border-border-main rounded-lg px-3 py-2 shadow-lg">
      <p className="text-text-muted text-xs mb-1">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="font-mono text-sm" style={{ color: entry.color }}>
          {entry.name}: ${Number(entry.value).toFixed(2)}
        </p>
      ))}
    </div>
  );
}

export default function EMAChart({ ticker, height = 300 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!ticker) {
      setData(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`/api/price/${ticker}`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch price data');
        return res.json();
      })
      .then((json) => {
        if (!cancelled) {
          setData(json.prices || json.data || json);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [ticker]);

  if (!ticker) {
    return (
      <div
        className="flex flex-col items-center justify-center text-text-dim"
        style={{ height }}
      >
        <BarChart3 size={48} className="mb-3 opacity-40" />
        <p className="text-sm">Select a stock to view chart</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="animate-pulse" style={{ height }}>
        <div className="bg-bg-elevated rounded-lg w-full h-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="flex items-center justify-center text-loss text-sm"
        style={{ height }}
      >
        {error}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-text-dim text-sm"
        style={{ height }}
      >
        No data available for {ticker}
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="tealGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={TEAL} stopOpacity={0.3} />
            <stop offset="100%" stopColor={TEAL} stopOpacity={0} />
          </linearGradient>
        </defs>

        <XAxis
          dataKey="date"
          axisLine={false}
          tickLine={false}
          tick={{ fill: '#334155', fontSize: 11 }}
          minTickGap={40}
        />
        <YAxis
          domain={['auto', 'auto']}
          axisLine={false}
          tickLine={false}
          tick={{ fill: '#334155', fontSize: 11 }}
          width={55}
          tickFormatter={(v) => `$${v}`}
        />

        <Tooltip content={<CustomTooltip />} />

        <Area
          type="monotone"
          dataKey="close"
          name="Close"
          stroke={TEAL}
          strokeWidth={2}
          fill="url(#tealGradient)"
        />
        <Line
          type="monotone"
          dataKey="ema20"
          name="EMA20"
          stroke={TEAL_LIGHT}
          strokeWidth={1.5}
          strokeDasharray="6 3"
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="ema50"
          name="EMA50"
          stroke={GOLD}
          strokeWidth={1.5}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
