const yaml = require('js-yaml');
const rules = require('./rules.json');

function generateWorkflow(detections) {
  if (detections.length === 0) {
    throw new Error('No supported ecosystems detected in this project.');
  }

  const workflow = {
    name: 'CI',
    on: {
      push: { branches: ['main', 'master'] },
      pull_request: { branches: ['main', 'master'] },
    },
    permissions: { contents: 'read' },
    jobs: {},
  };

  for (const det of detections) {
    const prefix = detections.length > 1 ? `${det.ecosystem}-` : '';
    addLintJob(workflow, det, prefix);
    addTestJob(workflow, det, prefix);
    addBuildJob(workflow, det, prefix);
  }

  addSecurityJob(workflow, detections);

  return yaml.dump(workflow, {
    lineWidth: 120,
    noRefs: true,
    quotingType: '"',
    forceQuotes: false,
  });
}

function addLintJob(workflow, det, prefix) {
  const jobId = `${prefix}lint`;

  if (det.linters.length === 0) return;

  const steps = [{ uses: 'actions/checkout@v4' }];

  addSetupStep(steps, det);
  addInstallStep(steps, det);

  for (const linter of det.linters) {
    steps.push({
      name: `Lint with ${linter.name}`,
      run: linter.command,
    });
  }

  workflow.jobs[jobId] = {
    name: `Lint (${det.language})`,
    'runs-on': 'ubuntu-latest',
    steps,
  };
}

function addTestJob(workflow, det, prefix) {
  const jobId = `${prefix}test`;

  if (!det.testRunner) return;

  const needsLint = det.linters.length > 0 ? [`${prefix}lint`] : undefined;

  const steps = [{ uses: 'actions/checkout@v4' }];
  addSetupStep(steps, det);
  addInstallStep(steps, det);

  steps.push({
    name: `Test with ${det.testRunner.name}`,
    run: det.testRunner.command,
  });

  const job = {
    name: `Test (${det.language})`,
    'runs-on': 'ubuntu-latest',
    steps,
  };

  if (needsLint) job.needs = needsLint;

  // Matrix for versions
  if (det.versions && det.versions.length > 1) {
    const versionKey = getVersionKey(det.ecosystem);
    job.strategy = {
      matrix: { [versionKey]: det.versions },
    };
    // Update setup step to use matrix version
    updateSetupVersion(job.steps, det.ecosystem, `\${{ matrix.${versionKey} }}`);
  }

  workflow.jobs[jobId] = job;
}

function addBuildJob(workflow, det, prefix) {
  const jobId = `${prefix}build`;

  if (!det.hasBuild) return;

  const eco = rules.ecosystems[det.ecosystem];
  const needs = [];
  if (det.testRunner) needs.push(`${prefix}test`);
  else if (det.linters.length > 0) needs.push(`${prefix}lint`);

  const steps = [{ uses: 'actions/checkout@v4' }];
  addSetupStep(steps, det);
  addInstallStep(steps, det);

  steps.push({
    name: 'Build',
    run: eco.buildCommands.command,
  });

  const job = {
    name: `Build (${det.language})`,
    'runs-on': 'ubuntu-latest',
    steps,
  };

  if (needs.length > 0) job.needs = needs;

  workflow.jobs[jobId] = job;
}

function addSecurityJob(workflow, detections) {
  const needs = [];
  for (const det of detections) {
    const prefix = detections.length > 1 ? `${det.ecosystem}-` : '';
    if (det.testRunner) needs.push(`${prefix}test`);
    else if (det.linters.length > 0) needs.push(`${prefix}lint`);
  }

  workflow.jobs.security = {
    name: 'Security Scan',
    'runs-on': 'ubuntu-latest',
    ...(needs.length > 0 ? { needs } : {}),
    steps: [
      { uses: 'actions/checkout@v4' },
      {
        name: rules.security.semgrep.name,
        uses: rules.security.semgrep.action,
      },
      {
        name: rules.security.trufflehog.name,
        uses: rules.security.trufflehog.action,
        with: rules.security.trufflehog.args,
      },
    ],
  };
}

function addSetupStep(steps, det) {
  if (det.ecosystem === 'node') {
    steps.push({
      name: 'Setup Node.js',
      uses: 'actions/setup-node@v4',
      with: { 'node-version': det.versions?.[det.versions.length - 1] || '20' },
    });
  } else if (det.ecosystem === 'python') {
    steps.push({
      name: 'Setup Python',
      uses: 'actions/setup-python@v5',
      with: { 'python-version': det.versions?.[det.versions.length - 1] || '3.12' },
    });
  } else if (det.ecosystem === 'go') {
    steps.push({
      name: 'Setup Go',
      uses: 'actions/setup-go@v5',
      with: { 'go-version': det.versions?.[det.versions.length - 1] || '1.23' },
    });
  }
}

function addInstallStep(steps, det) {
  if (det.packageManager) {
    steps.push({
      name: 'Install dependencies',
      run: det.packageManager.install,
    });
  }
}

function getVersionKey(ecosystem) {
  if (ecosystem === 'node') return 'node-version';
  if (ecosystem === 'python') return 'python-version';
  if (ecosystem === 'go') return 'go-version';
  return 'version';
}

function updateSetupVersion(steps, ecosystem, expr) {
  const actionMap = { node: 'actions/setup-node', python: 'actions/setup-python', go: 'actions/setup-go' };
  const keyMap = { node: 'node-version', python: 'python-version', go: 'go-version' };
  for (const step of steps) {
    if (step.uses && step.uses.startsWith(actionMap[ecosystem])) {
      step.with[keyMap[ecosystem]] = expr;
    }
  }
}

module.exports = { generateWorkflow };
