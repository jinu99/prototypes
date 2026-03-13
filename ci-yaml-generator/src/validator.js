const fs = require('fs');
const yaml = require('js-yaml');

const VALID_TRIGGERS = new Set([
  'push', 'pull_request', 'pull_request_target', 'workflow_dispatch',
  'schedule', 'release', 'workflow_call', 'issues', 'issue_comment',
  'create', 'delete', 'fork', 'watch', 'repository_dispatch',
]);

function validateYaml(filePath) {
  const errors = [];
  const warnings = [];

  // 1. Read and parse YAML
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    return { valid: false, errors: [`Cannot read file: ${err.message}`], warnings };
  }

  let doc;
  try {
    doc = yaml.load(content);
  } catch (err) {
    return { valid: false, errors: [`Invalid YAML syntax: ${err.message}`], warnings };
  }

  if (!doc || typeof doc !== 'object') {
    return { valid: false, errors: ['YAML document is empty or not an object'], warnings };
  }

  // 2. Check required top-level keys
  if (!doc.name) {
    warnings.push('Missing "name" field (recommended)');
  }

  if (!doc.on) {
    errors.push('Missing required "on" trigger definition');
  } else {
    // Validate triggers
    const triggers = typeof doc.on === 'string' ? [doc.on] : Object.keys(doc.on);
    for (const t of triggers) {
      if (!VALID_TRIGGERS.has(t)) {
        warnings.push(`Unknown trigger: "${t}"`);
      }
    }
  }

  if (!doc.jobs || typeof doc.jobs !== 'object') {
    errors.push('Missing required "jobs" section');
  } else {
    // 3. Validate each job
    for (const [jobId, job] of Object.entries(doc.jobs)) {
      if (!job['runs-on']) {
        errors.push(`Job "${jobId}": missing required "runs-on" field`);
      }
      if (!job.steps || !Array.isArray(job.steps) || job.steps.length === 0) {
        errors.push(`Job "${jobId}": missing or empty "steps" array`);
      } else {
        for (let i = 0; i < job.steps.length; i++) {
          const step = job.steps[i];
          if (!step.uses && !step.run) {
            errors.push(`Job "${jobId}", step ${i + 1}: must have either "uses" or "run"`);
          }
        }
      }

      // Validate needs references
      if (job.needs) {
        const needs = Array.isArray(job.needs) ? job.needs : [job.needs];
        for (const dep of needs) {
          if (!doc.jobs[dep]) {
            errors.push(`Job "${jobId}": depends on unknown job "${dep}"`);
          }
        }
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

module.exports = { validateYaml };
