const fs = require('fs');
const yaml = require('js-yaml');
const path = require('path');

/**
 * Load assertion rules from a YAML file.
 *
 * Rule format:
 *   rules:
 *     - name: "order-creation"
 *       endpoint: "POST /api/orders"
 *       assertions:
 *         - type: "body_contains"
 *           field: "id"
 *           condition: "exists"
 *         - type: "body_check"
 *           field: "status"
 *           condition: "equals"
 *           value: "created"
 *         - type: "callback"
 *           fn: "checkOrderInDb"
 */

let rules = [];
let callbackRegistry = {};

function loadRules(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const parsed = yaml.load(content);
  rules = (parsed.rules || []).map(r => ({
    ...r,
    _method: r.endpoint.split(' ')[0].toUpperCase(),
    _path: r.endpoint.split(' ').slice(1).join(' '),
  }));
  return rules;
}

function registerCallback(name, fn) {
  callbackRegistry[name] = fn;
}

function getCallback(name) {
  return callbackRegistry[name];
}

function matchRules(method, reqPath) {
  return rules.filter(r => {
    if (r._method !== method.toUpperCase()) return false;
    // Simple path matching: exact or pattern with :param
    const ruleSegments = r._path.split('/');
    const reqSegments = reqPath.split('?')[0].split('/');
    if (ruleSegments.length !== reqSegments.length) return false;
    return ruleSegments.every((seg, i) => seg.startsWith(':') || seg === reqSegments[i]);
  });
}

function runAssertions(assertions, { req, res, responseBody }) {
  const failures = [];
  let body;
  try { body = typeof responseBody === 'string' ? JSON.parse(responseBody) : responseBody; } catch { body = responseBody; }

  for (const assertion of assertions) {
    switch (assertion.type) {
      case 'body_contains': {
        const val = getNestedField(body, assertion.field);
        if (assertion.condition === 'exists' && (val === undefined || val === null)) {
          failures.push({ ...assertion, expected: `field "${assertion.field}" exists`, actual: 'missing' });
        }
        break;
      }
      case 'body_check': {
        const val = getNestedField(body, assertion.field);
        if (assertion.condition === 'equals' && val !== assertion.value) {
          failures.push({ ...assertion, expected: `${assertion.field} == ${assertion.value}`, actual: String(val) });
        }
        if (assertion.condition === 'not_empty' && (!val || (Array.isArray(val) && val.length === 0))) {
          failures.push({ ...assertion, expected: `${assertion.field} not empty`, actual: String(val) });
        }
        if (assertion.condition === 'gt' && (typeof val !== 'number' || val <= Number(assertion.value))) {
          failures.push({ ...assertion, expected: `${assertion.field} > ${assertion.value}`, actual: String(val) });
        }
        break;
      }
      case 'callback': {
        const fn = getCallback(assertion.fn);
        if (fn) {
          const result = fn({ req, res, responseBody: body });
          if (result && !result.pass) {
            failures.push({ ...assertion, expected: result.expected || 'callback pass', actual: result.actual || 'callback failed' });
          }
        }
        break;
      }
      default:
        break;
    }
  }
  return failures;
}

function getNestedField(obj, fieldPath) {
  if (!obj || typeof obj !== 'object') return undefined;
  return fieldPath.split('.').reduce((o, k) => (o && typeof o === 'object' ? o[k] : undefined), obj);
}

function getRules() {
  return rules;
}

module.exports = { loadRules, registerCallback, matchRules, runAssertions, getRules };
