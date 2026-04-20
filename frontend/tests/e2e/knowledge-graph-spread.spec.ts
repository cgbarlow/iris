/**
 * Regression test for the multi-collection spread-slider fix (ADR-118 / SPEC-118-A).
 *
 * Seeds a multi-collection graph (2 collections × 2 sets × 3 root packages per
 * set) via the API, opens the dashboard, drives the real <input type="range">
 * spread slider at {0.2, 1.0, 3.0}, and reads back graph geometry via the
 * VITE_IRIS_DEBUG-gated window.__irisGraph hook. Asserts three invariants:
 *
 *   1. bbox growth 0.2 → 3.0 is bounded (ratio < 50×);
 *   2. mean inter-collection centroid distance is monotonic non-decreasing;
 *   3. no pair of collection bboxes overlap at spread=3.0.
 */

import { expect, test, type Page } from '@playwright/test';
import {
	createCollection,
	createPackage,
	createSet,
	getAuthToken,
	loginAsAdmin,
	seedAdmin,
} from './fixtures';

const SETTLE_MS = 8000;
const TAG = `kg-spread-${Date.now()}`;

type Metrics = {
	bbox_w: number;
	bbox_h: number;
	mean_inter_col: number;
	collections: Array<{ id: string; cx: number; cy: number; w: number; h: number }>;
	orphanCentroid: { cx: number; cy: number; count: number } | null;
};

async function setSpread(page: Page, value: number): Promise<void> {
	// Open settings panel and switch to Display tab if not already there — same
	// pattern as frontend/tests/probes/spread-slider-ui.ts.
	const settingsBtn = page.locator('button[title="Graph settings"]');
	if (await settingsBtn.count()) {
		const panelVisible = await page
			.locator('input[type="range"][min="0.2"][max="3"]')
			.first()
			.isVisible()
			.catch(() => false);
		if (!panelVisible) {
			await settingsBtn.click();
			await page.waitForTimeout(200);
			const displayTab = page.locator('button:has-text("Display")');
			if (await displayTab.count()) {
				await displayTab.click();
				await page.waitForTimeout(200);
			}
		}
	}
	const applied = await page.evaluate((v: number) => {
		const inputs = Array.from(
			document.querySelectorAll<HTMLInputElement>('input[type="range"]'),
		);
		const slider = inputs.find((i) => i.min === '0.2' && i.max === '3');
		if (!slider) return false;
		slider.value = String(v);
		slider.dispatchEvent(new Event('input', { bubbles: true }));
		slider.dispatchEvent(new Event('change', { bubbles: true }));
		return true;
	}, value);
	expect(applied, 'spread slider (min=0.2, max=3) must be present').toBe(true);
	await page.waitForTimeout(SETTLE_MS);
}

