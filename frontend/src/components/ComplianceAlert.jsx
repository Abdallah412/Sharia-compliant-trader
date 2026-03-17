export default function ComplianceAlert({ holdings }) {
  if (!holdings || holdings.length === 0) return null

  const haramHoldings = holdings.filter((h) => {
    const s = (h.halal_status || '').toUpperCase()
    return s === 'HARAM' || s === 'NON_COMPLIANT'
  })

  const doubtfulHoldings = holdings.filter((h) => {
    const s = (h.halal_status || '').toUpperCase()
    return s === 'DOUBTFUL' || s === 'REVIEW'
  })

  if (haramHoldings.length === 0 && doubtfulHoldings.length === 0) return null

  return (
    <div className="sticky top-0 z-50">
      {haramHoldings.length > 0 && (
        <div className="bg-red-600 text-white px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center gap-3">
            <span className="text-lg flex-shrink-0">&#9888;</span>
            <p className="text-sm font-medium">
              <strong>HARAM ALERT:</strong>{' '}
              {haramHoldings.map((h) => h.ticker).join(', ')}{' '}
              {haramHoldings.length === 1 ? 'is' : 'are'} non-compliant.
              Immediate liquidation recommended.
            </p>
          </div>
        </div>
      )}
      {doubtfulHoldings.length > 0 && (
        <div className="bg-amber-500 text-white px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center gap-3">
            <span className="text-lg flex-shrink-0">&#9888;</span>
            <p className="text-sm font-medium">
              <strong>REVIEW NEEDED:</strong>{' '}
              {doubtfulHoldings.map((h) => h.ticker).join(', ')}{' '}
              {doubtfulHoldings.length === 1 ? 'requires' : 'require'} Sharia compliance review.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
