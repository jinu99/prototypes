/**
 * 한국어 진단 리포트 생성
 */

const SEVERITY_LABELS = {
  high: '🔴 심각',
  medium: '🟡 주의',
  low: '🟢 참고',
};

const TYPE_LABELS = {
  js_dependent: 'JS 의존',
  mismatch: '불일치',
  missing: '누락',
};

function getAdvice(issue) {
  const adviceMap = {
    title: {
      js_dependent: '제목(title)이 JavaScript에 의존합니다. 검색엔진 크롤러가 JS를 실행하지 못하면 제목이 표시되지 않습니다. 서버 사이드 렌더링(SSR)을 적용하거나, 정적 HTML에 제목을 포함하세요.',
      mismatch: 'JS 실행 전후로 제목이 다릅니다. 크롤러가 잘못된 제목을 인덱싱할 수 있습니다. 초기 HTML에 정확한 제목을 설정하세요.',
      missing: '제목(title)이 없습니다. 검색 결과에 페이지 제목이 표시되지 않아 클릭률이 크게 떨어집니다. 반드시 <title> 태그를 추가하세요.',
    },
    description: {
      js_dependent: 'meta description이 JS에 의존합니다. 크롤러가 설명을 가져오지 못하면 검색 결과에 자동 생성된 스니펫이 표시됩니다. 정적 HTML에 description을 포함하세요.',
      mismatch: 'JS 실행 전후로 description이 다릅니다. 초기 HTML의 description을 최종 버전과 일치시키세요.',
      missing: 'meta description이 없습니다. 검색엔진이 페이지 내용에서 자동으로 스니펫을 추출하지만, 직접 작성하면 클릭률을 높일 수 있습니다.',
    },
    canonical: {
      js_dependent: 'canonical URL이 JS에 의존합니다. 크롤러가 정확한 canonical을 읽지 못하면 중복 콘텐츠 문제가 발생할 수 있습니다. 정적 HTML에 <link rel="canonical">을 포함하세요.',
      mismatch: 'canonical URL이 JS 실행 전후로 다릅니다. 잘못된 canonical은 페이지가 인덱싱에서 제외되는 원인이 됩니다. 초기 HTML에 정확한 canonical을 설정하세요.',
      missing: 'canonical URL이 설정되지 않았습니다. 중복 콘텐츠가 있는 경우 검색엔진이 어떤 페이지를 기준으로 할지 판단하기 어렵습니다.',
    },
    robots: {
      js_dependent: 'robots 메타 태그가 JS에 의존합니다. 크롤러가 이를 읽지 못하면 기본값(index, follow)이 적용됩니다. 의도한 robots 설정을 정적 HTML에 포함하세요.',
      mismatch: 'robots 설정이 JS 실행 전후로 다릅니다. 의도하지 않은 크롤링 차단이나 인덱싱이 발생할 수 있습니다.',
      missing: null,
    },
    'JSON-LD': {
      js_dependent: '구조화 데이터(JSON-LD)가 JS에 의존합니다. Google은 JS를 실행하지만, 다른 검색엔진은 그렇지 않을 수 있습니다. 가능하면 정적 HTML에 JSON-LD를 포함하세요.',
      mismatch: 'JS 실행 전후로 JSON-LD 개수가 다릅니다. 구조화 데이터가 올바르게 포함되어 있는지 확인하세요.',
    },
    h1: {
      js_dependent: 'H1 태그가 JS에 의존합니다. 검색엔진이 페이지의 주제를 파악하는 데 H1이 중요합니다. 정적 HTML에 H1을 포함하세요.',
    },
  };

  // OG 태그 처리
  if (issue.element.startsWith('og:')) {
    if (issue.type === 'js_dependent') {
      return `${issue.element} 태그가 JS에 의존합니다. 소셜 미디어 크롤러(Facebook, Twitter 등)는 JS를 실행하지 않으므로, 공유 시 올바른 미리보기가 표시되지 않습니다. 정적 HTML에 OG 태그를 포함하세요.`;
    }
    if (issue.type === 'mismatch') {
      return `${issue.element} 태그가 JS 실행 전후로 다릅니다. 소셜 미디어 공유 시 잘못된 정보가 표시될 수 있습니다.`;
    }
  }

  const elementAdvice = adviceMap[issue.element];
  if (elementAdvice && elementAdvice[issue.type]) {
    return elementAdvice[issue.type];
  }

  return '해당 요소를 확인하고 필요한 경우 정적 HTML에 포함하세요.';
}

/**
 * CLI용 텍스트 리포트 생성
 */
function generateCliReport(url, analysis) {
  const lines = [];
  lines.push('');
  lines.push('═══════════════════════════════════════════════════');
  lines.push(`  SEO 크롤러 시뮬레이션 진단 리포트`);
  lines.push(`  URL: ${url}`);
  lines.push('═══════════════════════════════════════════════════');
  lines.push('');

  if (analysis.issues.length === 0) {
    lines.push('✅ 발견된 문제가 없습니다. JS 실행 전후 SEO 요소가 동일합니다.');
    lines.push('');
    return lines.join('\n');
  }

  // 심각도별 정렬
  const sorted = [...analysis.issues].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.severity] || 3) - (order[b.severity] || 3);
  });

  lines.push(`발견된 문제: ${sorted.length}개`);
  lines.push(`  🔴 심각: ${sorted.filter(i => i.severity === 'high').length}개`);
  lines.push(`  🟡 주의: ${sorted.filter(i => i.severity === 'medium').length}개`);
  lines.push(`  🟢 참고: ${sorted.filter(i => i.severity === 'low').length}개`);
  lines.push('');

  for (const issue of sorted) {
    const sev = SEVERITY_LABELS[issue.severity] || issue.severity;
    const typ = TYPE_LABELS[issue.type] || issue.type;
    lines.push(`───────────────────────────────────────────────────`);
    lines.push(`${sev} | ${typ} | ${issue.element}`);
    lines.push('');
    lines.push(`  크롤러가 보는 값 (JS 실행 전): ${issue.raw || '(없음)'}`);
    lines.push(`  실제 렌더링 값 (JS 실행 후):   ${issue.rendered || '(없음)'}`);
    lines.push('');

    const advice = getAdvice(issue);
    if (advice) {
      lines.push(`  💡 해결 방법:`);
      lines.push(`     ${advice}`);
    }
    lines.push('');
  }

  lines.push('═══════════════════════════════════════════════════');
  lines.push('');
  return lines.join('\n');
}

/**
 * JSON 형태의 리포트 (웹 UI용)
 */
function generateJsonReport(url, analysis) {
  return {
    url,
    timestamp: new Date().toISOString(),
    summary: {
      total: analysis.issues.length,
      high: analysis.issues.filter(i => i.severity === 'high').length,
      medium: analysis.issues.filter(i => i.severity === 'medium').length,
      low: analysis.issues.filter(i => i.severity === 'low').length,
    },
    issues: analysis.issues.map(issue => ({
      ...issue,
      advice: getAdvice(issue),
      severityLabel: SEVERITY_LABELS[issue.severity],
      typeLabel: TYPE_LABELS[issue.type],
    })),
    seo: {
      raw: analysis.rawSeo,
      rendered: analysis.renderedSeo,
    },
  };
}

module.exports = { generateCliReport, generateJsonReport };
