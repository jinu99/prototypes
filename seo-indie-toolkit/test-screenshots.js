#!/usr/bin/env node

/**
 * Playwright를 사용해 웹 UI의 스크린샷을 찍고 기본 동작을 검증
 */

const { setupBrowserEnv } = require('./src/browser-env');
setupBrowserEnv();

const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { crawlUrl, launchBrowser } = require('./src/crawler');
const { analyze } = require('./src/analyzer');
const { generateJsonReport } = require('./src/reporter');

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const PORT = 3457;

async function startServer() {
  // 서버 모듈을 직접 사용하지 않고 간단한 서버를 띄운다
  const serverModule = require('./src/server-lib');
  return serverModule.start(PORT);
}

// server-lib가 없으므로 직접 구현
async function startTestServer() {
  const serverPath = path.join(__dirname, 'src', 'server.js');
  return new Promise((resolve) => {
    const { fork } = require('child_process');
    const child = fork(serverPath, [], {
      env: { ...process.env, PORT: String(PORT) },
      stdio: 'pipe',
    });
    child.stdout.on('data', (data) => {
      if (data.toString().includes('서버가 시작')) {
        resolve(child);
      }
    });
    child.stderr.on('data', (data) => {
      // ignore
    });
    // fallback timeout
    setTimeout(() => resolve(child), 3000);
  });
}

async function main() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
  }

  console.log('🚀 테스트 서버 시작 중...');
  const serverProcess = await startTestServer();

  const browser = await chromium.launch({ headless: true });

  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

    // 1. 초기 화면 스크린샷
    console.log('📸 초기 화면 스크린샷...');
    await page.goto(`http://localhost:${PORT}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '01-initial.png'),
      fullPage: true,
    });

    // 2. URL 입력 후 진단 실행
    console.log('📸 진단 실행 중...');
    await page.fill('#urlInput', 'https://app.diagrams.net');
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '02-url-input.png'),
      fullPage: true,
    });

    // 진단 버튼 클릭
    await page.click('#analyzeBtn');

    // 결과 대기 (최대 30초)
    await page.waitForSelector('.result-card', { timeout: 60000 });
    await page.waitForTimeout(1000);

    // 3. 결과 화면 스크린샷
    console.log('📸 결과 화면 스크린샷...');
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '03-results.png'),
      fullPage: true,
    });

    // 검증: 결과 카드가 존재하는지
    const resultCards = await page.locator('.result-card').count();
    const issueItems = await page.locator('.issue-item').count();
    console.log(`✅ 결과 카드: ${resultCards}개, 이슈 항목: ${issueItems}개`);

    if (resultCards > 0 && issueItems > 0) {
      console.log('✅ 웹 UI 검증 통과: 진단 결과가 올바르게 표시됩니다.');
    } else {
      console.log('❌ 웹 UI 검증 실패: 진단 결과가 표시되지 않습니다.');
    }

    await page.close();
  } finally {
    await browser.close();
    serverProcess.kill();
  }
}

main().catch(err => {
  console.error('오류:', err.message);
  process.exit(1);
});
