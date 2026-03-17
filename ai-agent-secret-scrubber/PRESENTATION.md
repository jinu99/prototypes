---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# AI Agent Secret Scrubber

> AI 에이전트 출력 스트림에서 시크릿을 실시간 탐지·마스킹하는 쉘 래퍼

**카테고리**: AI Agent Security / Developer Tooling
**스택**: Python, uv, subprocess + selectors, Shannon entropy
**날짜**: 2026-03-15

<!--
이 프로토타입은 AI 에이전트가 작업 중에 시크릿을 터미널에 그대로 뱉는 문제를 다룬다.
결국 에이전트의 출력 스트림을 가로채서 시크릿을 마스킹하는 쉘 래퍼를 만든 거다.
Python 표준 라이브러리만으로 대부분 구현했고, 외부 의존성 없이 동작한다.
-->

---

## Background

AI 코딩 에이전트가 일상 도구가 되면서, 에이전트에게 작업을 시키려면 API 키나 토큰 같은 시크릿을 공유해야 하는 상황이 늘고 있다.

문제는 에이전트가 이 값들을 출력에 그대로 노출한다는 거다.

- 채팅 히스토리에 `.env` 내용이 평문으로 남음
- 에이전트가 디버깅하면서 환경변수를 출력하면 시크릿이 터미널 로그에 기록됨
- 기존 DLP 솔루션(Nightfall 등)은 엔터프라이즈 유료 SaaS — 개인 개발자에겐 과함
- detect-secrets(Yelp)는 **커밋 시점** 스캔용이라 **실시간 스트림**에는 적용 안 됨

<!--
AI 코딩 에이전트가 보편화되면서 새로운 종류의 시크릿 유출 경로가 생겼다.
기존에는 git commit에 시크릿이 들어가는 게 문제였는데, 이제는 에이전트의 stdout에 시크릿이 찍히는 게 문제다.
커밋 단계 스캔으로는 이걸 못 잡는다. 출력 스트림 자체를 실시간으로 필터링해야 한다.
기존 DLP 도구는 엔터프라이즈 대상이라 개인 개발자가 쓰기에는 과하고, 오픈소스 경량 도구는 아직 없다.
-->

---

## Pain Point

커뮤니티에서 실제로 반복 보고되는 고통들:

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | HN | ★★★ | AI 에이전트와 API 키·토큰을 공유할 때 **채팅 히스토리에 시크릿이 평문 노출** |
| 2 | HN | ★★★ | GPT-4o가 프롬프트에 없는 **내부 세션 토큰 구조를 의미적으로 누출** |
| 3 | HN | ★★★ | AI 코딩 에이전트가 생성한 코드가 **학습 데이터로 사용되는지 확인 불가** |
| 4 | Reddit | ★★★ | AI 에이전트가 **DB와 .env 파일을 삭제·손상**시키는데 자동 백업 없음 |

공통점: 에이전트에게 권한을 주는 순간, 시크릿의 통제권을 잃는다.

<!--
커뮤니티에서 계속 나오는 얘기가 있다. AI 에이전트가 편한데, 시크릿 관리가 안 된다는 거다.
에이전트한테 작업을 시키려면 환경변수 접근을 줘야 하는데, 그 순간 시크릿이 채팅 로그에 남는다.
심지어 GPT-4o가 프롬프트에 넣지도 않은 세션 토큰을 추론해서 출력한 사례도 보고됐다.
결국 이건 에이전트에게 권한을 위임하는 순간 시크릿의 통제권을 잃는 구조적 문제다.
-->

---

## Solution

**한 줄 요약**: 에이전트의 명령을 subprocess로 감싸고, 출력을 3단계 파이프라인으로 필터링

기존 접근과의 차이:

| 기존 | 이 프로토타입 |
|------|-------------|
| **커밋 시점** 스캔 (pre-commit hook) | **실시간 출력 스트림** 스크러빙 |
| 정적 regex 매칭만 | registry → regex → **entropy** 3단계 탐지 |
| 엔터프라이즈 SaaS | 로컬 CLI, 외부 의존성 0 |
| 에이전트 동작 수정 필요 | 쉘 래퍼로 **에이전트 무수정** 적용 |

검증 질문: "에이전트 동작을 방해하지 않으면서 실시간 마스킹이 가능한가?" → **가능하다**

