/**
 * E2E for ADR-260 (issue #315) — canvas text is readable.
 *
 * Builds two canvases through the API, the way an MCP client would, and
 * checks what the browser renders:
 *   1. A note's text is at least 12px.
 *   2. A long node title wraps and carries the full name as a tooltip.
 *   3. A boundary with a node width and height renders at that size.
 *   4. A class shows its attributes and operations, whether they were
 *      stored as `data.attributes` / `data.operations` or the older
 *      `data.compartments`, and keeps them after element hydration.
 */

import { expect, test, type Page } from '@playwright/test';

import {
	createDiagram,
	createElement,
	createSet,
	getAuthToken,
	loginAsAdmin,
	seedAdmin,
} from './fixtures';

const LONG_NAME = 'Customer Relationship Management Integration Gateway Service';

/** A canvas node's box in canvas units (independent of the fit-view zoom). */
async function canvasSize(page: Page, nodeId: string): Promise<{ width: number; height: number }> {
	return page.locator(`.svelte-flow__node[data-id="${nodeId}"]`).evaluate((el) => ({
		width: (el as HTMLElement).offsetWidth,
		height: (el as HTMLElement).offsetHeight,
	}));
}

function fontSize(page: Page, selector: string): Promise<number> {
	return page.locator(selector).first().evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
}

test.describe('Canvas text is readable (ADR-260)', () => {
	let token: string;
	let setId: string;

	test.beforeAll(async () => {
		await seedAdmin();
		token = await getAuthToken();
		const set = await createSet(undefined, token, { name: `Canvas text ${Date.now()}` });
		setId = set.id as string;
	});

	test('notes, long titles and boundaries', async ({ page }) => {
		const gateway = await createElement(undefined, token, {
			name: LONG_NAME,
			element_type: 'component',
			set_id: setId,
		});
		const diagram = await createDiagram(undefined, token, {
			diagram_type: 'component',
			notation: 'simple',
			name: 'Readable simple canvas',
			set_id: setId,
			data: {
				nodes: [
					{
						id: 'note',
						type: 'note',
						position: { x: 40, y: 40 },
						width: 220,
						data: {
							label: 'Reading guide',
							entityType: 'note',
							description: 'Blue boxes are systems we own.',
						},
					},
					{
						id: 'gateway',
						type: 'component',
						position: { x: 320, y: 40 },
						width: 200,
						data: { label: LONG_NAME, entityType: 'component', entityId: gateway.id },
					},
					{
						id: 'zone',
						type: 'boundary',
						position: { x: 40, y: 240 },
						width: 520,
						height: 300,
						data: { label: 'Trust boundary', entityType: 'boundary' },
					},
				],
				edges: [],
			},
		});

		await loginAsAdmin(page);
		await page.goto(`/views/${diagram.id}`);
		await expect(page.locator('.svelte-flow__node[data-id="zone"]')).toBeVisible();

		// 1. Note header and body are at least 12px.
		const note = '.svelte-flow__node[data-id="note"]';
		expect(await fontSize(page, `${note} .canvas-node__label`)).toBeGreaterThanOrEqual(12);
		expect(await fontSize(page, `${note} .canvas-node__description`)).toBeGreaterThanOrEqual(12);

		// 2. The long title wraps onto more than one line and has a tooltip.
		const title = page.locator('.svelte-flow__node[data-id="gateway"] .canvas-node__label');
		await expect(title).toHaveAttribute('title', LONG_NAME);
		const lines = await title.evaluate((el) => {
			const style = getComputedStyle(el);
			return Math.round((el as HTMLElement).offsetHeight / parseFloat(style.lineHeight));
		});
		expect(lines).toBeGreaterThan(1);
		expect(lines).toBeLessThanOrEqual(3);

		// 3. The boundary keeps its stored size.
		expect(await canvasSize(page, 'zone')).toEqual({ width: 520, height: 300 });
	});

	test('class attributes and operations', async ({ page }) => {
		const order = await createElement(undefined, token, {
			name: 'Order',
			element_type: 'class',
			notation: 'uml',
			set_id: setId,
		});
		const diagram = await createDiagram(undefined, token, {
			diagram_type: 'class',
			notation: 'uml',
			name: 'Readable class canvas',
			set_id: setId,
			data: {
				nodes: [
					// Element-backed; the element defines no members of its own.
					{
						id: 'order',
						type: 'class',
						position: { x: 40, y: 40 },
						width: 220,
						data: {
							label: 'Order',
							entityType: 'class',
							entityId: order.id,
							attributes: ['id: UUID'],
							operations: ['submit(): void'],
						},
					},
					// Members written the way the older creation prompt said to.
					{
						id: 'invoice',
						type: 'class',
						position: { x: 340, y: 40 },
						width: 220,
						data: {
							label: 'Invoice',
							entityType: 'class',
							compartments: {
								attributes: ['number: String'],
								operations: ['send(): void'],
							},
						},
					},
				],
				edges: [],
			},
		});

		await loginAsAdmin(page);
		const hydrated = page.waitForResponse(
			(r) => r.url().includes(`/api/diagrams/${diagram.id}/elements`) && r.ok(),
		);
		await page.goto(`/views/${diagram.id}`);
		await hydrated;

		const members = (nodeId: string) =>
			page.locator(`.svelte-flow__node[data-id="${nodeId}"] .uml-node__attr`);
		await expect(members('order')).toHaveText(['id: UUID', 'submit(): void']);
		await expect(members('invoice')).toHaveText(['number: String', 'send(): void']);
	});
});
