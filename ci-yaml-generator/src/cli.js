#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { detectEcosystem } = require('./detector');
const { generateWorkflow } = require('./generator');
const { validateYaml } = require('./validator');

const HELP = `
ci-gen — CI/CD YAML Generator

Usage:
  ci-gen init [directory]       Detect project and generate GitHub Actions workflow
  ci-gen validate <file>        Validate a GitHub Actions YAML file
  ci-gen detect [directory]     Show detection results without generating

Options:
  --output, -o <path>   Output file path (default: .github/workflows/ci.yml)
  --dry-run             Print YAML to stdout without writing file
  --help, -h            Show this help
`;

function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(HELP);
    process.exit(0);
  }

  const command = args[0];

  if (command === 'init') {
    cmdInit(args.slice(1));
  } else if (command === 'validate') {
    cmdValidate(args.slice(1));
  } else if (command === 'detect') {
    cmdDetect(args.slice(1));
  } else {
    console.error(`Unknown command: ${command}`);
    console.log(HELP);
    process.exit(1);
  }
}

function parseFlags(args) {
  const flags = { dir: '.', output: null, dryRun: false };
  let i = 0;
  while (i < args.length) {
    if (args[i] === '--output' || args[i] === '-o') {
      flags.output = args[++i];
    } else if (args[i] === '--dry-run') {
      flags.dryRun = true;
    } else if (!args[i].startsWith('-')) {
      flags.dir = args[i];
    }
    i++;
  }
  return flags;
}

function cmdInit(args) {
  const flags = parseFlags(args);
  const projectDir = path.resolve(flags.dir);

  console.log(`\n🔍 Scanning project: ${projectDir}\n`);

  const detections = detectEcosystem(projectDir);

  if (detections.length === 0) {
    console.error('❌ No supported ecosystems detected.');
    console.error('   Supported: Node.js (package.json), Python (pyproject.toml), Go (go.mod)');
    process.exit(1);
  }

  // Print detection summary
  for (const det of detections) {
    console.log(`✅ Detected: ${det.language}`);
    console.log(`   Package Manager: ${det.packageManager?.name || 'none'}`);
    console.log(`   Test Runner: ${det.testRunner?.name || 'none'}`);
    console.log(`   Linters: ${det.linters.map(l => l.name).join(', ') || 'none'}`);
    console.log(`   Has Build: ${det.hasBuild ? 'yes' : 'no'}`);
    console.log('');
  }

  // Generate YAML
  const yamlContent = generateWorkflow(detections);

  if (flags.dryRun) {
    console.log('--- Generated Workflow ---\n');
    console.log(yamlContent);
    return;
  }

  const outputPath = flags.output
    ? path.resolve(flags.output)
    : path.join(projectDir, '.github', 'workflows', 'ci.yml');

  const outputDir = path.dirname(outputPath);
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(outputPath, yamlContent, 'utf8');

  console.log(`📄 Workflow written to: ${outputPath}`);

  // Auto-validate
  const result = validateYaml(outputPath);
  if (result.valid) {
    console.log('✅ YAML validation passed');
  } else {
    console.log('⚠️  YAML validation issues:');
    result.errors.forEach(e => console.log(`   ❌ ${e}`));
  }
  if (result.warnings.length > 0) {
    result.warnings.forEach(w => console.log(`   ⚠️  ${w}`));
  }
}

function cmdValidate(args) {
  if (args.length === 0) {
    console.error('Usage: ci-gen validate <file>');
    process.exit(1);
  }

  const filePath = path.resolve(args[0]);
  console.log(`\n🔍 Validating: ${filePath}\n`);

  const result = validateYaml(filePath);

  if (result.errors.length > 0) {
    console.log('Errors:');
    result.errors.forEach(e => console.log(`  ❌ ${e}`));
  }

  if (result.warnings.length > 0) {
    console.log('Warnings:');
    result.warnings.forEach(w => console.log(`  ⚠️  ${w}`));
  }

  if (result.valid) {
    console.log('✅ Valid GitHub Actions workflow');
  } else {
    console.log('\n❌ Validation failed');
    process.exit(1);
  }
}

function cmdDetect(args) {
  const flags = parseFlags(args);
  const projectDir = path.resolve(flags.dir);

  console.log(`\n🔍 Detecting project: ${projectDir}\n`);

  const detections = detectEcosystem(projectDir);

  if (detections.length === 0) {
    console.log('No supported ecosystems found.');
    process.exit(1);
  }

  console.log(JSON.stringify(detections, null, 2));
}

main();
