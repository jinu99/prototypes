const express = require('express');
const path = require('path');
const { loadRules, registerCallback } = require('./rules');
const { silentFailureDetector } = require('./middleware');
const { setupDemoRoutes } = require('./demo-service');
const { setupDashboardApi } = require('./dashboard-api');

const app = express();
const PORT = process.env.PORT || 3456;

// Parse JSON bodies
app.use(express.json());

// Load assertion rules
const rulesPath = path.join(__dirname, '..', 'rules.yaml');
loadRules(rulesPath);
console.log(`[SFD] Rules loaded from ${rulesPath}`);

// Register assertion callbacks for demo scenarios
registerCallback('verifyOrderInDb', ({ req, res, responseBody }) => {
  const orderId = responseBody?.id;
  if (!orderId) return { pass: false, expected: 'order id in response', actual: 'missing' };
  const order = app.locals.getOrder(orderId);
  if (!order) return { pass: false, expected: `order ${orderId} in DB`, actual: 'not found in DB' };
  return { pass: true };
});

registerCallback('verifyProfileUpdated', ({ req, res, responseBody }) => {
  const userId = req.params?.id;
  const user = app.locals.getUser(userId);
  if (!user) return { pass: true }; // 404 handled elsewhere

  // Check if the requested changes were actually applied
  const body = req.body || {};
  for (const [key, value] of Object.entries(body)) {
    if (key === 'id') continue; // skip id
    if (user[key] !== value) {
      return { pass: false, expected: `${key} = ${value}`, actual: `${key} = ${user[key]}` };
    }
  }
  return { pass: true };
});

// Install the silent failure detector middleware
app.use(silentFailureDetector());

// Setup demo service routes
setupDemoRoutes(app);

// Setup dashboard
app.use('/public', express.static(path.join(__dirname, '..', 'public')));
setupDashboardApi(app);

// Root redirect
app.get('/', (req, res) => res.redirect('/dashboard'));

app.listen(PORT, () => {
  console.log(`[SFD] Silent Failure Detector running at http://localhost:${PORT}`);
  console.log(`[SFD] Dashboard: http://localhost:${PORT}/dashboard`);
  console.log(`[SFD] Demo endpoints:`);
  console.log(`  POST /api/orders         — silent DB write failure`);
  console.log(`  POST /api/payments       — partial failure (charged=false)`);
  console.log(`  PUT  /api/users/:id      — intermittent update failure`);
});
