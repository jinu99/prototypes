const http = require('http');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const DIR = __dirname;
const PORT = 9877;

// Simple static file server
const server = http.createServer((req, res) => {
  const filePath = path.join(DIR, req.url === '/' ? 'index.html' : req.url);
  const ext = path.extname(filePath);
  const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css' };
  try {
    const content = fs.readFileSync(filePath);
    res.writeHead(200, { 'Content-Type': types[ext] || 'text/plain' });
    res.end(content);
  } catch (e) {
    res.writeHead(404);
    res.end('Not found');
  }
});

async function run() {
  server.listen(PORT);
  console.log(`Server on http://localhost:${PORT}`);

  // Test 1: HTML loads correctly
  console.log('\n--- Test 1: HTML loads ---');
  const htmlRes = await fetch(`http://localhost:${PORT}/`);
  const html = await htmlRes.text();
  console.log(`  Status: ${htmlRes.status} — ${htmlRes.status === 200 ? 'PASS' : 'FAIL'}`);
  console.log(`  Contains session-guard.js: ${html.includes('session-guard.js') ? 'PASS' : 'FAIL'}`);
  console.log(`  Contains SessionGuard init: ${html.includes('new SessionGuard') ? 'PASS' : 'FAIL'}`);
  console.log(`  Contains leak simulator: ${html.includes('btn-leak-start') ? 'PASS' : 'FAIL'}`);

  // Test 2: JS library loads correctly
  console.log('\n--- Test 2: JS library loads ---');
  const jsRes = await fetch(`http://localhost:${PORT}/session-guard.js`);
  const js = await jsRes.text();
  console.log(`  Status: ${jsRes.status} — ${jsRes.status === 200 ? 'PASS' : 'FAIL'}`);
  console.log(`  Contains SessionGuard class: ${js.includes('function SessionGuard') ? 'PASS' : 'FAIL'}`);
  console.log(`  Contains predictOOM: ${js.includes('predictOOM') ? 'PASS' : 'FAIL'}`);
  console.log(`  Contains linear regression: ${js.includes('sumXY') ? 'PASS' : 'FAIL'}`);
  console.log(`  Contains WebSocket patch: ${js.includes('_patchWebSocket') ? 'PASS' : 'FAIL'}`);
  console.log(`  Contains sessionStorage recovery: ${js.includes('sessionStorage') ? 'PASS' : 'FAIL'}`);

  // Test 3: Library size
  console.log('\n--- Test 3: Library size ---');
  const rawSize = Buffer.byteLength(js);
  const gzipped = execFileSync('gzip', ['-c', path.join(DIR, 'session-guard.js')]);
  const gzipSize = gzipped.length;
  console.log(`  Raw: ${rawSize} bytes (${(rawSize/1024).toFixed(1)} KB)`);
  console.log(`  Gzipped: ${gzipSize} bytes (${(gzipSize/1024).toFixed(1)} KB)`);
  console.log(`  Under 5KB gzipped: ${gzipSize < 5120 ? 'PASS' : 'FAIL'}`);

  // Test 4: Library API completeness
  console.log('\n--- Test 4: API completeness ---');
  const features = [
    ['performance.memory collection', 'performance.memory'],
    ['DOM node counting', 'querySelectorAll'],
    ['Linear regression', 'sumX2'],
    ['Heap threshold check', 'heapThreshold'],
    ['Auto recovery', 'autoRecover'],
    ['State snapshot', 'stateKey'],
    ['Soft reload', 'location.reload'],
    ['Exponential backoff (WS)', 'Math.pow(2, attempt)'],
    ['Overlay panel', 'sg-overlay'],
    ['Memory chart (canvas)', 'sg-chart'],
    ['Destroy/cleanup', 'destroy']
  ];
  for (const [name, pattern] of features) {
    console.log(`  ${name}: ${js.includes(pattern) ? 'PASS' : 'FAIL'}`);
  }

  // Test 5: Demo page features
  console.log('\n--- Test 5: Demo page features ---');
  const demoFeatures = [
    ['Leak controls', 'btn-leak-start'],
    ['Burst button', 'btn-leak-burst'],
    ['DOM flood', 'btn-dom-flood'],
    ['State preservation', 'state-name'],
    ['Recovery banner', 'restored-banner'],
    ['Force recovery', 'btn-force-recover'],
    ['Event log', 'event-log'],
    ['stateSelector', 'stateSelector']
  ];
  for (const [name, pattern] of demoFeatures) {
    console.log(`  ${name}: ${html.includes(pattern) ? 'PASS' : 'FAIL'}`);
  }

  server.close();
  console.log('\nAll tests done.');
}

run().catch(e => { console.error(e); server.close(); process.exit(1); });
