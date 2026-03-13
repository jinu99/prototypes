/**
 * E2E functional test via HTTP calls.
 * Tests the full flow: spec parsing, mock API, proxy, validation, and HTML serving.
 * Run with: node test-e2e.js
 * Requires the server to be running on port 4567.
 */

const BASE = "http://127.0.0.1:4567";
let passed = 0;
let failed = 0;

async function test(name, fn) {
  try {
    await fn();
    console.log(`  PASS  ${name}`);
    passed++;
  } catch (err) {
    console.log(`  FAIL  ${name}: ${err.message}`);
    failed++;
  }
}

function assert(condition, msg) {
  if (!condition) throw new Error(msg || "Assertion failed");
}

async function fetchJSON(path, options) {
  const res = await fetch(BASE + path, options);
  return res.json();
}

async function run() {
  console.log("\n=== OpenAPI Form Tester — E2E Tests ===\n");

  // ─── 1. Spec API ───
  await test("GET /api/spec returns parsed spec with 5 endpoints", async () => {
    const spec = await fetchJSON("/api/spec");
    assert(spec.title === "Pet Store (Demo)", "title mismatch: " + spec.title);
    assert(spec.endpoints.length === 5, "expected 5 endpoints, got " + spec.endpoints.length);
    assert(spec.servers[0].url.includes("4567"), "server URL should include port 4567");
  });

  await test("Spec endpoints have correct methods", async () => {
    const spec = await fetchJSON("/api/spec");
    const methods = spec.endpoints.map((e) => e.method + " " + e.path).sort();
    assert(methods.includes("GET /pets"), "missing GET /pets");
    assert(methods.includes("POST /pets"), "missing POST /pets");
    assert(methods.includes("POST /orders"), "missing POST /orders");
    assert(methods.includes("PUT /settings"), "missing PUT /settings");
  });

  await test("POST /pets endpoint has requestBody schema", async () => {
    const spec = await fetchJSON("/api/spec");
    const postPets = spec.endpoints.find((e) => e.method === "POST" && e.path === "/pets");
    assert(postPets.requestBody, "requestBody should exist");
    assert(postPets.requestBody.schema.properties.name, "should have name property");
    assert(postPets.requestBody.schema.properties.species, "should have species property");
    assert(postPets.requestBody.schema.properties.species.enum, "species should be enum");
  });

  await test("Schema includes all types: string, number, boolean, object, array", async () => {
    const spec = await fetchJSON("/api/spec");
    const orderSchema = spec.endpoints.find((e) => e.operationId === "createOrder").requestBody.schema;
    const types = new Set();
    function collectTypes(s) {
      if (s.type) types.add(s.type);
      if (s.properties) Object.values(s.properties).forEach(collectTypes);
      if (s.items) collectTypes(s.items);
    }
    collectTypes(orderSchema);
    assert(types.has("integer"), "missing integer: " + [...types]);
    assert(types.has("boolean"), "missing boolean: " + [...types]);
    assert(types.has("string"), "missing string: " + [...types]);
    assert(types.has("object"), "missing object: " + [...types]);
  });

  // ─── 2. Mock API ───
  await test("GET /mock/pets returns pet list with drift (createdAt)", async () => {
    const res = await fetch(BASE + "/mock/pets");
    const data = await res.json();
    assert(Array.isArray(data), "should be array");
    assert(data.length >= 2, "should have at least 2 pets");
    assert(data[0].createdAt, "should have undocumented createdAt field");
  });

  await test("POST /mock/pets creates a pet", async () => {
    const res = await fetch(BASE + "/mock/pets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Test", species: "bird", age: 1 }),
    });
    const data = await res.json();
    assert(res.status === 201, "should return 201");
    assert(data.id, "should have id");
    assert(data.name === "Test", "name mismatch");
  });

  await test("POST /mock/orders returns undocumented totalPrice", async () => {
    const res = await fetch(BASE + "/mock/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ petId: 1, quantity: 3 }),
    });
    const data = await res.json();
    assert(data.totalPrice, "should have undocumented totalPrice");
    assert(data.status === "pending", "should have status");
  });

  // ─── 3. Proxy ───
  await test("POST /api/send proxies GET requests", async () => {
    const result = await fetchJSON("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: BASE + "/mock/pets", method: "GET" }),
    });
    assert(result.status === 200, "status should be 200");
    assert(Array.isArray(result.body), "body should be array");
  });

  await test("POST /api/send proxies POST requests with body", async () => {
    const result = await fetchJSON("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: BASE + "/mock/pets",
        method: "POST",
        body: { name: "Proxy", species: "fish" },
      }),
    });
    assert(result.status === 201, "status should be 201");
    assert(result.body.name === "Proxy", "name should be Proxy");
  });

  // ─── 4. Validation ───
  await test("POST /api/validate detects type mismatch", async () => {
    const result = await fetchJSON("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        responseBody: { id: 1, name: "Test", species: "dog", vaccinated: "true" },
        schema: {
          type: "object",
          required: ["id", "name", "species"],
          properties: {
            id: { type: "integer" },
            name: { type: "string" },
            species: { type: "string" },
            vaccinated: { type: "boolean" },
          },
        },
      }),
    });
    assert(result.count >= 1, "should detect at least 1 drift");
    const mismatch = result.drifts.find((d) => d.type === "type_mismatch");
    assert(mismatch, "should have type_mismatch");
    assert(mismatch.path === "vaccinated", "path should be vaccinated");
  });

  await test("POST /api/validate detects undocumented fields", async () => {
    const result = await fetchJSON("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        responseBody: { id: 1, name: "Test", extraField: "surprise" },
        schema: {
          type: "object",
          properties: { id: { type: "integer" }, name: { type: "string" } },
        },
      }),
    });
    const undoc = result.drifts.find((d) => d.type === "undocumented");
    assert(undoc, "should detect undocumented field");
    assert(undoc.path === "extraField", "path should be extraField");
  });

  await test("POST /api/validate detects missing required fields", async () => {
    const result = await fetchJSON("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        responseBody: { id: 1 },
        schema: {
          type: "object",
          required: ["id", "name"],
          properties: { id: { type: "integer" }, name: { type: "string" } },
        },
      }),
    });
    const missing = result.drifts.find((d) => d.type === "missing");
    assert(missing, "should detect missing field");
    assert(missing.path === "name", "path should be name");
  });

  await test("POST /api/validate returns 0 drifts for conforming response", async () => {
    const result = await fetchJSON("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        responseBody: { id: 1, name: "Test", species: "dog" },
        schema: {
          type: "object",
          required: ["id", "name", "species"],
          properties: {
            id: { type: "integer" },
            name: { type: "string" },
            species: { type: "string" },
          },
        },
      }),
    });
    assert(result.count === 0, "should have 0 drifts, got " + result.count);
  });

  // ─── 5. HTML Serving ───
  await test("GET / serves index.html with correct structure", async () => {
    const res = await fetch(BASE + "/");
    const html = await res.text();
    assert(html.includes("OpenAPI Form Tester"), "should have title");
    assert(html.includes("endpoint-list"), "should have endpoint list");
    assert(html.includes("mainPanel"), "should have main panel");
    assert(html.includes("app.js"), "should load app.js");
    assert(html.includes("style.css"), "should load style.css");
  });

  await test("GET /app.js serves JavaScript", async () => {
    const res = await fetch(BASE + "/app.js");
    const js = await res.text();
    assert(js.includes("renderEndpointList"), "should have endpoint renderer");
    assert(js.includes("buildSchemaForm"), "should have form builder");
    assert(js.includes("validateDrift"), "should have drift validator");
    assert(js.includes("renderDrift"), "should have drift renderer");
  });

  // ─── 6. Full Flow (proxy + validate) ───
  await test("Full flow: proxy GET /pets then validate shows drift", async () => {
    const spec = await fetchJSON("/api/spec");
    const getPets = spec.endpoints.find((e) => e.method === "GET" && e.path === "/pets");
    const responseSchema = getPets.responses["200"].schema;

    const proxyResult = await fetchJSON("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: BASE + "/mock/pets", method: "GET" }),
    });

    const validateResult = await fetchJSON("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        responseBody: proxyResult.body,
        schema: responseSchema,
      }),
    });

    assert(validateResult.count > 0, "should detect drift in mock response");
    const undoc = validateResult.drifts.find((d) => d.type === "undocumented");
    assert(undoc, "should find undocumented createdAt");
  });

  // ─── Summary ───
  console.log(`\n  Results: ${passed} passed, ${failed} failed\n`);
  process.exit(failed > 0 ? 1 : 0);
}

run();
