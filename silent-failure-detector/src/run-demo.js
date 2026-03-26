/**
 * CLI demo script: starts the server, runs all 3 scenarios, prints results.
 */
const http = require('http');

const BASE = 'http://localhost:3456';

function request(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE);
    const opts = {
      method,
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      headers: { 'Content-Type': 'application/json' },
    };
    const req = http.request(opts, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch { resolve(data); }
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function run() {
  console.log('\n=== Silent Failure Detector — Demo ===\n');

  // Clear previous data
  await request('POST', '/api/failures/clear');
  console.log('[1/4] Cleared previous failure data');

  // Scenario 1: Order creation (silent DB failure)
  const order = await request('POST', '/api/orders', { item: 'Premium Widget', qty: 5 });
  console.log(`[2/4] POST /api/orders → ${JSON.stringify(order)}`);

  // Scenario 2: Payment (partial failure)
  const payment = await request('POST', '/api/payments', { amount: 149.99, card: '****4321' });
  console.log(`[3/4] POST /api/payments → ${JSON.stringify(payment)}`);

  // Scenario 3: Profile update (intermittent failure - send twice)
  const update1 = await request('PUT', '/api/users/1', { name: 'Alice Wonderland' });
  console.log(`[4/4] PUT /api/users/1 → ${JSON.stringify(update1)}`);
  const update2 = await request('PUT', '/api/users/2', { name: 'Bob Builder' });
  console.log(`      PUT /api/users/2 → ${JSON.stringify(update2)}`);

  // Wait for async assertions
  await new Promise(r => setTimeout(r, 500));

  // Fetch detected failures
  const { failures, total } = await request('GET', '/api/failures');
  console.log(`\n=== Detected Silent Failures: ${total} ===\n`);

  failures.forEach((f, i) => {
    console.log(`  ${i + 1}. [${f.rule_name}] ${f.method} ${f.path}`);
    console.log(`     Expected: ${f.expected}`);
    console.log(`     Actual:   ${f.actual}`);
    console.log('');
  });

  // Stats
  const { stats } = await request('GET', '/api/stats');
  console.log('=== Endpoint Stats ===\n');
  stats.forEach(s => {
    console.log(`  ${s.method} ${s.path}: ${s.count} failures (last: ${s.last_seen})`);
  });

  console.log('\n=== Demo Complete ===');
  console.log(`Dashboard: ${BASE}/dashboard\n`);
}

run().catch(err => {
  console.error('Demo failed. Is the server running? Start with: npm start');
  console.error(err.message);
  process.exit(1);
});
