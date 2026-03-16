# Indie Launch Kit

> README.md 하나로 랜딩페이지, 체인지로그, 런치 포스트를 CLI 한 줄에 생성

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI (commander)                          │
│                  init · build --dir --theme                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      builder.js (오케스트레이션)                  │
│                                                                  │
│  ┌──────────────┐   ┌───────────────┐   ┌─────────────────────┐ │
│  │  parser.js   │   │ metadata.js   │   │   changelog.js      │ │
│  │              │   │               │   │                     │ │
│  │ README.md →  │   │ package.json  │   │ git log (최근 200)  │ │
│  │ remark AST → │   │ pyproject.toml│   │ → conventional      │ │
│  │ 의미적 섹션  │   │ → name, ver,  │   │   commit 파싱       │ │
│  │ 분류         │   │   license 등  │   │ → 타입별 그룹화     │ │
│  └──────┬───────┘   └──────┬────────┘   └──────────┬──────────┘ │
│         │                  │                       │            │
│         ▼                  ▼                       ▼            │
│  ┌─────────────────────────────────┐  ┌────────────────────┐   │
│  │        templates.js             │  │  launch-posts.js   │   │
│  │                                 │  │                    │   │
│  │  Handlebars 렌더링              │  │  meta + sections → │   │
│  │  3개 테마: minimal·dark·gradient│  │  Product Hunt 초안 │   │
│  │  → index.html (랜딩페이지)      │  │  Reddit 초안       │   │
│  │  → changelog.html               │  │  Hacker News 초안  │   │
│  └──────────────┬──────────────────┘  └─────────┬──────────┘   │
│                 │                               │              │
└─────────────────┼───────────────────────────────┼──────────────┘
                  │                               │
                  ▼                               ▼
        ┌─────────────────────────────────────────────────┐
        │                   dist/                         │
        │  ├── index.html          (랜딩페이지)           │
        │  ├── changelog.html      (체인지로그)           │
        │  └── launch-posts/                              │
        │      ├── product-hunt.md                        │
        │      ├── reddit.md                              │
        │      └── hacker-news.md                         │
        └─────────────────────────────────────────────────┘
```

### 데이터 흐름

1. **입력**: 프로젝트 디렉토리의 `README.md` + `package.json`/`pyproject.toml` + git history
2. **파싱**: `remark` (GFM 지원)로 Markdown AST를 생성하고, 헤딩 키워드 패턴 매칭으로 `hero` / `features` / `install` / `cta` 섹션으로 자동 분류
3. **렌더링**: Handlebars 템플릿에 섹션 데이터와 메타데이터를 주입하여 테마별 HTML 생성
4. **출력**: 정적 HTML 파일 + Markdown 런치 포스트 초안

## Demo

```bash
# 샘플 프로젝트로 minimal 테마 빌드
$ node bin/cli.js build --dir ./test-fixtures/sample-project --theme minimal

🚀 indie-launch-kit build
  Project: /home/user/indie-launch-kit/test-fixtures/sample-project
  Theme: minimal

  ✓ Parsed README.md → hero: "Sample Project", 2 feature sections, 1 install sections
  ✓ Metadata: sample-project v1.0.0
  ✓ Landing page → dist/index.html (theme: minimal)
  ✓ Changelog → dist/changelog.html (12 commits)
  ✓ Launch posts → dist/launch-posts/

✅ Done! Open dist/index.html in your browser.
```

```bash
# 설정 파일 초기화
$ node bin/cli.js init

Created .launchkit.json
Available themes: minimal, dark, gradient

Run `npx indie-launch-kit build` to generate your landing page.
```

```bash
# dark 테마로 빌드
$ node bin/cli.js build --dir ./my-project --theme dark

# gradient 테마로 빌드
$ node bin/cli.js build --dir ./my-project --theme gradient
```

### 생성 결과물 예시

**`dist/index.html`** — 프로젝트 README의 hero, features, install 섹션이 테마에 맞게 스타일링된 싱글 페이지 랜딩페이지

**`dist/launch-posts/product-hunt.md`** — 바로 사용할 수 있는 Product Hunt 런치 포스트 초안:
```markdown
# Product Hunt Launch Post
**Product Name:** my-project
**Tagline:** A CLI tool for awesome things
**Key Features:**
- Feature 1
- Feature 2
```

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
