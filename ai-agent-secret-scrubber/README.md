# AI Agent Secret Scrubber

> AI 에이전트 출력 스트림에서 시크릿을 실시간 탐지·마스킹하는 쉘 래퍼

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
