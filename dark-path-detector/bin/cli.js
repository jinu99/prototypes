#!/usr/bin/env node

const path = require('path');
const { scanDirectory } = require('../src/scanner');
const { formatResults } = require('../src/formatter');

function printUsage() {
  console.log(`
  Usage: dark-path-detector <directory> [options]

  Options:
    --json       Output results as JSON
    --verbose    Show detailed information
    --ignore     Additional glob patterns to ignore (comma-separated)
    --help       Show this help message

  Examples:
    dark-path-detector ./src
    dark-path-detector ./my-project --json
    dark-path-detector . --ignore "test/**,scripts/**"
  `);
}

async function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.length === 0) {
    printUsage();
    process.exit(0);
  }

  // Parse arguments
  const dir = args.find(a => !a.startsWith('--')) || '.';
  const json = args.includes('--json');
  const verbose = args.includes('--verbose');

  const ignoreIdx = args.indexOf('--ignore');
  let extraIgnore = [];
  if (ignoreIdx !== -1 && args[ignoreIdx + 1]) {
    extraIgnore = args[ignoreIdx + 1].split(',').map(s => s.trim());
  }

  const targetDir = path.resolve(dir);
  const fs = require('fs');

  if (!fs.existsSync(targetDir)) {
    console.error(`Error: directory not found: ${targetDir}`);
    process.exit(2);
  }

  try {
    const results = await scanDirectory(targetDir, {
      ignore: undefined, // use defaults
      ...(extraIgnore.length > 0 && {
        ignore: [
          'node_modules/**', 'dist/**', 'build/**', 'coverage/**',
          '.git/**', '*.min.js', '*.bundle.js', 'vendor/**',
          ...extraIgnore,
        ],
      }),
    });

    const output = formatResults(results, { json, verbose });
    console.log(output);

    // Exit with non-zero if dark paths found (useful for CI)
    if (results.summary.totalDarkPaths > 0) {
      process.exit(1);
    }
  } catch (err) {
    console.error(`Error scanning directory: ${err.message}`);
    process.exit(2);
  }
}

main();
