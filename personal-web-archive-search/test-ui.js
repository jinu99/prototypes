const { chromium } = require('playwright');
const path = require('path');

const SCREENSHOTS = path.join(__dirname, 'screenshots');
const BASE_URL = 'http://localhost:3777';

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 800, height: 900 } });

  // 1. Home page
  await page.goto(BASE_URL);
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(SCREENSHOTS, '01-home.png') });
  console.log('✓ Screenshot: home page');

  // 2. Korean search
  await page.fill('#searchInput', '한국어');
  await page.click('.search-box button');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(SCREENSHOTS, '02-search-korean.png') });
  console.log('✓ Screenshot: Korean search results');

  // 3. English search
  await page.fill('#searchInput', 'javascript');
  await page.click('.search-box button');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(SCREENSHOTS, '03-search-english.png') });
  console.log('✓ Screenshot: English search results');

  // 4. Short Korean query (2 chars)
  await page.fill('#searchInput', '경제');
  await page.click('.search-box button');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(SCREENSHOTS, '04-search-short-korean.png') });
  console.log('✓ Screenshot: Short Korean query');

  // 5. Add URL via UI
  await page.fill('#urlInput', 'https://ko.wikipedia.org/wiki/%ED%8C%8C%EC%9D%B4%EC%8D%AC');
  await page.click('.add-section button');
  await page.waitForTimeout(5000);
  await page.screenshot({ path: path.join(SCREENSHOTS, '05-add-url.png') });
  console.log('✓ Screenshot: After adding URL');

  // 6. Search newly added content
  await page.fill('#searchInput', '파이썬');
  await page.click('.search-box button');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(SCREENSHOTS, '06-search-python.png') });
  console.log('✓ Screenshot: Python search');

  await browser.close();
  console.log('\nAll screenshots saved to screenshots/');
}

run().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
