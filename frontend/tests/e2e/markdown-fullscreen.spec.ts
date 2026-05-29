/**
 * E2E: Full screen (focus mode) on markdown-notation diagrams (issue #243).
 *
 * Regression guard: the "Full screen" toolbar button used to do nothing on
 * text/markdown views because the text render branches never mounted
 * <FocusView>. This spec creates a Text (markdown) view, clicks Full screen,
 * and asserts the focus-view overlay appears with the markdown content, then
 * that exiting (button + Escape) restores the normal view.
 */

import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, createDiagram } from './fixtures';

const MARKDOWN_SOURCE = [
	'# Fullscreen Markdown Test',
	'',
	'This text view must be able to go full screen (#243).',
	'',
	'- one',
	'- two',
].join('\n');

let diagramId = '';

test.describe('Markdown view full screen / focus mode (#243)', () => {
	test.beforeAll(async () => {
		await seedAdmin();
		const token = await getAuthToken();

		const body = await createDiagram(undefined, token, {
			diagram_type: 'text',
			notation: 'markdown',
			name: 'Fullscreen Markdown Test',
			description: 'Created by markdown-fullscreen.spec.ts',
			data: { content: MARKDOWN_SOURCE },
		});
		diagramId = body.id as string;
	});

	test('Full screen button opens the focus-view overlay with the markdown', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/views/${diagramId}`);

		// Markdown content mounts in normal (non-focus) view first.
		await expect(page.locator('.md-view').first()).toBeVisible({ timeout: 15_000 });

		// No focus overlay until the button is clicked.
		const focus = page.locator('[role="dialog"][aria-label="Focus view"]');
		await expect(focus).toHaveCount(0);

		await page.getByRole('button', { name: 'Full screen' }).click();

		// The overlay appears and renders the markdown inside it.
		await expect(focus).toBeVisible({ timeout: 10_000 });
		await expect(focus.locator('.md-view')).toContainText('Fullscreen Markdown Test');
	});

	test('Exit button and Escape both close the focus-view overlay', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/views/${diagramId}`);
		await expect(page.locator('.md-view').first()).toBeVisible({ timeout: 15_000 });

		const focus = page.locator('[role="dialog"][aria-label="Focus view"]');

		// Exit via the close button.
		await page.getByRole('button', { name: 'Full screen' }).click();
		await expect(focus).toBeVisible({ timeout: 10_000 });
		await page.getByRole('button', { name: 'Exit focus view' }).click();
		await expect(focus).toHaveCount(0);
		await expect(page.locator('.md-view').first()).toBeVisible();

		// Exit via Escape.
		await page.getByRole('button', { name: 'Full screen' }).click();
		await expect(focus).toBeVisible({ timeout: 10_000 });
		await page.keyboard.press('Escape');
		await expect(focus).toHaveCount(0);
		await expect(page.locator('.md-view').first()).toBeVisible();
	});
});
