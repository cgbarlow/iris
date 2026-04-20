/**
 * UAT-scale regression: knowledge graph cluster collapse on large single-collection
 * datasets (ADR-119 / SPEC-119-A).
 *
 * Injects a real captured /api/graph response (711 nodes, 1349 edges —
 * DoView Strategy Models collection from UAT: 1 × 11 × 60 × 639) via
 * page.route, mirroring the UAT user's visibility state (Elements off,
 * "Direct diagram links" off). Asserts that the force layout produces
 * per-set clusters that are substantially tighter than the gaps between
 * them — a property that fails when ADR-118's bidirectional target-
 * distance separator at the set and package layers caps inter-cluster
 * separation and collapses everything to the graph centre.
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

test.describe('Knowledge graph — UAT-scale cluster collapse (ADR-119)', () => {
	test.describe.configure({ timeout: 180_000 });

	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('per-set clusters must separate, not collapse to centre', async ({
		page,
	}) => {
		const fixtureRaw = fs.readFileSync(FIXTURE_PATH, 'utf-8');

		// Intercept the graph data endpoint — return the captured UAT payload.
		await page.route(/\/api\/graph(\?[^/]*)?$/, async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: fixtureRaw,
			});
		});

		// Intercept graph settings — mirror the UAT screenshot's state
		// (elements hidden, Direct diagram links unchecked, defaults else).
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
							direct_diagram_links: false,
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
		// Generous settle — 711 nodes need more simulation iterations than
		// the smaller seeds used in the SPEC-118-A regression tests.
		await page.waitForTimeout(15_000);

		type Cluster = {
			setId: string;
			setName: string;
			diagrams: Array<{ x: number; y: number }>;
		};
		const clusters: Cluster[] = await page.evaluate(() => {
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const fg: any = (window as any).__irisGraph;
			const data = fg.graphData();
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const nodes: any[] = data.nodes || [];
			// Derive set ownership of each diagram via the edge structure —
			// set_membership targets both packages and diagrams, hierarchy
			// edges go from packages to diagrams. Walk diagram→package via
			// hierarchy, package→set via set_membership.
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
			const out = new Map<
				string,
				{ setName: string; diagrams: Array<{ x: number; y: number }> }
			>();
			for (const n of nodes) {
				if (n.node_type !== 'diagram') continue;
				if (!Number.isFinite(n.x) || !Number.isFinite(n.y)) continue;
				const pkg = diagToPkg.get(n.id);
				if (!pkg) continue;
				const sid = pkgToSet.get(pkg);
				if (!sid) continue;
				const sNode = nodeById.get(sid);
				if (!out.has(sid)) {
					out.set(sid, { setName: sNode?.name ?? sid, diagrams: [] });
				}
				out.get(sid)!.diagrams.push({ x: n.x, y: n.y });
			}
			return [...out.entries()].map(([setId, v]) => ({
				setId,
				setName: v.setName,
				diagrams: v.diagrams,
			}));
		});

		expect(
			clusters.length,
			'fixture must produce at least 2 sets with diagrams',
		).toBeGreaterThanOrEqual(2);

		// Per-set centroids (from diagrams only — the set node itself would
		// skew a tight cluster).
		const centroids = clusters.map((c) => {
			const n = c.diagrams.length;
			return {
				id: c.setId,
				name: c.setName,
				cx: c.diagrams.reduce((s, d) => s + d.x, 0) / n,
				cy: c.diagrams.reduce((s, d) => s + d.y, 0) / n,
			};
		});

		// Mean cluster radius (average distance from a diagram to its own set
		// centroid, averaged over all sets).
		let radiusSum = 0;
		let radiusCount = 0;
		for (let i = 0; i < clusters.length; i++) {
			const c = centroids[i];
			for (const d of clusters[i].diagrams) {
				radiusSum += Math.hypot(d.x - c.cx, d.y - c.cy);
				radiusCount++;
			}
		}
		const meanRadius = radiusSum / Math.max(radiusCount, 1);

		// Mean pairwise inter-centroid distance.
		let interSum = 0;
		let interCount = 0;
		for (let i = 0; i < centroids.length; i++) {
			for (let j = i + 1; j < centroids.length; j++) {
				interSum += Math.hypot(
					centroids[i].cx - centroids[j].cx,
					centroids[i].cy - centroids[j].cy,
				);
				interCount++;
			}
		}
		const meanInter = interSum / Math.max(interCount, 1);

		console.log(
			`mean cluster radius: ${meanRadius.toFixed(0)} px; mean inter-centroid: ${meanInter.toFixed(0)} px; ratio ${(meanRadius / meanInter).toFixed(2)}`,
		);
		for (const c of centroids) {
			const n = clusters.find((cl) => cl.setId === c.id)!.diagrams.length;
			console.log(
				`  ${c.name.padEnd(30)} n=${n.toString().padStart(3)} centroid=(${c.cx.toFixed(0).padStart(5)},${c.cy.toFixed(0).padStart(5)})`,
			);
		}

		// Primary regression assertion: clusters must be substantially tighter
		// than the gaps between them. Pre-fix behaviour: meanRadius ≈ 140 px,
		// meanInter ≈ 100 px (ratio > 1 — clusters overlap so heavily that
		// every set's diagrams are nearer another set's centroid than their
		// own). Post-fix expectation: meanRadius < 0.5 × meanInter.
		expect(
			meanRadius,
			`mean cluster radius (${meanRadius.toFixed(0)} px) must be less than half the mean inter-centroid distance (${meanInter.toFixed(0)} px). When this fails, the 11 per-set clusters have collapsed toward the graph centre and are visually indistinguishable — the UAT "everything in one ball" symptom.`,
		).toBeLessThan(meanInter * 0.5);

		// Secondary: the spread between the farthest centroids must be
		// reasonable for 711 nodes. Pre-fix: max ≈ 200 px (everything near
		// origin). Post-fix: expect at least 500 px max separation.
		let maxInter = 0;
		for (let i = 0; i < centroids.length; i++) {
			for (let j = i + 1; j < centroids.length; j++) {
				maxInter = Math.max(
					maxInter,
					Math.hypot(
						centroids[i].cx - centroids[j].cx,
						centroids[i].cy - centroids[j].cy,
					),
				);
			}
		}
		expect(
			maxInter,
			`max pairwise inter-centroid distance (${maxInter.toFixed(0)} px) must exceed 500 px — with 11 sets and 711 nodes, anything tighter indicates the set-layer force is capping separation.`,
		).toBeGreaterThan(500);
	});
});
