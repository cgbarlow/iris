/**
 * Knowledge graph — radial hierarchy ordering (ADR-120 / SPEC-120-A).
 *
 * Asserts that each galaxy (a set + its packages + its diagrams) lays out
 * with the hierarchy flowing radially outward: the set node is closest to
 * the collection centre, packages sit between set and diagrams, and
 * diagrams sit outside their packages. Concretely — for each set, the
 * mean distance from its packages to the set node must be LESS than the
 * mean distance from its diagrams to the set node.
 *
 * Pre-fix reality on the UAT fixture (v4.0.3 force model): every diagram
 * has both a set_membership edge (set→diagram, distance 120) and a
 * hierarchy edge (package→diagram, distance 25). The N short hierarchy
 * links collectively yank the package outward through its own children,
 * so packages settle BEYOND their diagrams. The radial hierarchy inverts.
 *
 * Post-fix (ADR-120 radial layer force): per-galaxy forceRadial pins each
 * node type to a prescribed radius band inside its governing collection,
 * so `set < package < diagram < element` is enforced directionally.
 */

import { expect, test } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loginAsAdmin, seedAdmin } from './fixtures';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE_PATH = path.resolve(
	HERE,
	'../fixtures/uat-doview-strategy-models-graph.json',
);
const UAT_COLLECTION_ID = 'b302d473-cad6-4145-8391-d05b5a29c42c';

