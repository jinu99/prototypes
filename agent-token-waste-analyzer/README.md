# Agent Token Waste Analyzer

> Claude Code 세션 로그를 분석하여 토큰 낭비 패턴을 식별하고 최적화 제안을 제공하는 터미널 대시보드 CLI

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI (run.py / main.py)                       │
│              list · analyze <path> · latest                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │ 명령어 분기
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Parser (parser.py)                             │
│                                                                     │
│  ~/.claude/projects/**/*.jsonl  ──▶  SessionData                    │
│                                       ├─ messages: SessionMessage[] │
│                                       ├─ tool_calls: ToolCall[]     │
│                                       └─ token usage 집계           │
└────────────────────────────┬────────────────────────────────────────┘
                             │ SessionData
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Analyzer (analyzer.py)                           │
│                                                                     │
│  ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────────┐  │
│  │  repeated_read   │ │  unused_search   │ │  duplicate_context  │  │
│  │  같은 파일 반복  │ │  미사용 검색결과 │ │  캐시 과다 재로딩   │  │
│  │  Read 감지       │ │  Grep/Glob 감지  │ │  턴별 비율 분석     │  │
│  └────────┬─────────┘ └────────┬─────────┘ └──────────┬──────────┘  │
│           └────────────────────┼───────────────────────┘             │
│                                ▼                                    │
│                  WastePattern[] + OptimizationSuggestion[]           │
│                         → AnalysisResult                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │ AnalysisResult
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Dashboard (dashboard.py)                          │
│                         Rich 터미널 UI                              │
│                                                                     │
│  ┌──────────────────┬──────────────────┐                            │
│  │  📊 Session      │  🔧 Tool         │                            │
│  │     Summary      │     Distribution │                            │
│  ├──────────────────┴──────────────────┤                            │
│  │  🔥 Waste Hotspots (Top 5)          │                            │
│  ├─────────────────────────────────────┤                            │
│  │  💡 Optimization Suggestions        │                            │
│  ├─────────────────────────────────────┤                            │
│  │  Efficiency Grade: A~F │ Waste %    │                            │
│  └─────────────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Demo

샘플 세션 로그를 생성한 뒤 분석하는 CLI 워크플로우:

```bash
# 1. 샘플 세션 로그 생성
$ uv run python samples/generate_sample.py
Generated sample session: samples/sample_session.jsonl

# 2. 샘플 세션 분석
$ uv run python run.py analyze samples/sample_session.jsonl

Parsing: samples/sample_session.jsonl
Found 42 tool calls in 87 messages
Analyzing waste patterns...

──────────────────── Agent Token Waste Analyzer ────────────────────

┌──── 📊 Session Summary ─────┬──── 🔧 Tool Distribution ────┐
│ Session: sample_session...   │ Tool       Count Distribution │
│ Tool Calls: 42               │ Read         18  ▓▓▓▓▓▓▓░░ 43%│
│ Messages: 87                 │ Grep          9  ▓▓▓░░░░░░ 21%│
│                              │ Edit          7  ▓▓░░░░░░░ 17%│
│ Total Tokens:     245.3K     │ Bash          5  ▓░░░░░░░░ 12%│
│ Effective Tokens: 198.1K     │ Glob          3  ▓░░░░░░░░  7%│
│ Wasted Tokens:     47.2K     │                               │
│                              │                               │
│ Effective Ratio: ████████░░ 80.8%                            │
└──────────────────────────────┴───────────────────────────────┘

┌──── 🔥 Waste Hotspots (Top 5) ───────────────────────────────┐
│  # │ Type             │ Description              │ Wasted    │
│  1 │ repeated_read    │ File read 5 times: ...   │ 22.1K     │
│  2 │ duplicate_context│ 4 turns with >95% cache  │ 15.3K     │
│  3 │ unused_search    │ Grep result not used     │  5.8K     │
└──────────────────────────────────────────────────────────────┘

┌──── 💡 Optimization Suggestions ─────────────────────────────┐
│ 1. Avoid re-reading files                                     │
│    3 files were read multiple times. Cache file contents...   │
│    Estimated savings: 22.1K tokens                            │
│ 2. Reduce context re-loading                                  │
│    Many turns re-loaded large context with minimal output...  │
│    Estimated savings: 15.3K tokens                            │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Efficiency Grade: B  |  Waste: 19.2%  |  Patterns: 5       │
└─────────────────────────────────────────────────────────────┘
```

```bash
# 3. 실제 Claude Code 세션 로그 목록 조회
$ uv run python run.py list

Found 12 session log(s):

    0  abc123def456.jsonl  (384 KB)
       /home/user/.claude/projects/my-project
    1  789ghi012jkl.jsonl  (156 KB)
       /home/user/.claude/projects/another-project
  ...

# 4. 가장 최근 세션 바로 분석
$ uv run python run.py latest
```

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
