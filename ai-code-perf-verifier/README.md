# AI Code Perf Verifier

> Git diff에서 변경된 Python 함수를 자동 식별하고, 변경 전/후 성능을 비교하여 머지 전 성능 회귀를 탐지하는 CLI 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        perf-verify CLI                         │
│                         (cli.py)                               │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────┐    git diff --unified=0    ┌────────────┐
│   Diff Parser       │◀──────────────────────────▶│    Git     │
│  (diff_parser.py)   │                            │ Repository │
│                     │                            └────────────┘
│ ChangedFile[]:      │
│  - path             │
│  - changed_lines    │
└──────────┬──────────┘
           │ 변경된 .py 파일 + 라인 번호
           ▼
┌─────────────────────┐
│   AST Analyzer      │    Python AST 파싱으로
│  (ast_analyzer.py)  │    변경 라인이 속한
│                     │    함수/메서드 식별
│ FunctionInfo[]:     │
│  - name             │
│  - start/end_line   │
│  - module           │
└──────────┬──────────┘
           │ 변경된 함수 목록
           ▼
┌─────────────────────┐    git show ref:file    ┌────────────────┐
│   Benchmarker       │◀───────────────────────▶│ Before Source  │
│  (benchmarker.py)   │                         │  (at git ref)  │
│                     │                         └────────────────┘
│ - 테스트 자동 탐색   │    time.perf_counter
│ - warmup + N회 실행  │    tracemalloc
│ - 시간/메모리 측정   │
│                     │
│ BenchResult[]:      │
│  - avg_time_ms      │
│  - peak_memory_kb   │
└──────────┬──────────┘
           │ before/after 벤치마크 결과
           ▼
┌─────────────────────┐
│   Reporter          │    Rich 테이블로
│  (reporter.py)      │    비교 리포트 출력
│                     │
│ - ratio 계산        │    exit code:
│ - threshold 비교    │    0 = OK
│ - 회귀 탐지 판정    │    1 = 회귀 감지
└─────────────────────┘
```

## Demo

`demo.sh`를 실행하면 임시 git 저장소에서 성능 회귀를 시뮬레이션합니다.

```bash
# E2E 데모 실행
bash demo.sh
```

**데모 시나리오**: fibonacci를 O(n) → O(2^n) 재귀로, sort를 내장 정렬 → 버블 정렬로 변경한 뒤 회귀를 탐지합니다.

```
=== Running perf-verify ===

        Changed Functions
┌──────────────┬────────────────┬───────┐
│ Function     │ File           │ Lines │
├──────────────┼────────────────┼───────┤
│ fibonacci    │ algorithms.py  │ 4-12  │
│ sort_data    │ algorithms.py  │ 15-23 │
└──────────────┴────────────────┴───────┘

          Performance Comparison
┌──────────────┬────────┬────────┬───────┬────────┬──────────────┐
│ Function     │ Before │ After  │ Ratio │ Mem Δ  │ Status       │
│              │ (ms)   │ (ms)   │       │ (KB)   │              │
├──────────────┼────────┼────────┼───────┼────────┼──────────────┤
│ fibonacci    │  0.03  │ 18.42  │ 614x  │ +2.1   │ ⚠ SLOWER     │
│ sort_data    │  0.15  │  8.71  │ 58.1x │ +0.3   │ ⚠ SLOWER     │
└──────────────┴────────┴────────┴───────┴────────┴──────────────┘

⚠ Performance regression detected! (threshold: 2.0x)

=== Exit code: 1 ===
```

일반 사용 예시:

```bash
# 현재 브랜치에서 변경된 함수만 확인
uv run perf-verify --list-only

# main 브랜치 대비 성능 비교 (5회 반복)
uv run perf-verify --ref main --runs 5

# 3배 이상 느려질 때만 회귀로 판정
uv run perf-verify --threshold 3.0
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# CLI 사용 (git 프로젝트 내에서)
uv run perf-verify                  # HEAD~1 대비 성능 비교
uv run perf-verify --list-only      # 변경 함수 목록만 출력
uv run perf-verify --threshold 3.0  # 3배 이상 느려질 때만 경고
uv run perf-verify --runs 10        # 벤치마크 10회 반복
uv run perf-verify --ref main       # main 브랜치 대비 비교

# End-to-end 데모
bash demo.sh
```

## 구조

```
├── perf_verify/
│   ├── cli.py            # CLI 진입점 (perf-verify 명령)
│   ├── diff_parser.py    # git diff 파싱 → 변경 파일/라인 추출
│   ├── ast_analyzer.py   # Python AST로 변경 함수/메서드 식별
│   ├── benchmarker.py    # 기존 테스트를 벤치마크로 실행 (시간/메모리)
│   └── reporter.py       # Rich 테이블 리포트 출력
├── sample_project/       # 데모용 샘플 프로젝트
│   ├── algorithms.py
│   └── tests/test_algorithms.py
├── demo.sh               # E2E 데모 스크립트
├── pyproject.toml
└── BUILD_LOG.md
```

## 원본
prototype-pipeline spec: ai-code-perf-verifier
