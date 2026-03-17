---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Webhook Chaos Tester

**웹훅 엔드포인트에 카오스 시나리오를 쏘는 CLI 도구**

- **카테고리**: Developer Tools / Testing
- **스택**: Python, httpx, Click, PyYAML
- **날짜**: 2026-03-15

<!--
웹훅 기반 연동을 만들어본 분이라면 공감하실 텐데, 대부분 "정상 전송"만 테스트하고 배포한다. 그런데 프로덕션에선 같은 웹훅이 두 번 오고, 순서가 뒤바뀌고, 3초 뒤에 재전송이 온다. 이 프로토타입은 그런 카오스 상황을 의도적으로 만들어서 핸들러가 버티는지 확인하는 도구다.
-->

---

## Background

웹훅은 현대 SaaS 연동의 사실상 표준이다.
Stripe, GitHub, Slack — 다 웹훅으로 이벤트를 전달한다.

**문제는 "행복한 경로"만 테스트한다는 것.**

- 개발자는 `POST /webhook` → `200 OK` 흐름만 확인하고 배포
- 실제 환경: 중복 전송, 네트워크 지연 후 재전송, 순서 역전이 빈번
- 기존 카오스 도구(LitmusChaos, Chaos Mesh)는 Kubernetes 인프라 대상
- webhook-tester 류는 수신/검사만 하고 **장애 시뮬레이션은 안 함**

→ 웹훅 레벨의 카오스 테스트 도구는 사실상 없다.

<!--
웹훅이라는 게 보내는 쪽은 Stripe나 GitHub처럼 잘 만든 서비스인데, 받는 쪽은 각 팀이 직접 구현한다. 그러다 보니 "잘 오면 잘 처리된다"까지만 테스트하고 끝나는 경우가 대부분이다. 카오스 엔지니어링이라는 개념 자체는 익숙한데, 그게 쿠버네티스 파드를 죽이는 수준이지 웹훅 페이로드 레벨에서 장애를 시뮬레이션하는 도구는 딱히 없다. 결국 "같은 결제 이벤트가 두 번 왔을 때 두 번 처리되는" 버그는 프로덕션에서 발견된다.
-->

---

## Pain Point

커뮤니티에서 반복적으로 나오는 신호들:

| # | 출처 | Signal | 내용 |
|---|------|:------:|------|
| 1 | r/SideProject | ★★★ | 웹훅의 실제 환경 문제(중복, 지연, 순서 뒤바뀜)를 프로덕션 전에 테스트할 도구가 없다 |
| 2 | r/webdev | ★★★ | 업타임 모니터가 HTTP 200만 확인하고 실제 처리 상태를 검사하지 않아 3일간 깨진 사이트를 놓쳤다 |
| 3 | HN | ★★★ | 크론잡/모니터링 도구가 비싸거나 무료 티어가 심하게 제한적이다 |

공통점: **"정상 응답 = 정상 처리"라는 가정이 깨지는 순간을 잡을 방법이 없다.**

<!--
세 군데서 비슷한 얘기가 나온다. 첫 번째는 웹훅 장애 시뮬레이션 도구 자체가 없다는 것, 두 번째는 모니터링이 200만 보고 끝난다는 것, 세 번째는 그나마 있는 도구도 비싸다는 것이다. 결국 같은 문제를 다른 각도에서 겪고 있는 건데, 핵심은 "200이 돌아왔으니 괜찮겠지"라는 가정이 프로덕션에서 깨진다는 거다. 사람으로 치면 건강검진에서 혈압만 재고 "건강합니다" 하는 것과 마찬가지다.
-->

---

## Solution

> **웹훅 핸들러에 의도적으로 카오스를 주입하고, 멱등성과 에러 처리를 자동 검증하는 CLI 도구**

### 기존 도구와의 차이

| 기존 | Webhook Chaos Tester |
|------|---------------------|
| webhook-tester: 수신만 | 장애 시나리오를 **능동적으로 전송** |
| LitmusChaos: 인프라 레벨 | **HTTP 페이로드 레벨** 카오스 |
| 수동 curl 테스트 | YAML 기반 **시나리오 자동화** + 판정 |

### 검증 질문
"중복, 지연, 순서 뒤바뀜 시나리오를 자동 실행하여
핸들러의 멱등성과 에러 처리 누락을 **사전에** 발견할 수 있는가?"

<!--
접근법은 단순하다. 웹훅 핸들러에 일부러 나쁜 상황을 만들어서 보내고, 응답 코드로 판정하는 거다. 중복 전송해서 다 200이면 멱등하게 처리한 거고, 에코 서버를 reject-duplicates 모드로 바꾸면 두 번째부터 409가 돌아온다. 기존 도구들이 수신 검사에 머물거나 인프라 레벨에서 움직이는 것과 달리, 이건 HTTP 페이로드 수준에서 카오스를 만든다. curl로 수동 테스트하는 걸 YAML 시나리오로 자동화한 셈이다.
-->

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLI (cli.py)                           │
│           click-based commands: run / demo / echo               │
└──────┬──────────────────┬───────────────────────┬───────────────┘
       │                  │                       │
       ▼                  ▼                       ▼
┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐
│ Loader       │  │ Engine        │  │ Echo Server            │
│ (loader.py)  │  │ (engine.py)   │  │ (echo_server.py)       │
│              │  │               │  │                        │
│ YAML parsing │  │ Run scenarios │  │ Test HTTP server       │
│ → Scenario[] │  │ Send via httpx│  │ Receive POST /webhook  │
└──────────────┘  └───────────────┘  │ --reject-duplicates    │
                                     │  : 409 reject dups     │
                                     └────────────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ Report        │
                  │ (report.py)   │
                  │ Markdown/JSON │
                  └───────────────┘
