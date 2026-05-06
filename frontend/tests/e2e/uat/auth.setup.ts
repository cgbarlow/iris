/**
 * v5.5.0 (issue #46/#37 reopen): UAT auth setup.
 *
 * Runs once per `npm run test:uat` invocation. Signs in as the dedicated
 * tester account at https://iris-uat.chrisbarlow.nz and persists the
 * authenticated browser state to disk so each verification spec reuses
 * the same session without re-authenticating.
 */

import { test as setup } from '@playwright/test';
import { existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { TESTER_USERNAME, TESTER_PASSWORD } from '../fixtures';

const STORAGE_STATE_PATH = 'tests/e2e/uat/.auth/tester.json';

setup('sign in as tester', async ({ page }) => {
	// Make sure the .auth/ dir exists before storageState() writes to it.
	const dir = dirname(STORAGE_STATE_PATH);
	if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

	await page.goto('/login');
	// v5.5.3: wait for the form to hydrate (Svelte mounts client-side),
	// then pick the right user field — UAT (Supabase mode) labels it
	// "Email" via ARIA; SQLite mode labels it "Username".
	await page.getByRole('button', { name: 'Sign in' }).waitFor({ timeout: 15_000 });
	const emailField = page.getByRole('textbox', { name: /^Email$/i });
	const usernameField = page.getByRole('textbox', { name: /^Username$/i });
	const userField = (await emailField.count()) ? emailField.first() : usernameField.first();
	await userField.fill(TESTER_USERNAME);
	await page.locator('input[type="password"]').first().fill(TESTER_PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await page.waitForURL('/', { timeout: 30_000 });
	await page.getByRole('heading', { name: 'Dashboard' }).waitFor({ timeout: 15_000 });

	await page.context().storageState({ path: STORAGE_STATE_PATH });
});
