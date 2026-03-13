const http = require('http');
const fs = require('fs');
const path = require('path');
const { createDb } = require('./db');
const { setupRoutes } = require('./routes');
const { addClient } = require('./sse');

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, 'public');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.webmanifest': 'application/manifest+json',
};

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        reject(new Error('잘못된 JSON 형식'));
      }
    });
    req.on('error', reject);
  });
}

function sendJson(res, obj, statusCode = 200) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(obj));
}

function serveStatic(req, res) {
  let filePath = path.join(PUBLIC_DIR, req.url === '/' ? 'index.html' : req.url);
  // Prevent directory traversal
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }
  const ext = path.extname(filePath);
  const mime = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, data) => {
    if (err) {
      // Try appending .html
      if (!ext) {
        fs.readFile(filePath + '.html', (err2, data2) => {
          if (err2) { res.writeHead(404); res.end('Not Found'); return; }
          res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
          res.end(data2);
        });
        return;
      }
      res.writeHead(404);
      res.end('Not Found');
      return;
    }
    res.writeHead(200, { 'Content-Type': mime });
    res.end(data);
  });
}

function start() {
  const db = createDb();
  const routes = setupRoutes(db);

  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const pathname = url.pathname;

    // API routes
    if (pathname === '/api/events' && req.method === 'GET') {
      addClient(res);
      return;
    }

    if (pathname === '/api/queue' && req.method === 'POST') {
      try {
        const body = await parseBody(req);
        const result = routes.addToQueue(body);
        sendJson(res, result.error ? { error: result.error } : result.data, result.status);
      } catch (e) {
        sendJson(res, { error: e.message }, 400);
      }
      return;
    }

    if (pathname === '/api/queue' && req.method === 'GET') {
      const result = routes.listQueue();
      sendJson(res, result.data, result.status);
      return;
    }

    if (pathname === '/api/queue/all' && req.method === 'GET') {
      const result = routes.listAll();
      sendJson(res, result.data, result.status);
      return;
    }

    const statusMatch = pathname.match(/^\/api\/queue\/(\d+)\/status$/);
    if (statusMatch && req.method === 'PATCH') {
      try {
        const body = await parseBody(req);
        const result = routes.updateStatus(parseInt(statusMatch[1]), body);
        sendJson(res, result.error ? { error: result.error } : result.data, result.status);
      } catch (e) {
        sendJson(res, { error: e.message }, 400);
      }
      return;
    }

    const entryMatch = pathname.match(/^\/api\/queue\/(\d+)$/);
    if (entryMatch && req.method === 'GET') {
      const result = routes.getEntry(parseInt(entryMatch[1]));
      sendJson(res, result.error ? { error: result.error } : result.data, result.status);
      return;
    }

    if (pathname === '/api/qrcode' && req.method === 'GET') {
      const targetUrl = url.searchParams.get('url') || `http://${req.headers.host}/join`;
      const result = await routes.generateQR(targetUrl);
      sendJson(res, result.error ? { error: result.error } : result.data, result.status);
      return;
    }

    // Static files
    serveStatic(req, res);
  });

  server.listen(PORT, () => {
    console.log(`🏪 Small Biz Queue Ops running at http://localhost:${PORT}`);
    console.log(`   고객 등록: http://localhost:${PORT}/join`);
    console.log(`   매장 관리: http://localhost:${PORT}/admin`);
    console.log(`   KDS 뷰:   http://localhost:${PORT}/kds`);
  });
}

start();
