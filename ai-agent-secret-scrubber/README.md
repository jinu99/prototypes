# AI Agent Secret Scrubber

> AI 에이전트 출력 스트림에서 시크릿을 실시간 탐지·마스킹하는 쉘 래퍼

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI (main.py)                            │
│                  scan │ wrap │ demo 명령 분기                    │
└───────┬─────────────────┬───────────────────────────────────────┘
        │                 │
        ▼                 ▼
┌───────────────┐   ┌──────────────────────────────────────────┐
│  SecretRegistry│   │          Scrubber (scrubber.py)          │
│ (registry.py) │   │                                          │
│               │   │  subprocess.Popen ─▶ selectors 기반      │
│ .env 파싱     │   │  stdout/stderr 실시간 스트림 인터셉트     │
│ credentials   │   │                                          │
│  .json 파싱   │   │  ┌─ 라인 단위 처리 ──────────────────┐   │
│               │   │  │         SecretDetector            │   │
│  ┌──────────┐ │   │  │        (detector.py)              │   │
│  │ key=value│──────▶ │                                   │   │
│  │  수집    │ │   │  │  1️⃣ Registry 매칭 (정확 일치)     │   │
│  └──────────┘ │   │  │  2️⃣ Pattern 매칭 (regex)         │   │
└───────────────┘   │  │  3️⃣ Entropy 탐지 (Shannon)       │   │
                    │  │                                   │   │
                    │  │  탐지 → "***" 마스킹              │   │
                    │  └───────────────────────────────────┘   │
                    │                                          │
                    └─────────┬──────────────────┬─────────────┘
                              │                  │
                              ▼                  ▼
                    ┌──────────────┐   ┌──────────────────┐
                    │  마스킹된    │   │  .scrubber_log   │
                    │  stdout/stderr│   │   .json          │
                    │  (실시간 출력)│   │  (탐지 이력 기록) │
                    └──────────────┘   └──────────────────┘
```

**데이터 흐름 요약:**

1. `SecretRegistry`가 `.env` / `credentials.json`에서 시크릿 값을 수집
2. `Scrubber`가 대상 명령을 subprocess로 실행, `selectors`로 stdout/stderr를 실시간 감시
3. 각 라인을 `SecretDetector`의 3단계 탐지 파이프라인(registry → pattern → entropy)에 통과
4. 탐지된 시크릿은 `***`로 마스킹하여 출력, 탐지 이력은 JSON 로그에 기록

## Demo

### 빌트인 데모 실행

```bash
$ uv run main.py demo
```

**Step 1 — 시크릿 스캔 결과:**

```
Scanned: /path/to/demo_workspace
Secret Registry: 5 secrets loaded
  - DATABASE_URL: ********
  - API_KEY: ********
  - AWS_SECRET_ACCESS_KEY: ********
  - STRIPE_SECRET_KEY: ********
  - SLACK_TOKEN: ********
```

**Step 2 — `cat .env` 출력이 마스킹됨:**

```
# Demo secrets
DATABASE_URL=***
API_KEY=***
AWS_SECRET_ACCESS_KEY=***
STRIPE_SECRET_KEY=***
SLACK_TOKEN=***
HARMLESS_VAR=hello       ← 짧은 값은 시크릿으로 간주하지 않음
SHORT=abc                ← 8자 미만은 무시
```

**Step 3 — 탐지 통계:**

```
[scrubber] Detection stats: registry=5, pattern=1, entropy=0
```

> `registry=5`: .env에서 수집한 값과 정확 일치, `pattern=1`: connection URL 내 비밀번호가 regex로 추가 탐지됨

### 실전 사용 예시

```bash
# AI 에이전트 실행 시 시크릿이 터미널에 노출되지 않도록 래핑
$ uv run main.py wrap --scan-dir ./my-project python agent.py

# 특정 디렉토리의 시크릿만 스캔
$ uv run main.py scan ./my-project
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 데모 실행 (샘플 .env 생성 + cat 래핑)
uv run main.py demo

# 시크릿 스캔
uv run main.py scan [directory]

# 명령어 래핑 (시크릿 마스킹)
uv run main.py wrap --scan-dir <env-directory> <command> [args...]
```

### 예시

```bash
# .env가 있는 디렉토리에서 cat 실행 시 시크릿 마스킹
uv run main.py wrap --scan-dir ./my-project cat ./my-project/.env

# 에이전트 명령 래핑
uv run main.py wrap --scan-dir . python agent.py
```

## 탐지 방식

1. **레지스트리 매칭**: .env, credentials.json에서 수집한 시크릿 값을 정확히 매칭
2. **패턴 매칭**: `sk-`, `ghp_`, `AKIA`, `eyJ` (JWT) 등 알려진 시크릿 형식 regex
3. **엔트로피 탐지**: Shannon entropy 기반으로 미지의 고엔트로피 문자열 탐지

## 구조

```
├── main.py          # CLI 진입점 (scan, wrap, demo)
├── registry.py      # 시크릿 레지스트리 (.env, credentials.json 파싱)
├── detector.py      # 3단계 탐지 (registry, pattern, entropy)
├── scrubber.py      # 쉘 래퍼 (subprocess + selector 기반 스트림 인터셉트)
├── pyproject.toml   # uv 프로젝트 설정
├── BUILD_LOG.md     # 빌드 일지
└── STATUS.md        # 프로토타입 상태
```

## 원본
prototype-pipeline spec: ai-agent-secret-scrubber
