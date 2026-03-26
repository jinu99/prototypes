const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', 'data', 'failures.db');

let db;

function getDb() {
  if (!db) {
    const fs = require('fs');
    fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
    db = new Database(DB_PATH);
    db.pragma('journal_mode = WAL');
    db.exec(`
      CREATE TABLE IF NOT EXISTS silent_failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        method TEXT NOT NULL,
        path TEXT NOT NULL,
        status_code INTEGER NOT NULL,
        rule_name TEXT NOT NULL,
        assertion_type TEXT NOT NULL,
        expected TEXT,
        actual TEXT,
        request_body TEXT,
        response_body TEXT
      )
    `);
  }
  return db;
}

function logFailure({ method, path: reqPath, statusCode, ruleName, assertionType, expected, actual, requestBody, responseBody }) {
  const db = getDb();
  db.prepare(`
    INSERT INTO silent_failures (method, path, status_code, rule_name, assertion_type, expected, actual, request_body, response_body)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(method, reqPath, statusCode, ruleName, assertionType, expected, actual, requestBody, responseBody);
}

function getFailures({ limit = 50, offset = 0 } = {}) {
  const db = getDb();
  return db.prepare('SELECT * FROM silent_failures ORDER BY timestamp DESC LIMIT ? OFFSET ?').all(limit, offset);
}

function getStats() {
  const db = getDb();
  return db.prepare(`
    SELECT path, method, COUNT(*) as count, MAX(timestamp) as last_seen
    FROM silent_failures
    GROUP BY path, method
    ORDER BY count DESC
  `).all();
}

function getTotal() {
  const db = getDb();
  return db.prepare('SELECT COUNT(*) as total FROM silent_failures').get().total;
}

function clearAll() {
  const db = getDb();
  db.exec('DELETE FROM silent_failures');
}

module.exports = { getDb, logFailure, getFailures, getStats, getTotal, clearAll };
