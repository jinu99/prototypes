# Agent Token Waste Analyzer

> Claude Code 세션 로그를 분석하여 토큰 낭비 패턴을 식별하고 최적화 제안을 제공하는 터미널 대시보드 CLI

## 실행 방법

```bash
# 의존성 설치
uv sync

# 세션 로그 목록 보기
uv run python run.py list

# 최근 세션 분석
uv run python run.py latest

# 특정 세션 분석
uv run python run.py analyze <path-to-session.jsonl>

# 샘플 세션으로 데모
uv run python samples/generate_sample.py
uv run python run.py analyze samples/sample_session.jsonl
```

## 감지하는 낭비 패턴

| 패턴 | 설명 |
|------|------|
| **repeated_read** | 같은 파일을 여러 번 Read하는 패턴 |
| **unused_search** | Grep/Glob 결과를 이후 행동에서 활용하지 않는 패턴 |
| **duplicate_context** | 매 턴마다 대량의 캐시를 재로딩하면서 극소량의 출력만 생성하는 패턴 |

## 구조

```
.
├── run.py                  # CLI 진입점
├── src/
│   ├── parser.py           # JSONL 세션 로그 파서
│   ├── analyzer.py         # 낭비 패턴 감지 엔진
│   ├── dashboard.py        # Rich 터미널 대시보드
│   └── main.py             # CLI 명령어 정의
├── samples/
│   ├── generate_sample.py  # 샘플 세션 로그 생성기
│   └── sample_session.jsonl
├── BUILD_LOG.md            # 빌드 일지
└── STATUS.md               # 검증 결과
```

## 원본
prototype-pipeline spec: agent-token-waste-analyzer
