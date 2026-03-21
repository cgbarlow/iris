/**
 * Runtime deployment configuration.
 *
 * Set VITE_DB_BACKEND=supabase (and the Supabase vars below) for the optional
 * Supabase/Netlify cloud deployment. Leave unset to use the default SQLite mode.
 *
 * See docs/deployment-netlify-supabase.md for full setup instructions.
 */

export const DB_BACKEND: string = import.meta.env.VITE_DB_BACKEND ?? 'sqlite';

/** Supabase project URL — only required when DB_BACKEND === 'supabase'. */
export const SUPABASE_URL: string = import.meta.env.VITE_SUPABASE_URL ?? '';

/** Supabase anon/public key — only required when DB_BACKEND === 'supabase'. */
export const SUPABASE_ANON_KEY: string = import.meta.env.VITE_SUPABASE_ANON_KEY ?? '';
