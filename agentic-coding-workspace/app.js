/* Agentic Coding Workspace — Core Logic
   Uses safe DOM methods (textContent, createElement) to prevent XSS.
   Rendering functions are in render.js */

var STORAGE_KEY = 'agentic-workspace-cells';
var cells = [];
var cellIdCounter = 0;

// ── Cell Management ──
function createCellId() { return ++cellIdCounter; }

function addPromptCell(initialText) {
  var cell = {
    id: createCellId(), type: 'prompt', text: initialText || '',
    status: 'idle', resultCellId: null, planCellId: null
  };
  cells.push(cell);
  renderCells();
  saveState();
  var ta = document.querySelector('#cell-' + cell.id + ' textarea');
  if (ta) ta.focus();
}

function addPlanCell(parentId, planItems) {
  var cell = {
    id: createCellId(), type: 'plan', parentId: parentId,
    items: planItems.map(function(text) { return { text: text, checked: true, deleted: false }; }),
    status: 'pending'
  };
  var idx = cells.findIndex(function(c) { return c.id === parentId; });
  cells.splice(idx + 1, 0, cell);
  var parent = cells.find(function(c) { return c.id === parentId; });
  if (parent) parent.planCellId = cell.id;
  renderCells();
  saveState();
  return cell;
}

function addResultCell(parentId) {
  var cell = {
    id: createCellId(), type: 'result', parentId: parentId,
    blocks: [], streamIdx: 0, streamCharIdx: 0, status: 'idle'
  };
  var parent = cells.find(function(c) { return c.id === parentId; });
  var insertIdx;
  if (parent && parent.planCellId) {
    insertIdx = cells.findIndex(function(c) { return c.id === parent.planCellId; }) + 1;
  } else {
    insertIdx = cells.findIndex(function(c) { return c.id === parentId; }) + 1;
  }
  cells.splice(insertIdx, 0, cell);
  if (parent) parent.resultCellId = cell.id;
  renderCells();
  saveState();
  return cell;
}

function deleteCell(id) {
  var cell = cells.find(function(c) { return c.id === id; });
  if (!cell) return;
  if (cell.type === 'prompt') {
    if (cell.planCellId) cells = cells.filter(function(c) { return c.id !== cell.planCellId; });
    if (cell.resultCellId) cells = cells.filter(function(c) { return c.id !== cell.resultCellId; });
  }
  cells = cells.filter(function(c) { return c.id !== id; });
  renderCells();
  saveState();
}

// ── Execution ──
function executeCell(promptCellId) {
  var promptCell = cells.find(function(c) { return c.id === promptCellId; });
  if (!promptCell || promptCell.status === 'running') return;
  if (!promptCell.text.trim()) return;

  promptCell.status = 'running';
  if (promptCell.planCellId) {
    cells = cells.filter(function(c) { return c.id !== promptCell.planCellId; });
    promptCell.planCellId = null;
  }
  if (promptCell.resultCellId) {
    cells = cells.filter(function(c) { return c.id !== promptCell.resultCellId; });
    promptCell.resultCellId = null;
  }

  renderCells();
  var mock = getMockResponse(promptCell.text);
  setTimeout(function() {
    var planCell = addPlanCell(promptCellId, mock.plan);
    scrollToCell(planCell.id);
  }, 400);
}

function approvePlan(planCellId) {
  var planCell = cells.find(function(c) { return c.id === planCellId; });
  if (!planCell) return;
  planCell.status = 'approved';

  var promptCell = cells.find(function(c) { return c.id === planCell.parentId; });
  if (!promptCell) return;

  var approved = planCell.items.filter(function(i) { return i.checked && !i.deleted; });
  if (approved.length === 0) {
    promptCell.status = 'idle';
    showToast('No plan items selected');
    renderCells();
    saveState();
    return;
  }

  var resultCell = addResultCell(promptCell.id);
  resultCell.status = 'running';
  renderCells();
  streamResponse(resultCell.id, getMockResponse(promptCell.text).response, promptCell.id);
}

function streamResponse(resultCellId, responseBlocks, promptCellId) {
  var resultCell = cells.find(function(c) { return c.id === resultCellId; });
  if (!resultCell) return;

  resultCell.blocks = [];
  var blockIdx = 0, charIdx = 0, speed = 12, chunkSize = 3;

  var interval = setInterval(function() {
    if (blockIdx >= responseBlocks.length) {
      clearInterval(interval);
      resultCell.status = 'done';
      var promptCell = cells.find(function(c) { return c.id === promptCellId; });
      if (promptCell) promptCell.status = 'done';
      renderResultCellDOM(resultCellId);
      renderCells();
      saveState();
      return;
    }
    var srcBlock = responseBlocks[blockIdx];
    if (!resultCell.blocks[blockIdx]) {
      resultCell.blocks[blockIdx] = { type: srcBlock.type, lang: srcBlock.lang || '', text: '' };
    }
    var fullText = srcBlock.text;
    charIdx = Math.min(charIdx + chunkSize, fullText.length);
    resultCell.blocks[blockIdx].text = fullText.substring(0, charIdx);
    if (charIdx >= fullText.length) { blockIdx++; charIdx = 0; }
    renderResultCellDOM(resultCellId);
  }, speed);
}

function rerunCell(promptCellId) { executeCell(promptCellId); }

// ── Plan Interactions ──
function togglePlanItem(cellId, idx) {
  var cell = cells.find(function(c) { return c.id === cellId; });
  if (!cell || cell.status === 'approved') return;
  cell.items[idx].checked = !cell.items[idx].checked;
  renderCells(); saveState();
}
function editPlanItem(cellId, idx, newText) {
  var cell = cells.find(function(c) { return c.id === cellId; });
  if (!cell || cell.status === 'approved') return;
  cell.items[idx].text = newText; saveState();
}
function deletePlanItem(cellId, idx) {
  var cell = cells.find(function(c) { return c.id === cellId; });
  if (!cell || cell.status === 'approved') return;
  cell.items[idx].deleted = !cell.items[idx].deleted;
  cell.items[idx].checked = false;
  renderCells(); saveState();
}

// ── Helpers ──
function scrollToCell(cellId) {
  setTimeout(function() {
    var el = document.getElementById('cell-' + cellId);
    if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 100);
}
function showToast(msg) {
  var el = document.getElementById('toast');
  el.textContent = msg; el.classList.add('show');
  setTimeout(function() { el.classList.remove('show'); }, 2000);
}

// ── Persistence ──
function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ cells: cells, cellIdCounter: cellIdCounter }));
  } catch(e) { /* quota exceeded */ }
}
function loadState() {
  try {
    var raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    var data = JSON.parse(raw);
    cells = data.cells || []; cellIdCounter = data.cellIdCounter || 0;
    cells.forEach(function(c) { if (c.status === 'running') c.status = 'idle'; });
    return cells.length > 0;
  } catch(e) { return false; }
}

// ── Demo ──
function loadDemo() {
  clearAll(true);
  document.getElementById('demoBanner').style.display = 'flex';
  addPromptCell('React Todo 앱에 필터 기능을 추가해줘. All / Active / Completed 3가지 필터가 필요해.');
  showToast('Demo scenario loaded \u2014 press Run!');
}
function hideBanner() { document.getElementById('demoBanner').style.display = 'none'; }
function clearAll(silent) {
  if (!silent && cells.length > 0 && !confirm('Clear all cells?')) return;
  cells = []; cellIdCounter = 0; renderCells(); saveState(); hideBanner();
}

// ── Init ──
(function init() {
  if (loadState()) { renderCells(); showToast('Restored from previous session'); }
  else { renderCells(); }
})();
