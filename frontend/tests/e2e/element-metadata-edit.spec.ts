/**
 * E2E for ADR-228 — element metadata edit UI.
 *
 * Verifies that the Status input under Details and the editable
 * tagged-values grid under Extended round-trip through the API:
 *   1. Status changes are sent in the PUT body's `metadata` and
 *      survive a page reload.
 *   2. A new tagged value added in the editor is persisted, and the
 *      Notes textarea on a row carrying a `#NOTES#` block reassembles
 *      via `joinTaggedValue` on save.
 *   3. Deleting a tagged-value row drops it from `metadata.tagged_values`.
 *   4. Regression: the PUT body MUST NOT include `element_type`
 *      (v6.39.0 dead-byte cleanup).
 */

import { expect, test } from '@playwright/test';

import { createSet, getAuthToken, loginAsAdmin } from './fixtures';

const API_BASE = 'http://localhost:8000';

async function createElement(
	token: string,
	body: {
		name: string;
		element_type: string;
		set_id: string;
		metadata?: Record<string, unknown>;
	},
): Promise<{ id: string; current_version: number }> {
	const res = await fetch(`${API_BASE}/api/elements`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(body),
	});
	if (!res.ok) {
		throw new Error(`createElement failed: ${res.status} ${await res.text()}`);
	}
	return (await res.json()) as { id: string; current_version: number };
}

test.describe('ADR-228 element metadata edit', () => {
	test('status + tagged-values round-trip through the UI', async ({ page }) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, {
			name: `Set-meta-${Date.now()}`,
		})) as { id: string };
		const el = await createElement(token, {
			name: 'MetaEditMe',
			element_type: 'component',
			set_id: set.id,
			metadata: {
				status: 'Proposed',
				stereotype: 'ArchiMate_Capability',
				tagged_values: [
					{
						property: 'Current Maturity Level',
						value: '-#NOTES#Values: -,0,1,2,3,4,5\nDefault: -',
					},
				],
			},
		});

		// Capture every PUT body sent to this element so we can assert
		// `metadata` is included and `element_type` is not.
		const putBodies: Array<Record<string, unknown>> = [];
		page.on('request', (req) => {
			if (
				req.method() === 'PUT' &&
				req.url().includes(`/api/elements/${el.id}`) &&
				!req.url().includes('/tags')
			) {
				try {
					putBodies.push(JSON.parse(req.postData() ?? '{}'));
				} catch {
					/* not JSON — ignore */
				}
			}
		});

		await loginAsAdmin(page);
		await page.goto(`/elements/${el.id}?edit=true`);

		// Open the Details accordion so the Status input is visible.
		const detailsTrigger = page.getByRole('button', { name: /^Details/ });
		if ((await detailsTrigger.getAttribute('data-state')) !== 'open') {
			await detailsTrigger.click();
		}
		await page.getByLabel('Status').fill('Validated');

		// Open the Extended accordion to surface the tagged-values grid.
		const extendedTrigger = page.getByRole('button', { name: /^Extended/ });
		if ((await extendedTrigger.getAttribute('data-state')) !== 'open') {
			await extendedTrigger.click();
		}
		// Edit the seeded tagged value's value cell, then add a fresh one.
		await page.getByLabel('Tagged value 1 value').fill('3');
		await page.getByRole('button', { name: '+ Add Tagged Value' }).click();
		await page.getByLabel('Tagged value 2 property').fill('Reviewer');
		await page.getByLabel('Tagged value 2 value').fill('Alice');

		await page.getByRole('button', { name: /^Save$/i }).first().click();
		await page.waitForResponse(
			(r) =>
				r.url().includes(`/api/elements/${el.id}`) &&
				!r.url().includes('/tags') &&
				r.request().method() === 'PUT',
		);

		// Verify via the backend (decoupled from the UI's read path).
		const res1 = await fetch(`${API_BASE}/api/elements/${el.id}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const body1 = (await res1.json()) as {
			metadata: Record<string, unknown>;
			element_type: string;
		};
		expect(body1.metadata.status).toBe('Validated');
		expect(body1.element_type).toBe('component'); // unchanged
		const tvs1 = body1.metadata.tagged_values as Array<{
			property: string;
			value: string | null;
		}>;
		expect(tvs1).toHaveLength(2);
		// First row: value 3 + the original #NOTES# block reassembled.
		expect(tvs1[0].property).toBe('Current Maturity Level');
		expect(tvs1[0].value).toMatch(/^3#NOTES#Values: -,0,1,2,3,4,5/);
		// Second row: new Reviewer / Alice, no notes.
		expect(tvs1.find((tv) => tv.property === 'Reviewer')?.value).toBe('Alice');

		// Regression: the captured PUT body must include `metadata` and
		// must NOT include `element_type` (v6.39.0 cleanup).
		expect(putBodies.length).toBeGreaterThan(0);
		const last = putBodies[putBodies.length - 1];
		expect(last).toHaveProperty('metadata');
		expect(last).not.toHaveProperty('element_type');

		// Now: reload, re-enter edit, delete the second tagged value,
		// save, reload, assert it's gone.
		await page.reload();
		await page.goto(`/elements/${el.id}?edit=true`);
		const extendedTrigger2 = page.getByRole('button', { name: /^Extended/ });
		if ((await extendedTrigger2.getAttribute('data-state')) !== 'open') {
			await extendedTrigger2.click();
		}
		await page
			.getByRole('button', { name: 'Remove tagged value 2' })
			.click();
		await page.getByRole('button', { name: /^Save$/i }).first().click();
		await page.waitForResponse(
			(r) =>
				r.url().includes(`/api/elements/${el.id}`) &&
				!r.url().includes('/tags') &&
				r.request().method() === 'PUT',
		);
		const res2 = await fetch(`${API_BASE}/api/elements/${el.id}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const body2 = (await res2.json()) as { metadata: Record<string, unknown> };
		const tvs2 = body2.metadata.tagged_values as Array<{ property: string }>;
		expect(tvs2).toHaveLength(1);
		expect(tvs2[0].property).toBe('Current Maturity Level');
	});
});
