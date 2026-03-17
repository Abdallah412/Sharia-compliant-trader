import { useState, useEffect, useCallback } from 'react';
import { useMarketHours } from './useMarketHours';

export function usePortfolio() {
  const [portfolio, setPortfolio] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [trades, setTrades] = useState([]);
  const [status, setStatus] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const isMarketOpen = useMarketHours();

  const fetchAll = useCallback(async () => {
    try {
      const results = await Promise.all([
        fetch('/api/portfolio').then(r => r.ok ? r.json() : null).catch(() => null),
        fetch('/api/holdings').then(r => r.ok ? r.json() : null).catch(() => null),
        fetch('/api/trades').then(r => r.ok ? r.json() : null).catch(() => null),
        fetch('/api/status').then(r => r.ok ? r.json() : null).catch(() => null),
        fetch('/api/decisions').then(r => r.ok ? r.json() : null).catch(() => null),
      ]);
      if (results[0]) setPortfolio(results[0]);
      if (results[1]) setHoldings(Array.isArray(results[1]) ? results[1] : results[1].holdings || []);
      if (results[2]) setTrades(Array.isArray(results[2]) ? results[2] : results[2].trades || []);
      if (results[3]) setStatus(results[3]);
      if (results[4]) setDecisions(Array.isArray(results[4]) ? results[4] : results[4].decisions || []);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch portfolio data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => {
      if (isMarketOpen) fetchAll();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchAll, isMarketOpen]);

  return { portfolio, holdings, trades, status, decisions, loading, lastUpdated, refetch: fetchAll };
}
