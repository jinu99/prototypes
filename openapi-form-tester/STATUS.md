# STATUS: SUCCESS

## 요약
OpenAPI 3.x 스펙에서 동적 폼을 자동 생성하고, API 요청을 보낸 뒤 응답-스펙 드리프트를 시각화하는 로컬 웹 도구. 5개 완료 기준 전수 통과.

## 완료 기준 결과
- [x] `node cli.js spec.yaml` 실행 시 로컬 웹 UI가 열린다
- [x] OpenAPI 3.x spec에서 엔드포인트 목록을 파싱하여 사이드바에 표시한다
- [x] 선택한 엔드포인트의 request body 스키마에서 타입별 입력 폼을 자동 생성한다 (string, number, boolean, object, array)
- [x] 폼으로 구성한 요청을 실제 API에 전송하고 응답을 표시한다
- [x] 응답을 스펙과 비교하여 드리프트(누락 필드, 타입 불일치, 미문서화 필드)를 diff UI로 시각화한다

## 실행 방법
```bash
npm install
node cli.js                    # 내장 샘플 spec으로 실행
node cli.js ./my-api.yaml      # 직접 spec 지정
```

## 소요 정보
- 생성일: 2026-03-03
- 원본 spec: openapi-form-tester.md
- 자동 생성: prototype-pipeline spawn
