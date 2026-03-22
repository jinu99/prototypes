// Test file with various dark path patterns

// 1. Empty catch block (should detect — high severity)
async function fetchData() {
  try {
    const res = await fetch('/api/data');
    return res.json();
  } catch (err) {
  }
}

// 2. Catch block without logging (should detect — medium severity)
function parseConfig(raw) {
  try {
    return JSON.parse(raw);
  } catch (err) {
    return {};
  }
}

// 3. Catch block WITH logging (should NOT detect)
function safeRead(path) {
  try {
    return require('fs').readFileSync(path, 'utf-8');
  } catch (err) {
    console.error('Failed to read file:', err);
    return null;
  }
}

// 4. Error callback with ignored error param (should detect)
const fs = require('fs');
fs.readFile('/tmp/test', function (err, data) {
  process.stdout.write(data);
});

// 5. Error callback that properly handles error (should NOT detect)
fs.readFile('/tmp/test', function (err, data) {
  if (err) {
    console.error(err);
    return;
  }
  process.stdout.write(data);
});

// 6. Arrow function error callback — ignored (should detect)
somePromise.then(data => {
  use(data);
}).catch(error => {
  // just swallow it
});

// 7. Catch with rethrow (should NOT detect)
function strict() {
  try {
    riskyOp();
  } catch (e) {
    throw new Error('Wrapped: ' + e.message);
  }
}

// 8. @dark-path-ignore — should be excluded
function ignoredHandler() {
  try {
    something();
  // @dark-path-ignore
  } catch (err) {
    // intentionally empty
  }
}

// 9. Error callback with Sentry (should NOT detect)
fetchStuff().catch(err => {
  Sentry.captureException(err);
});
