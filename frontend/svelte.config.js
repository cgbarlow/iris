import adapterAuto from '@sveltejs/adapter-auto';
import adapterStatic from '@sveltejs/adapter-static';

// Use static adapter on Render or any Supabase cloud build (SPA mode — all routing client-side).
// Fall back to adapter-auto for local dev / self-hosted.
const adapter = (process.env.RENDER || process.env.VITE_DB_BACKEND === 'supabase')
	? adapterStatic({ fallback: 'index.html' })
	: adapterAuto();

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter
	}
};

export default config;
