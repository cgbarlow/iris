import { defineConfig } from '@playwright/test';

export default defineConfig({
	testDir: 'tests/e2e',
	timeout: 30_000,
	retries: 1,
	use: {
		baseURL: 'http://localhost:4173',
		actionTimeout: 10_000,
		trace: 'on-first-retry',
	},
	projects: [
		{ name: 'chromium', use: { browserName: 'chromium' } },
	],
	webServer: [
		{
			command: 'cd ../backend && uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000',
			port: 8000,
			reuseExistingServer: true,
			timeout: 15_000,
		},
		{
			command: 'npm run build && npm run preview',
			port: 4173,
			reuseExistingServer: true,
			timeout: 30_000,
		},
	],
});
