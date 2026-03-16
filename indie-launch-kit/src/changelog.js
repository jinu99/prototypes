import simpleGit from 'simple-git';

/**
 * Parse conventional commits from git log and generate changelog HTML.
 */
export async function generateChangelog(projectDir) {
  const git = simpleGit(projectDir);

  let logs;
  try {
    logs = await git.log({ maxCount: 200 });
  } catch {
    return { html: '<p>No git history found.</p>', entries: [] };
  }

  if (!logs.all.length) {
    return { html: '<p>No commits found.</p>', entries: [] };
  }

  const entries = logs.all.map(commit => {
    const parsed = parseConventionalCommit(commit.message);
    return {
      hash: commit.hash.slice(0, 7),
      date: commit.date,
      author: commit.author_name,
      ...parsed,
    };
  });

  // Group by type
  const groups = {};
  for (const entry of entries) {
    const key = entry.type || 'other';
    if (!groups[key]) groups[key] = [];
    groups[key].push(entry);
  }

  const typeLabels = {
    feat: 'Features',
    fix: 'Bug Fixes',
    docs: 'Documentation',
    style: 'Styles',
    refactor: 'Refactoring',
    perf: 'Performance',
    test: 'Tests',
    build: 'Build',
    ci: 'CI',
    chore: 'Chores',
    other: 'Other',
  };

  const order = ['feat', 'fix', 'perf', 'refactor', 'docs', 'style', 'test', 'build', 'ci', 'chore', 'other'];

  let html = '<div class="changelog">\n<h1>Changelog</h1>\n';
  for (const type of order) {
    if (!groups[type]) continue;
    const label = typeLabels[type] || type;
    html += `<h2>${escapeHtml(label)}</h2>\n<ul>\n`;
    for (const entry of groups[type]) {
      const scope = entry.scope ? `<strong>${escapeHtml(entry.scope)}</strong>: ` : '';
      html += `<li>${scope}${escapeHtml(entry.subject)} <span class="hash">(${entry.hash})</span></li>\n`;
    }
    html += '</ul>\n';
  }
  html += '</div>';

  return { html, entries };
}

function parseConventionalCommit(message) {
  const match = message.match(/^(\w+)(?:\(([^)]*)\))?(!)?:\s*(.+)/);
  if (match) {
    return {
      type: match[1],
      scope: match[2] || '',
      breaking: !!match[3],
      subject: match[4].trim(),
      raw: message,
    };
  }
  return {
    type: 'other',
    scope: '',
    breaking: false,
    subject: message.split('\n')[0].trim(),
    raw: message,
  };
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
