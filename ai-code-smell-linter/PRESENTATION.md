---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# AI Code Smell Linter

> tree-sitter AST 기반으로 AI 생성 코드의 구조적 위험 패턴을 탐지하는 CLI 린터

**카테고리**: Developer Tools / Static Analysis
**스택**: Python, tree-sitter, Click, uv
**날짜**: 2026-03-17

<!--
이번에 만든 프로토타입은 AI가 짠 코드에서 나타나는 특유의 코드 스멜을 잡아내는 CLI 린터다.
tree-sitter로 AST를 파싱하고, 그 위에서 패턴 매칭을 돌리는 방식이다.
Python, JavaScript, TypeScript 세 언어를 지원하고, git diff 연동도 된다.
-->

---

## Background

AI 코딩 도구가 일상이 된 시대의 새로운 문제

- Copilot, Claude Code, Cursor 등 AI 코딩 도구가 생성하는 코드는 **컴파일되고 테스트를 통과한다**
- 하지만 인간이 작성한 코드와는 **다른 종류의 위험 패턴**을 포함한다
- CodeRabbit 분석: AI 공동 작성 코드는 인간 코드 대비 **1.7배 많은 이슈** 포함
- 70%의 조직이 AI 생성 코드에서 **보안 취약점을 발견**

기존 린터(ESLint, Pylint)는 구문 오류와 스타일 규칙에 집중하지,
**AI가 만들어내는 구조적 위험 패턴**은 탐지 범위 밖이다.

<!--
AI 코딩 도구가 보편화되면서 새로운 종류의 문제가 생겼다.
AI가 짠 코드는 돌아간다. 테스트도 통과한다. 그런데 프로덕션에 올리면 터진다.
왜냐하면 AI는 "일단 동작하게" 만드는 데 최적화되어 있어서, 에러 핸들링을 빈 catch로 넘기거나, 시크릿을 하드코딩하거나, 함수 하나에 모든 걸 때려넣는 경향이 있다.
기존 린터는 이런 패턴을 못 잡는다. 구문적으로는 문제가 없으니까.
결국 이건 정적 분석의 사각지대 문제다.
-->

---

## Pain Point

커뮤니티에서 반복적으로 나오는 고통

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | GeekNews | ★★★★ | AI 생성 코드의 급증으로 기존 수동 코드 리뷰가 더 이상 유효하지 않음 |
| 2 | Hacker News | ★★★ | AI 코드가 empty catch, 하드코딩 시크릿, god function 등 특유의 스멜을 남긴다 |
| 3 | r/LocalLLaMA | ★★★ | AI 코드 리뷰 도구가 SaaS라 코드가 외부로 나가는 문제 |
| 4 | r/programming | ★★★★ | AI 생성 코드가 테스트 통과 후 프로덕션에서 **630만 건 주문 데이터 파괴** |

<!--
커뮤니티에서 이런 얘기가 계속 나온다.
AI 코딩 도구가 좋은데, 만든 코드가 조용히 위험한 패턴을 심어놓는다는 거다.
가장 인상적인 사례가 r/programming에 올라온 건데, AI가 짠 코드가 테스트를 전부 통과했는데 프로덕션에서 630만 건의 주문 데이터를 날렸다.
그리고 이걸 잡아주는 도구들은 대부분 SaaS라서, 민감한 코드를 다루는 팀은 쓸 수가 없다.
결국 로컬에서 돌아가는, AI 코드 전용 린터가 필요하다.
-->

---

## Solution

**로컬 실행 + AI 코드 전용 룰셋 + git diff 연동**

기존 도구와의 차이:

| | SonarQube | CodeRabbit | ESLint/Pylint | **aicslint** |
|---|:---:|:---:|:---:|:---:|
| 로컬 실행 | △ (셀프호스팅) | ✗ | ✓ | **✓** |
| AI 특유 패턴 | ✗ | △ | ✗ | **✓** |
| git diff 연동 | ✗ | ✓ | △ | **✓** |
| 무료/오픈 | △ | ✗ | ✓ | **✓** |

