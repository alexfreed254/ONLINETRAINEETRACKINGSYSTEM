from supabase import create_client, Client
from flask import current_app
import os


def get_supabase() -> Client:
    """Get Supabase client with anon key (respects RLS)."""
    url = current_app.config['SUPABASE_URL']
    key = current_app.config['SUPABASE_KEY']
    return create_client(url, key)


def get_supabase_admin() -> Client:
    """Get Supabase client with service role key (bypasses RLS)."""
    url = current_app.config['SUPABASE_URL']
    key = current_app.config['SUPABASE_SERVICE_KEY']
    return create_client(url, key)
