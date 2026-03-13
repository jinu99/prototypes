# 에스컬레이션 품질 시뮬레이터: Workflow vs Agent

> Agent의 confidence 기반 에스컬레이션이 Workflow의 규칙 기반 에스컬레이션보다 품질이 높다는 가설을 시뮬레이션으로 검증한다.

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
