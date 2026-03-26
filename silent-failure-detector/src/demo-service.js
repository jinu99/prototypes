const express = require('express');

/**
 * Creates a demo service with 3 scenarios:
 * 1. POST /api/orders — returns 200 with id, but DB write "silently fails"
 * 2. POST /api/payments — returns 200 with result:"success" but details.charged:false
 * 3. PUT /api/users/:id — returns 200 but intermittently doesn't actually update
 */

// In-memory "databases" for demo
const orders = {};
const users = {
  '1': { id: '1', name: 'Alice', email: 'alice@example.com' },
  '2': { id: '2', name: 'Bob', email: 'bob@example.com' },
};

let requestCount = 0;

function setupDemoRoutes(app) {
  // Scenario 1: Silent DB failure — order endpoint returns 200 but never persists
  app.post('/api/orders', (req, res) => {
    const orderId = `ord_${Date.now()}`;
    // BUG: We return success but never write to the "database"
    // orders[orderId] = { ...req.body, id: orderId, status: 'created' };  // ← commented out!
    res.json({
      id: orderId,
      status: 'created',
      message: 'Order placed successfully',
    });
  });

  // Scenario 2: Partial failure — payment looks successful but charge didn't go through
  app.post('/api/payments', (req, res) => {
    // BUG: Returns success at top level, but the actual charge failed
    res.json({
      result: 'success',
      transactionId: `tx_${Date.now()}`,
      details: {
        charged: false,         // ← silent failure: charge didn't actually happen
        amount: req.body?.amount || 0,
        gateway: 'mock_gateway',
        gatewayError: 'insufficient_funds',  // buried error
      },
    });
  });

  // Scenario 3: Intermittent failure — profile update sometimes doesn't apply
  app.put('/api/users/:id', (req, res) => {
    requestCount++;
    const user = users[req.params.id];
    if (!user) return res.status(404).json({ error: 'User not found' });

    // BUG: Every other request silently drops the update
    if (requestCount % 2 === 0) {
      // Actually update
      Object.assign(user, req.body, { id: user.id });
    }
    // else: silently ignore the update

    // Always returns 200 with "updated" data (which may be stale)
    res.json({
      ...user,
      updated: true,
      message: 'Profile updated successfully',
    });
  });

  // Helper: get order from "DB" (used by assertion callback)
  app.locals.getOrder = (id) => orders[id];
  app.locals.getUser = (id) => users[id];
  app.locals.users = users;
}

module.exports = { setupDemoRoutes };
