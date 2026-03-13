# STATUS: SUCCESS

## 요약
GGUF 메타데이터 기반 VRAM 예측기. 수식 기반 추정이 llama.cpp 레퍼런스 대비 7/7 모두 20% 이내 오차로 통과. 멀티 모델 동시 실행 계획, MoE expert 오프로딩 시나리오, 그리드 서치 필터링까지 구현.

## 완료 기준 결과
- [x] GGUF 파일에서 모델 구조 메타데이터(파라미터 수, 레이어 수, hidden dim, GQA head, MoE expert 수/활성 수, 양자화)를 파싱하여 출력
- [x] 2개 이상 모델 조합의 총 VRAM 사용량(가중치 + KV 캐시 + 활성화 + 시스템 오버헤드)을 수식 기반으로 산출
- [x] llama.cpp 실행 시 보고되는 VRAM 사용량과 비교하여 오차가 합리적 범위(~20% 이내)임을 1개 이상의 멀티 모델 조합에서 확인 — 7/7 모델 전부 통과 (최대 오차 10.6%)
- [x] 주어진 VRAM 제약 내에서 실행 가능한 모델×양자화×컨텍스트 조합을 필터링하여 표시
- [x] MoE 모델 포함 시 expert 오프로딩 옵션별 예상 VRAM/RAM 사용량을 정보로 표시

## 실행 방법
```bash
uv sync
uv run main.py          # 웹 서버 (http://localhost:8000)
uv run main.py --cli    # CLI 모드
```

## 소요 정보
- 생성일: 2026-03-13
- 원본 spec: local-agent-resource-planner.md
- 자동 생성: prototype-pipeline spawn
