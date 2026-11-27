import { supabase } from '@/lib/supabaseClient';
import { getBackendUrl } from '@/lib/utils';

/**
 * Opens the clip and records the download.
 *
 * The window must be opened synchronously inside the click handler: browsers (notably Safari and mobile
 * browsers) block `window.open` once an `await` has happened, which made the Download button silently do
 * nothing. The analytics call is therefore fire-and-forget.
 */
export function openClipDownload(clip: { id: string; public_url?: string | null }): void {
  if (clip.public_url) {
    window.open(clip.public_url, '_blank', 'noopener,noreferrer');
  }

  void (async () => {
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      if (!token) return;
      await fetch(`${getBackendUrl()}/api/v1/clips/${clip.id}/download`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (err) {
      console.warn('Could not record download:', err);
    }
  })();
}
