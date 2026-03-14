# Local Coding Agent Stabilizer

> OpenAI-호환 프록시로 로컬 LLM 코딩 에이전트의 파괴적 파일 편집을 실시간 감지·차단하는 미들웨어

## 실행 방법

```bash
# 의존성 설치
uv sync

# Mock 모드 실행 (Ollama 불필요)
uv run python proxy.py --mock

# 라이브 모드 실행 (Ollama 필요)
uv run python proxy.py --backend http://localhost:11434

# 데모 (자동으로 서버 시작 + 테스트 실행)
./demo.sh
```

대시보드: http://localhost:8400/

### Aider 연동

```bash
# 1. 프록시 시작
uv run python proxy.py

# 2. Aider를 프록시 경유로 실행
OPENAI_API_BASE=http://localhost:8400/v1 aider --model ollama/codellama
```

## 기능

- **파괴적 편집 감지**: 파일 삭제, 빈 파일 쓰기, 80% 이상 코드 소실 차단
- **루프 감지**: 동일 도구 연속 3회 호출 시 세션 중단
- **SSE 스트리밍**: OpenAI-호환 스트리밍 응답 투명 전달
- **세션 로그**: SQLite에 모든 도구 호출 + 차단 이벤트 기록
- **대시보드**: 세션 상태, 도구 호출 이력, 차단 이벤트 실시간 조회

## 구조

```
├── proxy.py            # FastAPI 리버스 프록시 (메인 서버)
├── analyzer.py         # diff 분석 기반 파괴적 편집 감지
├── loop_detector.py    # 연속 동일 도구 호출 루프 감지
├── db.py               # SQLite 세션/도구호출 로그
├── dashboard.html      # 단일 HTML 대시보드 (vanilla JS)
├── test_scenarios.py   # 자동화된 테스트 시나리오
├── test_dashboard.py   # Playwright 대시보드 테스트
├── demo.sh             # 원클릭 데모 스크립트
├── BUILD_LOG.md        # 빌드 일지
└── STATUS.md           # 프로토타입 상태
```

## 원본
prototype-pipeline spec: local-coding-agent-stabilizer
