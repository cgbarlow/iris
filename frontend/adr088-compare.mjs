import { chromium } from 'playwright';

const IRIS_URL = 'http://localhost:5173/diagrams/57f0f29b-e613-4b68-a678-9a84bae1996e';

async function getToken() {
  const res = await fetch('http://localhost:8000/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'TestAdmin1' }),
  });
  const data = await res.json();
  return data;
}

async function main() {
  const tokens = await getToken();
  if (!tokens?.access_token) { console.error('Login failed'); process.exit(1); }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1200 } });

  const irisPage = await context.newPage();
  await irisPage.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await irisPage.evaluate((t) => {
    sessionStorage.setItem('iris_auth', JSON.stringify({
      accessToken: t.access_token,
      refreshToken: t.refresh_token,
      user: { id: 'admin', username: 'admin', role: 'admin' },
    }));
  }, tokens);

  await irisPage.goto(IRIS_URL, { waitUntil: 'networkidle', timeout: 30000 });
  await irisPage.waitForTimeout(5000);

  // Click Canvas tab
  try {
    const canvasBtn = irisPage.locator('button').filter({ hasText: 'Canvas' }).first();
    if (await canvasBtn.isVisible({ timeout: 2000 })) {
      await canvasBtn.click();
      await irisPage.waitForTimeout(3000);
    }
  } catch (e) {}

  await irisPage.waitForTimeout(2000);

  // Canvas screenshot
  try {
    const canvas = irisPage.locator('.svelte-flow').first();
    if (await canvas.isVisible({ timeout: 3000 })) {
      await canvas.screenshot({ path: '/tmp/iris-adr088-canvas.png' });
      console.log('Canvas screenshot saved to /tmp/iris-adr088-canvas.png');
    }
  } catch (e) {
    console.log('No canvas found');
  }

  // === DETAILED ANALYSIS ===
  console.log('\n========== ADR-088 DETAILED ANALYSIS ==========\n');

  const analysis = await irisPage.evaluate(() => {
    const nodes = document.querySelectorAll('.svelte-flow__node');
    const result = { nodes: [], edges: [], handles: [], endpointLabels: [] };

    for (const n of nodes) {
      const transform = n.style.transform || '';
      const translateMatch = transform.match(/translate\((\S+)px,\s*(\S+)px\)/);
      const x = translateMatch ? parseFloat(translateMatch[1]) : 0;
      const y = translateMatch ? parseFloat(translateMatch[2]) : 0;

      const label = n.querySelector('.uml-node__label, .canvas-node__label');
      const attrs = n.querySelectorAll('.uml-node__attr');
      const mainEl = n.querySelector('.uml-node, .canvas-node--note');
      const mainStyle = mainEl ? window.getComputedStyle(mainEl) : null;
      const desc = n.querySelector('.canvas-node__description');
      const noteHeader = n.querySelector('.canvas-node__header .canvas-node__label');
      const compartment = n.querySelector('.uml-node__compartment');
      const compartmentStyle = compartment ? window.getComputedStyle(compartment) : null;
      const attrEl = n.querySelector('.uml-node__attr');
      const attrStyle = attrEl ? window.getComputedStyle(attrEl) : null;
      const rect = mainEl?.getBoundingClientRect() || n.getBoundingClientRect();

      // Check if content overflows
      const isOverflowing = mainEl ? (mainEl.scrollHeight > mainEl.clientHeight || mainEl.scrollWidth > mainEl.clientWidth) : false;

      // Check handles
      const handles = n.querySelectorAll('.svelte-flow__handle');
      const handleData = Array.from(handles).map(h => ({
        id: h.getAttribute('data-handleid') || h.id || '?',
        type: h.classList.contains('source') ? 'source' : h.classList.contains('target') ? 'target' : '?',
        pos: h.classList.contains('top') ? 'top' :
             h.classList.contains('bottom') ? 'bottom' :
             h.classList.contains('left') ? 'left' :
             h.classList.contains('right') ? 'right' : '?',
      }));

      result.nodes.push({
        label: label?.textContent?.trim() ?? noteHeader?.textContent?.trim() ?? '?',
        x: Math.round(x), y: Math.round(y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        isNote: !!n.querySelector('.canvas-node--note'),
        isDiagramFrame: n.getAttribute('data-id')?.includes('diagram_frame') || n.querySelector('.diagram-frame-node') !== null,
        attrCount: attrs.length,
        attrs: Array.from(attrs).map(a => a.textContent?.trim()),
        attrFontStyle: attrStyle?.fontStyle ?? null,
        compartmentFontStyle: compartmentStyle?.fontStyle ?? null,
        overflow: mainStyle?.overflow,
        boxSizing: mainStyle?.boxSizing,
        isOverflowing,
        hasDescription: !!desc,
        descriptionText: desc?.textContent?.trim()?.substring(0, 100) ?? null,
        noteHeaderText: noteHeader?.textContent?.trim() ?? null,
        handleCount: handles.length,
        handles: handleData,
        cssWidth: mainStyle?.width,
        cssHeight: mainStyle?.height,
        cssMinWidth: mainStyle?.minWidth,
      });
    }

    // Edge analysis
    const edges = document.querySelectorAll('.svelte-flow__edge');
    for (const e of edges) {
      const path = e.querySelector('path');
      const d = path?.getAttribute('d') ?? '';
      const markerStart = path?.getAttribute('marker-start') ?? 'none';
      const markerEnd = path?.getAttribute('marker-end') ?? 'none';

      // Try to find source/target
      const edgeId = e.getAttribute('data-id') ?? '';

      result.edges.push({
        id: edgeId,
        markerStart, markerEnd,
        pathD: d.substring(0, 150),
      });
    }

    // Endpoint labels
    const epLabels = document.querySelectorAll('.edge-endpoint-label');
    for (const lbl of epLabels) {
      const text = lbl.textContent?.trim() ?? '';
      const rect = lbl.getBoundingClientRect();
      result.endpointLabels.push({
        text,
        x: Math.round(rect.x),
        y: Math.round(rect.y),
      });
    }

    return result;
  });

  // Report nodes
  console.log('--- NODES ---');
  for (const n of analysis.nodes) {
    if (n.isDiagramFrame) {
      console.log(`  [FRAME] "${n.label}" at (${n.x},${n.y}) ${n.width}x${n.height}px`);
      continue;
    }
    const type = n.isNote ? 'NOTE' : 'CLASS';
    console.log(`  [${type}] "${n.label}" at (${n.x},${n.y}) ${n.width}x${n.height}px`);
    if (n.isNote) {
      console.log(`    Header: "${n.noteHeaderText}"`);
      console.log(`    Description present: ${n.hasDescription}`);
      if (n.descriptionText) console.log(`    Description: "${n.descriptionText}..."`);
    }
    if (!n.isNote) {
      console.log(`    CSS: width=${n.cssWidth} height=${n.cssHeight} minWidth=${n.cssMinWidth}`);
      console.log(`    overflow=${n.overflow} boxSizing=${n.boxSizing} overflowing=${n.isOverflowing}`);
      console.log(`    attrFontStyle=${n.attrFontStyle} compartmentFontStyle=${n.compartmentFontStyle}`);
      console.log(`    Attrs (${n.attrCount}): ${n.attrs.join(' | ')}`);
    }
    console.log(`    Handles (${n.handleCount}): ${n.handles.map(h => `${h.id}:${h.type}`).join(', ')}`);
  }

  // Vertical alignment check
  console.log('\n--- VERTICAL ALIGNMENT CHECK ---');
  const classNodes = analysis.nodes.filter(n => !n.isNote && !n.isDiagramFrame);
  const byName = {};
  for (const n of classNodes) byName[n.label] = n;

  const alignTargets = ['AIXMFeature', 'AIXMTimeSlice', 'AIXMFeaturePropertyGroup', 'Extension'];
  for (const name of alignTargets) {
    const n = byName[name];
    if (n) {
      const centerX = n.x + n.width / 2;
      console.log(`  ${name}: x=${n.x} centerX=${Math.round(centerX)} width=${n.width}`);
    } else {
      console.log(`  ${name}: NOT FOUND`);
    }
  }

  // Edge analysis
  console.log('\n--- EDGES ---');
  for (const e of analysis.edges) {
    console.log(`  ${e.id.substring(0, 8)}: start=${e.markerStart} end=${e.markerEnd}`);
    console.log(`    path: ${e.pathD}...`);
  }

  // Endpoint labels
  console.log('\n--- ENDPOINT LABELS ---');
  for (const l of analysis.endpointLabels) {
    console.log(`  "${l.text}" at (${l.x}, ${l.y})`);
  }

  // ADR-088 Issue Checks
  console.log('\n========== ADR-088 ISSUE CHECKS ==========');

  // Issue 1: Note dedup
  const noteNodes = analysis.nodes.filter(n => n.isNote);
  for (const note of noteNodes) {
    const headerText = note.noteHeaderText || '';
    const descText = note.descriptionText || '';
    const isDuplicated = descText.startsWith(headerText);
    console.log(`\n[Issue 1 - Note Dedup] "${headerText}"`);
    console.log(`  Description starts with header: ${isDuplicated ? 'FAIL - still duplicated' : 'PASS'}`);
    console.log(`  Description: "${descText}"`);
  }

  // Issue 2: Attr italic
  const abstractNodes = classNodes.filter(n => n.label === 'AIXMFeature' || n.label === 'AIXMTimeSlice');
  for (const n of abstractNodes) {
    console.log(`\n[Issue 2 - Attr Italic] ${n.label}`);
    console.log(`  attrFontStyle: ${n.attrFontStyle} (should be 'normal')`);
    console.log(`  ${n.attrFontStyle === 'normal' ? 'PASS' : 'FAIL'}`);
  }

  // Issue 3: Fixed sizing
  for (const n of classNodes) {
    console.log(`\n[Issue 3 - Fixed Sizing] ${n.label}`);
    console.log(`  overflow: ${n.overflow} (should be 'hidden')`);
    console.log(`  overflowing: ${n.isOverflowing}`);
    console.log(`  ${n.overflow === 'hidden' && !n.isOverflowing ? 'PASS' : n.isOverflowing ? 'FAIL - content overflows' : 'CHECK'}`);
  }

  // Issue 4: Composition markers
  const compositionEdges = analysis.edges.filter(e => e.markerStart.includes('diamond'));
  console.log(`\n[Issue 4 - Composition Markers]`);
  for (const e of compositionEdges) {
    console.log(`  Edge ${e.id.substring(0, 8)}: start=${e.markerStart} end=${e.markerEnd}`);
    console.log(`  Has target arrow: ${e.markerEnd !== 'none' ? 'PASS' : 'FAIL'}`);
  }

  // Issue 5: Handles
  console.log(`\n[Issue 5 - Handles]`);
  for (const n of classNodes.slice(0, 3)) {
    const sourceHandles = n.handles.filter(h => h.type === 'source').length;
    const targetHandles = n.handles.filter(h => h.type === 'target').length;
    console.log(`  ${n.label}: ${n.handleCount} handles (${sourceHandles} source, ${targetHandles} target)`);
  }

  // Issue 7: Diagram frame
  const frameNodes = analysis.nodes.filter(n => n.isDiagramFrame);
  console.log(`\n[Issue 7 - Diagram Frame]`);
  console.log(`  Frame nodes found: ${frameNodes.length} ${frameNodes.length > 0 ? 'PASS' : 'FAIL'}`);

  await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
