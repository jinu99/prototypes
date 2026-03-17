---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Vibe Code Decay Detector

**Git 히스토리 기반 아키텍처 침식 탐지 CLI**

커밋별 의존성 결합도, 순환 의존성, churn rate 추적 및 commit-revert 패턴 감지

|  |  |
|---|---|
| 카테고리 | Developer Tooling / Code Quality |
| 스택 | Python, tree-sitter, Click, Rich, SQLite |
| 날짜 | 2026-03-09 |

<!--
이번에 만든 프로토타입은 Vibe Code Decay Detector다. git 히스토리를 분석해서 아키텍처가 조용히 무너지고 있는지 감지하는 CLI 도구다. AI 코딩 시대에 꽤 실질적인 문제를 다루고 있어서, 그 배경부터 얘기해보겠다.
-->

---

## Background

**AI 코딩 도구의 역설: 빠르게 만들수록 조용히 무너진다**

- Cursor, Copilot, Claude Code 같은 AI 코딩 도구가 보편화되면서 코드 생성 속도가 비약적으로 빨라짐
- 개별 커밋 단위로는 정상적인 코드지만, **수십 커밋이 누적되면 아키텍처가 조용히 침식**됨
- CodeRabbit 분석: AI 공동 작성 코드는 인간 작성 코드 대비 **1.7배 많은 주요 이슈** 포함
- 모듈 간 의존성이 얽히고, 유사 로직이 여러 파일에 중복 생성되고, 추상화 계층이 무너짐
- 개발자는 PR에서 개별 diff만 보기 때문에 **점진적 침식을 인지하지 못함**

<!--
AI 코딩 도구가 꽤 좋아졌다. 근데 재밌는 역설이 하나 있다. 개별 커밋 단위로 보면 괜찮은 코드인데, 30개 40개 쌓이면 아키텍처가 슬금슬금 무너진다. CodeRabbit이 분석한 데이터를 보면 AI가 같이 쓴 코드에서 주요 이슈가 1.7배 더 나온다. 결국 이건 속도와 구조의 트레이드오프 문제인데, 개발자가 PR diff만 보고 있으니까 점진적 침식을 알아차리기가 어렵다.
-->

---

## Pain Point

**커뮤니티에서 반복적으로 나오는 고통**

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/SideProject | ●●● | AI로 빠르게 코드를 생성하지만, 시간이 지날수록 아키텍처가 무너져 **수정이 불가능**해진다 |
| 2 | Hacker News | ●●● | AI 생성 코드의 **commit-revert 반복 루프**가 증가하며, 디버깅에 코딩의 5배 시간 소요 |
| 3 | GeekNews | ●●● | AI 코딩 도구가 기존 코드베이스의 구조를 이해하지 못해 **일관성 없는 코드**를 점진적으로 추가 |

모든 출처에서 Signal Strength 3 (강한 신호).
공통 패턴: **개별 코드는 괜찮지만, 누적되면 구조가 무너진다.**

<!--
Reddit, Hacker News, GeekNews에서 비슷한 얘기가 계속 올라온다. 셋 다 signal strength가 가장 높은 3이다. 공통점은 결국 같다. 개별 코드는 괜찮은데 쌓이면 구조가 무너진다는 거다. 특히 Hacker News에서 나온 commit-revert 반복 루프 얘기가 인상적인데, 디버깅에 코딩의 5배 시간이 든다는 건 결국 아키텍처 침식의 증상이다.
-->

---

## Solution

**커밋 단위로 아키텍처 침식을 추적하고, 악화 추세를 조기 경고한다**

핵심 아이디어:
> 기존 린터(ESLint, SonarQube)는 **개별 파일의 코드 품질**을 본다.
> 우리는 **커밋 히스토리에 걸친 아키텍처 레벨 추세**를 본다.

| 기존 도구 | Decay Detector |
|-----------|---------------|
| SonarQube: 파일 단위 정적 분석, 추세 없음 | 커밋별 결합도/순환 의존성 **시계열 추적** |
| CodeClimate: 유지보수성 점수, AI 패턴 무관 | **commit-revert, rapid-edit** 패턴 감지 |
| CodeRabbit: PR 단위 diff 리뷰 | 장기 아키텍처 침식 **트렌드 경고** |

<!--
기존 도구들이 못하는 게 있다. SonarQube는 파일 단위 정적 분석이고, CodeClimate은 유지보수성 점수를 주긴 하는데 AI 코딩 패턴과는 무관하다. CodeRabbit은 PR 리뷰 도구라 장기 추세를 볼 수 없다. 우리 접근법은 다르다. 개별 파일이 아니라 커밋 히스토리 전체를 보고, 결합도와 순환 의존성의 시계열을 추적한다. 사람으로 치면 건강검진에서 혈압을 한 번 재는 게 아니라, 매일 재서 추세를 보는 거다.
-->

---

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
         │              │ · 의존성 그래프 구축   │
         │              │ · edge count 계산     │
         │              │ · 순환 의존성 탐지     │
         │              └──────────┬───────────┘
         ▼                         ▼
┌─────────────────┐     ┌──────────────────────┐
│Pattern Detector │     │   SQLite Storage      │
│ · add-delete    │────▶│ · commit_metrics      │
│ · delete-readd  │     │ · revert_patterns     │
│ · rapid-edit    │     │ · 시계열 저장/조회     │
└─────────────────┘     └──────────┬───────────┘
                                   ▼
                        ┌──────────────────────┐
                        │   Visualizer (Rich)   │
                        │ · 결합도 bar chart    │
                        │ · churn rate chart    │
                        │ · revert 패턴 테이블  │
                        │ · health warning      │
                        └──────────────────────┘
