import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Moon } from 'lucide-react';

export default function Register() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }
    setLoading(true);
    try {
      await register(email, password, fullName);
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
          <h1 className="text-2xl font-bold text-text-primary">Create Account</h1>
          <p className="text-sm text-text-muted mt-1">Start your halal investing journey</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-loss/10 border border-loss/30 text-loss text-sm">{error}</div>
          )}

          <div>
            <label className="block text-xs text-text-muted mb-1">Full Name</label>
            <input
              type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-bg-card border border-border-main text-text-primary text-sm focus:outline-none focus:border-brand-teal"
              placeholder="Your name"
            />
          </div>

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
              placeholder="Minimum 8 characters"
            />
          </div>

          <button
            type="submit" disabled={loading}
            className="w-full py-2.5 rounded-lg bg-brand-teal text-white font-semibold text-sm hover:bg-brand-teal-light transition disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <p className="text-center text-sm text-text-muted mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-brand-teal-light hover:underline">Sign in</Link>
        </p>
        <p className="text-center mt-3">
          <Link to="/" className="text-xs text-text-muted hover:text-text-primary">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}
