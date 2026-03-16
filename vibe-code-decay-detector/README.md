# Vibe Code Decay Detector

> Git 히스토리 기반 아키텍처 침식 탐지 CLI — 의존성 결합도, 순환 의존성, churn rate 추적 및 commit-revert 패턴 감지

## Architecture

```
┌─────────────────┐
│   CLI (Click)   │  decay-detect scan <repo-path>
│    cli.py       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────┐
│  Git Analyzer   │────▶│  Dependency Parser    │
│ git_analyzer.py │     │ dependency_parser.py  │
│                 │     │ (tree-sitter 기반)    │
│ · commit 목록   │     │ · Python import 파싱  │
│ · 파일 내용     │     │ · JS/TS import 파싱   │
│ · churn 통계    │     └──────────┬───────────┘
│ · diff 파일     │                │
└────────┬────────┘                ▼
         │              ┌──────────────────────┐
         │              │   Metrics Engine      │
         │              │   metrics.py          │
         │              │                       │
         │              │ · 의존성 그래프 구축   │
         │              │ · edge count 계산     │
         │              │ · 순환 의존성 탐지     │
         │              └──────────┬───────────┘
         │                         │
         ▼                         ▼
┌─────────────────┐     ┌──────────────────────┐
│Pattern Detector │     │   SQLite Storage      │
│pattern_detector │     │   storage.py          │
│                 │     │                       │
│ · add-delete    │────▶│ · commit_metrics 테이블│
│ · delete-readd  │     │ · revert_patterns     │
│ · rapid-edit    │     │ · 시계열 저장/조회     │
└─────────────────┘     └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │   Visualizer (Rich)   │
                        │   visualizer.py       │
                        │                       │
                        │ · 결합도 bar chart    │
                        │ · 순환 의존성 trend   │
                        │ · churn rate chart    │
                        │ · revert 패턴 테이블  │
                        │ · health warning      │
                        └──────────────────────┘
```

**데이터 흐름 요약:**
1. **Git 히스토리 수집** — `git log`, `git ls-tree`, `git show`, `git diff-tree`로 커밋별 소스 파일과 변경 내역 추출
2. **의존성 분석** — tree-sitter로 Python/JS import 구문을 파싱하여 모듈 간 의존성 그래프 구축
3. **메트릭 계산** — edge count(결합도), 순환 의존성 수, churn(추가/삭제 라인 수) 산출
4. **패턴 감지** — 파일의 add→delete, delete→re-add, 단시간 반복 수정(rapid-edit) 패턴 탐지
5. **저장 및 시각화** — SQLite에 시계열 저장 후 Rich 터미널 차트와 경고 메시지 출력

## Demo

### 테스트 리포지토리 생성 및 스캔

```bash
# 1. 테스트용 Git 리포지토리 생성
$ bash create_test_repo.sh
Creating test repo at /tmp/decay-test-repo...
Done.

# 2. 아키텍처 decay 스캔 실행
$ uv run decay-detect scan /tmp/decay-test-repo

Scanning: /tmp/decay-test-repo
Database: /tmp/decay-test-repo/.decay-detect.db

Found 12 commits to analyze.

Analyzing commits... ━━━━━━━━━━━━━━━━━━━━ 12/12
```

### 출력 예시

```
Analysis complete
  Commits: 12  Period: 2025-01-01 → 2025-01-12  Patterns: 3

╭─ Module Coupling (Edge Count) ↑ ─╮
│                                   │
╰───────────────────────────────────╯
  a1b2c3d ██░░░░░░░░░░░░░░░░ 4
  e4f5a6b ████░░░░░░░░░░░░░░ 8
  c7d8e9f ██████████░░░░░░░░ 15
  ...

  No cyclic dependencies detected.

╭─ Code Churn (lines changed) ↑ ─╮
│                                  │
╰──────────────────────────────────╯
  a1b2c3d ████████░░░░░░░░░░ +45 -12
  e4f5a6b ██░░░░░░░░░░░░░░░░ +10 -3
  c7d8e9f ██████████████████ +120 -80
  ...

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     Commit-Revert Patterns Detected      ┃
┡━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┯━━━━━━━━━━┩
│ File             │ Type      │ Detail   │
├──────────────────┼───────────┼──────────┤
│ utils/helper.py  │ add-delete│ Added in │
│                  │           │ a1b2c3d, │
│                  │           │ deleted  │
│                  │           │ in e4f5a6│
│ src/config.py    │ rapid-edit│ 4 edits  │
│                  │           │ within   │
│                  │           │ 30min    │
└──────────────────┴───────────┴──────────┘

╭─ Architecture Health Warnings ─╮
│                                 │
╰─────────────────────────────────╯
  WARNING: Coupling increased by 45% over the last 6 commits (avg 5 → 12 edges)
  WARNING: Code churn increased by 67% over the last 6 commits

Results saved to /tmp/decay-test-repo/.decay-detect.db
```

### 주요 CLI 옵션

```bash
# 최근 200개 커밋만 분석
$ uv run decay-detect scan <repo-path> --max-commits 200

# 별도 DB 파일에 메트릭 저장
$ uv run decay-detect scan <repo-path> --db metrics.db
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실행
uv run decay-detect scan <repo-path>

# 옵션
uv run decay-detect scan <repo-path> --max-commits 200 --db metrics.db
```

## 테스트

```bash
# 테스트 repo 생성
bash create_test_repo.sh

# 분석 실행
uv run decay-detect scan /tmp/decay-test-repo
```

## 구조

```
decay_detect/
├── __init__.py
├── cli.py                 # Click CLI 엔트리포인트
├── git_analyzer.py        # Git 히스토리 분석 (커밋 목록, 파일 내용, churn)
├── dependency_parser.py   # tree-sitter 기반 import 파싱 (Python, JS)
├── metrics.py             # 의존성 그래프 메트릭 (edge count, 순환 의존성)
├── pattern_detector.py    # commit-revert 패턴 감지 (add-delete, rapid-edit)
├── visualizer.py          # Rich 터미널 차트 및 경고 출력
└── storage.py             # SQLite 시계열 저장
```

## 원본
prototype-pipeline spec: vibe-code-decay-detector
