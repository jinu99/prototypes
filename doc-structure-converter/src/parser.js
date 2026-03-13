import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";

const BLOCK_TYPES = new Set([
  "table",
  "code",
  "list",
  "image",
  "heading",
  "blockquote",
  "thematicBreak",
]);

export function parseMarkdown(markdown) {
  const tree = unified().use(remarkParse).use(remarkGfm).parse(markdown);
  return tree;
}

export function identifyBlocks(tree) {
  const blocks = [];

  for (const node of tree.children) {
    const block = {
      type: node.type,
      isStructural: BLOCK_TYPES.has(node.type),
      breakable: !["table", "code", "image"].includes(node.type),
      node,
    };

    if (node.type === "heading") {
      block.depth = node.depth;
    }

    blocks.push(block);
  }

  return blocks;
}

export function analyzeDocument(markdown) {
  const tree = parseMarkdown(markdown);
  const blocks = identifyBlocks(tree);

  const stats = {
    total: blocks.length,
    tables: blocks.filter((b) => b.type === "table").length,
    codeBlocks: blocks.filter((b) => b.type === "code").length,
    lists: blocks.filter((b) => b.type === "list").length,
    images: blocks.filter((b) => b.type === "image").length,
    headings: blocks.filter((b) => b.type === "heading").length,
    unbreakable: blocks.filter((b) => !b.breakable).length,
  };

  return { tree, blocks, stats };
}
