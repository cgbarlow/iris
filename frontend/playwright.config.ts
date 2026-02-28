import { defineConfig } from '@playwright/test';
import { defineBddConfig } from 'playwright-bdd';

const bddTestDir = defineBddConfig({
	features: 'tests/bdd/features/**/*.feature',
	steps: ['tests/bdd/steps/**/*.ts'],
	outputDir: '.features-gen',
});

export default defineConfig({
	timeout: 30_000,
	retries: 1,
	workers: 1,
	use: {
		baseURL: 'http://localhost:4173',
		actionTimeout: 10_000,
		trace: 'on-first-retry',
	},
	projects: [
		{
			name: 'e2e',
			testDir: 'tests/e2e',
			use: { browserName: 'chromium' },
		},
		{
			name: 'bdd',
			testDir: bddTestDir,
			use: { browserName: 'chromium' },
		},
	],
	webServer: [
		{
			command: 'bash scripts/start-test-backend.sh',
			port: 8000,
			reuseExistingServer: false,
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
