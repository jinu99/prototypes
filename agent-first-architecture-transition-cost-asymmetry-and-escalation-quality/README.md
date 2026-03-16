# 에스컬레이션 품질 시뮬레이터: Workflow vs Agent

> Agent의 confidence 기반 에스컬레이션이 Workflow의 규칙 기반 에스컬레이션보다 품질이 높다는 가설을 시뮬레이션으로 검증한다.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (CLI)                            │
│                   시뮬레이션 오케스트레이터                        │
└──────────┬──────────────────────────────────┬───────────────────┘
           │                                  │
           ▼                                  ▼
┌─────────────────────┐           ┌──────────────────────────────┐
│  scenarios.py        │           │  server.py                   │
│  ┌───────────────┐  │           │  HTTP 서버 (port 8000)        │
│  │ Scenario ×10  │  │           │  dashboard.html 서빙          │
│  │ ○ simple ×5   │  │           └──────────┬───────────────────┘
│  │ ◉ complex ×3  │  │                      │
│  │ ◆ edge ×2     │  │                      ▼
│  └───────────────┘  │           ┌──────────────────────────────┐
└──────────┬──────────┘           │  dashboard.html              │
           │                      │  시각화 대시보드 (vanilla JS)  │
           │ 시나리오 입력          └──────────────────────────────┘
           │                                  ▲
     ┌─────┴─────┐                            │
     ▼           ▼                   output/results.json
┌──────────┐ ┌───────────────────┐            ▲
│ Workflow │ │ Agent 엔진         │            │
│ 엔진     │ │                   │            │
│          │ │ 5가지 판단 순간:   │            │
│ 규칙기반 │ │ 1. Intent 해석    │            │
│ if/else  │ │ 2. Tool 선택      │            │
│ 분기     │ │ 3. Context 충분성 │            │
│          │ │ 4. 결과 검증      │            │
│ 키워드   │ │ 5. 사람 개입 판단 │            │
│ 매칭     │ │                   │            │
│ + 감정   │ │ confidence 캐스케 │            │
│ 키워드   │ │ 이드 → 에스컬레이 │            │
│          │ │ 션 결정           │            │
└─────┬────┘ └────────┬──────────┘            │
      │               │                      │
      └───────┬───────┘                      │
              ▼                               │
     ┌─────────────────┐                     │
     │  comparator.py  │                     │
     │                 │                     │
     │ ground truth 대 │                     │
     │ 비 정확도 비교   ├─────────────────────┘
     │ FP/FN 메트릭    │      JSON 결과 저장
     │ 민감도 분석      │
     └─────────────────┘
```

**데이터 흐름**: `scenarios.py`에서 10개의 고객 지원 시나리오(단순 5, 복합 3, 엣지 2)를 정의 → 두 엔진이 동일 시나리오를 독립 처리 → `comparator.py`가 ground truth 대비 정확도, 오탐(FP), 미탐(FN)을 산출 → 결과를 JSON으로 저장하여 CLI 출력 및 웹 대시보드에서 시각화.

## Demo

### CLI 시뮬레이션

```bash
uv run main.py
```

**출력 예시** (10개 시나리오 중 핵심 결과):

```
─── ○ [S04] FAQ 질문 (simple) ───
  정답: 자동 처리 가능
  Workflow: ✗ 에스컬레이션 → level2        ← "환불" 키워드에 과잉 반응
  Agent:    ✓ 자동 처리 → none (confidence: 97%)

─── ◉ [C02] 기술 문제 + 청구 문제 교차 (complex) ───
  정답: 에스컬레이션 필요
  Workflow: ✗ 자동 처리 → none             ← 규칙에 없어서 놓침
  Agent:    ✓ 에스컬레이션 → specialist (confidence: 51%)

─── ◆ [E01] 정중하지만 해지 의향 암시 (edge) ───
  정답: 에스컬레이션 필요
  Workflow: ✗ 자동 처리 → none             ← 키워드가 없어 감지 불가
  Agent:    ✓ 에스컬레이션 → retention_team (confidence: 62%)
```

**집계 결과**:

```
                       Workflow      Agent         차이
  ────────────────────────────────────────────────────
  정확도                      60%      100%      +40%p
  불필요 에스컬레이션              1          0
  놓친 에스컬레이션               3          0

  → Agent가 Workflow보다 40%p 더 정확합니다.
  → Agent는 Workflow가 놓친 3개의 에스컬레이션을 포착했습니다.
```

### 웹 대시보드

```bash
uv run server.py
# → http://localhost:8000/dashboard.html 접속
```

대시보드에서 시나리오별 비교, confidence 분포, 임계값 민감도 분석 차트를 확인할 수 있다.

## 실행 방법

```bash
# 의존성 설치
uv sync

# 시뮬레이션 실행 (CLI)
uv run main.py

# 대시보드 실행 (웹)
uv run server.py
# → http://localhost:8000/dashboard.html 접속
```

## 구조

```
.
├── main.py              # CLI 진입점: 시뮬레이션 실행 + 결과 출력
├── scenarios.py         # 고객 지원 시나리오 10개 정의
├── workflow_engine.py   # 규칙 기반 Workflow 엔진
├── agent_engine.py      # confidence 기반 Agent 엔진 (5가지 판단 순간)
├── comparator.py        # 결과 비교 및 메트릭 산출
├── server.py            # 대시보드 HTTP 서버
├── dashboard.html       # 시각화 대시보드 (vanilla JS)
├── output/
│   └── results.json     # 시뮬레이션 결과 (자동 생성)
├── spec.md              # 프로토타입 스펙
├── BUILD_LOG.md         # 빌드 일지
└── STATUS.md            # 최종 상태
```

## 핵심 개념

**5가지 판단 순간 (Agent 엔진)**
1. Intent 해석 — 고객의 의도를 얼마나 확신하는가
2. Tool 선택 — 어떤 도구/액션을 써야 하는지
3. Context 충분성 — 판단에 필요한 맥락이 충분한가
4. 결과 검증 — 이전 판단들의 종합 검증
5. 사람 개입 판단 — 종합적으로 사람이 필요한가

각 순간에서 confidence 점수를 계산하고, 임계값 이하이면 에스컬레이션을 고려한다. 이 판단 순간들은 독립적이 아니라 **순차적으로 캐스케이드 효과**를 만들어 미묘한 신호를 증폭시킨다.

## 원본 아이디어
Agent-First 아키텍처 전략 - 전환 비용의 비대칭성과 에스컬레이션 품질. Workflow→Agent 전환의 비대칭적 비용과 Agent 아키텍처의 에스컬레이션 품질 우위를 논증하는 아이디어.
