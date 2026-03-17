export default function TradeLog({ trades }) {
  const recent = (trades || []).slice(0, 20)

  return (
    <div className="bg-white rounded-xl shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-bold text-navy">Trade Log</h2>
      </div>

      {recent.length === 0 ? (
        <p className="text-gray-400 text-center py-8 text-sm">No trades recorded</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-gray-500 text-xs uppercase tracking-wider">
                <th className="px-4 py-3 font-semibold">Time</th>
                <th className="px-4 py-3 font-semibold">Ticker</th>
                <th className="px-4 py-3 font-semibold">Side</th>
                <th className="px-4 py-3 font-semibold text-right">Qty</th>
                <th className="px-4 py-3 font-semibold text-right">Price</th>
                <th className="px-4 py-3 font-semibold text-right hidden sm:table-cell">P&L</th>
                <th className="px-4 py-3 font-semibold hidden md:table-cell">Sheikh Verdict</th>
                <th className="px-4 py-3 font-semibold text-right hidden lg:table-cell">Tax Impact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recent.map((t, i) => (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">
                    {formatTimestamp(t.timestamp)}
                  </td>
                  <td className="px-4 py-3 font-bold text-navy">{t.ticker}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${
                      (t.side || t.action || '').toUpperCase() === 'BUY'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {(t.side || t.action || '--').toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">{t.qty || t.quantity || '--'}</td>
                  <td className="px-4 py-3 text-right">
                    ${Number(t.price || 0).toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-right hidden sm:table-cell font-medium ${
                    (t.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {t.pnl != null
                      ? `${t.pnl >= 0 ? '+' : ''}$${Number(t.pnl).toFixed(2)}`
                      : '--'}
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className={`text-xs ${
                      (t.sheikh_verdict || t.verdict || '').toUpperCase().includes('HALAL')
                        ? 'text-green-600'
                        : (t.sheikh_verdict || t.verdict || '').toUpperCase().includes('HARAM')
                        ? 'text-red-600'
                        : 'text-gray-500'
                    }`}>
                      {t.sheikh_verdict || t.verdict || '--'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500 hidden lg:table-cell">
                    {t.tax_impact != null
                      ? `$${Number(t.tax_impact).toFixed(2)}`
                      : '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function formatTimestamp(ts) {
  if (!ts) return '--'
  const d = new Date(ts)
  if (isNaN(d)) return ts
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
