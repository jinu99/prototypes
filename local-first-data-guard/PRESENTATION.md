---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Local-First Data Guard

**브라우저 스토리지 내구성 자동 탐지 + IndexedDB ↔ OPFS 크로스 스토리지 자동 복구 라이브러리**

- 카테고리: Local-First / Browser Storage
- 스택: TypeScript, esbuild, IndexedDB, OPFS, Storage API
- 날짜: 2026-03-11

<!--
로컬 퍼스트 웹앱을 만들면 꼭 마주치는 문제가 하나 있다. 브라우저가 데이터를 지워버린다는 거다. 특히 Safari에서. 오늘 소개할 프로토타입은 이 문제를 탐지하고 자동으로 복구하는 경량 라이브러리다.
-->

---

## Background

**로컬 퍼스트 웹앱의 구조적 취약점**

- 2020년부터 Safari는 ITP(Intelligent Tracking Prevention) 정책으로 **7일간 미방문 사이트의 IndexedDB, localStorage를 경고 없이 삭제**
- 사용자는 "로컬에 저장했다"고 믿었는데, 어느 날 데이터가 사라져 있음
- PWA 홈스크린 설치, OPFS 같은 우회 방법이 있지만 이를 **통합적으로 처리하는 라이브러리가 없다**
- localForage는 ITP를 고려하지 않고, ElectricSQL/PowerSync 같은 동기화 엔진은 서버 동기화에 초점

<!--
로컬 퍼스트 앱이 요즘 다시 주목받고 있다. 서버 의존 없이 빠르게 동작하니까. 그런데 이 접근에는 구조적 취약점이 하나 있다. 브라우저가 주인이라는 거다. Safari는 ITP 정책으로 7일간 방문하지 않은 사이트의 데이터를 조용히 지운다. 개발자 입장에서 꽤 당황스러운 상황이다. localStorage, IndexedDB 다 날아간다. 우회 방법은 개별적으로 존재하는데, 이걸 통합해서 처리하는 도구가 없다는 게 문제다.
-->

---

## Pain Point

**커뮤니티에서 반복적으로 나오는 고통**

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/webdev | ★★★★ | Safari가 7일 후 IndexedDB 데이터를 **조용히 삭제**하여 로컬 퍼스트 웹앱의 사용자 데이터가 손실 |
| 2 | r/webdev | ★★★ | Safari가 경고 없이 localStorage를 삭제하여 **로그인 상태와 설정**을 잃음 |
| 3 | HN | ★★★ | 로컬 퍼스트 앱 개발 시 어떤 동기화 엔진을 선택해야 할지 **2026년에도 명확한 기준이 없다** |

핵심: "데이터를 로컬에 저장했는데 브라우저가 마음대로 지운다"

<!--
Reddit r/webdev과 Hacker News에서 이 얘기가 계속 반복된다. Safari가 데이터를 조용히 지워서 사용자 데이터가 날아갔다는 거다. Signal strength가 4점짜리 글이 있을 정도로 공감대가 크다. 결국 이건 "내가 저장한 데이터를 브라우저가 마음대로 지운다"는 신뢰의 문제다. 개발자 입장에서 어떤 스토리지가 안전한지 판단할 기준이 없으니 시행착오를 반복하게 된다.
-->

---

## Solution

**한 줄 요약: 스토리지 내구성을 탐지하고, 이중 기록으로 자동 복구한다**

### 기존 접근과의 차이

| 기존 | Local-First Data Guard |
|------|----------------------|
| localForage: 스토리지 추상화만 제공, ITP 무시 | 브라우저별 ITP/persist 정책을 **자동 탐지** |
| 동기화 엔진: 서버 동기화에 초점 | **클라이언트 내** 크로스 스토리지 복제 |
| 개발자가 수동으로 OPFS/PWA 대응 | dual-write + read-repair로 **자동 복구** |

### 검증 목표
> 브라우저별 스토리지 내구성 자동 탐지 + 크로스 스토리지 복제로 데이터 손실을 방지하는 것이 개발자에게 실질적 가치를 제공하는지

<!--
접근법은 꽤 단순하다. 두 가지를 한다. 첫째, 지금 이 브라우저가 데이터를 얼마나 안전하게 보관하는지 자동으로 탐지한다. Safari인지, ITP가 걸리는지, persist가 승인됐는지. 둘째, IndexedDB에 쓸 때 OPFS에도 같이 쓴다. 한쪽이 날아가면 다른 쪽에서 자동으로 복구한다. 기존 솔루션과의 차이는, 이걸 개발자가 수동으로 하는 게 아니라 라이브러리가 알아서 한다는 거다.
-->

---

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
│  │  Safari/ITP 감지     │   │  put() → IDB + OPFS 이중기록  │   │
│  │  persist() 확인      │   │  get() → IDB miss시 OPFS 복구 │   │
│  │  OPFS 가용성 확인    │   │  recoverAll() → 일괄 복구     │   │
│  │  → StorageReport     │   │                               │   │
│  └─────────────────────┘   └───────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────┐   ┌───────────────────────────────┐   │
│  │     IndexedDB         │   │     OPFS (Origin Private FS)  │   │
│  │  (Primary Storage)    │   │  (Backup — 파일 기반)         │   │
│  └──────────────────────┘   └───────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

- **detect.ts**: Safari/ITP 감지, persist() 확인, OPFS 가용성 → safe/warning/danger 등급 산출
- **replicate.ts**: dual-write(이중 기록) + read-repair(읽기 시 자동 복구) 패턴

