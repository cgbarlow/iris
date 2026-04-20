/**
 * Shared helpers for the knowledge-graph spread-slider probes.
 *
 * Reuses getAuthToken and ADMIN_PASSWORD from the e2e fixtures so probes stay
 * aligned with how Playwright tests authenticate (SPEC-118-A; DRY per protocol #13).
 */

import type { BrowserContext, Page } from 'playwright';
import { ADMIN_PASSWORD, ADMIN_USERNAME, getAuthToken } from '../e2e/fixtures';

export const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
export const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
export const SINGLE_COLLECTION_ID = process.env.IRIS_SINGLE_COLLECTION_ID || '';
/** Probes default to the e2e fixture password. Override with IRIS_ADMIN_PASSWORD
 *  when running against a real dev backend seeded with different credentials. */
export const PROBE_ADMIN_PASSWORD = process.env.IRIS_ADMIN_PASSWORD || ADMIN_PASSWORD;
export const PROBE_ADMIN_USERNAME = process.env.IRIS_ADMIN_USERNAME || ADMIN_USERNAME;
export const OUTPUT_DIR =
	process.env.IRIS_PROBE_OUTPUT_DIR ||
	new URL('./output/', import.meta.url).pathname;
export const SCREENSHOT_DIR = `${OUTPUT_DIR.replace(/\/$/, '')}/screenshots`;
export const RESULTS_PATH = `${OUTPUT_DIR.replace(/\/$/, '')}/results.md`;

export type ProbeUrl = { label: string; short: string; path: string };

/** The URLs the probes exercise. The single-collection URL is only included if
 *  IRIS_SINGLE_COLLECTION_ID is set — it's environment-specific seed data. */
export function probeUrls(): ProbeUrl[] {
	const urls: ProbeUrl[] = [
		{ label: 'multi-collection', short: 'multi', path: '/' },
	];
	if (SINGLE_COLLECTION_ID) {
		urls.push({
			label: 'single-collection',
			short: 'single',
			path: `/?collection_id=${SINGLE_COLLECTION_ID}`,
		});
	}
	return urls;
}

/** Authenticate via the backend API and fetch the `/api/auth/me` user object
 *  so callers can populate the iris_auth store shape. */
export async function probeLogin(): Promise<{
	accessToken: string;
	refreshToken: string | null;
	user: unknown;
}> {
	const accessToken = await getAuthToken(
		BACKEND_URL,
		PROBE_ADMIN_USERNAME,
		PROBE_ADMIN_PASSWORD,
	);
	const me = await fetch(`${BACKEND_URL}/api/auth/me`, {
		headers: { Authorization: `Bearer ${accessToken}` },
	});
	const user = me.ok ? await me.json() : null;
	return { accessToken, refreshToken: null, user };
}

/** Inject the auth payload into sessionStorage + localStorage so the Svelte
 *  auth store initialises without going through the login form. */
export async function seedAuthInitScript(
	ctx: BrowserContext,
	auth: { accessToken: string; refreshToken: string | null; user: unknown },
): Promise<void> {
	const storedAuth = JSON.stringify(auth);
	await ctx.addInitScript((stored: string) => {
		try {
			sessionStorage.setItem('iris_auth', stored);
			localStorage.setItem('iris_auth', stored);
		} catch {
			/* ignore */
		}
	}, storedAuth);
}

/** Pre-seed every scope the dashboard might consult so the scope cascade doesn't
 *  override the spread value we're testing. */
export function settingsValuesForSpread(spread: number): Record<string, unknown> {
	return {
		nodes: {
			collection: true,
			set: true,
			package: true,
			diagram: true,
			element: true,
		},
		edges: {
			collection_membership: true,
			set_membership: true,
			hierarchy: true,
			diagram_link: true,
			diagram_element: true,
			diagram_package: true,
			package_relationship: true,
			element_relationship: true,
		},
		label_density: 10,
		node_spacing: spread,
		size_contrast: 1.0,
		link_length: spread,
	};
}

