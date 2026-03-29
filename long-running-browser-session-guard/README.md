# Session Guard

> 5KB 드롭인 JS 라이브러리 — 장시간 실행 브라우저 세션의 OOM을 사전 감지하고, 사용자 상태를 보존한 채 자동 복구

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser Tab                                            │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │ performance   │    │ DOM Node     │    │ Detached  │  │
│  │ .memory API   │    │ Counter      │    │ DOM Scan  │  │
│  └──────┬───────┘    └──────┬───────┘    └─────┬─────┘  │
│         │                   │                  │        │
│         ▼                   ▼                  ▼        │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Session Guard (4.3KB gz)              │    │
│  │                                                 │    │
│  │  ┌────────────┐  ┌─────────────┐  ┌──────────┐ │    │
│  │  │ Linear     │  │ Health      │  │ WS/SSE   │ │    │
│  │  │ Regression │──▶ Assessment  │  │ Auto-    │ │    │
│  │  │ OOM Predict│  │ ok/warn/crit│  │ Reconnect│ │    │
│  │  └────────────┘  └──────┬──────┘  └──────────┘ │    │
│  │                         │                       │    │
│  │              ┌──────────┴──────────┐            │    │
│  │              ▼                     ▼            │    │
│  │  ┌───────────────┐  ┌──────────────────┐       │    │
│  │  │ Health Overlay │  │ Auto Recovery    │       │    │
│  │  │ Panel + Chart  │  │ sessionStorage   │       │    │
│  │  │ (bottom-right) │  │ → soft reload    │       │    │
│  │  └───────────────┘  │ → state restore  │       │    │
│  │                     └──────────────────┘       │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Demo

데모 페이지에서 다음 플로우를 시연할 수 있다:

1. **Start Leak** → 조절 가능한 속도로 메모리 누수 시작
2. **Burst (10x)** → 한 번에 대량 메모리 할당
3. **Flood DOM** → DOM 노드 1000개 추가
4. 오버레이에서 힙 사용량 차트, OOM 예측 시간 실시간 표시
5. 임계치 도달 시 → 앱 상태(이름, 카운터) 스냅샷 → 자동 리로드 → 복원
6. **Force Recovery** → 수동으로 복구 플로우 테스트

```
# 실제 테스트 결과 (node test-demo.js)
--- Test 3: Library size ---
  Raw: 14307 bytes (14.0 KB)
  Gzipped: 4406 bytes (4.3 KB)
  Under 5KB gzipped: PASS

--- Test 4: API completeness ---
  performance.memory collection: PASS
  DOM node counting: PASS
  Linear regression: PASS
  Heap threshold check: PASS
  Auto recovery: PASS
  State snapshot: PASS
  Soft reload: PASS
  Exponential backoff (WS): PASS
  Overlay panel: PASS
  Memory chart (canvas): PASS
  Destroy/cleanup: PASS
```

## 실행 방법

```bash
# 방법 1: npx serve
npx serve .
# 브라우저에서 http://localhost:3000 접속

# 방법 2: Python
python3 -m http.server 8080
# 브라우저에서 http://localhost:8080 접속

# 방법 3: 아무 정적 파일 서버
# Chrome 또는 Edge에서 열 것 (performance.memory API 필요)
```

### 다른 프로젝트에 적용

```html
<script src="session-guard.js"></script>
<script>
  var guard = new SessionGuard({
    pollInterval: 5000,       // 수집 주기 (ms)
    heapThreshold: 0.85,      // 힙 사용률 임계치
    autoRecover: true,        // 자동 복구 활성화
    showOverlay: true,        // 헬스 오버레이 표시
    stateSelector: function() {
      // 복구 시 보존할 상태 반환
      return { formData: getFormData(), scrollPos: window.scrollY };
    },
    onRecover: function(snapshot) {
      // 복구 후 상태 복원
      restoreFormData(snapshot.state.formData);
    }
  });
</script>
```

## 구조

```
long-running-browser-session-guard/
├── session-guard.js   # 핵심 라이브러리 (14KB raw, 4.3KB gzipped)
├── index.html         # 데모 페이지 (메모리 누수 시뮬레이터)
├── test-demo.js       # 기능 검증 스크립트
├── BUILD_LOG.md       # 빌드 일지
├── STATUS.md          # 완료 상태
└── README.md          # 이 파일
```

## 원본
prototype-pipeline spec: long-running-browser-session-guard
