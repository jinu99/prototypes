import puppeteer from 'puppeteer';

const BASE = 'http://localhost:8765';
const SCREENSHOTS = './screenshots';

async function getTextById(page, id) {
  const handle = await page.$('#' + id);
  if (!handle) return '';
  const text = await handle.evaluate(node => node.textContent);
  return text;
}

async function run() {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });

  const logs = [];
  page.on('console', msg => logs.push('[' + msg.type() + '] ' + msg.text()));
  page.on('pageerror', err => logs.push('[ERROR] ' + err.message));

  console.log('1. Loading page...');
  await page.goto(BASE + '/index.html', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: SCREENSHOTS + '/01-dashboard.png', fullPage: true });
  console.log('   Screenshot: 01-dashboard.png');

  console.log('2. Saving test data...');
  await page.click('#btn-save');
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: SCREENSHOTS + '/02-data-saved.png', fullPage: true });
  console.log('   Screenshot: 02-data-saved.png');

  console.log('3. Simulating storage loss...');
  await page.click('#btn-delete');
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: SCREENSHOTS + '/03-data-deleted.png', fullPage: true });
  console.log('   Screenshot: 03-data-deleted.png');

  console.log('4. Auto-recovering from OPFS...');
  await page.click('#btn-recover');
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: SCREENSHOTS + '/04-recovered.png', fullPage: true });
  console.log('   Screenshot: 04-recovered.png');

  // Verify results
  const errors = logs.filter(l => l.startsWith('[ERROR]'));
  if (errors.length > 0) {
    console.log('\nConsole errors:');
    errors.forEach(e => console.log('  ' + e));
  } else {
    console.log('\nNo console errors detected.');
  }

  const rows = await page.$$('#data-tbody tr');
  console.log('Data table rows after recovery: ' + rows.length);

  const overall = await getTextById(page, 'score-overall');
  const idb = await getTextById(page, 'score-idb');
  const opfs = await getTextById(page, 'score-opfs');
  const cache = await getTextById(page, 'score-cache');
  console.log('Scores — Overall: ' + overall + ', IDB: ' + idb + ', OPFS: ' + opfs + ', Cache: ' + cache);

  const strategy = await getTextById(page, 'strategy-info');
  console.log('Persist strategy: ' + strategy.substring(0, 100) + '...');

  const logEntries = await page.$$('.log-entry');
  console.log('Log entries: ' + logEntries.length);

  console.log('\nAll console messages:');
  logs.forEach(l => console.log('  ' + l));

  await browser.close();
  console.log('\nDone! Check screenshots/ directory.');
}

run().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
