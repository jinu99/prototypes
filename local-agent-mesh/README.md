# Local Agent Mesh

> 소형/대형 LLM 간 복잡도 기반 스마트 라우팅 + self-delegation CLI 도구

## 실행 방법

```bash
# 의존성 설치
uv sync

# 단일 요청
uv run python main.py ask "Summarize the benefits of renewable energy"

# 전체 데모 (5개 시나리오)
uv run python main.py demo

# 상세 출력
uv run python main.py demo -v

# 옵션
uv run python main.py --help
```

## 아키텍처

```
요청 → [복잡도 분류기] → simple → [소형 모델] → [self-eval]
           │                                        │
           │                              confidence ≥ 0.6 → 응답 반환
           │                              confidence < 0.6 → [대형 모델] → 응답 반환
           │
           └──→ complex → [대형 모델] → 응답 반환
```

**핵심 메커니즘:**

1. **복잡도 라우팅** (`router.py`): TF-IDF + 키워드 heuristic으로 요청 복잡도 분류
2. **모델 생성** (`models.py`): Ollama REST API 클라이언트 (미설치 시 mock fallback)
3. **Self-evaluation** (`confidence.py`): hedging 언어, 응답 길이, 완성도 기반 신뢰도 평가
4. **오케스트레이션** (`mesh.py`): 라우팅 → 생성 → 평가 → 에스컬레이션 파이프라인

## 구조

```
local-agent-mesh/
├── main.py              # CLI 진입점 (ask, demo 커맨드)
├── agent_mesh/
│   ├── __init__.py
│   ├── models.py        # Ollama 클라이언트 + mock fallback
│   ├── router.py        # TF-IDF 복잡도 분류기
│   ├── confidence.py    # Self-evaluation 신뢰도 평가
│   ├── mesh.py          # 오케스트레이션 파이프라인
│   └── display.py       # ANSI 터미널 출력
├── pyproject.toml
├── BUILD_LOG.md         # 빌드 일지
├── STATUS.md            # 검증 결과
└── README.md
```

## 데모 시나리오

| # | 유형 | 라우팅 | 결과 |
|---|------|--------|------|
| 1 | 간단한 요약 | simple → small | 소형 모델에서 처리 완료 |
| 2 | 간단한 Q&A | simple → small | 소형 모델에서 처리 완료 |
| 3 | 복잡한 코드 | complex → large | 대형 모델로 직행 |
| 4 | 추론 과제 | simple → small → **escalate** | 소형 시도 → 자신감 부족 → 대형 에스컬레이션 |
| 5 | 복잡한 설계 | complex → large | 대형 모델로 직행 |

## Ollama 연동

Ollama가 로컬에서 실행 중이면 자동으로 감지하여 실제 모델을 사용합니다:

```bash
# Ollama 설치 후
ollama pull qwen2.5:0.5b
ollama pull qwen2.5:7b
ollama serve

# 실제 모델로 실행
uv run python main.py demo
```

## 원본
prototype-pipeline spec: local-agent-mesh
