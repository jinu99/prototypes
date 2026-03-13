// E2E test via API calls + HTML parsing (no browser needed)
const http = require('http');
const path = require('path');
const fs = require('fs');

const BASE = 'http://localhost:4567';
const SAMPLE_FILE = path.join(__dirname, 'sample.md');
const results = [];

function log(msg) { console.log('[TEST]', msg); }
function pass(name) { results.push({ name, ok: true }); log('PASS: ' + name); }
function fail(name, reason) { results.push({ name, ok: false, reason }); log('FAIL: ' + name + ' — ' + reason); }

function fetch(url, opts = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const reqOpts = {
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname,
      method: opts.method || 'GET',
      headers: opts.headers || {}
    };
    const req = http.request(reqOpts, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, text: data, json: () => JSON.parse(data) }));
    });
    req.on('error', reject);
    if (opts.body) req.write(opts.body);
    req.end();
  });
}

async function run() {
  // Restore sample.md to clean state first
  const originalSample = `---
marp: true
theme: default
paginate: true
---

# 프로토타입 데모

슬라이드 Last-Mile Editor

클릭하여 이 텍스트를 편집해보세요.

---

## 두 번째 슬라이드

- 마크다운 소스와 **실시간 동기화**
- 블록 레벨 편집 지원
- 드래그로 위치 조정 가능

이 문단도 편집할 수 있습니다.

---

## 세 번째 슬라이드

### 기능 요약

1. Marp 렌더링 미리보기
2. 인라인 텍스트 편집
3. 드래그 리포지셔닝
4. Diff 하이라이트

> 블록 레벨 양방향 편집으로 last-mile 마찰을 줄입니다.`;
  fs.writeFileSync(SAMPLE_FILE, originalSample, 'utf-8');

  // Reset diff baseline
  await fetch(BASE + '/api/diff/reset', { method: 'POST' });

  // ── Test 1: Slide rendering ──
  log('Test 1: Load and render slides');
  const loadRes = await fetch(BASE + '/api/slide');
  const loadData = loadRes.json();

  const hasMarkdown = loadData.markdown && loadData.markdown.length > 0;
  const hasHtml = loadData.html && loadData.html.length > 0;
  const hasCss = loadData.css && loadData.css.length > 0;
  const sectionCount = (loadData.html.match(/<section/g) || []).length;

  if (hasMarkdown && hasHtml && hasCss && sectionCount >= 3) {
    pass('Marp rendering (3+ slides): ' + sectionCount + ' sections');
  } else {
    fail('Marp rendering', 'sections=' + sectionCount + ' md=' + hasMarkdown + ' html=' + hasHtml);
  }

  // ── Test 2: Source line mapping ──
  log('Test 2: data-source-line attributes');
  const sourceLineMatches = loadData.html.match(/data-source-line/g) || [];
  if (sourceLineMatches.length > 0) {
    pass('Source line mapping: ' + sourceLineMatches.length + ' elements');
  } else {
    fail('Source line mapping', 'No data-source-line found in HTML');
  }

  // ── Test 3: Inline edit → source sync ──
  log('Test 3: Inline edit syncs to source');
  const editRes = await fetch(BASE + '/api/edit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sourceLine: 6, sourceEnd: 7, newText: '# Edited Title' })
  });
  const editData = editRes.json();

  if (editData.markdown.includes('# Edited Title')) {
    pass('Inline edit → source sync');
    // Also verify file on disk
    const diskContent = fs.readFileSync(SAMPLE_FILE, 'utf-8');
    if (diskContent.includes('# Edited Title')) pass('Edit persisted to disk');
    else fail('Edit persisted to disk', 'File not updated');
  } else {
    fail('Inline edit → source sync', 'Markdown not updated');
  }

  // ── Test 4: Re-render after edit ──
  log('Test 4: Re-render contains edited content');
  if (editData.html.includes('Edited Title')) {
    pass('Re-render shows edited content');
  } else {
    fail('Re-render', 'Edited content not in re-rendered HTML');
  }

  // ── Test 5: Drag → inline style ──
  log('Test 5: Style/position update');
  const styleRes = await fetch(BASE + '/api/style', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sourceLine: 8, sourceEnd: 9, styleStr: 'margin-top: 30px' })
  });
  const styleData = styleRes.json();

  if (styleData.markdown.includes('margin-top: 30px')) {
    pass('Drag → inline style in .md');
  } else {
    fail('Drag → inline style', 'margin-top not found in markdown');
  }

  // ── Test 6: Diff ──
  log('Test 6: Diff between original and current');
  const diffRes = await fetch(BASE + '/api/diff');
  const diffData = diffRes.json();

  const hasChanges = diffData.changes && diffData.changes.some(c => c.added || c.removed);
  if (hasChanges) {
    const added = diffData.changes.filter(c => c.added).length;
    const removed = diffData.changes.filter(c => c.removed).length;
    pass('Diff display: ' + added + ' additions, ' + removed + ' removals');
  } else {
    fail('Diff display', 'No changes detected');
  }

  // ── Test 7: Full save from source ──
  log('Test 7: Full markdown save');
  const newMd = originalSample.replace('두 번째 슬라이드', 'Second Slide Updated');
  const saveRes = await fetch(BASE + '/api/slide', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ markdown: newMd })
  });
  const saveData = saveRes.json();

  if (saveData.html.includes('Second Slide Updated')) {
    pass('Full save → re-render');
  } else {
    fail('Full save', 'Updated content not in rendered HTML');
  }

  // ── Test 8: Static file serving (index.html) ──
  log('Test 8: Static file serving');
  const htmlRes = await fetch(BASE + '/');
  if (htmlRes.status === 200 && htmlRes.text.includes('Slide Last-Mile Editor')) {
    pass('Static HTML served');
  } else {
    fail('Static HTML', 'Status=' + htmlRes.status);
  }

  // Restore sample
  fs.writeFileSync(SAMPLE_FILE, originalSample, 'utf-8');
  await fetch(BASE + '/api/diff/reset', { method: 'POST' });

  // Summary
  console.log('\n=== TEST SUMMARY ===');
  const passed = results.filter(r => r.ok).length;
  const failed = results.filter(r => !r.ok).length;
  results.forEach(r => console.log(r.ok ? '  PASS' : '  FAIL', r.name, r.ok ? '' : '— ' + r.reason));
  console.log('\nTotal: ' + passed + ' passed, ' + failed + ' failed out of ' + results.length);

  process.exit(failed > 0 ? 1 : 0);
}

run().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
