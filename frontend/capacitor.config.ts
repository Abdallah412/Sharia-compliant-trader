import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.halaltrader.app',
  appName: 'Halal Trader',
  webDir: 'dist',
  plugins: {
    SplashScreen: {
      backgroundColor: '#080E14',
      launchAutoHide: true,
      launchShowDuration: 2000,
    },
    StatusBar: {
      style: 'dark' as const,
      backgroundColor: '#0B2545',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
  },
};

export default config;
