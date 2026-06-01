/**
 * ADR-230 / SPEC-230-A: GEANZ diagram render fidelity.
 *
 * Seeds a CCS.00-shaped capability diagram (zone + capabilities + a
 * dashed redirect + dashed theme pills) whose source ELEMENTS carry no
 * visual — exactly like the real GEANZ import, where the EA fill/border
 * lives only on the canvas node. Then:
 *
 *  - AC1 (the flip regression): after the post-paint /api/elements/{id}
 *    refresh batch settles, every node's computed style is STILL the
 *    themed look (zone #ccf2fe + ~866px wide, capabilities white with a
 *    royal-blue border) — it must NOT flip to the iris-default-uml look.
 *  - AC6 (fidelity): per-archetype computed CSS matches the ground-truth
 *    (fills, royal-blue borders, dashed pills/redirect, rounded corners,
 *    italic pills, no ArchiMate icon, no description text).
 *
 * A screenshot is saved for human comparison against
 * /tmp/geanz/EARoot/EA1/EA34.png (the EA ground-truth for CCS.00).
 */

import { test, expect, type Page } from '@playwright/test';

import {
	seedAdmin,
	getAuthToken,
	loginAsAdmin,
	createSet,
	createPackage,
	createElement,
	createDiagram,
} from './fixtures';

const ROYAL_BLUE = 'rgb(65, 105, 225)'; // #4169e1
const ZONE_FILL = 'rgb(204, 242, 254)'; // #ccf2fe
const WHITE = 'rgb(255, 255, 255)';

const CAP = (
	extra: Record<string, unknown>,
): Record<string, unknown> => ({
	bgColor: '#ffffff',
	borderColor: '#4169e1',
	borderWidth: 2,
	borderRadius: 10,
	...extra,
});

/** Read a computed style property off a rendered node's renderer root. */
async function nodeStyle(page: Page, id: string, prop: string): Promise<string> {
	return page
		.locator(`.svelte-flow__node[data-id="${id}"] .archimate-node`)
		.first()
		.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
}

async function labelStyle(page: Page, id: string, prop: string): Promise<string> {
	return page
		.locator(`.svelte-flow__node[data-id="${id}"] .archimate-node__label`)
		.first()
		.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
}

