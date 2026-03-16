const path = require('path');
const fs = require('fs');

/**
 * Playwright 브라우저 실행에 필요한 추가 라이브러리 경로를 설정한다.
 * 시스템에 설치되지 않은 라이브러리가 있을 경우 /tmp/pw-libs에서 찾는다.
 */
function setupBrowserEnv() {
  const extraLibPath = '/tmp/pw-libs/extracted/usr/lib/x86_64-linux-gnu';
  if (fs.existsSync(extraLibPath)) {
    const current = process.env.LD_LIBRARY_PATH || '';
    if (!current.includes(extraLibPath)) {
      process.env.LD_LIBRARY_PATH = current
        ? `${extraLibPath}:${current}`
        : extraLibPath;
    }
  }
}

module.exports = { setupBrowserEnv };
