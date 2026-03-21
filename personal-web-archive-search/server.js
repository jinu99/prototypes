const http = require('http');
const fs = require('fs');
const path = require('path');
const { openDb, initDb, addPage, search, listPages, getPageCount } = require('./db');
const { extractFromUrl } = require('./extractor');

const PORT = process.env.PORT || 3777;

const db = openDb();
initDb(db);

const indexHtml = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf-8');

function jsonResponse(res, statusCode, data) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try { resolve(JSON.parse(body)); }
      catch (e) { reject(e); }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  // Serve UI
  if (req.method === 'GET' && url.pathname === '/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(indexHtml);
    return;
  }

  // Search API
  if (req.method === 'GET' && url.pathname === '/api/search') {
    const q = url.searchParams.get('q');
    if (!q || q.length < 2) {
      return jsonResponse(res, 400, { error: 'Query must be at least 2 characters' });
    }
    try {
      const results = search(db, q);
      jsonResponse(res, 200, { results, query: q });
    } catch (err) {
      jsonResponse(res, 500, { error: err.message });
    }
    return;
  }

  // Add URL API
  if (req.method === 'POST' && url.pathname === '/api/add') {
    try {
      const { url: pageUrl } = await parseBody(req);
      if (!pageUrl) {
        return jsonResponse(res, 400, { error: 'url is required' });
      }
      const article = await extractFromUrl(pageUrl);
      addPage(db, article);
      jsonResponse(res, 200, {
        success: true,
        title: article.title,
        lang: article.lang,
        contentLength: article.content.length,
      });
    } catch (err) {
      jsonResponse(res, 500, { error: err.message });
    }
    return;
  }

  // List pages API
  if (req.method === 'GET' && url.pathname === '/api/pages') {
    const pages = listPages(db);
    jsonResponse(res, 200, { pages, total: pages.length });
    return;
  }

  // Stats API
  if (req.method === 'GET' && url.pathname === '/api/stats') {
    const count = getPageCount(db);
    jsonResponse(res, 200, { total: count });
    return;
  }

  res.writeHead(404);
  res.end('Not Found');
});

server.listen(PORT, () => {
  console.log(`Web Archive Search running at http://localhost:${PORT}`);
});