<!--
구조는 두 개의 모듈로 나뉜다. detect.ts가 탐지 엔진이고, replicate.ts가 복제 엔진이다. 탐지 엔진은 Safari 여부, ITP 버전, persist() 승인 상태, OPFS 가용성을 확인해서 스토리지별로 safe, warning, danger 등급을 매긴다. 복제 엔진은 데이터를 쓸 때 IndexedDB와 OPFS에 동시에 쓰고, 읽을 때 IndexedDB에 없으면 OPFS에서 자동 복구한다. 분산 시스템에서 쓰는 read-repair 패턴을 브라우저 스토리지에 적용한 거다.
-->

---

## Demo

### 복구 시나리오 — 핵심 흐름

```
1. [Save Test Data]    → IndexedDB + OPFS에 3건 동시 저장
2. [Delete IndexedDB]  → IndexedDB만 삭제 (스토리지 유실 시뮬레이션)
3. [Auto-Recover]      → OPFS 백업에서 IndexedDB로 자동 복구
```

```
✓ Saved "user-profile" to IndexedDB + OPFS
✓ Saved "draft-post" to IndexedDB + OPFS
✓ Saved "app-settings" to IndexedDB + OPFS
⚠ IndexedDB cleared! Data is gone from primary storage.
✓ Recovered "user-profile" from opfs
✓ Recovered "draft-post" from opfs
✓ Recovered "app-settings" from opfs
```

### 탐지 대시보드
- 스토리지별 내구성 등급 (safe/warning/danger) 시각화
- Chrome vs Safari ITP 비교 차트
- persist() 전략 분기 안내

<!--
데모는 단일 HTML 페이지에서 동작한다. 가장 인상적인 부분은 복구 시나리오다. 데이터 3건을 저장하면 IndexedDB와 OPFS에 동시에 들어간다. 그 다음 IndexedDB를 삭제해버린다. Safari가 7일 후에 하는 일을 시뮬레이션한 거다. 그리고 자동 복구를 누르면 OPFS 백업에서 3건이 전부 살아난다. 사용자 입장에서는 데이터가 사라졌다가 돌아온 거다. 탐지 대시보드에서는 현재 브라우저의 스토리지 안전성을 한눈에 볼 수 있다.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 결정 | 이유 |
|------|------|
| **esbuild + 단일 HTML** | Spec이 "번들 사이즈 최소화, 프레임워크 무관"을 명시. 결과: 8.7kb ESM, 3ms 빌드 |
| **OPFS를 백업 스토리지로 선택** | ITP 정책 하에서 IndexedDB보다 약간 더 내구성이 높음. 파일 기반이라 key별 개별 관리 가능 |
| **innerHTML → DOM API 리팩토링** | 보안 hook에서 XSS 경고 → createElement/textContent로 전면 교체 |

### 심의 점수

| 항목 | 점수 |
|------|:----:|
| 문제 진정성 (authenticity) | 3.7/5 |
| 프로토타입 적합성 (prototypability) | 4.0/5 |
| 신선도 (freshness) | 3.0/5 |
| 학습 가치 (learning value) | 3.7/5 |

<!--
스택 선택에서 고민은 거의 없었다. Spec이 방향을 명확히 잡아줬다. esbuild로 8.7kb짜리 ESM 번들을 뽑았고, 빌드는 3ms면 끝난다. 시행착오가 있었던 건 innerHTML이다. 처음에 innerHTML로 UI를 그렸는데 보안 hook에서 XSS 경고가 떴다. 전부 DOM API로 리팩토링했다. 심의 점수를 보면 프로토타입 적합성이 4.0으로 가장 높다. 실제로 2시간 안에 핵심 흐름을 검증할 수 있는 범위였다. 신선도가 3.0인 건 솔직히 ITP 문제 자체가 2020년부터 알려진 거라 새롭지는 않기 때문이다.
-->

---

## Results & Future

### 성과 (4/4 완료 기준 통과)

- [x] `detectDurability()` — 스토리지별 내구성 점수 반환
- [x] IndexedDB ↔ OPFS 크로스 복제, 삭제 후 자동 복구
- [x] `navigator.storage.persist()` 결과에 따른 전략 분기
- [x] 단일 HTML 데모에서 Chrome/Safari 내구성 비교 시각화
- 테스트: 핵심 로직 21개 + Spec 검증 4개 전부 통과

### 한계

- OPFS 미지원 브라우저에서 Cache API 폴백 미구현
- 실제 Safari 환경에서의 실기기 테스트 미수행 (Node.js mock 기반)
- 프로덕션 수준의 에러 핸들링, 마이그레이션 미포함

### 프로덕트가 되려면

- Cache API 폴백 체인 추가 (OPFS → Cache API → Service Worker)
- 실제 Safari/iOS 환경 E2E 테스트
- 스토리지 사용량 모니터링 + 쿼터 초과 시 알림
- npm 패키지 배포 + React/Vue 어댑터

<!--
4개 완료 기준을 전부 통과했다. 21개 테스트도 다 통과했고. 솔직히 아쉬운 건 두 가지다. 하나는 OPFS가 안 되는 브라우저에서 Cache API로 폴백하는 걸 못 넣었다. 다른 하나는 실제 Safari에서 테스트를 못 했다. Node.js의 fake-indexeddb로 핵심 로직은 검증했지만, 브라우저 환경은 다를 수 있다. 이게 실제 프로덕트가 되려면 폴백 체인을 늘리고, 실기기 E2E 테스트를 붙이고, npm 패키지로 배포하는 과정이 필요하다. 결국 이 프로토타입이 검증한 건, 브라우저 스토리지 내구성 문제를 라이브러리 레벨에서 자동으로 처리하는 게 가능하다는 거다.
-->
