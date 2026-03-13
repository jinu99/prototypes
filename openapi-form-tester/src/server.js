const express = require("express");
const path = require("path");
const cors = require("cors");
const { parseSpec } = require("./parser");
const { validateResponse } = require("./validator");

function createServer(specPath, options = {}) {
  const app = express();
  const port = options.port || 3000;

  app.use(cors());
  app.use(express.json());

  // Serve static frontend
  app.use(express.static(path.join(__dirname, "..", "public")));

  // Mount mock API if using sample spec
  const mockRoutes = tryLoadMockRoutes();
  if (mockRoutes) {
    app.use("/mock", mockRoutes);
  }

  // API: get parsed spec
  let parsedSpec = null;

  app.get("/api/spec", async (req, res) => {
    try {
      if (!parsedSpec) {
        parsedSpec = await parseSpec(specPath);
        // Rewrite server URLs that point to localhost:3000 to use the actual port
        if (parsedSpec.servers) {
          parsedSpec.servers = parsedSpec.servers.map((s) => ({
            ...s,
            url: s.url.replace(/localhost:\d+/, `localhost:${port}`),
          }));
        }
      }
      res.json(parsedSpec);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // API: proxy request to target API
  app.post("/api/send", async (req, res) => {
    const { url, method, body, headers } = req.body;

    try {
      const fetchOptions = {
        method: method || "GET",
        headers: { "Content-Type": "application/json", ...headers },
      };
      if (body && method !== "GET") {
        fetchOptions.body = JSON.stringify(body);
      }

      const response = await fetch(url, fetchOptions);
      const contentType = response.headers.get("content-type") || "";

      let responseBody;
      if (contentType.includes("application/json")) {
        responseBody = await response.json();
      } else {
        responseBody = await response.text();
      }

      res.json({
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries()),
        body: responseBody,
      });
    } catch (err) {
      res.status(502).json({ error: `Request failed: ${err.message}` });
    }
  });

  // API: validate response against spec
  app.post("/api/validate", (req, res) => {
    const { responseBody, schema } = req.body;
    const drifts = validateResponse(responseBody, schema);
    res.json({ drifts, count: drifts.length });
  });

  return { app, port };
}

function tryLoadMockRoutes() {
  try {
    return require("../sample/mock-routes");
  } catch {
    return null;
  }
}

module.exports = { createServer };
