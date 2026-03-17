import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  ArrowRightLeft,
  ShieldAlert,
  AlertTriangle,
  Receipt,
  Newspaper,
  Heart,
  Bell,
} from 'lucide-react';

const TYPE_CONFIG = {
  trade_executed: {
    borderClass: 'border-l-gain',
    Icon: ArrowRightLeft,
    iconColor: 'text-gain',
  },
  stop_loss: {
    borderClass: 'border-l-loss',
    Icon: AlertTriangle,
    iconColor: 'text-loss',
  },
  compliance_alert: {
    borderClass: 'border-l-doubtful',
    Icon: ShieldAlert,
    iconColor: 'text-doubtful',
  },
  tax_warning: {
    borderClass: 'border-l-brand-gold',
    Icon: Receipt,
    iconColor: 'text-brand-gold',
  },
  news_trigger: {
    borderClass: 'border-l-brand-teal',
    Icon: Newspaper,
    iconColor: 'text-brand-teal',
  },
  zakat_reminder: {
    borderClass: 'border-l-brand-teal-light',
    Icon: Heart,
    iconColor: 'text-brand-teal-light',
  },
};

const DEFAULT_CONFIG = {
  borderClass: 'border-l-border-main',
  Icon: Bell,
  iconColor: 'text-text-muted',
};

function formatTimestamp(ts) {
  if (!ts) return '';
  const date = new Date(ts);
  const now = new Date();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

export default function NotificationPanel({ notifications = [], onClose, onClear }) {
  const [readIds, setReadIds] = useState(new Set());

  // Reset read state when notifications list changes significantly
  useEffect(() => {
    // keep existing read state
  }, [notifications]);

  const markAsRead = (id) => {
    setReadIds((prev) => new Set([...prev, id]));
  };

  return (
    <AnimatePresence>
      <motion.aside
        className="fixed top-0 right-0 z-30 w-96 h-full bg-bg-card border-l border-border-main overflow-y-auto"
        initial={{ x: 400 }}
        animate={{ x: 0 }}
        exit={{ x: 400 }}
        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-bg-card border-b border-border-main px-4 py-3 flex items-center justify-between z-10">
          <h2 className="text-text-primary font-semibold text-lg">Notifications</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={onClear}
              className="text-text-muted hover:text-text-primary text-sm transition-colors"
            >
              Clear All
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Notification List */}
        <div className="p-2">
          {notifications.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-text-muted">
              <Bell size={32} className="mb-3 opacity-40" />
              <p className="text-sm">No notifications</p>
            </div>
          )}

          {notifications.map((notif) => {
            const id = notif.id || notif.timestamp || Math.random();
            const isRead = readIds.has(id);
            const config = TYPE_CONFIG[notif.type] || DEFAULT_CONFIG;
            const { borderClass, Icon, iconColor } = config;

            return (
              <button
                key={id}
                onClick={() => markAsRead(id)}
                className={`w-full text-left p-3 rounded-lg mb-1 border-l-4 ${borderClass} bg-bg-elevated hover:bg-bg-hover transition-colors cursor-pointer`}
              >
                <div className="flex gap-3">
                  <div className={`mt-0.5 ${iconColor}`}>
                    <Icon size={16} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm leading-snug ${
                      isRead ? 'text-text-muted' : 'text-text-primary font-medium'
                    }`}>
                      {notif.message || notif.text}
                    </p>
                    <p className="text-text-dim text-xs mt-1">
                      {formatTimestamp(notif.timestamp || notif.created_at)}
                    </p>
                  </div>
                  {!isRead && (
                    <div className="mt-1.5">
                      <span className="block w-2 h-2 rounded-full bg-brand-teal" />
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </motion.aside>
    </AnimatePresence>
  );
}
