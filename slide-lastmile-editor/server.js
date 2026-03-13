const express = require('express');
const fs = require('fs');
const path = require('path');
const Marp = require('@marp-team/marp-core').default || require('@marp-team/marp-core');
const Diff = require('diff');

const app = express();
const PORT = process.env.PORT || 4567;
const SLIDE_FILE = path.join(__dirname, 'sample.md');

app.use(express.json({ limit: '1mb' }));
app.use(express.static(__dirname));

// Store original content for diff
let originalContent = fs.readFileSync(SLIDE_FILE, 'utf-8');

// Render Marp markdown to HTML with source line mapping
function renderMarp(markdown) {
  const marp = new Marp({
    html: true,
    math: false,
  });

  // Inject source line data attributes via markdown-it plugin
  marp.markdown.core.ruler.push('source_line_map', (state) => {
    for (const token of state.tokens) {
      if (token.map && token.map.length >= 2) {
        const attrName = 'data-source-line';
        const attrVal = `${token.map[0]}`;
        if (token.type === 'heading_open' || token.type === 'paragraph_open' ||
            token.type === 'bullet_list_open' || token.type === 'ordered_list_open' ||
            token.type === 'blockquote_open' || token.type === 'list_item_open') {
          token.attrSet(attrName, attrVal);
          token.attrSet('data-source-end', `${token.map[1]}`);
        }
      }
    }
  });

  const { html, css } = marp.render(markdown);
  return { html, css };
}

// GET /api/slide — load markdown + rendered HTML
app.get('/api/slide', (req, res) => {
  const markdown = fs.readFileSync(SLIDE_FILE, 'utf-8');
  const { html, css } = renderMarp(markdown);
  res.json({ markdown, html, css });
});

// POST /api/slide — save markdown
app.post('/api/slide', (req, res) => {
  const { markdown } = req.body;
  if (!markdown) return res.status(400).json({ error: 'markdown required' });
  fs.writeFileSync(SLIDE_FILE, markdown, 'utf-8');
  const { html, css } = renderMarp(markdown);
  res.json({ markdown, html, css });
});

// POST /api/edit — edit a specific block by source line
app.post('/api/edit', (req, res) => {
  const { sourceLine, sourceEnd, newText } = req.body;
  if (sourceLine == null || newText == null) {
    return res.status(400).json({ error: 'sourceLine and newText required' });
  }

  const markdown = fs.readFileSync(SLIDE_FILE, 'utf-8');
  const lines = markdown.split('\n');
  const start = parseInt(sourceLine);
  const end = sourceEnd != null ? parseInt(sourceEnd) : start + 1;

  // Replace the lines in range
  const newLines = newText.split('\n');
  lines.splice(start, end - start, ...newLines);

  const updated = lines.join('\n');
  fs.writeFileSync(SLIDE_FILE, updated, 'utf-8');
  const { html, css } = renderMarp(updated);
  res.json({ markdown: updated, html, css });
});

// POST /api/style — update element position as inline style
app.post('/api/style', (req, res) => {
  const { sourceLine, sourceEnd, styleStr } = req.body;
  if (sourceLine == null || styleStr == null) {
    return res.status(400).json({ error: 'sourceLine and styleStr required' });
  }

  const markdown = fs.readFileSync(SLIDE_FILE, 'utf-8');
  const lines = markdown.split('\n');
  const start = parseInt(sourceLine);

  // Inject or update HTML comment with style on the line before the block
  const existingLine = lines[start] || '';
  // Remove previous style comment if present
  const cleaned = existingLine.replace(/<!--\s*style:.*?-->\s*/, '');
  lines[start] = `<!-- style: ${styleStr} -->\n${cleaned}`;

  const updated = lines.join('\n');
  fs.writeFileSync(SLIDE_FILE, updated, 'utf-8');
  const { html, css } = renderMarp(updated);
  res.json({ markdown: updated, html, css });
});

// GET /api/diff — get diff between original and current
app.get('/api/diff', (req, res) => {
  const current = fs.readFileSync(SLIDE_FILE, 'utf-8');
  const changes = Diff.diffLines(originalContent, current);
  res.json({ original: originalContent, current, changes });
});

// POST /api/diff/reset — reset original baseline
app.post('/api/diff/reset', (req, res) => {
  originalContent = fs.readFileSync(SLIDE_FILE, 'utf-8');
  res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`Slide Last-Mile Editor running at http://localhost:${PORT}`);
});
