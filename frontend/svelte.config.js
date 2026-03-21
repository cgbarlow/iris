import adapterAuto from '@sveltejs/adapter-auto';
import adapterStatic from '@sveltejs/adapter-static';

// Use static adapter on Netlify (SPA mode — all routing handled client-side).
// Fall back to adapter-auto for local dev / self-hosted.
const adapter = process.env.NETLIFY
	? adapterStatic({ fallback: 'index.html' })
	: adapterAuto();

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter
	}
};

export default config;
