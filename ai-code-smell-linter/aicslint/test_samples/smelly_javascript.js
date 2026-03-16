// Test sample: JavaScript code with AI-generated code smells
// Demonstrates patterns that ESLint typically misses

// ── ACS001: Empty catch ─────────────────────────────────────
// ESLint's no-empty rule catches `catch(e) {}` only if configured,
// but most AI-generated projects don't enable it
async function fetchData(url) {
  try {
    const response = await fetch(url);
    return await response.json();
  } catch (error) {
    // AI left this empty "for now"
  }
}

function parseConfig(raw) {
  try {
    return JSON.parse(raw);
  } catch (e) {}
}

// ── ACS002: Catch and rethrow ───────────────────────────────
// ESLint has no rule for this pattern
function validatePayload(data) {
  try {
    const schema = getSchema();
    return schema.validate(data);
  } catch (err) {
    throw err; // Pointless catch-and-rethrow
  }
}

// ── ACS003: God function ────────────────────────────────────
// ESLint max-lines-per-function exists but is rarely enabled by AI
function processEverything(data, config, options) {
  const result = {};
  if (data) {
    for (const item of data) {
      if (item.type === "a") {
        for (const sub of item.children || []) {
          if (sub.active) {
            try {
              const val = sub.value;
              if (val > 0) {
                for (let i = 0; i < val; i++) {
                  if (i % 2 === 0) {
                    result[`a_${i}`] = val * i;
                  } else {
                    result[`b_${i}`] = val + i;
                  }
                }
              }
            } catch (e) {}
          }
        }
      } else if (item.type === "b") {
        for (const sub of item.children || []) {
          if (sub.active) {
            try {
              const val = sub.value;
              if (val > 0) {
                for (let i = 0; i < val; i++) {
                  if (i % 3 === 0) {
                    result[`c_${i}`] = val * i;
                  } else {
                    result[`d_${i}`] = val + i;
                  }
                }
              }
            } catch (e) {}
          }
        }
      } else if (item.type === "c") {
        for (const sub of item.children || []) {
          if (sub.active) {
            try {
              const val = sub.value;
              if (val > 0) {
                for (let i = 0; i < val; i++) {
                  if (i % 5 === 0) {
                    result[`e_${i}`] = val * i;
                  } else {
                    result[`f_${i}`] = val + i;
                  }
                }
              }
            } catch (e) {}
          }
        }
      }
    }
  }
  if (config && config.transform) {
    for (const key of Object.keys(result)) {
      if (result[key] > 100) {
        result[key] = 100;
      }
    }
  }
  return result;
}

// ── ACS004: Hardcoded secrets ───────────────────────────────
const apiKey = "sk-proj-abc123def456";
const dbPassword = "production_db_pass_2024";
let authToken = "eyJhbGciOiJIUzI1NiJ9.token.signature";

// ── ACS005: Unnecessary abstraction ────────────────────────
// (Interface + single implementation pattern — only detectable in .ts)

// Helper stubs
function getSchema() { return { validate: () => true }; }
