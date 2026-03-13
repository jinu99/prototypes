# Local Agent VRAM Resource Planner

> GGUF 메타데이터 기반 멀티 모델 VRAM 예측 및 리소스 플래닝 도구

## 실행 방법

```bash
# 의존성 설치
uv sync

# 웹 서버 실행 (http://localhost:8000)
uv run main.py

# CLI 모드
uv run main.py --cli

# 커스텀 포트
uv run main.py --port 3000
```

## 기능

- **GGUF 파서**: 바이너리 GGUF 파일에서 모델 구조 메타데이터 추출
- **VRAM 계산기**: 가중치 + KV 캐시 + 활성화 + 오버헤드 수식 기반 추정
- **멀티 모델 플래너**: 2+ 모델 동시 실행 시 총 VRAM 산출 및 실현 가능성 판단
- **그리드 서치**: 모델×양자화×컨텍스트 조합 중 VRAM 예산 내 실행 가능한 것 필터링
- **MoE 오프로딩**: Expert 수 별 VRAM/RAM 분배 시나리오 표시
- **llama.cpp 검증**: 커뮤니티 레퍼런스 값 대비 오차율 확인 (7/7 pass, ≤20%)

## 구조

```
local-agent-resource-planner/
├── main.py              # 엔트리포인트 (웹/CLI 모드)
├── gguf_parser.py       # GGUF 바이너리 파서 + 샘플 프로파일
├── vram_calculator.py   # VRAM 추정 수식 엔진
├── planner.py           # 멀티 모델 플래닝 + 그리드 서치
├── server.py            # HTTP API 서버
├── index.html           # 웹 UI (단일 HTML + vanilla JS)
├── create_test_gguf.py  # 테스트용 GGUF 파일 생성기
├── test_browser.py      # Playwright 브라우저 테스트
├── test_models/         # 생성된 테스트 GGUF 파일
├── BUILD_LOG.md         # 빌드 일지
└── STATUS.md            # 최종 상태
```

## 원본
prototype-pipeline spec: local-agent-resource-planner
