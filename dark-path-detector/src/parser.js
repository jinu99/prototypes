const Parser = require('tree-sitter');
const JavaScript = require('tree-sitter-javascript');
const TypeScript = require('tree-sitter-typescript').typescript;
const TSX = require('tree-sitter-typescript').tsx;

/**
 * Create a parser for the given file extension.
 * Returns null if the extension is not supported.
 */
function createParser(ext) {
  const parser = new Parser();
  switch (ext) {
    case '.js':
    case '.mjs':
    case '.cjs':
      parser.setLanguage(JavaScript);
      return parser;
    case '.ts':
      parser.setLanguage(TypeScript);
      return parser;
    case '.tsx':
    case '.jsx':
      parser.setLanguage(TSX);
      return parser;
    default:
      return null;
  }
}

/**
 * Parse source code and return the tree.
 */
function parseSource(source, ext) {
  const parser = createParser(ext);
  if (!parser) return null;
  return parser.parse(source);
}

module.exports = { createParser, parseSource };
