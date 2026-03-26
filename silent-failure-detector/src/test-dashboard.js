const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const SCREENSHOTS_DIR = path.join(__dirname, '..', 'screenshots');
fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

async function testDashboard() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  console.log('[Test] Opening dashboard...');
  await page.goto('http://localhost:3456/dashboard');
  await page.waitForTimeout(500);

  // Screenshot 1: Empty state
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '01-empty-state.png'), fullPage: true });
  console.log('[Test] Screenshot: 01-empty-state.png');

  // Click "Run Demo" button
  console.log('[Test] Clicking "Run Demo"...');
  await page.click('text=Run Demo');
  await page.waitForTimeout(1000);

  // Screenshot 2: After demo run
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '02-failures-detected.png'), fullPage: true });
  console.log('[Test] Screenshot: 02-failures-detected.png');

  // Verify failure count is displayed
  const totalBadge = await page.textContent('#totalBadge');
  console.log(`[Test] Total failures shown: ${totalBadge}`);
  if (parseInt(totalBadge) >= 3) {
    console.log('[Test] PASS: Failures detected and shown');
  } else {
    console.log('[Test] FAIL: Expected >= 3 failures');
  }

  // Click "Endpoint Stats" tab
  await page.click('text=Endpoint Stats');
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '03-endpoint-stats.png'), fullPage: true });
  console.log('[Test] Screenshot: 03-endpoint-stats.png');

  // Click "Rules" tab
  await page.click('text=Rules');
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, '04-rules.png'), fullPage: true });
  console.log('[Test] Screenshot: 04-rules.png');

  // Verify rules are shown
  const rulesText = await page.textContent('#rulesTable');
  if (rulesText.includes('order-db-write') && rulesText.includes('payment-processing')) {
    console.log('[Test] PASS: Rules displayed correctly');
  } else {
    console.log('[Test] FAIL: Rules not displayed');
  }

  await browser.close();
  console.log('[Test] Dashboard test complete');
}

testDashboard().catch(err => {
  console.error('[Test] Failed:', err.message);
  process.exit(1);
});
