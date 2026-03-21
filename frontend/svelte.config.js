import adapterAuto from '@sveltejs/adapter-auto';
import adapterNetlify from '@sveltejs/adapter-netlify';

// Use Netlify adapter when deployed to Netlify (NETLIFY env var is set automatically).
// Fall back to adapter-auto for all other environments (local dev, self-hosted).
const adapter = process.env.NETLIFY ? adapterNetlify() : adapterAuto();

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter
	}
};

export default config;
