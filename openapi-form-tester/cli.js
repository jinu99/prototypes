#!/usr/bin/env node

const path = require("path");
const { createServer } = require("./src/server");

const args = process.argv.slice(2);
const specPath = args[0] || path.join(__dirname, "sample", "petstore.yaml");
const port = parseInt(args[1]) || 4567;

if (args.includes("--help") || args.includes("-h")) {
  console.log(`
OpenAPI Form Tester
  Test APIs with auto-generated forms and drift detection.

Usage:
  node cli.js [spec-file] [port]

Examples:
  node cli.js                         # Use built-in sample spec on port 3000
  node cli.js ./my-api.yaml           # Your own OpenAPI 3.x spec
  node cli.js ./my-api.yaml 8080      # Custom port
`);
  process.exit(0);
}

const { app } = createServer(specPath, { port });

app.listen(port, () => {
  const url = `http://localhost:${port}`;
  console.log(`\n  OpenAPI Form Tester`);
  console.log(`  Spec: ${path.resolve(specPath)}`);
  console.log(`  UI:   ${url}\n`);

  // Try to open browser
  import("open")
    .then((mod) => mod.default(url))
    .catch(() => {});
});
