import { useEffect } from 'react';
import { usePlatform } from './usePlatform';
import { useAuth } from './useAuth';

const API_BASE = import.meta.env.VITE_API_URL || '';

export function usePushNotifs() {
  const { isNative } = usePlatform();
  const { token } = useAuth();

  useEffect(() => {
    if (!isNative || !token) return;

    let cleanup = () => {};

    (async () => {
      try {
        const { PushNotifications } = await import('@capacitor/push-notifications');

        const permResult = await PushNotifications.requestPermissions();
        if (permResult.receive !== 'granted') return;

        await PushNotifications.register();

        const regListener = await PushNotifications.addListener('registration', async (fcmToken) => {
          // Send FCM token to backend
          await fetch(`${API_BASE}/api/users/push-token`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              token: fcmToken.value,
              platform: window.Capacitor?.getPlatform() || 'web',
            }),
          });
        });

        const notifListener = await PushNotifications.addListener(
          'pushNotificationReceived',
          (notification) => {
            console.log('Push received:', notification);
          }
        );

        cleanup = () => {
          regListener.remove();
          notifListener.remove();
        };
      } catch (e) {
        console.warn('Push notifications not available:', e);
      }
    })();

    return () => cleanup();
  }, [isNative, token]);
}
