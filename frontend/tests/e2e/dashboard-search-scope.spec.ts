/**
 * Dashboard search scope regression test (ADR-121 / issues #16, #17).
 *
 * Reproduces the UAT bug where the dashboard search silently filters by a
 * sessionStorage-persisted set id after the user returns to the dashboard
 * root `/` without any URL params. The search appears broken because the
 * UI shows no visible filter.
 *
 * Pre-fix expectation: searching for a term unique to set B while
 * sessionStorage holds set A's id returns zero results.
 *
 * Post-fix expectation: the same search returns set B's matching entity
 * because `handleSearch()` reads scope from URL params only, ignoring
 * sessionStorage for global dashboard search.
 */

import { expect, test } from '@playwright/test';
import {
	createCollection,
	createPackage,
	createSet,
	getAuthToken,
	loginAsAdmin,
	seedAdmin,
} from './fixtures';

// Unique per run — collection/set names have DB uniqueness constraints.
const RUN_TAG = Math.random().toString(36).slice(2, 8);
const UNIQUE_A = `alphaberetseed${RUN_TAG}`;
const UNIQUE_B = `betacharliezed${RUN_TAG}`;

test.describe('Dashboard search scope (ADR-121)', () => {
	test.describe.configure({ timeout: 120_000 });

	test('global search on / returns results from every set even when sessionStorage holds another set id', async ({
		page,
		baseURL,
	}) => {
		await seedAdmin(baseURL);
		const token = await getAuthToken(baseURL);

		const collection = await createCollection(baseURL, token, {
			name: `Search Scope Regression ${RUN_TAG}`,
		});
		const collectionId = collection.id as string;

		const setA = await createSet(baseURL, token, {
			name: `Alpha Set ${RUN_TAG}`,
			collection_id: collectionId,
		});
		const setB = await createSet(baseURL, token, {
			name: `Beta Set ${RUN_TAG}`,
			collection_id: collectionId,
		});

		await createPackage(baseURL, token, {
			name: `${UNIQUE_A} package`,
			set_id: setA.id as string,
		});
		await createPackage(baseURL, token, {
			name: `${UNIQUE_B} package`,
			set_id: setB.id as string,
		});

		await loginAsAdmin(page);

		// Visit set A via URL param — this populates sessionStorage via
		// setActiveSet() so that a subsequent visit to `/` without params
		// carries the stale filter.
		await page.goto(`/?set_id=${setA.id}`);
		await page.getByRole('heading', { name: 'Dashboard' }).waitFor();
		// Wait long enough for loadDashboard → setActiveSet to fire.
		await page.waitForTimeout(1_000);
		await expect
			.poll(async () => page.evaluate(() => sessionStorage.getItem('iris-active-set')))
			.toContain(setA.id as string);

		// Navigate back to `/` WITHOUT any URL params. sessionStorage still
		// holds set A's id; the bug is that search silently scopes to it.
		await page.goto('/');
		await page.getByRole('heading', { name: 'Dashboard' }).waitFor();

		// Type set B's unique search term. Debounce is 300 ms; we poll for
		// results to appear rather than assume immediate settle.
		const input = page.getByPlaceholder('Search elements and diagrams...');
		await input.fill(UNIQUE_B);

		// Give the 300 ms debounce + API round-trip time to resolve.
		await page.waitForTimeout(1_500);

		const resultCount = await page
			.getByText(/result/i)
			.first()
			.textContent();

		// Post-fix assertion: set B's package must appear in results. The
		// UI renders `<p>N result(s)</p>` when there are hits.
		expect(
			resultCount,
			'search with no URL params must return results from every set, not silently filter by sessionStorage',
		).toMatch(/\b[1-9]\d* result/);

		// And the package name should be visible.
		await expect(
			page.getByText(`${UNIQUE_B} package`, { exact: false }).first(),
		).toBeVisible();
	});
});
