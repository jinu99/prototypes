const chalk = require('chalk');

const SEVERITY_COLORS = {
  high: chalk.red,
  medium: chalk.yellow,
  low: chalk.blue,
};

const SEVERITY_ICONS = {
  high: '●',
  medium: '◐',
  low: '○',
};

/**
 * Format scan results for terminal output.
 */
function formatResults(results, options = {}) {
  const { verbose = false, json = false } = options;

  if (json) {
    return JSON.stringify(results, null, 2);
  }

  const lines = [];

  lines.push('');
  lines.push(chalk.bold('  Dark Path Detector'));
  lines.push(chalk.dim('  Finding unobserved error paths in your code'));
  lines.push('');

  if (results.files.length === 0) {
    lines.push(chalk.green('  ✓ No dark paths found!'));
    lines.push('');
    lines.push(formatSummary(results.summary));
    return lines.join('\n');
  }

  // Group by severity
  for (const file of results.files) {
    lines.push(chalk.underline(`  ${file.path}`));

    for (const finding of file.findings) {
      const color = SEVERITY_COLORS[finding.severity] || chalk.white;
      const icon = SEVERITY_ICONS[finding.severity] || '○';

      const location = chalk.dim(`L${finding.line}`);
      const type = chalk.dim(`[${finding.type}]`);
      lines.push(`    ${color(icon)} ${location} ${finding.message} ${type}`);
    }

    lines.push('');
  }

  lines.push(formatSummary(results.summary));

  return lines.join('\n');
}

/**
 * Format the summary section.
 */
function formatSummary(summary) {
  const lines = [];

  lines.push(chalk.bold('  ─── Summary ───'));
  lines.push('');
  lines.push(`  Files scanned:     ${summary.totalFiles}`);
  lines.push(`  Error paths found: ${summary.totalErrorPaths}`);

  const darkPathStr = summary.totalDarkPaths > 0
    ? chalk.red(`${summary.totalDarkPaths}`)
    : chalk.green('0');
  lines.push(`  Dark paths:        ${darkPathStr}`);

  // Coverage bar
  const coverage = summary.coveragePercent;
  const barLen = 20;
  const filled = Math.round((coverage / 100) * barLen);
  const empty = barLen - filled;
  const coverageColor = coverage >= 80 ? chalk.green : coverage >= 50 ? chalk.yellow : chalk.red;
  const bar = coverageColor('█'.repeat(filled)) + chalk.dim('░'.repeat(empty));
  lines.push(`  Coverage:          ${bar} ${coverageColor(`${coverage}%`)}`);
  lines.push('');

  return lines.join('\n');
}

module.exports = { formatResults };
