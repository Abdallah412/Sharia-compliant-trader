import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings as SettingsIcon,
  Link2,
  AlertTriangle,
  Eye,
  EyeOff,
  Send,
  Bell,
  Shield,
  DollarSign,
  Sliders,
} from 'lucide-react';

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.25 } },
};

const US_STATES = [
  'Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware',
  'Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky',
  'Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi',
  'Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico',
  'New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania',
  'Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont',
  'Virginia','Washington','West Virginia','Wisconsin','Wyoming',
];

const INCOME_BRACKETS = ['10', '12', '22', '24', '32', '35', '37'];
const FILING_STATUSES = [
  'Single',
  'Married Filing Jointly',
  'Married Filing Separately',
  'Head of Household',
];
const MADHABS = ['Hanafi', 'Maliki', "Shafi'i", 'Hanbali', 'AAOIFI Default'];

async function fetchJSON(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// Custom Toggle Switch
function Toggle({ checked, onChange, disabled = false }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-teal ${
        checked ? 'bg-brand-teal' : 'bg-bg-elevated'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span
        className={`inline-block h-4 w-4 rounded-full bg-white transition-transform duration-200 ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

// Section wrapper
function Section({ title, icon: Icon, children, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="bg-bg-card rounded-lg p-6 mb-4 border border-border-main"
    >
      <div className="flex items-center gap-2 mb-5">
        <Icon size={20} className="text-brand-teal" />
        <h2 className="text-text-primary text-lg font-semibold">{title}</h2>
      </div>
      {children}
    </motion.div>
  );
}

// Input styling
const inputClasses =
  'bg-bg-elevated border border-border-main text-text-primary rounded px-3 py-2 focus:ring-2 focus:ring-brand-teal focus:border-brand-teal outline-none transition-colors w-full';
const selectClasses =
  'bg-bg-elevated border border-border-main text-text-primary rounded px-3 py-2 focus:ring-2 focus:ring-brand-teal focus:border-brand-teal outline-none transition-colors w-full';

export default function Settings() {
  // Account
  const [schwabConnected, setSchwabConnected] = useState(false);
  const [tokenAgeDays, setTokenAgeDays] = useState(0);
  const [accountHash, setAccountHash] = useState('');

  // Trading
  const [dryRun, setDryRun] = useState(true);
  const [dryRunConfirmStep, setDryRunConfirmStep] = useState(0); // 0=idle, 1=warning shown
  const [autoExecute, setAutoExecute] = useState(false);
  const [maxUsd, setMaxUsd] = useState(1000);
  const [stopLoss, setStopLoss] = useState(8);
  const [takeProfitPartial, setTakeProfitPartial] = useState(50);
  const [takeProfitFull, setTakeProfitFull] = useState(100);

  // Tax
  const [incomeBracket, setIncomeBracket] = useState('22');
  const [filingStatus, setFilingStatus] = useState('Single');
  const [state, setState] = useState('California');

  // Notifications
  const [telegramConnected, setTelegramConnected] = useState(false);
  const [notifTradeAlerts, setNotifTradeAlerts] = useState(true);
  const [notifCompliance, setNotifCompliance] = useState(true);
  const [notifTaxWarnings, setNotifTaxWarnings] = useState(true);
  const [notifDailySummary, setNotifDailySummary] = useState(false);
  const [notifZakat, setNotifZakat] = useState(true);

  // Compliance
  const [madhab, setMadhab] = useState('AAOIFI Default');
  const [zoyaKey, setZoyaKey] = useState('');
  const [showZoyaKey, setShowZoyaKey] = useState(false);

  useEffect(() => {
    (async () => {
      const data = await fetchJSON('/api/settings');
      if (!data) return;
      if (data.schwab_connected != null) setSchwabConnected(data.schwab_connected);
      if (data.token_age_days != null) setTokenAgeDays(data.token_age_days);
      if (data.account_hash) setAccountHash(data.account_hash);
      if (data.dry_run != null) setDryRun(data.dry_run);
      if (data.auto_execute != null) setAutoExecute(data.auto_execute);
      if (data.max_usd != null) setMaxUsd(data.max_usd);
      if (data.stop_loss != null) setStopLoss(data.stop_loss);
      if (data.take_profit_partial != null) setTakeProfitPartial(data.take_profit_partial);
      if (data.take_profit_full != null) setTakeProfitFull(data.take_profit_full);
      if (data.income_bracket) setIncomeBracket(data.income_bracket);
      if (data.filing_status) setFilingStatus(data.filing_status);
      if (data.state) setState(data.state);
      if (data.telegram_connected != null) setTelegramConnected(data.telegram_connected);
      if (data.notifications) {
        const n = data.notifications;
        if (n.trade_alerts != null) setNotifTradeAlerts(n.trade_alerts);
        if (n.compliance != null) setNotifCompliance(n.compliance);
        if (n.tax_warnings != null) setNotifTaxWarnings(n.tax_warnings);
        if (n.daily_summary != null) setNotifDailySummary(n.daily_summary);
        if (n.zakat != null) setNotifZakat(n.zakat);
      }
      if (data.madhab) setMadhab(data.madhab);
      if (data.zoya_api_key) setZoyaKey(data.zoya_api_key);
    })();
  }, []);

  const handleDryRunToggle = () => {
    if (dryRun) {
      // Trying to turn OFF dry run (go live)
      if (dryRunConfirmStep === 0) {
        setDryRunConfirmStep(1); // Show warning
      } else if (dryRunConfirmStep === 1) {
        setDryRun(false);
        setDryRunConfirmStep(0);
      }
    } else {
      // Turning ON dry run (safe)
      setDryRun(true);
      setDryRunConfirmStep(0);
    }
  };

  const handleReauth = () => {
    window.location.href = '/api/auth/schwab';
  };

  const handleTestMessage = async () => {
    await fetch('/api/notifications/test', { method: 'POST' });
  };

  const maskedHash = accountHash
    ? `${'*'.repeat(Math.max(0, accountHash.length - 4))}${accountHash.slice(-4)}`
    : '****';

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit"
      className="min-h-screen bg-bg-base p-6 max-w-3xl mx-auto">

      {/* Page Header */}
      <div className="flex items-center gap-3 mb-6">
        <SettingsIcon size={28} className="text-brand-teal" />
        <h1 className="font-display text-2xl font-bold text-text-primary">Settings</h1>
      </div>

      {/* Section 1 — Account */}
      <Section title="Account" icon={Link2} delay={0.1}>
        <div className="space-y-4">
          {/* Connection status */}
          <div className="flex items-center gap-3">
            <span className={`w-3 h-3 rounded-full ${schwabConnected ? 'bg-gain' : 'bg-loss'}`} />
            <span className="text-text-primary">
              Schwab {schwabConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Token age */}
          <div className="flex items-center gap-2">
            <span className="text-text-muted text-sm">Token is {tokenAgeDays} days old</span>
            {tokenAgeDays > 5 && (
              <span className="flex items-center gap-1 text-doubtful text-xs">
                <AlertTriangle size={12} />
                Token may be stale
              </span>
            )}
          </div>

          {/* Re-authenticate */}
          <button
            onClick={handleReauth}
            className="bg-brand-teal text-white px-4 py-2 rounded font-medium hover:opacity-90 transition-opacity"
          >
            Re-authenticate
          </button>

          {/* Account hash */}
          <div className="text-sm">
            <span className="text-text-muted">Account Hash: </span>
            <span className="font-mono text-text-primary">{maskedHash}</span>
          </div>
        </div>
      </Section>

      {/* Section 2 — Trading Configuration */}
      <Section title="Trading Configuration" icon={Sliders} delay={0.2}>
        <div className="space-y-5">
          {/* DRY_RUN toggle */}
          <div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary font-medium">Dry Run Mode</p>
                <p className="text-text-muted text-xs mt-0.5">Simulate trades without real execution</p>
              </div>
              <Toggle checked={dryRun} onChange={handleDryRunToggle} />
            </div>

            <AnimatePresence>
              {dryRunConfirmStep === 1 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-3 p-3 bg-loss/10 border border-loss/30 rounded-lg"
                >
                  <p className="text-loss text-sm font-semibold flex items-center gap-2">
                    <AlertTriangle size={16} />
                    Are you sure? This will use REAL MONEY.
                  </p>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={handleDryRunToggle}
                      className="bg-loss text-white px-3 py-1.5 rounded text-sm font-medium hover:opacity-90"
                    >
                      Yes, go live
                    </button>
                    <button
                      onClick={() => setDryRunConfirmStep(0)}
                      className="bg-bg-elevated text-text-primary px-3 py-1.5 rounded text-sm border border-border-main hover:bg-bg-card"
                    >
                      Cancel
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {!dryRun && (
              <p className="text-loss text-xs mt-2 font-semibold flex items-center gap-1">
                <AlertTriangle size={12} />
                LIVE MODE — Real money is being used for trades
              </p>
            )}
          </div>

          {/* Auto-execute */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-primary font-medium">Auto-Execute Trades</p>
            </div>
            <Toggle checked={autoExecute} onChange={setAutoExecute} />
          </div>

          {/* Max USD */}
          <div>
            <label className="text-text-muted text-sm block mb-1">Max USD per Trade</label>
            <input
              type="number"
              value={maxUsd}
              onChange={(e) => setMaxUsd(Number(e.target.value))}
              className={`${inputClasses} font-mono max-w-xs`}
            />
          </div>

          {/* Stop-loss */}
          <div>
            <label className="text-text-muted text-sm block mb-1">Stop-Loss %</label>
            <input
              type="number"
              value={stopLoss}
              onChange={(e) => setStopLoss(Number(e.target.value))}
              className={`${inputClasses} font-mono max-w-xs`}
              step={0.5}
            />
          </div>

          {/* Take-profit */}
          <div className="grid grid-cols-2 gap-4 max-w-xs">
            <div>
              <label className="text-text-muted text-sm block mb-1">Take-Profit Partial %</label>
              <input
                type="number"
                value={takeProfitPartial}
                onChange={(e) => setTakeProfitPartial(Number(e.target.value))}
                className={`${inputClasses} font-mono`}
                step={1}
              />
            </div>
            <div>
              <label className="text-text-muted text-sm block mb-1">Take-Profit Full %</label>
              <input
                type="number"
                value={takeProfitFull}
                onChange={(e) => setTakeProfitFull(Number(e.target.value))}
                className={`${inputClasses} font-mono`}
                step={1}
              />
            </div>
          </div>
        </div>
      </Section>

      {/* Section 3 — Tax Settings */}
      <Section title="Tax Settings" icon={DollarSign} delay={0.3}>
        <div className="space-y-4">
          {/* Income bracket */}
          <div>
            <label className="text-text-muted text-sm block mb-1">Federal Income Bracket</label>
            <select
              value={incomeBracket}
              onChange={(e) => setIncomeBracket(e.target.value)}
              className={`${selectClasses} max-w-xs`}
            >
              {INCOME_BRACKETS.map((b) => (
                <option key={b} value={b}>{b}%</option>
              ))}
            </select>
          </div>

          {/* Filing status */}
          <div>
            <label className="text-text-muted text-sm block mb-1">Filing Status</label>
            <select
              value={filingStatus}
              onChange={(e) => setFilingStatus(e.target.value)}
              className={`${selectClasses} max-w-xs`}
            >
              {FILING_STATUSES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* State */}
          <div>
            <label className="text-text-muted text-sm block mb-1">State</label>
            <select
              value={state}
              onChange={(e) => setState(e.target.value)}
              className={`${selectClasses} max-w-xs`}
            >
              {US_STATES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>
      </Section>

      {/* Section 4 — Notifications */}
      <Section title="Notifications" icon={Bell} delay={0.4}>
        <div className="space-y-4">
          {/* Telegram status */}
          <div className="flex items-center gap-3">
            <span className={`w-3 h-3 rounded-full ${telegramConnected ? 'bg-gain' : 'bg-loss'}`} />
            <span className="text-text-primary">
              Telegram {telegramConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Test message */}
          <button
            onClick={handleTestMessage}
            className="flex items-center gap-2 bg-bg-elevated border border-border-main text-text-primary px-4 py-2 rounded font-medium hover:bg-bg-card transition-colors"
          >
            <Send size={16} />
            Send Test Message
          </button>

          {/* Notification toggles */}
          <div className="space-y-3 pt-2">
            {[
              { label: 'Trade Alerts', value: notifTradeAlerts, setter: setNotifTradeAlerts },
              { label: 'Compliance Alerts', value: notifCompliance, setter: setNotifCompliance },
              { label: 'Tax Warnings', value: notifTaxWarnings, setter: setNotifTaxWarnings },
              { label: 'Daily Summary', value: notifDailySummary, setter: setNotifDailySummary },
              { label: 'Zakat Reminders', value: notifZakat, setter: setNotifZakat },
            ].map(({ label, value, setter }) => (
              <div key={label} className="flex items-center justify-between">
                <span className="text-text-primary text-sm">{label}</span>
                <Toggle checked={value} onChange={setter} />
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* Section 5 — Compliance Preferences */}
      <Section title="Compliance Preferences" icon={Shield} delay={0.5}>
        <div className="space-y-5">
          {/* Madhab preference */}
          <div>
            <p className="text-text-muted text-sm mb-3">Madhab Preference</p>
            <div className="space-y-2">
              {MADHABS.map((m) => (
                <label
                  key={m}
                  className="flex items-center gap-3 cursor-pointer group"
                  onClick={() => setMadhab(m)}
                >
                  <div
                    className={`w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors ${
                      madhab === m
                        ? 'border-brand-teal bg-brand-teal'
                        : 'border-border-main bg-bg-elevated group-hover:border-brand-teal/50'
                    }`}
                  >
                    {madhab === m && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                  </div>
                  <span className="text-text-primary text-sm">{m}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Zoya API key */}
          <div>
            <label className="text-text-muted text-sm block mb-1">Zoya API Key</label>
            <div className="relative max-w-md">
              <input
                type={showZoyaKey ? 'text' : 'password'}
                value={zoyaKey}
                onChange={(e) => setZoyaKey(e.target.value)}
                placeholder="Enter your Zoya API key"
                className={`${inputClasses} pr-10`}
              />
              <button
                type="button"
                onClick={() => setShowZoyaKey(!showZoyaKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
              >
                {showZoyaKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
        </div>
      </Section>
    </motion.div>
  );
}
