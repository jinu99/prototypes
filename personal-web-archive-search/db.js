const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = path.join(__dirname, 'archive.db');

function openDb() {
  const db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  return db;
}

function initDb(db) {
  // Main pages table
  db.exec(`
    CREATE TABLE IF NOT EXISTS pages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      url TEXT UNIQUE NOT NULL,
      title TEXT,
      content TEXT,
      excerpt TEXT,
      site_name TEXT,
      added_at TEXT DEFAULT (datetime('now')),
      lang TEXT
    )
  `);

  // FTS5 with trigram tokenizer for CJK support
  // trigram tokenizer indexes every 3-byte sequence, works great for CJK
  db.exec(`
    CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
      title, content,
      content='pages',
      content_rowid='id',
      tokenize='trigram'
    )
  `);

  // Triggers to keep FTS in sync
  db.exec(`
    CREATE TRIGGER IF NOT EXISTS pages_ai AFTER INSERT ON pages BEGIN
      INSERT INTO pages_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
    END
  `);
  db.exec(`
    CREATE TRIGGER IF NOT EXISTS pages_ad AFTER DELETE ON pages BEGIN
      INSERT INTO pages_fts(pages_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
    END
  `);
  db.exec(`
    CREATE TRIGGER IF NOT EXISTS pages_au AFTER UPDATE ON pages BEGIN
      INSERT INTO pages_fts(pages_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
      INSERT INTO pages_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
    END
  `);
}

function addPage(db, { url, title, content, excerpt, siteName, lang }) {
  const stmt = db.prepare(`
    INSERT OR REPLACE INTO pages (url, title, content, excerpt, site_name, lang)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  return stmt.run(url, title, content, excerpt, siteName, lang);
}

function search(db, query) {
  // FTS5 trigram requires 3+ chars. For shorter queries, fall back to LIKE.
  if (query.length < 3) {
    const pattern = `%${query}%`;
    const stmt = db.prepare(`
      SELECT id, url, title, excerpt, site_name, added_at, lang,
             substr(content, max(1, instr(content, ?) - 60), 160) AS snippet
      FROM pages
      WHERE title LIKE ? OR content LIKE ?
      LIMIT 20
    `);
    return stmt.all(query, pattern, pattern);
  }

  const stmt = db.prepare(`
    SELECT p.id, p.url, p.title, p.excerpt, p.site_name, p.added_at, p.lang,
           snippet(pages_fts, 1, '<mark>', '</mark>', '…', 40) AS snippet
    FROM pages_fts fts
    JOIN pages p ON p.id = fts.rowid
    WHERE pages_fts MATCH ?
    ORDER BY rank
    LIMIT 20
  `);
  return stmt.all(query);
}

function listPages(db) {
  return db.prepare('SELECT id, url, title, added_at FROM pages ORDER BY added_at DESC').all();
}

function getPageCount(db) {
  return db.prepare('SELECT COUNT(*) as count FROM pages').get().count;
}

module.exports = { openDb, initDb, addPage, search, listPages, getPageCount };
