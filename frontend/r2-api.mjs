import { chromium } from '@playwright/test';

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Login
  await page.goto('http://localhost:5173/login');
  await page.waitForLoadState('networkidle');
  await page.fill('input[name="username"], input[type="text"]', 'admin');
  await page.fill('input[name="password"], input[type="password"]', 'AdminPass123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  // Fetch diagram API
  const apiData = await page.evaluate(async () => {
    const resp = await fetch('/api/diagrams/23835ff6-6a8f-4494-803c-24ca5d5c288b');
    const json = await resp.json();
    return { keys: Object.keys(json), dataKeys: json.data ? Object.keys(json.data) : null, sample: JSON.stringify(json).substring(0, 500) };
  });
  console.log('API response keys:', apiData.keys);
  console.log('Data keys:', apiData.dataKeys);
  console.log('Sample:', apiData.sample);

  // Get canvas data
  const canvasData = await page.evaluate(async () => {
    const resp = await fetch('/api/diagrams/23835ff6-6a8f-4494-803c-24ca5d5c288b/canvas');
    if (!resp.ok) return { status: resp.status, text: await resp.text().then(t => t.substring(0, 200)) };
    const json = await resp.json();
    return { keys: Object.keys(json), edgeCount: json.edges?.length, nodeCount: json.nodes?.length, sample: JSON.stringify(json).substring(0, 500) };
  });
  console.log('\nCanvas data:', canvasData);

  // Try the actual diagram endpoint for canvas nodes/edges
  const diagramFull = await page.evaluate(async () => {
    const resp = await fetch('/api/diagrams/23835ff6-6a8f-4494-803c-24ca5d5c288b');
    const json = await resp.json();
    const edges = json.canvas_data?.edges || json.data?.edges || [];
    const nodes = json.canvas_data?.nodes || json.data?.nodes || [];
    return {
      edgeCount: edges.length,
      nodeCount: nodes.length,
      edgeSample: edges.slice(0, 2),
      nodeSample: nodes.slice(0, 2).map(n => ({ type: n.type, label: n.data?.label, pos: n.position, w: n.data?.visual?.width, h: n.data?.visual?.height })),
      allKeys: JSON.stringify(Object.keys(json)),
    };
  });
  console.log('\nDiagram full:', JSON.stringify(diagramFull, null, 2));

  await browser.close();
}

run().catch(e => { console.error(e); process.exit(1); });
