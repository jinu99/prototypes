# Dark Path Detector

> 코드에서 관측성이 누락된 에러 경로(dark path)를 찾아내는 정적 분석 CLI 도구

## Architecture

```
  JS/TS Files
      │
      ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Scanner   │────▶│    Parser    │────▶│   Analyzer   │
│  (glob +    │     │ (tree-sitter │     │ (AST walk +  │
│  file I/O)  │     │  JS/TS/TSX)  │     │ pattern match│
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                              ┌─────────────────┤
                              ▼                 ▼
                     ┌──────────────┐   ┌──────────────┐
                     │  Formatter   │   │   Coverage    │
                     │ (terminal /  │   │   Calculator  │
                     │    JSON)     │   │  (observed /  │
                     └──────────────┘   │   total %)    │
                              │         └──────────────┘
                              ▼
                     CLI Output / JSON
```

## Demo

```
$ node bin/cli.js test-fixtures/

  Dark Path Detector
  Finding unobserved error paths in your code

  sample.ts
    ◐ L12 Catch block has no logging, error reporting, or rethrow [silent-catch]
    ◐ L22 Catch block has no logging, error reporting, or rethrow [silent-catch]

  sample.js
    ● L8 Empty catch block — error is silently swallowed [empty-catch]
    ◐ L16 Catch block has no logging, error reporting, or rethrow [silent-catch]
    ◐ L33 Error parameter 'err' is never used in callback body [ignored-error-param]
    ◐ L49 Error parameter 'error' is never used in callback body [ignored-error-param]

  ─── Summary ───

  Files scanned:     2
  Error paths found: 10
  Dark paths:        6
  Coverage:          ████████░░░░░░░░░░░░ 40%
```

Express.js에서 실행 시:
```
$ node bin/cli.js /path/to/express

  lib/view.js
    ◐ L202 Catch block has no logging, error reporting, or rethrow [silent-catch]

  ─── Summary ───

  Files scanned:     50
  Error paths found: 23
  Dark paths:        1
  Coverage:          ███████████████████░ 96%
```

## 실행 방법

```bash
# 의존성 설치
npm install

# 실행
node bin/cli.js <directory>

# JSON 출력
node bin/cli.js <directory> --json

# 특정 패턴 제외
node bin/cli.js <directory> --ignore "scripts/**,examples/**"
```

## 감지 패턴

| 패턴 | 심각도 | 설명 |
|------|--------|------|
| `empty-catch` | ● high | 빈 catch 블록 — 에러를 완전히 삼킴 |
| `silent-catch` | ◐ medium | catch 블록에 로깅/리포팅/rethrow 없음 |
| `ignored-error-param` | ◐ medium | 에러 콜백의 err 파라미터를 사용하지 않음 |

`// @dark-path-ignore` 주석으로 의도적 무시를 표시할 수 있음.

## 구조

```
dark-path-detector/
├── bin/
│   └── cli.js            # CLI 엔트리포인트
├── src/
│   ├── parser.js          # tree-sitter 파서 (JS/TS/TSX)
│   ├── analyzer.js        # AST 순회 + dark path 패턴 매칭
│   ├── scanner.js         # 디렉토리 스캔 + 파일 분석 오케스트레이션
│   └── formatter.js       # 터미널/JSON 출력 포매터
├── test-fixtures/
│   ├── sample.js          # JS 테스트 케이스
│   └── sample.ts          # TS 테스트 케이스
├── BUILD_LOG.md
├── STATUS.md
└── package.json
```

## 원본
prototype-pipeline spec: dark-path-detector
