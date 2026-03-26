const { getFailures, getStats, getTotal, clearAll } = require('./db');
const { getRules } = require('./rules');

function setupDashboardApi(app) {
  // Serve dashboard HTML
  app.get('/dashboard', (req, res) => {
    res.sendFile(require('path').join(__dirname, '..', 'public', 'dashboard.html'));
  });

  // API: list failures
  app.get('/api/failures', (req, res) => {
    const limit = parseInt(req.query.limit) || 50;
    const offset = parseInt(req.query.offset) || 0;
    const failures = getFailures({ limit, offset });
    const total = getTotal();
    res.json({ failures, total, limit, offset });
  });

  // API: endpoint stats
  app.get('/api/stats', (req, res) => {
    const stats = getStats();
    res.json({ stats });
  });

  // API: active rules
  app.get('/api/rules', (req, res) => {
    const rules = getRules();
    res.json({ rules: rules.map(r => ({ name: r.name, endpoint: r.endpoint, assertions: r.assertions.length })) });
  });

  // API: clear all failures (for demo reset)
  app.post('/api/failures/clear', (req, res) => {
    clearAll();
    res.json({ cleared: true });
  });
}

module.exports = { setupDashboardApi };
