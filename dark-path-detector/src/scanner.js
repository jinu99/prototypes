const fs = require('fs');
const path = require('path');
const { glob } = require('glob');
const { analyzeSource } = require('./analyzer');

const SUPPORTED_EXTENSIONS = ['.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx'];

const DEFAULT_IGNORE = [
  'node_modules/**',
  'dist/**',
  'build/**',
  'coverage/**',
  '.git/**',
  '*.min.js',
  '*.bundle.js',
  'vendor/**',
  '__tests__/**',
  'test/**',
  'tests/**',
  '**/*.test.*',
  '**/*.spec.*',
];

/**
 * Scan a directory for JS/TS files and analyze them.
 */
async function scanDirectory(dir, options = {}) {
  const { ignore = DEFAULT_IGNORE } = options;
  const absDir = path.resolve(dir);

  const patterns = SUPPORTED_EXTENSIONS.map(ext => `**/*${ext}`);
  const files = await glob(patterns, {
    cwd: absDir,
    ignore,
    absolute: true,
    nodir: true,
  });

  const results = {
    files: [],
    summary: {
      totalFiles: 0,
      filesWithDarkPaths: 0,
      totalErrorPaths: 0,
      totalDarkPaths: 0,
      observedErrorPaths: 0,
      coveragePercent: 0,
    },
  };

  for (const filePath of files) {
    const ext = path.extname(filePath);
    let source;
    try {
      source = fs.readFileSync(filePath, 'utf-8');
    } catch {
      continue;
    }

    let analysis;
    try {
      analysis = analyzeSource(source, ext);
    } catch {
      continue; // Skip files that crash the parser
    }
    if (!analysis) continue;

    results.summary.totalFiles++;
    results.summary.totalErrorPaths += analysis.totalErrorPaths;
    results.summary.observedErrorPaths += analysis.observedErrorPaths;
    results.summary.totalDarkPaths += analysis.darkPaths;

    if (analysis.findings.length > 0) {
      results.summary.filesWithDarkPaths++;
      results.files.push({
        path: path.relative(absDir, filePath),
        findings: analysis.findings,
        totalErrorPaths: analysis.totalErrorPaths,
        darkPaths: analysis.darkPaths,
      });
    }
  }

  // Calculate coverage
  if (results.summary.totalErrorPaths > 0) {
    results.summary.coveragePercent = Math.round(
      (results.summary.observedErrorPaths / results.summary.totalErrorPaths) * 100
    );
  } else {
    results.summary.coveragePercent = 100; // No error paths = fully covered
  }

  return results;
}

module.exports = { scanDirectory, SUPPORTED_EXTENSIONS, DEFAULT_IGNORE };