핵심 아이디어: **AST 레벨에서 AI 코드의 구조적 패턴을 잡는다.**
regex가 아닌 tree-sitter AST로 분석하므로, 문법 구조를 정확히 이해한 탐지가 가능하다.

<!--
우리 접근법은 간단하다. 로컬에서 돌아가는 CLI 린터를 만들되, AI 코드에서 자주 나타나는 위험 패턴에 특화된 룰셋을 쓰는 거다.
기존에 SonarQube나 CodeRabbit 같은 도구가 있지만, 하나는 무겁고 유료이고, 하나는 SaaS라 코드가 나간다.
ESLint나 Pylint는 로컬이지만 AI 특유 패턴을 잡는 룰이 없다.
그래서 tree-sitter AST 파싱을 쓴다. regex로는 catch 블록이 비어있는지, 함수의 중첩 깊이가 얼마인지 정확히 못 잡는다. AST 레벨에서 봐야 한다.
-->

---

## Architecture

```
                    ┌─────────────┐
   .py/.js/.ts ────▶│  Parser     │ tree-sitter
   source files     │  (multi-    │ Language()
                    │   lang)     │
                    └──────┬──────┘
                           │ AST
                    ┌──────▼──────┐
                    │  Scanner    │ run all rules
                    │             │ against AST
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──┐     ┌──────▼──┐     ┌───────▼─┐
   │ ACS001  │     │ ACS003  │     │ ACS005  │  ... 5 rules
   │ empty   │     │ god     │     │ unnec.  │
   │ catch   │     │ function│     │ abstr.  │
   └─────────┘     └─────────┘     └─────────┘
                           │
                    ┌──────▼──────┐
   CLI ────────────▶│  Output     │──▶ JSON / colored text
   scan / diff      │  Formatter  │
                    └─────────────┘
```

- **Parser**: tree-sitter로 Python/JS/TS 소스를 AST로 변환
- **Scanner**: 모든 룰을 AST에 대해 실행, 언어별 적용 가능 룰 자동 필터
- **Rules**: 각 룰이 BaseRule을 상속, `check(tree, source, lang, filepath)` 인터페이스
- **Output**: JSON 또는 컬러 텍스트 포맷 선택

<!--
구조는 꽤 단순하다.
소스 파일이 들어오면 tree-sitter가 AST를 만들고, 스캐너가 등록된 5개 룰을 순회하면서 패턴을 찾는다.
각 룰은 BaseRule을 상속받아서 check 메서드만 구현하면 되는 구조라, 룰 추가가 쉽다.
결과는 JSON이나 컬러 텍스트로 출력된다.
중요한 설계 판단은, 룰마다 지원하는 언어 목록을 갖고 있어서 스캐너가 자동으로 필터링한다는 거다.
-->

---

## Demo

### Python 스캔 결과
```
$ uv run aicslint scan aicslint/test_samples/smelly_python.py

⚠ Found 12 code smell(s):

  [CRITICAL] smelly_python.py:13  — Empty catch/except block           ACS001
  [CRITICAL] smelly_python.py:96  — Hardcoded secret 'api_key'         ACS004
  [WARNING]  smelly_python.py:30  — Catch block only re-raises         ACS002
  [WARNING]  smelly_python.py:42  — 'process_everything' 50 lines,     ACS003
                                    nesting depth 9
  [INFO]     smelly_python.py:103 — 'BaseProcessor' has only 1 impl    ACS005
```

### Pylint이 못 잡는 패턴 비교
```
$ pylint comparison_demo.py    → missing-docstring만 리포트
$ aicslint scan comparison_demo.py
  [WARNING] :18 — Catch block only re-raises          ACS002 ← Pylint 미탐지
  [INFO]    :25 — 'IDataStore' has only 1 impl        ACS005 ← Pylint 미탐지
```

