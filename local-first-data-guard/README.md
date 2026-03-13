# Local-First Data Guard

> 브라우저 스토리지 내구성 자동 탐지 + IndexedDB ↔ OPFS 크로스 스토리지 자동 복구 라이브러리

## 실행 방법

```bash
# 의존성 설치
npm install

# TypeScript → ESM 번들 빌드
npm run build

# 데모 서버 실행
python3 -m http.server 8765

# 브라우저에서 http://localhost:8765 접속
```

## 테스트

```bash
# 핵심 로직 테스트 (21개)
node test-core.mjs

# Spec 완료 기준 검증 (4개)
node test-criteria.mjs
```

## 구조

```
local-first-data-guard/
├── src/
│   ├── detect.ts       # 브라우저 환경 탐지 엔진 (detectDurability)
│   ├── replicate.ts    # 크로스 스토리지 복제 (DataGuardReplicator)
│   └── index.ts        # Public API exports
├── dist/
│   └── data-guard.js   # esbuild 번들 (8.7kb ESM)
├── index.html          # 단일 HTML 데모 페이지
├── test-core.mjs       # 핵심 로직 테스트
├── test-criteria.mjs   # Spec 완료 기준 검증
├── BUILD_LOG.md        # 빌드 일지
├── STATUS.md           # 최종 상태
└── package.json
```

## 원본
prototype-pipeline spec: local-first-data-guard
