#!/usr/bin/env node
/**
 * Fresh-load spread slider probe — reloads the dashboard for each spread value,
 * captures node-distance metrics, and writes results as Markdown. Used as the
 * baseline reading for the 1× vs 3× target-distance decision in SPEC-118-A.
 *
 * Requires `VITE_IRIS_DEBUG=1` at frontend build time so `window.__irisGraph`
 * is exposed. Against a real dev backend, also set `IRIS_ADMIN_PASSWORD` to the
 * dev admin password (defaults to the e2e test fixture password otherwise).
 *
 * Run with: npx tsx frontend/tests/probes/spread-slider-probe.ts --label=baseline
 */

import { chromium } from 'playwright';
import {
	existsSync,
	mkdirSync,
	readFileSync,
	writeFileSync,
} from 'node:fs';
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

const SETTLE_MS = 8000;
const SPREADS = [0.2, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0] as const;

const LABEL = (
	process.argv.find((a) => a.startsWith('--label=')) || '--label=baseline'
).split('=')[1];

if (!existsSync(SCREENSHOT_DIR)) mkdirSync(SCREENSHOT_DIR, { recursive: true });

async function main(): Promise<void> {
	console.log(`[probe] login against ${BACKEND_URL}`);
	const auth = await probeLogin();
	console.log(`[probe] logged in (user=${(auth.user as { username?: string } | null)?.username ?? '?'})`);

	const browser = await chromium.launch({ headless: true });
	const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
	await seedAuthInitScript(ctx, auth);

	const urls = probeUrls();
	const results: Array<Record<string, unknown>> = [];

	for (const url of urls) {
		console.log(`\n[probe] === ${url.label} (${url.path}) ===`);
		for (const spread of SPREADS) {
			const settings = settingsValuesForSpread(spread);
			await seedGraphSettingsInitScript(ctx, settings);
			const page = await ctx.newPage();
			page.on('pageerror', (e) => console.log('[pageerror]', e.message));
			console.log(`  spread=${spread} → loading ${FRONTEND_URL}${url.path}`);
			try {
				await page.goto(`${FRONTEND_URL}${url.path}`, {
					waitUntil: 'networkidle',
					timeout: 25000,
				});
			} catch (e) {
				console.log(
					`    [warn] networkidle timeout, continuing: ${(e as Error).message}`,
				);
			}
			try {
				await page.waitForFunction(
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					() => !!(window as any).__irisGraph,
					{ timeout: 15000 },
				);
			} catch {
				console.log(`    [error] no __irisGraph after 15s — skipping`);
				results.push({ url: url.label, spread, error: 'no graph hook' });
				await page.close();
				continue;
			}
			console.log(`    settling ${SETTLE_MS}ms…`);
			await page.waitForTimeout(SETTLE_MS);

			const m = await computeMetrics(page, `${url.label}@${spread}`);
			console.log(
				`    nodes=${m.node_count} mean=${fmt(m.mean_dist)} bbox=${fmt(m.bbox_w)}x${fmt(m.bbox_h)} cols=${m.collection_count ?? '?'} overlap=${m.overlap_pairs ?? '?'}`,
			);
			results.push({ url: url.label, spread, ...m });

			if ([0.2, 1.0, 2.0, 3.0].includes(spread)) {
				const fname = `${LABEL}-${url.short}-spread${String(spread).replace('.', '_')}.png`;
				await page.screenshot({
					path: path.join(SCREENSHOT_DIR, fname),
					fullPage: false,
				});
				console.log(`    saved ${fname}`);
			}
			await page.close();
		}
	}

	await browser.close();

	let md = '';
	if (existsSync(RESULTS_PATH)) {
		md = readFileSync(RESULTS_PATH, 'utf8');
		md += '\n\n---\n\n';
	} else {
		md = `# Spread Slider Experiment — Raw Results\n\n`;
	}
	md += `## Run: ${LABEL} (${new Date().toISOString()})\n\n`;
	md += `Frontend: ${FRONTEND_URL}  ·  Backend: ${BACKEND_URL}  ·  Settle: ${SETTLE_MS}ms  ·  Spreads: ${SPREADS.join(', ')}\n\n`;

	for (const url of urls) {
		md += `### ${url.label} (\`${url.path}\`)\n\n`;
		md += `| spread | nodes | mean dist | median | min | max | stddev | CV | bbox W×H | collections | inter-col distances | overlap |\n`;
		md += `|---|---|---|---|---|---|---|---|---|---|---|---|\n`;
		for (const r of results.filter((x) => x.url === url.label) as Array<Record<string, unknown>>) {
			if (r.error) {
				md += `| ${r.spread} | ERROR: ${String(r.error)} | | | | | | | | | | |\n`;
				continue;
			}
			md += `| ${r.spread} | ${r.node_count} | ${fmt(r.mean_dist)} | ${fmt(r.median_dist)} | ${fmt(r.min_dist)} | ${fmt(r.max_dist)} | ${fmt(r.stddev)} | ${fmt(r.cv, 3)} | ${fmt(r.bbox_w, 0)}×${fmt(r.bbox_h, 0)} | ${r.collection_count ?? '?'} | ${((r.inter_collection_dists as number[] | undefined) || []).join(', ') || '–'} | ${r.overlap_pairs ?? '?'} |\n`;
		}
		md += `\n`;
		const baseline = (results.filter((x) => x.url === url.label && !x.error) as Array<Record<string, unknown>>)
			.find((x) => x.spread === 1.0);
		const cols = baseline?.collections as Array<Record<string, unknown>> | undefined;
		if (cols && cols.length > 1) {
			md += `**Per-collection sizes (spread=1.0):**\n\n| collection | node count | bbox W×H | centroid |\n|---|---|---|---|\n`;
			for (const c of cols) {
				md += `| ${c.id} | ${c.count} | ${c.w}×${c.h} | (${c.cx}, ${c.cy}) |\n`;
			}
			md += `\n`;
		}
	}

	writeFileSync(RESULTS_PATH, md);
	console.log(`\n[probe] wrote ${RESULTS_PATH}`);
	console.log(`[probe] DONE`);
}

main().catch((e) => {
	console.error(e);
	process.exit(1);
});
