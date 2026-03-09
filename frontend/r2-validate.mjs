/**
 * R2 Validation: Capture Iris rendering + EA ground truth for visual comparison.
 */
import { chromium } from '@playwright/test';
import { readFileSync, writeFileSync } from 'fs';

const IRIS_URL = 'http://localhost:5173/diagrams/23835ff6-6a8f-4494-803c-24ca5d5c288b';
const GROUND_TRUTH_URL = 'https://aixm.aero/sites/default/files/imce/AIXM511HTML/AIXM/Diagram_Main.html?menu=open';

async function run() {
  const browser = await chromium.launch();

  // --- Capture Iris diagram ---
  const irisPage = await browser.newPage({ viewport: { width: 1600, height: 1200 } });

  // Login first
  await irisPage.goto('http://localhost:5173/login');
  await irisPage.waitForLoadState('networkidle');
  await irisPage.fill('input[name="username"], input[type="text"]', 'admin');
  await irisPage.fill('input[name="password"], input[type="password"]', 'AdminPass123!');
  await irisPage.click('button[type="submit"]');
  await irisPage.waitForURL('**/diagrams**', { timeout: 10000 }).catch(() => {});
  await irisPage.waitForTimeout(1000);

  // Navigate to diagram
  await irisPage.goto(IRIS_URL);
  await irisPage.waitForLoadState('networkidle');
  await irisPage.waitForTimeout(3000); // Let canvas render

  // Try to fit view
  try {
    // Look for fit view button
    const fitBtn = await irisPage.$('[aria-label="fit view"], button:has-text("Fit"), .svelte-flow__controls button:first-child');
    if (fitBtn) await fitBtn.click();
    await irisPage.waitForTimeout(1000);
  } catch(e) {}

  await irisPage.screenshot({ path: '/tmp/iris-diagram.png', fullPage: false });
  console.log('Iris screenshot saved to /tmp/iris-diagram.png');

  // --- Capture ground truth ---
  const gtPage = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
  await gtPage.goto(GROUND_TRUTH_URL, { waitUntil: 'networkidle', timeout: 30000 });
  await gtPage.waitForTimeout(2000);

  // The diagram is an image - try to get just the image
  const imgEl = await gtPage.$('img');
  if (imgEl) {
    await imgEl.screenshot({ path: '/tmp/ground-truth.png' });
    console.log('Ground truth screenshot saved to /tmp/ground-truth.png');
  } else {
    await gtPage.screenshot({ path: '/tmp/ground-truth.png', fullPage: true });
    console.log('Ground truth full page screenshot saved to /tmp/ground-truth.png');
  }

  await browser.close();
  console.log('\nCompare: /tmp/iris-diagram.png vs /tmp/ground-truth.png');
}

run().catch(e => { console.error(e); process.exit(1); });
