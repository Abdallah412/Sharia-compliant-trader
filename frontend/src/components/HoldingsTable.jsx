export default function HoldingsTable({ holdings, selectedTicker, onSelectTicker }) {
  if (!holdings || holdings.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-lg font-bold text-navy mb-4">Holdings</h2>
        <p className="text-gray-400 text-center py-8">No holdings to display</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-bold text-navy">Holdings</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-gray-500 text-xs uppercase tracking-wider">
              <th className="px-4 py-3 font-semibold">Ticker</th>
              <th className="px-4 py-3 font-semibold hidden sm:table-cell">Name</th>
              <th className="px-4 py-3 font-semibold text-right">Shares</th>
              <th className="px-4 py-3 font-semibold text-right">Price</th>
              <th className="px-4 py-3 font-semibold text-right hidden md:table-cell">Value</th>
              <th className="px-4 py-3 font-semibold text-right">P&L</th>
              <th className="px-4 py-3 font-semibold text-right hidden lg:table-cell">P&L%</th>
              <th className="px-4 py-3 font-semibold text-center">Halal</th>
              <th className="px-4 py-3 font-semibold text-right hidden lg:table-cell">Days</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {holdings.map((h) => {
              const isSelected = selectedTicker === h.ticker
              return (
                <tr
                  key={h.ticker}
                  onClick={() => onSelectTicker(h.ticker)}
                  className={`cursor-pointer transition-colors hover:bg-gray-50 ${
                    isSelected ? 'bg-blue-50 hover:bg-blue-50' : ''
                  }`}
                >
                  <td className="px-4 py-3 font-bold text-navy">{h.ticker}</td>
                  <td className="px-4 py-3 text-gray-600 hidden sm:table-cell truncate max-w-[160px]">
                    {h.name || '--'}
                  </td>
                  <td className="px-4 py-3 text-right">{h.shares}</td>
                  <td className="px-4 py-3 text-right">${Number(h.price || 0).toFixed(2)}</td>
                  <td className="px-4 py-3 text-right hidden md:table-cell">
                    ${Number(h.value || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </td>
                  <td className={`px-4 py-3 text-right font-medium ${
                    (h.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {(h.pnl || 0) >= 0 ? '+' : ''}${Number(h.pnl || 0).toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-right hidden lg:table-cell font-medium ${
                    (h.pnl_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {(h.pnl_pct || 0) >= 0 ? '+' : ''}{Number(h.pnl_pct || 0).toFixed(2)}%
                  </td>
                  <td className="px-4 py-3 text-center">
                    <HalalBadge status={h.halal_status} />
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500 hidden lg:table-cell">
                    {h.days_held ?? '--'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function HalalBadge({ status }) {
  const normalized = (status || '').toUpperCase()

  if (normalized === 'HALAL' || normalized === 'COMPLIANT') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-green-100 text-green-800">
        HALAL
      </span>
    )
  }
  if (normalized === 'REVIEW' || normalized === 'DOUBTFUL') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
        REVIEW
      </span>
    )
  }
  if (normalized === 'HARAM' || normalized === 'NON_COMPLIANT') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800">
        HARAM
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-gray-100 text-gray-500">
      {status || 'N/A'}
    </span>
  )
}
