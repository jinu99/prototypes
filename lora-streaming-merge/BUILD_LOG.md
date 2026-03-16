# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-16 Spec 파일 확인 완료
- [판단] 스택 선택: Python + uv (이유: safetensors/torch 생태계가 Python에 집중, CLI 도구에 적합)
- [판단] 의존성: torch (CPU), safetensors, tqdm (이유: 최소 의존성, 표준 라이브러리 argparse로 CLI)
- [판단] 테스트 전략: 가짜 소형 모델(4레이어, 64dim)로 구조를 재현하여 검증. 실제 7B 모델 없이도 스트리밍 머지 로직과 정밀도 검증 가능
- [범위] 핵심 흐름: safe_open으로 레이어별 lazy load → LoRA A·B 행렬곱 → base + scale*AB 머지 → save_file로 순차 저장

## Phase 2 — 구현
- [시도] uv init + uv add torch safetensors tqdm → [결과] 성공 (packaging, numpy 추가 필요)
- [에러] safetensors.torch가 packaging 모듈 요구 → [수정] uv add packaging
- [에러] safetensors _tobytes가 numpy 요구 → [수정] uv add numpy
- [시도] 테스트 픽스처 (4레이어, 64dim, 2샤드, LoRA rank=8) → [결과] 성공
- [시도] 핵심 모듈 구현: shard_map.py, adapter.py, merge.py, estimate.py, verify.py → [결과] 성공
- [에러] pyproject.toml에서 [project.scripts] 위치 잘못 → [수정] 섹션 분리
- [에러] uv가 entry point 설치 안 함 → [수정] [build-system] + [tool.setuptools.packages.find] 추가
- [시도] CLI run + verify → [결과] 성공, 24/30 텐서 머지, allclose 통과

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 기능은 동작하지만 메모리 절약 증명이 부족
- [불만] 초기 구현이 샤드 단위로 텐서를 모아서 save → 피크 RAM이 샤드 크기와 비례하여 1/N 기준 미충족
- [개선] merge.py 전면 재설계: 텐서 1개씩(batch_size=1) 처리 후 바로 save_file → 피크 RAM = 단일 텐서 크기
- [검증] 큰 테스트 모델(8레이어, 512dim, ~84MB): Peak RAM 2.18MB vs 전체 83.91MB = 2.6%. 1/N=12.5% 기준 통과
- [평가] estimate 모듈이 구 방식(샤드 누적) 기준으로 계산 → [개선] 텐서 단위 스트리밍 기준으로 수정
- [평가] 에러 메시지가 raw traceback → [개선] CLI에서 FileNotFoundError 등 깔끔하게 처리

## Phase 4 — 검증
- [체크] 피크 RAM <= 전체/N (32레이어, 82MB 모델): 1.40MB peak, 1/N=2.56MB → 통과
- [체크] allclose(rtol=1e-5): 226개 텐서 전부 일치 → 통과
- [체크] 멀티파일 shard 매핑 (4개 소스 샤드 → 226개 출력 샤드): 정확 동작 → 통과
- [체크] estimate 서브커맨드: 피크 RAM/디스크/시간 리포트 출력 → 통과
- [체크] CLI `lora-merge run --base --adapter --output` 형태 실행 → 통과
- [결과] 5/5 통과 → SUCCESS
