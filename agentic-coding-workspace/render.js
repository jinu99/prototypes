// Cell DOM rendering functions (safe DOM construction, no innerHTML)

function renderCells() {
  var container = document.getElementById('cells');
  container.textContent = '';
  if (cells.length === 0) {
    var empty = document.createElement('div');
    empty.className = 'empty-state';
    var h2 = document.createElement('h2');
    h2.textContent = 'No cells yet';
    var p = document.createElement('p');
    p.textContent = 'Add a prompt cell to start, or click Demo to load a sample scenario.';
    empty.appendChild(h2);
    empty.appendChild(p);
    container.appendChild(empty);
    return;
  }
  cells.forEach(function(cell) {
    var el;
    if (cell.type === 'prompt') el = buildPromptCellDOM(cell);
    else if (cell.type === 'plan') el = buildPlanCellDOM(cell);
    else if (cell.type === 'result') el = buildResultCellDOM(cell);
    if (el) container.appendChild(el);
  });
}

function buildPromptCellDOM(cell) {
  var div = document.createElement('div');
  div.className = 'cell'; div.id = 'cell-' + cell.id;
  var header = document.createElement('div'); header.className = 'cell-header';
  var hl = document.createElement('div'); hl.style.cssText = 'display:flex;align-items:center;gap:8px;';
  var badge = document.createElement('span'); badge.className = 'cell-type-badge prompt'; badge.textContent = '\u25B6 Prompt';
  var dot = document.createElement('span'); dot.className = 'status-dot ' + cell.status;
  var num = document.createElement('span'); num.style.cssText = 'font-size:11px;color:var(--text-dim)'; num.textContent = 'Cell #' + cell.id;
  hl.appendChild(badge); hl.appendChild(dot); hl.appendChild(num);
  var acts = document.createElement('div'); acts.className = 'cell-actions';
  var del = document.createElement('button'); del.className = 'btn btn-sm'; del.textContent = '\u2715'; del.title = 'Delete cell';
  del.addEventListener('click', function() { deleteCell(cell.id); });
  acts.appendChild(del);
  header.appendChild(hl); header.appendChild(acts); div.appendChild(header);

  var body = document.createElement('div'); body.className = 'cell-body';
  var ta = document.createElement('textarea');
  ta.placeholder = 'Enter your coding task... (Ctrl+Enter to run)';
  ta.value = cell.text || '';
  ta.addEventListener('input', function() { cell.text = ta.value; saveState(); });
  ta.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); executeCell(cell.id); }
  });
  body.appendChild(ta); div.appendChild(body);

  var footer = document.createElement('div'); footer.className = 'cell-footer';
  if (cell.status === 'done') {
    var rr = document.createElement('button'); rr.className = 'btn btn-sm'; rr.textContent = '\u21BB Re-run';
    rr.addEventListener('click', function() { rerunCell(cell.id); }); footer.appendChild(rr);
  }
  var run = document.createElement('button'); run.className = 'btn btn-sm btn-primary';
  run.textContent = cell.status === 'running' ? 'Running...' : '\u25B6 Run';
  run.disabled = cell.status === 'running';
  run.addEventListener('click', function() { executeCell(cell.id); });
  footer.appendChild(run); div.appendChild(footer);
  return div;
}

