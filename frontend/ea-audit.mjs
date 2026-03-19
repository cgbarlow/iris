#!/usr/bin/env node
/**
 * EA Visual Audit Script — Iterative Improvement Loop
 *
 * Runs a visual audit of Iris diagrams against ground truth expectations,
 * supports multiple iterations with before/after comparison to track
 * improvement over successive fix rounds.
 *
 * Usage:
 *   node ea-audit.mjs [--set AIXM|FIXM|APM_META|APM_ESSENTIAL] [--limit N] [--iteration N]
 *                      [--set-id <uuid>] [--handle-strategy auto|none|center]
 *                      [--skip-visual-compare]
 *
 * Iterations:
 *   --iteration 0   Baseline scan (default). Saves to audit_iter_0.json
 *   --iteration 1   First fix round. Compares against iter 0.
 *   --iteration 2   Second fix round. Compares against iter 1.
 *   --iteration 3   Final verification. Compares against iter 2.
 *
 * Handle strategies:
 *   --handle-strategy auto     Record that auto-handle routing is active (default)
 *   --handle-strategy none     Record that SvelteFlow auto-pick routing is active
 *   --handle-strategy center   Record that center-handle routing is active
 *
 * Each run creates a dated subfolder under <git-root>/ea-visual-audit/:
 *   ea-visual-audit/YYYY-MM-DD_NNN/
 *     audit_iter_{N}.json        — raw findings
 *     AUDIT_ITER_{N}.md          — human-readable report
 *     AUDIT_COMPARISON_{N}.md    — delta vs previous (N>0)
 *     AUDIT_SUMMARY.md           — cumulative progress (updated each run)
 *   ea-visual-audit/AUDIT_SUMMARY.md — always updated at top level too
 *
 * Prerequisites:
 *   - Backend running on :8000, frontend on :5173
 *   - JWT token saved to /tmp/iris_token.txt
 *   - Playwright chromium installed: npx playwright install chromium
 */
import { chromium } from '@playwright/test';
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { execSync } from 'node:child_process';
import { createRequire } from 'node:module';

// ── Configuration ──────────────────────────────────────────────────────────
const IRIS_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8000';
const MAX_ITERATIONS = 3;

// Fallback set IDs — used when dynamic discovery fails
const FALLBACK_SETS = {
  AIXM:           'cc4c40e5-a5c6-41ec-9b89-b6073e2c83c0',
  FIXM:           'cb3011c7-d16d-4637-ad48-843c28bfa21a',
  APM_META:       '6d6823eb-c35e-40d6-adf2-d6ca5e4765af',
  APM_ESSENTIAL:  '962ef0ec-95e7-469f-a8fa-8499964f7965',
};

// Parse CLI args
const args = process.argv.slice(2);
function getArg(name) {
  const idx = args.indexOf(`--${name}`);
  return idx >= 0 ? args[idx + 1] : null;
}
const setFilter = getArg('set');
const setIdArg = getArg('set-id');
const limitArg = parseInt(getArg('limit') || '0');
const iteration = parseInt(getArg('iteration') || '0');
const handleStrategy = getArg('handle-strategy') || 'auto';
const skipVisualCompare = args.includes('--skip-visual-compare');

// Ground truth base paths (relative to git root)
const GROUND_TRUTH_DIR = 'sparxea_imports/ground_truth';
const AIXM_GT_BASE = 'https://aixm.aero/sites/default/files/imce/AIXM511HTML/AIXM';

if (iteration < 0 || iteration > MAX_ITERATIONS) {
  console.error(`Iteration must be 0-${MAX_ITERATIONS}`);
  process.exit(1);
}

// ── Output Directory (git root based, dated subfolder) ────────────────────
function findGitRoot() {
  try {
    return execSync('git rev-parse --show-toplevel', { encoding: 'utf-8' }).trim();
  } catch {
    // Fallback: walk up from cwd looking for .git
    let dir = process.cwd();
    while (dir !== '/') {
      if (existsSync(join(dir, '.git'))) return dir;
      dir = resolve(dir, '..');
    }
    return process.cwd();
  }
}

const gitRoot = findGitRoot();
const BASE_OUTPUT_DIR = resolve(gitRoot, 'ea-visual-audit');

/** Create a unique dated subfolder: ea-visual-audit/YYYY-MM-DD_NNN/ */
function createRunDir() {
  if (!existsSync(BASE_OUTPUT_DIR)) mkdirSync(BASE_OUTPUT_DIR, { recursive: true });
  const today = new Date().toISOString().split('T')[0];
  let seq = 1;
  while (existsSync(join(BASE_OUTPUT_DIR, `${today}_${String(seq).padStart(3, '0')}`))) {
    seq++;
  }
  const runDir = join(BASE_OUTPUT_DIR, `${today}_${String(seq).padStart(3, '0')}`);
  mkdirSync(runDir, { recursive: true });
  return runDir;
}

/**
 * Find the most recent run directory that contains a given iteration file.
 * Searches dated subdirs in reverse chronological order.
 */
function findIterationFile(iterNum) {
  if (!existsSync(BASE_OUTPUT_DIR)) return null;
  const entries = readdirSync(BASE_OUTPUT_DIR)
    .filter(e => statSync(join(BASE_OUTPUT_DIR, e)).isDirectory())
    .sort()
    .reverse();
  for (const dir of entries) {
    const candidate = join(BASE_OUTPUT_DIR, dir, `audit_iter_${iterNum}.json`);
    if (existsSync(candidate)) return candidate;
  }
  // Also check the base dir itself (legacy flat layout)
  const legacy = join(BASE_OUTPUT_DIR, `audit_iter_${iterNum}.json`);
  if (existsSync(legacy)) return legacy;
  return null;
}

// ── Auth ───────────────────────────────────────────────────────────────────
function getToken() {
  const tokenPath = '/tmp/iris_token.txt';
  if (!existsSync(tokenPath)) {
    console.error('ERROR: No token at /tmp/iris_token.txt. Generate one first.');
    console.error('HINT: Token expires after 30 min. For long audit sessions, use access_token_expire_minutes=120');
    process.exit(1);
  }
  return readFileSync(tokenPath, 'utf-8').trim();
}

/** Re-read token from disk (for mid-run refresh after expiry). */
function refreshToken() {
  const tokenPath = '/tmp/iris_token.txt';
  if (!existsSync(tokenPath)) return null;
  return readFileSync(tokenPath, 'utf-8').trim();
}

// ── API Helpers ────────────────────────────────────────────────────────────

/** Discover available sets from the API. Returns map of name -> setId. */
async function discoverSets(token) {
  try {
    const resp = await fetch(`${API_URL}/api/sets?page_size=100`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    const sets = {};
    for (const s of (data.items || data)) {
      // Map set names to short keys
      const name = s.name || '';
      if (name.includes('AIXM')) sets.AIXM = s.id;
      else if (name.includes('FIXM') && name.includes('Extension')) sets.FIXM = s.id;
      else if (name.includes('FIXM')) sets.FIXM = sets.FIXM || s.id;
      else if (name.includes('APM') && name.includes('Metamodel')) sets.APM_META = s.id;
      else if (name.includes('Essential') || name.includes('APM')) sets.APM_ESSENTIAL = sets.APM_ESSENTIAL || s.id;
      else sets[name.replace(/[^a-zA-Z0-9]/g, '_').toUpperCase()] = s.id;
    }
    return Object.keys(sets).length > 0 ? sets : null;
  } catch {
    return null;
  }
}

async function fetchAllDiagrams(token, setId) {
  const all = [];
  let page = 1;
  while (true) {
    const resp = await fetch(
      `${API_URL}/api/diagrams?set_id=${setId}&page_size=100&page=${page}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!resp.ok) {
      // If 401, try refreshing token once
      if (resp.status === 401) {
        const newToken = refreshToken();
        if (newToken && newToken !== token) {
          const retry = await fetch(
            `${API_URL}/api/diagrams?set_id=${setId}&page_size=100&page=${page}`,
            { headers: { Authorization: `Bearer ${newToken}` } }
          );
          if (retry.ok) {
            const data = await retry.json();
            all.push(...data.items);
            if (all.length >= data.total) break;
            page++;
            continue;
          }
        }
      }
      throw new Error(`API error ${resp.status}: ${await resp.text()}`);
    }
    const data = await resp.json();
    all.push(...data.items);
    if (all.length >= data.total) break;
    page++;
  }
  return all;
}

async function fetchDiagramDetail(token, id) {
  let resp = await fetch(`${API_URL}/api/diagrams/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  // Retry with refreshed token on 401
  if (resp.status === 401) {
    const newToken = refreshToken();
    if (newToken && newToken !== token) {
      resp = await fetch(`${API_URL}/api/diagrams/${id}`, {
        headers: { Authorization: `Bearer ${newToken}` },
      });
    }
  }
  if (!resp.ok) throw new Error(`API error ${resp.status} for diagram ${id}`);
  return resp.json();
}

// ── Ground Truth Visual Comparison ────────────────────────────────────────

/**
 * Resolve the ground truth source for a diagram.
 * Returns { type: 'png'|'html'|'none', path: string } where path is a
 * local file path (for png) or URL (for html).
 */
function resolveGroundTruth(setName, diagramName, diagramIndex) {
  if (setName === 'APM_ESSENTIAL') {
    const pngPath = join(gitRoot, GROUND_TRUTH_DIR,
      'The Essential Architecture - APM', `${diagramIndex + 1}_apm.png`);
    if (existsSync(pngPath)) return { type: 'png', path: pngPath };
  }
  if (setName === 'APM_META') {
    const pngPath = join(gitRoot, GROUND_TRUTH_DIR,
      'APM Metamodel', 'APM Metamodel.png');
    if (existsSync(pngPath)) return { type: 'png', path: pngPath };
  }
  if (setName === 'AIXM') {
    const encodedName = encodeURIComponent(diagramName).replace(/%20/g, '%20');
    const url = `${AIXM_GT_BASE}/Diagram_${encodedName}.html`;
    return { type: 'html', path: url };
  }
  // FIXM NAS has PDF ground truth — skip for now (PDF screenshot requires external tools)
  // FIXM Core has no ground truth
  return { type: 'none', path: null };
}

/**
 * Screenshot the Iris diagram canvas area (excluding toolbar/sidebar).
 * Triggers SvelteFlow's "fit view" first to ensure the full diagram is visible,
 * then screenshots the viewport element.
 */
async function screenshotIrisDiagram(page) {
  // Click the fit-to-view button if available (SvelteFlow controls)
  try {
    const fitBtn = await page.$('.svelte-flow__controls button[title*="fit"], .svelte-flow__controls button:last-child');
    if (fitBtn) {
      await fitBtn.click();
      await page.waitForTimeout(500); // Let the zoom animation settle
    }
  } catch { /* ignore if no fit button */ }

  // Try to find the SvelteFlow viewport and screenshot just that
  const viewport = await page.$('.svelte-flow');
  if (viewport) {
    return viewport.screenshot({ type: 'png' });
  }
  // Fallback: full page
  return page.screenshot({ type: 'png', fullPage: false });
}

/**
 * Get ground truth image as a PNG buffer.
 * For PNG files: read from disk.
 * For HTML pages: open in a new Playwright page and screenshot.
 */
async function getGroundTruthImage(browser, gt) {
  if (gt.type === 'png') {
    return readFileSync(gt.path);
  }
  if (gt.type === 'html') {
    const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const gtPage = await ctx.newPage();
    try {
      await gtPage.goto(gt.path, { timeout: 15000, waitUntil: 'networkidle' });
      await gtPage.waitForTimeout(1000);
      // AIXM HTML pages: screenshot the diagram image/SVG within the page
      const diagramEl = await gtPage.$('img, svg, .diagram, #diagram, [class*="diagram"]');
      if (diagramEl) {
        const buf = await diagramEl.screenshot({ type: 'png' });
        await ctx.close();
        return buf;
      }
      const buf = await gtPage.screenshot({ type: 'png', fullPage: false });
      await ctx.close();
      return buf;
    } catch (e) {
      await ctx.close();
      return null;
    }
  }
  return null;
}

/**
 * Extract the dominant color palette from a ground truth PNG image.
 * Loads the image into an offscreen canvas inside Playwright and clusters
 * pixel colors, ignoring white/black/grey (background/text).
 *
 * Returns an array of { color: '#rrggbb', percentage: N } sorted by frequency.
 */
async function analyzeGroundTruthColors(page, gtBuffer) {
  const gtB64 = gtBuffer.toString('base64');
  return page.evaluate(async (b64) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; });

    const canvas = document.createElement('canvas');
    canvas.width = img.width; canvas.height = img.height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;

    // Bucket non-white, non-black, non-grey colors into 16-level quantized bins
    const buckets = {};
    let totalSampled = 0;
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i], g = data[i + 1], b = data[i + 2];
      // Skip near-white (background)
      if (r > 220 && g > 220 && b > 220) continue;
      // Skip near-black (text/lines)
      if (r < 40 && g < 40 && b < 40) continue;
      // Skip greys (r≈g≈b within tolerance)
      if (Math.abs(r - g) < 30 && Math.abs(g - b) < 30 && Math.abs(r - b) < 30) continue;

      totalSampled++;
      // Quantize to 16-level buckets for clustering
      const qr = Math.floor(r / 16) * 16;
      const qg = Math.floor(g / 16) * 16;
      const qb = Math.floor(b / 16) * 16;
      const key = `${qr},${qg},${qb}`;
      buckets[key] = (buckets[key] || 0) + 1;
    }

    // Convert to sorted array, return top colors
    const totalPixels = (data.length / 4);
    const colors = Object.entries(buckets)
      .map(([key, count]) => {
        const [r, g, b] = key.split(',').map(Number);
        const hex = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
        return { color: hex, count, percentage: parseFloat(((count / totalPixels) * 100).toFixed(2)) };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 20);

    return {
      colors,
      totalColoredPixels: totalSampled,
      totalColoredPct: parseFloat(((totalSampled / totalPixels) * 100).toFixed(1)),
      hasMultipleHues: colors.length >= 3,
      imageSize: { w: img.width, h: img.height },
    };
  }, gtB64);
}

