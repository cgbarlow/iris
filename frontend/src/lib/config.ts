/**
 * Runtime deployment configuration.
 *
 * Set VITE_DB_BACKEND=supabase (and the Supabase vars below) for the optional
 * Render + Supabase cloud deployment. Leave unset to use the default SQLite mode.
 *
 * See docs/deployment-render-supabase.md for full setup instructions.
 */

export const DB_BACKEND: string = import.meta.env.VITE_DB_BACKEND ?? 'sqlite';

/**
 * Base URL for backend API calls. Set to the Render Web Service URL
 * (e.g. https://iris-api.onrender.com) for cloud deployment.
 * Empty string (default) means relative paths — used in self-hosted SQLite mode.
 */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '';

/** Supabase project URL — only required when DB_BACKEND === 'supabase'. */
export const SUPABASE_URL: string = import.meta.env.VITE_SUPABASE_URL ?? '';

/** Supabase anon/public key — only required when DB_BACKEND === 'supabase'. */
export const SUPABASE_ANON_KEY: string = import.meta.env.VITE_SUPABASE_ANON_KEY ?? '';
