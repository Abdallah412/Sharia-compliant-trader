import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Search, TrendingUp, Settings } from 'lucide-react';

const tabs = [
  { icon: LayoutDashboard, label: 'Home', to: '/' },
  { icon: Briefcase, label: 'Portfolio', to: '/portfolio' },
  { icon: Search, label: 'Screen', to: '/screener' },
  { icon: TrendingUp, label: 'Charts', to: '/charts' },
  { icon: Settings, label: 'More', to: '/settings' },
];

export default function MobileTabBar() {
  const location = useLocation();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-bg-card border-t border-border-main"
         style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
      <ul className="flex items-center justify-around py-2">
        {tabs.map(({ icon: Icon, label, to }) => {
          const isActive = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to);
          return (
            <li key={to}>
              <NavLink
                to={to}
                className={`flex flex-col items-center gap-0.5 px-2 py-1 text-[10px] transition ${
                  isActive ? 'text-brand-teal-light' : 'text-text-muted'
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
  );
}
