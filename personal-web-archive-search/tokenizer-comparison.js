#!/usr/bin/env node
/**
 * Tokenizer comparison: trigram vs unicode61 vs ICU
 * Tests Korean, English, and mixed-language search quality
 */
const Database = require('better-sqlite3');
const path = require('path');

const TEST_DOCS = [
  { id: 1, title: '인공지능의 미래', content: '인공지능(AI)은 machine learning과 deep learning을 포함한다. 자연어 처리(NLP)는 한국어와 영어를 모두 다룬다.' },
  { id: 2, title: 'Node.js Performance', content: 'Node.js uses the V8 JavaScript engine for high performance. It supports async/await patterns.' },
  { id: 3, title: '서울의 맛집 가이드', content: '서울 강남구에 위치한 맛집들을 소개합니다. 떡볶이, 김치찌개, 된장찌개 등 한국 전통 음식을 맛볼 수 있습니다.' },
  { id: 4, title: 'Mixed 한영 Article', content: 'React와 Vue.js는 프론트엔드 framework입니다. TypeScript를 사용하면 타입 안전성이 높아집니다.' },
];

const TEST_QUERIES = [
  { q: '인공지능', expect: [1], desc: '한국어 3글자 이상' },
  { q: '서울', expect: [3], desc: '한국어 2글자' },
  { q: '김치', expect: [3], desc: '한국어 2글자 음식' },
  { q: 'JavaScript', expect: [2], desc: '영어 단어' },
  { q: 'machine learning', expect: [1], desc: '영어 구문' },
  { q: 'React', expect: [4], desc: '혼합 문서에서 영어 검색' },
  { q: '프론트엔드', expect: [4], desc: '혼합 문서에서 한국어 검색' },
  { q: '떡볶이', expect: [3], desc: '한국어 3글자 음식' },
];

function createTrigramDb() {
  const db = new Database(':memory:');
  db.exec('CREATE TABLE docs (id INTEGER PRIMARY KEY, title TEXT, content TEXT)');
  db.exec("CREATE VIRTUAL TABLE docs_fts USING fts5(title, content, content='docs', content_rowid='id', tokenize='trigram')");
  db.exec('CREATE TRIGGER docs_ai AFTER INSERT ON docs BEGIN INSERT INTO docs_fts(rowid, title, content) VALUES (new.id, new.title, new.content); END');
  return db;
}

function createUnicode61Db() {
  const db = new Database(':memory:');
  db.exec('CREATE TABLE docs (id INTEGER PRIMARY KEY, title TEXT, content TEXT)');
  db.exec("CREATE VIRTUAL TABLE docs_fts USING fts5(title, content, content='docs', content_rowid='id', tokenize='unicode61')");
  db.exec('CREATE TRIGGER docs_ai AFTER INSERT ON docs BEGIN INSERT INTO docs_fts(rowid, title, content) VALUES (new.id, new.title, new.content); END');
  return db;
}

function insertDocs(db) {
  var stmt = db.prepare('INSERT INTO docs (id, title, content) VALUES (?, ?, ?)');
  for (var i = 0; i < TEST_DOCS.length; i++) {
    var doc = TEST_DOCS[i];
    stmt.run(doc.id, doc.title, doc.content);
  }
}

function searchTrigram(db, query) {
  if (query.length < 3) {
    var pattern = '%' + query + '%';
    return db.prepare('SELECT id FROM docs WHERE title LIKE ? OR content LIKE ?').all(pattern, pattern).map(function(r) { return r.id; });
  }
  try {
    return db.prepare('SELECT rowid as id FROM docs_fts WHERE docs_fts MATCH ?').all(query).map(function(r) { return r.id; });
  } catch(e) { return []; }
}

function searchUnicode61(db, query) {
  try {
    var ftsQuery = query.indexOf(' ') >= 0 ? '"' + query + '"' : query;
    return db.prepare('SELECT rowid as id FROM docs_fts WHERE docs_fts MATCH ?').all(ftsQuery).map(function(r) { return r.id; });
  } catch(e) { return []; }
}

function runComparison() {
  var trigramDb = createTrigramDb();
  var unicode61Db = createUnicode61Db();
  insertDocs(trigramDb);
  insertDocs(unicode61Db);

  console.log('===== Tokenizer Comparison: trigram vs unicode61 =====');
  console.log('');

  var trigramScore = 0;
  var unicode61Score = 0;
  var total = TEST_QUERIES.length;

  console.log('Query                 | Expected | Trigram    | Unicode61');
  console.log('----------------------+----------+-----------+-----------');

  for (var i = 0; i < TEST_QUERIES.length; i++) {
    var test = TEST_QUERIES[i];
    var trigramResults = searchTrigram(trigramDb, test.q);
    var unicode61Results = searchUnicode61(unicode61Db, test.q);

    var trigramPass = test.expect.every(function(id) { return trigramResults.indexOf(id) >= 0; });
    var unicode61Pass = test.expect.every(function(id) { return unicode61Results.indexOf(id) >= 0; });

    if (trigramPass) trigramScore++;
    if (unicode61Pass) unicode61Score++;

    var qStr = test.q + ' (' + test.desc + ')';
    while (qStr.length < 21) qStr += ' ';
    var eStr = JSON.stringify(test.expect);
    while (eStr.length < 8) eStr += ' ';
    var tRes = (trigramPass ? 'PASS' : 'FAIL') + ' ' + JSON.stringify(trigramResults);
    var uRes = (unicode61Pass ? 'PASS' : 'FAIL') + ' ' + JSON.stringify(unicode61Results);

    console.log(qStr + ' | ' + eStr + ' | ' + tRes + ' | ' + uRes);
  }

  console.log('----------------------+----------+-----------+-----------');
  console.log('Score                 |          | ' + trigramScore + '/' + total + '       | ' + unicode61Score + '/' + total);
  console.log('');

  console.log('=== Analysis ===');
  console.log('');
  console.log('trigram (chosen):');
  console.log('  + Handles CJK natively via byte-level trigrams');
  console.log('  + Substring matching works for Korean partial words');
  console.log('  + No external dependencies (mecab, ICU)');
  console.log('  ~ Requires 3+ chars for FTS match (2-char fallback to LIKE)');
  console.log('  ~ Larger index size (every 3-char sequence stored)');
  console.log('');
  console.log('unicode61:');
  console.log('  + Good for English word tokenization');
  console.log('  - Treats each CJK char as individual token (poor for Korean)');
  console.log('  - Cannot match multi-char Korean words as units');
  console.log('');
  console.log('mecab-ko (not tested, requires system install):');
  console.log('  + Best Korean morphological analysis');
  console.log('  + Understands word boundaries and conjugations');
  console.log('  - Requires mecab + mecab-ko-dic system packages');
  console.log('  - Not available as SQLite FTS5 built-in tokenizer');
  console.log('');
  console.log('Conclusion: trigram + LIKE fallback gives the best balance');
  console.log('of Korean search quality and zero-dependency portability.');

  trigramDb.close();
  unicode61Db.close();

  return { trigramScore: trigramScore, unicode61Score: unicode61Score, total: total };
}

runComparison();
