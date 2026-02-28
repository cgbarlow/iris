import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		host: '0.0.0.0',
		proxy: {
			'/api': 'http://localhost:8000',
			'/health': 'http://localhost:8000',
		},
		allowedHosts: true,
	},
	preview: {
		proxy: {
			'/api': 'http://localhost:8000',
			'/health': 'http://localhost:8000',
		},
		allowedHosts: true,
	},
	test: {
		include: ['tests/unit/**/*.test.ts'],
		environment: 'jsdom',
	},
});
