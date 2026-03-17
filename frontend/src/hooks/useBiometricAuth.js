import { useCallback, useRef } from 'react';
import { usePlatform } from './usePlatform';

export function useBiometricAuth() {
  const { isNative } = usePlatform();
  const lastAuthRef = useRef(Date.now());

  const authenticate = useCallback(async (reason = 'Verify your identity') => {
    if (!isNative) return true; // Web: skip biometric

    try {
      const { BiometricAuth } = await import('@aparajita/capacitor-biometric-auth');

      const available = await BiometricAuth.checkBiometry();
      if (!available.isAvailable) return true; // No biometric hardware

      await BiometricAuth.authenticate({ reason, cancelTitle: 'Cancel' });
      lastAuthRef.current = Date.now();
      return true;
    } catch (e) {
      console.warn('Biometric auth failed:', e);
      return false;
    }
  }, [isNative]);

  const requireAuth = useCallback(async (reason) => {
    // Re-authenticate if >5 minutes since last auth
    const elapsed = Date.now() - lastAuthRef.current;
    if (elapsed > 5 * 60 * 1000) {
      return authenticate(reason);
    }
    return true;
  }, [authenticate]);

  return { authenticate, requireAuth };
}
