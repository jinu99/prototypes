---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# OpenAPI Form Tester

**OpenAPI 스펙에서 자동 생성된 폼으로 API를 테스트하고, 응답-스펙 드리프트를 즉시 시각화하는 로컬 웹 도구**

- **카테고리**: API 개발 도구
- **스택**: Node.js · Express · swagger-parser · Vanilla JS
- **날짜**: 2026-03-03

<!--
API 개발할 때 Swagger UI에서 JSON 직접 쓰거나, Postman에서 요청 만들어서 보내는 과정이 있다. 그 과정에서 두 가지 문제가 반복된다. 하나는 JSON 수동 편집에서 오는 실수, 다른 하나는 응답이 스펙과 실제로 맞는지 확인할 방법이 없다는 것이다. 이 프로토타입은 그 두 문제를 하나의 워크플로로 합쳐본 실험이다.
-->

---

## Background

API 생태계에서 **스펙과 코드의 거리**가 점점 벌어지고 있다.

- OpenAPI 스펙으로 시작해도, 비즈니스 로직이 쌓이면 스펙은 방치된다
- Swagger UI의 "Try it out"은 여전히 **raw JSON 텍스트 에디터** 방식
- 스펙 검증 도구(Dredd, Optic)와 요청 도구(Postman, Bruno)가 **분리**되어 있다
- Postman이 $19/사용자로 올리면서 소규모 팀의 대안 탐색이 활발해졌다

결국 "요청을 보내는 행위"와 "스펙을 검증하는 행위"가 따로 놀고 있다는 게 문제다.

<!--
API를 만들 때 보통 스펙을 먼저 쓴다. OpenAPI YAML 같은 걸로. 근데 코드가 쌓이면 스펙은 점점 안 맞게 된다. 이게 자연스러운 건데, 문제는 그 괴리를 발견하는 시점이 너무 늦다는 거다. 프론트엔드가 "이 필드 왜 없어요?" 하고 물어볼 때 알게 된다. 기존 도구들은 요청 보내는 것과 스펙 검증하는 것을 완전히 별개로 취급한다. 마치 의사가 진찰은 여기서 하고, 검사 결과는 다른 병원 가서 보라는 것과 마찬가지다.
-->

---

## Pain Point

커뮤니티에서 반복적으로 나오는 세 가지 마찰:

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/SideProject | ★★★ | Swagger UI에서 JSON 요청 본문을 수동 편집할 때 **구문 오류가 빈번**하다 |
| 2 | r/webdev | ★★★ | Postman 팀 요금이 **$19/사용자**로 올라 소규모 팀에 부담 |
| 3 | Hacker News | ★★★ | API 스펙 변경 시 코드와의 일관성을 **자동으로 강제할 방법이 없다** |

공통 패턴: **스키마 정보가 이미 있는데, 그걸 활용하지 못하고 있다.**

<!--
레딧이나 해커뉴스에서 이 주제로 글이 계속 올라온다. 첫 번째는 Swagger UI에서 중첩 객체 JSON을 손으로 쓸 때 쉼표 하나 빠져서 에러 나는 얘기. 두 번째는 Postman 가격 인상 이후 대안을 찾는 흐름. 세 번째가 핵심인데, 스펙이 변경돼도 코드가 따라가는지 확인할 방법이 없다는 거다. 결국 공통점은 하나다. OpenAPI 스키마에 타입 정보가 다 있는데, 그걸 제대로 활용하는 도구가 없다.
-->

---

## Solution

> **"요청을 보내는 순간, 스펙 준수 여부를 바로 확인한다"**

핵심 아이디어: **스키마 → 폼 생성**과 **응답 → 스펙 비교**를 하나의 워크플로로 통합

| 기존 방식 | 이 도구 |
|-----------|---------|
| Swagger UI에서 JSON 수동 편집 | 스키마에서 타입별 폼 자동 생성 |
| 응답 확인 → 별도 도구로 스펙 검증 | 응답 수신 즉시 드리프트 테이블 표시 |
| Postman + Dredd 조합 필요 | `node cli.js spec.yaml` 한 줄로 끝 |

<!--
접근법은 단순하다. OpenAPI 스펙을 읽어서 폼을 자동으로 만들고, 요청을 보내고, 응답이 오면 스펙과 바로 비교한다. 기존에는 Swagger UI로 요청 보내고, Dredd나 Optic으로 따로 검증하는 두 단계 과정이었다. 이걸 한 화면에서 끝나게 만든 거다. JSON을 직접 쓸 필요도 없다. 스키마에 string이라고 되어 있으면 텍스트 필드, enum이면 드롭다운, 중첩 객체면 폼 그룹이 자동으로 나온다.
-->

---

## Architecture

```
OpenAPI YAML ──▶ Parser (swagger-parser, $ref 역참조) ──▶ /api/spec ──▶ 브라우저 UI
사용자 폼 입력 ──▶ /api/send (Express 프록시) ──▶ 대상 API ──▶ 응답 수신
응답 JSON ──▶ /api/validate ──▶ Validator (재귀적 스키마 비교) ──▶ 드리프트 테이블
```

| 컴포넌트 | 역할 |
|----------|------|
| **cli.js** | spec 경로 파싱 → 서버 기동 → 브라우저 자동 오픈 |
| **parser.js** | swagger-parser로 OpenAPI 3.x $ref 해석 및 엔드포인트 추출 |
| **validator.js** | 응답 vs 스펙 재귀 비교 — missing / type_mismatch / undocumented 감지 |
| **form-builder.js** | JSON Schema → 동적 폼 렌더링 (중첩 object, array, enum 지원) |
| **app.js** | 사이드바 · 요청 전송 · 응답/드리프트 표시 메인 로직 |