function buildPlanCellDOM(cell) {
  var div = document.createElement('div'); div.className = 'cell plan-cell'; div.id = 'cell-' + cell.id;
  var header = document.createElement('div'); header.className = 'cell-header';
  var hl = document.createElement('div'); hl.style.cssText = 'display:flex;align-items:center;gap:8px;';
  var badge = document.createElement('span'); badge.className = 'cell-type-badge plan'; badge.textContent = '\u2637 Plan Preview';
  var hint = document.createElement('span'); hint.style.cssText = 'font-size:11px;color:var(--text-dim)';
  hint.textContent = cell.status === 'approved' ? 'Approved' : 'Review & approve to continue';
  hl.appendChild(badge); hl.appendChild(hint); header.appendChild(hl); div.appendChild(header);

  var body = document.createElement('div'); body.className = 'cell-body';
  var ul = document.createElement('ul'); ul.className = 'plan-items';
  cell.items.forEach(function(item, i) {
    var li = document.createElement('li'); li.className = 'plan-item';
    var cb = document.createElement('input'); cb.type = 'checkbox';
    cb.checked = item.checked; cb.disabled = cell.status === 'approved';
    cb.addEventListener('change', function() { togglePlanItem(cell.id, i); });
    var ti = document.createElement('input'); ti.type = 'text';
    ti.className = 'plan-item-text' + (item.deleted ? ' deleted' : '');
    ti.value = item.text; ti.disabled = cell.status === 'approved';
    ti.addEventListener('change', function() { editPlanItem(cell.id, i, ti.value); });
    li.appendChild(cb); li.appendChild(ti);
    if (cell.status !== 'approved') {
      var rm = document.createElement('button'); rm.className = 'btn-icon';
      rm.textContent = '\u2715'; rm.title = 'Remove item';
      rm.addEventListener('click', function() { deletePlanItem(cell.id, i); });
      li.appendChild(rm);
    }
    ul.appendChild(li);
  });
  body.appendChild(ul); div.appendChild(body);

  if (cell.status !== 'approved') {
    var footer = document.createElement('div'); footer.className = 'cell-footer';
    var cnt = document.createElement('span'); cnt.style.cssText = 'font-size:11px;color:var(--text-dim)';
    var sel = cell.items.filter(function(i) { return i.checked && !i.deleted; }).length;
    cnt.textContent = sel + '/' + cell.items.length + ' items selected';
    var ab = document.createElement('button'); ab.className = 'btn btn-sm btn-primary';
    ab.textContent = '\u2713 Approve & Execute';
    ab.addEventListener('click', function() { approvePlan(cell.id); });
    footer.appendChild(cnt); footer.appendChild(ab); div.appendChild(footer);
  }
  return div;
}

function buildResultCellDOM(cell) {
  var div = document.createElement('div'); div.className = 'cell'; div.id = 'cell-' + cell.id;
  var header = document.createElement('div'); header.className = 'cell-header';
  var hl = document.createElement('div'); hl.style.cssText = 'display:flex;align-items:center;gap:8px;';
  var badge = document.createElement('span'); badge.className = 'cell-type-badge result'; badge.textContent = '\u25A0 Result';
  var dot = document.createElement('span'); dot.className = 'status-dot ' + cell.status;
  hl.appendChild(badge); hl.appendChild(dot); header.appendChild(hl); div.appendChild(header);
  var body = document.createElement('div'); body.className = 'cell-body';
  var content = document.createElement('div'); content.className = 'result-content';
  content.id = 'result-content-' + cell.id;
  body.appendChild(content); div.appendChild(body);
  setTimeout(function() { renderResultCellDOM(cell.id); }, 0);
  return div;
}

function renderResultCellDOM(cellId) {
  var container = document.getElementById('result-content-' + cellId);
  var cell = cells.find(function(c) { return c.id === cellId; });
  if (!container || !cell) return;

  container.textContent = '';
  (cell.blocks || []).forEach(function(block) {
    var el;
    if (block.type === 'heading') {
      el = document.createElement('strong');
      el.style.cssText = 'color:var(--accent);font-size:14px;display:block;margin-bottom:4px;';
      el.textContent = block.text;
    } else if (block.type === 'code') {
      el = document.createElement('div');
      el.className = 'code-block';
      el.textContent = block.text;
    } else {
      el = document.createElement('span');
      el.textContent = block.text;
    }
    container.appendChild(el);
    container.appendChild(document.createTextNode('\n'));
  });

  if (cell.status === 'running') {
    var cursor = document.createElement('span');
    cursor.className = 'cursor-blink';
    cursor.textContent = '|';
    container.appendChild(cursor);
  }
  var dot = document.querySelector('#cell-' + cellId + ' .status-dot');
  if (dot) dot.className = 'status-dot ' + cell.status;
}
