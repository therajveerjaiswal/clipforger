'use client';

import { useState, useEffect } from 'react';
import FingerprintJS from '@fingerprintjs/fingerprintjs';

let cachedVisitorId: string | null = null;

export function useDeviceFingerprint() {
  const [visitorId, setVisitorId] = useState<string>(cachedVisitorId || '');
  const [loading, setLoading] = useState<boolean>(!cachedVisitorId);

  useEffect(() => {
    if (cachedVisitorId) {
      setVisitorId(cachedVisitorId);
      setLoading(false);
      return;
    }

    let isMounted = true;

    async function getFingerprint() {
      try {
        const fp = await FingerprintJS.load();
        const result = await fp.get();
        if (isMounted) {
          cachedVisitorId = result.visitorId;
          setVisitorId(result.visitorId);
          setLoading(false);
        }
      } catch (err) {
        console.warn('FingerprintJS load error, using fallback:', err);
        // Fallback random storage-backed client token
        const fallback = localStorage.getItem('cf_device_token') || `dev_${Math.random().toString(36).substring(2, 15)}`;
        localStorage.setItem('cf_device_token', fallback);
        if (isMounted) {
          cachedVisitorId = fallback;
          setVisitorId(fallback);
          setLoading(false);
        }
      }
    }

    getFingerprint();

    return () => {
      isMounted = false;
    };
  }, []);

  return { visitorId, loading };
}
