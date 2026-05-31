import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, createDiagram } from './fixtures';

// Phase 3 of the mobile-responsive rollout (ADR-229 / SPEC-229-A).
// On mobile the diagram canvas is pan/zoom view-only: layout authoring (node
// drag, edge draw) is disabled even in edit mode, but panning still works.

const API_BASE = 'http://localhost:8000';

let diagramId = '';

test.beforeAll(async () => {
	await seedAdmin();
	const token = await getAuthToken();

	const elRes = await fetch(`${API_BASE}/api/elements`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
		body: JSON.stringify({ element_type: 'class', name: 'Mobile Canvas Node', data: {} })
	});
	if (!elRes.ok) throw new Error(`create element failed: ${elRes.status} ${await elRes.text()}`);
	const entityId = (await elRes.json()).id as string;

	const diagram = await createDiagram(undefined, token, {
		diagram_type: 'class',
		notation: 'uml',
		name: 'Mobile Canvas Probe',
		description: 'Drag-disabled on mobile.',
		data: { nodes: [{ id: 'n0', position: { x: 120, y: 120 }, data: { entityId } }], edges: [] }
	});
	diagramId = diagram.id as string;
});

test('canvas layout authoring is locked on mobile but panning works', async ({ page }) => {
	test.slow(); // login + diagram load; absorb rate-limit back-off under full-suite load
	await loginAsAdmin(page);
	await page.goto(`/views/${diagramId}`);

	// Wait for the diagram to finish loading before reaching for the toolbar.
	await expect(page.getByText('Loading diagram...')).toHaveCount(0, { timeout: 20_000 });

	// Enter edit mode — on a phone this is where the lock matters most.
	await page.getByRole('button', { name: 'Edit Canvas' }).click();

	// The view-only hint proves interactiveLayout resolved to false on mobile.
	await expect(page.getByTestId('layout-locked-hint')).toBeVisible({ timeout: 15_000 });

	// The node renders but is NOT draggable: SvelteFlow only adds the
	// `draggable` class to nodes when nodesDraggable is true.
	const node = page.locator('.svelte-flow__node').first();
	await expect(node).toBeVisible();
	await expect(node).not.toHaveClass(/\bdraggable\b/);

	// Panning still works (touch-first viewing): dragging the pane translates
	// the SvelteFlow viewport transform.
	const viewportEl = page.locator('.svelte-flow__viewport');
	const before = await viewportEl.evaluate((el) => getComputedStyle(el).transform);
	const box = await page.locator('.svelte-flow__pane').boundingBox();
	if (box) {
		// Start in the top-right of the pane — empty canvas, clear of the
		// fitView-centred node (centre), the mode badges (top-left) and xyflow's
		// zoom Controls (bottom-left) — so the gesture pans the viewport.
		const sx = box.x + box.width - 28;
		const sy = box.y + 28;
		await page.mouse.move(sx, sy);
		await page.mouse.down();
		await page.mouse.move(sx - 140, sy + 110, { steps: 10 });
		await page.mouse.up();
	}
	const after = await viewportEl.evaluate((el) => getComputedStyle(el).transform);
	expect(after).not.toBe(before);
});

test('the full-screen (FocusView) trigger is available on mobile', async ({ page }) => {
	test.slow();
	await loginAsAdmin(page);
	await page.goto(`/views/${diagramId}`);
	await expect(page.getByText('Loading diagram...')).toHaveCount(0, { timeout: 20_000 });
	// Restored on mobile (ADR-229 follow-up) — fullscreen canvas viewing.
	await expect(page.getByRole('button', { name: 'Full screen' })).toBeVisible();
});

test('the hierarchy toggle opens an overlay drawer on mobile', async ({ page }) => {
	test.slow();
	await loginAsAdmin(page);
	await page.goto(`/views/${diagramId}`);
	await expect(page.getByText('Loading diagram...')).toHaveCount(0, { timeout: 20_000 });

	const aside = page.locator('[data-hierarchy-sidebar]');
	// Toggle the hierarchy on.
	await page.getByRole('button', { name: 'Toggle hierarchy sidebar' }).first().click();
	await expect(aside).toBeVisible();
	// On mobile it's a fixed overlay (not the inline sticky column).
	await expect(aside).toHaveCSS('position', 'fixed');
	// It fills the viewport height (a fixed flex column can otherwise
	// shrink-wrap to content, leaving the tree area looking empty).
	const vh = await page.evaluate(() => window.innerHeight);
	const box = await aside.boundingBox();
	expect(box!.height).toBeGreaterThan(vh * 0.8);
	// The backdrop closes it — tap the strip to the right of the ≤320px drawer.
	await page.getByRole('button', { name: 'Close hierarchy' }).click({ position: { x: 370, y: 400 } });
	await expect(aside).toBeHidden();
});