<!--
구조는 꽤 단순하다. CLI가 진입점이고, Express 서버가 세 가지 API를 제공한다. 스펙 조회, 요청 프록시, 드리프트 검증. 프론트엔드는 vanilla JS로 세 모듈로 나뉜다. 핵심은 validator.js인데, 재귀적으로 스키마를 순회하면서 실제 응답과 비교한다. 필드가 빠졌는지, 타입이 다른지, 스펙에 없는 필드가 있는지. 이 세 가지를 잡아낸다.
-->

---

## Demo

**동적 폼 생성 → 요청 전송 → 드리프트 감지** 전체 흐름:

```
Server
  Base URL: [http://localhost:4567/mock        ]

Request Body
  name     * string  [Buddy                    ]
  status     string  [▼ available              ]

  [Send Request]  Done (200)
```

```
Spec Drift Analysis
  1 missing  1 undocumented

  ┌──────────────┬────────────┬──────────┬──────────┐
  │ Type         │ Path       │ Expected │ Actual   │
  ├──────────────┼────────────┼──────────┼──────────┤
  │ Missing      │ tag        │ string   │ —        │
  │ Undocumented │ createdAt  │ —        │ string   │
  └──────────────┴────────────┴──────────┴──────────┘
```

스펙에는 `tag` 필드가 있는데 응답에 없고, `createdAt`은 응답에 있는데 스펙에 없다. **이게 드리프트다.**

<!--
실제로 돌려보면 이렇다. petstore 샘플 스펙을 로드하면 왼쪽에 엔드포인트가 태그별로 나온다. POST /pets를 누르면 name, status 같은 필드가 폼으로 자동 생성된다. 값 넣고 Send 누르면 응답이 오는데, 그 아래에 드리프트 테이블이 바로 뜬다. 여기서 tag 필드는 스펙에는 있는데 실제 응답에는 없고, createdAt은 반대로 응답에만 있다. 이런 괴리를 요청 보내는 시점에 바로 확인할 수 있다는 게 핵심이다.
-->

---

## Key Decisions & Lessons

**1. Vanilla JS + innerHTML 제거**
- 보안 훅이 innerHTML을 차단 → 모든 DOM 생성을 `el()` 헬퍼 + textContent로 전환
- 결과적으로 XSS 안전한 코드가 됐다. 제약이 더 나은 설계를 만든 케이스

**2. integer vs number 구분**
- JS의 `typeof 1`은 "number"인데, OpenAPI는 integer/number를 구분한다
- `Number.isInteger()` 체크 + number 스키마가 integer도 허용하도록 처리

**3. Mock API 내장 전략**
- 별도 프로세스 대신 Express 라우트로 mock을 내장 → 의도적 드리프트 포함
- 설치 즉시 데모 가능. "돌려봐야 알 수 있는 도구"에서 이건 꽤 중요하다

**심의 점수**: 문제 진정성 3.7 · 프로토타입 적합성 4.3 · 학습 가치 4.0 · 만장일치 승인

<!--
기술 판단 중에 인상적이었던 게 세 가지 있다. 첫째, innerHTML 차단 때문에 DOM 생성 방식을 전부 바꿔야 했는데, 결과적으로 XSS 안전한 코드가 됐다. 제약이 있으니까 오히려 더 나은 방향으로 간 거다. 둘째, JavaScript와 OpenAPI의 타입 체계가 미묘하게 다르다. typeof 1이 number인데 OpenAPI에서는 integer다. 이런 경계 지점에서 버그가 나온다. 셋째, mock API를 별도 서버로 안 빼고 Express 안에 넣은 건 좋은 판단이었다. 프로토타입은 설치하고 바로 돌려볼 수 있어야 의미가 있다.
-->

---

## Results & Future

### 성과
- **5/5 완료 기준 전수 통과** (STATUS: SUCCESS)
- E2E 테스트 16개 항목 전수 통과
- app.js 474줄 → 3파일 분리 (dom-utils 37 + form-builder 136 + app 251)

### 한계
- path/query/header parameter 폼 미지원 (body만 가능)
- `oneOf`/`anyOf`/순환 참조 등 고급 JSON Schema 미처리
- 인증/OAuth 플로우 미지원
- 브라우저 UI 실물 검증은 시스템 제약으로 미완 (E2E + curl로 대체)

### 프로덕트가 되려면
- parameter 폼 확장 (path, query, header)
- 테스트 시나리오 저장/재실행 기능
- CI 파이프라인 연동 (드리프트 감지 → 빌드 실패)
- VS Code 확장 또는 `npx` 패키지 배포

<!--
결과적으로 5개 완료 기준을 다 통과했다. 솔직히 아쉬운 부분도 있다. body만 폼으로 만들 수 있고, path parameter나 query parameter는 아직 안 된다. oneOf 같은 복잡한 스키마도 미지원이다. 근데 프로토타입의 목적은 "통합 워크플로가 정말 가치가 있는가"를 확인하는 거였고, 그건 충분히 검증됐다고 본다. 이게 실제 프로덕트가 되려면 CI 파이프라인에 붙여서 드리프트 감지되면 빌드를 깨뜨리는 방향이 가장 현실적일 것 같다. 결국 스펙 준수를 강제하는 메커니즘이 필요한 거니까.
-->
