/**
 * E2E for ADR-243 / SPEC-243-A — element page **Data** panel (issue #292).
 *
 * An element's free-form `data` blob (written by MCP `create_element(s)` or
 * element templates) used to be invisible unless it lived under
 * `data.attributes`. Verifies:
 *   1. The issue #292 article payload renders as a `Data (N)` accordion with
 *      scalar rows, an http(s) link, and nested values as formatted JSON.
 *   2. A UML `attributes` array stays in the Attributes accordion and is not
 *      duplicated into Data; an element with nothing else shows no Data group.
 *   3. The unrecognised keys survive an ordinary edit + save round-trip.
 *   4. ADR-245: in edit mode, fields can be changed, retyped, added and
 *      removed; invalid JSON blocks Save; the attributes array is untouched.
 */

import { expect, test } from '@playwright/test';

import { createElement, createSet, getAuthToken, loginAsAdmin, seedAdmin } from './fixtures';

const API_BASE = 'http://localhost:8000';

const ARTICLE_DATA = {
	type: 'article',
	slug: 'epic-quest-career-development-part-2',
	url: 'https://unchartedquests.substack.com/p/an-epic-quest-in-career-development-d1a',
	publication: 'Uncharted Quests',
	date: '2025-03-16',
	series: 'An epic quest in career development',
	part: 2,
	links: { canonical: '/articles/epic-quest-2' },
};

async function openAccordion(page: import('@playwright/test').Page, name: RegExp) {
	// The accordions live under the Details tab (ADR-208 default is Relationships).
	const detailsTab = page.getByRole('tab', { name: 'Details' });
	if ((await detailsTab.getAttribute('aria-selected')) !== 'true') {
		await detailsTab.click();
	}
	const trigger = page.getByRole('button', { name });
	if ((await trigger.getAttribute('data-state')) !== 'open') {
		await trigger.click();
	}
}

