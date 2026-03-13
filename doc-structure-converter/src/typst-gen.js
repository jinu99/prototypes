// AST → Typst markup converter with breakable hints

export function astToTypst(blocks) {
  const lines = [];
  lines.push(preamble());

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    const nextBlock = blocks[i + 1];
    lines.push(convertBlock(block, nextBlock));
  }

  return lines.join("\n\n");
}

function preamble() {
  return `#set page(margin: (top: 2cm, bottom: 2cm, left: 2cm, right: 2cm))
#set text(font: "New Computer Modern", size: 11pt)
#set par(justify: true, leading: 0.65em)`;
}

function convertBlock(block, nextBlock) {
  const { type, node } = block;

  switch (type) {
    case "heading":
      return convertHeading(node, nextBlock);
    case "paragraph":
      return convertParagraph(node);
    case "code":
      return convertCode(node);
    case "table":
      return convertTable(node);
    case "list":
      return convertList(node);
    case "blockquote":
      return convertBlockquote(node);
    case "thematicBreak":
      return "#line(length: 100%, stroke: 0.5pt + gray)";
    case "image":
      return convertImage(node);
    default:
      return convertParagraph(node);
  }
}

function convertHeading(node, nextBlock) {
  const text = inlineToTypst(node.children);
  const level = "=".repeat(node.depth);

  // Keep heading attached to next content block
  if (nextBlock) {
    return `#block(breakable: false, below: 0.4em)[
${level} ${text}
]`;
  }
  return `${level} ${text}`;
}

function convertParagraph(node) {
  if (!node.children) return "";
  return inlineToTypst(node.children);
}

function convertCode(node) {
  const lang = node.lang || "";
  const code = node.value; // raw block — no escaping needed
  // Core feature: code blocks are unbreakable
  return `#block(breakable: false, width: 100%, inset: 8pt, fill: luma(245), radius: 4pt)[
\`\`\`${lang}
${code}
\`\`\`
]`;
}

function convertTable(node) {
  const rows = node.children;
  if (rows.length === 0) return "";

  const headerRow = rows[0];
  const cols = headerRow.children.length;
  const align = (node.align || []).map((a) => {
    if (a === "left") return "left";
    if (a === "right") return "right";
    if (a === "center") return "center";
    return "auto";
  });

  while (align.length < cols) align.push("auto");

  const colDef = align.map((a) => `${a}`).join(", ");

  let tableContent = "";

  // Header
  for (const cell of headerRow.children) {
    const text = inlineToTypst(cell.children);
    tableContent += `    [*${text}*],\n`;
  }

  // Body rows
  for (let i = 1; i < rows.length; i++) {
    for (const cell of rows[i].children) {
      const text = inlineToTypst(cell.children);
      tableContent += `    [${text}],\n`;
    }
  }

  // Core feature: tables are unbreakable
  return `#block(breakable: false)[
  #table(
    columns: (${Array(cols).fill("1fr").join(", ")}),
    align: (${colDef}),
    stroke: 0.5pt + gray,
${tableContent}  )
]`;
}

function convertList(node) {
  const items = node.children.map((item) => {
    const content = item.children
      .map((child) => {
        if (child.type === "paragraph") return inlineToTypst(child.children);
        if (child.type === "list") return convertList(child);
        return "";
      })
      .join("\n");
    return content;
  });

  if (node.ordered) {
    return items.map((item, i) => `+ ${item}`).join("\n");
  }
  return items.map((item) => `- ${item}`).join("\n");
}

function convertBlockquote(node) {
  const content = node.children
    .map((child) => {
      if (child.type === "paragraph") return inlineToTypst(child.children);
      return "";
    })
    .join("\n");
  return `#quote(block: true)[${content}]`;
}

function convertImage(node) {
  // Images are unbreakable
  const alt = node.alt || "";
  const url = node.url || "";
  return `#block(breakable: false)[
  #figure(
    image("${url}"),
    caption: [${alt}]
  )
]`;
}

// Inline content conversion
function inlineToTypst(children) {
  if (!children) return "";
  return children.map(inlineNodeToTypst).join("");
}

function inlineNodeToTypst(node) {
  switch (node.type) {
    case "text":
      return escapeTypst(node.value);
    case "strong":
      return `*${inlineToTypst(node.children)}*`;
    case "emphasis":
      return `_${inlineToTypst(node.children)}_`;
    case "inlineCode":
      return `\`${node.value}\``;
    case "link":
      return `#link("${node.url}")[${inlineToTypst(node.children)}]`;
    case "image":
      return `#image("${node.url}")`;
    case "break":
      return "\\\n";
    default:
      if (node.children) return inlineToTypst(node.children);
      if (node.value) return escapeTypst(node.value);
      return "";
  }
}

function escapeTypst(text) {
  return text
    .replace(/\\/g, "\\\\")
    .replace(/#/g, "\\#")
    .replace(/\$/g, "\\$")
    .replace(/@/g, "\\@")
    .replace(/_/g, "\\_")
    .replace(/\*/g, "\\*");
}
