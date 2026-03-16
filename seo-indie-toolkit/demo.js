#!/usr/bin/env node

/**
 * 데모 스크립트: 테스트 SPA + 실제 SPA 사이트에서 인덱싱 문제를 발견하는 시연
 */

const { setupBrowserEnv } = require('./src/browser-env');
setupBrowserEnv();

const http = require('http');
const fs = require('fs');
const path = require('path');
const { crawlUrl, launchBrowser } = require('./src/crawler');
const { analyze } = require('./src/analyzer');
const { generateCliReport } = require('./src/reporter');

const DEMO_TARGETS = [
  {
    name: '로컬 테스트 SPA (JS-only meta tags)',
    url: 'http://localhost:9876',
    local: true,
  },
  {
    name: 'draw.io (SPA 앱)',
    url: 'https://app.diagrams.net',
  },
  {
    name: 'Trello (SPA 앱)',
    url: 'https://trello.com',
  },
];

async function main() {
  // 로컬 테스트 서버 시작
  const testHtml = fs.readFileSync(
    path.join(__dirname, 'test-spa', 'index.html'),
    'utf-8'
  );
  const testServer = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(testHtml);
  });
  await new Promise(resolve => testServer.listen(9876, resolve));
  console.log('📦 테스트 SPA 서버 시작 (port 9876)\n');

  console.log('╔═══════════════════════════════════════════════════╗');
  console.log('║   SEO Indie Toolkit — 데모: SPA 인덱싱 문제 발견   ║');
  console.log('╚═══════════════════════════════════════════════════╝\n');

  const browser = await launchBrowser();
  let totalIssues = 0;
  let sitesWithIssues = 0;

  try {
    for (let i = 0; i < DEMO_TARGETS.length; i++) {
      const target = DEMO_TARGETS[i];
      console.log(`\n[${ i + 1}/${DEMO_TARGETS.length}] ${target.name}`);
      console.log(`    URL: ${target.url}\n`);

      try {
        const { rawHtml, renderedHtml } = await crawlUrl(target.url, browser);
        const analysis = analyze(rawHtml, renderedHtml);
        console.log(generateCliReport(target.url, analysis));

        if (analysis.issues.length > 0) {
          sitesWithIssues++;
          totalIssues += analysis.issues.length;
        }
      } catch (err) {
        console.error(`  ❌ 오류: ${err.message}\n`);
      }
    }

    console.log('╔═══════════════════════════════════════════════════╗');
    console.log('║                    데모 결과                      ║');
    console.log('╠═══════════════════════════════════════════════════╣');
    console.log(`║  진단 사이트: ${DEMO_TARGETS.length}개`);
    console.log(`║  문제 발견 사이트: ${sitesWithIssues}개`);
    console.log(`║  총 발견 문제: ${totalIssues}개`);
    console.log('╚═══════════════════════════════════════════════════╝');

  } finally {
    await browser.close();
    testServer.close();
  }
}

main().catch(err => {
  console.error('치명적 오류:', err.message);
  process.exit(1);
});
