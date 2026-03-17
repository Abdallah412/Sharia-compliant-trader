import { Bell, Settings, Wifi, WifiOff, Bot } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function TopBar({
  status,
  lastUpdated,
  notificationCount = 0,
  onNotificationClick,
  onSettingsClick,
}) {
  const tradingMode = status?.trading_mode || 'paper';
  const isLive = tradingMode === 'live';
  const schwabConnected = status?.schwab_connected ?? false;
  const botActive = status?.bot_active ?? false;

  const updatedText = lastUpdated
    ? `Updated ${formatDistanceToNow(lastUpdated, { addSuffix: false })} ago`
    : 'Connecting...';

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-card border-b border-border-main shrink-0">
      {/* Left: Branding */}
      <div className="flex items-center gap-3">
        <span className="text-brand-gold text-sm leading-tight" dir="rtl">
          بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ
        </span>
        <span className="font-display font-bold text-xl text-text-primary tracking-wide">
          HALAL TRADER
        </span>
      </div>

      {/* Center: Status Pills */}
      <div className="hidden md:flex items-center gap-3">
        {/* Trading Mode Pill */}
        {isLive ? (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-gain/10 text-gain text-xs font-semibold uppercase">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-gain opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-gain" />
            </span>
            Live
          </span>
        ) : (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-doubtful/10 text-doubtful text-xs font-semibold uppercase">
            <span className="h-2 w-2 rounded-full bg-doubtful" />
            Paper
          </span>
        )}

        {/* Schwab Connection Pill */}
        <span
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
            schwabConnected
              ? 'bg-gain/10 text-gain'
              : 'bg-loss/10 text-loss'
          }`}
        >
          {schwabConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
          Schwab
        </span>

        {/* Bot Status Pill */}
        <span
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
            botActive
              ? 'bg-brand-teal/10 text-brand-teal-light'
              : 'bg-text-dim/20 text-text-muted'
          }`}
        >
          <Bot size={14} />
          {botActive ? 'Bot Active' : 'Bot Paused'}
        </span>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-4">
        <span className="text-xs text-text-muted hidden sm:block">{updatedText}</span>

        {/* Notification Bell */}
        <button
          onClick={onNotificationClick}
          className="relative p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-hover transition"
          aria-label="Notifications"
        >
          <Bell size={20} />
          {notificationCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center h-4 min-w-[1rem] px-1 rounded-full bg-loss text-white text-[10px] font-bold">
              {notificationCount > 99 ? '99+' : notificationCount}
            </span>
          )}
        </button>

        {/* Settings Gear */}
        <button
          onClick={onSettingsClick}
          className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-hover transition"
          aria-label="Settings"
        >
          <Settings size={20} />
        </button>
      </div>
    </header>
  );
}
