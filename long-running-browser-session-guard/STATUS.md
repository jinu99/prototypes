# STATUS: SUCCESS

## 요약
5KB 미만(4.3KB gzipped)의 드롭인 JS 라이브러리로 브라우저 세션의 메모리 누수를 감지하고, 상태를 보존한 채 자동 복구하는 프로토타입. 데모 페이지에서 의도적 누수 → 감지 → 복구 플로우를 시연할 수 있다.

## 완료 기준 결과
- [x] 라이브러리가 `<script>` 한 줄로 삽입되어 메모리 사용량, DOM 노드 수를 주기적으로 수집한다
- [x] 메모리 증가 추세를 선형 회귀로 분석하여 OOM 예상 시점을 계산하고 콘솔/오버레이에 표시한다
- [x] 임계치 도달 시 sessionStorage에 지정된 상태를 스냅샷하고 소프트 리로드 후 복원한다
- [x] 데모 페이지에서 의도적 메모리 누수 → 감지 → 경고 → 자동 복구 흐름을 시연할 수 있다
- [x] 라이브러리 크기가 5KB gzipped 이하이다 (4,406 bytes)

## 실행 방법
README.md 참조 또는:
```bash
npx serve .
# 브라우저에서 http://localhost:3000 접속 (Chrome/Edge 권장)
```

## 소요 정보
- 생성일: 2026-03-29
- 원본 spec: long-running-browser-session-guard.md
- 자동 생성: prototype-pipeline spawn
