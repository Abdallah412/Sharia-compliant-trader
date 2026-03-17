import { AnimatePresence, motion } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import { usePortfolio } from '../hooks/usePortfolio';
import TopBar from './TopBar';
import Sidebar from './Sidebar';

const pageTransition = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.2, ease: 'easeInOut' },
};

export default function Layout({
  children,
  notificationCount = 0,
  onNotificationClick,
  onSettingsClick,
}) {
  const location = useLocation();
  const { status, lastUpdated } = usePortfolio();

  return (
    <div className="flex h-screen overflow-hidden bg-bg-base">
      <Sidebar status={status} />

      <div className="flex flex-col flex-1 overflow-hidden">
        <TopBar
          status={status}
          lastUpdated={lastUpdated}
          notificationCount={notificationCount}
          onNotificationClick={onNotificationClick}
          onSettingsClick={onSettingsClick}
        />

        <main className="flex-1 overflow-y-auto p-6 pb-20 md:pb-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={pageTransition.initial}
              animate={pageTransition.animate}
              exit={pageTransition.exit}
              transition={pageTransition.transition}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
