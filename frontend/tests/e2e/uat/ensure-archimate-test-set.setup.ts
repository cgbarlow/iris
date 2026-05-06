/**
 * v5.6.0 (issue #52): ensure an "ArchiMate Test" set exists on UAT for
 * the OEX import spec to drop the imported model into. Idempotent —
 * reuses the existing set if found, creates one under the "test"
 * collection otherwise. Writes the resolved set id to a JSON sidecar so
 * the import spec can read it without a second round-trip.
 */

import { test as setup } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';

const API = 'https://iris-api-gtb3.onrender.com';
const SIDECAR = 'tests/e2e/uat/.auth/archimate-set.json';

async function getToken(page: import('@playwright/test').Page): Promise<string | null> {
	return await page.evaluate(() => {
		for (let i = 0; i < localStorage.length; i++) {
			const k = localStorage.key(i);
			if (k && k.includes('auth-token')) {
				const raw = localStorage.getItem(k);
				if (raw) {
					try {
						const parsed = JSON.parse(raw);
						return parsed.access_token ?? null;
					} catch { /* ignore */ }
				}
			}
		}
		return null;
	});
}

setup('ensure ArchiMate test set exists', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('heading', { name: 'Dashboard' }).waitFor({ timeout: 15_000 });
	const token = await getToken(page);
	if (!token) throw new Error('No auth token in localStorage after login');
	const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

	// Find the "test" collection.
	const collectionsResp = await page.request.get(`${API}/api/collections?page_size=50`, { headers });
	if (!collectionsResp.ok()) throw new Error(`GET /api/collections failed: ${collectionsResp.status()}`);
	const collections = (await collectionsResp.json()).items ?? [];
	const testCollection = collections.find((c: { name: string }) => /test/i.test(c.name));
	if (!testCollection) throw new Error('No "test" collection found on UAT — manual setup required.');

	// Find or create the "ArchiMate Test" set under it.
	const setsResp = await page.request.get(
		`${API}/api/sets?collection_id=${testCollection.id}&page_size=50`,
		{ headers },
	);
	if (!setsResp.ok()) throw new Error(`GET /api/sets failed: ${setsResp.status()}`);
	const sets = (await setsResp.json()).items ?? [];
	let archimateSet = sets.find((s: { name: string }) => s.name === 'ArchiMate Test');
	if (!archimateSet) {
		const create = await page.request.post(`${API}/api/sets`, {
			headers,
			data: { name: 'ArchiMate Test', collection_id: testCollection.id },
		});
		if (!create.ok()) {
			throw new Error(`POST /api/sets failed: ${create.status()} ${await create.text()}`);
		}
		archimateSet = await create.json();
	}

	mkdirSync(dirname(SIDECAR), { recursive: true });
	writeFileSync(SIDECAR, JSON.stringify({ set_id: archimateSet.id, set_name: archimateSet.name }, null, 2));
	console.log(`[ensure-archimate] set ready: ${archimateSet.id}`);
});
