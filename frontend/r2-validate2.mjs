/**
 * R2 Validation v2: Better captures for comparison.
 */
import { chromium } from '@playwright/test';

const IRIS_URL = 'http://localhost:5173/diagrams/23835ff6-6a8f-4494-803c-24ca5d5c288b';
const GROUND_TRUTH_URL = 'https://aixm.aero/sites/default/files/imce/AIXM511HTML/AIXM/Diagram_Main.html?menu=open';

async function run() {
  const browser = await chromium.launch();

  // --- Capture ground truth (the diagram image) ---
  const gtPage = await browser.newPage({ viewport: { width: 1800, height: 1400 } });
  await gtPage.goto(GROUND_TRUTH_URL, { waitUntil: 'networkidle', timeout: 30000 });
  await gtPage.waitForTimeout(3000);

  // Get the actual diagram image (it's a large base64 PNG)
  const imgSrc = await gtPage.evaluate(() => {
    const imgs = document.querySelectorAll('img');
    for (const img of imgs) {
      if (img.naturalWidth > 200) return img.src.substring(0, 100) + '... (width=' + img.naturalWidth + ', height=' + img.naturalHeight + ')';
    }
    return 'no large image found';
  });
  console.log('Ground truth image info:', imgSrc);

  // Screenshot the full page content area
  await gtPage.screenshot({ path: '/tmp/ground-truth-full.png', fullPage: true });

  // Try to find and screenshot just the diagram area
  const diagramImg = await gtPage.$('img[usemap], img:not([src*="logo"])');
  if (diagramImg) {
    const box = await diagramImg.boundingBox();
    console.log('Diagram image bounding box:', box);
    if (box && box.width > 200) {
      await diagramImg.screenshot({ path: '/tmp/ground-truth-diagram.png' });
      console.log('Ground truth diagram saved to /tmp/ground-truth-diagram.png');
    }
  }

  // --- Capture Iris diagram ---
  const irisPage = await browser.newPage({ viewport: { width: 1800, height: 1400 } });

  // Login
  await irisPage.goto('http://localhost:5173/login');
  await irisPage.waitForLoadState('networkidle');
  await irisPage.fill('input[name="username"], input[type="text"]', 'admin');
  await irisPage.fill('input[name="password"], input[type="password"]', 'AdminPass123!');
  await irisPage.click('button[type="submit"]');
  await irisPage.waitForTimeout(2000);

  // Navigate to diagram
  await irisPage.goto(IRIS_URL);
  await irisPage.waitForLoadState('networkidle');
  await irisPage.waitForTimeout(4000);

  // Full page screenshot first
  await irisPage.screenshot({ path: '/tmp/iris-full.png', fullPage: false });

  // Now zoom into the canvas area for detail
  const canvasEl = await irisPage.$('.svelte-flow');
  if (canvasEl) {
    await canvasEl.screenshot({ path: '/tmp/iris-canvas.png' });
    console.log('Iris canvas saved to /tmp/iris-canvas.png');
  }

  // Get node data for analysis
  const nodeInfo = await irisPage.evaluate(() => {
    const nodes = document.querySelectorAll('.svelte-flow__node');
    return Array.from(nodes).map(n => {
      const rect = n.getBoundingClientRect();
      const label = n.querySelector('.uml-node__label, .note-node__label, text')?.textContent?.trim() || n.getAttribute('data-id') || 'unknown';
      const type = n.getAttribute('data-type') || 'unknown';
      return {
        label: label.substring(0, 40),
        type,
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        w: Math.round(rect.width),
        h: Math.round(rect.height),
      };
    });
  });
  console.log('\n=== IRIS NODE LAYOUT ===');
  nodeInfo.forEach(n => console.log(`  ${n.type.padEnd(16)} ${n.label.padEnd(35)} pos=(${n.x},${n.y}) size=${n.w}x${n.h}`));

  // Get edge info
  const edgeInfo = await irisPage.evaluate(() => {
    const edges = document.querySelectorAll('.svelte-flow__edge');
    return Array.from(edges).map(e => {
      const labels = e.querySelectorAll('.edge-endpoint-label');
      const labelTexts = Array.from(labels).map(l => l.textContent?.trim());
      const type = e.getAttribute('data-type') || 'unknown';
      return { type, labels: labelTexts };
    });
  });
  console.log('\n=== IRIS EDGES ===');
  edgeInfo.forEach(e => console.log(`  ${e.type.padEnd(16)} labels: [${e.labels.join(', ')}]`));

  // Check for diagram frame
  const frameNode = await irisPage.$('[data-type="diagram_frame"], .diagram-frame-node');
  console.log('\n=== DIAGRAM FRAME ===');
  console.log('  Frame node present:', !!frameNode);
  if (frameNode) {
    const box = await frameNode.boundingBox();
    console.log('  Frame bounding box:', box);
  }

  // Check note node
  const noteNodes = await irisPage.$$('[data-type="note"]');
  console.log('\n=== NOTE NODES ===');
  for (const n of noteNodes) {
    const text = await n.evaluate(el => el.textContent?.trim().substring(0, 100));
    console.log('  Note:', text);
  }

  // Check for clipped content in class nodes
  const clippedInfo = await irisPage.evaluate(() => {
    const results = [];
    document.querySelectorAll('.uml-node').forEach(node => {
      const label = node.querySelector('.uml-node__label')?.textContent?.trim() || 'unknown';
      const scrollH = node.scrollHeight;
      const clientH = node.clientHeight;
      const attrs = node.querySelectorAll('.uml-node__attr');
      if (scrollH > clientH + 2) {
        results.push({ label, scrollH, clientH, attrCount: attrs.length, clipped: true });
      } else {
        results.push({ label, scrollH, clientH, attrCount: attrs.length, clipped: false });
      }
    });
    return results;
  });
  console.log('\n=== CLIPPING CHECK ===');
  clippedInfo.forEach(c => console.log(`  ${c.label.padEnd(35)} scroll=${c.scrollH} client=${c.clientH} attrs=${c.attrCount} ${c.clipped ? 'CLIPPED!' : 'ok'}`));

  await browser.close();
}

run().catch(e => { console.error(e); process.exit(1); });
