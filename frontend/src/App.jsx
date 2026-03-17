import { useState, useEffect, useCallback } from 'react'
import PortfolioSummary from './components/PortfolioSummary'
import HoldingsTable from './components/HoldingsTable'
import PriceChart from './components/PriceChart'
import TradeLog from './components/TradeLog'
import ComplianceAlert from './components/ComplianceAlert'
import AllocatorPanel from './components/AllocatorPanel'

const POLL_INTERVAL = 30000

function isMarketHours() {
  const now = new Date()
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }))
  const hours = et.getHours()
  const minutes = et.getMinutes()
  const day = et.getDay()
  if (day === 0 || day === 6) return false
  const timeInMinutes = hours * 60 + minutes
  return timeInMinutes >= 570 && timeInMinutes <= 960 // 9:30 - 16:00
}

async function fetchJSON(url) {
  try {
    const res = await fetch(url)
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export default function App() {
  const [portfolio, setPortfolio] = useState(null)
  const [holdings, setHoldings] = useState([])
  const [trades, setTrades] = useState([])
  const [status, setStatus] = useState(null)
  const [selectedTicker, setSelectedTicker] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchAll = useCallback(async () => {
    const [p, h, t, s] = await Promise.all([
      fetchJSON('/api/portfolio'),
      fetchJSON('/api/holdings'),
      fetchJSON('/api/trades'),
      fetchJSON('/api/status'),
    ])
    if (p) setPortfolio(p)
    if (h) setHoldings(Array.isArray(h) ? h : h.holdings || [])
    if (t) setTrades(Array.isArray(t) ? t : t.trades || [])
    if (s) setStatus(s)
    setLastUpdated(new Date())
  }, [])

  useEffect(() => {
    fetchAll()

    const interval = setInterval(() => {
      if (isMarketHours()) {
        fetchAll()
      }
    }, POLL_INTERVAL)

    return () => clearInterval(interval)
  }, [fetchAll])

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-navy text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            <span className="mr-2">🕌</span>Halal Trader Dashboard
          </h1>
          <div className="text-right text-sm">
            <div className="flex items-center gap-2">
              <span className={`inline-block w-2 h-2 rounded-full ${
                status?.active ? 'bg-green-400 animate-pulse' : 'bg-gray-400'
              }`} />
              <span>{status?.active ? 'Trading Active' : 'Market Closed'}</span>
            </div>
            {lastUpdated && (
              <p className="text-gray-300 text-xs mt-1">
                Updated {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
        </div>
      </header>

      {/* Compliance Alert */}
      <ComplianceAlert holdings={holdings} />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Portfolio Summary */}
        <PortfolioSummary portfolio={portfolio} />

        {/* Holdings + Chart */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2">
            <HoldingsTable
              holdings={holdings}
              selectedTicker={selectedTicker}
              onSelectTicker={setSelectedTicker}
            />
          </div>
          <div className="xl:col-span-1">
            <PriceChart ticker={selectedTicker} />
          </div>
        </div>

        {/* Portfolio Allocator */}
        <AllocatorPanel />

        {/* Trade Log */}
        <TradeLog trades={trades} />
      </main>

      {/* Footer */}
      <footer className="bg-navy text-gray-400 text-center text-xs py-4 mt-8">
        Sharia-Compliant Automated Trading System &mdash; All trades screened for halal compliance
      </footer>
    </div>
  )
}
