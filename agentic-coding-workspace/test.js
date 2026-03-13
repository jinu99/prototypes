// DOM-level functional test using jsdom
var fs = require('fs');
var path = require('path');
var jsdom = require('jsdom');
var JSDOM = jsdom.JSDOM;

// Build a combined HTML for testing (simulates browser loading external scripts)
var htmlFile = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
var mockDataJS = fs.readFileSync(path.join(__dirname, 'mock-data.js'), 'utf8');
var renderJS = fs.readFileSync(path.join(__dirname, 'render.js'), 'utf8');
var appJS = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');

// Inline scripts for jsdom (it doesn't load external file:// scripts well)
var testHTML = htmlFile
  .replace('<script src="mock-data.js"></script>', '<script>' + mockDataJS + '<\/script>')
  .replace('<script src="render.js"></script>', '<script>' + renderJS + '<\/script>')
  .replace('<script src="app.js"></script>', '<script>' + appJS + '<\/script>')
  .replace('<link rel="stylesheet" href="style.css">', '');

function createDOM() {
  return new JSDOM(testHTML, {
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
    url: 'http://localhost/',
    storageQuota: 10000000,
  });
}

var pass = 0, fail = 0;
function check(name, condition) {
  if (condition) { console.log('[PASS]', name); pass++; }
  else { console.log('[FAIL]', name); fail++; }
}

function delay(ms) { return new Promise(function(r) { setTimeout(r, ms); }); }

async function run() {
  console.log('=== Agentic Coding Workspace — jsdom Test ===\n');

  var dom = createDOM();
  var w = dom.window;
  var d = w.document;
  await delay(200);

  check('1. Initial: no cells', d.querySelectorAll('.cell').length === 0);
  check('2. Empty state shown', d.querySelector('.empty-state') !== null);

  w.addPromptCell();
  await delay(100);
  check('3. One cell created', d.querySelectorAll('.cell').length === 1);
  check('4. Textarea exists', d.querySelector('textarea') !== null);

  d.querySelector('textarea').value = 'React Todo 앱에 필터 기능 추가';
  d.querySelector('textarea').dispatchEvent(new w.Event('input'));
  await delay(50);
  check('5. Text stored', w.cells[0].text === 'React Todo 앱에 필터 기능 추가');

  w.executeCell(w.cells[0].id);
  await delay(600);
  check('6. Plan cell created', d.querySelectorAll('.plan-cell').length === 1);
  check('7. Plan has 5 items', d.querySelectorAll('.plan-item').length === 5);

  var cbs = d.querySelectorAll('.plan-item input[type="checkbox"]');
  var allChecked = true;
  for (var i = 0; i < cbs.length; i++) { if (!cbs[i].checked) allChecked = false; }
  check('8. All items checked', allChecked);

  var planCellId = w.cells[1].id;
  w.togglePlanItem(planCellId, 2);
  await delay(50);
  check('9. Item unchecked', !w.cells[1].items[2].checked);

  w.editPlanItem(planCellId, 0, 'Custom filter management');
  check('10. Item edited', w.cells[1].items[0].text === 'Custom filter management');

  w.deletePlanItem(planCellId, 4);
  check('11. Item deleted', w.cells[1].items[4].deleted === true);
  check('12. Deleted item unchecked', w.cells[1].items[4].checked === false);

  w.approvePlan(planCellId);
  await delay(100);
  check('13. Plan approved', w.cells[1].status === 'approved');

  var results = w.cells.filter(function(c) { return c.type === 'result'; });
  check('14. Result cell created', results.length === 1);
  check('15. Result running', results[0].status === 'running');

  await delay(7000);
  var result = w.cells.find(function(c) { return c.type === 'result'; });
  check('16. Streaming done', result.status === 'done');
  check('17. Has content', result.blocks.length > 0);
  check('18. Prompt done', w.cells[0].status === 'done');

  w.executeCell(w.cells[0].id);
  await delay(600);
  check('19. Re-run: new plan', w.cells.filter(function(c) { return c.type === 'plan'; }).length === 1);
  check('20. Old result removed', w.cells.filter(function(c) { return c.type === 'result'; }).length === 0);

  w.addPromptCell('에러 핸들링 구현');
  check('21. Multiple prompts', w.cells.filter(function(c) { return c.type === 'prompt'; }).length === 2);

  var prompts = w.cells.filter(function(c) { return c.type === 'prompt'; });
  w.executeCell(prompts[1].id);
  await delay(600);
  check('22. Independent: 2 plans', w.cells.filter(function(c) { return c.type === 'plan'; }).length === 2);

  var stored = w.localStorage.getItem('agentic-workspace-cells');
  check('23. LocalStorage saved', stored !== null);
  var parsed = JSON.parse(stored);
  check('24. Cells array exists', Array.isArray(parsed.cells));
  check('25. Counter preserved', parsed.cellIdCounter > 0);

  var dom2 = createDOM();
  dom2.window.localStorage.setItem('agentic-workspace-cells', stored);
  dom2.window.loadState();
  dom2.window.renderCells();
  await delay(200);
  check('26. State restored', dom2.window.cells.length === parsed.cells.length);
  check('27. Running reset to idle', dom2.window.cells.every(function(c) { return c.status !== 'running'; }));

  w.loadDemo();
  await delay(200);
  var demo = w.cells.find(function(c) { return c.type === 'prompt'; });
  check('28. Demo loaded', demo !== null);
  check('29. Has filter keyword', demo.text.indexOf('필터') !== -1);

  w.clearAll(true);
  check('30. Clear works', w.cells.length === 0);

  dom.window.close();
  dom2.window.close();

  console.log('\n=== Results: ' + pass + ' passed, ' + fail + ' failed ===');
  process.exit(fail > 0 ? 1 : 0);
}

run().catch(function(e) { console.error('Test error:', e); process.exit(1); });
