'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { useDeviceFingerprint } from './useDeviceFingerprint';
import { QuotaStatus } from '@/types';
import { getBackendUrl } from '@/lib/utils';

interface QuotaContextValue {
  quota: QuotaStatus | null;
  loading: boolean;
  refetchQuota: () => Promise<void>;
}

const QuotaContext = createContext<QuotaContextValue>({
  quota: null,
  loading: true,
  refetchQuota: async () => {},
});

/**
 * Single source of truth for the signed-in user's quota. Mounted once in the root layout so the header badge,
 * ad slots, input form and pricing page all share one request and update together (previously every component
 * kept its own copy, so the header badge stayed stale after a job was submitted or a plan was bought).
 */
export function QuotaProvider({ children }: { children: React.ReactNode }) {
  const { visitorId } = useDeviceFingerprint();
  const [quota, setQuota] = useState<QuotaStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchQuota = useCallback(async () => {
    if (!visitorId) return;

    try {
      const session = (await supabase.auth.getSession()).data.session;
      if (!session) {
        setQuota(null);
        return;
      }

      const res = await fetch(`${getBackendUrl()}/api/v1/quota/status`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'X-Device-Fingerprint': visitorId,
        },
      });

      if (res.ok) {
        setQuota(await res.json());
      }
    } catch (err) {
      console.error('Error fetching quota:', err);
    } finally {
      setLoading(false);
    }
  }, [visitorId]);

  useEffect(() => {
    fetchQuota();

    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (!session) {
        setQuota(null);
      } else if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED' || event === 'USER_UPDATED') {
        // INITIAL_SESSION is skipped: the fetch above already covers it.
        fetchQuota();
      }
    });

    return () => {
      listener.subscription.unsubscribe();
    };
  }, [fetchQuota]);

  const value = useMemo(() => ({ quota, loading, refetchQuota: fetchQuota }), [quota, loading, fetchQuota]);

  return <QuotaContext.Provider value={value}>{children}</QuotaContext.Provider>;
}

export function useQuota() {
  return useContext(QuotaContext);
}