test.describe('ADR-243 element data panel', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('renders arbitrary data keys read-only', async ({ page }) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-data-${Date.now()}` })) as {
			id: string;
		};
		const el = (await createElement(undefined, token, {
			name: 'An epic quest in career development (Part 2)',
			element_type: 'note',
			set_id: set.id,
			data: ARTICLE_DATA,
		})) as { id: string };

		await loginAsAdmin(page);
		await page.goto(`/elements/${el.id}`);

		await openAccordion(page, /^Data \(8\)/);
		const panel = page.getByTestId('element-data-panel');
		await expect(panel).toBeVisible();

		await expect(panel.getByText('publication', { exact: true })).toBeVisible();
		await expect(panel.getByText('Uncharted Quests', { exact: true })).toBeVisible();
		await expect(panel.getByText('2', { exact: true })).toBeVisible();

		const link = panel.getByRole('link', { name: ARTICLE_DATA.url });
		await expect(link).toHaveAttribute('href', ARTICLE_DATA.url);
		await expect(link).toHaveAttribute('rel', 'noopener noreferrer');

		await expect(panel.locator('pre')).toContainText('"canonical": "/articles/epic-quest-2"');
	});

	test('attributes stay in the Attributes group; no Data group when nothing else is set', async ({
		page,
	}) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-attrs-${Date.now()}` })) as {
			id: string;
		};
		const el = (await createElement(undefined, token, {
			name: 'AttrsOnly',
			element_type: 'component',
			set_id: set.id,
			data: { attributes: [{ name: 'id', type: 'int', scope: 'Public' }] },
		})) as { id: string };

		await loginAsAdmin(page);
		await page.goto(`/elements/${el.id}`);
		await page.getByRole('tab', { name: 'Details' }).click();

		await expect(page.getByRole('button', { name: /^Attributes \(1\)/ })).toBeVisible();
		await expect(page.getByRole('button', { name: /^Data \(/ })).toHaveCount(0);
	});

	test('data keys survive an ordinary edit and save', async ({ page }) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-save-${Date.now()}` })) as {
			id: string;
		};
		const el = (await createElement(undefined, token, {
			name: 'SaveMe',
			element_type: 'note',
			set_id: set.id,
			data: ARTICLE_DATA,
		})) as { id: string };

		await loginAsAdmin(page);
		await page.goto(`/elements/${el.id}?edit=true`);

		// The Data editor is seeded with the existing keys while editing.
		await openAccordion(page, /^Data \(8\)/);
		await expect(page.getByTestId('element-data-editor')).toBeVisible();

		await openAccordion(page, /^Details/);
		await page.getByRole('textbox', { name: 'Status', exact: true }).fill('Validated');
		await page.getByRole('button', { name: /^Save$/i }).first().click();
		await page.waitForResponse(
			(r) =>
				r.url().includes(`/api/elements/${el.id}`) &&
				!r.url().includes('/tags') &&
				r.request().method() === 'PUT',
		);

		const res = await fetch(`${API_BASE}/api/elements/${el.id}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const body = (await res.json()) as {
			data: Record<string, unknown>;
			metadata: Record<string, unknown>;
		};
		expect(body.metadata.status).toBe('Validated');
		expect(body.data).toEqual(ARTICLE_DATA);
	});

	test('data fields can be edited, added, removed, and retyped (ADR-245)', async ({ page }) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-edit-${Date.now()}` })) as {
			id: string;
		};
		const el = (await createElement(undefined, token, {
			name: 'EditData',
			element_type: 'note',
			set_id: set.id,
			data: {
				...ARTICLE_DATA,
				attributes: [{ name: 'id', type: 'int', scope: 'Public' }],
			},
		})) as { id: string };

		await loginAsAdmin(page);
		await page.goto(`/elements/${el.id}`);
		await page.getByRole('tab', { name: 'Details' }).click();
		await page.getByRole('button', { name: 'Edit Details' }).click();
		await openAccordion(page, /^Data \(8\)/);
		const editor = page.getByTestId('element-data-editor');
		await expect(editor).toBeVisible();

		// Edit a text value (row 4 = publication) and a number (row 7 = part).
		await page.getByLabel('Data field 4 value').fill('Uncharted Quests Weekly');
		await page.getByLabel('Data field 7 value').fill('3');

		// Invalid JSON blocks Save with an inline error, then gets fixed.
		const save = page.getByRole('button', { name: /^Save$/i }).first();
		await page.getByLabel('Data field 8 value').fill('{ "canonical": ');
		await expect(editor.getByRole('alert')).toHaveText('Data "links" is not valid JSON');
		await expect(save).toBeDisabled();
		await page.getByLabel('Data field 8 value').fill('{ "canonical": "/articles/quest-3" }');
		await expect(editor.getByRole('alert')).toHaveCount(0);

		// Remove `slug` (row 2), then add a boolean field.
		await page.getByRole('button', { name: 'Remove data field 2' }).click();
		await page.getByRole('button', { name: '+ Add Data Field' }).click();
		await page.getByLabel('Data field 8 key').fill('featured');
		await page.getByLabel('Data field 8 type').selectOption('boolean');
		await page.getByLabel('Data field 8 value').selectOption('true');

		await expect(save).toBeEnabled();
		await save.click();
		await page.waitForResponse(
			(r) =>
				r.url().includes(`/api/elements/${el.id}`) &&
				!r.url().includes('/tags') &&
				r.request().method() === 'PUT',
		);

		const res = await fetch(`${API_BASE}/api/elements/${el.id}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const body = (await res.json()) as { data: Record<string, unknown> };
		const { slug: _slug, ...rest } = ARTICLE_DATA;
		expect(body.data).toEqual({
			...rest,
			publication: 'Uncharted Quests Weekly',
			part: 3,
			links: { canonical: '/articles/quest-3' },
			featured: true,
			// The Attributes table's array is untouched by Data edits.
			attributes: [expect.objectContaining({ name: 'id', type: 'int' })],
		});

		// Back in view mode the saved values render.
		await openAccordion(page, /^Data \(8\)/);
		await expect(page.getByTestId('element-data-panel').getByText('featured', { exact: true })).toBeVisible();
	});
});
