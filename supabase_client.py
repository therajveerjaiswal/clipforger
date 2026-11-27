from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

_supabase_admin_client: Optional[Client] = None


def get_supabase_admin() -> Client:
    """
    Lazy singleton initialization: prevents application startup crashes
    if environment variables are still being configured.
    """
    global _supabase_admin_client
    if _supabase_admin_client is None:
        url = settings.NEXT_PUBLIC_SUPABASE_URL or "https://placeholder.supabase.co"
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.NEXT_PUBLIC_SUPABASE_ANON_KEY or "placeholder-key"
        _supabase_admin_client = create_client(
            supabase_url=url,
            supabase_key=key,
        )
    return _supabase_admin_client
