const cheerio = require('cheerio');

/**
 * HTML에서 SEO 관련 요소를 추출한다
 */
function extractSeoElements(html) {
  const $ = cheerio.load(html);

  const meta = {};
  meta.title = $('title').text().trim() || null;
  meta.description = $('meta[name="description"]').attr('content') || null;
  meta.robots = $('meta[name="robots"]').attr('content') || null;
  meta.canonical = $('link[rel="canonical"]').attr('href') || null;

  // Open Graph
  const og = {};
  $('meta[property^="og:"]').each((_, el) => {
    const prop = $(el).attr('property');
    og[prop] = $(el).attr('content') || null;
  });

  // JSON-LD 구조화 데이터
  const jsonLd = [];
  $('script[type="application/ld+json"]').each((_, el) => {
    try {
      jsonLd.push(JSON.parse($(el).html()));
    } catch {}
  });

  // h1 태그들
  const h1s = [];
  $('h1').each((_, el) => h1s.push($(el).text().trim()));

  return { meta, og, jsonLd, h1s };
}

/**
 * raw와 rendered SEO 요소를 비교하여 차이점을 반환
 */
function compareSeo(rawSeo, renderedSeo) {
  const issues = [];

  // Meta 비교
  for (const key of ['title', 'description', 'robots', 'canonical']) {
    const rawVal = rawSeo.meta[key];
    const renVal = renderedSeo.meta[key];

    if (!rawVal && renVal) {
      issues.push({
        type: 'js_dependent',
        element: key,
        raw: rawVal,
        rendered: renVal,
        severity: key === 'title' || key === 'canonical' ? 'high' : 'medium',
      });
    } else if (rawVal && renVal && rawVal !== renVal) {
      issues.push({
        type: 'mismatch',
        element: key,
        raw: rawVal,
        rendered: renVal,
        severity: 'medium',
      });
    } else if (!rawVal && !renVal && key !== 'robots') {
      // robots 누락은 문제가 아님 (기본값: index, follow)
      issues.push({
        type: 'missing',
        element: key,
        raw: rawVal,
        rendered: renVal,
        severity: key === 'title' ? 'high' : 'low',
      });
    }
  }

  // OG 태그 비교
  const allOgKeys = new Set([
    ...Object.keys(rawSeo.og),
    ...Object.keys(renderedSeo.og),
  ]);
  for (const key of allOgKeys) {
    const rawVal = rawSeo.og[key] || null;
    const renVal = renderedSeo.og[key] || null;
    if (!rawVal && renVal) {
      issues.push({
        type: 'js_dependent',
        element: key,
        raw: rawVal,
        rendered: renVal,
        severity: 'medium',
      });
    } else if (rawVal && renVal && rawVal !== renVal) {
      issues.push({
        type: 'mismatch',
        element: key,
        raw: rawVal,
        rendered: renVal,
        severity: 'low',
      });
    }
  }

  // JSON-LD 비교
  const rawLdCount = rawSeo.jsonLd.length;
  const renLdCount = renderedSeo.jsonLd.length;
  if (rawLdCount === 0 && renLdCount > 0) {
    issues.push({
      type: 'js_dependent',
      element: 'JSON-LD',
      raw: `${rawLdCount}개`,
      rendered: `${renLdCount}개`,
      severity: 'high',
    });
  } else if (rawLdCount !== renLdCount) {
    issues.push({
      type: 'mismatch',
      element: 'JSON-LD 개수',
      raw: `${rawLdCount}개`,
      rendered: `${renLdCount}개`,
      severity: 'medium',
    });
  }

  // H1 비교
  if (rawSeo.h1s.length === 0 && renderedSeo.h1s.length > 0) {
    issues.push({
      type: 'js_dependent',
      element: 'h1',
      raw: '없음',
      rendered: renderedSeo.h1s.join(', '),
      severity: 'medium',
    });
  }

  return issues;
}

/**
 * 전체 분석 파이프라인
 */
function analyze(rawHtml, renderedHtml) {
  const rawSeo = extractSeoElements(rawHtml);
  const renderedSeo = extractSeoElements(renderedHtml);
  const issues = compareSeo(rawSeo, renderedSeo);

  return { rawSeo, renderedSeo, issues };
}

module.exports = { extractSeoElements, compareSeo, analyze };
