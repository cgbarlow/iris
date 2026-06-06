/**
 * E2E for ADR-239 (issue #255) — tap-to-tick checklists in Markdown views.
 *
 * Verifies:
 *   1. With checklist mode on, list items render as tappable checkboxes.
 *   2. Tapping an item ticks it (strike-through class) and PERSISTS the
 *      GFM marker into the source across a reload (full PUT + OCC round-trip).
 *   3. Tapping again unticks it.
 *   4. The Checklist toggle button enables the mode from a plain text view.
 *   5. The User Guide still renders lists WITHOUT checkboxes (opt-in guard).
 */

import { expect, test } from '@playwright/test';

import { createDiagram, createSet, getAuthToken, loginAsAdmin, seedAdmin } from './fixtures';

const API_BASE = 'http://localhost:8000';

test.describe('Checklist mode (ADR-239)', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('tap ticks an item and persists across reload', async ({ page }) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const diagram = (await createDiagram(undefined, token, {
			diagram_type: 'text',
			notation: 'markdown',
			name: 'Checklist-View',
			set_id: set.id,
			data: { content: '- Buy milk\n- Clean kitchen\n- Walk dog' },
			metadata: { checklist: true },
		})) as { id: string };

		await loginAsAdmin(page);
		await page.goto(`/views/${diagram.id}`);

		const boxes = page.locator('.md-check');
		await expect(boxes).toHaveCount(3);

		// Tap the second item ("Clean kitchen").
		await boxes.nth(1).click();

		// Its <li> should gain the checked (strike-through) class.
		const items = page.locator('.md-view li');
		await expect(items.nth(1)).toHaveClass(/md-check-checked/);

		// Persisted: reload and confirm it is still checked.
		await page.reload();
		await expect(page.locator('.md-view li').nth(1)).toHaveClass(/md-check-checked/);
		await expect(page.locator('.md-check').nth(1)).toHaveAttribute('aria-checked', 'true');

		// Confirm the source carries the GFM marker via the API.
		const res = await fetch(`${API_BASE}/api/diagrams/${diagram.id}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const body = (await res.json()) as { data: { content: string } };
		expect(body.data.content).toContain('- [x] Clean kitchen');
		expect(body.data.content).toContain('- Buy milk');

		// Tapping again unticks.
		await page.locator('.md-check').nth(1).click();
		await expect(page.locator('.md-view li').nth(1)).not.toHaveClass(/md-check-checked/);
	});

	test('rapid taps on multiple items all stick (no uncheck race)', async ({ page }) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const diagram = (await createDiagram(undefined, token, {
			diagram_type: 'text',
			notation: 'markdown',
			name: 'Rapid-Checklist',
			set_id: set.id,
			data: { content: '- one\n- two\n- three\n- four\n- five' },
			metadata: { checklist: true },
		})) as { id: string };

		await loginAsAdmin(page);
		await page.goto(`/views/${diagram.id}`);

		const boxes = page.locator('.md-check');
		await expect(boxes).toHaveCount(5);

		// Tap all five as fast as possible (no waiting between taps) — exercises
		// the coalescing save while PUTs are in flight.
		for (let i = 0; i < 5; i++) {
			await boxes.nth(i).click({ noWaitAfter: true });
		}

		// Every item must end up checked and stay checked.
		for (let i = 0; i < 5; i++) {
			await expect(page.locator('.md-view li').nth(i)).toHaveClass(/md-check-checked/);
		}

		// And it must persist: poll the API until all five markers are saved.
		await expect
			.poll(async () => {
				const res = await fetch(`${API_BASE}/api/diagrams/${diagram.id}`, {
					headers: { Authorization: `Bearer ${token}` },
				});
				const body = (await res.json()) as { data: { content: string } };
				return (body.data.content.match(/- \[x\] /g) ?? []).length;
			})
			.toBe(5);

		// A fresh load reflects all five ticked.
		await page.reload();
		for (let i = 0; i < 5; i++) {
			await expect(page.locator('.md-view li').nth(i)).toHaveClass(/md-check-checked/);
		}
	});

	test('toggle button enables checklist mode from a plain text view', async ({ page }) => {
		const token = await getAuthToken();
		const set = (await createSet(undefined, token, { name: `Set-${Date.now()}` })) as {
			id: string;
		};
		const diagram = (await createDiagram(undefined, token, {
			diagram_type: 'text',
			notation: 'markdown',
			name: 'Plain-View',
			set_id: set.id,
			data: { content: '- One\n- Two' },
		})) as { id: string };

		await loginAsAdmin(page);
		await page.goto(`/views/${diagram.id}`);

		// No checkboxes until the mode is enabled.
		await expect(page.locator('.md-check')).toHaveCount(0);

		await page.getByRole('button', { name: 'Toggle checklist mode' }).click();

		await expect(page.locator('.md-check')).toHaveCount(2);
	});

	test('User Guide lists are NOT decorated as checkboxes (opt-in guard)', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/guide');
		// Wait for guide content to render, then assert no checklist buttons.
		await expect(page.locator('.md-view').first()).toBeVisible();
		await expect(page.locator('.md-check')).toHaveCount(0);
	});
});