test.describe('GEANZ diagram render fidelity (ADR-230)', () => {
	let viewId: string;

	test.beforeAll(async ({ baseURL }) => {
		await seedAdmin(baseURL);
		const token = await getAuthToken(baseURL);

		const set = await createSet(baseURL, token, { name: `GEANZ Render ${Date.now()}` });
		const setId = set.id as string;
		const pkg = await createPackage(baseURL, token, { name: 'CBC', set_id: setId });
		const pkgId = pkg.id as string;

		// Source elements carry NO data.visual — like the real GEANZ import.
		const mk = async (name: string) =>
			(await createElement(baseURL, token, {
				name,
				element_type: 'capability',
				notation: 'archimate',
				set_id: setId,
				package_id: pkgId,
				description: `${name} — generic capability description that the EA ground-truth does not show inside the box.`,
				data: { stereotype: 'ArchiMate_Capability' },
			})).id as string;

		const zoneId = await mk('Customer Service Delivery capability zone');
		const stratId = await mk('Service Delivery Strategy');
		const planId = await mk('Service Delivery Planning');
		const caseId = await mk('Case Management');
		const redirectId = await mk('Product and Service Management (redirect)');
		const pStrategyId = await mk('Strategy (theme)');
		const pPlanningId = await mk('Planning (theme)');

		const capNode = (
			id: string,
			entityId: string,
			label: string,
			x: number,
			y: number,
			visual: Record<string, unknown>,
			extraData: Record<string, unknown> = {},
		) => ({
			id,
			type: 'capability',
			position: { x, y },
			zIndex: 2,
			data: {
				label,
				entityType: 'capability',
				entityId,
				description: `${label} — description text`,
				stereotype: 'ArchiMate_Capability',
				visual,
				...extraData,
			},
		});

		const nodes = [
			// Zone — light-blue fill, thick royal-blue border, larger radius,
			// rendered BEHIND its children (lower zIndex).
			{
				id: 'zone',
				type: 'capability',
				position: { x: 7, y: 124 },
				zIndex: 0,
				data: {
					label: 'Customer Service Delivery capability zone',
					entityType: 'capability',
					entityId: zoneId,
					description: 'Generic customer service delivery capabilities.',
					stereotype: 'ArchiMate_Capability',
					visual: {
						bgColor: '#ccf2fe',
						borderColor: '#4169e1',
						borderWidth: 3,
						borderRadius: 14,
						width: 866,
						height: 390,
					},
				},
			},
			capNode('cap-strat', stratId, 'Service Delivery Strategy', 27, 174, CAP({ width: 266, height: 55 })),
			capNode('cap-plan', planId, 'Service Delivery Planning', 305, 174, CAP({ width: 266, height: 55 })),
			capNode('cap-case', caseId, 'Case Management', 582, 241, CAP({ width: 266, height: 55 })),
			// Redirect / proposed — dashed border.
			capNode('redirect', redirectId, 'Product and Service Management (redirect)', 582, 307,
				CAP({ width: 266, height: 44, borderStyle: 'dashed' })),
			// Theme pills — white, dashed, pill-shaped, italic, qualifier 'CBC Themes'.
			capNode('pill-strategy', pStrategyId, 'Strategy (theme)', 170, 80,
				{ bgColor: '#ffffff', borderColor: '#4169e1', borderWidth: 1, borderStyle: 'dashed', cornerStyle: 'pill', italic: true, width: 122, height: 30 },
				{ qualifier: 'CBC Themes' }),
			capNode('pill-planning', pPlanningId, 'Planning (theme)', 353, 80,
				{ bgColor: '#ffffff', borderColor: '#4169e1', borderWidth: 1, borderStyle: 'dashed', cornerStyle: 'pill', italic: true, width: 132, height: 30 },
				{ qualifier: 'CBC Themes' }),
			// Notes — title + date stamp (no entityId → not refreshed).
			{ id: 'note-title', type: 'note', position: { x: 253, y: 0 }, zIndex: 3,
				data: { label: 'Common Customer Service Delivery (CCS) capability zone', entityType: 'note', description: 'capability areas', visual: { width: 627, height: 62 } } },
			{ id: 'note-date', type: 'note', position: { x: 1, y: 24 }, zIndex: 3,
				data: { label: 'August 2025', entityType: 'note', description: 'August 2025', visual: { width: 148, height: 30 } } },
		];

		const edges = [
			{ id: 'e1', source: 'pill-strategy', target: 'cap-strat', type: 'association',
				data: { relationshipType: 'association', stereotype: 'ArchiMate_Association' }, sourceHandle: 'bottom', targetHandle: 'top' },
			{ id: 'e2', source: 'pill-planning', target: 'cap-plan', type: 'association',
				data: { relationshipType: 'association', stereotype: 'ArchiMate_Association' }, sourceHandle: 'bottom', targetHandle: 'top' },
		];

		const diagram = await createDiagram(baseURL, token, {
			diagram_type: 'class',
			notation: 'uml',
			name: 'CCS.00 Customer Service Delivery capability zone',
			set_id: setId,
			parent_package_id: pkgId,
			metadata: { theme_id: 'geanz-default' },
			data: { nodes, edges },
		});
		viewId = diagram.id as string;
	});

	test('renders the GEANZ archetypes faithfully and does not flip to UML default', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/views/${viewId}`);
		await expect(page.getByText('Loading diagram...')).toHaveCount(0, { timeout: 20_000 });
		await expect(page.locator('.svelte-flow__node[data-id="zone"] .archimate-node')).toBeVisible();

		// Let the post-paint /api/elements/{id} refresh batch run to completion —
		// this is exactly what used to flip the diagram to iris-default-uml.
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1500);

		// AC1 — the zone survived the refresh: still light-blue, still ~866 wide.
		expect(await nodeStyle(page, 'zone', 'background-color')).toBe(ZONE_FILL);
		expect(await nodeStyle(page, 'zone', 'border-color')).toBe(ROYAL_BLUE);
		expect(await nodeStyle(page, 'zone', 'border-top-style')).toBe('solid');
		const zoneW = parseFloat(await nodeStyle(page, 'zone', 'width'));
		expect(zoneW).toBeGreaterThan(800); // did NOT shrink/re-measure
		expect(parseFloat(await nodeStyle(page, 'zone', 'border-top-left-radius'))).toBeGreaterThanOrEqual(12);

		// AC6 — capability: white fill, royal-blue solid border, ~10px radius.
		for (const id of ['cap-strat', 'cap-plan', 'cap-case']) {
			expect(await nodeStyle(page, id, 'background-color')).toBe(WHITE);
			expect(await nodeStyle(page, id, 'border-color')).toBe(ROYAL_BLUE);
			expect(await nodeStyle(page, id, 'border-top-style')).toBe('solid');
			expect(parseFloat(await nodeStyle(page, id, 'border-top-left-radius'))).toBeGreaterThanOrEqual(8);
		}

		// AC6 — redirect / proposed: dashed border.
		expect(await nodeStyle(page, 'redirect', 'border-top-style')).toBe('dashed');

		// AC6 — theme pills: dashed, pill radius, italic label.
		for (const id of ['pill-strategy', 'pill-planning']) {
			expect(await nodeStyle(page, id, 'border-top-style')).toBe('dashed');
			expect(parseFloat(await nodeStyle(page, id, 'border-top-left-radius'))).toBeGreaterThanOrEqual(100);
			expect(await labelStyle(page, id, 'font-style')).toBe('italic');
		}

		// AC6 — no ArchiMate icon and no description text on any capability node
		// (the geanz-default theme hides both).
		expect(await page.locator('.svelte-flow__node[data-id="zone"] .archimate-node__icon').count()).toBe(0);
		expect(await page.locator('.svelte-flow__node[data-id="cap-strat"] .archimate-node__icon').count()).toBe(0);
		expect(await page.locator('.svelte-flow__node[data-id="cap-strat"] .archimate-node__description').count()).toBe(0);

		// Evidence screenshot for human comparison vs EA34.png.
		await page.locator('.svelte-flow__viewport').first().screenshot({
			path: 'tests/e2e/uat/screenshots/geanz-ccs00.png',
		});
	});
});
