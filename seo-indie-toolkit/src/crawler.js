const { chromium } = require('playwright');
const https = require('https');
const http = require('http');

/**
 * raw HTML을 HTTP GET으로 가져온다 (JS 실행 전)
 */
function fetchRawHtml(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client.get(url, { headers: { 'User-Agent': 'Googlebot/2.1' } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return fetchRawHtml(res.headers.location).then(resolve).catch(reject);
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
    }).on('error', reject);
  });
}

/**
 * Playwright로 JS 실행 후 렌더링된 HTML을 가져온다
 */
async function fetchRenderedHtml(url, browser) {
  const page = await browser.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    // JS가 SEO 태그를 설정할 시간을 준다
    await page.waitForTimeout(3000);
    const html = await page.content();
    return html;
  } finally {
    await page.close();
  }
}

/**
 * 단일 URL에 대해 raw/rendered HTML 쌍을 반환
 */
async function crawlUrl(url, browser) {
  const [rawHtml, renderedHtml] = await Promise.all([
    fetchRawHtml(url),
    fetchRenderedHtml(url, browser),
  ]);
  return { url, rawHtml, renderedHtml };
}

/**
 * 브라우저 인스턴스 생성
 */
async function launchBrowser() {
  return chromium.launch({ headless: true });
}

module.exports = { fetchRawHtml, fetchRenderedHtml, crawlUrl, launchBrowser };