async function readMetrics(page: Page): Promise<Metrics> {
	return (await page.evaluate(() => {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const fg: any = (window as any).__irisGraph;
		if (!fg || typeof fg.graphData !== 'function') {
			throw new Error(
				'window.__irisGraph not defined — is VITE_IRIS_DEBUG=1 set at build time?',
			);
		}
		const data = fg.graphData();
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const nodes: any[] = (data.nodes || []).filter(
			(n: { x?: number; y?: number }) =>
				Number.isFinite(n.x) && Number.isFinite(n.y),
		);
		if (nodes.length < 2) {
			throw new Error(`not enough valid node positions: ${nodes.length}`);
		}

		let minX = Infinity;
		let maxX = -Infinity;
		let minY = Infinity;
		let maxY = -Infinity;
		for (const n of nodes) {
			if (n.x < minX) minX = n.x;
			if (n.x > maxX) maxX = n.x;
			if (n.y < minY) minY = n.y;
			if (n.y > maxY) maxY = n.y;
		}

		const setToCol = new Map<string, string>();
		const nodeToSet = new Map<string, string>();
		for (const l of data.links || []) {
			const src = typeof l.source === 'object' ? l.source.id : l.source;
			const tgt = typeof l.target === 'object' ? l.target.id : l.target;
			if (l.edge_type === 'collection_membership') setToCol.set(tgt, src);
			if (l.edge_type === 'set_membership') nodeToSet.set(tgt, src);
		}
		for (let pass = 0; pass < 5; pass++) {
			for (const l of data.links || []) {
				if (l.edge_type !== 'hierarchy') continue;
				const src = typeof l.source === 'object' ? l.source.id : l.source;
				const tgt = typeof l.target === 'object' ? l.target.id : l.target;
				if (!nodeToSet.has(tgt) && nodeToSet.has(src)) {
					nodeToSet.set(tgt, nodeToSet.get(src) as string);
				}
			}
		}
		const colMap = new Map<
			string,
			{ sx: number; sy: number; n: number; mn: number; mx: number; mny: number; mxy: number }
		>();
		for (const n of nodes) {
			let cid: string | undefined;
			if (n.node_type === 'collection') cid = n.id;
			else {
				const sid =
					nodeToSet.get(n.id) || (n.node_type === 'set' ? n.id : null);
				if (sid) cid = setToCol.get(sid);
			}
			if (!cid) continue;
			let c = colMap.get(cid);
			if (!c) {
				c = { sx: 0, sy: 0, n: 0, mn: Infinity, mx: -Infinity, mny: Infinity, mxy: -Infinity };
				colMap.set(cid, c);
			}
			c.sx += n.x;
			c.sy += n.y;
			c.n++;
			if (n.x < c.mn) c.mn = n.x;
			if (n.x > c.mx) c.mx = n.x;
			if (n.y < c.mny) c.mny = n.y;
			if (n.y > c.mxy) c.mxy = n.y;
		}
		const collections: Array<{
			id: string;
			cx: number;
			cy: number;
			w: number;
			h: number;
		}> = [];
		for (const [id, c] of colMap) {
			if (c.n === 0) continue;
			collections.push({
				id,
				cx: c.sx / c.n,
				cy: c.sy / c.n,
				w: c.mx - c.mn,
				h: c.mxy - c.mny,
			});
		}
		const interCol: number[] = [];
		for (let i = 0; i < collections.length; i++) {
			for (let j = i + 1; j < collections.length; j++) {
				const dx = collections[i].cx - collections[j].cx;
				const dy = collections[i].cy - collections[j].cy;
				interCol.push(Math.sqrt(dx * dx + dy * dy));
			}
		}
		const meanInter =
			interCol.length > 0
				? interCol.reduce((s, v) => s + v, 0) / interCol.length
				: 0;

		// Orphan-set centroid: aggregate of nodes whose resolved set has no
		// collection_membership edge. Exercises the SPEC-118-A orphan-set
		// contract — without the __orphan_<sid> synthetic collection grouping,
		// these nodes have no collection-layer force and drift unboundedly.
		let orphanSx = 0;
		let orphanSy = 0;
		let orphanN = 0;
		for (const n of nodes) {
			let sid: string | undefined;
			if (n.node_type === 'set') sid = n.id;
			else sid = nodeToSet.get(n.id);
			if (!sid) continue;
			if (setToCol.has(sid)) continue;
			orphanSx += n.x;
			orphanSy += n.y;
			orphanN++;
		}
		const orphanCentroid =
			orphanN > 0
				? { cx: orphanSx / orphanN, cy: orphanSy / orphanN, count: orphanN }
				: null;

		return {
			bbox_w: maxX - minX,
			bbox_h: maxY - minY,
			mean_inter_col: meanInter,
			collections,
			orphanCentroid,
		};
	})) as Metrics;
}

