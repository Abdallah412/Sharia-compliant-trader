import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { CheckCircle, XCircle, Clock } from 'lucide-react';
import Disclaimer from '../components/Disclaimer';

export default function TraderInbox() {
  const { authFetch } = useAuth();
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchQueue = async () => {
    try {
      const res = await authFetch('/trader/queue');
      if (res.ok) {
        const data = await res.json();
        setQueue(data.queue || []);
      }
    } catch (e) {
      console.error('Failed to fetch queue:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchQueue(); }, []);

  const handleAction = async (reviewId, action) => {
    try {
      const res = await authFetch(`/trader/${action}/${reviewId}`, { method: 'POST' });
      if (res.ok) {
        setQueue(q => q.filter(r => r.id !== reviewId));
      }
    } catch (e) {
      console.error(`Failed to ${action}:`, e);
    }
  };

  if (loading) return <div className="text-text-muted p-8">Loading trader queue...</div>;

  return (
    <div>
      <h1 className="font-heading text-2xl font-bold text-text-primary mb-6">Trader Review Queue</h1>

      {queue.length === 0 ? (
        <div className="text-center py-16 text-text-muted">
          <Clock size={48} className="mx-auto mb-4 opacity-50" />
          <p>No pending reviews</p>
        </div>
      ) : (
        <div className="space-y-4">
          {queue.map((review) => (
            <div key={review.id} className="p-4 rounded-xl bg-bg-card border border-border-main">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span className="font-mono text-lg font-bold text-text-primary">
                    {review.signal?.ticker || 'Unknown'}
                  </span>
                  <span className="ml-2 text-xs text-text-muted">
                    {review.signal?.action || '?'} × {review.signal?.quantity || '?'}
                  </span>
                </div>
                <span className="text-xs text-text-muted">{new Date(review.created_at).toLocaleString()}</span>
              </div>

              {review.signal && (
                <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
                  <div className="p-2 rounded bg-bg-elevated">
                    <span className="text-text-muted">Sheikh:</span>{' '}
                    <span className="text-text-primary">{review.signal.sheikh_verdict || '?'}</span>
                  </div>
                  <div className="p-2 rounded bg-bg-elevated">
                    <span className="text-text-muted">Finance:</span>{' '}
                    <span className="font-mono text-text-primary">{review.signal.confidence || 0}%</span>
                  </div>
                  <div className="p-2 rounded bg-bg-elevated">
                    <span className="text-text-muted">Tax:</span>{' '}
                    <span className="text-text-primary">{review.signal.tax_verdict || '?'}</span>
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => handleAction(review.id, 'approve')}
                  className="flex items-center gap-1 px-4 py-2 rounded-lg bg-gain/20 text-gain text-sm font-semibold hover:bg-gain/30 transition"
                >
                  <CheckCircle size={16} /> Approve
                </button>
                <button
                  onClick={() => handleAction(review.id, 'reject')}
                  className="flex items-center gap-1 px-4 py-2 rounded-lg bg-loss/20 text-loss text-sm font-semibold hover:bg-loss/30 transition"
                >
                  <XCircle size={16} /> Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <Disclaimer />
    </div>
  );
}
