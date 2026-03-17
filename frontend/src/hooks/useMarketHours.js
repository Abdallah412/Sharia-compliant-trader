import { useState, useEffect } from 'react';

export function useMarketHours() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const check = () => {
      const now = new Date();
      const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
      const day = et.getDay();
      if (day === 0 || day === 6) { setIsOpen(false); return; }
      const mins = et.getHours() * 60 + et.getMinutes();
      setIsOpen(mins >= 570 && mins <= 960);
    };
    check();
    const interval = setInterval(check, 60000);
    return () => clearInterval(interval);
  }, []);

  return isOpen;
}
