const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = path.join(__dirname, 'queue.db');

function createDb() {
  const db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  db.exec(`
    CREATE TABLE IF NOT EXISTS queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      party_size INTEGER NOT NULL DEFAULT 1,
      status TEXT NOT NULL DEFAULT 'waiting',
      created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
      called_at TEXT,
      seated_at TEXT,
      completed_at TEXT
    )
  `);

  return db;
}

module.exports = { createDb };
