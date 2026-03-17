export default function PortfolioSummary({ portfolio }) {
  if (!portfolio) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-xl shadow p-5 animate-pulse">
            <div className="h-3 bg-gray-200 rounded w-24 mb-3" />
            <div className="h-7 bg-gray-200 rounded w-32" />
          </div>
        ))}
      </div>
    )
  }

  const {
    total_value = 0,
    day_pnl = 0,
    day_pnl_pct = 0,
    total_return_pct = 0,
    cash = 0,
  } = portfolio

  const cards = [
    {
      label: 'Portfolio Value',
      value: formatCurrency(total_value),
      color: 'text-navy',
    },
    {
      label: 'Day P&L',
      value: `${day_pnl >= 0 ? '+' : ''}${formatCurrency(day_pnl)}`,
      sub: `${day_pnl_pct >= 0 ? '+' : ''}${day_pnl_pct.toFixed(2)}%`,
      color: day_pnl >= 0 ? 'text-green-600' : 'text-red-600',
    },
    {
      label: 'Total Return',
      value: `${total_return_pct >= 0 ? '+' : ''}${total_return_pct.toFixed(2)}%`,
      color: total_return_pct >= 0 ? 'text-green-600' : 'text-red-600',
    },
    {
      label: 'Cash Available',
      value: formatCurrency(cash),
      color: 'text-navy',
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-xl shadow hover:shadow-md transition-shadow p-5"
        >
          <p className="text-sm text-gray-500 font-medium">{card.label}</p>
          <p className={`text-2xl font-bold mt-1 ${card.color}`}>{card.value}</p>
          {card.sub && (
            <p className={`text-sm mt-0.5 ${card.color}`}>{card.sub}</p>
          )}
        </div>
      ))}
    </div>
  )
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}
