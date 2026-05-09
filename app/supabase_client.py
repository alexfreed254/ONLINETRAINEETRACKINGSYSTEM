from supabase import create_client, Client
from flask import current_app
import os


def get_supabase() -> Client:
    """Get Supabase client with anon key (respects RLS)."""
    url = current_app.config['SUPABASE_URL']
    key = current_app.config['SUPABASE_KEY']
    if not url or not key:
        raise RuntimeError('SUPABASE_URL and SUPABASE_KEY must be set in environment variables.')
    return create_client(url, key)


def get_supabase_admin() -> Client:
    """Get Supabase client with service role key (bypasses RLS).
    Raises RuntimeError with a clear message if the key is not configured.
    """
    url = current_app.config['SUPABASE_URL']
    key = current_app.config['SUPABASE_SERVICE_KEY']
    placeholder_values = {'', 'your-service-role-key-here', 'placeholder', None}
    if not url or key in placeholder_values:
        raise RuntimeError(
            'SUPABASE_SERVICE_KEY is not configured. '
            'Add it in Render → Environment → SUPABASE_SERVICE_KEY. '
            'Find it in Supabase Dashboard → Project Settings → API → service_role.'
        )
    try:
        return create_client(url, key)
    except Exception as e:
        raise RuntimeError(f'Failed to create Supabase admin client: {e}') from e
