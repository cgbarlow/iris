/**
 * v5.5.4 (issue #46 reopen, harness): ensure a BPMN view exists on UAT
 * for the suite to drive. Creates one in the "test" collection if no
 * BPMN view already exists.
 *
 * Idempotent — re-running the suite reuses an existing BPMN view; only
 * creates a new one when needed.
 */

import { test as setup } from '@playwright/test';

const API = 'https://iris-api-gtb3.onrender.com';

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
					} catch { /* fall through */ }
				}
			}
		}
		return null;
	});
}

setup('ensure a BPMN view exists', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('heading', { name: 'Dashboard' }).waitFor({ timeout: 15_000 });
	const token = await getToken(page);
	if (!token) throw new Error('No auth token in localStorage after login');

	const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

	// Already have a BPMN view? Done.
	const listResp = await page.request.get(`${API}/api/diagrams?notation=bpmn&page_size=1`, { headers });
	if (listResp.ok()) {
		const body = await listResp.json();
		if ((body.items ?? []).length > 0) {
			console.log(`[ensure-bpmn] found existing BPMN view: ${body.items[0].id}`);
			return;
		}
	}

	// Find or use the "test" collection.
	const collectionsResp = await page.request.get(`${API}/api/collections?page_size=50`, { headers });
	if (!collectionsResp.ok()) throw new Error(`GET /api/collections failed: ${collectionsResp.status()}`);
	const collections = (await collectionsResp.json()).items ?? [];
	const testCollection = collections.find((c: { name: string }) => /test/i.test(c.name));
	if (!testCollection) throw new Error('No "test" collection found on UAT — manual setup required.');

	// Find or create a "test" set under it.
	const setsResp = await page.request.get(
		`${API}/api/sets?collection_id=${testCollection.id}&page_size=50`,
		{ headers },
	);
	if (!setsResp.ok()) throw new Error(`GET /api/sets failed: ${setsResp.status()}`);
	let sets = (await setsResp.json()).items ?? [];
	let testSet = sets[0];
	if (!testSet) {
		const setCreate = await page.request.post(`${API}/api/sets`, {
			headers,
			data: { name: 'Test set', collection_id: testCollection.id },
		});
		if (!setCreate.ok()) throw new Error(`POST /api/sets failed: ${setCreate.status()} ${await setCreate.text()}`);
		testSet = await setCreate.json();
	}

	// Create a BPMN diagram in that set.
	const diagramCreate = await page.request.post(`${API}/api/diagrams`, {
		headers,
		data: {
			name: 'UAT verification BPMN',
			diagram_type: 'process',
			notation: 'bpmn',
			set_id: testSet.id,
			data: {
				nodes: [
					{
						id: 'start-1',
						type: 'event_start',
						position: { x: 100, y: 200 },
						data: { label: 'Start', entityType: 'event_start' },
					},
					{
						id: 'task-1',
						type: 'task',
						position: { x: 250, y: 200 },
						data: { label: 'Do something', entityType: 'task' },
					},
					{
						id: 'end-1',
						type: 'event_end',
						position: { x: 500, y: 200 },
						data: { label: 'End', entityType: 'event_end' },
					},
				],
				edges: [
					{ id: 'e-start-task', source: 'start-1', target: 'task-1', type: 'sequence_flow' },
					{ id: 'e-task-end', source: 'task-1', target: 'end-1', type: 'sequence_flow' },
				],
			},
		},
	});
	if (!diagramCreate.ok()) {
		throw new Error(`POST /api/diagrams failed: ${diagramCreate.status()} ${await diagramCreate.text()}`);
	}
	const created = await diagramCreate.json();
	console.log(`[ensure-bpmn] created BPMN view: ${created.id}`);
});
