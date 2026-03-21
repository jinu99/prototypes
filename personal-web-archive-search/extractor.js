const { Readability } = require('@mozilla/readability');
const { parseHTML } = require('linkedom');
const fetch = require('node-fetch');

async function extractFromUrl(url) {
  const response = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; WebArchiveBot/1.0)',
      'Accept': 'text/html',
    },
    timeout: 15000,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const html = await response.text();
  return extractFromHtml(html, url);
}

function extractFromHtml(html, url) {
  const { document } = parseHTML(html);
  const reader = new Readability(document);
  const article = reader.parse();

  if (!article) {
    throw new Error('Failed to extract article content');
  }

  // Detect language (simple heuristic: check for CJK characters)
  const cjkRatio = (article.textContent.match(/[\u3000-\u9fff\uac00-\ud7af]/g) || []).length
    / Math.max(article.textContent.length, 1);
  const lang = cjkRatio > 0.1 ? 'ko' : 'en';

  return {
    url,
    title: article.title || '',
    content: article.textContent || '',
    excerpt: article.excerpt || '',
    siteName: article.siteName || new URL(url).hostname,
    lang,
  };
}

module.exports = { extractFromUrl, extractFromHtml };
