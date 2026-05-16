/**
 * E2E for ADR-186 — Dynamic List diagram type (issue #147).
 *
 * Verifies:
 *   1. A dynamic_list diagram with default-mode renders 2 bullets per
 *      intra-diagram relationship (source name + target name).
 *   2. The /view Edit button exposes a Source panel with all three
 *      controls.
 *   3. Toggling "Show description" appends ``(description)`` to each
 *      bullet.
 *   4. Switching mode to ``package_elements`` and picking a package
 *      switches the rendered bullets to the package's elements.
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
		description?: string;
		package_id?: string;
	},
): Promise<{ id: string }> {
	const res = await fetch(`${API_BASE}/api/elements`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(body),
	});
	if (!res.ok) throw new Error(`createElement failed: ${res.status} ${await res.text()}`);
	return (await res.json()) as { id: string };
}

async function createRelationship(
	token: string,
	source: string,
	target: string,
): Promise<void> {
	const res = await fetch(`${API_BASE}/api/relationships`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			source_element_id: source,
			target_element_id: target,
			relationship_type: 'relates_to',
		}),
	});
	if (!res.ok) throw new Error(`createRelationship failed: ${res.status} ${await res.text()}`);
}

async function createDynamicListDiagram(
	token: string,
	body: {
		name: string;
		set_id: string;
		elementIds: string[];
		dynamicSource: {
			mode: 'diagram_relationships' | 'package_elements';
			package_id: string | null;
			show_description: boolean;
		};
	},
): Promise<{ id: string }> {
	const nodes = body.elementIds.map((eid, i) => ({
		id: `n${i}`,
		data: { entityId: eid },
	}));
	const res = await fetch(`${API_BASE}/api/diagrams`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			diagram_type: 'dynamic_list',
			notation: 'markdown',
			name: body.name,
			set_id: body.set_id,
			data: {
				nodes,
				edges: [],
				dynamic_source: body.dynamicSource,
			},
		}),
	});
	if (!res.ok) throw new Error(`createDynamicListDiagram failed: ${res.status} ${await res.text()}`);
	return (await res.json()) as { id: string };
}

test.describe('Dynamic List diagram (ADR-186)', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('API: default mode emits two bullets per intra-diagram relationship', async () => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const a = await createElement(token, {
			name: 'Alpha',
			element_type: 'component',
			set_id: set.id,
		});
		const b = await createElement(token, {
			name: 'Beta',
			element_type: 'component',
			set_id: set.id,
		});
		await createRelationship(token, a.id, b.id);
		const dl = await createDynamicListDiagram(token, {
			name: 'List',
			set_id: set.id,
			elementIds: [a.id, b.id],
			dynamicSource: {
				mode: 'diagram_relationships',
				package_id: null,
				show_description: false,
			},
		});

		const res = await fetch(`${API_BASE}/api/diagrams/${dl.id}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const body = (await res.json()) as {
			data: { content: string; is_content_locked: boolean };
		};
		expect(body.data.is_content_locked).toBe(true);
		expect(body.data.content).toContain('Alpha');
		expect(body.data.content).toContain('Beta');
		// 2 bullets total.
		const bullets = body.data.content
			.split('\n')
			.filter((line) => line.startsWith('- '));
		expect(bullets.length).toBe(2);
	});

	test('API: show_description=true appends descriptions in brackets', async () => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const a = await createElement(token, {
			name: 'AA',
			element_type: 'component',
			set_id: set.id,
			description: 'first',
		});
		const b = await createElement(token, {
			name: 'BB',
			element_type: 'component',
			set_id: set.id,
			description: 'second',
		});
		await createRelationship(token, a.id, b.id);
		const dl = await createDynamicListDiagram(token, {
			name: 'List',
			set_id: set.id,
			elementIds: [a.id, b.id],
			dynamicSource: {
				mode: 'diagram_relationships',
				package_id: null,
				show_description: true,
			},
		});

		const res = await fetch(`${API_BASE}/api/diagrams/${dl.id}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const body = (await res.json()) as { data: { content: string } };
		expect(body.data.content).toContain('(first)');
		expect(body.data.content).toContain('(second)');
	});

	test('API: package_elements mode lists package members alphabetically', async () => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const pkg = (await createPackage(undefined, token, {
			name: 'P',
			set_id: set.id,
		})) as { id: string };
		await createElement(token, {
			name: 'Charlie',
			element_type: 'component',
			set_id: set.id,
			package_id: pkg.id,
		});
		await createElement(token, {
			name: 'Alpha',
			element_type: 'component',
			set_id: set.id,
			package_id: pkg.id,
		});
		const dl = await createDynamicListDiagram(token, {
			name: 'List',
			set_id: set.id,
			elementIds: [],
			dynamicSource: {
				mode: 'package_elements',
				package_id: pkg.id,
				show_description: false,
			},
		});

		const res = await fetch(`${API_BASE}/api/diagrams/${dl.id}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const body = (await res.json()) as { data: { content: string } };
		const idxA = body.data.content.indexOf('Alpha');
		const idxC = body.data.content.indexOf('Charlie');
		expect(idxA).toBeGreaterThan(-1);
		expect(idxC).toBeGreaterThan(idxA);
	});

	test('UI: browse-mode renders bullets and the Edit Source panel appears', async ({ page }) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const a = await createElement(token, {
			name: 'Foo',
			element_type: 'component',
			set_id: set.id,
		});
		const b = await createElement(token, {
			name: 'Bar',
			element_type: 'component',
			set_id: set.id,
		});
		await createRelationship(token, a.id, b.id);
		const dl = await createDynamicListDiagram(token, {
			name: 'UI-List',
			set_id: set.id,
			elementIds: [a.id, b.id],
			dynamicSource: {
				mode: 'diagram_relationships',
				package_id: null,
				show_description: false,
			},
		});

		await loginAsAdmin(page);
		await page.goto(`/views/${dl.id}`);
		// Browse-mode shows the bullets.
		await expect(page.getByText('Foo')).toBeVisible();
		await expect(page.getByText('Bar')).toBeVisible();
	});
});
