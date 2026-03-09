/**
 * Detailed data extraction from the Iris canvas for comparison.
 */
import { chromium } from '@playwright/test';

const IRIS_URL = 'http://localhost:5173/diagrams/23835ff6-6a8f-4494-803c-24ca5d5c288b';

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1800, height: 1400 } });

  // Login
  await page.goto('http://localhost:5173/login');
  await page.waitForLoadState('networkidle');
  await page.fill('input[name="username"], input[type="text"]', 'admin');
  await page.fill('input[name="password"], input[type="password"]', 'AdminPass123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  await page.goto(IRIS_URL);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(4000);

  // Extract raw node/edge data from SvelteFlow store via window
  const data = await page.evaluate(() => {
    // Scrape all node DOM elements
    const nodes = [];
    document.querySelectorAll('.svelte-flow__node').forEach(el => {
      const transform = el.style.transform;
      const label = el.querySelector('.uml-node__label')?.textContent?.trim()
        || el.querySelector('.note-node__label')?.textContent?.trim()
        || el.querySelector('text')?.textContent?.trim()
        || 'unknown';
      const nodeType = el.classList.toString();
      const attrs = Array.from(el.querySelectorAll('.uml-node__attr')).map(a => a.textContent?.trim());
      const stereotype = el.querySelector('.uml-node__stereotype')?.textContent?.trim();
      const compartments = el.querySelectorAll('.uml-node__compartment').length;
      const overflowHidden = getComputedStyle(el.querySelector('.uml-node') || el).overflow;
      const umlNode = el.querySelector('.uml-node');

      nodes.push({
        label,
        transform,
        classes: nodeType.substring(0, 120),
        attrs,
        stereotype,
        compartments,
        scrollH: umlNode?.scrollHeight,
        clientH: umlNode?.clientHeight,
        overflow: umlNode ? getComputedStyle(umlNode).overflow : 'n/a',
        computedWidth: umlNode ? getComputedStyle(umlNode).width : 'n/a',
        computedHeight: umlNode ? getComputedStyle(umlNode).height : 'n/a',
        inlineStyle: umlNode?.style.cssText?.substring(0, 200),
      });
    });

    // Scrape edge labels
    const edgeLabels = [];
    document.querySelectorAll('.edge-endpoint-label').forEach(el => {
      const rect = el.getBoundingClientRect();
      edgeLabels.push({
        text: el.textContent?.trim(),
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        isRole: el.classList.contains('edge-endpoint-label--role'),
      });
    });

    // Scrape edge paths
    const edges = [];
    document.querySelectorAll('.svelte-flow__edge').forEach(el => {
      const path = el.querySelector('path')?.getAttribute('d')?.substring(0, 80);
      const markers = {
        start: el.querySelector('path')?.getAttribute('marker-start')?.substring(0, 50),
        end: el.querySelector('path')?.getAttribute('marker-end')?.substring(0, 50),
      };
      edges.push({ classes: el.className.baseVal?.substring(0, 100), path, markers });
    });

    // Check diagram frame
    const frameEl = document.querySelector('.diagram-frame-node');
    const frameSvg = frameEl?.querySelector('svg');
    const frameInfo = frameEl ? {
      visible: frameEl.offsetWidth > 0,
      width: frameEl.offsetWidth,
      height: frameEl.offsetHeight,
      svgWidth: frameSvg?.getAttribute('width'),
      svgHeight: frameSvg?.getAttribute('height'),
      text: frameEl.querySelector('text')?.textContent?.trim(),
    } : null;

    return { nodes, edgeLabels, edges, frameInfo };
  });

  console.log('\n=== NODES ===');
  data.nodes.forEach(n => {
    console.log(`\n  ${n.label}`);
    console.log(`    stereotype: ${n.stereotype || 'none'}`);
    console.log(`    attrs: [${n.attrs.join(', ')}]`);
    console.log(`    compartments: ${n.compartments}`);
    console.log(`    scroll/client: ${n.scrollH}/${n.clientH} overflow: ${n.overflow}`);
    console.log(`    computed size: ${n.computedWidth} x ${n.computedHeight}`);
    console.log(`    inline style: ${n.inlineStyle}`);
  });

  console.log('\n=== EDGE LABELS ===');
  data.edgeLabels.forEach(l => {
    console.log(`  "${l.text}" at (${l.x},${l.y}) role=${l.isRole}`);
  });

  console.log('\n=== EDGES ===');
  data.edges.forEach((e, i) => {
    console.log(`  Edge ${i}: markers=[start:${e.markers.start}, end:${e.markers.end}]`);
    console.log(`    path: ${e.path}`);
  });

  console.log('\n=== DIAGRAM FRAME ===');
  console.log(JSON.stringify(data.frameInfo, null, 2));

  // Also fetch the raw diagram data from the API
  const cookies = await page.context().cookies();
  const tokenCookie = cookies.find(c => c.name === 'token' || c.name === 'access_token');

  const apiData = await page.evaluate(async () => {
    const resp = await fetch('/api/diagrams/23835ff6-6a8f-4494-803c-24ca5d5c288b');
    return resp.json();
  });

  console.log('\n=== RAW API EDGE DATA ===');
  const rawEdges = apiData.data?.edges || [];
  rawEdges.forEach(e => {
    console.log(`  ${e.type}: ${e.source.substring(0,8)}→${e.target.substring(0,8)} sh=${e.sourceHandle} th=${e.targetHandle}`);
    if (e.data) {
      const d = e.data;
      console.log(`    sourceCard: ${d.sourceCardinality || '-'} targetCard: ${d.targetCardinality || '-'}`);
      console.log(`    sourceRole: ${d.sourceRole || '-'} targetRole: ${d.targetRole || '-'}`);
      if (d.labelPositions) console.log(`    labelPositions: ${JSON.stringify(d.labelPositions)}`);
    }
  });

  console.log('\n=== RAW API NODE DATA (sizes) ===');
  const rawNodes = apiData.data?.nodes || [];
  rawNodes.forEach(n => {
    const d = n.data;
    const vis = d?.visual || {};
    console.log(`  ${(d?.label || n.type).padEnd(30)} type=${n.type} w=${vis.width||'-'} h=${vis.height||'-'} pos=(${n.position?.x},${n.position?.y})`);
  });

  await browser.close();
}

run().catch(e => { console.error(e); process.exit(1); });
