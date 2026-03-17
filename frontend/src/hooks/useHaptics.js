import { useCallback } from 'react';
import { usePlatform } from './usePlatform';

export function useHaptics() {
  const { isNative } = usePlatform();

  const impact = useCallback(async (style = 'light') => {
    if (!isNative) return;
    try {
      const { Haptics, ImpactStyle } = await import('@capacitor/haptics');
      const styleMap = {
        light: ImpactStyle.Light,
        medium: ImpactStyle.Medium,
        heavy: ImpactStyle.Heavy,
      };
      await Haptics.impact({ style: styleMap[style] || ImpactStyle.Light });
    } catch {}
  }, [isNative]);

  const success = useCallback(async () => {
    if (!isNative) return;
    try {
      const { Haptics, NotificationType } = await import('@capacitor/haptics');
      await Haptics.notification({ type: NotificationType.Success });
    } catch {}
  }, [isNative]);

  const error = useCallback(async () => {
    if (!isNative) return;
    try {
      const { Haptics, NotificationType } = await import('@capacitor/haptics');
      await Haptics.notification({ type: NotificationType.Error });
    } catch {}
  }, [isNative]);

  return { impact, success, error };
}
