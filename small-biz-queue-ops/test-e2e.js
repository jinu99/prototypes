const { chromium } = require('playwright');
const path = require('path');

const BASE = 'http://localhost:3100';
const SCREENSHOTS = path.join(__dirname, 'screenshots');

async function run() {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || undefined,
  });
  const context = await browser.newContext({ viewport: { width: 430, height: 932 } });

  try {
    // 1. Home page with QR
    console.log('1. Home page...');
    const home = await context.newPage();
    await home.goto(BASE);
    await home.waitForSelector('#qr-img[src]', { timeout: 5000 });
    await home.screenshot({ path: path.join(SCREENSHOTS, '01-home.png'), fullPage: true });
    console.log('   ✓ Home captured');

    // 2. Customer join page
    console.log('2. Join page...');
    const join = await context.newPage();
    await join.goto(BASE + '/join');
    await join.screenshot({ path: path.join(SCREENSHOTS, '02-join-form.png'), fullPage: true });

    // Fill form and submit
    await join.fill('#name', '김철수');
    await join.fill('#party_size', '4');
    await join.click('button[type="submit"]');
    await join.waitForSelector('#wait-section:not([style*="display: none"])', { timeout: 5000 });
    await join.screenshot({ path: path.join(SCREENSHOTS, '03-join-waiting.png'), fullPage: true });
    console.log('   ✓ Join + waiting captured');

    // Register more customers
    const join2 = await context.newPage();
    await join2.goto(BASE + '/join');
    await join2.fill('#name', '이영희');
    await join2.fill('#party_size', '2');
    await join2.click('button[type="submit"]');
    await join2.waitForSelector('#wait-section:not([style*="display: none"])', { timeout: 5000 });

    const join3 = await context.newPage();
    await join3.goto(BASE + '/join');
    await join3.fill('#name', '박지민');
    await join3.fill('#party_size', '5');
    await join3.click('button[type="submit"]');
    await join3.waitForSelector('#wait-section:not([style*="display: none"])', { timeout: 5000 });
    console.log('   ✓ 3 customers registered');

    // 3. Admin page
    console.log('3. Admin page...');
    const admin = await context.newPage();
    await admin.goto(BASE + '/admin');
    await admin.waitForSelector('.card strong', { timeout: 5000 });
    await admin.screenshot({ path: path.join(SCREENSHOTS, '04-admin-list.png'), fullPage: true });

    // Click "호출" on first customer
    const callBtn = admin.locator('.btn-warning').first();
    await callBtn.click();
    await admin.waitForTimeout(500);
    await admin.screenshot({ path: path.join(SCREENSHOTS, '05-admin-called.png'), fullPage: true });
    console.log('   ✓ Admin + call action captured');

    // Check customer page shows "호출" message
    await join.reload();
    await join.waitForTimeout(1000);
    // Re-register since DB was reset; let's check admin view instead

    // 4. KDS page
    console.log('4. KDS page...');
    const kds = await context.newPage();
    await kds.goto(BASE + '/kds');
    await kds.waitForSelector('.kds-card', { timeout: 5000 });
    await kds.screenshot({ path: path.join(SCREENSHOTS, '06-kds.png'), fullPage: true });
    console.log('   ✓ KDS captured');

    // 5. Continue status flow: seated, completed
    const seatBtn = admin.locator('.btn-success').first();
    if (await seatBtn.count()) {
      await seatBtn.click();
      await admin.waitForTimeout(500);
    }
    await admin.screenshot({ path: path.join(SCREENSHOTS, '07-admin-seated.png'), fullPage: true });

    const completeBtn = admin.locator('.btn-danger').first();
    if (await completeBtn.count()) {
      await completeBtn.click();
      await admin.waitForTimeout(500);
    }
    await admin.screenshot({ path: path.join(SCREENSHOTS, '08-admin-completed.png'), fullPage: true });
    console.log('   ✓ Full status flow captured');

    // Home page after all changes
    await home.reload();
    await home.waitForTimeout(1000);
    await home.screenshot({ path: path.join(SCREENSHOTS, '09-home-updated.png'), fullPage: true });
    console.log('   ✓ Home updated captured');

    console.log('\n✅ All screenshots saved to screenshots/');
  } finally {
    await browser.close();
  }
}

run().catch(err => {
  console.error('E2E test failed:', err.message);
  process.exit(1);
});
