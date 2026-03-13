# OpenAPI Form Tester

> OpenAPI 스펙에서 자동 생성된 폼으로 API를 테스트하고 응답-스펙 드리프트를 즉시 시각화하는 로컬 웹 도구

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
