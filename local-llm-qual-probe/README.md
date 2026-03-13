# Local LLM Quality Probe

> 소형 로컬 LLM의 실패 패턴(JSON 깨짐, 멀티턴 붕괴, 과잉 출력)을 한 줄 명령으로 감지하는 CLI 도구

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실제 LLM 서버 대상 실행 (Ollama, llama.cpp, vLLM 등)
uv run llm-qual-probe http://localhost:11434

# mock 모드 (LLM 서버 없이 테스트)
uv run llm-qual-probe http://localhost:11434 --mock

# 특정 프로브만 실행
uv run llm-qual-probe http://localhost:11434 --mock -p structured,multiturn

# 모델 지정 + JSON 리포트 경로 지정
uv run llm-qual-probe http://localhost:11434 -m llama3.2 -o results.json
```

## 프로브

| 프로브 | 설명 |
|--------|------|
| `structured` | JSON/YAML 파싱 성공률, 스키마 준수율, 필드 환각률 측정 |
| `multiturn` | 7턴x2 자동 대화, 반복 출력 및 컨텍스트 망각 감지 |
| `efficiency` | thinking on/off 및 시스템 프롬프트 변형별 토큰 사용량 비교 |

## 구조

```
llm_qual_probe/
  cli.py           # CLI 엔트리포인트
  client.py        # OpenAI-호환 API 클라이언트 + mock 모드
  reporter.py      # Rich 터미널 리포트 + JSON 내보내기
  probes/
    structured.py  # 구조화 출력 진단
    multiturn.py   # 멀티턴 안정성 테스트
    efficiency.py  # 출력 효율성 검사
```

## 원본
prototype-pipeline spec: local-llm-qual-probe
