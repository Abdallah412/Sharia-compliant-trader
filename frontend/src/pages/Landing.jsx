import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, TrendingUp, Bot, Moon, ChevronRight } from 'lucide-react';

const features = [
  { icon: Shield, title: 'AAOIFI Compliant', desc: 'Five-screen Shariah screening based on Islamic finance standards' },
  { icon: Bot, title: 'AI-Powered Trading', desc: 'Four-agent pipeline: Sheikh, Finance Professor, Tax CPA, Orchestrator' },
  { icon: TrendingUp, title: '15-25% Target Returns', desc: 'EMA crossover signals with news sentiment and macro analysis' },
  { icon: Moon, title: 'Zakat & Purification', desc: 'Automatic zakat calculations and dividend purification tracking' },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-bg-base text-text-primary">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-border-main max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <Moon className="text-brand-gold" size={24} />
          <span className="text-lg font-bold">Halal Trader</span>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/login" className="text-sm text-text-muted hover:text-text-primary transition">Login</Link>
          <Link to="/register" className="px-4 py-2 rounded-lg bg-brand-teal text-white text-sm font-semibold hover:bg-brand-teal-light transition">
            Get Started Free
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <p className="text-brand-gold text-sm font-semibold mb-4 tracking-wide">بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</p>
          <h1 className="text-4xl md:text-6xl font-bold mb-6 leading-tight">
            Invest with <span className="text-brand-teal-light">Barakah</span>
          </h1>
          <p className="text-lg text-text-muted max-w-2xl mx-auto mb-8">
            AI-powered automated trading that respects Islamic principles.
            Shariah-screened stocks, tax optimization, and intelligent portfolio management.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link to="/register" className="px-6 py-3 rounded-lg bg-brand-teal text-white font-semibold hover:bg-brand-teal-light transition flex items-center gap-2">
              Start Free <ChevronRight size={18} />
            </Link>
            <Link to="/pricing" className="px-6 py-3 rounded-lg border border-border-light text-text-muted hover:text-text-primary hover:border-text-muted transition">
              View Pricing
            </Link>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-2 gap-6">
          {features.map(({ icon: Icon, title, desc }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
              className="p-6 rounded-xl bg-bg-card border border-border-main hover:border-brand-teal/30 transition"
            >
              <Icon className="text-brand-teal-light mb-3" size={28} />
              <h3 className="text-lg font-semibold mb-2">{title}</h3>
              <p className="text-sm text-text-muted">{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-6 py-16 text-center">
        <div className="p-8 rounded-2xl bg-bg-card border border-border-main">
          <h2 className="text-2xl font-bold mb-4">Start with $500. Grow with tawakkul.</h2>
          <p className="text-text-muted mb-6">Free tier includes 5 Shariah screens per day. Upgrade for automated trading.</p>
          <Link to="/register" className="px-6 py-3 rounded-lg bg-brand-teal text-white font-semibold hover:bg-brand-teal-light transition">
            Create Free Account
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border-main py-8 text-center text-xs text-text-muted">
        <p>This is not financial or religious advice. Consult a qualified advisor and Islamic scholar.</p>
        <p className="mt-2">Built with tawakkul. May your rizq be halal and barakah.</p>
      </footer>
    </div>
  );
}