<!--
접근법은 꽤 단순하다. 에이전트 명령을 subprocess로 감싸서 출력 스트림을 가로채는 거다.
기존 도구들은 커밋 시점에 스캔하거나, 엔터프라이즈 SaaS 형태라 개인 개발자가 쓰기 어렵다.
이 프로토타입은 에이전트를 수정할 필요 없이, 쉘 래퍼로 감싸기만 하면 된다.
핵심 질문은 마스킹이 에이전트의 exit code나 출력 구조를 망가뜨리지 않느냐였는데, 결론은 가능하다.
-->

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI (main.py)                            │
│                  scan │ wrap │ demo command routing               │
└───────┬─────────────────┬───────────────────────────────────────┘
        │                 │
        ▼                 ▼
┌───────────────┐   ┌──────────────────────────────────────────┐
│  SecretRegistry│   │          Scrubber (scrubber.py)          │
│ (registry.py) │   │                                          │
│               │   │  subprocess.Popen ─▶ selectors-based     │
│ .env parsing  │   │  real-time stdout/stderr stream intercept │
│ credentials   │   │                                          │
│  .json parsing │   │  ┌─ line-by-line processing ─────────┐   │
│               │   │  │         SecretDetector            │   │
│  ┌──────────┐ │   │  │        (detector.py)              │   │
│  │ key=value│──────▶ │                                   │   │
│  │ collection│ │   │  │  1️⃣ Registry match (exact match)  │   │
│  └──────────┘ │   │  │  2️⃣ Pattern match (regex)        │   │
└───────────────┘   │  │  3️⃣ Entropy detection (Shannon)  │   │
                    │  │                                   │   │
                    │  │  detected → "***" masking         │   │
                    │  └───────────────────────────────────┘   │
                    └─────────┬──────────────────┬─────────────┘
                              │                  │
                              ▼                  ▼
                    ┌──────────────┐   ┌──────────────────┐
                    │   Masked     │   │  .scrubber_log   │
                    │  stdout/stderr│   │   .json          │
                    │ (real-time)  │   │ (detection log)  │
                    └──────────────┘   └──────────────────┘
```

<!--
구조는 크게 세 부분이다. SecretRegistry가 .env에서 시크릿 값을 수집하고, Scrubber가 subprocess로 명령을 실행하면서 selectors로 stdout과 stderr를 실시간 감시한다.
각 라인이 SecretDetector의 3단계 파이프라인을 통과하는데, 먼저 레지스트리에 등록된 값과 정확히 매칭하고, 그 다음 regex 패턴으로 잡고, 마지막으로 Shannon entropy로 미지의 고엔트로피 문자열을 탐지한다.
selectors 기반이라 stdout과 stderr가 실시간으로 인터리빙 처리된다. 한쪽이 끝나야 다른 쪽을 처리하는 게 아니다.
-->

---

## Demo

**`uv run main.py demo` 실행 결과:**

```
Secret Registry: 5 secrets loaded
  - DATABASE_URL: ********
  - API_KEY: ********
  - AWS_SECRET_ACCESS_KEY: ********
  - STRIPE_SECRET_KEY: ********
  - SLACK_TOKEN: ********
