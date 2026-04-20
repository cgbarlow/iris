#!/usr/bin/env node
/**
 * Live spread-slider probe — loads the dashboard once, then mutates the d3-force
 * charge + link forces in place via `window.__irisGraph.d3Force(...)` for each
 * spread value. This isolates the behaviour of charge+link scaling; note that
 * the cluster force closes over the Svelte component scope so its target
 * distances do NOT update through this probe.
 *
 * Requires `VITE_IRIS_DEBUG=1` at frontend build time. Against a real dev
 * backend, set `IRIS_ADMIN_PASSWORD` to the dev admin password.
 *
 * Run with: npx tsx frontend/tests/probes/spread-slider-live.ts
 */

import { chromium, type Page } from 'playwright';
import { appendFileSync, existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import {
	BACKEND_URL,
	FRONTEND_URL,
	RESULTS_PATH,
	SCREENSHOT_DIR,
	computeMetrics,
	fmt,
	probeLogin,
	probeUrls,
	seedAuthInitScript,
	seedGraphSettingsInitScript,
	settingsValuesForSpread,
} from './probe-utils';

const SETTLE_AFTER_LOAD_MS = 6000;
const SETTLE_AFTER_SLIDER_MS = 5000;
const SPREADS = [1.0, 0.2, 0.5, 1.5, 2.0, 3.0] as const;

if (!existsSync(SCREENSHOT_DIR)) mkdirSync(SCREENSHOT_DIR, { recursive: true });

async function applySpreadDirect(page: Page, spread: number) {
	return await page.evaluate((s: number) => {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const fg: any = (window as any).__irisGraph;
		if (!fg) return { error: 'no graph' };
		const charge = fg.d3Force('charge');
		if (charge?.strength) {
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			charge.strength((n: any) => {
				const bases: Record<string, number> = {
					collection: -300,
					set: -200,
					package: -80,
					diagram: -40,
				};
				return (bases[n.node_type] ?? -30) * s;
			});
		}
		const link = fg.d3Force('link');
		if (link?.distance) {
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			link.distance((l: any) => {
				const tgt = typeof l.target === 'object' ? l.target : null;
				const tgtType = tgt?.node_type;
				let base = 60;
				if (l.edge_type === 'collection_membership') base = 200;
				else if (l.edge_type === 'set_membership') {
					if (tgtType === 'package') base = 60;
					else if (tgtType === 'diagram') base = 120;
					else base = 80;
				} else if (l.edge_type === 'hierarchy') {
					base = tgtType === 'package' ? 25 : 40;
				} else if (l.edge_type === 'diagram_element' || l.edge_type === 'diagram_package') {
					base = 40;
				}
				return base * s;
			});
		}
		// Cluster force closes over settings.node_spacing from Svelte scope and is
		// not mutable from here — this probe only moves charge + link.
		fg.d3ReheatSimulation();
		return { ok: true };
	}, spread);
}

async function main(): Promise<void> {
	console.log(`[live] login against ${BACKEND_URL}`);
	const auth = await probeLogin();
	const browser = await chromium.launch({ headless: true });
	const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
	await seedAuthInitScript(ctx, auth);

	const urls = probeUrls();
	const allResults: Array<Record<string, unknown>> = [];

	for (const url of urls) {
		console.log(`\n=== ${url.label} live-slider sweep ===`);
		await seedGraphSettingsInitScript(ctx, settingsValuesForSpread(1.0));

		const page = await ctx.newPage();
		page.on('pageerror', (e) => console.log('[pageerror]', e.message));
		console.log(`  loading ${FRONTEND_URL}${url.path}`);
		try {
			await page.goto(`${FRONTEND_URL}${url.path}`, {
				waitUntil: 'networkidle',
				timeout: 25000,
			});
		} catch {
			/* ignore */
		}
		await page.waitForFunction(
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			() => !!(window as any).__irisGraph,
			{ timeout: 15000 },
		);
		console.log(`  initial settle ${SETTLE_AFTER_LOAD_MS}ms…`);
		await page.waitForTimeout(SETTLE_AFTER_LOAD_MS);

		for (const spread of SPREADS) {
			console.log(`  applying spread=${spread} (live, no reload)`);
			const r = await applySpreadDirect(page, spread);
			if ('error' in r) {
				console.log(`    err: ${r.error}`);
				continue;
			}
			await page.waitForTimeout(SETTLE_AFTER_SLIDER_MS);
			const m = await computeMetrics(page, `${url.label}@live${spread}`);
			console.log(
				`    nodes=${m.node_count} mean=${fmt(m.mean_dist)} bbox=${fmt(m.bbox_w)}x${fmt(m.bbox_h)} zoom=${fmt(m.cam_zoom, 3)}`,
			);
			allResults.push({ url: url.label, spread, ...m });
			const fname = `live-${url.short}-spread${String(spread).replace('.', '_')}.png`;
			await page.screenshot({
				path: path.join(SCREENSHOT_DIR, fname),
				fullPage: false,
			});
		}
		await page.close();
	}
	await browser.close();

	let md = '\n\n---\n\n## Live-slider run (no reload between spreads)\n\n';
	md += `Loads page once at spread=1.0, then mutates charge+link forces in-place via \`window.__irisGraph.d3Force\`.\n`;
	md += `**Note:** the cluster force closure captures \`settings.node_spacing\` from the Svelte component scope, so this probe does NOT update cluster force target distances. It only updates charge & link. This isolates whether charge+link alone produce visible change.\n\n`;
	for (const url of urls) {
		md += `### ${url.label} (live-slider)\n\n| spread | nodes | mean dist | bbox W×H | camera zoom |\n|---|---|---|---|---|\n`;
		for (const r of allResults.filter((x) => x.url === url.label) as Array<Record<string, unknown>>) {
			if (r.error) {
				md += `| ${r.spread} | ERR ${String(r.error)} | | | |\n`;
				continue;
			}
			md += `| ${r.spread} | ${r.node_count} | ${fmt(r.mean_dist)} | ${fmt(r.bbox_w, 0)}×${fmt(r.bbox_h, 0)} | ${fmt(r.cam_zoom, 3)} |\n`;
		}
		md += `\n`;
	}
	appendFileSync(RESULTS_PATH, md);
	console.log('\n[live] DONE — appended to', RESULTS_PATH);
}

main().catch((e) => {
	console.error(e);
	process.exit(1);
});
