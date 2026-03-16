# Indie Launch Kit

> README.md 하나로 랜딩페이지, 체인지로그, 런치 포스트를 CLI 한 줄에 생성

## 실행 방법

```bash
# 의존성 설치
npm install

# 빌드 (프로젝트 디렉토리에서)
node bin/cli.js build --dir <project-path> --theme <minimal|dark|gradient>

# 설정 파일 생성 (선택)
node bin/cli.js init
```

### 예시

```bash
# minimal 테마로 랜딩페이지 생성
node bin/cli.js build --dir ./test-fixtures/sample-project --theme minimal

# dark 테마
node bin/cli.js build --dir ./test-fixtures/express-api --theme dark

# gradient 테마
node bin/cli.js build --dir ./test-fixtures/python-cli --theme gradient
```

### 생성 결과물

- `dist/index.html` — 랜딩페이지
- `dist/changelog.html` — 체인지로그 (conventional commits 기반)
- `dist/launch-posts/product-hunt.md` — Product Hunt 런치 포스트 초안
- `dist/launch-posts/reddit.md` — Reddit 런치 포스트 초안
- `dist/launch-posts/hacker-news.md` — Hacker News 런치 포스트 초안

## 구조

```
indie-launch-kit/
├── bin/
│   └── cli.js              # CLI 엔트리포인트 (commander)
├── src/
│   ├── parser.js            # README.md → 의미적 섹션 분류
│   ├── metadata.js          # package.json / pyproject.toml 메타데이터 추출
│   ├── templates.js         # 3개 테마 Handlebars 템플릿
│   ├── changelog.js         # conventional commits → HTML 체인지로그
│   ├── launch-posts.js      # PH/Reddit/HN 런치 포스트 생성
│   └── builder.js           # 빌드 오케스트레이션
├── test-fixtures/           # 테스트용 샘플 프로젝트 3개
├── BUILD_LOG.md
├── STATUS.md
└── package.json
```

## 원본
prototype-pipeline spec: indie-launch-kit
