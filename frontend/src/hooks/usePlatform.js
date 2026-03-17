import { useState, useEffect } from 'react';

export function usePlatform() {
  const [platform, setPlatform] = useState('web');

  useEffect(() => {
    // Detect Capacitor native platform
    if (window.Capacitor?.isNativePlatform()) {
      setPlatform(window.Capacitor.getPlatform()); // 'ios' or 'android'
    }
  }, []);

  return {
    platform,
    isNative: platform !== 'web',
    isIOS: platform === 'ios',
    isAndroid: platform === 'android',
    isWeb: platform === 'web',
  };
}