/**
 * Generate a side-by-side HTML comparison report for a set of diagrams.
 * This is the primary visual output — human-reviewable with automated check
 * results annotated alongside the images.
 */
function generateComparisonHtml(runDir, allResults) {
  let html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>EA Visual Audit — Side-by-Side Comparison</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
  h1 { color: #e94560; }
  .diagram { border: 1px solid #444; margin: 20px 0; padding: 20px; background: #16213e; border-radius: 8px; }
  .diagram h2 { margin-top: 0; color: #0f3460; background: #e94560; padding: 8px 16px; border-radius: 4px; display: inline-block; }
  .images { display: flex; gap: 12px; margin: 12px 0; }
  .images figure { flex: 1; margin: 0; text-align: center; }
  .images img { max-width: 100%; border: 2px solid #333; border-radius: 4px; background: #fff; }
  .images figcaption { font-size: 13px; color: #aaa; margin-top: 4px; }
  .checks { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 8px; }
  .check { padding: 8px 12px; border-radius: 4px; font-size: 13px; }
  .check.pass { background: #1b4332; color: #95d5b2; }
  .check.fail { background: #4a1520; color: #f4978e; }
  .check.info { background: #1a365d; color: #90cdf4; }
  .check .label { font-weight: 600; }
  .colors { display: flex; gap: 4px; margin: 8px 0; flex-wrap: wrap; }
  .swatch { width: 32px; height: 32px; border-radius: 4px; border: 2px solid #555; display: inline-block; }
  .color-section { display: flex; gap: 24px; }
  .color-section > div { flex: 1; }
  summary { cursor: pointer; color: #e94560; font-weight: 600; }
</style></head><body>
<h1>EA Visual Audit — Side-by-Side Comparison</h1>
<p>Generated: ${new Date().toISOString()}</p>\n`;

  for (const [setName, results] of Object.entries(allResults)) {
    html += `<h2>${setName}</h2>\n`;
    for (const r of results) {
      const actionable = r.issues.filter(i => i.severity !== 'info');
      const status = actionable.length === 0 ? 'PASS' : `${actionable.length} ISSUES`;
      const statusColor = actionable.length === 0 ? '#95d5b2' : '#f4978e';

      html += `<div class="diagram">
  <h2>${r.name}</h2> <span style="color:${statusColor};font-weight:600">${status}</span>\n`;

      // Side-by-side images (if screenshots exist)
      const safeName = r.name.replace(/[^a-zA-Z0-9_-]/g, '_');
      html += `  <div class="images">
    <figure><img src="screenshots/${setName}/${safeName}_iris.png" alt="Iris"><figcaption>Iris Rendering</figcaption></figure>
    <figure><img src="screenshots/${setName}/${safeName}_gt.png" alt="Ground Truth"><figcaption>Ground Truth (EA)</figcaption></figure>
  </div>\n`;

      // Color comparison
      if (r.gtColorAnalysis?.colors?.length > 0) {
        html += `  <div class="color-section">
    <div><strong>GT Colors:</strong><div class="colors">`;
        for (const c of r.gtColorAnalysis.colors.slice(0, 10)) {
          html += `<span class="swatch" style="background:${c.color}" title="${c.color} (${c.percentage}%)"></span>`;
        }
        html += `</div></div>
    <div><strong>Iris Colors:</strong><div class="colors">`;
        if (r.renderedColors) {
          for (const c of r.renderedColors.slice(0, 10)) {
            html += `<span class="swatch" style="background:${c}" title="${c}"></span>`;
          }
        }
        html += `</div></div></div>\n`;
      }

      // Check results
      html += `  <div class="checks">\n`;
      for (const issue of r.issues) {
        const cls = issue.severity === 'info' ? 'info' : 'fail';
        html += `    <div class="check ${cls}"><span class="label">[${issue.severity}] ${issue.type}:</span> ${issue.detail}</div>\n`;
      }
      for (const c of r.correct) {
        html += `    <div class="check pass"><span class="label">✓</span> ${c}</div>\n`;
      }
      html += `  </div>\n</div>\n`;
    }
  }

  html += '</body></html>';
  writeFileSync(join(runDir, 'COMPARISON.html'), html);
  console.log(`  Side-by-side report: ${join(runDir, 'COMPARISON.html')}`);
}

// ── Audit Logic ────────────────────────────────────────────────────────────
async function auditDiagram(page, diagramId, diagramName, apiData) {
  const issues = [];
  const correct = [];
  const nodes = apiData?.data?.nodes || [];
  const edges = apiData?.data?.edges || [];

  // Navigate to diagram
  try {
    await page.goto(`${IRIS_URL}/diagrams/${diagramId}`, { timeout: 20000 });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2500);
  } catch (e) {
    issues.push({ type: 'navigation_error', severity: 'critical', detail: e.message });
    return { issues, correct };
  }

  // Check for page errors
  const errorEl = await page.$('.error-message, [role="alert"]');
  if (errorEl) {
    const errText = await errorEl.textContent();
    issues.push({ type: 'page_error', severity: 'critical', detail: errText?.trim().slice(0, 200) });
    return { issues, correct };
  }

  // ── 1. Node count ──
  const renderedNodes = await page.$$('.svelte-flow__node');
  const contentNodes = nodes.filter(n => n.type !== 'diagram_frame');
  const frameDom = await page.$('.diagram-frame-node, [data-type="diagram_frame"]');
  const adjustedRendered = frameDom ? renderedNodes.length - 1 : renderedNodes.length;

  if (adjustedRendered !== contentNodes.length) {
    issues.push({
      type: 'missing_nodes', severity: 'critical',
      detail: `API: ${contentNodes.length} nodes, DOM: ${adjustedRendered} (delta: ${contentNodes.length - adjustedRendered})`,
    });
  } else {
    correct.push(`Node count: ${contentNodes.length}`);
  }

  // ── 2. Edge count ──
  const renderedEdges = await page.$$('.svelte-flow__edge');
  if (renderedEdges.length !== edges.length) {
    issues.push({
      type: 'missing_edges', severity: 'critical',
      detail: `API: ${edges.length} edges, DOM: ${renderedEdges.length} (delta: ${edges.length - renderedEdges.length})`,
    });
  } else {
    correct.push(`Edge count: ${edges.length}`);
  }

  // ── 3. Content clipping ──
  const clippedNodes = await page.evaluate(() => {
    const clipped = [];
    document.querySelectorAll('.svelte-flow__node').forEach(el => {
      const inner = el.querySelector('.uml-node, .note-node, [class*="renderer"]');
      if (inner && inner.scrollHeight > inner.clientHeight + 2) {
        const label = inner.querySelector('.uml-node__label, .node-label')?.textContent || 'unknown';
        clipped.push({ label: label.trim(), overflow: inner.scrollHeight - inner.clientHeight });
      }
    });
    return clipped;
  });
  if (clippedNodes.length > 0) {
    issues.push({
      type: 'content_clipping', severity: 'high',
      detail: `${clippedNodes.length} nodes clipped: ${clippedNodes.slice(0, 5).map(c => `${c.label}(+${c.overflow}px)`).join(', ')}`,
    });
  } else {
    correct.push('No content clipping');
  }

  // ── 4. Text overflow (informational — CSS ellipsis is expected) ──
  const overflowNodes = await page.evaluate(() => {
    const items = [];
    document.querySelectorAll('.uml-node__label, .uml-node__attr, .uml-node__stereotype').forEach(el => {
      if (el.scrollWidth > el.clientWidth + 2) {
        items.push({ text: el.textContent?.trim().slice(0, 40), overflow: el.scrollWidth - el.clientWidth });
      }
    });
    return items;
  });
  if (overflowNodes.length > 0) {
    issues.push({
      type: 'text_overflow', severity: 'info',
      detail: `${overflowNodes.length} text elements truncated by CSS ellipsis (expected for fixed-width nodes)`,
    });
  }

  // ── 5. Missing edge markers ──
  const edgeMarkerCheck = await page.evaluate(() => {
    const results = { composition: 0, aggregation: 0, generalization: 0 };
    document.querySelectorAll('.svelte-flow__edge').forEach(edge => {
      const path = edge.querySelector('path');
      if (!path) return;
      const markerEnd = path.getAttribute('marker-end') || '';
      const markerStart = path.getAttribute('marker-start') || '';
      if (markerEnd.includes('diamond-filled') || markerStart.includes('diamond-filled')) results.composition++;
      if (markerEnd.includes('diamond-open') || markerStart.includes('diamond-open')) results.aggregation++;
      if (markerEnd.includes('triangle') || markerStart.includes('triangle')) results.generalization++;
    });
    return results;
  });

  const expectedComposition = edges.filter(e => {
    const t = (e.data?.edgeType || e.data?.type || '').toLowerCase();
    return t.includes('composition');
  }).length;
  const expectedAggregation = edges.filter(e => {
    const t = (e.data?.edgeType || e.data?.type || '').toLowerCase();
    return t.includes('aggregation');
  }).length;

  if (expectedComposition > 0 && edgeMarkerCheck.composition === 0) {
    issues.push({
      type: 'missing_markers', severity: 'high',
      detail: `Expected ${expectedComposition} composition diamonds, found 0 in DOM`,
    });
  }
  if (expectedAggregation > 0 && edgeMarkerCheck.aggregation === 0) {
    issues.push({
      type: 'missing_markers', severity: 'high',
      detail: `Expected ${expectedAggregation} aggregation diamonds, found 0 in DOM`,
    });
  }

  // ── 6. Stereotype formatting ──
  const stereotypes = await page.evaluate(() => {
    const items = [];
    document.querySelectorAll('.uml-node__stereotype').forEach(el => {
      const text = el.textContent?.trim() || '';
      items.push(text);
    });
    return items;
  });
  const badStereotypes = stereotypes.filter(s => s && !s.startsWith('\u00AB') && !s.startsWith('<<'));
  if (badStereotypes.length > 0) {
    issues.push({
      type: 'stereotype_format', severity: 'low',
      detail: `${badStereotypes.length} stereotypes missing guillemets: ${badStereotypes.slice(0, 3).join(', ')}`,
    });
  }

  // ── 7. Node background colors ──
  const nodeColors = await page.evaluate(() => {
    const colorMap = {};
    document.querySelectorAll('.svelte-flow__node').forEach(node => {
      const inner = node.querySelector('.uml-node');
      if (!inner) return;
      const bg = getComputedStyle(inner).backgroundColor;
      const label = inner.querySelector('.uml-node__label')?.textContent?.trim() || 'unknown';
      const stereo = inner.querySelector('.uml-node__stereotype')?.textContent?.trim() || '';
      if (bg && bg !== 'rgba(0, 0, 0, 0)') {
        colorMap[label] = { bg, stereo };
      }
    });
    return colorMap;
  });

  // ── 8. Italic inheritance on attributes ──
  const italicAttrs = await page.evaluate(() => {
    const items = [];
    document.querySelectorAll('.uml-node__attr').forEach(el => {
      const style = getComputedStyle(el);
      if (style.fontStyle === 'italic') {
        items.push(el.textContent?.trim().slice(0, 40));
      }
    });
    return items;
  });
  if (italicAttrs.length > 0) {
    issues.push({
      type: 'italic_inheritance', severity: 'medium',
      detail: `${italicAttrs.length} attributes inheriting italic: ${italicAttrs.slice(0, 3).join(', ')}`,
    });
  }

  // ── 9. Note title duplication (legacy check — see also #26 for improved version) ──
  const noteDupes = await page.evaluate(() => {
    const dupes = [];
    document.querySelectorAll('.canvas-node--note').forEach(note => {
      const header = note.querySelector('.canvas-node__header');
      const desc = note.querySelector('.canvas-node__description');
      if (header && desc) {
        const title = header.textContent?.trim();
        const body = desc.textContent?.trim();
        if (title && body && body.startsWith(title)) {
          dupes.push(title.slice(0, 30));
        }
      }
    });
    return dupes;
  });
  if (noteDupes.length > 0) {
    issues.push({
      type: 'note_duplication', severity: 'low',
      detail: `${noteDupes.length} notes with duplicated title in body: ${noteDupes.join(', ')}`,
    });
  }

  // ── 10. Diagram frame ──
  const hasFrame = nodes.some(n => n.type === 'diagram_frame');
  if (hasFrame && !frameDom) {
    issues.push({
      type: 'missing_frame', severity: 'low',
      detail: 'API has diagram_frame node but not rendered in DOM',
    });
  }

  // ── 11. Node overlapping (informational — excludes parent-child containment) ──
  const overlaps = await page.evaluate(() => {
    const rects = [];
    document.querySelectorAll('.svelte-flow__node').forEach(node => {
      const r = node.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) {
        const label = node.querySelector('.uml-node__label, .node-label')?.textContent?.trim() || '';
        // Detect container types (packages, boundaries) by checking for child content area
        const isContainer = node.classList.contains('boundary-node') ||
          node.querySelector('.boundary-node, .package-tab') !== null ||
          node.getAttribute('data-type')?.includes('package') ||
          node.getAttribute('data-type')?.includes('boundary');
        rects.push({ x: r.x, y: r.y, w: r.width, h: r.height, label, isContainer });
      }
    });
    const overlapping = [];
    for (let i = 0; i < rects.length; i++) {
      for (let j = i + 1; j < rects.length; j++) {
        const a = rects[i], b = rects[j];
        // Skip parent-child containment: if one is a container and fully contains the other
        if (a.isContainer || b.isContainer) {
          const outer = a.isContainer ? a : b;
          const inner = a.isContainer ? b : a;
          if (inner.x >= outer.x && inner.y >= outer.y &&
              inner.x + inner.w <= outer.x + outer.w &&
              inner.y + inner.h <= outer.y + outer.h) {
            continue;  // Skip — this is expected containment
          }
        }
        const overlapX = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
        const overlapY = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
        const area = overlapX * overlapY;
        const minArea = Math.min(a.w * a.h, b.w * b.h);
        if (area > minArea * 0.1) {
          overlapping.push(`${a.label} x ${b.label}`);
        }
      }
    }
    return overlapping;
  });
  if (overlaps.length > 0) {
    issues.push({
      type: 'node_overlap', severity: 'info',
      detail: `${overlaps.length} overlapping pairs (excluding parent-child containment): ${overlaps.slice(0, 3).join('; ')}`,
    });
  }

  // ── 12. Edge labels (cardinality, role names) ──
  const edgeLabels = await page.evaluate(() => {
    const labels = [];
    document.querySelectorAll('.svelte-flow__edge .edge-label, .edge-endpoint-label').forEach(el => {
      labels.push(el.textContent?.trim());
    });
    return labels.filter(Boolean);
  });
  const expectedLabels = edges.filter(e =>
    e.data?.sourceLabel || e.data?.targetLabel || e.data?.label
  ).length;
  if (expectedLabels > 0) {
    correct.push(`Edge labels found: ${edgeLabels.length} (${expectedLabels} edges have label data)`);
  }

  // ── 13. Package nodes (improved selector) ──
  // Match actual UML package containers, not ArchiMate work_package elements
  const packageNodes = nodes.filter(n => {
    const et = (n.data?.entityType || '').toLowerCase();
    return et === 'package' || et === 'uml_package' || (et.includes('package') && !et.includes('work_package'));
  });
  if (packageNodes.length > 0) {
    // Count all rendered nodes whose type attribute contains package-related types
    const renderedPackageCount = await page.evaluate((pkgCount) => {
      let found = 0;
      document.querySelectorAll('.svelte-flow__node').forEach(node => {
        const nodeType = node.getAttribute('data-id') || '';
        // Check rendered class names for boundary/package indicators
        if (node.querySelector('.boundary-node, .package-tab') ||
            node.classList.contains('boundary-node') ||
            node.textContent?.includes('Package')) {
          found++;
        }
      });
      return found;
    }, packageNodes.length);
    if (renderedPackageCount < packageNodes.length) {
      issues.push({
        type: 'missing_packages', severity: 'medium',
        detail: `API has ${packageNodes.length} package nodes, DOM has ${renderedPackageCount}`,
      });
    }
  }

  // ── 14. Links and cross-references ──
  const links = await page.evaluate(() => {
    const found = [];
    document.querySelectorAll('a[href], [data-link], [data-href]').forEach(el => {
      found.push({
        href: el.getAttribute('href') || el.getAttribute('data-link') || el.getAttribute('data-href'),
        text: el.textContent?.trim().slice(0, 40),
      });
    });
    return found;
  });
  if (links.length > 0) {
    correct.push(`${links.length} links/cross-references detected`);
  }

  // ── 15. Missing node background colors (data completeness) ──
  // Nodes without explicit bgColor use CSS theme defaults (e.g. #ffffcc for UML classes,
  // ArchiMate layer colors). Only flag as issue when ALL nodes lack color AND the rendered
  // DOM shows no background differentiation.
  const nodesWithoutBgColor = contentNodes.filter(n => {
    const visual = n.data?.visual || {};
    return !visual.bgColor && !visual.backgroundColor;
  });
  if (nodesWithoutBgColor.length === 0 && contentNodes.length > 0) {
    correct.push('All nodes have bgColor');
  } else if (nodesWithoutBgColor.length > 0) {
    // Check if rendered nodes actually show colors (CSS defaults may provide them)
    const renderedColors = await page.evaluate(() => {
      const colors = new Set();
      document.querySelectorAll('.svelte-flow__node').forEach(node => {
        const inner = node.querySelector('[class*="node"]');
        if (!inner) return;
        const bg = getComputedStyle(inner).backgroundColor;
        if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') colors.add(bg);
      });
      return colors.size;
    });
    if (renderedColors >= 1) {
      // CSS theme defaults are providing colors — this is correct behavior
      correct.push(`${nodesWithoutBgColor.length} nodes use CSS theme colors (${renderedColors} distinct colors rendered)`);
    } else {
      // No rendered colors at all — nodes are transparent/white with no theme
      issues.push({
        type: 'missing_bg_color', severity: 'high',
        detail: `All ${nodesWithoutBgColor.length} content nodes lack bgColor and render with no background color`,
      });
    }
  }

  // ── 16. Missing edge waypoints (informational — EA auto-routes most edges) ──
  const edgesWithoutWaypoints = edges.filter(e => {
    const wp = e.data?.waypoints || [];
    return wp.length === 0;
  });
  if (edgesWithoutWaypoints.length > 0 && edges.length > 0) {
    const pct = Math.round((edgesWithoutWaypoints.length / edges.length) * 100);
    // Always informational — EA only stores waypoints for manually-routed edges
    issues.push({
      type: 'missing_waypoints', severity: 'info',
      detail: `${edgesWithoutWaypoints.length}/${edges.length} edges (${pct}%) auto-routed (no EA waypoints — SvelteFlow handles routing)`,
    });
  }

  // ── 17. Missing edge visual styles (data completeness) ──
  const edgesWithoutVisual = edges.filter(e => {
    const visual = e.data?.visual || {};
    return !visual.lineColor && !visual.color;
  });
  if (edgesWithoutVisual.length > 0 && edges.length > 0) {
    const pct = Math.round((edgesWithoutVisual.length / edges.length) * 100);
    if (pct > 80) {
      issues.push({
        type: 'missing_edge_visual', severity: 'medium',
        detail: `${edgesWithoutVisual.length}/${edges.length} edges (${pct}%) lack visual styling (lineColor)`,
      });
    }
  }

  // ── 18. Edge stereotype labels not rendered ──
  const edgesWithStereotype = edges.filter(e =>
    e.data?.stereotype && !e.data?.label
  );
  if (edgesWithStereotype.length > 0) {
    issues.push({
      type: 'edge_stereotype_hidden', severity: 'medium',
      detail: `${edgesWithStereotype.length} edges have stereotype but no label — stereotype text not visible (e.g., "${edgesWithStereotype[0]?.data?.stereotype}")`,
    });
  }

  // ── 19. Nodes outside diagram frame bounds ──
  if (hasFrame) {
    const frameNode = nodes.find(n => n.type === 'diagram_frame');
    if (frameNode) {
      const fw = frameNode.data?.visual?.width || frameNode.width || 0;
      const fh = frameNode.data?.visual?.height || frameNode.height || 0;
      const fx = frameNode.position?.x || 0;
      const fy = frameNode.position?.y || 0;
      if (fw > 0 && fh > 0) {
        const outside = contentNodes.filter(n => {
          const nx = n.position?.x || 0;
          const ny = n.position?.y || 0;
          return nx < fx || ny < fy || nx > fx + fw || ny > fy + fh;
        });
        if (outside.length > 0) {
          issues.push({
            type: 'nodes_outside_frame', severity: 'medium',
            detail: `${outside.length}/${contentNodes.length} nodes positioned outside the diagram frame bounds`,
          });
        }
      }
    }
  }

  // ── 20. Node size fidelity — rendered size vs EA-specified dimensions ──
  // Note: getBoundingClientRect includes SvelteFlow zoom transform, so we
  // extract the zoom level and normalize sizes before comparing.
  const sizeMismatches = await page.evaluate((apiNodes) => {
    // Extract SvelteFlow zoom from the viewport transform
    const viewport = document.querySelector('.svelte-flow__viewport');
    let zoom = 1;
    if (viewport) {
      const transform = getComputedStyle(viewport).transform;
      const match = transform.match(/matrix\(([^,]+)/);
      if (match) zoom = parseFloat(match[1]) || 1;
    }

    const mismatches = [];
    for (const apiNode of apiNodes) {
      const expectedW = apiNode.data?.visual?.width || apiNode.measured?.width;
      const expectedH = apiNode.data?.visual?.height || apiNode.measured?.height;
      if (!expectedW || !expectedH) continue;
      if (apiNode.type === 'diagram_frame') continue;

      // Find rendered node by ID — check all renderer types
      const el = document.querySelector(`[data-id="${apiNode.id}"] .uml-node, [data-id="${apiNode.id}"] .archimate-node, [data-id="${apiNode.id}"] .note-node, [data-id="${apiNode.id}"] .boundary-node`);
      if (!el) continue;
      const rect = el.getBoundingClientRect();
      if (rect.width === 0) continue;

      // Normalize for zoom
      const actualW = rect.width / zoom;
      const actualH = rect.height / zoom;
      const wRatio = actualW / expectedW;
      const hRatio = actualH / expectedH;
      const label = apiNode.data?.label || 'unknown';

      // Flag if rendered at less than 70% or more than 150% of EA size
      if (wRatio < 0.7 || hRatio < 0.7) {
        mismatches.push({
          label, expected: `${expectedW}x${expectedH}`,
          rendered: `${Math.round(actualW)}x${Math.round(actualH)}`,
          ratio: `${(wRatio * 100).toFixed(0)}%w/${(hRatio * 100).toFixed(0)}%h`,
          tooSmall: true,
        });
      } else if (wRatio > 1.5 || hRatio > 1.5) {
        mismatches.push({
          label, expected: `${expectedW}x${expectedH}`,
          rendered: `${Math.round(actualW)}x${Math.round(actualH)}`,
          ratio: `${(wRatio * 100).toFixed(0)}%w/${(hRatio * 100).toFixed(0)}%h`,
          tooSmall: false,
        });
      }
    }
    return mismatches;
  }, contentNodes);

  if (sizeMismatches.length > 0) {
    const tooSmall = sizeMismatches.filter(m => m.tooSmall);
    const tooLarge = sizeMismatches.filter(m => !m.tooSmall);
    if (tooSmall.length > 0) {
      issues.push({
        type: 'node_undersized', severity: 'high',
        detail: `${tooSmall.length}/${contentNodes.length} nodes rendered smaller than EA dimensions: ${tooSmall.slice(0, 3).map(m => `${m.label} (${m.rendered} vs ${m.expected})`).join(', ')}`,
      });
    }
    if (tooLarge.length > 0) {
      issues.push({
        type: 'node_oversized', severity: 'medium',
        detail: `${tooLarge.length} nodes rendered larger than EA dimensions: ${tooLarge.slice(0, 3).map(m => `${m.label} (${m.rendered} vs ${m.expected})`).join(', ')}`,
      });
    }
  } else if (contentNodes.length > 0) {
    correct.push('Node sizes match EA dimensions');
  }

  // ── 21. Minimum readable size — nodes too small to read ──
  const tinyNodes = await page.evaluate(() => {
    // Account for SvelteFlow zoom
    const viewport = document.querySelector('.svelte-flow__viewport');
    let zoom = 1;
    if (viewport) {
      const transform = getComputedStyle(viewport).transform;
      const match = transform.match(/matrix\(([^,]+)/);
      if (match) zoom = parseFloat(match[1]) || 1;
    }
    const tiny = [];
    document.querySelectorAll('.svelte-flow__node').forEach(node => {
      const rect = node.getBoundingClientRect();
      const actualW = rect.width / zoom;
      if (actualW > 0 && actualW < 60) {
        const label = node.querySelector('.uml-node__label, .archimate-node__label, .node-label')?.textContent?.trim() || '';
        tiny.push({ label, w: Math.round(actualW), h: Math.round(rect.height / zoom) });
      }
    });
    return tiny;
  });
  if (tinyNodes.length > 0) {
    issues.push({
      type: 'unreadable_nodes', severity: 'high',
      detail: `${tinyNodes.length} nodes too small to read (<60px wide): ${tinyNodes.slice(0, 5).map(t => `${t.label}(${t.w}x${t.h})`).join(', ')}`,
    });
  }

  // ── 22. Color rendering fidelity — do rendered colors match API bgColor? ──
  // ArchiMate nodes with bgColor=#ffffff use CSS layer colors instead — this is
  // correct behaviour, not a mismatch. We define ArchiMate types to skip.
  const ARCHIMATE_TYPE_PREFIXES = ['business_', 'application_', 'technology_'];
  const ARCHIMATE_EXTRA_TYPES = new Set([
    'stakeholder', 'driver', 'assessment', 'goal', 'outcome', 'principle',
    'requirement_archimate', 'constraint_archimate', 'resource', 'capability',
    'course_of_action', 'value_stream', 'work_package', 'deliverable',
    'implementation_event', 'plateau', 'gap',
  ]);
  const isArchimateType = (t) => ARCHIMATE_TYPE_PREFIXES.some(p => t?.startsWith(p)) || ARCHIMATE_EXTRA_TYPES.has(t);

  const colorFidelity = await page.evaluate(({ apiNodes, archPrefixes, archExtra }) => {
    const isArchimate = (t) => archPrefixes.some(p => t?.startsWith(p)) || archExtra.includes(t);
    const results = { matched: 0, mismatched: [], noColor: 0, total: 0, archimateOverride: 0 };
    for (const apiNode of apiNodes) {
      if (apiNode.type === 'diagram_frame') continue;
      const expectedBg = apiNode.data?.visual?.bgColor;
      if (!expectedBg) { results.noColor++; continue; }

      const el = document.querySelector(`[data-id="${apiNode.id}"] .uml-node, [data-id="${apiNode.id}"] .archimate-node`);
      if (!el) continue;
      results.total++;

      // ArchiMate nodes with EA default #ffffff get layer colors — skip comparison
      if (isArchimate(apiNode.type) && expectedBg.toLowerCase() === '#ffffff') {
        results.archimateOverride++;
        results.matched++;
        continue;
      }

      const computed = getComputedStyle(el).backgroundColor;
      // Convert computed rgb(r,g,b) to hex for comparison
      const match = computed.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
      if (match) {
        const hex = '#' + [match[1], match[2], match[3]].map(c => parseInt(c).toString(16).padStart(2, '0')).join('');
        if (hex.toLowerCase() === expectedBg.toLowerCase()) {
          results.matched++;
        } else {
          results.mismatched.push({
            label: apiNode.data?.label || 'unknown',
            expected: expectedBg,
            rendered: hex,
          });
        }
      }
    }
    return results;
  }, { apiNodes: contentNodes, archPrefixes: ARCHIMATE_TYPE_PREFIXES, archExtra: [...ARCHIMATE_EXTRA_TYPES] });

  if (colorFidelity.mismatched.length > 0) {
    issues.push({
      type: 'color_mismatch', severity: 'high',
      detail: `${colorFidelity.mismatched.length}/${colorFidelity.total} nodes render wrong background color: ${colorFidelity.mismatched.slice(0, 3).map(m => `${m.label} (expected ${m.expected}, got ${m.rendered})`).join(', ')}`,
    });
  } else if (colorFidelity.total > 0) {
    correct.push(`Colors: ${colorFidelity.matched}/${colorFidelity.total} nodes match API bgColor`);
  }

  // Collect unique rendered colors for reporting
  const renderedColors = await page.evaluate(() => {
    const colors = new Set();
    document.querySelectorAll('.uml-node, .archimate-node').forEach(el => {
      const bg = getComputedStyle(el).backgroundColor;
      const match = bg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
      if (match) {
        const hex = '#' + [match[1], match[2], match[3]].map(c => parseInt(c).toString(16).padStart(2, '0')).join('');
        if (hex !== '#ffffff' && hex !== '#000000') colors.add(hex);
      }
    });
    return [...colors];
  });

  // ── 23. Label truncation severity — what percentage of labels are fully visible? ──
  // Distinguish fixed-size nodes (ArchiMate/UML with EA dimensions — truncation is faithful
  // to EA) from auto-sized nodes where truncation is a real rendering issue.
  const labelStats = await page.evaluate(() => {
    let total = 0, truncated = 0, fullyVisible = 0, fixedSizeTruncated = 0;
    document.querySelectorAll('.uml-node__label, .archimate-node__label').forEach(el => {
      total++;
      if (el.scrollWidth > el.clientWidth + 2) {
        truncated++;
        // Check if parent node has fixed width (inline style with explicit width)
        const nodeEl = el.closest('.uml-node, .archimate-node');
        if (nodeEl && nodeEl.style.width) fixedSizeTruncated++;
      } else {
        fullyVisible++;
      }
    });
    const autoSizeTruncated = truncated - fixedSizeTruncated;
    return { total, truncated, fullyVisible, fixedSizeTruncated, autoSizeTruncated,
      pct: total > 0 ? Math.round((autoSizeTruncated / total) * 100) : 0 };
  });
  // Only flag non-fixed-size truncation as an issue (fixed-size matches EA)
  if (labelStats.autoSizeTruncated > 0 && labelStats.pct > 50) {
    issues.push({
      type: 'majority_labels_truncated', severity: 'high',
      detail: `${labelStats.autoSizeTruncated}/${labelStats.total} auto-sized labels (${labelStats.pct}%) are truncated`,
    });
  } else if (labelStats.autoSizeTruncated > 0 && labelStats.pct > 20) {
    issues.push({
      type: 'many_labels_truncated', severity: 'medium',
      detail: `${labelStats.autoSizeTruncated}/${labelStats.total} auto-sized labels (${labelStats.pct}%) are truncated`,
    });
  } else if (labelStats.total > 0) {
    const note = labelStats.fixedSizeTruncated > 0
      ? ` (${labelStats.fixedSizeTruncated} fixed-size nodes truncated as in EA)` : '';
    correct.push(`Labels: ${labelStats.fullyVisible}/${labelStats.total} fully visible${note}`);
  }

  // ── 24. Layout spread — is the diagram using the available space? ──
  const layoutSpread = await page.evaluate(() => {
    const viewport = document.querySelector('.svelte-flow');
    if (!viewport) return null;
    const vpRect = viewport.getBoundingClientRect();

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    let nodeCount = 0;
    document.querySelectorAll('.svelte-flow__node').forEach(node => {
      const r = node.getBoundingClientRect();
      if (r.width === 0) return;
      nodeCount++;
      minX = Math.min(minX, r.x);
      minY = Math.min(minY, r.y);
      maxX = Math.max(maxX, r.x + r.width);
      maxY = Math.max(maxY, r.y + r.height);
    });

    if (nodeCount < 2) return null;
    const contentW = maxX - minX;
    const contentH = maxY - minY;
    const vpW = vpRect.width;
    const vpH = vpRect.height;

    return {
      contentBounds: { w: Math.round(contentW), h: Math.round(contentH) },
      viewportSize: { w: Math.round(vpW), h: Math.round(vpH) },
      fillRatioW: parseFloat((contentW / vpW * 100).toFixed(1)),
      fillRatioH: parseFloat((contentH / vpH * 100).toFixed(1)),
      aspectRatio: parseFloat((contentW / contentH).toFixed(2)),
    };
  });

  if (layoutSpread) {
    // If content fills less than 30% of viewport in either dimension, it's compressed
    if (layoutSpread.fillRatioW < 30 && layoutSpread.fillRatioH < 30) {
      issues.push({
        type: 'layout_compressed', severity: 'medium',
        detail: `Diagram uses only ${layoutSpread.fillRatioW}%w x ${layoutSpread.fillRatioH}%h of viewport (${layoutSpread.contentBounds.w}x${layoutSpread.contentBounds.h} in ${layoutSpread.viewportSize.w}x${layoutSpread.viewportSize.h})`,
      });
    }
  }

  // ── 25. Edge routing quality — edges crossing through nodes ──
  const edgeCrossings = await page.evaluate(() => {
    const viewport = document.querySelector('.svelte-flow__viewport');
    let zoom = 1;
    if (viewport) {
      const transform = getComputedStyle(viewport).transform;
      const match = transform.match(/matrix\(([^,]+)/);
      if (match) zoom = parseFloat(match[1]) || 1;
    }

    // Collect node bounding rects (unzoomed), excluding frames and boundaries
    const nodeRects = [];
    document.querySelectorAll('.svelte-flow__node').forEach(node => {
      const r = node.getBoundingClientRect();
      if (r.width === 0) return;
      const id = node.getAttribute('data-id') || '';
      // Skip diagram frames and boundary/container nodes — edges pass through these naturally
      if (node.querySelector('.diagram-frame-node, .canvas-node--boundary')) return;
      const dataType = node.getAttribute('data-type') || '';
      if (dataType === 'diagram_frame' || dataType === 'boundary') return;
      // Also skip very large nodes (>500px in both dims) as they're likely containers
      const w = r.width / zoom, h = r.height / zoom;
      if (w > 500 && h > 500) return;
      const label = node.querySelector('.canvas-node__label, [class*="label"]')?.textContent?.trim() || '';
      nodeRects.push({ id, x: r.x / zoom, y: r.y / zoom, w, h, label: label.slice(0, 30) });
    });

    // Check each edge path for segments crossing through non-source/target nodes
    let crossings = 0;
    const crossingDetails = [];
    document.querySelectorAll('.svelte-flow__edge').forEach(edge => {
      const path = edge.querySelector('path');
      if (!path) return;
      const edgeId = edge.getAttribute('data-id') || '';

      // Get source/target node IDs from the edge element
      const sourceId = edge.getAttribute('data-source') || '';
      const targetId = edge.getAttribute('data-target') || '';

      // Find edge label for reporting
      const edgeLabelEl = edge.querySelector('.edge-label, foreignObject');
      const edgeLabel = edgeLabelEl?.textContent?.trim()?.slice(0, 30) || edgeId.slice(0, 8);

      // Sample points along the path
      const pathEl = path;
      const totalLen = pathEl.getTotalLength();
      if (totalLen === 0) return;

      const step = Math.max(5, totalLen / 40); // Sample ~40 points
      for (let d = step; d < totalLen - step; d += step) {
        const pt = pathEl.getPointAtLength(d);
        // Transform point to unzoomed coordinates
        const px = pt.x / zoom;
        const py = pt.y / zoom;

        for (const rect of nodeRects) {
          // Skip source and target nodes
          if (rect.id === sourceId || rect.id === targetId) continue;
          // Check if point is inside node rect (with small margin)
          const margin = 3;
          if (px > rect.x + margin && px < rect.x + rect.w - margin &&
              py > rect.y + margin && py < rect.y + rect.h - margin) {
            crossings++;
            crossingDetails.push(`edge "${edgeLabel}" crosses "${rect.label}" (${rect.id.slice(0,8)})`);
            return; // Count each edge only once
          }
        }
      }
    });

    return { crossings, details: crossingDetails.slice(0, 5) };
  });

  if (edgeCrossings.crossings > 0) {
    const detailStr = edgeCrossings.details.length > 0
      ? `: ${edgeCrossings.details.join('; ')}`
      : '';
    issues.push({
      type: 'edge_node_crossing', severity: 'medium',
      detail: `${edgeCrossings.crossings} edges cross through non-endpoint nodes (broken routing)${detailStr}`,
    });
  } else if (edges.length > 0) {
    correct.push('No edges crossing through nodes');
  }

  // ── 26. Note title duplication — label text repeated in description ──
  const noteDuplication = await page.evaluate(() => {
    const dupes = [];
    document.querySelectorAll('.canvas-node--note').forEach(note => {
      const header = note.querySelector('.canvas-node__header');
      const desc = note.querySelector('.canvas-node__description');
      if (header && desc) {
        const headerText = header.textContent?.trim() || '';
        const descText = desc.textContent?.trim() || '';
        // Check if description starts with or equals header text
        if (headerText && descText && descText.startsWith(headerText)) {
          dupes.push(headerText.slice(0, 30));
        }
      }
    });
    return dupes;
  });
  if (noteDuplication.length > 0) {
    issues.push({
      type: 'note_title_duplication', severity: 'medium',
      detail: `${noteDuplication.length} notes show duplicate title text in body: ${noteDuplication.join(', ')}`,
    });
  }

  // ── 27. Numbered list preservation — check notes render <ol> items correctly ──
  const noteListCheck = (() => {
    const notesWithLists = contentNodes.filter(n => {
      return n.data?.entityType === 'note' && n.data?.description?.includes('<ol>');
    });
    return { expected: notesWithLists.length, noteLabels: notesWithLists.map(n => n.data?.label?.slice(0, 30)) };
  })();
  if (noteListCheck.expected > 0) {
    const renderedLists = await page.evaluate(() => {
      let count = 0;
      document.querySelectorAll('.canvas-node--note .canvas-node__description ol').forEach(() => count++);
      return count;
    });
    if (renderedLists < noteListCheck.expected) {
      issues.push({
        type: 'missing_numbered_lists', severity: 'medium',
        detail: `${noteListCheck.expected} notes have numbered lists in API but only ${renderedLists} render <ol> elements`,
      });
    } else {
      correct.push(`Numbered lists: ${renderedLists}/${noteListCheck.expected} notes render <ol> correctly`);
    }
  }

  // ── 28. Boundary size accuracy — compare rendered vs EA dimensions ──
  const boundaryNodes = contentNodes.filter(n => n.data?.entityType === 'boundary');
  if (boundaryNodes.length > 0) {
    const boundarySizes = await page.evaluate(({ boundaries, zoomHint }) => {
      const viewport = document.querySelector('.svelte-flow__viewport');
      let zoom = 1;
      if (viewport) {
        const transform = getComputedStyle(viewport).transform;
        const match = transform.match(/matrix\(([^,]+)/);
        if (match) zoom = parseFloat(match[1]) || 1;
      }
      const mismatches = [];
      for (const b of boundaries) {
        const expectedW = b.data?.visual?.width;
        const expectedH = b.data?.visual?.height;
        if (!expectedW || !expectedH) continue;
        const el = document.querySelector(`[data-id="${b.id}"] .canvas-node--boundary`);
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        const actualW = rect.width / zoom;
        const actualH = rect.height / zoom;
        const wRatio = actualW / expectedW;
        const hRatio = actualH / expectedH;
        if (wRatio < 0.8 || wRatio > 1.2 || hRatio < 0.8 || hRatio > 1.2) {
          mismatches.push({
            label: b.data?.label || 'unknown',
            expected: `${expectedW}x${expectedH}`,
            actual: `${Math.round(actualW)}x${Math.round(actualH)}`,
          });
        }
      }
      return mismatches;
    }, { boundaries: boundaryNodes });
    if (boundarySizes.length > 0) {
      issues.push({
        type: 'boundary_size_mismatch', severity: 'medium',
        detail: `${boundarySizes.length} boundaries with wrong size: ${boundarySizes.map(m => `${m.label} (${m.actual} vs ${m.expected})`).join(', ')}`,
      });
    } else {
      correct.push(`Boundary sizes: ${boundaryNodes.length} match EA dimensions`);
    }
  }

  // ── 29. Note overlap — notes overlapping each other or mispositioned ──
  const noteOverlaps = await page.evaluate(() => {
    const viewport = document.querySelector('.svelte-flow__viewport');
    let zoom = 1;
    if (viewport) {
      const transform = getComputedStyle(viewport).transform;
      const match = transform.match(/matrix\(([^,]+)/);
      if (match) zoom = parseFloat(match[1]) || 1;
    }
    const noteRects = [];
    document.querySelectorAll('.svelte-flow__node').forEach(node => {
      const noteEl = node.querySelector('.canvas-node--note');
      if (!noteEl) return;
      const r = node.getBoundingClientRect();
      const label = noteEl.querySelector('.canvas-node__label, .canvas-node__description')?.textContent?.trim().slice(0, 20) || '';
      noteRects.push({ x: r.x / zoom, y: r.y / zoom, w: r.width / zoom, h: r.height / zoom, label });
    });
    const overlaps = [];
    for (let i = 0; i < noteRects.length; i++) {
      for (let j = i + 1; j < noteRects.length; j++) {
        const a = noteRects[i], b = noteRects[j];
        const overlapX = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
        const overlapY = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
        const area = overlapX * overlapY;
        const minArea = Math.min(a.w * a.h, b.w * b.h);
        if (area > minArea * 0.15) {
          overlaps.push(`${a.label} x ${b.label}`);
        }
      }
    }
    return overlaps;
  });
  if (noteOverlaps.length > 0) {
    issues.push({
      type: 'note_overlap', severity: 'medium',
      detail: `${noteOverlaps.length} note-note overlapping pairs: ${noteOverlaps.slice(0, 3).join('; ')}`,
    });
  }

  // ── 30. ArchiMate icon correctness — check for proper notation icons ──
  const archimateNodes = contentNodes.filter(n => {
    const t = n.data?.entityType || '';
    return t.startsWith('business_') || t.startsWith('application_') || t.startsWith('technology_') ||
      ['stakeholder', 'capability', 'work_package', 'resource', 'course_of_action', 'value_stream',
       'deliverable', 'implementation_event', 'plateau', 'gap'].includes(t);
  });
  if (archimateNodes.length > 0) {
    const iconCheck = await page.evaluate((nodeIds) => {
      let withIcon = 0, withoutIcon = 0, wrongPosition = 0;
      for (const nodeId of nodeIds) {
        const el = document.querySelector(`[data-id="${nodeId}"]`);
        if (!el) continue;
        const iconEl = el.querySelector('.archimate-node__icon svg');
        if (iconEl) {
          withIcon++;
          // Check icon is in top-right (position: absolute, right, top)
          const style = getComputedStyle(iconEl.parentElement);
          if (style.position !== 'absolute') wrongPosition++;
        } else {
          withoutIcon++;
        }
      }
      return { withIcon, withoutIcon, wrongPosition };
    }, archimateNodes.map(n => n.id));
    if (iconCheck.withoutIcon > 0) {
      issues.push({
        type: 'missing_archimate_icons', severity: 'medium',
        detail: `${iconCheck.withoutIcon}/${archimateNodes.length} ArchiMate nodes missing notation icon`,
      });
    } else {
      correct.push(`ArchiMate icons: ${iconCheck.withIcon}/${archimateNodes.length} nodes have correct icons`);
    }
    if (iconCheck.wrongPosition > 0) {
      issues.push({
        type: 'archimate_icon_position', severity: 'low',
        detail: `${iconCheck.wrongPosition} ArchiMate icons not positioned in top-right corner`,
      });
    }
  }

  // ── 31. Boundary covering non-child content ──
  if (boundaryNodes.length > 0) {
    const boundaryCoveringIssues = await page.evaluate((boundaryInfos) => {
      const viewport = document.querySelector('.svelte-flow__viewport');
      let zoom = 1;
      if (viewport) {
        const transform = getComputedStyle(viewport).transform;
        const match = transform.match(/matrix\(([^,]+)/);
        if (match) zoom = parseFloat(match[1]) || 1;
      }
      const problems = [];
      for (const bInfo of boundaryInfos) {
        const bId = bInfo.id;
        // Skip boundaries with negative zIndex — they render behind content
        if (typeof bInfo.zIndex === 'number' && bInfo.zIndex < 0) continue;
        const bNode = document.querySelector(`[data-id="${bId}"]`);
        if (!bNode) continue;
        const bRect = bNode.getBoundingClientRect();
        const bLabel = bNode.querySelector('.canvas-node__label, .canvas-node__header')?.textContent?.trim().slice(0, 30) || bId;
        // Get all content nodes that are NOT children of this boundary
        const allNodes = document.querySelectorAll('.svelte-flow__node');
        let coveredCount = 0;
        const coveredLabels = [];
        for (const node of allNodes) {
          if (node === bNode) continue;
          const nodeId = node.getAttribute('data-id');
          // Skip if this node is a child (parentId matches boundary)
          if (node.closest(`[data-id="${bId}"]`)) continue;
          // Skip other boundaries and diagram frames
          if (node.querySelector('.canvas-node--boundary, .diagram-frame-node')) continue;
          const nRect = node.getBoundingClientRect();
          // Check overlap
          const overlapX = Math.max(0, Math.min(bRect.right, nRect.right) - Math.max(bRect.left, nRect.left));
          const overlapY = Math.max(0, Math.min(bRect.bottom, nRect.bottom) - Math.max(bRect.top, nRect.top));
          const overlapArea = overlapX * overlapY;
          const nodeArea = nRect.width * nRect.height;
          if (nodeArea > 0 && overlapArea > nodeArea * 0.3) {
            coveredCount++;
            const label = node.querySelector('.uml-node__label, .canvas-node__label, .node-label')?.textContent?.trim().slice(0, 20) || nodeId;
            coveredLabels.push(label);
          }
        }
        if (coveredCount > 0) {
          problems.push({ boundary: bLabel, covered: coveredCount, labels: coveredLabels.slice(0, 3) });
        }
      }
      return problems;
    }, boundaryNodes.map(n => ({ id: n.id, zIndex: n.zIndex })));
    if (boundaryCoveringIssues.length > 0) {
      issues.push({
        type: 'boundary_covering_content', severity: 'high',
        detail: `${boundaryCoveringIssues.length} boundaries cover non-child nodes: ${boundaryCoveringIssues.map(b => `${b.boundary} covers ${b.covered} nodes (${b.labels.join(', ')})`).join('; ')}`,
      });
    } else {
      correct.push(`Boundary z-order: no boundaries covering non-child content`);
    }
  }

  // ── 32. ArchiMate text alignment ──
  const archimateTextAlignment = await page.evaluate(() => {
    const labels = document.querySelectorAll('.archimate-node__label');
    if (labels.length === 0) return null;
    let misaligned = 0;
    const examples = [];
    for (const label of labels) {
      const align = getComputedStyle(label).textAlign;
      if (align !== 'center') {
        misaligned++;
        if (examples.length < 3) {
          examples.push({ text: label.textContent?.trim().slice(0, 20) || '?', align });
        }
      }
    }
    return { total: labels.length, misaligned, examples };
  });
  if (archimateTextAlignment) {
    if (archimateTextAlignment.misaligned > 0) {
      issues.push({
        type: 'archimate_text_alignment', severity: 'medium',
        detail: `${archimateTextAlignment.misaligned}/${archimateTextAlignment.total} ArchiMate labels not center-aligned: ${archimateTextAlignment.examples.map(e => `"${e.text}" is ${e.align}`).join(', ')}`,
      });
    } else {
      correct.push(`ArchiMate text alignment: all ${archimateTextAlignment.total} labels center-aligned`);
    }
  }

  // ── 33. Diagram frame visible ──
  const diagramFrameVisible = await page.evaluate(() => {
    const frame = document.querySelector('.diagram-frame-node, [data-type="diagram_frame"]');
    if (!frame) return null;
    const style = getComputedStyle(frame);
    const opacity = parseFloat(style.opacity);
    const borderWidth = parseFloat(style.borderWidth) || 0;
    const borderStyle = style.borderStyle;
    const display = style.display;
    const visibility = style.visibility;
    const isVisible = display !== 'none' && visibility !== 'hidden' && opacity > 0;
    const hasBorder = borderWidth > 0 && borderStyle !== 'none';
    return { isVisible, hasBorder, opacity, borderWidth, borderStyle, display, visibility };
  });
  if (diagramFrameVisible) {
    if (diagramFrameVisible.isVisible && diagramFrameVisible.hasBorder) {
      issues.push({
        type: 'diagram_frame_visible', severity: 'medium',
        detail: `Diagram frame is visibly rendered (opacity=${diagramFrameVisible.opacity}, border=${diagramFrameVisible.borderWidth}px ${diagramFrameVisible.borderStyle}) — EA ground truth does not show the surrounding frame box`,
      });
    } else {
      correct.push('Diagram frame: correctly hidden or borderless');
    }
  }

  // ── 34. Note unexpected bold heading ──
  const noteBoldCheck = await page.evaluate(() => {
    const headers = document.querySelectorAll('.canvas-node--note .canvas-node__header');
    if (headers.length === 0) return null;
    let boldCount = 0;
    const examples = [];
    for (const h of headers) {
      const weight = parseInt(getComputedStyle(h).fontWeight) || 400;
      if (weight >= 600) {
        boldCount++;
        if (examples.length < 3) {
          examples.push({ text: h.textContent?.trim().slice(0, 25) || '?', weight });
        }
      }
    }
    return { total: headers.length, boldCount, examples };
  });
  if (noteBoldCheck) {
    if (noteBoldCheck.boldCount > 0) {
      issues.push({
        type: 'note_unexpected_bold', severity: 'low',
        detail: `${noteBoldCheck.boldCount}/${noteBoldCheck.total} note headers are bold (weight >= 600) — EA ground truth uses plain text: ${noteBoldCheck.examples.map(e => `"${e.text}" w=${e.weight}`).join(', ')}`,
      });
    } else {
      correct.push(`Note headers: ${noteBoldCheck.total} headers use plain (non-bold) text`);
    }
  }

  // ── 35. Edge attachment granularity ──
  const attachmentCheck = await page.evaluate((edgeData) => {
    const nodeRects = {};
    document.querySelectorAll('.svelte-flow__node').forEach(node => {
      const id = node.getAttribute('data-id');
      if (!id) return;
      const r = node.getBoundingClientRect();
      nodeRects[id] = { x: r.x, y: r.y, w: r.width, h: r.height, cx: r.x + r.width / 2, cy: r.y + r.height / 2 };
    });
    let totalEndpoints = 0;
    let cardinalEndpoints = 0;
    const tolerance = 3; // pixels
    for (const edge of edgeData) {
      const sourceRect = nodeRects[edge.source];
      const targetRect = nodeRects[edge.target];
      if (!sourceRect || !targetRect) continue;
      const edgeEl = document.querySelector(`[data-id="${edge.id}"] path, .svelte-flow__edge[data-id="${edge.id}"] path`);
      if (!edgeEl) continue;
      const d = edgeEl.getAttribute('d');
      if (!d) continue;
      // Extract first point (M command) and last point
      const coords = d.match(/[\d.-]+/g);
      if (!coords || coords.length < 4) continue;
      const startX = parseFloat(coords[0]);
      const startY = parseFloat(coords[1]);
      const endX = parseFloat(coords[coords.length - 2]);
      const endY = parseFloat(coords[coords.length - 1]);
      // Check if start point is at cardinal center of source node
      const sCx = sourceRect.cx;
      const sTop = sourceRect.y, sBottom = sourceRect.y + sourceRect.h;
      const sLeft = sourceRect.x, sRight = sourceRect.x + sourceRect.w;
      const sCy = sourceRect.cy;
      const isCardinalStart = (
        (Math.abs(startX - sCx) < tolerance && (Math.abs(startY - sTop) < tolerance || Math.abs(startY - sBottom) < tolerance)) ||
        (Math.abs(startY - sCy) < tolerance && (Math.abs(startX - sLeft) < tolerance || Math.abs(startX - sRight) < tolerance))
      );
      // Check if end point is at cardinal center of target node
      const tCx = targetRect.cx;
      const tTop = targetRect.y, tBottom = targetRect.y + targetRect.h;
      const tLeft = targetRect.x, tRight = targetRect.x + targetRect.w;
      const tCy = targetRect.cy;
      const isCardinalEnd = (
        (Math.abs(endX - tCx) < tolerance && (Math.abs(endY - tTop) < tolerance || Math.abs(endY - tBottom) < tolerance)) ||
        (Math.abs(endY - tCy) < tolerance && (Math.abs(endX - tLeft) < tolerance || Math.abs(endX - tRight) < tolerance))
      );
      totalEndpoints += 2;
      if (isCardinalStart) cardinalEndpoints++;
      if (isCardinalEnd) cardinalEndpoints++;
    }
    return { totalEndpoints, cardinalEndpoints };
  }, edges);
  if (attachmentCheck.totalEndpoints > 0) {
    const cardinalPct = (attachmentCheck.cardinalEndpoints / attachmentCheck.totalEndpoints * 100).toFixed(1);
    if (parseFloat(cardinalPct) > 80) {
      issues.push({
        type: 'edge_cardinal_only', severity: 'medium',
        detail: `${cardinalPct}% of edge endpoints (${attachmentCheck.cardinalEndpoints}/${attachmentCheck.totalEndpoints}) attach at exact cardinal centers — EA supports granular attachment along any node edge`,
      });
    } else {
      correct.push(`Edge attachment: ${cardinalPct}% cardinal (granular attachment working)`);
    }
  }

  // ── 36. Self-loop 90-degree routing ──
  const selfLoopEdges = edges.filter(e => e.source === e.target);
  if (selfLoopEdges.length > 0) {
    const selfLoopCheck = await page.evaluate((selfLoopIds) => {
      let curved = 0;
      let rectangular = 0;
      const examples = [];
      for (const edgeId of selfLoopIds) {
        const pathEl = document.querySelector(`[data-id="${edgeId}"] path, .svelte-flow__edge[data-id="${edgeId}"] path`);
        if (!pathEl) continue;
        const d = pathEl.getAttribute('d') || '';
        const hasCurve = /[CQcq]/.test(d);
        const hasLine = /[Ll]/.test(d);
        if (hasCurve && !hasLine) {
          curved++;
          if (examples.length < 2) examples.push({ id: edgeId, type: 'curved' });
        } else {
          rectangular++;
          if (examples.length < 2) examples.push({ id: edgeId, type: 'rectangular' });
        }
      }
      return { total: selfLoopIds.length, curved, rectangular, examples };
    }, selfLoopEdges.map(e => e.id));
    if (selfLoopCheck.curved > 0) {
      issues.push({
        type: 'self_loop_not_rectangular', severity: 'low',
        detail: `${selfLoopCheck.curved}/${selfLoopCheck.total} self-loop edges use curved routing — EA renders self-loops with 90-degree rectangular corners`,
      });
    } else if (selfLoopCheck.rectangular > 0) {
      correct.push(`Self-loops: ${selfLoopCheck.rectangular} edges use rectangular routing`);
    }
  }

  // ── 37. Edge label position accuracy ──
  const edgesWithLabels = edges.filter(e => e.data?.label || e.data?.labelPositions || e.label);
  if (edgesWithLabels.length > 0) {
    const labelPositionCheck = await page.evaluate((labelEdges) => {
      let withPositionData = 0;
      let atMidpoint = 0;
      let total = 0;
      for (const edge of labelEdges) {
        const hasPositionData = edge.data?.labelPositions || edge.data?.labelX != null || edge.data?.labelY != null;
        if (!hasPositionData) continue;
        withPositionData++;
        // Check if the label element is rendered at path midpoint
        const edgeEl = document.querySelector(`[data-id="${edge.id}"]`);
        if (!edgeEl) continue;
        const labelEl = edgeEl.querySelector('.edge-label, .svelte-flow__edge-text, [class*="label"]');
        const pathEl = edgeEl.querySelector('path');
        if (!labelEl || !pathEl) continue;
        total++;
        // Get label position and path midpoint
        const labelRect = labelEl.getBoundingClientRect();
        const labelCx = labelRect.x + labelRect.width / 2;
        const labelCy = labelRect.y + labelRect.height / 2;
        // Get path midpoint
        try {
          const pathLen = pathEl.getTotalLength();
          const midPt = pathEl.getPointAtLength(pathLen / 2);
          // Transform to screen coords
          const svg = pathEl.ownerSVGElement;
          const ctm = svg?.getScreenCTM();
          if (ctm) {
            const screenMidX = midPt.x * ctm.a + ctm.e;
            const screenMidY = midPt.y * ctm.d + ctm.f;
            const dist = Math.sqrt((labelCx - screenMidX) ** 2 + (labelCy - screenMidY) ** 2);
            if (dist < 10) atMidpoint++;
          }
        } catch (e) { /* path methods may fail */ }
      }
      return { withPositionData, total, atMidpoint };
    }, edgesWithLabels);
    if (labelPositionCheck.withPositionData > 0 && labelPositionCheck.atMidpoint > 0) {
      const ignoredPct = (labelPositionCheck.atMidpoint / labelPositionCheck.total * 100).toFixed(0);
      issues.push({
        type: 'edge_label_position_ignored', severity: 'medium',
        detail: `${labelPositionCheck.atMidpoint}/${labelPositionCheck.total} edge labels with EA position data render at path midpoint instead — ${ignoredPct}% of positioned labels ignore EA coordinates`,
      });
    } else if (labelPositionCheck.withPositionData > 0) {
      correct.push(`Edge labels: ${labelPositionCheck.withPositionData} labels with EA position data rendered at specified positions`);
    }
  }

  // ── 38. Navigation cell rendering — check Prolaborate NavigationCell tiles ──
  const navCellNodes = contentNodes.filter(n => n.data?.entityType === 'navigation_cell');
  if (navCellNodes.length > 0) {
    const navCheck = await page.evaluate((nodeIds) => {
      let rendered = 0, missingLink = 0, wrongRenderer = 0;
      const examples = [];
      for (const nodeId of nodeIds) {
        const el = document.querySelector(`[data-id="${nodeId}"]`);
        if (!el) continue;
        rendered++;
        // Check it's using NavigationCellNode (has .nav-cell class), not BaseNode or UmlRenderer
        const hasNavClass = !!el.querySelector('.nav-cell');
        if (!hasNavClass) {
          wrongRenderer++;
          if (examples.length < 3) {
            const label = el.querySelector('.canvas-node__label, .nav-cell__title')?.textContent?.trim().slice(0, 30) || nodeId;
            examples.push(label);
          }
        }
        // Check for link badge (navigation cells should link to diagrams)
        const linkBadge = el.querySelector('.nav-cell__link-badge');
        if (!linkBadge) missingLink++;
      }
      return { rendered, wrongRenderer, missingLink, examples, total: nodeIds.length };
    }, navCellNodes.map(n => n.id));
    if (navCheck.wrongRenderer > 0) {
      issues.push({
        type: 'navigation_cell_wrong_renderer', severity: 'high',
        detail: `${navCheck.wrongRenderer}/${navCheck.total} navigation cells using wrong renderer (should be card/tile, not UML class): ${navCheck.examples.join(', ')}`,
      });
    } else {
      correct.push(`Navigation cells: ${navCheck.rendered}/${navCheck.total} rendered as card tiles`);
    }
    if (navCheck.missingLink > 0) {
      issues.push({
        type: 'navigation_cell_missing_link', severity: 'medium',
        detail: `${navCheck.missingLink}/${navCheck.total} navigation cells have no diagram link — they should navigate to another diagram when clicked`,
      });
    }
  }

  // ── 38b. Navigation cell icons — check NID-based Prolaborate icons are present ──
  if (navCellNodes.length > 0) {
    const navIconCheck = await page.evaluate((nodeIds) => {
      let withIcon = 0, withoutIcon = 0;
      const missing = [];
      for (const nodeId of nodeIds) {
        const el = document.querySelector(`[data-id="${nodeId}"]`);
        if (!el) continue;
        // Check for NID-mapped icon SVG (not the fallback generic diagram icon)
        const nidIcon = el.querySelector('.nav-cell__nid-icon');
        const isFallback = nidIcon && nidIcon.style && nidIcon.style.opacity === '0.4';
        if (nidIcon && !isFallback) {
          withIcon++;
        } else {
          withoutIcon++;
          const label = el.querySelector('.nav-cell__title')?.textContent?.trim().slice(0, 30) || nodeId;
          if (missing.length < 3) missing.push(label);
        }
      }
      return { withIcon, withoutIcon, missing, total: nodeIds.length };
    }, navCellNodes.map(n => n.id));
    if (navIconCheck.withoutIcon > 0) {
      issues.push({
        type: 'navigation_cell_missing_icon', severity: 'medium',
        detail: `${navIconCheck.withoutIcon}/${navIconCheck.total} navigation cells missing Prolaborate icon (NID not mapped): ${navIconCheck.missing.join(', ')}`,
      });
    } else if (navIconCheck.withIcon > 0) {
      correct.push(`Navigation cell icons: ${navIconCheck.withIcon}/${navIconCheck.total} have Prolaborate NID-mapped icons`);
    }
  }

  // ── 39. ArchiMate layer colour fidelity — check nodes use correct layer colours ──
  if (archimateNodes.length > 0) {
    const layerColorCheck = await page.evaluate((nodeInfos) => {
      // Expected CSS layer background colours (from ArchimateRenderer CSS)
      const LAYER_COLORS = {
        business: '#ffffb5',
        application: '#b5ffff',
        technology: '#c9e7b7',
        motivation: '#ccccff',
        strategy: '#f5deaa',
        implementation_migration: '#ffe0e0',
      };
      function deriveLayer(entityType) {
        if (entityType.startsWith('business_')) return 'business';
        if (entityType.startsWith('application_')) return 'application';
        if (entityType.startsWith('technology_')) return 'technology';
        if (['stakeholder', 'driver', 'assessment', 'goal', 'outcome', 'principle',
          'requirement_archimate', 'constraint_archimate'].includes(entityType)) return 'motivation';
        if (['resource', 'capability', 'course_of_action', 'value_stream'].includes(entityType)) return 'strategy';
        if (['work_package', 'deliverable', 'implementation_event', 'plateau', 'gap'].includes(entityType)) return 'implementation_migration';
        return 'business';
      }
      function hexToRgb(hex) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return { r, g, b };
      }
      function colorDistance(c1, c2) {
        return Math.sqrt((c1.r - c2.r) ** 2 + (c1.g - c2.g) ** 2 + (c1.b - c2.b) ** 2);
      }
      function parseRgb(css) {
        const m = css.match(/rgb\((\d+),\s*(\d+),\s*(\d+)/);
        if (m) return { r: parseInt(m[1]), g: parseInt(m[2]), b: parseInt(m[3]) };
        return null;
      }
      let wrongLayer = 0;
      let umlOverridden = 0;
      const examples = [];
      for (const info of nodeInfos) {
        const el = document.querySelector(`[data-id="${info.id}"]`);
        if (!el) continue;
        const inner = el.querySelector('.archimate-node');
        if (!inner) continue;
        const bg = getComputedStyle(inner).backgroundColor;
        const rendered = parseRgb(bg);
        if (!rendered) continue;
        const layer = deriveLayer(info.entityType);
        const expected = hexToRgb(LAYER_COLORS[layer] || '#ffffff');
        const dist = colorDistance(rendered, expected);
        // Check if overridden by UML theme cream (#ffffcc = rgb(255,255,204))
        const umlCream = { r: 255, g: 255, b: 204 };
        const distToCream = colorDistance(rendered, umlCream);
        if (dist > 40 && distToCream < 10 && layer !== 'business') {
          umlOverridden++;
          if (examples.length < 5) {
            const label = inner.querySelector('.archimate-node__label')?.textContent?.trim().slice(0, 25) || info.id;
            examples.push(`${label} (${layer}: expected ${LAYER_COLORS[layer]}, got UML cream)`);
          }
        } else if (dist > 60 && !info.hasBgOverride) {
          wrongLayer++;
          if (examples.length < 5) {
            const label = inner.querySelector('.archimate-node__label')?.textContent?.trim().slice(0, 25) || info.id;
            examples.push(`${label} (${layer}: distance=${dist.toFixed(0)})`);
          }
        }
      }
      return { total: nodeInfos.length, wrongLayer, umlOverridden, examples };
    }, archimateNodes.map(n => ({
      id: n.id,
      entityType: n.data?.entityType || '',
      hasBgOverride: !!n.data?.visual?.bgColor,
    })));
    if (layerColorCheck.umlOverridden > 0) {
      issues.push({
        type: 'archimate_uml_color_override', severity: 'high',
        detail: `${layerColorCheck.umlOverridden}/${layerColorCheck.total} ArchiMate nodes overridden by UML theme cream — layer colours not applied: ${layerColorCheck.examples.join('; ')}`,
      });
    }
    if (layerColorCheck.wrongLayer > 0) {
      issues.push({
        type: 'archimate_wrong_layer_color', severity: 'medium',
        detail: `${layerColorCheck.wrongLayer}/${layerColorCheck.total} ArchiMate nodes have unexpected background colour: ${layerColorCheck.examples.join('; ')}`,
      });
    }
    if (layerColorCheck.umlOverridden === 0 && layerColorCheck.wrongLayer === 0) {
      correct.push(`ArchiMate layer colours: ${layerColorCheck.total} nodes correctly coloured by layer`);
    }
  }

  return { issues, correct, renderedColors, meta: { nodeColors, edgeLabels, links, stereotypes, sizeMismatches, labelStats, layoutSpread } };
}

// ── Comparison Logic ──────────────────────────────────────────────────────
function loadPreviousIteration(prevIter) {
  // Search across all dated subdirs for the previous iteration's data
  const prevPath = findIterationFile(prevIter);
  if (!prevPath) return null;
  return JSON.parse(readFileSync(prevPath, 'utf-8'));
}

/**
 * Compare current vs previous results by diagram NAME (not ID).
 * This ensures comparisons work correctly even after re-importing
 * diagrams with new database IDs.
 */
function computeDelta(currentResults, previousResults) {
  const delta = {
    fixed: [],      // issues in previous but not in current
    regressed: [],  // issues in current but not in previous
    persistent: [], // issues in both
    newDiagrams: [],
  };

  for (const [setName, currentSet] of Object.entries(currentResults)) {
    const prevSet = previousResults[setName] || [];
    // Match by name instead of ID for stability across re-imports
    const prevByName = {};
    for (const d of prevSet) {
      prevByName[d.name] = d;
    }

    for (const curr of currentSet) {
      const prev = prevByName[curr.name];
      if (!prev) {
        delta.newDiagrams.push({ set: setName, id: curr.id, name: curr.name });
        continue;
      }

      // Compare issues by type (not detail, since detail text may change slightly)
      const prevIssueKeys = new Set(prev.issues.map(i => `${i.type}::${i.detail}`));
      const currIssueKeys = new Set(curr.issues.map(i => `${i.type}::${i.detail}`));

      for (const issue of prev.issues) {
        const key = `${issue.type}::${issue.detail}`;
        if (!currIssueKeys.has(key)) {
          delta.fixed.push({ set: setName, diagram: curr.name, id: curr.id, ...issue });
        }
      }

      for (const issue of curr.issues) {
        const key = `${issue.type}::${issue.detail}`;
        if (!prevIssueKeys.has(key)) {
          delta.regressed.push({ set: setName, diagram: curr.name, id: curr.id, ...issue });
        } else {
          delta.persistent.push({ set: setName, diagram: curr.name, id: curr.id, ...issue });
        }
      }
    }
  }

  return delta;
}

function countIssues(results) {
  let total = 0;
  let totalActionable = 0;
  const byType = {};
  const bySeverity = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  let diagsWithIssues = 0;
  let diagsWithActionableIssues = 0;
  let totalDiags = 0;

  for (const set of Object.values(results)) {
    for (const d of set) {
      totalDiags++;
      let hasIssue = false;
      let hasActionable = false;
      for (const issue of d.issues) {
        total++;
        byType[issue.type] = (byType[issue.type] || 0) + 1;
        bySeverity[issue.severity] = (bySeverity[issue.severity] || 0) + 1;
        hasIssue = true;
        if (issue.severity !== 'info') {
          totalActionable++;
          hasActionable = true;
        }
      }
      if (hasIssue) diagsWithIssues++;
      if (hasActionable) diagsWithActionableIssues++;
    }
  }

  return { total, totalActionable, byType, bySeverity, diagsWithIssues, diagsWithActionableIssues, totalDiags };
}

// ── Output Writers ────────────────────────────────────────────────────────
function writeIterationReport(outputDir, iter, allResults) {
  const jsonPath = join(outputDir, `audit_iter_${iter}.json`);
  const mdPath = join(outputDir, `AUDIT_ITER_${iter}.md`);

  // JSON output
  writeFileSync(jsonPath, JSON.stringify(allResults, null, 2));
  console.log(`  JSON: ${jsonPath}`);

  // Markdown report
  const stats = countIssues(allResults);
  let md = `# EA Visual Audit — Iteration ${iter}\n\n`;
  md += `**Date:** ${new Date().toISOString().split('T')[0]}\n`;
  md += `**Iteration:** ${iter} of ${MAX_ITERATIONS}\n`;
  md += `**Handle strategy:** ${handleStrategy}\n`;
  md += `**Diagrams audited:** ${stats.totalDiags}\n`;
  md += `**Diagrams with actionable issues:** ${stats.diagsWithActionableIssues}\n`;
  md += `**Total issues:** ${stats.total} (${stats.totalActionable} actionable, ${stats.total - stats.totalActionable} informational)\n`;
  md += `**By severity:** critical=${stats.bySeverity.critical}, high=${stats.bySeverity.high}, medium=${stats.bySeverity.medium}, low=${stats.bySeverity.low}, info=${stats.bySeverity.info || 0}\n\n`;

  md += '## Summary by Issue Type\n\n';
  md += '| Issue Type | Count | Severity |\n';
  md += '|-----------|-------|----------|\n';
  const issueSummary = {};
  for (const [setName, results] of Object.entries(allResults)) {
    for (const r of results) {
      for (const issue of r.issues) {
        if (!issueSummary[issue.type]) issueSummary[issue.type] = { count: 0, severity: issue.severity };
        issueSummary[issue.type].count++;
      }
    }
  }
  for (const [type, data] of Object.entries(issueSummary).sort((a, b) => b[1].count - a[1].count)) {
    md += `| ${type} | ${data.count} | ${data.severity} |\n`;
  }

  // Visual comparison summary (if any diagrams were compared)
  const vizResults = [];
  for (const [setName, results] of Object.entries(allResults)) {
    for (const r of results) {
      if (r.visualComparison) {
        vizResults.push({ set: setName, name: r.name, ...r.visualComparison,
          gtColors: r.gtColorAnalysis?.colors?.length || 0,
          irisColors: r.renderedColors?.length || 0,
        });
      }
    }
  }
  if (vizResults.length > 0) {
    md += '\n## Visual Ground Truth Comparison\n\n';
    md += `**Diagrams compared:** ${vizResults.length}\n`;
    md += `**Screenshots saved to:** \`screenshots/\` subdirectory\n`;
    md += `**Side-by-side report:** \`COMPARISON.html\`\n\n`;
    md += '| Set | Diagram | GT Type | GT Colors | Iris Colors | Screenshots |\n';
    md += '|-----|---------|---------|-----------|-------------|-------------|\n';
    for (const v of vizResults) {
      const screenshotStatus = v.hasScreenshots ? 'Yes' : (v.gtAvailable ? 'Partial' : 'No GT');
      md += `| ${v.set} | ${v.name} | ${v.groundTruthType} | ${v.gtColors} | ${v.irisColors} | ${screenshotStatus} |\n`;
    }
  }

  for (const [setName, results] of Object.entries(allResults)) {
    md += `\n---\n\n## ${setName}\n\n`;
    for (const r of results) {
      md += `### ${r.name} (id: \`${r.id}\`)\n`;
      const actionableIssues = r.issues.filter(i => i.severity !== 'info');
      md += `**Status:** ${actionableIssues.length === 0 ? 'PASS' : 'ISSUES_FOUND'}\n\n`;
      if (r.visualComparison) {
        md += `**Ground truth:** ${r.visualComparison.groundTruthType} (${r.visualComparison.hasScreenshots ? 'screenshots saved' : 'no screenshots'})\n\n`;
      }
      if (r.issues.length > 0) {
        md += '**Issues:**\n';
        for (const issue of r.issues) {
          md += `- [${issue.severity}] **${issue.type}**: ${issue.detail}\n`;
        }
        md += '\n';
      }
      if (r.correct.length > 0) {
        md += '**Correct:** ' + r.correct.join(', ') + '\n\n';
      }
    }
  }

  writeFileSync(mdPath, md);
  console.log(`  Report: ${mdPath}`);
}

function writeComparisonReport(outputDir, iter, delta, currentStats, previousStats) {
  const mdPath = join(outputDir, `AUDIT_COMPARISON_${iter}.md`);

  let md = `# Audit Comparison — Iteration ${iter} vs ${iter - 1}\n\n`;
  md += `**Date:** ${new Date().toISOString().split('T')[0]}\n\n`;

  // Score summary
  const issueReduction = previousStats.total - currentStats.total;
  const pct = previousStats.total > 0 ? ((issueReduction / previousStats.total) * 100).toFixed(1) : '0';
  md += '## Score\n\n';
  md += `| Metric | Iter ${iter - 1} | Iter ${iter} | Delta |\n`;
  md += '|--------|----------|----------|-------|\n';
  md += `| Total issues | ${previousStats.total} | ${currentStats.total} | ${issueReduction > 0 ? '-' : '+'}${Math.abs(issueReduction)} (${pct}%) |\n`;
  md += `| Actionable issues | ${previousStats.totalActionable} | ${currentStats.totalActionable} | ${previousStats.totalActionable - currentStats.totalActionable} |\n`;
  md += `| Diagrams with issues | ${previousStats.diagsWithIssues} | ${currentStats.diagsWithIssues} | ${previousStats.diagsWithIssues - currentStats.diagsWithIssues} |\n`;
  md += `| Critical | ${previousStats.bySeverity.critical} | ${currentStats.bySeverity.critical} | ${previousStats.bySeverity.critical - currentStats.bySeverity.critical} |\n`;
  md += `| High | ${previousStats.bySeverity.high} | ${currentStats.bySeverity.high} | ${previousStats.bySeverity.high - currentStats.bySeverity.high} |\n`;
  md += `| Medium | ${previousStats.bySeverity.medium} | ${currentStats.bySeverity.medium} | ${previousStats.bySeverity.medium - currentStats.bySeverity.medium} |\n`;
  md += `| Low | ${previousStats.bySeverity.low} | ${currentStats.bySeverity.low} | ${previousStats.bySeverity.low - currentStats.bySeverity.low} |\n`;
  md += `| Info | ${previousStats.bySeverity.info || 0} | ${currentStats.bySeverity.info || 0} | ${(previousStats.bySeverity.info || 0) - (currentStats.bySeverity.info || 0)} |\n\n`;

  // By type comparison
  const allTypes = new Set([...Object.keys(previousStats.byType), ...Object.keys(currentStats.byType)]);
  md += '## By Issue Type\n\n';
  md += `| Type | Iter ${iter - 1} | Iter ${iter} | Delta |\n`;
  md += '|------|----------|----------|-------|\n';
  for (const type of [...allTypes].sort()) {
    const prev = previousStats.byType[type] || 0;
    const curr = currentStats.byType[type] || 0;
    const d = prev - curr;
    md += `| ${type} | ${prev} | ${curr} | ${d > 0 ? '-' : d < 0 ? '+' : ''}${Math.abs(d)} |\n`;
  }

  // Fixed issues
  md += `\n## Fixed (${delta.fixed.length})\n\n`;
  if (delta.fixed.length > 0) {
    for (const f of delta.fixed) {
      md += `- **${f.diagram}** [${f.set}]: ${f.type} — ${f.detail}\n`;
    }
  } else {
    md += '_No issues fixed in this iteration._\n';
  }

  // Regressions
  md += `\n## Regressions (${delta.regressed.length})\n\n`;
  if (delta.regressed.length > 0) {
    for (const r of delta.regressed) {
      md += `- **${r.diagram}** [${r.set}]: ${r.type} — ${r.detail}\n`;
    }
  } else {
    md += '_No regressions._\n';
  }

  // Persistent
  md += `\n## Persistent Issues (${delta.persistent.length})\n\n`;
  if (delta.persistent.length > 0) {
    const grouped = {};
    for (const p of delta.persistent) {
      grouped[p.type] = grouped[p.type] || [];
      grouped[p.type].push(p);
    }
    for (const [type, items] of Object.entries(grouped)) {
      md += `### ${type} (${items.length})\n`;
      for (const item of items.slice(0, 10)) {
        md += `- ${item.diagram}: ${item.detail}\n`;
      }
      if (items.length > 10) md += `- _...and ${items.length - 10} more_\n`;
      md += '\n';
    }
  }

  writeFileSync(mdPath, md);
  console.log(`  Comparison: ${mdPath}`);
}

function writeSummaryReport(outputDir, iter) {
  const mdPath = join(outputDir, 'AUDIT_SUMMARY.md');
  let md = '# EA Visual Audit — Cumulative Summary\n\n';
  md += `**Last updated:** ${new Date().toISOString().split('T')[0]}\n`;
  md += `**Iterations completed:** ${iter + 1} (0 through ${iter})\n`;
  md += `**Handle strategy:** ${handleStrategy}\n\n`;

  // Load all iterations (searching across all dated subdirs)
  const iterStats = [];
  for (let i = 0; i <= iter; i++) {
    const iterPath = findIterationFile(i);
    if (!iterPath) continue;
    const data = JSON.parse(readFileSync(iterPath, 'utf-8'));
    iterStats.push({ iter: i, ...countIssues(data) });
  }

  if (iterStats.length === 0) {
    md += '_No iteration data found._\n';
    writeFileSync(mdPath, md);
    return;
  }

  // Progress table
  md += '## Progress\n\n';
  md += '| Iteration | Total Issues | Actionable | Info | Critical | High | Medium | Low | Diagrams w/ Actionable |\n';
  md += '|-----------|-------------|-----------|------|----------|------|--------|-----|------------------------|\n';
  for (const s of iterStats) {
    md += `| ${s.iter} | ${s.total} | ${s.totalActionable} | ${s.total - s.totalActionable} | ${s.bySeverity.critical} | ${s.bySeverity.high} | ${s.bySeverity.medium} | ${s.bySeverity.low} | ${s.diagsWithActionableIssues}/${s.totalDiags} |\n`;
  }

  // Improvement rate
  if (iterStats.length >= 2) {
    const first = iterStats[0];
    const last = iterStats[iterStats.length - 1];
    const totalReduction = first.totalActionable - last.totalActionable;
    const pct = first.totalActionable > 0 ? ((totalReduction / first.totalActionable) * 100).toFixed(1) : '0';
    md += `\n**Overall improvement:** ${totalReduction} actionable issues fixed (${pct}% reduction from baseline)\n`;

    if (last.totalActionable === 0) {
      md += '\n**All actionable issues resolved!**\n';
    } else {
      md += `\n**Remaining actionable issues:** ${last.totalActionable}\n`;
      md += '\n### Remaining by Type\n\n';
      for (const [type, count] of Object.entries(last.byType).sort((a, b) => b[1] - a[1])) {
        md += `- ${type}: ${count}\n`;
      }
    }
  }

  writeFileSync(mdPath, md);
  console.log(`  Summary: ${mdPath}`);
}

// ── Main ───────────────────────────────────────────────────────────────────
async function main() {
  console.log(`\n========================================`);
  console.log(`  EA Visual Audit — Iteration ${iteration}`);
  console.log(`  Handle strategy: ${handleStrategy}`);
  console.log(`========================================\n`);

  const token = getToken();
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  // Login via token in sessionStorage (Iris stores auth in sessionStorage with key 'iris_auth')
  await page.goto(`${IRIS_URL}`, { timeout: 10000 });
  await page.evaluate((t) => {
    const authData = JSON.stringify({
      accessToken: t,
      refreshToken: t,
      user: { id: 'audit', username: 'audit', role: 'admin' },
    });
    sessionStorage.setItem('iris_auth', authData);
    localStorage.setItem('token', t);
  }, token);

  // Discover sets dynamically, fall back to hardcoded
  let SETS;
  if (setIdArg) {
    SETS = { CUSTOM: setIdArg };
  } else {
    const discovered = await discoverSets(token);
    if (discovered) {
      console.log(`  Discovered ${Object.keys(discovered).length} sets from API`);
      SETS = discovered;
    } else {
      console.log('  Using fallback set IDs (API discovery failed)');
      SETS = FALLBACK_SETS;
    }
  }

  // Create run dir early so screenshots can be saved during the audit
  const RUN_DIR = createRunDir();
  const screenshotsDir = join(RUN_DIR, 'screenshots');
  mkdirSync(screenshotsDir, { recursive: true });

  const allResults = {};
  const setsToAudit = setFilter ? { [setFilter]: SETS[setFilter] } : SETS;

  // Skip DEFAULT set (seed data, not EA imports) unless explicitly requested
  if (!setFilter || setFilter !== 'DEFAULT') {
    delete setsToAudit['DEFAULT'];
  }

  for (const [setName, setId] of Object.entries(setsToAudit)) {
    if (!setId) {
      console.error(`Unknown set: ${setName}`);
      continue;
    }
    console.log(`\n--- Auditing ${setName} ---`);
    let diagrams;
    try {
      diagrams = await fetchAllDiagrams(token, setId);
    } catch (e) {
      console.error(`Failed to fetch diagrams for ${setName}: ${e.message}`);
      continue;
    }

    if (limitArg > 0) diagrams = diagrams.slice(0, limitArg);
    console.log(`  ${diagrams.length} diagrams to audit`);

    // Create set-specific screenshot directory
    const setScreenshotDir = join(screenshotsDir, setName);
    mkdirSync(setScreenshotDir, { recursive: true });

    const results = [];
    for (let i = 0; i < diagrams.length; i++) {
      const d = diagrams[i];
      const name = d.name || `diagram-${i + 1}`;
      process.stdout.write(`  [${i + 1}/${diagrams.length}] ${name}...`);

      let detail;
      try {
        detail = await fetchDiagramDetail(token, d.id);
      } catch (e) {
        console.log(` ERROR: ${e.message}`);
        results.push({ id: d.id, name, issues: [{ type: 'api_error', severity: 'critical', detail: e.message }], correct: [] });
        continue;
      }

      const result = await auditDiagram(page, d.id, name, detail);

      // ── Visual ground truth comparison (DOM-based + side-by-side screenshots) ──
      if (!skipVisualCompare) {
        const gt = resolveGroundTruth(setName, name, i);
        if (gt.type !== 'none') {
          try {
            const irisScreenshot = await screenshotIrisDiagram(page);
            const gtImage = await getGroundTruthImage(browser, gt);

            // Save screenshots for side-by-side HTML report
            const safeName = name.replace(/[^a-zA-Z0-9_-]/g, '_');
            if (irisScreenshot) {
              writeFileSync(join(setScreenshotDir, `${safeName}_iris.png`), irisScreenshot);
            }
            if (gtImage) {
              writeFileSync(join(setScreenshotDir, `${safeName}_gt.png`), gtImage);
            }

            // Extract GT color palette for comparison with rendered colors
            if (gtImage) {
              try {
                const gtColorAnalysis = await analyzeGroundTruthColors(page, gtImage);
                result.gtColorAnalysis = gtColorAnalysis;

                // Compare GT color palette against rendered node colors.
                // Note: GT color count includes all page colors (UI chrome, borders, text),
                // not just node backgrounds. For UML class diagrams where EA uses a single
                // default color, having 1 rendered color is correct even if GT shows 20.
                const irisColorCount = result.renderedColors?.length || 0;
                const gtColorCount = gtColorAnalysis.colors.length;
                if (gtColorAnalysis.hasMultipleHues && irisColorCount === 0) {
                  result.issues.push({
                    type: 'gt_color_missing', severity: 'high',
                    detail: `Ground truth has ${gtColorCount} distinct colors but Iris renders no colored nodes (all white/default)`,
                  });
                } else if (gtColorAnalysis.hasMultipleHues && irisColorCount > 0 && irisColorCount < gtColorCount * 0.1) {
                  // Only flag as deficit when Iris has <10% of GT colors AND GT has many colors
                  // (suggesting the diagram genuinely uses color differentiation)
                  result.issues.push({
                    type: 'gt_color_deficit', severity: 'info',
                    detail: `Ground truth page has ${gtColorCount} colors, Iris renders ${irisColorCount} node colors (GT count includes page UI colors)`,
                  });
                }
              } catch (colorErr) {
                // Color analysis failed — not critical, continue
              }
            }

            result.visualComparison = {
              groundTruthType: gt.type,
              groundTruthPath: gt.path,
              hasScreenshots: !!(irisScreenshot && gtImage),
              gtAvailable: !!gtImage,
            };

            if (!gtImage) {
              result.issues.push({
                type: 'gt_unavailable', severity: 'info',
                detail: `Ground truth ${gt.type} could not be loaded: ${gt.path}`,
              });
            }
          } catch (e) {
            result.issues.push({
              type: 'visual_compare_error', severity: 'info',
              detail: `Visual comparison failed: ${e.message}`,
            });
          }
        }
      }

      results.push({ id: d.id, name, ...result });

      const issueCount = result.issues.filter(i => i.severity !== 'info').length;
      const infoCount = result.issues.filter(i => i.severity === 'info').length;
      const vizNote = result.visualComparison ? ` [gt:${result.visualComparison.groundTruthType}]` : '';
      if (issueCount > 0) {
        console.log(` ${issueCount} issues${infoCount > 0 ? ` (+${infoCount} info)` : ''}${vizNote}`);
      } else if (infoCount > 0) {
        console.log(` OK (${infoCount} info)${vizNote}`);
      } else {
        console.log(` OK${vizNote}`);
      }
    }

    allResults[setName] = results;
  }

  await browser.close();

  console.log(`\n--- Writing results to ${RUN_DIR} ---`);

  // 0. Side-by-side HTML comparison (if visual compare was run)
  if (!skipVisualCompare) {
    generateComparisonHtml(RUN_DIR, allResults);
  }

  // 1. Iteration report
  writeIterationReport(RUN_DIR, iteration, allResults);

  // 2. Comparison with previous (if not baseline)
  const currentStats = countIssues(allResults);
  if (iteration > 0) {
    const prevData = loadPreviousIteration(iteration - 1);
    if (prevData) {
      const previousStats = countIssues(prevData);
      const delta = computeDelta(allResults, prevData);
      writeComparisonReport(RUN_DIR, iteration, delta, currentStats, previousStats);

      console.log(`\n--- Iteration ${iteration} vs ${iteration - 1} ---`);
      console.log(`  Fixed: ${delta.fixed.length}`);
      console.log(`  Regressed: ${delta.regressed.length}`);
      console.log(`  Persistent: ${delta.persistent.length}`);
      console.log(`  Total issues: ${previousStats.total} -> ${currentStats.total} (${previousStats.total - currentStats.total > 0 ? '-' : '+'}${Math.abs(previousStats.total - currentStats.total)})`);
      console.log(`  Actionable: ${previousStats.totalActionable} -> ${currentStats.totalActionable}`);
    } else {
      console.log(`  WARNING: No previous iteration ${iteration - 1} data found for comparison`);
    }
  }

  // 3. Cumulative summary (written to run dir and also to base dir for easy access)
  writeSummaryReport(RUN_DIR, iteration);
  writeSummaryReport(BASE_OUTPUT_DIR, iteration);

  console.log(`\n========================================`);
  console.log(`  Iteration ${iteration} complete`);
  console.log(`  Total diagrams: ${currentStats.totalDiags}`);
  console.log(`  Total issues: ${currentStats.total} (${currentStats.totalActionable} actionable)`);
  console.log(`  Diagrams passing: ${currentStats.totalDiags - currentStats.diagsWithActionableIssues}/${currentStats.totalDiags}`);
  if (iteration < MAX_ITERATIONS && currentStats.totalActionable > 0) {
    console.log(`\n  Next: Fix issues, then run with --iteration ${iteration + 1}`);
  } else if (currentStats.totalActionable === 0) {
    console.log(`\n  All actionable issues resolved!`);
  } else {
    console.log(`\n  Final iteration complete. Review AUDIT_SUMMARY.md for overall progress.`);
  }
  console.log(`========================================\n`);
}

main().catch(e => {
  console.error('Fatal:', e);
  process.exit(1);
});
