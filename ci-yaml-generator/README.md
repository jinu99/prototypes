# CI/CD YAML 자동 생성기

> 프로젝트 디렉토리를 스캔하여 GitHub Actions CI 워크플로우 YAML을 자동 생성하는 CLI 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (cli.js)                            │
│              init / detect / validate 명령 라우팅                │
└──────┬──────────────────┬───────────────────┬───────────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌──────────────┐  ┌───────────────┐  ┌────────────────┐
│   Detector   │  │   Generator   │  │   Validator    │
│ detector.js  │  │ generator.js  │  │  validator.js  │
├──────────────┤  ├───────────────┤  ├────────────────┤
│ • 프로젝트   │  │ • Detection   │  │ • YAML 파싱   │
│   파일 스캔  │  │   결과 → Job  │  │ • trigger 검증│
│ • ecosystem  │  │   구성        │  │ • job 구조    │
│   감지       │  │ • Lint/Test/  │  │   검증        │
│ • 패키지매니 │  │   Build/Sec   │  │ • needs 참조  │
│   저, 테스트 │  │   Job 생성    │  │   유효성 확인 │
│   러너, 린터 │  │ • Matrix 전략 │  │               │
│   자동 인식  │  │   적용        │  │               │
└──────┬───────┘  └───────┬───────┘  └───────┬────────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌──────────────┐  ┌───────────────┐  ┌────────────────┐
│  rules.json  │  │  YAML 출력    │  │  검증 리포트   │
│ (감지 규칙)  │  │  (ci.yml)     │  │  (errors/warn) │
└──────────────┘  └───────────────┘  └────────────────┘

데이터 흐름 (init 명령):

  프로젝트 디렉토리
       │
       ▼
  ┌──────────┐    rules.json     ┌───────────┐
  │ Detector │◀─────────────────│  감지 규칙  │
  └────┬─────┘                   │ Node/Py/Go │
       │ Detection[]             └───────────┘
       ▼
  ┌───────────┐    js-yaml       ┌────────────┐
  │ Generator │─────────────────▶│  ci.yml     │
  └─────┬─────┘                  └──────┬─────┘
        │ (auto-validate)               │
        ▼                               ▼
  ┌───────────┐                  ┌────────────┐
  │ Validator │─────────────────▶│ ✅/❌ 결과  │
  └───────────┘                  └────────────┘
```

## Demo

### Node.js 프로젝트 감지 & YAML 생성

```bash
$ node src/cli.js init samples/node-project --dry-run

🔍 Scanning project: /home/user/ci-yaml-generator/samples/node-project

✅ Detected: Node.js
   Package Manager: npm
   Test Runner: jest
   Linters: eslint
   Has Build: yes

--- Generated Workflow ---

name: CI
"on":
  push:
    branches:
      - main
      - master
  pull_request:
    branches:
      - main
      - master
permissions:
  contents: read
jobs:
  lint:
    name: Lint (Node.js)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "22"
      - name: Install dependencies
        run: npm ci
      - name: Lint with eslint
        run: npx eslint .
  test:
    name: Test (Node.js)
    runs-on: ubuntu-latest
    needs:
      - lint
    strategy:
      matrix:
        node-version:
          - "18"
          - "20"
          - "22"
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - name: Install dependencies
        run: npm ci
      - name: Test with jest
        run: npx jest --coverage
  build:
    name: Build (Node.js)
    runs-on: ubuntu-latest
    needs:
      - test
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
      - name: Install dependencies
        run: npm ci
      - name: Build
        run: npm run build
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    needs:
      - test
    steps:
      - uses: actions/checkout@v4
      - name: Semgrep SAST
        uses: returntocorp/semgrep-action@v1
      - name: TruffleHog Secret Scan
        uses: trufflesecurity/trufflehog@main
```

### Python 프로젝트 감지 (JSON 출력)

```bash
$ node src/cli.js detect samples/python-project

🔍 Detecting project: /home/user/ci-yaml-generator/samples/python-project

[
  {
    "ecosystem": "python",
    "language": "Python",
    "packageManager": { "name": "pip", "install": "pip install -e \".[dev]\"" },
    "testRunner": { "name": "pytest", "command": "pytest" },
    "linters": [
      { "name": "ruff", "command": "ruff check ." },
      { "name": "mypy", "command": "mypy ." }
    ],
    "hasBuild": false,
    "versions": ["3.10", "3.11", "3.12"]
  }
]
```

### YAML 검증

```bash
$ node src/cli.js validate .github/workflows/ci.yml

🔍 Validating: /home/user/project/.github/workflows/ci.yml

✅ Valid GitHub Actions workflow
```

## 실행 방법

```bash
# 의존성 설치
npm install

# 현재 프로젝트에서 YAML 생성
node src/cli.js init .

# 특정 디렉토리 스캔
node src/cli.js init ./my-project

# stdout으로만 출력 (파일 미생성)
node src/cli.js init . --dry-run

# 생성된 YAML 검증
node src/cli.js validate .github/workflows/ci.yml

# 감지 결과만 보기 (JSON)
node src/cli.js detect .
```

## 샘플 프로젝트 데모

```bash
# Node.js 프로젝트
node src/cli.js init samples/node-project --dry-run

# Python 프로젝트
node src/cli.js init samples/python-project --dry-run

# Go 프로젝트
node src/cli.js init samples/go-project --dry-run
```

## 구조

```
ci-yaml-generator/
├── src/
│   ├── cli.js          # CLI 엔트리포인트 (init/validate/detect)
│   ├── detector.js     # 프로젝트 감지 로직
│   ├── generator.js    # GitHub Actions YAML 생성
│   ├── validator.js    # YAML 문법/구조 검증
│   └── rules.json      # 감지 규칙 설정 (확장 가능)
├── samples/
│   ├── node-project/   # Node.js 샘플 (jest + eslint)
│   ├── python-project/ # Python 샘플 (pytest + ruff + mypy)
│   └── go-project/     # Go 샘플 (go test + go vet)
├── BUILD_LOG.md        # 빌드 일지
├── STATUS.md           # 결과 상태
└── README.md
```

## 원본
prototype-pipeline spec: ci-yaml-generator
