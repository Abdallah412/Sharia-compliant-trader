import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Briefcase,
  Search,
  Newspaper,
  TrendingUp,
  Receipt,
  Shield,
  Settings,
  Moon,
  Bot,
} from 'lucide-react';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', to: '/' },
  { icon: Briefcase, label: 'Portfolio', to: '/portfolio' },
  { icon: Search, label: 'Screener', to: '/screener' },
  { icon: Newspaper, label: 'News Feed', to: '/news' },
  { icon: TrendingUp, label: 'Charts', to: '/charts' },
  { icon: Receipt, label: 'Tax Center', to: '/tax' },
  { icon: Shield, label: 'Compliance', to: '/compliance' },
  { icon: Settings, label: 'Settings', to: '/settings' },
];

const mobileNavItems = navItems.slice(0, 5);

function BotStatusWidget({ status }) {
  const botActive = status?.bot_active ?? false;
  const lastRun = status?.last_run || null;
  const tradingMode = status?.trading_mode || 'paper';
  const isLive = tradingMode === 'live';

  return (
    <div className="mx-3 p-3 rounded-lg bg-bg-elevated border border-border-main">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Bot size={16} className="text-text-muted" />
          <span className="text-xs font-semibold text-text-primary">Bot Status</span>
        </div>
        <span
          className={`h-2.5 w-2.5 rounded-full ${
            botActive ? 'bg-gain' : 'bg-doubtful'
          }`}
        />
      </div>
      <p className="text-[11px] text-text-muted mb-2">
        {lastRun ? `Last run: ${lastRun}` : 'No recent activity'}
      </p>
      {isLive ? (
        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-gain/15 text-gain">
          Live
        </span>
      ) : (
        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-doubtful/15 text-doubtful">
          Paper Mode
        </span>
      )}
    </div>
  );
}

function ZakatReminder({ status }) {
  const zakatDueDays = status?.zakat_due_days ?? 30;
  const totalDays = status?.zakat_cycle_days ?? 354; // Islamic lunar year
  const progress = Math.max(0, Math.min(100, ((totalDays - zakatDueDays) / totalDays) * 100));

  return (
    <div className="mx-3 mt-2 p-3 rounded-lg bg-bg-elevated border border-border-main">
      <div className="flex items-center gap-2 mb-2">
        <Moon size={14} className="text-brand-gold" />
        <span className="text-xs font-semibold text-text-primary">Zakat Reminder</span>
      </div>
      <p className="text-[11px] text-text-muted mb-2">
        Zakat due in {zakatDueDays} days
      </p>
      <div className="w-full h-1.5 rounded-full bg-bg-hover overflow-hidden">
        <div
          className="h-full rounded-full bg-brand-gold transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

export default function Sidebar({ status }) {
  const location = useLocation();

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col w-60 bg-card border-r border-border-main h-full shrink-0">
        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          <ul className="space-y-0.5">
            {navItems.map(({ icon: Icon, label, to }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-2.5 text-sm transition ${
                      isActive
                        ? 'bg-bg-hover border-l-2 border-brand-teal text-brand-teal-light font-semibold'
                        : 'border-l-2 border-transparent text-text-muted hover:bg-bg-hover hover:text-text-primary'
                    }`
                  }
                >
                  <Icon size={18} />
                  <span>{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Bottom Widgets */}
        <div className="pb-4 space-y-2">
          <BotStatusWidget status={status} />
          <ZakatReminder status={status} />
        </div>
      </aside>

      {/* Mobile Bottom Nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-card border-t border-border-main">
        <ul className="flex items-center justify-around py-2">
          {mobileNavItems.map(({ icon: Icon, label, to }) => {
            const isActive =
              to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(to);

            return (
              <li key={to}>
                <NavLink
                  to={to}
                  className={`flex flex-col items-center gap-0.5 px-2 py-1 text-[10px] transition ${
                    isActive
                      ? 'text-brand-teal-light'
                      : 'text-text-muted'
                  }`}
                >
                  <Icon size={20} />
                  <span>{label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
