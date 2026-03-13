/**
 * Compare an actual API response body against an OpenAPI response schema.
 * Returns an array of drift items:
 *   { type: "missing" | "type_mismatch" | "undocumented", path, expected?, actual? }
 */
function validateResponse(actual, schema) {
  if (!schema) return [];
  const drifts = [];
  compareValue(actual, schema, "", drifts);
  return drifts;
}

function compareValue(actual, schema, path, drifts) {
  if (!schema) return;

  const schemaType = schema.type;

  if (actual === undefined || actual === null) {
    if (schema.type) {
      drifts.push({ type: "missing", path: path || "(root)", expected: schemaType });
    }
    return;
  }

  if (schemaType === "object" || schema.properties) {
    compareObject(actual, schema, path, drifts);
  } else if (schemaType === "array") {
    compareArray(actual, schema, path, drifts);
  } else if (schemaType) {
    const actualType = getJsonType(actual);
    // "number" schema accepts both integer and number
    const compatible =
      actualType === schemaType ||
      (schemaType === "number" && actualType === "integer");
    if (!compatible) {
      drifts.push({
        type: "type_mismatch",
        path: path || "(root)",
        expected: schemaType,
        actual: actualType,
      });
    }
  }
}

function compareObject(actual, schema, path, drifts) {
  if (typeof actual !== "object" || Array.isArray(actual)) {
    drifts.push({
      type: "type_mismatch",
      path: path || "(root)",
      expected: "object",
      actual: getJsonType(actual),
    });
    return;
  }

  const properties = schema.properties || {};
  const required = schema.required || [];

  // Check for missing fields defined in spec
  for (const [key, propSchema] of Object.entries(properties)) {
    const fieldPath = path ? `${path}.${key}` : key;
    if (!(key in actual)) {
      if (required.includes(key)) {
        drifts.push({ type: "missing", path: fieldPath, expected: propSchema.type || "any" });
      }
    } else {
      compareValue(actual[key], propSchema, fieldPath, drifts);
    }
  }

  // Check for undocumented fields not in spec
  for (const key of Object.keys(actual)) {
    if (!(key in properties) && !schema.additionalProperties) {
      const fieldPath = path ? `${path}.${key}` : key;
      drifts.push({
        type: "undocumented",
        path: fieldPath,
        actual: getJsonType(actual[key]),
      });
    }
  }
}

function compareArray(actual, schema, path, drifts) {
  if (!Array.isArray(actual)) {
    drifts.push({
      type: "type_mismatch",
      path: path || "(root)",
      expected: "array",
      actual: getJsonType(actual),
    });
    return;
  }

  if (schema.items && actual.length > 0) {
    // Validate first element as representative
    compareValue(actual[0], schema.items, `${path}[0]`, drifts);
  }
}

function getJsonType(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  if (typeof value === "number") {
    return Number.isInteger(value) ? "integer" : "number";
  }
  return typeof value;
}

module.exports = { validateResponse };