test.describe('Knowledge graph — radial hierarchy ordering (ADR-120)', () => {
	test.describe.configure({ timeout: 180_000 });

	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('packages must sit between set and diagrams (not outside their own children)', async ({
		page,
	}) => {
		const fixtureRaw = fs.readFileSync(FIXTURE_PATH, 'utf-8');

		await page.route(/\/api\/graph(\?[^/]*)?$/, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: fixtureRaw,
			});
		});

		// Defaults: all hierarchy layers visible. The radial ordering must
		// hold with the full hierarchy in view — that's the case users see
		// when they open a collection.
		await page.route(/\/api\/graph\/settings/, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					scope_type: 'collection',
					scope_id: UAT_COLLECTION_ID,
					settings: {
						nodes: {
							collection: true,
							set: true,
							package: true,
							diagram: true,
							element: false,
						},
						edges: {
							collection_membership: true,
							set_membership: true,
							direct_diagram_links: true,
							hierarchy: true,
							diagram_element: false,
							diagram_package: false,
							diagram_link: false,
							package_relationship: false,
							element_relationship: false,
						},
						label_density: 10,
						node_spacing: 1.0,
						size_contrast: 1.0,
						link_length: 1.0,
					},
					updated_at: null,
					updated_by: null,
				}),
			});
		});

		await loginAsAdmin(page);
		await page.goto(`/?collection_id=${UAT_COLLECTION_ID}`);
		await page.waitForFunction(
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			() => !!(window as any).__irisGraph,
			{ timeout: 30_000 },
		);
		await page.waitForTimeout(15_000);

		type PerSet = {
			setId: string;
			setName: string;
			sx: number;
			sy: number;
			packages: Array<{ x: number; y: number }>;
			diagrams: Array<{ x: number; y: number }>;
		};

		const perSet: PerSet[] = await page.evaluate(() => {
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const fg: any = (window as any).__irisGraph;
			const data = fg.graphData();
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const nodes: any[] = data.nodes || [];
			const nodeById = new Map(nodes.map((n) => [n.id, n]));

			const pkgToSet = new Map<string, string>();
			const diagToPkg = new Map<string, string>();
			for (const l of data.links || []) {
				const src = typeof l.source === 'object' ? l.source.id : l.source;
				const tgt = typeof l.target === 'object' ? l.target.id : l.target;
				if (l.edge_type === 'set_membership') {
					const t = nodeById.get(tgt);
					if (t?.node_type === 'package') pkgToSet.set(tgt, src);
				} else if (l.edge_type === 'hierarchy') {
					const s = nodeById.get(src);
					if (s?.node_type === 'package') diagToPkg.set(tgt, src);
				}
			}

			const out = new Map<string, PerSet>();
			for (const n of nodes) {
				if (n.node_type !== 'set') continue;
				if (!Number.isFinite(n.x) || !Number.isFinite(n.y)) continue;
				out.set(n.id, {
					setId: n.id,
					setName: n.name ?? n.id,
					sx: n.x,
					sy: n.y,
					packages: [],
					diagrams: [],
				});
			}
			for (const n of nodes) {
				if (!Number.isFinite(n.x) || !Number.isFinite(n.y)) continue;
				if (n.node_type === 'package') {
					const sid = pkgToSet.get(n.id);
					if (sid && out.has(sid)) {
						out.get(sid)!.packages.push({ x: n.x, y: n.y });
					}
				} else if (n.node_type === 'diagram') {
					const pkg = diagToPkg.get(n.id);
					if (!pkg) continue;
					const sid = pkgToSet.get(pkg);
					if (sid && out.has(sid)) {
						out.get(sid)!.diagrams.push({ x: n.x, y: n.y });
					}
				}
			}
			return [...out.values()].filter(
				(s) => s.packages.length > 0 && s.diagrams.length > 0,
			);
		});

		expect(
			perSet.length,
			'fixture must produce at least 3 sets with both packages and diagrams',
		).toBeGreaterThanOrEqual(3);

		// For each set, compute mean distance from (pkgs | diagrams) → set node.
		const rows = perSet.map((s) => {
			const meanDist = (pts: Array<{ x: number; y: number }>) =>
				pts.reduce((sum, p) => sum + Math.hypot(p.x - s.sx, p.y - s.sy), 0) /
				pts.length;
			return {
				name: s.setName,
				nPkg: s.packages.length,
				nDiag: s.diagrams.length,
				rPkg: meanDist(s.packages),
				rDiag: meanDist(s.diagrams),
			};
		});

		for (const r of rows) {
			console.log(
				`  ${r.name.padEnd(30)} pkgs n=${r.nPkg.toString().padStart(3)} r=${r.rPkg.toFixed(0).padStart(4)}  diags n=${r.nDiag.toString().padStart(3)} r=${r.rDiag.toFixed(0).padStart(4)}  ${r.rPkg < r.rDiag ? 'ok' : 'INVERTED'}`,
			);
		}

		// Primary invariant: most sets must satisfy packages < diagrams in
		// radial distance from the set node. Allow a small tolerance for
		// the occasional odd-shaped galaxy where a very small package count
		// can randomly land outside — but require the overwhelming majority
		// to be correctly ordered.
		const ordered = rows.filter((r) => r.rPkg < r.rDiag).length;
		const orderedRatio = ordered / rows.length;

		console.log(
			`radially ordered sets: ${ordered}/${rows.length} (${(orderedRatio * 100).toFixed(0)}%)`,
		);

		expect(
			orderedRatio,
			`at least 80% of sets must lay out with packages closer to their set node than diagrams (got ${ordered}/${rows.length} = ${(orderedRatio * 100).toFixed(0)}%). The hierarchy should flow set → packages → diagrams outward.`,
		).toBeGreaterThanOrEqual(0.8);

		// Secondary invariant: the GLOBAL means should also be ordered. Sums
		// each layer's distance independently — robust to very-small-count
		// sets where one pkg pulling outside throws off the per-set ratio.
		const totalPkg = rows.reduce((s, r) => s + r.rPkg * r.nPkg, 0);
		const countPkg = rows.reduce((s, r) => s + r.nPkg, 0);
		const totalDiag = rows.reduce((s, r) => s + r.rDiag * r.nDiag, 0);
		const countDiag = rows.reduce((s, r) => s + r.nDiag, 0);
		const globalMeanPkg = totalPkg / countPkg;
		const globalMeanDiag = totalDiag / countDiag;

		console.log(
			`global mean package-radius=${globalMeanPkg.toFixed(0)} px, diagram-radius=${globalMeanDiag.toFixed(0)} px`,
		);

		expect(
			globalMeanPkg,
			`global mean package radius (${globalMeanPkg.toFixed(0)} px) must be less than global mean diagram radius (${globalMeanDiag.toFixed(0)} px). When packages are larger than diagrams, the hierarchy has inverted.`,
		).toBeLessThan(globalMeanDiag);
	});
});
