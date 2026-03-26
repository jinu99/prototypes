const { matchRules, runAssertions } = require('./rules');
const { logFailure } = require('./db');

/**
 * Express middleware that intercepts responses and runs assertion rules
 * asynchronously after the response is sent.
 */
function silentFailureDetector() {
  return (req, res, next) => {
    // Capture the original json method to intercept response body
    const originalJson = res.json.bind(res);
    let capturedBody = null;

    res.json = function (body) {
      capturedBody = body;
      return originalJson(body);
    };

    // After the response is finished, run assertions asynchronously
    res.on('finish', () => {
      // Only check 2xx responses — explicit errors are not "silent"
      if (res.statusCode < 200 || res.statusCode >= 300) return;

      const matched = matchRules(req.method, req.path);
      if (matched.length === 0) return;

      // Run assertions asynchronously (non-blocking)
      setImmediate(() => {
        for (const rule of matched) {
          const failures = runAssertions(rule.assertions, {
            req,
            res,
            responseBody: capturedBody,
          });

          for (const f of failures) {
            logFailure({
              method: req.method,
              path: req.path,
              statusCode: res.statusCode,
              ruleName: rule.name,
              assertionType: f.type,
              expected: f.expected,
              actual: f.actual,
              requestBody: JSON.stringify(req.body),
              responseBody: JSON.stringify(capturedBody),
            });
            console.log(`[SILENT FAILURE] ${rule.name}: ${f.expected} → got ${f.actual}`);
          }
        }
      });
    });

    next();
  };
}

module.exports = { silentFailureDetector };
