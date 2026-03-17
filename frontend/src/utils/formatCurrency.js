export function formatCurrency(value) {
  if (value == null || isNaN(value)) return '$0.00';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

export function formatPct(value, includeSign = true) {
  if (value == null || isNaN(value)) return '0.00%';
  const sign = includeSign && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function pnlColor(value) {
  if (value > 0) return 'text-gain';
  if (value < 0) return 'text-loss';
  return 'text-text-muted';
}
