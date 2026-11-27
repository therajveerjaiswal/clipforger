'use client';

import { useState, useEffect } from 'react';
import FingerprintJS from '@fingerprintjs/fingerprintjs';

let cachedVisitorId: string | null = null;
// Shared in-flight promise: every component using the hook awaits the same single FingerprintJS load.
let pendingFingerprint: Promise<string> | null = null;

function loadFingerprint(): Promise<string> {
  if (cachedVisitorId) return Promise.resolve(cachedVisitorId);
  if (pendingFingerprint) return pendingFingerprint;

  pendingFingerprint = (async () => {
    try {
      const fp = await FingerprintJS.load();
      const result = await fp.get();
      cachedVisitorId = result.visitorId;
    } catch (err) {
      console.warn('FingerprintJS load error, using fallback:', err);
      // Fallback random storage-backed client token
      let fallback: string | null = null;
      try {
        fallback = localStorage.getItem('cf_device_token');
      } catch {
        // storage unavailable (private mode / blocked): keep an in-memory token for this page view
      }
      if (!fallback) {
        fallback = `dev_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 10)}`;
        try {
          localStorage.setItem('cf_device_token', fallback);
        } catch {
          // ignore
        }
      }
      cachedVisitorId = fallback;
    }
    return cachedVisitorId as string;
  })();

  return pendingFingerprint;
}

export function useDeviceFingerprint() {
  const [visitorId, setVisitorId] = useState<string>(cachedVisitorId || '');
  const [loading, setLoading] = useState<boolean>(!cachedVisitorId);

  useEffect(() => {
    let isMounted = true;

    loadFingerprint().then((id) => {
      if (isMounted) {
        setVisitorId(id);
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  return { visitorId, loading };
}
