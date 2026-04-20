#!/usr/bin/env node
/**
 * UI-driven spread-slider probe — opens the settings panel, navigates to the
 * Display tab, and drives the `<input type="range" min="0.2" max="3">` slider
 * via DOM `input`+`change` events in the same order a user would when dragging.
 * This is the closest representation of the live user-reported bug.
 *
 * Requires `VITE_IRIS_DEBUG=1` at frontend build time. Against a real dev
 * backend, set `IRIS_ADMIN_PASSWORD` to the dev admin password.
 *
 * Run with: npx tsx frontend/tests/probes/spread-slider-ui.ts
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
const SPREADS = [1.0, 0.2, 0.5, 1.5, 2.0, 2.5, 3.0] as const;

if (!existsSync(SCREENSHOT_DIR)) mkdirSync(SCREENSHOT_DIR, { recursive: true });

async function dragSlider(page: Page, value: number) {
	return await page.evaluate((v: number) => {
		const inputs = Array.from(
			document.querySelectorAll<HTMLInputElement>('input[type="range"]'),
		);
		const slider = inputs.find((i) => i.min === '0.2' && i.max === '3');
		if (!slider) return { error: 'no slider found', count: inputs.length };
		slider.value = String(v);
		slider.dispatchEvent(new Event('input', { bubbles: true }));
		slider.dispatchEvent(new Event('change', { bubbles: true }));
		return { ok: true, value: slider.value };
	}, value);
}

async function main(): Promise<void> {
	console.log(`[ui] login against ${BACKEND_URL}`);
	const auth = await probeLogin();
	const browser = await chromium.launch({ headless: true });
	const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
	await seedAuthInitScript(ctx, auth);

	const urls = probeUrls();
	const allResults: Array<Record<string, unknown>> = [];

	for (const url of urls) {
		console.log(`\n=== ${url.label} UI-driven sweep ===`);
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

		const settingsButton = page.locator('button[title="Graph settings"]');
		try {
			await settingsButton.click({ timeout: 5000 });
			console.log(`  opened settings panel`);
		} catch (e) {
			console.log(`  [warn] couldn't click settings button: ${(e as Error).message}`);
		}
		await page.waitForTimeout(500);
		try {
			await page.locator('button:has-text("Display")').click({ timeout: 3000 });
			console.log(`  switched to Display tab`);
		} catch (e) {
			console.log(`  [warn] couldn't click Display tab: ${(e as Error).message}`);
		}
		await page.waitForTimeout(500);

		for (const spread of SPREADS) {
			console.log(`  drag slider → spread=${spread}`);
			const r = await dragSlider(page, spread);
			if ('error' in r) {
				console.log(`    err: ${r.error} (${r.count} range inputs)`);
				continue;
			}
			await page.waitForTimeout(SETTLE_AFTER_SLIDER_MS);
			const m = await computeMetrics(page, `${url.label}@ui${spread}`);
			const interColStr = (m.inter_collection_dists ?? []).length
				? ` interCol=[${(m.inter_collection_dists ?? []).join(',')}]`
				: '';
			console.log(
				`    nodes=${m.node_count} mean=${fmt(m.mean_dist)} bbox=${fmt(m.bbox_w)}x${fmt(m.bbox_h)} zoom=${fmt(m.cam_zoom, 3)}${interColStr}`,
			);
			allResults.push({ url: url.label, spread, ...m });
			const fname = `ui-${url.short}-spread${String(spread).replace('.', '_')}.png`;
			await page.screenshot({
				path: path.join(SCREENSHOT_DIR, fname),
				fullPage: false,
			});
		}
		await page.close();
	}
	await browser.close();

	let md = '\n\n---\n\n## UI-driven slider run (open settings panel, drag spread slider)\n\n';
	md += `Page loads at default spread=1.0. Slider is then driven via DOM events in the order: 1.0, 0.2, 0.5, 1.5, 2.0, 2.5, 3.0. Camera is NEVER manually fitted between drags — only the simulation reheats. This is the closest representation of the live user experience.\n\n`;
	for (const url of urls) {
		md += `### ${url.label} (UI-driven)\n\n| spread | nodes | mean dist | bbox W×H | camera zoom | inter-col distances |\n|---|---|---|---|---|---|\n`;
		for (const r of allResults.filter((x) => x.url === url.label) as Array<Record<string, unknown>>) {
			if (r.error) {
				md += `| ${r.spread} | ERR ${String(r.error)} | | | | |\n`;
				continue;
			}
			md += `| ${r.spread} | ${r.node_count} | ${fmt(r.mean_dist)} | ${fmt(r.bbox_w, 0)}×${fmt(r.bbox_h, 0)} | ${fmt(r.cam_zoom, 3)} | ${((r.inter_collection_dists as number[] | undefined) || []).join(', ') || '–'} |\n`;
		}
		md += `\n`;
		const rows = (allResults.filter(
			(x) => x.url === url.label && Array.isArray(x.collections) && (x.collections as unknown[]).length > 1,
		) as Array<Record<string, unknown>>);
		if (rows.length > 0) {
			const firstCols = rows[0].collections as Array<Record<string, unknown>>;
			md += `**Per-collection bbox (UI-driven):**\n\n| spread | ${firstCols.map((c) => c.id).join(' | ')} |\n|---|${firstCols.map(() => '---').join('|')}|\n`;
			for (const r of rows) {
				const cols = r.collections as Array<Record<string, unknown>>;
				md += `| ${r.spread} | ${cols.map((c) => `n=${c.count} ${c.w}×${c.h} @(${c.cx},${c.cy})`).join(' | ')} |\n`;
			}
			md += `\n`;
		}
	}
	appendFileSync(RESULTS_PATH, md);
	console.log('\n[ui] DONE — appended to', RESULTS_PATH);
}

main().catch((e) => {
	console.error(e);
	process.exit(1);
});