```

<!--
구조는 6개 모듈로 나뉜다. Git Analyzer가 히스토리를 읽고, Dependency Parser가 tree-sitter로 import문을 AST 레벨에서 파싱한다. 정규식이 아니라 AST를 쓰는 이유는 정확도 때문이다. Metrics Engine이 의존성 그래프를 만들어서 edge count와 순환 의존성을 계산하고, Pattern Detector가 add-delete나 rapid-edit 같은 commit-revert 패턴을 잡는다. 전부 SQLite에 시계열로 저장되고, Rich로 터미널에 시각화된다.
-->

---

## Demo

```
Analysis complete
  Commits: 12  Period: 2025-01-01 → 2025-01-12  Patterns: 3

╭─ Module Coupling (Edge Count) ↑ ─╮
  a1b2c3d ██░░░░░░░░░░░░░░░░ 4
  e4f5a6b ████░░░░░░░░░░░░░░ 8
  c7d8e9f ██████████░░░░░░░░ 15        ← 결합도 점진적 증가
```
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     Commit-Revert Patterns Detected      ┃
┡━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┯━━━━━━━━━━┩
│ utils/helper.py  │ add-delete│ Added →  │
│                  │           │ Deleted  │
│ src/config.py    │ rapid-edit│ 4 edits  │
│                  │           │ in 30min │
└──────────────────┴───────────┴──────────┘
```
```
╭─ Architecture Health Warnings ─╮
  WARNING: Coupling increased by 45% over the last 6 commits
  WARNING: Code churn increased by 67% over the last 6 commits
╰─────────────────────────────────╯
```

<!--
테스트 리포를 만들어서 12개 커밋을 넣고 돌린 결과다. 결합도가 4에서 15로 올라가는 게 bar chart로 보이고, commit-revert 패턴이 테이블로 나온다. 그리고 아래쪽에 경고가 뜬다. 결합도 45% 증가, churn 67% 증가. 솔직히 이 경고 하나만으로도 가치가 있다고 본다. 개발자가 뭔가 이상한데 감으로만 느끼던 걸 숫자로 보여주니까.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 판단 | 이유 |
|------|------|
| **tree-sitter로 AST 파싱** | 정규식 대신 AST를 쓰면 `from x import y`, `import x.y` 등 다양한 패턴을 정확히 잡음. 학습 가치도 높음 (심의 점수 4.7/5) |
| **자동 window 사이징** | 경고 판정 window를 커밋 수의 절반으로 자동 조정. 커밋 10개인 repo에서 window 20이면 경고가 안 나오는 문제 해결 |
| **모듈명 정규화 함수 추가** | `src/models` vs `src.models` 불일치로 순환 의존성이 0개로 나오던 버그. `_normalize_module()` 추가 후 1→4개 감지 |

### 심의 점수

| 항목 | 점수 |
|------|------|
| 문제 진정성 (Authenticity) | 4.3 / 5 |
| 프로토타입 적합성 (Prototypability) | 4.0 / 5 |
| 신선도 (Freshness) | 3.3 / 5 |
| 학습 가치 (Learning Value) | **4.7 / 5** |

<!--
몇 가지 기술 판단이 있었는데, 가장 중요한 건 tree-sitter 선택이다. 정규식으로 import문을 파싱하면 엣지 케이스가 많다. AST를 쓰면 정확하다. 실제로 구현하면서 배운 게 꽤 있었고, 심의에서도 학습 가치를 4.7로 쳐줬다. 시행착오도 있었는데, 모듈명 정규화를 안 해서 순환 의존성이 0으로 나온 적이 있다. 파일 경로와 import문의 모듈명이 다른 형식이었던 거다. 이런 건 실제로 돌려봐야 알 수 있는 문제다.
-->

---

## Results & Future

### 성과 (5/5 통과)

- [x] git 히스토리에서 커밋별 의존성 그래프 메트릭 추출 → SQLite 저장
- [x] 커밋별 결합도 및 churn rate 시계열 터미널 차트 출력
- [x] commit-revert 패턴 감지 (add-delete, delete-readd, rapid-edit)
- [x] 테스트 repo에서 침식 추이 시각적 확인 (coupling 2→17, cycles 0→4)
- [x] 메트릭 추세 악화 시 경고 ("Coupling increased by 154%")

### 한계점
- 코드 중복 감지(유사도 해시)는 범위에서 제외
- Python/JS만 지원, 다중 언어 동시 분석 불가
- pre-commit hook / CI 연동 없음

### 프로덕트가 되려면
- **CI/CD 연동**: GitHub Actions에서 PR마다 자동 실행 → 침식 경고를 PR comment로
- **언어 확장**: Go, Rust, Java 등 tree-sitter grammar 추가
- **대시보드**: 시계열 데이터를 웹 UI로 시각화, 팀 단위 아키텍처 건강도 모니터링

<!--
완료 기준 5개를 다 통과했다. 결합도가 2에서 17로, 순환 의존성이 0에서 4로 증가하는 걸 시각적으로 확인할 수 있었다. 솔직히 한계는 있다. 코드 중복 감지는 빠져있고, 언어도 Python과 JS만 된다. 프로덕트가 되려면 CI에 붙여서 PR마다 자동으로 돌아가야 한다. 그래서 이걸 왜 만들었냐면, 결국 AI 코딩 시대에 아키텍처 침식은 피할 수 없는 문제고, 그걸 조기에 인지하는 도구가 아직 없기 때문이다. 이 프로토타입이 그 방향의 첫 단추다.
-->
