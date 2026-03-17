import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Moon } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-base flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Moon className="text-brand-gold mx-auto mb-3" size={32} />
          <h1 className="text-2xl font-bold text-text-primary">Welcome Back</h1>
          <p className="text-sm text-text-muted mt-1">Sign in to your Halal Trader account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-loss/10 border border-loss/30 text-loss text-sm">{error}</div>
          )}

          <div>
            <label className="block text-xs text-text-muted mb-1">Email</label>
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-bg-card border border-border-main text-text-primary text-sm focus:outline-none focus:border-brand-teal"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-xs text-text-muted mb-1">Password</label>
            <input
              type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-bg-card border border-border-main text-text-primary text-sm focus:outline-none focus:border-brand-teal"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit" disabled={loading}
            className="w-full py-2.5 rounded-lg bg-brand-teal text-white font-semibold text-sm hover:bg-brand-teal-light transition disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-sm text-text-muted mt-6">
          Don't have an account?{' '}
          <Link to="/register" className="text-brand-teal-light hover:underline">Create one</Link>
        </p>
        <p className="text-center mt-3">
          <Link to="/" className="text-xs text-text-muted hover:text-text-primary">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}
