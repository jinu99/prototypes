# OpenAPI Form Tester

> OpenAPI 스펙에서 자동 생성된 폼으로 API를 테스트하고 응답-스펙 드리프트를 즉시 시각화하는 로컬 웹 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI (cli.js)                                                   │
│  OpenAPI spec 경로 + 포트 파싱 → 서버 기동 → 브라우저 자동 오픈  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Express Server (src/server.js)                     port:4567   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ GET /api/spec│  │POST /api/send│  │ POST /api/validate    │  │
│  │  스펙 조회   │  │  API 프록시  │  │  드리프트 검증        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬────────────┘  │
│         │                 │                      │              │
│         ▼                 │                      ▼              │
│  ┌─────────────┐          │           ┌────────────────────┐    │
│  │ Parser      │          │           │ Validator          │    │
│  │ (parser.js) │          │           │ (validator.js)     │    │
│  │             │          │           │                    │    │
│  │ swagger-    │          │           │ missing /          │    │
│  │ parser로    │          │           │ type_mismatch /    │    │
│  │ OpenAPI 3.x │          │           │ undocumented       │    │
│  │ 역참조·변환 │          │           │ 드리프트 감지      │    │
│  └─────────────┘          │           └────────────────────┘    │
│                           │                                     │
│  ┌────────────────────────┼───────────────────────────────────┐ │
│  │ Static Files (public/) │                                   │ │
│  │                        ▼                                   │ │
│  │  ┌──────────┐  ┌─────────────┐  ┌───────────────────────┐ │ │
│  │  │ app.js   │  │form-builder │  │ dom-utils.js          │ │ │
│  │  │          │  │    .js      │  │ 안전한 DOM 생성 헬퍼  │ │ │
│  │  │ 사이드바 │  │             │  └───────────────────────┘ │ │
│  │  │ 요청전송 │  │ JSON Schema │                            │ │
│  │  │ 응답표시 │  │ → 동적 폼   │                            │ │
│  │  │ 드리프트 │  │ (중첩 obj,  │                            │ │
│  │  │ 테이블   │  │  array 지원)│                            │ │
│  │  └──────────┘  └─────────────┘                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Mock API (/mock)  ─  sample/mock-routes.js                 │ │
│  │ petstore.yaml 샘플 스펙 + 의도적 드리프트 포함 Mock 응답  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

데이터 흐름:
  OpenAPI YAML ──▶ Parser (역참조) ──▶ /api/spec ──▶ 브라우저 UI
  사용자 폼 입력 ──▶ /api/send (프록시) ──▶ 대상 API ──▶ 응답 수신
  응답 JSON ──▶ /api/validate ──▶ Validator (스펙 비교) ──▶ 드리프트 테이블
```

## Demo

웹 UI 기반 도구로, 브라우저에서 다음과 같은 화면을 제공합니다.

**1. 서버 실행**

```bash
$ node cli.js

  OpenAPI Form Tester
  Spec: /home/user/openapi-form-tester/sample/petstore.yaml
  UI:   http://localhost:4567
```

**2. 엔드포인트 사이드바**

좌측에 OpenAPI 스펙의 엔드포인트가 tag별로 그룹화되어 표시됩니다.
각 항목은 HTTP method 컬러 배지(`GET` `POST` `PUT` `DELETE`)와 경로로 구성됩니다.

**3. 동적 폼으로 요청 전송**

엔드포인트를 선택하면 request body 스키마에 맞는 폼이 자동 생성됩니다.
string, number, boolean, enum, 중첩 object, array 등 모든 타입을 지원합니다.

```
Server
  Base URL: [http://localhost:4567/mock        ]

Request Body
  name     * string  [Buddy                    ]
  status     string  [▼ available              ]

  [Send Request]  Done (200)
```

**4. 응답 확인 및 드리프트 감지**

Send Request 후 응답 본문과 함께 스펙 대비 드리프트가 테이블로 표시됩니다.

```
Response
  200 OK

  {
    "id": 42,
    "name": "Buddy",
    "status": "available",
    "createdAt": "2024-01-01T00:00:00Z"
  }

Spec Drift Analysis
  1 missing  1 undocumented

  ┌──────────────┬────────────┬──────────┬──────────┐
  │ Type         │ Path       │ Expected │ Actual   │
  ├──────────────┼────────────┼──────────┼──────────┤
  │ Missing      │ tag        │ string   │ —        │
  │ Undocumented │ createdAt  │ —        │ string   │
  └──────────────┴────────────┴──────────┴──────────┘
```

드리프트 타입별 색상으로 구분됩니다:
- **Missing** (빨강): 스펙에 정의된 필드가 응답에 없음
- **Type Mismatch** (노랑): 필드의 실제 타입이 스펙과 불일치
- **Undocumented** (파랑): 응답에 존재하지만 스펙에 미정의된 필드

## 실행 방법

```bash
# 의존성 설치
npm install

# 내장 샘플 spec으로 실행 (port 4567)
node cli.js

# 직접 spec 지정
node cli.js ./my-api.yaml

# 포트 변경
node cli.js ./my-api.yaml 8080
```

브라우저가 자동으로 열립니다. `http://localhost:4567`에서 UI를 확인하세요.

## 구조

```
openapi-form-tester/
├── cli.js                  # CLI 진입점
├── src/
│   ├── server.js           # Express 서버 (정적 파일 + API 라우트)
│   ├── parser.js           # OpenAPI 3.x 파서 (swagger-parser)
│   └── validator.js        # 응답 vs 스펙 드리프트 검증기
├── public/
│   ├── index.html          # 메인 HTML
│   ├── style.css           # 다크 테마 스타일
│   ├── dom-utils.js        # 안전한 DOM 생성 유틸
│   ├── form-builder.js     # 스키마 기반 폼 생성기
│   └── app.js              # 메인 앱 로직
├── sample/
│   ├── petstore.yaml       # 샘플 OpenAPI spec (의도적 드리프트 포함)
│   └── mock-routes.js      # 내장 Mock API
├── test-e2e.js             # E2E 기능 테스트 (16개 항목)
├── BUILD_LOG.md            # 빌드 일지
└── STATUS.md               # 프로토타입 상태
```

## 주요 기능

- **엔드포인트 사이드바**: tags별 그룹핑, method 컬러 배지
- **동적 폼 생성**: string, number, integer, boolean, enum, object (중첩), array 지원
- **API 프록시**: 폼 데이터로 실제 API 호출
- **드리프트 감지**: 누락 필드(missing), 타입 불일치(type_mismatch), 미문서화 필드(undocumented)
- **diff UI**: 드리프트를 테이블 형태로 시각화, 타입별 색상 구분

## 원본
prototype-pipeline spec: openapi-form-tester
