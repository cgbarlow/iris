/** Supabase client — only initialised when VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are set. */

import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { SUPABASE_URL, SUPABASE_ANON_KEY } from '$lib/config.js';

export const supabase: SupabaseClient | null =
	SUPABASE_URL && SUPABASE_ANON_KEY
		? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
		: null;