/** Write the graph-settings localStorage keys the dashboard cascade reads. */
export async function seedGraphSettingsInitScript(
	ctx: BrowserContext,
	settings: Record<string, unknown>,
): Promise<void> {
	const json = JSON.stringify(settings);
	const singleId = SINGLE_COLLECTION_ID;
	await ctx.addInitScript(
		({ sJson, collectionId }: { sJson: string; collectionId: string }) => {
			try {
				localStorage.setItem('iris-graph-settings-migrated', '1');
				localStorage.setItem('iris-graph-settings:__global__', sJson);
				if (collectionId) {
					localStorage.setItem(`iris-graph-settings:${collectionId}`, sJson);
				}
			} catch {
				/* ignore */
			}
		},
		{ sJson: json, collectionId: singleId },
	);
}

export type Metrics = {
	scope: string;
	node_count: number;
	valid_count?: number;
	sample_size?: number;
	pair_count?: number;
	mean_dist: number;
	median_dist?: number;
	min_dist?: number;
	max_dist?: number;
	stddev?: number;
	cv?: number;
	bbox_w: number;
	bbox_h: number;
	centroid_x?: number;
	centroid_y?: number;
	collection_count?: number;
	collections?: Array<{
		id: string;
		count: number;
		cx: number;
		cy: number;
		w: number;
		h: number;
	}>;
	inter_collection_dists?: number[];
	overlap_pairs?: number;
	cam_zoom?: number | null;
	cam_centre?: unknown;
	error?: string;
};

/** Pairwise-distance and per-collection metrics computed in-browser from the
 *  exposed `window.__irisGraph` force-graph instance. Requires
 *  `VITE_IRIS_DEBUG=1` at build time so the hook is present. */
