const { setupBrowserEnv } = require('./browser-env');
setupBrowserEnv();

const http = require('http');
const fs = require('fs');
const path = require('path');
const { crawlUrl, launchBrowser } = require('./crawler');
const { analyze } = require('./analyzer');
const { generateJsonReport } = require('./reporter');
const { fetchSitemap } = require('./sitemap');

const PORT = process.env.PORT || 3000;

let browser = null;

async function ensureBrowser() {
  if (!browser || !browser.isConnected()) {
    browser = await launchBrowser();
  }
  return browser;
}

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data, null, 2));
}

function sendHtml(res, filePath) {
  const html = fs.readFileSync(filePath, 'utf-8');
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(html);
}

async function handleAnalyze(url, res) {
  try {
    const b = await ensureBrowser();
    const { rawHtml, renderedHtml } = await crawlUrl(url, b);
    const analysis = analyze(rawHtml, renderedHtml);
    const report = generateJsonReport(url, analysis);
    sendJson(res, 200, report);
  } catch (err) {
    sendJson(res, 500, { error: err.message });
  }
}

async function handleSitemap(sitemapUrl, limit, res) {
  try {
    let urls = await fetchSitemap(sitemapUrl);
    if (limit && limit < urls.length) {
      urls = urls.slice(0, limit);
    }

    const b = await ensureBrowser();
    const results = [];

    for (const url of urls) {
      try {
        const { rawHtml, renderedHtml } = await crawlUrl(url, b);
        const analysis = analyze(rawHtml, renderedHtml);
        results.push(generateJsonReport(url, analysis));
      } catch (err) {
        results.push({ url, error: err.message });
      }
    }

    sendJson(res, 200, { total: urls.length, results });
  } catch (err) {
    sendJson(res, 500, { error: err.message });
  }
}

const server = http.createServer(async (req, res) => {
  const parsed = new URL(req.url, `http://localhost:${PORT}`);

  if (parsed.pathname === '/' && req.method === 'GET') {
    sendHtml(res, path.join(__dirname, '..', 'public', 'index.html'));
    return;
  }

  if (parsed.pathname === '/api/analyze' && req.method === 'GET') {
    const url = parsed.searchParams.get('url');
    if (!url) {
      sendJson(res, 400, { error: 'url 파라미터가 필요합니다.' });
      return;
    }
    await handleAnalyze(url, res);
    return;
  }

  if (parsed.pathname === '/api/sitemap' && req.method === 'GET') {
    const url = parsed.searchParams.get('url');
    const limit = parseInt(parsed.searchParams.get('limit') || '0', 10) || undefined;
    if (!url) {
      sendJson(res, 400, { error: 'url 파라미터가 필요합니다.' });
      return;
    }
    await handleSitemap(url, limit, res);
    return;
  }

  res.writeHead(404);
  res.end('Not Found');
});

server.listen(PORT, () => {
  console.log(`🚀 SEO Indie Toolkit 서버가 시작되었습니다: http://localhost:${PORT}`);
});

process.on('SIGINT', async () => {
  if (browser) await browser.close();
  process.exit(0);
});
