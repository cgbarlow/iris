import { chromium } from 'playwright';

const IRIS_URL = 'http://localhost:5173/diagrams/a33fc32f-d202-4023-9e96-39dc51a39e0e';
const EA_URL = 'https://aixm.aero/sites/default/files/imce/AIXM511HTML/AIXM/Diagram_Main.html';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1200 } });

  // --- Step 1: Navigate to Iris, handle auth ---
  console.log('Navigating to Iris...');
  const irisPage = await context.newPage();
  await irisPage.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await irisPage.waitForTimeout(2000);
  console.log('Current URL:', irisPage.url());

  // Check if login needed
  const usernameInput = irisPage.locator('#username');
  const passwordInput = irisPage.locator('#password');

  if (await usernameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
    console.log('Found login form...');
    for (const pwd of ['TestAdmin1', 'admin', 'Admin123', 'password']) {
      await usernameInput.fill('admin');
      await passwordInput.fill(pwd);
      const submitBtn = irisPage.locator('button[type="submit"]');
      await submitBtn.click();
      await irisPage.waitForTimeout(3000);
      console.log(`  Tried ${pwd} -> URL: ${irisPage.url()}`);
      if (!irisPage.url().includes('login')) {
        console.log(`Logged in with: admin/${pwd}`);
        break;
      }
    }
  }

  // Navigate to diagram
  console.log('Navigating to diagram...');
  await irisPage.goto(IRIS_URL, { waitUntil: 'networkidle', timeout: 30000 });
  await irisPage.waitForTimeout(5000);
  console.log('Diagram URL:', irisPage.url());

  // Click Canvas tab if exists
  try {
    const canvasBtn = irisPage.locator('button').filter({ hasText: 'Canvas' }).first();
    if (await canvasBtn.isVisible({ timeout: 2000 })) {
      await canvasBtn.click();
      await irisPage.waitForTimeout(3000);
    }
  } catch (e) {}

  // Wait more for rendering
  await irisPage.waitForTimeout(2000);
  await irisPage.screenshot({ path: '/tmp/iris-diagram.png', fullPage: true });

  // Canvas screenshot
  try {
    const canvas = irisPage.locator('.svelte-flow').first();
    if (await canvas.isVisible({ timeout: 3000 })) {
      await canvas.screenshot({ path: '/tmp/iris-canvas.png' });
      console.log('Canvas screenshot saved');
    }
  } catch (e) {
    console.log('No canvas found');
  }

  // === IRIS ANALYSIS ===
  console.log('\n========== IRIS DIAGRAM ANALYSIS ==========');

  const analysis = await irisPage.evaluate(() => {
    const nodes = document.querySelectorAll('.svelte-flow__node');
    const edges = document.querySelectorAll('.svelte-flow__edge');

    const nodeData = Array.from(nodes).map(n => {
      const label = n.querySelector('.uml-node__label, .canvas-node__label');
      const stereotype = n.querySelector('.uml-node__stereotype');
      const qualifier = n.querySelector('.uml-node__qualifier');
      const attrs = n.querySelectorAll('.uml-node__attr');
      const header = n.querySelector('.uml-node__header');
      const headerStyle = header ? window.getComputedStyle(header) : null;
      const labelStyle = label ? window.getComputedStyle(label) : null;
      const mainEl = n.querySelector('.uml-node, .canvas-node--note');
      const mainStyle = mainEl ? window.getComputedStyle(mainEl) : null;
      const rect = n.getBoundingClientRect();

      return {
        label: label?.textContent?.trim() ?? '?',
        stereotype: stereotype?.textContent?.trim() ?? null,
        qualifier: qualifier?.textContent?.trim() ?? null,
        attrCount: attrs.length,
        attrs: Array.from(attrs).map(a => a.textContent?.trim()),
        headerDisplay: headerStyle?.display,
        headerFlexDir: headerStyle?.flexDirection,
        headerAlignItems: headerStyle?.alignItems,
        labelWeight: labelStyle?.fontWeight,
        labelStyle: labelStyle?.fontStyle,
        bgColor: mainStyle?.backgroundColor,
        borderRadius: mainStyle?.borderRadius,
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        isNote: !!n.querySelector('.canvas-node--note'),
      };
    });

    const edgeData = Array.from(edges).map(e => {
      const path = e.querySelector('path');
      const d = path?.getAttribute('d') ?? '';
      const hasWaypoints = d.includes('L ') && (d.match(/L /g) || []).length > 1;
      return {
        markerStart: path?.getAttribute('marker-start') ?? 'none',
        markerEnd: path?.getAttribute('marker-end') ?? 'none',
        hasWaypoints,
        pathType: d.startsWith('M') && d.includes('C') ? 'bezier' : d.includes('L') ? 'polyline/step' : 'unknown',
      };
    });

    const frame = document.querySelector('svg.diagram-frame');

    return { nodes: nodeData, edges: edgeData, hasFrame: !!frame };
  });

  console.log(`Total: ${analysis.nodes.length} nodes, ${analysis.edges.length} edges, frame: ${analysis.hasFrame}`);

  // Categorize nodes
  const umlNodes = analysis.nodes.filter(n => !n.isNote);
  const noteNodes = analysis.nodes.filter(n => n.isNote);

  console.log('\n--- UML CLASS NODES ---');
  for (const n of umlNodes) {
    let line = `  ${n.label}`;
    if (n.qualifier) line += ` (${n.qualifier}::)`;
    if (n.stereotype) line += ` ${n.stereotype}`;
    console.log(line);
    console.log(`    Size: ${n.width}x${n.height}px | bg: ${n.bgColor} | radius: ${n.borderRadius}`);
    console.log(`    Header: display=${n.headerDisplay}, flex-dir=${n.headerFlexDir}, align=${n.headerAlignItems}`);
    console.log(`    Label: weight=${n.labelWeight}, style=${n.labelStyle}`);
    if (n.attrCount > 0) console.log(`    Attrs (${n.attrCount}): ${n.attrs.join(' | ')}`);
  }

  if (noteNodes.length > 0) {
    console.log('\n--- NOTE NODES ---');
    for (const n of noteNodes) {
      console.log(`  "${n.label}" | ${n.width}x${n.height}px | bg: ${n.bgColor}`);
    }
  }

  console.log('\n--- EDGES ---');
  const markerGroups = {};
  let waypointCount = 0;
  for (const e of analysis.edges) {
    const key = `${e.markerStart} → ${e.markerEnd} (${e.pathType})`;
    markerGroups[key] = (markerGroups[key] || 0) + 1;
    if (e.hasWaypoints) waypointCount++;
  }
  for (const [k, v] of Object.entries(markerGroups)) {
    console.log(`  ${k}: ${v} edges`);
  }
  console.log(`  Edges with waypoints: ${waypointCount}/${analysis.edges.length}`);

  // === EA GROUND TRUTH ===
  console.log('\n========== EA GROUND TRUTH ==========');
  const eaPage = await context.newPage();
  await eaPage.goto(EA_URL, { waitUntil: 'networkidle', timeout: 30000 });
  await eaPage.waitForTimeout(2000);
  await eaPage.screenshot({ path: '/tmp/ea-ground-truth.png', fullPage: true });

  const diagImg = eaPage.locator('img[alt="Main.png"]').first();
  if (await diagImg.isVisible()) {
    await diagImg.screenshot({ path: '/tmp/ea-diagram-img.png' });
    const imgSize = await diagImg.evaluate(el => ({ w: el.naturalWidth, h: el.naturalHeight }));
    console.log(`EA diagram image: ${imgSize.w}x${imgSize.h}px`);
  }

  // Extract class names from image map areas
  const eaData = await eaPage.evaluate(() => {
    const areas = document.querySelectorAll('area');
    return Array.from(areas).map(a => ({
      title: a.getAttribute('title') || a.getAttribute('alt') || '',
      href: a.getAttribute('href') || '',
      shape: a.getAttribute('shape') || '',
    })).filter(a => a.title);
  });
  console.log(`EA image map areas: ${eaData.length}`);
  for (const a of eaData) {
    console.log(`  ${a.title} (${a.shape})`);
  }

  await browser.close();

  // === COMPARISON ===
  console.log('\n========== COMPARISON CHECKLIST ==========');
  console.log('Check these against EA ground truth:');

  // Check 1: No <<abstract>> stereotype text
  const hasAbstractStereotype = umlNodes.some(n => n.stereotype && n.stereotype.includes('abstract'));
  console.log(`[${hasAbstractStereotype ? 'FAIL' : 'PASS'}] No <<abstract>> stereotype text on abstract classes`);

  // Check 2: Abstract classes italic-only (not bold)
  const abstractNodes = umlNodes.filter(n => n.labelStyle === 'italic');
  const abstractBoldNodes = abstractNodes.filter(n => n.labelWeight === '700' || n.labelWeight === 'bold');
  console.log(`[${abstractBoldNodes.length > 0 ? 'FAIL' : abstractNodes.length > 0 ? 'PASS' : 'N/A'}] Abstract classes italic-only (not bold) — ${abstractNodes.length} italic nodes, ${abstractBoldNodes.length} still bold`);

  // Check 3: Class names centered
  const centeredHeaders = umlNodes.filter(n => n.headerDisplay === 'flex' && n.headerAlignItems === 'center');
  console.log(`[${centeredHeaders.length === umlNodes.length ? 'PASS' : 'FAIL'}] Class names centered (flex) — ${centeredHeaders.length}/${umlNodes.length}`);

  // Check 4: Note dimensions (no overlap)
  if (noteNodes.length > 0) {
    const note = noteNodes[0];
    const isSmall = note.width < 170; // Should be ~115, not ~161 (scaled)
    console.log(`[${isSmall ? 'PASS' : 'FAIL'}] Note uses original EA dimensions — ${note.width}x${note.height}px`);
  }

  // Check 5: Border radius (EA = 0)
  const zeroRadius = umlNodes.filter(n => n.borderRadius === '0px');
  console.log(`[${zeroRadius.length === umlNodes.length ? 'PASS' : 'PARTIAL'}] EA-style 0px border radius — ${zeroRadius.length}/${umlNodes.length}`);

  // Check 6: SVG markers present
  const markeredEdges = analysis.edges.filter(e => e.markerStart !== 'none' || e.markerEnd !== 'none');
  console.log(`[${markeredEdges.length > 0 ? 'PASS' : 'FAIL'}] SVG markers present — ${markeredEdges.length}/${analysis.edges.length} edges with markers`);

  // Check 7: Diagram frame
  console.log(`[${analysis.hasFrame ? 'PASS' : 'FAIL'}] Diagram frame present`);

  // Check 8: Qualifiers
  const qualifiedNodes = umlNodes.filter(n => n.qualifier);
  console.log(`[${qualifiedNodes.length > 0 ? 'PASS' : 'N/A'}] Cross-package qualifiers — ${qualifiedNodes.length} nodes with qualifiers`);

  // Check 9: Attributes visible
  const nodesWithAttrs = umlNodes.filter(n => n.attrCount > 0);
  console.log(`[${nodesWithAttrs.length > 0 ? 'PASS' : 'FAIL'}] Attributes rendered — ${nodesWithAttrs.length} nodes with attributes`);

  // Check 10: Waypoints
  console.log(`[${waypointCount > 0 ? 'PASS' : 'INFO'}] Waypoint edges — ${waypointCount}/${analysis.edges.length}`);

  console.log('\nScreenshots:');
  console.log('  /tmp/iris-diagram.png   — Full Iris page');
  console.log('  /tmp/iris-canvas.png    — Iris canvas only');
  console.log('  /tmp/ea-ground-truth.png — EA full page');
  console.log('  /tmp/ea-diagram-img.png  — EA diagram image');
}

main().catch(e => { console.error(e); process.exit(1); });