export async function computeMetrics(page: Page, scope: string): Promise<Metrics> {
	return (await page.evaluate(
		({ scopeLabel }: { scopeLabel: string }) => {
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const fg: any = (window as any).__irisGraph;
			if (!fg || typeof fg.graphData !== 'function') {
				return { error: 'no __irisGraph hook', scope: scopeLabel };
			}
			const data = fg.graphData();
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const nodes: any[] = data.nodes || [];
			if (nodes.length === 0) return { error: 'no nodes', scope: scopeLabel };

			const valid = nodes.filter(
				(n) => Number.isFinite(n.x) && Number.isFinite(n.y),
			);
			if (valid.length < 2) {
				return { error: 'fewer than 2 valid positions', scope: scopeLabel };
			}

			let minX = Infinity;
			let maxX = -Infinity;
			let minY = Infinity;
			let maxY = -Infinity;
			for (const n of valid) {
				if (n.x < minX) minX = n.x;
				if (n.x > maxX) maxX = n.x;
				if (n.y < minY) minY = n.y;
				if (n.y > maxY) maxY = n.y;
			}
			const bboxW = maxX - minX;
			const bboxH = maxY - minY;
			const cx = (minX + maxX) / 2;
			const cy = (minY + maxY) / 2;

			const SAMPLE = Math.min(valid.length, 250);
			const step = Math.max(1, Math.floor(valid.length / SAMPLE));
			const idxs: number[] = [];
			for (let i = 0; i < valid.length && idxs.length < SAMPLE; i += step) {
				idxs.push(i);
			}

			const dists: number[] = [];
			for (let i = 0; i < idxs.length; i++) {
				for (let j = i + 1; j < idxs.length; j++) {
					const a = valid[idxs[i]];
					const b = valid[idxs[j]];
					const dx = a.x - b.x;
					const dy = a.y - b.y;
					dists.push(Math.sqrt(dx * dx + dy * dy));
				}
			}
			dists.sort((a, b) => a - b);
			const sum = dists.reduce((s, v) => s + v, 0);
			const mean = sum / dists.length;
			const median = dists[Math.floor(dists.length / 2)];
			const min = dists[0];
			const max = dists[dists.length - 1];
			const variance =
				dists.reduce((s, v) => s + (v - mean) ** 2, 0) / dists.length;
			const stddev = Math.sqrt(variance);
			const cv = mean > 0 ? stddev / mean : 0;

			// Per-collection centroids: group nodes by collection (resolved through set→collection)
			const setToCol = new Map<string, string>();
			const nodeToSet = new Map<string, string>();
			for (const l of data.links || []) {
				const src = typeof l.source === 'object' ? l.source.id : l.source;
				const tgt = typeof l.target === 'object' ? l.target.id : l.target;
				if (l.edge_type === 'collection_membership') setToCol.set(tgt, src);
				if (l.edge_type === 'set_membership') nodeToSet.set(tgt, src);
				if (l.edge_type === 'hierarchy') {
					if (!nodeToSet.has(tgt) && nodeToSet.has(src)) {
						nodeToSet.set(tgt, nodeToSet.get(src) as string);
					}
				}
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
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const colCentroids = new Map<string, { sx: number; sy: number; count: number; nodes: any[] }>();
			for (const n of valid) {
				let colId: string | undefined;
				if (n.node_type === 'collection') colId = n.id;
				else {
					const sid =
						nodeToSet.get(n.id) || (n.node_type === 'set' ? n.id : null);
					if (sid) colId = setToCol.get(sid);
				}
				if (!colId) continue;
				let c = colCentroids.get(colId);
				if (!c) {
					c = { sx: 0, sy: 0, count: 0, nodes: [] };
					colCentroids.set(colId, c);
				}
				c.sx += n.x;
				c.sy += n.y;
				c.count++;
				c.nodes.push(n);
			}
			const colStats: Array<{
				id: string;
				count: number;
				cx: number;
				cy: number;
				w: number;
				h: number;
			}> = [];
			for (const [id, c] of colCentroids) {
				if (c.count === 0) continue;
				const cxC = c.sx / c.count;
				const cyC = c.sy / c.count;
				let mn = Infinity;
				let mx = -Infinity;
				let mny = Infinity;
				let mxy = -Infinity;
				for (const n of c.nodes) {
					if (n.x < mn) mn = n.x;
					if (n.x > mx) mx = n.x;
					if (n.y < mny) mny = n.y;
					if (n.y > mxy) mxy = n.y;
				}
				colStats.push({
					id: id.slice(0, 8),
					count: c.count,
					cx: cxC,
					cy: cyC,
					w: mx - mn,
					h: mxy - mny,
				});
			}
			const interCol: number[] = [];
			for (let i = 0; i < colStats.length; i++) {
				for (let j = i + 1; j < colStats.length; j++) {
					const dx = colStats[i].cx - colStats[j].cx;
					const dy = colStats[i].cy - colStats[j].cy;
					interCol.push(Math.sqrt(dx * dx + dy * dy));
				}
			}
			let overlap = 0;
			const RADIUS = 6;
			for (let i = 0; i < idxs.length; i++) {
				for (let j = i + 1; j < idxs.length; j++) {
					const a = valid[idxs[i]];
					const b = valid[idxs[j]];
					if (
						Math.abs(a.x - b.x) < RADIUS * 2 &&
						Math.abs(a.y - b.y) < RADIUS * 2
					) {
						const dx = a.x - b.x;
						const dy = a.y - b.y;
						if (dx * dx + dy * dy < (RADIUS * 2) ** 2) overlap++;
					}
				}
			}
			return {
				scope: scopeLabel,
				node_count: nodes.length,
				valid_count: valid.length,
				sample_size: idxs.length,
				pair_count: dists.length,
				mean_dist: mean,
				median_dist: median,
				min_dist: min,
				max_dist: max,
				stddev,
				cv,
				bbox_w: bboxW,
				bbox_h: bboxH,
				centroid_x: cx,
				centroid_y: cy,
				collection_count: colStats.length,
				collections: colStats.map((c) => ({
					...c,
					cx: Math.round(c.cx),
					cy: Math.round(c.cy),
					w: Math.round(c.w),
					h: Math.round(c.h),
				})),
				inter_collection_dists: interCol.map((d) => Math.round(d)),
				overlap_pairs: overlap,
				cam_zoom: typeof fg.zoom === 'function' ? fg.zoom() : null,
			};
		},
		{ scopeLabel: scope },
	)) as Metrics;
}

export function fmt(n: unknown, p = 1): string {
	if (typeof n !== 'number' || !Number.isFinite(n)) return '–';
	return Number(n).toFixed(p);
}
