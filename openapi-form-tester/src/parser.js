const SwaggerParser = require("@apidevtools/swagger-parser");
const path = require("path");

async function parseSpec(specPath) {
  const resolved = path.resolve(specPath);
  const api = await SwaggerParser.dereference(resolved);

  if (!api.openapi || !api.openapi.startsWith("3.")) {
    throw new Error(`Unsupported OpenAPI version: ${api.openapi || "unknown"}`);
  }

  const endpoints = [];
  const paths = api.paths || {};

  for (const [pathStr, pathItem] of Object.entries(paths)) {
    for (const method of ["get", "post", "put", "patch", "delete"]) {
      const operation = pathItem[method];
      if (!operation) continue;

      const endpoint = {
        path: pathStr,
        method: method.toUpperCase(),
        operationId: operation.operationId || `${method}_${pathStr}`,
        summary: operation.summary || "",
        description: operation.description || "",
        requestBody: extractRequestBodySchema(operation),
        responses: extractResponseSchemas(operation),
        tags: operation.tags || [],
      };

      endpoints.push(endpoint);
    }
  }

  return {
    title: (api.info && api.info.title) || "Untitled API",
    version: (api.info && api.info.version) || "0.0.0",
    servers: api.servers || [{ url: "/" }],
    endpoints,
  };
}

function extractRequestBodySchema(operation) {
  if (!operation.requestBody) return null;
  const content = operation.requestBody.content;
  if (!content) return null;

  const jsonContent = content["application/json"];
  if (!jsonContent || !jsonContent.schema) return null;

  return {
    required: !!operation.requestBody.required,
    schema: jsonContent.schema,
  };
}

function extractResponseSchemas(operation) {
  const result = {};
  const responses = operation.responses || {};

  for (const [statusCode, response] of Object.entries(responses)) {
    const content = response.content;
    if (!content) {
      result[statusCode] = { description: response.description || "", schema: null };
      continue;
    }

    const jsonContent = content["application/json"];
    result[statusCode] = {
      description: response.description || "",
      schema: jsonContent ? jsonContent.schema : null,
    };
  }

  return result;
}

module.exports = { parseSpec };
