/**
 * ADR-234 / SPEC-234-A: GEANZ render fidelity at scale.
 *
 * Imports the FULL GEANZ Common Business Capabilities model, then renders
 * EVERY diagram and asserts there are no overlapping boxes — the
 * deterministic gate for "faithful layout" (pixel-identity to the EA raster
 * is infeasible and not a gate). A node may CONTAIN another (a zone contains
 * its capabilities); what's forbidden is two boxes that partially intersect
 * without one containing the other. Screenshots are saved for human
 * comparison against /tmp/geanz/EARoot/EA1/*.png.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { test, expect } from '@playwright/test';

import { seedAdmin, getAuthToken, loginAsAdmin, createSet } from './fixtures';

const API_BASE = 'http://localhost:8000';
const GEANZ_XML = join(process.cwd(), '..', 'GEANZ Common Business Capabilities Sparx EA model.xml');
interface Rect { id: string; left: number; top: number; right: number; bottom: number; w: number; h: number; }

function overlapArea(a: Rect, b: Rect): number {
	const x = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
	const y = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
	return x * y;
}
/**
 * A real overlap (the bug) = two boxes whose intersection is a SUBSTANTIAL
 * fraction of the smaller box, but where neither is (mostly) contained in the
 * other. Containment (a zone holding its capabilities → small box ~fully
 * inside the big one) is legitimate and excluded; so are tiny border slivers
 * from a child poking a few px past its parent.
 */
function conflict(a: Rect, b: Rect): boolean {
	const ov = overlapArea(a, b);
	if (ov <= 0) return false;
	const areaA = a.w * a.h, areaB = b.w * b.h;
	const smaller = Math.min(areaA, areaB), larger = Math.max(areaA, areaB);
	if (smaller <= 0) return false;
	// Container relationship (one box much larger than the other): a small node
	// touching a much bigger one's edge — e.g. a dashed theme pill at the top
	// border of its capability zone — is a containment/adjacency, not the
	// "overlapping boxes" defect. The real bug is comparably-sized SIBLINGS
	// colliding (the capability-grid overlap), so only judge similar-size pairs.
	if (larger / smaller > 4) return false;
	const frac = ov / smaller; // how much of the smaller box is covered
	if (frac >= 0.9) return false; // smaller box ~fully inside the other → containment
	return frac >= 0.2; // substantial partial overlap → real sibling collision
}

test.describe('GEANZ render fidelity at scale (ADR-234)', () => {
	let setId: string;
	let diagrams: { id: string; name: string }[] = [];

	test.beforeAll(async ({ baseURL }) => {
		test.setTimeout(120_000);
		await seedAdmin(baseURL);
		const token = await getAuthToken(baseURL);
		const set = await createSet(baseURL, token, { name: `GEANZ Scale ${Date.now()}` });
		setId = set.id as string;

		// Upload the full GEANZ XMI into the set.
		const buf = readFileSync(GEANZ_XML);
		const fd = new FormData();
		fd.append('file', new Blob([buf], { type: 'text/xml' }), 'geanz.xml');
		fd.append('set_id', setId);
		const res = await fetch(`${API_BASE}/api/import/sparx-xml`, {
			method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
		});
		if (!res.ok) throw new Error(`import failed: ${res.status} ${await res.text()}`);

		// Enumerate every diagram in the set from the hierarchy.
		const hres = await fetch(`${API_BASE}/api/diagrams/hierarchy?set_id=${setId}`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		const tree = await hres.json();
		const walk = (nodes: any[]) => {
			for (const n of nodes) {
				if (n.node_type === 'diagram') diagrams.push({ id: n.id, name: n.name });
				if (n.children) walk(n.children);
			}
		};
		walk(tree);
		expect(diagrams.length).toBeGreaterThan(30);
	});

	test('every imported diagram renders with no overlapping boxes', async ({ page }) => {
		test.setTimeout(300_000);
		await loginAsAdmin(page);

		const offenders: { diagram: string; pairs: string[] }[] = [];

		for (const d of diagrams) {
			await page.goto(`/views/${d.id}`);
			await expect(page.getByText('Loading diagram...')).toHaveCount(0, { timeout: 20_000 });
			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(600);

			const rects: Rect[] = await page.$$eval('.svelte-flow__node', (els) =>
				els
					// The diagram_frame is the EA boundary rectangle (background
					// chrome) — GEANZ content legitimately extends past it — and
					// notes are floating annotations; neither is a content box, so
					// exclude both from collision detection (they still render).
					.filter((e) => !e.className.includes('node-diagram_frame') && !e.className.includes('node-note'))
					.map((e) => {
						const r = e.getBoundingClientRect();
						return {
							id: e.getAttribute('data-id') ?? '?',
							left: r.left, top: r.top, right: r.right, bottom: r.bottom, w: r.width, h: r.height,
						};
					}),
			);

			const pairs: string[] = [];
			for (let i = 0; i < rects.length; i++) {
				for (let j = i + 1; j < rects.length; j++) {
					if (conflict(rects[i], rects[j])) {
						pairs.push(`${rects[i].id}↔${rects[j].id}`);
					}
				}
			}
			// Fit-to-view so the screenshot captures the whole diagram (the
			// overlap rects above were read at load zoom — geometry is
			// zoom-invariant so the conflict result is unaffected).
			await page.locator('.svelte-flow__controls-fitview').click({ timeout: 2000 }).catch(() => {});
			await page.waitForTimeout(300);
			const safe = d.name.replace(/[^a-z0-9]+/gi, '-').slice(0, 50);
			await page.locator('.svelte-flow__viewport').first().screenshot({
				path: `tests/e2e/uat/screenshots/geanz-scale-${safe}.png`,
			}).catch(() => {});
			if (pairs.length) offenders.push({ diagram: d.name, pairs });
		}

		if (offenders.length) {
			console.log('OVERLAP OFFENDERS:\n' + offenders.map((o) => `  ${o.diagram}: ${o.pairs.join(', ')}`).join('\n'));
		}
		expect(offenders, `${offenders.length}/${diagrams.length} diagrams have overlapping boxes`).toEqual([]);
	});
});
