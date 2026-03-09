import { chromium } from '@playwright/test';

async function run() {
  const browser = await chromium.launch();

  // Ground truth
  const gtPage = await browser.newPage({ viewport: { width: 1800, height: 1400 } });
  await gtPage.goto('https://aixm.aero/sites/default/files/imce/AIXM511HTML/AIXM_v.5.1.1/Diagram_AIXM_v.5.1.1.html?menu=open', { waitUntil: 'networkidle', timeout: 30000 });
  await gtPage.waitForTimeout(2000);
  // Try to get the diagram image specifically
  const imgInfo = await gtPage.evaluate(() => {
    const imgs = document.querySelectorAll('img');
    return Array.from(imgs).map(i => ({ src: i.src.substring(0, 80), w: i.naturalWidth, h: i.naturalHeight }));
  });
  console.log('Ground truth images:', imgInfo);
  // Capture the largest image
  const bigImg = await gtPage.$('img:not([src*="logo"]):not([src*="pulsar"])');
  if (bigImg) {
    await bigImg.screenshot({ path: '/tmp/gt-diagram2.png' });
    console.log('Ground truth diagram 2 saved');
  } else {
    await gtPage.screenshot({ path: '/tmp/gt-diagram2.png', fullPage: true });
  }

  // Iris diagram
  const page = await browser.newPage({ viewport: { width: 1800, height: 1400 } });
  await page.goto('http://localhost:5173/login');
  await page.waitForLoadState('networkidle');
  await page.fill('input[name="username"], input[type="text"]', 'admin');
  await page.fill('input[name="password"], input[type="password"]', 'AdminPass123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  await page.goto('http://localhost:5173/diagrams/4ca5d195-3380-4f79-9a68-5c843d3b8aed');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);

  const canvas = await page.$('.svelte-flow');
  if (canvas) {
    await canvas.screenshot({ path: '/tmp/iris-diagram2.png' });
    console.log('Iris diagram 2 saved');
  }

  // Node details
  const nodeData = await page.evaluate(() => {
    const nodes = [];
    document.querySelectorAll('.svelte-flow__node').forEach(el => {
      const rect = el.getBoundingClientRect();
      const text = el.textContent?.trim()?.substring(0, 80);
      nodes.push({ text, x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) });
    });
    return nodes;
  });
  console.log('\n=== IRIS DIAGRAM 2 NODES ===');
  nodeData.forEach(n => console.log(`  "${n.text}" pos=(${n.x},${n.y}) size=${n.w}x${n.h}`));

  await browser.close();
}

run().catch(e => { console.error(e); process.exit(1); });
