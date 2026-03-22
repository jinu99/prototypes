const { parseSource } = require('./parser');

// Patterns that indicate observability (logging, error reporting)
const OBSERVABILITY_PATTERNS = [
  // console methods
  /console\.(log|error|warn|info|debug|trace)/,
  // common loggers
  /logger\.(log|error|warn|info|debug|fatal|trace)/,
  /log\.(log|error|warn|info|debug|fatal|trace)/,
  // error reporting services
  /Sentry\./,
  /Bugsnag\./,
  /rollbar\./,
  /newrelic\./,
  /datadog\./,
  // throw/rethrow
  /\bthrow\b/,
  // process.exit (intentional crash)
  /process\.exit/,
  // error propagation via callback
  /\bcallback\s*\(\s*(err|error|e|ex)\b/,
  /\bcb\s*\(\s*(err|error|e|ex)\b/,
  /\bnext\s*\(\s*(err|error|e|ex)\b/,
  /\breject\s*\(/,
  /\bdone\s*\(\s*(err|error|e|ex)\b/,
  // framework error propagation
  /\breply\.send\s*\(\s*(err|error|e|ex)\b/,
  /\bres\.send\s*\(\s*(err|error|e|ex)\b/,
  /\bres\.status\b/,
  /\.emit\s*\(\s*['"]error['"]/,
  /\.publish\s*\(/,
  // common reporting functions
  /reportError/,
  /captureException/,
  /captureMessage/,
  /notify/,
  /alert/,
];

const IGNORE_COMMENT = '@dark-path-ignore';

/**
 * Check if a node's source text contains observability calls.
 */
function hasObservability(nodeText) {
  return OBSERVABILITY_PATTERNS.some(p => p.test(nodeText));
}

/**
 * Check if source has an ignore comment near the given line range.
 */
function hasIgnoreComment(sourceLines, startLine, endLine) {
  // Check the line before the block and lines within
  const checkStart = Math.max(0, startLine - 1);
  const checkEnd = Math.min(sourceLines.length - 1, endLine);
  for (let i = checkStart; i <= checkEnd; i++) {
    if (sourceLines[i].includes(IGNORE_COMMENT)) {
      return true;
    }
  }
  return false;
}

/**
 * Check if the catch parameter is passed as argument to any function call in body.
 * This covers patterns like: preValidationCallback(err, ...), onErrorHook(reply, e), etc.
 */
function isErrorPropagated(bodyNode, paramName) {
  const text = bodyNode.text;
  if (!paramName) {
    // Parameterless catch — check if body calls error-related functions
    return /\b(done|callback|cb|next|reject)\s*\(\s*new\s/.test(text);
  }
  // Check if error param is passed to any function call
  const callRegex = new RegExp(`\\w+\\s*\\([^)]*\\b${paramName}\\b`);
  if (callRegex.test(text)) return true;
  // Check if error is reassigned to outer variable (captured for later use)
  const assignRegex = new RegExp(`\\w+\\s*=\\s*${paramName}\\s*[;\\n]`);
  if (assignRegex.test(text)) return true;
  return false;
}

/**
 * Check if a catch clause body is a dark path.
 */
function analyzeCatchClause(node, sourceLines, source) {
  const body = node.childForFieldName('body');
  if (!body) return null;

  const startLine = node.startPosition.row;
  const endLine = node.endPosition.row;

  if (hasIgnoreComment(sourceLines, startLine, endLine)) {
    return null;
  }

  const bodyText = body.text;

  // Empty catch block (including catch without parameter: `catch { }`)
  if (bodyText.replace(/[{}]/g, '').trim() === '') {
    return {
      type: 'empty-catch',
      line: startLine + 1,
      endLine: endLine + 1,
      message: 'Empty catch block — error is silently swallowed',
      severity: 'high',
    };
  }

  // Get catch parameter name
  const paramNode = node.children.find(c => c.type === 'identifier' || c.type === 'catch_parameter');
  const paramName = paramNode ? paramNode.text : null;

  // Check if error is propagated via function call, reassignment, etc.
  if (isErrorPropagated(body, paramName)) {
    return null; // Error is being propagated
  }

  // Catch block without observability
  if (!hasObservability(bodyText)) {
    return {
      type: 'silent-catch',
      line: startLine + 1,
      endLine: endLine + 1,
      message: 'Catch block has no logging, error reporting, or rethrow',
      severity: 'medium',
    };
  }

  return null; // Has observability — not a dark path
}

/**
 * Detect error callback patterns where the error parameter is ignored.
 * Looks for: (err) => { ... } or function(err) { ... } where err is never used.
 */
function analyzeErrorCallback(node, sourceLines, source) {
  // Look for function/arrow_function nodes
  if (node.type !== 'arrow_function' && node.type !== 'function' &&
      node.type !== 'function_expression') {
    return null;
  }

  // Arrow functions with single param (no parens) use 'parameter' field
  let paramName;
  const singleParam = node.childForFieldName('parameter');
  if (singleParam) {
    paramName = singleParam.text;
  } else {
    const params = node.childForFieldName('parameters') || node.children.find(c => c.type === 'formal_parameters');
    if (!params) return null;
    const paramNodes = params.namedChildren;
    if (paramNodes.length === 0) return null;
    paramName = paramNodes[0].text;
  }

  // Check if first param looks like an error param
  if (!/^(err|error|e|ex|exception)$/i.test(paramName)) {
    return null;
  }

  const body = node.childForFieldName('body');
  if (!body) return null;

  const startLine = node.startPosition.row;
  const endLine = node.endPosition.row;

  if (hasIgnoreComment(sourceLines, startLine, endLine)) {
    return null;
  }

  const bodyText = body.text;

  // Check if the error param is used in the body (beyond the parameter itself)
  const paramRegex = new RegExp(`\\b${paramName}\\b`);
  if (!paramRegex.test(bodyText)) {
    return {
      type: 'ignored-error-param',
      line: startLine + 1,
      endLine: endLine + 1,
      message: `Error parameter '${paramName}' is never used in callback body`,
      severity: 'medium',
    };
  }

  // If error param is used in any way, it's not a "dark path" per spec
  // (spec targets genuinely *ignored* error params, not just unlogged ones)
  return null;
}

/**
 * Walk the AST tree and collect dark paths.
 */
function walkTree(node, sourceLines, source, findings) {
  if (node.type === 'catch_clause') {
    const finding = analyzeCatchClause(node, sourceLines, source);
    if (finding) findings.push(finding);
  }

  // Check for error callbacks in call expressions
  if (node.type === 'arrow_function' || node.type === 'function_expression') {
    const finding = analyzeErrorCallback(node, sourceLines, source);
    if (finding) findings.push(finding);
  }

  for (let i = 0; i < node.childCount; i++) {
    walkTree(node.child(i), sourceLines, source, findings);
  }
}

/**
 * Analyze a single file's source code.
 * Returns { findings, totalErrorPaths, observedErrorPaths }
 */
function analyzeSource(source, ext) {
  const tree = parseSource(source, ext);
  if (!tree) return null;

  const sourceLines = source.split('\n');
  const findings = [];

  walkTree(tree.rootNode, sourceLines, source, findings);

  // Count total error paths (excluding @dark-path-ignore'd ones)
  const totalErrorPaths = countErrorPaths(tree.rootNode, sourceLines);
  const darkPaths = findings.length;
  const observedErrorPaths = totalErrorPaths - darkPaths;

  return {
    findings,
    totalErrorPaths,
    observedErrorPaths,
    darkPaths,
  };
}

/**
 * Count all error-handling paths in the AST.
 */
function countErrorPaths(node, sourceLines) {
  let count = 0;

  if (node.type === 'catch_clause') {
    if (!hasIgnoreComment(sourceLines, node.startPosition.row, node.endPosition.row)) {
      count++;
    }
  }

  // Count error callbacks
  if (node.type === 'arrow_function' || node.type === 'function_expression') {
    let paramName = null;
    const singleParam = node.childForFieldName('parameter');
    if (singleParam) {
      paramName = singleParam.text;
    } else {
      const params = node.childForFieldName('parameters') || node.children.find(c => c.type === 'formal_parameters');
      if (params && params.namedChildren.length > 0) {
        paramName = params.namedChildren[0].text;
      }
    }
    if (paramName && /^(err|error|e|ex|exception)$/i.test(paramName)) {
      if (!hasIgnoreComment(sourceLines, node.startPosition.row, node.endPosition.row)) {
        count++;
      }
    }
  }

  for (let i = 0; i < node.childCount; i++) {
    count += countErrorPaths(node.child(i), sourceLines);
  }

  return count;
}

module.exports = { analyzeSource, hasObservability, OBSERVABILITY_PATTERNS };