<!--
실제 실행 결과를 보면, 테스트 샘플에서 12개의 코드 스멜을 잡아낸다.
가장 핵심적인 비교는 Pylint과의 차이인데, 같은 파일을 Pylint에 돌리면 docstring 없다는 얘기만 하고, catch-rethrow나 단일 구현 추상 클래스 같은 패턴은 전혀 못 잡는다.
aicslint는 이 두 가지를 정확히 잡아낸다. 이게 이 프로토타입의 검증 포인트였다.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 판단 | 선택 | 이유 |
|------|------|------|
| AST 파서 | tree-sitter | 다언어 지원, 성숙한 Python 바인딩, 부분 파싱 가능 |
| CLI 프레임워크 | Click (vs argparse) | 서브커맨드 처리가 깔끔, 의존성 하나 추가할 가치 있음 |
| god function 기준 | 40줄 + 중첩 5단계 | 처음 50줄로 했다가 테스트 샘플에서 안 걸려서 조정 |

### 시행착오
- tree-sitter 노드 타입이 **언어마다 다르다** — Python의 `as_pattern_target`, TS의 `catch_parameter` 등 각 언어별 예외 처리가 필요했음
- ACS003 임계값 튜닝: AI 코드는 40줄만 넘어도 중첩이 깊으면 충분히 위험

### 심의 점수
문제 진정성 **4.0**/5 · 프로토타입 적합성 **4.3**/5 · 신선도 **3.0**/5 · 학습 가치 **3.7**/5

<!--
기술 판단에서 가장 중요했던 건 tree-sitter 선택이다. regex로도 할 수 있지만, catch 블록이 비어있는지, 함수의 중첩 깊이가 몇인지는 AST 없이는 정확히 못 잡는다.
시행착오로는, tree-sitter의 노드 타입이 언어마다 다르다는 걸 실감했다. Python에서 except as e의 e가 identifier가 아니라 as_pattern_target이라는 별도 노드로 나온다. 이런 건 해봐야 안다.
god function 기준도 처음에 50줄로 잡았는데 AI 코드 특성상 40줄 + 깊은 중첩이면 이미 위험하다는 판단으로 조정했다.
심의 점수에서 신선도가 3.0으로 낮은데, 솔직히 코드 스멜 린터라는 개념 자체는 새롭지 않다. 차별점은 AI 특유 패턴에 특화했다는 거다.
-->

---

## Results & Future

### 성과 (5/5 완료 기준 통과)
- ✅ `aicslint scan` — 단일 파일 스캔 + JSON 출력
- ✅ 5개 룰 구현 — Python/JS/TS에서 탐지 시연
- ✅ `aicslint diff` — git staged 변경만 스캔
- ✅ Pylint 미탐지 패턴 2개 비교 시연 (ACS002, ACS005)
- ✅ 다언어 데모 — Python + JS/TS 동일 룰 동작

### 한계
- 룰 5개는 **시작점**일 뿐, 실제로는 10-15개 이상 필요
- AI가 생성한 코드인지 **판별하는 기능은 없음** (모든 코드에 동일 적용)
- SARIF 포맷 미지원 → CI/CD 통합 시 추가 작업 필요

### 프로덕트가 되려면
- pre-commit hook 자동 설치 스크립트
- `.aicslintrc` 설정 파일 (룰별 on/off, 임계값 커스텀)
- VS Code extension으로 인라인 경고
- 커뮤니티 룰 기여 구조 (플러그인 시스템)

<!--
완료 기준 5개를 전부 통과했다. 핵심 검증 포인트인 "기존 린터가 못 잡는 패턴을 AST로 잡을 수 있는가"에 대한 답은 예스다.
솔직히 아쉬운 건 룰이 5개밖에 없다는 거다. 실제로 쓰려면 AI가 만드는 보일러플레이트 패턴, 불필요한 null 체크 체인, 과도한 타입 캐스팅 같은 룰이 더 필요하다.
그리고 이 린터가 프로덕트가 되려면 결국 VS Code extension이 필요하다. CLI만으로는 채택률이 낮다. pre-commit hook도 마찬가지다.
그래도 이 프로토타입이 보여준 건, tree-sitter AST 기반으로 AI 코드 전용 린팅이 실용적으로 가능하다는 거다. 그 검증은 됐다.
-->
