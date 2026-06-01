import { defineConfig, devices } from '@playwright/test';
import { defineBddConfig } from 'playwright-bdd';

const bddTestDir = defineBddConfig({
	features: 'tests/bdd/features/**/*.feature',
	steps: ['tests/bdd/steps/**/*.ts'],
	outputDir: '.features-gen',
});

// v5.5.0 (issue #46/#37 reopen): the UAT verification suite drives the live
// UAT deployment at https://iris-uat.chrisbarlow.nz, signs in once via a
// setup project that persists storageState, then runs verification specs
// against that authenticated session. Run on demand only — `npm run test:uat`.
const UAT_BASE_URL = process.env.IRIS_UAT_URL ?? 'https://iris-uat.chrisbarlow.nz';
const UAT_STORAGE_STATE = 'tests/e2e/uat/.auth/tester.json';

// `npm run test:uat` sets PLAYWRIGHT_UAT=1 so we skip the local backend +
// vite preview servers — the suite drives a remote deployment and never
// touches localhost:4173 / localhost:8000.
const IS_UAT_RUN = process.env.PLAYWRIGHT_UAT === '1';

// Fast-iteration escape hatch: point the local `e2e` project at an already-
// running stack (e.g. the dev server on :5173 with HMR) by setting
// IRIS_E2E_BASE_URL. When set we skip the build+preview webServer entirely
// (the dev stack is assumed up, backend on :8000). Default behaviour —
// build + preview on :4173 — is unchanged.
const E2E_BASE_URL = process.env.IRIS_E2E_BASE_URL;

export default defineConfig({
	timeout: 30_000,
	retries: 1,
	workers: 1,
	use: {
		baseURL: E2E_BASE_URL ?? 'http://localhost:4173',
		actionTimeout: 10_000,
		trace: 'on-first-retry',
	},
	projects: [
		{
			name: 'e2e',
			testDir: 'tests/e2e',
			// Mobile specs run in the dedicated `mobile` project (Pixel 5 device);
			// keep them out of the desktop suite so the two stay disjoint.
			testIgnore: ['**/uat/**', '**/*.mobile.spec.ts'],
			use: { browserName: 'chromium' },
		},
		{
			// v6.41.0 (ADR-229): mobile-responsive verification. Pixel 5 device
			// descriptor (393×851, touch, mobile UA). Shares the same
			// localhost:4173 webServer as `e2e`; runs on demand via
			// `npm run test:mobile`. Specs are named *.mobile.spec.ts.
			name: 'mobile',
			testDir: 'tests/e2e',
			testMatch: /\.mobile\.spec\.ts$/,
			use: { ...devices['Pixel 5'] },
		},
		{
			name: 'bdd',
			testDir: bddTestDir,
			use: { browserName: 'chromium' },
		},
		{
			// Manual project — produces user-guide screenshots on demand.
			// Invoked via `npm run screenshots`, not part of test:e2e (SPEC-122-A).
			name: 'screenshots',
			testDir: 'tests/screenshots',
			use: { browserName: 'chromium', viewport: { width: 1280, height: 720 } },
			retries: 0,
		},
		{
			// v5.5.0: signs in once and persists storageState for the uat project.
			name: 'uat-setup',
			testDir: 'tests/e2e/uat',
			testMatch: /auth\.setup\.ts$/,
			use: {
				browserName: 'chromium',
				baseURL: UAT_BASE_URL,
				viewport: { width: 1440, height: 900 },
				// v5.5.3: ignore HTTPS errors so headless chromium without the
				// system CA bundle (e.g. minimal Linux / WSL2 with extracted
				// libs) can still drive the live UAT site.
				ignoreHTTPSErrors: true,
			},
		},
		{
			// v5.5.4: ensures a BPMN view exists on UAT for the suite to
			// drive (creates one in the "test" collection if none exists).
			name: 'uat-ensure-fixtures',
			testDir: 'tests/e2e/uat',
			testMatch: /ensure-.*\.setup\.ts$/,
			use: {
				browserName: 'chromium',
				baseURL: UAT_BASE_URL,
				storageState: UAT_STORAGE_STATE,
				viewport: { width: 1440, height: 900 },
				ignoreHTTPSErrors: true,
			},
			dependencies: ['uat-setup'],
		},
		{
			// v5.5.0: UAT verification suite — drives the live deployment to
			// confirm released fixes actually landed correctly.
			name: 'uat',
			testDir: 'tests/e2e/uat',
			testIgnore: /\.setup\.ts$/,
			use: {
				browserName: 'chromium',
				baseURL: UAT_BASE_URL,
				storageState: UAT_STORAGE_STATE,
				viewport: { width: 1440, height: 900 },
				screenshot: 'only-on-failure',
				ignoreHTTPSErrors: true,
			},
			dependencies: ['uat-ensure-fixtures'],
			retries: 0,
		},
	],
	webServer: IS_UAT_RUN || E2E_BASE_URL
		? undefined
		: [
				{
					command: 'bash scripts/start-test-backend.sh',
					port: 8000,
					reuseExistingServer: true,
					timeout: 15_000,
				},
				{
					// VITE_IRIS_DEBUG is inlined at build time (Vite replaces
					// import.meta.env.VITE_*), so it must be set on `vite build`, not
					// preview. Enables the window.__irisGraph hook used by
					// knowledge-graph-spread.spec.ts (SPEC-118-A).
					command: 'VITE_IRIS_DEBUG=1 npm run build && npm run preview',
					port: 4173,
					reuseExistingServer: true,
					timeout: 30_000,
				},
			],
});
