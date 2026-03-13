const fs = require('fs');
const path = require('path');
const toml = require('@iarna/toml');
const rules = require('./rules.json');

function detectEcosystem(projectDir) {
  const results = [];

  for (const [key, eco] of Object.entries(rules.ecosystems)) {
    for (const file of eco.detectFiles) {
      if (fs.existsSync(path.join(projectDir, file))) {
        const result = analyzeEcosystem(key, eco, projectDir);
        results.push(result);
        break;
      }
    }
  }

  return results;
}

function analyzeEcosystem(key, eco, projectDir) {
  const result = {
    ecosystem: key,
    language: eco.language,
    packageManager: null,
    testRunner: null,
    linters: [],
    hasBuild: false,
    versions: [],
  };

  // Detect package manager
  result.packageManager = detectPackageManager(eco, projectDir);

  // Parse config and detect tools
  if (key === 'node') {
    analyzeNode(eco, projectDir, result);
  } else if (key === 'python') {
    analyzePython(eco, projectDir, result);
  } else if (key === 'go') {
    analyzeGo(eco, projectDir, result);
  }

  return result;
}

function detectPackageManager(eco, projectDir) {
  for (const [name, pm] of Object.entries(eco.packageManagers)) {
    if (pm.detectFiles) {
      for (const file of pm.detectFiles) {
        if (fs.existsSync(path.join(projectDir, file))) {
          return { name, install: pm.install };
        }
      }
    }
  }
  // Return default
  for (const [name, pm] of Object.entries(eco.packageManagers)) {
    if (pm.default) {
      return { name, install: pm.install };
    }
  }
  const first = Object.entries(eco.packageManagers)[0];
  return { name: first[0], install: first[1].install };
}

function analyzeNode(eco, projectDir, result) {
  const pkgPath = path.join(projectDir, 'package.json');
  let pkg = {};
  try {
    pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
  } catch {
    return;
  }

  const allDeps = {
    ...pkg.dependencies,
    ...pkg.devDependencies,
  };

  // Detect test runner
  for (const [name, runner] of Object.entries(eco.testRunners)) {
    if (runner.detectDeps.some(dep => dep in allDeps)) {
      result.testRunner = { name, command: runner.command };
      break;
    }
  }
  // Fallback: check scripts.test
  if (!result.testRunner && pkg.scripts?.test && !pkg.scripts.test.includes('no test specified')) {
    result.testRunner = { name: 'npm-test', command: 'npm test' };
  }

  // Detect linters
  for (const [name, linter] of Object.entries(eco.linters)) {
    if (linter.detectDeps.some(dep => dep in allDeps)) {
      result.linters.push({ name, command: linter.command });
    }
  }

  // Detect build
  if (pkg.scripts?.build) {
    result.hasBuild = true;
  }

  result.versions = eco.nodeVersions;
}

function analyzePython(eco, projectDir, result) {
  const tomlPath = path.join(projectDir, 'pyproject.toml');
  let config = {};
  try {
    config = toml.parse(fs.readFileSync(tomlPath, 'utf8'));
  } catch {
    return;
  }

  // Gather all dependency names
  const deps = new Set();
  // PEP 621 dependencies
  const projDeps = config.project?.dependencies || [];
  projDeps.forEach(d => deps.add(d.split(/[>=<!\s\[]/)[0].toLowerCase()));

  // Optional dependencies
  const optDeps = config.project?.['optional-dependencies'] || {};
  for (const group of Object.values(optDeps)) {
    group.forEach(d => deps.add(d.split(/[>=<!\s\[]/)[0].toLowerCase()));
  }

  // Poetry dependencies
  const poetryDeps = config.tool?.poetry?.dependencies || {};
  Object.keys(poetryDeps).forEach(d => deps.add(d.toLowerCase()));
  const poetryDevDeps = config.tool?.poetry?.['dev-dependencies'] || {};
  Object.keys(poetryDevDeps).forEach(d => deps.add(d.toLowerCase()));

  // uv dependencies
  const uvDeps = config.tool?.uv?.dependencies || [];
  uvDeps.forEach(d => deps.add(d.split(/[>=<!\s\[]/)[0].toLowerCase()));
  const uvDevDeps = config.tool?.uv?.['dev-dependencies'] || [];
  uvDevDeps.forEach(d => deps.add(d.split(/[>=<!\s\[]/)[0].toLowerCase()));

  // Detect test runner
  for (const [name, runner] of Object.entries(eco.testRunners)) {
    if (runner.detectDeps.length === 0) continue;
    if (runner.detectDeps.some(dep => deps.has(dep.toLowerCase()))) {
      result.testRunner = { name, command: runner.command };
      break;
    }
  }
  if (!result.testRunner) {
    result.testRunner = { name: 'unittest', command: eco.testRunners.unittest.command };
  }

  // Detect linters
  for (const [name, linter] of Object.entries(eco.linters)) {
    if (linter.detectDeps.some(dep => deps.has(dep.toLowerCase()))) {
      result.linters.push({ name, command: linter.command });
    }
  }

  // Refine package manager based on lock files and config
  if (fs.existsSync(path.join(projectDir, 'uv.lock'))) {
    result.packageManager = { name: 'uv', install: 'uv sync' };
  } else if (fs.existsSync(path.join(projectDir, 'poetry.lock'))) {
    result.packageManager = { name: 'poetry', install: 'poetry install' };
  } else if (fs.existsSync(path.join(projectDir, 'requirements.txt'))) {
    result.packageManager = { name: 'pip', install: 'pip install -r requirements.txt' };
  } else {
    // pyproject.toml exists but no lock file — use pip install with editable + dev extras
    const hasDevExtras = Object.keys(optDeps).length > 0;
    const installCmd = hasDevExtras
      ? `pip install -e ".[${Object.keys(optDeps).join(',')}]"`
      : 'pip install -e .';
    result.packageManager = { name: 'pip', install: installCmd };
  }

  result.versions = eco.pythonVersions;
}

function analyzeGo(eco, projectDir, result) {
  const modPath = path.join(projectDir, 'go.mod');
  let content = '';
  try {
    content = fs.readFileSync(modPath, 'utf8');
  } catch {
    return;
  }

  // Extract go version
  const versionMatch = content.match(/^go\s+(\d+\.\d+)/m);
  if (versionMatch) {
    const major = versionMatch[1];
    // Include detected version and next
    const allVersions = eco.goVersions;
    const idx = allVersions.indexOf(major);
    if (idx >= 0) {
      result.versions = allVersions.slice(idx);
    } else {
      result.versions = allVersions;
    }
  } else {
    result.versions = eco.goVersions;
  }

  // Go always has test
  result.testRunner = { name: 'gotest', command: eco.testRunners.gotest.command };

  // Detect linters by config files
  for (const [name, linter] of Object.entries(eco.linters)) {
    if (linter.detectFiles) {
      for (const file of linter.detectFiles) {
        if (fs.existsSync(path.join(projectDir, file))) {
          result.linters.push({ name, command: linter.command });
          break;
        }
      }
    }
  }

  // Default linter: go vet
  if (result.linters.length === 0) {
    result.linters.push({ name: 'govet', command: eco.linters.govet.command });
  }

  result.hasBuild = true;
}

module.exports = { detectEcosystem };
