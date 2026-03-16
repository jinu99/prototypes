# Local-First Data Guard

> 브라우저 스토리지 내구성 자동 탐지 + IndexedDB ↔ OPFS 크로스 스토리지 자동 복구 라이브러리

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser Environment                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    index.ts (Public API)                  │   │
│  │         detectDurability() / DataGuardReplicator          │   │
│  └──────────┬──────────────────────────┬────────────────────┘   │
│             │                          │                        │
│             ▼                          ▼                        │
│  ┌─────────────────────┐   ┌───────────────────────────────┐   │
│  │   detect.ts          │   │   replicate.ts                │   │
│  │   (탐지 엔진)        │   │   (복제 엔진)                 │   │
│  │                      │   │                               │   │
│  │ ┌──────────────────┐ │   │  put(key, value)              │   │
│  │ │ Safari/ITP 감지  │ │   │    │                          │   │
│  │ │ persist() 확인   │ │   │    ├──▶ IndexedDB (primary)   │   │
│  │ │ OPFS 가용성 확인 │ │   │    └──▶ OPFS (backup)         │   │
│  │ │ Storage Estimate │ │   │                               │   │
│  │ └────────┬─────────┘ │   │  get(key)                     │   │
│  │          ▼           │   │    │                          │   │
│  │ ┌──────────────────┐ │   │    ├─ IndexedDB hit? ─▶ 반환  │   │
│  │ │ StorageReport     │ │   │    └─ miss? ─▶ OPFS 조회     │   │
│  │ │                  │ │   │          └─▶ 자동 복구 + 반환  │   │
│  │ │ indexedDB: safe  │ │   │                               │   │
│  │ │ opfs: safe       │ │   │  recoverAll()                 │   │
│  │ │ cacheAPI: warning│ │   │    OPFS ──▶ IndexedDB 일괄복구│   │
│  │ │ overall: safe    │ │   │                               │   │
│  │ └──────────────────┘ │   └───────────────────────────────┘   │
│  └─────────────────────┘                                        │
│                                                                 │
│  ┌──────────────────────┐   ┌───────────────────────────────┐   │
│  │     IndexedDB         │   │     OPFS (Origin Private FS)  │   │
│  │  data-guard-store     │   │  data-guard-backup/           │   │
│  │  ┌────────────────┐   │   │  ┌─────────────────────────┐ │   │
│  │  │ records store   │   │   │  │ {key}.json 파일들       │ │   │
│  │  └────────────────┘   │   │  └─────────────────────────┘ │   │
│  └──────────────────────┘   └───────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**데이터 흐름 요약:**
1. `detectDurability()` → 브라우저 스토리지 환경 탐지 → `StorageReport` (safe/warning/danger 등급)
2. `put()` → IndexedDB + OPFS 이중 기록 (dual-write)
3. `get()` → IndexedDB 조회 → miss 시 OPFS에서 자동 복구 (read-repair)
4. `simulateStorageLoss()` → IndexedDB 삭제 → `recoverAll()`로 OPFS에서 일괄 복구

## Demo

이 프로토타입은 웹 데모 페이지(`index.html`)를 통해 동작을 확인할 수 있습니다.

**실행:**
```bash
npm run build
python3 -m http.server 8765
# 브라우저에서 http://localhost:8765 접속
```

**주요 화면 구성:**

| 영역 | 설명 |
|---|---|
| **Durability Dashboard** | IndexedDB, OPFS, Cache API 각각의 내구성 등급을 safe/warning/danger로 표시 |
| **Detection Details** | persist() 지원 여부, OPFS 가용성, Safari ITP 감지, 스토리지 쿼터/사용량 표시 |
| **Persist Strategy** | persist() 결과에 따른 복제 전략 안내 (GRANTED / DENIED / UNSUPPORTED) |
| **Browser Comparison** | 현재 브라우저 vs Safari(ITP) 내구성 비교 차트 |
| **Replication Demo** | 데이터 저장 → IndexedDB 삭제 → OPFS 자동 복구 시나리오 체험 |

**복구 시나리오 체험 순서:**
```
1. [Save Test Data]    → IndexedDB + OPFS에 3건 저장
2. [Delete IndexedDB]  → IndexedDB만 삭제 (스토리지 유실 시뮬레이션)
3. [Auto-Recover]      → OPFS 백업에서 IndexedDB로 자동 복구

로그 출력 예시:
  ✓ Saved "user-profile" to IndexedDB + OPFS
  ✓ Saved "draft-post" to IndexedDB + OPFS
  ✓ Saved "app-settings" to IndexedDB + OPFS
  ⚠ IndexedDB cleared! Data is gone from primary storage.
  ✓ Recovered "user-profile" from opfs
  ✓ Recovered "draft-post" from opfs
  ✓ Recovered "app-settings" from opfs
```

**라이브러리 사용 예제:**
```typescript
import { detectDurability, DataGuardReplicator } from './dist/data-guard.js';

// 1. 브라우저 스토리지 내구성 탐지
const report = await detectDurability();
console.log(report.overall);   // 'safe' | 'warning' | 'danger'
console.log(report.details);   // { isSafari, isITP, opfsAvailable, ... }

// 2. 크로스 스토리지 복제기 사용
const guard = new DataGuardReplicator({
  onRecovery: (key, source) => console.log(`복구됨: ${key} ← ${source}`)
});

await guard.put('user-data', JSON.stringify({ name: 'Alice' }));
const value = await guard.get('user-data');  // IndexedDB 우선, miss 시 OPFS 자동 복구
```

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