test.describe('Knowledge graph — multi-collection spread slider (ADR-118)', () => {
	// Seed seeds several hundred packages via sequential API calls + the test
	// itself drives three 8s simulation settles, so the default 30s doesn't fit.
	test.describe.configure({ timeout: 300_000 });

	test.beforeAll(async () => {
		await seedAdmin();
		const token = await getAuthToken();

		// Seed enough depth and breadth that the three-level cluster force has
		// real work to do: the buggy cubic-amplified, cross-collection-compounding
		// model only visibly "loses the plot" once the graph has ~100+ nodes of
		// hierarchy per collection. Shape: 3 collections × 3 sets × 4 root
		// packages × 3 children × 2 grandchildren = 216 leaves + 72 middle +
		// 36 roots + 9 sets + 3 collections ≈ 336 graph nodes. Names are
		// timestamped to avoid collision across runs.
		for (let ci = 0; ci < 3; ci++) {
			const col = await createCollection(undefined, token, {
				name: `${TAG}-col-${ci}`,
				description: 'Spread-slider regression seed',
			});
			for (let si = 0; si < 3; si++) {
				const set = await createSet(undefined, token, {
					name: `${TAG}-col${ci}-set${si}`,
					collection_id: col.id as string,
				});
				for (let pi = 0; pi < 4; pi++) {
					const root = await createPackage(undefined, token, {
						name: `${TAG}-col${ci}-set${si}-pkg${pi}`,
						set_id: set.id as string,
					});
					for (let chi = 0; chi < 3; chi++) {
						const child = await createPackage(undefined, token, {
							name: `${TAG}-col${ci}-set${si}-pkg${pi}-c${chi}`,
							set_id: set.id as string,
							parent_package_id: root.id as string,
						});
						for (let gi = 0; gi < 2; gi++) {
							await createPackage(undefined, token, {
								name: `${TAG}-col${ci}-set${si}-pkg${pi}-c${chi}-g${gi}`,
								set_id: set.id as string,
								parent_package_id: child.id as string,
							});
						}
					}
				}
			}
		}

		// Orphan set: no collection_id. Exercises SPEC-118-A orphan-set
		// contract. Without the collection-layer __orphan_<sid> binding,
		// these nodes have no counter-force against charge repulsion and
		// drift unboundedly outward as spread rises.
		const orphanSet = await createSet(undefined, token, {
			name: `${TAG}-orphan-default`,
		});
		for (let pi = 0; pi < 4; pi++) {
			const root = await createPackage(undefined, token, {
				name: `${TAG}-orphan-pkg${pi}`,
				set_id: orphanSet.id as string,
			});
			for (let chi = 0; chi < 2; chi++) {
				await createPackage(undefined, token, {
					name: `${TAG}-orphan-pkg${pi}-c${chi}`,
					set_id: orphanSet.id as string,
					parent_package_id: root.id as string,
				});
			}
		}
	});

	test('spread slider behaves smoothly on multi-collection graph', async ({ page }) => {
		test.setTimeout(120_000);
		await loginAsAdmin(page);
		// Land on dashboard and wait for the force-graph hook.
		await page.goto('/');
		await page.waitForFunction(
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			() => !!(window as any).__irisGraph,
			{ timeout: 20_000 },
		);
		// Initial settle at default spread.
		await page.waitForTimeout(SETTLE_MS);

		// Sweep three representative values.
		await setSpread(page, 0.2);
		const low = await readMetrics(page);

		await setSpread(page, 1.0);
		const mid = await readMetrics(page);

		await setSpread(page, 3.0);
		const high = await readMetrics(page);

		// Must have seeded at least two collections.
		expect(high.collections.length).toBeGreaterThanOrEqual(2);

		// #1 — bbox stays bounded 0.2 → 3.0 (ratio < 50×).
		const lowArea = Math.max(low.bbox_w * low.bbox_h, 1);
		const highArea = high.bbox_w * high.bbox_h;
		expect(
			highArea / lowArea,
			`bbox area at spread=3.0 (${highArea.toFixed(0)}) should not exceed 50× bbox area at spread=0.2 (${lowArea.toFixed(0)})`,
		).toBeLessThan(50);

		// #2 — mean inter-collection centroid distance is monotonic non-decreasing.
		expect(
			mid.mean_inter_col,
			`mean inter-collection distance at spread=1.0 should not be less than at 0.2`,
		).toBeGreaterThanOrEqual(low.mean_inter_col);
		expect(
			high.mean_inter_col,
			`mean inter-collection distance at spread=3.0 should not be less than at 1.0`,
		).toBeGreaterThanOrEqual(mid.mean_inter_col);

		// #3 — no pair of collection bboxes overlap at spread=3.0.
		for (let i = 0; i < high.collections.length; i++) {
			for (let j = i + 1; j < high.collections.length; j++) {
				const a = high.collections[i];
				const b = high.collections[j];
				const dx = Math.abs(a.cx - b.cx);
				const dy = Math.abs(a.cy - b.cy);
				const sepX = dx - (a.w + b.w) / 2;
				const sepY = dy - (a.h + b.h) / 2;
				expect(
					Math.max(sepX, sepY),
					`collection bboxes ${a.id.slice(0, 8)} and ${b.id.slice(0, 8)} must be disjoint on at least one axis at spread=3.0`,
				).toBeGreaterThan(0);
			}
		}
	});

	test('orphan set (no collection) stays bounded under spread sweep', async ({
		page,
	}) => {
		// Regression for the orphan-set drift bug observed on
		// feature/knowledge-graph after ADR-118 landed: a set with
		// collection_id=NULL (the "default" set) received no collection-layer
		// force and drifted outward unboundedly as spread oscillated. Fix:
		// orphan sets join the collection-layer force under a synthetic
		// __orphan_<sid> group so the bidirectional target-distance separator
		// pulls them back when farther than target.
		test.setTimeout(180_000);
		await loginAsAdmin(page);
		await page.goto('/');
		await page.waitForFunction(
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			() => !!(window as any).__irisGraph,
			{ timeout: 20_000 },
		);
		await page.waitForTimeout(SETTLE_MS);

		// Up-down-up hysteresis sweep. Pre-fix the orphan set ratchets outward
		// with each rise and fails to retract on drop; post-fix it is bound to
		// a neighborhood of the collection cluster by the collection-layer
		// force.
		await setSpread(page, 3.0);
		await setSpread(page, 0.2);
		await setSpread(page, 3.0);
		const m = await readMetrics(page);

		expect(m.orphanCentroid, 'orphan set must be present in seed').not.toBeNull();
		expect(m.collections.length).toBeGreaterThanOrEqual(2);

		// Orphan centroid should sit within the same neighbourhood as the real
		// collection centroids — not far outside them. Compare against the
		// farthest collection centroid magnitude plus a verlet-noise slack. At
		// spread=3.0 the collection-layer target is 400·3 = 1200, so a healthy
		// orphan sits ≤ ~1.5× the outermost collection; we allow 3× + 800 for
		// headroom while still catching the unbounded-drift regression.
		const maxColMag = Math.max(
			...m.collections.map((c) => Math.sqrt(c.cx * c.cx + c.cy * c.cy)),
		);
		const orphanMag = Math.sqrt(
			m.orphanCentroid!.cx * m.orphanCentroid!.cx +
				m.orphanCentroid!.cy * m.orphanCentroid!.cy,
		);
		expect(
			orphanMag,
			`orphan-set centroid magnitude (${orphanMag.toFixed(0)}) after up-down-up sweep must stay within 3× the farthest collection centroid magnitude (${maxColMag.toFixed(0)}) + 800 slack. Unbounded growth indicates the orphan set is missing collection-layer binding (SPEC-118-A).`,
		).toBeLessThan(maxColMag * 3 + 800);
	});
});
