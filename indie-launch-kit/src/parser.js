import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';

/**
 * Parse a README markdown string into semantic sections:
 * hero, features, install, cta, and other.
 */
export function parseReadme(markdown) {
  const tree = unified().use(remarkParse).use(remarkGfm).parse(markdown);
  const sections = [];
  let currentSection = null;

  for (const node of tree.children) {
    if (node.type === 'heading') {
      const text = extractText(node);
      const type = classifySection(text, node.depth);

      // Sub-headings (h3+) stay within their parent h2 section
      if (currentSection && currentSection.depth >= 2 && node.depth > currentSection.depth) {
        currentSection.nodes.push(node);
      } else {
        if (currentSection) sections.push(currentSection);
        currentSection = { type, heading: text, depth: node.depth, nodes: [] };
      }
    } else {
      if (!currentSection) {
        currentSection = { type: 'hero', heading: '', depth: 0, nodes: [] };
      }
      currentSection.nodes.push(node);
    }
  }
  if (currentSection) sections.push(currentSection);

  return groupSections(sections);
}

function extractText(node) {
  let text = '';
  if (node.children) {
    for (const child of node.children) {
      if (child.type === 'text') text += child.value;
      else if (child.type === 'inlineCode') text += child.value;
      else text += extractText(child);
    }
  }
  return text;
}

const SECTION_PATTERNS = {
  hero: /^(about|introduction|overview|what is)/i,
  features: /^(features|highlights|why|what you get|capabilities|benefits)/i,
  install: /^(install|setup|getting started|usage|quick start|how to use|prerequisites|requirements)/i,
  cta: /^(contributing|contribute|support|sponsor|donate|links|community|join|get involved|license|acknowledgements|credits)/i,
  changelog: /^(changelog|changes|release notes|what's new|history)/i,
};

function classifySection(heading, depth) {
  // Top-level h1 is typically the project title → hero
  if (depth === 1) return 'hero';

  const lower = heading.toLowerCase().trim();
  for (const [type, pattern] of Object.entries(SECTION_PATTERNS)) {
    if (pattern.test(lower)) return type;
  }
  return 'other';
}

function groupSections(sections) {
  const result = {
    hero: { title: '', description: '', badges: [] },
    features: [],
    install: [],
    cta: [],
    other: [],
  };

  for (const section of sections) {
    switch (section.type) {
      case 'hero':
        if (section.depth <= 1 && section.heading) {
          result.hero.title = section.heading;
        }
        result.hero.description += nodesToHtml(section.nodes);
        break;
      case 'features':
        result.features.push({
          heading: section.heading,
          content: nodesToHtml(section.nodes),
          items: extractListItems(section.nodes),
        });
        break;
      case 'install':
        result.install.push({
          heading: section.heading,
          content: nodesToHtml(section.nodes),
          codeBlocks: extractCodeBlocks(section.nodes),
        });
        break;
      case 'cta':
        result.cta.push({
          heading: section.heading,
          content: nodesToHtml(section.nodes),
        });
        break;
      default:
        result.other.push({
          heading: section.heading,
          content: nodesToHtml(section.nodes),
        });
        break;
    }
  }

  return result;
}

/** Convert AST nodes to simple HTML */
function nodesToHtml(nodes) {
  return nodes.map(nodeToHtml).join('\n');
}

function nodeToHtml(node) {
  switch (node.type) {
    case 'paragraph':
      return `<p>${inlineToHtml(node.children)}</p>`;
    case 'list':
      const tag = node.ordered ? 'ol' : 'ul';
      const items = node.children.map(li => `<li>${nodesToHtml(li.children)}</li>`).join('');
      return `<${tag}>${items}</${tag}>`;
    case 'code':
      return `<pre><code class="language-${node.lang || ''}">${escapeHtml(node.value)}</code></pre>`;
    case 'blockquote':
      return `<blockquote>${nodesToHtml(node.children)}</blockquote>`;
    case 'heading':
      return `<h${node.depth}>${inlineToHtml(node.children)}</h${node.depth}>`;
    case 'thematicBreak':
      return '<hr>';
    case 'html':
      return node.value;
    case 'table':
      return renderTable(node);
    default:
      if (node.children) return nodesToHtml(node.children);
      if (node.value) return escapeHtml(node.value);
      return '';
  }
}

function inlineToHtml(children) {
  if (!children) return '';
  return children.map(child => {
    switch (child.type) {
      case 'text': return escapeHtml(child.value);
      case 'strong': return `<strong>${inlineToHtml(child.children)}</strong>`;
      case 'emphasis': return `<em>${inlineToHtml(child.children)}</em>`;
      case 'inlineCode': return `<code>${escapeHtml(child.value)}</code>`;
      case 'link': return `<a href="${child.url}">${inlineToHtml(child.children)}</a>`;
      case 'image': return `<img src="${child.url}" alt="${child.alt || ''}" />`;
      case 'break': return '<br>';
      case 'html': return child.value;
      default:
        if (child.children) return inlineToHtml(child.children);
        if (child.value) return escapeHtml(child.value);
        return '';
    }
  }).join('');
}

function renderTable(node) {
  const [head, ...body] = node.children;
  let html = '<table><thead><tr>';
  for (const cell of head.children) {
    html += `<th>${inlineToHtml(cell.children)}</th>`;
  }
  html += '</tr></thead><tbody>';
  for (const row of body) {
    html += '<tr>';
    for (const cell of row.children) {
      html += `<td>${inlineToHtml(cell.children)}</td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  return html;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function extractListItems(nodes) {
  const items = [];
  for (const node of nodes) {
    if (node.type === 'list') {
      for (const li of node.children) {
        items.push(nodesToHtml(li.children));
      }
    }
  }
  return items;
}

function extractCodeBlocks(nodes) {
  const blocks = [];
  for (const node of nodes) {
    if (node.type === 'code') {
      blocks.push({ lang: node.lang || '', code: node.value });
    }
  }
  return blocks;
}
