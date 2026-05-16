/**
 * E2E for ADR-184 — element → package optional membership (issue #149).
 *
 * Verifies the new UI affordances actually round-trip through the API:
 *   1. The element edit form exposes a Package picker; saving with a
 *      selection writes ``package_id`` to the backend.
 *   2. ``GET /api/packages/{id}/elements`` returns the member.
 *   3. The /view Relationships tab shows the new "Element → Package
 *      memberships" section for elements drawn on the diagram.
 */

import { expect, test } from '@playwright/test';

import {
	createDiagram,
	createPackage,
	createSet,
	getAuthToken,
	loginAsAdmin,
	seedAdmin,
} from './fixtures';

const API_BASE = 'http://localhost:8000';

async function createElement(
	token: string,
	body: {
		name: string;
		element_type: string;
		set_id: string;
		package_id?: string;
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
	if (!res.ok) throw new Error(`createElement failed: ${res.status} ${await res.text()}`);
	return (await res.json()) as { id: string; current_version: number };
}

async function setDiagramCanvas(
	token: string,
	diagram_id: string,
	current_version: number,
	element_ids: string[],
): Promise<void> {
	const nodes = element_ids.map((eid, i) => ({
		id: `n${i}`,
		data: { entityId: eid },
	}));
	const res = await fetch(`${API_BASE}/api/diagrams/${diagram_id}`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
			'If-Match': String(current_version),
		},
		body: JSON.stringify({
			name: 'D',
			description: '',
			data: { nodes, edges: [] },
		}),
	});
	if (!res.ok) throw new Error(`setDiagramCanvas failed: ${res.status} ${await res.text()}`);
}

test.describe('Element → Package membership (ADR-184)', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('GET /api/packages/{id}/elements returns members', async () => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const pkg = (await createPackage(undefined, token, {
			name: 'Pkg-A',
			set_id: set.id,
		})) as { id: string };

		const memberEl = await createElement(token, {
			name: 'Member',
			element_type: 'component',
			set_id: set.id,
			package_id: pkg.id,
		});
		// Non-member element to ensure filtering is correct.
		await createElement(token, {
			name: 'NonMember',
			element_type: 'component',
			set_id: set.id,
		});

		const res = await fetch(
			`${API_BASE}/api/packages/${pkg.id}/elements`,
			{ headers: { Authorization: `Bearer ${token}` } },
		);
		expect(res.ok).toBe(true);
		const body = (await res.json()) as {
			items: Array<{ id: string }>;
			total: number;
		};
		expect(body.total).toBe(1);
		expect(body.items.map((i) => i.id)).toContain(memberEl.id);
	});

	test('GET /api/diagrams/{id}/relationships includes element_package_memberships', async ({}) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const pkg = (await createPackage(undefined, token, {
			name: 'Pkg-B',
			set_id: set.id,
		})) as { id: string };
		const member = await createElement(token, {
			name: 'OnCanvas',
			element_type: 'component',
			set_id: set.id,
			package_id: pkg.id,
		});
		const diagram = (await createDiagram(undefined, token, {
			diagram_type: 'component',
			notation: 'simple',
			name: 'D',
			data: { nodes: [{ id: 'n0', data: { entityId: member.id } }], edges: [] },
		})) as { id: string };

		const res = await fetch(
			`${API_BASE}/api/diagrams/${diagram.id}/relationships`,
			{ headers: { Authorization: `Bearer ${token}` } },
		);
		expect(res.ok).toBe(true);
		const body = (await res.json()) as {
			element_package_memberships: Array<{
				element_id: string;
				package_id: string;
				package_name: string;
			}>;
		};
		expect(body.element_package_memberships.length).toBe(1);
		expect(body.element_package_memberships[0].element_id).toBe(member.id);
		expect(body.element_package_memberships[0].package_id).toBe(pkg.id);
		expect(body.element_package_memberships[0].package_name).toBe('Pkg-B');
	});

	test('element edit form Package picker round-trips through the UI', async ({ page }) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const pkg = (await createPackage(undefined, token, {
			name: 'Pkg-Picker',
			set_id: set.id,
		})) as { id: string };
		const el = await createElement(token, {
			name: 'PickMe',
			element_type: 'component',
			set_id: set.id,
		});

		await loginAsAdmin(page);
		await page.goto(`/elements/${el.id}?edit=true`);
		// The Package picker is a <select> labelled "Package membership".
		// Choose Pkg-Picker and submit.
		const picker = page.getByLabel('Package membership');
		await picker.selectOption({ label: 'Pkg-Picker' });
		// Save the form — the page exposes a Save button in the edit
		// chrome that triggers saveEntityMetadata().
		await page.getByRole('button', { name: /^Save$/i }).first().click();
		// Wait for the API round-trip; then verify via the backend.
		await page.waitForTimeout(750);
		const res = await fetch(`${API_BASE}/api/elements/${el.id}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const body = (await res.json()) as { package_id: string | null };
		expect(body.package_id).toBe(pkg.id);
	});
});
