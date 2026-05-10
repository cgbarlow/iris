/**
 * E2E: Mermaid rendering in a Text diagram view (ADR-149 / SPEC-149-A).
 *
 * Creates a Text diagram via the API with three fenced blocks:
 *  1. a valid flowchart      → renders as SVG
 *  2. an invalid mermaid     → renders as .mermaid-error
 *  3. a plain typescript     → renders as ordinary <pre><code>
 *
 * Then visits /views/<id> and asserts the rendered DOM matches.
 */

import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, createDiagram } from './fixtures';

const MERMAID_SOURCE = [
	'# Mermaid Smoke Test',
	'',
	'A valid flowchart:',
	'',
	'```mermaid',
	'flowchart TD',
	'    A[Client] --> B{Load Balancer}',
	'    B --> C[Server 1]',
	'    B --> D[Server 2]',
	'```',
	'',
	'An invalid one to test the error fallback:',
	'',
	'```mermaid',
	'thisIsNotValid ::: nope',
	'```',
	'',
	'A normal code block (must not render as mermaid):',
	'',
	'```typescript',
	'const x: number = 42;',
	'```',
	'',
	'Done.',
].join('\n');

let diagramId = '';

test.describe('Text view mermaid rendering (ADR-149)', () => {
	test.beforeAll(async () => {
		await seedAdmin();
		const token = await getAuthToken();

		const body = await createDiagram(undefined, token, {
			diagram_type: 'text',
			notation: 'markdown',
			name: 'Mermaid Smoke Test',
			description: 'Created by text-view-mermaid.spec.ts',
			data: { content: MERMAID_SOURCE },
		});
		diagramId = body.id as string;
	});

	test('valid mermaid block renders as inline SVG', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/views/${diagramId}`);

		// Wait for the markdown view to mount and mermaid to render.
		const block = page.locator('.md-view .mermaid-block').first();
		await expect(block).toBeVisible({ timeout: 15_000 });

		// SVG must replace the placeholder <code>.
		const svg = block.locator('svg').first();
		await expect(svg).toBeVisible({ timeout: 15_000 });

		// Diagram content sanity-check: nodes labelled "Client" and
		// "Load Balancer" appear somewhere in the SVG text content.
		await expect(block).toContainText('Client');
		await expect(block).toContainText('Load Balancer');
	});

	test('invalid mermaid block renders a .mermaid-error fallback', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/views/${diagramId}`);

		const error = page.locator('.md-view .mermaid-error').first();
		await expect(error).toBeVisible({ timeout: 15_000 });
		await expect(error).toContainText(/Mermaid render error/i);
	});

	test('non-mermaid code blocks render as ordinary <pre><code>', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/views/${diagramId}`);

		// The typescript block has class "language-typescript" via marked's
		// default fenced-code rendering — never gets the mermaid-block class.
		const tsCode = page.locator('.md-view pre code.language-typescript').first();
		await expect(tsCode).toBeVisible({ timeout: 15_000 });
		await expect(tsCode).toContainText('const x: number = 42');

		// And there must be no mermaid-block element wrapping the typescript code.
		const tsParentClass = await tsCode.evaluate((el) => el.parentElement?.className ?? '');
		expect(tsParentClass).not.toContain('mermaid-block');
	});

	test('the rest of the document still renders even if a mermaid block errors', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/views/${diagramId}`);

		// "Done." paragraph appears below all the blocks.
		await expect(page.locator('.md-view').getByText('Done.')).toBeVisible({ timeout: 15_000 });
		// And the H1 heading rendered too.
		await expect(page.locator('.md-view h1', { hasText: 'Mermaid Smoke Test' })).toBeVisible();
	});
});
