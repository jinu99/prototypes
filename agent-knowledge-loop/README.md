# Agent Knowledge Loop

> 에이전트 세션 로그에서 실패-해결 패턴을 자동 추출하여 에이전트-독립적 규칙 파일로 동기화하는 CLI 파이프라인

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌────────────┐     ┌──────────────────┐
│  Session Logs   │────▶│  Extractor   │────▶│  SQLite DB │────▶│  Rule Exporter   │
│  (JSONL/text)   │     │  (패턴 매칭)  │     │  (중복 병합) │     │                  │
└─────────────────┘     └──────────────┘     └────────────┘     └──────┬───────────┘
                                                                       │
                                                          ┌────────────┼────────────┐
                                                          ▼            ▼            ▼
                                                     CLAUDE.md   AGENTS.md   .cursor/rules
```

## Demo

### 1. 세션 로그 Ingest

```
$ uv run python main.py ingest samples/*.jsonl

  → Processing: session_docker_debug.jsonl
    ✓ New: Error: Cannot find module '/app/server.js'     at Module._re...
  → Processing: session_git_conflict.jsonl
    ✓ New: git pull을 했는데 CONFLICT가 발생했어요. 어떻게 해결하나요?...
  → Processing: session_python_import.jsonl
    ✓ New: ImportError: cannot import name 'Request' from 'flask' 에러가 나...
    ✓ New: 동작합니다! 근데 다른 곳에서 DeprecationWarning이 뜨네요...

  Summary: 4 new, 0 merged. Total in DB: 4
```

### 2. 중복 감지 (같은 로그 재실행)

```
$ uv run python main.py ingest samples/session_docker_debug.jsonl

  → Processing: session_docker_debug.jsonl
    ↻ Merged: Error: Cannot find module '/app/server.js'...

  Summary: 0 new, 1 merged. Total in DB: 4
```

### 3. 교훈 목록 확인

```
$ uv run python main.py list

  [1] [dependency] ImportError: cannot import name 'Request' from 'flask'... (×2)
      → Flask 0.12에서는 Request를 직접 import하는 방식이 다릅니다...
  [2] [docker] Error: Cannot find module '/app/server.js'...
      → COPY 경로와 CMD 경로 불일치 문제...
  ...
```

### 4. 규칙 파일 내보내기

```
$ uv run python main.py export claude.md -o output/CLAUDE.md
  ✓ Exported 4 lessons to output/CLAUDE.md

$ uv run python main.py export cursor -o output/.cursor/rules/learned.mdc
  ✓ Exported 4 lessons to output/.cursor/rules/learned.mdc
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 세션 로그 ingest
uv run python main.py ingest <log-file-1> <log-file-2> ...

# 교훈 목록 확인
uv run python main.py list

# 규칙 파일 내보내기 (claude.md | agents.md | cursor)
uv run python main.py export <format> [-o output-path]

# DB 리셋
uv run python main.py reset
```

## 구조

```
agent-knowledge-loop/
├── main.py                 # CLI 진입점 (ingest, export, list, reset)
├── src/
│   ├── db.py               # SQLite 교훈 저장소 + 중복 병합
│   ├── extractor.py        # 세션 로그 → 실패-해결 패턴 추출
│   └── exporter.py         # 교훈 → CLAUDE.md / AGENTS.md / .cursor/rules
├── samples/                # 샘플 세션 로그 (JSONL)
│   ├── session_docker_debug.jsonl
│   ├── session_git_conflict.jsonl
│   └── session_python_import.jsonl
├── BUILD_LOG.md            # 빌드 일지
└── STATUS.md               # 완료 상태
```

## 원본
prototype-pipeline spec: agent-knowledge-loop
