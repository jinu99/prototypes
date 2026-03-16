#!/usr/bin/env node

const { setupBrowserEnv } = require('./browser-env');
setupBrowserEnv();

const { crawlUrl, launchBrowser } = require('./crawler');
const { analyze } = require('./analyzer');
const { generateCliReport } = require('./reporter');
const { fetchSitemap } = require('./sitemap');

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help')) {
    console.log(`
SEO Indie Toolkit — SPA 크롤러 시뮬레이션 진단 도구

사용법:
  node src/cli.js <URL>                  단일 페이지 진단
  node src/cli.js --sitemap <URL>        sitemap.xml 기반 일괄 진단
  node src/cli.js --sitemap <URL> --limit <N>  상위 N개만 진단

예시:
  node src/cli.js https://example.com
  node src/cli.js --sitemap https://example.com/sitemap.xml
  node src/cli.js --sitemap https://example.com/sitemap.xml --limit 5
`);
    process.exit(0);
  }

  const isSitemap = args.includes('--sitemap');
  const limitIdx = args.indexOf('--limit');
  const limit = limitIdx !== -1 ? parseInt(args[limitIdx + 1], 10) : Infinity;

  let urls = [];

  if (isSitemap) {
    const sitemapUrl = args.find(a => a.startsWith('http'));
    if (!sitemapUrl) {
      console.error('오류: sitemap URL을 입력하세요.');
      process.exit(1);
    }
    console.log(`📡 Sitemap 가져오는 중: ${sitemapUrl}`);
    try {
      urls = await fetchSitemap(sitemapUrl);
      console.log(`📋 발견된 URL: ${urls.length}개`);
      if (limit < urls.length) {
        urls = urls.slice(0, limit);
        console.log(`🔢 상위 ${limit}개만 진단합니다.`);
      }
    } catch (err) {
      console.error(`오류: Sitemap을 가져올 수 없습니다 — ${err.message}`);
      process.exit(1);
    }
  } else {
    const url = args.find(a => a.startsWith('http'));
    if (!url) {
      console.error('오류: URL을 입력하세요.');
      process.exit(1);
    }
    urls = [url];
  }

  console.log(`🚀 브라우저를 시작합니다...`);
  const browser = await launchBrowser();

  const allResults = [];

  try {
    for (let i = 0; i < urls.length; i++) {
      const url = urls[i];
      console.log(`\n🔍 [${i + 1}/${urls.length}] 진단 중: ${url}`);

      try {
        const { rawHtml, renderedHtml } = await crawlUrl(url, browser);
        const analysis = analyze(rawHtml, renderedHtml);
        const report = generateCliReport(url, analysis);
        console.log(report);
        allResults.push({ url, analysis, success: true });
      } catch (err) {
        console.error(`  ❌ 오류: ${err.message}`);
        allResults.push({ url, error: err.message, success: false });
      }
    }

    // 요약
    if (urls.length > 1) {
      console.log('\n═══════════════════════════════════════════════════');
      console.log('  종합 요약');
      console.log('═══════════════════════════════════════════════════\n');

      const successful = allResults.filter(r => r.success);
      const failed = allResults.filter(r => !r.success);

      console.log(`진단 완료: ${successful.length}/${urls.length}개`);
      if (failed.length > 0) {
        console.log(`실패: ${failed.length}개`);
        failed.forEach(r => console.log(`  - ${r.url}: ${r.error}`));
      }

      const totalIssues = successful.reduce((sum, r) => sum + r.analysis.issues.length, 0);
      const highIssues = successful.reduce((sum, r) =>
        sum + r.analysis.issues.filter(i => i.severity === 'high').length, 0);

      console.log(`\n총 발견된 문제: ${totalIssues}개 (심각: ${highIssues}개)`);
    }
  } finally {
    await browser.close();
  }
}

main().catch(err => {
  console.error('치명적 오류:', err.message);
  process.exit(1);
});