```

**`cat .env` 출력이 실시간 마스킹됨:**

```
DATABASE_URL=***
API_KEY=***
AWS_SECRET_ACCESS_KEY=***
STRIPE_SECRET_KEY=***
SLACK_TOKEN=***
HARMLESS_VAR=hello       ← 짧은 값은 시크릿으로 간주하지 않음
SHORT=abc                ← 8자 미만은 무시
```

**탐지 통계:** `registry=5, pattern=1, entropy=0`
— `pattern=1`은 DATABASE_URL 안에 임베디드된 비밀번호가 regex로 추가 탐지된 것

<!--
데모를 보면, .env에서 5개의 시크릿을 자동 수집하고, cat .env를 래핑 실행하면 모든 시크릿 값이 별표로 마스킹된다.
재밌는 건 HARMLESS_VAR=hello나 SHORT=abc 같은 짧은 값은 시크릿으로 간주하지 않는다는 거다. 8자 미만은 무시한다.
그리고 pattern=1이 찍힌 건 DATABASE_URL의 connection string 안에 임베디드된 비밀번호를 regex로 추가 탐지한 거다. 레지스트리 매칭과 패턴 매칭이 상호보완적으로 동작하는 셈이다.
-->

---

## Key Decisions & Lessons

### 1. 외부 의존성 제로
`detect-secrets` 라이브러리를 쓸 수 있었지만, 표준 라이브러리(`subprocess`, `re`, `math`, `selectors`)만으로 충분했다. 프로토타입에서 외부 의존성은 검증 속도를 늦춘다.

### 2. selectors 기반 실시간 인터리빙
처음에는 stdout → stderr 순차 처리였는데, 실제 에이전트 출력은 두 스트림이 섞여 나온다. `selectors`로 바꾸니 실시간 인터리빙이 해결됐다.

### 3. False positive와의 싸움
- `TOKEN_PATTERN`에 `=`이 포함되어 `KEY=value`가 하나의 토큰으로 잡힘
- 환경변수 키 이름(`HARMLESS_VAR`)이 entropy 탐지에 걸림
- `ALL_CAPS_UNDERSCORE` 패턴 필터를 추가해서 해결

**심의 점수**: 문제 진정성 4.0 | 프로토타입 적합성 3.3 | 학습 가치 3.7
**반대 의견**: "쉘 래퍼 수준의 stdout 필터링으로는 tool call 기반 에이전트에서 핵심 가치를 증명하기 어렵다" (준혁)

<!--
기술 판단에서 인상적이었던 건 세 가지다.
첫째, detect-secrets를 쓸까 고민했는데, 표준 라이브러리만으로 충분했다. entropy 계산은 math.log2면 되고, 패턴 매칭은 re로 된다. 프로토타입에서 외부 의존성은 오히려 걸림돌이다.
둘째, selectors 기반 처리. 처음에 stdout 다 읽고 stderr 읽는 순차 방식이었는데, 실제 에이전트 출력은 두 스트림이 섞여 나온다. selectors로 바꾸니 실시간 인터리빙이 해결됐다.
셋째, false positive. 환경변수 키 이름이 고엔트로피로 잡히는 문제가 있었다. ALL_CAPS 패턴 필터로 해결했는데, 결국 시크릿 탐지는 정밀도와 재현율의 균형 문제다.
심의에서 준혁이 "쉘 래퍼로는 tool call 기반 에이전트에서 가치를 증명하기 어렵다"고 반대 의견을 냈는데, 이건 맞는 지적이고 한계점이다.
-->

---

## Results & Future

### 성과 (5/5 완료 기준 통과)
- ✅ `.env`에서 시크릿 자동 수집 → 레지스트리 구축
- ✅ 쉘 래퍼로 stdout/stderr 마스킹 (실시간)
- ✅ entropy 기반 미등록 고엔트로피 문자열 탐지
- ✅ `cat .env` 래핑 데모 동작
- ✅ exit code, 출력 구조 보존 (0, 1, 2, 42, 127 모두 검증)

### 한계
- **stdout 기반 래퍼**이므로 tool call(MCP, function calling) 채널은 커버 못 함
- 바이너리 출력에는 적용 안 됨
- entropy 기반 탐지는 false positive 가능성이 있음

### 프로덕트가 되려면
- MCP 미들웨어로 확장 → tool call 입출력도 스크러빙
- 보호 파일 목록 관리 (`.env`, `*.sqlite` 등 쓰기/삭제 차단)
- 에이전트별 플러그인 시스템 (Claude Code, Cursor, Copilot 등)
- 세션 종료 시 로그/히스토리 스크러빙

<!--
완료 기준 5개를 모두 통과했다. exit code 보존도 42나 127 같은 비정상 코드까지 테스트했다.
솔직히 한계는 명확하다. 이건 stdout 기반 래퍼라서 tool call 채널은 못 잡는다. MCP로 통신하는 에이전트라면 이 방식으로는 부족하다. 준혁의 지적이 맞는 부분이다.
프로덕트가 되려면 MCP 미들웨어로 확장해서 tool call 입출력까지 커버해야 한다. 그리고 파일 시스템 보호 기능도 붙여야 한다.
그래도 이 프로토타입이 증명한 건 하나다. 에이전트의 출력 스트림을 실시간으로 필터링하는 게 에이전트 동작을 망가뜨리지 않으면서 가능하다는 것. 그 기본 전제가 확인된 셈이다.
-->
