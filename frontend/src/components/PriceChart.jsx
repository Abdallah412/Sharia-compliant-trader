import { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

export default function PriceChart({ ticker }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!ticker) {
      setData([])
      return
    }

    let cancelled = false
    setLoading(true)

    fetch(`/api/price/${ticker}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        if (cancelled) return
        if (json) {
          const prices = Array.isArray(json) ? json : json.prices || json.data || []
          setData(
            prices.map((p) => ({
              date: p.date || p.timestamp || '',
              price: Number(p.close || p.price || 0),
              ema20: p.ema20 != null ? Number(p.ema20) : null,
              ema50: p.ema50 != null ? Number(p.ema50) : null,
            }))
          )
        } else {
          setData([])
        }
        setLoading(false)
      })
      .catch(() => {
        if (!cancelled) {
          setData([])
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [ticker])

  if (!ticker) {
    return (
      <div className="bg-white rounded-xl shadow p-6 h-full flex items-center justify-center">
        <p className="text-gray-400 text-sm text-center">
          Select a holding to view price chart
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow p-6">
      <h2 className="text-lg font-bold text-navy mb-4">
        {ticker} &mdash; 30 Day Price
      </h2>
      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-halal" />
        </div>
      ) : data.length === 0 ? (
        <div className="h-64 flex items-center justify-center">
          <p className="text-gray-400 text-sm">No price data available</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: '#9ca3af' }}
              tickFormatter={(v) => {
                const d = new Date(v)
                return isNaN(d) ? v : `${d.getMonth() + 1}/${d.getDate()}`
              }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#9ca3af' }}
              domain={['auto', 'auto']}
              tickFormatter={(v) => `$${v}`}
              width={60}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value, name) => [
                `$${Number(value).toFixed(2)}`,
                name === 'price' ? 'Price' : name === 'ema20' ? 'EMA 20' : 'EMA 50',
              ]}
            />
            <Legend
              wrapperStyle={{ fontSize: '12px' }}
              formatter={(value) =>
                value === 'price' ? 'Price' : value === 'ema20' ? 'EMA 20' : 'EMA 50'
              }
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#0B2545"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="ema20"
              stroke="#1B6B3A"
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="ema50"
              stroke="#1B6B3A"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
