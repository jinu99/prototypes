# CI/CD YAML 자동 생성기

> 프로젝트 디렉토리를 스캔하여 GitHub Actions CI 워크플로우 YAML을 자동 생성하는 CLI 도구

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