```

**Loader** → Parse YAML scenarios | **Engine** → Execute chaos patterns + judge results | **Echo** → Local test target | **Report** → Output results

<!--
구조는 꽤 직관적이다. CLI가 진입점이고, Loader가 YAML 시나리오를 파싱하고, Engine이 실제로 HTTP 요청을 카오스 패턴에 맞게 보내고, Report가 결과를 정리한다. Echo Server는 테스트 타겟이 없을 때 로컬에서 띄우는 가짜 서버인데, reject-duplicates 모드를 지원해서 "멱등성을 구현한 서버"와 "안 한 서버"를 둘 다 시뮬레이션할 수 있다. 전체 의존성이 httpx, pyyaml, click 세 개뿐이고, 각 모듈이 300줄 미만이다.
-->

---

## Demo

```bash
$ uv run webhook-chaos demo

Starting echo server on port 9876...
Target: http://127.0.0.1:9876/webhook
Scenarios: 3

[1/3] duplicate-delivery (duplicate)...
  PASS: All 3 duplicate requests returned 2xx
[2/3] delayed-delivery (delay)...
  PASS: Response 200 after 2.0s delay
[3/3] out-of-order (reorder)...
  PASS: All reversed-order requests returned 2xx

Results: 3/3 passed
```

`demo` 한 줄로 Echo Server 자동 시작 → 기본 시나리오 3종 실행 → 리포트 출력.
`--format json --output report.json`으로 CI 통합도 가능.

<!--
demo 명령어 하나면 된다. 에코 서버를 자동으로 띄우고, 기본 시나리오 세 개를 돌리고, 결과를 바로 보여준다. 이게 기본 모드에서는 다 PASS가 나오는데, 에코 서버를 reject-duplicates 모드로 바꾸면 duplicate 시나리오에서 FAIL이 뜬다. 그게 핵심이다. 멱등성 처리를 안 한 서버에서는 중복 전송 시나리오가 정확히 결함을 잡아낸다. JSON 출력도 지원하니까 CI 파이프라인에 끼워넣는 것도 가능하다.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 판단 | 이유 |
|------|------|
| Python + httpx | HTTP 타이밍 제어가 간결하고, YAML/CLI 구현이 최소 의존성으로 가능 |
| http.server 기반 Echo | 외부 의존성 없이 stdlib만으로 테스트 서버 구현. 스레드로 백그라운드 실행 |
| 응답 코드 기반 판정 | DB 상태 검증은 scope 밖. "200이면 OK"라는 단순한 기준이 오히려 범용성을 높임 |

### 심의 점수
- **문제 진정성**: 4.0/5 — 실제 커뮤니티 pain point 기반
- **프로토타입 적합성**: 4.3/5 — 하루 안에 핵심 검증 가능
- **반대 의견**: "기술적 도전이 부족. HTTP 타이밍 제어 + 응답 비교 수준" (준혁)
  → 솔직히 맞는 말인데, 도전이 아니라 실용성이 핵심인 프로토타입이다.

<!--
스택 선택에서 Go와 Python 사이에서 고민했는데, 결국 httpx의 간결함이 이겼다. 에코 서버도 Flask 같은 걸 쓸까 했지만, stdlib의 http.server로 충분했다. 심의에서 준혁이 "기술적 도전이 부족하다"고 했는데, 솔직히 맞다. 이건 어려운 기술을 쓰는 게 아니라 아무도 안 만든 조합을 만드는 프로토타입이다. 시행착오가 있었다면 hatchling 패키징 설정 쪽인데, 패키지 디렉토리 이름이 안 맞아서 entry point가 설치 안 된 문제가 있었다. 결국 wheel packages를 명시적으로 잡아서 해결했다.
-->

---

## Results & Future

### 성과
- [x] 기본 시나리오 3종 (중복, 지연, 역순) 실행 — **완료**
- [x] YAML 커스텀 시나리오 정의 — **완료**
- [x] PASS/FAIL 판정 + Markdown/JSON 리포트 — **완료**
- [x] Echo Server 포함 자체 데모 — **완료**
- [x] README + 시나리오 작성 가이드 — **완료**

→ 완료 기준 **5/5 전부 통과**. STATUS: SUCCESS.

### 한계점
- 응답 코드만으로 판정 — DB 상태까지는 확인 못 함
- 서명 검증(HMAC) 시나리오 미구현
- 동시성 카오스(concurrent burst) 미지원

### 프로덕트가 되려면
- Stripe/GitHub/Slack 등 주요 서비스별 **페이로드 템플릿**
- 서명 생성 + 잘못된 서명 시나리오
- CI/CD 플러그인 (GitHub Actions, GitLab CI)
- 웹 대시보드로 결과 시각화

<!--
완료 기준 다섯 개를 전부 통과했다. 솔직히 아쉬운 건 응답 코드만 보고 판정한다는 점이다. 실제로는 200을 돌려놓고 내부에서 이중 처리하는 경우도 있으니까. 그리고 서명 검증 시나리오를 넣으면 좀 더 현실적인 테스트가 될 텐데 이번 범위에서는 뺐다. 프로덕트로 가려면 Stripe 같은 서비스별 페이로드 템플릿이 필요하고, GitHub Actions에서 바로 돌릴 수 있는 플러그인이 있으면 좋겠다. 결국 이 도구의 가치는 "프로덕션에서 터지기 전에 한 번 돌려보는 것"인데, 그 경험이 가능하다는 걸 이번 프로토타입으로 확인했다.
-->
