'use client';

import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useDeviceFingerprint } from './useDeviceFingerprint';
import { QuotaStatus } from '@/types';
import { getBackendUrl } from '@/lib/utils';

export function useQuota() {
  const { visitorId } = useDeviceFingerprint();
  const [quota, setQuota] = useState<QuotaStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchQuota = useCallback(async () => {
    if (!visitorId) return;

    try {
      const session = (await supabase.auth.getSession()).data.session;
      if (!session) {
        setQuota(null);
        setLoading(false);
        return;
      }

      const backendUrl = getBackendUrl();
      const res = await fetch(`${backendUrl}/api/v1/quota/status`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'X-Device-Fingerprint': visitorId,
        },
      });

      if (res.ok) {
        const data = await res.json();
        setQuota(data);
      }
    } catch (err) {
      console.error('Error fetching quota:', err);
    } finally {
      setLoading(false);
    }
  }, [visitorId]);

  useEffect(() => {
    fetchQuota();

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        fetchQuota();
      } else {
        setQuota(null);
      }
    });

    return () => {
      listener.subscription.unsubscribe();
    };
  }, [fetchQuota]);

  return { quota, loading, refetchQuota: fetchQuota };
}
